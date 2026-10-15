"""Open, escalate, acknowledge, and resolve alerts. Dedupe keys keep one open alert per condition."""

from __future__ import annotations

import json
import sqlite3

from fermentd.clock import Clock
from fermentd.timefmt import isoformat

_RANK = {"info": 0, "warning": 1, "action": 2, "critical": 3}


def raise_alert(
    conn: sqlite3.Connection,
    clock: Clock,
    *,
    dedupe_key: str,
    severity: str,
    alert_type: str,
    detail: dict,
    vessel_id: str | None,
    batch_id: int | None,
    actor: str = "control",
) -> str:
    now = isoformat(clock.now())
    existing = conn.execute(
        "SELECT * FROM ALERT WHERE dedupe_key = ? AND status != 'resolved' ORDER BY id DESC LIMIT 1",
        (dedupe_key,),
    ).fetchone()
    if existing is not None:
        if _RANK[severity] > _RANK[existing["severity"]]:
            conn.execute("UPDATE ALERT SET severity = ? WHERE id = ?", (severity, existing["id"]))
            return "escalated"
        return "existing"
    cursor = conn.execute(
        """
        INSERT INTO EVENT (ts, batch_id, vessel_id, type, severity, actor, detail_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (now, batch_id, vessel_id, alert_type, severity, actor, json.dumps(detail)),
    )
    conn.execute(
        """
        INSERT INTO ALERT (event_id, dedupe_key, severity, status, opened_at)
        VALUES (?, ?, ?, 'open', ?)
        """,
        (cursor.lastrowid, dedupe_key, severity, now),
    )
    return "opened"


def ack_alert(conn: sqlite3.Connection, clock: Clock, alert_id: int, actor: str) -> str | None:
    row = conn.execute("SELECT * FROM ALERT WHERE id = ?", (alert_id,)).fetchone()
    if row is None:
        return "NOT_FOUND"
    if row["status"] == "resolved":
        return None
    conn.execute(
        "UPDATE ALERT SET status = 'acked', acked_at = ?, acked_by = ? WHERE id = ?",
        (isoformat(clock.now()), actor, alert_id),
    )
    return None


def resolve_alert(conn: sqlite3.Connection, clock: Clock, dedupe_key: str) -> None:
    conn.execute(
        """
        UPDATE ALERT SET status = 'resolved', resolved_at = ?
        WHERE dedupe_key = ? AND status != 'resolved'
        """,
        (isoformat(clock.now()), dedupe_key),
    )
