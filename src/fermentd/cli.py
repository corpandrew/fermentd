"""fermentd-ctl: heaters-off, probe reads, and a local plug test."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from fermentd.config import load_actuator_secrets, load_config, load_secrets
from fermentd.drivers.base import ActuatorUnreachable
from fermentd.drivers.factory import build_hardware


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fermentd-ctl")
    parser.add_argument("--config", default="config/fermentd.example.yaml")
    sub = parser.add_subparsers(dest="command", required=True)
    heaters = sub.add_parser("heaters-off")
    heaters.add_argument("--all", action="store_true")
    sub.add_parser("probes")
    plug = sub.add_parser("plug-test")
    plug.add_argument("zone")
    for name in ("scale-read", "scale-tare", "scale-calibrate"):
        cmd = sub.add_parser(name, help="sent to the running controller, which owns the GPIO")
        cmd.add_argument("vessel")
        if name == "scale-calibrate":
            cmd.add_argument("--grams", type=float, required=True, help="known weight, e.g. 1000 for 1 L of water")
    direct = sub.add_parser("scale-test", help="read an HX711 directly (scale not enabled in the controller)")
    direct.add_argument("--dout", type=int, default=5)
    direct.add_argument("--sck", type=int, default=6)
    direct.add_argument("--count", type=int, default=5)
    planned = sub.add_parser(
        "planned-restart", help="mark the next restart as intentional (no alert), then restart the services"
    )
    planned.add_argument("--minutes", type=float, default=5, help="how long the marker stays valid")
    planned.add_argument("--marker-only", action="store_true", help="write the marker but do not restart")
    planned.add_argument(
        "--units", nargs="+", default=["fermentd-control", "fermentd-web", "fermentd-mcp"], help="systemd units"
    )
    pw = sub.add_parser("set-password", help="set the dashboard login password (stored as a scrypt hash)")
    pw.add_argument("--stdin", action="store_true", help="read the password from the first line of stdin")
    pw.add_argument("--secrets", help="secrets file to update (default: the one named in --config)")
    args = parser.parse_args(argv)
    if args.command == "set-password":
        return _set_password(args)
    if args.command == "scale-test":
        return _scale_test(args.dout, args.sck, args.count)
    config = load_config(Path(args.config))
    if args.command == "planned-restart":
        return _planned_restart(config, args)
    if args.command.startswith("scale-"):
        return _scale_command(config, args)
    secrets_path = Path(config.secrets)
    if args.command == "heaters-off":
        secrets = load_actuator_secrets(secrets_path)
    else:
        secrets = load_secrets(secrets_path)
    hardware = build_hardware(config, secrets)
    if args.command == "heaters-off":
        return _heaters_off(hardware)
    if args.command == "probes":
        return _probes(config, hardware)
    if args.command == "plug-test":
        return _plug_test(config, hardware, args.zone)
    return 2


def _set_password(args, stdin=None) -> int:
    import sys

    path = Path(args.secrets) if args.secrets else Path(load_config(Path(args.config)).secrets)
    if args.stdin:
        password = (stdin or sys.stdin).readline().rstrip("\r\n")
    else:
        import getpass

        password = getpass.getpass("New dashboard password: ")
        if getpass.getpass("Again: ") != password:
            print("passwords do not match")
            return 1
    if len(password) < 10:
        print("use at least 10 characters")
        return 1
    write_password_hash(path, password)
    print(f"dashboard password hash saved to {path}; restart fermentd-web to apply")
    return 0


def write_password_hash(path: Path, password: str) -> None:
    """Store web.password_hash in secrets.yaml (mode 600), keeping every other key."""
    import os

    import yaml

    from fermentd.config import Secrets
    from fermentd.web.auth import hash_password

    raw = (yaml.safe_load(path.read_text()) or {}) if path.exists() else {}
    if not isinstance(raw, dict):
        raise SystemExit(f"{path} must be a mapping")
    web = raw.get("web") or {}
    web["password_hash"] = hash_password(password)
    raw["web"] = web
    Secrets.model_validate(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write("# Managed partly by `fermentd-ctl set-password`; comments are not kept.\n")
        yaml.safe_dump(raw, fh, sort_keys=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _planned_restart(config, args, run=None) -> int:
    import subprocess
    from datetime import UTC, datetime

    from fermentd.control.planned import write_marker
    from fermentd.db.connection import connect

    conn = connect(Path(config.database.path))
    until = write_marker(conn, datetime.now(UTC), args.minutes, actor="planned-restart")
    conn.close()
    print(f"planned-restart marker set until {until}")
    if args.marker_only:
        return 0
    cmd = ["sudo", "systemctl", "restart", *args.units]
    print("running:", " ".join(cmd))
    return (run or subprocess.call)(cmd)


def _heaters_off(hardware) -> int:
    failed = False
    for zone_id, heater in hardware.heaters.items():
        try:
            heater.set(False)
            state = heater.read_state()
        except ActuatorUnreachable as exc:
            print(f"{zone_id}: unreachable ({exc})")
            failed = True
            continue
        print(f"{zone_id}: off (readback {state})")
        if state is True:
            failed = True
    return 1 if failed else 0


def _probes(config, hardware) -> int:
    roms = [config.one_wire.ambient_probe]
    roms.extend(vessel.probe_rom_id for vessel in config.vessels if vessel.probe_rom_id)
    for rom in roms:
        sample = hardware.probes.read(rom)
        if sample.reject_reason:
            print(f"{rom}: {sample.reject_reason}")
        else:
            print(f"{rom}: {sample.temp_f:.2f} F")
    return 0


def _plug_test(config, hardware, zone_id: str) -> int:
    heater = hardware.heaters.get(zone_id)
    if heater is None:
        print(f"no heater for {zone_id}")
        return 1
    pause = 1.0 if _driver(config, zone_id) == "tuya" else 0.0
    try:
        heater.set(True)
        if pause:
            time.sleep(pause)
        on_state = heater.read_state()
        heater.set(False)
        if pause:
            time.sleep(pause)
        off_state = heater.read_state()
    except ActuatorUnreachable as exc:
        print(f"{zone_id}: unreachable ({exc})")
        return 1
    print(f"{zone_id}: on readback {on_state}, off readback {off_state}")
    return 0 if on_state is True and off_state is False else 1


def _driver(config, zone_id: str) -> str:
    for zone in config.temp_zones:
        if zone.id == zone_id:
            return zone.heater.driver
    return ""


def _scale_command(config, args) -> int:
    import json

    from fermentd.clock import SystemClock
    from fermentd.control.commands import enqueue
    from fermentd.db.connection import connect
    from fermentd.db.migrate import migrate

    conn = connect(Path(config.database.path))
    migrate(conn)
    command = {"scale-read": "scale_read", "scale-tare": "scale_tare", "scale-calibrate": "scale_calibrate"}[
        args.command
    ]
    params: dict = {"vessel_id": args.vessel}
    if command == "scale_calibrate":
        params["grams"] = args.grams
    command_id = enqueue(
        conn,
        SystemClock(),
        actor="cli",
        command_type=command,
        params=params,
        idempotency_key=f"cli-{command}-{time.time_ns()}",
        ttl_s=60,
    )
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        row = conn.execute("SELECT status, result_json FROM COMMAND WHERE id = ?", (command_id,)).fetchone()
        if row["status"] != "pending":
            result = json.loads(row["result_json"] or "{}")
            if row["status"] == "done":
                print(", ".join(f"{k}: {v}" for k, v in result.items() if k != "ok"))
                return 0
            print(result.get("message") or row["status"])
            return 1
        time.sleep(0.5)
    print("The controller did not answer. Is fermentd-control running?")
    return 1


def _scale_test(dout: int, sck: int, count: int) -> int:
    from fermentd.drivers.base import ScaleUnavailable
    from fermentd.drivers.hx711 import Hx711Sensor

    sensor = Hx711Sensor(dout, sck)
    try:
        for _ in range(count):
            print(f"raw {sensor.read_raw():.0f}")
            time.sleep(0.5)
    except ScaleUnavailable as exc:
        print(f"scale not connected: {exc}")
        return 1
    finally:
        sensor.close()
    print("Press on the platform and run again: the number should change by thousands.")
    return 0
