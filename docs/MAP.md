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

Then: stray single escarpment edges are dropped (an escarpment is a line);
places from `data/features.json` are put in their hexes; each route is found
over the ground between the places it names (least cost); and wherever a route
crosses an escarpment edge, that edge becomes a pass.

**3. Render** (`mapgen/render.py`) draws `map.png` for inspection.

The same inputs always give the same map: there is nothing random in it.

## The file: `data/map.json`

- `terrain`: one string per map row; `~` sea, `.` desert, `^` rough, `v` depression, `s` sand sea.
- `elevation`: mean height of each hex in metres, by row.
- `escarpments`: `[col, row, direction, high side]` — the edge of hex (col, row)
  in direction 1 NE, 2 SE or 3 S; high side 0 = this hex, 1 = the neighbour.
- `passes`: escarpment edges a route crosses.
- `routes`: name, kind (road / track / rail) and the hexes in order.
- `places`: name, kind (port / town / oasis / site), hex, coordinates.

Hexes are flat-topped; odd columns sit half a hex lower.

## Known limitations

- **Sollum–Halfaya.** The escarpment is found only in part (it fades into a
  slope inland), so the generator leaves gaps where the real one had only the
  Halfaya and Sollum passes. To do: let `features.json` add or remove
  escarpment edges by hand where the period maps show them.
- **Approximate sites.** About 15 period sites (marked `approx` in
  `features.json`) are placed from general references, to within a hex or so.
- **Tracks** are joined from place to place by least cost, not traced.
- **Sand sea** outline approximate; **coastal salt marshes** (e.g. at El Agheila)
  not marked yet.
- The thresholds above were tuned by eye on the Tobruk–Sollum area and the
  Jebel Akhdar.
