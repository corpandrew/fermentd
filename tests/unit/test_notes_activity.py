"""Batch notes with photos, the per-batch activity log and the batch diary timeline."""

import io
import re

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from tests.conftest import probes_of, service_bundle

from fermentd.control import notes as nt
from fermentd.mcp import diary as d
from fermentd.mcp import queries as q
from fermentd.mcp import tastes as t
from fermentd.mcp import writes as w
from fermentd.web.app import create_app


@pytest.fixture
def env(tmp_path):
    service, clock, hardware, _n = service_bundle(tmp_path)
    service.startup()
    probes_of(hardware).set_temp("28-0000000000b2", 72.0)
    probes_of(hardware).set_temp("28-0000000000a1", 65.0)
    service.tick()
    service.conn.execute("UPDATE VESSEL SET vessel_type = 'jug' WHERE id = 'vessel1'")
    service.conn.commit()
    ro = q.connect_ro(tmp_path / "fermentd.db")
    writer = w.Writer(conn=service.conn, pump=service.tick, clock=clock)
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    return service, clock, ro, writer, client, tmp_path


def _jpeg(w_px=3000, h_px=2000) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w_px, h_px), (200, 150, 60)).save(buf, "JPEG")
    return buf.getvalue()


def _form(key):
    return {"confirm": "yes", "idempotency_key": key}


def test_mcp_notes_and_activity_are_audited_and_plain_english(env):
    service, clock, ro, writer, client, _p = env
    bid = w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "GA", None, None)["batch_id"]
    clock.advance(60)
    out = d.add_batch_note(ro, writer, bid, "Lots of bubbles")
    assert out["added"]["text"] == "Lots of bubbles" and out["added"]["source"] == "Grok Bot (via MCP)"
    assert out["added"]["photo_url"] is None
    clock.advance(60)
    t.add_batch_tweak(ro, writer, bid, "change", "ginger", "6 oz")
    t.log_tasting(ro, writer, bid, 4, make_again=True)
    with pytest.raises(w.WriteRejected, match="empty"):
        d.add_batch_note(ro, writer, bid, "  ")
    notes = d.list_batch_notes(ro, bid)
    assert notes["count"] == 1 and notes["notes"][0]["at"]["zone"] == "America/New_York"
    act = d.get_batch_activity(ro, bid)["activity"]
    whats = [a["what"] for a in act]
    assert whats[0] == "Tasted it: 4/5, would make again"
    assert "Recipe change: fresh ginger: 4 oz → 6 oz" in whats and "Added a note" in whats
    assert whats[-1].startswith("Started “GA”") and all(a["source"] == "Grok Bot (via MCP)" for a in act)
    assert len(d.get_batch_activity(ro, bid, limit=2)["activity"]) == 2
    audit = service.conn.execute("SELECT actor, batch_id FROM AUDIT_LOG WHERE action = 'add_note'").fetchall()
    assert audit and all(r["actor"] == "mcp" and r["batch_id"] == bid for r in audit)


def test_activity_covers_stage_target_reminder_gravity_end_and_skips_automatic_changes(env):
    service, clock, ro, writer, client, _p = env
    bid = w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "GA", None, None)["batch_id"]
    client.post("/vessels/vessel1/target", data={**_form("t1"), "target_f": "73"})
    from fermentd.mcp import guide as g
    g.log_gravity(ro, writer, bid, 1.012) if hasattr(g, "log_gravity") else w.log_gravity(ro, writer, bid, 1.012)
    service.conn.execute("UPDATE REMINDER SET due_at = '2000-01-01T00:00:00Z' WHERE batch_id = ?", (bid,))
    service.conn.commit()
    rem = service.conn.execute("SELECT id, text FROM REMINDER WHERE batch_id = ? LIMIT 1", (bid,)).fetchone()
    service.submit("web", "complete_reminder", {"batch_id": bid, "reminder_id": rem["id"]}, "r1")
    service.submit("web", "set_stage", {"batch_id": bid, "stage": "refrigerated"}, "s1")
    clock.advance(30)
    service.tick()
    w.end_batch(ro, writer, bid)
    rows = nt.activity(service.conn, bid)
    texts = [r["text"] for r in rows]
    assert texts[0] == "Ended the batch"
    assert "Moved to the next step: " + __import__("fermentd.web.status", fromlist=["x"]).stage_label("refrigerated") in texts
    assert f"Marked a reminder done: {rem['text']}" in texts
    assert "Logged a gravity reading of 1.012" in texts
    assert any(x.startswith("Set the target temperature to 73") for x in texts)
    assert {r["source"] for r in rows} == {"Dashboard", "Grok Bot (via MCP)"}
    assert not any("heat" in x.lower() and "mat" in x.lower() for x in texts)
    # rejected commands do not show up
    service.submit("web", "set_stage", {"batch_id": bid, "stage": "nope"}, "s2")
    assert len(nt.activity(service.conn, bid)) == len(rows)


def test_photo_upload_is_downscaled_with_thumbnail_and_served(env):
    service, clock, ro, writer, client, tmp_path = env
    bid = w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "GA", None, None)["batch_id"]
    r = client.post(f"/batches/{bid}/notes", data={**_form("n1"), "text": "Day 1"},
                    files={"photo": ("IMG_1.jpg", _jpeg(), "image/jpeg")}, follow_redirects=False)
    assert r.status_code == 303
    note = service.conn.execute("SELECT * FROM NOTE WHERE batch_id = ?", (bid,)).fetchone()
    big, thumb = tmp_path / "photos" / note["photo"], tmp_path / "photos" / note["thumb"]
    assert max(Image.open(big).size) == 1600 and max(Image.open(thumb).size) == 320
    assert note["actor"] == "web"
    assert client.get(f"/photos/{note['thumb']}").headers["content-type"] == "image/jpeg"
    assert client.get("/photos/..%2Fsecrets.yaml").status_code == 404
    # re-submitting the same form does not store a second photo
    client.post(f"/batches/{bid}/notes", data={**_form("n1"), "text": "Day 1"},
                files={"photo": ("IMG_1.jpg", _jpeg(), "image/jpeg")})
    assert len(list((tmp_path / "photos").iterdir())) == 2
    bad = client.post(f"/batches/{bid}/notes", data={**_form("n2"), "text": "x"},
                      files={"photo": ("a.jpg", b"not an image", "image/jpeg")}, follow_redirects=False)
    assert "error=" in bad.headers["location"]
    listed = d.list_batch_notes(ro, bid)["notes"][0]
    assert listed["photo_url"].endswith(f"/photos/{note['photo']}")


def test_photo_links_follow_the_configured_dashboard_url(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FERMENTD_DASHBOARD_URL", raising=False)
    assert d.dashboard_url() == "http://127.0.0.1:8080"
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "fermentd.env").write_text("# local\nFERMENTD_DASHBOARD_URL=\"https://dash.example.com/\"\n")
    assert d.dashboard_url() == "https://dash.example.com"
    monkeypatch.setenv("FERMENTD_DASHBOARD_URL", "http://100.64.0.1:8080")
    assert d.dashboard_url() == "http://100.64.0.1:8080"


def test_timeline_mixes_notes_and_actions_with_filter_and_survives_end(env):
    service, clock, ro, writer, client, _p = env
    bid = w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "Diary test", None, None)["batch_id"]
    clock.advance(60)
    client.post(f"/batches/{bid}/notes", data={**_form("n1"), "text": "Smells gingery"})
    clock.advance(60)
    t.log_tasting(ro, writer, bid, 5)
    page = client.get("/vessels/vessel1").text
    assert "Batch diary" in page and "Smells gingery" in page and "Tasted it: 5/5" in page
    assert 'accept="image/*"' in page and "capture" in page
    assert page.count("Added a note") == 0  # the note itself is the entry
    only = client.get("/vessels/vessel1?show=notes").text
    assert "Smells gingery" in only and "Tasted it: 5/5" not in only
    w.end_batch(ro, writer, bid)
    hist = client.get(f"/history/{bid}").text
    assert "Smells gingery" in hist and "Ended the batch" in hist


def test_migration_backfills_batch_links(env):
    service, clock, ro, writer, client, _p = env
    conn = service.conn
    clock.advance(60)
    bid = w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "GA", None, None)["batch_id"]
    assert bid == 1
    # An old audit row for a deleted batch that had the same id, from before this batch started.
    cid = conn.execute("SELECT MIN(id) FROM COMMAND").fetchone()[0]
    conn.execute("INSERT INTO AUDIT_LOG (ts, actor, action, target, new_value, command_id) "
                 "VALUES ('2000-01-01T00:00:00Z', 'web', 'end_batch', 'vessel1', '{\"ok\": true, \"batch_id\": 1}', ?)",
                 (cid,))
    clock.advance(60)
    client.post("/vessels/vessel1/target", data={**_form("t1"), "target_f": "73"})
    clock.advance(60)
    t.log_tasting(ro, writer, bid, 3)
    conn.execute("UPDATE AUDIT_LOG SET batch_id = NULL")
    sql = __import__("pathlib").Path("src/fermentd/db/migrations/0010_notes_activity.sql").read_text()
    for stmt in re.findall(r"UPDATE AUDIT_LOG SET batch_id = .*?;", sql, flags=re.S):
        conn.execute(stmt)
    texts = [a["text"] for a in nt.activity(conn, bid)]
    assert texts[0] == "Tasted it: 3/5" and texts[-1].startswith("Started")
    assert any(x.startswith("Set the target temperature to 73") for x in texts)
    assert "Ended the batch" not in texts  # the reused id's old row stays unlinked


def test_deleting_a_batch_removes_its_photos(env):
    service, clock, ro, writer, client, tmp_path = env
    bid = w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "GA", None, None)["batch_id"]
    client.post(f"/batches/{bid}/notes", data={**_form("n1"), "text": ""},
                files={"photo": ("IMG.jpg", _jpeg(400, 300), "image/jpeg")})
    t.add_batch_tweak(ro, writer, bid, "change", "ginger", "6 oz")
    t.log_tasting(ro, writer, bid, 4)
    t.save_tweaks_as_variant(ro, writer, bid, "Mine")
    w.end_batch(ro, writer, bid)
    assert len(list((tmp_path / "photos").iterdir())) == 2
    client.post(f"/history/{bid}/delete", data=_form("del"))
    assert service.conn.execute("SELECT COUNT(*) FROM BATCH").fetchone()[0] == 0
    assert list((tmp_path / "photos").iterdir()) == []
    assert t.list_variants(ro)["variants"][0]["name"] == "Mine"  # your saved version survives


def test_get_vessel_heater_and_page_show_the_safety_cutoff(env):
    service, clock, ro, writer, client, _p = env
    from tests.conftest import heater_of
    heater = heater_of(service.hardware)
    heater.countdown_supported = True
    w.start_batch(ro, writer, "vessel1", "soda_ginger_ale", "GA", None, None)
    probes_of(service.hardware).set_temp("28-0000000000b2", 66.0)
    service.tick()
    assert heater.on
    clock.advance(10)
    service.tick()
    out = q.get_vessel_heater(ro, "vessel1", clock.now())
    assert out["safety_cutoff"]["state"] == "armed" and out["safety_cutoff"]["minutes_left"] == 10
    assert "Safety cutoff: armed (10 min)" in client.get("/vessels/vessel1").text
