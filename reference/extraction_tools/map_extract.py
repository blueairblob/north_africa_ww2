#!/usr/bin/env python3
"""
map_extract.py - extract the Desert Rats terrain map from a snapshot.

Map array located by: static low-value region right after the unit arrays,
row width found by vertical-correlation, base fixed by the constraint that every
on-map unit sits on land (never sea).

    base   = 0xC5A4
    width  = 100   (matches unit X range 8..98)
    height ~= 32    (desert core rows ~14-27; sea above, coast strip rows 8-13)

Encoding: terrain in the low byte values (CONFIRMED: 0 = sea, 14 = desert);
higher byte values carry coastal features (road / town / escarpment / rough).
Full per-code legend still to be pinned by scrolling to known features in-game
or reading the tile-draw lookup in the disassembly.

Usage:
    python3 map_extract.py scenario_enter_rommel.szx [--base 0xC5A4 --width 100 --height 32]
"""
import argparse, json, os
from collections import Counter
from skoolkit.snapshot import get_snapshot

LEGEND = {0: "sea", 14: "desert"}  # confirmed; extend as codes are identified

# rough palette for rendering (terrain low values; features collapsed to one tone)
PALETTE = {0: (45, 95, 205), 14: (205, 195, 75)}
FEATURE = (110, 75, 40)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snap")
    ap.add_argument("--base", type=lambda s: int(s, 0), default=0xC5A4)
    ap.add_argument("--width", type=int, default=100)
    ap.add_argument("--height", type=int, default=32)
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--scale", type=int, default=8)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    m = get_snapshot(a.snap)
    B, W, H = a.base, a.width, a.height
    grid = [[m[B + y * W + x] for x in range(W)] for y in range(H)]

    stem = os.path.splitext(os.path.basename(a.snap))[0]
    flat = [c for row in grid for c in row]
    doc = {
        "base": f"0x{B:04X}", "width": W, "height": H,
        "legend": {str(k): v for k, v in LEGEND.items()},
        "histogram": {str(v): n for v, n in Counter(flat).most_common()},
        "grid": grid,
    }
    jpath = os.path.join(a.outdir, f"terrain_{stem}.json")
    with open(jpath, "w") as f:
        json.dump(doc, f)

    # render
    try:
        from PIL import Image
        img = Image.new("RGB", (W, H))
        img.putdata([PALETTE.get(v, FEATURE) for v in flat])
        img = img.resize((W * a.scale, H * a.scale), Image.NEAREST)
        ppath = os.path.join(a.outdir, f"terrain_{stem}.png")
        img.save(ppath)
    except ImportError:
        ppath = "(PIL not installed - PNG skipped)"

    print(f"{stem}: {W}x{H} terrain grid -> {jpath}")
    print(f"  render -> {ppath}")
    print(f"  top codes: {Counter(flat).most_common(8)}")


if __name__ == "__main__":
    main()
