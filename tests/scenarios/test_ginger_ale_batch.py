from tests.conftest import service_bundle

from fermentd.demo import run_ginger_ale


def test_simulated_ginger_ale_batch_reaches_the_fridge(tmp_path):
    service, clock, _hardware, _notifier = service_bundle(tmp_path)
    result = run_ginger_ale(service, clock)
    assert result["name"] == "Ginger ale"
    assert result["stage"] == "refrigerated"
    assert result["cutoff"] is False
    assert result["longest_on_minutes"] < 240
    assert 70.0 <= result["final_temp_f"] <= 73.0
    assert result["w42_digests"] == 1
    assert result["refrigerate_status"] == "completed"
    open_reminder = service.conn.execute("SELECT due_at FROM REMINDER WHERE reminder_key = 'open'").fetchone()
    assert open_reminder is not None
    notices = [message for message in _notifier.messages if message[0] == "refrigerate_now"]
    assert any(message[1] == "action" for message in notices)
    assert any(message[1] == "critical" for message in notices)
