# Art required: German reconnaissance

**Deliver:** `art/counters/artist/de_recon.png`, one picture in one file.

**Status:** painted Sd.Kfz. 222 representative for both German reconnaissance
formations. A c. 1941 Australian War Memorial photo (P08802.015) confirms
the vehicle's period appearance. An archival-derived 30 December 1941 table lists 222s and 231/232
armoured cars in **both** Abteilungen 3 and 33; this does **not** establish
their 18 November mix or validate the scenario's 30-car counts. The table
has internal numerical errors; see `docs/SOURCES.md`. Both units have
dated picture hover notes.

**Priority:** painted subject in use; verify the 18 November unit returns.

## The subject

The light armoured car of the German reconnaissance battalions.

*How sure:* Period Sd.Kfz. 222 use is photographed; both battalions are
listed with 222 and heavier cars on 30 December, not 18 November. The
original German return and opening-day model mix remain unresolved
(`docs/SOURCES.md`).

## The prompt

For an image generator, or as the brief for an artist.

```
A single vehicle for a hex wargame counter, North African desert campaign, November 1941.

Subject: an SdKfz 222 light armoured car: four wheels, a sloped many-sided hull and an open turret. Strict side profile, facing right, the whole subject in frame, standing on one level baseline.

Style: match the reference pictures given with this prompt: a painted illustration with a very bold dark-brown outline of even weight, three or four tones of one colour, a little wear and dust on the surfaces, lit softly from the upper left. No photographic shading, no cast shadow, no ground, no scenery.

Colour: yellow-brown desert sand, with dark grey-brown for the tyres and metal.

Detail: it must stay recognisable at 43 x 26 pixels. Keep the shapes that tell it apart bold and simple: the armoured hull, the turret and the wheels. No aerials, rivets, bolts, buckles or small hatches.

No markings: no crosses, roundels, numbers, lettering, unit signs or camouflage patterns. No crew, no figures.

Composition: canvas 480 x 288 pixels (5:3). The subject fills about 85 per cent of the width, centred, with its wheels, tracks or feet on a line 40 pixels above the bottom edge, and nothing that matters in the corners.

Background: fully transparent PNG with a real alpha channel. Not white, not black, not a checkerboard pattern.

One subject only. No border, no frame, no text.
```

## Reference images

Style (this game's own pictures; the new one must sit beside them as one set):

- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/de_armour.png (the German tank already in the game: match its outline, finish and palette)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/de_motorised.png (the German lorry already in the game: the same)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/de_recon.png (the plain picture the game draws for itself: the pose and the canvas, not the style)

Shape (photographs and drawings of the real thing; for its shape and proportions only, never to trace or copy):

- https://en.wikipedia.org/wiki/Sd.Kfz._222
- https://commons.wikimedia.org/wiki/Category:Sd.Kfz._222

## Checks before it is accepted

- 480 x 288 PNG with a real alpha channel. A checkerboard painted into the picture is not transparency.
- Facing right; wheels, tracks or feet on the line at y = 248; the subject within 410 x 214, centred.
- Told apart at 43 x 26 pixels from the other five pictures of the same nation, and from the same kind of the other two nations.
- The same outline weight, finish and light as the style references.
- No markings, lettering, crew or ground.
- Its origin in writing: who made it, with what tool, and that it may be published in this public repository and used in a commercial game. The repository is clean-room (`docs/CLEAN_ROOM.md`): nothing from another game's art.
- Saved under the name above, it replaces the game's own picture at once: no code changes (`docs/COUNTERS.md`).
