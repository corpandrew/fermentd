from pathlib import Path

from fermentd.drivers.actuator_tuya import TuyaPlug
from fermentd.drivers.base import ActuatorUnreachable
from fermentd.drivers.ds18b20 import Ds18b20, rate_reject
from fermentd.drivers.hx711 import Hx711Sensor
from fermentd.drivers.sim import ThermalModel


def _write_slave(root: Path, rom: str, body: str) -> None:
    device = root / rom
    device.mkdir(parents=True)
    (device / "w1_slave").write_text(body)


def test_ds18b20_reads_sysfs_and_rejects_faults(tmp_path: Path):
    root = tmp_path / "w1"
    _write_slave(
        root,
        "28-good",
        "aa : crc=aa YES\naa t=20000\n",
    )
    _write_slave(root, "28-crc", "aa : crc=aa NO\n")
    _write_slave(root, "28-boot", "aa : crc=aa YES\naa t=85000\n")
    probe = Ds18b20(root, probe_min_f=32, probe_max_f=120)

    good = probe.read("28-good")
    assert good.reject_reason is None
    assert good.temp_f is not None
    assert abs(good.temp_f - 68.0) < 0.01
    assert probe.read("28-crc").reject_reason == "crc"
    assert probe.read("28-boot").reject_reason == "power_on_default"
    assert probe.read("28-missing").reject_reason == "missing"


def test_rate_reject_flags_an_impossible_jump():
    assert rate_reject(70.0, 0.0, 80.0, 60.0, 5.0) == "rate"
    assert rate_reject(70.0, 0.0, 72.0, 60.0, 5.0) is None


class FakeOutlet:
    def __init__(self) -> None:
        self.on = False
        self.fail = False
        self.armed: tuple[int, int] | None = None
        self.switches: list[tuple[str, int]] = []
        self.dp = 1

    def turn_on(self, switch: int = 1, nowait: bool = False) -> dict:
        self.switches.append(("on", switch))
        self.dp = switch
        if self.fail:
            return {"Error": "network"}
        self.on = True
        return {"dps": {str(switch): True}}

    def turn_off(self, switch: int = 1, nowait: bool = False) -> dict:
        self.switches.append(("off", switch))
        self.dp = switch
        if self.fail:
            return {"Error": "network"}
        self.on = False
        return {"dps": {str(switch): False}}

    def status(self) -> dict:
        if self.fail:
            return {"Error": "network"}
        return {"dps": {str(self.dp): self.on}}

    def set_value(self, dp: int, value: int) -> dict:
        self.armed = (dp, value)
        return {"dps": {str(dp): value}}


def test_tuya_plug_sets_and_reads_back():
    outlet = FakeOutlet()
    plug = TuyaPlug("zone1", outlet, switch_dp=1, countdown_dp=None)
    plug.set(True)
    assert plug.read_state() is True
    plug.set(False)
    assert plug.read_state() is False
    assert plug.supports_countdown() is False
    plug.arm_countdown(60)
    assert outlet.armed is None


def test_tuya_plug_switches_the_configured_outlet():
    outlet = FakeOutlet()
    plug = TuyaPlug("strip", outlet, switch_dp=3)
    plug.set(True)
    plug.set(False)
    assert outlet.switches == [("on", 3), ("off", 3)]
    assert plug.read_state() is False


def test_ds18b20_file_and_parse_errors_are_rejected_samples(tmp_path: Path):
    root = tmp_path / "w1"
    _write_slave(root, "28-parse", "aa : crc=aa YES\naa t=nope\n")
    probe = Ds18b20(root, probe_min_f=32, probe_max_f=120)
    parsed = probe.read("28-parse")
    assert parsed.temp_f is None
    assert parsed.reject_reason == "read_error"

    blocked = root / "28-blocked"
    blocked.mkdir()
    slave = blocked / "w1_slave"
    slave.write_text("aa : crc=aa YES\naa t=20000\n")
    slave.chmod(0)
    try:
        failed = probe.read("28-blocked")
    finally:
        slave.chmod(0o644)
    assert failed.temp_f is None
    assert failed.reject_reason == "read_error"


def test_tuya_error_is_unreachable_and_countdown_arms_when_configured():
    outlet = FakeOutlet()
    outlet.fail = True
    plug = TuyaPlug("zone1", outlet, countdown_dp=9)
    try:
        plug.set(True)
        raised = False
    except ActuatorUnreachable:
        raised = True
    assert raised
    assert plug.read_state() is None
    outlet.fail = False
    assert plug.arm_countdown(900) is True
    assert outlet.armed == (9, 900)
    outlet.set_value = lambda dp, v: {"Error": "Network Error"}
    try:
        plug.arm_countdown(900)
        raised = False
    except ActuatorUnreachable:
        raised = True
    assert raised  # tinytuya reports errors as a dict, not an exception
    outlet.set_value = lambda dp, v: {"dps": {"1": True}}
    assert plug.arm_countdown(900) is False  # answered but did not echo DP 9


def test_hx711_construction_does_not_touch_gpio():
    scale = Hx711Sensor(5, 6)
    assert scale._handle is None and (scale.dout_gpio, scale.sck_gpio) == (5, 6)


def test_thermal_model_warms_only_while_the_heater_is_on():
    model = ThermalModel(temp_f=64.0, ambient_f=64.0, tau_s=7200.0, heater_gain_f_per_hour=8.0)
    model.step(3600, heater_on=False)
    assert abs(model.temp_f - 64.0) < 0.01
    model.step(3600, heater_on=True)
    assert model.temp_f > 68.0
