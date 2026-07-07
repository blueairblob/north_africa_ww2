"""Extract the pressure-projection tables from the tape memory.

- class -> column index (0xDB8F, used by 0x6454)
- terrain-class percentage table in tenths at 0xDD94, laid out as
  11-byte blocks PER CLASS-COLUMN, indexed within each block by terrain
  type (rows 0-8) or 10 (the supplied-defender modifier used by 0x82C9):
  value = bytes[11*column + row] -- verified against the 0x6C8C indexer
  (index = 11*col + row) and the 0x82C9 oracle (class 12 -> col 0 ->
  row 10 = 5 -> x0.5)
- class percentage table used by 0x8286 (values oracle-verified; the
  table itself is embedded -- we store the oracled mapping)

Factual data -> committed to data/combat_tables.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_render_tables import load_tzx_memory

ROOT = Path(__file__).resolve().parent.parent.parent

CLASS_PCT = {1: 60, 2: 60, 3: 30, 4: 30, 5: 50, 6: 50, 7: 70,
             8: 50, 9: 30, 10: 20, 11: 50, 12: 50, 13: 0}


def main(tape):
    mem = load_tzx_memory(tape)
    class_col = list(mem[0xDB8F:0xDB8F + 14])
    # one 11-byte block per class-column; block[row] with row = terrain
    # type 0-8 or 10 (supplied-defender)
    dd94 = [list(mem[0xDD94 + c * 11: 0xDD94 + (c + 1) * 11]) for c in range(11)]
    out = {
        "_provenance": (
            "Recovered from the original's combat data "
            "(reference/extraction_tools/extract_combat_tables.py); "
            "semantics disassembled/oracle-verified -- see NOTES.md "
            "'Pressure inflow: recovered'."
        ),
        "class_to_column": class_col,
        "tenths_by_column": dd94,
        "class_pct": CLASS_PCT,
        "supplied_defender_row": 10,
    }
    path = ROOT / "data" / "combat_tables.json"
    path.write_text(json.dumps(out, indent=1))
    print(f"wrote {path}")


if __name__ == "__main__":
    main(sys.argv[1])
