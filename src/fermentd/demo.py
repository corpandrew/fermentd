"""Accelerated ginger ale batch. Day 0 bottling is already done; the controller starts at in_bottle."""

from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

from fermentd.clock import ManualClock, SystemClock
from fermentd.config import load_config, load_secrets
from fermentd.control.service import ControlService
from fermentd.db.connection import connect
from fermentd.db.migrate import migrate
from fermentd.drivers.factory import build_hardware
from fermentd.drivers.sim import SimHeater, ThermalModel
from fermentd.notify.fanout import build_notifier, finish_delivery, start_delivery
from fermentd.profiles.loader import load_profiles

# 4 F/h equilibrates at the 72 F setpoint, so the heater would never turn off.
# 8 F/h crosses 72 F and cycles inside the hysteresis band, under the 4 h cap.
HEATER_GAIN_F_PER_HOUR = 8.0
ROOM_F = 64.0
TAU_S = 2 * 3600
STEP_S = 60
CARBONATION_MINUTES = 36 * 60


def run_ginger_ale(service: ControlService, clock: ManualClock, pace_s: float = 0.0) -> dict:
    hardware = service.hardware
    heater = hardware.heaters["zone1"]
    assert isinstance(heater, SimHeater)
    bank = hardware.sim_probes
    assert bank is not None
    vessel_rom = service.config.vessels[0].probe_rom_id
    ambient_rom = service.config.one_wire.ambient_probe
    assert vessel_rom is not None
    model = ThermalModel(ROOM_F, ROOM_F, TAU_S, HEATER_GAIN_F_PER_HOUR)
    bank.set_temp(vessel_rom, ROOM_F)
    bank.set_temp(ambient_rom, ROOM_F)
    service.startup()
    service.submit(
        "demo",
        "start_batch",
        {"vessel_id": service.config.vessels[0].id, "name": "Ginger ale", "profile_id": "soda_ginger_ale"},
        "demo-start",
    )
    service.tick()
    longest_on = 0
    current_on = 0
    cutoff = False
    for _minute in range(CARBONATION_MINUTES):
        model.step(STEP_S, heater.on)
        bank.set_temp(vessel_rom, model.temp_f)
        bank.set_temp(ambient_rom, ROOM_F)
        clock.advance(STEP_S)
        service.tick()
        if heater.on:
            current_on += 1
            longest_on = max(longest_on, current_on)
        else:
            current_on = 0
        if service.runtime.zones["zone1"].cutoff_latched:
            cutoff = True
        if pace_s and _minute % 60 == 0:
            hour = _minute // 60
            state = "ON" if heater.on else "off"
            print(f"sim hour {hour}: {model.temp_f:.1f} F, heater {state}", flush=True)
        if pace_s:
            time.sleep(pace_s)
    reminder = service.conn.execute(
        "SELECT id, status FROM REMINDER WHERE reminder_key = 'refrigerate_now'"
    ).fetchone()
    service.submit("demo", "complete_reminder", {"reminder_id": reminder["id"]}, "demo-fridge")
    service.submit(
        "demo",
        "set_stage",
        {"vessel_id": service.config.vessels[0].id, "stage": "refrigerated"},
        "demo-stage",
    )
    service.tick()
    sunday = datetime(2026, 10, 18, 13, 0, tzinfo=UTC)
    clock.advance((sunday - clock.now()).total_seconds())
    service.tick()
    service.tick()
    digest_rows = service.conn.execute("SELECT digest_id FROM DIGEST_LOG WHERE digest_id = '2026-W42'").fetchall()
    batch = service.conn.execute("SELECT stage, name FROM BATCH").fetchone()
    return {
        "stage": batch["stage"],
        "name": batch["name"],
        "longest_on_minutes": longest_on,
        "cutoff": cutoff,
        "final_temp_f": model.temp_f,
        "w42_digests": len(digest_rows),
        "refrigerate_status": service.conn.execute(
            "SELECT status FROM REMINDER WHERE reminder_key = 'refrigerate_now'"
        ).fetchone()["status"],
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fermentd-demo")
    parser.add_argument("--config", default="config/fermentd.example.yaml")
    parser.add_argument(
        "--pace",
        type=float,
        default=0.0,
        help="Real seconds to pause after each simulated minute. 0 finishes immediately.",
    )
    args = parser.parse_args(argv)
    config_path = Path(args.config)
    config = load_config(config_path)
    data = yaml.safe_load(config_path.read_text())
    db_path = Path(data["database"]["path"])
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    conn = connect(db_path)
    migrate(conn)
    clock = ManualClock(datetime(2026, 10, 12, 18, 0, tzinfo=UTC))
    secrets = load_secrets(Path(config.secrets))
    hardware = build_hardware(config, secrets)
    notifier = build_notifier(
        secrets,
        database=db_path,
        clock=SystemClock(),
        click=config.web.url,
    )
    service = ControlService(
        config,
        conn,
        clock,
        hardware,
        load_profiles(Path(config.profiles.user_dir) if Path(config.profiles.user_dir).exists() else None),
        notifier,
    )
    start_delivery(notifier)
    try:
        result = run_ginger_ale(service, clock, pace_s=args.pace)
        print(
            f"{result['name']} finished in stage {result['stage']} at {result['final_temp_f']:.1f} F; "
            f"longest heater run {result['longest_on_minutes']} min; "
            f"week 2026-W42 digests {result['w42_digests']}"
        )
    finally:
        finish_delivery(notifier)
