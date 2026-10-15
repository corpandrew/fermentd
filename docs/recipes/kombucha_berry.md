---
schema: fermentd.recipe/v1
id: kombucha_berry
category: kombucha
profile_id: kombucha_berry
batch_number: 1
name: Berry Kombucha
status: active
yield:
  volume_gal: 1
  bottle_fl_oz: 16
  bottle_count: 6-7
tracking_mode: timer
target_f: 75
pitch_below_f: 80
f1_days:
- 7
- 12
carbonation_window_h:
- 48
- 96
condition_f: 75
chill_before_open_h: 24
drink_within_days:
- 14
- 30
ph_start_max: 4.5
ingredients:
- id: water
  item: water, chlorine-free (filtered, or boiled and cooled)
  amount: 1 gallon (16 cups)
  amount_half: 1/2 gallon (8 cups)
- id: tea
  item: plain black tea bags
  amount: 8 bags (or 2 tbsp loose)
  amount_half: 4 bags (or 1 tbsp loose)
  note: no oils or flavors, such as Earl Grey
- id: sugar
  item: white sugar
  amount: 1 cup (200 g)
  amount_half: 1/2 cup (100 g)
  grams: 200
- id: starter
  item: starter liquid (unflavored kombucha from the last batch or the SCOBY bag)
  amount: 2 cups
  amount_half: 1 cup
  note: keeps the pH low and safe from day 0
- id: scoby
  item: SCOBY
  amount: '1'
  amount_half: '1'
  note: one SCOBY works for either size
- id: berries
  item: mashed berries (raspberry, blueberry, strawberry, or mixed; frozen is fine)
  amount: 1 1/2 cups
  amount_half: 3/4 cup
- id: f2sugar
  item: white sugar (optional)
  amount: 1 tbsp
  amount_half: 1/2 tbsp
  note: only if the berries are tart
optional:
- id: ph
  item: pH strips (2.5-4.5 range)
  amount: a few
  amount_half: a few
  note: for checking that the starting pH is 4.5 or lower
equipment:
- '1-gallon wide-mouth glass jar (half batch: a half-gallon jar)'
- tight-weave cotton cloth or coffee filters and a rubber band
- '6-7 swing-top bottles (16 oz) rated for carbonation (half batch: 3), plus one plastic tester bottle'
- funnel and fine strainer
- pH strips (recommended)
- hydrometer and test jar (optional, for tracking)
- seedling heat mat in the backpack cooler
safety:
- id: ph
  text: Always add the starter liquid. The starting pH must be 4.5 or lower; this is what keeps harmful bacteria out.
- id: mold
  text: Fuzzy, dry, green, black or white spots on top of the SCOBY are mold. Throw out the whole batch and the SCOBY.
- id: glass
  text: Flavored bottles can over-carbonate. Use a plastic tester and move bottles to the fridge when it is hard.
- id: temp
  text: Add starter and SCOBY only when the tea is below 80 F.
- id: metal
  text: Brew in glass. Avoid reactive metal containers; stainless utensils are fine.
steps:
- id: brew
  stage: day0
  profile_stage: f1
  text: Brew strong sweet tea, then top up with cold water.
- id: cool
  stage: day0
  profile_stage: f1
  text: Cool below 80 F, add the starter liquid and SCOBY, cover with cloth, and start the batch at 75 F.
- id: f1
  stage: ferment
  profile_stage: f1
  text: Ferment 7-12 days, tasting from day 7.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Reserve 2 cups with the SCOBY, add the flavorings, and bottle with a plastic tester.
- id: f2
  stage: package
  profile_stage: in_bottle
  text: Carbonate at about 72-75 F for 2-4 days.
- id: fridge
  stage: serve
  profile_stage: refrigerated
  text: Refrigerate when the tester is hard.
taste: Tart and fruity with berry color, lightly sweet and fizzy.
not_this_batch:
  id: kombucha_juice
  summary: Adding 100% fruit juice instead of whole fruit (about 1/4 cup per bottle) is a variation. It is not this batch.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 16
    bottle_count: '3'
reminders:
- id: taste
  at: stage:f1+7d
  repeat: 1d
  text: Taste a little from under the SCOBY with a clean straw. Bottle when it is pleasantly tart, not sweet and not vinegary.
- id: squeeze
  at: stage:in_bottle+48h
  repeat: 12h
  text: Squeeze the plastic tester bottle. Move every bottle to the fridge when it is firm to rock hard.
- id: refrigerate_now
  at: stage:in_bottle+72h
  repeat: 12h
  text: If the tester is hard, move all bottles to the fridge now. Do not leave flavored glass bottles warm.
- id: finish
  at: stage:refrigerated+14d
  text: Drink the kombucha within the next couple of weeks; open over the sink.
---


## Ingredients

Makes [[1 gallon, about 6-7 bottles of 16 oz after keeping 2 cups back for the next batch|a half gallon, about 3 bottles of 16 oz after keeping 1 cup back (a test batch)]]. Under about 1% alcohol.

**First ferment (sweet tea):**

- [[1 gallon (16 cups)|1/2 gallon (8 cups)]] water, chlorine-free (filtered, or boiled and cooled)
- [[8 bags (or 2 tbsp loose)|4 bags (or 1 tbsp loose)]] plain black tea bags (no oils or flavors, such as Earl Grey)
- [[1 cup (200 g)|1/2 cup (100 g)]] white sugar
- [[2 cups|1 cup]] starter liquid (unflavored kombucha from the last batch or the SCOBY bag) (keeps the pH low and safe from day 0)
- [[1|1]] SCOBY (one SCOBY works for either size)

**Second ferment (in the bottles):**

- [[1 1/2 cups|3/4 cup]] mashed berries (raspberry, blueberry, strawberry, or mixed; frozen is fine)
- [[1 tbsp|1/2 tbsp]] white sugar (optional) (only if the berries are tart)

**Berry.** About 3-4 tbsp mashed fruit per 16 oz bottle. Berries add sugar, color and fizz; the bottles turn pink to purple.

## Equipment

- [[1-gallon wide-mouth glass jar|**Half-gallon wide-mouth glass jar** (a half batch in the gallon jar is fine for this open ferment, but a smaller jar keeps the layer of liquid deep enough)]]
- Tight-weave cotton cloth or coffee filters and a rubber band (not cheesecloth; fruit flies get through)
- [[6-7|3]] swing-top bottles (16 oz) rated for carbonation, plus one plastic tester bottle
- Funnel and a fine strainer
- **pH strips** (recommended, 2.5-4.5 range)
- Hydrometer and test jar (optional: kombucha is judged by taste, but the gravity drops from about 1.020 to about 1.006-1.010 as it sours)
- Seedling heat mat in the backpack cooler

**Temperature.** Kombucha likes 75-80 F. fermentd holds 75 F, its maximum, so a cold winter room is not a problem. Colder than 70 F, kombucha gets slow and more prone to mold.

## Sanitation

Wash the jar, bottles and utensils in hot soapy water and rinse very well; soap residue harms the SCOBY. You can rinse the jar with a splash of distilled vinegar or starter liquid instead of Star San. Wash your hands before handling the SCOBY.

## Brew the sweet-tea base

About 30 minutes, plus cooling time.

1. Bring [[4 cups|2 cups]] of the water to a boil, turn off the heat, and steep the tea bags for 10 minutes. Remove the bags.
2. Stir in the sugar until it dissolves.
3. Pour the sweet tea into the jar and add the rest of the cold water, leaving about 2 inches at the top.
4. Check the temperature: it must be **below 80 F**.
5. Add the starter liquid and the SCOBY. If you have pH strips, check that the pH is **4.5 or lower**; if not, add more starter.
6. Cover with the cloth and rubber band. Put the jar in the cooler on the mat (lid off or cracked for airflow) and start the batch in fermentd. It starts in **First ferment** at 75 F.

## First ferment (F1)

### First 3 days

1. Do not move or stir the jar. A new, thin, clear-to-white layer forms on top within a few days; that is the new SCOBY.
2. Brown stringy bits hanging from the SCOBY and bubbles trapped under it are normal yeast.
3. A mild vinegar smell is normal. Check for mold: fuzzy, dry spots on top.

### Taste and decide, days 7-12

From day 7, fermentd reminds you daily to taste. Slide a clean straw under the SCOBY and taste. It is ready when it is **pleasantly tart with a little sweetness left**. Warmer and longer means more sour; it can turn to vinegar after about 3 weeks.

## Second ferment (F2): flavor and bottle

1. With clean hands, lift the SCOBY onto a clean plate. Keep **[[2 cups|1 cup]]** of the kombucha with it as starter for the next batch (store it covered at room temperature).
2. Put the flavorings into the bottles using a funnel (split evenly), then fill each bottle with kombucha through the strainer, leaving 1-2 inches of headspace. Fill the plastic tester the same way.
3. Close the bottles and press **Bottled**. Keep them in the cooler at 72-75 F.

## Carbonation check and refrigerate

From about 48 hours, fermentd reminds you to squeeze the plastic tester. When it is **firm to rock hard** (usually 2-4 days), move every bottle to the fridge and press **Move bottles to the fridge**. Chill 24 hours, then open over the sink; fruit and ginger bottles can foam. Strain out the fruit or ginger as you pour.

## SCOBY care

**Getting a SCOBY.** Ask a friend, buy one online with its starter liquid, or grow one from a bottle of raw, unflavored store kombucha (pour it into a jar with a cup of cooled sweet tea and wait 2-4 weeks). A SCOBY does not need halving for a half batch.

- **Keep a SCOBY hotel.** Put spare SCOBYs in a jar with enough plain kombucha to cover them, cover with a cloth, and keep it at room temperature. Top it up with sweet tea every 4-6 weeks. It is also your backup if a batch gets mold.
- **Every batch makes a new layer.** Peel off and give away or compost the oldest layers once the SCOBY is more than about an inch thick.
- **Never refrigerate a SCOBY** you plan to brew with; cold makes it sluggish and prone to mold.
- **Healthy looks:** cream to tan, rubbery, with brown yeast strings. Holes, bumps and dark spots underneath are fine. Fuzz on top is not.

## Safety

- **Always add the starter liquid.** It keeps the starting pH at 4.5 or lower, which keeps harmful bacteria out.
- **Mold** (fuzzy, dry, green, black or white spots on top) means the whole batch and SCOBY go in the trash. Do not try to save it.
- Flavored second ferments carbonate fast. Always bottle a plastic tester and move every bottle to the fridge once it is hard.
- Add the starter and SCOBY only below 80 F.
- Brew in glass, not reactive metal. People who are pregnant, immunocompromised or sensitive to alcohol should check with a doctor; kombucha contains a little alcohol and live cultures.

## Troubleshooting

- **No new SCOBY layer after a week.** It may be too cold or too little starter. Keep it at 75 F and be patient; the tea still ferments.
- **Too sweet after 12 days.** Too cold or a weak SCOBY. Give it a few more days.
- **Too vinegary.** It went too long. Use it as starter or salad vinegar, and bottle sooner next time.
- **Flat bottles.** Add 1 tsp sugar per bottle next time, make sure the swing-top gaskets seal, and leave them warm a day longer.
- **Fruit flies.** The cloth is too loose or too thin. Use a tighter weave or coffee filters.

## Taste

Tart and fruity with berry color, lightly sweet and fizzy.

## Related styles

Adding 100% fruit juice instead of whole fruit (about 1/4 cup per bottle) is a variation. It is not this batch.
