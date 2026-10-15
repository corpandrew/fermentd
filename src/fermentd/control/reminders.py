"""Schedule profile reminders and raise them when they come due."""

from __future__ import annotations

import sqlite3
from datetime import timedelta

from fermentd.clock import Clock
from fermentd.control.alerts import raise_alert, resolve_alert
from fermentd.profiles.schema import Profile, anchor_offset_seconds, duration_seconds
from fermentd.timefmt import isoformat, parse_iso

Notice = tuple[str, str, str, str]


def schedule_for_stage(
    conn: sqlite3.Connection,
    *,
    batch_id: int,
    profile: Profile,
    stage: str,
    stage_started_at: str,
    actor: str,
) -> None:
    started = parse_iso(stage_started_at)
    prefix = f"stage:{stage}+"
    for reminder in profile.reminders:
        if not reminder.at.startswith(prefix):
            continue
        due = isoformat(started + timedelta(seconds=anchor_offset_seconds(reminder.at)))
        repeat = duration_seconds(reminder.repeat) if reminder.repeat else None
        existing = conn.execute(
            "SELECT id FROM REMINDER WHERE batch_id = ? AND reminder_key = ?",
            (batch_id, reminder.id),
        ).fetchone()
        if existing is not None:
            continue
        conn.execute(
            """
            INSERT INTO REMINDER (
                batch_id, reminder_key, due_at, text, status, created_by, repeat_seconds
            ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (batch_id, reminder.id, due, reminder.text, actor, repeat),
        )


def evaluate_reminders(conn: sqlite3.Connection, clock: Clock) -> list[Notice]:
    now = clock.now()
    now_iso = isoformat(now)
    notices: list[Notice] = []
    rows = conn.execute(
        """
        SELECT REMINDER.*, BATCH.vessel_id, BATCH.name AS batch_name
        FROM REMINDER JOIN BATCH ON BATCH.id = REMINDER.batch_id
        WHERE REMINDER.status IN ('pending', 'open') AND REMINDER.due_at <= ?
        """,
        (now_iso,),
    ).fetchall()
    for row in rows:
        severity = "action"
        overdue_at = parse_iso(row["due_at"])
        if row["reminder_key"] == "refrigerate_now" and now >= overdue_at + timedelta(hours=12):
            severity = "critical"
        elif now >= overdue_at + timedelta(days=2):
            severity = "critical"
        kind = "refrigerate_now" if row["reminder_key"] == "refrigerate_now" else "reminder_due"
        outcome = raise_alert(
            conn,
            clock,
            dedupe_key=f"{row['reminder_key']}:batch:{row['batch_id']}",
            severity=severity,
            alert_type=kind,
            detail={"text": row["text"], "batch": row["batch_name"]},
            vessel_id=row["vessel_id"],
            batch_id=row["batch_id"],
        )
        repeat_ready = False
        if row["repeat_seconds"] and row["last_notified_at"]:
            elapsed = (now - parse_iso(row["last_notified_at"])).total_seconds()
            repeat_ready = elapsed >= row["repeat_seconds"]
        should_notify = row["last_notified_at"] is None or outcome == "escalated" or repeat_ready
        if should_notify:
            notices.append((kind, severity, row["batch_name"], row["text"]))
            conn.execute(
                "UPDATE REMINDER SET status = 'open', last_notified_at = ? WHERE id = ?",
                (now_iso, row["id"]),
            )
        else:
            conn.execute("UPDATE REMINDER SET status = 'open' WHERE id = ?", (row["id"],))
    return notices


def complete_reminder(conn: sqlite3.Connection, clock: Clock, reminder_id: int) -> str | None:
    row = conn.execute("SELECT * FROM REMINDER WHERE id = ?", (reminder_id,)).fetchone()
    if row is None:
        return "NOT_FOUND"
    conn.execute("UPDATE REMINDER SET status = 'completed' WHERE id = ?", (reminder_id,))
    resolve_alert(conn, clock, f"{row['reminder_key']}:batch:{row['batch_id']}")
    return None


def close_reminder_keys(
    conn: sqlite3.Connection,
    clock: Clock,
    batch_id: int,
    keys: list[str],
) -> None:
    if not keys:
        return
    marks = ",".join("?" for _ in keys)
    conn.execute(
        f"""
        UPDATE REMINDER SET status = 'completed'
        WHERE batch_id = ? AND reminder_key IN ({marks}) AND status != 'completed'
        """,
        (batch_id, *keys),
    )
    for key in keys:
        resolve_alert(conn, clock, f"{key}:batch:{batch_id}")
