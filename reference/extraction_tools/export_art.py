#!/usr/bin/env python3
"""Regenerate original art assets from the locally-extracted data.

The public repo ships TOOLS, never ART (see NOTES.md asset policy). This
script is the "art regenerates on demand" half of that bargain: given the
local-only extracts, it reproduces every sheet/PNG the docs refer to.

Inputs (all gitignored, local-only -- produce them from your own tape with
extract_render_tables.py and extract_unit_glyphs.py):
    data/tiles_original.json     256 terrain tile bitmaps
    data/glyphs_original.json    0xF438 sprite/UDG family (unit symbols)
    data/font_original.json      character set (optional)

Outputs (ALL gitignored -- original pixel art):
    data/tiles_sheet.png         contact sheet, 256 terrain tiles, indexed
    glyph_sheet_local.png        contact sheet, 0xF438 family, indexed
    data/font_sheet.png          contact sheet, character set (if present)
    terrain_exact.png            the full 100x32 map in exact tile art
                                 (delegates to render_authentic_map.py)

Usage:
    python3 export_art.py [--scale N] [--all|--tiles|--glyphs|--font|--map]

Nothing here is committable. Everything here is reproducible.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"

try:
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("needs Pillow: pip install desert-rats[image]")

PAPER = (20, 20, 30)
INK = (230, 225, 180)
LABEL = (150, 150, 160)


def _load(name: str):
    p = DATA / name
    if not p.exists():
        return None
    doc = json.loads(p.read_text())
    for key in ("tiles", "glyphs", "chars", "font"):
        if key in doc:
            return doc[key]
    raise SystemExit(f"{name}: no recognised bitmap array")


def contact_sheet(bitmaps, out: Path, scale: int = 4, per_row: int = 16) -> None:
    """Indexed contact sheet: every 8x8 bitmap at `scale`, labelled."""
    pitch = 8 * scale + 14
    rows = (len(bitmaps) + per_row - 1) // per_row
    sheet = Image.new("RGB", (per_row * pitch, rows * pitch), PAPER)
    dr = ImageDraw.Draw(sheet)
    for i, b in enumerate(bitmaps):
        gx, gy = (i % per_row) * pitch, (i // per_row) * pitch
        for ry in range(8):
            byte = b[ry]
            if not byte:
                continue
            for rx in range(8):
                if byte & (0x80 >> rx):
                    dr.rectangle(
                        [gx + rx * scale, gy + ry * scale,
                         gx + rx * scale + scale - 1, gy + ry * scale + scale - 1],
                        fill=INK,
                    )
        dr.text((gx, gy + 8 * scale + 1), str(i), fill=LABEL)
    sheet.save(out)
    print(f"  wrote {out.relative_to(ROOT)}  ({len(bitmaps)} cells @ {scale}x)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--tiles", action="store_true")
    ap.add_argument("--glyphs", action="store_true")
    ap.add_argument("--font", action="store_true")
    ap.add_argument("--map", action="store_true")
    args = ap.parse_args()
    if not any((args.all, args.tiles, args.glyphs, args.font, args.map)):
        args.all = True

    print("Regenerating original art (LOCAL ONLY -- do not commit):")
    did = False

    if args.all or args.tiles:
        t = _load("tiles_original.json")
        if t:
            contact_sheet(t, DATA / "tiles_sheet.png", args.scale)
            did = True
        else:
            print("  skip tiles_sheet.png: data/tiles_original.json absent "
                  "(run extract_render_tables.py)")

    if args.all or args.glyphs:
        g = _load("glyphs_original.json")
        if g:
            contact_sheet(g, ROOT / "glyph_sheet_local.png", args.scale)
            did = True
        else:
            print("  skip glyph_sheet_local.png: data/glyphs_original.json absent "
                  "(run extract_unit_glyphs.py)")

    if args.all or args.font:
        f = _load("font_original.json")
        if f:
            contact_sheet(f, DATA / "font_sheet.png", args.scale)
            did = True
        else:
            print("  skip font_sheet.png: data/font_original.json absent")

    if args.all or args.map:
        t = _load("tiles_original.json")
        if t:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import render_authentic_map as ram

            rm = json.loads((DATA / "render_model.json").read_text())
            img = Image.new("RGB", (100 * 8, 32 * 8))
            px = img.load()
            for cy, row in enumerate(rm["tile_index_grid"]):
                for cx, b in enumerate(row):
                    ink, paper = ram.attr_colours(rm["attribute_table"][b])
                    for ry in range(8):
                        bits = t[b][ry]
                        for rx in range(8):
                            px[cx * 8 + rx, cy * 8 + ry] = (
                                ink if (bits >> (7 - rx)) & 1 else paper
                            )
            if args.scale != 1:
                img = img.resize((800 * args.scale, 256 * args.scale), Image.NEAREST)
            out = ROOT / "terrain_exact.png"
            img.save(out)
            print(f"  wrote {out.relative_to(ROOT)}  (100x32 cells @ {args.scale}x)")
            did = True
        else:
            print("  skip terrain_exact.png: data/tiles_original.json absent")

    if not did:
        raise SystemExit(
            "\nNo art produced: extract from your own tape first --\n"
            "  python3 reference/extraction_tools/extract_render_tables.py TAPE.tzx\n"
            "  python3 reference/extraction_tools/extract_unit_glyphs.py TAPE.tzx"
        )


if __name__ == "__main__":
    main()
