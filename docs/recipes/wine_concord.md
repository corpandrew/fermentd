---
schema: fermentd.recipe/v1
id: wine_concord
category: wine
profile_id: wine_concord
batch_number: 1
name: Concord Grape Wine
status: active
yield:
  volume_gal: 1
  bottle_fl_oz: 25
  bottle_count: 4-5
tracking_mode: timer
target_f: 66
pitch_below_f: 80
og_target:
- 1.08
- 1.09
fg_target:
- 0.99
- 0.998
abv_expected:
- 10.5
- 12.0
primary_weeks:
- 3
- 5
aging_months:
- 2
- 4
carbonation_window_h:
- 0
- 0
chill_before_open_h: 0
drink_within_days:
- 90
- 545
ingredients:
- id: juice
  item: 100% Concord grape juice, bottled
  amount: 1 gallon
  amount_half: 1/2 gallon (64 fl oz)
  note: Welch's bottled 100% grape juice works; no sorbate or benzoate. Or 3 cans of frozen 100% Concord concentrate made up to 1 gallon
- id: sugar
  item: white sugar
  amount: about 1 cup (200 g)
  amount_half: about 1/2 cup (100 g)
  grams: 200
  note: only enough to reach the OG target
- id: pectic
  item: pectic enzyme
  amount: 1/2 tsp
  amount_half: 1/4 tsp
- id: nutrient
  item: yeast nutrient
  amount: 1 tsp
  amount_half: 1/2 tsp
- id: tannin
  item: wine tannin
  amount: 1/8 tsp
  amount_half: a pinch
- id: yeast
  item: Lalvin 71B wine yeast
  amount: 1-2 g (1/4-1/2 packet)
  amount_half: about 1 g; yeast does not need exact halving
  note: 71B eats some malic acid and softens Concord's sharpness; EC-1118 also works
optional:
- id: sorbate
  item: potassium sorbate
  amount: 1/2 tsp
  amount_half: 1/4 tsp
  note: for the traditional semi-sweet finish
- id: campden
  item: Campden tablet
  amount: '1'
  amount_half: 1/2
  note: at racking and bottling
equipment:
- '1-gallon glass jug with bung and airlock (half batch: a half-gallon jug or growler)'
- a second clean jug for racking
- hydrometer and test jar (needed)
- auto-siphon and tubing
- funnel
- Star San and a spray bottle
- thermometer and kitchen scale
- '4-5 wine bottles with corks, or 9-10 12 oz bottles with caps (half batch: 2 or 5)'
- seedling heat mat in the backpack cooler
safety:
- id: dry
  text: Bottle only when the wine is dry (0.998 or lower) and unchanged on 3 readings over 3 days. Bottled wine that is still fermenting can push corks or burst bottles.
- id: sweeten
  text: Never add sugar or juice at bottling unless the wine was stabilized with potassium sorbate and Campden at least 24 hours before.
- id: campden
  text: Wait at least 12 hours after Campden before pitching yeast.
- id: pitch
  text: Pitch below 80 F.
- id: sorbate
  text: Juice with sorbate or benzoate will not ferment reliably. Check the label.
steps:
- id: sanitize
  stage: day0
  profile_stage: primary
  text: Sanitize the jug, funnel, hydrometer and test jar.
- id: og
  stage: day0
  profile_stage: primary
  text: Read the juice gravity and add sugar to reach OG 1.080-1.090.
- id: pitch
  stage: day0
  profile_stage: primary
  text: Add pectic enzyme, nutrient and tannin, fill to the shoulder, pitch the yeast, and start the batch in fermentd at 66 F.
- id: primary
  stage: ferment
  profile_stage: primary
  text: Ferment 1-2 weeks until the gravity is 1.000 or lower.
- id: rack
  stage: ferment
  profile_stage: secondary
  text: Rack off the sediment, top up into the neck, and finish dry over 2-4 weeks.
- id: age
  stage: ferment
  profile_stage: aging
  text: Rack every 1-2 months and age 2-4 months.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Bottle dry, or stabilize and sweeten to taste for the classic semi-sweet style.
- id: cellar
  stage: serve
  profile_stage: cellared
  text: Store cool and dark; it softens over 3-6 months.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 25
    bottle_count: '2'
taste: Bright purple, grapey and jammy, sharp when dry and classic when finished semi-sweet, about 10.5-12% ABV.
not_this_batch:
  id: wine_concord_port
  summary: A sweet, fortified Concord port needs added spirits. It is not this batch.
reminders:
- id: airlock
  at: stage:primary+2d
  text: Check that the airlock is bubbling. Concord foams; wipe and re-sanitize the airlock if foam reaches it.
- id: gravity
  at: stage:primary+10d
  repeat: 3d
  text: Take a gravity reading. Rack once it is 1.000 or lower.
- id: dry_check
  at: stage:secondary+14d
  repeat: 7d
  text: Check gravity and clarity. Move on to aging once it is 0.998 or lower and the same on 3 readings over 3 days.
- id: rack
  at: stage:aging+30d
  repeat: 45d
  text: Rack off any new sediment into a clean jug, add 1/4 crushed Campden tablet per gallon every other racking, and top up to the neck.
- id: bottle_ready
  at: stage:aging+60d
  repeat: 30d
  text: Bottle when clear. To make it semi-sweet, stabilize with sorbate and Campden first, wait 24 hours, then sweeten to taste.
- id: cellar
  at: stage:cellared+60d
  text: Try a bottle. Concord wine softens a lot after 3-6 months.
---


## Ingredients

Makes [[1 gallon, about 4-5 wine bottles (or 9-10 bottles of 12 oz)|a half gallon, about 2 wine bottles (or 5 bottles of 12 oz), a test batch]]. OG 1.080-1.090, about 10.5-12% ABV, still (not sparkling).

- [[1 gallon|1/2 gallon (64 fl oz)]] 100% Concord grape juice, bottled (Welch's 100% grape juice works), **with no potassium sorbate or sodium benzoate** on the label. Or [[3 cans|1 1/2 cans]] of frozen 100% Concord concentrate made up to [[1 gallon|1/2 gallon]] with water
- [[About 1 cup (200 g)|About 1/2 cup (100 g)]] white sugar, only enough to reach the target gravity
- [[1/2 tsp|1/4 tsp]] pectic enzyme
- [[1 tsp|1/2 tsp]] yeast nutrient
- [[1/8 tsp|a pinch]] wine tannin
- Lalvin 71B wine yeast, [[1-2 g|about 1 g]] (EC-1118 also works)
- Optional, at bottling: [[1/2 tsp|1/4 tsp]] potassium sorbate and [[1|1/2]] Campden tablet, for the semi-sweet finish

**Concord wine.** Concord is the American grape behind grape juice and jelly. Its "foxy", grapey flavor and sharp acid are why this wine is traditionally finished **semi-sweet**, like the classic kosher-style or Niagara-region bottles. Bottled juice usually reads about 1.060-1.065, so it needs a little sugar; each 1/4 cup raises a gallon by about 0.010. 71B yeast is chosen because it eats some of the malic acid and softens the bite.

**Yeast.** Use [[1/4-1/2 of a 5 g packet (1-2 g)|about 1/4 of a 5 g packet (about 1 g)]]. A wine yeast packet is sized for up to 5 gallons. **Yeast does not need exact halving** for a half batch; a little extra does no harm. Rehydrate it in 1/4 cup lukewarm (95-100 F) water for 15 minutes before pitching.

## Equipment

- [[1-gallon glass jug|**Half-gallon glass jug or growler**]] with bung and airlock[[|. A half batch in the 1-gallon jug leaves too much air on top, which spoils wine over months of aging; use a half-gallon jug that takes your stopper size (about $5-8)]]
- A second clean jug of the same size for racking
- **Hydrometer and test jar** (needed)
- Auto-siphon and tubing, funnel, strainer
- Star San and a spray bottle
- Thermometer and a kitchen scale
- Bottles: [[4-5 wine bottles (750 ml) with corks, or 9-10 12 oz bottles with caps|2 wine bottles (750 ml) with corks, or 5 12 oz bottles with caps]]
- Seedling heat mat in the backpack cooler

**Temperature, with a heat-only rig.** Fruit wine yeast likes about 64-72 F. fermentd holds a floor of 66 F, which suits winter well: in a cool room the mat just keeps the yeast warm enough. Aging can happen anywhere cool and dark, off the rig.

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Sanitize everything that touches the fruit or juice: bucket, jug, bung, airlock, funnel, spoon, hydrometer and test jar, siphon, and later the bottles. Let it drain; do not rinse.

## Juice prep and pitch

About 30 minutes, plus 15 minutes to rehydrate the yeast. No Campden needed for bottled juice.

1. Let the juice reach room temperature. Sanitize the jug, funnel, hydrometer and test jar.
2. Pour a little juice into the test jar and read the gravity. Dissolve sugar in a cup of the juice, a little at a time, until it reads **1.080-1.090**. Write down the OG.
3. Stir in the pectic enzyme, nutrient and tannin.
4. Pour it into the jug **only to the shoulder**: Concord foams hard in the first days. Keep any leftover juice in the fridge for topping up later.
5. Rehydrate the yeast for 15 minutes and pitch it below 80 F.
6. Fit the bung and airlock, put the jug in the cooler on the mat, and start the batch in fermentd. It starts in **Primary** at 66 F.

## Primary

### First 3 days

1. Bubbling starts within 24-48 hours, often with a thick purple foam. If foam reaches the airlock, take it off, rinse and re-sanitize it, wipe the neck, and refit it.
2. A grapey, yeasty smell is normal. A strong rotten-egg smell means it wants more nutrient; see Troubleshooting.

### Until 1.000, 1-2 weeks

From day 10 fermentd reminds you every 3 days to take a gravity reading. Move on when it reads **1.000 or lower**.

## Rack and finish dry

1. Siphon off the sediment into the clean jug, top up into the neck with the saved juice or a little water, and fit the airlock. Press **Clearing in secondary**.
2. It is done when it reads **0.998 or lower and the same on 3 readings over 3 days**.

## Rack, clear and age

1. Rack off the sediment again, add [[1/4|1/8]] crushed Campden tablet, top up, and press **Start aging**.
2. Rack every 1-2 months. Purple sediment and tartrate crystals on the glass are normal.
3. Aging can happen anywhere cool and dark, off the heat mat, which frees the cooler for another batch.

## Backsweeten (optional) and bottle

1. Confirm the gravity is 0.998 or lower and unchanged on 3 readings over 3 days, and the wine has dropped no sediment for a month.
2. **Dry wine:** add [[1/4|1/8]] crushed Campden tablet, then siphon into sanitized bottles and cork or cap them.
3. **Semi-sweet (optional):** stir in [[1/2 tsp|1/4 tsp]] potassium sorbate and [[1|1/2]] crushed Campden tablet. Wait at least 24 hours. Then dissolve sugar to taste (start with [[1/4 cup|2 tbsp]]), taste, and bottle. **Without the sorbate, the sugar will ferment in the bottle.**
4. Press **Bottled** on the dashboard. Store bottles cool and dark; lay corked bottles on their side after 3 days.

## Safety

- Bottle only when dry and stable on 3 readings over 3 days.
- Never add sugar or juice at bottling unless you stabilized with potassium sorbate and Campden at least 24 hours before.
- Wait at least 12 hours after Campden before pitching yeast.
- Pitch below 80 F.
- Juice with potassium sorbate or sodium benzoate will not ferment reliably. Read the label.

## Troubleshooting

- **No bubbles after 3 days.** Check the gravity first; if it dropped, it is working. Make sure you waited 12 hours after Campden, the cooler is at least 64 F, and the juice has no sorbate. Pitch fresh rehydrated yeast if nothing has moved.
- **Rotten-egg smell.** The yeast is short of nutrient. Stir in [[1/4 tsp|1/8 tsp]] more nutrient in the first week and swirl the jug.
- **Stuck above 1.005.** Swirl to rouse the yeast, warm to 70 F, and add [[1/4 tsp|1/8 tsp]] nutrient. If it still does not move in a week, pitch rehydrated EC-1118; it finishes almost anything.
- **Too sour.** Acidity softens with months of aging. Stabilize and sweeten slightly at bottling, which balances it.
- **Hazy after 3 months.** That is usually pectin haze; the pectic enzyme prevents most of it. Wait longer, or use a fining agent such as bentonite or Sparkolloid as the label directs.
- **Vinegar smell or a white film.** Too much air. Keep the jug topped up into the neck and the airlock filled. A thin white film (flowers of wine) can be skimmed off; a strong vinegar smell means the batch is lost.

## Taste

Bright purple, grapey and jammy, sharp when dry and classic when finished semi-sweet, about 10.5-12% ABV.

## Related styles

A sweet, fortified Concord port needs added spirits. It is not this batch.
