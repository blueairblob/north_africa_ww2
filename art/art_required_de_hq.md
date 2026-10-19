# Art required: German headquarters

**Deliver:** `art/counters/artist/de_hq.png`, one picture in one file.

**Status:** in use, from the owner's AI-generated picture `art/WWII Desert Kübelwagen Icon.png`, cut from its painted checkerboard by `python -m countergen cut`. Needed only if it is to be redrawn: its finish is flatter than the artist's other pictures, and its pennant is black where the game's other headquarters fly red.

**Priority:** none while the present picture serves (1 missing from the game, 2 the wrong subject, 3 redrawn to the brief).

## The subject

A headquarters is told from a lorry by its pennant.

*How sure:* Wikipedia confirms the Type 82 as a command car but not its date in North Africa; it is commonly photographed with the Afrika Korps. Not confirmed for 1941 in the sources read.

## The prompt

For an image generator, or as the brief for an artist.

```
A single vehicle for a hex wargame counter, North African desert campaign, November 1941.

Subject: a Kübelwagen (Volkswagen Type 82), hood down, spare wheel on the front, with a small pennant on a short staff at the rear. Strict side profile, facing right, the whole subject in frame, standing on one level baseline.

Style: match the reference pictures given with this prompt: a painted illustration with a very bold dark-brown outline of even weight, three or four tones of one colour, a little wear and dust on the surfaces, lit softly from the upper left. No photographic shading, no cast shadow, no ground, no scenery.

Colour: yellow-brown desert sand, with dark grey-brown for the tyres and metal. A small red pennant on a short staff at the rear, large enough to read at counter size.

Detail: it must stay recognisable at 43 x 26 pixels. Keep the shapes that tell it apart bold and simple: the body, the wheels and the pennant. No aerials, rivets, bolts, buckles or small hatches.

No markings: no crosses, roundels, numbers, lettering, unit signs or camouflage patterns. No crew, no figures.

Composition: canvas 480 x 288 pixels (5:3). The subject fills about 85 per cent of the width, centred, with its wheels, tracks or feet on a line 40 pixels above the bottom edge, and nothing that matters in the corners.

Background: fully transparent PNG with a real alpha channel. Not white, not black, not a checkerboard pattern.

One subject only. No border, no frame, no text.
```

## Reference images

Style (this game's own pictures; the new one must sit beside them as one set):

- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/de_armour.png (the German tank already in the game: match its outline, finish and palette)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/de_motorised.png (the German lorry already in the game: the same)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/de_hq.png (what is in the game now, once committed)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/de_hq.png (the plain picture the game draws for itself: the pose and the canvas, not the style)

Shape (photographs and drawings of the real thing; for its shape and proportions only, never to trace or copy):

- https://en.wikipedia.org/wiki/Volkswagen_K%C3%BCbelwagen
- https://commons.wikimedia.org/wiki/Category:Volkswagen_K%C3%BCbelwagen

## Checks before it is accepted

- 480 x 288 PNG with a real alpha channel. A checkerboard painted into the picture is not transparency.
- Facing right; wheels, tracks or feet on the line at y = 248; the subject within 410 x 214, centred.
- Told apart at 43 x 26 pixels from the other five pictures of the same nation, and from the same kind of the other two nations.
- The same outline weight, finish and light as the style references.
- No markings, lettering, crew or ground (the pennant is the one exception).
- Its origin in writing: who made it, with what tool, and that it may be published in this public repository and used in a commercial game. The repository is clean-room (`docs/CLEAN_ROOM.md`): nothing from another game's art.
- Saved under the name above, it replaces the game's own picture at once: no code changes (`docs/COUNTERS.md`).
