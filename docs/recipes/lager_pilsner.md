---
schema: fermentd.recipe/v1
id: lager_pilsner
category: lager
profile_id: lager_pilsner
batch_number: 1
name: Czech-Style Pilsner
status: active
yield:
  volume_gal: 1
  bottle_fl_oz: 12
  bottle_count: 9-10
tracking_mode: timer
target_f: 50
pitch_below_f: 60
og_target:
- 1.046
- 1.05
fg_target:
- 1.008
- 1.012
abv_expected:
- 4.6
- 5.2
ibu: 32
primary_weeks:
- 1.5
- 2
lager_weeks:
- 3
- 6
bottle_condition_weeks:
- 2
- 3
condition_f: 66
priming:
  target_vol:
  - 2.4
  - 2.6
  table_sugar_g: 22
  corn_sugar_g: 24
carbonation_window_h:
- 336
- 504
chill_before_open_h: 48
drink_within_days:
- 0
- 90
ingredients:
- id: dme
  item: Pilsen Light dry malt extract
  amount: 500 g (1.1 lb)
  amount_half: 250 g
  grams: 500
  note: the palest extract you can find
- id: bitter
  item: Saaz hops (about 3.5% AA), bittering
  amount: 11 g
  amount_half: 6 g
  grams: 11
  note: 60 minutes
- id: flavor
  item: Saaz hops, flavor
  amount: 7 g
  amount_half: 4 g
  grams: 7
  note: 15 minutes
- id: aroma
  item: Saaz hops, aroma
  amount: 7 g
  amount_half: 4 g
  grams: 7
  note: at flameout
- id: yeast
  item: Saflager W-34/70 dry lager yeast
  amount: about 6 g (half an 11.5 g packet)
  amount_half: about 4 g (a third of the packet); yeast does not need exact halving
  note: sprinkle dry onto the cooled wort
- id: priming
  item: table sugar for priming
  amount: 22 g
  amount_half: 11 g
  grams: 22
  note: at bottling only; or 24 g corn sugar
optional:
- id: irish_moss
  item: Irish moss
  amount: 1/4 tsp
  amount_half: 1/8 tsp
  note: at 15 minutes, for clarity
equipment:
- 8-quart (2-gallon) stock pot
- '1-gallon glass jug with bung and airlock (half batch: a half-gallon jug or growler)'
- hydrometer and test jar (needed)
- kitchen scale that reads grams (hops are weighed in grams)
- thermometer
- auto-siphon and tubing with a bottle filler
- funnel and strainer
- Star San and a spray bottle
- a sink or tub for an ice bath
- '9-10 heavy 12 oz bottles with caps and a capper, or swing-tops (half batch: 5), plus one plastic tester bottle'
- a fridge or a garage that stays near freezing, for lagering
- seedling heat mat in the backpack cooler
safety:
- id: stable
  text: Prime only fully finished beer, with the same gravity on 3 readings over 3 days.
- id: glass
  text: Use bottles rated for carbonation and weigh the priming sugar.
- id: tester
  text: Bottle one plastic tester and move all bottles cold once it is rock hard.
- id: hot
  text: Boiling wort boils over fast. Stay at the stove when the extract goes in and in the first minutes of the boil.
- id: pitch
  text: Chill the wort below 60 F before pitching.
steps:
- id: sanitize
  stage: day0
  profile_stage: primary
  text: Sanitize everything that touches the wort after the boil.
- id: boil
  stage: day0
  profile_stage: primary
  text: Stir in the malt extract off the heat, then boil 60 minutes with the hop additions.
- id: chill
  stage: day0
  profile_stage: primary
  text: Chill in an ice bath below 60 F, pour into the jug, and top up with cold water to the batch size.
- id: pitch
  stage: day0
  profile_stage: primary
  text: Read the OG, pitch the yeast, fit the airlock, and start the batch in fermentd at 50 F in a cold spot.
- id: primary
  stage: ferment
  profile_stage: primary
  text: Ferment about 10-14 days at 50 F.
- id: drest
  stage: ferment
  profile_stage: diacetyl_rest
  text: Raise the target to 60 F for 2-3 days (diacetyl rest).
- id: lager
  stage: ferment
  profile_stage: lagering
  text: Rack into a clean jug and lager in the fridge or a near-freezing garage for 3-6 weeks.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Prime with the weighed sugar and bottle with 1 inch of headspace plus a plastic tester.
- id: condition
  stage: package
  profile_stage: bottle_condition
  text: Condition at 64-66 F about 2-3 weeks until the tester is rock hard, then store cold.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 12
    bottle_count: '5'
  priming:
    target_vol:
    - 2.4
    - 2.6
    table_sugar_g: 11
    corn_sugar_g: 12
taste: Pale gold, crisp, and clean with a firm bitterness and a spicy, floral Saaz finish, about 4.6-5.2% ABV.
not_this_batch:
  id: lager_german_pils
  summary: A German pils is drier and more bitter, with Hallertau or Tettnang hops. Swap the Saaz for Hallertau and add 2 g more at 60 minutes if you want one.
reminders:
- id: airlock
  at: stage:primary+2d
  text: Lagers start slowly when cold. Check for a thin krausen or airlock activity; up to 72 hours is normal at 50 F.
- id: room_check
  at: stage:primary+3d
  repeat: 3d
  text: Check the cooler temperature. The heater can only hold the floor; if it reads above 56 F, move the cooler somewhere colder.
- id: gravity
  at: stage:primary+10d
  repeat: 2d
  text: Take a gravity reading. Start the diacetyl rest once it is within about 0.004 of the expected final gravity.
- id: drest_done
  at: stage:diacetyl_rest+3d
  text: Diacetyl rest done if the gravity is stable and a warmed sample has no butter or butterscotch smell. Set the target back down and move to lagering.
- id: lager_check
  at: stage:lagering+21d
  repeat: 7d
  text: Lagering is done after 3-6 weeks cold, once the beer is clear. Bottle when it tastes clean.
- id: tester
  at: stage:bottle_condition+10d
  repeat: 2d
  text: Squeeze the plastic tester bottle. Conditioning is done when it is rock hard.
- id: condition_done
  at: stage:bottle_condition+21d
  repeat: 3d
  text: If the tester is rock hard, move all bottles to the fridge or a cold garage. Do not leave carbonated glass warm.
---


## Ingredients

Makes [[1 gallon, about 9-10 bottles of 12 oz|a half gallon, about 5 bottles of 12 oz (a test batch)]]. OG 1.046-1.050, about 4.6-5.2% ABV, about 32 IBU.

- [[500 g (1.1 lb)|250 g]] Pilsen Light dry malt extract
- [[11 g|6 g]] Saaz hops at 60 minutes (bittering)
- [[7 g|4 g]] Saaz hops at 15 minutes (flavor)
- [[7 g|4 g]] Saaz hops at flameout (aroma)
- Saflager W-34/70 dry lager yeast, [[about 6 g (half the packet)|about 4 g (a third of the packet)]]
- [[22 g|11 g]] table sugar for priming at bottling, or [[24 g|12 g]] corn sugar
- Optional: [[1/4 tsp|1/8 tsp]] Irish moss at 15 minutes, for clarity

**What makes it a Czech pilsner.** Pale malt, soft water, and a generous amount of spicy, herbal Saaz hops. Saaz is low in alpha acid, so it takes more of it to get the bitterness. If your tap water is very hard, brew with half spring or distilled water for a softer, cleaner bite.

**Yeast.** Saflager W-34/70 is a forgiving dry lager yeast that works from 48 to 59 F. Lagers want about twice the yeast of an ale, so use [[half of the 11.5 g packet (about 6 g)|about a third of the packet (4 g)]]. **Yeast does not need to be scaled down exactly**: a little extra is never a problem, so for a half batch just use a generous pinch more than a third. Fold the rest of the packet shut, tape it, and keep it in the fridge for the next batch.

**Malt extract instead of grain.** A one-gallon all-grain mash is possible, but dry malt extract (DME) gives a reliable result on a stovetop with no extra gear. Buy it fresh; old extract darkens and tastes stale.

## Equipment

- 8-quart (2-gallon) stock pot
- [[1-gallon glass jug|**Half-gallon glass jug or growler**]] with bung and airlock[[|. A half batch in the 1-gallon jug leaves too much air on top; get a half-gallon jug that takes your stopper size (about $5-8)]]
- A second clean jug of the same size for lagering
- **Hydrometer and test jar** (needed)
- Kitchen scale that reads grams; hops are weighed in grams
- Thermometer
- Auto-siphon and tubing with a bottle filler, funnel, strainer
- Star San and a spray bottle
- A sink or tub for an ice bath
- [[9-10|5]] heavy 12 oz bottles with caps and a capper (or swing-tops), plus one plastic tester bottle
- A fridge with room for the jug, or a garage that stays near freezing, for lagering
- Seedling heat mat in the backpack cooler

**Temperature, with a heat-only rig. Read this first.** A lager ferments at about 48-55 F. The heat mat can only add heat, so fermentd holds a **floor** of 50 F and the room has to do the cooling. That means the cooler must sit somewhere **unheated that stays about 45-55 F**: a winter garage, a cold basement, or an unheated porch room. The mat keeps it from dropping too low on cold nights. In a normal 65-70 F room this recipe will not taste like a lager; wait for a colder spot or make the cider instead.

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Everything that touches the wort **after the boil** must be sanitized: jug, bung, airlock, funnel, strainer, thermometer, hydrometer and test jar, siphon, and later the bottles and caps. Let it drain; do not rinse.

## Brew day

About 2 hours, mostly the boil and the chill.

1. Bring [[1.5 gallons|3 quarts]] of water to about 160 F in the stock pot.
2. Turn off the heat and stir in the malt extract a little at a time until there are no clumps. (Extract added to boiling water foams over.)
3. Bring it back to a boil. As soon as it boils, add the **bittering hops** and start a 60-minute timer. Keep the lid off and watch for boil-over in the first 5 minutes.
4. With 15 minutes left, add the **flavor hops** (and the Irish moss if using).
5. At 60 minutes, turn off the heat and add the **aroma hops** if the recipe has them. Let them sit 5 minutes.
6. Set the pot in an ice-water bath in the sink and stir gently. Refresh the ice until the wort is **below 60 F**. This takes 20-40 minutes.
7. Sanitize the jug, funnel, strainer, hydrometer and test jar. Pour the cooled wort through the strainer into the jug, then top up with cold water to [[the 1-gallon mark (about the shoulder)|the half-gallon mark (about the shoulder)]].
8. Read the original gravity (OG) and write it down.
9. Sprinkle in the yeast (dry pitch is fine for W-34/70 at this size), fit the bung and airlock, and swirl.
10. Put the jug in the cooler in your **cold spot** and start the batch in fermentd. It starts in **Primary** at 50 F.

## Ferment

### First 3 days

1. Cold lager yeast starts slowly. A thin foam and slow airlock bubbles within 24-72 hours is normal at 50 F.
2. Watch the cooler temperature on the dashboard. The heat mat switches on only when the cooler drops below 50 F. **If the reading sits above 56 F, the room is too warm; find a colder spot.** Fermenting a lager at 65 F gives fruity, ale-like flavors.
3. A faint sulfur (rotten-egg) smell is normal for lager yeast and fades during lagering.

### Primary, about 10-14 days at 50 F

From day 10, fermentd reminds you every 2 days to take a gravity reading. Primary is done when the gravity is within about 0.004 of the expected final gravity (about 1.008-1.012).

## Diacetyl rest

Press **Start diacetyl rest** and raise the target to 60 F on the dashboard. The mat can do this one, since it only needs *more* heat. The warmer yeast cleans up diacetyl, a butter or butterscotch flavor. When the gravity has been the same for 3 days and a warmed sample has no butter smell, it is done.

## Lager (off the rig)

Lagering happens **off the rig**, because the mat cannot cool.

1. Sanitize a second jug and the siphon. Rack the beer off the yeast, leaving the sediment behind, and fit the airlock.
2. Press **Moved to cold lagering**, then move the jug to the fridge, or to a garage that stays around 33-40 F without freezing.
3. Leave it 3-6 weeks. It clears and the flavor gets clean and smooth.

## Bottle

1. Sanitize the bottling vessel (a clean pot works), the siphon, the bottle filler, [[9-10|5]] bottles and caps, and the plastic tester.
2. Weigh **[[22 g|11 g]] table sugar** (or [[24 g|12 g]] corn sugar). Dissolve it in [[1/4 cup|2 tbsp]] boiling water and let it cool.
3. Pour the sugar solution into the bottling vessel and siphon the beer onto it. Stir gently without splashing.
4. Fill bottles with the bottle filler, leaving about 1 inch of headspace. Fill and squeeze the plastic tester, then cap everything.
5. Press **Bottled, start conditioning**.

## Condition in the bottle

Bring the bottles back to the cooler, set the target to 64-66 F, and let the yeast carbonate them. After cold lagering there is still enough yeast; it just takes a little longer than an ale. When the tester is **rock hard**, move every bottle to the fridge and press **Conditioning done, move to cool storage**.

## Serve

Chill at least 2 days. Pour gently and leave the yeast layer in the bottle. Drink within about 3 months; lagers taste best fresh.

## Safety

- **Prime only fully finished beer**, with the same gravity on 3 readings over 3 days. Priming beer that is still fermenting is how bottles burst.
- Weigh the priming sugar. Do not use more than 22 g table sugar per gallon (11 g per half gallon).
- Always bottle a plastic tester. Once it is rock hard, move all bottles cold.
- Boiling wort can boil over in seconds and causes bad burns. Stay at the stove.
- Chill below 60 F before pitching.

## Troubleshooting

- **No activity after 3 days.** Normal-ish when cold. Check the gravity; if it has dropped, it is working. If not, let it warm to 55 F for a day, then bring it back down.
- **Fruity, ale-like taste.** It fermented too warm in the first week. Next time pick a colder spot, or brew in mid-winter.
- **Butter or butterscotch flavor.** The diacetyl rest was skipped or too short. Warm the jug to 60 F for 3 more days before lagering.
- **Sulfur smell.** Lager yeast makes some. It fades with cold lagering.
- **Cloudy beer.** Lager longer, or add Irish moss next time. A chill haze clears as it sits cold.
- **Flat after 3 weeks.** Keep the bottles at 66 F one more week.
- **Gushing.** Primed before it finished, or too much sugar. Chill all the bottles and open them over the sink.

## Taste

Pale gold, crisp, and clean with a firm bitterness and a spicy, floral Saaz finish, about 4.6-5.2% ABV.

## Related styles

A German pils is drier and more bitter, with Hallertau or Tettnang hops. Swap the Saaz for Hallertau and add 2 g more at 60 minutes if you want one.
