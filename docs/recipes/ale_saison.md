---
schema: fermentd.recipe/v1
id: ale_saison
category: ale
profile_id: ale_saison
batch_number: 1
name: Belgian Saison
status: active
yield:
  volume_gal: 1
  bottle_fl_oz: 12
  bottle_count: 9-10
tracking_mode: timer
target_f: 72
pitch_below_f: 75
og_target:
- 1.048
- 1.052
fg_target:
- 1.002
- 1.006
abv_expected:
- 5.8
- 6.5
ibu: 25
primary_weeks:
- 1
- 2
bottle_condition_weeks:
- 2
- 3
condition_f: 70
priming:
  target_vol: 2.8
  table_sugar_g: 28
carbonation_window_h:
- 336
- 504
chill_before_open_h: 48
drink_within_days:
- 0
- 120
ingredients:
- id: dme
  item: Pilsen Light dry malt extract
  amount: 450 g (1 lb)
  amount_half: 225 g
  grams: 450
- id: sugar
  item: table sugar, added to the boil
  amount: 60 g
  amount_half: 30 g
  grams: 60
  note: dries it out
- id: bitter
  item: Styrian Goldings hops (about 5% AA), 60 minutes
  amount: 7 g
  amount_half: 4 g
  grams: 7
- id: aroma
  item: Styrian Goldings hops, 5 minutes
  amount: 5 g
  amount_half: 3 g
  grams: 5
- id: yeast
  item: LalBrew Belle Saison dry yeast
  amount: about 4 g (1/3 of an 11 g packet)
  amount_half: about 3 g; yeast does not need exact halving
- id: priming
  item: table sugar for priming
  amount: 28 g
  amount_half: 14 g
  grams: 28
  note: at bottling only
optional:
- id: irish_moss
  item: Irish moss
  amount: 1/4 tsp
  amount_half: 1/8 tsp
  note: at 15 minutes, for clarity
equipment:
- 8-quart (2-gallon) stock pot
- '1-gallon glass jug with bung and airlock (half batch: a half-gallon jug or growler)'
- blow-off tube that fits the bung, and a small jar
- hydrometer and test jar (needed)
- kitchen scale that reads grams
- thermometer
- auto-siphon and tubing with a bottle filler
- funnel and strainer
- grain bag (if the recipe steeps grain)
- Star San and a spray bottle
- a sink or tub for an ice bath
- '9-10 heavy 12 oz bottles with caps and a capper, or swing-tops (half batch: 5), plus one plastic tester bottle'
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
- id: boil
  stage: day0
  profile_stage: primary
  text: Stir in the extract off the heat, then boil 60 minutes with the hop additions.
- id: chill
  stage: day0
  profile_stage: primary
  text: Chill below 75 F, pour into the jug, and top up with cold water to the batch size.
- id: pitch
  stage: day0
  profile_stage: primary
  text: Read the OG, pitch the yeast, fit a blow-off tube, and start the batch in fermentd at 72 F.
- id: primary
  stage: ferment
  profile_stage: primary
  text: Start at 72 F. After day 3, raise the target to 75 F (the maximum fermentd allows) so the yeast finishes dry. It usually takes 10-14 days.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Prime with the weighed sugar and bottle with 1 inch of headspace plus a plastic tester.
- id: condition
  stage: package
  profile_stage: bottle_condition
  text: Condition at about 70 F for 2 weeks until the tester is rock hard, then store cold.
taste: Pale gold, bone dry and very fizzy, with pepper, citrus and a light earthy hop finish, about 6% ABV.
not_this_batch:
  id: ale_saison_dark
  summary: A dark or spiced saison (with orange peel and coriander) is a variation; it is not this batch.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 12
    bottle_count: '5'
  priming:
    target_vol: 2.8
    table_sugar_g: 14
reminders:
- id: airlock
  at: stage:primary+1d
  text: Check for foam (krausen) and airlock activity. If foam reaches the airlock, swap in a blow-off tube or rinse and re-sanitize the airlock.
- id: gravity
  at: stage:primary+10d
  repeat: 2d
  text: Take a hydrometer reading. Bottle only when it is in the final gravity range and the same on 3 readings over 3 days.
- id: tester
  at: stage:bottle_condition+7d
  repeat: 2d
  text: Squeeze the plastic tester bottle. Conditioning is done when it is rock hard. At 70 F this takes about 2 weeks.
- id: condition_done
  at: stage:bottle_condition+14d
  repeat: 3d
  text: If the tester is rock hard, move all bottles to the fridge or cool storage. Do not leave carbonated glass warm.
---


## Ingredients

Makes [[1 gallon, about 9-10 bottles of 12 oz|a half gallon, about 5 bottles of 12 oz (a test batch)]]. OG 1.048-1.052, FG 1.002-1.006, about 5.8-6.5% ABV, about 25 IBU.

- [[450 g (1 lb)|225 g]] Pilsen Light dry malt extract
- [[60 g|30 g]] table sugar, added to the boil (dries it out)
- [[7 g|4 g]] Styrian Goldings hops (about 5% AA), 60 minutes
- [[5 g|3 g]] Styrian Goldings hops, 5 minutes
- [[about 4 g (1/3 of an 11 g packet)|about 3 g; yeast does not need exact halving]] LalBrew Belle Saison dry yeast
- [[28 g|14 g]] table sugar for priming (at bottling only)
- Optional: [[1/4 tsp|1/8 tsp]] Irish moss at 15 minutes, for clarity

**What makes it a saison.** A very dry, highly carbonated Belgian farmhouse ale with peppery, fruity yeast character. The sugar and the saison yeast take it down to about 1.004, and it is bottled with extra carbonation, so heavy bottles matter here.

**Hops.** Styrian Goldings give the earthy, peppery-floral note. Saaz or East Kent Goldings are good swaps.

**Yeast.** LalBrew Belle Saison is a dry saison yeast that does not stall, unlike some liquid saison strains. Use about 4 g. **Yeast does not need exact halving** for a half batch; a little extra is never a problem. Fold the packet shut, tape it, and keep the rest in the fridge.

## Equipment

- 8-quart (2-gallon) stock pot
- [[1-gallon glass jug|**Half-gallon glass jug or growler**]] with bung and airlock[[|. A half batch in the 1-gallon jug leaves too much air on top; use a half-gallon jug that takes your stopper size (about $5-8)]]
- Blow-off tube that fits the bung, and a small jar of sanitizer
- **Hydrometer and test jar** (needed: it is the only safe way to know the beer is done before priming)
- Kitchen scale that reads grams; hops and priming sugar are weighed
- Thermometer, auto-siphon and tubing with a bottle filler, funnel, strainer, grain bag
- Star San and a spray bottle
- A sink or tub for an ice bath
- [[9-10|5]] heavy 12 oz bottles with caps and a capper (or swing-tops), plus one plastic tester bottle
- Seedling heat mat in the backpack cooler

**Temperature.** These like warmth. The heat mat holds the target even in a cold winter room, so they work well all year. fermentd caps every target at 75 F. Ale fermentation makes its own heat in the first 3 days, so the jug can run 3-5 F above the room; the mat simply switches off then.

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Everything that touches the wort **after the boil** must be sanitized: jug, bung, blow-off tube, airlock, funnel, strainer, thermometer, hydrometer and test jar, siphon, and later the bottles and caps. Let it drain; do not rinse.

## Brew day

About 2 hours, mostly the boil and the chill.

1. Bring [[1.5 gallons|3 quarts]] of water to about 160 F in the stock pot.
2. Turn off the heat and stir in the extract a little at a time until there are no clumps.
3. Bring it back to a boil. Add the 60-minute hops and start a 60-minute timer. Watch for boil-over in the first 5 minutes.
4. Add the later hop additions at the times listed (and Irish moss at 15 minutes if using).
5. At the end, set the pot in an ice-water bath and stir gently until the wort is **below 75 F**.
6. Sanitize the jug, funnel, strainer, hydrometer and test jar. Strain the wort into the jug, then top up with cold water to [[the 1-gallon mark|the half-gallon mark]] (about the shoulder).
7. Read the original gravity (OG) with the hydrometer and write it down. Correct for temperature if the wort is warm.
8. Sprinkle in the yeast, fit the bung with a **blow-off tube** into a jar of sanitizer, and swirl.
9. Put the jug in the cooler on the mat and start the batch in fermentd at 72 F.

## Ferment

### First 3 days

1. Active fermentation starts within 12-24 hours with a thick foam (krausen).
2. If foam climbs the blow-off tube, that is what it is for. After day 3, swap the tube for an airlock.
3. A yeasty, fruity smell is normal.

### Primary

Start at 72 F. After day 3, raise the target to 75 F (the maximum fermentd allows) so the yeast finishes dry. It usually takes 10-14 days. From day 10, fermentd reminds you every 2 days to take a hydrometer reading. It is done when the gravity is in the 1.002-1.006 range and **the same on 3 readings over 3 days**. ABV is about (OG - FG) x 131.

**Saison and the 75 F cap.** Many saison brewers let it rise into the 80s. fermentd stops at 75 F for safety, which is warm enough for Belle Saison to finish dry; it just takes a few days longer.

## Bottle

1. Sanitize the bottling vessel (a clean pot), siphon, bottle filler, [[9-10|5]] bottles and caps, and the plastic tester.
2. Weigh **[[28 g|14 g]] table sugar**. Dissolve it in [[1/4 cup|2 tbsp]] boiling water and let it cool.
3. Pour it into the bottling vessel and siphon the beer onto it, leaving the sediment behind. Stir gently.
4. Fill bottles with 1 inch of headspace. Fill and squeeze the plastic tester, then cap everything.
5. Press **Bottled, start conditioning** and set the target to about 70 F.

## Condition in the bottle

When the plastic tester is **rock hard**, move every bottle cold and press **Conditioning done, move to cool storage**. Chill at least 2 days before opening; pour gently and leave the yeast layer behind.

## Safety

- **Prime only fully finished beer**, with the same gravity on 3 readings over 3 days. Priming unfinished beer is how bottles burst.
- Weigh the priming sugar; never more than [[28 g|14 g]] for this batch.
- Always bottle a plastic tester. Once it is rock hard, move all bottles cold.
- Boiling wort boils over in seconds and burns. Stay at the stove.

## Troubleshooting

- **No activity after 2 days.** Check the gravity; if it dropped, it is working. Make sure the wort was below 75 F when you pitched.
- **Blow-off everywhere.** Normal for a full jug. Clean up, re-sanitize, and use the blow-off tube next time from day 0.
- **Stuck a few points high.** Swirl the jug gently and raise the target 2 F for a few days.
- **Hot, solvent-like taste.** It fermented too warm in the first 3 days. Keep the room cooler during the most active days.
- **Flat after 2 weeks.** Keep the bottles at 70 F another week.
- **Gushing.** Primed before it finished, or too much sugar. Chill all bottles and open over the sink.

## Taste

Pale gold, bone dry and very fizzy, with pepper, citrus and a light earthy hop finish, about 6% ABV.

## Related styles

A dark or spiced saison (with orange peel and coriander) is a variation; it is not this batch.
