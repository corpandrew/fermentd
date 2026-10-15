from datetime import UTC, datetime
from pathlib import Path

import yaml

from fermentd.clock import ManualClock
from fermentd.config import load_config, load_secrets
from fermentd.control.service import ControlService
from fermentd.db.connection import connect
from fermentd.db.migrate import migrate
from fermentd.drivers.factory import build_hardware
from fermentd.drivers.sim import SimHeater, SimProbeBank
from fermentd.profiles.loader import load_profiles


class RecordingNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str, str]] = []

    def notify(self, kind: str, severity: str, title: str, body: str) -> None:
        self.messages.append((kind, severity, title, body))


def service_bundle(tmp_path: Path, when: datetime | None = None, mutate=None):
    data = yaml.safe_load(Path("config/fermentd.example.yaml").read_text())
    data["database"]["path"] = str(tmp_path / "fermentd.db")
    data["database"]["backup_dir"] = str(tmp_path / "backups")
    data["profiles"]["user_dir"] = str(tmp_path / "profiles.d")
    if mutate is not None:
        mutate(data)
    path = tmp_path / "fermentd.yaml"
    path.write_text(yaml.safe_dump(data))
    config = load_config(path)
    conn = connect(tmp_path / "fermentd.db")
    migrate(conn)
    clock = ManualClock(when or datetime(2026, 10, 12, 18, 0, tzinfo=UTC))
    hardware = build_hardware(config, load_secrets(Path("config/secrets.example.yaml")))
    notifier = RecordingNotifier()
    service = ControlService(
        config,
        conn,
        clock,
        hardware,
        load_profiles(),
        notifier,
    )
    return service, clock, hardware, notifier


def heater_of(hardware) -> SimHeater:
    heater = hardware.heaters["zone1"]
    assert isinstance(heater, SimHeater)
    return heater


def probes_of(hardware) -> SimProbeBank:
    assert hardware.sim_probes is not None
    return hardware.sim_probes
