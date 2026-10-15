from pathlib import Path

import yaml

from fermentd.cli import main


def test_heaters_off_runs_when_the_secrets_file_is_broken(tmp_path: Path, capsys):
    data = yaml.safe_load(Path("config/fermentd.example.yaml").read_text())
    data["database"]["path"] = str(tmp_path / "fermentd.db")
    secrets = tmp_path / "secrets.yaml"
    secrets.write_text(
        "tuya:\n"
        "  teckin_mat:\n"
        "    device_id: abc\n"
        "    local_key: def\n"
        "topic: leaked-topic\n"
        "server: https://ntfy.sh\n"
    )
    data["secrets"] = str(secrets)
    config = tmp_path / "fermentd.yaml"
    config.write_text(yaml.safe_dump(data))
    assert main(["--config", str(config), "heaters-off", "--all"]) == 0
    assert "off" in capsys.readouterr().out


def test_heaters_off_and_probes_use_the_simulator(tmp_path: Path, capsys):
    data = yaml.safe_load(Path("config/fermentd.example.yaml").read_text())
    data["database"]["path"] = str(tmp_path / "fermentd.db")
    config = tmp_path / "fermentd.yaml"
    config.write_text(yaml.safe_dump(data))
    assert main(["--config", str(config), "heaters-off", "--all"]) == 0
    probes = capsys.readouterr().out
    assert "off" in probes
    assert main(["--config", str(config), "probes"]) == 0
    listed = capsys.readouterr().out
    assert "28-0000000000b2" in listed
    assert main(["--config", str(config), "plug-test", "zone1"]) == 0
