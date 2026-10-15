---
schema: fermentd.recipe/v1
id: wine_blackberry
category: wine
profile_id: wine_blackberry
batch_number: 1
name: Blackberry Country Wine
status: active
yield:
  volume_gal: 1
  bottle_fl_oz: 25
  bottle_count: 4-5
tracking_mode: timer
target_f: 66
pitch_below_f: 80
og_target:
- 1.085
- 1.095
fg_target:
- 0.99
- 0.998
abv_expected:
- 11.0
- 13.0
primary_weeks:
- 3
- 5
aging_months:
- 3
- 6
carbonation_window_h:
- 0
- 0
chill_before_open_h: 0
drink_within_days:
- 180
- 730
ingredients:
- id: fruit
  item: blackberries, fresh or frozen
  amount: 3-4 lb
  amount_half: 1.5-2 lb
  note: frozen fruit releases juice better; thaw first. Strawberries, raspberries, or mixed berries work the same way
- id: sugar
  item: white sugar
  amount: 2 lb (900 g, about 4 1/2 cups)
  amount_half: 1 lb (450 g, about 2 1/4 cups)
  grams: 900
  note: add 3/4 first, then adjust to the OG target
- id: water
  item: water
  amount: to make 1 gallon
  amount_half: to make 1/2 gallon
  note: chlorine-free or boiled and cooled
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
- id: campden
  item: Campden tablet, crushed
  amount: '1'
  amount_half: 1/2
  note: day 0, then 12-24 hours before pitching
- id: yeast
  item: Lalvin 71B or EC-1118 wine yeast
  amount: 1-2 g (1/4-1/2 packet)
  amount_half: about 1 g; yeast does not need exact halving
  note: 71B keeps more fruit; EC-1118 finishes drier
optional:
- id: acid
  item: acid blend
  amount: up to 1/2 tsp
  amount_half: up to 1/4 tsp
  note: only for strawberries or sweet, low-acid fruit
- id: sorbate
  item: potassium sorbate
  amount: 1/2 tsp
  amount_half: 1/4 tsp
  note: only if sweetening at bottling
equipment:
- '2-gallon food-grade bucket with a lid and airlock grommet (half batch: a 1-gallon bucket or wide jar)'
- fine nylon straining bag
- '1-gallon glass jug with bung and airlock (half batch: a half-gallon jug or growler)'
- a second clean jug for racking
- hydrometer and test jar (needed)
- auto-siphon and tubing
- funnel and strainer
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
  profile_stage: must
  text: Sanitize the bucket, straining bag, spoon, hydrometer and test jar.
- id: mash
  stage: day0
  profile_stage: must
  text: Crush the fruit in the bag in the bucket, add the water and 3/4 of the sugar, and stir in the Campden tablet.
- id: wait
  stage: day0
  profile_stage: must
  text: Cover and wait 12 hours, then add pectic enzyme and wait 12 more.
- id: pitch
  stage: day0
  profile_stage: must
  text: Adjust to OG 1.085-1.095, add nutrient and tannin, pitch the yeast, and start the batch in fermentd at 66 F.
- id: on_fruit
  stage: ferment
  profile_stage: must
  text: Press the fruit bag down daily for 5-7 days.
- id: strain
  stage: ferment
  profile_stage: secondary
  text: Lift out the bag, siphon into the jug under airlock, and ferment dry over 2-4 weeks.
- id: age
  stage: ferment
  profile_stage: aging
  text: Rack off sediment every 1-2 months and age 3-6 months, topped up.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Bottle still when dry and clear, stabilizing first if sweetening.
- id: cellar
  stage: serve
  profile_stage: cellared
  text: Age in bottles; best from about 6-12 months after starting.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 25
    bottle_count: '2'
taste: Deep purple-red, dry to off-dry, with jammy blackberry fruit and a light tannic grip, about 11-13% ABV.
not_this_batch:
  id: wine_port_style
  summary: A fortified, port-style blackberry wine needs high gravity and spirits added. It is not this batch.
reminders:
- id: punch
  at: stage:must+1d
  repeat: 1d
  text: Open the bucket, push the fruit bag under and squeeze it gently with sanitized hands or a spoon. Do this daily while on fruit.
- id: strain
  at: stage:must+5d
  text: After 5-7 days on fruit, lift out the bag, let it drain without hard squeezing, and siphon the wine into the jug under an airlock.
- id: gravity
  at: stage:secondary+14d
  repeat: 7d
  text: Take a gravity reading. Rack off the sediment once it is 0.998 or lower and the same on 3 readings over 3 days.
- id: rack
  at: stage:aging+30d
  repeat: 45d
  text: Rack off any new sediment into a clean jug, add 1/4 crushed Campden tablet per gallon every other racking, and top up to the neck.
- id: bottle_ready
  at: stage:aging+90d
  repeat: 30d
  text: Bottle when it is clear and has dropped no sediment for a month. It keeps improving in the bottle.
- id: cellar
  at: stage:cellared+90d
  text: Try a bottle. Fruit wine is usually best from 6 to 12 months after starting.
---


## Ingredients

Makes [[1 gallon, about 4-5 wine bottles (or 9-10 bottles of 12 oz)|a half gallon, about 2 wine bottles (or 5 bottles of 12 oz), a test batch]]. OG 1.085-1.095, about 11-13% ABV, still (not sparkling).

- [[3-4 lb|1.5-2 lb]] blackberries, fresh or frozen (thaw frozen fruit first)
- [[2 lb (900 g, about 4 1/2 cups)|1 lb (450 g, about 2 1/4 cups)]] white sugar
- Water to make [[1 gallon|1/2 gallon]] (chlorine-free, or boiled and cooled)
- [[1/2 tsp|1/4 tsp]] pectic enzyme
- [[1 tsp|1/2 tsp]] yeast nutrient
- [[1/8 tsp|a pinch]] wine tannin
- [[1|1/2]] Campden tablet, crushed
- Lalvin 71B or EC-1118 wine yeast, [[1-2 g|about 1 g]]
- Optional: up to [[1/2 tsp|1/4 tsp]] acid blend for strawberries or other sweet fruit; [[1/2 tsp|1/4 tsp]] potassium sorbate if you sweeten at bottling

**Country wine.** "Country wine" means a wine from fruit other than grapes. Blackberries are ideal: lots of color, acid and tannin of their own. **Strawberry** works with the same amounts, plus up to [[1/2 tsp|1/4 tsp]] acid blend and the full tannin; its color fades to pink-amber, which is normal. **Raspberry** or a mixed bag of frozen berries also work. Each 1/4 cup of sugar raises a gallon by about 0.010.

**Yeast.** Use [[1/4-1/2 of a 5 g packet (1-2 g)|about 1/4 of a 5 g packet (about 1 g)]]. A wine yeast packet is sized for up to 5 gallons. **Yeast does not need exact halving** for a half batch; a little extra does no harm. Rehydrate it in 1/4 cup lukewarm (95-100 F) water for 15 minutes before pitching.

## Equipment

- [[2-gallon food-grade bucket|1-gallon food-grade bucket or wide-mouth jar]] with a lid and airlock grommet, for the first week on fruit
- Fine nylon straining bag
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

## Fruit maceration and must prep

About 30 minutes today, then two short waits.

1. Sanitize the bucket, straining bag, spoon, hydrometer and test jar.
2. Put the fruit in the straining bag in the bucket and crush it well with clean hands or a potato masher.
3. Dissolve [[3/4 of the sugar (about 1 1/2 lb)|3/4 of the sugar (about 3/4 lb)]] in [[a quart|2 cups]] of hot water, add it, and top up with cool water to [[1 gallon|1/2 gallon]] of total volume.
4. Stir in the crushed Campden tablet. Cover with the lid (airlock fitted) and wait **12 hours**.
5. Stir in the pectic enzyme and wait **12 more hours**. (Campden first, enzyme later: the sulfite slows the enzyme.)
6. Read the gravity. Add the rest of the sugar a little at a time until it reads **1.085-1.095**.
7. Stir in the nutrient and tannin. Rehydrate the yeast for 15 minutes and pitch it below 80 F.
8. Close the lid, put the bucket in the cooler on the mat, and start the batch in fermentd. It starts on **Fruit in primary** at 66 F.

## On fruit

### First 3 days

1. Bubbling starts within 24-48 hours.
2. Once a day, open the lid and press the fruit bag under the liquid with a sanitized spoon, then close it. This keeps the fruit cap from drying out and spoiling and pulls out color. fermentd reminds you daily.
3. A fruity, yeasty smell is normal. A strong rotten-egg smell means it wants more nutrient; see Troubleshooting.

### Lift out the fruit, day 5-7

After 5-7 days, lift the bag out and let it drain into the bucket for a few minutes. A gentle squeeze is fine; squeezing hard adds bitter tannin.

## Rack and finish dry

1. Siphon the wine into the sanitized jug, leaving the thick sediment behind, and fit the airlock. Fill to the shoulder for now; it may still foam.
2. Press **Clearing in secondary**.
3. From day 14 fermentd reminds you weekly to take a gravity reading. It is done when it reads **0.998 or lower and the same on 3 readings over 3 days**.

## Rack, clear and age

1. Rack into the clean jug, off the sediment, and top up into the neck with a little water or a similar wine. Press **Start aging**.
2. Every 1-2 months, rack again off any new sediment. Add [[1/4|1/8]] crushed Campden tablet every other racking to protect it.
3. It is ready to bottle when it is clear and drops no new sediment for a month. Aging can happen anywhere cool and dark, off the heat mat, which frees the cooler for another batch.

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

Deep purple-red, dry to off-dry, with jammy blackberry fruit and a light tannic grip, about 11-13% ABV.

## Related styles

A fortified, port-style blackberry wine needs high gravity and spirits added. It is not this batch.
