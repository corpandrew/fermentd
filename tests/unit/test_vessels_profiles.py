from pathlib import Path

from fastapi.testclient import TestClient
from tests.conftest import heater_of, probes_of, service_bundle

from fermentd.web.app import create_app

GINGER = "soda_ginger_ale"


def _setup(tmp_path):
    service, clock, hardware, _notifier = service_bundle(tmp_path)
    service.startup()
    probes_of(hardware).set_temp("28-0000000000b2", 66.0)
    probes_of(hardware).set_temp("28-0000000000a1", 62.0)
    service.tick()
    client = TestClient(create_app(service.conn, service.clock, pump=service.tick))
    return service, clock, hardware, client


def _add_jar(client, rom="28-0000000000c3", name="Second jug"):
    return client.post(
        "/vessels",
        data={
            "name": name,
            "vessel_type": "bottle_group",
            "temp_zone": "zone1",
            "probe_rom_id": rom,
            "capacity_l": "3.8",
            "confirm": "yes",
            "idempotency_key": f"add-{name}",
        },
        follow_redirects=False,
    )


def test_a_vessel_can_be_added_and_two_batches_run_at_once(tmp_path):
    service, clock, hardware, client = _setup(tmp_path)
    probes_of(hardware).set_temp("28-0000000000c3", 67.0)
    added = _add_jar(client)
    assert "error" not in added.headers["location"]
    row = service.conn.execute("SELECT * FROM VESSEL WHERE source = 'dashboard'").fetchone()
    assert row["name"] == "Second jug" and row["temp_zone_id"] == "zone1"
    assert "Second jug" in client.get("/vessels").text
    for vessel_id, key in (("vessel1", "a"), (row["id"], "b")):
        client.post(
            f"/vessels/{vessel_id}/start",
            data={"name": f"Batch {key}", "profile_id": GINGER, "confirm": "yes", "idempotency_key": key},
        )
    active = service.conn.execute("SELECT COUNT(*) AS n FROM BATCH WHERE ended_at IS NULL").fetchone()["n"]
    assert active == 2
    clock.advance(60)
    service.tick()
    assert (
        service.conn.execute(
            "SELECT COUNT(*) AS n FROM READING WHERE vessel_id = ? AND batch_id IS NOT NULL", (row["id"],)
        ).fetchone()["n"]
        >= 1
    )
    # Ending one batch in a shared zone does not touch the heater decision of the other.
    client.post("/vessels/vessel1/end", data={"confirm": "yes", "idempotency_key": "end-a"})
    assert service.conn.execute("SELECT COUNT(*) AS n FROM BATCH WHERE ended_at IS NULL").fetchone()["n"] == 1
    client.post(f"/vessels/{row['id']}/end", data={"confirm": "yes", "idempotency_key": "end-b"})
    assert heater_of(hardware).read_state() is False


def test_the_warmest_vessel_in_a_zone_drives_the_heater(tmp_path):
    service, clock, hardware, client = _setup(tmp_path)
    _add_jar(client)
    jar = service.conn.execute("SELECT id FROM VESSEL WHERE source = 'dashboard'").fetchone()["id"]
    client.post("/vessels/vessel1/start", data={"name": "A", "confirm": "yes", "idempotency_key": "a"})
    target = service.conn.execute("SELECT target_f FROM TEMP_ZONE WHERE id = 'zone1'").fetchone()["target_f"]
    probes_of(hardware).set_temp("28-0000000000b2", target - 6)
    probes_of(hardware).set_temp("28-0000000000c3", target + 0.5)
    clock.advance(600)
    service.tick()
    assert jar
    assert heater_of(hardware).read_state() is False


def test_a_batch_whose_profile_cannot_use_the_zone_target_is_refused(tmp_path):
    service, _clock, hardware, client = _setup(tmp_path)
    probes_of(hardware).set_temp("28-0000000000c3", 67.0)
    _add_jar(client)
    jar = service.conn.execute("SELECT id FROM VESSEL WHERE source = 'dashboard'").fetchone()["id"]
    client.post("/vessels/vessel1/start", data={"name": "A", "confirm": "yes", "idempotency_key": "a"})
    saved = client.post(
        f"/profiles/{GINGER}",
        data={
            "name": "Cool ginger",
            "default_target_f": "66",
            "recommended_low_f": "65",
            "recommended_high_f": "67",
            "allowed_low_f": "64",
            "allowed_high_f": "68",
            "confirm": "yes",
            "idempotency_key": "cool",
        },
        follow_redirects=False,
    )
    assert saved.headers["location"] == f"/profiles/{GINGER}_custom"
    refused = client.post(
        f"/vessels/{jar}/start",
        data={"name": "B", "profile_id": f"{GINGER}_custom", "confirm": "yes", "idempotency_key": "b"},
        follow_redirects=False,
    )
    assert "error=" in refused.headers["location"]
    assert "holding" in client.get(refused.headers["location"]).text
    assert service.conn.execute("SELECT target_f FROM TEMP_ZONE").fetchone()["target_f"] == 72


def test_start_form_lists_profiles_and_groups_unavailable_ones(tmp_path):
    _service, _clock, _hardware, client = _setup(tmp_path)
    page = client.get("/vessels/vessel1").text
    assert 'name="profile_id"' in page
    assert f'value="{GINGER}"' in page
    assert '<optgroup label="Coming later">' in page
    later = page.split('<optgroup label="Coming later">', 1)[1].split("</optgroup>", 1)[0]
    assert "disabled" in later
    assert "(stub)" not in page and "not supported yet" not in page


def test_all_four_sodas_are_available_for_a_jug(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    for vessel_type in ("jug", "bottle_group"):
        _edit(client, "vessel1", f"type-{vessel_type}", vessel_type=vessel_type)
        page = client.get("/vessels/vessel1").text
        available = page.split('name="profile_id"', 1)[1].split("<optgroup", 1)[0]
        for name in ("Ginger ale", "Lemon-lime soda", "Root beer", "Spiced cola"):
            assert name in available, (vessel_type, name)
        assert "disabled" not in available


def test_guides_render_on_profile_pages_and_from_a_running_batch(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    for profile_id in ("soda_ginger_ale", "soda_lemon_lime", "soda_root_beer", "soda_cola"):
        detail = client.get(f"/profiles/{profile_id}")
        assert detail.status_code == 200
        assert "Step-by-step guide" in detail.text
        guide = client.get(f"/profiles/{profile_id}/guide")
        assert guide.status_code == 200
        assert 'type="checkbox" data-step=' in guide.text
        assert "Troubleshooting" in guide.text
        assert "<script" not in guide.text.split('data-guide="', 1)[1].split("</article>", 1)[0]
    assert client.get("/profiles/cider/guide").status_code == 404  # generic placeholder removed
    client.post(
        "/vessels/vessel1/start",
        data={"profile_id": "soda_root_beer", "confirm": "yes", "idempotency_key": "rb"},
    )
    card = client.get("/").text
    assert "/profiles/soda_root_beer/guide?batch=Root+beer+%231" in card


def test_a_disabled_profile_is_rejected_by_the_controller(tmp_path):
    import yaml

    from fermentd.profiles.loader import save_user_profile
    from fermentd.profiles.schema import Profile

    service, _clock, _hardware, client = _setup(tmp_path)
    fixture = Path(__file__).parents[1] / "fixtures" / "profiles" / "disabled_stub.yaml"
    stub = Profile.model_validate(yaml.safe_load(fixture.read_text()))
    assert stub.status == "unsupported_v1"
    save_user_profile(service.conn, stub, "2026-01-01T00:00:00Z")
    service.conn.commit()
    response = client.post(
        "/vessels/vessel1/start",
        data={"name": "Stub", "profile_id": "disabled_stub", "confirm": "yes", "idempotency_key": "stub"},
        follow_redirects=False,
    )
    assert "error=" in response.headers["location"]
    assert service.conn.execute("SELECT COUNT(*) AS n FROM BATCH").fetchone()["n"] == 0


def test_profiles_page_and_builtin_edits_make_a_versioned_copy(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    assert "Ginger ale" in client.get("/profiles").text
    assert "Copy and edit" in client.get(f"/profiles/{GINGER}").text
    assert "Allowed high" in client.get(f"/profiles/{GINGER}?edit=1").text
    data = {"name": "My ginger", "default_target_f": "71", "confirm": "yes"}
    client.post(f"/profiles/{GINGER}", data={**data, "idempotency_key": "e1"})
    builtin = service.conn.execute(
        "SELECT COUNT(*) AS n FROM BEVERAGE_PROFILE WHERE id = ? AND source = 'user'", (GINGER,)
    ).fetchone()["n"]
    assert builtin == 0
    copy = f"{GINGER}_custom"
    client.post(f"/profiles/{copy}", data={**data, "default_target_f": "70", "idempotency_key": "e2"})
    versions = [
        row["version"]
        for row in service.conn.execute("SELECT version FROM BEVERAGE_PROFILE WHERE id = ? ORDER BY version", (copy,))
    ]
    assert versions == [1, 2]
    started = client.post(
        "/vessels/vessel1/start",
        data={"name": "Mine", "profile_id": copy, "confirm": "yes", "idempotency_key": "s"},
        follow_redirects=False,
    )
    assert "error" not in started.headers["location"]
    batch = service.conn.execute("SELECT * FROM BATCH").fetchone()
    assert batch["profile_id"] == copy and batch["target_temp_f"] == 70
    # Running batches keep their snapshot.
    client.post(f"/profiles/{copy}", data={**data, "default_target_f": "69", "idempotency_key": "e3"})
    assert '"default_target_f": 70.0' in service.conn.execute("SELECT profile_snapshot_json FROM BATCH").fetchone()[0]


def test_profile_edits_that_loosen_safety_are_rejected(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    bad = [
        {"cutoff_f": "85"},
        {"allowed_high_f": "79"},
        {"default_target_f": "50", "allowed_low_f": "60"},
        {"default_hysteresis_f": "5"},
        {"cutoff_f": "70"},
        {"reminder_at:squeeze": "whenever"},
    ]
    for index, edits in enumerate(bad):
        response = client.post(
            f"/profiles/{GINGER}",
            data={**edits, "confirm": "yes", "idempotency_key": f"bad-{index}"},
            follow_redirects=False,
        )
        assert "error=" in response.headers["location"], edits
    assert service.conn.execute("SELECT COUNT(*) AS n FROM BEVERAGE_PROFILE WHERE source = 'user'").fetchone()["n"] == 0
    assert client.post(f"/profiles/{GINGER}", data={"confirm": "no", "idempotency_key": "x"}).status_code == 400


def test_user_profiles_survive_a_restart(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    client.post(f"/profiles/{GINGER}", data={"default_target_f": "70", "confirm": "yes", "idempotency_key": "e"})
    service.profiles.pop(f"{GINGER}_custom")
    service.startup()
    assert f"{GINGER}_custom" in service.profiles


def test_busy_dashboard_vessels_cannot_be_removed_and_probes_are_unique(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    _add_jar(client)
    jar = service.conn.execute("SELECT id FROM VESSEL WHERE source = 'dashboard'").fetchone()["id"]
    dup = _add_jar(client, rom="28-0000000000c3", name="Third")
    assert "error=" in dup.headers["location"]
    client.post(f"/vessels/{jar}/start", data={"name": "B", "confirm": "yes", "idempotency_key": "b"})
    busy = client.post(
        f"/vessels/{jar}/edit",
        data={"remove": "yes", "confirm": "yes", "idempotency_key": "rm"},
        follow_redirects=False,
    )
    assert "error=" in busy.headers["location"]
    client.post(f"/vessels/{jar}/end", data={"confirm": "yes", "idempotency_key": "end"})
    client.post(f"/vessels/{jar}/edit", data={"remove": "yes", "confirm": "yes", "idempotency_key": "rm2"})
    assert service.conn.execute("SELECT enabled FROM VESSEL WHERE id = ?", (jar,)).fetchone()["enabled"] == 0


def _edit(client, vessel_id, key, **fields):
    data = {
        "name": "Vessel 1",
        "vessel_type": "bottle_group",
        "temp_zone": "zone1",
        "probe_rom_id": "28-0000000000b2",
        "capacity_l": "3.8",
        "confirm": "yes",
        "idempotency_key": key,
    }
    data.update(fields)
    return client.post(f"/vessels/{vessel_id}/edit", data=data, follow_redirects=False)


def test_config_vessels_are_editable_and_edits_survive_a_restart(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    edited = _edit(client, "vessel1", "e1", name="Kitchen jug", vessel_type="jug")
    assert "error" not in edited.headers["location"]
    client.post("/zones/zone1/rename", data={"name": "Pantry", "confirm": "yes", "idempotency_key": "z"})
    service.startup()
    row = service.conn.execute("SELECT * FROM VESSEL WHERE id = 'vessel1'").fetchone()
    assert (row["name"], row["vessel_type"], row["source"]) == ("Kitchen jug", "jug", "config")
    assert service.conn.execute("SELECT name FROM TEMP_ZONE WHERE id = 'zone1'").fetchone()["name"] == "Pantry"
    assert [vessel.name for vessel in service._vessels()] == ["Kitchen jug"]
    assert "Remove vessel" not in client.get("/vessels").text.split("vessel1", 1)[1].split("</tr>", 1)[0]
    removed = client.post(
        "/vessels/vessel1/edit",
        data={"remove": "yes", "confirm": "yes", "idempotency_key": "rmc"},
        follow_redirects=False,
    )
    assert "error=" in removed.headers["location"]


def test_a_running_batch_allows_rename_only(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    client.post("/vessels/vessel1/start", data={"confirm": "yes", "idempotency_key": "s"})
    assert "error" not in _edit(client, "vessel1", "r1", name="Renamed").headers["location"]
    assert service.conn.execute("SELECT name FROM VESSEL WHERE id = 'vessel1'").fetchone()["name"] == "Renamed"
    for key, change in (
        ("t", {"vessel_type": "jug"}),
        ("p", {"probe_rom_id": "28-0000000000ff"}),
        ("z", {"temp_zone": ""}),
    ):
        assert "error=" in _edit(client, "vessel1", key, name="Renamed", **change).headers["location"]


def test_card_titles_and_default_batch_names(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    page = client.get("/").text
    assert "Vessel 1" in page and "No batch running" in page
    assert "Zone 1" not in page
    assert 'value="Ginger ale #1"' in page
    assert "required" not in page.split("data-batch-name")[0].rsplit("<input", 1)[1]
    client.post("/vessels/vessel1/start", data={"name": "", "confirm": "yes", "idempotency_key": "s"})
    batch = service.conn.execute("SELECT name FROM BATCH").fetchone()["name"]
    assert batch == "Ginger ale #1"
    page = client.get("/").text
    assert '<a href="/vessels/vessel1">Ginger ale #1</a>' in page
    assert "Ginger ale · Vessel 1" in page
    client.post("/vessels/vessel1/end", data={"confirm": "yes", "idempotency_key": "e"})
    assert 'value="Ginger ale #2"' in client.get("/").text


def test_zone_label_shows_only_with_two_zones(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    service.conn.execute(
        """INSERT INTO TEMP_ZONE (id, name, capability, actuator_driver, target_f, hysteresis_f)
           VALUES ('zone2', 'Garage', 'heat', 'sim', 70, 1)"""
    )
    service.conn.commit()
    _add_jar(client, name="Garage jug")
    jar = service.conn.execute("SELECT id FROM VESSEL WHERE source = 'dashboard'").fetchone()["id"]
    service.conn.execute("UPDATE VESSEL SET temp_zone_id = 'zone2', probe_rom_id = NULL WHERE id = ?", (jar,))
    service.conn.commit()
    page = client.get("/").text
    assert "Zone 1" in page and "Garage" in page


def test_cider_is_available_for_a_jug_only_and_walks_its_stages(tmp_path):
    service, clock, _hardware, client = _setup(tmp_path)
    page = client.get("/vessels/vessel1").text
    later = page.split('<optgroup label="Coming later">', 1)[1].split("</optgroup>", 1)[0]
    assert "French-style brut cider" in later
    _edit(client, "vessel1", "to-jug", vessel_type="jug")
    page = client.get("/vessels/vessel1").text
    available = page.split('name="profile_id"', 1)[1].split("<optgroup", 1)[0]
    assert 'value="cider_french_brut"' in available
    assert 'value="cider"' not in page
    client.post(
        "/vessels/vessel1/start",
        data={"profile_id": "cider_french_brut", "confirm": "yes", "idempotency_key": "cider"},
    )
    batch = service.conn.execute("SELECT * FROM BATCH").fetchone()
    assert (batch["stage"], batch["target_temp_f"]) == ("primary", 62)
    assert service.conn.execute("SELECT target_f FROM TEMP_ZONE").fetchone()["target_f"] == 62
    keys = {r["reminder_key"] for r in service.conn.execute("SELECT reminder_key FROM REMINDER")}
    assert keys == {"airlock", "gravity", "rack"}
    vessel = client.get("/vessels/vessel1").text
    assert "Racked to secondary" in vessel and "Guide" in vessel
    for stage in ("secondary", "aging", "bottle", "bottle_condition", "cellared"):
        response = client.post(
            "/vessels/vessel1/stage",
            data={"stage": stage, "confirm": "yes", "idempotency_key": f"st-{stage}"},
            follow_redirects=False,
        )
        assert "error" not in response.headers["location"], stage
    assert service.conn.execute("SELECT stage FROM BATCH").fetchone()["stage"] == "cellared"
    assert client.get("/profiles/cider_french_brut/guide").status_code == 200


def test_batch_size_is_picked_at_start_and_carried_to_the_guide(tmp_path):
    service, _clock, _hardware, client = _setup(tmp_path)
    _edit(client, "vessel1", "to-jug", vessel_type="jug")
    page = client.get("/vessels/vessel1").text
    assert 'name="batch_size_gal"' in page
    available = page.split('name="profile_id"', 1)[1].split("<optgroup", 1)[0]
    for pid in (
        "lager_pilsner",
        "lager_helles",
        "lager_marzen",
        "wine_concord",
        "wine_blackberry",
        "cider_french_brut",
    ):
        assert f'value="{pid}"' in available, pid
        assert client.get(f"/profiles/{pid}/guide").status_code == 200
        half = client.get(f"/profiles/{pid}/guide?size=0.5")
        assert half.status_code == 200 and "<strong>Half gallon</strong>" in half.text
    assert "Mead" not in page
    client.post(
        "/vessels/vessel1/start",
        data={"profile_id": "lager_pilsner", "batch_size_gal": "0.5", "confirm": "yes", "idempotency_key": "pils"},
    )
    batch = service.conn.execute("SELECT * FROM BATCH").fetchone()
    assert (batch["stage"], batch["target_temp_f"]) == ("primary", 50)
    assert abs(batch["volume_l"] - 1.893) < 0.01
    card = client.get("/").text
    assert "/profiles/lager_pilsner/guide?batch=" in card and "size=0.5" in card
    response = client.post(
        "/vessels/vessel1/stage",
        data={"stage": "diacetyl_rest", "confirm": "yes", "idempotency_key": "dr"},
        follow_redirects=False,
    )
    assert "error" not in response.headers["location"]


def test_jar_and_bottle_profiles_have_guides_at_both_sizes(tmp_path):
    _service, _clock, _hardware, client = _setup(tmp_path)
    for pid in (
        "kombucha_black_tea",
        "kombucha_ginger_lemon",
        "kombucha_berry",
        "water_kefir_lemon",
        "water_kefir_grape",
        "water_kefir_ginger_lime",
        "ginger_beer_jamaican",
    ):
        for q in ("", "?size=0.5"):
            assert client.get(f"/profiles/{pid}/guide{q}").status_code == 200, pid
    page = client.get("/profiles").text
    assert "Mead" not in page and "Kombucha, berry" in page
