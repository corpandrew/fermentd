"""Planned-restart marker. `fermentd-ctl planned-restart` writes it just before restarting the
services so a deploy does not page Andrew. It lives in SETTING with an expiry (default 5 min).
A crash, power loss or OOM kill writes no marker, so those still raise service_interrupted."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from fermentd.timefmt import isoformat, parse_iso

KEY = "planned_restart_until"
DEFAULT_MINUTES = 5


def write_marker(conn: sqlite3.Connection, now: datetime, minutes: float = DEFAULT_MINUTES, actor: str = "cli") -> str:
    until = isoformat(now + timedelta(minutes=minutes))
    conn.execute(
        "INSERT INTO SETTING (key, value, updated_at, updated_by) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at, "
        "updated_by = excluded.updated_by",
        (KEY, until, isoformat(now), actor),
    )
    conn.commit()
    return until


def marker_fresh(conn: sqlite3.Connection, now: datetime) -> bool:
    row = conn.execute("SELECT value FROM SETTING WHERE key = ?", (KEY,)).fetchone()
    if row is None:
        return False
    try:
        return now <= parse_iso(row["value"])
    except ValueError:
        return False


def take_marker(conn: sqlite3.Connection, now: datetime) -> bool:
    """True if a fresh marker was present. Always clears it (fresh or expired)."""
    fresh = marker_fresh(conn, now)
    conn.execute("DELETE FROM SETTING WHERE key = ?", (KEY,))
    return fresh
