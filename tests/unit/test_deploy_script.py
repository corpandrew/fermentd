"""scripts/deploy.sh: valid bash, and the stale-session patterns hit only stdio MCP sessions."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path("scripts/deploy.sh")


def _pattern(name: str) -> str:
    match = re.search(rf"^{name}='([^']+)'$", SCRIPT.read_text(), flags=re.M)
    assert match, name
    return match.group(1)


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash")
def test_script_is_valid_bash():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0


def test_pi_pattern_matches_stdio_but_not_http_or_itself():
    pat = re.compile(_pattern("PI_STDIO_PATTERN"))
    assert pat.search(".venv/bin/python -m fermentd.mcp --db data/fermentd.db")
    assert not pat.search(
        "/home/pi/fermentd/.venv/bin/python3 /home/pi/fermentd/.venv/bin/fermentd-mcp --http --host 100.64.0.1"
    )
    assert not pat.search("bash -c pkill -f '[p]ython -m fermentd.mcp --db'")


def test_local_pattern_matches_only_ssh_mcp_sessions():
    pat = re.compile(_pattern("LOCAL_STDIO_PATTERN"))
    assert pat.search(
        "ssh -T fermentd cd /home/pi/fermentd && exec .venv/bin/python -m fermentd.mcp --db data/fermentd.db"
    )
    assert not pat.search("ssh fermentd cd fermentd && .venv/bin/pip install -q -e .")
    assert not pat.search("ssh -T otherhost python -m fermentd.mcp --db x")


def test_stale_sessions_are_ended_after_the_planned_restart():
    text = SCRIPT.read_text()
    assert text.index("planned-restart") < text.index("pkill -f '$PI_STDIO_PATTERN'") < text.index(
        'pkill -f "$LOCAL_STDIO_PATTERN"'
    )


@pytest.mark.skipif(shutil.which("bash") is None, reason="no bash")
def test_install_units_renders_one_home_layout_with_no_placeholders_left():
    env = {"PATH": "/usr/bin:/bin", "DRY_RUN": "1", "FERMENTD_USER": "pi", "FERMENTD_DIR": "/home/pi/fermentd"}
    out = subprocess.run(["bash", "scripts/install-units.sh"], env=env, capture_output=True, text=True, check=True)
    text = out.stdout
    assert "@USER@" not in text and "@APP_DIR@" not in text and "/opt/fermentd" not in text
    assert text.count("User=pi") == 5
    assert "ExecStart=/home/pi/fermentd/.venv/bin/fermentd-web --config /home/pi/fermentd/config/fermentd.yaml" in text
    assert "EnvironmentFile=-/home/pi/fermentd/config/fermentd.env" in text
