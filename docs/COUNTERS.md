# Counters: sizes, sprites and what the first trials showed

Notes on the design of the unit counters. The first part (sizes, the prompt,
the trials) dates from the first work on them in October 2026, before there
was a screen. The pictures the game now uses are described under "The drawn
set" below.

## Sizes

Hexes are flat-topped, so a hex is 0.866 as high as it is wide. These sizes
were set for a screen with two zoom levels, the far one half the near one.
The screen as built zooms smoothly instead, from the whole map (about 20 px
to the hex) to 128 px, over a base map drawn at 64 px to the hex
(`python -m mapgen base`); a counter is always 0.74 of the hex, the most that
keeps the counters of neighbouring hexes apart. So a counter is 47 px at the
opening zoom and 94 px at the closest, and its picture is 43 × 26 and
86 × 52. The master size and the 5:3 shape below still hold.

| | Near zoom | Far zoom | Master to draw at |
| --- | --- | --- | --- |
| Hex, corner to corner | 96 px | 48 px | — |
| Hex, flat to flat | 83 px | 42 px | — |
| Counter (square, fits inside the hex) | 60 × 60 | 30 × 30 | 480 × 480 |
| Picture area (the top of the counter) | 60 × 36 | 30 × 18 | 480 × 288 |

- A sprite is drawn at **480 × 288** (5:3) on a transparent background. It
  shrinks by 8 and by 16 to the two zooms.
- The bottom 24 px of the near-zoom counter is kept for the numbers and the
  two bars (`DESIGN.md` §4.2), which the code draws.
- The test that matters is the far zoom: the vehicle must still read at
  30 × 18.
- A hex can hold two formations and an HQ (`docs/RULES.md` 4.3.1), so counters
  overlap in a stack. The subject is centred, with nothing that matters in
  the corners.

## The prompt

For an image generator. `[SUBJECT]` and the colour are filled in for each
sprite.

```
A single military vehicle sprite for a hex wargame counter, North African
desert campaign, 1940-1942.

Subject: [SUBJECT], shown in strict side profile, facing right, the whole
vehicle in frame, wheels or tracks on one level baseline.

Style: flat vector illustration, like a recognition silhouette with a little
detail. Three or four flat tones of one colour, plus a dark outline. No
gradients, no texture, no photographic shading, no cast shadow, no ground, no
dust, no crew, no markings, flags, insignia, numbers or lettering.

Outline: very bold, about 2 per cent of the image width, dark brown, the same
weight everywhere.

Colour: [desert sand yellow for British and Commonwealth | dark grey-tan for
German | grey-green for Italian].

Detail: it must stay recognisable when shrunk to 30 pixels wide. No aerials,
no rivets, no bolts, no track teeth, no small hatches. Draw the track as one
solid dark band. Make the gun barrel at least as thick as the outline. Keep
only the features that identify the type: hull shape, turret, gun length,
wheel or track layout, as thick shapes.

Composition: the subject fills about 85 per cent of the width, centred, with
even empty margin on all sides. Canvas 480 x 288 pixels (5:3).

Background: fully transparent PNG with an alpha channel. Not black, not white.

One vehicle only. No scene, no border, no frame, no text.
```

## Subjects

One per unit type per nation, so that a set stays consistent.

| Unit type | Commonwealth | German | Italian |
| --- | --- | --- | --- |
| Armour | Crusader; Matilda II (army tank brigades); M3 Stuart | Panzer III | M13/40 |
| Guns | 25-pounder | 88 mm Flak on its carriage | a field gun |
| Motorised infantry | Bedford or CMP 15-cwt truck | Opel Blitz lorry | Lancia lorry |
| Foot infantry | a marching rifleman, in the same flat style — the one sprite that is not a vehicle | | |
| Reconnaissance | Marmon-Herrington or Humber armoured car | SdKfz 222 | AB 41 |
| HQ | a command truck, or a jeep (jeeps reached the desert only in 1942) | Kübelwagen with an aerial | a staff car |

Markers, not counters: a supply lorry; a goods locomotive with one wagon for
the railhead; a Hurricane, a Bf 109 and a Stuka for the air mission.

## Three things to hold to

- **One baseline, one scale, one outline weight** across the set, or the
  counters will not look like a set. Generate one sprite, then give it back
  to the generator as the style reference for the rest.
- **Mirror in code, not in the art.** Everything is drawn facing right; the
  screen can flip one side.
- **Originals only.** The repository is public and clean-room
  (`docs/CLEAN_ROOM.md`): no art from another game. Photographs may be used as
  a reference for a vehicle's shape; the sprite must be newly drawn.

## What the first trials showed

A Matilda II was generated twice with ChatGPT from the prompt above (in its
first form, without the Outline, Detail and Background paragraphs, which were
added because of what follows). Each result was shrunk to 60 × 36 and 30 × 18
and laid on three counter colours to see what survives.

**First result** — 1,619 × 971 pixels, 5:3, side profile, facing right, flat
tones: the framing and proportion asked for.

- The background was painted black, not transparent: every pixel was opaque.
- The outline was about 6 px wide. At 60 px across that is a quarter of a
  pixel, so it vanished and the tank went soft.
- With the outline gone, a sand tank on a sand map had little contrast.
- The aerials, rivets, track teeth and small hatches all disappeared; the gun
  barrel thinned to under a pixel at the far zoom.
- At 30 px it was clearly a tank but no longer clearly a Matilda. The side
  skirt with its row of openings is the feature that identifies it, and that
  did survive at 60 px.

**Second result** — delivered as an SVG file.

- It is not a vector drawing: the SVG wraps the same 1,619 × 971 PNG (about
  1 MB). It is usable, but it does not scale as a drawing would.
- The background was now truly transparent: 61% of the picture clear, the
  tank opaque.
- The drawing itself was unchanged: the outline still thin (about 11 px,
  0.7% of the width), the aerials and small detail still there. The
  background had been removed, not the tank redrawn.
- There was no margin: the tank filled 99% of the width and touched the
  bottom edge.

**The repair.** The second result was then fixed with a few lines of image
code, without going back to the generator:

1. the dark outline grown to about 23 px (1.4% of the width);
2. a dark rim added round the whole silhouette;
3. the tank re-centred on a 5:3 canvas at 86% of its width.

Before the repair the tank was soft at 60 px and nearly merged with the
desert at 30 px. After it, the tank was crisp at both sizes on all three
counter colours: the skirt openings showed at 60 px, and at 30 px the hull,
turret and gun were distinct. The aerials were the one thing still wrong, a
stray vertical line at 60 px.

**What follows from this.** A generator gives the right shape and framing but
not the line weight, the margin or, reliably, the transparent background. A
clean-up step supplies those. So the art can be generated at the level of
detail the generator likes, and a small tool can turn any such picture into
counter sprites.

## The clean-up tool (proposed, not built)

Given one generated picture, it would:

1. clear the background (by transparency if the file has it, otherwise by
   keying out the colour that touches the border);
2. make every pixel either clear or solid;
3. thicken the outline to a set share of the width, and rim the silhouette;
4. optionally erase lines too thin to survive, such as aerials;
5. centre the subject on a 5:3 canvas with its margin;
6. write the master at 480 × 288 and the two sizes the screen uses, 60 × 36
   and 30 × 18, into `art/counters/`.

The screen would load a sprite from `art/counters/` when one exists and draw a
NATO-style symbol when it does not, so the game is playable before the art is
complete.

## The drawn set

`python -m countergen` draws all eighteen pictures and writes them to
`art/counters/`: `<nation>_<kind>.svg`, a true vector drawing, and the
`.png` made from it, which is what the screen loads. Each is built from a few
shapes written out in `countergen/__init__.py`, so the set shares one outline
weight, one ground line and one palette, and a picture is changed by changing
a few numbers. They were drawn from the known shapes of the vehicles, not
from any other game's art.

| Kind | Commonwealth | German | Italian |
| --- | --- | --- | --- |
| `armour` | Crusader | Panzer III, short 50 mm gun | M13/40 |
| `foot` | three riflemen, flat-brimmed helmet, shorts | three riflemen, flared helmet | three riflemen, domed helmet |
| `guns` | 25-pounder | 88 mm Flak on its mount | 75 mm field gun, spoked wheel |
| `motorised` | Bedford 3-ton lorry | Opel Blitz | Lancia 3Ro |
| `recon` | Marmon-Herrington | SdKfz 222 | AB 41 |
| `hq` | staff car with a pennant | Kübelwagen with a pennant | Fiat staff car with a pennant |

- Plain colours, no camouflage and no markings. The nation is told by the
  counter's face, the kind by the outline.
- Three men, not one, stand for the infantry: one figure in a 5:3 space is
  about 18 px high in play and does not read.
- A headquarters is told from a lorry by its pennant: red on the drawn
  pictures, the owner's colours on the Axis cars (below).
- These are likenesses at 36 px, not scale drawings. Which vehicle stands for
  which arm is a choice: German divisional artillery was mostly 105 mm
  howitzers, and a Matilda or Stuart brigade shows a Crusader.
- A picture from an artist goes in `art/counters/artist/` under the same
  name, `<nation>_<kind>.png`, on the same 480 × 288 canvas. The screen takes
  it before the drawn one, so the drawn set stays whole underneath and fills
  whatever the artist has not done.

### The artist's first sheets (a stopgap)

An artist's first trial came as two sheets, each a single picture of eighteen
sprites (`art/counters_sheet_1.png`, `art/counters_sheet_1_1.png`): infantry,
light tank, medium tank, artillery, anti-tank gun and transport for each
nation. They are richer than the drawn set and read as well at 47 px, so
`python -m countergen cut` cuts twelve of them into `art/counters/artist/`:
infantry, tank, gun and lorry for each nation. It clears the tip of a
neighbour's gun where two sprites touch, sets three of the one soldier in
file, and fits each to the canvas and ground line of the drawn set.

What this leaves, until the pictures come one to a file and drawn to the
brief:

- The sheets have no armoured car and no headquarters. The German and Italian
  headquarters now come one to a file (below), so four counters, the three
  armoured cars and the British headquarters, show the drawn pictures, in a plainer style beside the artist's.
- The German gun is the sheet's anti-tank gun: its German "artillery" is an
  assault gun, not a gun on a carriage. The German soldier comes from the
  first sheet, the only one that gives him his own cap.
- Not checked against a source, and doubtful: the striped camouflage on the
  British and Italian tanks, the British gun (spoked wooden wheels, so not a
  25-pounder), and which marks of tank are shown. The British tank is a
  Matilda, not the Crusader the drawn set has.
- Where they come from: generated by an AI image tool, the owner said on
  19 October 2026, and not under anyone's copyright. Which tool was used is
  not recorded.

## The counter as a thing

The counter is drawn to look like a piece lying on the map, not a flat
square (`Painter.face` and `Painter.shadow` in `screen/draw.py`): its face is
lit from the top left, lighter at the top than the bottom, with a bevelled
edge, a little grain and a soft shadow; a counter taken up casts a longer
one. The owner chose this, in October 2026, over tilting the board: a mock
showed that a tilt made the numbers harder to read and the piles more
crowded for the sake of mood alone. The face, the picture, the strength
number and the two bars are laid out as shares of the counter's side, so
they hold at every zoom. The face and the panel's tile are cut from the same
slab (`slab` in `screen/draw.py`).

## The tile layout

In October 2026 the owner showed the counters of a published tactical board
game as a look he liked: a large picture in the middle, the name along the
top, a coloured notch, and numbers in fixed places round the picture. That
game's numbers (range, armour to the front and the flank, the cost of
firing) describe one tank or one squad and have no meaning for a brigade, so
none of them was taken; `DESIGN.md` also holds a counter to a symbol, a name
and at most three numbers. What was taken is the arrangement, and every
figure shown is one this game's engine already keeps. A mock
(`logs/counter-tile-mock.png`, not kept in the repository) offered a
nation-coloured face and a pale one; the owner chose the nation colour for
the map, where three pale counters could hardly be told apart at 47 px, and
the pale face for the panel.

**On the map.**

- A unit of a division carries the division's **notch** in the middle of its
  top edge, at every size from 22 px: one colour to each division of a side,
  given in the order of the divisions' HQs (`DIVISION` in `screen/theme.py`,
  `Session.division`). A unit of no division (a corps HQ, a garrison, an army
  tank brigade) has none. There are ten colours and the Axis has ten
  divisions in Crusader; an eleventh would repeat the first. Some are weak
  against one face (lime on the Italian green, pale blue on the Commonwealth
  blue), which is why the notch has a dark outline.
- At the closest zoom only (a counter of `NAMED` = 90 px or more; the one
  taken up, being drawn larger, is named a zoom step sooner) the counter also
  carries the unit's **short name** along the top and, for the player's own
  units, its **pace** beside the strength: an arrowhead and the hexes of open
  desert it can cross in a turn in this turn's weather (a group's is its
  slowest member's, `docs/RULES.md` 9.1.1, 20.2.6, 21.4.3). The picture is a
  little smaller to make room, and the tags for the pile and the order sit
  above the top edge so that they do not cover the name.
- The strength on the counter is still in steps, as before; the tile gives it
  in tanks, men or guns.

**Short names** come from a rule, not from the scenario file (`short` and
`BRIEF` in `screen/theme.py`): "4th Armoured Brigade" is "4 Armd Bde",
"Panzer-Regiment 8" is "Pz.Rgt. 8", "132 Reggimento carri" is "132 Carri". A
test holds every unit of Crusader to the width of the counter. The British
and German forms are meant to be those armies' own abbreviations, written
from memory and **not checked against a source**; the Italian ones simply
keep the number and the arm.

**In the panel.** The unit taken up by itself is shown as one tile, as wide
as the panel's text and 210 px high (`Painter.tile`): a pale face with a band
of the nation's colour holding the name and the division, the picture, and
round it the strength in real terms, the pace, the morale
level with its word, the fuel in kilometres (vehicles only), the experience
as one to three pips, and the stores as a bar. Each figure has its word under
it, and pointing at one gives the fuller figure. The pace's word is "moves"
(the owner's, 10 October 2026): the hexes of open desert the unit can cross
in a turn, which its tip says in full. The nation's flag is in the top right
corner of the band (`flag` in `screen/draw.py`, 42 by 28 px), and a name too
long to sit centred clear of it moves left. Which flag is told from the
unit's name, or failing that its division's (`flag_of` and `CONTINGENT` in
`screen/theme.py`): a rule, like the short names, and not scenario data. See
"The flags" below. When more of the player's units are in the hex, a chip
under the orders, to the right of "Back to group" and off the tile (the
owner's place for it), says which this is ("3 of 6") with an arrow each way. The
arrows, the mouse wheel or Up and Down with the pointer on the tile, and Page
Up and Page Down anywhere, go through them: each group, then each of its
units by itself (`Session.stack`). The tile is the unit's
header, and the orders are directly under it (`HEAD_Y` and `ORDERS_Y` in
`screen/layout.py`); it replaces the small card and name that were the header
and the four bars that were under the orders. It was first put under the
orders, where it left room for hardly one report. A group taken up is shown in the same place above the orders as its
**order of battle** (`Painter.roster`, the owner's choice of 19 October 2026,
from the second tile example): its HQ's card across the top in the nation's
colour, with the flag, the group's name, a line saying how many units one
order moves, and the pencil to rename it; and under it a small tile for each
of its units, joined to the card by a line as on a chart of a formation. A
tile carries the unit's short name in its nation's band, its picture, its
strength in real terms and the trouble mark (`Painter.mini_tile`). Up to four
units sit in one row, more in two. A click on the card takes up the HQ by
itself, a click on a tile that unit. A group with no HQ in it has the card
without a unit behind it. A unit chosen from its
group has a "Back to group" button under the orders, which is also what says
it came from a group; the owner moved it there from the tile's corner.

## Decided since (October 2026)

- **Pictures are the default**, NATO-style symbols the option (F3). Until
  there is art, the screen draws its own simple pictures (`screen/pictures.py`).
- **Contrast comes from the counter face:** Commonwealth blue, German dark
  grey with pale marks, Italian green. These are this game's own colours.
- A sprite file in `art/counters/<nation>_<type>.png` replaces the drawn
  picture for that nation and arm.

## Open decisions

- **Sprites or NATO symbols.** `DESIGN.md` §4.2 and §12 say NATO-style
  symbols, generated, with no hand-drawn art needed. Sprites are more work
  and more charm. A fallback to symbols lets both exist.
- **Where the contrast comes from.** Either each vehicle is drawn dark enough
  to stand out from the desert, or vehicles stay light and each sits on a
  counter face in its nation's colour (for example khaki-brown for the
  Commonwealth, field grey for the Germans, grey-green for the Italians). The
  second lets one sprite style serve all three nations, and is the
  recommendation.
- **How specific a sprite is.** One sprite per unit type per nation (about
  eighteen), or particular vehicles for particular formations (a Matilda for
  an army tank brigade, a Crusader for an armoured brigade). The complexity
  budget (`DESIGN.md` §14.1) allows a counter a symbol, a name and at most
  three numbers; the picture is the symbol, so either fits.

## Art still required

One brief for each of the eighteen counter pictures, in `art/`, named
`art_required_<nation>_<kind>.md` (the owner's request of 19 October 2026,
for a commercial standard). Each says the file to deliver, why it is
needed, the subject and how sure its history is, an exact prompt, the
reference images by address (the game's own pictures on GitHub for the
style, Wikipedia and Wikimedia Commons for the real vehicle's shape) and the
checks before it is accepted, including its origin in writing.

| Priority | Pictures |
| --- | --- |
| 1, missing | the three armoured cars and the British headquarters (the German and Italian ones are in use, below) |
| 2, the wrong subject | the British tank (a Matilda, not a Crusader), the British gun (not a 25-pounder), the German gun (an anti-tank gun) |
| 3, redrawn one to a file | the other nine, now cut from the two sheets |

Three subjects are not settled and say so: the British and Italian staff
cars, and whether the AB 41 had reached Libya by November 1941. The briefs
ask for no markings, crosses or numbers, which the artist's sheets have:
at counter size they do not read, and the nation is told by the counter's
face and the tile's flag.

**The Axis headquarters.** The owner put `art/WWII Desert Kübelwagen Icon.png`
forward on 19 October 2026, on a checkerboard painted into the picture, and on
20 October 2026 two pictures on real transparency in `art/axis_hq_cars/`:
`german_hq.png`, the same Kübelwagen (Type 82, hood down, a black pennant at
the rear), and `it_hq.png`, an Italian staff car with its hood up and a small
tricolour pennant at the front. Both are AI-generated by the owner, side on
and facing right, on the 480 × 288 canvas with their wheels on the ground
line, and both read beside their nation's lorry at 43, 86 and 180 pixels.
`python -m countergen cut` trims each to its one piece and fits it to the
canvas as `art/counters/artist/de_hq.png` and `it_hq.png`. The first
Kübelwagen file is no longer used.

Not settled, and left as drawn: the pennants are black and tricolour, not
the red the brief asks for, and the tricolour is faint at 43 pixels. Which
car the Italian picture is was not checked: it looks like a 1930s tourer of
the Fiat 508 kind, which the brief names as likely but unconfirmed.

## The flags

The owner asked on 10 October 2026 for each Commonwealth country's flag as it
was at the time. Looked up that day in Wikipedia's article on each flag
(facts only). The drawings are this game's own, made by `flag` in
`screen/draw.py` from each flag's description, and simplified for 42 by 28
pixels.

| Flies | Flag | Found | How sure |
| --- | --- | --- | --- |
| United Kingdom | the Union Flag | | not in doubt. The red saltire is drawn plain, not counterchanged |
| New Zealand | the blue ensign with four red stars edged white | "Flag of New Zealand": in use since 1869, by law from 1902 | the flag is right for 1941. The Union Flag was the "superior flag" until 1965 and was flown above it |
| Australia | the blue ensign with the Commonwealth Star of seven points and the Southern Cross | "Flag of Australia": the seventh point was added in 1908; "From 1911 it was the saluting flag of the Australian army" | right for the army in 1941. It was declared the national flag only in 1953. No Australian unit is in Crusader, so it is not yet seen in play |
| India | the red ensign with the Star of India under a crown | "Flag of India": this flag stood for India abroad | **which flag the Indian Army served under was not found.** The star is simplified |
| Union of South Africa | orange, white and blue with three small flags on the white | "Flag of South Africa (1928–1994)": from 1928 to 1957 this flag and the Union Flag had equal standing | right for 1941. The three small flags are only suggested at this size |
| Poland | white over red | | from memory, unchecked |
| Italy | the tricolour with the arms of Savoy | | from memory, unchecked |
| Germany | the army's black cross | | **not the flag of 1941**, which carried the swastika. A choice made for the shops and the laws a published game meets; kept by the owner on 19 October 2026 |

Two things for the owner to know. South Africa's flag of 1928 is the right
one for 1941, and in South Africa today its gratuitous display is unlawful
(Equality Court, 2019, upheld on appeal in 2023), with exceptions that include
artistic and historical use. The owner chose the period flag on 19 October
2026. And the rule gives a whole division one flag:
the British regiments that served in the Indian and other divisions are not
told apart, because the game's units are brigades.
