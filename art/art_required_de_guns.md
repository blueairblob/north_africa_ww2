# Art required: German artillery

**Deliver:** `art/counters/artist/de_guns.png`, one picture in one file.

**Status:** redo: the stopgap is the sheet's anti-tank gun; the sheet's own German artillery is an assault gun, not a gun on a carriage.

**Priority:** 2 (1 missing from the game, 2 the wrong subject, 3 redrawn to the brief).

## The subject

A single 8.8 cm Flak cannot stand for all six German `guns` formations:
divisional artillery regiments principally need a 10.5 cm leFH 18 field
howitzer, while anti-tank battalions, mixed garrisons and groupings need
separate historically checked representative subjects. Keep rule `type=guns`
unchanged and use `counter_art` variants after verifying the formations'
equipment and dates in primary order-of-battle evidence.

*How sure:* The broad distinction is known; exact gun allocation within the
mixed groupings has not yet been verified.

## The prompt

For an image generator, or as the brief for an artist.

```
A single gun for a hex wargame counter, North African desert campaign, November 1941.

Subject: a 10.5 cm leFH 18 field howitzer on its shielded two-wheel carriage, barrel raised a little. Strict side profile, facing right, the whole subject in frame, standing on one level baseline.

Style: match the reference pictures given with this prompt: a painted illustration with a very bold dark-brown outline of even weight, three or four tones of one colour, a little wear and dust on the surfaces, lit softly from the upper left. No photographic shading, no cast shadow, no ground, no scenery.

Colour: yellow-brown desert sand, with dark grey-brown for the barrel, tyres and metal. No tractor, no crew.

Detail: it must stay recognisable at 43 x 26 pixels. Keep the shapes that tell it apart bold and simple: the barrel, the shield, the wheels or platform and the trail; the barrel at least as thick as the outline. No aerials, rivets, bolts, buckles or small hatches.

No markings: no crosses, roundels, numbers, lettering, unit signs or camouflage patterns. No crew, no figures.

Composition: canvas 480 x 288 pixels (5:3). The subject fills about 85 per cent of the width, centred, with its wheels, tracks or feet on a line 40 pixels above the bottom edge, and nothing that matters in the corners.

Background: fully transparent PNG with a real alpha channel. Not white, not black, not a checkerboard pattern.

One subject only. No border, no frame, no text.
```

## Reference images

Style (this game's own pictures; the new one must sit beside them as one set):

- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/de_armour.png (the German tank already in the game: match its outline, finish and palette)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/de_motorised.png (the German lorry already in the game: the same)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/de_guns.png (what is in the game now: the stopgap this replaces)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/de_guns.png (the plain picture the game draws for itself: the pose and the canvas, not the style)

Shape (photographs and drawings of the real thing; for its shape and proportions only, never to trace or copy):

- https://en.wikipedia.org/wiki/8.8_cm_Flak_18/36/37/41
- https://commons.wikimedia.org/wiki/Category:8.8_cm_Flak_18
- https://commons.wikimedia.org/wiki/Category:10.5_cm_leFH_18

## Checks before it is accepted

- 480 x 288 PNG with a real alpha channel. A checkerboard painted into the picture is not transparency.
- Facing right; wheels, tracks or feet on the line at y = 248; the subject within 410 x 214, centred.
- Told apart at 43 x 26 pixels from the other five pictures of the same nation, and from the same kind of the other two nations.
- The same outline weight, finish and light as the style references.
- No markings, lettering, crew or ground.
- Its origin in writing: who made it, with what tool, and that it may be published in this public repository and used in a commercial game. The repository is clean-room (`docs/CLEAN_ROOM.md`): nothing from another game's art.
- Saved under the name above, it replaces the game's own picture at once: no code changes (`docs/COUNTERS.md`).
