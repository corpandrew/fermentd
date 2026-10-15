"""The Prep ('Making it') stage and monitor-only vessels (no heater zone, no probe)."""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import heater_of, probes_of, service_bundle

from fermentd.mcp import diary as d
from fermentd.mcp import guide as g
from fermentd.mcp import queries as q
from fermentd.mcp import tastes as t
from fermentd.mcp import writes as w
from fermentd.web.app import create_app

ROM = "28-0000000000b2"


@pytest.fixture
def env(tmp_path):
    service, clock, hardware, notifier = service_bundle(tmp_path)
    service.startup()
    probes_of(hardware).set_temp(ROM, 72.0)
    probes_of(hardware).set_temp("28-0000000000a1", 65.0)
    service.tick()
    service.conn.execute("UPDATE VESSEL SET vessel_type = 'jug' WHERE id = 'vessel1'")
    service.conn.commit()
    ro = q.connect_ro(tmp_path / "fermentd.db")
    writer = w.Writer(conn=service.conn, pump=service.tick, clock=clock)
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    return service, clock, hardware, notifier, ro, writer, client


def _run(service, clock, minutes):
    for _ in range(int(minutes * 6)):
        clock.advance(10)
        service.tick()


def _open_alerts(service):
    return {r[0].split(":")[0] for r in service.conn.execute("SELECT dedupe_key FROM ALERT WHERE resolved_at IS NULL")}


def test_prep_batch_does_not_heat_or_alert_until_it_advances(env):
    service, clock, hardware, notifier, ro, writer, client = env
    heater = heater_of(hardware)
    probes_of(hardware).set_temp(ROM, 60.0)  # cold wort / water: would normally heat and alert
    zone_before = service.conn.execute("SELECT target_f FROM TEMP_ZONE").fetchone()[0]
    out = w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "GA", stage="prep")
    assert out["stage"] == "prep"
    _run(service, clock, 90)
    assert heater.on is False and not any(heater.set_calls)
    assert not _open_alerts(service) & {"temp_below_target", "temp_out_of_range", "target_reached"}
    assert service.conn.execute("SELECT target_f FROM TEMP_ZONE").fetchone()[0] == zone_before
    na = g.next_actions(ro, out["batch_id"])["batches"][0]
    assert na["stage_label"] == "Making it" and any("Simmer the grated ginger" in s for s in na["next_steps"])
    assert na["next_stage"] == "bottle"
    w.advance_stage(ro, writer, out["batch_id"])
    service.tick()
    assert service.conn.execute("SELECT target_f FROM TEMP_ZONE").fetchone()[0] == 72.0
    assert heater.on is True


def test_monitor_only_vessel_runs_a_batch_without_touching_the_heater(env):
    service, clock, hardware, notifier, ro, writer, client = env
    heater = heater_of(hardware)
    # The water-test style batch owns the heater.
    w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "Water test")
    probes_of(hardware).set_temp(ROM, 70.0)
    service.tick()
    assert heater.on is True
    service.submit("web", "add_vessel", {"name": "Bottles", "vessel_type": "bottle_group"}, "v1")
    service.tick()
    vessel = service.conn.execute("SELECT * FROM VESSEL WHERE id = 'bottles'").fetchone()
    assert vessel["temp_zone_id"] is None and vessel["probe_rom_id"] is None
    zone = dict(service.conn.execute("SELECT target_f, hysteresis_f FROM TEMP_ZONE").fetchone())
    gid = w.start_batch(ro, writer, "bottles", "soda_ginger_ale", "Ginger ale #2", 1, stage="prep")["batch_id"]
    tw = t.add_batch_tweak(ro, writer, gid, "change", "ginger", "94 g", note="grated")
    view = t.get_batch_tweaks(ro, gid)
    ginger = next(r for r in view["ingredients"] if r["id"] == "ginger")
    assert ginger["recipe"] == "4 oz" and ginger["mine"] == "94 g" and tw["added_tweak_id"]
    t.add_batch_tweak(ro, writer, gid, "note", note="Steeped 1 minute longer.")
    d.add_batch_note(ro, writer, gid, "Some ginger skin went in by accident — fine, it gets strained out.")
    _run(service, clock, 30)
    w.advance_stage(ro, writer, gid)  # Prep -> Bottling, still no zone
    w.advance_stage(ro, writer, gid)  # -> Carbonating in the bottles
    _run(service, clock, 30)
    assert dict(service.conn.execute("SELECT target_f, hysteresis_f FROM TEMP_ZONE").fetchone()) == zone
    assert heater.on is True  # still driven by the water test only
    status = q.get_vessel_status(ro, "bottles")
    assert status["vessel_id"] == "bottles"
    page = client.get("/").text
    assert "Ginger ale #2" in page and "Water test" in page
    assert "Ginger ale #2" in client.get("/vessels/bottles").text
    act = [a["what"] for a in d.get_batch_activity(ro, gid)["activity"]]
    assert "Added a note" in act and any("94 g" in a for a in act)
    assert "Process note: Steeped 1 minute longer." in act
    assert {r["actor"] for r in service.conn.execute(
        "SELECT actor FROM AUDIT_LOG WHERE batch_id = ? AND command_id IS NOT NULL", (gid,))} == {"mcp"}


def test_existing_batches_keep_their_snapshot_without_prep(env):
    service, clock, hardware, notifier, ro, writer, client = env
    import json

    bid = w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "Old")["batch_id"]
    # Simulate a batch started before Prep existed.
    row = service.conn.execute("SELECT profile_snapshot_json FROM BATCH WHERE id = ?", (bid,)).fetchone()
    snap = json.loads(row[0])
    snap["stages"] = [s for s in snap["stages"] if s["id"] != "prep"]
    service.conn.execute("UPDATE BATCH SET profile_snapshot_json = ? WHERE id = ?", (json.dumps(snap), bid))
    service.conn.commit()
    na = g.next_actions(ro, bid)["batches"][0]
    assert na["stage"] == "in_bottle" and na["next_stage"] == "refrigerated"
    assert "Making it" not in client.get("/vessels/vessel1").text


def test_dashboard_start_form_offers_prep_and_starts_in_it(env):
    service, clock, hardware, notifier, ro, writer, client = env
    page = client.get("/vessels/vessel1").text
    assert 'name="start_stage"' in page and "Making it now" in page
    client.post("/vessels/vessel1/start", data={"confirm": "yes", "idempotency_key": "s1", "name": "GA",
                                                "profile_id": "soda_ginger_ale", "start_stage": "prep"})
    assert service.conn.execute("SELECT stage FROM BATCH").fetchone()[0] == "prep"
    assert "Making it" in client.get("/vessels/vessel1").text


def test_soda_guides_have_no_jug_and_a_sanitize_checklist():
    from pathlib import Path

    from fermentd.web.markdown import load_guide

    for name in ("ginger_ale", "lemon_lime", "root_beer", "cola"):
        g = load_guide(Path(f"docs/recipes/soda_{name}.md"), size="1")
        steps = " ".join(s["text"] for s in g["meta"]["steps"]).lower()
        equipment = " ".join(g["meta"]["equipment"]).lower()
        assert "jug" not in steps and "jug" not in equipment, name
        assert "mesh strainer" in equipment and "bottle filler" in equipment and "baking dish" in equipment
        assert "Sanitize these" in g["html"] and "Stirring spoon (metal is fine)" in g["html"]
        assert "strain right before adding the yeast" in steps and "baking dish or the sink" in steps


def test_a_prep_batch_vessel_can_take_over_the_zone_and_probe(env):
    service, clock, hardware, notifier, ro, writer, client = env
    heater = heater_of(hardware)
    old = w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "Water test")["batch_id"]
    service.submit("web", "add_vessel", {"name": "Bottles", "vessel_type": "bottle_group"}, "v1")
    service.tick()
    gid = w.start_batch(ro, writer, "bottles", "soda_ginger_ale", "GA", 1, stage="prep")["batch_id"]
    w.end_batch(ro, writer, old)
    v1 = dict(service.conn.execute("SELECT * FROM VESSEL WHERE id = 'vessel1'").fetchone())
    writer.submit("update_vessel", {"vessel_id": "vessel1", "name": v1["name"], "vessel_type": v1["vessel_type"],
                                    "temp_zone": "", "probe_rom_id": ""})
    writer.submit("update_vessel", {"vessel_id": "bottles", "name": "Bottles", "vessel_type": "bottle_group",
                                    "temp_zone": "zone1", "probe_rom_id": ROM})
    probes_of(hardware).set_temp(ROM, 68.0)
    service.tick()
    assert heater.on is False  # still Prep
    w.advance_stage(ro, writer, gid, "in_bottle")
    _run(service, clock, 16)  # bottles keep the mat off at least 15 min between bursts
    assert heater.on is True
    assert service.conn.execute("SELECT target_f FROM TEMP_ZONE").fetchone()[0] == 72.0
    st = q.get_vessel_status(ro, "bottles")
    assert st["batch"]["name"] == "GA" if "batch" in st and st["batch"] else True
    # A running (non-Prep) batch still blocks hardware changes.
    with pytest.raises(w.WriteRejected, match="batch is running"):
        writer.submit("update_vessel", {"vessel_id": "bottles", "name": "Bottles", "vessel_type": "bottle_group",
                                        "temp_zone": "", "probe_rom_id": ""})
