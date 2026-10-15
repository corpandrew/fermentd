"""HX711 24-bit load-cell ADC, bit-banged over two GPIO lines with lgpio.

Pi 3B: DOUT on BCM 5 (physical pin 29), SCK on BCM 6 (physical pin 31) by default. The DS18B20
1-Wire bus on BCM 4 is not touched. Channel A, gain 128 (25 clock pulses per reading).

No maintained pip package works on the Pi's Python 3.13 venv without RPi.GPIO, so this is a
small own implementation on lgpio (the Raspberry Pi OS python3-lgpio package). The venv does not
include system site-packages, so the system copy is imported from dist-packages as a fallback.
Missing library or hardware raises ScaleUnavailable; the controller keeps running.
"""

from __future__ import annotations

import importlib
import statistics
import sys
import time
from typing import Any

from fermentd.drivers.base import ScaleUnavailable

READY_TIMEOUT_S = 0.6  # HX711 delivers 10 samples/s at RATE=0
MIN_GOOD_FRACTION = 0.6
_SYSTEM_DIST = "/usr/lib/python3/dist-packages"


def _load_lgpio() -> Any:
    try:
        return importlib.import_module("lgpio")
    except ImportError:
        pass
    if _SYSTEM_DIST not in sys.path:
        sys.path.append(_SYSTEM_DIST)
    try:
        return importlib.import_module("lgpio")
    except ImportError as exc:
        raise ScaleUnavailable("lgpio is not installed (sudo apt install python3-lgpio)") from exc


def to_signed(value: int) -> int:
    """24-bit two's complement."""
    return value - (1 << 24) if value & 0x800000 else value


def median_filter(values: list[int], samples: int) -> float:
    if len(values) < max(1, int(samples * MIN_GOOD_FRACTION)):
        raise ScaleUnavailable(f"only {len(values)} of {samples} readings came back")
    values = sorted(values)
    # Drop the outer quarter on each side (spikes from a missed clock), then take the median.
    cut = len(values) // 4
    core = values[cut : len(values) - cut] or values
    return float(statistics.median(core))


class Hx711Sensor:
    def __init__(self, dout_gpio: int = 5, sck_gpio: int = 6, samples: int = 15, chip: int = 0) -> None:
        self.dout_gpio = dout_gpio
        self.sck_gpio = sck_gpio
        self.samples = samples
        self.chip = chip
        self._lg: Any = None
        self._handle: int | None = None

    def _open(self) -> None:
        if self._handle is not None:
            return
        lg = _load_lgpio()
        try:
            handle = lg.gpiochip_open(self.chip)
            lg.gpio_claim_output(handle, self.sck_gpio, 0)
            lg.gpio_claim_input(handle, self.dout_gpio)
        except Exception as exc:  # lgpio.error, OSError
            raise ScaleUnavailable(f"cannot open GPIO {self.dout_gpio}/{self.sck_gpio}: {exc}") from exc
        self._lg, self._handle = lg, handle

    def _read_once(self) -> int | None:
        lg, h = self._lg, self._handle
        deadline = time.monotonic() + READY_TIMEOUT_S
        while lg.gpio_read(h, self.dout_gpio) == 1:  # DOUT goes low when a sample is ready
            if time.monotonic() > deadline:
                return None
            time.sleep(0.001)
        value = 0
        for _ in range(24):
            lg.gpio_write(h, self.sck_gpio, 1)
            lg.gpio_write(h, self.sck_gpio, 0)
            value = (value << 1) | lg.gpio_read(h, self.dout_gpio)
        lg.gpio_write(h, self.sck_gpio, 1)  # 25th pulse: channel A, gain 128 for the next one
        lg.gpio_write(h, self.sck_gpio, 0)
        if value in (0xFFFFFF, 0x7FFFFF, 0x800000):
            return None  # floating DOUT (not wired) or saturated
        return to_signed(value)

    def read_raw(self) -> float:
        self._open()
        values: list[int] = []
        try:
            for _ in range(self.samples):
                got = self._read_once()
                if got is not None:
                    values.append(got)
        except Exception as exc:
            self.close()
            raise ScaleUnavailable(f"read failed: {exc}") from exc
        if not values:
            raise ScaleUnavailable("no data from the HX711 (check wiring and power)")
        return median_filter(values, self.samples)

    def close(self) -> None:
        if self._handle is not None and self._lg is not None:
            try:
                self._lg.gpio_write(self._handle, self.sck_gpio, 1)  # SCK high >60 us powers it down
                self._lg.gpiochip_close(self._handle)
            except Exception:
                pass
        self._handle = None
