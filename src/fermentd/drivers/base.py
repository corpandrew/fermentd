"""Sensor and actuator protocols. The control loop depends on these, not on tinytuya or sysfs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TempSample:
    temp_f: float | None
    reject_reason: str | None


class TempSensor(Protocol):
    def read(self, rom_id: str) -> TempSample: ...


class ActuatorUnreachable(Exception):
    pass


class Actuator(Protocol):
    id: str

    def set(self, on: bool) -> None: ...

    def read_state(self) -> bool | None: ...

    def supports_countdown(self) -> bool: ...

    def arm_countdown(self, seconds: int) -> bool: ...

    def close(self) -> None: ...


class ScaleUnavailable(Exception):
    """The scale did not answer: not wired, GPIO library missing, or no data-ready pulse."""


class WeightSensor(Protocol):
    def read_raw(self) -> float:
        """Median of several raw HX711 counts. Raises ScaleUnavailable."""
        ...

    def close(self) -> None: ...
