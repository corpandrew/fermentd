---
schema: fermentd.recipe/v1
id: water_kefir_lemon
category: water_kefir
profile_id: water_kefir_lemon
batch_number: 1
name: Lemon Water Kefir
status: active
yield:
  volume_gal: 1
  bottle_fl_oz: 16
  bottle_count: '7'
tracking_mode: timer
target_f: 74
pitch_below_f: 80
f1_hours:
- 24
- 48
carbonation_window_h:
- 12
- 48
condition_f: 74
chill_before_open_h: 12
drink_within_days:
- 7
- 14
ingredients:
- id: water
  item: water, chlorine-free (spring or filtered; not distilled)
  amount: 1 gallon (16 cups)
  amount_half: 1/2 gallon (8 cups)
- id: sugar
  item: sugar (white, or half white and half raw/turbinado)
  amount: 1 cup (200 g)
  amount_half: 1/2 cup (100 g)
  grams: 200
- id: grains
  item: hydrated water kefir grains
  amount: 1 cup
  amount_half: 1/2 cup
  note: about 1/4 cup per quart; they multiply over weeks
- id: fig
  item: dried unsulfured fig (or 1 tbsp raisins)
  amount: '1'
  amount_half: 1/2
  note: minerals and food for the grains
- id: minerals
  item: pinch of baking soda or a few drops of trace minerals
  amount: a pinch
  amount_half: a small pinch
  note: only for soft or filtered water
- id: lemon_slices
  item: lemon slices, in the first ferment
  amount: 2 slices
  amount_half: 1 slice
- id: lemon
  item: fresh lemon juice
  amount: 1/3 cup (2 lemons)
  amount_half: 3 tbsp (1 lemon)
- id: f2sugar
  item: white sugar
  amount: 2 tbsp
  amount_half: 1 tbsp
  note: split between the bottles, for fizz
optional: []
equipment:
- '1-gallon glass jar or jug (half batch: a half-gallon jar)'
- plastic or stainless fine strainer
- cloth or loose lid
- '7 swing-top bottles (16 oz) rated for carbonation (half batch: 3-4), plus one plastic tester bottle'
- funnel
- hydrometer and test jar (optional)
- seedling heat mat in the backpack cooler
safety:
- id: glass
  text: Fruit second ferments carbonate in hours. Bottle a plastic tester and move bottles to the fridge when it is hard.
- id: temp
  text: Add the grains only when the sugar water is below 80 F.
- id: spoiled
  text: Slimy, foul-smelling or moldy grains mean the batch and grains go in the trash.
steps:
- id: sugar
  stage: day0
  profile_stage: f1
  text: Dissolve the sugar in a little hot water, then top up with cool water.
- id: grains
  stage: day0
  profile_stage: f1
  text: Below 80 F, add the grains, fig and minerals, cover, and start the batch at 74 F.
- id: f1
  stage: ferment
  profile_stage: f1
  text: Ferment 24-48 hours, tasting from 24 hours.
- id: bottle
  stage: package
  profile_stage: bottle
  text: Strain out the grains, add the flavoring, and bottle with a plastic tester.
- id: f2
  stage: package
  profile_stage: in_bottle
  text: Carbonate 12-48 hours at about 74 F.
- id: fridge
  stage: serve
  profile_stage: refrigerated
  text: Refrigerate when the tester is hard.
taste: Light, lemony and lightly sweet, like a gentle natural lemon soda.
not_this_batch:
  id: milk_kefir
  summary: Milk kefir uses different grains and milk. It is not this batch.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 16
    bottle_count: 3-4
reminders:
- id: taste
  at: stage:f1+24h
  repeat: 12h
  text: Taste the water kefir. Strain out the grains when it is only lightly sweet, usually 24-48 hours. Do not go past 72 hours.
- id: squeeze
  at: stage:in_bottle+12h
  repeat: 6h
  text: Squeeze the plastic tester bottle. Move every bottle to the fridge when it is firm to rock hard.
- id: refrigerate_now
  at: stage:in_bottle+48h
  repeat: 6h
  text: If the tester is hard, move all bottles to the fridge now. Do not leave fruit-flavored glass bottles warm.
- id: finish
  at: stage:refrigerated+7d
  text: Drink the water kefir within the next week or so.
---


## Ingredients

Makes [[1 gallon, about 7 bottles of 16 oz|a half gallon, about 3-4 bottles of 16 oz (a test batch)]]. Usually under 1% alcohol.

**First ferment (sugar water):**

- [[1 gallon (16 cups)|1/2 gallon (8 cups)]] water, chlorine-free (spring or filtered; not distilled)
- [[1 cup (200 g)|1/2 cup (100 g)]] sugar (white, or half white and half raw/turbinado)
- [[1 cup|1/2 cup]] hydrated water kefir grains (about 1/4 cup per quart; they multiply over weeks)
- [[1|1/2]] dried unsulfured fig (or 1 tbsp raisins) (minerals and food for the grains)
- [[a pinch|a small pinch]] pinch of baking soda or a few drops of trace minerals (only for soft or filtered water)
- [[2 slices|1 slice]] lemon slices, in the first ferment

**Second ferment (in the bottles):**

- [[1/3 cup (2 lemons)|3 tbsp (1 lemon)]] fresh lemon juice
- [[2 tbsp|1 tbsp]] white sugar (split between the bottles, for fizz)

**Plain lemon.** The classic: a fig and lemon slice in the first ferment, a little lemon juice and sugar in the bottles. Light, tangy and like a natural lemon soda.

## Equipment

- [[1-gallon glass jar or jug|**Half-gallon glass jar**]]
- Plastic or stainless fine strainer (avoid reactive metals such as aluminum)
- A cloth or loose lid
- [[7|3-4]] swing-top bottles (16 oz) rated for carbonation, plus one plastic tester bottle
- Funnel
- Hydrometer and test jar (optional: the sugar water starts near 1.020 and is ready around 1.008-1.012; taste works just as well)
- Seedling heat mat in the backpack cooler

**Temperature.** Water kefir likes 68-78 F. fermentd holds 74 F, so it works all winter. Below about 65 F it gets slow and the grains can sulk.

## Sanitation

Wash the jar, strainer and bottles in hot soapy water and rinse very well. Rinse with plain water, not sanitizer, right before touching the grains. Wash your hands.

## Brew the sugar-water base

About 15 minutes, plus cooling.

1. Dissolve the sugar in [[2 cups|1 cup]] of hot water in the jar.
2. Add the rest of the cool water. Check that it is **below 80 F**.
3. Add the grains, the fig and the minerals (if your water is soft or filtered). Add the lemon slices too.
4. Cover with a cloth or a loose lid. Put it in the cooler on the mat and start the batch in fermentd. It starts in **First ferment** at 74 F.

## First ferment (F1)

1. From 24 hours, fermentd reminds you to taste it twice a day. It is ready when it is **only lightly sweet** and a little tangy, usually 24-48 hours. Do not leave the grains in sugar water past 72 hours; they starve.
2. Strain out the grains into a clean jar. Start the next batch with fresh sugar water right away, or rest them in the fridge in sugar water for up to a week.
3. Remove the fig and lemon.

## Second ferment (F2): flavor and bottle

1. Split the flavorings between the bottles using a funnel.
2. Fill the bottles with the strained water kefir, leaving 1-2 inches of headspace. Fill the plastic tester the same way.
3. Close them and press **Bottled**. Keep them in the cooler at about 74 F.

## Carbonation check and refrigerate

Fruit-juice second ferments are **fast**. From 12 hours, fermentd reminds you every 6 hours to squeeze the tester. When it is firm to rock hard, move every bottle to the fridge and press **Move bottles to the fridge**. Chill at least 12 hours and open over the sink.

## Grain care

**Grains.** Water kefir grains are a different culture from milk kefir grains; do not swap them. You need about 1/4 cup of hydrated grains per quart, so [[1 cup for a gallon|1/2 cup for a half gallon]]. If you only have a small starter amount, make a half batch first; the grains grow over a few weeks. Grains bought dried need 3-5 days of rehydrating in sugar water first (follow the seller's steps). Grains do not need exact halving; extra grains just ferment faster.

- **Between batches:** start the next batch right away, or rest the grains in fresh sugar water in the fridge for up to 1-2 weeks.
- **They multiply.** Healthy grains grow 10-50% a week. Keep about [[1 cup|1/2 cup]] for each batch and share or compost the rest.
- **Feed minerals.** If they shrink or turn mushy, add a pinch of baking soda or trace minerals, or use half raw sugar for a few batches.
- **Rinse rarely.** Rinse only in plain water, never chlorinated tap water, and only if they are slimy.

## Safety

- Fruit second ferments carbonate in hours, not days. Always bottle a plastic tester and move bottles to the fridge when it is hard.
- Add the grains only below 80 F.
- Slimy, foul-smelling or moldy grains mean the batch and grains go in the trash.

## Troubleshooting

- **Still very sweet after 48 hours.** Too cold, too few grains, or tired grains. Keep it at 74 F, add a fig and a pinch of minerals, and make the next batch smaller.
- **Grains not growing.** Common with filtered or soft water. Add the pinch of baking soda or trace minerals, or use half raw sugar.
- **Slimy liquid.** Usually too much sugar or too long in F1. Shorten the ferment.
- **Flat bottles.** Add 1 tsp sugar or a little more juice per bottle, check the gaskets, and leave them warm longer.
- **Yeasty or beery taste.** It fermented too long. Bottle sooner.

## Taste

Light, lemony and lightly sweet, like a gentle natural lemon soda.

## Related styles

Milk kefir uses different grains and milk. It is not this batch.
