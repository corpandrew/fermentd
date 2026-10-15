from fastapi.testclient import TestClient
from tests.conftest import probes_of, service_bundle

from fermentd.web.app import create_app

ROM = "28-0000000000b2"


def _setup(tmp_path, temp=66.0):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    probes_of(hardware).set_temp(ROM, temp)
    probes_of(hardware).set_temp("28-0000000000a1", temp)
    service.tick()
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    return service, clock, hardware, notifier, client


def _post(client, path, key, **data):
    return client.post(path, data={**data, "confirm": "yes", "idempotency_key": key}, follow_redirects=False)


def _jug(client):
    _post(
        client,
        "/vessels/vessel1/edit",
        "jug",
        name="Vessel 1",
        vessel_type="jug",
        temp_zone="zone1",
        probe_rom_id=ROM,
        capacity_l="3.8",
    )


def _start(client, profile_id):
    _post(client, "/vessels/vessel1/start", f"start-{profile_id}", profile_id=profile_id)


def _zone_target(service):
    return service.conn.execute("SELECT target_f FROM TEMP_ZONE WHERE id = 'zone1'").fetchone()["target_f"]


def test_idle_vessel_shows_idle_not_holding(tmp_path):
    _service, _clock, _hw, _n, client = _setup(tmp_path)
    page = client.get("/").text
    assert "Holding" not in page and "data-idle" in page and "Target 72" not in page
    _start(client, "soda_ginger_ale")
    page = client.get("/").text
    assert "Holding 72°F" in page and "data-idle" not in page


def test_target_can_be_changed_within_the_profile_range_and_is_audited(tmp_path):
    service, _clock, _hw, _n, client = _setup(tmp_path)
    _jug(client)
    _start(client, "ale_pale")
    page = client.get("/vessels/vessel1").text
    assert 'name="target_f"' in page and 'max="70.0"' in page
    response = _post(client, "/vessels/vessel1/target", "t68", target_f="68")
    assert "error" not in response.headers["location"]
    assert _zone_target(service) == 68
    assert service.conn.execute("SELECT target_temp_f FROM BATCH").fetchone()["target_temp_f"] == 68
    audit = service.conn.execute("SELECT * FROM AUDIT_LOG WHERE action = 'set_target_temp'").fetchone()
    assert audit["new_value"] == "68.0"
    response = _post(client, "/vessels/vessel1/target", "t74", target_f="74")
    assert "error" in response.headers["location"]
    assert _zone_target(service) == 68
    response = _post(client, "/vessels/vessel1/target", "t80", target_f="80")
    assert "error" in response.headers["location"]


def test_gravity_log_shows_abv_attenuation_and_stability(tmp_path):
    service, clock, _hw, _n, client = _setup(tmp_path)
    _jug(client)
    _start(client, "ale_pale")
    assert "error" in _post(client, "/vessels/vessel1/gravity", "bad", sg="12").headers["location"]
    _post(client, "/vessels/vessel1/gravity", "g1", sg="1.052", sample_temp_f="66")
    clock.advance(7 * 86400)
    service.tick()
    _post(client, "/vessels/vessel1/gravity", "g2", sg="1.013")
    page = client.get("/vessels/vessel1").text
    assert "Still dropping" in page
    clock.advance(2 * 86400 + 60)
    service.tick()
    _post(client, "/vessels/vessel1/gravity", "g3", sg="1.012")
    page = client.get("/vessels/vessel1").text
    assert "1.052" in page and "5.3%" in page and "77%" in page
    assert "Stable: 1.013 → 1.012" in page
    assert service.conn.execute("SELECT og FROM BATCH").fetchone()["og"] == 1.052


def test_lager_stage_steps_the_target_automatically(tmp_path):
    service, _clock, _hw, _n, client = _setup(tmp_path, temp=50.0)
    _jug(client)
    _start(client, "lager_pilsner")
    assert _zone_target(service) == 50
    _post(client, "/vessels/vessel1/stage", "dr", stage="diacetyl_rest")
    assert _zone_target(service) == 60
    row = service.conn.execute("SELECT * FROM AUDIT_LOG WHERE action = 'auto_target'").fetchone()
    assert row["new_value"] == "60.0" and "stage:diacetyl_rest" in row["target"]
    _post(client, "/vessels/vessel1/stage", "lag", stage="lagering")
    assert _zone_target(service) == 50


def test_saison_ramps_after_three_days_once(tmp_path):
    service, clock, _hw, notifier, client = _setup(tmp_path, temp=72.0)
    _jug(client)
    _start(client, "ale_saison")
    assert _zone_target(service) == 72
    clock.advance(2 * 86400)
    service.tick()
    assert _zone_target(service) == 72
    clock.advance(86400 + 60)
    service.tick()
    assert _zone_target(service) == 75
    assert any(kind == "auto_target" for kind, *_ in notifier.messages)
    _post(client, "/vessels/vessel1/target", "back", target_f="73")
    service.tick()
    assert _zone_target(service) == 73  # a manual change is not overridden by the ramp again


def test_out_of_range_temperature_raises_an_action_alert(tmp_path):
    service, clock, hardware, notifier, client = _setup(tmp_path, temp=50.0)
    _jug(client)
    _start(client, "lager_pilsner")
    probes_of(hardware).set_temp(ROM, 70.0)
    service.tick()
    clock.advance(121 * 60)
    probes_of(hardware).set_temp(ROM, 70.0)
    service.tick()
    alerts = [m for m in notifier.messages if m[0] == "temp_out_of_range"]
    assert alerts and alerts[0][1] == "action" and "cannot cool" in alerts[0][3]
    probes_of(hardware).set_temp(ROM, 55.0)
    service.tick()
    open_alerts = service.conn.execute(
        "SELECT * FROM ALERT WHERE dedupe_key LIKE 'temp_out_of_range%' AND status = 'open'"
    )
    assert open_alerts.fetchone() is None


def test_soda_fridge_reminder_is_pushed(tmp_path):
    service, clock, _hw, notifier, client = _setup(tmp_path, temp=72.0)
    _start(client, "soda_ginger_ale")
    clock.advance(24 * 3600 + 60)
    service.tick()
    kinds = {m[0] for m in notifier.messages if m[1] in {"action", "critical"}}
    assert "refrigerate_now" in kinds
