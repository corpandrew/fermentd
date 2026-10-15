"""Single writer for readings, batches, alerts, and heaters."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sqlite3
import time
from pathlib import Path

from fermentd.clock import Clock, SystemClock
from fermentd.config import FermentdConfig, VesselConfig, load_config, load_secrets
from fermentd.control import cutoff
from fermentd.control.alerts import raise_alert, resolve_alert
from fermentd.control.commands import CommandContext, apply_auto_target, enqueue, execute
from fermentd.control.digest import build_digest, digest_slot, record_digest, sent_digest_ids
from fermentd.control.probes import ProbeHealth, observe
from fermentd.control.reminders import evaluate_reminders
from fermentd.control.planned import marker_fresh, take_marker
from fermentd.control.safety import ProbeView, SafetyInput, SafetyLimits, check_target, evaluate_safety
from fermentd.control.scale import sample_scales, sync_scale_rows
from fermentd.control.state import Runtime, ZoneRuntime
from fermentd.control.thermostat import evaluate_thermostat
from fermentd.control import tuning as heat_tuning
from fermentd.db.connection import connect
from fermentd.db.migrate import migrate
from fermentd.drivers.base import ActuatorUnreachable
from fermentd.drivers.factory import Hardware, build_hardware
from fermentd.notify.base import Notifier
from fermentd.notify.fanout import build_notifier, finish_delivery, start_delivery
from fermentd.profiles.loader import load_profiles, load_user_profiles, persist_profiles
from fermentd.profiles.schema import Profile, duration_seconds
from fermentd.timefmt import format_local, isoformat, parse_iso
from fermentd.web.status import alert_sentence, format_temp

log = logging.getLogger("fermentd")
FLAG_PROBE_FAULT = 4
FLAG_SAFETY = 16
FLAG_SETTLING = 32  # probe just moved: kept for the chart, left out of stats and alerts
PRESSURE_CLEAR_BELOW_F = 0.5
FALLING_LOOKBACK_S = 300
FALLING_MIN_DROP_F = 0.1
HEAT_STATE_KEY = "heater_state:"
HEAT_STATE_MAX_AGE_S = 600
FRESH_READING_MAX_S = 90.0
BELOW_TARGET_MARGIN_F = 3.0
BELOW_TARGET_AFTER_S = 3 * 3600
BELOW_TARGET_PUSH_AFTER_S = 15 * 3600
INTERRUPTED_CLEAR_S = 180
INTERRUPTED_CLEAR_TICKS = 3
TARGET_REACHED_TOLERANCE_F = 0.5
_ZONE_ALERTS = (
    "config_conflict",
    "overtemp_cutoff",
    "sensor_fault",
    "max_on_rest",
    "heater_unreachable",
    "heater_state_mismatch",
    "countdown_arm_failed",
    "countdown_not_armed",
    "temp_below_target",
    "temp_out_of_range",
)


class ControlService:
    def __init__(
        self,
        config: FermentdConfig,
        conn: sqlite3.Connection,
        clock: Clock,
        hardware: Hardware,
        profiles: dict[str, Profile],
        notifier: Notifier,
    ) -> None:
        self.config = config
        self.conn = conn
        self.clock = clock
        self.hardware = hardware
        self.profiles = profiles
        self.notifier = notifier
        self.runtime = Runtime()

    def startup(self) -> None:
        self._sync_hardware_rows()
        sync_scale_rows(self.conn, self.config)
        persist_profiles(self.conn, self.profiles, isoformat(self.clock.now()))
        self.profiles.update(load_user_profiles(self.conn, self.config))
        planned = marker_fresh(self.conn, self.clock.now())
        saved = self._load_heat_states() if planned else {}
        for zone_id, heater in self.hardware.heaters.items():
            state = ZoneRuntime()
            try:
                heater.set(False)
            except ActuatorUnreachable:
                log.warning("heater %s was unreachable while forcing off at startup", zone_id)
            state.commanded_on = False
            self.runtime.zones[zone_id] = state
            if zone_id in saved:
                self._restore_heat_state(zone_id, saved[zone_id])
        self._notify_interrupted_restart()
        self.runtime.started_mono = self.clock.monotonic()
        self.conn.execute(
            """
            INSERT INTO EVENT (ts, type, severity, actor, detail_json)
            VALUES (?, 'service_started', 'info', 'control', '{}')
            """,
            (isoformat(self.clock.now()),),
        )
        self.conn.commit()

    def stop(self) -> None:
        planned = marker_fresh(self.conn, self.clock.now())
        self.conn.execute(
            """
            INSERT INTO EVENT (ts, type, severity, actor, detail_json)
            VALUES (?, 'service_stopped', ?, 'control', ?)
            """,
            (isoformat(self.clock.now()), "info" if planned else "action", json.dumps({"planned": planned})),
        )
        if planned:  # deploy restart: no push, the marker is consumed by the next startup
            self._save_heat_states()
            self.conn.commit()
            return
        self.notifier.notify(
            "service_stopping",
            "action",
            self._alert_title(None, None),
            alert_sentence("service_stopping", {}),
        )
        self.conn.commit()

    def tick(self) -> None:
        self._poll_commands()
        self._apply_ramps()
        self._read_probes()
        self._track_wiring()
        now = self.clock.monotonic()
        for zone in self.config.temp_zones:
            state = self.runtime.zones.setdefault(zone.id, ZoneRuntime())
            state.have_fresh = self._readings_are_fresh(zone.id, now)
            self._control_zone(zone.id)
        self._check_probe_silence()
        self._write_readings()
        sample_scales(self)
        for kind, severity, title, body in evaluate_reminders(self.conn, self.clock):
            self.notifier.notify(kind, severity, title, body)
        self._maybe_digest()
        resolve_alert(self.conn, self.clock, "control_fault:zone:control")
        self._clear_interrupted_when_healthy()
        self.conn.commit()

    # --- mat state across a planned restart -------------------------------------------------
    def _save_heat_states(self) -> None:
        """Remember each mat's state (and burst/timer progress) so a deploy does not cut a heating
        burst short. Only read back after a planned restart, and only if recent."""
        now_mono = self.clock.monotonic()
        now_ts = self.clock.now().timestamp()
        for zone_id, state in self.runtime.zones.items():
            def wall(mono):
                return None if mono is None else now_ts - (now_mono - mono)
            payload = {
                "saved_at": now_ts,
                "on": state.commanded_on,
                "on_since": wall(state.on_since),
                "off_since": wall(state.off_since),
                "window_start": wall(state.window_start),
                "window_on_s": state.window_on_s,
                "window_key": list(state.window_key) if state.window_key else None,
            }
            self.conn.execute(
                "INSERT INTO SETTING (key, value, updated_at, updated_by) VALUES (?, ?, ?, 'control') "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (HEAT_STATE_KEY + zone_id, json.dumps(payload), isoformat(self.clock.now())),
            )

    def _load_heat_states(self) -> dict[str, dict]:
        out = {}
        rows = self.conn.execute("SELECT key, value FROM SETTING WHERE key LIKE ?", (HEAT_STATE_KEY + "%",)).fetchall()
        for row in rows:
            try:
                data = json.loads(row["value"])
            except ValueError:
                continue
            if self.clock.now().timestamp() - float(data.get("saved_at", 0)) <= HEAT_STATE_MAX_AGE_S:
                out[row["key"][len(HEAT_STATE_KEY):]] = data
        self.conn.execute("DELETE FROM SETTING WHERE key LIKE ?", (HEAT_STATE_KEY + "%",))
        return out

    def _restore_heat_state(self, zone_id: str, data: dict) -> None:
        state = self.runtime.zones[zone_id]
        now_mono = self.clock.monotonic()
        now_ts = self.clock.now().timestamp()

        def mono(wall):
            return None if wall is None else now_mono - (now_ts - float(wall))
        state.window_start = mono(data.get("window_start"))
        state.window_on_s = float(data.get("window_on_s") or 0.0)
        state.window_key = tuple(data["window_key"]) if data.get("window_key") else None
        state.off_since = mono(data.get("off_since"))
        if data.get("on"):
            # Turn the mat straight back on and re-arm the plug's own 10-min off-timer. The first tick
            # re-checks every safety rule (probe, cutoff, max-on) and turns it off if anything is wrong.
            if self._set_heater(zone_id, True, now_mono):
                state.on_since = mono(data.get("on_since")) or now_mono
                self._arm_countdown(zone_id, now_mono, force=True)
        self.conn.execute(
            "INSERT INTO EVENT (ts, type, severity, actor, detail_json) VALUES (?, 'heater_state_restored', 'info', 'control', ?)",
            (isoformat(self.clock.now()), json.dumps({"zone_id": zone_id, "on": bool(data.get("on"))})),
        )

    # --- probe moves ---------------------------------------------------------------------------
    def _track_wiring(self) -> None:
        """A vessel whose probe or heater zone changed gets a quiet period: the probe is still
        settling into its new spot, so those readings are left out of stats and alerts."""
        now = self.clock.monotonic()
        settle = self.config.control.probe_settle_minutes * 60
        for vessel in self._vessels():
            wiring = (vessel.probe_rom_id, vessel.temp_zone)
            before = self.runtime.vessel_wiring.get(vessel.id)
            if before is not None and before != wiring and vessel.probe_rom_id:
                self.runtime.settle_until[vessel.id] = now + settle
            self.runtime.vessel_wiring[vessel.id] = wiring

    def _settling(self, vessel_id: str | None) -> bool:
        until = self.runtime.settle_until.get(vessel_id or "")
        return until is not None and self.clock.monotonic() < until

    def _clear_interrupted_when_healthy(self) -> None:
        """A service_interrupted alert resolves itself once control has run normally for a few loop
        cycles and a few minutes after the restart. History stays: the row is resolved, not deleted."""
        rt = self.runtime
        rt.healthy_ticks += 1
        if rt.interrupted_cleared or rt.started_mono is None:
            return
        if rt.healthy_ticks >= INTERRUPTED_CLEAR_TICKS and self.clock.monotonic() - rt.started_mono >= INTERRUPTED_CLEAR_S:
            resolve_alert(self.conn, self.clock, "service_interrupted:zone:control")
            rt.interrupted_cleared = True

    def guarded_tick(self) -> None:
        try:
            self.tick()
        except Exception as exc:
            log.exception("control tick failed")
            self._fail_closed(exc)

    def submit(self, actor: str, command_type: str, params: dict, idempotency_key: str) -> int:
        return enqueue(
            self.conn,
            self.clock,
            actor=actor,
            command_type=command_type,
            params=params,
            idempotency_key=idempotency_key,
        )

    def _vessels(self) -> list[VesselConfig]:
        """Vessels as stored in the database: yaml seeds plus dashboard edits and additions."""
        configured = {vessel.id: vessel for vessel in self.config.vessels}
        vessels = []
        for row in self.conn.execute("SELECT * FROM VESSEL WHERE enabled = 1 ORDER BY id").fetchall():
            seed = configured.get(row["id"])
            if row["source"] == "config" and seed is None:
                continue
            vessels.append(
                VesselConfig(
                    id=row["id"],
                    name=row["name"],
                    vessel_type=row["vessel_type"],
                    capacity_l=row["capacity_l"],
                    enabled=True,
                    temp_zone=row["temp_zone_id"],
                    scale=None if seed is None else seed.scale,
                    probe_rom_id=row["probe_rom_id"],
                )
            )
        return vessels

    def poll_pending_commands(self) -> bool:
        """Cheap between-tick check so dashboard actions apply within about a second."""
        try:
            row = self.conn.execute("SELECT 1 FROM COMMAND WHERE status = 'pending' LIMIT 1").fetchone()
            if row is None:
                return False
            self._poll_commands()
            return True
        except Exception as exc:
            log.exception("command poll failed")
            self._fail_closed(exc)
            return False

    def _poll_commands(self) -> None:
        now = isoformat(self.clock.now())
        self.conn.execute(
            """
            UPDATE COMMAND SET status = 'expired', executed_at = ?
            WHERE status = 'pending' AND expires_at < ?
            """,
            (now, now),
        )
        rows = self.conn.execute("SELECT * FROM COMMAND WHERE status = 'pending' ORDER BY id").fetchall()
        ctx = CommandContext(
            self.conn,
            self.clock,
            self.config,
            self.profiles,
            self.hardware.heaters,
            self.runtime.zones,
            self.hardware.scales,
        )
        for row in rows:
            status, result = execute(ctx, row["id"], row["actor"], row["type"], json.loads(row["params_json"]))
            self.conn.execute(
                "UPDATE COMMAND SET status = ?, result_json = ?, executed_at = ? WHERE id = ?",
                (status, json.dumps(result), isoformat(self.clock.now()), row["id"]),
            )
        self.conn.commit()

    def _read_probes(self) -> None:
        roms = [self.config.one_wire.ambient_probe]
        roms.extend(vessel.probe_rom_id for vessel in self._vessels() if vessel.probe_rom_id)
        now = self.clock.monotonic()
        for rom in roms:
            sample = self.hardware.probes.read(rom)
            previous = self.runtime.probes.get(rom, ProbeHealth())
            self.runtime.probes[rom] = observe(
                previous,
                sample,
                now,
                self.config.safety.max_rate_f_per_min,
            )

    def _control_zone(self, zone_id: str) -> None:
        zone_cfg = next(zone for zone in self.config.temp_zones if zone.id == zone_id)
        state = self.runtime.zones[zone_id]
        row = self.conn.execute("SELECT * FROM TEMP_ZONE WHERE id = ?", (zone_id,)).fetchone()
        views: list[ProbeView] = []
        temps: list[float] = []
        alert_temps: list[float] = []
        controlling: list[tuple[str, str]] = []
        # Batches in Prep ("Making it") are not fermenting yet: their vessel's probe still counts for the
        # over-temperature cutoff, but not for the thermostat, the zone's range or temperature alerts.
        prep_vessels = {
            r["vessel_id"]
            for r in self.conn.execute("SELECT vessel_id FROM BATCH WHERE ended_at IS NULL AND stage = 'prep'")
        }
        for vessel in self._vessels():
            if vessel.temp_zone != zone_id or not vessel.enabled or not vessel.probe_rom_id:
                continue
            health = self.runtime.probes[vessel.probe_rom_id]
            views.append(ProbeView(vessel.probe_rom_id, "vessel", health.temp_f, health.faulted))
            if health.temp_f is not None and not health.faulted and vessel.id not in prep_vessels:
                temps.append(health.temp_f)
                controlling.append((vessel.id, vessel.vessel_type))
                if not self._settling(vessel.id):
                    alert_temps.append(health.temp_f)
        ambient = self.runtime.probes[self.config.one_wire.ambient_probe]
        views.append(ProbeView(self.config.one_wire.ambient_probe, "ambient", ambient.temp_f, ambient.faulted))
        active = self.conn.execute(
            """
            SELECT BATCH.* FROM BATCH
            JOIN VESSEL ON VESSEL.id = BATCH.vessel_id
            WHERE VESSEL.temp_zone_id = ? AND BATCH.ended_at IS NULL AND BATCH.stage != 'prep'
            """,
            (zone_id,),
        ).fetchall()
        ranges = []
        for batch in active:
            profile = Profile.model_validate(json.loads(batch["profile_snapshot_json"]))
            low, high = profile.temperature.allowed_target_f
            ranges.append((profile.id, float(low), float(high)))
        target_ok = (
            check_target(
                row["target_f"],
                row["hysteresis_f"],
                global_low=self.config.control.target_min_f,
                global_high=self.config.control.target_max_f,
                hysteresis_low=self.config.control.hysteresis_min_f,
                hysteresis_high=self.config.control.hysteresis_max_f,
                profile_ranges=ranges,
            )
            is None
        )
        cutoff = self.config.safety.cutoff_f
        for batch in active:
            tighter = Profile.model_validate(json.loads(batch["profile_snapshot_json"])).safety.cutoff_f
            if tighter is not None:
                cutoff = min(cutoff, tighter)
        limits = SafetyLimits(
            cutoff_f=cutoff,
            cutoff_clear_f=min(self.config.safety.cutoff_clear_f, cutoff - 2.0),
            max_on_s=self.config.safety.max_on_minutes * 60,
            rest_s=self.config.safety.rest_minutes * 60,
        )
        decision = evaluate_safety(
            SafetyInput(
                now_mono=self.clock.monotonic(),
                probes=views,
                heater_on=state.commanded_on,
                on_since_mono=state.on_since,
                rest_until_mono=state.rest_until,
                cutoff_latched=state.cutoff_latched,
                cutoff_below_since_mono=state.cutoff_below_since,
                target_in_range=target_ok,
                fresh=state.have_fresh,
                ambient_fault_disables_heat=self.config.safety.ambient_fault_disables_heat,
            ),
            limits,
        )
        state.cutoff_latched = decision.cutoff_latched
        state.cutoff_below_since = decision.cutoff_below_since_mono
        state.rest_until = decision.rest_until_mono
        for alert_type, severity in decision.alerts:
            self._raise(zone_id, None, None, alert_type, severity, {"reasons": decision.reasons})
        # One heater per zone: heat until the warmest vessel reaches the target, so no vessel is overheated.
        raw_temp = max(temps) if temps else None
        allow_heat = bool(active) or row["mode"] == "test"
        picked = heat_tuning.pick_vessel(controlling)
        tune = heat_tuning.tuning_for(
            picked[0] if picked else None,
            picked[1] if picked else None,
            {k: v.model_dump() for k, v in self.config.control.tuning.items()},
        )
        tune = heat_tuning.Tuning(**{**tune.__dict__,
                                     "min_on_min": max(tune.min_on_min, zone_cfg.min_on_minutes),
                                     "min_off_min": max(tune.min_off_min, zone_cfg.min_off_minutes)})
        state.mode = tune.mode
        now_mono = self.clock.monotonic()
        if raw_temp is None:
            state.history.clear()
            control_temp = None
        else:
            state.history = (state.history + [raw_temp])[-5:]
            control_temp = heat_tuning.smooth(state.history, tune.smoothing)
            state.trend = [(t, v) for t, v in state.trend if now_mono - t <= 2 * FALLING_LOOKBACK_S]
            state.trend.append((now_mono, raw_temp))
        if control_temp is None or decision.force_off or not allow_heat:
            desired = False
            state.window_start = None
        elif tune.mode == "proportional":
            desired = self._proportional(state, tune, control_temp, row["target_f"], picked, now_mono)
        else:
            want = heat_tuning.onoff_desired(control_temp, row["target_f"], tune, state.commanded_on)
            desired = evaluate_thermostat(
                temp_f=(row["target_f"] - 10.0) if want else (row["target_f"] + 10.0),
                target_f=row["target_f"],
                hysteresis_f=row["hysteresis_f"],
                currently_on=state.commanded_on,
                on_since_mono=state.on_since,
                off_since_mono=state.off_since,
                now_mono=now_mono,
                min_on_s=tune.min_on_min * 60,
                min_off_s=tune.min_off_min * 60,
                force_off=False,
                allow_heat=True,
            )
        self._apply(zone_id, desired)
        alert_temp = max(alert_temps) if alert_temps else None
        self._pressure(active, alert_temp, row["target_f"], state)
        reached = self._track_target_reached(active, row["target_f"])
        self._track_below_target(zone_id, state, alert_temp, row["target_f"], allow_heat, reached)
        self._track_out_of_range(zone_id, state, alert_temp, ranges, reached)
        self._track_heater_stuck(zone_id, state, alert_temp)
        self._settle_zone_alerts(zone_id, state, decision)

    def _proportional(self, state: ZoneRuntime, tune, temp_f: float, target_f: float, picked, now: float) -> bool:
        """Time-proportioning: one burst at the start of each window, sized by how far below target."""
        window_s = tune.window_min * 60
        key = (picked[0] if picked else None, float(target_f))
        if state.window_start is None or now - state.window_start >= window_s or state.window_key != key:
            if state.commanded_on and state.on_since is not None and now - state.on_since < tune.min_on_min * 60:
                return True
            if (not state.commanded_on and state.off_since is not None
                    and now - state.off_since < tune.min_off_min * 60):
                return False
            state.window_start = now
            state.window_on_s = heat_tuning.burst_seconds(temp_f, target_f, tune)
            state.window_key = key
        if temp_f >= target_f + tune.hot_cut_f:
            state.window_on_s = min(state.window_on_s, now - state.window_start)  # end this burst now
            return False
        return now - state.window_start < state.window_on_s

    def _apply(self, zone_id: str, desired: bool) -> None:
        heater = self.hardware.heaters.get(zone_id)
        if heater is None:
            return
        state = self.runtime.zones[zone_id]
        now = self.clock.monotonic()
        changed = desired != state.commanded_on
        if changed and not self._set_heater(zone_id, desired, now):
            return
        if state.commanded_on:
            self._arm_countdown(zone_id, now, force=changed)
        try:
            reported = heater.read_state()
        except Exception:
            reported = None
        if reported is None:
            state.unreachable_streak += 1
            self._note_unreachable(zone_id, state)
            return
        if reported != state.commanded_on:
            if not self._set_heater(zone_id, state.commanded_on, now):
                return
            if state.commanded_on:
                self._arm_countdown(zone_id, now, force=True)
            try:
                reported = heater.read_state()
            except Exception:
                reported = None
            if reported != state.commanded_on:
                severity = "critical" if reported is True and not state.commanded_on else "action"
                state.mismatch = True
                self._raise(zone_id, None, None, "heater_state_mismatch", severity, {"reported_on": reported})
                return
        state.unreachable_streak = 0
        state.mismatch = False
        self._check_countdown(zone_id)

    def _set_heater(self, zone_id: str, on: bool, now: float) -> bool:
        heater = self.hardware.heaters[zone_id]
        state = self.runtime.zones[zone_id]
        try:
            heater.set(on)
        except ActuatorUnreachable:
            state.unreachable_streak += 1
            self._note_unreachable(zone_id, state)
            return False
        if on != state.commanded_on:
            state.commanded_on = on
            if on:
                state.on_since = now
                state.off_since = None
            else:
                state.off_since = now
                state.on_since = None
        if not on:
            state.countdown_armed_mono = None
            state.countdown_armed_wall = None
            state.countdown_failed = False
        return True

    def _arm_countdown(self, zone_id: str, now: float, *, force: bool) -> None:
        """Re-arm the plug's hardware off-timer every control cycle while heating."""
        heater = self.hardware.heaters.get(zone_id)
        if heater is None or not heater.supports_countdown():
            return
        state = self.runtime.zones[zone_id]
        try:
            acked = heater.arm_countdown(cutoff.COUNTDOWN_ARM_S)
        except Exception as exc:
            log.warning("countdown arm failed for %s", zone_id, exc_info=True)
            state.countdown_failed = True
            try:
                self._raise(zone_id, None, None, "countdown_arm_failed", "action", {"error": str(exc)})
            except Exception:
                log.exception("could not record countdown_arm_failed")
            return
        state.countdown_failed = False
        if acked is not False:
            state.countdown_armed_mono = now
            state.countdown_armed_wall = self.clock.now()

    def _check_countdown(self, zone_id: str) -> None:
        """Self-check: while heating, the plug must have acknowledged an arm recently, and if the
        plug reports its countdown (DP 11) it must be nonzero. Otherwise warn and push."""
        heater = self.hardware.heaters.get(zone_id)
        if heater is None or not heater.supports_countdown():
            return
        state = self.runtime.zones[zone_id]
        now = self.clock.monotonic()
        unarmed = False
        reported = getattr(heater, "last_countdown", None)
        if state.commanded_on:
            ref = state.countdown_armed_mono if state.countdown_armed_mono is not None else state.on_since
            if ref is not None and now - ref > cutoff.UNARMED_GRACE_S and (
                state.countdown_armed_mono is None or now - state.countdown_armed_mono > cutoff.UNARMED_GRACE_S
            ):
                unarmed = True
            if reported == 0:
                unarmed = True
        if unarmed and not state.countdown_unarmed:
            detail = {"reported_countdown_s": reported}
            self._raise(zone_id, None, None, "countdown_not_armed", "warning", detail)
            self.notifier.notify("countdown_not_armed", "warning", self._alert_title(None, zone_id),
                                 alert_sentence("countdown_not_armed", detail))
        state.countdown_unarmed = unarmed
        payload = {
            "on": state.commanded_on,
            "armed_at": None if state.countdown_armed_wall is None or not state.commanded_on
            else isoformat(state.countdown_armed_wall),
            "seconds": cutoff.COUNTDOWN_ARM_S,
            "reported_s": reported,
            "unarmed": unarmed,
        }
        last = state.countdown_saved
        if last is None or last[1] != (payload["on"], unarmed) or now - last[0] >= cutoff.PERSIST_EVERY_S:
            cutoff.save(self.conn, zone_id, self.clock.now(), payload)
            state.countdown_saved = (now, (payload["on"], unarmed))

    def _readings_are_fresh(self, zone_id: str, now: float) -> bool:
        roms = [
            vessel.probe_rom_id
            for vessel in self._vessels()
            if vessel.temp_zone == zone_id and vessel.enabled and vessel.probe_rom_id
        ]
        if self.config.safety.ambient_fault_disables_heat:
            roms.append(self.config.one_wire.ambient_probe)
        if not roms:
            return False
        for rom in roms:
            health = self.runtime.probes.get(rom)
            if health is None or health.last_good_mono is None:
                return False
            if now - health.last_good_mono > FRESH_READING_MAX_S:
                return False
        return True

    def _fail_closed(self, exc: BaseException) -> None:
        for zone_id, heater in self.hardware.heaters.items():
            state = self.runtime.zones.setdefault(zone_id, ZoneRuntime())
            try:
                heater.set(False)
            except Exception:
                log.warning("heater %s could not be forced off after a tick error", zone_id, exc_info=True)
            state.commanded_on = False
            state.on_since = None
            state.off_since = self.clock.monotonic()
            state.countdown_armed_mono = None
        detail = {"error": str(exc) or type(exc).__name__}
        try:
            self._raise("control", None, None, "control_fault", "critical", detail)
            self.conn.commit()
        except Exception:
            log.exception("could not record control_fault")
            try:
                self.notifier.notify(
                    "control_fault",
                    "critical",
                    self._alert_title(None, None),
                    alert_sentence("control_fault", detail),
                )
            except Exception:
                log.exception("could not send control_fault alert")

    def _note_unreachable(self, zone_id: str, state: ZoneRuntime) -> None:
        if state.unreachable_streak < 3:
            return
        severity = "critical" if state.commanded_on else "action"
        self._raise(zone_id, None, None, "heater_unreachable", severity, {"streak": state.unreachable_streak})

    def _pressure(
        self, batches: list[sqlite3.Row], temp_f: float | None, target_f: float, state: ZoneRuntime | None = None
    ) -> None:
        """Bottled soda running warm builds pressure. Quiet for a grace period after a stage change
        (the vessel is still settling), not raised while it is already cooling with the mat off, and
        cleared only once it is PRESSURE_CLEAR_BELOW_F under the limit so it does not flicker."""
        now = self.clock.now()
        grace_s = self.config.control.stage_change_grace_minutes * 60
        cooling = state is not None and not state.commanded_on and self._falling(state)
        for batch in batches:
            key = f"pressure_risk:batch:{batch['id']}"
            if temp_f is None or batch["stage"] != "in_bottle":
                resolve_alert(self.conn, self.clock, key)
                continue
            profile = Profile.model_validate(json.loads(batch["profile_snapshot_json"]))
            limit = target_f + profile.alerts.pressure_risk_margin_f
            is_open = self.conn.execute(
                "SELECT 1 FROM ALERT WHERE dedupe_key = ? AND status = 'open'", (key,)
            ).fetchone() is not None
            if temp_f < limit - PRESSURE_CLEAR_BELOW_F:
                resolve_alert(self.conn, self.clock, key)
                continue
            if is_open or temp_f <= limit:
                continue  # inside the band: leave it as it is
            started = batch["stage_started_at"]
            if started and now.timestamp() - parse_iso(started).timestamp() < grace_s:
                continue
            if cooling:
                continue
            self._raise(
                batch["vessel_id"],
                batch["vessel_id"],
                batch["id"],
                "pressure_risk",
                "action",
                {"temp_f": temp_f, "target_f": target_f},
            )

    def _falling(self, state: ZoneRuntime) -> bool:
        if len(state.trend) < 2:
            return False
        now_t, now_v = state.trend[-1]
        older = [v for t, v in state.trend if now_t - t >= FALLING_LOOKBACK_S]
        if not older:
            return False
        return now_v <= older[-1] - FALLING_MIN_DROP_F

    def _raise(
        self,
        zone_or_vessel: str,
        vessel_id: str | None,
        batch_id: int | None,
        alert_type: str,
        severity: str,
        detail: dict,
    ) -> None:
        key_scope = f"batch:{batch_id}" if batch_id is not None else f"zone:{zone_or_vessel}"
        outcome = raise_alert(
            self.conn,
            self.clock,
            dedupe_key=f"{alert_type}:{key_scope}",
            severity=severity,
            alert_type=alert_type,
            detail=detail,
            vessel_id=vessel_id,
            batch_id=batch_id,
        )
        if outcome in {"opened", "escalated"} and severity in {"action", "critical"}:
            self.notifier.notify(
                alert_type,
                severity,
                self._alert_title(vessel_id, zone_or_vessel),
                alert_sentence(alert_type, detail),
            )

    def _apply_ramps(self) -> None:
        """Timed temperature steps from the profile (for example a saison ramp). Heat-only; every
        step goes through the same range checks as a manual change, and only when the batch has the
        zone to itself. Each step is applied once and logged in the audit log."""
        rows = self.conn.execute(
            "SELECT * FROM BATCH WHERE ended_at IS NULL AND stage_started_at IS NOT NULL"
        ).fetchall()
        if not rows:
            return
        ctx = CommandContext(
            self.conn, self.clock, self.config, self.profiles, self.hardware.heaters, self.runtime.zones
        )
        now = self.clock.now()
        for batch in rows:
            profile = Profile.model_validate(json.loads(batch["profile_snapshot_json"]))
            spec = next((item for item in profile.stages if item.id == batch["stage"]), None)
            if spec is None or spec.ramp is None:
                continue
            due = parse_iso(batch["stage_started_at"]).timestamp() + duration_seconds(spec.ramp.after)
            if now.timestamp() < due:
                continue
            why = f"ramp:{batch['stage']}:{batch['stage_started_at']}"
            done = self.conn.execute(
                "SELECT 1 FROM AUDIT_LOG WHERE action = 'auto_target' AND target = ?",
                (f"batch:{batch['id']}:{why}",),
            ).fetchone()
            if done is None and apply_auto_target(ctx, batch, spec.ramp.target_f, why) == "applied":
                self.notifier.notify(
                    "auto_target",
                    "info",
                    batch["name"],
                    f"Stepped the target to {spec.ramp.target_f:g}°F as the profile plans.",
                )
        self.conn.commit()

    def _check_probe_silence(self) -> None:
        """Push when a vessel probe has given no valid reading (missing, read error, bad checksum or
        an impossible jump) for probe_silent_s, and once more when it comes back. The heater is
        already held off by the safety layer (sensor_fault) while the probe is bad."""
        now = self.clock.monotonic()
        limit = self.config.control.probe_silent_s
        for vessel in self._vessels():
            if not vessel.enabled or not vessel.probe_rom_id:
                continue
            health = self.runtime.probes.get(vessel.probe_rom_id)
            if health is None:
                continue
            first = self.runtime.probe_first_seen.setdefault(vessel.probe_rom_id, now)
            key = f"probe_silent:zone:{vessel.id}"
            if health.temp_f is not None:
                if vessel.id in self.runtime.probe_silent_alerted:
                    self.runtime.probe_silent_alerted.discard(vessel.id)
                    resolve_alert(self.conn, self.clock, key)
                    self.notifier.notify(
                        "probe_recovered",
                        "info",
                        self._alert_title(vessel.id, vessel.id),
                        f"The {vessel.name} probe is reading again ({health.temp_f:.1f}°F).",
                    )
                continue
            last = health.last_good_mono if health.last_good_mono is not None else first
            if now - last >= limit and vessel.id not in self.runtime.probe_silent_alerted:
                self.runtime.probe_silent_alerted.add(vessel.id)
                minutes = max(1, round((now - last) / 60))
                self._raise(
                    vessel.id,
                    vessel.id,
                    None,
                    "probe_silent",
                    "action",
                    {
                        "text": f"No valid reading from the {vessel.name} probe for {minutes} min "
                        f"({health.reject_reason or 'no data'}). The heat mat is held off. "
                        "Check the probe plug and the wiring on the breadboard."
                    },
                )

    def _track_heater_stuck(self, zone_id: str, state: ZoneRuntime, control_temp: float | None) -> None:
        """Heater on for heater_stuck_minutes but the vessel warmed less than heater_stuck_min_rise_f:
        the jug may have slid off the mat or the plug is not switching. Rate-limited."""
        cfg = self.config.control
        now = self.clock.monotonic()
        if not state.commanded_on or control_temp is None:
            state.stuck_window_start = None
            state.stuck_window_temp = None
            return
        if state.stuck_window_start is None:
            state.stuck_window_start = now
            state.stuck_window_temp = control_temp
            return
        if now - state.stuck_window_start < cfg.heater_stuck_minutes * 60:
            return
        rise = control_temp - (state.stuck_window_temp or control_temp)
        if rise < cfg.heater_stuck_min_rise_f:
            recent = state.stuck_last_alert is not None and (
                now - state.stuck_last_alert < cfg.heater_stuck_repeat_minutes * 60
            )
            if not recent:
                state.stuck_last_alert = now
                minutes = round((now - state.stuck_window_start) / 60)
                self.notifier.notify(
                    "heater_stuck",
                    "action",
                    self._alert_title(None, zone_id),
                    f"The heat mat has been on for {minutes} min but the temperature rose only "
                    f"{rise:+.1f}°F (now {control_temp:.1f}°F). Check that the jug is sitting on the mat "
                    "and the smart plug is actually switching on.",
                )
                self.conn.execute(
                    """
                    INSERT INTO EVENT (ts, type, severity, actor, detail_json)
                    VALUES (?, 'heater_stuck', 'action', 'control', ?)
                    """,
                    (isoformat(self.clock.now()), json.dumps({"zone_id": zone_id, "rise_f": rise})),
                )
        # Slide the window so the next check covers the next stretch.
        state.stuck_window_start = now
        state.stuck_window_temp = control_temp

    def _track_target_reached(self, active: list[sqlite3.Row], target_f: float) -> bool:
        """Announce once when a batch first gets within TARGET_REACHED_TOLERANCE_F of its target, and
        once more after each target change (for example a timed temperature step). State lives on the
        BATCH row so a restart does not repeat it. Returns True when every batch here has reached a
        target at least once (or there are no batches), which arms the cold excursion alerts."""
        if not active:
            return True
        now_iso = isoformat(self.clock.now())
        vessels = {vessel.id: vessel for vessel in self._vessels()}
        all_reached = True
        for batch in active:
            armed_f = batch["target_armed_f"]
            armed_at = batch["target_armed_at"] or batch["started_at"]
            if armed_f is None or abs(armed_f - target_f) > 1e-6:
                if armed_f is not None:
                    armed_at = now_iso
                self.conn.execute(
                    "UPDATE BATCH SET target_armed_f = ?, target_armed_at = ? WHERE id = ?",
                    (target_f, armed_at, batch["id"]),
                )
            previous = batch["target_reached_f"]
            if previous is not None and abs(previous - target_f) <= 1e-6:
                continue
            vessel = vessels.get(batch["vessel_id"])
            if self._settling(batch["vessel_id"]):
                if previous is None:
                    all_reached = False
                continue
            rom = vessel.probe_rom_id if vessel else None
            health = self.runtime.probes.get(rom) if rom else None
            temp = health.temp_f if health is not None and not health.faulted else None
            if temp is None or abs(temp - target_f) > TARGET_REACHED_TOLERANCE_F:
                if previous is None:
                    all_reached = False
                continue
            self.conn.execute(
                "UPDATE BATCH SET target_reached_f = ?, target_reached_at = ? WHERE id = ?",
                (target_f, now_iso, batch["id"]),
            )
            took = _human_duration(self.clock.now().timestamp() - parse_iso(armed_at).timestamp())
            vessel_name = vessel.name if vessel else batch["vessel_id"]
            from_above = temp > target_f
            verb = "settled at" if from_above else "reached"
            body = (
                f"{batch['name']} in {vessel_name} {verb} its {target_f:g}°F target "
                f"(reading {temp:.1f}°F) after {took}."
                + ("" if previous is None else f" New target after a change from {previous:g}°F.")
            )
            self.conn.execute(
                """
                INSERT INTO EVENT (ts, type, severity, actor, detail_json)
                VALUES (?, 'target_reached', 'info', 'control', ?)
                """,
                (now_iso, json.dumps({"batch_id": batch["id"], "target_f": target_f, "temp_f": temp, "from_above": from_above,
                            "text": body})),
            )
            title = f"{batch['name']}: settled at target" if from_above else f"{batch['name']}: at target"
            self.notifier.notify("target_reached", "info", title, body)
        return all_reached

    def _track_out_of_range(
        self,
        zone_id: str,
        state: ZoneRuntime,
        control_temp: float | None,
        ranges: list[tuple[str, float, float]],
        reached: bool = True,
    ) -> None:
        """Alert when the vessel sits outside what its profile allows for a while. The rig only heats,
        so a warm excursion usually means the room is too warm (move the cooler somewhere colder)."""
        if control_temp is None or not ranges:
            state.out_of_range_since = None
            return
        low = max(item[1] for item in ranges)
        high = min(item[2] for item in ranges)
        margin = self.config.control.over_target_margin_f
        # Too warm is always armed. Too cold only counts once the batch has first reached its target,
        # so a cold start that is still warming up does not alert.
        outside = control_temp > high + margin or (reached and control_temp < low - margin)
        if not outside:
            state.out_of_range_since = None
            resolve_alert(self.conn, self.clock, f"temp_out_of_range:zone:{zone_id}")
            return
        now = self.clock.monotonic()
        if state.out_of_range_since is None:
            state.out_of_range_since = now
        if now - state.out_of_range_since >= self.config.control.over_target_minutes * 60:
            detail = {"temp_f": control_temp, "low_f": low, "high_f": high}
            self._raise(zone_id, None, None, "temp_out_of_range", "action", detail)

    def _track_below_target(
        self,
        zone_id: str,
        state: ZoneRuntime,
        control_temp: float | None,
        target_f: float,
        allow_heat: bool,
        reached: bool = True,
    ) -> None:
        cold = allow_heat and control_temp is not None and control_temp < target_f - BELOW_TARGET_MARGIN_F
        if not cold:
            state.below_target_since = None
            return
        now = self.clock.monotonic()
        if state.below_target_since is None:
            state.below_target_since = now
        elapsed = now - state.below_target_since
        detail = {"temp_f": control_temp, "target_f": target_f}
        if elapsed >= BELOW_TARGET_PUSH_AFTER_S:
            # Still pushed while warming up: 15 h without getting close means the heat is not keeping up.
            self._raise(zone_id, None, None, "temp_below_target", "action", detail)
        elif elapsed >= BELOW_TARGET_AFTER_S and reached:
            self._raise(zone_id, None, None, "temp_below_target", "warning", detail)

    def _settle_zone_alerts(self, zone_id: str, state: ZoneRuntime, decision) -> None:
        active = {alert_type for alert_type, _severity in decision.alerts}
        if state.cutoff_latched:
            active.add("overtemp_cutoff")
        if state.rest_until is not None and self.clock.monotonic() < state.rest_until:
            active.add("max_on_rest")
        if state.unreachable_streak >= 3:
            active.add("heater_unreachable")
        if state.mismatch:
            active.add("heater_state_mismatch")
        if state.countdown_failed:
            active.add("countdown_arm_failed")
        if state.countdown_unarmed:
            active.add("countdown_not_armed")
        if state.below_target_since is not None:
            if self.clock.monotonic() - state.below_target_since >= BELOW_TARGET_AFTER_S:
                active.add("temp_below_target")
        if state.out_of_range_since is not None:
            active.add("temp_out_of_range")
        for alert_type in _ZONE_ALERTS:
            if alert_type not in active:
                resolve_alert(self.conn, self.clock, f"{alert_type}:zone:{zone_id}")

    def _alert_title(self, vessel_id: str | None, zone_id: str | None) -> str:
        if vessel_id:
            row = self.conn.execute("SELECT name FROM VESSEL WHERE id = ?", (vessel_id,)).fetchone()
            if row is not None:
                return row["name"]
        if zone_id and zone_id != "control":
            rows = self.conn.execute(
                "SELECT name FROM VESSEL WHERE enabled = 1 AND temp_zone_id = ? ORDER BY id",
                (zone_id,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT name FROM VESSEL WHERE enabled = 1 ORDER BY id").fetchall()
        if rows:
            return ", ".join(row["name"] for row in rows)
        return self.config.site.name

    def _notify_interrupted_restart(self) -> None:
        previous = self.conn.execute(
            """
            SELECT type FROM EVENT
            WHERE type IN ('service_started', 'service_stopped')
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        if take_marker(self.conn, self.clock.now()):
            # Restarted on purpose (fermentd-ctl planned-restart): log it, no alert, no push, even if
            # the old process was killed before it could log its stop.
            self.conn.execute(
                """
                INSERT INTO EVENT (ts, type, severity, actor, detail_json)
                VALUES (?, 'planned_restart', 'info', 'control', ?)
                """,
                (isoformat(self.clock.now()), json.dumps({"clean_stop": previous is not None and previous["type"] == "service_stopped"})),
            )
            return
        if previous is None or previous["type"] != "service_started":
            return
        resolve_alert(self.conn, self.clock, "service_interrupted:zone:control")
        self._raise("control", None, None, "service_interrupted", "critical", {})

    def _write_readings(self) -> None:
        ts = isoformat(self.clock.now())
        ambient = self.runtime.probes.get(self.config.one_wire.ambient_probe, ProbeHealth())
        for vessel in self._vessels():
            if not vessel.enabled or not vessel.probe_rom_id or not vessel.temp_zone:
                continue
            health = self.runtime.probes.get(vessel.probe_rom_id, ProbeHealth())
            zone_state = self.runtime.zones.get(vessel.temp_zone, ZoneRuntime())
            batch = self.conn.execute(
                "SELECT id FROM BATCH WHERE vessel_id = ? AND ended_at IS NULL",
                (vessel.id,),
            ).fetchone()
            flags = 0
            if health.faulted:
                flags |= FLAG_PROBE_FAULT
            if zone_state.cutoff_latched or zone_state.rest_until is not None:
                flags |= FLAG_SAFETY
            if self._settling(vessel.id):
                flags |= FLAG_SETTLING
            self.conn.execute(
                """
                INSERT OR IGNORE INTO READING (
                    ts, vessel_id, batch_id, weight_g, vessel_temp_f, ambient_temp_f, heater_on, flags
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?)
                """,
                (
                    ts,
                    vessel.id,
                    None if batch is None else batch["id"],
                    health.temp_f,
                    ambient.temp_f,
                    1 if zone_state.commanded_on else 0,
                    flags,
                ),
            )

    def _maybe_digest(self) -> None:
        if not self.config.digest.enabled:
            return
        digest_id, slot, late = digest_slot(
            self.clock.now(),
            self.config.site.timezone,
            self.config.digest.weekday,
            self.config.digest.time,
        )
        if digest_id in sent_digest_ids(self.conn):
            return
        summary = build_digest(
            self.conn,
            period_end=slot,
            digest_id=digest_id,
            late=late,
            as_of=self.clock.now(),
        )
        record_digest(self.conn, summary, isoformat(self.clock.now()), "control")
        self.notifier.notify("digest", "info", digest_id, _digest_text(summary))

    def _sync_hardware_rows(self) -> None:
        for zone in self.config.temp_zones:
            self.conn.execute(
                """
                INSERT INTO TEMP_ZONE (
                    id, name, capability, actuator_driver, device_ref, target_f, hysteresis_f, mode, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(id) DO UPDATE SET
                    name = CASE WHEN TEMP_ZONE.user_named THEN TEMP_ZONE.name ELSE excluded.name END,
                    capability = excluded.capability,
                    actuator_driver = excluded.actuator_driver,
                    device_ref = excluded.device_ref,
                    mode = excluded.mode,
                    enabled = 1
                """,
                (
                    zone.id,
                    zone.name,
                    zone.capability,
                    zone.heater.driver,
                    zone.heater.device_id_ref,
                    zone.default_target_f,
                    zone.default_hysteresis_f,
                    zone.mode,
                ),
            )
        ids: list[str] = []
        for vessel in self.config.vessels:
            ids.append(vessel.id)
            hx = vessel.scale if vessel.scale is not None and vessel.scale.driver == "hx711" else None
            dout = None if hx is None else hx.dout_gpio
            sck = None if hx is None else hx.sck_gpio
            self.conn.execute(
                """
                INSERT INTO VESSEL (
                    id, name, vessel_type, capacity_l, hx711_dout_gpio, hx711_sck_gpio,
                    probe_rom_id, temp_zone_id, enabled, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'config')
                ON CONFLICT(id) DO UPDATE SET
                    name = CASE WHEN VESSEL.user_edited THEN VESSEL.name ELSE excluded.name END,
                    vessel_type = CASE WHEN VESSEL.user_edited THEN VESSEL.vessel_type ELSE excluded.vessel_type END,
                    capacity_l = CASE WHEN VESSEL.user_edited THEN VESSEL.capacity_l ELSE excluded.capacity_l END,
                    probe_rom_id = CASE WHEN VESSEL.user_edited THEN VESSEL.probe_rom_id ELSE excluded.probe_rom_id END,
                    temp_zone_id = CASE WHEN VESSEL.user_edited THEN VESSEL.temp_zone_id ELSE excluded.temp_zone_id END,
                    enabled = excluded.enabled,
                    source = 'config'
                """,
                (
                    vessel.id,
                    vessel.name,
                    vessel.vessel_type,
                    vessel.capacity_l,
                    dout,
                    sck,
                    vessel.probe_rom_id,
                    vessel.temp_zone,
                    1 if vessel.enabled else 0,
                ),
            )
        if ids:
            marks = ",".join("?" for _ in ids)
            self.conn.execute(
                f"UPDATE VESSEL SET enabled = 0 WHERE source = 'config' AND id NOT IN ({marks})",
                ids,
            )


def _human_duration(seconds: float) -> str:
    minutes = max(0, int(round(seconds / 60)))
    if minutes < 60:
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    if hours < 48:
        return f"{hours} h {minutes} min" if minutes else f"{hours} h"
    days, hours = divmod(hours, 24)
    return f"{days} d {hours} h"


def _digest_text(summary: dict) -> str:
    lines = [f"fermentd weekly digest {summary['digest_id']}"]
    if summary["late"]:
        lines[0] += " (late)"
    safety = summary["health"]["safety_events"]
    if safety:
        parts = [f"{count} {name.replace('_', ' ')}" for name, count in sorted(safety.items())]
        lines.append("Safety events: " + ", ".join(parts) + ".")
    else:
        lines.append("No safety events this week.")
    if not summary["batches"]:
        lines.append("No active batches.")
    for batch in summary["batches"]:
        lines.append(
            f"{batch['name']} ({batch['profile_id']}, {batch['vessel']}), {batch['stage']}, "
            f"{batch['elapsed_hours_in_stage']} h in this stage"
        )
        if batch["temp_mean_f"] is None:
            lines.append("No temperature readings this week.")
        else:
            lines.append(
                f"Temperature {format_temp(batch['temp_mean_f'])} average "
                f"({format_temp(batch['temp_min_f'])} to {format_temp(batch['temp_max_f'])})."
            )
        action = batch.get("next_action")
        if action:
            lines.append(f"Next: {action['text']} ({format_local(action['due_at'])})")
        else:
            lines.append("Next: nothing scheduled.")
    if summary["open_alerts"]:
        lines.append("Open alerts:")
        for alert in summary["open_alerts"]:
            lines.append(f"- {alert['text']}")
    else:
        lines.append("Open alerts: none.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fermentd-control")
    parser.add_argument("--config", default="config/fermentd.example.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(Path(args.config))
    conn = connect(Path(config.database.path))
    migrate(conn)
    secrets = load_secrets(Path(config.secrets))
    hardware = build_hardware(config, secrets)
    clock = SystemClock()
    notifier = build_notifier(
        secrets,
        database=Path(config.database.path),
        clock=clock,
        click=config.web.url,
    )
    service = ControlService(
        config,
        conn,
        clock,
        hardware,
        load_profiles(Path(config.profiles.user_dir)),
        notifier,
    )
    stopping = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    service.startup()
    start_delivery(notifier)
    try:
        while not stopping:
            started = time.monotonic()
            service.guarded_tick()
            remaining = 10.0 - (time.monotonic() - started)
            while remaining > 0 and not stopping:
                time.sleep(min(1.0, remaining))
                service.poll_pending_commands()
                remaining = 10.0 - (time.monotonic() - started)
    finally:
        service.stop()
        finish_delivery(notifier)
