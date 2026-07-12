#!/usr/bin/env python3
"""Render the authentic Desert Rats terrain screen from extracted data.

Two modes, chosen automatically:

  EXACT  -- if data/tiles_original.json exists (gitignored, local-only;
            regenerate with reference/extraction_tools/
            extract_render_tables.py from your own tape), renders the
            100x32 map pixel-for-pixel: full cell byte -> tile bitmap
            (8 bytes, MSB leftmost) + ZX attribute (paper/ink/bright)
            from data/render_model.json. This IS the original terrain
            art, town-name letter tiles included -- keep the output
            local, same policy as tiles_original.json.

  APPROX -- without the tile art, per-cell ink_coverage from
            render_model.json is rendered as an ordered-dither fill in
            the correct attribute colours. Geometry, colours and layout
            are faithful; pixel art is not. Safe to share/commit.

Usage:
    python3 render_authentic_map.py [--scale N] [--out FILE]
Run from the repo root (reads data/render_model.json).
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ZX = {  # index -> (normal, bright)
    0: ((0, 0, 0), (0, 0, 0)),
    1: ((0, 0, 215), (0, 0, 255)),
    2: ((215, 0, 0), (255, 0, 0)),
    3: ((215, 0, 215), (255, 0, 255)),
    4: ((0, 215, 0), (0, 255, 0)),
    5: ((0, 215, 215), (0, 255, 255)),
    6: ((215, 215, 0), (255, 255, 0)),
    7: ((215, 215, 215), (255, 255, 255)),
}

BAYER8 = [  # classic 8x8 ordered-dither matrix, values 0..63
    [0, 32, 8, 40, 2, 34, 10, 42],
    [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38],
    [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41],
    [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37],
    [63, 31, 55, 23, 61, 29, 53, 21],
]


def attr_colours(attr: int):
    bright = 1 if attr & 0x40 else 0
    ink = ZX[attr & 0x07][bright]
    paper = ZX[(attr >> 3) & 0x07][bright]
    return ink, paper


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("--out", default=None)
    ap.add_argument("--data", default="data", help="data directory")
    args = ap.parse_args()

    data = Path(args.data)
    rm = json.load(open(data / "render_model.json"))
    grid = rm["tile_index_grid"]
    attrs = rm["attribute_table"]
    coverage = rm["ink_coverage"]
    H, W = len(grid), len(grid[0])

    tiles = None
    tiles_path = data / "tiles_original.json"
    if tiles_path.exists():
        tiles = json.load(open(tiles_path))["tiles"]
        mode = "EXACT (original tile art -- keep output local)"
    else:
        mode = "APPROX (ink-coverage dither; run locally with tiles_original.json for pixel-exact)"

    out = args.out or ("terrain_exact.png" if tiles else "terrain_approx.png")

    img = Image.new("RGB", (W * 8, H * 8))
    px = img.load()
    for cy in range(H):
        for cx in range(W):
            b = grid[cy][cx]
            ink, paper = attr_colours(attrs[b])
            if tiles:
                t = tiles[b]
                for ry in range(8):
                    row = t[ry]
                    for rx in range(8):
                        on = (row >> (7 - rx)) & 1
                        px[cx * 8 + rx, cy * 8 + ry] = ink if on else paper
            else:
                thresh = coverage[b] * 64.0
                for ry in range(8):
                    for rx in range(8):
                        on = BAYER8[ry][rx] < thresh
                        px[cx * 8 + rx, cy * 8 + ry] = ink if on else paper

    if args.scale != 1:
        img = img.resize((W * 8 * args.scale, H * 8 * args.scale), Image.NEAREST)
    img.save(out)
    print(f"mode: {mode}")
    print(f"{out}: {img.size[0]}x{img.size[1]} ({W}x{H} cells, scale {args.scale})")


if __name__ == "__main__":
    main()
