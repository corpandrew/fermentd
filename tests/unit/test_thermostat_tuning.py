"""Per-vessel heat tuning, the quieter pressure warning, probe-move settling and the mat state
across a planned restart (October 2026 control analysis)."""

from datetime import timedelta

from tests.conftest import heater_of, probes_of, service_bundle

from fermentd.control import tuning as T
from fermentd.control.planned import write_marker
from fermentd.control.service import FLAG_SETTLING, ControlService
from fermentd.timefmt import isoformat

ROM = "28-0000000000b2"
AMB = "28-0000000000a1"


def _bundle(tmp_path, vessel_type="bottle_group", temp=72.0, mutate=None):
    service, clock, hardware, notifier = service_bundle(tmp_path, mutate=mutate)
    service.startup()
    service.conn.execute("UPDATE VESSEL SET vessel_type = ? WHERE id = 'vessel1'", (vessel_type,))
    probes_of(hardware).set_temp(ROM, temp)
    probes_of(hardware).set_temp(AMB, 60.0)
    service.submit("test", "start_batch",
                   {"vessel_id": "vessel1", "name": "GA", "profile_id": "soda_ginger_ale"}, "s1")
    service.tick()
    return service, clock, hardware, notifier


def _run(service, clock, minutes):
    for _ in range(int(minutes * 6)):
        clock.advance(10)
        service.tick()


def _ramp(service, clock, hardware, start, end):
    """Move the probe gradually (the probe filter rejects impossible jumps)."""
    steps = max(1, int(abs(end - start) / 0.3))
    for i in range(1, steps + 1):
        probes_of(hardware).set_temp(ROM, start + (end - start) * i / steps)
        clock.advance(10)
        service.tick()


def _batch_id(service):
    return service.conn.execute("SELECT id FROM BATCH WHERE ended_at IS NULL").fetchone()["id"]


def _open(service, prefix):
    return service.conn.execute(
        "SELECT COUNT(*) FROM ALERT WHERE dedupe_key LIKE ? AND status = 'open'", (prefix + "%",)
    ).fetchone()[0]


# --- pure tuning ---------------------------------------------------------------------------

def test_defaults_per_vessel_type():
    jug = T.tuning_for("v", "jug")
    bottles = T.tuning_for("v", "bottle_group")
    assert (jug.mode, jug.overshoot_f, jug.smoothing) == ("onoff", 0.4, 3)
    assert (bottles.mode, bottles.overshoot_f, bottles.min_on_min, bottles.min_off_min) == ("proportional", 0.55, 15, 15)
    assert T.tuning_for("x", "carboy") == T.GENERIC


def test_overrides_by_type_then_vessel_id():
    out = T.tuning_for("b1", "bottle_group", {"bottle_group": {"window_min": 30}, "b1": {"base_duty": 0.25}})
    assert out.window_min == 30 and out.base_duty == 0.25 and out.mode == "proportional"


def test_slowest_vessel_sets_the_zone():
    assert T.pick_vessel([("a", "jug"), ("b", "bottle_group")]) == ("b", "bottle_group")
    assert T.pick_vessel([]) is None


def test_onoff_band_is_centred_on_target():
    jug = T.tuning_for("v", "jug")
    assert T.onoff_desired(71.4, 72, jug, False) is True
    assert T.onoff_desired(71.5, 72, jug, False) is False  # inside the band: stay off
    assert T.onoff_desired(71.5, 72, jug, True) is True  # inside the band: stay on
    assert T.onoff_desired(71.6, 72, jug, True) is False  # early off; coasting adds about 0.4


def test_burst_length_follows_the_error():
    b = T.tuning_for("v", "bottle_group")
    assert T.burst_seconds(72.0, 72, b) == 15 * 60  # 25 % of an hour at target
    assert abs(T.burst_seconds(71.0, 72, b) - 36 * 60) < 1e-6
    assert T.burst_seconds(72.3, 72, b) == 0  # warm: skip this window
    assert T.burst_seconds(72.2, 72, b) == 15 * 60  # short bursts are stretched to the 15-min minimum
    assert T.burst_seconds(70.5, 72, b) == 45 * 60  # partial bursts leave the 15-min off gap
    assert T.burst_seconds(60.0, 72, b) == 60 * 60  # far below: heat the whole hour to warm up


def test_smoothing_ignores_a_wobble_but_follows_a_real_jump():
    assert T.smooth([72.0, 72.3, 72.0], 3) == 72.0
    assert T.smooth([72.0, 72.0, 66.0], 3) == 66.0
    assert T.smooth([72.0, 72.3], 1) == 72.3


# --- the controller ------------------------------------------------------------------------

def test_jug_turns_off_early_and_on_below_target(tmp_path):
    service, clock, hardware, _n = _bundle(tmp_path, "jug", temp=71.0)
    heater = heater_of(hardware)
    _run(service, clock, 1)
    assert heater.on is True
    probes_of(hardware).set_temp(ROM, 71.7)
    _run(service, clock, 6)  # past the 5-min minimum on time
    assert heater.on is False
    probes_of(hardware).set_temp(ROM, 71.5)
    _run(service, clock, 6)
    assert heater.on is False  # still inside the band
    probes_of(hardware).set_temp(ROM, 71.3)
    _run(service, clock, 1)
    assert heater.on is True


def test_bottles_get_timed_bursts(tmp_path):
    service, clock, hardware, _n = _bundle(tmp_path, "bottle_group", temp=72.0)
    heater = heater_of(hardware)
    assert heater.on is True and service.runtime.zones["zone1"].mode == "proportional"
    _run(service, clock, 14)
    assert heater.on is True  # 15-min burst (25 % of the hour)
    _run(service, clock, 2)
    assert heater.on is False
    _run(service, clock, 43)
    assert heater.on is False  # rest of the hour
    _run(service, clock, 2)
    assert heater.on is True  # next window


def test_bottles_burst_ends_early_when_warm(tmp_path):
    service, clock, hardware, _n = _bundle(tmp_path, "bottle_group", temp=71.5)
    heater = heater_of(hardware)
    assert heater.on is True
    probes_of(hardware).set_temp(ROM, 72.4)
    _run(service, clock, 1)
    assert heater.on is False


def test_countdown_still_rearmed_every_cycle_in_burst_mode(tmp_path):
    service, clock, hardware, _n = _bundle(tmp_path, "bottle_group", temp=71.0)
    heater = heater_of(hardware)
    heater.countdown_supported = True
    before = service.runtime.zones["zone1"].countdown_armed_mono
    _run(service, clock, 1)
    after = service.runtime.zones["zone1"].countdown_armed_mono
    assert heater.on is True and after is not None and after != before


# --- pressure warning ------------------------------------------------------------------------

def _bottle(service, clock, ago_h):
    service.conn.execute(
        "UPDATE BATCH SET stage = 'in_bottle', stage_started_at = ? WHERE id = ?",
        (isoformat(clock.now() - timedelta(hours=ago_h)), _batch_id(service)),
    )


def test_pressure_quiet_right_after_bottling(tmp_path):
    service, clock, hardware, _n = _bundle(tmp_path, temp=72.0)
    _bottle(service, clock, 0)
    _ramp(service, clock, hardware, 72.0, 75.5)
    _run(service, clock, 5)
    assert _open(service, "pressure_risk") == 0


def test_pressure_raised_after_grace_and_clears_with_hysteresis(tmp_path):
    service, clock, hardware, notifier = _bundle(tmp_path, temp=72.0)
    _bottle(service, clock, 3)
    _ramp(service, clock, hardware, 72.0, 75.5)
    _run(service, clock, 1)
    assert _open(service, "pressure_risk") == 1
    probes_of(hardware).set_temp(ROM, 74.8)  # back under 75 but not by 0.5
    _run(service, clock, 1)
    assert _open(service, "pressure_risk") == 1
    probes_of(hardware).set_temp(ROM, 74.4)
    _run(service, clock, 1)
    assert _open(service, "pressure_risk") == 0
    assert len([m for m in notifier.messages if m[0] == "pressure_risk"]) == 1


def test_pressure_not_raised_while_cooling_with_mat_off(tmp_path):
    service, clock, hardware, _n = _bundle(tmp_path, temp=76.5)
    for temp in (76.5, 76.45):
        probes_of(hardware).set_temp(ROM, temp)
        _run(service, clock, 3)
    _bottle(service, clock, 3)
    for temp in (76.4, 76.2, 76.0, 75.8, 75.6, 75.4, 75.2):
        probes_of(hardware).set_temp(ROM, temp)
        _run(service, clock, 1)
    assert heater_of(hardware).on is False
    assert _open(service, "pressure_risk") == 0


# --- target reached wording -------------------------------------------------------------------

def test_target_reached_from_above_says_settled(tmp_path):
    service, clock, hardware, notifier = _bundle(tmp_path, temp=74.0)
    probes_of(hardware).set_temp(ROM, 72.3)
    _run(service, clock, 1)
    sent = [m for m in notifier.messages if m[0] == "target_reached"]
    assert sent and "settled at target" in sent[0][2] and "settled at its 72°F target" in sent[0][3]


# --- probe moves ------------------------------------------------------------------------------

def test_probe_move_is_quiet_for_ten_minutes(tmp_path):
    service, clock, hardware, _n = _bundle(tmp_path, temp=72.0)
    service.conn.execute("UPDATE VESSEL SET probe_rom_id = ? WHERE id = 'vessel1'", (AMB,))
    service.conn.execute("UPDATE VESSEL SET probe_rom_id = ? WHERE id = 'vessel1'", (ROM,))
    service.runtime.vessel_wiring["vessel1"] = ("28-old", "zone1")  # as if it was just moved
    _bottle(service, clock, 3)
    _ramp(service, clock, hardware, 72.0, 77.0)
    _run(service, clock, 5)
    assert _open(service, "pressure_risk") == 0
    flags = service.conn.execute("SELECT flags FROM READING ORDER BY ts DESC LIMIT 1").fetchone()[0]
    assert flags & FLAG_SETTLING
    _run(service, clock, 6)
    assert _open(service, "pressure_risk") == 1
    flags = service.conn.execute("SELECT flags FROM READING ORDER BY ts DESC LIMIT 1").fetchone()[0]
    assert not flags & FLAG_SETTLING


# --- planned restart --------------------------------------------------------------------------

def _restart(service, clock, hardware, notifier):
    again = ControlService(service.config, service.conn, clock, hardware, service.profiles, notifier)
    again.startup()
    return again


def test_planned_restart_keeps_the_mat_on_and_rearms_the_cutoff(tmp_path):
    service, clock, hardware, notifier = _bundle(tmp_path, temp=71.0)
    heater = heater_of(hardware)
    heater.countdown_supported = True
    _run(service, clock, 3)
    assert heater.on is True
    window = service.runtime.zones["zone1"].window_start
    write_marker(service.conn, clock.now())
    service.stop()
    clock.advance(20)
    again = _restart(service, clock, hardware, notifier)
    zone = again.runtime.zones["zone1"]
    assert heater.on is True and zone.commanded_on and zone.countdown_armed_mono is not None
    assert abs(zone.window_start - window) < 1  # same burst continues
    again.tick()
    assert heater.on is True


def test_unplanned_restart_still_starts_with_the_mat_off(tmp_path):
    service, clock, hardware, notifier = _bundle(tmp_path, temp=71.0)
    heater = heater_of(hardware)
    _run(service, clock, 3)
    assert heater.on is True
    service.stop()
    _restart(service, clock, hardware, notifier)
    assert heater.on is False
