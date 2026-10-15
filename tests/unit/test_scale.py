from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from tests.conftest import probes_of, service_bundle

from fermentd.config import FermentdConfig
from fermentd.control.weight import fermentation_loss, weight_summary
from fermentd.drivers import hx711
from fermentd.drivers.base import ScaleUnavailable
from fermentd.drivers.hx711 import Hx711Sensor, median_filter, to_signed
from fermentd.web.app import create_app

GOOD_SCALE = {"driver": "sim"}


def _with_scale(scale):
    def mutate(data):
        data["vessels"][0]["scale"] = scale
        data["vessels"][0]["vessel_type"] = "jug"

    return mutate


def _setup(tmp_path, scale=GOOD_SCALE):
    service, clock, hardware, notifier = service_bundle(tmp_path, mutate=_with_scale(scale))
    service.startup()
    probes_of(hardware).set_temp("28-0000000000b2", 64.0)
    probes_of(hardware).set_temp("28-0000000000a1", 62.0)
    service.tick()
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    return service, clock, hardware, notifier, client


def _base_config():
    return yaml.safe_load(Path("config/fermentd.example.yaml").read_text())


def test_scale_config_defaults_legacy_key_and_pin_conflicts():
    data = _base_config()
    data["vessels"][0]["scale"] = {"driver": "hx711"}
    scale = FermentdConfig.model_validate(data).vessels[0].scale
    assert (scale.dout_gpio, scale.sck_gpio, scale.sample_interval_s) == (5, 6, 300)
    data["vessels"][0]["scale"] = {"driver": "hx711", "dout_gpio": 4}
    with pytest.raises(ValueError, match="GPIO 4"):
        FermentdConfig.model_validate(data)  # the DS18B20 1-Wire bus
    data["vessels"][0]["scale"] = None
    data["vessels"][0]["hx711"] = {"dout_gpio": 5, "sck_gpio": 6}
    assert FermentdConfig.model_validate(data).vessels[0].scale.driver == "hx711"


def test_hx711_helpers_and_median_rejects_spikes():
    assert to_signed(0x7FFFFF) == 8388607 and to_signed(0xFFFFFF) == -1 and to_signed(0x800000) == -8388608
    assert median_filter([100, 101, 99, 100, 9_000_000, -5_000_000, 100, 102], 8) == 100.0
    with pytest.raises(ScaleUnavailable):
        median_filter([1, 2], 15)


class FakeLgpio:
    """Shifts out a 24-bit value on DOUT, MSB first, one bit per SCK pulse, like the HX711."""

    def __init__(self, value: int, ready: bool = True) -> None:
        self.value, self.ready, self.pulses, self.sck = value, ready, 0, 0

    def gpiochip_open(self, chip):
        return 1

    def gpio_claim_output(self, h, pin, level):
        return 0

    def gpio_claim_input(self, h, pin):
        return 0

    def gpiochip_close(self, h):
        return 0

    def gpio_write(self, h, pin, level):
        if self.sck == 1 and level == 0:
            self.pulses += 1
        self.sck = level

    def gpio_read(self, h, pin):
        if not self.ready:
            return 1
        if self.pulses == 0 or self.pulses >= 25:
            self.pulses = 0
            return 0  # DOUT low: next sample ready
        return (self.value >> (24 - self.pulses)) & 1


@pytest.mark.parametrize("value", [0x0ABCDE, 0xF00001])
def test_hx711_bitbang_reads_signed_24_bit(monkeypatch, value):
    monkeypatch.setattr(hx711, "_load_lgpio", lambda: FakeLgpio(value))
    assert Hx711Sensor(5, 6, samples=5).read_raw() == float(to_signed(value))


def test_hx711_without_hardware_is_not_connected(monkeypatch):
    monkeypatch.setattr(hx711, "_load_lgpio", lambda: FakeLgpio(0, ready=False))
    monkeypatch.setattr(hx711, "READY_TIMEOUT_S", 0.01)
    with pytest.raises(ScaleUnavailable, match="no data"):
        Hx711Sensor(5, 6, samples=3).read_raw()


def test_missing_scale_hardware_never_crashes_the_controller(tmp_path, monkeypatch):
    def no_lgpio():
        raise ScaleUnavailable("lgpio is not installed")

    monkeypatch.setattr(hx711, "_load_lgpio", no_lgpio)
    service, clock, _hw, _n, client = _setup(tmp_path, {"driver": "hx711"})
    row = service.conn.execute("SELECT status, status_detail FROM SCALE WHERE vessel_id = 'vessel1'").fetchone()
    assert row["status"] == "not_connected" and "lgpio" in row["status_detail"]
    page = client.get("/vessels/vessel1").text
    assert "Scale not connected" in page
    response = client.post(
        "/vessels/vessel1/scale/tare", data={"confirm": "yes", "idempotency_key": "t1"}, follow_redirects=False
    )
    assert "Scale+not+connected" in response.headers["location"]


def _tare_and_calibrate(client, scale):
    scale.grams = 0
    assert (
        client.post("/vessels/vessel1/scale/tare", data={"confirm": "yes", "idempotency_key": "t"}).status_code == 200
    )
    scale.grams = 1000
    client.post("/vessels/vessel1/scale/calibrate", data={"grams": "1000", "confirm": "yes", "idempotency_key": "c"})


def test_calibration_is_stored_in_the_database(tmp_path):
    service, _clock, hardware, _n, client = _setup(tmp_path)
    scale = hardware.scales["vessel1"]
    _tare_and_calibrate(client, scale)
    row = service.conn.execute("SELECT * FROM SCALE WHERE vessel_id = 'vessel1'").fetchone()
    assert row["tare_offset"] == scale.zero_counts
    assert row["counts_per_gram"] == pytest.approx(scale.counts_per_gram)
    assert row["status"] == "ok" and row["cal_weight_g"] == 1000
    bad = client.post(
        "/vessels/vessel1/scale/calibrate",
        data={"grams": "20", "confirm": "yes", "idempotency_key": "c2"},
        follow_redirects=False,
    )
    assert "error=" in bad.headers["location"]


def test_fermentation_curve_estimates_and_quiet_alert(tmp_path):
    service, clock, hardware, notifier, client = _setup(tmp_path)
    scale = hardware.scales["vessel1"]
    _tare_and_calibrate(client, scale)
    scale.grams = 4500.0
    client.post(
        "/vessels/vessel1/start",
        data={"profile_id": "cider_french_brut", "confirm": "yes", "idempotency_key": "b1"},
    )
    batch_id = service.conn.execute("SELECT id FROM BATCH WHERE ended_at IS NULL").fetchone()["id"]
    reads_before = scale.reads
    lost_total = 150.0  # about 5% ABV in 3.785 L
    for step in range(int(6 * 24 * 12)):  # six days of 5-minute samples
        hours = step / 12
        scale.grams = 4500.0 - lost_total * min(1.0, hours / 72)
        if step >= 300:
            scale.grams -= 100.0  # a hydrometer sample pulled at hour 25
        clock.advance(300)
        probes_of(hardware).set_temp("28-0000000000b2", 64.0)
        service.tick()
    samples = scale.reads - reads_before
    assert 6 * 24 * 12 - 5 <= samples <= 6 * 24 * 12 + 5  # one per 5 minutes, not one per tick
    summary = weight_summary(service.conn, batch_id)
    assert summary["lost_g"] == pytest.approx(lost_total, abs=3)  # the 100 g sample step is ignored
    assert summary["abv"] == pytest.approx(lost_total / 3.785 / 7.9, abs=0.1)
    assert summary["state"] == "stable"
    quiet = [m for m in notifier.messages if m[0] == "fermentation_quiet"]
    assert len(quiet) == 1 and quiet[0][1] == "action" and "hydrometer" in quiet[0][3]
    page = client.get("/vessels/vessel1").text
    for text in ("Lost since start", "ABV (est.)", "g/day", "wchart", "data-weight-hint", "48 hours"):
        assert text in page, text


def test_fermentation_loss_ignores_handling_steps():
    from datetime import UTC, datetime, timedelta

    t = datetime(2026, 1, 1, tzinfo=UTC)
    points = [(t + timedelta(minutes=5 * i), g) for i, g in enumerate([1000, 998, 996, 896, 894, 994, 992])]
    lost, _ = fermentation_loss(points)
    assert lost == 8
