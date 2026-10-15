"""Hardware dead-man: the heat plug's own countdown timer (Tuya DP 11).

While heating, the controller re-arms the countdown every control cycle (10 s) to COUNTDOWN_ARM_S.
If the Pi, the controller or Wi-Fi dies with the mat on, the plug switches itself off within
COUNTDOWN_ARM_S. The controller records the last acknowledged arm in SETTING so the dashboard and
MCP (separate processes) can show 'Safety cutoff: armed (X min)'.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from fermentd.timefmt import isoformat, parse_iso

COUNTDOWN_ARM_S = 10 * 60
# Heating with no acknowledged arm for this long raises countdown_not_armed (warning + push).
UNARMED_GRACE_S = 60
PERSIST_EVERY_S = 60


def key(zone_id: str) -> str:
    return f"cutoff:{zone_id}"


def save(conn: sqlite3.Connection, zone_id: str, now: datetime, payload: dict) -> None:
    conn.execute(
        "INSERT INTO SETTING (key, value, updated_at, updated_by) VALUES (?, ?, ?, 'control') "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key(zone_id), json.dumps(payload), isoformat(now)),
    )


def status(conn: sqlite3.Connection, zone_id: str | None, now: datetime) -> dict:
    """Plain-English cutoff state for the dashboard and get_vessel_heater. The controller writes the
    SETTING row only for plugs with a countdown DP, so no row means 'not set up'."""
    row = None if zone_id is None else conn.execute(
        "SELECT value FROM SETTING WHERE key = ?", (key(zone_id),)).fetchone()
    if row is None:
        return {"state": "not_configured", "minutes_left": None,
                "text": "Safety cutoff: not set up for this plug"}
    data = json.loads(row["value"])
    if not data.get("on"):
        return {"state": "idle", "minutes_left": None,
                "text": "Safety cutoff: standing by (heat mat is off)"}
    armed_at = data.get("armed_at")
    seconds = data.get("seconds") or COUNTDOWN_ARM_S
    if armed_at and data.get("on"):
        left = seconds - (now - parse_iso(armed_at)).total_seconds()
        if left > 0 and not data.get("unarmed"):
            minutes = max(1, round(left / 60))
            return {"state": "armed", "minutes_left": minutes, "last_armed": armed_at,
                    "text": f"Safety cutoff: armed ({minutes} min)"}
    return {"state": "not_armed", "minutes_left": None, "last_armed": armed_at,
            "text": "Safety cutoff: NOT armed. The plug will not switch itself off if the Pi stops."}
