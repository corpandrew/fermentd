import pytest

from fermentd.control.safety import ProbeView, SafetyInput, SafetyLimits, check_target, evaluate_safety
from fermentd.control.thermostat import evaluate_thermostat

LIMITS = SafetyLimits()


def _probe(probe_id: str, temp: float | None, role: str = "vessel", fault: bool = False) -> ProbeView:
    return ProbeView(probe_id, role, temp, fault or temp is None)


def _inp(**overrides: object) -> SafetyInput:
    base = dict(
        now_mono=0.0,
        probes=[_probe("vessel", 70.0), _probe("ambient", 60.0, role="ambient")],
        heater_on=True,
        on_since_mono=0.0,
        rest_until_mono=None,
        cutoff_latched=False,
        cutoff_below_since_mono=None,
        target_in_range=True,
        fresh=True,
    )
    base.update(overrides)
    return SafetyInput(**base)  # type: ignore[arg-type]


def test_healthy_zone_is_not_forced_off():
    decision = evaluate_safety(_inp(), LIMITS)
    assert decision.force_off is False
    assert decision.alerts == []


def test_missing_fresh_samples_force_off():
    decision = evaluate_safety(_inp(fresh=False), LIMITS)
    assert decision.force_off is True
    assert "no_fresh_sensors" in decision.reasons


def test_overtemp_latches_until_all_probes_stay_under_78_for_15_minutes():
    hot = evaluate_safety(_inp(probes=[_probe("vessel", 80.1), _probe("ambient", 70.0, "ambient")]), LIMITS)
    assert hot.force_off is True
    assert hot.cutoff_latched is True
    assert ("overtemp_cutoff", "critical") in hot.alerts

    still = evaluate_safety(
        _inp(
            now_mono=60,
            probes=[_probe("vessel", 79.0), _probe("ambient", 70.0, "ambient")],
            cutoff_latched=True,
        ),
        LIMITS,
    )
    assert still.cutoff_latched is True
    assert still.force_off is True

    cooling = evaluate_safety(
        _inp(
            now_mono=100,
            probes=[_probe("vessel", 77.0), _probe("ambient", 70.0, "ambient")],
            cutoff_latched=True,
        ),
        LIMITS,
    )
    assert cooling.cutoff_latched is True
    cleared = evaluate_safety(
        _inp(
            now_mono=100 + 15 * 60,
            probes=[_probe("vessel", 77.0), _probe("ambient", 70.0, "ambient")],
            cutoff_latched=True,
            cutoff_below_since_mono=100,
        ),
        LIMITS,
    )
    assert cleared.cutoff_latched is False
    assert cleared.force_off is False


def test_sensor_fault_forces_the_heater_off():
    faulted = evaluate_safety(
        _inp(probes=[_probe("vessel", None, fault=True), _probe("ambient", 60.0, "ambient")]),
        LIMITS,
    )
    assert faulted.force_off is True
    assert ("sensor_fault", "critical") in faulted.alerts

    ambient = evaluate_safety(
        _inp(probes=[_probe("vessel", 70.0), _probe("ambient", None, "ambient", fault=True)]),
        LIMITS,
    )
    assert ambient.force_off is True


def test_max_on_then_rest_preempts_a_call_for_heat():
    tripped = evaluate_safety(_inp(now_mono=240 * 60, on_since_mono=0.0), LIMITS)
    assert tripped.force_off is True
    assert tripped.rest_until_mono == 240 * 60 + 15 * 60
    resting = evaluate_safety(
        _inp(now_mono=240 * 60 + 60, heater_on=False, rest_until_mono=tripped.rest_until_mono),
        LIMITS,
    )
    assert resting.force_off is True
    assert "rest" in resting.reasons
    done = evaluate_safety(
        _inp(now_mono=tripped.rest_until_mono, heater_on=False, rest_until_mono=tripped.rest_until_mono),
        LIMITS,
    )
    assert done.force_off is False


def test_target_out_of_range_forces_off():
    decision = evaluate_safety(_inp(target_in_range=False), LIMITS)
    assert decision.force_off is True
    assert ("config_conflict", "action") in decision.alerts


@pytest.mark.parametrize(
    ("target", "hysteresis", "ranges", "ok"),
    [
        (50.0, 0.5, [], True),
        (75.0, 3.0, [], True),
        (49.9, 1.0, [], False),
        (75.1, 1.0, [], False),
        (62.0, 0.4, [], False),
        (62.0, 3.1, [], False),
        (68.0, 1.0, [("soda_ginger_ale", 68.0, 75.0)], True),
        (75.0, 1.0, [("soda_ginger_ale", 68.0, 75.0)], True),
        (67.9, 1.0, [("soda_ginger_ale", 68.0, 75.0)], False),
    ],
)
def test_check_target_boundaries(target: float, hysteresis: float, ranges: list, ok: bool):
    reason = check_target(
        target,
        hysteresis,
        global_low=50,
        global_high=75,
        hysteresis_low=0.5,
        hysteresis_high=3,
        profile_ranges=ranges,
    )
    assert (reason is None) is ok
    if target == 67.9:
        assert reason is not None
        assert "soda_ginger_ale" in reason


def test_thermostat_hysteresis_and_minimum_times():
    common = dict(
        target_f=72.0,
        hysteresis_f=1.0,
        now_mono=1000.0,
        min_on_s=300.0,
        min_off_s=300.0,
        force_off=False,
        allow_heat=True,
    )
    assert evaluate_thermostat(temp_f=71.0, currently_on=False, on_since_mono=None, off_since_mono=None, **common)
    assert not evaluate_thermostat(temp_f=72.0, currently_on=True, on_since_mono=0.0, off_since_mono=None, **common)
    assert evaluate_thermostat(temp_f=71.5, currently_on=True, on_since_mono=0.0, off_since_mono=None, **common)
    assert not evaluate_thermostat(temp_f=71.5, currently_on=False, on_since_mono=None, off_since_mono=0.0, **common)
    assert not evaluate_thermostat(
        temp_f=70.0, currently_on=False, on_since_mono=None, off_since_mono=900.0, **common
    )
    assert evaluate_thermostat(
        temp_f=73.0, currently_on=True, on_since_mono=800.0, off_since_mono=None, **common
    )


def test_safety_preempts_minimum_on_time():
    assert (
        evaluate_thermostat(
            temp_f=70.0,
            target_f=72.0,
            hysteresis_f=1.0,
            currently_on=True,
            on_since_mono=950.0,
            off_since_mono=None,
            now_mono=1000.0,
            min_on_s=300.0,
            min_off_s=300.0,
            force_off=True,
            allow_heat=True,
        )
        is False
    )


def test_no_active_batch_does_not_heat():
    assert (
        evaluate_thermostat(
            temp_f=60.0,
            target_f=72.0,
            hysteresis_f=1.0,
            currently_on=False,
            on_since_mono=None,
            off_since_mono=None,
            now_mono=0.0,
            min_on_s=300.0,
            min_off_s=300.0,
            force_off=False,
            allow_heat=False,
        )
        is False
    )
