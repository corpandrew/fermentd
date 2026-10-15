"""Read-only MCP server: queries, read-only connection, tool registration, auth and no secrets."""

import asyncio
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from tests.conftest import probes_of, service_bundle

from fermentd.mcp import queries as q
from fermentd.mcp.server import BearerAuth, build_server
from fermentd.web.app import create_app

ROM = "28-0000000000b2"
TOOLS = {
    "list_vessels", "get_vessel_status", "get_vessel_temperature", "get_vessel_temperature_history",
    "get_vessel_heater", "get_vessel_weight", "list_batches", "get_batch", "get_batch_gravity", "list_alerts",
    "list_profiles", "start_batch", "end_batch", "get_profile", "get_next_actions",
    "advance_stage", "complete_reminder", "log_gravity",
    "get_batch_tweaks", "list_tastings", "get_best_batches", "list_variants",
    "add_batch_tweak", "remove_batch_tweak", "log_tasting", "save_tweaks_as_variant",
    "list_batch_notes", "get_batch_activity", "add_batch_note",
}
WRITE_TOOLS = {"start_batch", "end_batch", "advance_stage", "complete_reminder", "log_gravity",
               "add_batch_tweak", "remove_batch_tweak", "log_tasting", "save_tweaks_as_variant", "add_batch_note"}


@pytest.fixture
def world(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    for i in range(30):
        probes_of(hardware).set_temp(ROM, 66.0 + i * 0.2)
        probes_of(hardware).set_temp("28-0000000000a1", 60.0)
        clock.advance(60)
        service.tick()
        if i == 1:
            client.post("/vessels/vessel1/start", data={"profile_id": "soda_ginger_ale", "confirm": "yes", "idempotency_key": "s"})
    client.post("/vessels/vessel1/gravity", data={"sg": "1.050", "confirm": "yes", "idempotency_key": "g1"})
    clock.advance(86400)
    service.tick()
    client.post("/vessels/vessel1/gravity", data={"sg": "1.020", "confirm": "yes", "idempotency_key": "g2"})
    service.conn.commit()
    ro = q.connect_ro(tmp_path / "fermentd.db")
    return service, clock, ro, tmp_path


def test_read_only_connection_refuses_writes(world):
    _s, _c, ro, _p = world
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("UPDATE TEMP_ZONE SET target_f = 90")
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("CREATE TABLE x (a)")


def test_vessel_tools(world):
    service, clock, ro, _p = world
    now = clock.now()
    vessels = q.list_vessels(ro, now)["vessels"]
    v = next(item for item in vessels if item["vessel_id"] == "vessel1")
    assert v["current_batch"]["name"] and v["target_f"] == 72 and v["temp_f"] is not None
    assert v["reading_time"]["utc"].endswith("Z") and v["reading_time"]["local"].endswith("-04:00")
    temp = q.get_vessel_temperature(ro, "vessel1", now)
    assert temp["delta_f"] == pytest.approx(temp["temp_f"] - 72, abs=0.01) and temp["reading_age_s"] == 0
    hist = q.get_vessel_temperature_history(ro, "vessel1", hours=48, bucket_minutes=10, now=now)
    assert hist["buckets"] and all(b["min_f"] <= b["avg_f"] <= b["max_f"] for b in hist["buckets"])
    assert hist["bucket_minutes"] == 10
    heater = q.get_vessel_heater(ro, "vessel1", now)
    assert isinstance(heater["heater_on"], bool) and 0 <= heater["duty_pct_24h"] <= 100
    assert heater["duty_pct_batch"] is not None
    weight = q.get_vessel_weight(ro, "vessel1", now)
    assert weight["has_scale"] is False and "No scale" in weight["note"]
    status = q.get_vessel_status(ro, "vessel1", now)
    assert status["batch"]["day"] == 2 and "temperature" in status
    with pytest.raises(q.NotFound):
        q.get_vessel_temperature(ro, "nope", now)


def test_batch_and_alert_tools(world):
    service, clock, ro, _p = world
    now = clock.now()
    batches = q.list_batches(ro, "active", now)["batches"]
    assert len(batches) == 1 and batches[0]["vessel_id"] == "vessel1" and batches[0]["profile_id"] == "soda_ginger_ale"
    assert q.list_batches(ro, "all", now)["batches"]
    with pytest.raises(ValueError):
        q.list_batches(ro, "bogus", now)
    batch = q.get_batch(ro, batches[0]["batch_id"], now)
    assert batch["schedule"] and any(s["current"] for s in batch["schedule"])
    assert batch["started"]["local"]
    gravity = q.get_batch_gravity(ro, batches[0]["batch_id"])
    assert [r["sg"] for r in gravity["readings"]] == [1.05, 1.02] and gravity["est_abv_pct"] == pytest.approx(3.94, abs=0.01)
    alerts = q.list_alerts(ro, "all")
    assert isinstance(alerts["alerts"], list)
    for item in alerts["alerts"]:
        assert item["opened"]["utc"].endswith("Z")


def test_server_registers_exactly_the_read_only_tools(world):
    _s, _c, ro, tmp = world
    server = build_server(conn=ro)
    tools = asyncio.run(server.list_tools())
    assert {t.name for t in tools} == TOOLS
    assert all(t.annotations.readOnlyHint for t in tools if t.name not in WRITE_TOOLS)
    assert all(not t.annotations.readOnlyHint and t.description.startswith("WRITE: Changes state on the Pi.")
               for t in tools if t.name in WRITE_TOOLS)
    result = asyncio.run(server.call_tool("get_vessel_temperature", {"vessel_id": "vessel1"}))
    text = json.dumps([getattr(c, "text", "") for c in (result[0] if isinstance(result, tuple) else result)])
    assert "delta_f" in text


def test_no_secret_reaches_any_tool(world, tmp_path):
    _s, _c, ro, tmp = world
    server = build_server(conn=ro)
    blobs = []
    for name, args in [("list_vessels", {}), ("get_vessel_status", {"vessel_id": "vessel1"}),
                       ("list_batches", {"status": "all"}), ("list_alerts", {"status": "all"})]:
        result = asyncio.run(server.call_tool(name, args))
        blobs.append(json.dumps([getattr(c, "text", "") for c in (result[0] if isinstance(result, tuple) else result)]))
    joined = " ".join(blobs).lower()
    for word in ("local_key", "topic", "token", "replace-with"):
        assert word not in joined


def test_bearer_auth_rejects_missing_and_wrong_tokens():
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["path"])
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    token = "x" * 40
    guarded = BearerAuth(app, token)

    def call(headers):
        sent = []

        async def send(msg):
            sent.append(msg)

        async def receive():
            return {"type": "http.request"}

        asyncio.run(guarded({"type": "http", "path": "/mcp", "headers": headers}, receive, send))
        return sent[0]["status"]

    assert call([]) == 401
    assert call([(b"authorization", b"Bearer wrong")]) == 401
    assert call([(b"authorization", f"Bearer {token}".encode())]) == 200
    with pytest.raises(ValueError):
        BearerAuth(app, "short")


def test_stdio_end_to_end(world):
    import os
    import sys

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    _s, _c, _ro, tmp = world
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(["src", "."] + sys.path)}
    params = StdioServerParameters(command=sys.executable, args=["-m", "fermentd.mcp", "--db", str(tmp / "fermentd.db")], env=env)

    async def run():
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            result = await session.call_tool("list_vessels", {})
            return names, result.content[0].text

    names, text = asyncio.run(run())
    assert names == TOOLS and "vessel1" in text


def test_duty_window_starts_at_batch_start(tmp_path):
    service, clock, hardware, _n = service_bundle(tmp_path)
    service.startup()
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    for _ in range(120):  # two idle hours before the batch, heat off
        probes_of(hardware).set_temp(ROM, 60.0)
        probes_of(hardware).set_temp("28-0000000000a1", 60.0)
        clock.advance(60)
        service.tick()
    client.post("/vessels/vessel1/start", data={"profile_id": "soda_ginger_ale", "confirm": "yes", "idempotency_key": "s"})
    for _ in range(60):  # one hour cold, heat on the whole time
        probes_of(hardware).set_temp(ROM, 60.0)
        clock.advance(60)
        service.tick()
    service.conn.commit()
    heater = q.get_vessel_heater(q.connect_ro(tmp_path / "fermentd.db"), "vessel1", clock.now())
    assert heater["duty_pct_24h"] >= 95  # not diluted by the idle hours before the batch
    assert heater["duty_hours_covered"] <= 1.05
    batch_start = service.conn.execute("SELECT started_at FROM BATCH").fetchone()[0]
    assert heater["duty_window_start"]["utc"] >= batch_start


def test_tool_descriptions_do_not_hard_code_a_vessel_id():
    server = build_server(conn=sqlite3.connect(":memory:"))
    blob = json.dumps([t.inputSchema for t in asyncio.run(server.list_tools())])
    assert "vessel1" not in blob and "list_vessels" in blob


def test_service_interrupted_resolves_after_healthy_running(tmp_path):
    from fermentd.control.service import ControlService

    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()  # leaves 'service_started' as the last event: next start looks like a crash
    probes_of(hardware).set_temp(ROM, 66.0)
    probes_of(hardware).set_temp("28-0000000000a1", 60.0)
    again = ControlService(service.config, service.conn, clock, hardware, service.profiles, notifier)
    again.startup()
    key = "service_interrupted:zone:control"
    row = lambda: service.conn.execute("SELECT status, resolved_at FROM ALERT WHERE dedupe_key = ?", (key,)).fetchone()
    assert row()["status"] == "open"
    for _ in range(2):
        clock.advance(60)
        again.tick()
    assert row()["status"] == "open"
    clock.advance(70)
    again.tick()
    assert row()["status"] == "resolved" and row()["resolved_at"]
    assert service.conn.execute("SELECT COUNT(*) FROM ALERT WHERE dedupe_key = ?", (key,)).fetchone()[0] == 1


def test_server_version_tracks_tool_set():
    server = build_server(conn=sqlite3.connect(":memory:"))
    assert f"+tools{len(TOOLS)}." in server._mcp_server.version
