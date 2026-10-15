from pathlib import Path

import pytest
import yaml

from fermentd.profiles.loader import load_profiles
from fermentd.profiles.schema import Profile, check_against_globals


def test_builtin_profiles_load_and_the_sodas_are_supported():
    profiles = load_profiles()
    ginger = profiles["soda_ginger_ale"]
    assert ginger.status == "supported"
    assert ginger.tracking_mode == "timer"
    assert ginger.default_stage == "in_bottle"
    assert ginger.temperature.default_target_f == 72
    assert [stage.id for stage in ginger.stages] == ["prep", "bottle", "in_bottle", "refrigerated"]
    supported = sorted(profile.id for profile in profiles.values() if profile.status == "supported")
    assert set(SPECIFIC) <= set(supported)
    for retired in (
        "mead",
        "ale",
        "lager",
        "cider",
        "kombucha",
        "water_kefir",
        "soda_ginger_beer",
        "wine",
        "wine_red",
        "wine_white",
    ):
        assert retired not in profiles


def test_profile_cannot_loosen_global_limits():
    document = yaml.safe_load(Path("src/fermentd/profiles/builtin/soda_ginger_ale.yaml").read_text())
    document["temperature"]["allowed_target_f"] = [45, 85]
    profile = Profile.model_validate(document)
    with pytest.raises(ValueError, match="outside the global"):
        check_against_globals(profile)

    document = yaml.safe_load(Path("src/fermentd/profiles/builtin/soda_ginger_ale.yaml").read_text())
    document["safety"]["cutoff_f"] = 90
    profile = Profile.model_validate(document)
    with pytest.raises(ValueError, match="cutoff_f"):
        check_against_globals(profile)


def test_user_file_merges_over_a_builtin(tmp_path: Path):
    user = tmp_path / "profiles.d"
    user.mkdir()
    (user / "soda_ginger_ale.yaml").write_text("id: soda_ginger_ale\ntemperature:\n  default_target_f: 70\n")
    profiles = load_profiles(user)
    assert profiles["soda_ginger_ale"].temperature.default_target_f == 70
    assert profiles["soda_ginger_ale"].temperature.allowed_target_f == (68, 75)


SODAS = ["soda_ginger_ale", "soda_lemon_lime", "soda_root_beer", "soda_cola"]


@pytest.mark.parametrize("profile_id", SODAS)
def test_soda_profiles_match_ginger_ale_and_their_guides(profile_id):
    from fermentd.profiles.recipe import load_recipe, required_sections

    profiles = load_profiles()
    ginger = profiles["soda_ginger_ale"]
    profile = profiles[profile_id]
    check_against_globals(profile)
    assert profile.status == "supported"
    assert profile.tracking_mode == "timer"
    assert profile.requires_capability == ["heat"]
    assert set(profile.vessel_types) == {"jug", "bottle_group"}
    assert profile.temperature == ginger.temperature
    assert [stage.id for stage in profile.stages] == [stage.id for stage in ginger.stages]
    assert [(r.id, r.at, r.repeat) for r in profile.reminders] == [(r.id, r.at, r.repeat) for r in ginger.reminders]
    recipe = load_recipe(Path(profile.recipe))
    assert recipe["profile_id"] == profile_id
    assert recipe["target_f"] == 72 and recipe["pitch_below_f"] == 80
    assert recipe["reminders"] == [item.model_dump(exclude_none=True) for item in profile.reminders]
    assert recipe["ingredients"][-1] == {
        "id": "yeast",
        "item": "EC-1118 yeast",
        "amount": "1/8 tsp",
        "note": "Lalvin EC-1118, about 1/8 tsp per gallon",
    }
    for heading in required_sections(recipe["category"]):
        assert f"## {heading}\n" in recipe["body"]
    body = recipe["body"]
    assert "1-2 inches of headspace" in body
    assert "below 80 F" in body
    assert "rock hard" in body


def test_no_builtin_profile_name_says_stub():
    assert all("stub" not in profile.name.lower() for profile in load_profiles().values())


def test_french_brut_cider_profile_and_guide():
    from fermentd.profiles.loader import profile_safety_errors
    from fermentd.profiles.recipe import load_recipe, required_sections

    profile = load_profiles()["cider_french_brut"]
    check_against_globals(profile)
    assert profile_safety_errors(profile) is None
    assert profile.status == "supported"
    assert profile.tracking_mode == "timer"
    assert profile.requires_capability == ["heat"]
    assert profile.vessel_types == ["jug"]
    assert profile.default_stage == "primary"
    assert profile.temperature.default_target_f == 62
    low, high = profile.temperature.allowed_target_f
    assert 50 <= low <= 62 <= high <= 75
    assert profile.safety.cutoff_f is not None and high < profile.safety.cutoff_f <= 80
    assert [s.id for s in profile.stages] == ["prep",
        "primary",
        "secondary",
        "aging",
        "bottle",
        "bottle_condition",
        "cellared",
    ]
    keys = [r.id for r in profile.reminders]
    assert {"airlock", "gravity", "rack", "clear_check", "tester", "condition_done"} <= set(keys)
    recipe = load_recipe(Path(profile.recipe))
    assert recipe["reminders"] == [item.model_dump(exclude_none=True) for item in profile.reminders]
    assert recipe["og_target"] == [1.045, 1.055]
    assert recipe["abv_expected"] == [5.5, 7.0]
    assert recipe["priming"]["table_sugar_g"] == 25
    body = recipe["body"]
    for heading in required_sections(recipe["category"]):
        assert f"## {heading}\n" in body
    for phrase in ("sorbate", "Hydrometer", "3 readings over 3 days", "keeving", "chapeau brun", "non-fermentable"):
        assert phrase.lower() in body.lower(), phrase


SPECIFIC = (
    "ale_saison",
    "ale_kveik",
    "ale_bitter",
    "ale_pale",
    "kombucha_black_tea",
    "kombucha_ginger_lemon",
    "kombucha_berry",
    "water_kefir_lemon",
    "water_kefir_grape",
    "water_kefir_ginger_lime",
    "ginger_beer_quick",
    "ginger_beer_jamaican",
    "soda_cola",
    "soda_ginger_ale",
    "soda_lemon_lime",
    "soda_root_beer",
    "lager_pilsner",
    "lager_helles",
    "lager_marzen",
    "wine_blackberry",
    "wine_concord",
    "cider_french_brut",
)
NEW = SPECIFIC[:12]
WINTER = ("lager_pilsner", "lager_helles", "lager_marzen", "wine_blackberry", "wine_concord", "cider_french_brut")


@pytest.mark.parametrize("profile_id", WINTER + NEW)
def test_winter_profiles_match_their_guides_and_scale(profile_id):
    from fermentd.profiles.loader import profile_safety_errors
    from fermentd.profiles.recipe import load_recipe, required_sections
    from fermentd.web.markdown import load_guide

    profile = load_profiles()[profile_id]
    check_against_globals(profile)
    assert profile_safety_errors(profile) is None
    assert profile.status == "supported" and profile.requires_capability == ["heat"]
    recipe = load_recipe(Path(profile.recipe))
    assert recipe["reminders"] == [item.model_dump(exclude_none=True) for item in profile.reminders]
    stage_ids = {s.id for s in profile.stages}
    assert {step["profile_stage"] for step in recipe["steps"]} <= stage_ids
    for heading in required_sections(recipe["category"]):
        assert f"## {heading}\n" in recipe["body"]
    full = load_guide(profile.recipe, size="1")
    half = load_guide(profile.recipe, size="0.5")
    assert full["sizes"] == ["1", "0.5"]
    assert (full["meta"]["yield"]["volume_gal"], half["meta"]["yield"]["volume_gal"]) == (1, 0.5)
    for guide in (full, half):
        assert "[[" not in guide["html"] and "]]" not in guide["html"]
    assert "Half-gallon" in half["html"] or "half batch is fine" in half["html"]
    assert "not need" in half["html"]  # yeast, SCOBY or grains are not halved
    assert full["html"] != half["html"]
    assert all(item.get("amount_half") for item in recipe["ingredients"])


def test_lagers_are_heat_only_floor_with_a_cold_spot_note():
    for pid, og in (
        ("lager_pilsner", [1.046, 1.050]),
        ("lager_helles", [1.046, 1.050]),
        ("lager_marzen", [1.052, 1.056]),
    ):
        profile = load_profiles()[pid]
        assert profile.temperature.default_target_f == 50
        assert [s.id for s in profile.stages] == ["prep",
            "primary",
            "diacetyl_rest",
            "lagering",
            "bottle",
            "bottle_condition",
            "cellared",
        ]
        assert "unheated" in profile.guidance.note
        from fermentd.profiles.recipe import load_recipe

        recipe = load_recipe(Path(profile.recipe))
        assert recipe["og_target"] == og
        assert recipe["priming"]["table_sugar_g"] == 22
        assert "floor" in recipe["body"] and "diacetyl" in recipe["body"].lower()


def test_wines_are_still_and_warn_about_sweetening():
    for pid in ("wine_blackberry", "wine_concord"):
        profile = load_profiles()[pid]
        assert profile.carbonation.default == "still"
        from fermentd.profiles.recipe import load_recipe

        body = load_recipe(Path(profile.recipe))["body"]
        assert "potassium sorbate" in body and "0.998" in body


def test_warm_profiles_fit_the_75_f_cap_and_cultures_have_safety_rules():
    from fermentd.profiles.recipe import load_recipe

    profiles = load_profiles()
    for pid in NEW:
        profile = profiles[pid]
        assert profile.temperature.allowed_target_f[1] <= 75
        assert profile.temperature.default_target_f >= 66
        assert "75 F" in profile.guidance.note
    for pid in ("kombucha_black_tea", "kombucha_ginger_lemon", "kombucha_berry"):
        body = load_recipe(Path(profiles[pid].recipe))["body"]
        assert "4.5 or lower" in body and "Mold" in body
    quick = load_recipe(Path(profiles["ginger_beer_quick"].recipe))
    assert quick["og_target"] == [1.030, 1.034] and quick["priming"]["table_sugar_g"] == 25
