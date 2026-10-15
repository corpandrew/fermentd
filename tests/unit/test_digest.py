from datetime import UTC, datetime, timedelta

from tests.conftest import probes_of, service_bundle

from fermentd.control.digest import digest_slot
from fermentd.timefmt import isoformat


def test_sunday_morning_et_is_the_digest_slot_and_a_later_day_is_late():
    sunday = datetime(2026, 10, 18, 13, 0, tzinfo=UTC)
    digest_id, _slot, late = digest_slot(sunday, "America/New_York", "sunday", "09:00")
    assert digest_id == "2026-W42"
    assert late is False

    before = datetime(2026, 10, 18, 12, 59, tzinfo=UTC)
    earlier_id, _slot, earlier_late = digest_slot(before, "America/New_York", "sunday", "09:00")
    assert earlier_id == "2026-W41"
    assert earlier_late is True


def test_hours_in_stage_stay_positive_when_the_batch_starts_after_the_digest_slot(tmp_path):
    service, clock, _hardware, notifier = service_bundle(tmp_path)
    service.startup()
    service.submit(
        "test",
        "start_batch",
        {"vessel_id": "vessel1", "name": "Ginger ale", "profile_id": "soda_ginger_ale"},
        "start-1",
    )
    service.tick()
    service.conn.execute("DELETE FROM DIGEST_LOG")
    service.conn.commit()
    clock.advance(5 * 3600)
    future = isoformat(clock.now() + timedelta(days=1))
    batch_id = service.conn.execute("SELECT id FROM BATCH").fetchone()["id"]
    service.conn.execute(
        """
        INSERT INTO AUDIT_LOG (ts, actor, action, target, old_value, new_value)
        VALUES (?, 'test', 'set_stage', ?, 'in_bottle', 'refrigerated')
        """,
        (future, f"batch:{batch_id}"),
    )
    _digest_id, slot, _late = digest_slot(clock.now(), "America/New_York", "sunday", "09:00")
    service.conn.execute(
        """
        INSERT INTO READING (ts, vessel_id, vessel_temp_f, ambient_temp_f, heater_on, flags)
        VALUES (?, 'vessel1', 71.2, 60.0, 1, 0)
        """,
        (isoformat(slot - timedelta(days=1)),),
    )
    service.conn.commit()
    probes_of(service.hardware).set_fault("28-0000000000b2", "missing")
    notifier.messages.clear()
    service.tick()
    body = next(message[3] for message in notifier.messages if message[0] == "digest")
    assert "5.0 h in this stage" in body
    assert "71.2°F average" in body
    assert "Squeeze the plastic seltzer bottle" in body
    assert "temperature probe stopped reading" in body
