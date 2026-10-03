# How the map is generated

`python -m mapgen all` runs three steps.

**1. Fetch** (`mapgen/fetch.py`) downloads, once, into `cache/` (not committed):
119 elevation tiles and the Natural Earth 1:10m land polygons and boundary lines.

**2. Build** (`mapgen/build.py`) lays the data on a 0.5 km grid and derives each
hex from it. The rules are a handful of named numbers at the top of the file:

| Rule | Value | Meaning |
| --- | --- | --- |
| `LAND_SHARE` | 0.5 | a hex is land if at least half of it is |
| `ROUGH_SLOPE` | 30 m/km | mean slope from which a hex is rough going |
| `BELOW_SEA` | −25 m | deep below sea level: depression (the oases are shallower and stay passable) |
| `SCARP_STEEP` | 28 m/km | a cliff line: somewhere the ground is this steep… |
| `SCARP_SLOPE` | 14 m/km | …and the line is followed for as long as it stays this steep… |
| `SCARP_KM` | 10 km | …and is at least this long |
| `SCARP_DROP`, `SCARP_REACH` | 15 m, 1.5 km | where the line passes between two hexes, the drop between points either side of it |
| `SCARP_SIDES` | 4 | an escarpment on the map is a line of at least this many hex edges |
| `BROKEN_SIDES` | 4 | a hex with this many escarpment edges is rough ground |
| `RINGED_SIDES` | 6 | a hex ringed by them is a hill or hollow: rough, without the lines |
| `ROUTE_COST`, `SCARP_COST` | 1 / 1.6, +4 | how routes weigh desert, rough ground and climbing an escarpment |
| `DRAWN_KM` | 5 km | a hand-drawn escarpment replaces the found edges this close to its line |
| `PASS_KM` | 6 km | a named pass must be this close to an escarpment edge |

**Escarpments** are found in two steps. First the cliff lines are traced on the
grid: the steepest line of each sharp slope, followed along for as long as it
stays steep (this is edge detection, on lightly smoothed ground). Then each line
is laid on the hex edges it runs between — the edges whose two hex centres it
separates. Because the line is unbroken, so are the hex edges: an escarpment
that runs through the middle of a hex is moved to one side of it, not lost.
Between two rough hexes the escarpment is part of the going and is not drawn.

Then: short scraps of escarpment are dropped (an escarpment is a line);
places from `data/features.json` are put in their hexes; each route is found
over the ground between the places it names (least cost); and wherever a route
crosses an escarpment edge, that edge becomes a pass.

## What is drawn by hand

Where the rules are not enough, or the result matters too much to leave to
them, `data/features.json` says where the escarpment is:

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

**3. Render** (`mapgen/render.py`) draws `map.png` in the manner of a map of
the period: the hexes over relief shading from the same elevation data (lit
from the north-west; `LIGHT` and `SHADE` set how strong), the sand sea dotted
and the depressions dashed as such maps draw them, escarpments with ticks on
the low side, the coast road, tracks and railway, the frontier, and the names
of places and regions. Round it go a neat line with the degrees marked, a title
block with legend and scales of miles and kilometres, and a line of credits.

The same inputs always give the same map: there is nothing random in it.

## The file: `data/map.json`

- `terrain`: one string per map row; `~` sea, `.` desert, `^` rough, `v` depression, `s` sand sea.
- `elevation`: mean height of each hex in metres, by row.
- `escarpments`: `[col, row, direction, high side]` — the edge of hex (col, row)
  in direction 1 NE, 2 SE or 3 S; high side 0 = this hex, 1 = the neighbour.
- `passes`: the edges where an escarpment can be climbed: `name` (null where a
  route made the pass and it has no name), `col`, `row`, `side` (the direction).
- `routes`: name, kind (road / track / rail) and the hexes in order.
- `frontier`: the Libya–Egypt frontier as latitude/longitude points (where the
  Italians built the Wire). Drawn only; it is not yet a rule.
- `labels`: names of seas, countries and regions, for the picture.
- `places`: name, kind (port / town / oasis / site), hex, coordinates.

Hexes are flat-topped; odd columns sit half a hex lower.

## Checked against period maps

Two maps of the time were laid over the generated map by fitting their
latitude/longitude grid or scale bar, and the places read off them:

- **Gazala, May 1942** (a battle map published in 1954, with a 1° grid): Tmimi,
  Gazala, Tobruk, El Adem, Gambut and Bir Hakeim all fell within about 5 km of
  where they already were. From it came Acroma and Knightsbridge, the track
  Acroma – Knightsbridge – Bir Hakeim, and two corrections to the Trigh Capuzzo:
  it runs on west through Knightsbridge, and it passes some 10 km *south* of
  Gambut, not through it.
- **Cyrenaica, April 1941** (a diagram of the Axis lines of advance, with a
  scale bar): Benghazi, Derna, Tobruk, Agedabia, Mersa Brega, Soluch, Msus and
  Mechili agreed. **Antelat was wrong**: it had been placed at a modern village
  of the same name 30 km too far south; it is now beside Beda Fomm, where the
  diagram and the gazetteer's other entry put it. From it came Sceleidima,
  Maaten el Grara, Ben Gania and Tengeder, and the tracks Agedabia – Ben Gania –
  Tengeder – Mechili, Soluch – Sceleidima – Msus, and the Trigh el Abd's start
  at Tengeder.

- **Cyrenaica in March 1941** (a map published in 1956, with a scale bar):
  fitted on Benghazi, Tobruk, Agedabia, Siwa and Jarabub, it gave the northern
  edge of the **Libyan Sand Sea**, which runs much further west than the first
  hand-drawn outline did — and agrees with the dunes that show in the elevation
  data. The sand sea went from 47 hexes to 252. Its names are used on the
  picture: Libyan Sand Sea, Gulf of Sidra, Gulf of Bomba, Jebel Akhdar.
  It also draws the Sollum escarpment running on east, past Sofafi to Matruh;
  the elevation data shows that stretch as a slope, not a cliff, so it is not
  on the map yet (see below).

Only positions and names (facts) were taken from these maps; the maps
themselves are not in this repository. Places read off them are marked
`approx` unless a gazetteer confirmed them.

## Known limitations

- **Escarpments end where the cliff does.** An escarpment that fades into a
  slope stops, and can be passed round its end; that is the ground, not a gap.
  The lines were checked by eye against the elevation data for Gazala–Bardia,
  Sollum, the Jebel Akhdar, Matruh–Alamein and the Qattara rim, but not against
  period maps, and only Sollum has named passes. The other passes are simply
  where a route climbs.
- **Close pairs.** Two escarpments less than a hex apart (the ridges at Sidi
  Rezegh) leave a row of hexes with cliffs on both sides, some of them rough.
- **The Jebel Akhdar** is cut up by wadis: it comes out as rough ground with
  pieces of escarpment round its edge, not as its two clean terraces.
- **The Halfaya track** is joined from the pass to Sidi Omar by least cost, and
  the pass positions come from general references, not period survey sheets.
- **Approximate sites.** About 15 period sites (marked `approx` in
  `features.json`) are placed from general references, to within a hex or so.
- **Tracks** are joined from place to place by least cost, not traced.
- **Sofafi to Matruh.** The 1956 map draws an escarpment all the way from
  Sollum to Matruh; here it stops near Sofafi and starts again south of Matruh.
  Whether the stretch between was a barrier to vehicles needs a better source.
- **Sand sea** edge read off a small-scale map: good to a hex or so; **coastal salt marshes** (e.g. at El Agheila)
  not marked yet.
- The thresholds above were tuned by eye on the Tobruk–Sollum area and
  checked on the rest.
