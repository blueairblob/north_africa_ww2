# Art required: British and Commonwealth armour

**Deliver:** `art/counters/artist/cw_armour.png`, one picture in one file.

**Status:** original painted Crusader in use for 22nd Armoured; a Stuart variant
serves 4th Armoured, an original four-road-wheel A13 variant serves 7th
Armoured. The old sheet-cut Matilda has been replaced with a new original
Matilda II for the two mixed army-tank brigades. Its Caunter-inspired
three-tone pattern is illustrative; exact brigade paintwork remains open.

**Priority:** fulfilled for the Crusader subject; mixed brigades need further historical checks.

## The subject

The British armoured brigades of 7th Armoured Division fought Crusader (November 1941) with mixed equipment: the Queen's Royal Hussars Museum estimates A13 cruisers formed roughly half of 7th Armoured Brigade; 22nd Armoured used Crusaders; the army tank brigades had Matildas and Valentines, and 4th Armoured Brigade American Stuarts. A single picture cannot accurately stand for all British armour;
`counter_art` chooses a representative type per formation.

*How sure:* The type and the operation are well known; which mark is shown does not matter at counter size.

## The prompt

For an image generator, or as the brief for an artist.

```
A single vehicle for a hex wargame counter, North African desert campaign, November 1941.

Subject: a Crusader cruiser tank (A15, Mark I or II), with its 2-pounder gun in a low, many-sided turret and five large road wheels a side. Strict side profile, facing right, the whole subject in frame, standing on one level baseline.

Style: match the reference pictures given with this prompt: a painted illustration with a very bold dark-brown outline of even weight, three or four tones of one colour, a little wear and dust on the surfaces, lit softly from the upper left. No photographic shading, no cast shadow, no ground, no scenery.

Colour: pale desert sand, with dark grey-brown for the tracks and the gun.

Detail: it must stay recognisable at 43 x 26 pixels. Keep the shapes that tell it apart bold and simple: the hull, the turret, the length of the gun and the run of road wheels; each track one dark band; the gun barrel at least as thick as the outline. No aerials, rivets, bolts, buckles or small hatches.

No markings: no crosses, roundels, numbers, lettering, unit signs or camouflage patterns. No crew, no figures.

Composition: canvas 480 x 288 pixels (5:3). The subject fills about 85 per cent of the width, centred, with its wheels, tracks or feet on a line 40 pixels above the bottom edge, and nothing that matters in the corners.

Background: fully transparent PNG with a real alpha channel. Not white, not black, not a checkerboard pattern.

One subject only. No border, no frame, no text.
```

## Reference images

Style (this game's own pictures; the new one must sit beside them as one set):

- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/cw_armour.png (the British and Commonwealth tank already in the game: match its outline, finish and palette)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/cw_motorised.png (the British and Commonwealth lorry already in the game: the same)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/cw_armour.png (what is in the game now: the stopgap this replaces)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/cw_armour.png (the plain picture the game draws for itself: the pose and the canvas, not the style)

Shape (photographs and drawings of the real thing; for its shape and proportions only, never to trace or copy):

- https://en.wikipedia.org/wiki/Crusader_tank
- https://commons.wikimedia.org/wiki/Category:Crusader_tank

## Checks before it is accepted

- 480 x 288 PNG with a real alpha channel. A checkerboard painted into the picture is not transparency.
- Facing right; wheels, tracks or feet on the line at y = 248; the subject within 410 x 214, centred.
- Told apart at 43 x 26 pixels from the other five pictures of the same nation, and from the same kind of the other two nations.
- The same outline weight, finish and light as the style references.
- No markings, lettering, crew or ground.
- Its origin in writing: who made it, with what tool, and that it may be published in this public repository and used in a commercial game. The repository is clean-room (`docs/CLEAN_ROOM.md`): nothing from another game's art.
- Saved under the name above, it replaces the game's own picture at once: no code changes (`docs/COUNTERS.md`).
