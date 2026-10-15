---
schema: fermentd.recipe/v1
id: wine_sparkling_chardonnay
category: sparkling_wine
profile_id: wine_sparkling_chardonnay
batch_number: 1
status: active
tracking_mode: timer
name: Sparkling Chardonnay (Méthode Classique)
yield:
  volume_gal: 1
  bottle_fl_oz: 25.4
  bottle_count: 4-5 × 750 mL Champagne bottles
target_f: 60
pitch_below_f: 70
og_target:
- 1.07
- 1.078
fg_target:
- 0.99
- 0.996
abv_expected:
- 11.0
- 12.0
tirage_sugar_g_l: 24
pressure_atm: 6
en_tirage_months:
- 9
- 15
dosage_g_l:
- 6
- 10
primary_weeks:
- 2
- 4
cold_stabilize_weeks:
- 2
- 3
riddling_weeks:
- 2
- 4
condition_f: 58
chill_before_open_h: 24
drink_within_days:
- 30
- 1095
ingredients:
- id: juice
  item: Chardonnay juice, fresh or frozen (no preservatives)
  amount: 1 gallon
  amount_half: 1/2 gallon (64 fl oz)
  note: 'or 68 Brix concentrate: about 28-30 fl oz topped up with water to 1 gallon (half: 14-15 fl oz to a half gallon); check with a hydrometer'
- id: tartaric
  item: tartaric acid
  amount: to taste, about 1-4 g
  amount_half: about 0.5-2 g
  note: aim for TA 7.5-9 g/L and pH 3.0-3.3; 3.8 g per gallon raises TA about 1 g/L
- id: nutrient
  item: yeast nutrient (Fermaid-O or K)
  amount: 1/4 tsp, plus 1/8 tsp at tirage
  amount_half: 1/8 tsp, plus a pinch at tirage
- id: yeast
  item: Lalvin DV10 or EC-1118 for primary
  amount: 1/4 tsp (about 1 g)
  amount_half: 1/4 tsp (about 1 g); no need to halve
  note: rehydrate 15 minutes in 1/4 cup water at about 100 F
- id: campden
  item: Campden tablet
  amount: 1/2, crushed
  amount_half: 1/4, crushed
  note: after primary only; keep sulfite low before the tirage
- id: bentonite
  item: bentonite (hydrated slurry)
  amount: 1/2 tsp
  amount_half: 1/4 tsp
  note: protein stability
- id: tirage_sugar
  item: table sugar for the tirage (24 g per liter)
  amount: 91 g
  amount_half: 45 g
  grams: 91
  note: about 6 atmospheres in the bottle; weigh it
- id: tirage_yeast
  item: fresh EC-1118 or DV10 for the tirage, as an acclimated starter
  amount: 1 g plus starter
  amount_half: 1 g plus starter
  note: use fresh yeast, not the lees
- id: riddling_aid
  item: riddling aid (Adjuvant 84 or similar)
  amount: per label
  amount_half: per label
  note: helps the lees slide into the neck
- id: dosage_sugar
  item: sugar for the dosage liqueur
  amount: 50 g
  amount_half: 25 g
  note: 'dissolved in base wine to make 100 mL (half: 50 mL)'
optional: []
equipment:
- '1-gallon glass jug (half batch: half-gallon jug) with bung and airlock, plus a second for racking'
- hydrometer and test jar (needed); acid titration kit and pH strips or meter
- fridge space for the jug for 2-3 weeks
- '4-5 heavy 750 mL Champagne bottles with a 29 mm crown finish (half batch: 2)'
- 29 mm crown caps and 29 mm plastic bidules, plus spares
- a bench capper with a 29 mm bell (most beer cappers are 26 mm)
- a riddling rack, or a sturdy cardboard box with neck holes cut at 45 degrees
- an ice-and-salt brine bath (or dry ice) deep enough for 1.5 inches of neck
- safety glasses and heavy gloves, a towel and a bucket for disgorging
- syringes for the dosage
- one plastic tester bottle
- seedling heat mat in the backpack cooler
safety:
- id: bottles
  text: Only heavy Champagne bottles. 12 oz beer bottles, screw-top or thin wine bottles can burst at about 6 atmospheres.
- id: sugar
  text: 'Weigh the tirage sugar: 24 g per liter, never more.'
- id: eyes
  text: Wear safety glasses and gloves whenever you move, riddle or open tirage bottles, and keep them in a closed box.
- id: cold
  text: Chill bottles to 40 F before disgorging and point them away from people.
- id: dry
  text: Make the tirage only from fully dry base wine, 0.996 or lower and stable on 3 readings.
steps:
- id: prep
  stage: day0
  profile_stage: primary
  text: Adjust the juice to OG 1.070-1.078, TA 7.5-9 g/L, pH 3.0-3.3.
- id: pitch
  stage: day0
  profile_stage: primary
  text: Pitch rehydrated DV10 or EC-1118 with nutrient and start the batch at 60 F.
- id: primary
  stage: ferment
  profile_stage: primary
  text: Ferment 2-4 weeks until 0.996 or lower and stable for 3 days.
- id: rack
  stage: ferment
  profile_stage: secondary
  text: Rack, add the Campden and bentonite, and let it settle.
- id: cold
  stage: ferment
  profile_stage: cold_stabilize
  text: Hold the jug in the fridge 2-3 weeks, then rack off any crystals.
- id: tirage
  stage: package
  profile_stage: tirage
  text: Add tirage sugar, starter, nutrient and riddling aid; bottle with bidules and crown caps.
- id: second
  stage: package
  profile_stage: in_bottle
  text: Hold at 55-60 F for 4-8 weeks for the second ferment.
- id: age
  stage: age
  profile_stage: en_tirage
  text: Age on the lees 9-15 months (3 minimum).
- id: riddle
  stage: age
  profile_stage: riddling
  text: Riddle 2-4 weeks until the lees sit in the neck.
- id: disgorge
  stage: finish
  profile_stage: disgorge
  text: Freeze the neck, disgorge, add the dosage and re-cap.
- id: cellar
  stage: serve
  profile_stage: cellared
  text: Rest 4-8 weeks, then chill and serve.
taste: 'Crisp, bright and brut: green apple, lemon and white flowers with fine bubbles and toasty, brioche notes from the lees.'
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 25.4
    bottle_count: 2 × 750 mL Champagne bottles
not_this_batch:
  id: wine_concord
  summary: For a still wine with no pressure risk, make the Concord or blackberry wine.
reminders:
- id: airlock
  at: stage:primary+2d
  text: Check for airlock activity and a fresh, fruity smell.
- id: gravity
  at: stage:primary+14d
  text: Take a gravity reading. Rack once it is 0.996 or lower and the same on 3 readings over 3 days.
  repeat: 3d
- id: dry
  at: stage:secondary+14d
  text: Check gravity and clarity. Move the jug to the fridge to cold stabilize once it is dry and fairly clear.
  repeat: 7d
- id: cold_done
  at: stage:cold_stabilize+21d
  text: Cold stabilizing is done after 2-3 weeks. Rack off any crystals, let it warm to 60-65 F, then make the tirage.
- id: tirage_check
  at: stage:in_bottle+28d
  text: Check the plastic tester. When it is rock hard and the deposit has settled, move the bottles to cellar aging.
  repeat: 7d
- id: tirage_taste
  at: stage:en_tirage+90d
  text: Minimum time en tirage reached. For finer bubbles and toasty flavor keep going to 9-15 months.
  repeat: 60d
- id: riddle
  at: stage:riddling+1d
  text: 'Riddle: give every bottle a sharp 1/8 turn and tilt it slightly more neck-down. Wear safety glasses.'
  repeat: 1d
- id: riddle_done
  at: stage:riddling+21d
  text: Check that the deposit is a tight plug in the neck. When it is, chill the bottles to 40 F for disgorging.
  repeat: 3d
---

## Ingredients

Makes [[1 gallon of base wine, about 4-5 Champagne bottles of 750 mL|a half gallon of base wine, about 2 Champagne bottles of 750 mL]]. Expect 11-12% ABV, brut.

**Base wine**
- [[1 gallon|1/2 gallon (64 fl oz)]] **Chardonnay juice**, fresh or frozen, with no preservatives. Or use 68 Brix Chardonnay concentrate: about [[28-30 fl oz topped up with water to 1 gallon|14-15 fl oz topped up with water to a half gallon]]. Confirm with a hydrometer.
- Tartaric acid to reach **TA 7.5-9 g/L and pH 3.0-3.3**. Sparkling wine wants more acid than still wine. [[3.8 g|1.9 g]] raises the TA by about 1 g/L.
- [[1/4 tsp|1/8 tsp]] yeast nutrient and 1/4 tsp (about 1 g) **Lalvin DV10 or EC-1118** (no need to halve)
- [[1/2 Campden tablet|1/4 Campden tablet]] after primary, and [[1/2 tsp|1/4 tsp]] hydrated bentonite

**Tirage (the second ferment, in the bottle)**
- **[[91 g|45 g]] table sugar**: **24 g per liter**, for about **6 atmospheres** of pressure. Weigh it.
- Fresh EC-1118 or DV10, built up into an acclimated starter (see Tirage)
- [[1/8 tsp|a pinch of]] yeast nutrient, and a riddling aid (Adjuvant 84 or similar) at its label rate

**Dosage**
- [[50 g|25 g]] sugar dissolved in base wine to make [[100 mL|50 mL]] of liqueur; each 10 mL carries 5 g of sugar

**Base wine target.** OG **1.070-1.078**, about 10-10.5% ABV before the tirage adds roughly 1.4%. If the juice is higher, dilute it with water; a heavy, high-alcohol base wine stalls the second ferment.

## Equipment

- [[1-gallon glass jug|Half-gallon glass jug]] with bung and airlock, plus a second for racking
- Hydrometer and test jar; acid titration kit and pH strips or a meter
- Fridge space for the jug for 2-3 weeks
- **[[4-5|2]] heavy 750 mL Champagne bottles** with a **29 mm crown finish**, new or free of chips and scratches
- **29 mm crown caps** and **29 mm plastic bidules** (small cups that catch the lees), plus spares
- **A capper with a 29 mm bell.** Most beer cappers are 26 mm and won't seal these bottles.
- A riddling rack, or a sturdy cardboard box with holes cut to hold bottles neck-down at 45 degrees
- An ice-and-salt brine bath (or dry ice in alcohol), a bucket, a towel, **safety glasses and heavy gloves**
- Syringes for the dosage, and one plastic tester bottle

**Not safe: standard 12 oz beer bottles.** They are made for about 3 atmospheres, and this wine reaches about 6. The same goes for screw-top wine bottles, thin clear glass and swing-tops not rated for sparkling wine.

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Sanitize the bottles, bidules and caps right before the tirage. Hold every bottle up to a light and reject any with a chip or scratch.

## Juice prep and pitch

1. Thaw the juice (or mix the concentrate) and stir. Read the gravity and adjust it to 1.070-1.078.
2. Measure the TA and pH. Add tartaric acid in small doses, stirring and re-testing, until you reach TA 7.5-9 g/L and pH 3.0-3.3.
3. Fill the jug to the shoulder, add the nutrient and pitch the rehydrated yeast.
4. Fit the airlock and start the batch in fermentd at **60 F**.

## Primary (still base wine)

A cool, clean ferment keeps the delicate fruit and avoids off-flavors that the bubbles would amplify. Ferment at 58-62 F for 2-4 weeks. It is done at **0.996 or lower, unchanged on 3 readings over 3 days**. Never make the tirage from unfinished wine; leftover sugar becomes extra pressure.

## Rack and finish dry

Rack off the lees into a clean jug and stir in [[1/2 Campden tablet|1/4 Campden tablet]] (about 30 ppm). Keep the sulfite low, because too much stops the second ferment. Stir in the hydrated bentonite and let it settle for 1-2 weeks at 60-62 F.

## Cold stabilize

Tartrate crystals that form later give bubbles a place to form and make bottles gush at disgorging, so drop them now.

1. Rack off the bentonite and put the jug in the **fridge (28-38 F) for 2-3 weeks**. This happens off the rig; press **Moved to the fridge to cold stabilize**.
2. Rack the cold wine off any crystals on the glass and let it warm back to 60-65 F.

## Tirage

1. **Make the starter 2 days ahead.** Rehydrate the tirage yeast in 1/4 cup of 100 F water for 15 minutes, then add 1/4 cup of base wine and 1 tsp of sugar. Every 8-12 hours, double the volume with base wine and a little sugar until it is foaming vigorously. This acclimates the yeast to alcohol.
2. **Sugar.** Dissolve **[[91 g|45 g]] table sugar** (24 g/L) in about [[1 cup|1/2 cup]] of warm base wine.
3. Stir the syrup, about [[1/2 cup|1/4 cup]] of the active starter, the nutrient and the riddling aid into the wine.
4. Fill the Champagne bottles to about 1.5 inches below the rim. Press a **bidule** into each neck and crimp on a **29 mm crown cap**. Fill the plastic tester with the same wine.
5. Lay the bottles on their sides **in a closed box** and press **Tirage bottled**.

## En tirage aging

1. Hold the bottles at **55-60 F** for **4-8 weeks** while the second ferment runs; the cooler at 58 F works. The tester goes rock hard.
2. Then age them on their sides, somewhere dark at **50-60 F**, for **at least 3 months, ideally 9-15**. As the yeast slowly breaks down (autolysis), the bubbles get finer and toasty, brioche flavors develop.
3. Keep them in the closed box, and wear safety glasses whenever you move them.

## Riddling

Riddling moves the yeast deposit down into the bidule.

1. Wearing safety glasses, give each bottle one sharp shake so the lees swirl, then set it **neck-down at 45 degrees** in the rack or box.
2. Once a day, give each bottle a quick **1/8 turn** and tilt it slightly more toward vertical.
3. After **2-4 weeks** the bottles are nearly vertical and the deposit is a tight plug in the neck. Keep them neck-down until you disgorge.

## Disgorge

1. Chill the bottles **neck-down to about 40 F** overnight. Cold wine holds its CO2 and gushes far less.
2. Make a brine of ice, water and plenty of salt (well below 32 F), or use dry ice in alcohol. Put on safety glasses and gloves.
3. Dip about **1.5 inches** of neck into the bath for 10-20 minutes, until an ice plug traps the bidule and lees.
4. Hold the bottle at 45 degrees, **pointed away from everyone** and into a bucket or bag, and pop the crown with an opener. The pressure shoots out the ice plug, bidule and yeast.
5. Cover the mouth with your thumb straight away and go directly to the dosage.

## Dosage and closure

1. Add the dosage liqueur with a syringe. **12 mL per 750 mL bottle gives about 8 g/L (brut).** Stay at or under **17 mL (about 11 g/L)** to remain brut (under 12 g/L), or add none for brut nature.
2. Top up with wine from a sacrificial bottle if needed, and re-cap immediately with a new 29 mm crown (or a Champagne cork and wire cage, if you have a Champagne corker).
3. Press **Disgorged**, then rest the bottles 4-8 weeks so the dosage integrates.

## Serve

Chill to 40-45 F for at least 24 hours. Hold the bottle at 45 degrees pointing away from people, and ease the cap off slowly under a towel. Serve in tulip glasses.

## Safety

- **Pressure.** Every tirage bottle holds about **6 atmospheres (about 90 psi)**, roughly three times a car tire. A failing bottle throws glass hard and far.
- **Use only heavy Champagne bottles** with a 29 mm crown finish. **Standard 12 oz beer bottles are not safe**, and neither are screw-top wine bottles or thin decorative glass.
- **Weigh the tirage sugar** at 24 g per liter: [[91 g|45 g]] for this batch. Never add more, and never make the tirage from wine that isn't fully dry and stable.
- Wear **safety glasses and gloves** when moving, riddling, disgorging or opening. Keep the bottles in a closed box away from where people walk. Apart from the single riddling swirl, never shake them after the tirage.
- **Disgorge cold** (40 F), pointed away from people and pets.
- Never put whole bottles in the freezer, and never warm them to "speed things up."

## Troubleshooting

- **No pressure after 8 weeks (soft tester).** The tirage yeast wasn't active, or the sulfite was too high. Move the bottles to 62-64 F for 2-3 weeks. If they are still flat, build a stronger starter next time and keep the SO2 low.
- **Gushing at disgorging.** The wine wasn't cold enough, or there were tartrate crystals. Chill to 35-40 F, and always cold stabilize.
- **Lees stuck to the glass.** You skipped the riddling aid, or the turns were too gentle. Give a sharp twist each day, or a firm tap on the base.
- **Cloudy after disgorging.** Lees were left behind. Let the bottle settle neck-down and disgorge again carefully.
- **Too sharp.** Use a slightly larger dosage, staying under 17 mL per bottle for brut.

## Taste

Crisp, bright and brut: green apple, lemon and white flowers, with fine bubbles and toasty brioche notes from the time on the lees.

## Related styles

For a still wine with no pressure risk, make the Concord (`wine_concord`) or blackberry wine (`wine_blackberry`).
