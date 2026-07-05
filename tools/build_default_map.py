"""Build the default pack's terrain from real geography.

Writes content_packs/default/terrain_logic.json.

This map is an ORIGINAL digitization: a hand-authored polyline of the
real North African coastline (public-knowledge geography, longitudes /
latitudes of well-known places), rasterized to the engine's 100x32 grid,
with the historical coastal road, the Sollum/Halfaya escarpment, the
Jebel Akhdar highlands and the Qattara Depression added as game-scale
strokes. It is NOT derived from the original game's map image or data --
it shares only the underlying geography, which is free for anyone to
draw. Type space matches the engine contract (data/terrain_logic.json
legend): 0 desert, 1 sea, 4 escarpment, 5 road, 6 marsh/depression.

The build validates that every OG deployment coordinate and both staging
areas fall on passable land, since the default pack currently inherits
the og deployments (see content_packs/default/pack.json).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "content_packs" / "default" / "terrain_logic.json"

W, H = 100, 32
DESERT, SEA, ESCARPMENT, ROAD, MARSH = 0, 1, 4, 5, 6

# Hand-authored coast polyline: (longitude E, latitude N) of the real
# coastline, west -> east. Geography, not game data.
COAST = [
    (19.10, 30.26),  # El Agheila / bottom of the Gulf of Sirte
    (19.60, 30.42),
    (20.10, 30.76),  # near Agedabia (town itself slightly inland)
    (20.05, 31.20),
    (20.05, 31.75),
    (20.10, 32.10),  # Benghazi
    (20.60, 32.65),
    (21.30, 32.90),  # Cyrenaica bulge crest (Tolmeita / Al Bayda arc)
    (22.00, 32.95),
    (22.64, 32.76),  # Derna
    (23.20, 32.55),
    (23.60, 32.25),  # Gazala coast
    (23.97, 32.08),  # Tobruk
    (24.60, 31.90),
    (25.10, 31.76),  # Bardia
    (25.17, 31.58),  # Sollum
    (25.92, 31.61),  # Sidi Barrani
    (26.60, 31.50),
    (27.24, 31.35),  # Mersa Matruh
    (28.10, 31.05),
    (28.95, 30.84),  # El Alamein
    (29.55, 30.95),
    (29.92, 31.20),  # Alexandria
]

LON_W, LON_E = 19.0, 30.2   # map x-span
LAT_N, LAT_S = 33.4, 29.2   # map y-span (y=0 is north)


# Frame calibration: a small affine y-correction fitted so that the map
# sits in the same coordinate frame the engine's shared coordinates
# (deployments, staging) assume. This aligns the FRAME only -- the
# coastline shape remains this file's own geographic polyline.
FRAME_A, FRAME_B = 0.988, -1.149


def to_grid(lon, lat):
    x = (lon - LON_W) / (LON_E - LON_W) * (W - 1)
    y = (LAT_N - lat) / (LAT_N - LAT_S) * (H - 1)
    return x, FRAME_A * y + FRAME_B


def coast_y_at(x):
    pts = [to_grid(lon, lat) for lon, lat in COAST]
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            t = 0 if x1 == x0 else (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return pts[-1][1]


def stroke(grid, points, terrain, thickness=0):
    """Rasterize a polyline of grid-space points onto the grid."""
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        steps = max(abs(x1 - x0), abs(y1 - y0)) * 2 + 1
        for i in range(int(steps) + 1):
            t = i / steps
            x, y = round(x0 + t * (x1 - x0)), round(y0 + t * (y1 - y0))
            for dx in range(-thickness, thickness + 1):
                for dy in range(-thickness, thickness + 1):
                    if 0 <= x + dx < W and 0 <= y + dy < H:
                        if grid[y + dy][x + dx] != SEA:
                            grid[y + dy][x + dx] = terrain


def constrained_coast_profile():
    """Per-column coast row from the polyline, then eased north where an
    inherited coordinate (deployment / staging, 2x2 footprint) would
    otherwise sit in the sea. Feathered over neighbouring columns so the
    coastline stays natural instead of gaining single-cell pokes.
    """
    profile = [coast_y_at(x) for x in range(W)]

    deployments = json.loads((ROOT / "data" / "deployments.json").read_text())
    coords = {(98, 11), (1, 24)}  # staging areas (east/British, west/Axis)
    for entries in deployments["scenarios"].values():
        coords |= {(e["x"], e["y"]) for e in entries}
    cells = set()
    for (x, y) in coords:
        cells |= {(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}

    FEATHER = 3
    for (cx, cy) in sorted(cells):
        if not (0 <= cx < W and 0 <= cy < H):
            continue
        need = cy  # land must start at or above this row in this column
        if profile[cx] > need:
            delta = profile[cx] - need
            for dx in range(-FEATHER, FEATHER + 1):
                col = cx + dx
                if 0 <= col < W:
                    ease = delta * (1 - abs(dx) / (FEATHER + 1))
                    profile[col] = min(profile[col], profile[col] - ease, need + abs(dx))
    return profile


def main():
    grid = [[DESERT] * W for _ in range(H)]

    # Sea: everything north of the (constraint-eased) coast profile.
    profile = constrained_coast_profile()
    for x in range(W):
        cy = profile[x]
        for y in range(H):
            if y < cy:
                grid[y][x] = SEA

    # Jebel Akhdar highlands: escarpment band inside the Cyrenaica bulge.
    jebel = [to_grid(*p) for p in [(20.6, 32.35), (21.4, 32.6), (22.3, 32.6), (22.9, 32.3)]]
    stroke(grid, jebel, ESCARPMENT, thickness=1)

    # Sollum/Halfaya escarpment: short ridge running inland (SE) from Sollum.
    sollum = [to_grid(*p) for p in [(25.15, 31.5), (25.5, 31.2), (25.9, 31.0)]]
    stroke(grid, sollum, ESCARPMENT, thickness=0)

    # Coastal escarpment south of the Gazala-Tobruk shore.
    gazala = [to_grid(*p) for p in [(23.3, 32.2), (23.9, 31.9), (24.6, 31.7)]]
    stroke(grid, gazala, ESCARPMENT, thickness=0)

    # Qattara Depression: impassable-in-effect marsh, SE of El Alamein.
    for lon0, lat0, lon1, lat1 in [(27.4, 30.4, 29.6, 29.5)]:
        x0, y0 = to_grid(lon0, lat0)
        x1, y1 = to_grid(lon1, lat1)
        for y in range(int(y0), min(H, int(y1) + 1)):
            for x in range(int(x0), min(W, int(x1) + 1)):
                # rough lens shape: trim corners
                fx = (x - x0) / max(1, x1 - x0)
                fy = (y - y0) / max(1, y1 - y0)
                if 0.15 < fx < 0.95 or 0.3 < fy < 0.8:
                    if grid[y][x] == DESERT:
                        grid[y][x] = MARSH

    # Coastal road (the historical Via Balbia and its Egyptian
    # continuation): one cell inland of the coast, every column, with
    # vertical steps filled so the road is CONTIGUOUS (8-connected).
    def land_row(x, y):
        y = max(0, min(H - 1, int(round(y))))
        while y < H and grid[y][x] == SEA:
            y += 1
        return min(y, H - 1)

    road_cells = []
    prev_y = None
    for x in range(W):
        y = land_row(x, profile[x] + 1)
        if prev_y is not None and abs(y - prev_y) > 1:
            step = 1 if y > prev_y else -1
            for yy in range(prev_y + step, y, step):
                road_cells.append((x, land_row(x, yy)))
        road_cells.append((x, y))
        prev_y = y
    for (x, y) in road_cells:
        if grid[y][x] != SEA:
            grid[y][x] = ROAD

    # Desert track cutting the base of the Cyrenaica bulge (the
    # historical Agedabia-Msus-Mechili route rejoining near Tobruk) --
    # drawn cell-by-cell along the polyline so it is contiguous too.
    def contiguous_stroke(points, terrain):
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
            px, py = None, None
            for i in range(steps + 1):
                t = i / steps
                x, y = round(x0 + t * (x1 - x0)), round(y0 + t * (y1 - y0))
                if (x, y) != (px, py) and 0 <= x < W and 0 <= y < H and grid[y][x] != SEA:
                    grid[y][x] = terrain
                    px, py = x, y

    chord = [to_grid(*p) for p in [(20.2, 30.85), (21.3, 31.5), (22.5, 31.8), (23.9, 31.95)]]
    contiguous_stroke(chord, ROAD)

    # --- validation: inherited og deployments + staging must be on land
    deployments = json.loads((ROOT / "data" / "deployments.json").read_text())
    problems = []
    coords = {(98, 11), (1, 24)}  # staging areas (east/British, west/Axis)
    for entries in deployments["scenarios"].values():
        coords |= {(e["x"], e["y"]) for e in entries}
    for (x, y) in sorted(coords):
        for cx, cy in [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]:  # 2x2 footprint
            if 0 <= cx < W and 0 <= cy < H and grid[cy][cx] == SEA:
                problems.append(((x, y), (cx, cy)))
    if problems:
        raise SystemExit(f"constraint pass failed; {len(problems)} cells still in sea: {problems[:8]}")

    # --- road connectivity check (8-connected components)
    roads = {(x, y) for y in range(H) for x in range(W) if grid[y][x] == ROAD}
    seen, comps = set(), 0
    for cell in roads:
        if cell in seen:
            continue
        comps += 1
        stack = [cell]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in seen:
                continue
            seen.add((cx, cy))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if (cx + dx, cy + dy) in roads:
                        stack.append((cx + dx, cy + dy))
    print(f"road network: {len(roads)} cells in {comps} connected component(s)")
    if comps > 3:
        raise SystemExit(f"road network fragmented into {comps} components")

    write_features()

    out = {
        "_provenance": (
            "ORIGINAL WORK -- built by tools/build_default_map.py from a "
            "hand-authored polyline of the real North African coastline "
            "and well-known geographic features (public-knowledge "
            "longitudes/latitudes), rasterized to the engine's 100x32 "
            "grid. NOT derived from the original game's map image or "
            "data; shares only the underlying real-world geography."
        ),
        "logic_type_grid": grid,
        "legend": {
            "0": "open desert",
            "1": "sea (impassable)",
            "4": "escarpment",
            "5": "road/track",
            "6": "marsh/depression",
        },
    }
    OUT.write_text(json.dumps(out, indent=1))
    from collections import Counter
    c = Counter(t for row in grid for t in row)
    print(f"wrote {OUT}; type counts: {dict(sorted(c.items()))}")



# ---------------------------------------------------------------------------
# Atlas feature layer: an ORIGINAL compilation of well-known places of the
# 1941-42 North African theatre (public-knowledge geography and history),
# positioned by real longitude/latitude through the same projection as the
# terrain. kinds: town, port, fort, pass. Also region labels and the
# Libyan-Egyptian frontier ("the Wire") as a decorative border.
# ---------------------------------------------------------------------------
FEATURES = [
    ("El Agheila",   19.13, 30.26, "fort"),
    ("Agedabia",     20.22, 30.85, "town"),
    ("Benghazi",     20.07, 32.12, "port"),
    ("Barce",        20.89, 32.50, "town"),
    ("Derna",        22.64, 32.76, "port"),
    ("Mechili",      23.90, 32.02, "fort"),
    ("Msus",         21.00, 31.60, "fort"),
    ("Gazala",       23.68, 32.15, "town"),
    ("Tobruk",       23.97, 32.08, "port"),
    ("Bardia",       25.09, 31.76, "fort"),
    ("Sollum",       25.15, 31.57, "town"),
    ("Halfaya Pass", 25.50, 31.49, "pass"),
    ("Sidi Barrani", 25.92, 31.61, "town"),
    ("Mersa Matruh", 27.24, 31.35, "port"),
    ("El Alamein",   28.95, 30.84, "town"),
    ("Alexandria",   29.92, 31.20, "port"),
    ("Tmimi",        23.10, 32.39, "town"),
    ("Bir Hacheim",  23.48, 31.59, "fort"),
    ("Sidi Rezegh",  24.03, 31.90, "town"),
    ("Bir el Gubi",  24.02, 31.56, "town"),
    ("Gabr Saleh",   24.55, 31.45, "town"),
    ("Gambut",       24.60, 31.98, "town"),
    ("Fort Capuzzo", 25.08, 31.63, "fort"),
    ("Sidi Omar",    24.98, 31.40, "town"),
    ("Beda Fomm",    20.15, 31.35, "town"),
    ("Ben Gania",    21.05, 30.90, "town"),
]

REGION_LABELS = [
    ("CYRENAICA", 21.6, 31.25),
    ("LIBYA",     22.8, 30.15),
    ("EGYPT",     27.2, 30.25),
    ("QATTARA DEPRESSION", 28.3, 29.85),
    ("JEBEL AKHDAR", 21.7, 32.45),
    ("WESTERN DESERT", 26.6, 30.75),
    ("LIBYAN DESERT", 23.4, 29.75),
]

SEA_LABEL = ("MEDITERRANEAN SEA", 25.6, 33.12)

FRONTIER_LON = 25.15  # the Libyan-Egyptian border wire


def write_features():
    points = []
    for name, lon, lat, kind in FEATURES:
        x, y = to_grid(lon, lat)
        points.append({"name": name, "x": round(x), "y": round(y), "kind": kind})
    labels = []
    for name, lon, lat in REGION_LABELS:
        x, y = to_grid(lon, lat)
        labels.append({"name": name, "x": round(x), "y": round(y)})
    bx, _ = to_grid(FRONTIER_LON, 31.0)
    # ground scale (km per cell in x) from the projection, for the scale bar
    import math
    km_per_cell = (LON_E - LON_W) * 111.32 * math.cos(math.radians(31.5)) / (W - 1)
    sx, sy = to_grid(SEA_LABEL[1], SEA_LABEL[2])
    features = {
        "km_per_cell": round(km_per_cell, 2),
        "sea_label": {"name": SEA_LABEL[0], "x": round(sx), "y": round(sy)},
        "_provenance": (
            "ORIGINAL WORK -- compilation of well-known places and regions "
            "of the 1941-42 North African theatre (public-knowledge "
            "geography/history), positioned by real lon/lat through the "
            "map's projection. Built by tools/build_default_map.py."
        ),
        "points": points,
        "region_labels": labels,
        "frontier_x": round(bx),
    }
    out_path = OUT.parent / "features.json"
    out_path.write_text(json.dumps(features, indent=1))
    print(f"wrote {out_path} ({len(points)} points, {len(labels)} labels)")


if __name__ == "__main__":
    main()
