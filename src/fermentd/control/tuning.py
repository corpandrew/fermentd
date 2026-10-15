"""Per-vessel heat tuning, from the October 2026 control analysis (water test + Ginger ale #2).

Measured:
  jug (about 1 gal of water): about 5 min before the probe starts climbing, warms about 3.7 F/h,
      keeps rising about 0.4 F after the mat turns off.
  bottle_group (sealed bottles in the cooler): about 20 min lag, about 1.3 F/h, about 0.55 F
      coast after the mat turns off.

Two ways to drive the mat:
  "onoff"        thermostat with an early turn-off. The mat turns off `overshoot_f` below the
                 target (the leftover heat carries it the rest of the way) and back on
                 `on_below_f` below the target, so the band sits centred on the target.
  "proportional" time-proportioning for slow vessels. Every `window_min` minutes the mat gets one
                 burst whose length depends on how far below target the bottles are
                 (`base_duty` at target, plus `gain_per_f` per degree below). Bursts are never
                 shorter than `min_on_min`, and the off gap never shorter than `min_off_min`.

Anything can be overridden in fermentd.yaml under control.tuning, keyed by vessel id or vessel type.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from statistics import median


@dataclass(frozen=True)
class Tuning:
    mode: str = "onoff"  # "onoff" | "proportional"
    overshoot_f: float = 0.4
    on_below_f: float = 0.6
    min_on_min: float = 5
    min_off_min: float = 5
    smoothing: int = 1  # median of the last N readings (1 = off)
    window_min: float = 60
    base_duty: float = 0.3
    gain_per_f: float = 0.35
    max_duty: float = 1.0
    hot_cut_f: float = 0.3  # proportional: end a burst early once this far above target
    lag_min: float = 5
    warm_rate_f_per_h: float = 3.7


DEFAULTS: dict[str, Tuning] = {
    "jug": Tuning(mode="onoff", overshoot_f=0.4, on_below_f=0.6, min_on_min=5, min_off_min=5,
                  smoothing=3, lag_min=5, warm_rate_f_per_h=3.7),
    "bottle_group": Tuning(mode="proportional", overshoot_f=0.55, on_below_f=0.6, min_on_min=15,
                           min_off_min=15, smoothing=1, window_min=60, base_duty=0.25, gain_per_f=0.35,
                           lag_min=20, warm_rate_f_per_h=1.3),
}
GENERIC = Tuning()
SMOOTH_MAX_SPREAD_F = 0.5
# Slowest first: when a zone holds several vessel types, tune for the slowest one.
_SLOWNESS = {"bottle_group": 3, "carboy": 2, "bucket": 2, "jar": 1, "jug": 1}


def tuning_for(vessel_id: str | None, vessel_type: str | None, overrides: dict | None = None) -> Tuning:
    base = DEFAULTS.get(vessel_type or "", GENERIC)
    overrides = overrides or {}
    for key in (vessel_type, vessel_id):
        if key and key in overrides:
            fields = {k: v for k, v in dict(overrides[key]).items() if v is not None}
            base = replace(base, **fields)
    return base


def pick_vessel(vessels: list[tuple[str, str]]) -> tuple[str, str] | None:
    """(id, type) pairs in a zone -> the slowest one, which sets the zone's tuning."""
    if not vessels:
        return None
    return max(vessels, key=lambda v: (_SLOWNESS.get(v[1], 1), v[0]))


def smooth(history: list[float], n: int) -> float:
    """Median of the last n readings, to ignore one-off wobbles. A real jump bigger than
    SMOOTH_MAX_SPREAD_F (the probe was moved, the lid opened) is passed straight through."""
    if n <= 1 or len(history) < 2:
        return history[-1]
    recent = history[-n:]
    if max(recent) - min(recent) > SMOOTH_MAX_SPREAD_F:
        return history[-1]
    return median(recent)


def onoff_desired(temp_f: float, target_f: float, tuning: Tuning, currently_on: bool) -> bool:
    if temp_f >= target_f - tuning.overshoot_f:
        return False
    if temp_f <= target_f - tuning.on_below_f:
        return True
    return currently_on


def burst_seconds(temp_f: float, target_f: float, tuning: Tuning) -> float:
    """Length of the mat-on burst for the next window."""
    if temp_f >= target_f + tuning.hot_cut_f:
        return 0.0
    duty = tuning.base_duty + tuning.gain_per_f * (target_f - temp_f)
    duty = max(0.0, min(tuning.max_duty, duty))
    window = tuning.window_min * 60
    on_s = duty * window
    min_on = tuning.min_on_min * 60
    if on_s < min_on:
        on_s = 0.0 if on_s < min_on / 2 else min_on
    on_s = min(on_s, max(0.0, window - tuning.min_off_min * 60)) if on_s < window else window
    return on_s
