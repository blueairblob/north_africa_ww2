"""Flat-topped hexes, 10 km between the centres of neighbours.

Hexes are addressed (col, row) in "odd-q" offset layout: odd columns sit half a
hex lower. Positions are in kilometres, x east and y south from the map's
north-west corner. Directions: 0 N, 1 NE, 2 SE, 3 S, 4 SW, 5 NW.
"""
import math

HEX_KM = 10.0                         # centre to centre
SIZE = HEX_KM / math.sqrt(3)          # centre to corner
COL_STEP = 1.5 * SIZE                 # between column centres
ROW_STEP = HEX_KM                     # between row centres
DIRECTIONS = ("N", "NE", "SE", "S", "SW", "NW")

_EVEN = ((0, -1), (1, -1), (1, 0), (0, 1), (-1, 0), (-1, -1))
_ODD = ((0, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0))


def centre(col, row):
    """(x, y) in km of the centre of hex (col, row)."""
    return COL_STEP * col + SIZE, ROW_STEP * (row + 0.5 * (col & 1)) + ROW_STEP / 2


def neighbour(col, row, d):
    dc, dr = (_ODD if col & 1 else _EVEN)[d]
    return col + dc, row + dr


def neighbours(col, row):
    return [neighbour(col, row, d) for d in range(6)]


def hex_at(x, y):
    """The hex containing the point (x, y) km."""
    x -= SIZE
    y -= ROW_STEP / 2
    q = (2 / 3 * x) / SIZE
    r = (-x / 3 + math.sqrt(3) / 3 * y) / SIZE
    # cube rounding
    s = -q - r
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return rq, rr + (rq - (rq & 1)) // 2


def distance(a, b):
    """Hexes between two hexes."""
    def cube(col, row):
        q = col
        r = row - (col - (col & 1)) // 2
        return q, r, -q - r
    (q1, r1, s1), (q2, r2, s2) = cube(*a), cube(*b)
    return max(abs(q1 - q2), abs(r1 - r2), abs(s1 - s2))


def corners(col, row):
    """The six corners of a hex, starting east and going clockwise (y is south)."""
    cx, cy = centre(col, row)
    return [(cx + SIZE * math.cos(math.radians(60 * i)), cy + SIZE * math.sin(math.radians(60 * i)))
            for i in range(6)]


def edge(col, row, d):
    """The two ends of the hexside in direction d, and the unit vector across it."""
    (x0, y0), (x1, y1) = centre(col, row), centre(*neighbour(col, row, d))
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = (x1 - x0) / HEX_KM, (y1 - y0) / HEX_KM
    px, py = -ny * SIZE / 2, nx * SIZE / 2
    return (mx - px, my - py), (mx + px, my + py), (nx, ny)


def side(col, row, d):
    """A hexside named once: (col, row, d) with d in 1..3, whichever hex it is seen from."""
    if d in (1, 2, 3):
        return col, row, d
    c, r = neighbour(col, row, d)
    return c, r, (d + 3) % 6
