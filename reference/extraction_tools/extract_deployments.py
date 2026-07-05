"""Extract per-scenario scripted deployments from the tape image.

Usage:
    python3 extract_deployments.py /path/to/Desert_Rats_-_Side_1.tzx

Writes data/deployments.json: for each scenario, the list of units present
at scenario start with their scripted starting positions.

Recovered model (see NOTES.md "Deployment & stacking"): scenario records
live at 0xDE53 + index*25 with a 1-BASED index (record 0 is a dummy);
record bytes [4..5] are a little-endian offset into a deployment region at
0xEABF. Each deployment list is [count] then count x 3-byte entries of
(unit_slot, x, y), unit_slot 1-based into the 128-record roster. The
placement routine (0x93AF) writes x/y directly per entry -- initial
deployment is scripted historical data, NOT edge-staging. Divisions are
deployed clustered (often several units on the SAME cell), which is the
"formation stacking" visible in the original game. Edge staging applies
only to later reinforcements.

Validation: division clustering (e.g. Ariete's four units on one cell,
9th Australian at the Tobruk area) and scenario-record day windows
matching data/scenarios.json exactly.
"""
import json
import sys
from pathlib import Path

from extract_render_tables import load_tzx_memory  # same directory

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"

SCENARIO_RECORDS = 0xDE53   # 25 bytes each, 1-based index
DEPLOY_BASE = 0xEABF


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    mem = load_tzx_memory(sys.argv[1])

    scenarios_json = json.loads((DATA / "scenarios.json").read_text())["scenarios"]

    out_scenarios = {}
    for idx in range(1, 7):
        rec = mem[SCENARIO_RECORDS + idx * 25 : SCENARIO_RECORDS + (idx + 1) * 25]
        start_day = rec[0] | (rec[1] << 8)
        end_day = rec[2] | (rec[3] << 8)
        expected = scenarios_json[idx - 1]
        if (start_day, end_day) != (expected["start_day"], expected["end_day"]):
            raise SystemExit(
                f"scenario {idx} day-window mismatch vs scenarios.json: "
                f"tape ({start_day},{end_day}) vs ({expected['start_day']},{expected['end_day']})"
            )
        base = DEPLOY_BASE + (rec[4] | (rec[5] << 8))
        count = mem[base]
        entries = []
        for i in range(count):
            slot, x, y = mem[base + 1 + i * 3 : base + 4 + i * 3]
            entries.append({"oob_index": slot - 1, "x": x, "y": y})
        out_scenarios[str(idx)] = entries

    out = {
        "_provenance": (
            "Extracted by reference/extraction_tools/extract_deployments.py. "
            "Per-scenario scripted starting deployments recovered from the "
            "scenario records (0xDE53, 1-based, bytes 4-5 = offset) and the "
            "deployment region (0xEABF, [count][slot,x,y]*count, slot "
            "1-based -> oob_index = slot-1). Placement routine 0x93AF writes "
            "these coordinates directly; divisions deploy clustered, often "
            "sharing cells (original setup permits co-located units). "
            "Day-window cross-check against scenarios.json passed on "
            "extraction. See NOTES.md."
        ),
        "scenarios": out_scenarios,
    }
    (DATA / "deployments.json").write_text(json.dumps(out, indent=1))
    counts = {k: len(v) for k, v in out_scenarios.items()}
    print(f"wrote {DATA / 'deployments.json'} — entries per scenario: {counts}")


if __name__ == "__main__":
    main()
