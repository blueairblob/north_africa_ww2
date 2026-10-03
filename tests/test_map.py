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
    assert all((p["col"], p["row"], p["side"]) in scarps for p in m["passes"])


def test_saved_file_is_what_the_writer_produces(m):
    assert build.dumps(m) == open(build.OUT).read()


def _steps(m, a, b, closed):
    """Hexes from a to b without crossing the closed hexsides (breadth first)."""
    seen, edge = {a: 0}, [a]
    while edge and b not in seen:
        nxt = []
        for cur in edge:
            for d in range(6):
                n = H.neighbour(*cur, d)
                if (geo.in_map(*n) and n not in seen and H.side(*cur, d) not in closed
                        and m["terrain"][n[1]][n[0]] not in build.IMPASSABLE):
                    seen[n] = seen[cur] + 1
                    nxt.append(n)
        edge = nxt
    return seen.get(b)


def test_the_sollum_escarpment_is_crossed_only_at_its_passes(m):
    where = {p["name"]: (p["col"], p["row"]) for p in m["places"]}
    scarps = {tuple(s[:3]) for s in m["escarpments"]}
    passes = {p["name"]: (p["col"], p["row"], p["side"]) for p in m["passes"]}
    assert {"Sollum Pass", "Halfaya Pass"} <= set(passes)
    below, above = where["Buq Buq"], where["Fort Capuzzo"]
    direct = H.distance(below, above)
    assert _steps(m, below, above, scarps - set(passes.values())) == direct      # up through the passes
    for name in ("Sollum Pass", "Halfaya Pass"):                                 # either pass alone will do
        assert _steps(m, below, above, scarps - {passes[name]}) <= direct + 1, name
    shut = _steps(m, below, above, scarps)                                       # without them: no way, or a long one
    assert shut is None or shut >= direct + 4


def test_escarpments_are_lines_not_scraps(m):
    scarps = {tuple(s[:3]): s[3] for s in m["escarpments"]}
    assert build._lines_only(scarps) == scarps                  # none shorter than SCARP_SIDES
    where = {p["name"]: (p["col"], p["row"]) for p in m["places"]}
    closed = set(scarps)
    # the escarpment behind the coast from Gazala to Tobruk, and the ridges south of Tobruk:
    # with the passes shut there is no short way up from the coast road
    for below, above in (("Gazala", "Bir Hakeim"), ("Tobruk", "Bir el Gubi")):
        direct = H.distance(where[below], where[above])
        assert _steps(m, where[below], where[above], closed) >= direct + 4, (below, above)


def test_frontier_and_labels_are_on_the_map(m):
    lats = [lat for lat, lon in m["frontier"]]
    assert all(24.5 < lon < 25.5 for lat, lon in m["frontier"])          # between Jarabub and Siwa, to Sollum
    assert max(lats) > 31.5 and min(lats) < geo.LAT_S + 0.1              # from the sea to the southern edge
    for label in m["labels"]:
        assert geo.LON_W < label["lon"] < geo.LON_E and geo.LAT_S < label["lat"] < geo.LAT_N, label["name"]


def test_places_checked_against_the_period_maps(m):
    where = {p["name"]: (p["col"], p["row"]) for p in m["places"]}
    assert where["Antelat"][1] < where["Agedabia"][1] - 3                # well north of Agedabia, east of Beda Fomm
    assert abs(where["Antelat"][1] - where["Beda Fomm"][1]) <= 1
    capuzzo = next(r for r in m["routes"] if r["name"] == "Trigh Capuzzo")["hexes"]
    assert list(where["Knightsbridge"]) in capuzzo and list(where["El Adem"]) in capuzzo
    assert list(where["Gambut"]) not in capuzzo                          # it passes south of Gambut


def test_the_plateau_behind_sidi_barrani_is_reached_only_by_a_pass(m):
    where = {p["name"]: (p["col"], p["row"]) for p in m["places"]}
    scarps = {tuple(s[:3]) for s in m["escarpments"]}
    below, above = where["Sidi Barrani"], (80, 22)             # the open plateau to the south
    assert m["terrain"][above[1]][above[0]] == build.DESERT
    direct = H.distance(below, above)
    assert _steps(m, below, above, set()) == direct
    assert _steps(m, below, above, scarps) is None             # the coastal plain is walled in
    passes = {(p["col"], p["row"], p["side"]) for p in m["passes"]}
    assert _steps(m, below, above, scarps - passes) is not None


def test_the_oases_are_on_the_map(m):
    where = {p["name"]: (p["col"], p["row"]) for p in m["places"]}
    for name in ("Siwa", "Jarabub", "Augila", "Gicherra", "Marada"):
        c, r = where[name]
        assert m["terrain"][r][c] == build.OASIS, name
    assert sum(row.count(build.OASIS) for row in m["terrain"]) >= 8      # Siwa is a string of them


def test_the_compass_approach_from_matruh_to_the_camps_and_the_coast(m):
    where = {p["name"]: (p["col"], p["row"]) for p in m["places"]}
    scarps = {tuple(s[:3]) for s in m["escarpments"]}
    passes = {(p["col"], p["row"], p["side"]) for p in m["passes"]}
    for a, b in (("Mersa Matruh", "Nibeiwa"), ("Nibeiwa", "Sidi Barrani"), ("Nibeiwa", "Sofafi")):
        assert _steps(m, where[a], where[b], scarps - passes) == H.distance(where[a], where[b]), (a, b)
