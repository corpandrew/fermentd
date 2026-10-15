"""Target reached, probe silent, heater stuck, fermentation slowing, heater duty cycle."""

from fastapi.testclient import TestClient
from tests.conftest import heater_of, probes_of, service_bundle

from fermentd.control.service import ControlService
from fermentd.notify.ntfy import NtfyNotifier
from fermentd.web.app import create_app
from fermentd.web.chart import hourly_duty

ROM = "28-0000000000b2"
AMB = "28-0000000000a1"


def _setup(tmp_path, temp=66.0, mutate=None):
    service, clock, hardware, notifier = service_bundle(tmp_path, mutate=mutate)
    service.startup()
    probes_of(hardware).set_temp(ROM, temp)
    probes_of(hardware).set_temp(AMB, 60.0)
    service.tick()
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    return service, clock, hardware, notifier, client


def _post(client, path, key, **data):
    return client.post(path, data={**data, "confirm": "yes", "idempotency_key": key}, follow_redirects=False)


def _jug(client):
    _post(
        client, "/vessels/vessel1/edit", "jug",
        name="Vessel 1", vessel_type="jug", temp_zone="zone1", probe_rom_id=ROM, capacity_l="3.8",
    )


def _start(client, profile_id="soda_ginger_ale"):
    _post(client, "/vessels/vessel1/start", f"start-{profile_id}", profile_id=profile_id)


def _kinds(notifier, kind):
    return [m for m in notifier.messages if m[0] == kind]


def _step(service, clock, hardware, temp, seconds=60):
    clock.advance(seconds)
    probes_of(hardware).set_temp(ROM, temp)
    probes_of(hardware).set_temp(AMB, 60.0)
    service.tick()


def test_target_reached_fires_once_with_duration_and_survives_restart(tmp_path):
    service, clock, hardware, notifier, client = _setup(tmp_path)
    _start(client)
    temp = 66.0
    while temp < 71.0:
        temp += 0.3
        _step(service, clock, hardware, temp, 300)
    assert not _kinds(notifier, "target_reached")
    _step(service, clock, hardware, 71.6, 300)
    sent = _kinds(notifier, "target_reached")
    assert len(sent) == 1
    kind, severity, title, body = sent[0]
    assert "72°F" in body and "71.6°F" in body and " h " in body or "min" in body
    assert "Vessel 1" in body or "vessel1" in body
    for _ in range(5):
        _step(service, clock, hardware, 72.1)
    assert len(_kinds(notifier, "target_reached")) == 1
    # A restart (fresh service on the same database) does not repeat it.
    again = ControlService(service.config, service.conn, clock, hardware, service.profiles, notifier)
    again.startup()
    _step(again, clock, hardware, 72.0)
    assert len(_kinds(notifier, "target_reached")) == 1


def test_target_reached_fires_again_after_a_step_to_a_new_target(tmp_path):
    service, clock, hardware, notifier, client = _setup(tmp_path, temp=72.0)
    _jug(client)
    _start(client, "ale_saison")
    _step(service, clock, hardware, 72.0)
    assert len(_kinds(notifier, "target_reached")) == 1
    clock.advance(3 * 86400 + 60)
    _step(service, clock, hardware, 72.0)
    assert service.conn.execute("SELECT target_f FROM TEMP_ZONE").fetchone()["target_f"] == 75
    assert len(_kinds(notifier, "target_reached")) == 1
    _step(service, clock, hardware, 74.8, 3600)
    sent = _kinds(notifier, "target_reached")
    assert len(sent) == 2 and "75°F" in sent[1][3] and "1 h" in sent[1][3] and "from 72°F" in sent[1][3]


def test_cold_excursions_wait_until_target_is_first_reached(tmp_path):
    service, clock, hardware, notifier, _client = None, None, None, None, None
    service, clock, hardware, notifier, client = _setup(tmp_path, temp=60.0)
    _start(client)
    for _ in range(5):  # 5 h cold start: no 3 h warning, no out-of-range push
        _step(service, clock, hardware, 60.0, 3600)
    assert not service.conn.execute(
        "SELECT 1 FROM ALERT WHERE (dedupe_key LIKE 'temp_below_target%' OR dedupe_key LIKE 'temp_out_of_range%') AND status = 'open'"
    ).fetchone()
    for _ in range(11):  # but 15 h without getting there is still pushed
        _step(service, clock, hardware, 60.0, 3600)
    assert _kinds(notifier, "temp_below_target")


def test_cold_excursion_after_reaching_target_warns_at_three_hours(tmp_path):
    service, clock, hardware, notifier, client = _setup(tmp_path, temp=72.0)
    _start(client)
    _step(service, clock, hardware, 72.0)
    for _ in range(4):
        _step(service, clock, hardware, 66.0, 3600)
    assert service.conn.execute(
        "SELECT 1 FROM ALERT WHERE dedupe_key LIKE 'temp_below_target%' AND status = 'open'"
    ).fetchone()


def test_probe_silent_alert_and_recovery(tmp_path):
    service, clock, hardware, notifier, client = _setup(tmp_path, temp=70.0)
    _start(client)
    probes_of(hardware).set_fault(ROM, "crc")
    clock.advance(60)
    service.tick()
    assert not _kinds(notifier, "probe_silent")
    assert heater_of(hardware).on is False
    for _ in range(2):
        clock.advance(40)
        service.tick()
    sent = _kinds(notifier, "probe_silent")
    assert len(sent) == 1 and sent[0][1] == "action" and "crc" in sent[0][3]
    clock.advance(60)
    service.tick()
    assert len(_kinds(notifier, "probe_silent")) == 1
    _step(service, clock, hardware, 70.0)
    rec = _kinds(notifier, "probe_recovered")
    assert len(rec) == 1 and "70.0°F" in rec[0][3]
    assert not service.conn.execute(
        "SELECT 1 FROM ALERT WHERE dedupe_key LIKE 'probe_silent%' AND status = 'open'"
    ).fetchone()


def test_heater_stuck_alert_is_rate_limited(tmp_path):
    service, clock, hardware, notifier, client = _setup(tmp_path, temp=66.0)
    _start(client)
    for _ in range(50):  # 50 min on, no rise
        _step(service, clock, hardware, 66.0)
    sent = _kinds(notifier, "heater_stuck")
    assert len(sent) == 1 and "on the mat" in sent[0][3]
    for _ in range(60):
        _step(service, clock, hardware, 66.0)
    assert len(_kinds(notifier, "heater_stuck")) == 1  # within the 3 h repeat window


def test_heater_warming_normally_is_not_stuck(tmp_path):
    service, clock, hardware, notifier, client = _setup(tmp_path, temp=60.0)
    _start(client)
    temp = 60.0
    for _ in range(100):
        temp += 0.03
        _step(service, clock, hardware, temp)
    assert not _kinds(notifier, "heater_stuck")


def test_fermentation_slowing_fires_once_per_batch(tmp_path):
    def mutate(data):
        data["vessels"][0]["scale"] = {"driver": "sim"}
        data["vessels"][0]["vessel_type"] = "jug"

    service, clock, hardware, notifier, client = _setup(tmp_path, temp=64.0, mutate=mutate)
    scale = hardware.scales["vessel1"]
    scale.grams = 0
    _post(client, "/vessels/vessel1/scale/tare", "t")
    scale.grams = 1000
    _post(client, "/vessels/vessel1/scale/calibrate", "c", grams="1000")
    scale.grams = 4500.0
    _start(client, "cider_french_brut")
    for step in range(5 * 24 * 12):
        hours = step / 12
        # fast for two days, then a long slow tail at about 5% of the peak rate
        scale.grams = 4500.0 - (100 * min(hours, 48) / 48) - max(0.0, hours - 48) * 0.1
        clock.advance(300)
        probes_of(hardware).set_temp(ROM, 64.0)
        service.tick()
    sent = _kinds(notifier, "fermentation_slowing")
    assert len(sent) == 1 and "hydrometer" in sent[0][3] and "bottle" in sent[0][3]
    assert service.conn.execute("SELECT slowing_notified_at FROM BATCH").fetchone()[0]


def test_ntfy_pushes_info_progress_kinds():
    posts = []
    ntfy = NtfyNotifier("topic", post=lambda url, body, headers, *a: posts.append(body))
    ntfy.notify("target_reached", "info", "t", "reached")
    ntfy.notify("auto_target", "info", "t", "quiet")
    assert posts == ["reached"]


def test_duty_cycle_on_chart_and_page(tmp_path):
    service, clock, hardware, notifier, client = _setup(tmp_path, temp=66.0)
    _start(client)
    for i in range(180):
        _step(service, clock, hardware, 66.0 if i < 90 else 75.0)
    rows = service.conn.execute("SELECT ts, heater_on FROM READING ORDER BY ts").fetchall()
    duty = hourly_duty([dict(r) for r in rows])
    assert max(d for _h, d in duty) >= 0.9 and min(d for _h, d in duty) == 0.0
    page = client.get("/vessels/vessel1").text
    assert "data-duty" in page and "On, last 24 h" in page and 'class="duty"' in page
    assert "% on per hour" in page
