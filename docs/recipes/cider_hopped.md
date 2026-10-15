---
schema: fermentd.recipe/v1
id: cider_hopped
category: cider
profile_id: cider_hopped
batch_number: 1
status: active
tracking_mode: timer
name: Dry-Hopped Cider
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
- 7
- 90
ingredients:
- id: juice
  item: apple juice, no preservatives
  amount: 1 gallon
  amount_half: 1/2 gallon (64 fl oz)
- id: nutrient
  item: yeast nutrient
  amount: 1/2 tsp
  amount_half: 1/4 tsp
- id: yeast
  item: EC-1118 or a cider yeast
  amount: 1/4 tsp (about 1 g)
  amount_half: 1/4 tsp (about 1 g); no need to halve
- id: citra
  item: Citra hops (pellets), dry hop
  amount: 7 g
  amount_half: 4 g
  note: for 3-4 days after primary
- id: nelson
  item: Nelson Sauvin hops (pellets), dry hop
  amount: 7 g
  amount_half: 4 g
  note: for 3-4 days after primary
- id: priming
  item: table sugar for priming
  amount: 25 g (2 tbsp)
  amount_half: 12 g (1 tbsp)
  grams: 25
  note: at bottling only
optional:
- id: malic
  item: malic acid
  amount: 1/4 tsp, to taste
  amount_half: 1/8 tsp, to taste
  note: only if the juice tastes flat
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
  text: Sanitize the jug, bung, airlock, funnel and hydrometer.
- id: pitch
  stage: day0
  profile_stage: primary
  text: Add nutrient, take an OG reading, pitch the yeast and start the batch at 62 F.
- id: primary
  stage: ferment
  profile_stage: primary
  text: Ferment 2-3 weeks until 1.000 or lower and stable for 3 days.
- id: dry_hop
  stage: ferment
  profile_stage: dry_hop
  text: Rack into the clean jug and add the hops in a sanitized bag for 3-4 days.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Pull the hops, prime with the weighed sugar and bottle with a plastic tester.
- id: condition
  stage: package
  profile_stage: bottle_condition
  text: Condition 2-3 weeks until the tester is rock hard, then refrigerate.
- id: cellar
  stage: serve
  profile_stage: cellared
  text: Keep it cold and drink it fresh.
taste: Bone dry and crisp, with apple underneath a burst of tropical fruit and white grape from Citra and Nelson Sauvin.
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
  id: ale_pale
  summary: If you want hops with malt rather than apple, brew the pale ale.
hop_table: true
reminders:
- id: airlock
  at: stage:primary+2d
  text: Check that the airlock is bubbling. A faint sulfur smell in week 1 is normal.
- id: gravity
  at: stage:primary+14d
  text: Take a hydrometer reading. Rack onto the hops once it is 1.000 or lower and stable for 3 days.
  repeat: 3d
- id: pull_hops
  at: stage:dry_hop+3d
  text: Taste a sample. Pull the hop bag at day 3-4; longer gets grassy.
- id: tester
  at: stage:bottle_condition+7d
  text: Squeeze the plastic tester bottle. Conditioning is done when it is rock hard.
  repeat: 2d
- id: condition_done
  at: stage:bottle_condition+14d
  text: If the tester is rock hard, move all bottles to the fridge. Hop aroma fades warm.
  repeat: 3d
---

## Ingredients

Makes [[1 gallon, about 9-10 bottles of 12 oz|a half gallon, about 5 bottles of 12 oz]]. Expect 5.5-6.5% ABV.

- [[1 gallon|1/2 gallon (64 fl oz)]] apple juice with **no potassium sorbate or sodium benzoate**
- [[1/2 tsp|1/4 tsp]] yeast nutrient
- 1/4 tsp (about 1 g) EC-1118 or a cider yeast
- **[[7 g|4 g]] Citra** and **[[7 g|4 g]] Nelson Sauvin** hop pellets for dry hopping (about 1/2 oz total per gallon)
- [[25 g|12 g]] table sugar for priming
- Optional: [[1/4 tsp|1/8 tsp]] malic acid if the juice tastes flat

**Why dry hop only.** The hops are never boiled, so they add aroma and no bitterness. A dry, neutral cider lets Citra's passion fruit and Nelson's white-grape notes show. Mosaic, Galaxy or Motueka can substitute gram for gram.

## Equipment

- [[1-gallon glass jug|Half-gallon glass jug or growler]] with bung and airlock, plus a second for the dry hop
- A small muslin or nylon hop bag, plus a few glass marbles as a weight
- Hydrometer and test jar; auto-siphon, tubing and bottle filler; funnel
- Star San, thermometer, kitchen scale that reads grams
- [[9-10|5]] heavy 12 oz bottles and caps, plus one plastic tester
- Seedling heat mat in the backpack cooler

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Soak the hop bag and marbles before they go in.

## Juice prep and pitch

1. Sanitize the jug, funnel and hydrometer.
2. Pour in the juice and add the nutrient (and acid if it tastes flat). Take an OG reading (1.045-1.052).
3. Pitch the rehydrated yeast, fit the airlock and start the batch in fermentd at **62 F**.

## Primary

Ferment 2-3 weeks at 62 F, until the gravity is 1.000 or lower and unchanged for 3 days. Let it finish fully before dry hopping, or active fermentation carries the aroma out the airlock.

## Rack and clear

Rack into the clean jug off the yeast and top up to the shoulder.

## Dry hop

1. Put the [[7 g Citra and 7 g Nelson Sauvin|4 g Citra and 4 g Nelson Sauvin]] in the sanitized bag with the marbles, tied with a long string.
2. Lower it into the jug, refit the airlock and press **Hops added**. Hold it at 60-62 F.
3. Taste at day 3. Pull the bag at **day 3-4**; longer turns grassy.

## Bottle

Only bottle when the gravity is unchanged for 3 days. Target about 2.5-2.7 volumes of CO2.

1. Sanitize the bottling vessel, siphon, bottle filler, [[9-10|5]] bottles and caps, and the plastic tester.
2. Weigh **[[25 g|12 g]] table sugar**, dissolve it in [[1/4 cup|2 tbsp]] boiling water and cool a little.
3. Pour it into the bottling vessel and siphon the cider onto it, leaving the sediment behind.
4. Fill with 1 inch of headspace, fill the plastic tester the same way, cap, and press **Bottled, start conditioning**.

## Condition in the bottle

Keep the bottles in the closed cooler at about 66 F. From day 7 fermentd reminds you to squeeze the tester. When it is **rock hard**, move every bottle to the **fridge** (hop aroma fades fast when warm) and press **Conditioning done, move to cool storage**.


## Serve

Serve cold, within 3 months, while the hop aroma is fresh.

## Safety

- **Prime only fully finished cider**: 1.000 or lower and unchanged on 3 readings over 3 days.
- Weigh the priming sugar; no more than [[25 g|12 g]].
- Bottle a plastic tester and refrigerate once it is rock hard.
- Hops are toxic to dogs. Keep spent hops away from pets.

## Troubleshooting

- **Grassy or green taste.** The hops stayed in too long. Pull them at day 3 next time.
- **Weak aroma.** Fermentation wasn't finished, or the bottles sat warm after carbonating. Store them cold.
- **Hop debris in the bottles.** Use a finer bag, or cold-crash the jug in the fridge for 2 days before bottling.

## Taste

Bone dry and crisp, with apple underneath a burst of tropical fruit and white grape from Citra and Nelson Sauvin.

## Related styles

If you want hops with malt rather than apple, brew the pale ale (`ale_pale`).
