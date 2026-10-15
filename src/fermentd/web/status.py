"""Read-only status for the dashboard. Writes go through the command table."""

from __future__ import annotations

import json
import sqlite3
from datetime import timedelta

from fermentd.timefmt import describe_due, format_local, isoformat, parse_iso

_STAGE = {
    "prep": "Making it",
    "keeve": "Keeving (waiting for the brown cap)",
    "slow_ferment": "Slow ferment",
    "cold_stabilize": "Cold stabilizing (fridge)",
    "tirage": "Tirage (bottled for the second ferment)",
    "en_tirage": "Aging en tirage",
    "riddling": "Riddling",
    "disgorge": "Disgorging and dosage",
    "dry_hop": "Dry hopping",
    "bottle": "Bottling",
    "in_bottle": "Carbonating in the bottles",
    "refrigerated": "In the fridge",
    "primary": "Primary fermentation",
    "secondary": "Clearing in secondary",
    "aging": "Aging",
    "bottle_condition": "Bottle conditioning",
    "cellared": "Cellared",
    "diacetyl_rest": "Diacetyl rest",
    "lagering": "Lagering cold",
    "must": "Fruit in primary",
    "f1": "First ferment",
}
_RAIL_LABEL = {
    "keeve": "Keeve",
    "slow_ferment": "Slow ferment",
    "cold_stabilize": "Cold stabilize",
    "tirage": "Tirage",
    "en_tirage": "En tirage",
    "riddling": "Riddling",
    "disgorge": "Disgorge",
    "dry_hop": "Dry hop",
    "bottle": "Bottled",
    "in_bottle": "Carbonating",
    "refrigerated": "In the fridge",
    "primary": "Primary",
    "secondary": "Secondary",
    "aging": "Aging",
    "bottle_condition": "Conditioning",
    "cellared": "Cellared",
    "diacetyl_rest": "D-rest",
    "lagering": "Lagering",
    "must": "On fruit",
    "f1": "First ferment",
}
_NEXT_ACTION = {
    "prep": "Back to making it",
    "slow_ferment": "Racked off the cap, start the slow ferment",
    "cold_stabilize": "Moved to the fridge to cold stabilize",
    "tirage": "Tirage bottled",
    "en_tirage": "Start aging en tirage",
    "riddling": "Start riddling",
    "disgorge": "Disgorged",
    "dry_hop": "Hops added",
    "refrigerated": "Move bottles to the fridge",
    "secondary": "Racked to secondary",
    "aging": "Start aging",
    "bottle": "Bottled",
    "bottle_condition": "Bottled, start conditioning",
    "cellared": "Conditioning done, move to cool storage",
    "diacetyl_rest": "Start diacetyl rest",
    "lagering": "Moved to cold lagering",
}
_VESSEL = {"bottle_group": "Bottles", "jug": "Jug", "carboy": "Carboy", "bucket": "Bucket", "jar": "Jar"}
_SEVERITY = {
    "info": "Note",
    "warning": "Warning",
    "action": "Needs attention",
    "critical": "Critical",
}
_RAIL = (
    ("bottle", "Bottled"),
    ("in_bottle", "Carbonating"),
    ("refrigerated", "In the fridge"),
)
_CARBONATION_HOURS = 48
_CHECK_HOURS = 24

_ALERT = {
    "fermentation_quiet": (
        "The weight has been stable for 48 hours. Fermentation has likely finished; take a hydrometer reading."
    ),
    "fermentation_slowing": "Fermentation is slowing down.",
    "config_conflict": "The temperature target is outside the range this batch allows.",
    "overtemp_cutoff": "A probe is above 80°F. The heat mat is held off.",
    "sensor_fault": "A temperature probe stopped reading. The heat mat is held off.",
    "max_on_rest": "The heat mat has been on for four hours, so it is resting.",
    "heater_unreachable": "The heat mat is not responding.",
    "heater_state_mismatch": "The heat mat did not switch the way the controller asked.",
    "pressure_risk": "The bottles are warm enough to build pressure. Move them to the fridge.",
    "temp_below_target": "The cooler has stayed well below its target. The heat mat may not be keeping up.",
    "control_fault": "The control loop hit an error and turned the heat mat off. It will keep trying.",
    "service_stopping": "The control service is stopping. The heat mat is being turned off.",
    "service_interrupted": (
        "fermentd stopped unexpectedly and has restarted. The heat mat was turned off. Check the cooler."
    ),
    "pi_offline": (
        "The Pi has not checked in. It may be off or off the network, and the heat mat may still be in its last state."
    ),
    "countdown_arm_failed": "The heat mat's safety timer could not be set. Check the plug.",
    "countdown_not_armed": (
        "The heat mat is on but its safety timer is not set, so the plug would not switch itself off "
        "if the Pi stopped. Check the plug."
    ),
    "temp_out_of_range": "The vessel has stayed outside the temperature range its profile allows.",
}


def format_temp(value: float | None) -> str | None:
    if value is None:
        return None
    if abs(value - round(value)) < 0.05:
        return f"{round(value):.0f}°F"
    return f"{value:.1f}°F"


def alert_sentence(event_type: str | None, detail: dict) -> str:
    text = detail.get("text")
    if isinstance(text, str) and text:
        return text
    if event_type == "pressure_risk" and detail.get("temp_f") is not None:
        return (
            f"The bottles are {float(detail['temp_f']):.0f}°F, warm enough to build pressure. Move them to the fridge."
        )
    if event_type == "temp_below_target" and detail.get("temp_f") is not None and detail.get("target_f") is not None:
        return (
            f"The cooler is {format_temp(float(detail['temp_f']))} and the target is "
            f"{format_temp(float(detail['target_f']))}. It has stayed well below the target, "
            "so the heat mat may not be keeping up."
        )
    if event_type == "temp_out_of_range" and detail.get("temp_f") is not None:
        temp = float(detail["temp_f"])
        low, high = float(detail.get("low_f", 0)), float(detail.get("high_f", 0))
        if temp > high:
            return (
                f"The vessel is {format_temp(temp)}, above the {format_temp(high)} this batch allows. "
                "The heat mat cannot cool; move the cooler somewhere colder."
            )
        return (
            f"The vessel is {format_temp(temp)}, below the {format_temp(low)} this batch allows. "
            "The heat mat may not be keeping up; insulate the cooler or move it somewhere warmer."
        )
    return _ALERT.get(event_type or "", "Something needs attention.")


def elapsed_label(started: str, now: str) -> str:
    seconds = int((parse_iso(now) - parse_iso(started)).total_seconds())
    if seconds < 0:
        seconds = 0
    minutes, _seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d {hours}h since start"
    if hours:
        return f"{hours}h {minutes}m since start"
    return f"{minutes}m since start"


def stage_steps(stage: str, stages: list[str] | None = None) -> list[dict]:
    if stages and stage in stages:
        index = stages.index(stage)
        return [
            {
                "label": _RAIL_LABEL.get(sid, sid.replace("_", " ").capitalize()),
                "state": "done" if i < index else "now" if i == index else "next",
            }
            for i, sid in enumerate(stages)
        ]
    order = [item[0] for item in _RAIL]
    if stage not in order:
        return [{"label": _STAGE.get(stage, stage.replace("_", " ")), "state": "now"}]
    index = order.index(stage)
    return [
        {"label": label, "state": "done" if i < index else "now" if i == index else "next"}
        for i, (_stage_id, label) in enumerate(_RAIL)
    ]


def carbonation_progress(stage: str, started: str, now: str) -> dict | None:
    if stage != "in_bottle":
        return None
    seconds = max(0.0, (parse_iso(now) - parse_iso(started)).total_seconds())
    progress = min(1.0, seconds / (_CARBONATION_HOURS * 3600))
    return {
        "progress_pct": round(progress * 100, 1),
        "tick_pct": round(_CHECK_HOURS / _CARBONATION_HOURS * 100, 1),
        "label": "24–48 hour carbonation window.",
    }


def temp_tone(temp: float | None, target: float | None, hysteresis: float | None) -> str:
    if temp is None:
        return "idle"
    if temp >= 80:
        return "critical"
    if target is None:
        return "hold"
    band = 1.0 if hysteresis is None else hysteresis
    if temp > target + 1:
        return "warm"
    if temp < target - band:
        return "heat"
    return "hold"


def temp_meter(temp: float | None, target: float | None, hysteresis: float | None) -> dict | None:
    if target is None:
        return None
    low = target - 8
    high = target + 8
    width = high - low

    def pct(value: float) -> float:
        return round(min(100.0, max(0.0, (value - low) / width * 100)), 1)

    band = 0.0 if hysteresis is None else hysteresis
    left = pct(target - band)
    return {
        "mark": None if temp is None else pct(temp),
        "band_left": left,
        "band_width": round(max(0.0, pct(target) - left), 1),
        "low_label": format_temp(low),
        "high_label": format_temp(high),
    }


def temperature_history(conn: sqlite3.Connection, vessel_id: str, *, hours: int = 24) -> list[dict]:
    latest = conn.execute("SELECT MAX(ts) AS ts FROM READING WHERE vessel_id = ?", (vessel_id,)).fetchone()["ts"]
    if latest is None:
        return []
    start = isoformat(parse_iso(latest) - timedelta(hours=hours))
    rows = conn.execute(
        """
        SELECT ts, vessel_temp_f, ambient_temp_f, heater_on
        FROM READING
        WHERE vessel_id = ? AND ts >= ?
        ORDER BY ts
        """,
        (vessel_id, start),
    ).fetchall()
    points = [
        {
            "ts": row["ts"],
            "vessel_temp_f": row["vessel_temp_f"],
            "ambient_temp_f": row["ambient_temp_f"],
            "heater_on": bool(row["heater_on"]),
        }
        for row in rows
    ]
    return _bucket(points, 480)


def _average(samples: list[dict], key: str) -> float | None:
    values = [sample[key] for sample in samples if sample[key] is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _bucket(points: list[dict], max_points: int) -> list[dict]:
    if len(points) <= max_points:
        return points
    size = len(points) / max_points
    buckets = []
    for index in range(max_points):
        chunk = points[int(index * size) : int((index + 1) * size)]
        if not chunk:
            continue
        on = sum(1 for sample in chunk if sample["heater_on"])
        buckets.append(
            {
                "ts": chunk[-1]["ts"],
                "vessel_temp_f": _average(chunk, "vessel_temp_f"),
                "ambient_temp_f": _average(chunk, "ambient_temp_f"),
                "heater_on": on * 2 >= len(chunk),
            }
        )
    return buckets


def snapshot(conn: sqlite3.Connection) -> dict:
    vessels = []
    for vessel in conn.execute("SELECT * FROM VESSEL WHERE enabled = 1 ORDER BY id"):
        zone = None
        if vessel["temp_zone_id"]:
            zone = conn.execute("SELECT * FROM TEMP_ZONE WHERE id = ?", (vessel["temp_zone_id"],)).fetchone()
        batch = conn.execute(
            "SELECT * FROM BATCH WHERE vessel_id = ? AND ended_at IS NULL",
            (vessel["id"],),
        ).fetchone()
        reading = conn.execute(
            "SELECT * FROM READING WHERE vessel_id = ? ORDER BY ts DESC LIMIT 1",
            (vessel["id"],),
        ).fetchone()
        reminder = None
        guidance = ""
        profile_name = None
        stage_ids: list[str] = []
        next_stage = None
        if batch is not None:
            profile = json.loads(batch["profile_snapshot_json"])
            profile_name = profile.get("name")
            stage_ids = [item["id"] for item in profile.get("stages", [])]
            next_stage = None
            if batch["stage"] in stage_ids and stage_ids.index(batch["stage"]) + 1 < len(stage_ids):
                sid = stage_ids[stage_ids.index(batch["stage"]) + 1]
                label = _STAGE.get(sid, sid.replace("_", " ").capitalize())
                next_stage = {"id": sid, "label": label, "action": _NEXT_ACTION.get(sid, f"Move to {label.lower()}")}
            guidance = profile.get("guidance", {}).get("safety_glass", "")
            reminder = conn.execute(
                """
                SELECT * FROM REMINDER
                WHERE batch_id = ? AND status IN ('pending', 'open')
                ORDER BY due_at LIMIT 1
                """,
                (batch["id"],),
            ).fetchone()
        vessel_label = _VESSEL.get(vessel["vessel_type"], vessel["vessel_type"].replace("_", " "))
        zone_name = None if zone is None else zone["name"]
        vessels.append(
            {
                "id": vessel["id"],
                "name": vessel["name"],
                "vessel_type": vessel["vessel_type"],
                "vessel_label": vessel_label,
                "zone_name": zone_name,
                "zone_id": vessel["temp_zone_id"],
                "capability": None if zone is None else zone["capability"],
                "source": vessel["source"],
                "probe_rom_id": vessel["probe_rom_id"],
                "capacity_l": vessel["capacity_l"],
                "place_label": vessel_label if zone_name is None else f"{vessel_label} · {zone_name}",
                "target_f": None if zone is None else zone["target_f"],
                "target_label": None if zone is None else format_temp(zone["target_f"]),
                "hysteresis_f": None if zone is None else zone["hysteresis_f"],
                "heater_on": bool(reading["heater_on"]) if reading is not None else False,
                "vessel_temp_f": None if reading is None else reading["vessel_temp_f"],
                "vessel_temp_label": None if reading is None else format_temp(reading["vessel_temp_f"]),
                "ambient_temp_f": None if reading is None else reading["ambient_temp_f"],
                "ambient_temp_label": None if reading is None else format_temp(reading["ambient_temp_f"]),
                "batch": None
                if batch is None
                else {
                    "id": batch["id"],
                    "name": batch["name"],
                    "stage": batch["stage"],
                    "stage_label": _STAGE.get(batch["stage"], batch["stage"].replace("_", " ")),
                    "profile_id": batch["profile_id"],
                    "profile_name": profile_name,
                    "started_at": batch["started_at"],
                    "started_label": format_local(batch["started_at"]),
                    "guidance": guidance,
                    "stages": stage_ids,
                    "next_stage": next_stage,
                },
                "next_reminder": None,
            }
        )
        if reminder is not None:
            vessels[-1]["next_reminder"] = {
                "id": reminder["id"],
                "due_at": reminder["due_at"],
                "text": reminder["text"],
            }
    as_of = conn.execute("SELECT MAX(ts) AS ts FROM READING").fetchone()["ts"]
    zone_count = len({item["zone_id"] for item in vessels if item["zone_id"]})
    for item in vessels:
        item["show_zone"] = zone_count > 1
        if item["zone_name"] and zone_count > 1:
            item["place_label"] = f"{item['vessel_label']} · {item['zone_name']}"
        else:
            item["place_label"] = item["vessel_label"]
        reminder = item["next_reminder"]
        if reminder is not None and as_of is not None:
            reminder["due_label"] = describe_due(reminder["due_at"], as_of)
        elif reminder is not None:
            reminder["due_label"] = format_local(reminder["due_at"])
        item["tone"] = temp_tone(item["vessel_temp_f"], item["target_f"], item["hysteresis_f"])
        item["meter"] = temp_meter(item["vessel_temp_f"], item["target_f"], item["hysteresis_f"])
        item["elapsed_label"] = None
        item["steps"] = []
        item["carbonation"] = None
        batch = item["batch"]
        if batch is not None:
            item["steps"] = stage_steps(batch["stage"], batch.get("stages"))
            if as_of is not None:
                item["elapsed_label"] = elapsed_label(batch["started_at"], as_of)
                item["carbonation"] = carbonation_progress(batch["stage"], batch["started_at"], as_of)
    alerts = []
    rows = conn.execute(
        """
        SELECT ALERT.id, ALERT.dedupe_key, ALERT.severity, ALERT.status, ALERT.opened_at,
               EVENT.type AS event_type, EVENT.detail_json
        FROM ALERT
        LEFT JOIN EVENT ON EVENT.id = ALERT.event_id
        WHERE ALERT.status != 'resolved'
        ORDER BY CASE ALERT.status WHEN 'open' THEN 0 ELSE 1 END, ALERT.id
        """
    )
    for row in rows:
        detail = json.loads(row["detail_json"]) if row["detail_json"] else {}
        alerts.append(
            {
                "id": row["id"],
                "dedupe_key": row["dedupe_key"],
                "severity": row["severity"],
                "severity_label": _SEVERITY.get(row["severity"], row["severity"]),
                "status": row["status"],
                "opened_at": row["opened_at"],
                "opened_label": f"Since {format_local(row['opened_at'])}",
                "text": alert_sentence(row["event_type"], detail),
                "reminder": row["event_type"] in {"reminder_due", "refrigerate_now"},
            }
        )
    return {
        "vessels": vessels,
        "zone_count": zone_count,
        "alerts": alerts,
        "as_of": as_of,
        "as_of_label": None if as_of is None else format_local(as_of),
    }


def duration_label(started: str, ended: str) -> str:
    return elapsed_label(started, ended).replace(" since start", "")


def _history_item(row: sqlite3.Row) -> dict:
    profile = json.loads(row["profile_snapshot_json"])
    return {
        "id": row["id"],
        "name": row["name"],
        "vessel_id": row["vessel_id"],
        "vessel_name": row["vessel_name"] if "vessel_name" in row.keys() else row["vessel_id"],
        "profile_id": row["profile_id"],
        "profile_name": profile.get("name") or row["profile_id"],
        "stage": row["stage"],
        "stage_label": _STAGE.get(row["stage"], row["stage"].replace("_", " ").capitalize()),
        "started_at": row["started_at"],
        "started_label": format_local(row["started_at"]),
        "ended_at": row["ended_at"],
        "ended_label": None if row["ended_at"] is None else format_local(row["ended_at"]),
        "duration_label": None if row["ended_at"] is None else duration_label(row["started_at"], row["ended_at"]),
        "target_temp_f": row["target_temp_f"],
    }


def batch_history(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT BATCH.*, VESSEL.name AS vessel_name
        FROM BATCH LEFT JOIN VESSEL ON VESSEL.id = BATCH.vessel_id
        WHERE BATCH.ended_at IS NOT NULL
        ORDER BY BATCH.ended_at DESC, BATCH.id DESC
        """
    ).fetchall()
    return [_history_item(row) for row in rows]


def batch_detail(conn: sqlite3.Connection, batch_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT BATCH.*, VESSEL.name AS vessel_name
        FROM BATCH LEFT JOIN VESSEL ON VESSEL.id = BATCH.vessel_id
        WHERE BATCH.id = ?
        """,
        (batch_id,),
    ).fetchone()
    if row is None:
        return None
    item = _history_item(row)
    stats = conn.execute(
        """
        SELECT COUNT(*) AS n, MIN(vessel_temp_f) AS lo, MAX(vessel_temp_f) AS hi, AVG(vessel_temp_f) AS mean,
               AVG(heater_on) AS duty
        FROM READING WHERE batch_id = ? AND (flags & 32) = 0
        """,
        (batch_id,),
    ).fetchone()
    item["reading_count"] = stats["n"]
    item["temp_min_label"] = format_temp(stats["lo"])
    item["temp_max_label"] = format_temp(stats["hi"])
    item["temp_mean_label"] = format_temp(stats["mean"])
    item["heater_duty_pct"] = None if stats["duty"] is None else round(stats["duty"] * 100)
    item["notes"] = [
        {"ts_label": format_local(note["ts"]), "actor": note["actor"], "text": note["text"]}
        for note in conn.execute("SELECT * FROM NOTE WHERE batch_id = ? ORDER BY ts", (batch_id,))
    ]
    item["alert_count"] = conn.execute(
        "SELECT COUNT(*) AS n FROM EVENT WHERE batch_id = ? AND severity IN ('warning', 'action', 'critical')",
        (batch_id,),
    ).fetchone()["n"]
    return item


def batch_temperature_history(conn: sqlite3.Connection, batch_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT ts, vessel_temp_f, ambient_temp_f, heater_on FROM READING WHERE batch_id = ? ORDER BY ts",
        (batch_id,),
    ).fetchall()
    points = [
        {
            "ts": row["ts"],
            "vessel_temp_f": row["vessel_temp_f"],
            "ambient_temp_f": row["ambient_temp_f"],
            "heater_on": bool(row["heater_on"]),
        }
        for row in rows
    ]
    return _bucket(points, 480)


def profile_catalog(conn: sqlite3.Connection) -> list[dict]:
    """Latest version of every profile the controller has loaded or saved."""
    rows = conn.execute(
        """
        SELECT p.* FROM BEVERAGE_PROFILE p
        WHERE p.version = (SELECT MAX(version) FROM BEVERAGE_PROFILE q WHERE q.id = p.id)
        ORDER BY p.name, p.id
        """
    ).fetchall()
    counts = {
        r["profile_id"]: r["n"] for r in conn.execute("SELECT profile_id, COUNT(*) AS n FROM BATCH GROUP BY profile_id")
    }
    from fermentd.profiles.loader import load_profiles

    shipped = set(load_profiles())
    items = []
    for row in rows:
        if row["source"] != "user" and row["id"] not in shipped and not counts.get(row["id"]):
            continue  # a retired built-in placeholder with no batches
        definition = json.loads(row["definition_json"])
        temperature = definition.get("temperature", {})
        items.append(
            {
                "id": row["id"],
                "name": row["name"],
                "version": row["version"],
                "source": row["source"],
                "builtin": row["source"] != "user",
                "status": row["status"],
                "requires_capability": definition.get("requires_capability", []),
                "vessel_types": definition.get("vessel_types", []),
                "tracking_mode": definition.get("tracking_mode"),
                "target_label": format_temp(temperature.get("default_target_f")),
                "definition": definition,
                "batch_count": counts.get(row["id"], 0),
            }
        )
    return items


def profile_choices(catalog: list[dict], vessel: dict) -> list[dict]:
    """Profiles for a vessel's start form, each marked available or with the reason it is not."""
    choices = []
    for item in catalog:
        reason = None
        if item["status"] != "supported":
            reason = "not supported yet" if item["status"] == "unsupported_v1" else item["status"]
        elif vessel.get("capability") is None:
            reason = "vessel has no temperature zone"
        elif any(cap != vessel["capability"] for cap in item["requires_capability"]):
            reason = "needs " + ", ".join(cap for cap in item["requires_capability"] if cap != vessel["capability"])
        elif item["vessel_types"] and vessel["vessel_type"] not in item["vessel_types"]:
            reason = "not for this vessel"
        choices.append(
            {
                "id": item["id"],
                "name": item["name"],
                "available": reason is None,
                "reason": reason,
                "default_name": f"{item['name']} #{item.get('batch_count', 0) + 1}",
            }
        )
    choices.sort(key=lambda choice: (not choice["available"], choice["name"]))
    return choices


def target_control(conn: sqlite3.Connection, vessel: dict) -> dict | None:
    """Range a running batch's target may be set to: every active profile in the zone, inside the
    hard global limits (the controller re-checks against the configured limits)."""
    from fermentd.config import HARD_TARGET_MAX_F, HARD_TARGET_MIN_F

    rows = conn.execute(
        """
        SELECT BATCH.profile_snapshot_json FROM BATCH JOIN VESSEL ON VESSEL.id = BATCH.vessel_id
        WHERE VESSEL.temp_zone_id = ? AND BATCH.ended_at IS NULL
        """,
        (vessel["zone_id"],),
    ).fetchall()
    low, high = HARD_TARGET_MIN_F, HARD_TARGET_MAX_F
    for row in rows:
        allowed = json.loads(row["profile_snapshot_json"]).get("temperature", {}).get("allowed_target_f")
        if allowed:
            low, high = max(low, float(allowed[0])), min(high, float(allowed[1]))
    if low > high:
        return None
    return {
        "low": low,
        "high": high,
        "value": vessel.get("target_f"),
        "label": f"{format_temp(low)}–{format_temp(high)}",
        "shared": len(rows) > 1,
    }


def gravity_summary(conn: sqlite3.Connection, batch_id: int) -> dict:
    """Hydrometer log with ABV, apparent attenuation and a stability hint."""
    batch = conn.execute("SELECT og, profile_snapshot_json FROM BATCH WHERE id = ?", (batch_id,)).fetchone()
    rows = conn.execute(
        "SELECT ts, sg, sample_temp_f FROM GRAVITY_READING WHERE batch_id = ? ORDER BY ts, id", (batch_id,)
    ).fetchall()
    readings = [
        {
            "label": format_local(r["ts"]),
            "sg": r["sg"],
            "sg_label": f"{r['sg']:.3f}",
            "temp": format_temp(r["sample_temp_f"]),
        }
        for r in rows
    ]
    out: dict = {"readings": list(reversed(readings)), "og": None, "abv": None, "attenuation": None, "hint": None}
    if not rows:
        return out
    og = batch["og"] if batch and batch["og"] else rows[0]["sg"]
    latest = rows[-1]
    out["og"] = f"{og:.3f}"
    if og > 1.0 and len(rows) > 1:
        out["abv"] = f"{max(0.0, (og - latest['sg']) * 131.25):.1f}%"
        out["attenuation"] = f"{max(0.0, (og - latest['sg']) / (og - 1.0) * 100):.0f}%"
    last_ts = parse_iso(latest["ts"])
    earlier = [r for r in rows[:-1] if (last_ts - parse_iso(r["ts"])).total_seconds() >= 2 * 86400]
    if earlier:
        prev = earlier[-1]
        if abs(prev["sg"] - latest["sg"]) <= 0.001:
            out["hint"] = {
                "stable": True,
                "text": f"Stable: {prev['sg']:.3f} → {latest['sg']:.3f} over 2+ days. If it is at the guide's final "
                "gravity, it is safe to bottle (the guide asks for 3 readings over 3 days to be sure).",
            }
        else:
            out["hint"] = {"stable": False, "text": "Still dropping. Keep fermenting and read again in 2 days."}
    else:
        out["hint"] = {
            "stable": False,
            "text": "Take another reading at least 2 days after this one to check it is finished.",
        }
    return out


def stage_label(stage_id: str) -> str:
    return _STAGE.get(stage_id, stage_id.replace("_", " ").capitalize())


def reminder_when(anchor: str) -> str:
    """'stage:primary+14d' -> 'Primary fermentation, day 14'."""
    head, _, offset = anchor.partition("+")
    where = stage_label(head.removeprefix("stage:")) if head.startswith("stage:") else head.capitalize()
    unit = {"m": "min", "h": "h", "d": "day"}.get(offset[-1:], "")
    number = offset[:-1]
    when = f"day {number}" if unit == "day" else f"{number} {unit}"
    return f"{where}, {when}"


def heater_duty(conn: sqlite3.Connection, vessel_id: str, batch_id: int | None) -> dict | None:
    """Share of readings with the heat mat on: last 24 h and the whole batch."""
    latest = conn.execute("SELECT MAX(ts) AS ts FROM READING WHERE vessel_id = ?", (vessel_id,)).fetchone()["ts"]
    if latest is None:
        return None
    since = isoformat(parse_iso(latest) - timedelta(hours=24))
    day = conn.execute(
        "SELECT AVG(heater_on) AS d, COUNT(*) AS n FROM READING WHERE vessel_id = ? AND ts > ?", (vessel_id, since)
    ).fetchone()
    out = {"day_pct": None if not day["n"] else round(day["d"] * 100), "batch_pct": None}
    if batch_id is not None:
        whole = conn.execute(
            "SELECT AVG(heater_on) AS d, COUNT(*) AS n FROM READING WHERE batch_id = ?", (batch_id,)
        ).fetchone()
        if whole["n"]:
            out["batch_pct"] = round(whole["d"] * 100)
    return out
