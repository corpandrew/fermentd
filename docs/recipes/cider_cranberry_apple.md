---
schema: fermentd.recipe/v1
id: cider_cranberry_apple
category: cider
profile_id: cider_cranberry_apple
batch_number: 1
status: active
tracking_mode: timer
name: Cranberry-Apple Holiday Cider
yield:
  volume_gal: 1
  bottle_fl_oz: 12
  bottle_count: 9-10
target_f: 62
pitch_below_f: 75
og_target:
- 1.045
- 1.052
fg_target:
- 0.996
- 1.0
abv_expected:
- 5.5
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
  item: apple juice, no preservatives
  amount: 7/8 gallon (112 fl oz)
  amount_half: 7/16 gallon (56 fl oz)
- id: cranberry
  item: 100% cranberry juice, unsweetened (not cocktail)
  amount: 2 cups (16 fl oz)
  amount_half: 1 cup (8 fl oz)
  note: no sorbate or benzoate on the label
- id: nutrient
  item: yeast nutrient
  amount: 1/2 tsp
  amount_half: 1/4 tsp
- id: pectic
  item: pectic enzyme
  amount: 1/2 tsp
  amount_half: 1/4 tsp
  note: keeps the cranberry from making it hazy
- id: yeast
  item: EC-1118 or a cider yeast
  amount: 1/4 tsp (about 1 g)
  amount_half: 1/4 tsp (about 1 g); no need to halve
- id: cinnamon
  item: cinnamon stick
  amount: 1 (3-inch)
  amount_half: 1/2 stick
  note: in secondary
- id: cloves
  item: whole cloves
  amount: '3'
  amount_half: '2'
  note: in secondary
- id: orange
  item: orange peel, no white pith
  amount: from 1/2 orange
  amount_half: from 1/4 orange
  note: in secondary
- id: priming
  item: table sugar for priming
  amount: 25 g (2 tbsp)
  amount_half: 12 g (1 tbsp)
  grams: 25
  note: at bottling only
optional:
- id: brown_sugar
  item: brown sugar
  amount: up to 1/4 cup
  amount_half: up to 2 tbsp
  note: only to raise a low OG; each 1/4 cup per gallon adds about 0.005
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
  text: Ferment 2-4 weeks at 62 F until 1.000 or lower and stable for 3 days.
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
taste: Dry, tart and ruby-pink, with apple up front and a cranberry snap, warmed by a whisper of cinnamon, clove and orange.
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
  summary: 'Plain dry cider without fruit or spice: see the French-style brut cider.'
reminders:
- id: airlock
  at: stage:primary+2d
  text: Check that the airlock is bubbling. A faint sulfur smell in week 1 is normal.
- id: gravity
  at: stage:primary+14d
  text: Take a hydrometer reading. Rack once it is 1.000 or lower and the same on 3 readings over 3 days.
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

Makes [[1 gallon, about 9-10 bottles of 12 oz|a half gallon, about 5 bottles of 12 oz]]. Expect 5.5-6.5% ABV.

- [[7/8 gallon (112 fl oz)|7/16 gallon (56 fl oz)]] apple juice with **no potassium sorbate or sodium benzoate**
- [[2 cups (16 fl oz)|1 cup (8 fl oz)]] **100% unsweetened cranberry juice**, not "cranberry cocktail"
- [[1/2 tsp|1/4 tsp]] yeast nutrient and [[1/2 tsp|1/4 tsp]] pectic enzyme
- 1/4 tsp (about 1 g) EC-1118 or a cider yeast
- Spices for secondary: [[1 cinnamon stick, 3 whole cloves and the peel of 1/2 orange|1/2 cinnamon stick, 2 cloves and the peel of 1/4 orange]], with no white pith
- [[25 g|12 g]] table sugar for priming
- Optional: up to [[1/4 cup|2 tbsp]] brown sugar if the OG is below 1.045

**Why only 2 cups of cranberry per gallon.** Pure cranberry juice has a pH around 2.5 and contains natural benzoic acid. Much more than an eighth of the batch makes it harshly sour and can stall the yeast. This ratio gives color and snap without fighting the ferment.

**Spice lightly.** The spices go in after primary, so the yeast doesn't scrub them out, and only for 3-5 days. Taste daily; clove takes over fast.

## Equipment

- [[1-gallon glass jug|Half-gallon glass jug or growler]] with bung and airlock, plus a second for racking
- A small muslin bag for the spices
- Hydrometer and test jar; auto-siphon, tubing and bottle filler; funnel
- Star San, thermometer, kitchen scale
- [[9-10|5]] heavy 12 oz bottles and caps, plus one plastic tester
- Seedling heat mat in the backpack cooler

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Boil the spices for 1 minute in a splash of water to sanitize them before they go in.

## Juice prep and pitch

1. Sanitize the jug, funnel and hydrometer.
2. Pour in both juices and add the nutrient and pectic enzyme. Shake to aerate.
3. Take an OG reading (aim for 1.045-1.052; add brown sugar if it is low).
4. Pitch the rehydrated yeast, fit the airlock and start the batch in fermentd at **62 F**.

## Primary

Ferment 2-4 weeks at 62 F. Cranberry acidity can make the start slow; give it 3-4 days. It is done at 1.000 or lower and unchanged for 3 days.

## Rack and clear

1. Rack into the clean jug off the sediment.
2. Add the sanitized spices in the muslin bag.
3. Taste daily, and pull the spices after 3-5 days, or as soon as you like it.
4. Let it clear 1-2 more weeks.

## Bottle

Only bottle when the gravity is unchanged for 3 days. Target about 2.5-2.7 volumes of CO2.

1. Sanitize the bottling vessel, siphon, bottle filler, [[9-10|5]] bottles and caps, and the plastic tester.
2. Weigh **[[25 g|12 g]] table sugar**, dissolve it in [[1/4 cup|2 tbsp]] boiling water and cool a little.
3. Pour it into the bottling vessel and siphon the cider onto it, leaving the sediment behind.
4. Fill with 1 inch of headspace, fill the plastic tester the same way, cap, and press **Bottled, start conditioning**.

## Condition in the bottle

Keep the bottles in the closed cooler at about 66 F. From day 7 fermentd reminds you to squeeze the tester. When it is **rock hard**, move every bottle to cool storage and press **Conditioning done, move to cool storage**.


## Serve

Chill at least 24 hours and pour gently. Great with holiday food. The spice fades over a few months, so drink it within the season.

## Safety

- **Prime only fully finished cider**: 1.000 or lower and unchanged on 3 readings over 3 days.
- Weigh the priming sugar; no more than [[25 g|12 g]].
- Bottle a plastic tester and refrigerate once it is rock hard.
- Use only cranberry juice without preservatives; "cocktail" blends often contain sorbate or benzoate.

## Troubleshooting

- **Slow start.** Keep it at 62-64 F and wait 3-4 days before worrying.
- **Too sour.** Use 1 1/2 cups of cranberry per gallon next time.
- **Too much clove.** It fades in 1-2 months in the bottle. Next time use 2 cloves per gallon.
- **Color fading.** It goes from red to rosé pink as the yeast settles. That is normal.

## Taste

Dry, tart and ruby-pink, with apple up front and a cranberry snap, warmed by a whisper of cinnamon, clove and orange.

## Related styles

For plain dry cider, see the French-style brut cider (`cider_french_brut`).
