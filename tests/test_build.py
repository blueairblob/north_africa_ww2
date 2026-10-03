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
    scarps = build.escarpments(elev, t)
    assert len(scarps) > geo.COLS                   # a line right across
    rows = {r for _, r, _ in scarps}
    assert max(rows) - min(rows) <= 2               # ...and only along the cliff
    assert build.escarpments(_flat(), t) == {}      # flat ground has none


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
    assert len(passes) == 1 and tuple(passes[0]) in wall


def test_stray_hexsides_are_dropped_but_lines_kept():
    line = {(5, 5, 1): 1, (5, 5, 2): 1, (30, 30, 1): 0}
    assert set(build._lines_only(line)) == {(5, 5, 1), (5, 5, 2)}
