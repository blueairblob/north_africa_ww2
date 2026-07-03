# Escarpment tile — extracted from a real gameplay screenshot

Source: a person-supplied ZX Spectrum gameplay screenshot (256x192 pixels,
exact hardware resolution — Gazala, "MAY 27th 1942", unit "201st Guards
Brigade" selected). Not a mockup, not an emulator UI capture with chrome —
the raw 256x192 screen bitmap.

## What it confirmed

BUILD_SPEC.md §8 characterised the paper table (0xD80E) as "mostly PAPER 6
= desert yellow" with only sea (§5.1/§8 more generally) as another
confirmed distinct case. This screenshot showed that's incomplete:
**escarpment terrain (types 2/3 in data/terrain_authentic.json's legend)
renders as a distinct 8x8 tile — red ink hash pattern on desert paper —
not flat desert.**

## Method

The whole screenshot only contains 6 distinct RGB values (consistent with
ZX Spectrum attribute-clash colour limits):

| RGB | Role |
|---|---|
| (210,210,0) | desert paper (yellow) |
| (223,0,0) | escarpment ink (red) |
| (0,0,162) | British unit ink (non-bright blue) |
| (0,0,0) | German unit ink (black) — also UI panel background |
| (231,0,182) | Italian unit ink (magenta) |
| (202,202,202) | UI text (white/grey) — UI panel only, x≥184px |

The map viewport occupies x=0..176px — exactly 22 cells at 8px/cell,
independently confirming BUILD_SPEC §8's 22×22 viewport claim. The
right-hand UI panel (order menu, unit name) occupies x=176..256px.

Within the viewport, an 8×8-pixel cell containing only (210,210,0) and
(223,0,0) was sampled directly:

```
.##.....
#..#....
....#..#
.....##.
.##.....
#..#....
....#..#
.....##.
```

This 8-row pattern is periodic with period 4, i.e. genuinely an 8-byte
tile bitmap (matching graphics.json's documented "8 bytes per 8x8 tile,
MSB=leftmost pixel" format) that repeats twice per cell:

```
row 0: .##..... = 01100000 = 0x60
row 1: #..#.... = 10010000 = 0x90
row 2: ....#..# = 00001001 = 0x09
row 3: .....##. = 00000110 = 0x06
(repeats)
```

**`ESCARPMENT_TILE_BYTES = (0x60, 0x90, 0x09, 0x06, 0x60, 0x90, 0x09, 0x06)`**

Unit counters were also confirmed to occupy a 16×16px block (2×2 cells @
8px), independently matching BUILD_SPEC §3.2's 2×2 footprint claim.

## What's still open

Only escarpment (types 2/3) was directly observed in this one scene near
Gazala. The other 14 terrain codes' paper/ink are still unconfirmed — see
reference/prospects.md #12. If further gameplay screenshots covering other
terrain (towns, ports, oases, rough ground) become available, the same
extraction method (isolate 8×8 cells with exactly 2 colours, decode as a
bitmap) applies directly.

## Implementation

`desert_rats/render/image.py`'s `ESCARPMENT_TILE_BYTES`, `ESCARPMENT_INK`,
and `NATION_COLOUR` — see that module's docstring and NOTES.md for the
full account of what changed and why.
