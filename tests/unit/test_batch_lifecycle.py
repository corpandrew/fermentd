from fastapi.testclient import TestClient
from tests.conftest import heater_of, probes_of, service_bundle

from fermentd.web.app import create_app


def _running(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    service.submit(
        "test",
        "start_batch",
        {"vessel_id": "vessel1", "name": "Ginger ale", "profile_id": "soda_ginger_ale"},
        "start-1",
    )
    probes_of(hardware).set_temp("28-0000000000b2", 66.0)
    probes_of(hardware).set_temp("28-0000000000a1", 62.0)
    service.tick()
    clock.advance(60)
    service.tick()
    return service, clock, hardware


def _batch_id(service):
    return service.conn.execute("SELECT id FROM BATCH ORDER BY id DESC LIMIT 1").fetchone()["id"]


def test_ending_a_batch_turns_the_heater_off_and_cancels_reminders(tmp_path):
    service, clock, hardware = _running(tmp_path)
    assert heater_of(hardware).read_state() is True
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    page = client.get("/vessels/vessel1")
    assert "End batch" in page.text
    ended = client.post(
        "/vessels/vessel1/end",
        data={"confirm": "yes", "idempotency_key": "end-1"},
        follow_redirects=False,
    )
    assert ended.status_code == 303
    assert "error" not in ended.headers["location"]
    batch = service.conn.execute("SELECT * FROM BATCH").fetchone()
    assert batch["ended_at"] is not None
    assert batch["stage"] != "in_bottle"
    assert heater_of(hardware).read_state() is False
    pending = service.conn.execute("SELECT COUNT(*) AS n FROM REMINDER WHERE status IN ('pending', 'open')").fetchone()[
        "n"
    ]
    assert pending == 0
    clock.advance(60)
    service.tick()
    assert heater_of(hardware).read_state() is False
    vessel = client.get("/vessels/vessel1")
    assert "No batch running" in vessel.text
    assert "Start batch" in vessel.text
    audit = service.conn.execute("SELECT COUNT(*) AS n FROM AUDIT_LOG WHERE action = 'end_batch'").fetchone()["n"]
    assert audit >= 1


def test_ending_twice_is_idempotent_and_no_active_batch_is_rejected(tmp_path):
    service, _clock, _hardware = _running(tmp_path)
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    for _ in range(2):
        client.post("/vessels/vessel1/end", data={"confirm": "yes", "idempotency_key": "end-same"})
    assert service.conn.execute("SELECT COUNT(*) AS n FROM COMMAND WHERE type = 'end_batch'").fetchone()["n"] == 1
    again = client.post(
        "/vessels/vessel1/end",
        data={"confirm": "yes", "idempotency_key": "end-other"},
        follow_redirects=False,
    )
    assert "error=" in again.headers["location"]


def test_end_requires_confirm(tmp_path):
    service, _clock, _hardware = _running(tmp_path)
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    response = client.post("/vessels/vessel1/end", data={"confirm": "no", "idempotency_key": "x"})
    assert response.status_code == 400
    assert service.conn.execute("SELECT ended_at FROM BATCH").fetchone()["ended_at"] is None


def test_history_lists_ended_batches_newest_first_with_detail(tmp_path):
    service, clock, _hardware = _running(tmp_path)
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    client.post("/vessels/vessel1/end", data={"confirm": "yes", "idempotency_key": "end-a"})
    clock.advance(3600)
    service.tick()
    client.post(
        "/vessels/vessel1/start",
        data={"name": "Second batch", "confirm": "yes", "idempotency_key": "start-b"},
    )
    clock.advance(3600)
    service.tick()
    client.post("/vessels/vessel1/end", data={"confirm": "yes", "idempotency_key": "end-b"})
    page = client.get("/history")
    assert page.status_code == 200
    assert page.text.index("Second batch") < page.text.index(">Ginger ale<")
    assert 'href="/history"' in client.get("/").text
    first = service.conn.execute("SELECT id FROM BATCH WHERE name = 'Ginger ale'").fetchone()["id"]
    service.conn.execute(
        "INSERT INTO NOTE (batch_id, ts, actor, text) VALUES (?, '2026-10-12T18:00:00Z', 'web', 'Tasted great')",
        (first,),
    )
    service.conn.commit()
    detail = client.get(f"/history/{first}")
    assert detail.status_code == 200
    assert "Tasted great" in detail.text
    assert "<svg" in detail.text
    assert "Delete from history" in detail.text


def test_active_batch_is_not_in_history_and_cannot_be_deleted(tmp_path):
    service, _clock, _hardware = _running(tmp_path)
    batch_id = _batch_id(service)
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    assert "Ginger ale" not in client.get("/history").text.split("History", 2)[-1]
    assert client.get(f"/history/{batch_id}").status_code == 404
    response = client.post(
        f"/history/{batch_id}/delete",
        data={"confirm": "yes", "idempotency_key": "del-active"},
        follow_redirects=False,
    )
    assert "error=" in response.headers["location"]
    assert service.conn.execute("SELECT COUNT(*) AS n FROM BATCH").fetchone()["n"] == 1


def test_deleting_an_ended_batch_removes_its_rows(tmp_path):
    service, clock, _hardware = _running(tmp_path)
    batch_id = _batch_id(service)
    service.conn.execute(
        "INSERT INTO NOTE (batch_id, ts, actor, text) VALUES (?, '2026-10-12T18:00:00Z', 'web', 'n')",
        (batch_id,),
    )
    service.conn.execute(
        """INSERT INTO EVENT (ts, batch_id, vessel_id, type, severity, actor, detail_json)
           VALUES ('2026-10-12T18:00:00Z', ?, 'vessel1', 'pressure_risk', 'action', 'control', '{}')""",
        (batch_id,),
    )
    event_id = service.conn.execute("SELECT MAX(id) AS id FROM EVENT").fetchone()["id"]
    service.conn.execute(
        """INSERT INTO ALERT (event_id, dedupe_key, severity, status, opened_at)
           VALUES (?, ?, 'action', 'resolved', '2026-10-12T18:00:00Z')""",
        (event_id, f"pressure_risk:batch:{batch_id}"),
    )
    service.conn.commit()
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    client.post("/vessels/vessel1/end", data={"confirm": "yes", "idempotency_key": "end-d"})
    assert "Yes, delete this batch" in client.get(f"/history/{batch_id}?delete=1").text
    assert (
        client.post(f"/history/{batch_id}/delete", data={"confirm": "no", "idempotency_key": "d0"}).status_code == 400
    )
    deleted = client.post(
        f"/history/{batch_id}/delete",
        data={"confirm": "yes", "idempotency_key": "d1"},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert deleted.headers["location"] == "/history"
    for table in ("BATCH", "NOTE", "REMINDER"):
        column = "id" if table == "BATCH" else "batch_id"
        assert (
            service.conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {column} = ?", (batch_id,)).fetchone()["n"]
            == 0
        )
    assert (
        service.conn.execute("SELECT COUNT(*) AS n FROM READING WHERE batch_id = ?", (batch_id,)).fetchone()["n"] == 0
    )
    assert service.conn.execute("SELECT COUNT(*) AS n FROM EVENT WHERE batch_id = ?", (batch_id,)).fetchone()["n"] == 0
    assert service.conn.execute("SELECT COUNT(*) AS n FROM ALERT WHERE event_id = ?", (event_id,)).fetchone()["n"] == 0
    assert (
        service.conn.execute("SELECT COUNT(*) AS n FROM AUDIT_LOG WHERE action = 'delete_batch'").fetchone()["n"] >= 1
    )
    assert client.get(f"/history/{batch_id}").status_code == 404
    clock.advance(60)
    service.tick()
