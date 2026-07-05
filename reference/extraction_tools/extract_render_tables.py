"""Extract the original render model (attribute table, tile-index grid,
tile bitmaps) from the Desert Rats tape image.

Usage:
    python3 extract_render_tables.py /path/to/Desert_Rats_-_Side_1.tzx

Writes:
    data/render_model.json   -- COMMITTED: the 256-entry attribute table
                                (factual colour data), the full-byte
                                100x32 tile-index grid, and a derived
                                per-tile ink-coverage fraction. No pixel
                                art.
    data/tiles_original.json -- GITIGNORED, LOCAL ONLY: the 256 8-byte
                                tile bitmaps. This is the original's
                                pixel art; per the project's publishing
                                policy it must not be committed to a
                                public repo. The renderer uses it when
                                present for pixel-exact terrain, and
                                falls back to the coverage approximation
                                otherwise.

Recovered model (validated against a real gameplay screenshot and
pubmap_units.png -- see reference/screenshot_evidence.md and NOTES.md):

  * The map at 0xCB39 (100x32 bytes) stores a FULL-BYTE TILE INDEX per
    cell, not just a low-nibble type. Game logic masks the low nibble
    for terrain type; RENDERING uses the whole byte.
  * Attribute table at 0xD80E, 256 entries, indexed by the full cell
    byte: standard ZX attribute bytes (bit7 FLASH, bit6 BRIGHT,
    bits5-3 PAPER, bits2-0 INK). Organised in contiguous tile-index
    ranges (e.g. 0x23-0x44 -> yellow paper / red ink = escarpment art).
  * Tile bitmaps at 0xF6D8, 8 bytes per tile, MSB = leftmost pixel,
    indexed by the same full cell byte. tile[0x00] is blank (pure
    paper -> open desert); tile[0x0E] is solid (pure ink -> sea, whose
    "blue" is INK blue over yellow paper, fully covered).

Provenance for the base addresses: reference/engine-map.md located the
attribute-table accessors at 0xD80E during the original disassembly; the
tile base 0xF6D8 was found by searching loaded memory for the escarpment
tile bitmap independently extracted pixel-for-pixel from a real gameplay
screenshot, then confirmed by tile[0x00]=blank / tile[0x0E]=solid and a
94.8% sea-mask pixel agreement between a full-map reconstruction and
pubmap_units.png.
"""
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"

ATTR_BASE = 0xD80E
TILE_BASE = 0xF6D8
MAP_BASE = 0xCB39
MAP_W, MAP_H = 100, 32


def load_tzx_memory(path: str) -> bytes:
    """Parse a TZX tape image and reconstruct the 64K memory map by
    loading every Code block at its header-declared start address.
    """
    data = open(path, "rb").read()
    if data[:7] != b"ZXTape!":
        raise SystemExit(f"{path}: not a TZX file")
    pos = 10
    payloads = []
    while pos < len(data):
        bid = data[pos]
        pos += 1
        if bid == 0x10:  # standard speed data
            length = struct.unpack_from("<H", data, pos + 2)[0]
            payloads.append(data[pos + 4 : pos + 4 + length])
            pos += 4 + length
        elif bid == 0x11:  # turbo speed data
            length = data[pos + 15] | (data[pos + 16] << 8) | (data[pos + 17] << 16)
            payloads.append(data[pos + 18 : pos + 18 + length])
            pos += 18 + length
        elif bid == 0x30:  # text description
            pos += 1 + data[pos]
        elif bid == 0x32:  # archive info
            pos += 2 + struct.unpack_from("<H", data, pos)[0]
        elif bid == 0x20:  # pause / stop-the-tape
            pos += 2
        else:
            raise SystemExit(f"unhandled TZX block id 0x{bid:02X} at offset {pos-1}")

    mem = bytearray(65536)
    i = 0
    while i < len(payloads):
        p = payloads[i]
        if p[0] == 0x00 and len(p) >= 19 and p[1] == 3 and i + 1 < len(payloads):
            start = struct.unpack_from("<H", p, 14)[0]
            length = struct.unpack_from("<H", p, 12)[0]
            body = payloads[i + 1][1:-1]  # strip flag + checksum
            if len(body) != length:
                raise SystemExit(f"code block length mismatch: header {length}, data {len(body)}")
            mem[start : start + length] = body
            i += 2
        else:
            i += 1
    return bytes(mem)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    mem = load_tzx_memory(sys.argv[1])

    attrs = list(mem[ATTR_BASE : ATTR_BASE + 256])
    grid = [
        list(mem[MAP_BASE + y * MAP_W : MAP_BASE + (y + 1) * MAP_W])
        for y in range(MAP_H)
    ]
    tiles = [list(mem[TILE_BASE + t * 8 : TILE_BASE + t * 8 + 8]) for t in range(256)]

    # Logic-type table at 0xD90E: the movement/rules code derives a cell's
    # terrain TYPE as table[cell_byte] & 15 (verified in the mover's road
    # check) -- NOT as the cell byte's own low nibble, which the original
    # extraction wrongly assumed (2011/3200 cells differ). Real type space
    # is 0..8. Road-direction bits at 0xDA0E gate the road cost discount
    # to steps moving along the road.
    type_table = list(mem[0xD90E:0xDA0E])
    road_direction_table = list(mem[0xDA0E:0xDB0E])
    logic_type_grid = [[type_table[c] & 15 for c in row] for row in grid]

    terrain_logic = {
        "_provenance": (
            "Extracted by reference/extraction_tools/extract_render_tables.py. "
            "logic_type_grid[y][x] = type_table[cell_byte] & 15, the exact "
            "lookup the original movement code performs (road check: type == "
            "5). This SUPERSEDES terrain_authentic.json's grid for game "
            "logic: that file's low-nibble types are wrong for 2011 of 3200 "
            "cells. Confirmed type meanings: 0 = open desert (includes all "
            "decorative coast/border/label art -- passable), 1 = sea "
            "(impassable), 4 = escarpment, 5 = road, 6 = marsh/depression "
            "art. Types 2, 3, 7, 8 exist (small counts) with semantics not "
            "yet pinned. road_direction_table[cell_byte] carries the "
            "direction bits the road-discount test masks against the step "
            "direction. See NOTES.md."
        ),
        "type_table": type_table,
        "road_direction_table": road_direction_table,
        "logic_type_grid": logic_type_grid,
        "legend": {
            "0": "open desert (incl. decorative art cells)",
            "1": "sea (impassable)",
            "2": "unknown (17 cells)",
            "3": "unknown (23 cells)",
            "4": "escarpment",
            "5": "road/track",
            "6": "marsh/depression art",
            "7": "unknown (16 cells)",
            "8": "unknown (3 cells)",
        },
    }
    (DATA / "terrain_logic.json").write_text(json.dumps(terrain_logic, indent=1))

    # Sanity checks from the validated model
    assert attrs[0x00] == 0x30, "attr[0x00] should be PAPER yellow / INK black"
    assert all(b == 0x00 for b in tiles[0x00]), "tile 0x00 should be blank (open desert)"
    assert all(b == 0xFF for b in tiles[0x0E]), "tile 0x0E should be solid (sea)"

    coverage = [sum(bin(b).count("1") for b in t) / 64.0 for t in tiles]

    render_model = {
        "_provenance": (
            "Extracted by reference/extraction_tools/extract_render_tables.py "
            "from the original tape image. attribute_table: 256 ZX attribute "
            "bytes at 0xD80E indexed by the FULL map cell byte (bit7 FLASH, "
            "bit6 BRIGHT, bits5-3 PAPER, bits2-0 INK). tile_index_grid: the "
            "100x32 map at 0xCB39, full bytes (low nibble = game-logic "
            "terrain type; whole byte = tile/attr index for rendering). "
            "ink_coverage: fraction of set pixels per 8x8 tile, a derived "
            "statistic allowing an approximate render without the tile art "
            "(see data/tiles_original.json note). Validated against a real "
            "gameplay screenshot and pubmap_units.png -- see "
            "reference/screenshot_evidence.md and NOTES.md."
        ),
        "attribute_table": attrs,
        "tile_index_grid": grid,
        "ink_coverage": coverage,
    }
    (DATA / "render_model.json").write_text(json.dumps(render_model, indent=1))

    tiles_out = {
        "_warning": (
            "ORIGINAL PIXEL ART -- do not commit to a public repository. "
            "This file is gitignored; regenerate it locally with "
            "reference/extraction_tools/extract_render_tables.py from your "
            "own copy of the tape."
        ),
        "tile_base": TILE_BASE,
        "tiles": tiles,
    }
    (DATA / "tiles_original.json").write_text(json.dumps(tiles_out))

    print(f"wrote {DATA/'render_model.json'} (committed) and "
          f"{DATA/'tiles_original.json'} (gitignored, local only)")


if __name__ == "__main__":
    main()
