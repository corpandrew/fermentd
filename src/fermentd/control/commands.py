"""Validate and apply command rows. Rejections leave stored settings unchanged."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from fermentd.control import notes, tweaks
from fermentd.control.prep import PREP_STAGE
from fermentd.clock import Clock
from fermentd.config import FermentdConfig
from fermentd.control.alerts import ack_alert, resolve_alert
from fermentd.control.reminders import close_reminder_keys, complete_reminder, schedule_for_stage
from fermentd.control.safety import check_target
from fermentd.control.scale import scale_calibrate, scale_read, scale_tare
from fermentd.control.state import ZoneRuntime
from fermentd.drivers.base import Actuator, ActuatorUnreachable
from fermentd.profiles.schema import Profile
from fermentd.timefmt import isoformat, parse_iso

Result = tuple[str, dict[str, Any]]


class CommandContext:
    def __init__(
        self,
        conn: sqlite3.Connection,
        clock: Clock,
        config: FermentdConfig,
        profiles: dict[str, Profile],
        heaters: dict[str, Actuator],
        zones: dict[str, ZoneRuntime],
        scales: dict | None = None,
    ) -> None:
        self.conn = conn
        self.clock = clock
        self.config = config
        self.profiles = profiles
        self.heaters = heaters
        self.zones = zones
        self.scales = scales or {}


def database_now(conn: sqlite3.Connection, fallback: datetime) -> datetime:
    """Time of the newest controller write. The web process and a simulated controller do not share a clock."""
    row = conn.execute(
        """
        SELECT MAX(ts) AS ts FROM (
            SELECT ts FROM READING
            UNION ALL
            SELECT ts FROM EVENT
        )
        """
    ).fetchone()
    if row["ts"]:
        return parse_iso(row["ts"])
    return fallback


def enqueue(
    conn: sqlite3.Connection,
    clock: Clock,
    *,
    actor: str,
    command_type: str,
    params: dict,
    idempotency_key: str,
    ttl_s: int = 600,
) -> int:
    existing = conn.execute(
        "SELECT id FROM COMMAND WHERE actor = ? AND idempotency_key = ?",
        (actor, idempotency_key),
    ).fetchone()
    if existing is not None:
        return int(existing["id"])
    now = clock.now()
    cursor = conn.execute(
        """
        INSERT INTO COMMAND (
            idempotency_key, actor, type, params_json, status, created_at, expires_at
        ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            idempotency_key,
            actor,
            command_type,
            json.dumps(params),
            isoformat(now),
            isoformat(now + timedelta(seconds=ttl_s)),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def execute(ctx: CommandContext, command_id: int, actor: str, command_type: str, params: dict) -> Result:
    handler = {
        "start_batch": _start_batch,
        "set_stage": _set_stage,
        "set_target_temp": _set_target_temp,
        "add_gravity": _add_gravity,
        "end_batch": _end_batch,
        "delete_batch": _delete_batch,
        "add_vessel": _add_vessel,
        "update_vessel": _update_vessel,
        "rename_zone": _rename_zone,
        "save_profile": _save_profile,
        "ack_alert": _ack_alert,
        "complete_reminder": _complete_reminder,
        "heaters_off": _heaters_off,
        "scale_read": scale_read,
        "scale_tare": scale_tare,
        "scale_calibrate": scale_calibrate,
        "add_tweak": tweaks.cmd_add_tweak,
        "remove_tweak": tweaks.cmd_remove_tweak,
        "log_tasting": tweaks.cmd_log_tasting,
        "save_variant": tweaks.cmd_save_variant,
        "add_note": lambda c, a, p: notes.cmd_add_note(c, a, p, command_id),
    }.get(command_type)
    if handler is None:
        return _reject("UNKNOWN_COMMAND", f"unknown command {command_type}")
    result = handler(ctx, actor, params)
    if result[0] in {"done", "rejected"}:
        _audit(
            ctx,
            command_id,
            actor,
            command_type,
            str(
                params.get("vessel_id")
                or params.get("zone")
                or (f"batch:{params['batch_id']}" if params.get("batch_id") is not None else command_type)
            ),
            None,
            json.dumps(result[1]),
            _audit_batch_id(ctx, command_type, params, result[1]) if result[0] == "done" else None,
        )
    return result


def _start_batch(ctx: CommandContext, actor: str, params: dict) -> Result:
    vessel_id = params.get("vessel_id")
    vessel = ctx.conn.execute("SELECT * FROM VESSEL WHERE id = ?", (vessel_id,)).fetchone()
    if vessel is None or not vessel["enabled"]:
        return _reject("NOT_FOUND", f"vessel {vessel_id} was not found")
    active = ctx.conn.execute(
        "SELECT id FROM BATCH WHERE vessel_id = ? AND ended_at IS NULL",
        (vessel_id,),
    ).fetchone()
    if active is not None:
        return _reject("CONFLICT", f"vessel {vessel_id} already has an active batch")
    profile_id = params.get("profile_id") or ctx.config.profiles.default_profile
    profile = ctx.profiles.get(profile_id)
    if profile is None:
        return _reject("NOT_FOUND", f"profile {profile_id} was not found")
    if profile.status != "supported":
        return _reject("PROFILE_UNSUPPORTED", f"{profile_id} is {profile.status}")
    zone = _config_zone(ctx, vessel["temp_zone_id"])
    if zone is not None:
        missing = [cap for cap in profile.requires_capability if cap != zone.capability]
        if missing:
            return _reject("PROFILE_UNSUPPORTED", f"{profile_id} needs {', '.join(missing)}")
    if profile.vessel_types and vessel["vessel_type"] not in profile.vessel_types:
        return _reject("PROFILE_INVALID", f"{vessel['vessel_type']} is not a {profile_id} vessel")
    stage = params.get("stage") or profile.default_stage or profile.stages[0].id
    if stage not in {item.id for item in profile.stages}:
        return _reject("PROFILE_INVALID", f"unknown stage {stage}")
    stage_spec = next((item for item in profile.stages if item.id == stage), None)
    target_f = profile.temperature.default_target_f
    zone_setting = None
    if zone is not None and stage != PREP_STAGE:
        # A vessel with no zone is monitor-only, and a batch in Prep does not use its zone yet.
        joined = _join_zone(ctx, zone, profile, stage_spec)
        if isinstance(joined, tuple) and joined[0] == "rejected":
            return joined
        zone_setting = joined
        target_f = joined[0]
    size = str(params.get("batch_size_gal") or "1")
    if size not in {"1", "0.5"}:
        return _reject("PROFILE_INVALID", f"batch size {size} gal is not 1 or 0.5")
    volume_l = round(float(size) * 3.785, 3)
    copy_error = tweaks.check_copy_source(ctx.conn, profile.id, params)
    if copy_error:
        return _reject("INVALID", copy_error)
    now = isoformat(ctx.clock.now())
    snapshot = profile.model_dump(mode="json")
    cursor = ctx.conn.execute(
        """
        INSERT INTO BATCH (
            vessel_id, profile_id, profile_version, profile_snapshot_json, tracking_mode,
            name, stage, started_at, target_temp_f, volume_l, stage_started_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            vessel_id,
            profile.id,
            _profile_version(ctx, profile.id),
            json.dumps(snapshot),
            profile.tracking_mode,
            params.get("name") or profile.name,
            stage,
            now,
            target_f,
            volume_l,
            now,
        ),
    )
    batch_id = cursor.lastrowid
    if zone_setting is not None:
        ctx.conn.execute(
            "UPDATE TEMP_ZONE SET target_f = ?, hysteresis_f = ? WHERE id = ?",
            (zone_setting[0], zone_setting[1], zone.id),
        )
    schedule_for_stage(
        ctx.conn,
        batch_id=batch_id,
        profile=profile,
        stage=stage,
        stage_started_at=now,
        actor=actor,
    )
    tweaks.copy_into_new_batch(ctx, batch_id, profile.id, params, actor)
    return "done", {"ok": True, "batch_id": batch_id, "stage": stage, "profile_id": profile.id}


def _set_stage(ctx: CommandContext, actor: str, params: dict) -> Result:
    batch = _batch(ctx, params)
    if isinstance(batch, tuple):
        return batch
    profile = _snapshot_profile(batch)
    stage = params.get("stage")
    if stage not in {item.id for item in profile.stages}:
        return _reject("PROFILE_INVALID", f"unknown stage {stage}")
    old = batch["stage"]
    leaving_prep = old == PREP_STAGE and stage != PREP_STAGE
    zone = _config_zone(ctx, _zone_id(ctx, {"vessel_id": batch["vessel_id"]})) if leaving_prep else None
    if zone is not None:
        joined = _join_zone(ctx, zone, profile, next(item for item in profile.stages if item.id == stage))
        if joined[0] == "rejected":
            return joined
    if old != stage:
        keys = [item.id for item in profile.reminders if item.at.startswith(f"stage:{old}+")]
        close_reminder_keys(ctx.conn, ctx.clock, batch["id"], keys)
        now = isoformat(ctx.clock.now())
        ctx.conn.execute("UPDATE BATCH SET stage = ?, stage_started_at = ? WHERE id = ?", (stage, now, batch["id"]))
        schedule_for_stage(
            ctx.conn,
            batch_id=batch["id"],
            profile=profile,
            stage=stage,
            stage_started_at=now,
            actor=actor,
        )
        _audit(ctx, None, actor, "set_stage", f"batch:{batch['id']}", old, stage)
        spec = next(item for item in profile.stages if item.id == stage)
        if zone is not None:
            ctx.conn.execute("UPDATE TEMP_ZONE SET target_f = ?, hysteresis_f = ? WHERE id = ?",
                             (joined[0], joined[1], zone.id))
            ctx.conn.execute(
                "UPDATE BATCH SET target_temp_f = ?, target_armed_f = NULL, target_armed_at = ? WHERE id = ?",
                (joined[0], now, batch["id"]),
            )
        elif spec.target_f is not None:
            apply_auto_target(ctx, batch, spec.target_f, f"stage:{stage}")
    return "done", {"ok": True, "batch_id": batch["id"], "stage": stage}


def _join_zone(ctx: CommandContext, zone, profile: Profile, stage_spec) -> tuple:
    """Target and hysteresis a batch brings to its heater zone when it starts using it (at start, or
    when it leaves Prep). Zone rule: one heater, one target. Joining a busy zone adopts the zone's
    target and is refused if that target is outside what the profile allows."""
    overlap = _overlap_conflict(ctx, zone.id, profile)
    if overlap:
        return _reject("PROFILE_INVALID", overlap)
    target_f = profile.temperature.default_target_f
    hysteresis_f = profile.temperature.default_hysteresis_f
    if _active_in_zone(ctx, zone.id):
        current = ctx.conn.execute("SELECT target_f, hysteresis_f FROM TEMP_ZONE WHERE id = ?", (zone.id,)).fetchone()
        low, high = profile.temperature.allowed_target_f
        if not (low <= current["target_f"] <= high):
            return _reject(
                "CONFLICT",
                f"{zone.name} is holding {current['target_f']:g}°F for another batch, "
                f"but {profile.name} needs {low:g}–{high:g}°F. Use a vessel in another zone.",
            )
        return (current["target_f"], current["hysteresis_f"])
    if stage_spec is not None and stage_spec.target_f is not None:
        target_f = stage_spec.target_f
    return (target_f, hysteresis_f)


def apply_auto_target(ctx: CommandContext, batch, target_f: float, why: str) -> str:
    """Step the zone target for a profile schedule. Only when this batch has the zone to itself
    and the target passes every normal range check. Returns what happened."""
    zone_id = _zone_id(ctx, {"vessel_id": batch["vessel_id"]})
    if zone_id is None:
        return "no_zone"
    if len(_active_in_zone(ctx, zone_id)) != 1:
        return "shared"
    zone = ctx.conn.execute("SELECT * FROM TEMP_ZONE WHERE id = ?", (zone_id,)).fetchone()
    reason = check_target(
        target_f,
        zone["hysteresis_f"],
        global_low=ctx.config.control.target_min_f,
        global_high=ctx.config.control.target_max_f,
        hysteresis_low=ctx.config.control.hysteresis_min_f,
        hysteresis_high=ctx.config.control.hysteresis_max_f,
        profile_ranges=_profile_ranges(ctx, zone_id),
    )
    if reason is not None:
        return "out_of_range"
    if zone["target_f"] == target_f:
        return "unchanged"
    ctx.conn.execute("UPDATE TEMP_ZONE SET target_f = ? WHERE id = ?", (target_f, zone_id))
    ctx.conn.execute("UPDATE BATCH SET target_temp_f = ? WHERE id = ?", (target_f, batch["id"]))
    _audit(ctx, None, "schedule", "auto_target", f"batch:{batch['id']}:{why}", str(zone["target_f"]), str(target_f))
    return "applied"


def _set_target_temp(ctx: CommandContext, actor: str, params: dict) -> Result:
    zone_id = _zone_id(ctx, params)
    if zone_id is None:
        return _reject("NOT_FOUND", "temperature zone was not found")
    zone = ctx.conn.execute("SELECT * FROM TEMP_ZONE WHERE id = ?", (zone_id,)).fetchone()
    if zone is None:
        return _reject("NOT_FOUND", f"temperature zone {zone_id} was not found")
    target = float(params["target_f"])
    hysteresis = float(params.get("hysteresis_f", zone["hysteresis_f"]))
    reason = check_target(
        target,
        hysteresis,
        global_low=ctx.config.control.target_min_f,
        global_high=ctx.config.control.target_max_f,
        hysteresis_low=ctx.config.control.hysteresis_min_f,
        hysteresis_high=ctx.config.control.hysteresis_max_f,
        profile_ranges=_profile_ranges(ctx, zone_id),
    )
    if reason is not None:
        return _reject("OUT_OF_RANGE", reason)
    old = f"{zone['target_f']}"
    ctx.conn.execute(
        "UPDATE TEMP_ZONE SET target_f = ?, hysteresis_f = ? WHERE id = ?",
        (target, hysteresis, zone_id),
    )
    ctx.conn.execute(
        """
        UPDATE BATCH SET target_temp_f = ? WHERE ended_at IS NULL AND vessel_id IN (
            SELECT id FROM VESSEL WHERE temp_zone_id = ?
        )
        """,
        (target, zone_id),
    )
    _audit(ctx, None, actor, "set_target_temp", zone_id, old, str(target))
    return "done", {"ok": True, "zone": zone_id, "target_f": target, "hysteresis_f": hysteresis}


def _add_gravity(ctx: CommandContext, actor: str, params: dict) -> Result:
    batch = _batch(ctx, params)
    if isinstance(batch, tuple):
        return batch
    try:
        sg = float(params.get("sg"))
    except (TypeError, ValueError):
        return _reject("OUT_OF_RANGE", "Enter the gravity as a number such as 1.012.")
    if not (0.980 <= sg <= 1.200):
        return _reject("OUT_OF_RANGE", f"{sg} is not a hydrometer reading (0.980-1.200).")
    temp = params.get("sample_temp_f")
    temp_f = float(temp) if temp not in (None, "") else None
    now = isoformat(ctx.clock.now())
    ctx.conn.execute(
        "INSERT INTO GRAVITY_READING (batch_id, ts, sg, source, sample_temp_f) VALUES (?, ?, ?, 'hydrometer', ?)",
        (batch["id"], now, sg, temp_f),
    )
    if batch["og"] is None:
        ctx.conn.execute("UPDATE BATCH SET og = ? WHERE id = ?", (sg, batch["id"]))
    _audit(ctx, None, actor, "add_gravity", f"batch:{batch['id']}", None, f"{sg:.3f}")
    return "done", {"ok": True, "batch_id": batch["id"], "sg": sg}


def _end_batch(ctx: CommandContext, actor: str, params: dict) -> Result:
    batch = _batch(ctx, params)
    if isinstance(batch, tuple):
        return batch
    if batch["ended_at"] is not None:
        return _reject("CONFLICT", "That batch has already ended.")
    profile = _snapshot_profile(batch)
    done = next((stage.id for stage in profile.stages if stage.core == "done"), "done")
    now = isoformat(ctx.clock.now())
    keys = [
        row["reminder_key"]
        for row in ctx.conn.execute(
            "SELECT reminder_key FROM REMINDER WHERE batch_id = ? AND status IN ('pending', 'open')",
            (batch["id"],),
        )
    ]
    ctx.conn.execute(
        "UPDATE REMINDER SET status = 'cancelled' WHERE batch_id = ? AND status IN ('pending', 'open')",
        (batch["id"],),
    )
    for key in keys:
        resolve_alert(ctx.conn, ctx.clock, f"{key}:batch:{batch['id']}")
    resolve_alert(ctx.conn, ctx.clock, f"pressure_risk:batch:{batch['id']}")
    ctx.conn.execute(
        "UPDATE BATCH SET stage = ?, ended_at = ? WHERE id = ?",
        (done, now, batch["id"]),
    )
    heater = _idle_zone_heater(ctx, batch["vessel_id"])
    _audit(ctx, None, actor, "end_batch", f"batch:{batch['id']}", batch["stage"], done)
    return "done", {"ok": True, "batch_id": batch["id"], "stage": done, "heater": heater}


def _idle_zone_heater(ctx: CommandContext, vessel_id: str) -> str:
    """Turn the zone's heater off once nothing in the zone needs heat. Never leaves it on."""
    row = ctx.conn.execute("SELECT temp_zone_id FROM VESSEL WHERE id = ?", (vessel_id,)).fetchone()
    zone_id = None if row is None else row["temp_zone_id"]
    if zone_id is None:
        return "none"
    if _active_in_zone(ctx, zone_id):
        return "shared"
    heater = ctx.heaters.get(zone_id)
    if heater is None:
        return "none"
    state = ctx.zones.setdefault(zone_id, ZoneRuntime())
    try:
        heater.set(False)
    except ActuatorUnreachable:
        # The control loop holds the heater off with no active batch and keeps retrying.
        return "unreachable"
    if state.commanded_on or state.off_since is None:
        state.off_since = ctx.clock.monotonic()
    state.commanded_on = False
    state.on_since = None
    state.countdown_armed_mono = None
    state.countdown_failed = False
    return "off"


def _delete_batch(ctx: CommandContext, actor: str, params: dict) -> Result:
    if params.get("batch_id") is None:
        return _reject("NOT_FOUND", "batch was not found")
    batch = _batch(ctx, params)
    if isinstance(batch, tuple):
        return batch
    if batch["ended_at"] is None:
        return _reject("CONFLICT", "End the batch before deleting it.")
    batch_id = int(batch["id"])
    ctx.conn.commit()
    ctx.conn.execute("SAVEPOINT delete_batch")
    try:
        events = "SELECT id FROM EVENT WHERE batch_id = ?"
        ctx.conn.execute(
            f"DELETE FROM ALERT WHERE event_id IN ({events}) OR dedupe_key LIKE ?",
            (batch_id, f"%:batch:{batch_id}"),
        )
        ctx.conn.execute("UPDATE PROFILE_VARIANT SET source_batch_id = NULL WHERE source_batch_id = ?", (batch_id,))
        photos = [n for r in ctx.conn.execute("SELECT photo, thumb FROM NOTE WHERE batch_id = ?", (batch_id,))
                  for n in (r["photo"], r["thumb"]) if n]
        for table in (
            "EVENT",
            "READING",
            "READING_HOURLY",
            "GRAVITY_READING",
            "BASELINE_SEGMENT",
            "NOTE",
            "REMINDER",
            "BATCH_TWEAK",
            "TASTING",
        ):
            ctx.conn.execute(f"DELETE FROM {table} WHERE batch_id = ?", (batch_id,))
        ctx.conn.execute("DELETE FROM BATCH WHERE id = ?", (batch_id,))
    except Exception:
        ctx.conn.execute("ROLLBACK TO delete_batch")
        ctx.conn.execute("RELEASE delete_batch")
        raise
    ctx.conn.execute("RELEASE delete_batch")
    folder = notes.photo_dir(ctx.conn)
    for name in photos:
        if notes.PHOTO_NAME.match(name):
            (folder / name).unlink(missing_ok=True)
    _audit(ctx, None, actor, "delete_batch", f"batch:{batch_id}", batch["name"], None)
    return "done", {"ok": True, "batch_id": batch_id}


_VESSEL_TYPES = {"jug", "carboy", "bucket", "jar", "bottle_group"}


def _vessel_fields(ctx: CommandContext, params: dict) -> dict | Result:
    name = str(params.get("name") or "").strip()
    if not name:
        return _reject("INVALID", "A vessel needs a name.")
    vessel_type = params.get("vessel_type")
    if vessel_type not in _VESSEL_TYPES:
        return _reject("INVALID", f"Unknown vessel type {vessel_type}.")
    zone_id = params.get("temp_zone") or None
    if zone_id is not None and _config_zone(ctx, zone_id) is None:
        return _reject("NOT_FOUND", f"Temperature zone {zone_id} does not exist.")
    rom = str(params.get("probe_rom_id") or "").strip() or None
    if rom is not None:
        clash = ctx.conn.execute(
            "SELECT id FROM VESSEL WHERE probe_rom_id = ? AND enabled = 1 AND id != ?",
            (rom, params.get("vessel_id") or ""),
        ).fetchone()
        if clash is not None or rom == ctx.config.one_wire.ambient_probe:
            return _reject("CONFLICT", f"Probe {rom} is already in use.")
    capacity = params.get("capacity_l")
    return {
        "name": name,
        "vessel_type": vessel_type,
        "temp_zone_id": zone_id,
        "probe_rom_id": rom,
        "capacity_l": None if capacity in (None, "") else float(capacity),
    }


def _add_vessel(ctx: CommandContext, actor: str, params: dict) -> Result:
    fields = _vessel_fields(ctx, params)
    if isinstance(fields, tuple):
        return fields
    base = "".join(ch if ch.isalnum() else "_" for ch in fields["name"].lower()).strip("_") or "vessel"
    vessel_id = base
    n = 2
    while ctx.conn.execute("SELECT 1 FROM VESSEL WHERE id = ?", (vessel_id,)).fetchone():
        vessel_id = f"{base}{n}"
        n += 1
    ctx.conn.execute(
        """
        INSERT INTO VESSEL (id, name, vessel_type, capacity_l, probe_rom_id, temp_zone_id, enabled, source)
        VALUES (?, ?, ?, ?, ?, ?, 1, 'dashboard')
        """,
        (
            vessel_id,
            fields["name"],
            fields["vessel_type"],
            fields["capacity_l"],
            fields["probe_rom_id"],
            fields["temp_zone_id"],
        ),
    )
    _audit(ctx, None, actor, "add_vessel", f"vessel:{vessel_id}", None, json.dumps(fields))
    return "done", {"ok": True, "vessel_id": vessel_id}


def _update_vessel(ctx: CommandContext, actor: str, params: dict) -> Result:
    vessel_id = params.get("vessel_id")
    row = ctx.conn.execute("SELECT * FROM VESSEL WHERE id = ?", (vessel_id,)).fetchone()
    if row is None or not row["enabled"]:
        return _reject("NOT_FOUND", f"vessel {vessel_id} was not found")
    active = ctx.conn.execute(
        "SELECT id, stage FROM BATCH WHERE vessel_id = ? AND ended_at IS NULL", (vessel_id,)
    ).fetchone()
    if params.get("remove"):
        if row["source"] != "dashboard":
            return _reject("READ_ONLY", "This vessel comes from fermentd.yaml. Remove it there.")
        if active is not None:
            return _reject("CONFLICT", "End the running batch before removing this vessel.")
        ctx.conn.execute("UPDATE VESSEL SET enabled = 0 WHERE id = ?", (vessel_id,))
        _audit(ctx, None, actor, "remove_vessel", f"vessel:{vessel_id}", row["name"], None)
        return "done", {"ok": True, "vessel_id": vessel_id, "removed": True}
    fields = _vessel_fields(ctx, params)
    if isinstance(fields, tuple):
        return fields
    # A batch still in Prep ("Making it") does not use the heater or probe yet, so the vessel's
    # zone and probe can be attached now; the zone checks run when the batch leaves Prep.
    if active is not None and active["stage"] != PREP_STAGE:
        same = (
            fields["vessel_type"] == row["vessel_type"]
            and fields["temp_zone_id"] == row["temp_zone_id"]
            and fields["probe_rom_id"] == row["probe_rom_id"]
            and fields["capacity_l"] == row["capacity_l"]
        )
        if not same:
            return _reject(
                "CONFLICT",
                "A batch is running in this vessel. You can rename it now; end the batch to change anything else.",
            )
    ctx.conn.execute(
        """
        UPDATE VESSEL SET name = ?, vessel_type = ?, capacity_l = ?, probe_rom_id = ?, temp_zone_id = ?,
            user_edited = 1
        WHERE id = ?
        """,
        (
            fields["name"],
            fields["vessel_type"],
            fields["capacity_l"],
            fields["probe_rom_id"],
            fields["temp_zone_id"],
            vessel_id,
        ),
    )
    _audit(ctx, None, actor, "update_vessel", f"vessel:{vessel_id}", row["name"], json.dumps(fields))
    return "done", {"ok": True, "vessel_id": vessel_id}


def _rename_zone(ctx: CommandContext, actor: str, params: dict) -> Result:
    zone_id = params.get("zone")
    row = ctx.conn.execute("SELECT * FROM TEMP_ZONE WHERE id = ?", (zone_id,)).fetchone()
    if row is None:
        return _reject("NOT_FOUND", f"temperature zone {zone_id} was not found")
    name = str(params.get("name") or "").strip()
    if not name:
        return _reject("INVALID", "A zone needs a name.")
    ctx.conn.execute("UPDATE TEMP_ZONE SET name = ?, user_named = 1 WHERE id = ?", (name, zone_id))
    _audit(ctx, None, actor, "rename_zone", f"zone:{zone_id}", row["name"], name)
    return "done", {"ok": True, "zone": zone_id, "name": name}


def _save_profile(ctx: CommandContext, actor: str, params: dict) -> Result:
    """Save an edited profile as a new user version. Built-ins are copied, never changed."""
    source_id = params.get("profile_id")
    base = ctx.profiles.get(source_id)
    if base is None:
        return _reject("NOT_FOUND", f"profile {source_id} was not found")
    document = base.model_dump(mode="json")
    builtin = _profile_source(ctx, source_id) != "user"
    new_id = source_id
    if builtin:
        new_id = f"{source_id}_custom"
        n = 2
        while (
            new_id in ctx.profiles
            or ctx.conn.execute("SELECT 1 FROM BEVERAGE_PROFILE WHERE id = ?", (new_id,)).fetchone()
        ):
            new_id = f"{source_id}_custom{n}"
            n += 1
    edits = params.get("edits") or {}
    try:
        document["id"] = new_id
        document["extends"] = None
        if "name" in edits:
            document["name"] = str(edits["name"]).strip() or document["name"]
        temperature = document["temperature"]
        for key in ("default_target_f", "default_hysteresis_f"):
            if key in edits:
                temperature[key] = float(edits[key])
        if "allowed_low_f" in edits or "allowed_high_f" in edits:
            temperature["allowed_target_f"] = [
                float(edits.get("allowed_low_f", temperature["allowed_target_f"][0])),
                float(edits.get("allowed_high_f", temperature["allowed_target_f"][1])),
            ]
        if "recommended_low_f" in edits or "recommended_high_f" in edits:
            temperature["recommended_f"] = [
                float(edits.get("recommended_low_f", temperature["recommended_f"][0])),
                float(edits.get("recommended_high_f", temperature["recommended_f"][1])),
            ]
        if "cutoff_f" in edits:
            document["safety"]["cutoff_f"] = None if edits["cutoff_f"] in (None, "") else float(edits["cutoff_f"])
        if "safety_glass" in edits:
            document["guidance"]["safety_glass"] = str(edits["safety_glass"])
        for reminder in document["reminders"]:
            if f"reminder_at:{reminder['id']}" in edits:
                reminder["at"] = str(edits[f"reminder_at:{reminder['id']}"]).strip()
            if f"reminder_text:{reminder['id']}" in edits:
                reminder["text"] = str(edits[f"reminder_text:{reminder['id']}"]).strip()
        profile = Profile.model_validate(document)
    except (ValueError, TypeError, KeyError) as exc:
        return _reject("PROFILE_INVALID", _first_error(exc))
    from fermentd.profiles.loader import profile_safety_errors, save_user_profile

    low, high = profile.temperature.allowed_target_f
    rec_low, rec_high = profile.temperature.recommended_f
    if not (low <= rec_low <= rec_high <= high):
        return _reject("PROFILE_INVALID", "The recommended range must sit inside the allowed range.")
    reason = profile_safety_errors(profile, ctx.config)
    if reason is not None:
        return _reject("PROFILE_INVALID", reason)
    version = save_user_profile(ctx.conn, profile, isoformat(ctx.clock.now()))
    ctx.profiles[profile.id] = profile
    _audit(ctx, None, actor, "save_profile", f"profile:{profile.id}", source_id, str(version))
    return "done", {"ok": True, "profile_id": profile.id, "version": version, "copied": builtin}


def _profile_source(ctx: CommandContext, profile_id: str) -> str | None:
    row = ctx.conn.execute(
        "SELECT source FROM BEVERAGE_PROFILE WHERE id = ? ORDER BY version DESC LIMIT 1", (profile_id,)
    ).fetchone()
    return None if row is None else row["source"]


def _first_error(exc: Exception) -> str:
    errors = getattr(exc, "errors", None)
    if callable(errors):
        try:
            first = errors()[0]
            where = ".".join(str(part) for part in first.get("loc", ()))
            return f"{where}: {first.get('msg')}".strip(": ")
        except Exception:
            pass
    return str(exc).splitlines()[0] if str(exc) else "That profile is not valid."


def _ack_alert(ctx: CommandContext, actor: str, params: dict) -> Result:
    error = ack_alert(ctx.conn, ctx.clock, int(params["alert_id"]), actor)
    if error:
        return _reject(error, error)
    return "done", {"ok": True}


def _complete_reminder(ctx: CommandContext, actor: str, params: dict) -> Result:
    error = complete_reminder(ctx.conn, ctx.clock, int(params["reminder_id"]))
    if error:
        return _reject(error, error)
    _ = actor
    return "done", {"ok": True}


def _heaters_off(ctx: CommandContext, actor: str, params: dict) -> Result:
    _ = (actor, params)
    for zone_id, heater in ctx.heaters.items():
        try:
            heater.set(False)
        except ActuatorUnreachable:
            continue
        state = ctx.zones.setdefault(zone_id, ZoneRuntime())
        state.commanded_on = False
        state.off_since = ctx.clock.monotonic()
        state.on_since = None
    return "done", {"ok": True}


def _batch(ctx: CommandContext, params: dict) -> sqlite3.Row | Result:
    if params.get("batch_id") is not None:
        row = ctx.conn.execute("SELECT * FROM BATCH WHERE id = ?", (params["batch_id"],)).fetchone()
    else:
        row = ctx.conn.execute(
            "SELECT * FROM BATCH WHERE vessel_id = ? AND ended_at IS NULL",
            (params.get("vessel_id"),),
        ).fetchone()
    if row is None:
        return _reject("NOT_FOUND", "batch was not found")
    return row


def _snapshot_profile(batch: sqlite3.Row) -> Profile:
    return Profile.model_validate(json.loads(batch["profile_snapshot_json"]))


def _profile_version(ctx: CommandContext, profile_id: str) -> int:
    row = ctx.conn.execute(
        "SELECT version FROM BEVERAGE_PROFILE WHERE id = ? ORDER BY version DESC LIMIT 1",
        (profile_id,),
    ).fetchone()
    return 1 if row is None else int(row["version"])


def _config_zone(ctx: CommandContext, zone_id: str | None):
    for zone in ctx.config.temp_zones:
        if zone.id == zone_id:
            return zone
    return None


def _zone_id(ctx: CommandContext, params: dict) -> str | None:
    if params.get("zone"):
        return str(params["zone"])
    vessel_id = params.get("vessel") or params.get("vessel_id")
    if not vessel_id:
        return None
    row = ctx.conn.execute("SELECT temp_zone_id FROM VESSEL WHERE id = ?", (vessel_id,)).fetchone()
    if row is None:
        return None
    return row["temp_zone_id"]


def _profile_ranges(ctx: CommandContext, zone_id: str) -> list[tuple[str, float, float]]:
    ranges = []
    for batch in _active_in_zone(ctx, zone_id):
        profile = _snapshot_profile(batch)
        low, high = profile.temperature.allowed_target_f
        ranges.append((profile.id, float(low), float(high)))
    return ranges


def _overlap_conflict(ctx: CommandContext, zone_id: str, profile: Profile) -> str | None:
    low, high = profile.temperature.allowed_target_f
    for batch in _active_in_zone(ctx, zone_id):
        other = _snapshot_profile(batch)
        other_low, other_high = other.temperature.allowed_target_f
        if high < other_low or low > other_high:
            return f"{profile.id} does not overlap {other.id} in {zone_id}"
    return None


def _active_in_zone(ctx: CommandContext, zone_id: str) -> list[sqlite3.Row]:
    return ctx.conn.execute(
        """
        SELECT BATCH.* FROM BATCH
        JOIN VESSEL ON VESSEL.id = BATCH.vessel_id
        WHERE VESSEL.temp_zone_id = ? AND BATCH.ended_at IS NULL AND BATCH.stage != 'prep'
        """,
        (zone_id,),
    ).fetchall()


def _reject(code: str, message: str) -> Result:
    return "rejected", {"ok": False, "error": code, "message": message}


def _audit(
    ctx: CommandContext,
    command_id: int | None,
    actor: str,
    action: str,
    target: str,
    old: str | None,
    new: str | None,
    batch_id: int | None = None,
) -> None:
    if batch_id is None and target.startswith("batch:"):
        head = target.split(":")[1]
        batch_id = int(head) if head.isdigit() else None
    ctx.conn.execute(
        """
        INSERT INTO AUDIT_LOG (ts, actor, action, target, old_value, new_value, command_id, batch_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (isoformat(ctx.clock.now()), actor, action, target, old, new, command_id, batch_id),
    )


def _audit_batch_id(ctx: CommandContext, command_type: str, params: dict, result: dict) -> int | None:
    """Which batch a command belongs to, for the per-batch activity log."""
    if command_type == "delete_batch":
        return None
    for source in (result, params):
        value = source.get("batch_id") if isinstance(source, dict) else None
        if value is not None and str(value).isdigit():
            return int(value)
    if command_type == "set_target_temp":
        zone = (result or {}).get("zone") or params.get("zone") or params.get("zone_id")
        row = ctx.conn.execute(
            "SELECT b.id FROM BATCH b JOIN VESSEL v ON v.id = b.vessel_id "
            "WHERE v.temp_zone_id = ? AND b.ended_at IS NULL ORDER BY b.id DESC LIMIT 1",
            (zone,),
        ).fetchone()
        return None if row is None else row["id"]
    return None
