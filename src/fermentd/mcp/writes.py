"""MCP write tools. They change state on the Pi, but only through the controller's command queue:
the same COMMAND path, validation and audit log the web UI uses, with actor 'mcp'. The write
connection is separate from the read-only one the read tools use."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from fermentd.control.commands import enqueue
from fermentd.db.connection import connect
from fermentd.mcp import queries as q

ACTOR = "mcp"
WAIT_S = 20.0


class WriteRejected(ValueError):
    pass


class _Clock:
    """Stamp commands with the controller's clock (its last write), like the web UI does."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def now(self) -> datetime:
        try:
            from fermentd.control.commands import database_now

            return database_now(self.conn, datetime.now(UTC))
        except Exception:  # noqa: BLE001
            return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


class Writer:
    def __init__(self, db_path: Path | str | None = None, conn: sqlite3.Connection | None = None,
                 pump: Callable[[], None] | None = None, clock=None) -> None:
        self._path = db_path
        self._conn = conn
        self.pump = pump  # tests: run one controller tick instead of waiting for the live controller
        self.clock = clock

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = connect(Path(self._path))
        return self._conn

    def submit(self, command_type: str, params: dict) -> dict:
        command_id = enqueue(
            self.conn,
            self.clock or _Clock(self.conn),
            actor=ACTOR,
            command_type=command_type,
            params=params,
            idempotency_key=f"mcp-{uuid.uuid4()}",
        )
        deadline = time.monotonic() + WAIT_S
        while True:
            if self.pump is not None:
                self.pump()
            row = self.conn.execute("SELECT status, result_json FROM COMMAND WHERE id = ?", (command_id,)).fetchone()
            if row["status"] != "pending":
                result = json.loads(row["result_json"] or "{}")
                if row["status"] != "done":
                    raise WriteRejected(result.get("message") or result.get("error") or json.dumps(result))
                return result
            if self.pump is not None or time.monotonic() >= deadline:
                raise WriteRejected(
                    f"the controller did not process command {command_id} within {WAIT_S:.0f} s; "
                    "it may not be running (it will expire unprocessed)"
                )
            time.sleep(0.2)


def _profile_row(ro: sqlite3.Connection, profile_id: str) -> dict | None:
    row = ro.execute(
        "SELECT definition_json FROM BEVERAGE_PROFILE WHERE id = ? ORDER BY version DESC LIMIT 1", (profile_id,)
    ).fetchone()
    return None if row is None else json.loads(row["definition_json"])


def start_batch(ro: sqlite3.Connection, writer: Writer, vessel_id: str, profile_id: str, name: str,
                batch_size: str | float | None = None, target_f: float | None = None,
                variant_id: int | None = None, copy_tweaks_from_batch_id: int | None = None,
                stage: str | None = None) -> dict:
    # Clear pre-checks with readable errors. The controller re-validates everything.
    vessel = q._vessel(ro, vessel_id)
    active = q._active_batch(ro, vessel_id)
    if active is not None:
        raise WriteRejected(
            f"vessel {vessel_id} already has an active batch: #{active['id']} '{active['name']}' "
            f"(stage {active['stage']}). End it first."
        )
    profile = _profile_row(ro, profile_id)
    if profile is None:
        raise WriteRejected(f"unknown profile_id {profile_id!r}; see list_profiles")
    if profile.get("status") != "supported":
        raise WriteRejected(f"profile {profile_id} is {profile.get('status')}, not supported")
    allowed = profile.get("vessel_types") or []
    if allowed and vessel["vessel_type"] not in allowed:
        raise WriteRejected(f"profile {profile_id} is not allowed for a {vessel['vessel_type']} (allowed: {allowed})")
    size = "1" if batch_size in (None, "") else str(batch_size).rstrip("0").rstrip(".") if "." in str(batch_size) else str(batch_size)
    if size not in {"1", "0.5"}:
        raise WriteRejected(f"batch_size must be 1 or 0.5 (gallons), got {batch_size}")
    if target_f is not None:
        low, high = profile["temperature"]["allowed_target_f"]
        if not (low <= float(target_f) <= high):
            raise WriteRejected(f"target_f {target_f:g}°F is outside {profile_id}'s allowed range {low:g}–{high:g}°F")
    if not name or not name.strip():
        raise WriteRejected("name is required")
    stage_ids = [st["id"] for st in profile.get("stages", [])]
    if stage is not None and stage not in stage_ids:
        raise WriteRejected(f"unknown stage {stage!r} for {profile_id}; stages are {stage_ids}")
    if stage == "prep" and target_f is not None:
        raise WriteRejected("a batch in Prep has no temperature control; set target_f after advancing out of Prep")
    from fermentd.control.tweaks import check_copy_source

    copy = {"variant_id": variant_id, "copy_tweaks_from_batch_id": copy_tweaks_from_batch_id}
    problem = check_copy_source(ro, profile_id, copy)
    if problem:
        raise WriteRejected(problem)
    result = writer.submit(
        "start_batch",
        {"vessel_id": vessel_id, "profile_id": profile_id, "name": name.strip()[:80], "batch_size_gal": size,
         **({"stage": stage} if stage else {}),
         **{k: v for k, v in copy.items() if v is not None}},
    )
    batch_id = result["batch_id"]
    warning = None
    if target_f is not None:
        try:
            writer.submit("set_target_temp", {"vessel_id": vessel_id, "target_f": float(target_f)})
        except WriteRejected as exc:
            warning = f"batch started, but the target was not changed: {exc}"
    out = q.get_batch(writer.conn, batch_id)
    if warning:
        out["warning"] = warning
    return out


def end_batch(ro: sqlite3.Connection, writer: Writer, batch_id: int) -> dict:
    batch = q._batch_row(ro, batch_id)
    if batch["ended_at"] is not None:
        raise WriteRejected(f"batch {batch_id} '{batch['name']}' already ended")
    writer.submit("end_batch", {"batch_id": batch_id, "vessel_id": batch["vessel_id"]})
    return q.get_batch(writer.conn, batch_id)


def advance_stage(ro: sqlite3.Connection, writer: Writer, batch_id: int, to_stage: str | None = None) -> dict:
    batch = q._batch_row(ro, batch_id)
    if batch["ended_at"] is not None:
        raise WriteRejected(f"batch {batch_id} '{batch['name']}' has ended")
    ids = [s["id"] for s in q._profile(batch).get("stages", [])]
    cur = batch["stage"]
    if to_stage is None:
        if cur not in ids or ids.index(cur) + 1 >= len(ids):
            raise WriteRejected(f"batch {batch_id} is at its last stage ({cur}); end it with end_batch")
        to_stage = ids[ids.index(cur) + 1]
    if to_stage not in ids:
        raise WriteRejected(f"stage {to_stage!r} is not in this batch's schedule {ids}")
    if to_stage == cur:
        raise WriteRejected(f"batch {batch_id} is already at {cur}")
    writer.submit("set_stage", {"batch_id": batch_id, "vessel_id": batch["vessel_id"], "stage": to_stage})
    return q.get_batch(writer.conn, batch_id)


def complete_reminder(ro: sqlite3.Connection, writer: Writer, reminder_id: int | None = None,
                      batch_id: int | None = None, reminder: str | None = None) -> dict:
    if reminder_id is None:
        if batch_id is None or not reminder:
            raise WriteRejected("give reminder_id, or batch_id and reminder (its key or id)")
        rows = ro.execute(
            "SELECT * FROM REMINDER WHERE batch_id = ? AND status IN ('pending', 'open') ORDER BY due_at", (batch_id,)
        ).fetchall()
        match = [r for r in rows if r["reminder_key"] == reminder or str(r["id"]) == str(reminder)]
        if not match:
            raise WriteRejected(f"no pending reminder {reminder!r} on batch {batch_id}; pending: "
                                f"{[r['reminder_key'] for r in rows]}")
        reminder_id = match[0]["id"]
    row = ro.execute("SELECT * FROM REMINDER WHERE id = ?", (reminder_id,)).fetchone()
    if row is None:
        raise WriteRejected(f"unknown reminder_id {reminder_id}")
    if batch_id is not None and row["batch_id"] != batch_id:
        raise WriteRejected(f"reminder {reminder_id} belongs to batch {row['batch_id']}, not {batch_id}")
    if row["status"] not in ("pending", "open"):
        raise WriteRejected(f"reminder {reminder_id} is already {row['status']}")
    writer.submit("complete_reminder", {"reminder_id": reminder_id, "batch_id": row["batch_id"]})
    done = writer.conn.execute("SELECT * FROM REMINDER WHERE id = ?", (reminder_id,)).fetchone()
    return {"reminder_id": reminder_id, "batch_id": done["batch_id"], "key": done["reminder_key"],
            "status": done["status"], "text": done["text"]}


def hydrometer_correction(sg: float, temp_f: float, calibration_f: float = 60.0) -> float:
    """Standard hydrometer temperature correction (polynomial for water density), 60 °F calibration."""
    def rho(t: float) -> float:
        return 1.00130346 - 0.000134722124 * t + 0.00000204052596 * t**2 - 0.00000000232820948 * t**3

    return sg * rho(temp_f) / rho(calibration_f)


def log_gravity(ro: sqlite3.Connection, writer: Writer, batch_id: int, sg: float,
                temp_f: float | None = None, note: str | None = None) -> dict:
    batch = q._batch_row(ro, batch_id)
    if batch["ended_at"] is not None:
        raise WriteRejected(f"batch {batch_id} '{batch['name']}' has ended")
    sg = float(sg)
    if not (0.980 <= sg <= 1.200):
        raise WriteRejected(f"{sg} is not a hydrometer reading (0.980-1.200)")
    corrected = sg
    if temp_f is not None:
        if not (32 <= float(temp_f) <= 140):
            raise WriteRejected(f"sample temperature {temp_f} °F is out of range (32-140)")
        corrected = round(hydrometer_correction(sg, float(temp_f)), 4)
    writer.submit(
        "add_gravity",
        {"batch_id": batch_id, "vessel_id": batch["vessel_id"], "sg": f"{corrected:.4f}",
         "sample_temp_f": None if temp_f is None else float(temp_f)},
    )
    if note and note.strip():
        clock = writer.clock or _Clock(writer.conn)
        from fermentd.timefmt import isoformat

        ts = isoformat(clock.now())
        writer.conn.execute("INSERT INTO NOTE (batch_id, ts, actor, text) VALUES (?, ?, ?, ?)",
                            (batch_id, ts, ACTOR, f"Gravity {sg:.3f}: {note.strip()[:500]}"))
        writer.conn.execute(
            "INSERT INTO AUDIT_LOG (ts, actor, action, target, old_value, new_value) VALUES (?, ?, 'add_note', ?, NULL, ?)",
            (ts, ACTOR, f"batch:{batch_id}", note.strip()[:500]),
        )
        writer.conn.commit()
    out = q.get_batch_gravity(writer.conn, batch_id)
    out["logged"] = {"raw_sg": sg, "sample_temp_f": temp_f, "corrected_sg": corrected,
                     "correction": "60 °F hydrometer calibration" if temp_f is not None else "none (no temperature)"}
    return out


def list_profiles(ro: sqlite3.Connection, include_legacy: bool = False) -> dict:
    types = [r["vessel_type"] for r in ro.execute("SELECT DISTINCT vessel_type FROM VESSEL ORDER BY 1")]
    all_types = sorted(set(types) | {"jug", "carboy", "bucket", "jar", "bottle_group"})
    rows = ro.execute(
        """
        SELECT p.* FROM BEVERAGE_PROFILE p
        JOIN (SELECT id, MAX(version) AS v FROM BEVERAGE_PROFILE GROUP BY id) m ON m.id = p.id AND m.v = p.version
        ORDER BY p.id
        """
    ).fetchall()
    vessels = ro.execute("SELECT id, vessel_type FROM VESSEL WHERE enabled = 1 ORDER BY id").fetchall()
    from fermentd.mcp.guide import current_profile_ids

    current = current_profile_ids()
    out = []
    hidden = 0
    for row in rows:
        d = json.loads(row["definition_json"])
        legacy = not d.get("category") or (row["source"] == "builtin" and current and row["id"] not in current)
        if legacy and not include_legacy:
            hidden += 1
            continue
        allowed = d.get("vessel_types") or []
        temp = d.get("temperature", {})
        out.append(
            {
                "profile_id": row["id"],
                "name": d.get("name"),
                "drink_type": d.get("category"),
                "status": row["status"],
                "default_target_f": temp.get("default_target_f"),
                "allowed_target_f": temp.get("allowed_target_f"),
                "recommended_f": temp.get("recommended_f"),
                "batch_sizes_gal": [1, 0.5],
                "vessel_types": {t: (not allowed or t in allowed) for t in all_types},
                "allowed_for_vessels": [v["id"] for v in vessels if not allowed or v["vessel_type"] in allowed],
                **({"legacy": True} if legacy else {}),
            }
        )
    return {"profiles": out, "hidden_legacy": hidden}
