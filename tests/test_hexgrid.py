"""Hex geometry."""
import math

from mapgen import hexgrid as H


def test_a_hex_contains_its_own_centre():
    for col in range(-3, 12):
        for row in range(-3, 12):
            assert H.hex_at(*H.centre(col, row)) == (col, row)


def test_neighbours_are_ten_km_away_and_mutual():
    for col in (4, 5):
        for d in range(6):
            n = H.neighbour(col, 7, d)
            (x0, y0), (x1, y1) = H.centre(col, 7), H.centre(*n)
            assert math.isclose(math.hypot(x1 - x0, y1 - y0), H.HEX_KM)
            assert H.neighbour(*n, (d + 3) % 6) == (col, 7)
            assert H.distance((col, 7), n) == 1


def test_directions_point_where_they_say():
    (x, y) = H.centre(4, 4)
    north, south = H.centre(*H.neighbour(4, 4, 0)), H.centre(*H.neighbour(4, 4, 3))
    assert north[0] == x and north[1] < y and south[1] > y
    assert H.centre(*H.neighbour(4, 4, 1))[0] > x and H.centre(*H.neighbour(4, 4, 5))[0] < x


def test_a_hexside_has_one_name():
    for col in (4, 5):
        for d in range(6):
            n = H.neighbour(col, 7, d)
            assert H.side(col, 7, d) == H.side(*n, (d + 3) % 6)
            assert H.side(col, 7, d)[2] in (1, 2, 3)


def test_edge_lies_between_the_two_hexes():
    a, b, (nx, ny) = H.edge(4, 4, 1)
    assert math.isclose(math.hypot(b[0] - a[0], b[1] - a[1]), H.SIZE)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    assert H.hex_at(mid[0] - nx, mid[1] - ny) == (4, 4)
    assert H.hex_at(mid[0] + nx, mid[1] + ny) == H.neighbour(4, 4, 1)
