---
schema: fermentd.recipe/v1
id: cider_perry
category: cider
profile_id: cider_perry
batch_number: 1
status: active
tracking_mode: timer
name: Pear Perry
yield:
  volume_gal: 1
  bottle_fl_oz: 12
  bottle_count: 9-10
target_f: 60
pitch_below_f: 75
og_target:
- 1.045
- 1.055
fg_target:
- 1.002
- 1.006
abv_expected:
- 5.0
- 6.5
primary_weeks:
- 2
- 4
secondary_weeks:
- 2
- 3
bottle_condition_weeks:
- 2
- 3
condition_f: 66
priming:
  target_vol:
  - 2.5
  - 2.7
  table_sugar_g: 25
carbonation_window_h:
- 336
- 504
chill_before_open_h: 24
drink_within_days:
- 14
- 365
ingredients:
- id: juice
  item: pear juice, 100% juice, no preservatives
  amount: 1 gallon
  amount_half: 1/2 gallon (64 fl oz)
  note: fresh-pressed perry or ripe dessert pears is best; store juice must list no sorbate or benzoate; avoid nectars
- id: acid
  item: malic acid (or tartaric)
  amount: 1/2-1 tsp, to taste
  amount_half: 1/4-1/2 tsp, to taste
  note: pears are low in acid; aim for roughly pH 3.4-3.8
- id: tannin
  item: wine tannin powder
  amount: 1/4 tsp
  amount_half: 1/8 tsp
  note: skip if using real perry pears, which are tannic
- id: nutrient
  item: yeast nutrient
  amount: 1/2 tsp
  amount_half: 1/4 tsp
- id: yeast
  item: cider yeast or Lalvin 71B
  amount: 1/4 tsp (about 1 g)
  amount_half: 1/4 tsp (about 1 g); yeast does not need halving
  note: rehydrate 15 minutes in 1/4 cup lukewarm water
- id: priming
  item: table sugar for priming
  amount: 25 g (2 tbsp)
  amount_half: 12 g (1 tbsp)
  grams: 25
  note: at bottling only
optional:
- id: campden
  item: Campden tablet
  amount: 1, crushed
  amount_half: 1/2, crushed
  note: fresh-pressed juice only; wait 24 hours before pitching
equipment:
- '1-gallon glass jug with bung and airlock (half batch: a half-gallon jug or growler)'
- a second clean jug of the same size for secondary
- hydrometer and test jar (needed)
- auto-siphon and tubing with a bottle filler
- funnel
- Star San and a spray bottle
- thermometer
- kitchen scale that reads grams
- '9-10 heavy 12 oz bottles (crown-capped or swing-top; half batch: 5) plus one plastic tester bottle'
- seedling heat mat in the backpack cooler
safety:
- id: stable
  text: Prime only fully finished cider, with the same gravity on 3 readings over 3 days.
- id: glass
  text: Use heavy bottles rated for carbonation and weigh the priming sugar.
- id: tester
  text: Bottle one plastic tester and move all bottles cold once it is rock hard.
- id: sorbate
  text: Juice with potassium sorbate or sodium benzoate will not ferment. Read the label.
steps:
- id: sanitize
  stage: day0
  profile_stage: primary
  text: Sanitize the jug, bung, airlock, funnel, hydrometer and test jar.
- id: og
  stage: day0
  profile_stage: primary
  text: Mix the juice, take an OG reading and add the nutrient.
- id: pitch
  stage: day0
  profile_stage: primary
  text: Pitch the rehydrated yeast, fit the airlock and start the batch in fermentd.
- id: primary
  stage: ferment
  profile_stage: primary
  text: Ferment 2-4 weeks at 60 F until the gravity is stable for 3 days. It may stop above 1.000; that is the sorbitol.
- id: rack
  stage: ferment
  profile_stage: secondary
  text: Rack into the clean jug and let it clear 2-3 weeks.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Dissolve the weighed priming sugar, rack onto it and bottle with a plastic tester.
- id: condition
  stage: package
  profile_stage: bottle_condition
  text: Condition 2-3 weeks until the tester is rock hard, then store cold.
- id: cellar
  stage: serve
  profile_stage: cellared
  text: Chill at least 24 hours before opening.
taste: Soft, floral and pear-forward with a gentle residual sweetness from sorbitol, about 5-6.5% ABV.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 12
    bottle_count: '5'
  priming:
    target_vol:
    - 2.5
    - 2.7
    table_sugar_g: 12
not_this_batch:
  id: cider_french_brut
  summary: For a bone-dry cider, make the French-style brut cider instead.
reminders:
- id: airlock
  at: stage:primary+2d
  text: Check that the airlock is bubbling. A faint sulfur smell in week 1 is normal.
- id: gravity
  at: stage:primary+14d
  text: Take a hydrometer reading. Rack once it is stable (often 1.002-1.006, not 1.000, because of sorbitol) and the same on 3 readings over 3 days.
  repeat: 3d
- id: clear_check
  at: stage:secondary+14d
  text: Check clarity and gravity. Bottle only when the gravity is unchanged for 3 days.
  repeat: 7d
- id: tester
  at: stage:bottle_condition+7d
  text: Squeeze the plastic tester bottle. Conditioning is done when it is rock hard.
  repeat: 2d
- id: condition_done
  at: stage:bottle_condition+14d
  text: If the tester is rock hard, move all bottles to cool storage or the fridge.
  repeat: 3d
---

## Ingredients

Makes [[1 gallon, about 9-10 bottles of 12 oz|a half gallon, about 5 bottles of 12 oz]]. Expect 5-6.5% ABV.

- [[1 gallon|1/2 gallon (64 fl oz)]] **100% pear juice**: fresh-pressed perry pears if you can find them, otherwise ripe dessert pears pressed at home, or store juice with **no potassium sorbate or sodium benzoate**. Skip "nectars"; the purée and thickeners make it sludgy.
- [[1/2-1 tsp|1/4-1/2 tsp]] malic acid (or tartaric), added to taste
- [[1/4 tsp|1/8 tsp]] wine tannin (skip with real perry pears)
- [[1/2 tsp|1/4 tsp]] yeast nutrient
- 1/4 tsp (about 1 g) cider yeast or Lalvin 71B (no need to halve)
- [[25 g|12 g]] table sugar for priming at bottling

**Where to get pear juice.** Orchards that press perry pears (Barland, Blakeney Red, Thorn and others) sell the best juice in autumn. Otherwise, use a 100% pear juice from the health-food aisle and check it for preservatives.

**Sorbitol.** Pears contain sorbitol, a sugar alcohol that yeast cannot ferment. Depending on the variety, it can be a percent or more of the juice. That is why perry often finishes at **1.002-1.006** instead of below 1.000 and tastes softly sweet even when fully fermented. It also means the hydrometer can't tell you "done" by number alone; only a reading **stable for 3 days** can. (In quantity, sorbitol is mildly laxative.)

**Acid.** Pear juice is much lower in acid than apple, so it tastes flat and spoils more easily. Add malic acid a little at a time until it tastes like a crisp white wine.

## Equipment

- [[1-gallon glass jug|Half-gallon glass jug or growler]] with bung and airlock, plus a second for racking
- Hydrometer and test jar (needed)
- Auto-siphon, tubing and bottle filler; funnel
- Star San, thermometer, kitchen scale
- [[9-10|5]] heavy 12 oz bottles, caps and a capper (or swing-tops), plus one plastic tester bottle
- Seedling heat mat in the backpack cooler

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Sanitize everything that touches the juice once you open it.

## Juice prep and pitch

1. Sanitize the jug, funnel, hydrometer and test jar.
2. For fresh-pressed juice, crush in [[1 Campden tablet|1/2 Campden tablet]] and wait 24 hours.
3. Pour in the juice and add the nutrient and tannin, then the acid to taste.
4. Take an OG reading (aim for 1.045-1.055).
5. Pitch the rehydrated yeast, fit the airlock and start the batch in fermentd at **60 F**.

## Primary

Perry likes it cool and slow; 58-62 F keeps the delicate pear aroma. Expect 2-4 weeks. Start readings at day 14. It is done when the gravity is **unchanged for 3 days**, even if that is 1.004.

## Rack and clear

Rack off the sediment into the clean jug, top up to the shoulder and let it clear 2-3 weeks. Perry is often slower to clear than cider; patience beats finings.

## Bottle

Only bottle when the gravity is unchanged for 3 days. Target about 2.5-2.7 volumes of CO2.

1. Sanitize the bottling vessel, siphon, bottle filler, [[9-10|5]] bottles and caps, and the plastic tester.
2. Weigh **[[25 g|12 g]] table sugar**, dissolve it in [[1/4 cup|2 tbsp]] boiling water and cool a little.
3. Pour it into the bottling vessel and siphon the cider onto it, leaving the sediment behind.
4. Fill with 1 inch of headspace, fill the plastic tester the same way, cap, and press **Bottled, start conditioning**.

## Condition in the bottle

Keep the bottles in the closed cooler at about 66 F. From day 7 fermentd reminds you to squeeze the tester. When it is **rock hard**, move every bottle to cool storage and press **Conditioning done, move to cool storage**.


## Serve

Chill at least 24 hours and pour gently, leaving the yeast behind. Perry is at its best from 1 to 6 months.

## Safety

- **Prime only perry with a stable gravity**: unchanged on 3 readings over 3 days. Don't wait for 1.000; sorbitol can hold it at 1.002-1.006.
- Weigh the priming sugar: no more than [[25 g|12 g]].
- Bottle a plastic tester and move the bottles cold once it is rock hard.
- Pitch below 75 F, and check the juice label for preservatives.

## Troubleshooting

- **Stuck at 1.004.** Probably sorbitol, not a stuck ferment. If 3 readings match, it is done.
- **Sulfur smell.** Pears are low in nitrogen too. Add another [[1/4 tsp|1/8 tsp]] nutrient in week 1 and swirl.
- **Flat, dull taste.** Not enough acid. Add malic acid a pinch at a time before bottling.
- **Hazy.** That's pear pectin. Next time add pectic enzyme at the label rate on day 0.

## Taste

Soft, floral and pear-forward, with a gentle residual sweetness from the sorbitol. About 5-6.5% ABV.

## Related styles

For a bone-dry apple version, see the French-style brut cider (`cider_french_brut`).
