from datetime import timedelta

from tests.conftest import service_bundle

from fermentd import cli
from fermentd.control.planned import marker_fresh, take_marker, write_marker
from fermentd.control.service import ControlService


def _restart(service, clock, hardware, notifier):
    return ControlService(service.config, service.conn, clock, hardware, service.profiles, notifier)


def _alert(service):
    return service.conn.execute(
        "SELECT status FROM ALERT WHERE dedupe_key = 'service_interrupted:zone:control'"
    ).fetchone()


def test_planned_restart_is_logged_without_alert_or_push(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    write_marker(service.conn, clock.now())
    service.stop()
    again = _restart(service, clock, hardware, notifier)
    again.startup()
    assert _alert(service) is None
    assert not [m for m in notifier.messages if m[0] in {"service_stopping", "service_interrupted"}]
    types = [r[0] for r in service.conn.execute("SELECT type FROM EVENT ORDER BY id")]
    assert "planned_restart" in types
    assert not marker_fresh(service.conn, clock.now())  # consumed


def test_planned_restart_killed_before_clean_stop_still_suppressed(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    write_marker(service.conn, clock.now())
    _restart(service, clock, hardware, notifier).startup()  # no stop() logged
    assert _alert(service) is None


def test_crash_without_marker_still_alerts(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    _restart(service, clock, hardware, notifier).startup()
    assert _alert(service)["status"] == "open"
    assert [m for m in notifier.messages if m[0] == "service_interrupted"]


def test_expired_marker_does_not_suppress(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    write_marker(service.conn, clock.now(), minutes=5)
    clock.advance(6 * 60)
    _restart(service, clock, hardware, notifier).startup()
    assert _alert(service)["status"] == "open"
    assert not take_marker(service.conn, clock.now())


def test_unplanned_clean_stop_pushes_stopping_but_no_interrupted_alert(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    service.stop()
    _restart(service, clock, hardware, notifier).startup()
    assert _alert(service) is None
    assert [m for m in notifier.messages if m[0] == "service_stopping"]


def test_cli_planned_restart_writes_marker_and_restarts(tmp_path, monkeypatch):
    service, clock, _h, _n = service_bundle(tmp_path)
    calls = []
    monkeypatch.setattr("subprocess.call", lambda cmd: calls.append(cmd) or 0)
    assert cli.main(["--config", str(tmp_path / "fermentd.yaml"), "planned-restart"]) == 0
    assert calls == [["sudo", "systemctl", "restart", "fermentd-control", "fermentd-web", "fermentd-mcp"]]
    from datetime import UTC, datetime

    assert marker_fresh(service.conn, datetime.now(UTC))
    assert not marker_fresh(service.conn, datetime.now(UTC) + timedelta(minutes=6))
