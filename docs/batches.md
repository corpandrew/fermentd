# Vessels, profiles and batches

## Vessels, zones, probes and scales

- A **vessel** is something you ferment in: `jug`, `carboy`, `bucket`, `jar` or `bottle_group`
  (a set of bottles treated as one). Each vessel can have a DS18B20 **probe** (`probe_rom_id`) and,
  optionally, a load-cell **scale**.
- A **temperature zone** is one heat mat (one smart plug) and one target. Several vessels can share a
  zone, for example a jug and a group of bottles in the same cooler. A vessel with no zone is
  **monitor-only**: fermentd logs its temperature but never heats it.
- Vessels are added, edited and removed on the dashboard at `/vessels`. `fermentd.yaml` only seeds
  them: once a vessel or zone is edited on the dashboard, the database copy wins. Ids never change.
  While a batch is running a vessel can be renamed, but its type, zone, probe and capacity are locked.

**Zone rule (one heater, one decision).** The first batch in an empty zone sets the zone target from
its profile. A later batch in a busy zone adopts the current target and is refused if that target is
outside its profile's allowed range. The heater is driven from the **warmest** vessel probe, so no
vessel is pushed past the target, and the zone is tuned for its slowest vessel type.

**Scales** (planned hardware, finished software): with `scale:` set on a vessel, the controller
samples the HX711 every `sample_interval_s` (default 5 minutes, median of 15 reads). Tare and
calibrate from the vessel page or with `fermentd-ctl scale-tare <vessel>` /
`fermentd-ctl scale-calibrate <vessel> --grams 1000`; the values are stored in the database. Weight
lost is treated as CO2 leaving through the airlock, giving an estimated ABV (CO2 g / litres / 7.9).
Sudden drops of more than 30 g (a sample taken, the jug moved) are ignored. The scale raises
"fermentation is slowing" and "fermentation has gone quiet" (weight stable for 48 hours) alerts.

## Profiles and guides

A **profile** describes a drink: its allowed temperature range and default target, the stages and
any temperature steps or ramps in each stage, reminders, alert tweaks, a tighter safety cutoff if
needed, carbonation limits, and a link to a recipe in [recipes/](recipes/).

There are 28 built-in profiles across ciders, sodas, ginger beers, ales, lagers, wines, kombucha and
water kefir. All of them use heating only. Browse them at `/profiles`; each has a step-by-step guide
page at `/profiles/<id>/guide` built from its recipe.

Built-ins are read-only. Editing one on the dashboard saves your own copy (`<id>_custom`); editing a
copy adds a new version. Edits are checked against the global limits (targets 50–75°F, hysteresis
0.5–3°F, cutoff never above 80°F). Running batches keep the profile snapshot they started with.

## Batch lifecycle

1. **Start** a batch on an idle vessel: pick a profile, a name and a batch size. You can start from a
   saved "my version" variant or copy the tweaks from an earlier batch.
2. **Prep ("Making it")** is an optional first stage that every profile gets. Use it while you're
   still brewing or mixing. A batch in Prep does not drive the heater, doesn't count toward its
   zone's target and raises no temperature alerts.
3. **Stages**: advance with the dashboard button (or the `advance_stage` MCP tool). Each stage can set
   a new target, step the target after a delay, and schedule reminders. The vessel page shows a stage
   rail and, for bottle batches, the 24–48 hour carbonation window.
4. **Target**: you can change the zone target from the vessel page within the profile's range.
5. **End** the batch when it's done. Its reminders are cancelled and the heater turns off unless
   another batch in the zone still needs it. Ended batches live in `/history`; only ended batches
   can be deleted.

## Reminders and next actions

Profiles schedule reminders relative to a stage (for ginger ale: open a test bottle around 24 hours,
refrigerate within 48). When a reminder comes due it opens an alert, shows on the dashboard and
pushes to your phone. Some reminders repeat until you mark them done. An ignored reminder escalates
to critical after 2 days, or after 12 hours for "refrigerate now".

"What's next" combines the current stage, the guide's next steps and pending reminders; it's on the
vessel page and in the `get_next_actions` MCP tool.

## Gravity

Log hydrometer readings from the vessel page (with the sample temperature, if you have it, for
temperature correction). fermentd shows original gravity, ABV ((OG − SG) × 131.25) and attenuation.

## Tweaks, variants and tastings

- **Tweaks** record how this batch differs from the written recipe: change an amount, add or remove
  an ingredient, or a free-text note. The batch page shows "recipe says" next to "you used". Tweaks
  can be undone (history is kept).
- **Variants**: save a batch's tweaks as a reusable "my version" of the profile, then start future
  batches from it.
- **Tastings**: a 1–5 rating, optional 1–5 sliders (carbonation, sweetness, dryness, flavour), notes
  and "would make again". Tastings can be added to active or ended batches; `/tastings` ranks your
  best batches.

## Notes, photos and the activity log

Add timestamped notes to any batch, with an optional photo from your phone. Photos are downscaled to
at most 1600 px (plus a 320 px thumbnail) and stored under `data/photos`; the original isn't kept, to
save SD card space.

The **activity log** on each batch lists what was done to it in plain English: start and end, stage
changes, target changes, reminders completed, gravity, notes, tweaks and tastings, from the dashboard
or MCP. Automatic changes such as the heater switching are not in it; they're in the temperature
chart instead.

## Weekly summary

Every Sunday at 09:00 (configurable) fermentd builds a digest: each batch's stage and health,
temperature min/mean/max for the week, readings received vs expected, safety events, open alerts and
upcoming reminders. It's pushed through ntfy if configured and recorded once per ISO week.
