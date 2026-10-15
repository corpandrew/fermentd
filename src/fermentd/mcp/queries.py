"""Read-only queries behind the MCP tools. Each takes a read-only sqlite connection and returns plain
JSON-able data. Every timestamp is given as ISO UTC (`*_utc`) plus America/New_York (`*_local`)."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fermentd.control import cutoff
from fermentd.timefmt import isoformat as _iso

LOCAL = ZoneInfo("America/New_York")


class NotFound(ValueError):
    pass


def connect_ro(path: Path | str) -> sqlite3.Connection:
    """Open the database read-only (sqlite URI mode=ro). Writes raise sqlite3.OperationalError."""
    uri = f"file:{Path(path).resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def when(ts: str | None) -> dict | None:
    if not ts:
        return None
    dt = parse_iso(ts).astimezone(UTC)
    return {
        "utc": dt.isoformat().replace("+00:00", "Z"),
        "local": dt.astimezone(LOCAL).isoformat(),
        "zone": "America/New_York",
    }


def _now(conn: sqlite3.Connection, now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _r1(value: float | None) -> float | None:
    return None if value is None else round(float(value), 2)


def _vessel(conn: sqlite3.Connection, vessel_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM VESSEL WHERE id = ?", (vessel_id,)).fetchone()
    if row is None:
        ids = [r["id"] for r in conn.execute("SELECT id FROM VESSEL ORDER BY id")]
        raise NotFound(f"unknown vessel_id {vessel_id!r}; known: {ids}")
    return row


def _batch_row(conn: sqlite3.Connection, batch_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM BATCH WHERE id = ?", (batch_id,)).fetchone()
    if row is None:
        raise NotFound(f"unknown batch_id {batch_id}")
    return row


def _active_batch(conn: sqlite3.Connection, vessel_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM BATCH WHERE vessel_id = ? AND ended_at IS NULL ORDER BY id DESC LIMIT 1", (vessel_id,)
    ).fetchone()


def _zone(conn: sqlite3.Connection, vessel: sqlite3.Row) -> sqlite3.Row | None:
    if not vessel["temp_zone_id"]:
        return None
    return conn.execute("SELECT * FROM TEMP_ZONE WHERE id = ?", (vessel["temp_zone_id"],)).fetchone()


def _latest_reading(conn: sqlite3.Connection, vessel_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM READING WHERE vessel_id = ? ORDER BY ts DESC LIMIT 1", (vessel_id,)
    ).fetchone()


def _alert_scopes(conn: sqlite3.Connection, vessel: sqlite3.Row) -> list[str]:
    scopes = [f"zone:{vessel['id']}"]
    if vessel["temp_zone_id"]:
        scopes.append(f"zone:{vessel['temp_zone_id']}")
    for b in conn.execute("SELECT id FROM BATCH WHERE vessel_id = ?", (vessel["id"],)):
        scopes.append(f"batch:{b['id']}")
    return scopes


def _alert_rows(conn: sqlite3.Connection, status: str) -> list[sqlite3.Row]:
    clause = {"open": "ALERT.status != 'resolved'", "resolved": "ALERT.status = 'resolved'", "all": "1=1"}
    if status not in clause:
        raise ValueError("status must be 'open', 'resolved' or 'all'")
    return conn.execute(
        f"""
        SELECT ALERT.*, EVENT.type AS event_type, EVENT.detail_json, EVENT.vessel_id AS event_vessel,
               EVENT.batch_id AS event_batch
        FROM ALERT LEFT JOIN EVENT ON EVENT.id = ALERT.event_id
        WHERE {clause[status]} ORDER BY ALERT.opened_at DESC, ALERT.id DESC
        """
    ).fetchall()


def _alert_matches(row: sqlite3.Row, vessel: sqlite3.Row, scopes: list[str]) -> bool:
    if row["event_vessel"] == vessel["id"]:
        return True
    return any(row["dedupe_key"].endswith(":" + scope) for scope in scopes)


def _profile(batch: sqlite3.Row) -> dict:
    try:
        return json.loads(batch["profile_snapshot_json"] or "{}")
    except ValueError:
        return {}


def _day_count(batch: sqlite3.Row, now: datetime) -> int:
    end = parse_iso(batch["ended_at"]) if batch["ended_at"] else now
    return int((end - parse_iso(batch["started_at"])).total_seconds() // 86400) + 1


def _batch_brief(batch: sqlite3.Row, now: datetime) -> dict:
    profile = _profile(batch)
    return {
        "batch_id": batch["id"],
        "name": batch["name"],
        "vessel_id": batch["vessel_id"],
        "profile_id": batch["profile_id"],
        "profile_name": profile.get("name"),
        "stage": batch["stage"],
        "status": "active" if batch["ended_at"] is None else "ended",
        "day": _day_count(batch, now),
        "started": when(batch["started_at"]),
        "ended": when(batch["ended_at"]),
    }


# ---------------------------------------------------------------- tools


def list_vessels(conn: sqlite3.Connection, now: datetime | None = None) -> dict:
    now = _now(conn, now)
    out = []
    open_alerts = _alert_rows(conn, "open")
    for vessel in conn.execute("SELECT * FROM VESSEL WHERE enabled = 1 ORDER BY id").fetchall():
        zone = _zone(conn, vessel)
        reading = _latest_reading(conn, vessel["id"])
        batch = _active_batch(conn, vessel["id"])
        scopes = _alert_scopes(conn, vessel)
        out.append(
            {
                "vessel_id": vessel["id"],
                "name": vessel["name"],
                "type": vessel["vessel_type"],
                "current_batch": None
                if batch is None
                else {"batch_id": batch["id"], "name": batch["name"], "stage": batch["stage"]},
                "temp_f": None if reading is None else _r1(reading["vessel_temp_f"]),
                "reading_time": None if reading is None else when(reading["ts"]),
                "target_f": None if zone is None or batch is None else zone["target_f"],
                "heater_on": None if reading is None else bool(reading["heater_on"]),
                "open_alerts": sum(1 for row in open_alerts if _alert_matches(row, vessel, scopes)),
            }
        )
    return {"vessels": out, "as_of": when(now.isoformat())}


def get_vessel_temperature(conn: sqlite3.Connection, vessel_id: str, now: datetime | None = None) -> dict:
    now = _now(conn, now)
    vessel = _vessel(conn, vessel_id)
    zone = _zone(conn, vessel)
    batch = _active_batch(conn, vessel_id)
    reading = _latest_reading(conn, vessel_id)
    temp = None if reading is None else reading["vessel_temp_f"]
    target = None if zone is None or batch is None else zone["target_f"]
    age = None if reading is None else round((now - parse_iso(reading["ts"])).total_seconds())
    return {
        "vessel_id": vessel_id,
        "temp_f": _r1(temp),
        "ambient_f": None if reading is None else _r1(reading["ambient_temp_f"]),
        "target_f": target,
        "hysteresis_f": None if zone is None else zone["hysteresis_f"],
        "delta_f": None if temp is None or target is None else _r1(temp - target),
        "reading_time": None if reading is None else when(reading["ts"]),
        "reading_age_s": age,
        "stale": age is None or age > 300,
        "note": None if batch is not None else "No active batch: the vessel is idle and not holding a target.",
    }


def get_vessel_temperature_history(
    conn: sqlite3.Connection,
    vessel_id: str,
    hours: float | None = 24,
    start: str | None = None,
    end: str | None = None,
    bucket_minutes: int | None = None,
    now: datetime | None = None,
) -> dict:
    now = _now(conn, now)
    _vessel(conn, vessel_id)
    end_dt = parse_iso(end) if end else now
    start_dt = parse_iso(start) if start else end_dt - timedelta(hours=float(hours or 24))
    if end_dt <= start_dt:
        raise ValueError("end must be after start")
    if end_dt - start_dt > timedelta(days=60):
        raise ValueError("range is limited to 60 days")
    span_min = (end_dt - start_dt).total_seconds() / 60
    bucket = int(bucket_minutes or max(5, round(span_min / 96)))
    bucket = max(1, min(bucket, 24 * 60))
    if span_min / bucket > 2000:
        raise ValueError("too many buckets; use a larger bucket_minutes")
    rows = conn.execute(
        "SELECT ts, vessel_temp_f, ambient_temp_f, heater_on FROM READING "
        "WHERE vessel_id = ? AND ts >= ? AND ts <= ? ORDER BY ts",
        (vessel_id, _iso(start_dt), _iso(end_dt)),
    ).fetchall()
    buckets: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        idx = int((parse_iso(row["ts"]) - start_dt).total_seconds() // (bucket * 60))
        buckets.setdefault(idx, []).append(row)
    out = []
    for idx in sorted(buckets):
        group = buckets[idx]
        temps = [r["vessel_temp_f"] for r in group if r["vessel_temp_f"] is not None]
        amb = [r["ambient_temp_f"] for r in group if r["ambient_temp_f"] is not None]
        out.append(
            {
                "start": when(_iso(start_dt + timedelta(minutes=idx * bucket))),
                "samples": len(group),
                "min_f": _r1(min(temps)) if temps else None,
                "max_f": _r1(max(temps)) if temps else None,
                "avg_f": _r1(sum(temps) / len(temps)) if temps else None,
                "ambient_avg_f": _r1(sum(amb) / len(amb)) if amb else None,
                "heater_on_pct": round(100 * sum(r["heater_on"] for r in group) / len(group)),
            }
        )
    return {
        "vessel_id": vessel_id,
        "start": when(_iso(start_dt)),
        "end": when(_iso(end_dt)),
        "bucket_minutes": bucket,
        "buckets": out,
    }


def get_vessel_heater(conn: sqlite3.Connection, vessel_id: str, now: datetime | None = None) -> dict:
    now = _now(conn, now)
    vessel = _vessel(conn, vessel_id)
    batch = _active_batch(conn, vessel_id)
    reading = _latest_reading(conn, vessel_id)
    if reading is None:
        return {"vessel_id": vessel_id, "heater_on": None, "note": "No readings yet."}
    state = reading["heater_on"]
    change = conn.execute(
        "SELECT MAX(ts) AS ts FROM READING WHERE vessel_id = ? AND heater_on != ?", (vessel_id, state)
    ).fetchone()["ts"]
    since = None
    if change is not None:
        since = conn.execute(
            "SELECT MIN(ts) AS ts FROM READING WHERE vessel_id = ? AND ts > ?", (vessel_id, change)
        ).fetchone()["ts"]

    def duty(where: str, args: tuple) -> dict:
        row = conn.execute(
            f"SELECT AVG(heater_on) AS d, COUNT(*) AS n, MIN(ts) AS t0, MAX(ts) AS t1 FROM READING WHERE {where}", args
        ).fetchone()
        if not row["n"]:
            return {"pct": None, "start": None, "hours": 0.0}
        hours = (parse_iso(row["t1"]) - parse_iso(row["t0"])).total_seconds() / 3600
        return {"pct": round(row["d"] * 100, 1), "start": when(row["t0"]), "hours": round(hours, 2)}

    latest_dt = parse_iso(reading["ts"])
    window_start = latest_dt - timedelta(hours=24)
    if batch is not None:
        window_start = max(window_start, parse_iso(batch["started_at"]))
    day = (
        duty("vessel_id = ? AND batch_id = ? AND ts >= ?", (vessel_id, batch["id"], _iso(window_start)))
        if batch is not None
        else duty("vessel_id = ? AND ts >= ?", (vessel_id, _iso(window_start)))
    )
    whole = None if batch is None else duty("batch_id = ?", (batch["id"],))

    zone = _zone(conn, vessel)
    return {
        "vessel_id": vessel_id,
        "zone_id": vessel["temp_zone_id"],
        "heater_driver": None if zone is None else zone["actuator_driver"],
        "heater_on": bool(state),
        "state_since": when(since),
        "last_change": when(since),
        "as_of": when(reading["ts"]),
        "duty_pct_24h": day["pct"],
        "duty_window_start": day["start"],
        "duty_hours_covered": day["hours"],
        "duty_note": "Last 24 h, but never before the batch started; covers only time with readings.",
        "duty_pct_batch": None if whole is None else whole["pct"],
        "duty_batch_hours_covered": None if whole is None else whole["hours"],
        "safety_cutoff": cutoff.status(conn, vessel["temp_zone_id"], now),
    }


def get_vessel_weight(conn: sqlite3.Connection, vessel_id: str, now: datetime | None = None) -> dict:
    from fermentd.control.weight import weight_summary

    _vessel(conn, vessel_id)
    scale = conn.execute("SELECT * FROM SCALE WHERE vessel_id = ?", (vessel_id,)).fetchone()
    if scale is None:
        return {"vessel_id": vessel_id, "has_scale": False, "note": "No scale is configured for this vessel."}
    out = {
        "vessel_id": vessel_id,
        "has_scale": True,
        "scale_status": scale["status"],
        "status_time": when(scale["status_at"]),
        "calibrated": scale["counts_per_gram"] is not None and scale["tare_offset"] is not None,
    }
    batch = _active_batch(conn, vessel_id)
    if batch is None:
        out["note"] = "No active batch."
        return out
    summary = weight_summary(conn, batch["id"]) or {}
    last = summary["points"][-1][0] if summary.get("points") else None
    out.update(
        batch_id=batch["id"],
        weight_g=_r1(summary.get("current_g")),
        start_weight_g=_r1(summary.get("start_g")),
        co2_lost_g=_r1(summary.get("co2_g")),
        rate_g_per_day=_r1(summary.get("rate_g_day")),
        peak_rate_g_per_day=_r1(summary.get("peak_g_day")),
        est_abv_pct=None if summary.get("abv") is None else round(summary["abv"], 2),
        volume_l=_r1(summary.get("volume_l")),
        state=summary.get("state"),
        summary=summary.get("text"),
        last_reading=when(last),
        samples=summary.get("count", 0),
    )
    return out


def get_vessel_status(conn: sqlite3.Connection, vessel_id: str, now: datetime | None = None) -> dict:
    now = _now(conn, now)
    vessel = _vessel(conn, vessel_id)
    batch = _active_batch(conn, vessel_id)
    scopes = _alert_scopes(conn, vessel)
    alerts = [_alert_item(r) for r in _alert_rows(conn, "open") if _alert_matches(r, vessel, scopes)]
    return {
        "vessel_id": vessel_id,
        "name": vessel["name"],
        "type": vessel["vessel_type"],
        "capacity_l": vessel["capacity_l"],
        "zone_id": vessel["temp_zone_id"],
        "batch": None if batch is None else _batch_brief(batch, now),
        "temperature": get_vessel_temperature(conn, vessel_id, now),
        "heater": get_vessel_heater(conn, vessel_id, now),
        "has_scale": conn.execute("SELECT 1 FROM SCALE WHERE vessel_id = ?", (vessel_id,)).fetchone() is not None,
        "open_alerts": alerts,
    }


def list_batches(conn: sqlite3.Connection, status: str = "active", now: datetime | None = None) -> dict:
    now = _now(conn, now)
    where = {"active": "ended_at IS NULL", "ended": "ended_at IS NOT NULL", "all": "1=1"}
    if status not in where:
        raise ValueError("status must be 'active', 'ended' or 'all'")
    rows = conn.execute(f"SELECT * FROM BATCH WHERE {where[status]} ORDER BY started_at DESC").fetchall()
    return {"status": status, "batches": [_batch_brief(r, now) for r in rows]}


def get_batch(conn: sqlite3.Connection, batch_id: int, now: datetime | None = None) -> dict:
    now = _now(conn, now)
    batch = _batch_row(conn, batch_id)
    profile = _profile(batch)
    vessel = conn.execute("SELECT * FROM VESSEL WHERE id = ?", (batch["vessel_id"],)).fetchone()
    zone = None if vessel is None else _zone(conn, vessel)
    stages = []
    for stage in profile.get("stages", []):
        stages.append(
            {
                "id": stage.get("id"),
                "core": stage.get("core"),
                "target_f": stage.get("target_f"),
                "step": None if not stage.get("ramp") else stage["ramp"],
                "current": stage.get("id") == batch["stage"],
            }
        )
    current = next((s for s in stages if s["current"]), None)
    step = None
    if current and current["step"] and batch["stage_started_at"]:
        from fermentd.profiles.schema import duration_seconds  # noqa: PLC0415

        due = parse_iso(batch["stage_started_at"]) + timedelta(seconds=duration_seconds(current["step"]["after"]))
        step = {"target_f": current["step"]["target_f"], "due": when(_iso(due)), "passed": now >= due}
    reminders = conn.execute(
        "SELECT * FROM REMINDER WHERE batch_id = ? AND status IN ('pending', 'open') ORDER BY due_at", (batch_id,)
    ).fetchall()
    temp = profile.get("temperature", {})
    return {
        **_batch_brief(batch, now),
        "yeast": batch["yeast"],
        "og": batch["og"],
        "volume_l": batch["volume_l"],
        "target_f": None if zone is None or batch["ended_at"] else zone["target_f"],
        "profile_temperature": {
            "default_target_f": temp.get("default_target_f"),
            "recommended_f": temp.get("recommended_f"),
            "allowed_target_f": temp.get("allowed_target_f"),
        },
        "stage_started": when(batch["stage_started_at"]),
        "schedule": stages,
        "next_temp_step": step,
        "target_reached": when(_safe(batch, "target_reached_at")),
        "upcoming_reminders": [
            {"reminder_id": r["id"], "key": r["reminder_key"], "text": r["text"], "due": when(r["due_at"]), "status": r["status"]} for r in reminders
        ],
    }


def get_batch_gravity(conn: sqlite3.Connection, batch_id: int, now: datetime | None = None) -> dict:
    batch = _batch_row(conn, batch_id)
    rows = conn.execute(
        "SELECT ts, sg, sample_temp_f, source FROM GRAVITY_READING WHERE batch_id = ? ORDER BY ts, id", (batch_id,)
    ).fetchall()
    readings = [
        {"time": when(r["ts"]), "sg": r["sg"], "sample_temp_f": r["sample_temp_f"], "source": r["source"]}
        for r in rows
    ]
    out = {"batch_id": batch_id, "readings": readings, "og": batch["og"], "est_abv_pct": None, "attenuation_pct": None}
    if rows:
        og = batch["og"] or rows[0]["sg"]
        out["og"] = og
        latest = rows[-1]["sg"]
        out["latest_sg"] = latest
        if og > 1.0 and len(rows) > 1 or (batch["og"] and og != latest):
            out["est_abv_pct"] = round(max(0.0, (og - latest) * 131.25), 2)
            out["attenuation_pct"] = round(max(0.0, (og - latest) / (og - 1.0) * 100), 1)
    out["formula"] = "ABV = (OG - SG) x 131.25"
    return out


def list_alerts(conn: sqlite3.Connection, status: str = "open", limit: int = 50) -> dict:
    rows = _alert_rows(conn, status)[: max(1, min(int(limit), 500))]
    return {"status": status, "alerts": [_alert_item(r) for r in rows]}


def _alert_item(row: sqlite3.Row) -> dict:
    from fermentd.web.status import alert_sentence

    detail = json.loads(row["detail_json"]) if row["detail_json"] else {}
    kind, _, scope = row["dedupe_key"].partition(":")
    return {
        "alert_id": row["id"],
        "type": row["event_type"] or kind,
        "scope": scope,
        "severity": row["severity"],
        "status": row["status"],
        "text": alert_sentence(row["event_type"] or kind, detail),
        "opened": when(row["opened_at"]),
        "acked": when(row["acked_at"]),
        "resolved": when(row["resolved_at"]),
    }


def _safe(row: sqlite3.Row, key: str):
    return row[key] if key in row.keys() else None


def parse_iso(text: str) -> datetime:
    """Accepts the database format and any ISO 8601 string; naive times are taken as New York time."""
    dt = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LOCAL)
    return dt.astimezone(UTC)
