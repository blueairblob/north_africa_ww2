"""The map builder's rules, on small made-up ground (no downloads needed)."""
import numpy as np

from mapgen import build, geo, raster
from mapgen import hexgrid as H


def _flat(height=100.0):
    return np.full(raster.shape(), height, dtype=np.float32)


def test_land_sea_and_depression():
    elev = _flat()
    land = np.ones(raster.shape(), dtype=bool)
    h, w = raster.shape()
    land[:, : w // 2] = False                       # the west half is sea
    elev[: h // 2, w * 3 // 4:] = -60.0             # a deep hollow in the north-east
    t, mean, _ = build.terrain(elev, land, raster.hex_index())
    assert t[2][5] == build.SEA
    assert t[geo.COLS - 3][2] == build.DEPRESSION
    assert t[geo.COLS - 3][geo.ROWS - 3] == build.DESERT
    assert mean[geo.COLS - 3][geo.ROWS - 3] == 100


def test_a_cliff_becomes_a_line_of_escarpment_hexsides():
    elev = _flat(50.0)
    h, w = raster.shape()
    elev[h // 2:, :] = 250.0                        # high ground to the south, a cliff across the map
    t = np.full((geo.COLS, geo.ROWS), build.DESERT, dtype="<U1")
    land = np.ones(raster.shape(), dtype=bool)
    scarps = build.escarpments(elev, land, t)
    assert len(scarps) > geo.COLS                   # a line right across
    rows = {r for _, r, _ in scarps}
    assert max(rows) - min(rows) <= 2               # ...and only along the cliff
    assert build.escarpments(_flat(), land, t) == {}   # flat ground has none


def test_routes_go_round_impassable_ground_and_make_passes_at_escarpments():
    t = np.full((geo.COLS, geo.ROWS), build.DESERT, dtype="<U1")
    for r in range(0, 12):
        t[10][r] = build.SEA                        # an inlet from the north edge
    path = build.find_route(t, {}, (8, 5), (12, 5))
    assert all(t[c][r] != build.SEA for c, r in path)
    assert all(H.distance(a, b) == 1 for a, b in zip(path, path[1:]))
    assert len(path) > 5                            # it had to go round
    # a wall of escarpment with no gap: the route crosses it once, and that is a pass
    wall = {H.side(20, r, d) for r in range(geo.ROWS) for d in (1, 2)}
    places = [{"name": "A", "col": 18, "row": 20}, {"name": "B", "col": 23, "row": 20}]
    routes, passes = build.routes(t, wall, places, {"routes": [{"name": "x", "kind": "road", "via": ["A", "B"]}]})
    assert len(passes) == 1 and passes[0]["name"] is None
    assert (passes[0]["col"], passes[0]["row"], passes[0]["side"]) in wall


def test_stray_hexsides_are_dropped_but_lines_kept():
    line = {H.side(20, r, d): 1 for r in (5, 6) for d in (1, 2)}        # four sides that join up
    stray = {(30, 30, 1): 0, (40, 10, 2): 0, (40, 10, 3): 0}            # one alone, and a pair
    assert set(build._lines_only({**line, **stray})) == set(line)


def test_a_hex_ringed_by_escarpments_is_rough_ground_without_the_lines():
    t = np.full((geo.COLS, geo.ROWS), build.DESERT, dtype="<U1")
    ring = {H.side(20, 20, d): 0 for d in range(6)}
    line = {H.side(40, r, d): 1 for r in (5, 6) for d in (1, 2)}
    assert set(build.broken_ground(t, {**ring, **line})) == set(line)
    assert t[20][20] == build.ROUGH and t[40][5] == build.DESERT


def test_a_drawn_escarpment_is_an_unbroken_line_and_replaces_what_was_found():
    t = np.full((geo.COLS, geo.ROWS), build.DESERT, dtype="<U1")
    mean = np.zeros((geo.COLS, geo.ROWS), dtype=int)
    (x0, y0), (x1, y1) = H.centre(30, 20), H.centre(46, 20)
    for c in range(geo.COLS):
        for r in range(geo.ROWS):
            mean[c][r] = 200 if H.centre(c, r)[1] > y0 + 4.0 else 0     # high ground south of the line
    line = [list(reversed(geo.to_lonlat(x, y + 4.0))) for x, y in ((x0, y0), (x1, y1))]
    found = {(35, 20, 2): 0, (80, 30, 1): 1}                            # one beside the line, one far away
    scarps = build.drawn_escarpments(t, mean, found, {"escarpments": [{"name": "x", "line": line}]})
    assert (80, 30, 1) in scarps and (35, 20, 2) not in scarps
    for (c, r, d), high in scarps.items():                              # the southern hex is the high one
        if (c, r, d) != (80, 30, 1):
            assert high == int(H.centre(*H.neighbour(c, r, d))[1] > H.centre(c, r)[1])
    ends = {}
    for s in scarps:
        if s != (80, 30, 1):
            for e in build._ends(*s):
                ends[e] = ends.get(e, 0) + 1
    assert sorted(ends.values()).count(1) == 2                          # one line: just two loose ends


def test_a_named_pass_is_the_nearest_escarpment_hexside_and_routes_use_it():
    t = np.full((geo.COLS, geo.ROWS), build.DESERT, dtype="<U1")
    wall = {H.side(20, r, d): 0 for r in range(geo.ROWS) for d in (1, 2)}
    (ax, ay), (bx, by), _ = H.edge(20, 21, 1)
    lon, lat = geo.to_lonlat((ax + bx) / 2, (ay + by) / 2)
    features = {"passes": [{"name": "The Gap", "lat": lat, "lon": lon}],
                "routes": [{"name": "x", "kind": "road", "via": ["A", "B"]}]}
    places = [{"name": "A", "col": 18, "row": 20}, {"name": "B", "col": 23, "row": 20}]
    routes, passes = build.routes(t, wall, places, features)
    assert passes == [{"name": "The Gap", "col": 20, "row": 21, "side": 1}]     # the road went to the pass
    assert [20, 21] in routes[0]["hexes"]


def test_an_oasis_is_the_hexes_its_points_fall_in_whatever_the_ground():
    t = np.full((geo.COLS, geo.ROWS), build.SAND, dtype="<U1")
    t[10][10] = build.SEA
    points = [list(reversed(geo.to_lonlat(*H.centre(c, r)))) for c, r in ((30, 20), (31, 20), (10, 10))]
    build.oases(t, {"oases": [{"name": "x", "at": points}]})
    assert t[30][20] == t[31][20] == build.OASIS and t[10][10] == build.SEA
    assert build.OASIS not in build.IMPASSABLE and build.OASIS in build.ROUTE_COST
