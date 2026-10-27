# Art required: Italian motorised infantry

**Deliver:** `art/counters/artist/it_motorised.png`, one picture in one file.

**Status:** original unmarked right-facing long-bed Italian lorry now replaces
the sheet cut with a prominent tricolour. The Lancia 3Ro is a representative
transport type, not a documented vehicle return for all four formations.

**Priority:** the marked sheet cut was replaced; vehicle allocations open.

**Bersaglieri variant (27 October 2026):** `art/counters/variants/it_bersaglieri_motorised.png`
distinguishes the 8th and 9th regiments from the ordinary 65th and 66th:
a separate original painted open-bed lorry with three feathered riders, not a
specific asserted truck model or an all-motorcycle regiment. The variant was
made by OpenAI image generation from only this project's own lorry and 7th
Bersaglieri counter as references; it was cropped by alpha and fitted to the
original 480 × 288 transparent canvas. Its original asset is usable by this
commercial game. Exact period transport mix remains to be documented.

## The subject

The heavy Italian lorry of the war.

*How sure:* Its use in Libya in 1941 is from general knowledge, not checked.

## The prompt

For an image generator, or as the brief for an artist.

```
A single vehicle for a hex wargame counter, North African desert campaign, November 1941.

Subject: a Lancia 3Ro heavy lorry with a canvas tilt over the load bed. Strict side profile, facing right, the whole subject in frame, standing on one level baseline.

Style: match the reference pictures given with this prompt: a painted illustration with a very bold dark-brown outline of even weight, three or four tones of one colour, a little wear and dust on the surfaces, lit softly from the upper left. No photographic shading, no cast shadow, no ground, no scenery.

Colour: pale sand with a faint grey-green cast, with dark grey-brown for the tyres and metal.

Detail: it must stay recognisable at 43 x 26 pixels. Keep the shapes that tell it apart bold and simple: the cab, the bonnet, the load bed under its tilt and the wheels. No aerials, rivets, bolts, buckles or small hatches.

No markings: no crosses, roundels, numbers, lettering, unit signs or camouflage patterns. No crew, no figures.

Composition: canvas 480 x 288 pixels (5:3). The subject fills about 85 per cent of the width, centred, with its wheels, tracks or feet on a line 40 pixels above the bottom edge, and nothing that matters in the corners.

Background: fully transparent PNG with a real alpha channel. Not white, not black, not a checkerboard pattern.

One subject only. No border, no frame, no text.
```

## Reference images

Style (this game's own pictures; the new one must sit beside them as one set):

- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/it_armour.png (the Italian tank already in the game: match its outline, finish and palette)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/it_motorised.png (the Italian lorry already in the game: the same)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/it_motorised.png (what is in the game now: the stopgap this replaces)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/it_motorised.png (the plain picture the game draws for itself: the pose and the canvas, not the style)

Shape (photographs and drawings of the real thing; for its shape and proportions only, never to trace or copy):

- https://en.wikipedia.org/wiki/Lancia_3Ro
- https://commons.wikimedia.org/wiki/Category:Lancia_3RO

## Checks before it is accepted

- 480 x 288 PNG with a real alpha channel. A checkerboard painted into the picture is not transparency.
- Facing right; wheels, tracks or feet on the line at y = 248; the subject within 410 x 214, centred.
- Told apart at 43 x 26 pixels from the other five pictures of the same nation, and from the same kind of the other two nations.
- The same outline weight, finish and light as the style references.
- No markings, lettering, crew or ground.
- Its origin in writing: who made it, with what tool, and that it may be published in this public repository and used in a commercial game. The repository is clean-room (`docs/CLEAN_ROOM.md`): nothing from another game's art.
- Saved under the name above, it replaces the game's own picture at once: no code changes (`docs/COUNTERS.md`).
