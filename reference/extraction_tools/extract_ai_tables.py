"""Extract the AI's strategic data tables from the tape memory.

- 30 strategic REGIONS at 0xD6F1 (7 bytes each): two anchor coordinate
  pairs, an importance value (low 3 bits of byte 4; upper bits are
  runtime flags), and two runtime accumulator bytes.
- The OBJECTIVE LADDER at 0xE07F (length byte + entries) that the target
  chooser walks directionally per side (Axis forward, British backward).

Factual data (coordinates/valuations recovered by analysis) -> committed
to data/ai_regions.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_render_tables import load_tzx_memory

ROOT = Path(__file__).resolve().parent.parent.parent
D6F1, E07F = 0xD6F1, 0xE07F


def main(tape):
    mem = load_tzx_memory(tape)
    regions = []
    for i in range(30):
        b = mem[D6F1 + i * 7 : D6F1 + (i + 1) * 7]
        regions.append({
            "index": i,
            "anchor_a": [b[0], b[1]],
            "anchor_b": [b[2], b[3]],
            "importance": b[4] & 7,
        })
    ladder_len = mem[E07F]
    ladder = list(mem[E07F : E07F + ladder_len])
    out = {
        "_provenance": (
            "Recovered from the original's AI data by analysis "
            "(reference/extraction_tools/extract_ai_tables.py): region "
            "strength-map table at 0xD6F1 and the objective ladder at "
            "0xE07F. Semantics oracle-verified/disassembled -- see "
            "reference/engine-map.md section 15."
        ),
        "regions": regions,
        "objective_ladder": ladder,
    }
    path = ROOT / "data" / "ai_regions.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path} ({len(regions)} regions, ladder len {ladder_len})")


if __name__ == "__main__":
    main(sys.argv[1])
