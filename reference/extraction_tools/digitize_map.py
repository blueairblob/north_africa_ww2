#!/usr/bin/env python3
"""
digitize_map.py - turn the published Desert Rats playing-area map (manual p.2)
into a terrain grid in the GAME's coordinate frame, so terrain[y][x] lines up
with the unit coordinates extracted from the snapshots.

Why this route: the in-RAM terrain map is compressed/tile-encoded (no row- or
column-major fold of the bytes reproduces the coastline), so it doesn't yield to
the diff-and-fold method that cracked the units. The published map is the
authoritative terrain source; we classify its colours and register it to the
game frame by fitting the game->image transform that makes every extracted unit
land on the coast.

Pipeline:
  1. classify each pixel: sea / desert / escarpment / road / saltmarsh(+text)
  2. fit ix=mx*x+bx, iy=my*y+by by minimising units' distance-to-coast
     (subject to: no unit on sea), which pins the alignment
  3. sample the classified image through that transform to build terrain[y][x]

Usage:
    python3 digitize_map.py pubmap.png snap1.szx [snap2.szx ...] [--gw 120 --gh 38]

Requires: numpy, scipy, pillow, skoolkit.
"""
import argparse, json
import numpy as np
from collections import Counter
from PIL import Image
from scipy.ndimage import distance_transform_edt
from skoolkit.snapshot import get_snapshot

# unit-array layout from the OOB work
S = 30
ARRAYS = [(0xBA5C, 33), (0xC074, 43)]

SEA, DESERT, ESCARP, MARSH, ROAD = 0, 1, 2, 3, 4
LEGEND = {0: "sea", 1: "desert", 2: "escarpment", 3: "saltmarsh/town-label", 4: "coast road"}


def classify(im):
    a = np.asarray(im.convert("RGB")).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    C = np.full(r.shape, DESERT, np.uint8)
    C[(b > 150) & (r < 100)] = SEA
    C[(r > 150) & (g < 110) & (b < 90)] = ESCARP
    C[(r > 150) & (g > 150) & (b > 150)] = MARSH
    C[(r < 70) & (g < 70) & (b < 70)] = ROAD
    return C


def unit_coords(snaps):
    pts = []
    for f in snaps:
        m = get_snapshot(f)
        for base, n in ARRAYS:
            for i in range(n):
                r = m[base + i * S: base + i * S + S]
                if r[23] == 0x90 and (r[0] or r[1]):
                    pts.append((r[0], r[1]))
    return np.array(pts)


def fit_transform(C, U):
    H, W = C.shape
    dist = distance_transform_edt(C != SEA)
    ux, uy = U[:, 0], U[:, 1]
    best = None
    for mx in np.arange(8, 20, 0.5):
        for my in np.arange(12, 28, 0.5):
            for bx in range(-30, 260, 12):
                for by in range(-40, 180, 12):
                    ix = (mx * ux + bx).astype(int)
                    iy = (my * uy + by).astype(int)
                    if ix.min() < 0 or ix.max() >= W or iy.min() < 0 or iy.max() >= H:
                        continue
                    cl = C[iy, ix]
                    if (cl == SEA).any():
                        continue
                    cost = dist[iy, ix].mean()
                    if best is None or cost < best[0]:
                        best = (cost, mx, my, bx, by)
    return best


def build_grid(C, mx, my, bx, by, GW, GH):
    H, W = C.shape
    grid = []
    for y in range(GH):
        row = []
        for x in range(GW):
            cx, cy = int(mx * x + bx), int(my * y + by)
            win = C[max(0, cy - 6):cy + 7, max(0, cx - 7):cx + 8].ravel()
            if win.size == 0:
                row.append(SEA); continue
            cnt = Counter(win.tolist()); tot = win.size
            if cnt.get(ESCARP, 0) / tot > 0.22:
                row.append(ESCARP)
            elif cnt.get(ROAD, 0) / tot > 0.30 and cnt.get(SEA, 0) / tot < 0.5:
                row.append(ROAD)
            else:
                base = {k: cnt.get(k, 0) for k in (SEA, DESERT, MARSH)}
                row.append(max(base, key=base.get))
        grid.append(row)
    return grid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("snaps", nargs="+")
    ap.add_argument("--gw", type=int, default=120)
    ap.add_argument("--gh", type=int, default=38)
    ap.add_argument("--out", default="terrain_map.json")
    a = ap.parse_args()

    C = classify(Image.open(a.image))
    U = unit_coords(a.snaps)
    cost, mx, my, bx, by = fit_transform(C, U)
    print(f"fit: mx={mx} my={my} bx={bx} by={by}  (avg unit dist-to-coast {cost:.1f}px)")
    grid = build_grid(C, mx, my, bx, by, a.gw, a.gh)
    doc = {
        "source": "Desert Rats manual p.2 playing-area map, digitised",
        "coordinate_frame": "game units: unit.x,unit.y index terrain[y][x]",
        "width": a.gw, "height": a.gh,
        "transform_game_to_image": {"mx": mx, "my": my, "bx": bx, "by": by},
        "legend": {str(k): v for k, v in LEGEND.items()},
        "grid": grid,
    }
    json.dump(doc, open(a.out, "w"))
    print(f"wrote {a.out}  ({a.gw}x{a.gh}); class counts "
          f"{dict(Counter(c for r in grid for c in r))}")


if __name__ == "__main__":
    main()
