# fermentd.recipe/v1

A recipe file is markdown with YAML frontmatter. The frontmatter is the source of truth for an assistant or a test. The headings below it are the same recipe for a person. Do not put a time, temperature, amount, or safety rule in the prose unless it is already in the frontmatter.

Required frontmatter keys:

- `schema`: `fermentd.recipe/v1`
- `id` and `profile_id`: the beverage profile id
- `batch_number`, `name`, `status`
- `yield.volume_gal`, `yield.bottle_fl_oz`, `yield.bottle_count`
- `tracking_mode`, `target_f`, `pitch_below_f`
- `carbonation_window_h`, `chill_before_open_h`, `drink_within_days`
- `ingredients`: list of `{id, item, amount}` plus optional `grams`, `preparation`, `note`
- `optional`: same shape, or an empty list
- `equipment`: list of strings
- `safety`: list of `{id, text}`
- `steps`: list of `{id, stage, profile_stage, text}` in the order they happen
- `reminders`: the same objects as the profile (`id`, `at`, `text`, optional `repeat`)
- `taste`: one sentence
- `not_this_batch`: `{id, summary}` when a nearby drink is out of scope

Required headings, in order, each as a level-2 heading:

1. Ingredients
2. Equipment
3. Day 0
4. Days 1-3
5. Day 4 and after
6. Safety
7. Taste
8. Not this batch

Amounts stay written strings. Add a numeric field only when the recipe already states that number, such as `grams: 200` on the sugar.
