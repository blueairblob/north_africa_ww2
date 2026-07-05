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
    # continuation): one cell inland of the coast for the full span.
    road_pts = [(x, profile[x] + 1.2) for x in range(0, W, 2)]
    stroke(grid, road_pts, ROAD)

    # Desert track cutting the base of the Cyrenaica bulge
    # (the historical Agedabia-Msus-Mechili-Tobruk inland route).
    chord = [to_grid(*p) for p in [(20.2, 30.85), (21.3, 31.5), (22.5, 31.8), (23.9, 31.95)]]
    stroke(grid, chord, ROAD)

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


if __name__ == "__main__":
    main()
