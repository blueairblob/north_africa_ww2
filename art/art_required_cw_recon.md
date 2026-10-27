# Art required: British and Commonwealth reconnaissance

**Deliver:** `art/counters/artist/cw_recon.png`, one picture in one file.

**Status:** original painted Marmon-Herrington Mk III-pattern car replaces
the older closed-turret generic candidate. A 2021 war-diary study identifies
Mk IIIs in the King's Dragoon Guards' A/B squadrons, part of composite unit
305; the other regiments' vehicle mix and the exact Mk III subvariant still require
formation returns. Unit 335, New Zealand Divisional Cavalry, uses a separate
painted Mark VI light-tank variant, not this default armoured car; its painted
carrier art remains as an unassigned, documented alternative.

**Priority:** the Mk II brief's mismatched subject is corrected; verify the
other components of unit 305 and the sprite's exact configuration.

## The subject

South African-built Marmon-Herrington Mk III cars served in KDG A/B squadrons in November 1941 (`docs/SOURCES.md`); the New Zealand Divisional Cavalry was a different formation. This is a *representative* for composite unit 305, not an established inventory of all its regiments.

*How sure:* Biermann's 2021 study, using contemporary war diaries, explicitly
identifies KDG A/B with Mk III cars; it does not establish all of unit 305's
fleet. The New Zealand official history *21 Battalion*, ch. 8 (events
of 29 November 1941), identifies Marmon-Herrington cars as the expected South
African recognition sign at Point 175, but the approaching cars proved to be
German in disguise. This establishes period recognition, **not** the exact
inventory of unit 305. The official history *Divisional Cavalry* records
light tanks and Bren carriers during November–December 1941, not a
Marmon-Herrington force; its Mark VI variant depicts only part of that group.

## The prompt

For an image generator, or as the brief for an artist.

```
A single vehicle for a hex wargame counter, North African desert campaign, November 1941.

Subject: a Marmon-Herrington Mark III armoured car: a four-wheeled, angular armoured hull with a visibly open octagonal turret, short Boys anti-tank rifle and coaxial Bren; no enclosed cupola or oversized gun. Strict side profile, facing right, the whole subject in frame, standing on one level baseline.

Style: match the reference pictures given with this prompt: a painted illustration with a very bold dark-brown outline of even weight, three or four tones of one colour, a little wear and dust on the surfaces, lit softly from the upper left. No photographic shading, no cast shadow, no ground, no scenery.

Colour: pale desert sand, with dark grey-brown for the tyres and metal.

Detail: it must stay recognisable at 43 x 26 pixels. Keep the shapes that tell it apart bold and simple: the armoured hull, the turret and the wheels. No aerials, rivets, bolts, buckles or small hatches.

No markings: no crosses, roundels, numbers, lettering, unit signs or camouflage patterns. No crew, no figures.

Composition: canvas 480 x 288 pixels (5:3). The subject fills about 85 per cent of the width, centred, with its wheels, tracks or feet on a line 40 pixels above the bottom edge, and nothing that matters in the corners.

Background: fully transparent PNG with a real alpha channel. Not white, not black, not a checkerboard pattern.

One subject only. No border, no frame, no text.
```

## Reference images

Style (this game's own pictures; the new one must sit beside them as one set):

- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/cw_armour.png (the British and Commonwealth tank already in the game: match its outline, finish and palette)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/artist/cw_motorised.png (the British and Commonwealth lorry already in the game: the same)
- https://raw.githubusercontent.com/blueairblob/north_africa_ww2/master/art/counters/cw_recon.png (the plain picture the game draws for itself: the pose and the canvas, not the style)

Shape (photographs and drawings of the real thing; for its shape and proportions only, never to trace or copy):

- https://saafmuseum.org.za/reconnaissance-car-marmon-herrington/ (South African museum car description; Mk II/III 4×4 use and armament)
- https://www.awm.gov.au/collection/C1282931 (Australian War Memorial catalogue identifies Mk III cars; photographed later in Java, **not** unit 305)

## Checks before it is accepted

- 480 x 288 PNG with a real alpha channel. A checkerboard painted into the picture is not transparency.
- Facing right; wheels, tracks or feet on the line at y = 248; the subject within 410 x 214, centred.
- Told apart at 43 x 26 pixels from the other five pictures of the same nation, and from the same kind of the other two nations.
- The same outline weight, finish and light as the style references.
- No markings, lettering, crew or ground.
- Its origin in writing: who made it, with what tool, and that it may be published in this public repository and used in a commercial game. The repository is clean-room (`docs/CLEAN_ROOM.md`): nothing from another game's art.
- Saved under the name above, it replaces the game's own picture at once: no code changes (`docs/COUNTERS.md`).
