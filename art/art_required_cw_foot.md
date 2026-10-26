# Art required: British and Commonwealth foot infantry

**Deliver:** `art/counters/artist/cw_foot.png`, one picture in one file.

**Status:** in use: original painted Brodie-helmeted tropical-dress rifleman, repeated three times and fitted to the 480 × 288 canvas. Representative of Commonwealth infantry; not a claim about each formation's uniform.

**Priority:** 3 (1 missing from the game, 2 the wrong subject, 3 redrawn to the brief).

## The subject

Infantry in 1941 desert dress. Three men, not one: one figure is too small to read on a counter.

*How sure:* Representative 1941 desert dress; exact uniform of each formation not verified.

## The prompt

For an image generator, or as the brief for an artist.

```
A single group of three soldiers for a hex wargame counter, North African desert campaign, November 1941.

Subject: three British riflemen in file, marching right: Brodie steel helmets, khaki drill shirts and shorts, webbing, rifles at the slope. Strict side profile, facing right, the whole subject in frame, standing on one level baseline.

Style: match the reference pictures given with this prompt: a painted illustration with a very bold dark-brown outline of even weight, three or four tones of one colour, a little wear and dust on the surfaces, lit softly from the upper left. No photographic shading, no cast shadow, no ground, no scenery.

Colour: pale desert sand, with dark brown for boots, belts and rifles. Three men in file, the same man three times, evenly spaced.

Detail: it must stay recognisable at 43 x 26 pixels. Keep the shapes that tell it apart bold and simple: the helmet or cap, the rifle and the stride, the three men alike. No aerials, rivets, bolts, buckles or small hatches.

No markings: no crosses, roundels, numbers, lettering, unit signs or camouflage patterns.

Composition: canvas 480 x 288 pixels (5:3). The subject fills about 85 per cent of the width, centred, with its wheels, tracks or feet on a line 40 pixels above the bottom edge, and nothing that matters in the corners.

Background: fully transparent PNG with a real alpha channel. Not white, not black, not a checkerboard pattern.

One subject only. No border, no frame, no text.
```

## Reference images

Style (this game's own pictures; the new one must sit beside them as one set):

- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/cw_armour.png (the British and Commonwealth tank already in the game: match its outline, finish and palette)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/cw_motorised.png (the British and Commonwealth lorry already in the game: the same)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/cw_foot.png (what is in the game now: the stopgap this replaces)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/cw_foot.png (the plain picture the game draws for itself: the pose and the canvas, not the style)

Shape (photographs and drawings of the real thing; for its shape and proportions only, never to trace or copy):

- https://en.wikipedia.org/wiki/Brodie_helmet
- https://en.wikipedia.org/wiki/Lee%E2%80%93Enfield

## Checks before it is accepted

- 480 x 288 PNG with a real alpha channel. A checkerboard painted into the picture is not transparency.
- Facing right; wheels, tracks or feet on the line at y = 248; the subject within 410 x 214, centred.
- Told apart at 43 x 26 pixels from the other five pictures of the same nation, and from the same kind of the other two nations.
- The same outline weight, finish and light as the style references.
- No markings, lettering, crew or ground.
- Its origin in writing: who made it, with what tool, and that it may be published in this public repository and used in a commercial game. The repository is clean-room (`docs/CLEAN_ROOM.md`): nothing from another game's art.
- Saved under the name above, it replaces the game's own picture at once: no code changes (`docs/COUNTERS.md`).
