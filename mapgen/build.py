"""Build the hex map: terrain, escarpment hexsides, routes, passes and places."""
import heapq
import json
import os

import numpy as np

from . import fetch, geo, raster
from . import hexgrid as H

SEA, DESERT, ROUGH, DEPRESSION, SAND, OASIS = "~", ".", "^", "v", "s", "o"
TERRAIN_NAMES = {SEA: "sea", DESERT: "desert", ROUGH: "rough", DEPRESSION: "depression", SAND: "sand sea",
                 OASIS: "oasis"}
IMPASSABLE = {SEA, DEPRESSION, SAND}

# the rules that turn the ground into the map
LAND_SHARE = 0.5            # a hex is land if at least this share of it is
ROUGH_SLOPE = 30.0          # mean slope (m per km) from which a hex is rough going
BELOW_SEA = -25.0           # deep below sea level: the Qattara Depression (the oases are shallower)
SCARP_STEEP = 28.0          # a cliff line: somewhere the ground is this steep (m per km)...
SCARP_SLOPE = 14.0          # ...and the line is followed for as long as it stays this steep
SCARP_KM = 10.0             # ...and is at least this long from end to end
SCARP_DROP = 15.0           # where it crosses between two hexes, the metres it drops...
SCARP_REACH = 1.5           # ...between points this many km either side of it
SCARP_SIDES = 4             # an escarpment on the map is a line of at least this many hexsides
BROKEN_SIDES = 4            # a hex with this many escarpment sides is broken ground: rough
RINGED_SIDES = 6            # ...and with this many it is a hill or hollow: rough, without the lines
ROUTE_COST = {DESERT: 1.0, ROUGH: 1.6, OASIS: 1.0}
SCARP_COST = 4.0            # extra cost for a route to cross an escarpment (it makes a pass)
DRAWN_KM = 5.0              # a drawn escarpment replaces the found hexsides this close to its line
PASS_KM = 6.0               # a named pass belongs to the escarpment hexside within this distance

FEATURES = os.path.join(fetch.HERE, "data", "features.json")
OUT = os.path.join(fetch.HERE, "data", "map.json")


def _per_hex(index, values, n, weights=None):
    ok = index >= 0
    return np.bincount(index[ok], weights=values[ok] if weights is None else (values * weights)[ok], minlength=n)


def terrain(elev, land, index):
    """Per-hex terrain letters and mean elevation, as [col][row] arrays."""
    n = geo.COLS * geo.ROWS
    count = np.maximum(_per_hex(index, np.ones_like(elev), n), 1)
    landf = land.astype(np.float32)
    land_px = np.maximum(_per_hex(index, landf, n), 1)
    land_share = _per_hex(index, landf, n) / count
    mean_elev = _per_hex(index, elev, n, landf) / land_px
    mean_slope = _per_hex(index, raster.slope(elev), n, landf) / land_px
    low_share = _per_hex(index, (elev < BELOW_SEA).astype(np.float32), n, landf) / land_px
    t = np.full(n, DESERT, dtype="<U1")
    t[mean_slope >= ROUGH_SLOPE] = ROUGH
    t[low_share >= 0.5] = DEPRESSION
    t[land_share < LAND_SHARE] = SEA
    shape = (geo.COLS, geo.ROWS)
    return t.reshape(shape), np.rint(mean_elev).astype(int).reshape(shape), land_share.reshape(shape)


def _inside(poly, x, y):
    inside = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside


def sand_seas(t, features):
    for sea in features.get("sand_seas", []):
        poly = [geo.to_km(lon, lat) for lat, lon in sea["outline"]]
        for c in range(geo.COLS):
            for r in range(geo.ROWS):
                if t[c][r] in (DESERT, ROUGH) and _inside(poly, *H.centre(c, r)):
                    t[c][r] = SAND


def oases(t, features):
    """The oases: water and palms in the desert. Each is the hexes its points fall in,
    whatever the ground there would otherwise be."""
    for oasis in features.get("oases", []):
        for lat, lon in oasis["at"]:
            c, r = geo.hex_of(lon, lat)
            if not geo.in_map(c, r):
                raise ValueError(f"{oasis['name']} is off the map")
            if t[c][r] != SEA:
                t[c][r] = OASIS


def cliff_lines(elev, land):
    """Thin lines of grid pixels along the cliffs: the steepest line of each sharp slope,
    followed for as long as it stays steep (edge detection on the smoothed ground).
    Returns the lines (True where a pixel is on one) and the smoothed elevation."""
    h, w = elev.shape
    pad = np.pad(elev, 1, mode="edge")
    smooth = sum(pad[i:i + h, j:j + w] for i in range(3) for j in range(3)) / 9
    gy, gx = np.gradient(smooth, raster.RES)
    steep = np.hypot(gx, gy)
    steep[~land] = 0
    # the crest of the slope: steeper than the pixels up and down the slope from it
    way = (np.rint(np.arctan2(gy, gx) / (np.pi / 4)) % 4).astype(int)
    pad = np.pad(steep, 1)

    def shifted(dy, dx):
        return pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    crest = np.zeros((h, w), dtype=bool)
    for k, (dy, dx) in enumerate(((0, 1), (1, 1), (1, 0), (1, -1))):
        crest |= (way == k) & (steep >= shifted(dy, dx)) & (steep > shifted(-dy, -dx))
    crest &= steep >= SCARP_SLOPE
    # keep each connected line that somewhere is a real cliff and is long enough
    lines = np.zeros((h, w), dtype=bool)
    seen = np.zeros((h, w), dtype=bool)
    for i, j in zip(*np.nonzero(crest & (steep >= SCARP_STEEP))):
        if seen[i, j]:
            continue
        seen[i, j] = True
        stack, line = [(i, j)], []
        while stack:
            y, x = stack.pop()
            line.append((y, x))
            for yy in range(max(y - 1, 0), min(y + 2, h)):
                for xx in range(max(x - 1, 0), min(x + 2, w)):
                    if crest[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        stack.append((yy, xx))
        ys, xs = [q[0] for q in line], [q[1] for q in line]
        if np.hypot(max(ys) - min(ys), max(xs) - min(xs)) * raster.RES >= SCARP_KM:
            lines[ys, xs] = True
    return lines, smooth


def escarpments(elev, land, t):
    """Hexsides the cliff lines run along: {(col, row, d): high side (0 this hex, 1 the neighbour)}.
    A cliff line is laid on the hexsides it parts (those whose two hexes it runs between),
    so an unbroken cliff makes an unbroken line of hexsides."""
    lines, smooth = cliff_lines(elev, land)
    h, w = lines.shape
    res = raster.RES

    def at(x, y):
        return float(smooth[min(max(int(y / res), 0), h - 1), min(max(int(x / res), 0), w - 1)])

    def open_ground(c, r):
        return geo.in_map(c, r) and t[c][r] != SEA

    found = {}
    for i, j in zip(*np.nonzero(lines)):
        a = ((j + 0.5) * res, (i + 0.5) * res)
        for dy, dx in ((0, 1), (1, -1), (1, 0), (1, 1)):            # each link to the next pixel of the line
            if not (i + dy < h and 0 <= j + dx < w and lines[i + dy, j + dx]):
                continue
            b = (a[0] + dx * res, a[1] + dy * res)
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            here = H.hex_at(mx, my)
            for c, r in [here] + H.neighbours(*here):
                if not open_ground(c, r):
                    continue
                for d in (1, 2, 3):
                    n = H.neighbour(c, r, d)
                    if (c, r, d) in found or not open_ground(*n) or (t[c][r] in IMPASSABLE and t[n[0]][n[1]] in IMPASSABLE):
                        continue
                    p, q = H.centre(c, r), H.centre(*n)
                    if _crosses(p, q, a, b):
                        ux, uy = (q[0] - p[0]) / H.HEX_KM * SCARP_REACH, (q[1] - p[1]) / H.HEX_KM * SCARP_REACH
                        rise = at(mx + ux, my + uy) - at(mx - ux, my - uy)
                        if abs(rise) >= SCARP_DROP:
                            found[(c, r, d)] = int(rise > 0)
    return _lines_only(found)


def _ends(c, r, d):
    (ax, ay), (bx, by), _ = H.edge(c, r, d)
    return (round(ax, 1), round(ay, 1)), (round(bx, 1), round(by, 1))


def broken_ground(t, scarps):
    """Hexes hemmed in by escarpments are rough ground. A hex ringed by them is a hill or
    a hollow, not a line: its escarpments go. So do those between two rough hexes, where
    the escarpment is part of the going."""
    sides = {}
    for c, r, d in scarps:
        for h in ((c, r), H.neighbour(c, r, d)):
            sides[h] = sides.get(h, 0) + 1
    for (c, r), n in sides.items():
        if n >= BROKEN_SIDES and t[c][r] == DESERT:
            t[c][r] = ROUGH
    kept = {}
    for (c, r, d), v in scarps.items():
        n = H.neighbour(c, r, d)
        ringed = sides[(c, r)] >= RINGED_SIDES or sides[n] >= RINGED_SIDES
        if not ringed and not (t[c][r] == ROUGH and t[n[0]][n[1]] == ROUGH):
            kept[(c, r, d)] = v
    return _lines_only(kept)


def _lines_only(found):
    """Drop stray hexsides: an escarpment is a line, so keep only the sides that join up
    into a line of at least SCARP_SIDES."""
    line = {s: s for s in found}

    def root(s):
        while line[s] != s:
            line[s] = line[line[s]]
            s = line[s]
        return s
    at = {}
    for s in sorted(found):
        for e in _ends(*s):
            if e in at:
                line[root(s)] = root(at[e])
            else:
                at[e] = s
    size = {}
    for s in found:
        size[root(s)] = size.get(root(s), 0) + 1
    return {s: v for s, v in found.items() if size[root(s)] >= SCARP_SIDES}


def _crosses(p, q, a, b):
    """Whether the segments p-q and a-b cross."""
    def turn(o, u, v):
        return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])
    return (turn(p, q, a) > 0) != (turn(p, q, b) > 0) and (turn(a, b, p) > 0) != (turn(a, b, q) > 0)


def _away(p, a, b):
    """Distance from the point p to the segment a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    k = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / ((dx * dx + dy * dy) or 1.0)))
    return ((a[0] + k * dx - p[0]) ** 2 + (a[1] + k * dy - p[1]) ** 2) ** 0.5


def _middle(s):
    (ax, ay), (bx, by), _ = H.edge(*s)
    return (ax + bx) / 2, (ay + by) / 2


def drawn_escarpments(t, mean_elev, scarps, features):
    """Escarpments drawn by hand in the features file, where the rules above leave gaps.
    The line is laid on the hexsides it parts (those whose two hexes it runs between)
    and replaces whatever was found along it."""
    scarps = dict(scarps)
    lines = [[geo.to_km(lon, lat) for lat, lon in scarp["line"]] for scarp in features.get("escarpments", [])]
    for line in lines:                                     # first clear what was found along them all
        for s in [s for s in scarps if min(_away(_middle(s), a, b) for a, b in zip(line, line[1:])) <= DRAWN_KM]:
            del scarps[s]
    for line in lines:
        for c in range(geo.COLS):
            for r in range(geo.ROWS):
                if t[c][r] == SEA:
                    continue
                for d in (1, 2, 3):
                    nc, nr = H.neighbour(c, r, d)
                    if not geo.in_map(nc, nr) or t[nc][nr] == SEA:
                        continue
                    p, q = H.centre(c, r), H.centre(nc, nr)
                    if any(_crosses(p, q, a, b) for a, b in zip(line, line[1:])):
                        scarps[(c, r, d)] = int(mean_elev[nc][nr] > mean_elev[c][r])
    return scarps


def named_passes(scarps, features):
    """Each named pass is the escarpment hexside nearest to it: {(col, row, d): name}."""
    out = {}
    for p in features.get("passes", []):
        x, y = geo.to_km(p["lon"], p["lat"])

        def away(s):
            mx, my = _middle(s)
            return (mx - x) ** 2 + (my - y) ** 2
        s = min(sorted(scarps), key=away, default=None)
        if s is None or away(s) > PASS_KM ** 2:
            raise ValueError(f"{p['name']} is not on an escarpment")
        if s in out:
            raise ValueError(f"{p['name']} and {out[s]} are the same hexside")
        out[s] = p["name"]
    return out


def find_route(t, scarps, a, b, passes=()):
    """The cheapest way over the ground from hex a to hex b (A*), as a list of hexes.
    Crossing an escarpment costs extra, except at a pass that is already there."""
    frontier = [(0.0, 0.0, a)]
    came, cost = {a: None}, {a: 0.0}
    while frontier:
        _, g, cur = heapq.heappop(frontier)
        if cur == b:
            break
        if g > cost[cur]:
            continue
        for d in range(6):
            nxt = H.neighbour(*cur, d)
            if not geo.in_map(*nxt) or t[nxt[0]][nxt[1]] in IMPASSABLE:
                continue
            s = H.side(*cur, d)
            step = ROUTE_COST[t[nxt[0]][nxt[1]]] + (SCARP_COST if s in scarps and s not in passes else 0)
            ng = g + step
            if ng < cost.get(nxt, 1e18):
                cost[nxt], came[nxt] = ng, cur
                heapq.heappush(frontier, (ng + H.distance(nxt, b), ng, nxt))
    if b not in came:
        raise ValueError(f"no way over land from {a} to {b}")
    path = [b]
    while came[path[-1]] is not None:
        path.append(came[path[-1]])
    return path[::-1]


def place_hexes(t, features):
    """Each place's hex. A place in the sea moves to the nearest land hex; one on
    impassable ground (an oasis in a depression or the sands) makes its hex passable."""
    out = []
    for p in features["places"]:
        c, r = geo.hex_of(p["lon"], p["lat"])
        if not geo.in_map(c, r):
            raise ValueError(f"{p['name']} is off the map")
        if t[c][r] in (DEPRESSION, SAND):
            t[c][r] = DESERT
        if t[c][r] == SEA:
            x, y = geo.to_km(p["lon"], p["lat"])
            near = [(n, (H.centre(*n)[0] - x) ** 2 + (H.centre(*n)[1] - y) ** 2) for n in H.neighbours(c, r)
                    if geo.in_map(*n) and t[n[0]][n[1]] not in IMPASSABLE]
            if not near:
                raise ValueError(f"{p['name']} has no land near it")
            c, r = min(near, key=lambda n: (n[1], n[0]))[0]
        out.append(dict(p, col=c, row=r))
    return out


def routes(t, scarps, places, features):
    """The routes, and the passes: the named ones and wherever else a road or track climbs an
    escarpment. A railway makes no pass: its cuttings are not a way up for anything else."""
    where = {p["name"]: (p["col"], p["row"]) for p in places}
    out, passes = [], named_passes(scarps, features)
    for route in features["routes"]:
        stops = [where[v] if isinstance(v, str) else geo.hex_of(v[1], v[0]) for v in route["via"]]
        hexes = [stops[0]]
        for a, b in zip(stops, stops[1:]):
            hexes += find_route(t, scarps, a, b, passes)[1:]
        for a, b in zip(hexes, hexes[1:]):
            d = next(k for k in range(6) if H.neighbour(*a, k) == b)
            if H.side(*a, d) in scarps and route["kind"] != "rail":
                passes.setdefault(H.side(*a, d), None)
        out.append({"name": route["name"], "kind": route["kind"], "hexes": [list(h) for h in hexes]})
    return out, [{"name": passes[s], "col": s[0], "row": s[1], "side": s[2]} for s in sorted(passes)]


def frontier():
    """The Libya-Egypt frontier (where the Italians built the Wire), as [lat, lon] points on the map."""
    with open(fetch.borders_path()) as f:
        lines = json.load(f)["features"]
    for line in lines:
        if {line["properties"]["ADM0_A3_L"], line["properties"]["ADM0_A3_R"]} == {"EGY", "LBY"}:
            return [[round(lat, 3), round(lon, 3)] for lon, lat in line["geometry"]["coordinates"]
                    if geo.LAT_S - 0.2 <= lat <= geo.LAT_N]
    raise ValueError("no Libya-Egypt frontier in the boundary data")


def build(log=print):
    features = json.load(open(FEATURES))
    elev = raster.elevation()
    land = raster.land()
    index = raster.hex_index()
    t, mean_elev, _ = terrain(elev, land, index)
    sand_seas(t, features)
    oases(t, features)
    places = place_hexes(t, features)
    scarps = drawn_escarpments(t, mean_elev, broken_ground(t, escarpments(elev, land, t)), features)
    route_list, passes = routes(t, scarps, places, features)
    counts = {TERRAIN_NAMES[k]: int((t == k).sum()) for k in TERRAIN_NAMES}
    log(f"{geo.COLS} x {geo.ROWS} hexes: {counts}; {len(scarps)} escarpment hexsides, "
        f"{len(passes)} passes, {len(route_list)} routes, {len(places)} places")
    return {
        "about": "Generated by `python -m mapgen build` from public geographic data (docs/SOURCES.md). "
                 "Do not edit: change mapgen/ or data/features.json and rebuild.",
        "hex_km": H.HEX_KM, "layout": "flat-topped hexes, odd columns half a hex lower; "
                                      "directions 0 N, 1 NE, 2 SE, 3 S, 4 SW, 5 NW",
        "cols": geo.COLS, "rows": geo.ROWS,
        "bounds": {"west": geo.LON_W, "east": geo.LON_E, "north": geo.LAT_N, "south": geo.LAT_S},
        "legend": TERRAIN_NAMES,
        "terrain": ["".join(t[c][r] for c in range(geo.COLS)) for r in range(geo.ROWS)],
        "elevation": [[int(mean_elev[c][r]) for c in range(geo.COLS)] for r in range(geo.ROWS)],
        "escarpments": [[c, r, d, scarps[(c, r, d)]] for c, r, d in sorted(scarps)],
        "passes": passes,
        "routes": route_list,
        "frontier": frontier(),
        "labels": features.get("labels", []),
        "shipping": features.get("shipping", []),
        "places": [{k: p[k] for k in ("name", "kind", "col", "row", "lat", "lon", "approx") if k in p}
                   for p in places],
    }


def dumps(m):
    """JSON with one map row, route or place per line."""
    def line(v):
        return json.dumps(v, separators=(", ", ": "))
    out = ["{"]
    keys = list(m)
    for k in keys:
        v = m[k]
        comma = "," if k != keys[-1] else ""
        if isinstance(v, list) and v and isinstance(v[0], (list, dict, str)):
            out.append(f'  {json.dumps(k)}: [')
            out += [f"    {line(x)}{',' if i < len(v) - 1 else ''}" for i, x in enumerate(v)]
            out.append(f"  ]{comma}")
        else:
            out.append(f"  {json.dumps(k)}: {line(v)}{comma}")
    out.append("}")
    return "\n".join(out) + "\n"


def write(m, path=OUT):
    with open(path, "w") as f:
        f.write(dumps(m))
