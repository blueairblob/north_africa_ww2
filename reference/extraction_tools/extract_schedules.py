"""Extract the turn-phased campaign schedule tables from the tape image.

Usage:
    python3 extract_schedules.py /path/to/Desert_Rats_-_Side_1.tzx

Writes data/schedules.json.

These are the tables BUILD_SPEC.md §10 listed as "located, not fully
labelled". Their structure (index formulas, side offsets, scaling, and
the Malta gating) was pinned by reading the reader routines at
0x96E0/0x9704/0x9740 (the "0x96E0 family" engine-map.md already pointed
at); the value semantics beyond that are recorded as hypotheses in the
output and in NOTES.md, to be settled by the diff harness.

Recovered structure:

  monthly_unit_schedule (0xDEFC, 22 groups x 6 bytes):
      index = (turn/30)*6 + (side-1)*2 + q, where q in {0,1} selects one
      of two per-side quantities (reader 0x9740, entered via 0x9732 with
      q=0 or 0x9739 with q=1). Bytes 4-5 of each group are not read by
      this routine family. Values are x10-scaled on read and then passed
      through the Malta modifier (below).

  monthly_side_rate (0xDF84, 22 entries per side, side 2 at +22):
      index = turn/30 (+22 if current side != 1); value x10 on read;
      then the Malta modifier (reader 0x96E0). Side 1's ramp 5..20
      across the war against side 2's flat 10 (peaking 15 in months
      13-14, the Gazala window) strongly suggests side 1 = British and
      the value is a supply/replacement rate -- hypothesis, not
      confirmed.

  malta_modifier (0xDFB6, 22 entries per half, second half at +22):
      Applied by 0x9704 ONLY when the current side != 1 (i.e. Axis).
      A selector at 0xCB25 picks: 1 -> first half, 2 (default path) ->
      second half, 3 -> bypass entirely. This is the invocation of the
      MALTA STATUS option (ui_strings.json malta_options) that
      engine-map.md §"still at large" believed was absent from the 48K
      image -- it modulates Axis-side scheduled values month by month.
      The exact arithmetic 0x82DF applies (scale/percentage) is not yet
      pinned.

The supply curve at 0xDFE8 sits immediately after and is re-verified on
extraction as an alignment check.
"""
import json
import sys
from pathlib import Path

from extract_render_tables import load_tzx_memory  # same directory

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"

SUPPLY_CURVE = [90,80,75,70,65,60,55,50,49,48,47,46,45,44,43,42,41,41,40,40,
                39,39,38,38,37,37,36,36,36,35,35]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    mem = load_tzx_memory(sys.argv[1])

    curve = list(mem[0xDFE8:0xDFE8 + 31])
    if curve != SUPPLY_CURVE:
        raise SystemExit("supply-curve alignment check FAILED -- wrong tape image?")

    monthly_unit_schedule = [
        list(mem[0xDEFC + m * 6 : 0xDEFC + (m + 1) * 6]) for m in range(22)
    ]
    monthly_side_rate = {
        "side_1": list(mem[0xDF84:0xDF84 + 22]),
        "side_2": list(mem[0xDF84 + 22:0xDF84 + 44]),
    }
    malta_modifier = {
        "half_1": list(mem[0xDFB6:0xDFB6 + 22]),
        "half_2": list(mem[0xDFB6 + 22:0xDFB6 + 44]),
    }

    out = {
        "_provenance": (
            "Extracted by reference/extraction_tools/extract_schedules.py. "
            "Structure (index formulas, side offsets, x10 scaling, Malta "
            "gating at 0xCB25) recovered from the reader routines at "
            "0x96E0/0x9704/0x9740; see this script's docstring and NOTES.md. "
            "Value SEMANTICS are hypotheses pending the diff harness. "
            "Supply-curve alignment check passed on extraction."
        ),
        "index_formula": "month = turn // 30 (turn counter at 0xCB0F); values x10 on read",
        "monthly_unit_schedule": monthly_unit_schedule,
        "monthly_unit_schedule_layout": "[nat1_poolA, nat1_poolB, nat2_poolA, nat2_poolB, nat3_poolA, nat3_poolB] per month -- CORRECTED: the monthly economy tick (0x978E) reads all three nationality pairs into the replacement pools (the earlier 'unread' note was wrong)",
        "monthly_side_rate": monthly_side_rate,
        "malta_modifier": malta_modifier,
        "malta_selector": "0xCB25: 1 -> half_1, 2 -> half_2, 3 -> bypass; applied to side != 1 only",
    }
    (DATA / "schedules.json").write_text(json.dumps(out, indent=1))
    print(f"wrote {DATA / 'schedules.json'} (supply-curve alignment check passed)")


if __name__ == "__main__":
    main()
