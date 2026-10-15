from pathlib import Path

import pytest

from fermentd.profiles.recipe import categories, load_recipe, parse_recipe
from fermentd.web.markdown import load_guide

RECIPES = sorted(Path("docs/recipes").glob("*_*.md"))


def _headings(body: str) -> list[str]:
    return [line[3:].strip() for line in body.splitlines() if line.startswith("## ")]


@pytest.mark.parametrize("path", RECIPES, ids=lambda p: p.stem)
def test_recipe_sections_follow_its_category(path):
    recipe = load_recipe(path)
    layout = categories()[recipe["category"]]
    headings = _headings(recipe["body"])
    assert set(layout["required"]) <= set(headings)
    assert all(h in layout["sections"] for h in headings)


def test_sections_differ_between_kinds_of_drink():
    soda = _headings(load_recipe(Path("docs/recipes/soda_ginger_ale.md"))["body"])
    lager = _headings(load_recipe(Path("docs/recipes/lager_pilsner.md"))["body"])
    kombucha = _headings(load_recipe(Path("docs/recipes/kombucha_black_tea.md"))["body"])
    assert "Diacetyl rest" in lager and "Diacetyl rest" not in soda
    assert "SCOBY care" in kombucha and "Brew day" not in kombucha
    assert "Carbonation check" in soda and "Day 0" not in soda


def test_unknown_category_and_stray_section_rejected():
    text = Path("docs/recipes/soda_ginger_ale.md").read_text()
    with pytest.raises(ValueError, match="category"):
        parse_recipe(text.replace("category: soda", "category: nope"))
    with pytest.raises(ValueError, match="not in its layout"):
        parse_recipe(text.replace("## Safety", "## Diacetyl rest\n\nx\n\n## Safety"))


def _tile_keys(rel, size="1"):
    return [t["k"] for t in load_guide(rel, size=size)["tiles"]]


def test_tiles_match_the_drink():
    soda = _tile_keys("docs/recipes/soda_ginger_ale.md")
    assert "Carbonate" in soda and "OG / ABV" not in soda and "Bitterness" not in soda
    kombucha = _tile_keys("docs/recipes/kombucha_black_tea.md")
    assert "Starting pH" in kombucha and "OG / ABV" not in kombucha
    lager = _tile_keys("docs/recipes/lager_pilsner.md")
    assert "Bitterness" in lager and "OG / ABV" in lager
    cider = _tile_keys("docs/recipes/cider_french_brut.md")
    assert "Bitterness" not in cider


def test_hop_schedule_scales_and_only_for_beer():
    full = load_guide("docs/recipes/lager_pilsner.md", size="1")
    half = load_guide("docs/recipes/lager_pilsner.md", size="0.5")
    assert full["hops"] and len(full["hops"]) == len(half["hops"])
    assert [h["amount"] for h in full["hops"]] != [h["amount"] for h in half["hops"]]
    assert not load_guide("docs/recipes/soda_ginger_ale.md")["hops"]
