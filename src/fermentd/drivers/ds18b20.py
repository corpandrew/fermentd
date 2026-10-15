"""DS18B20 reads from the w1 sysfs tree. Pass a fake root in tests."""

from __future__ import annotations

from pathlib import Path

from fermentd.drivers.base import TempSample
from fermentd.units import c_to_f

POWER_ON_C = 85.0
SENTINEL_C = -127.0


class Ds18b20:
    def __init__(self, sysfs_root: Path, probe_min_f: float, probe_max_f: float) -> None:
        self._root = sysfs_root
        self._min_f = probe_min_f
        self._max_f = probe_max_f

    def read(self, rom_id: str) -> TempSample:
        try:
            return self._read(rom_id)
        except (OSError, ValueError):
            return TempSample(None, "read_error")

    def _read(self, rom_id: str) -> TempSample:
        device = self._root / rom_id
        slave = device / "w1_slave"
        temp_file = device / "temperature"
        if slave.exists():
            parsed = _from_w1_slave(slave.read_text())
            if isinstance(parsed, str):
                return TempSample(None, parsed)
            celsius = parsed
        elif temp_file.exists():
            celsius = int(temp_file.read_text().strip()) / 1000.0
        else:
            return TempSample(None, "missing")
        return classify_celsius(celsius, self._min_f, self._max_f)


def classify_celsius(celsius: float, probe_min_f: float, probe_max_f: float) -> TempSample:
    if abs(celsius - POWER_ON_C) < 0.001:
        return TempSample(None, "power_on_default")
    if abs(celsius - SENTINEL_C) < 0.001:
        return TempSample(None, "sentinel")
    temp_f = celsius_to_sample_f(celsius)
    if temp_f < probe_min_f or temp_f > probe_max_f:
        return TempSample(None, "implausible")
    return TempSample(temp_f, None)


def celsius_to_sample_f(celsius: float) -> float:
    return c_to_f(celsius)


def rate_reject(
    previous_f: float | None,
    previous_mono: float | None,
    temp_f: float,
    now_mono: float,
    max_rate_f_per_min: float,
) -> str | None:
    if previous_f is None or previous_mono is None:
        return None
    minutes = (now_mono - previous_mono) / 60.0
    if minutes <= 0:
        return None
    if abs(temp_f - previous_f) / minutes > max_rate_f_per_min:
        return "rate"
    return None


def _from_w1_slave(text: str) -> float | str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "missing"
    if "YES" not in lines[0]:
        return "crc"
    for line in lines:
        if "t=" in line:
            raw = line.rsplit("t=", 1)[1].strip()
            return int(raw) / 1000.0
    return "missing"
