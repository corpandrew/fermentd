"""get_next_actions, get_profile, list_profiles legacy filter, and the new write tools (temp DB only)."""

from datetime import timedelta

import pytest
from tests.conftest import probes_of, service_bundle

from fermentd.mcp import guide as g
from fermentd.mcp import queries as q
from fermentd.mcp import writes as w

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
    return service, clock, ro, writer


def _ginger(ro, writer, name="GA"):
    return w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", name, None, None)["batch_id"]


def test_next_actions_for_ginger_ale(env):
    service, clock, ro, writer = env
    bid = _ginger(ro, writer)
    out = g.next_actions(ro, bid, clock.now())["batches"][0]
    assert out["stage"] == "in_bottle" and out["next_stage"] == "refrigerated"
    assert out["stage_meaning"].startswith("Conditioning")
    assert any("heat mat" in s for s in out["next_steps"])
    assert "rock hard" in out["advance_when"]
    keys = {r["key"]: r for r in out["pending_reminders"]}
    assert "squeeze" in keys and keys["squeeze"]["reminder_id"] and keys["squeeze"]["overdue"] is False
    later = g.next_actions(ro, bid, clock.now() + timedelta(hours=13))["batches"][0]
    assert any(r["overdue"] for r in later["pending_reminders"]) and later["overdue_count"] >= 1
    assert keys["squeeze"]["due"]["local"].endswith("-04:00")
    assert all("reminder_id" in r for r in q.get_batch(ro, bid)["upcoming_reminders"])
    assert g.next_actions(ro, None, clock.now())["batches"][0]["batch_id"] == bid


def test_get_profile_has_guide_sizes_and_schedule(env):
    _s, _c, ro, _w = env
    p = g.get_profile(ro, "soda_ginger_ale")
    assert p["drink_type"] == "soda" and p["guide_available"]
    assert [s["id"] for s in p["stages"]] == ["prep", "bottle", "in_bottle", "refrigerated"]
    assert p["stages"][0]["label"] == "Making it" and "No temperature control" in p["stages"][0]["meaning"]
    assert any("Simmer the grated ginger" in t for t in p["stages"][0]["steps"])
    assert any("Sanitize" in t for t in p["stages"][1]["steps"])
    assert p["ingredients_1gal"] and p["reminders_template"] and p["temperature"]["allowed_target_f"] == [68, 75]
    assert "Carbonation check" in p["guide_sections_1gal"]
    assert p["timeline"]["carbonation_window_h"] == [24, 48]
    if "0.5" in p["batch_sizes_gal"]:
        assert p["ingredients_half_gal"]
    with pytest.raises(q.NotFound):
        g.get_profile(ro, "nope")


def test_list_profiles_hides_legacy(env):
    service, _c, ro, _w = env
    service.conn.execute(
        "INSERT INTO BEVERAGE_PROFILE (id, version, name, source, status, definition_json, content_hash, loaded_at) "
        "VALUES ('old_ale', 1, 'Old ale', 'builtin', 'supported', ?, 'x', 'now')",
        ('{"name": "Old ale", "temperature": {}}',),
    )
    service.conn.commit()
    ids = {p["profile_id"] for p in w.list_profiles(ro)["profiles"]}
    assert "old_ale" not in ids and "soda_ginger_ale" in ids
    every = w.list_profiles(ro, include_legacy=True)
    legacy = [p for p in every["profiles"] if p["profile_id"] == "old_ale"]
    assert legacy and legacy[0]["legacy"] is True
    assert w.list_profiles(ro)["hidden_legacy"] >= 1


def test_advance_stage_default_and_validation(env):
    service, _c, ro, writer = env
    bid = _ginger(ro, writer)
    with pytest.raises(w.WriteRejected, match="not in this batch's schedule"):
        w.advance_stage(ro, writer, bid, "lagering")
    out = w.advance_stage(ro, writer, bid)
    assert out["stage"] == "refrigerated"
    with pytest.raises(w.WriteRejected, match="last stage"):
        w.advance_stage(ro, writer, bid)
    audit = service.conn.execute("SELECT actor FROM AUDIT_LOG WHERE action = 'set_stage'").fetchall()
    assert audit and all(r["actor"] == "mcp" for r in audit)


def test_complete_reminder_by_id_and_by_key(env):
    service, _c, ro, writer = env
    bid = _ginger(ro, writer)
    pending = g.next_actions(ro, bid)["batches"][0]["pending_reminders"]
    first = pending[0]
    done = w.complete_reminder(ro, writer, first["reminder_id"])
    assert done["status"] == "completed"
    with pytest.raises(w.WriteRejected, match="already completed"):
        w.complete_reminder(ro, writer, first["reminder_id"])
    other = pending[1]["key"]
    assert w.complete_reminder(ro, writer, None, bid, other)["status"] == "completed"
    with pytest.raises(w.WriteRejected, match="no pending reminder"):
        w.complete_reminder(ro, writer, None, bid, "nope")
    assert service.conn.execute(
        "SELECT COUNT(*) FROM AUDIT_LOG WHERE actor = 'mcp' AND action = 'complete_reminder'"
    ).fetchone()[0] == 2


def test_log_gravity_with_correction_and_note(env):
    service, _c, ro, writer = env
    bid = w.start_batch(ro, writer, "vessel1", "cider_french_brut", "Brut", None, None)["batch_id"]
    w.log_gravity(ro, writer, bid, 1.050, None, None)
    out = w.log_gravity(ro, writer, bid, 1.010, 80, "smells dry")
    assert out["logged"]["corrected_sg"] == pytest.approx(1.0125, abs=0.0006)
    assert out["est_abv_pct"] == pytest.approx((1.050 - out["logged"]["corrected_sg"]) * 131.25, abs=0.05)
    assert service.conn.execute("SELECT text FROM NOTE WHERE actor = 'mcp'").fetchone()["text"].endswith("smells dry")
    for bad in (0.5, 1.3):
        with pytest.raises(w.WriteRejected, match="0.980-1.200"):
            w.log_gravity(ro, writer, bid, bad)
    assert w.hydrometer_correction(1.000, 60) == pytest.approx(1.000)
