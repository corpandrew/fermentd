"""Safety guard. It can only force a heater off."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProbeView:
    probe_id: str
    role: str
    temp_f: float | None
    fault: bool


@dataclass(frozen=True)
class SafetyLimits:
    cutoff_f: float = 80.0
    cutoff_clear_f: float = 78.0
    clear_s: float = 15 * 60
    max_on_s: float = 240 * 60
    rest_s: float = 15 * 60


@dataclass
class SafetyInput:
    now_mono: float
    probes: list[ProbeView]
    heater_on: bool
    on_since_mono: float | None
    rest_until_mono: float | None
    cutoff_latched: bool
    cutoff_below_since_mono: float | None
    target_in_range: bool
    fresh: bool
    ambient_fault_disables_heat: bool = True


@dataclass
class SafetyDecision:
    force_off: bool
    reasons: list[str] = field(default_factory=list)
    alerts: list[tuple[str, str]] = field(default_factory=list)
    cutoff_latched: bool = False
    cutoff_below_since_mono: float | None = None
    rest_until_mono: float | None = None


def evaluate_safety(inp: SafetyInput, limits: SafetyLimits) -> SafetyDecision:
    reasons: list[str] = []
    alerts: list[tuple[str, str]] = []
    latched = inp.cutoff_latched
    below_since = inp.cutoff_below_since_mono
    rest_until = inp.rest_until_mono

    if not inp.fresh:
        reasons.append("no_fresh_sensors")
    if not inp.target_in_range:
        reasons.append("target_out_of_range")
        alerts.append(("config_conflict", "action"))

    if any(probe.temp_f is not None and probe.temp_f > limits.cutoff_f for probe in inp.probes):
        latched = True
        below_since = None
        alerts.append(("overtemp_cutoff", "critical"))
    if latched:
        if _all_below_clear(inp.probes, limits.cutoff_clear_f):
            if below_since is None:
                below_since = inp.now_mono
            elif inp.now_mono - below_since >= limits.clear_s:
                latched = False
                below_since = None
        else:
            below_since = None
        if latched:
            reasons.append("overtemp_cutoff")

    if _sensor_fault(inp):
        reasons.append("sensor_fault")
        alerts.append(("sensor_fault", "critical"))

    if (
        inp.heater_on
        and inp.on_since_mono is not None
        and inp.now_mono - inp.on_since_mono >= limits.max_on_s
    ):
        rest_until = inp.now_mono + limits.rest_s
        reasons.append("max_on")
        alerts.append(("max_on_rest", "info"))
    if rest_until is not None and inp.now_mono < rest_until:
        reasons.append("rest")
    elif rest_until is not None:
        rest_until = None

    return SafetyDecision(
        force_off=bool(reasons),
        reasons=reasons,
        alerts=alerts,
        cutoff_latched=latched,
        cutoff_below_since_mono=below_since,
        rest_until_mono=rest_until,
    )


def check_target(
    target_f: float,
    hysteresis_f: float,
    *,
    global_low: float,
    global_high: float,
    hysteresis_low: float,
    hysteresis_high: float,
    profile_ranges: list[tuple[str, float, float]],
) -> str | None:
    """Return an OUT_OF_RANGE reason, or None when the request is allowed."""
    if target_f < global_low or target_f > global_high:
        return (
            f"OUT_OF_RANGE target {target_f} F is outside the global range "
            f"{global_low}-{global_high} F"
        )
    if hysteresis_f < hysteresis_low or hysteresis_f > hysteresis_high:
        return (
            f"OUT_OF_RANGE hysteresis {hysteresis_f} F is outside "
            f"{hysteresis_low}-{hysteresis_high} F"
        )
    for profile_id, low, high in profile_ranges:
        if target_f < low or target_f > high:
            return (
                f"OUT_OF_RANGE target {target_f} F is outside {profile_id} allowed range {low}-{high} F"
            )
    return None


def _all_below_clear(probes: list[ProbeView], clear_f: float) -> bool:
    if not probes:
        return False
    for probe in probes:
        if probe.fault or probe.temp_f is None or probe.temp_f >= clear_f:
            return False
    return True


def _sensor_fault(inp: SafetyInput) -> bool:
    for probe in inp.probes:
        if not probe.fault:
            continue
        if probe.role == "ambient" and not inp.ambient_fault_disables_heat:
            continue
        return True
    return False
