"""Simulated probe, heater, and a single-vessel thermal model."""

from __future__ import annotations

from fermentd.drivers.base import ActuatorUnreachable, ScaleUnavailable, TempSample


class SimProbeBank:
    def __init__(self) -> None:
        self.temps: dict[str, float] = {}
        self.faults: dict[str, str] = {}

    def set_temp(self, rom_id: str, temp_f: float) -> None:
        self.temps[rom_id] = temp_f
        self.faults.pop(rom_id, None)

    def set_fault(self, rom_id: str, reason: str) -> None:
        self.faults[rom_id] = reason

    def read(self, rom_id: str) -> TempSample:
        if rom_id in self.faults:
            return TempSample(None, self.faults[rom_id])
        if rom_id not in self.temps:
            return TempSample(None, "missing")
        return TempSample(self.temps[rom_id], None)


class SimHeater:
    def __init__(self, plug_id: str) -> None:
        self.id = plug_id
        self.on = False
        self.unreachable = False
        self.report_on: bool | None = None
        self.set_calls: list[bool] = []
        self.countdown: int | None = None
        self.countdown_supported = False
        self.countdown_ack = True  # set False to simulate a plug that ignores the arm
        self.last_countdown: int | None = None

    def set(self, on: bool) -> None:
        self.set_calls.append(on)
        if self.unreachable:
            raise ActuatorUnreachable(self.id)
        self.on = on

    def read_state(self) -> bool | None:
        if self.unreachable:
            return None
        if self.report_on is not None:
            return self.report_on
        return self.on

    def supports_countdown(self) -> bool:
        return self.countdown_supported

    def arm_countdown(self, seconds: int) -> bool:
        if not self.countdown_ack:
            return False
        self.countdown = seconds
        return True

    def close(self) -> None:
        return None


class ThermalModel:
    """dT/dt = (T_amb - T) / tau + heater_gain * on."""

    def __init__(
        self,
        temp_f: float,
        ambient_f: float,
        tau_s: float,
        heater_gain_f_per_hour: float,
    ) -> None:
        self.temp_f = temp_f
        self.ambient_f = ambient_f
        self.tau_s = tau_s
        self.gain_per_s = heater_gain_f_per_hour / 3600.0

    def step(self, seconds: float, heater_on: bool) -> float:
        remaining = seconds
        while remaining > 0:
            dt = min(1.0, remaining)
            drive = self.gain_per_s if heater_on else 0.0
            self.temp_f += ((self.ambient_f - self.temp_f) / self.tau_s + drive) * dt
            remaining -= dt
        return self.temp_f


class SimScale:
    """A load cell with a fixed zero and gain. Set grams (what sits on it) or disconnect it."""

    def __init__(self, zero_counts: float = 84_000.0, counts_per_gram: float = 21.5) -> None:
        self.zero_counts = zero_counts
        self.counts_per_gram = counts_per_gram
        self.grams = 0.0
        self.connected = True
        self.reads = 0

    def read_raw(self) -> float:
        self.reads += 1
        if not self.connected:
            raise ScaleUnavailable("sim scale disconnected")
        return self.zero_counts + self.grams * self.counts_per_gram

    def close(self) -> None:
        return None
