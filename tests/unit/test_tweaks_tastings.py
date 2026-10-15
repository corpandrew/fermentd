"""Recipe tweaks, tasting log, 'my version' variants: controller commands, web pages and MCP tools."""

import pytest
from fastapi.testclient import TestClient
from tests.conftest import probes_of, service_bundle

from fermentd.control import tweaks as tw
from fermentd.mcp import queries as q
from fermentd.mcp import tastes as t
from fermentd.mcp import writes as w
from fermentd.web.app import create_app

ROM = "28-0000000000b2"


@pytest.fixture
def env(tmp_path):
    service, clock, hardware, _n = service_bundle(tmp_path)
    service.startup()
    probes_of(hardware).set_temp(ROM, 72.0)
    probes_of(hardware).set_temp("28-0000000000a1", 65.0)
    service.tick()
    service.conn.execute("UPDATE VESSEL SET vessel_type = 'jug' WHERE id = 'vessel1'")
    service.conn.commit()
    ro = q.connect_ro(tmp_path / "fermentd.db")
    writer = w.Writer(conn=service.conn, pump=service.tick, clock=clock)
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    return service, clock, ro, writer, client


def _ginger(ro, writer, name="GA #1", **kw):
    return w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", name, None, None, **kw)["batch_id"]


def test_tweaks_show_against_the_base_recipe(env):
    service, _c, ro, writer, _cl = env
    bid = _ginger(ro, writer)
    out = t.add_batch_tweak(ro, writer, bid, "change", "ginger", "5 oz")
    t.add_batch_tweak(ro, writer, bid, "add", None, "zest of 1", "lime zest")
    t.add_batch_tweak(ro, writer, bid, "remove", "salt")
    t.add_batch_tweak(ro, writer, bid, "note", note="steeped ginger 20 min")
    view = t.get_batch_tweaks(ro, bid)
    rows = {r["item"]: r for r in view["ingredients"]}
    assert rows["fresh ginger"]["recipe"] == "4 oz" and rows["fresh ginger"]["mine"] == "5 oz"
    assert rows["fresh ginger"]["state"] == "changed" and rows["salt"]["state"] == "removed"
    assert rows["lime zest"]["state"] == "added" and rows["white sugar"]["state"] == "same"
    assert view["notes"][0]["text"] == "steeped ginger 20 min" and view["change_count"] == 4
    assert out["added_tweak_id"]
    t.remove_batch_tweak(ro, writer, out["added_tweak_id"], bid)
    assert {r["item"]: r for r in t.get_batch_tweaks(ro, bid)["ingredients"]}["fresh ginger"]["state"] == "same"
    actors = {r[0] for r in service.conn.execute("SELECT actor FROM AUDIT_LOG WHERE action IN ('add_tweak','remove_tweak')")}
    assert actors == {"mcp"}


@pytest.mark.parametrize("args, match", [
    (("change", "unicorn", "1 oz"), "not in the recipe"),
    (("change", "ginger", None), "new amount"),
    (("bogus", None, None), "kind must be"),
    (("note", None, None), "process note"),
])
def test_bad_tweaks_are_rejected_without_writes(env, args, match):
    service, _c, ro, writer, _cl = env
    bid = _ginger(ro, writer)
    with pytest.raises(w.WriteRejected, match=match):
        t.add_batch_tweak(ro, writer, bid, *args)
    assert service.conn.execute("SELECT COUNT(*) FROM BATCH_TWEAK").fetchone()[0] == 0


def test_tastings_ranking_and_best_batches(env):
    service, _c, ro, writer, _cl = env
    a = _ginger(ro, writer, "Spicy")
    t.add_batch_tweak(ro, writer, a, "change", "ginger", "6 oz")
    t.log_tasting(ro, writer, a, 5, "2026-10-20", carbonation=4, flavor=5, notes="great bite", make_again=True)
    t.log_tasting(ro, writer, a, 4, "2026-10-22")
    w.end_batch(ro, writer, a)
    b = _ginger(ro, writer, "Mild")
    t.log_tasting(ro, writer, b, 2, notes="too sweet", make_again=False)
    best = t.get_best_batches(ro, profile_id="soda_ginger_ale")["ranked"]
    assert [r["name"] for r in best] == ["Spicy", "Mild"]
    assert best[0]["avg_rating"] == 4.5 and best[0]["make_again"] is True
    assert best[0]["changes"] == ["fresh ginger: 4 oz → 6 oz"] and best[1]["make_again"] is False
    assert t.get_best_batches(ro, drink_type="cider")["ranked"] == []
    entries = t.list_tastings(ro, a)["tastings"]
    assert len(entries) == 2 and entries[0]["tasted"]["local"].startswith("2026-10-22")
    assert len(t.list_tastings(ro)["tastings"]) == 3
    with pytest.raises(w.WriteRejected, match="1-5"):
        t.log_tasting(ro, writer, b, 6)
    with pytest.raises(w.WriteRejected, match="sweetness must be 1-5"):
        t.log_tasting(ro, writer, b, 3, sweetness=0)


def test_variant_and_copy_into_a_new_batch(env):
    service, _c, ro, writer, _cl = env
    a = _ginger(ro, writer, "Spicy")
    t.add_batch_tweak(ro, writer, a, "change", "ginger", "6 oz")
    t.add_batch_tweak(ro, writer, a, "note", note="steeped ginger 20 min")
    v = t.save_tweaks_as_variant(ro, writer, a, "Spicy ginger ale")
    assert v["name"] == "Spicy ginger ale" and len(v["changes"]) == 2
    assert t.list_variants(ro, "soda_ginger_ale")["variants"][0]["variant_id"] == v["variant_id"]
    w.end_batch(ro, writer, a)
    b = _ginger(ro, writer, "Spicy again", variant_id=v["variant_id"])
    view = t.get_batch_tweaks(ro, b)
    assert view["variant"]["name"] == "Spicy ginger ale" and view["change_count"] == 2
    w.end_batch(ro, writer, b)
    c = _ginger(ro, writer, "Copy", copy_tweaks_from_batch_id=a)
    assert t.get_batch_tweaks(ro, c)["change_count"] == 2
    w.end_batch(ro, writer, c)
    with pytest.raises(w.WriteRejected, match="not both"):
        _ginger(ro, writer, "X", variant_id=v["variant_id"], copy_tweaks_from_batch_id=a)
    with pytest.raises(w.WriteRejected, match="not cider_french_brut"):
        w.start_batch(ro, writer, "vessel1", "cider_french_brut", "Y", None, None, v["variant_id"], None)
    assert service.conn.execute("SELECT COUNT(*) FROM BATCH WHERE ended_at IS NULL").fetchone()[0] == 0


def test_batch_pages_show_tweaks_and_tastings_including_after_end(env):
    service, _c, ro, writer, client = env
    bid = _ginger(ro, writer, "Page test")
    form = {"confirm": "yes"}
    client.post(f"/batches/{bid}/tweaks", data={**form, "idempotency_key": "k1", "kind": "change",
                                                 "ingredient_id": "ginger", "to_amount": "5 oz"})
    client.post(f"/batches/{bid}/tastings", data={**form, "idempotency_key": "k2", "rating": "4",
                                                   "carbonation": "3", "notes": "nice", "make_again": "yes"})
    page = client.get("/vessels/vessel1").text
    assert "Your recipe for this batch" in page and "5 oz" in page and "changed" in page
    assert "Tasting notes" in page and "nice" in page and "Would make again" in page
    assert "Fizz" in page  # soda sliders use plain labels
    assert all(a[0] == "web" for a in service.conn.execute("SELECT actor FROM AUDIT_LOG WHERE action='add_tweak'"))
    client.post(f"/batches/{bid}/variant", data={**form, "idempotency_key": "k3", "name": "Mine"})
    client.post("/vessels/vessel1/end", data={**form, "idempotency_key": "k4"})
    hist = client.get(f"/history/{bid}").text
    assert "Your recipe for this batch" in hist and "nice" in hist
    ranking = client.get("/tastings").text
    assert "Page test" in ranking and "★★★★" in ranking
    start = client.get("/vessels/vessel1").text
    assert "My version: Mine" in start and "Same changes as Page test" in start


def test_sliders_adapt_to_drink_type():
    assert [s["key"] for s in tw.sliders_for("cider")][0] == "dryness"
    assert "Fizz" in [s["label"] for s in tw.sliders_for("soda")]
    assert len(tw.sliders_for(None)) == 4
