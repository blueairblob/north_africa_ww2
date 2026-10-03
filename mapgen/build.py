"""Build the hex map: terrain, escarpment hexsides, routes, passes and places."""
import heapq
import json
import os

import numpy as np

from . import fetch, geo, raster
from . import hexgrid as H

SEA, DESERT, ROUGH, DEPRESSION, SAND = "~", ".", "^", "v", "s"
TERRAIN_NAMES = {SEA: "sea", DESERT: "desert", ROUGH: "rough", DEPRESSION: "depression", SAND: "sand sea"}
IMPASSABLE = {SEA, DEPRESSION, SAND}

# the rules that turn the ground into the map
LAND_SHARE = 0.5            # a hex is land if at least this share of it is
ROUGH_SLOPE = 30.0          # mean slope (m per km) from which a hex is rough going
BELOW_SEA = -25.0           # deep below sea level: the Qattara Depression (the oases are shallower)
SCARP_DROP = 28.0           # metres between the two sides of a hexside...
SCARP_STEP = 9.0            # ...with at least this much of it within half a kilometre
SCARP_PROFILES = 3          # ...on at least this many of 5 lines across the hexside
BROKEN_SIDES = 3            # a hex with this many escarpment sides is broken ground: rough
ROUTE_COST = {DESERT: 1.0, ROUGH: 1.6}
SCARP_COST = 4.0            # extra cost for a route to cross an escarpment (it makes a pass)

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


def escarpments(elev, t):
    """Hexsides where the ground drops sharply: {(col, row, d): high side (0 this hex, 1 the neighbour)}."""
    h, w = elev.shape

    def at(x, y):
        return elev[min(max(int(y / raster.RES), 0), h - 1), min(max(int(x / raster.RES), 0), w - 1)]

    offsets = [k * 0.5 for k in range(-6, 7)]
    found = {}
    for c in range(geo.COLS):
        for r in range(geo.ROWS):
            if t[c][r] == SEA:
                continue
            for d in (1, 2, 3):
                nc, nr = H.neighbour(c, r, d)
                if not geo.in_map(nc, nr) or t[nc][nr] == SEA:
                    continue
                (ax, ay), (bx, by), (nx, ny) = H.edge(c, r, d)
                up = down = 0
                for k in (0.15, 0.325, 0.5, 0.675, 0.85):
                    px, py = ax + (bx - ax) * k, ay + (by - ay) * k
                    prof = [at(px + nx * o, py + ny * o) for o in offsets]
                    drop = sum(prof[-4:]) / 4 - sum(prof[:4]) / 4
                    step = max(abs(q - p) for p, q in zip(prof, prof[1:]))
                    if step >= SCARP_STEP:
                        if drop >= SCARP_DROP:
                            up += 1
                        elif drop <= -SCARP_DROP:
                            down += 1
                if up >= SCARP_PROFILES:
                    found[(c, r, d)] = 1
                elif down >= SCARP_PROFILES:
                    found[(c, r, d)] = 0
    return _lines_only(found)


def _ends(c, r, d):
    (ax, ay), (bx, by), _ = H.edge(c, r, d)
    return (round(ax, 1), round(ay, 1)), (round(bx, 1), round(by, 1))


def broken_ground(t, scarps):
    """Hexes hemmed in by escarpments are rough ground; between two rough hexes the
    escarpment is part of the going, not a line on the map."""
    sides = {}
    for c, r, d in scarps:
        for h in ((c, r), H.neighbour(c, r, d)):
            sides[h] = sides.get(h, 0) + 1
    for (c, r), n in sides.items():
        if n >= BROKEN_SIDES and t[c][r] == DESERT:
            t[c][r] = ROUGH
    kept = {}
    for (c, r, d), v in scarps.items():
        nc, nr = H.neighbour(c, r, d)
        if not (t[c][r] == ROUGH and t[nc][nr] == ROUGH):
            kept[(c, r, d)] = v
    return _lines_only(kept)


def _lines_only(found):
    """Drop stray hexsides: an escarpment is a line, so keep sides that join at least one other."""
    at = {}
    for s in found:
        for e in _ends(*s):
            at.setdefault(e, []).append(s)
    return {s: v for s, v in found.items() if any(len(at[e]) > 1 for e in _ends(*s))}


def find_route(t, scarps, a, b):
    """The cheapest way over the ground from hex a to hex b (A*), as a list of hexes."""
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
            step = ROUTE_COST[t[nxt[0]][nxt[1]]] + (SCARP_COST if H.side(*cur, d) in scarps else 0)
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
    where = {p["name"]: (p["col"], p["row"]) for p in places}
    out, passes = [], set()
    for route in features["routes"]:
        stops = [where[v] if isinstance(v, str) else geo.hex_of(v[1], v[0]) for v in route["via"]]
        hexes = [stops[0]]
        for a, b in zip(stops, stops[1:]):
            hexes += find_route(t, scarps, a, b)[1:]
        for a, b in zip(hexes, hexes[1:]):
            d = next(k for k in range(6) if H.neighbour(*a, k) == b)
            if H.side(*a, d) in scarps:
                passes.add(H.side(*a, d))
        out.append({"name": route["name"], "kind": route["kind"], "hexes": [list(h) for h in hexes]})
    return out, sorted(passes)


def build(log=print):
    features = json.load(open(FEATURES))
    elev = raster.elevation()
    land = raster.land()
    index = raster.hex_index()
    t, mean_elev, _ = terrain(elev, land, index)
    sand_seas(t, features)
    places = place_hexes(t, features)
    scarps = broken_ground(t, escarpments(elev, t))
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
        "passes": [list(p) for p in passes],
        "routes": route_list,
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
