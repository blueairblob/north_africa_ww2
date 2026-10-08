# Plan

## Where things stand (owner, 7 October 2026)

**Now: the pygame version, by trial play.** The work in hand is to make the
game good to play on the pygame screen. The owner is not yet convinced it is
good enough, and nothing below about the web or the phone is started or agreed
until he is.

**What "good enough" means.** Not every player is a history enthusiast. The
game has to be easy and gratifying to play, with reward in the playing. At
present its reward is mostly the kind that comes from time invested and
ownership of a long game, and that is not enough.

**The move to the web and the phone is a future plan.** Everything from "The
direction" onwards is a proposal from a review, recorded so that its themes
(a simpler screen, battles as stages on small maps, the division as the piece)
can be thought about while trial play continues. `DESIGN.md` is not changed
for it.

**One thing that does apply now:** nothing should be built on the pygame screen
that could not be done later in TypeScript on a phone. The next section is the
check for that.

## Will what pygame does carry over?

Checked on 7 October 2026 against commit `f0fbd7b`, by reading the code; no
browser or phone was used. Nothing the game does is impossible in a browser.
Some of how the player does it has no equivalent on a touch screen, and a few
things need care.

**Carries over as it is**

- The engine: integers only, no randomness, no files, no clock, no library
  beyond Python's own. About 2,000 lines.
- Everything drawn: the map picture, smooth zoom, hexes, counters, see-through
  overlays, the playback's flames and bursts, text and its wrapping. A browser
  canvas does all of it.
- Sound made by the program: a browser can generate the same tones.
- The orders standing from turn to turn, the stepping through units, the
  reports and the playback's scenes: these are in `screen/session.py` and
  `screen/replay.py`, which have no pygame in them.
- A saved or replayed game: a scenario and the orders given.

**Has no equivalent on a touch screen: needs another way in**

- Hover. The path shown before a click, the tooltip card over a unit, the
  words for a greyed button, and scrolling when the pointer reaches the map's
  edge all depend on it. The card and the path need a tap or a long press.
- The right click, which opens a stack's menu and lets go of a unit. A long
  press is the usual substitute.
- The keyboard: the order keys, the hex cursor, Space and Enter. Typing a
  group's name still works, with the phone's own keyboard.
- The mouse wheel for zoom. A pinch replaces it, and a pinch or a pan must not
  count as a tap.

Every action already has a button or a tap as well as its key, by an earlier
decision of the owner. What is missing on touch is information, not actions:
the path, the card and the reasons shown only on hover.

**Needs care**

- The map picture is 5,938 × 2,468 pixels, 14.7 million. Phone browsers limit
  how large a picture or canvas may be, and this is close to the limit I
  remember for iPhones (about 16.7 million); I am not sure of that figure. Cut
  into tiles, drawn smaller, or cropped to a stage, it is no problem.
- Sound in a browser cannot start until the player has touched the screen, and
  an iPhone's silent switch may mute it. Both are for the trial to answer.
- The layout is in fixed pixels: a panel 360 wide, buttons 36 high, a window no
  smaller than 900 × 560. It would be laid out again, not carried.
- The play log writes a file. A web page cannot; it would keep the log in the
  browser and offer it as a download.
- The unit taken up pulses all the time, so the screen is redrawn all the time.
  On a phone that costs battery.
- "A mobile app" can mean two things. A web application, installed from the
  browser or wrapped as an app, can use a canvas and everything above holds;
  React can be the shell round it. React Native, which draws with the phone's
  own parts, has no canvas: the drawing would be written again for it. The
  first is the one this plan assumes.

**To keep it so while pygame is worked on**

- Keep rules in `engine/` and behaviour in `session.py` and `replay.py`;
  `draw.py` and `app.py` only draw and listen.
- The engine stays integers only, with stated tie-breaks, and uses nothing but
  Python's own library.
- Anything shown only on hover, or done only by key or right click, also gets a
  place the player can tap.
- New rewards for the player (sound, movement, a result worth watching) are
  made from drawing and generated sound, which carry over; not from anything
  only a desktop has.

---

Written 7 October 2026, at commit `f0fbd7b`, from a review's proposal.
`DESIGN.md` has not been changed to match: the conflicts are listed in
"DESIGN.md: what would change", and wait for the owner.

## The direction

The owner's words:

- "The core aim is to get this game onto a mobile platform, therefore we need
  to adopt a more intuitive and simpler game screen."
- "Focus on the various battles as stages in a campaign, narrowing down the map
  size."
- "Adopt the very, very simple approach" of the small 8-bit desert wargames.

The game ships as one web application, playable on a phone and in a desktop
browser, at two levels of detail. The pygame screen is not the product. It is
the test bench until the web version replaces it.

Why: the pygame screen cannot reach a phone. The window refuses to go below
900 × 560; the side panel is 360 pixels wide; order buttons are 36 pixels high
where a thumb needs about 48; the path preview and the tooltip depend on hover.
Pygame does not run on phones in any way worth shipping.

## Proposed decisions (from the review; not yet confirmed by the owner)

1. Two modes, one engine: Simple mode for phones, Full mode for a browser on a
   wide screen.
2. Simple mode has five orders: Move, Attack, Hold, Rest, Dig in.
3. In Simple mode the division is the piece: about 8 to 15 a side.
4. The campaign is a series of stages, each battle on its own small map.
   Carrying losses from one stage to the next is an option for the player.
5. The shipped engine is written in TypeScript. The Python engine becomes the
   reference it is checked against.

Also decided, in play, October 2026: an HQ does not count toward stacking; a
unit may pass through a full hex; a unit loses at most 40 cohesion to a turn's
battles; a unit with no order holds, Dig in stands until the defences are
complete, and a click on the map gives an order only after Move or Attack is
pressed.

## Simple mode (phone)

- Each stage is a scenario on a map cropped from the generated one, about
  30 × 16 hexes, to fit a phone held sideways. The stages are the historical
  battles in order, each built from `docs/SOURCES.md`.
- A turn: the game takes the player through each division in turn, centred. Its
  current order is the default, kept with one tap. A tap on ground moves it; a
  tap on an enemy attacks. Hold, Rest and Dig in are the only buttons.
- When a division is taken up, the hexes it can reach are lit. Nothing depends
  on hover, a right click or a key.
- One card at the bottom for the division taken up: name, strength, supply as a
  word, morale as a word. No side panel.
- Folded away: Join, Split and Recall (divisions stay whole); road march;
  separate fuel and stores bars; air options; the zones overlay; renaming.
- Orders can be changed freely until the turn is ended. The screen says so.
- Before an attack is committed, one coarse word for the odds: strong, even,
  weak.
- A pan or a pinch never registers as a tap.
- Zoomed out, a division is a simple marker with its strength, not a shrunken
  counter.
- Tap targets at least 48 pixels. End turn and Next within the thumb's reach,
  bottom right.
- A whole turn, orders and playback, takes a couple of minutes.

## Full mode (browser, wide screen)

What the pygame screen does now: regiments, Join, Split and Recall, the layers,
the whole map, the play log. Built after Simple mode.

## Order of work

1. **Finish the open fixes** from the reviews, on the Python engine and the
   pygame screen, where they concern rules or behaviour both modes share. No
   more polishing of presentation that only pygame has: panel layout, button
   sizes, fonts.
2. **Settle the rules** on the Python engine, including Simple mode's five
   orders and the first stage scenario. A rule changed after the port is
   changed twice.
3. **Freeze the Python engine** as the reference. Record golden games: the
   scenario, both sides' orders and the full state after every turn, for each
   stage, with the scripted players in every pairing.
4. **Port the engine to TypeScript.** It must reproduce every recorded state
   exactly.
5. **Build the web screen:** Simple mode first, then Full mode.
6. **Retire the pygame screen** when Full mode matches it.

Staying in Python: the map generator, which is a build tool that writes JSON,
and the reference engine with its tests.

A trial comes before the port: see "The trial".

### What step 2 has to settle

These are rules questions that Simple mode and the stages raise. Each needs an
answer in `docs/RULES.md` before the freeze. The proposals are mine and are not
agreed.

- **A stage on a cropped map.** Supply today is traced over the whole map to
  ports, the railhead and Tripoli. On a 30 × 16 map most of those are off it.
  Proposal: a stage has supply entry hexes on its edge, each with a capacity
  and a haul cost already paid, worked out once from the whole map and written
  into the scenario. Tripoli is already handled this way (`docs/RULES.md`
  18.5). Also to settle: where reinforcements enter, whether a unit may leave
  by the edge, and what the objectives are when the usual ones are off the
  map.
- **The division as the piece.** The engine already moves and fights a
  division as one group under its HQ (§20). Simple mode would never split one.
  To settle: a regiment that arrives as a reinforcement, or is parted from its
  division by a retreat, must rejoin without a Join order. Proposal: the screen
  gives the Join for the player by a stated rule, so the engine still receives
  ordinary orders.
- **Road march without the order.** The engine never alters an order (8.2.1),
  and a column caught on a road defends at a quarter. If the screen turns a
  Move into a road march, the player takes that risk without having chosen it.
  Proposal: the screen does the choosing, by one stated rule the player can be
  told ("it travels by road when no enemy is seen within so many hexes of its
  way"), and the card says "travelling by road" when it does.
- **The word for the odds.** From what the side can see, never from what it
  cannot. To settle: the bands for strong, even and weak, and what is said when
  the enemy's strength is not known.
- **Air.** With the choice folded away, Simple mode needs a fixed one. Proposal:
  support.
- **Carrying losses over.** Each stage has its historical order of battle. If
  losses carry over, the next stage's order of battle is no longer the
  historical one. Not designed.
- **Morale.** Proposals A (now the odds word), D and E from the October play
  are still open.
- **The computer opponent.** A phone game is played alone, and the scripted
  players are test tools, not opponents. `DESIGN.md` milestone 5 is the
  computer opponent, and the order of work above does not place it. It has to
  be deterministic and it has to be ported or rewritten in TypeScript too.
  Proposal: build it in Python as part of step 2, outside the engine as a
  player, and record its games with the golden ones.
- **Tuning.** Unit strengths (only four tank figures are sourced), supply and
  victory figures, and the combat constants are all still marked to be tuned.
  Tuning after the freeze means recording the golden games again; it does not
  mean porting again, if the constants are data.

## A living map (web screen, after Simple mode is playable)

An idea of the owner's, recorded on 7 October 2026 from a review's note. It is
not for now and not for the pygame screen. None of it has been built or tested.
The note reached me with the ends of several lines cut off; where a point below
is marked "(cut)", its last words are my reading.

The owner's words: "Is it possible to animate the map somehow? I'm thinking
super realistic touches like wobbly sea, the odd desert storm sandy dust,
whispers of cloud passing over."

**Where it belongs.** In the web screen only. A browser can run these as thin
moving layers over the still map picture, on the graphics chip, so the map
itself is never redrawn. Pygame would draw every effect on the processor each
frame, for a screen that is to be retired.

**The effects, in the order to try them**

1. Cloud shadows: soft dark patches drifting over the map. Shadows read better
   than clouds and never hide a counter. (cut)
2. Sea: a slow ripple and glint, on sea pixels only. The map generator already
   knows which pixels are land.
3. Dust trails: a puff behind a formation as it moves. (cut)
4. Sandstorm: a haze over the whole map that thickens and clears, shown when a
   scheduled storm in the rules is in force.
5. Blowing sand: faint streaks moving one way across open desert.
6. Heat shimmer: a slight wobble far inland. Optional; the first to drop.

**So that it helps and does not hurt**

- Slow and faint. Motion draws the eye, and the counters must stay the loudest
  thing on the screen.
- Where it can, an effect tells the player something: a storm on the screen
  means the storm rule applies this turn; dust means something moved there.
  (cut)
- Animate while the screen is idle or playing back. Freeze during a drag or a
  pinch.
- A setting to turn it off; off by default when the device asks for reduced
  motion or is saving battery.
- No more than about 30 frames a second: battery is a standing complaint about
  phone wargames. (cut)
- Purely presentation. Nothing in the engine or the golden games depends on
  it, and a game with effects off plays identically. (cut)

**"Super realistic".** The map is drawn as a chart of the period, and
photographic effects on a paper chart would look wrong (cut). The aim is a lit
map table: light moving across paper, the sea catching it. If real textures
seem better when the time comes, show both.

**When the time comes.** Effect 1 alone first, on a real phone, with frame rate
and battery use measured before any other effect is added. (cut)

**The weather now exists in the rules** (`docs/RULES.md` §21, added 7 October
2026): rain and sandstorm, drawn by chance from a seed. So effect 4 has
something to show, and rain joins the list. The pygame screen shows both with a
still wash and a chip; the moving versions belong here. The generator is
written out in the rules and uses no product above 2 to the power 47, so a
TypeScript engine gives the same weather from the same seed.

## The trial

One stage map in a browser, one turn played on a real phone, the engine
stubbed. It answers two questions: is a 30 × 16 hex map usable under a thumb,
and does sound start reliably on the first tap?

What it takes:

- from the map generator, one cropped map: a picture and the hex geometry as
  JSON (a small addition to `mapgen`);
- from the Python engine, one recorded turn on that crop: the units, the hexes
  each can reach, and the events of the turn (a script, no engine change);
- one web page, no framework: the map on a canvas with pan and pinch that never
  count as a tap; a tap that takes up a division and lights its reach; a tap
  that orders it; the card; Hold, Rest, Dig in, Next and End turn at 48 pixels;
  the recorded turn played back with generated sound started by the first tap;
- somewhere the phone can load it from. The repository is public, so a public
  page is possible; a server on the home network is the private way.

It is throwaway code. The owner has to do the testing: it cannot be judged
without a hand and a phone.

## Risks

**The port.** The engine is about 2,000 lines, integers only, with no
randomness, which is as favourable as a port gets. Where it can go wrong:

- floor division: Python's `//` rounds down, JavaScript's division does not,
  and they differ on negative numbers (27 uses);
- the order things are walked in: a JavaScript object with keys that look like
  numbers is walked in number order, not the order they were added, and the
  state is keyed by unit id in places;
- sorting and ties (48 sorts): tuple keys, a stable sort, and above all the
  choice between two ways of equal cost in path-finding, which decides where
  units go;
- the text form of the state, which the golden games compare.

The golden games catch all of these, but only on what the recorded games
happen to do. The scripted players are simple, so the record should include
games with random legal orders from a seeded generator.

**Two modes on one engine.** The danger is two sets of rules. It is avoided if
Simple mode is only a way of giving orders: every tap becomes ordinary engine
orders, and the engine has no notion of a mode. The cost is that Simple mode's
conveniences (rejoining, road march, the air choice) must each be a stated rule
in the screen, tested like one. A second danger is two sets of scenarios, small
stages and the whole map, each needing its own tuning.

**What may not survive division-only play.**

- Massing armour and splitting a division, which the owner chose in October
  2026, exist only in Full mode.
- Stacking at two formations a hex is tight on a 16-row map with 15 divisions.
- A division of mixed arms moves at its slowest unit's pace and attacks with
  everything, so the differences between arms are felt less.
- Supply on a cropped map is the largest unknown: it is the heart of the game
  and the part most changed by cutting the map down.

**The plan itself.** The computer opponent is not in the order of work. The
rules freeze depends on tuning that has barely begun. And "learned in ten
minutes" has not been tried on anyone.

## DESIGN.md: what would change

Proposals. `DESIGN.md` is not edited until the owner agrees.

- **§12 Presentation** describes the pygame screen: a side panel, hover,
  right click, keys, End turn "plain until every unit has its order" (already
  untrue since `f0fbd7b`). It also says "no odds are shown before". Proposal:
  §12 becomes two short sections, Simple mode and Full mode, as in this plan;
  the playback stays as it is, since it carries over; the line on odds becomes
  "one coarse word before an attack, no numbers".
- **§13 Technical shape** says the engine is pure Python and the front ends are
  "a desktop window (pygame) first; a browser version later from the same
  engine". Proposal: the shipped engine is TypeScript; the Python engine is the
  reference, with recorded games as the test between them; the front end is one
  web application; the map generator stays in Python.
- **§14.1 The complexity budget** allows six orders and Join, about 60 counters
  a side, a counter with three numbers, "under ten scenarios plus the
  campaign", and "editors, sub-maps: none". Proposal: state the budget for
  Simple mode (five orders, 8 to 15 pieces a side, a marker and a card, a turn
  in a couple of minutes) and keep the present one as Full mode's; replace
  "sub-maps: none" with "each stage has its own map, cut from the one generated
  map".
- **§15 Milestones** ends with the computer opponent, more scenarios, the
  campaign and the tutorial. Proposal: replace milestones 4 to 6 with the order
  of work above, with the computer opponent placed in step 2.
- **§10 Scenarios** and **§2 Scale** were not named in the request but are
  touched: stages on cropped maps, and the division as the piece.

## Tasks from before the change

Dropped, as pygame presentation that will not carry over:

- the losses tab and further panel tabs;
- restyling the counters and the colour system on the pygame screen;
- greyed against hidden buttons, button sizes, fonts, panel layout;
- the speed test of the Python engine in a browser (Pyodide): the engine is to
  be ported, not carried.

Kept, as rules or behaviour both modes share:

- the engine's rules and their tests; tuning; sourcing unit strengths;
- the computer opponent;
- the play log, while pygame is the test bench;
- the unexplained dead clicks of 5 October, only if they recur: the log now
  says enough to find the cause.

Changed:

- `screen/session.py` and `screen/replay.py` have no pygame in them. They were
  to be moved out of `screen/` and reached from a browser through JSON. They
  become the description of what the web screen must do: standing orders,
  stepping through the pieces, reports, the playback's scenes.
- The odds warning (morale proposal A) becomes Simple mode's odds word.
- A plain Undo, and whether taking back a Join or Split restores the group,
  matter only to Full mode and move there.
- The counter pictures (`docs/COUNTERS.md`) carry over as art, but the sizes
  were set for the pygame screen and are to be set again for the marker and
  the card.
- The market notes (`docs/MARKETING.md`, not published) asked for supply seen
  at a glance, small stage maps and a plainer counter. The second and third are
  now in this plan. The first is not: how supply shows in Simple mode, beyond
  one word on the card, is still to be designed.

## Open, for the owner

- In Simple mode, are a division's regiments hidden entirely or shown on a long
  press?
- Which battles are the stages, and how many for a first release?
- How one stage's result sets up the next when losses are carried over.
- Where the computer opponent goes in the order of work.
- Whether this file is published with the repository.
- Price and store plans. No decision is needed now.

## The clean-room rule still holds

"The simple approach of the 8-bit games" means the workload: one unit at a
time, the current order as the default, a handful of orders, one report card,
the battle as a show. It does not mean any earlier game's scenario set, unit
lists, maps, order names, numbers, colours or wording. The same goes for phone
games: how they are operated is common to the genre; nothing else is taken
(`docs/CLEAN_ROOM.md`).
