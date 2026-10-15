import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from fermentd.clock import ManualClock
from fermentd.config import load_secrets
from fermentd.db.connection import connect
from fermentd.db.migrate import migrate
from fermentd.notify.fanout import build_notifier
from fermentd.notify.ntfy import NtfyNotifier
from fermentd.notify.outbox import OutboxNotifier


def test_action_and_digest_are_posted_and_warnings_are_not():
    sent = []

    def post(url, body, headers):
        sent.append((url, body, headers))

    notifier = NtfyNotifier("ginger-ale-topic", post=post)
    notifier.notify("reminder_due", "action", "Ginger ale", "Squeeze the bottle.")
    notifier.notify("probe_fault", "warning", "zone1", "{}")
    notifier.notify("digest", "info", "2026-W42", "weekly")
    notifier.notify("cutoff", "critical", "zone1", "80 F")

    assert [item[0] for item in sent] == [
        "https://ntfy.sh/ginger-ale-topic",
        "https://ntfy.sh/ginger-ale-topic",
        "https://ntfy.sh/ginger-ale-topic",
    ]
    assert sent[0][2]["Priority"] == "high"
    assert sent[0][2]["Title"] == "Ginger ale"
    assert sent[1][2]["Priority"] == "default"
    assert sent[2][2]["Priority"] == "urgent"


def test_token_is_sent_as_a_bearer_header():
    sent = []
    notifier = NtfyNotifier("topic", token="secret-token", post=lambda *args: sent.append(args))
    notifier.notify("heater_unreachable", "critical", "zone1", "{}")
    assert sent[0][2]["Authorization"] == "Bearer secret-token"


def test_a_delivery_failure_does_not_raise():
    def post(url, body, headers):
        raise OSError("offline")

    NtfyNotifier("topic", post=post).notify("reminder_due", "action", "Ginger ale", "Squeeze")


def test_example_secrets_leave_ntfy_unset():
    secrets = load_secrets(Path("config/secrets.example.yaml"))
    assert secrets.ntfy is None
    assert secrets.tuya["teckin_mat"].device_id == "replace-with-device-id"


def test_secrets_without_ntfy_build_a_log_only_notifier(tmp_path: Path):
    path = tmp_path / "secrets.yaml"
    path.write_text("tuya: {}\n")
    secrets = load_secrets(path)
    notifier = build_notifier(secrets)
    assert secrets.ntfy is None
    assert len(notifier._notifiers) == 1


def test_secrets_ntfy_topic_is_loaded(tmp_path: Path):
    path = tmp_path / "secrets.yaml"
    path.write_text(yaml.safe_dump({"ntfy": {"topic": "abc_123", "token": "tok"}}))
    secrets = load_secrets(path)
    assert secrets.ntfy is not None
    assert secrets.ntfy.topic == "abc_123"
    assert secrets.ntfy.server == "https://ntfy.sh"
    notifier = build_notifier(secrets)
    assert isinstance(notifier._notifiers[1], NtfyNotifier)


def test_a_click_header_opens_the_dashboard():
    sent = []
    notifier = NtfyNotifier("topic", click="http://127.0.0.1:8080", post=lambda *args: sent.append(args))
    notifier.notify("sensor_fault", "critical", "Ginger ale", "A temperature probe stopped reading.")
    assert sent[0][2]["Click"] == "http://127.0.0.1:8080"


def test_a_failed_send_is_retried_and_does_not_post_inline(tmp_path: Path):
    sent = []
    calls = {"n": 0}

    def post(url, body, headers, method="POST"):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("down")
        sent.append((url, body, headers, method))
        return b""

    database = tmp_path / "fermentd.db"
    migrate(connect(database))
    clock = ManualClock(datetime(2026, 10, 12, 18, 0, tzinfo=UTC))
    outbox = OutboxNotifier(database, clock, NtfyNotifier("topic", post=post))
    outbox.notify("sensor_fault", "critical", "Ginger ale", "A temperature probe stopped reading.")
    assert calls["n"] == 0
    outbox.drain()
    assert calls["n"] == 1
    assert sent == []
    outbox.drain()
    assert calls["n"] == 1
    clock.advance(30)
    outbox.drain()
    assert calls["n"] == 2
    assert sent[0][1] == "A temperature probe stopped reading."


def test_a_missed_checkin_is_scheduled_and_then_replaced(tmp_path: Path):
    sent = []
    ids = iter(["sched-1", "sched-2"])

    def post(url, body, headers, method="POST"):
        sent.append((method, url, body, dict(headers)))
        if method == "DELETE":
            return b""
        return json.dumps({"id": next(ids)}).encode()

    database = tmp_path / "fermentd.db"
    conn = connect(database)
    migrate(conn)
    conn.execute(
        """
        INSERT INTO VESSEL (id, name, vessel_type, enabled)
        VALUES ('vessel1', 'Ginger ale', 'bottle_group', 1)
        """
    )
    conn.commit()
    clock = ManualClock(datetime(2026, 10, 12, 18, 0, tzinfo=UTC))
    outbox = OutboxNotifier(
        database,
        clock,
        NtfyNotifier("topic", click="http://192.168.1.20:8080", post=post),
    )
    outbox.refresh_checkin()
    assert sent[0][0] == "POST"
    assert sent[0][2].startswith("The Pi has not checked in")
    assert sent[0][3]["Delay"] == "30m"
    assert sent[0][3]["Title"] == "Ginger ale"
    assert sent[0][3]["Click"] == "http://192.168.1.20:8080"
    clock.advance(10 * 60)
    outbox.refresh_checkin()
    assert len(sent) == 1
    clock.advance(10 * 60)
    outbox.refresh_checkin()
    assert sent[1][0] == "DELETE"
    assert sent[1][1].endswith("/sched-1")
    assert sent[2][3]["Delay"] == "30m"
    outbox.cancel_checkin()
    assert sent[-1][0] == "DELETE"
    outbox.refresh_checkin()
    assert len(sent) == 4


def test_ntfy_topic_must_be_a_single_path_segment(tmp_path: Path):
    path = tmp_path / "secrets.yaml"
    path.write_text("ntfy:\n  topic: has/slash\n")
    with pytest.raises(ValueError, match="ntfy topic"):
        load_secrets(path)
