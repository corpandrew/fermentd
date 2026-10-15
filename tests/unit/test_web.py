from fastapi.testclient import TestClient
from tests.conftest import probes_of, service_bundle

from fermentd.web.app import create_app


def test_dashboard_starts_a_ginger_ale_batch_and_shows_it(tmp_path):
    service, _clock, _hardware, _notifier = service_bundle(tmp_path)
    service.startup()
    app = create_app(service.conn, service.clock, pump=service.tick)
    client = TestClient(app)
    assert client.get("/healthz").json() == {"ok": True}
    page = client.get("/")
    assert page.status_code == 200
    assert "Ginger ale" in page.text
    started = client.post(
        "/vessels/vessel1/start",
        data={"name": "Ginger ale", "confirm": "yes", "idempotency_key": "web-start"},
        follow_redirects=False,
    )
    assert started.status_code == 303
    vessel = client.get("/vessels/vessel1")
    assert vessel.status_code == 200
    assert "Carbonating in the bottles" in vessel.text
    assert "in_bottle" not in vessel.text
    assert "glass" in vessel.text.lower()
    status = client.get("/api/status").json()
    assert status["vessels"][0]["batch"]["profile_id"] == "soda_ginger_ale"
    assert status["vessels"][0]["batch"]["stage"] == "in_bottle"


def test_dashboard_action_survives_when_the_controller_clock_is_ahead(tmp_path):
    """The demo clock runs ahead of the wall clock. A click must still be applied."""
    service, clock, hardware, _notifier = service_bundle(tmp_path)
    service.startup()
    service.submit(
        "test",
        "start_batch",
        {"vessel_id": "vessel1", "name": "Ginger ale", "profile_id": "soda_ginger_ale"},
        "start-1",
    )
    probes_of(hardware).set_temp("28-0000000000b2", 71.0)
    probes_of(hardware).set_temp("28-0000000000a1", 64.0)
    service.tick()
    clock.advance(36 * 3600)
    service.tick()
    alert_id = service.conn.execute("SELECT id FROM ALERT WHERE status = 'open' LIMIT 1").fetchone()["id"]
    app = create_app(service.conn, pump=lambda: None)
    client = TestClient(app)
    started = client.post(
        f"/alerts/{alert_id}/ack",
        data={"confirm": "yes", "idempotency_key": "web-ack"},
        follow_redirects=False,
    )
    assert started.status_code == 303
    clock.advance(60)
    service.tick()
    command = service.conn.execute(
        "SELECT status FROM COMMAND WHERE idempotency_key = 'web-ack'"
    ).fetchone()
    assert command["status"] == "done"
    assert service.conn.execute("SELECT status FROM ALERT WHERE id = ?", (alert_id,)).fetchone()["status"] == "acked"


def test_dashboard_uses_plain_language(tmp_path):
    # Plain thermostat so the 12-hour clock jump below does not leave a timed burst running.
    service, clock, hardware, _notifier = service_bundle(
        tmp_path, mutate=lambda d: d["control"].setdefault("tuning", {}).update({"vessel1": {"mode": "onoff"}})
    )
    service.startup()
    service.submit(
        "test",
        "start_batch",
        {"vessel_id": "vessel1", "name": "Ginger ale", "profile_id": "soda_ginger_ale"},
        "start-1",
    )
    probes_of(hardware).set_temp("28-0000000000b2", 71.6)
    probes_of(hardware).set_temp("28-0000000000a1", 64.0)
    service.tick()
    clock.advance(12 * 3600)
    service.tick()
    app = create_app(service.conn, service.clock, pump=service.tick)
    client = TestClient(app)
    page = client.get("/")
    assert page.status_code == 200
    assert "http-equiv=\"refresh\"" not in page.text
    css = client.get("/static/dashboard.css")
    assert css.status_code == 200
    assert "cursor: pointer" in css.text
    assert "Bottle and room temperature over the last day" in page.text
    assert "12h 0m since start" in page.text
    assert "Squeeze the plastic seltzer bottle" in page.text
    assert "Needs attention" in page.text
    assert "Carbonating in the bottles" in page.text
    assert "71.6°F" in page.text
    assert "Holding 72°F" in page.text
    assert "Last reading" in page.text
    assert "squeeze:batch" not in page.text
    assert "bottle_group" not in page.text
    alert_id = service.conn.execute("SELECT id FROM ALERT WHERE status = 'open'").fetchone()["id"]
    acked = client.post(
        f"/alerts/{alert_id}/ack",
        data={"confirm": "yes", "idempotency_key": "ack-plain"},
        follow_redirects=True,
    )
    assert "Needs attention" not in acked.text
    assert "Acknowledged" not in acked.text
    assert "Acknowledge</button>" not in acked.text
    assert "Squeeze the plastic seltzer bottle" in acked.text
    vessel = client.get("/vessels/vessel1")
    assert "Needs attention" not in vessel.text


def test_a_rejected_action_explains_itself(tmp_path):
    service, _clock, _hardware, _notifier = service_bundle(tmp_path)
    service.startup()
    service.tick()
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    page = client.post(
        "/alerts/999/ack",
        data={"confirm": "yes", "idempotency_key": "missing"},
        follow_redirects=True,
    )
    assert page.status_code == 200
    assert "no longer there" in page.text.lower()


def test_unconfirmed_post_is_rejected(tmp_path):
    service, _clock, _hardware, _notifier = service_bundle(tmp_path)
    service.startup()
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    response = client.post(
        "/vessels/vessel1/start",
        data={"name": "Ginger ale", "confirm": "no", "idempotency_key": "nope"},
    )
    assert response.status_code == 400
