from pathlib import Path

from fermentd.profiles.loader import load_profiles
from fermentd.profiles.recipe import load_recipe, required_sections

RECIPE = Path("docs/recipes/soda_ginger_ale.md")


def test_ginger_ale_recipe_matches_the_profile():
    recipe = load_recipe(RECIPE)
    profile = load_profiles()["soda_ginger_ale"]
    assert recipe["schema"] == "fermentd.recipe/v1"
    assert recipe["id"] == "soda_ginger_ale"
    assert recipe["profile_id"] == "soda_ginger_ale"
    assert recipe["target_f"] == 72
    assert recipe["pitch_below_f"] == 80
    assert recipe["carbonation_window_h"] == [24, 48]
    assert recipe["not_this_batch"]["id"] == "soda_ginger_beer"
    assert profile.reminders
    dumped = [item.model_dump(exclude_none=True) for item in profile.reminders]
    assert recipe["reminders"] == dumped
    for heading in required_sections(recipe["category"]):
        assert f"## {heading}\n" in recipe["body"]
    sugar = next(item for item in recipe["ingredients"] if item["id"] == "sugar")
    assert sugar["grams"] == 200
    assert recipe["ingredients"][-1]["item"] == "EC-1118 yeast"
