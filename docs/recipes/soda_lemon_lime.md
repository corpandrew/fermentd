---
schema: fermentd.recipe/v1
id: soda_lemon_lime
category: soda
profile_id: soda_lemon_lime
batch_number: 1
name: Lemon-Lime Soda
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
- id: lemon
  item: lemons
  amount: '3'
  preparation: zest, then juice
  note: about 1/2 cup juice
- id: lime
  item: limes
  amount: '4'
  preparation: zest, then juice
  note: about 1/2 cup juice
- id: sugar
  item: white sugar
  amount: 1 1/4 cups
  grams: 250
- id: salt
  item: salt
  amount: 1/8 tsp
- id: water
  item: water
  amount: about 1 gallon
  note: filtered if tap water is chlorinated
- id: yeast
  item: EC-1118 yeast
  amount: 1/8 tsp
  note: Lalvin EC-1118, about 1/8 tsp per gallon
optional:
- id: mint
  item: fresh mint
  amount: a few sprigs
  note: steep with the zest
equipment:
- large pot (at least 5 quarts, so the whole gallon fits; with a smaller pot, top up with cold water in the bucket instead)
- large mesh strainer (bigger is better; a small one clogs with grated ginger or zest)
- large pitcher or spouted measuring cup, or a bucket, to strain into
- funnel for filling bottles from the pitcher
- auto-siphon and bottle filler (optional; the easiest one-handed way to fill, straight from the bucket)
- baking dish or the sink, to stand the bottles in and catch spills
- swing-top glass bottles (about eight 16 oz)
- one plastic seltzer bottle for the squeeze test
- stirring spoon (metal is fine)
- Star San and a spray bottle
- thermometer
- measuring cups and spoons
- seedling heat mat in the backpack cooler
safety:
- id: glass
  text: Swing-tops are glass. Over-carbonated glass can burst.
- id: fridge
  text: Never leave the bottles warm once the plastic bottle is rock hard.
- id: burp
  text: If unsure, burp one bottle to check the pressure.
- id: yeast
  text: Wait until the liquid is below 80 F before pitching. Hot liquid kills yeast.
- id: open
  text: Open the first bottle slowly over the sink. It may foam.
steps:
- id: sanitize
  stage: day0
  profile_stage: bottle
  text: "Sanitize these with Star San: swing-top bottles and gaskets, the plastic tester bottle, stirring spoon (metal is fine), thermometer, mesh strainer, pitcher or bucket, funnel, and the auto-siphon and bottle filler if used. The pot just needs to be clean; the syrup boils in it."
- id: syrup
  stage: day0
  profile_stage: bottle
  text: "Bring 1 quart of water to a simmer with the sugar and salt, stirring until dissolved."
- id: steep
  stage: day0
  profile_stage: bottle
  text: "Off the heat, add the lemon and lime zest, cover, and steep for 15 minutes."
- id: cool
  stage: day0
  profile_stage: bottle
  text: "Add the juice, top up to just under a gallon with cold water, cover, and let it cool below 80 F. The zest can stay in while it cools."
- id: strain
  stage: day0
  profile_stage: bottle
  text: "Strain right before adding the yeast: pour through the large mesh strainer into the sanitized pitcher or bucket. Go in batches if the strainer fills up; a bigger strainer clogs less."
- id: pitch
  stage: day0
  profile_stage: bottle
  text: "Check it is below 80 F, sprinkle 1/8 tsp EC-1118 over the strained soda, and stir with the sanitized spoon for 30 seconds."
- id: bottle
  stage: day0
  profile_stage: bottle
  text: "Stand the bottles in a baking dish or the sink to catch spills. Fill them through the funnel from the pitcher, or with the auto-siphon and bottle filler from the bucket (easiest one-handed), leaving 1-2 inches of headspace. Fill the plastic bottle too, squeeze out the air, and cap it."
- id: carbonate
  stage: carbonate
  profile_stage: in_bottle
  text: Put the bottles in the backpack cooler on the heat mat and start the batch in fermentd. Timer mode, target 72 F.
- id: chill
  stage: serve
  profile_stage: refrigerated
  text: When the plastic bottle is rock hard, move every bottle to the fridge. Chill at least 24 hours before opening.
- id: serve
  stage: serve
  profile_stage: refrigerated
  text: Drink within 2-3 weeks. The yeast keeps working slowly even when cold.
reminders:
- id: squeeze
  at: stage:in_bottle+12h
  repeat: 12h
  text: Squeeze the plastic seltzer bottle. Twice a day until it is rock hard.
- id: refrigerate_now
  at: stage:in_bottle+24h
  repeat: 6h
  text: If the plastic bottle is rock hard, move every bottle to the fridge now. Do not leave glass swing-tops warm.
- id: open
  at: stage:refrigerated+24h
  text: Chill is done. Open the first bottle slowly over the sink.
- id: finish
  at: stage:refrigerated+14d
  text: Drink the lemon-lime soda within the next week. Yeast keeps working slowly even cold.
taste: Bright, tart, and clean, like a homemade Sprite, about 0.5% if chilled on time.
not_this_batch:
  id: soda_lemonade_still
  summary: A still lemonade skips the yeast and the bottles; this batch is about the fizz.
---


## Ingredients

Makes 1 gallon, about 7-8 bottles of 16 oz.

- 3 lemons, zested then juiced (about 1/2 cup juice)
- 4 limes, zested then juiced (about 1/2 cup juice)
- 1 1/4 cups (250 g) white sugar
- 1/8 tsp salt
- About 1 gallon of water, filtered if the tap water is chlorinated
- 1/8 tsp Lalvin EC-1118 yeast
- Optional: a few sprigs of mint, steeped with the zest

Zest only the colored skin. The white pith is bitter.

## Equipment

- Large pot, at least 5 quarts so the whole gallon fits (with a smaller pot, top up with cold water in the bucket instead)
- Large mesh strainer. Bigger is better: a small one clogs with grated ginger or zest
- Large pitcher or spouted measuring cup, or a bucket, to strain into
- Funnel for filling the bottles from the pitcher
- Optional, and the easiest one-handed way to fill: an auto-siphon and bottle filler, filling straight from the bucket
- A baking dish, or the sink, to stand the bottles in and catch spills
- Swing-top glass bottles (about eight 16 oz)
- One plastic seltzer bottle for the squeeze test
- Stirring spoon (metal is fine)
- Star San and a spray bottle
- Thermometer
- Measuring cups and spoons
- Seedling heat mat in the backpack cooler

No jug or fermenter is needed: the soda is mixed in the pot and goes straight into the bottles.

## Sanitation

Mix Star San at 1 oz per 5 gallons (about 1.5 tsp per gallon) of water. Spray or fill each item, let it drain for a minute, and do not rinse; the foam is fine.

**Sanitize these:**

- Swing-top bottles and their gaskets
- The plastic tester bottle and its cap
- Stirring spoon (metal is fine)
- Thermometer
- Mesh strainer
- Pitcher, measuring cup or bucket
- Funnel
- Auto-siphon and bottle filler, if you use them

The pot only needs to be clean, because the syrup boils in it. Anything that touches the soda after it has cooled must be sanitized.

## Mix and bottle

About 40 minutes, plus cooling.

1. Sanitize everything on the checklist above.
2. Zest the lemons and limes with a microplane, then juice them. Strain the seeds out of the juice.
3. Bring 1 quart of water to a simmer with the sugar and salt, stirring until it dissolves.
4. Take it off the heat, add the zest (and mint, if using), cover, and steep for 15 minutes.
5. Add the lemon and lime juice and top up to just under a gallon with cold water.
6. Cover the pot and let it cool until it is below 80 F and feels lukewarm. The zest can stay in while it cools.
7. Strain right before adding the yeast: pour through the large mesh strainer into the sanitized pitcher or bucket. Go in batches if the strainer fills up.
8. Sprinkle 1/8 tsp EC-1118 over the strained soda and stir with the sanitized spoon for 30 seconds.
9. Bottle right away. Stand the bottles in a baking dish or the sink to catch spills. Fill them through the funnel from the pitcher, or with the auto-siphon and bottle filler from the bucket (the easiest one-handed option), leaving 1-2 inches of headspace. Fill the plastic bottle too, squeeze out the air, and cap it.

## Carbonation check

Carbonation in the bottles, about 24-48 hours.

1. Put all the bottles, including the plastic tester, in the backpack cooler on the heat mat. Start the batch in fermentd (Timer mode, target 72 F) so it runs the mat and the reminders.
2. Squeeze the plastic bottle twice a day. It starts soft and slowly firms up.
3. When it is rock hard and will not dent with a firm squeeze, move every bottle to the fridge right away. This is usually 24-48 hours at 72 F, sooner if the room is warm.
4. Press "Move bottles to the fridge" on the dashboard so the reminders switch over.

## Fridge and serving

1. Chill at least 24 hours before opening. Cold soda holds its fizz and the yeast slows down.
2. Open the first bottle slowly over the sink. Lift the swing-top a little, let it hiss, then open fully.
3. Pour gently and leave the last half inch, which has the yeast sediment.
4. Drink within 2-3 weeks. The yeast keeps working slowly even cold, so the soda gets drier and fizzier over time.

## Safety

- The swing-tops are glass, and over-carbonated glass can burst. Never leave the bottles warm once the plastic bottle is rock hard.
- If you miss a day, put the bottles in the fridge first, then open one over the sink to release pressure.
- If you are unsure, burp one bottle to check the pressure.
- Pitch only below 80 F. Hot liquid kills yeast.
- Keep the bottles in the closed cooler while they carbonate, away from faces and pets.

## Troubleshooting

- **The plastic bottle is still soft after 48 hours.** Check that the cooler is near 72 F on the dashboard. Cold slows the yeast. Give it another 12-24 hours. If it never firms up, the yeast may have been pitched too hot; next time cool below 80 F first.
- **It is flat after chilling.** It went into the fridge too early or a gasket leaked. Leave it at room temperature for another day with the tester, then chill again.
- **It gushes when opened.** It was warm too long. Chill all the bottles well, open them over the sink, and drink them soon. Move to the fridge sooner next time.
- **It tastes yeasty.** Pour gently and leave the sediment in the bottle. A longer chill helps it settle.
- **It is too sweet or not sweet enough.** Adjust the sugar by 1/4 cup next batch. Do not add sugar to bottles that are already carbonating.

## Taste

Bright, tart, and clean, like a homemade lemon-lime soda. About 0.5% alcohol if you chill it on time.

## Related styles

A still lemonade skips the yeast and the bottles. This batch is about the fizz.
