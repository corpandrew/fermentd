"""Queue phone notifications so a slow or down ntfy server cannot stall control."""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import timedelta
from pathlib import Path

from fermentd.clock import Clock
from fermentd.db.connection import connect
from fermentd.notify.ntfy import NtfyNotifier
from fermentd.timefmt import isoformat, parse_iso
from fermentd.web.status import alert_sentence

LOG = logging.getLogger("fermentd")

_RETRY_S = (30, 120, 600, 1800, 3600)
_CHECKIN_KEY = "ntfy_checkin"
_CHECKIN_DELAY = "30m"
_CHECKIN_WINDOW = timedelta(minutes=30)
_CHECKIN_REFRESH_S = 15 * 60


class OutboxNotifier:
    """Accept notifications immediately and deliver them on a background thread."""

    def __init__(self, database: Path, clock: Clock, inner: NtfyNotifier) -> None:
        self._database = database
        self._clock = clock
        self._inner = inner
        self._lock = threading.Lock()
        self._drain_lock = threading.Lock()
        self._queue: list[tuple[str, str, str, str]] = []
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._closed = False
        self._thread: threading.Thread | None = None
        self._checkin_fire_at = self._stored_fire_at()

    def notify(self, kind: str, severity: str, title: str, body: str) -> None:
        if kind != "digest" and severity not in {"action", "critical"}:
            return
        with self._lock:
            self._queue.append((kind, severity, title, body))
        self._wake.set()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="fermentd-ntfy", daemon=True)
        self._thread.start()

    def finish(self) -> None:
        self._closed = True
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=12)
            self._thread = None
        self.drain(budget_s=15)
        self.cancel_checkin()

    def close(self) -> None:
        self._closed = True
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def drain(self, *, budget_s: float | None = None) -> None:
        with self._drain_lock:
            self._drain(budget_s=budget_s)

    def _drain(self, *, budget_s: float | None) -> None:
        self._persist_queue()
        deadline = None if budget_s is None else time.monotonic() + budget_s
        conn = connect(self._database)
        try:
            rows = conn.execute(
                """
                SELECT * FROM NOTIFICATION_OUTBOX
                WHERE sent_at IS NULL AND next_attempt_at <= ?
                ORDER BY id
                """,
                (isoformat(self._clock.now()),),
            ).fetchall()
            for row in rows:
                if deadline is not None and time.monotonic() >= deadline:
                    return
                if self._inner.deliver(row["kind"], row["severity"], row["title"], row["body"]):
                    conn.execute(
                        "UPDATE NOTIFICATION_OUTBOX SET sent_at = ? WHERE id = ?",
                        (isoformat(self._clock.now()), row["id"]),
                    )
                    conn.commit()
                    continue
                attempts = int(row["attempts"]) + 1
                delay = _RETRY_S[min(attempts - 1, len(_RETRY_S) - 1)]
                nxt = isoformat(self._clock.now() + timedelta(seconds=delay))
                conn.execute(
                    """
                    UPDATE NOTIFICATION_OUTBOX
                    SET attempts = ?, next_attempt_at = ?
                    WHERE id = ?
                    """,
                    (attempts, nxt, row["id"]),
                )
                conn.commit()
        finally:
            conn.close()

    def refresh_checkin(self) -> None:
        if self._closed:
            return
        if self._checkin_fire_at is not None:
            remaining = (self._checkin_fire_at - self._clock.now()).total_seconds()
            if remaining > _CHECKIN_REFRESH_S:
                return
        self._replace_checkin()

    def cancel_checkin(self) -> None:
        self._closed = True
        stored = self._load_checkin()
        if stored and stored.get("id"):
            self._inner.cancel(str(stored["id"]))
        self._checkin_fire_at = None
        self._save_checkin(None)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.clear()
            try:
                self.drain()
                self.refresh_checkin()
            except Exception:
                LOG.warning("notification delivery failed", exc_info=True)
            if self._stop.is_set():
                break
            self._wake.wait(5)

    def _persist_queue(self) -> None:
        with self._lock:
            items = self._queue
            self._queue = []
        if not items:
            return
        now = isoformat(self._clock.now())
        conn = connect(self._database)
        try:
            conn.executemany(
                """
                INSERT INTO NOTIFICATION_OUTBOX (
                    created_at, kind, severity, title, body, attempts, next_attempt_at
                ) VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                [(now, kind, severity, title, body, now) for kind, severity, title, body in items],
            )
            conn.commit()
        finally:
            conn.close()

    def _replace_checkin(self) -> None:
        if self._closed:
            return
        stored = self._load_checkin()
        if stored and stored.get("id") and not self._inner.cancel(str(stored["id"])):
            return
        message_id = self._inner.schedule(
            self._vessel_title(),
            alert_sentence("pi_offline", {}),
            severity="critical",
            delay=_CHECKIN_DELAY,
        )
        if message_id is None:
            return
        fire_at = self._clock.now() + _CHECKIN_WINDOW
        self._checkin_fire_at = fire_at
        self._save_checkin({"id": message_id, "fire_at": isoformat(fire_at)})

    def _vessel_title(self) -> str:
        conn = connect(self._database)
        try:
            rows = conn.execute("SELECT name FROM VESSEL WHERE enabled = 1 ORDER BY id").fetchall()
        finally:
            conn.close()
        if not rows:
            return "fermentd"
        return ", ".join(row["name"] for row in rows)

    def _stored_fire_at(self):
        stored = self._load_checkin()
        if not stored or not stored.get("fire_at"):
            return None
        try:
            return parse_iso(str(stored["fire_at"]))
        except ValueError:
            return None

    def _load_checkin(self) -> dict | None:
        conn = connect(self._database)
        try:
            row = conn.execute("SELECT value FROM SETTING WHERE key = ?", (_CHECKIN_KEY,)).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        try:
            loaded = json.loads(row["value"])
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, dict) else None

    def _save_checkin(self, payload: dict | None) -> None:
        conn = connect(self._database)
        try:
            if payload is None:
                conn.execute("DELETE FROM SETTING WHERE key = ?", (_CHECKIN_KEY,))
            else:
                conn.execute(
                    """
                    INSERT INTO SETTING (key, value, updated_at, updated_by)
                    VALUES (?, ?, ?, 'notify')
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at,
                        updated_by = excluded.updated_by
                    """,
                    (_CHECKIN_KEY, json.dumps(payload), isoformat(self._clock.now())),
                )
            conn.commit()
        finally:
            conn.close()
