from pathlib import Path

import pytest

from fermentd.profiles.loader import load_profiles
from fermentd.profiles.schema import check_against_globals
from fermentd.web.markdown import load_guide

NEW = [
    "cider_keeved",
    "cider_perry",
    "cider_cranberry_apple",
    "cider_hopped",
    "wine_sparkling_chardonnay",
    "ale_spiced_holiday",
]


@pytest.mark.parametrize("pid", NEW)
def test_new_profiles_fit_the_heat_only_rig_and_scale(pid):
    profile = load_profiles()[pid]
    check_against_globals(profile)
    assert profile.temperature.allowed_target_f[1] < profile.safety.cutoff_f <= 75
    assert all(s.target_f is None or s.target_f <= 75 for s in profile.stages)
    full, half = load_guide(profile.recipe, size="1"), load_guide(profile.recipe, size="0.5")
    assert full["html"] != half["html"]


def test_sparkling_chardonnay_numbers_and_bottle_warning():
    guide = load_guide("docs/recipes/wine_sparkling_chardonnay.md")
    tiles = {t["k"]: t["v"] for t in guide["tiles"]}
    assert tiles["Tirage"].startswith("24 g/L") and "6 atm" in tiles["Tirage"]
    assert "Dosage" in tiles and "En tirage" in tiles and "Bitterness" not in tiles
    html = guide["html"]
    for phrase in ("91 g", "29 mm", "bidule", "Riddling", "Disgorge", "12 oz beer bottles are not safe"):
        assert phrase in html, phrase
    assert "45 g" in load_guide("docs/recipes/wine_sparkling_chardonnay.md", size="0.5")["html"]


def test_keeved_cider_bottles_sweet_and_hopped_cider_has_hop_table():
    keeve = load_guide("docs/recipes/cider_keeved.md")
    assert {t["k"]: t["v"] for t in keeve["tiles"]}["Bottle at"] == "SG 1.020–1.025"
    assert "chapeau brun" in keeve["html"] and "No yeast nutrient" in keeve["html"]
    hops = load_guide("docs/recipes/cider_hopped.md", size="0.5")["hops"]
    assert [h["amount"] for h in hops] == ["4 g", "4 g"] and all(h["when"] == "dry hop" for h in hops)
    assert "sorbitol" in Path("docs/recipes/cider_perry.md").read_text()
