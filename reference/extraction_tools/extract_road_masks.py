"""Extract the road-connectivity mask table (0xDA0E).

The third per-cell byte table (sibling of the attribute table 0xD80E and
type table 0xD90E, all indexed by cell byte via 0x6437): a direction
bitmask per cell value. Low nibble bits 0-3 = directions N/E/S/W for
pathing connectivity (0x6BA7/0x6BC3); high nibble bits 4-7 = the same
directions gating the road-speed bonus (0x8592: on a road cell, moving/
pressing in a connected direction applies tenths[class][row 9]/10).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_render_tables import load_tzx_memory

ROOT = Path(__file__).resolve().parent.parent.parent


def main(tape):
    mem = load_tzx_memory(tape)
    table = list(mem[0xDA0E:0xDA0E + 256])
    out = {
        "_provenance": (
            "Recovered road-connectivity masks (per-cell-byte table at "
            "0xDA0E; see NOTES.md 'Closing sweep'). Directions 0-3 = "
            "N/E/S/W; low nibble = pathing connectivity, high nibble = "
            "road-speed-bonus gating."
        ),
        "mask_by_cell_byte": table,
    }
    (ROOT / "data" / "road_masks.json").write_text(json.dumps(out, indent=1))
    print("wrote data/road_masks.json")


if __name__ == "__main__":
    main(sys.argv[1])
