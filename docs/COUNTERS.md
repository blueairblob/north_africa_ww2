# Counters: sizes, sprites and what the first trials showed

Notes on the design of the unit counters, from the first work on them
(October 2026). Nothing here is built yet: there is no counter art in the
repository and no screen to show it. `DESIGN.md` §4.2 still describes
NATO-style symbols; the idea explored here is a picture of the formation's
typical equipment instead — a tank, a gun, a lorry. Which of the two the game
uses is still to be decided (see "Open decisions").

## Sizes

Hexes are flat-topped, so a hex is 0.866 as high as it is wide. These sizes
were set for a screen with two zoom levels, the far one half the near one.
The screen as built zooms smoothly instead, from the whole map (about 20 px
to the hex) to 128 px, over a base map drawn at 64 px to the hex
(`python -m mapgen base`); a counter is always 0.64 of the hex. The two sizes
below are still the ones to test a sprite at: a close view and a far one.

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
