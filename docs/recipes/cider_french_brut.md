---
schema: fermentd.recipe/v1
id: cider_french_brut
category: cider
profile_id: cider_french_brut
batch_number: 1
name: French-Style Brut Cider
status: active
yield:
  volume_gal: 1
  bottle_fl_oz: 12
  bottle_count: "9-10"
tracking_mode: timer
target_f: 62
pitch_below_f: 75
og_target: [1.045, 1.055]
fg_target: [0.996, 1.000]
abv_expected: [5.5, 7.0]
primary_weeks: [2, 4]
secondary_weeks: [2, 4]
bottle_condition_weeks: [2, 3]
priming:
  target_vol: [2.5, 2.8]
  table_sugar_g: 25
  corn_sugar_g: 28
carbonation_window_h: [336, 504]
chill_before_open_h: 24
drink_within_days: [30, 365]
ingredients:
  - id: juice
    item: apple juice or cider, unpasteurized or preservative-free
    amount: 1 gallon
    amount_half: 1/2 gallon (64 fl oz)
    note: no potassium sorbate or sodium benzoate on the label; UV-treated or pasteurized is fine
  - id: tannin
    item: wine tannin powder
    amount: 1/8-1/4 tsp
    amount_half: a pinch to 1/8 tsp
    note: or 1 cup of strong black tea (2 bags steeped 5 minutes), cooled
  - id: nutrient
    item: yeast nutrient
    amount: 1/2 tsp
    amount_half: 1/4 tsp
    note: helps prevent sulfur smells
  - id: priming
    item: table sugar for priming
    amount: 25 g (2 tbsp)
    amount_half: 12 g (1 tbsp)
    grams: 25
    note: at bottling only; or 28 g corn sugar
  - id: yeast
    item: EC-1118 yeast
    amount: 1/4 tsp (about 1 g)
    amount_half: 1/4 tsp (about 1 g); yeast does not need halving
    note: or a cider yeast such as a French-style cider strain; rehydrate in 1/4 cup lukewarm water for 15 minutes
optional:
  - id: malic
    item: malic acid
    amount: 1/4 tsp, to taste
    note: only if the juice tastes flat and sweet
  - id: sugar
    item: white sugar
    amount: up to 1/4 cup
    note: only to raise a low OG; each 1/4 cup adds about 0.005
  - id: campden
    item: Campden tablet
    amount: 1
    note: fresh-pressed juice only, crushed, then wait 24 hours before pitching
equipment:
  - 1-gallon jug fermenter with bung and airlock
  - a second clean 1-gallon jug for secondary
  - hydrometer and test jar (needed)
  - auto-siphon and tubing with a bottle filler
  - funnel and strainer
  - Star San and a spray bottle
  - thermometer
  - 9-10 heavy 12 oz bottles (swing-top or crown-capped) and one plastic tester bottle
  - kitchen scale for the priming sugar
  - seedling heat mat in the backpack cooler
safety:
  - id: stable
    text: Prime only fully finished cider, with the same gravity (1.000 or lower) on 3 readings over 3 days.
  - id: glass
    text: Use heavy bottles rated for carbonation. Over-primed or unfinished cider can burst glass.
  - id: tester
    text: Bottle one plastic tester and move all bottles to cool storage once it is rock hard.
  - id: pitch
    text: Pitch below 75 F.
  - id: sorbate
    text: Juice with sorbate or benzoate will not ferment reliably. Check the label.
steps:
  - id: sanitize
    stage: day0
    profile_stage: primary
    text: Sanitize the jug, bung, airlock, funnel, hydrometer, and test jar.
  - id: og
    stage: day0
    profile_stage: primary
    text: Take an original gravity reading. Aim for 1.045-1.055.
  - id: adjust
    stage: day0
    profile_stage: primary
    text: Add tannin and nutrient, adjust acid and sugar if needed, and fill the jug to the shoulder.
  - id: pitch
    stage: day0
    profile_stage: primary
    text: Pitch the rehydrated yeast, fit the airlock, and start the batch in fermentd at 62 F.
  - id: primary
    stage: ferment
    profile_stage: primary
    text: Ferment 2-4 weeks until the gravity is 1.000 or lower and stable for 3 days.
  - id: rack
    stage: ferment
    profile_stage: secondary
    text: Rack into the clean jug, top up to the shoulder, and clear for 2-4 weeks.
  - id: bottle
    stage: package
    profile_stage: bottle
    text: Confirm stable gravity, dissolve 25 g table sugar in a little boiled water, rack onto it, and bottle with 1 inch of headspace plus one plastic tester.
  - id: condition
    stage: package
    profile_stage: bottle_condition
    text: Condition about 2-3 weeks at room temperature until the tester is rock hard.
  - id: cellar
    stage: serve
    profile_stage: cellared
    text: Store cool and dark. Chill at least 24 hours before opening.
reminders:
  - id: airlock
    at: stage:primary+2d
    text: Check that the airlock is bubbling and the cider smells fruity. A faint sulfur smell is normal in the first week.
  - id: gravity
    at: stage:primary+14d
    repeat: 3d
    text: Take a hydrometer reading. Rack once it is 1.000 or lower and the same on 3 readings over 3 days.
  - id: rack
    at: stage:primary+21d
    text: If the gravity is stable at 1.000 or lower, rack off the sediment into the clean jug and fit the airlock.
  - id: clear_check
    at: stage:secondary+14d
    repeat: 7d
    text: Check clarity and gravity. Bottle only when it is clear-ish and the gravity is unchanged for 3 days.
  - id: age_taste
    at: stage:aging+30d
    repeat: 30d
    text: Taste a sample. Bottle when you like it; dry cider softens with a few months of aging.
  - id: tester
    at: stage:bottle_condition+7d
    repeat: 2d
    text: Squeeze the plastic tester bottle. Bottle conditioning is done when it is rock hard.
  - id: condition_done
    at: stage:bottle_condition+14d
    repeat: 3d
    text: If the tester is rock hard, move the bottles to cool storage or the fridge. Do not leave glass warm once carbonated.
  - id: cellar
    at: stage:cellared+30d
    text: The cider keeps improving for a few months in a cool, dark place. Chill before opening.
taste: Bone dry, crisp, and lightly tannic with fine bubbles, about 5.5-7% ABV.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 12
    bottle_count: "5"
  priming:
    target_vol: [2.5, 2.8]
    table_sugar_g: 12
    corn_sugar_g: 14
not_this_batch:
  id: cider_keeved
  summary: A true keeved cidre doux stays naturally sweet and needs fresh-pressed juice and cold cellar temperatures. See the advanced section; it is not the default batch.
---


## Ingredients

Makes [[1 gallon, about 9-10 bottles of 12 oz|a half gallon, about 5 bottles of 12 oz (a test batch)]]. Expect 5.5-7% ABV.

- [[1 gallon|1/2 gallon (64 fl oz)]] apple juice or sweet cider, **unpasteurized fresh-pressed if you can get it**, otherwise store-bought juice with **no potassium sorbate or sodium benzoate** on the label (UV-treated or pasteurized is fine)
- [[1/8-1/4 tsp|a pinch to 1/8 tsp]] wine tannin powder, or [[1 cup|1/2 cup]] strong black tea ([[2 bags|1 bag]] steeped 5 minutes, cooled)
- [[1/2 tsp|1/4 tsp]] yeast nutrient
- 1/4 tsp (about 1 g) EC-1118 champagne yeast, or a French-style cider yeast
- [[25 g (2 tbsp)|12 g (1 tbsp)]] table sugar for priming at bottling, or [[28 g|14 g]] corn sugar
- Optional: [[1/4 tsp|1/8 tsp]] malic acid if the juice tastes flat; up to [[1/4 cup|2 tbsp]] sugar to raise a low gravity; [[1 Campden tablet|1/2 Campden tablet]] for fresh-pressed juice

**Why French cider tastes the way it does.** Norman and Breton ciders are made from bittersweet and bittersharp apples (Bisquet, Kermerrien, Dabinett-type fruit) that bring tannin and body that dessert-apple juice lacks. You cannot buy those as juice in most places, so this recipe adds tannin and balances acid instead. If an orchard near you sells a cider blend with some crab or "cider" apples, use it.

**Gravity target.** Aim for an original gravity of 1.045-1.055. Most store juice lands around 1.045-1.050. Each 1/4 cup of sugar raises a gallon by about 0.005 (2 tbsp does the same for a half gallon); do not go above 1.060 for this style.

**Yeast.** EC-1118 ferments clean and completely dry, which is exactly what a brut wants, and you already own it. A dedicated cider yeast keeps a little more apple aroma. Either is fine. A 5 g packet is meant for up to 5 gallons, so use about a quarter of it. **Do not halve the yeast for a half-gallon batch**: 1/4 tsp is already a tiny amount, and a little extra yeast does no harm.

## Equipment

- [[1-gallon jug|**Half-gallon glass jug or growler**]] fermenter with bung and airlock[[|. A half batch in the 1-gallon jug leaves too much air on top; use a half-gallon jug that takes your stopper size (about $5-8)]]
- A second clean [[1-gallon|half-gallon]] jug for secondary (or rinse and re-sanitize the first while the cider sits in a sanitized pot, covered)
- **Hydrometer and test jar** (you need these; buy one if you do not have it)
- Auto-siphon and tubing, bottle filler
- Funnel and strainer
- Star San and a spray bottle
- Thermometer
- [[9-10|5]] heavy 12 oz bottles (swing-top or crown-capped) rated for carbonation, plus one plastic tester bottle
- Kitchen scale for the priming sugar
- Seedling heat mat in the backpack cooler

**Temperature, with a heat-only rig.** Cool, slow fermentation at about 60-62 F keeps the apple aroma that makes French cider. The heat mat can only *add* heat, so fermentd holds a floor (62 F by default) and the room does the rest. Put the backpack cooler in the coolest spot you have, around 60-64 F in the fall, so the mat only switches on to stop the temperature dipping at night. If the room runs warm, the cider will ferment faster and a little less aromatic; that is still fine.

## Sanitation

Mix Star San at about 1.5 tsp per gallon of water. Sanitize everything that touches the juice after it leaves its container: jug, bung, airlock, funnel, hydrometer and test jar, wine thief or siphon, and later the bottles and swing-top gaskets. Let it drain; do not rinse. Fill the airlock with Star San solution or cheap vodka.

## Juice prep and pitch

About 30 minutes, plus 15 minutes to rehydrate the yeast.

1. Let the juice reach room temperature (below 75 F). Sanitize the jug, bung, airlock, funnel, hydrometer, and test jar.
2. **Fresh-pressed juice only (optional):** stir in [[1 crushed Campden tablet|1/2 crushed Campden tablet]], cover with a sanitized cloth, and wait 24 hours before continuing.
3. Rehydrate the yeast: sprinkle 1/4 tsp EC-1118 into 1/4 cup lukewarm water (about 95-100 F) and let it stand 15 minutes.
4. Pour a little juice into the test jar and read the original gravity (OG). Write it down. Aim for 1.045-1.055; add up to [[1/4 cup|2 tbsp]] sugar dissolved in a little juice if it is low.
5. Stir the tannin and the yeast nutrient into a cup of juice until dissolved, then add it to the jug. Taste: if the juice is flat and sweet, stir in up to [[1/4 tsp|1/8 tsp]] malic acid.
6. Fill the jug to the shoulder, leaving room for foam. Pour in the yeast.
7. Fit the bung and airlock. Put the jug in the cooler on the heat mat and start the batch in fermentd. It starts in **Primary** at 62 F.

## Primary

### First 3 days

1. Bubbling in the airlock usually starts within 24-48 hours. fermentd reminds you on day 2 to check.
2. A faint rotten-egg (sulfur) smell in the first week is common with apple juice and usually blows off. See Troubleshooting if it lingers.
3. If foam reaches the airlock, remove it, rinse and re-sanitize it, wipe the neck, and refit it.

### Until dry, 2-4 weeks

Leave it alone at about 62 F. From day 14, fermentd reminds you every 3 days to take a gravity reading. Primary is done when the gravity is **1.000 or lower and the same on 3 readings over 3 days**. Brut cider usually finishes around 0.996-1.000.

ABV is roughly (OG - FG) x 131. For example, 1.050 to 0.998 is about 6.8%.

## Rack and clear

1. Sanitize the second jug, the siphon, and the airlock.
2. Siphon the cider off the yeast sediment into the clean jug, leaving the last half inch behind. Avoid splashing.
3. Top up to the shoulder if needed with a little more of the same juice, fit the airlock, and press **Racked to secondary** on the dashboard.
4. Let it clear for 2-4 weeks. It does not need to be crystal clear.

## Age (optional)

Dry cider softens with time. You can press **Start aging** and leave it under airlock for 1-3 months, tasting monthly. Keep the jug full to the shoulder to limit air contact.

## Bottle

Only bottle when the gravity is unchanged for 3 days. The target is about 2.5-2.8 volumes of CO2, lively but safe in heavy swing-tops.

1. Sanitize the bottling vessel (a clean pot works), siphon, bottle filler, [[9-10|5]] bottles (and gaskets or caps), and the plastic tester.
2. Weigh **[[25 g|12 g]] table sugar** (or [[28 g|14 g]] corn sugar). Dissolve it in [[1/4 cup|2 tbsp]] boiling water and let it cool a little.
3. Pour the sugar solution into the bottling vessel and siphon the cider onto it, leaving the sediment behind. Stir gently.
4. Fill the bottles with the bottle filler, leaving about 1 inch of headspace. Fill the plastic tester the same way, squeeze out the air, and cap it.
5. Press **Bottled, start conditioning** on the dashboard.

## Condition in the bottle

The yeast eats the priming sugar and carbonates the bottles. Ideally this happens at 65-68 F; in a 62-64 F room it takes closer to 3 weeks. EC-1118 has no trouble at either temperature.

1. Keep the bottles in the closed cooler.
2. fermentd reminds you from day 7 to squeeze the plastic tester. When it is **rock hard**, conditioning is done.
3. Move the bottles to cool storage (a basement or the fridge) and press **Conditioning done, move to cool storage**.

## Serve

Chill at least 24 hours before opening. Open over the sink and pour gently, leaving the yeast in the bottle. Serve in a wide glass or a traditional bolée. The cider keeps for a year in a cool, dark place and usually tastes best after 2-6 months.

**Want it less dry?** Because the bottles are carbonated by fermentation, any sugar added at bottling will also ferment. To sweeten, use only a non-fermentable sweetener such as erythritol, stevia, or xylitol (keep xylitol away from dogs), dissolved into the cider with the priming sugar. Do not back-sweeten with sugar or juice.

## Keeving (advanced, optional)

Keeving is how Normandy makes naturally sweet, low-alcohol cidre doux. It is **advanced and not the default batch**. It only works with **fresh-pressed, unpasteurized, untreated juice**, and it really wants cold cellar temperatures (around 40-50 F), which this heat-only rig cannot provide.

1. To the fresh juice, add pectin methyl esterase (PME) and calcium chloride at the dose on the product label (roughly 1/8 tsp calcium chloride per gallon).
2. Within a day or two, pectin gels with the calcium and rises as a brown cap (the *chapeau brun*), stripping out nutrients. A clear juice forms underneath.
3. Rack the clear juice from between the cap and the sediment into a clean jug, without the cap.
4. Let it ferment very slowly with wild or a low-attenuating yeast, racking again whenever it drops a heavy sediment, and bottle while some sweetness remains. With so few nutrients, the yeast struggles to finish, which keeps it sweet.

Without cold temperatures and real cider apples it often fails, so try the brut recipe first.

## Safety

- **Prime only fully finished cider:** the gravity must be 1.000 or lower and unchanged on 3 readings over 3 days. Priming cider that is still fermenting is how bottles burst.
- Use heavy swing-top bottles rated for carbonated drinks, weigh the priming sugar, and do not add more than 25 g table sugar per gallon (12 g per half gallon).
- Always bottle a plastic tester. Once it is rock hard, move all the bottles to cool storage; do not leave carbonated glass warm.
- Pitch below 75 F.
- Juice with potassium sorbate or sodium benzoate will not ferment reliably. Read the label.

## Troubleshooting

- **Rotten-egg or sulfur smell.** Common with apple juice, which is low in nitrogen. Make sure you added yeast nutrient; you can add another [[1/4 tsp|1/8 tsp]] in the first week. Gently swirl the jug to release gas. It almost always fades by the end of primary. If it is still there at racking, splash-rack once into the clean jug.
- **No bubbles after 3 days.** Check the bung seals; the airlock may be leaking around it. Confirm the juice has no preservatives. Check the gravity: if it has dropped, it is fermenting. If not, make sure the cooler is at least 60 F and pitch fresh rehydrated yeast.
- **Stuck above 1.005.** Swirl to rouse the yeast, keep it at 62-64 F, and add 1/4 tsp nutrient. If it still does not move in a week, pitch fresh rehydrated EC-1118.
- **Too sour or sharp.** Mostly from high-acid juice. It softens with aging. Next time skip the malic acid, or blend in a sweeter, lower-acid juice. Do not try to fix it with sugar at bottling.
- **Thin or watery.** Add the full 1/4 tsp tannin next time, or try a juice blend with some cider or crab apples.
- **Flat after 3 weeks.** It may need more time in a cool room; move it somewhere 65-68 F for a week. Check the swing-top gaskets.
- **Gushing.** It was primed before it finished, or with too much sugar. Chill all the bottles well, open them over the sink, and drink them soon.

## Taste

Bone dry, crisp, and lightly tannic with fine bubbles, about 5.5-7% ABV. Drier and leaner than a sweet Normandy cidre, closer to a cidre brut.

## Related styles

A naturally sweet keeved cidre doux needs fresh-pressed juice and cold cellar temperatures. See the advanced section above; it is not the default batch (`cider_keeved`).
