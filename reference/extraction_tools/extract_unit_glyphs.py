#!/usr/bin/env python3
"""Extract the unit-counter glyph family from the Desert Rats tape image.

Usage:
    python3 extract_unit_glyphs.py /path/to/Desert_Rats_-_Side_1.tzx

Writes:
    data/glyphs_original.json -- GITIGNORED, LOCAL ONLY: the 0xF438
                                 sprite/UDG family (8 bytes per 8x8 glyph,
                                 MSB = leftmost pixel), which per
                                 reference/engine-map.md #16 holds the
                                 unit-counter symbols drawn by routine
                                 0x694B. Original pixel art: same
                                 publishing policy as tiles_original.json.
    glyph_sheet_local.png     -- LOCAL ONLY contact sheet (indexed) for
                                 identifying which glyph indices are the
                                 unit symbols; used to fill in the
                                 committable mapping data/unit_symbols.json.

Model (engine-map.md #16): draw routine 0x694B fetches a pattern at
0xF438 + (symbol_code + hi*4 - 1) * 8. For a 2x2 counter the working
reading is hi = quadrant 0..3 (TL,TR,BL,BR), i.e. one symbol_code fans
out to four consecutive-by-hi glyphs; 1x1 travelling counters use a
single glyph. This quadrant reading is an INFERENCE (tracked as tunable
in NOTES.md deliverable format) -- pin it against the contact sheet and
a real gameplay screenshot before trusting it.
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"

GLYPH_BASE = 0xF438
GLYPH_COUNT = 361  # per engine-map.md: ~361 cells at 0xF438


def load_tzx_memory(path: str) -> bytearray:
    """Parse a TZX tape image and reconstruct the 64K memory map by
    loading every Code block at its header-declared start address.
    (Same loader as extract_render_tables.py.)
    """
    data = open(path, "rb").read()
    if data[:7] != b"ZXTape!":
        raise SystemExit(f"{path}: not a TZX file")
    pos = 10
    payloads = []
    while pos < len(data):
        bid = data[pos]
        pos += 1
        if bid == 0x10:
            length = struct.unpack_from("<H", data, pos + 2)[0]
            payloads.append(data[pos + 4 : pos + 4 + length])
            pos += 4 + length
        elif bid == 0x11:
            length = data[pos + 15] | (data[pos + 16] << 8) | (data[pos + 17] << 16)
            payloads.append(data[pos + 18 : pos + 18 + length])
            pos += 18 + length
        elif bid == 0x30:
            pos += 1 + data[pos]
        elif bid == 0x32:
            pos += 2 + struct.unpack_from("<H", data, pos)[0]
        else:
            raise SystemExit(f"unhandled TZX block 0x{bid:02X} at {pos-1}")

    mem = bytearray(65536)
    pending_header = None
    for p in payloads:
        if not p:
            continue
        flag, body = p[0], p[1:-1]  # strip flag + checksum
        if flag == 0x00 and len(body) == 17 and body[0] == 3:
            start = struct.unpack_from("<H", body, 12)[0]
            length = struct.unpack_from("<H", body, 10)[0]
            pending_header = (start, length)
        elif flag == 0xFF and pending_header:
            start, length = pending_header
            mem[start : start + len(body)] = body[:length]
            pending_header = None
    return mem


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    mem = load_tzx_memory(sys.argv[1])

    glyphs = [
        list(mem[GLYPH_BASE + i * 8 : GLYPH_BASE + (i + 1) * 8])
        for i in range(GLYPH_COUNT)
    ]

    (DATA / "glyphs_original.json").write_text(json.dumps({
        "_warning": (
            "ORIGINAL PIXEL ART -- do not commit to a public repository. "
            "Gitignored; regenerate locally with this script from your own "
            "copy of the tape."
        ),
        "glyph_base": GLYPH_BASE,
        "index_formula": "0xF438 + (symbol_code + hi*4 - 1) * 8  (engine-map.md #16)",
        "glyphs": glyphs,
    }))

    # Local contact sheet: 16 glyphs per row, 4x scale, index label rows.
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not installed; skipped contact sheet")
    else:
        per_row, scale, pitch = 16, 4, 8 * 4 + 14
        rows = (GLYPH_COUNT + per_row - 1) // per_row
        sheet = Image.new("RGB", (per_row * pitch, rows * pitch), (20, 20, 30))
        dr = ImageDraw.Draw(sheet)
        for i, g in enumerate(glyphs):
            gx, gy = (i % per_row) * pitch, (i // per_row) * pitch
            for ry in range(8):
                for rx in range(8):
                    if g[ry] & (0x80 >> rx):
                        dr.rectangle(
                            [gx + rx * scale, gy + ry * scale,
                             gx + rx * scale + scale - 1, gy + ry * scale + scale - 1],
                            fill=(230, 225, 180),
                        )
            dr.text((gx, gy + 8 * scale + 1), str(i), fill=(150, 150, 160))
        out = ROOT / "glyph_sheet_local.png"
        sheet.save(out)
        print(f"wrote {out} (LOCAL ONLY -- original art)")

    print(f"wrote {DATA / 'glyphs_original.json'} (gitignored, local only)")


if __name__ == "__main__":
    main()
