"""Extract the per-scenario victory conditions (0xDE53 records, 25 bytes).

Recovered semantics (scorer 0x9925, ladder 0x9A07; see NOTES.md
"Victory conditions: recovered"):

Each side has TWO objectives (British at record +8/+10, Axis at +12/+14),
each a (type, value) pair, plus a per-side surviving-unit threshold at
+0x15 (British) / +0x16 (Axis). A side scores 0-3 points:
  +1 per objective met (handlers at 0x9970);
  +3 (replacing the objective score) when the OPPOSING side has been
     wiped out (enemy on-map unit count == 0), i.e. annihilation;
  the score is ZEROED if the side's own surviving-unit count has fallen
     below its threshold (0x995A/0x996B).

Objective TYPE CODES (0x9970 dispatch):
  0 -> unused/none (contributes nothing)
  1 -> "reach the map edge": scan the board for a friendly unit in the
       far column band (0x99C2 -> 0x6CB0 raster scan, column 0x2B+)
  3 -> "hold the line at column V": the side's front-line column
       (0xCB07 British / 0xCB08 Axis) must be at or beyond V
       (British: front >= V; Axis: front <= V -- the DEC A/CP inversion)
  4 -> "the enemy must NOT be beyond column V" (the mirrored test)
  5 -> "keep at least V+1 units on the map" (0x99DE, counts via 0x8C0B)
Values are map columns (types 3/4) or unit counts (type 5).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_render_tables import load_tzx_memory

ROOT = Path(__file__).resolve().parent.parent.parent
BASE, STRIDE = 0xDE53, 0x19


def main(tape):
    mem = load_tzx_memory(tape)
    scenarios = []
    for s in range(6):
        b = mem[BASE + s * STRIDE: BASE + (s + 1) * STRIDE]
        scenarios.append({
            "index": s,
            "british_objectives": [[b[8], b[9]], [b[10], b[11]]],
            "axis_objectives": [[b[12], b[13]], [b[14], b[15]]],
            "british_unit_threshold": b[0x15],
            "axis_unit_threshold": b[0x16],
        })
    out = {
        "_provenance": (
            "Recovered per-scenario victory conditions (0xDE53 records); "
            "scorer 0x9925, ladder 0x9A07. See NOTES.md."
        ),
        "type_codes": {
            "0": "none",
            "1": "reach map edge",
            "3": "hold front line at/beyond column V",
            "4": "enemy front line not beyond column V",
            "5": "keep more than V units on map",
        },
        "ladder": {
            "0": "draw (equal scores)",
            "1": "tactical", "2": "major", "3": "decisive",
        },
        "scenarios": scenarios,
    }
    (ROOT / "data" / "victory_conditions.json").write_text(json.dumps(out, indent=1))
    print("wrote data/victory_conditions.json")


if __name__ == "__main__":
    main(sys.argv[1])
