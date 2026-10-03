# How the map is generated

`python -m mapgen all` runs three steps.

**1. Fetch** (`mapgen/fetch.py`) downloads, once, into `cache/` (not committed):
119 elevation tiles and the Natural Earth 1:10m land polygons.

**2. Build** (`mapgen/build.py`) lays the data on a 0.5 km grid and derives each
hex from it. The rules are a handful of named numbers at the top of the file:

| Rule | Value | Meaning |
| --- | --- | --- |
| `LAND_SHARE` | 0.5 | a hex is land if at least half of it is |
| `ROUGH_SLOPE` | 30 m/km | mean slope from which a hex is rough going |
| `BELOW_SEA` | −25 m | deep below sea level: depression (the oases are shallower and stay passable) |
| `SCARP_DROP` | 28 m | height difference across a hex edge… |
| `SCARP_STEP` | 9 m | …with at least this much of it within half a kilometre (a cliff, not a ramp)… |
| `SCARP_PROFILES` | 3 of 5 | …on most of the lines measured across the edge |
| `BROKEN_SIDES` | 3 | a hex with this many escarpment edges is rough ground instead |
| `ROUTE_COST`, `SCARP_COST` | 1 / 1.6, +4 | how routes weigh desert, rough ground and climbing an escarpment |
| `DRAWN_KM` | 5 km | a hand-drawn escarpment replaces the found edges this close to its line |
| `PASS_KM` | 6 km | a named pass must be this close to an escarpment edge |

Then: stray single escarpment edges are dropped (an escarpment is a line);
places from `data/features.json` are put in their hexes; each route is found
over the ground between the places it names (least cost); and wherever a route
crosses an escarpment edge, that edge becomes a pass.

## What is drawn by hand

The rules measure the ground across each hex edge, so an escarpment that runs
through the middle of a hex can be missed and leave a gap. Where that matters,
`data/features.json` says where the escarpment is:

- `escarpments`: a named line of latitude/longitude points. It is laid on the
  hex edges it runs between (so it is always unbroken) and replaces whatever the
  rules found within `DRAWN_KM` of it. The high side is the higher hex.
- `passes`: a named point. It becomes the nearest escarpment edge. Routes climb
  at a named pass for free, so they go to it instead of making a pass of their own.

So far this is done for the **Sollum escarpment**: traced along the steepest
ground in the elevation data from the sea at Sollum south-east for about 60 km,
to where it turns north and fades into a slope. Its passes are **Sollum Pass**
(the coast road) and **Halfaya Pass** (a track up to Sidi Omar); they are
neighbouring edges of the same hex below the cliff. East of the last of them the
only way up is round the end.

**3. Render** (`mapgen/render.py`) draws `map.png` for inspection.

The same inputs always give the same map: there is nothing random in it.

## The file: `data/map.json`

- `terrain`: one string per map row; `~` sea, `.` desert, `^` rough, `v` depression, `s` sand sea.
- `elevation`: mean height of each hex in metres, by row.
- `escarpments`: `[col, row, direction, high side]` — the edge of hex (col, row)
  in direction 1 NE, 2 SE or 3 S; high side 0 = this hex, 1 = the neighbour.
- `passes`: the edges where an escarpment can be climbed: `name` (null where a
  route made the pass and it has no name), `col`, `row`, `side` (the direction).
- `routes`: name, kind (road / track / rail) and the hexes in order.
- `places`: name, kind (port / town / oasis / site), hex, coordinates.

Hexes are flat-topped; odd columns sit half a hex lower.

## Known limitations

- **Other escarpments** (Gazala–Tobruk, Sidi Rezegh, the Jebel Akhdar, the
  Qattara rim) are as the rules found them: not yet checked edge by edge, and
  they may have gaps like the ones Sollum had.
- **The Halfaya track** is joined from the pass to Sidi Omar by least cost, and
  the pass positions come from general references, not period survey sheets.
- **Approximate sites.** About 15 period sites (marked `approx` in
  `features.json`) are placed from general references, to within a hex or so.
- **Tracks** are joined from place to place by least cost, not traced.
- **Sand sea** outline approximate; **coastal salt marshes** (e.g. at El Agheila)
  not marked yet.
- The thresholds above were tuned by eye on the Tobruk–Sollum area and the
  Jebel Akhdar.
