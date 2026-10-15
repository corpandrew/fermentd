from tests.conftest import heater_of, probes_of, service_bundle


def _start(service):
    service.submit(
        "test",
        "start_batch",
        {"vessel_id": "vessel1", "name": "Ginger ale", "profile_id": "soda_ginger_ale"},
        "start-1",
    )


def test_heating_rearms_a_ten_minute_countdown_every_cycle(tmp_path):
    from fermentd.control import cutoff

    service, clock, hardware, notifier = service_bundle(tmp_path)
    heater = heater_of(hardware)
    heater.countdown_supported = True
    service.startup()
    _start(service)
    service.tick()
    assert heater.on is True
    assert heater.countdown == 10 * 60
    heater.countdown = None
    clock.advance(10)
    service.tick()
    assert heater.countdown == 10 * 60  # refreshed on the very next cycle
    st = cutoff.status(service.conn, "zone1", clock.now())
    assert st["state"] == "armed" and st["text"] == "Safety cutoff: armed (10 min)"
    assert not service.conn.execute("SELECT 1 FROM ALERT WHERE dedupe_key = 'countdown_not_armed:zone:zone1'").fetchone()


def test_a_plug_that_ignores_the_arm_raises_a_warning_and_push(tmp_path):
    from fermentd.control import cutoff

    service, clock, hardware, notifier = service_bundle(tmp_path)
    heater = heater_of(hardware)
    heater.countdown_supported = True
    heater.countdown_ack = False
    service.startup()
    _start(service)
    for _ in range(8):
        service.tick()
        clock.advance(10)
    alert = service.conn.execute("SELECT severity, resolved_at FROM ALERT WHERE dedupe_key = 'countdown_not_armed:zone:zone1'").fetchone()
    assert alert["severity"] == "warning" and alert["resolved_at"] is None
    assert any(m[0] == "countdown_not_armed" for m in notifier.messages)
    assert cutoff.status(service.conn, "zone1", clock.now())["state"] == "not_armed"
    heater.countdown_ack = True
    service.tick()
    alert = service.conn.execute("SELECT resolved_at FROM ALERT WHERE dedupe_key = 'countdown_not_armed:zone:zone1'").fetchone()
    assert alert["resolved_at"] is not None


def test_a_plug_without_countdown_is_not_armed(tmp_path):
    service, _clock, hardware, _notifier = service_bundle(tmp_path)
    heater = heater_of(hardware)
    service.startup()
    service.submit(
        "test",
        "start_batch",
        {"vessel_id": "vessel1", "name": "Ginger ale", "profile_id": "soda_ginger_ale"},
        "start-1",
    )
    service.tick()
    assert heater.on is True
    assert heater.countdown is None


def test_a_probe_that_was_not_read_is_not_fresh(tmp_path):
    service, clock, hardware, _notifier = service_bundle(tmp_path)
    service.startup()
    bank = probes_of(hardware)
    bank.set_fault("28-0000000000b2", "missing")
    bank.set_fault("28-0000000000a1", "missing")
    service.tick()
    assert service.runtime.zones["zone1"].have_fresh is False

    bank.set_temp("28-0000000000b2", 64.0)
    bank.set_temp("28-0000000000a1", 64.0)
    service.tick()
    assert service.runtime.zones["zone1"].have_fresh is True
    clock.advance(91)
    bank.set_fault("28-0000000000b2", "crc")
    service.tick()
    assert service.runtime.zones["zone1"].have_fresh is False


def test_a_tick_error_forces_the_heater_off_alerts_and_the_loop_continues(tmp_path):
    service, _clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    service.submit(
        "test",
        "start_batch",
        {"vessel_id": "vessel1", "name": "Ginger ale", "profile_id": "soda_ginger_ale"},
        "start-1",
    )
    service.tick()
    heater = heater_of(hardware)
    assert heater.on is True
    probes = probes_of(hardware)
    original = probes.read

    def explode(_rom_id: str):
        raise RuntimeError("probe bus died")

    probes.read = explode
    service.guarded_tick()
    assert heater.on is False
    assert any(message[0] == "control_fault" and message[1] == "critical" for message in notifier.messages)
    probes.read = original
    service.guarded_tick()


def test_startup_forces_the_heater_off_and_the_first_tick_can_heat(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    heater = heater_of(hardware)
    heater.on = True
    service.startup()
    assert heater.on is False
    assert heater.set_calls == [False]

    service.submit(
        "test",
        "start_batch",
        {"vessel_id": "vessel1", "name": "Ginger ale", "profile_id": "soda_ginger_ale"},
        "start-1",
    )
    probes_of(hardware).set_temp("28-0000000000b2", 64.0)
    probes_of(hardware).set_temp("28-0000000000a1", 64.0)
    service.tick()
    assert heater.on is True
    batch = service.conn.execute("SELECT stage, profile_id, name FROM BATCH").fetchone()
    assert batch["stage"] == "in_bottle"
    assert batch["profile_id"] == "soda_ginger_ale"
    assert batch["name"] == "Ginger ale"
    assert service.conn.execute("SELECT COUNT(*) AS n FROM READING").fetchone()["n"] == 1


def test_out_of_range_target_is_rejected_and_unchanged(tmp_path):
    service, _clock, _hardware, _notifier = service_bundle(tmp_path)
    service.startup()
    service.submit("test", "start_batch", {"vessel_id": "vessel1", "name": "Ginger ale"}, "start-1")
    service.tick()
    before = service.conn.execute("SELECT target_f FROM TEMP_ZONE WHERE id = 'zone1'").fetchone()["target_f"]
    service.submit("test", "set_target_temp", {"zone": "zone1", "target_f": 67.9}, "target-1")
    service.tick()
    command = service.conn.execute(
        "SELECT status, result_json FROM COMMAND WHERE idempotency_key = 'target-1'"
    ).fetchone()
    assert command["status"] == "rejected"
    assert "soda_ginger_ale" in command["result_json"]
    after = service.conn.execute("SELECT target_f FROM TEMP_ZONE WHERE id = 'zone1'").fetchone()["target_f"]
    assert after == before


def test_sensor_fault_forces_the_heater_off(tmp_path):
    service, _clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    service.submit("test", "start_batch", {"vessel_id": "vessel1", "name": "Ginger ale"}, "start-1")
    service.tick()
    assert heater_of(hardware).on is True
    probes_of(hardware).set_fault("28-0000000000b2", "missing")
    service.tick()
    assert heater_of(hardware).on is False
    kinds = [message[0] for message in notifier.messages]
    assert "sensor_fault" in kinds


def test_three_unreachable_reads_alert_when_the_heater_was_commanded_on(tmp_path):
    service, _clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    service.submit("test", "start_batch", {"vessel_id": "vessel1", "name": "Ginger ale"}, "start-1")
    service.tick()
    heater = heater_of(hardware)
    assert heater.on is True
    heater.unreachable = True
    service.tick()
    service.tick()
    service.tick()
    critical = [message for message in notifier.messages if message[0] == "heater_unreachable"]
    assert critical
    assert critical[-1][1] == "critical"


def test_state_mismatch_on_while_commanded_off_is_critical(tmp_path):
    service, _clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    heater = heater_of(hardware)
    heater.report_on = True
    service.tick()
    assert any(message[0] == "heater_state_mismatch" and message[1] == "critical" for message in notifier.messages)
    assert False in heater.set_calls


def test_squeeze_and_refrigerate_reminders_follow_the_recipe_clock(tmp_path):
    service, clock, _hardware, notifier = service_bundle(tmp_path)
    service.startup()
    service.submit("test", "start_batch", {"vessel_id": "vessel1", "name": "Ginger ale"}, "start-1")
    service.tick()
    clock.advance(12 * 3600)
    service.tick()
    assert any(message[0] == "reminder_due" and "Squeeze" in message[3] for message in notifier.messages)
    clock.advance(12 * 3600)
    service.tick()
    fridge = [message for message in notifier.messages if message[0] == "refrigerate_now"]
    assert fridge
    assert fridge[-1][1] == "action"
    clock.advance(12 * 3600)
    service.tick()
    fridge = [message for message in notifier.messages if message[0] == "refrigerate_now"]
    assert fridge[-1][1] == "critical"
    reminder = service.conn.execute(
        "SELECT id FROM REMINDER WHERE reminder_key = 'refrigerate_now'"
    ).fetchone()
    service.submit("test", "complete_reminder", {"reminder_id": reminder["id"]}, "done-1")
    service.submit("test", "set_stage", {"vessel_id": "vessel1", "stage": "refrigerated"}, "stage-1")
    before = len(notifier.messages)
    service.tick()
    clock.advance(6 * 3600)
    service.tick()
    assert not any(message[0] == "refrigerate_now" for message in notifier.messages[before:])
    open_reminder = service.conn.execute(
        "SELECT text FROM REMINDER WHERE reminder_key = 'open'"
    ).fetchone()
    assert "sink" in open_reminder["text"]


def _start(service):
    service.startup()
    service.submit("test", "start_batch", {"vessel_id": "vessel1", "name": "Ginger ale"}, "start-1")
    service.tick()


def test_a_recovered_sensor_fault_can_alert_again(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    _start(service)
    probes = probes_of(hardware)
    probes.set_fault("28-0000000000b2", "missing")
    service.tick()
    first = [message for message in notifier.messages if message[0] == "sensor_fault"]
    assert len(first) == 1
    assert first[0][2] == "Vessel 1"
    assert "temperature probe stopped reading" in first[0][3]
    assert "sensor_fault" not in first[0][3]

    probes.set_temp("28-0000000000b2", 64.0)
    service.tick()
    clock.advance(300)
    service.tick()
    status = service.conn.execute(
        "SELECT status FROM ALERT WHERE dedupe_key = 'sensor_fault:zone:zone1' ORDER BY id DESC LIMIT 1"
    ).fetchone()["status"]
    assert status == "resolved"

    probes.set_fault("28-0000000000b2", "missing")
    service.tick()
    assert len([message for message in notifier.messages if message[0] == "sensor_fault"]) == 2


def test_a_recovered_overtemp_and_unreachable_plug_can_alert_again(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    _start(service)
    probes = probes_of(hardware)
    probes.set_temp("28-0000000000b2", 85.0)
    probes.set_temp("28-0000000000a1", 70.0)
    service.tick()
    overtemp = [message for message in notifier.messages if message[0] == "overtemp_cutoff"]
    assert len(overtemp) == 1
    assert "heat mat is held off" in overtemp[0][3]

    probes.set_temp("28-0000000000b2", 70.0)
    service.tick()
    clock.advance(15 * 60)
    service.tick()
    assert (
        service.conn.execute(
            "SELECT status FROM ALERT WHERE dedupe_key = 'overtemp_cutoff:zone:zone1' ORDER BY id DESC LIMIT 1"
        ).fetchone()["status"]
        == "resolved"
    )
    probes.set_temp("28-0000000000b2", 85.0)
    service.tick()
    assert len([message for message in notifier.messages if message[0] == "overtemp_cutoff"]) == 2

    heater = heater_of(hardware)
    heater.unreachable = True
    service.tick()
    service.tick()
    service.tick()
    unreachable = [message for message in notifier.messages if message[0] == "heater_unreachable"]
    assert len(unreachable) == 1
    assert "not responding" in unreachable[0][3]
    heater.unreachable = False
    service.tick()
    assert (
        service.conn.execute(
            "SELECT status FROM ALERT WHERE dedupe_key = 'heater_unreachable:zone:zone1' ORDER BY id DESC LIMIT 1"
        ).fetchone()["status"]
        == "resolved"
    )
    heater.unreachable = True
    service.tick()
    service.tick()
    service.tick()
    assert len([message for message in notifier.messages if message[0] == "heater_unreachable"]) == 2


def test_a_cooler_below_target_alerts_once_until_it_recovers(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    _start(service)
    clock.advance(3 * 3600)
    service.tick()
    assert not any(message[0] == "temp_below_target" for message in notifier.messages)
    warning = service.conn.execute(
        "SELECT severity FROM ALERT WHERE dedupe_key = 'temp_below_target:zone:zone1'"
    ).fetchone()
    assert warning is None  # still warming up: the 3 h warning waits until the target is first reached

    clock.advance(12 * 3600)
    service.tick()
    pushes = [message for message in notifier.messages if message[0] == "temp_below_target"]
    assert len(pushes) == 1
    assert pushes[0][1] == "action"
    assert pushes[0][2] == "Vessel 1"
    assert "64°F" in pushes[0][3]
    assert "72°F" in pushes[0][3]

    probes_of(hardware).set_temp("28-0000000000b2", 72.0)
    service.tick()
    assert (
        service.conn.execute(
            "SELECT status FROM ALERT WHERE dedupe_key = 'temp_below_target:zone:zone1'"
        ).fetchone()["status"]
        == "resolved"
    )
    probes_of(hardware).set_temp("28-0000000000b2", 64.0)
    service.tick()
    clock.advance(15 * 3600)
    service.tick()
    assert len([message for message in notifier.messages if message[0] == "temp_below_target"]) == 2


def test_a_reminder_ignored_for_two_days_becomes_critical(tmp_path):
    service, clock, _hardware, notifier = service_bundle(tmp_path)
    _start(service)
    clock.advance(12 * 3600)
    service.tick()
    squeeze = [message for message in notifier.messages if message[0] == "reminder_due" and "Squeeze" in message[3]]
    assert squeeze[-1][1] == "action"
    clock.advance(36 * 3600)
    service.tick()
    squeeze = [message for message in notifier.messages if message[0] == "reminder_due" and "Squeeze" in message[3]]
    assert squeeze[-1][1] == "action"
    clock.advance(12 * 3600)
    service.tick()
    squeeze = [message for message in notifier.messages if message[0] == "reminder_due" and "Squeeze" in message[3]]
    assert squeeze[-1][1] == "critical"
    assert "rock hard" in squeeze[-1][3]


def test_stopping_and_an_unexpected_restart_are_announced(tmp_path):
    service, _clock, _hardware, notifier = service_bundle(tmp_path)
    service.startup()
    assert not any(message[0] == "service_interrupted" for message in notifier.messages)
    service.stop()
    stopping = [message for message in notifier.messages if message[0] == "service_stopping"]
    assert stopping[-1][2] == "Vessel 1"
    assert "heat mat is being turned off" in stopping[-1][3]
    notifier.messages.clear()
    service.startup()
    assert not any(message[0] == "service_interrupted" for message in notifier.messages)
    service.startup()
    interrupted = [message for message in notifier.messages if message[0] == "service_interrupted"]
    assert interrupted[-1][1] == "critical"
    assert "stopped unexpectedly" in interrupted[-1][3]
