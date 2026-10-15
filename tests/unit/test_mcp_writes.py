"""MCP write tools, against a temp database only (never the live Pi)."""

import asyncio
import json

import pytest
from tests.conftest import probes_of, service_bundle

from fermentd.mcp import queries as q
from fermentd.mcp import writes as w
from fermentd.mcp.server import build_server

ROM = "28-0000000000b2"


def _jug(service):
    service.conn.execute("UPDATE VESSEL SET vessel_type = 'jug' WHERE id = 'vessel1'")
    service.conn.commit()


@pytest.fixture
def env(tmp_path):
    service, clock, hardware, _n = service_bundle(tmp_path)
    service.startup()
    probes_of(hardware).set_temp(ROM, 64.0)
    probes_of(hardware).set_temp("28-0000000000a1", 60.0)
    service.tick()
    _jug(service)
    ro = q.connect_ro(tmp_path / "fermentd.db")
    writer = w.Writer(conn=service.conn, pump=service.tick, clock=clock)
    return service, ro, writer


def _audits(service):
    return service.conn.execute("SELECT actor, action, new_value FROM AUDIT_LOG WHERE actor = 'mcp'").fetchall()


def test_list_profiles(env):
    _s, ro, _w = env
    profiles = {p["profile_id"]: p for p in w.list_profiles(ro)["profiles"]}
    brut = profiles["cider_french_brut"]
    assert brut["drink_type"] and brut["batch_sizes_gal"] == [1, 0.5]
    assert len(brut["allowed_target_f"]) == 2 and brut["default_target_f"]
    assert brut["vessel_types"]["jug"] is True and "vessel1" in brut["allowed_for_vessels"]


def test_start_then_end_batch_through_controller_with_audit(env):
    service, ro, writer = env
    out = w.start_batch(ro, writer, "vessel1", "cider_french_brut", "Brut #2", 0.5, None)
    assert out["name"] == "Brut #2" and out["status"] == "active" and out["volume_l"] == pytest.approx(1.893, abs=0.01)
    assert set(q.get_batch(ro, out["batch_id"])) == set(out)
    with pytest.raises(w.WriteRejected, match="already has an active batch: #.*Brut #2"):
        w.start_batch(ro, writer, "vessel1", "cider_french_brut", "Again", None, None)
    ended = w.end_batch(ro, writer, out["batch_id"])
    assert ended["status"] == "ended" and ended["ended"]["utc"]
    actions = [a["action"] for a in _audits(service)]
    assert actions.count("start_batch") == 1 and actions.count("end_batch") >= 1
    with pytest.raises(w.WriteRejected, match="already ended"):
        w.end_batch(ro, writer, out["batch_id"])


def test_target_within_range_is_applied(env):
    service, ro, writer = env
    profile = next(p for p in w.list_profiles(ro)["profiles"] if p["profile_id"] == "cider_french_brut")
    low, high = profile["allowed_target_f"]
    target = round((low + high) / 2)
    out = w.start_batch(ro, writer, "vessel1", "cider_french_brut", "Warm brut", None, target)
    assert out["target_f"] == target and "warning" not in out
    assert any(a["action"] == "set_target_temp" for a in _audits(service))


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"profile_id": "nope"}, "unknown profile_id"),
        ({"target_f": 150}, "outside"),
        ({"batch_size": 5}, "batch_size"),
        ({"name": "  "}, "name is required"),
    ],
)
def test_rejections_have_no_side_effects(env, kwargs, match):
    service, ro, writer = env
    args = {"profile_id": "cider_french_brut", "name": "X", "batch_size": None, "target_f": None, **kwargs}
    before = service.conn.execute("SELECT COUNT(*) FROM COMMAND").fetchone()[0]
    with pytest.raises(w.WriteRejected, match=match):
        w.start_batch(ro, writer, "vessel1", **args)
    assert service.conn.execute("SELECT COUNT(*) FROM BATCH").fetchone()[0] == 0
    assert service.conn.execute("SELECT COUNT(*) FROM COMMAND").fetchone()[0] == before


def test_profile_not_allowed_for_vessel_type(env):
    service, ro, writer = env
    service.conn.execute("UPDATE VESSEL SET vessel_type = 'bottle_group' WHERE id = 'vessel1'")
    service.conn.commit()
    restricted = next(p for p in w.list_profiles(ro)["profiles"] if not p["vessel_types"]["bottle_group"])
    with pytest.raises(w.WriteRejected, match="not allowed"):
        w.start_batch(ro, writer, "vessel1", restricted["profile_id"], "X", None, None)


def test_server_start_batch_tool_reports_rejection(env):
    service, ro, writer = env
    server = build_server(conn=ro, writer=writer)
    asyncio.run(server.call_tool("start_batch", {"vessel_id": "vessel1", "profile_id": "cider_french_brut", "name": "A"}))
    with pytest.raises(Exception, match="already has an active batch"):
        asyncio.run(server.call_tool("start_batch", {"vessel_id": "vessel1", "profile_id": "cider_french_brut", "name": "B"}))
    assert service.conn.execute("SELECT COUNT(*) FROM BATCH").fetchone()[0] == 1
