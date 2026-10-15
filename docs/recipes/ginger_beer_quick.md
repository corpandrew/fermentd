---
schema: fermentd.recipe/v1
id: ginger_beer_quick
category: ginger_beer
profile_id: ginger_beer_quick
batch_number: 1
name: Quick Ginger Beer (about 4%)
status: active
yield:
  volume_gal: 1
  bottle_fl_oz: 12
  bottle_count: 9-10
tracking_mode: timer
target_f: 70
pitch_below_f: 80
og_target:
- 1.03
- 1.034
fg_target:
- 0.996
- 1.0
abv_expected:
- 3.8
- 4.5
primary_weeks:
- 1
- 1.5
bottle_condition_weeks:
- 1
- 2
condition_f: 70
priming:
  target_vol: 2.7
  table_sugar_g: 25
carbonation_window_h:
- 168
- 336
chill_before_open_h: 24
drink_within_days:
- 0
- 90
ingredients:
- id: ginger
  item: fresh ginger, unpeeled, finely grated
  amount: 6 oz (about 170 g)
  amount_half: 3 oz (about 85 g)
  grams: 170
- id: sugar
  item: white sugar
  amount: 300 g (about 1 1/2 cups)
  amount_half: 150 g (about 3/4 cup)
  grams: 300
  note: for the ferment; aim for OG 1.030-1.034
- id: lime
  item: fresh lime juice
  amount: 1/4 cup (2 limes)
  amount_half: 2 tbsp (1 lime)
- id: tartar
  item: cream of tartar
  amount: 1/4 tsp
  amount_half: 1/8 tsp
  note: adds acid and helps the yeast
- id: nutrient
  item: yeast nutrient
  amount: 1/2 tsp
  amount_half: 1/4 tsp
- id: water
  item: water
  amount: to make 1 gallon
  amount_half: to make 1/2 gallon
- id: yeast
  item: EC-1118 yeast
  amount: 1/4 tsp (about 1 g)
  amount_half: 1/4 tsp (about 1 g); yeast does not need halving
- id: priming
  item: table sugar for priming
  amount: 25 g
  amount_half: 12 g
  grams: 25
  note: at bottling only
optional:
- id: sweetener
  item: non-fermentable sweetener (erythritol or stevia)
  amount: to taste
  amount_half: to taste
  note: at bottling only, if you want it less dry
equipment:
- '1-gallon glass jug with bung and airlock (half batch: a half-gallon jug or growler)'
- 8-quart stock pot
- hydrometer and test jar (needed)
- auto-siphon, tubing and bottle filler
- fine strainer or cloth
- Star San
- '9-10 heavy 12 oz bottles (half batch: 5) plus one plastic tester bottle'
- kitchen scale
- seedling heat mat in the backpack cooler
safety:
- id: stable
  text: Prime only fully fermented ginger beer, with the same gravity (1.000 or lower) on 3 readings over 3 days.
- id: tester
  text: Bottle one plastic tester and move every bottle to the fridge when it is rock hard.
- id: glass
  text: Over-carbonated glass can burst. Never leave the bottles warm once the tester is rock hard.
- id: pitch
  text: Pitch yeast only below 80 F.
steps:
- id: simmer
  stage: day0
  profile_stage: primary
  text: Simmer the ginger 20 minutes, dissolve the sugar and cream of tartar, and strain.
- id: cool
  stage: day0
  profile_stage: primary
  text: Top up with cold water, add lime juice and nutrient, and cool below 80 F.
- id: pitch
  stage: day0
  profile_stage: primary
  text: Read the OG, pitch the yeast, fit the airlock, and start the batch at 70 F.
- id: primary
  stage: ferment
  profile_stage: primary
  text: Ferment about 7-10 days until the gravity is 1.000 or lower and stable.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Prime with the weighed sugar and bottle with a plastic tester.
- id: condition
  stage: package
  profile_stage: bottle_condition
  text: Condition about 1-2 weeks at 70 F until the tester is rock hard, then refrigerate.
taste: Dry, spicy and crisp with a real ginger burn and lime, about 4% ABV.
not_this_batch:
  id: ginger_beer_plant
  summary: A traditional ginger beer plant (or a wild ginger bug) is a different culture. It is not this batch.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 12
    bottle_count: '5'
  priming:
    target_vol: 2.7
    table_sugar_g: 12
reminders:
- id: airlock
  at: stage:primary+1d
  text: Check that the airlock is bubbling.
- id: gravity
  at: stage:primary+5d
  repeat: 2d
  text: Take a hydrometer reading. Bottle only when it is 1.000 or lower and the same on 3 readings over 3 days.
- id: tester
  at: stage:bottle_condition+5d
  repeat: 2d
  text: Squeeze the plastic tester bottle. Conditioning is done when it is rock hard.
- id: condition_done
  at: stage:bottle_condition+10d
  repeat: 2d
  text: If the tester is rock hard, move all bottles to the fridge. Do not leave carbonated glass warm.
---


## Ingredients

Makes [[1 gallon, about 9-10 bottles of 12 oz|a half gallon, about 5 bottles of 12 oz (a test batch)]]. OG 1.030-1.034, dry, about 4% ABV.

- [[6 oz (about 170 g)|3 oz (about 85 g)]] fresh ginger, unpeeled, finely grated
- [[300 g (about 1 1/2 cups)|150 g (about 3/4 cup)]] white sugar (for the ferment; aim for OG 1.030-1.034)
- [[1/4 cup (2 limes)|2 tbsp (1 lime)]] fresh lime juice
- [[1/4 tsp|1/8 tsp]] cream of tartar (adds acid and helps the yeast)
- [[1/2 tsp|1/4 tsp]] yeast nutrient
- [[to make 1 gallon|to make 1/2 gallon]] water
- [[1/4 tsp (about 1 g)|1/4 tsp (about 1 g); yeast does not need halving]] EC-1118 yeast
- [[25 g|12 g]] table sugar for priming (at bottling only)

**What makes it "quick" and alcoholic.** This is a real fermented ginger beer: EC-1118 eats all the sugar in about a week for roughly 4% ABV, then it is primed and bottle-conditioned like cider. It is **dry**, not sweet. If you want it sweeter, add a non-fermentable sweetener (erythritol or stevia) at bottling; never sugar or juice.

**Yeast.** 1/4 tsp EC-1118 is plenty for either size. **Yeast does not need halving.**

## Equipment

- 8-quart stock pot
- [[1-gallon glass jug|**Half-gallon glass jug or growler**]] with bung and airlock[[|. A half batch in the 1-gallon jug leaves too much air on top; use a half-gallon jug that takes your stopper size (about $5-8)]]
- **Hydrometer and test jar** (needed: priming before it is dry is how bottles burst)
- Fine strainer or a clean cloth, funnel
- Auto-siphon, tubing and bottle filler
- Star San and a spray bottle
- Kitchen scale for the priming sugar
- [[9-10|5]] heavy 12 oz bottles (swing-top or crown-capped), plus one plastic tester bottle
- Seedling heat mat in the backpack cooler

**Temperature.** These like warmth. The heat mat holds the target even in a cold winter room, so they work well all year. fermentd caps every target at 75 F. EC-1118 is happy at 70 F.

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Sanitize the jug, bung, airlock, funnel, hydrometer and test jar, siphon, and later the bottles. Let it drain; do not rinse.

## Brew day

About 45 minutes, plus cooling.

1. Simmer the grated ginger in [[1 quart|2 cups]] of water for 20 minutes. Longer is spicier.
2. Turn off the heat and stir in the sugar and cream of tartar until dissolved.
3. Strain through a fine strainer or cloth into the jug, pressing the ginger. Top up with cold water to [[1 gallon|1/2 gallon]] (about the shoulder).
4. Add the lime juice and yeast nutrient. Check that it is **below 80 F**.
5. Read the OG with the hydrometer. Aim for **1.030-1.034**; add a little sugar if it is low.
6. Sprinkle in the yeast, fit the airlock, and start the batch in fermentd at 70 F.

## Ferment

### First 3 days

1. Bubbling starts within a day.
2. A cloudy, yeasty look and a slight sulfur smell are normal and fade.

### Primary, about 7-10 days

From day 5 fermentd reminds you every 2 days to take a hydrometer reading. It is done at **1.000 or lower, the same on 3 readings over 3 days**.

## Bottle

1. Sanitize the bottling pot, siphon, filler, [[9-10|5]] bottles and the plastic tester.
2. Weigh **[[25 g|12 g]] table sugar**, dissolve it in [[1/4 cup|2 tbsp]] boiling water, and pour it into the pot.
3. Siphon the ginger beer onto it, leaving the sediment. Bottle with 1 inch of headspace plus the tester.
4. Press **Bottled, start conditioning**.

## Condition in the bottle

When the tester is **rock hard**, move every bottle to the fridge and press **Conditioning done, move to cool storage**. Chill 24 hours and open over the sink.

## Safety

- **Prime only fully fermented ginger beer**, at 1.000 or lower on 3 readings over 3 days.
- Never back-sweeten with sugar or juice; only non-fermentable sweeteners.
- Always bottle a plastic tester and move every bottle to the fridge once it is rock hard.
- Pitch below 80 F.

## Troubleshooting

- **Not fermenting.** Make sure it was below 80 F at pitching and that you added nutrient; ginger alone is poor food for yeast.
- **Not spicy enough.** Use more ginger or simmer longer, and grate it finer. A pinch of cayenne helps.
- **Too dry or thin.** Normal for this style. Sweeten with erythritol or stevia at bottling.
- **Gushing.** Primed before it finished. Chill the bottles well and open over the sink.

## Taste

Dry, spicy and crisp with a real ginger burn and lime, about 4% ABV.

## Related styles

A traditional ginger beer plant (or a wild ginger bug) is a different culture. It is not this batch.
