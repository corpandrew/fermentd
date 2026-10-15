---
schema: fermentd.recipe/v1
id: ginger_beer_jamaican
category: soda
profile_id: ginger_beer_jamaican
batch_number: 1
name: Spicy Jamaican Ginger Beer
status: active
yield:
  volume_gal: 1
  bottle_fl_oz: 16
  bottle_count: 7-8
tracking_mode: timer
target_f: 72
pitch_below_f: 80
carbonation_window_h:
- 24
- 48
chill_before_open_h: 24
drink_within_days:
- 14
- 21
abv_if_chilled_on_time: 0.005
ingredients:
- id: ginger
  item: fresh ginger, unpeeled, finely grated
  amount: 8 oz (about 225 g)
  amount_half: 4 oz (about 115 g)
  grams: 225
  note: about twice the ginger ale amount
- id: sugar
  item: white sugar (or half brown sugar)
  amount: 1 1/4 cups (250 g)
  amount_half: 2/3 cup (125 g)
  grams: 250
- id: lime
  item: fresh lime juice
  amount: 1/2 cup (4 limes)
  amount_half: 1/4 cup (2 limes)
- id: allspice
  item: whole allspice (pimento) berries, lightly crushed
  amount: '8'
  amount_half: '4'
- id: cloves
  item: whole cloves
  amount: '4'
  amount_half: '2'
- id: cayenne
  item: cayenne pepper (optional, for extra heat)
  amount: a pinch
  amount_half: a tiny pinch
- id: water
  item: water
  amount: to make 1 gallon
  amount_half: to make 1/2 gallon
- id: yeast
  item: EC-1118 yeast
  amount: 1/8 tsp
  amount_half: 1/8 tsp; yeast does not need halving
optional: []
equipment:
- '1-gallon jug or pot for mixing (half batch: the same jug is fine, since it is not fermented in the jug)'
- 8-quart stock pot
- fine strainer or cloth
- funnel
- '7-8 swing-top bottles (16 oz) rated for carbonation (half batch: 3-4), plus one plastic tester bottle'
- hydrometer (optional)
- seedling heat mat in the backpack cooler
safety:
- id: tester
  text: Bottle one plastic tester and move every bottle to the fridge when it is rock hard.
- id: glass
  text: Over-carbonated glass can burst. Never leave the bottles warm once the tester is rock hard.
- id: pitch
  text: Pitch yeast only below 80 F.
steps:
- id: steep
  stage: day0
  profile_stage: bottle
  text: Steep the ginger and spices in hot water for 1 hour, then strain.
- id: mix
  stage: day0
  profile_stage: bottle
  text: Dissolve the sugar, add lime juice and cold water, and cool below 80 F.
- id: pitch
  stage: day0
  profile_stage: bottle
  text: Stir in the yeast and bottle right away with a plastic tester.
- id: carb
  stage: ferment
  profile_stage: in_bottle
  text: Carbonate 24-48 hours at 72 F until the tester is rock hard.
- id: fridge
  stage: serve
  profile_stage: refrigerated
  text: Refrigerate every bottle and drink within 2-3 weeks.
taste: Sweet, fiery and very gingery with lime and warm allspice, almost non-alcoholic.
not_this_batch:
  id: ginger_beer_quick
  summary: For a dry, alcoholic ginger beer of about 4%, see the quick ginger beer profile. It is not this batch.
half:
  yield:
    volume_gal: 0.5
    bottle_fl_oz: 16
    bottle_count: 3-4
reminders:
- id: squeeze
  at: stage:in_bottle+12h
  repeat: 12h
  text: Squeeze the plastic tester bottle. Twice a day until it is rock hard.
- id: refrigerate_now
  at: stage:in_bottle+24h
  repeat: 6h
  text: If the plastic tester is rock hard, move every bottle to the fridge now. Do not leave glass warm.
- id: open
  at: stage:refrigerated+24h
  text: Chill is done. Open the first bottle slowly over the sink.
- id: finish
  at: stage:refrigerated+14d
  text: Drink the ginger beer within the next week. Yeast keeps working slowly even cold.
---


## Ingredients

Makes [[1 gallon, about 7-8 bottles of 16 oz|a half gallon, about 3-4 bottles of 16 oz (a test batch)]]. Under about 0.5% alcohol if chilled on time.

- [[8 oz (about 225 g)|4 oz (about 115 g)]] fresh ginger, unpeeled, finely grated (about twice the ginger ale amount)
- [[1 1/4 cups (250 g)|2/3 cup (125 g)]] white sugar (or half brown sugar)
- [[1/2 cup (4 limes)|1/4 cup (2 limes)]] fresh lime juice
- [[8|4]] whole allspice (pimento) berries, lightly crushed
- [[4|2]] whole cloves
- [[a pinch|a tiny pinch]] cayenne pepper (optional, for extra heat)
- [[to make 1 gallon|to make 1/2 gallon]] water
- [[1/8 tsp|1/8 tsp; yeast does not need halving]] EC-1118 yeast

**What makes it Jamaican.** Jamaican ginger beer is fiery: about twice the ginger of a ginger ale, plenty of lime, and warm allspice (pimento) and clove. It is a sweet soft drink, carbonated in the bottle in 1-2 days and then chilled, like the ginger ale.

**Yeast.** 1/8 tsp EC-1118 for either size; it only needs to make bubbles. **Yeast does not need halving.**

## Equipment

- 8-quart stock pot
- A jug or large pot for mixing (it is not fermented in the jug, so a half batch is fine in the 1-gallon jug)
- Fine strainer or a clean cloth, funnel
- [[7-8|3-4]] swing-top bottles (16 oz) rated for carbonation, plus one plastic tester bottle
- Hydrometer (optional; it starts around 1.025-1.030 and barely moves before you chill it)
- Seedling heat mat in the backpack cooler

**Temperature.** These like warmth. The heat mat holds the target even in a cold winter room, so they work well all year. fermentd caps every target at 75 F. The bottles carbonate at 72 F in 24-48 hours.

## Sanitation

Mix Star San at about 1.5 tsp per gallon. Sanitize the jug or pot, funnel, strainer, bottles, gaskets and the plastic tester. Let them drain; do not rinse.

## Steep, mix and bottle

About 1 1/2 hours, mostly steeping and cooling.

1. Bring [[1/2 gallon|1 quart]] of water to a boil, turn off the heat, and add the grated ginger, crushed allspice and cloves. Cover and steep **1 hour**. Longer is spicier.
2. Strain through a fine strainer or cloth, pressing the ginger hard to get all the juice.
3. Stir in the sugar until it dissolves, then the lime juice and the cayenne if using.
4. Top up with cold water to [[1 gallon|1/2 gallon]]. Check that it is **below 80 F**.
5. Sprinkle in the yeast and stir well.
6. Funnel into the bottles, leaving 1-2 inches of headspace. Fill the plastic tester the same way, squeeze out the air, and cap it.
7. Put the bottles in the cooler on the mat and start the batch in fermentd. It starts in **Carbonating in the bottles** at 72 F.

## Carbonation check

1. From 12 hours, fermentd reminds you twice a day to squeeze the plastic tester.
2. When it is **rock hard** (usually 24-48 hours), move every bottle to the fridge right away and press **Move bottles to the fridge**.
3. Chill at least 24 hours before opening.

## Fridge and serving

Open slowly over the sink; ginger sediment makes it foam. Drink within 2-3 weeks. The yeast keeps working slowly even in the fridge, so it gets drier and fizzier over time.

## Safety

- Always bottle a plastic tester and move every bottle to the fridge once it is rock hard. Never leave carbonated glass warm.
- Add the yeast only below 80 F.
- Do not leave the bottles out to "get more fizzy"; that is how glass bursts.

## Troubleshooting

- **Tester not firming after 48 hours.** Check that it was below 80 F when the yeast went in and that the cooler is at 72 F. Give it 12 more hours.
- **Not spicy enough.** Use more ginger, grate it finer, steep longer, or add the cayenne.
- **Too sweet.** Use 1 cup sugar next time. Do not ferment it longer to dry it out; that over-carbonates the glass.
- **Gushing.** It sat warm too long. Chill well and open over the sink.

## Taste

Sweet, fiery and very gingery with lime and warm allspice, almost non-alcoholic.

## Related styles

For a dry, alcoholic ginger beer of about 4%, see the quick ginger beer profile. It is not this batch.
