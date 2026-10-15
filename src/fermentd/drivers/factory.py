"""Build drivers from config. sim and tuya share the Actuator protocol."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fermentd.config import FermentdConfig, Secrets
from fermentd.drivers.actuator_tuya import TuyaPlug, outlet_device
from fermentd.drivers.base import Actuator, TempSensor, WeightSensor
from fermentd.drivers.ds18b20 import Ds18b20
from fermentd.drivers.hx711 import Hx711Sensor
from fermentd.drivers.sim import SimHeater, SimProbeBank, SimScale


@dataclass
class Hardware:
    probes: TempSensor
    heaters: dict[str, Actuator]
    scales: dict[str, WeightSensor]
    sim_probes: SimProbeBank | None = None


def build_hardware(config: FermentdConfig, secrets: Secrets) -> Hardware:
    drivers = {zone.heater.driver for zone in config.temp_zones}
    if drivers <= {"sim", "none"}:
        bank = SimProbeBank()
        for rom in [config.one_wire.ambient_probe, *[v.probe_rom_id for v in config.vessels]]:
            if rom:
                bank.set_temp(rom, 64.0)
        heaters: dict[str, Actuator] = {}
        for zone in config.temp_zones:
            if zone.heater.driver == "none":
                continue
            heaters[zone.id] = SimHeater(zone.id)
        return Hardware(probes=bank, heaters=heaters, scales=_scales(config), sim_probes=bank)

    probes = Ds18b20(
        Path(config.one_wire.sysfs_root),
        config.safety.probe_min_f,
        config.safety.probe_max_f,
    )
    heaters = {}
    for zone in config.temp_zones:
        heater = zone.heater
        if heater.driver == "none":
            continue
        if heater.driver != "tuya":
            raise ValueError(f"zone {zone.id} driver {heater.driver} is not implemented")
        if not heater.device_id_ref or not heater.ip:
            raise ValueError(f"zone {zone.id} tuya heater needs device_id_ref and ip")
        secret = secrets.tuya.get(heater.device_id_ref)
        if secret is None:
            raise ValueError(f"secrets.yaml has no tuya entry {heater.device_id_ref}")
        device = outlet_device(secret.device_id, heater.ip, secret.local_key, heater.protocol_version)
        heaters[zone.id] = TuyaPlug(
            zone.id,
            device,
            switch_dp=heater.switch_dp,
            countdown_dp=heater.countdown_dp,
        )
    return Hardware(probes=probes, heaters=heaters, scales=_scales(config))


def _scales(config: FermentdConfig) -> dict[str, WeightSensor]:
    """Only builds driver objects; nothing touches GPIO until the first read."""
    scales: dict[str, WeightSensor] = {}
    for vessel in config.vessels:
        scale = vessel.scale
        if scale is None or scale.driver == "none":
            continue
        if scale.driver == "sim":
            scales[vessel.id] = SimScale()
        else:
            scales[vessel.id] = Hx711Sensor(scale.dout_gpio, scale.sck_gpio, scale.samples)
    return scales
