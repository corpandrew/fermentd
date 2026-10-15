---
schema: fermentd.recipe/v1
id: ale_spiced_holiday
category: ale
profile_id: ale_spiced_holiday
batch_number: 1
status: active
tracking_mode: timer
name: Spiced Holiday Ale
yield:
  volume_gal: 1
  bottle_fl_oz: 12
  bottle_count: 9-10
target_f: 64
pitch_below_f: 70
og_target:
- 1.062
- 1.068
fg_target:
- 1.014
- 1.018
abv_expected:
- 6.0
- 6.8
ibu: 28
primary_weeks:
- 2
- 3
bottle_condition_weeks:
- 2
- 3
condition_f: 70
priming:
  target_vol:
  - 2.2
  - 2.4
  table_sugar_g: 22
carbonation_window_h:
- 336
- 504
chill_before_open_h: 48
drink_within_days:
- 14
- 180
ingredients:
- id: crystal
  item: crystal 60L malt, crushed
  amount: 85 g (3 oz)
  amount_half: 43 g (1.5 oz)
  note: steeped
- id: chocolate
  item: chocolate malt, crushed
  amount: 14 g (1/2 oz)
  amount_half: 7 g (1/4 oz)
  note: steeped
- id: dme
  item: amber dry malt extract
  amount: 567 g (1 1/4 lb)
  amount_half: 283 g (10 oz)
- id: honey
  item: honey
  amount: 85 g (1/4 cup)
  amount_half: 43 g (2 tbsp)
  note: at flameout
- id: bitter
  item: Northern Brewer hops (about 9% AA), 60 minutes
  amount: 5 g
  amount_half: 3 g
  note: bittering
- id: flavor
  item: East Kent Goldings hops, 15 minutes
  amount: 5 g
  amount_half: 3 g
  note: flavor
- id: cinnamon
  item: cinnamon stick
  amount: 1 (3-inch)
  amount_half: 1/2 stick
  note: at flameout, 10-minute steep
- id: cloves
  item: whole cloves
  amount: '2'
  amount_half: '1'
  note: at flameout
- id: nutmeg
  item: freshly grated nutmeg
  amount: 1/8 tsp
  amount_half: a pinch
  note: at flameout
- id: orange
  item: orange zest, no pith
  amount: from 1 orange
  amount_half: from 1/2 orange
  note: at flameout
- id: yeast
  item: Safale S-04 ale yeast
  amount: 1/2 packet (about 5.5 g)
  amount_half: 1/4 packet (about 3 g)
- id: priming
  item: table sugar for priming
  amount: 22 g
  amount_half: 11 g
  grams: 22
  note: at bottling
optional:
- id: irish_moss
  item: Irish moss
  amount: 1/4 tsp
  amount_half: 1/8 tsp
  note: at 15 minutes, for clarity
equipment:
- 8-quart (2-gallon) stock pot
- '1-gallon glass jug with bung and airlock (half batch: a half-gallon jug or growler)'
- blow-off tube and a small jar
- hydrometer and test jar (needed)
- kitchen scale that reads grams
- thermometer
- grain bag for steeping
- auto-siphon and tubing with a bottle filler
- funnel and strainer
- Star San and a spray bottle
- a sink or tub for an ice bath
- '9-10 heavy 12 oz bottles with caps and a capper (half batch: 5), plus one plastic tester bottle'
- seedling heat mat in the backpack cooler
safety:
- id: stable
  text: Prime only fully finished beer, with the same gravity on 3 readings over 3 days.
- id: glass
  text: Use bottles rated for carbonation and weigh the priming sugar.
- id: tester
  text: Bottle one plastic tester and move all bottles cold once it is rock hard.
- id: hot
  text: Boiling wort boils over fast. Stay at the stove when the extract goes in.
steps:
- id: sanitize
  stage: day0
  profile_stage: primary
  text: Sanitize everything that touches the wort after the boil.
- id: steep
  stage: day0
  profile_stage: primary
  text: Steep the crushed grains in a bag at 150-160 F for 30 minutes.
- id: boil
  stage: day0
  profile_stage: primary
  text: Stir in the extract off the heat, then boil 60 minutes with the hop additions.
- id: spice
  stage: day0
  profile_stage: primary
  text: At flameout add honey and spices, steep 10 minutes, then strain.
- id: chill
  stage: day0
  profile_stage: primary
  text: Chill below 70 F, pour into the jug and top up with cold water to the batch size.
- id: pitch
  stage: day0
  profile_stage: primary
  text: Read the OG, pitch the yeast, fit a blow-off tube and start the batch at 64 F.
- id: primary
  stage: ferment
  profile_stage: primary
  text: Ferment 2-3 weeks; fermentd steps up to 68 F after day 4 to finish clean.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Prime with the weighed sugar and bottle with a plastic tester.
- id: condition
  stage: package
  profile_stage: bottle_condition
  text: Condition at about 70 F for 2 weeks until the tester is rock hard.
taste: 'Deep amber-brown and warming: toffee and bread crust, a little roast, honey, and gentle cinnamon-orange spice over moderate bitterness.'
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 12
    bottle_count: '5'
  priming:
    target_vol:
    - 2.2
    - 2.4
    table_sugar_g: 11
not_this_batch:
  id: ale_bitter
  summary: For an unspiced malty ale, brew the English bitter.
reminders:
- id: airlock
  at: stage:primary+1d
  text: Check for foam (krausen). If it reaches the airlock, use a blow-off tube.
- id: gravity
  at: stage:primary+10d
  text: Take a hydrometer reading. Bottle only at 1.014-1.018 and stable on 3 readings over 3 days.
  repeat: 2d
- id: tester
  at: stage:bottle_condition+7d
  text: Squeeze the plastic tester. Conditioning is done when it is rock hard.
  repeat: 2d
- id: condition_done
  at: stage:bottle_condition+14d
  text: If the tester is rock hard, move the bottles to cool storage. The spice softens over 2-4 weeks.
  repeat: 3d
---

## Ingredients

Makes [[1 gallon, about 9-10 bottles of 12 oz|a half gallon, about 5 bottles of 12 oz]]. OG 1.062-1.068, about 6-6.8% ABV, about 28 IBU.

- [[85 g (3 oz)|43 g (1.5 oz)]] crystal 60L and [[14 g (1/2 oz)|7 g (1/4 oz)]] chocolate malt, crushed, for steeping
- [[567 g (1 1/4 lb)|283 g (10 oz)]] amber dry malt extract
- [[85 g (1/4 cup)|43 g (2 tbsp)]] honey
- [[5 g|3 g]] Northern Brewer hops (about 9% AA) at 60 minutes, and [[5 g|3 g]] East Kent Goldings at 15 minutes
- Spices at flameout: [[1 cinnamon stick, 2 whole cloves, 1/8 tsp grated nutmeg and the zest of 1 orange|1/2 cinnamon stick, 1 clove, a pinch of nutmeg and the zest of 1/2 orange]]
- [[1/2 packet (about 5.5 g)|1/4 packet (about 3 g)]] Safale S-04
- [[22 g|11 g]] table sugar for priming
- Optional: [[1/4 tsp|1/8 tsp]] Irish moss at 15 minutes

**Less spice than you think.** Spice that tastes right in hot wort is too much after a month in the bottle, so these amounts sit in the background. For more, steep extra spice in 2 tbsp vodka for a few days and add the tincture to taste at bottling.

## Equipment

- 8-quart (2-gallon) stock pot and a grain bag
- [[1-gallon glass jug|Half-gallon jug or growler]] with bung and airlock, plus a blow-off tube and small jar
- Hydrometer and test jar; thermometer; kitchen scale
- Auto-siphon, tubing and bottle filler; funnel and strainer
- Star San; a sink or tub for an ice bath
- [[9-10|5]] heavy 12 oz bottles with caps and a capper, plus one plastic tester
- Seedling heat mat in the backpack cooler

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Everything that touches the wort **after the boil** must be sanitized.

## Brew day

1. Heat [[1.5 gallons|3 quarts]] of water to 150-160 F and steep the grain bag for 30 minutes. Lift it out and let it drain; don't squeeze it.
2. Bring to a boil, take it off the heat and stir in the extract until there are no clumps. Return it to the boil.
3. Add the Northern Brewer and boil for 60 minutes. Add the Goldings (and Irish moss) with 15 minutes left.
4. At flameout, stir in the honey, cinnamon, cloves, nutmeg and orange zest. Steep for 10 minutes, then strain out the spices.
5. Chill in an ice bath to **below 70 F**. Pour it into the jug and top up with cold water to [[1 gallon|a half gallon]].
6. Read the OG (1.062-1.068). Pitch the yeast, fit a blow-off tube and start the batch in fermentd at **64 F**.

## Ferment

fermentd holds **64 F** for the first 4 days, while most of the flavor is made, then automatically steps up to **68 F** to finish clean. Expect 2-3 weeks. Bottle only when the gravity is **1.014-1.018 and unchanged for 3 days**.

## Bottle

1. Sanitize the bottling vessel, siphon, filler, [[9-10|5]] bottles, caps and the plastic tester.
2. Dissolve **[[22 g|11 g]] table sugar** in [[1/4 cup|2 tbsp]] boiling water and pour it into the bottling vessel.
3. Siphon the beer onto it, leaving the yeast behind. Fill the bottles with 1 inch of headspace, fill the tester and cap everything.
4. Press **Bottled, start conditioning**.

## Condition in the bottle

Condition at about **70 F** for 2 weeks, until the tester is rock hard, then move the bottles to cool storage. The spice blends over another 2-4 weeks; it is at its best around the holidays.

## Safety

- **Prime only fully finished beer**: 1.014-1.018 and unchanged on 3 readings over 3 days.
- Weigh the priming sugar; no more than [[22 g|11 g]].
- Bottle a plastic tester and move the bottles cool once it is rock hard.
- Boiling wort boils over fast. Stay at the stove when the extract goes in.

## Troubleshooting

- **Too much spice.** Give it 1-2 more months; spice fades. Next time halve the cloves or skip them.
- **Stuck at 1.022.** Rouse the yeast and check that the rig stepped up to 68 F. The honey and crystal malt leave it a little sweet, which is normal.
- **Harsh or astringent.** The grain bag was squeezed, or the zest had pith.
- **Flat after 3 weeks.** Give it one more week at 70 F.

## Taste

Deep amber-brown and warming: toffee and bread crust, a little roast, honey, and gentle cinnamon-orange spice over moderate bitterness.

## Related styles

For an unspiced malty ale, brew the English bitter (`ale_bitter`).
