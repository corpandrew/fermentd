from fastapi.testclient import TestClient
from tests.conftest import service_bundle

import fermentd.web.app as webapp
from fermentd.web.app import create_app


def _slow_client(tmp_path, monkeypatch):
    service, clock, hardware, _notifier = service_bundle(tmp_path)
    service.startup()
    service.tick()
    monkeypatch.setattr(webapp, "SUBMIT_WAIT_S", 0.2)
    app = create_app(service.conn, service.clock)
    return service, TestClient(app)


def test_a_slow_controller_shows_a_neutral_notice_not_an_error(tmp_path, monkeypatch):
    service, client = _slow_client(tmp_path, monkeypatch)
    response = client.post(
        "/zones/zone1/rename",
        data={"name": "Pantry", "confirm": "yes", "idempotency_key": "slow"},
        follow_redirects=False,
    )
    location = response.headers["location"]
    assert "error" not in location
    assert "pending=" in location and "notice=" in location
    page = client.get(location).text
    assert "Saved, applying" in page
    assert "did not apply" not in page
    command_id = int(location.split("pending=")[1].split("&")[0])
    assert client.get(f"/api/commands/{command_id}").json() == {"status": "pending"}
    assert service.poll_pending_commands() is True
    assert client.get(f"/api/commands/{command_id}").json() == {"status": "done"}
    assert service.conn.execute("SELECT name FROM TEMP_ZONE WHERE id = 'zone1'").fetchone()["name"] == "Pantry"


def test_a_rejected_command_reports_its_message(tmp_path, monkeypatch):
    service, client = _slow_client(tmp_path, monkeypatch)
    response = client.post(
        "/vessels/vessel1/edit",
        data={"remove": "yes", "confirm": "yes", "idempotency_key": "rm"},
        follow_redirects=False,
    )
    command_id = int(response.headers["location"].split("pending=")[1].split("&")[0])
    service.poll_pending_commands()
    body = client.get(f"/api/commands/{command_id}").json()
    assert body["status"] == "rejected"
    assert "fermentd.yaml" in body["message"]


def test_poll_is_a_no_op_without_pending_commands(tmp_path):
    service, _clock, _hardware, _notifier = service_bundle(tmp_path)
    service.startup()
    assert service.poll_pending_commands() is False


def test_unknown_command_status_is_404(tmp_path, monkeypatch):
    _service, client = _slow_client(tmp_path, monkeypatch)
    assert client.get("/api/commands/9999").status_code == 404
