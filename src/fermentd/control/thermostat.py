"""Bang-bang heat control with hysteresis. Anticipation is deferred; a is 0."""

from __future__ import annotations


def evaluate_thermostat(
    *,
    temp_f: float,
    target_f: float,
    hysteresis_f: float,
    currently_on: bool,
    on_since_mono: float | None,
    off_since_mono: float | None,
    now_mono: float,
    min_on_s: float,
    min_off_s: float,
    force_off: bool,
    allow_heat: bool,
) -> bool:
    if force_off or not allow_heat:
        return False
    if temp_f <= target_f - hysteresis_f:
        desired = True
    elif temp_f >= target_f:
        desired = False
    else:
        desired = currently_on
    if desired and not currently_on and off_since_mono is not None:
        if now_mono - off_since_mono < min_off_s:
            return False
    if not desired and currently_on and on_since_mono is not None:
        if now_mono - on_since_mono < min_on_s:
            return True
    return desired
