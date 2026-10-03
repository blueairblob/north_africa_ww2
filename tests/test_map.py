"""The generated map (data/map.json): it is consistent with itself and with its rules."""
import json

import pytest

from mapgen import build, geo
from mapgen import hexgrid as H


@pytest.fixture(scope="module")
def m():
    with open(build.OUT) as f:
        return json.load(f)


def test_size_and_rows(m):
    assert (m["cols"], m["rows"]) == (geo.COLS, geo.ROWS)
    assert len(m["terrain"]) == m["rows"] and all(len(row) == m["cols"] for row in m["terrain"])
    assert set("".join(m["terrain"])) <= set(m["legend"])


def test_places_are_on_passable_ground(m):
    for p in m["places"]:
        assert m["terrain"][p["row"]][p["col"]] not in build.IMPASSABLE, p["name"]
        assert H.distance((p["col"], p["row"]), geo.hex_of(p["lon"], p["lat"])) <= 1, p["name"]


def test_routes_are_connected_and_stay_on_passable_ground(m):
    for route in m["routes"]:
        hexes = [tuple(h) for h in route["hexes"]]
        assert all(H.distance(a, b) == 1 for a, b in zip(hexes, hexes[1:])), route["name"]
        assert all(m["terrain"][r][c] not in build.IMPASSABLE for c, r in hexes), route["name"]


def test_geography_is_where_it_should_be(m):
    def terrain_at(lon, lat):
        c, r = geo.hex_of(lon, lat)
        return m["terrain"][r][c]
    assert terrain_at(22.0, 33.0) == build.SEA                 # the Mediterranean north of Cyrenaica
    assert terrain_at(27.5, 29.9) == build.DEPRESSION          # the Qattara Depression
    assert terrain_at(21.6, 32.6) == build.ROUGH               # the Jebel Akhdar
    assert terrain_at(24.0, 30.5) == build.DESERT              # the open desert south of Tobruk


def test_escarpments_and_passes(m):
    scarps = {tuple(s[:3]) for s in m["escarpments"]}
    assert all(d in (1, 2, 3) for _, _, d in scarps)
    assert all(tuple(p) in scarps for p in m["passes"])


def test_saved_file_is_what_the_writer_produces(m):
    assert build.dumps(m) == open(build.OUT).read()
