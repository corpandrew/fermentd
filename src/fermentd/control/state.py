"""In-memory heater state. Durations use the monotonic clock."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from fermentd.control.probes import ProbeHealth


@dataclass
class ZoneRuntime:
    commanded_on: bool = False
    on_since: float | None = None
    off_since: float | None = None
    rest_until: float | None = None
    cutoff_latched: bool = False
    cutoff_below_since: float | None = None
    unreachable_streak: int = 0
    have_fresh: bool = False
    countdown_armed_mono: float | None = None
    mismatch: bool = False
    countdown_failed: bool = False
    countdown_armed_wall: datetime | None = None
    countdown_unarmed: bool = False
    countdown_saved: tuple | None = None  # (monotonic, (on, unarmed)) of the last SETTING write
    below_target_since: float | None = None
    out_of_range_since: float | None = None
    stuck_window_start: float | None = None
    stuck_window_temp: float | None = None
    stuck_last_alert: float | None = None
    history: list = field(default_factory=list)  # recent raw control temps (for smoothing)
    trend: list = field(default_factory=list)  # (monotonic, temp) for the last ~10 min
    window_start: float | None = None  # proportional mode: current window
    window_on_s: float = 0.0
    window_key: tuple | None = None  # (vessel id, target) the window was planned for
    mode: str = "onoff"


@dataclass
class Runtime:
    zones: dict[str, ZoneRuntime] = field(default_factory=dict)
    probes: dict[str, ProbeHealth] = field(default_factory=dict)
    healthy_ticks: int = 0
    started_mono: float | None = None
    interrupted_cleared: bool = False
    probe_silent_alerted: set[str] = field(default_factory=set)  # vessel ids with an open probe_silent
    probe_first_seen: dict[str, float] = field(default_factory=dict)
    vessel_wiring: dict[str, tuple] = field(default_factory=dict)  # vessel id -> (probe, zone)
    settle_until: dict[str, float] = field(default_factory=dict)  # vessel id -> monotonic
    scale_due: dict[str, float] = field(default_factory=dict)  # vessel id -> monotonic time of next sample
