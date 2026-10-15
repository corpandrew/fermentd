"""Weekly digest. Sunday 09:00 America/New_York by default, deduped by ISO week."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fermentd.timefmt import isoformat, parse_iso
from fermentd.web.status import alert_sentence

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def digest_slot(now: datetime, timezone_name: str, weekday: str, hhmm: str) -> tuple[str, datetime, bool]:
    zone = ZoneInfo(timezone_name)
    local_now = now.astimezone(zone)
    hour, minute = (int(part) for part in hhmm.split(":"))
    target = WEEKDAYS.index(weekday.lower())
    days_back = (local_now.weekday() - target) % 7
    slot = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0) - timedelta(days=days_back)
    if slot > local_now:
        slot -= timedelta(days=7)
    digest_id = slot.strftime("%G-W%V")
    late = local_now.date() != slot.date()
    return digest_id, slot, late


def build_digest(
    conn: sqlite3.Connection,
    *,
    period_end: datetime,
    digest_id: str,
    late: bool,
    as_of: datetime | None = None,
) -> dict:
    period_start = period_end - timedelta(days=7)
    start_iso = isoformat(period_start)
    end_iso = isoformat(period_end)
    batches = []
    active = conn.execute(
        """
        SELECT BATCH.*, VESSEL.name AS vessel_name, VESSEL.id AS vessel
        FROM BATCH JOIN VESSEL ON VESSEL.id = BATCH.vessel_id
        WHERE BATCH.ended_at IS NULL OR BATCH.ended_at >= ?
        """,
        (start_iso,),
    ).fetchall()
    for batch in active:
        if batch["ended_at"] is not None and batch["ended_at"] < start_iso:
            continue
        temps = conn.execute(
            """
            SELECT AVG(vessel_temp_f) AS mean_f, MIN(vessel_temp_f) AS min_f,
                   MAX(vessel_temp_f) AS max_f, COUNT(vessel_temp_f) AS n
            FROM READING
            WHERE vessel_id = ? AND ts >= ? AND ts <= ? AND vessel_temp_f IS NOT NULL AND (flags & 32) = 0
            """,
            (batch["vessel_id"], start_iso, end_iso),
        ).fetchone()
        mark = as_of if as_of is not None else period_end
        if batch["ended_at"]:
            ended = parse_iso(batch["ended_at"])
            if ended < mark:
                mark = ended
        stage_row = conn.execute(
            """
            SELECT ts FROM AUDIT_LOG
            WHERE action = 'set_stage' AND target = ? AND ts <= ?
            ORDER BY id DESC LIMIT 1
            """,
            (f"batch:{batch['id']}", isoformat(mark)),
        ).fetchone()
        stage_started = parse_iso(stage_row["ts"] if stage_row else batch["started_at"])
        if stage_started > mark:
            elapsed_hours = 0.0
        else:
            elapsed_hours = (mark - stage_started).total_seconds() / 3600
        next_row = conn.execute(
            """
            SELECT due_at, text FROM REMINDER
            WHERE batch_id = ? AND status IN ('pending', 'open')
            ORDER BY due_at LIMIT 1
            """,
            (batch["id"],),
        ).fetchone()
        entry = {
            "name": batch["name"],
            "profile_id": batch["profile_id"],
            "vessel": batch["vessel_name"],
            "stage": batch["stage"],
            "tracking_mode": batch["tracking_mode"],
            "elapsed_hours_in_stage": round(elapsed_hours, 1),
            "temp_mean_f": temps["mean_f"],
            "temp_min_f": temps["min_f"],
            "temp_max_f": temps["max_f"],
            "next_action": None if next_row is None else {"due_at": next_row["due_at"], "text": next_row["text"]},
        }
        batches.append(entry)
    readings = conn.execute(
        "SELECT COUNT(*) AS n FROM READING WHERE ts >= ? AND ts <= ?",
        (start_iso, end_iso),
    ).fetchone()["n"]
    vessels = conn.execute("SELECT COUNT(*) AS n FROM VESSEL WHERE enabled = 1").fetchone()["n"]
    expected = max(vessels, 1) * 7 * 24 * 60
    safety = conn.execute(
        """
        SELECT type, COUNT(*) AS n FROM EVENT
        WHERE ts >= ? AND ts <= ? AND type IN ('overtemp_cutoff', 'sensor_fault', 'heater_unreachable')
        GROUP BY type
        """,
        (start_iso, end_iso),
    ).fetchall()
    open_alerts = conn.execute(
        """
        SELECT ALERT.dedupe_key, ALERT.severity, ALERT.status,
               EVENT.type AS event_type, EVENT.detail_json
        FROM ALERT
        LEFT JOIN EVENT ON EVENT.id = ALERT.event_id
        WHERE ALERT.status != 'resolved'
        ORDER BY ALERT.id
        """
    ).fetchall()
    upcoming = conn.execute(
        """
        SELECT due_at, text, batch_id FROM REMINDER
        WHERE status IN ('pending', 'open') AND due_at > ? AND due_at <= ?
        ORDER BY due_at
        """,
        (end_iso, isoformat(period_end + timedelta(days=7))),
    ).fetchall()
    return {
        "digest_id": digest_id,
        "late": late,
        "period_start": start_iso,
        "period_end": end_iso,
        "health": {
            "readings_received": readings,
            "readings_expected": expected,
            "completeness": round(readings / expected, 4) if expected else 1.0,
            "safety_events": {row["type"]: row["n"] for row in safety},
        },
        "batches": batches,
        "upcoming_reminders": [dict(row) for row in upcoming],
        "open_alerts": [_open_alert(row) for row in open_alerts],
    }


def _open_alert(row: sqlite3.Row) -> dict:
    detail = json.loads(row["detail_json"]) if row["detail_json"] else {}
    return {
        "dedupe_key": row["dedupe_key"],
        "severity": row["severity"],
        "status": row["status"],
        "text": alert_sentence(row["event_type"], detail),
    }


def record_digest(conn: sqlite3.Connection, summary: dict, sent_at: str, sent_by: str) -> None:
    conn.execute(
        """
        INSERT INTO DIGEST_LOG (digest_id, period_start, period_end, sent_at, sent_by, summary_json, late)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            summary["digest_id"],
            summary["period_start"],
            summary["period_end"],
            sent_at,
            sent_by,
            json.dumps(summary),
            1 if summary["late"] else 0,
        ),
    )


def sent_digest_ids(conn: sqlite3.Connection) -> set[str]:
    return {row["digest_id"] for row in conn.execute("SELECT digest_id FROM DIGEST_LOG")}
