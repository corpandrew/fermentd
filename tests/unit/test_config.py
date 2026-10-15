from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from fermentd.config import load_config

EXAMPLE = Path("config/fermentd.example.yaml")


def test_example_config_loads():
    cfg = load_config(EXAMPLE)
    assert cfg.profiles.default_profile == "soda_ginger_ale"
    assert cfg.vessels[0].name == "Vessel 1"
    assert cfg.vessels[0].hx711 is None
    assert cfg.temp_zones[0].heater.driver == "sim"
    assert cfg.site.timezone == "America/New_York"
    assert cfg.digest.weekday == "sunday"
    assert cfg.digest.time == "09:00"


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "fermentd.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def _base() -> dict:
    return yaml.safe_load(EXAMPLE.read_text())


def test_unknown_key_is_rejected(tmp_path: Path):
    data = _base()
    data["site"]["nope"] = 1
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, data))


def test_unknown_zone_is_rejected(tmp_path: Path):
    data = _base()
    data["vessels"][0]["temp_zone"] = "missing"
    with pytest.raises(ValidationError, match="unknown temperature zone"):
        load_config(_write(tmp_path, data))


def test_duplicate_gpio_is_rejected(tmp_path: Path):
    data = _base()
    data["vessels"][0]["hx711"] = {"dout_gpio": 4, "sck_gpio": 6}
    with pytest.raises(ValidationError, match="GPIO 4"):
        load_config(_write(tmp_path, data))


def test_cutoff_cannot_be_loosened(tmp_path: Path):
    data = _base()
    data["safety"]["cutoff_f"] = 90
    with pytest.raises(ValidationError, match="cutoff_f"):
        load_config(_write(tmp_path, data))
