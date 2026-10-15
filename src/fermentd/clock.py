"""Wall clock and monotonic clock. Tests advance ManualClock instead of sleeping."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Timezone-aware UTC."""

    def monotonic(self) -> float:
        """Seconds, not subject to NTP steps."""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


class ManualClock:
    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("ManualClock start must be timezone-aware")
        self._now = start.astimezone(UTC)
        self._mono = 0.0

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._mono

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("cannot advance the clock backwards")
        self._now += timedelta(seconds=seconds)
        self._mono += seconds
