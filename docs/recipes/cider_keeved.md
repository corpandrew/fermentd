---
schema: fermentd.recipe/v1
id: cider_keeved
category: keeved_cider
profile_id: cider_keeved
batch_number: 1
status: active
tracking_mode: timer
name: Keeved French Cider (Cidre Bouché Style)
yield:
  volume_gal: 1
  bottle_fl_oz: 25.4
  bottle_count: 4-5 × 750 mL Champagne bottles
target_f: 50
pitch_below_f: 55
og_target:
- 1.05
- 1.06
fg_target:
- 1.012
- 1.02
abv_expected:
- 3.0
- 4.5
bottle_gravity:
- 1.02
- 1.025
keeve_days:
- 3
- 14
slow_ferment_weeks:
- 4
- 12
carbonation_window_h:
- 336
- 1008
chill_before_open_h: 24
drink_within_days:
- 30
- 365
ingredients:
- id: juice
  item: fresh-pressed, unpasteurized, untreated apple juice (cider or late-season bittersweet apples)
  amount: 1 gallon
  amount_half: 1/2 gallon (64 fl oz)
  note: store juice, pasteurized or treated, will not keeve
- id: pme
  item: pectin methyl esterase (PME), e.g. Novoshape or a keeving-kit enzyme
  amount: per label (Novoshape about 0.75 mL)
  amount_half: per label (Novoshape about 0.4 mL)
  note: dilute in 10-20 times its volume of juice before adding
- id: calcium
  item: food-grade calcium chloride
  amount: 1-1.5 g
  amount_half: 0.5-0.75 g
  grams: 1.5
  note: maximum 0.4 g per liter; dissolve in a little juice; add 24 hours after the PME
- id: campden
  item: Campden tablet (optional, by pH)
  amount: 0-1, crushed
  amount_half: 0-1/2, crushed
  note: only if juice pH is above 3.8
- id: yeast
  item: no added yeast (wild), or a pinch of a slow cider yeast after racking
  amount: about 1/8 tsp if used
  amount_half: a pinch if used
  note: no yeast nutrient, ever
optional: []
equipment:
- '1-gallon glass jug (half batch: half-gallon jug) with bung and airlock, plus a second for racking'
- a cold spot that stays 40-55 F (unheated garage, cellar or porch in late autumn or winter)
- 1 mL syringe for the enzyme; kitchen scale that reads 0.1 g
- hydrometer and test jar (needed); pH strips or meter
- auto-siphon with a racking cane and tubing
- '4-5 heavy 750 mL Champagne bottles with 29 mm crown caps and a capper with a 29 mm bell (half batch: 2)'
- one plastic tester bottle
- fridge space for every bottle
- safety glasses
safety:
- id: pressure
  text: Bottled sweet cider is still fermenting. Use Champagne bottles, bottle a plastic tester and refrigerate everything as soon as it is firm.
- id: gravity
  text: Bottle no lower than 1.020. Every 0.001 the gravity drops in the bottle adds about 0.6 volumes of CO2.
- id: glasses
  text: Wear safety glasses when moving or opening bottles that sat out of the fridge.
- id: warm
  text: Never store the bottles warm. Above about 60 F the yeast wakes up and pressure climbs fast.
steps:
- id: enzyme
  stage: day0
  profile_stage: keeve
  text: Add the diluted PME to fresh, cold juice in the jug.
- id: calcium
  stage: day1
  profile_stage: keeve
  text: 24 hours later stir in the dissolved calcium chloride, then leave it still.
- id: rack_cap
  stage: keeve
  profile_stage: slow_ferment
  text: When the brown cap is firm, rack the clear middle into a clean jug.
- id: slow
  stage: ferment
  profile_stage: slow_ferment
  text: Ferment slowly at 45-55 F, racking off heavy sediment, until 1.020-1.025 and falling slowly.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Bottle into Champagne bottles with a plastic tester. No priming sugar.
- id: sparkle
  stage: package
  profile_stage: in_bottle
  text: Hold cool until the tester is firm (2-6 weeks), then refrigerate everything.
taste: Naturally sweet, low in alcohol, deep golden and gently sparkling, with soft tannin and baked-apple richness.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 25.4
    bottle_count: 2 × 750 mL Champagne bottles
not_this_batch:
  id: cider_french_brut
  summary: With store juice or no cold spot, make the French-style brut cider.
reminders:
- id: calcium
  at: stage:keeve+1d
  text: Add the dissolved calcium chloride now, 24 hours after the enzyme. Stir gently once, then don't disturb the jug.
- id: cap_check
  at: stage:keeve+3d
  text: Look for the brown cap (chapeau brun) on top and clear juice below. Don't move the jug. Rack when the cap is firm and the middle is clear.
  repeat: 1d
- id: gravity
  at: stage:slow_ferment+14d
  text: Take a gravity reading. Rack off heavy sediment. Bottle at 1.020-1.025 once it is falling slowly (no more than 0.002 a week).
  repeat: 7d
- id: tester
  at: stage:in_bottle+7d
  text: Squeeze the plastic tester. Refrigerate every bottle as soon as it is firm.
  repeat: 2d
- id: fridge
  at: stage:in_bottle+21d
  text: If any bottle is still out of the fridge, refrigerate them all now. Keeved cider keeps fermenting and can over-pressurize.
  repeat: 3d
---

## Ingredients

Makes [[1 gallon, about 4-5 Champagne bottles of 750 mL|a half gallon, about 2 Champagne bottles of 750 mL]]. Expect only 3-4.5% ABV, naturally sweet and lightly sparkling.

- [[1 gallon|1/2 gallon (64 fl oz)]] **fresh-pressed, unpasteurized, untreated apple juice**, ideally from late-season cider or bittersweet apples stored a few weeks before pressing
- **Pectin methyl esterase (PME)**, dosed by its label. For Novoshape (about 20 mL per 100 L) that is [[0.75 mL|0.4 mL]], measured with a syringe and diluted in 10-20 times its volume of juice.
- **[[1-1.5 g|0.5-0.75 g]] food-grade calcium chloride**, never more than 0.4 g per liter, dissolved in a few spoonfuls of juice
- Optional, by pH: up to [[1 Campden tablet|1/2 Campden tablet]], only if the juice pH is above 3.8
- Yeast: none (the juice's wild yeast), or a small pinch of a slow cider strain after racking
- **No yeast nutrient, ever.** Starving the yeast is the whole point.

**How keeving works.** PME strips methyl groups from the apple pectin, and the calcium then links that pectin into a gel. The gel traps solids, proteins and much of the yeast's nitrogen, and early fermentation gas floats it up as a brown cap, the *chapeau brun*. The clear juice underneath is so low in nutrients that the yeast ferments slowly and gives up while it is still sweet. The result is natural sweetness and natural sparkle with no added sugar.

**It needs low-nitrogen juice and cold.** Juice from heavily fertilized orchards, early-season fruit or dessert apples is often too rich in nitrogen to keeve. Pasteurized or store juice has been treated and won't form a cap. The keeve and slow ferment want **40-55 F**. This rig is heat-only and holds a 50 F floor: it can stop a cold garage from getting too cold, but it **cannot cool a warm room**. Do this in late autumn or winter only.

## Equipment

- [[1-gallon glass jug|Half-gallon glass jug]] with bung and airlock, plus a second jug for racking
- A cold spot that stays 40-55 F
- 1 mL syringe; kitchen scale that reads 0.1 g
- Hydrometer and test jar (needed); pH strips or a meter
- Auto-siphon with a racking cane and tubing
- **[[4-5|2]] heavy 750 mL Champagne bottles** with 29 mm crown caps, and a capper with a 29 mm bell. Ordinary 12 oz beer bottles are not suitable for cider that is still fermenting.
- One plastic tester bottle, fridge space for every bottle, and safety glasses

## Sanitation

Sanitize all equipment, but don't sulfite the juice unless the pH calls for it; the wild yeast does the fermenting.

## Keeve: enzyme and calcium

1. Press or collect the juice cold, ideally below 50 F. Check the pH, and add Campden only if it is above 3.8.
2. Fill the jug to the shoulder and stir in the diluted **PME**. Start the batch with the profile at **50 F** (the rig floor) in your coldest spot.
3. Wait **24 hours**, then gently stir in the dissolved **[[1-1.5 g|0.5-0.75 g]] calcium chloride**, once. After that, **don't move or stir the jug**.
4. Over 3-14 days a brown, spongy cap rises and the middle turns clear. Warmer is faster but riskier: if fermentation takes off before the cap forms, it won't keeve.

## Rack off the chapeau brun

When the cap is firm and the middle is clear, slide the racking cane gently through the cap. Siphon the **clear middle** into a clean jug, leaving the cap above and the sediment below. Fit the airlock and press **Racked off the cap, start the slow ferment**.

## Slow ferment

- Keep it at **45-55 F** for 1-3 months. The gravity should fall slowly, a couple of points a week.
- Rack again whenever a heavy sediment forms. Every racking removes yeast and slows it further.
- Optional: if nothing happens within 2 weeks, add a tiny pinch of slow cider yeast.
- Never add nutrient.

## Bottle while sweet

Bottle when the gravity is **1.020-1.025** and falling no faster than about **0.002 per week**.

1. Sanitize the Champagne bottles, caps and filler.
2. Rack carefully off the sediment and fill, leaving about 1.5 inches of headspace. Add **no priming sugar**.
3. Fill the plastic tester too. Cap everything and press **Bottled**.

## Natural sparkle and stopping it

The remaining yeast eats a few more points of sugar in the bottle, and that makes the bubbles. Store the bottles **cool, at 50-55 F**, in a closed box.

- From day 7, squeeze the tester every couple of days. As soon as it is **firm, refrigerate every bottle**, usually after 2-6 weeks. Cold stops the yeast; warmth restarts it.
- Every 0.001 the gravity falls in the bottle adds about 0.6 volumes of CO2. A drop from 1.022 to 1.012 would be about 6 volumes, enough to burst bottles. That is why you bottle no lower than 1.020, use Champagne glass and keep it cold once carbonated.

## Serve

Serve cold, straight from the fridge. Open over the sink with a towel over the cap. Keep it refrigerated and drink it within a year.

## Safety

- **This cider is bottled while still fermenting.** Use only heavy Champagne bottles, never thin beer, screw-top or decorative bottles.
- **Bottle at 1.020 or higher**, never once it is close to dry.
- **Always bottle a plastic tester**, and refrigerate every bottle once it is firm. Never leave carbonated bottles warm.
- Wear safety glasses when handling or opening bottles that sat out of the fridge.
- If a bottle gushes violently or the tester bulges, chill all the bottles to near freezing, then open them one at a time over a sink, pointed away from you.

## Troubleshooting

- **No cap after 2 weeks.** The juice was likely treated, too high in nitrogen or too warm. Ferment it out as a normal dry cider instead: add nutrient and yeast and follow the French-style brut guide.
- **The cap broke up and sank.** Fermentation started too fast. Rack the clearest juice anyway; it is still lower in nutrients than usual.
- **Fermenting fast (more than 0.005 a week).** Rack it off the yeast and move it somewhere colder.
- **Stuck at 1.030.** Fine. Bottle at 1.025 once it moves again, or serve it still and sweet.
- **Flat in the bottle.** Too cold or too clean. Give it a week at 55 F and watch the tester closely.

## Taste

Naturally sweet, low in alcohol, deep golden and gently sparkling, with soft tannin and baked-apple richness, in the style of a Normandy cidre bouché doux.

## Related styles

With store juice or no cold spot, make the French-style brut cider (`cider_french_brut`).
