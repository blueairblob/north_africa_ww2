"""Bake the default pack's cartographic map image.

Renders the pack's own atlas layer (an original work: own terrain
digitization + own place compilation + generic period-cartography
conventions) at high resolution into content_packs/default/map.png, and
writes the matching map_calibration.json. The game then uses the image
as THE map -- the 100x32 grid is the invisible engine underlay and
counters are transposed onto the image via the calibration.

Rebuild after changing the terrain or features:
    python3 tools/build_default_map.py
    python3 tools/build_default_map_image.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CELL_PX = 32  # bake resolution: 3200x1024


def main():
    import sys
    sys.path.insert(0, str(ROOT))
    from desert_rats import board, packs
    from desert_rats.render import image

    packs.set_active_pack("default")
    b = board.load_board()
    img = image.render_board_image([], b, cell_px=CELL_PX, use_map_image=False)
    out = ROOT / "content_packs" / "default" / "map.png"
    img.save(out, optimize=True)

    cal = ROOT / "content_packs" / "default" / "map_calibration.json"
    cal.write_text(json.dumps({
        "_provenance": (
            "Identity calibration for the baked atlas image "
            f"(tools/build_default_map_image.py, {CELL_PX}px per cell)."
        ),
        "cell_to_px_x": [CELL_PX, 0],
        "cell_to_px_y": [CELL_PX, 0],
    }, indent=1))
    print(f"wrote {out} ({img.size[0]}x{img.size[1]}) and {cal}")


if __name__ == "__main__":
    main()
