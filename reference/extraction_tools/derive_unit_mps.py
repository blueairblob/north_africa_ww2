"""Derive data/unit_mps.json: per-unit MPS for all 128 master_oob.json units.

master_oob.json's 10-byte packed table has NO mps field at all (confirmed:
see its own 'fields' string). The three legacy per-scenario snapshot files
(units_scenario_*.json -- superseded by master_oob.json for everything else,
but kept "for cross-checking" per README.md) were pulled from a *different*,
runtime unit-state table that does carry a live mps byte per on-map unit.

Method:
  1. For every on_map=true record in the three scenario snapshots, key by
     (designation, formation) and tally the mps value seen (majority vote
     across snapshots/turns resolves the few keys where off-map/uninitialised
     0 values or genuine inconsistency appear).
  2. For master_oob.json units whose (designation, division) key was directly
     observed on-map, use that per-unit confirmed value.
  3. For the rest, fall back to the majority mps value observed for other
     on-map units sharing the same `type` code.
  4. For the handful of types never seen on-map in any of the three snapshots,
     fall back to the global majority mps value across all observations.

This does not fully close the gap (67/128 units are still a type-level
guess, not a per-unit recovered value) but replaces a single flat constant
with real data wherever real data exists, and an evidenced fallback
elsewhere. See NOTES.md for the full accounting.
"""
import json
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"

oob = json.load(open(DATA / "master_oob.json"))["units"]
snapshot_files = [
    DATA / "units_scenario_enter_rommel.json",
    DATA / "units_scenario_battleaxe.json",
    DATA / "units_scenario_operation_crusader.json",
]

key_votes = collections.defaultdict(collections.Counter)
type_votes = collections.defaultdict(collections.Counter)
for f in snapshot_files:
    for u in json.load(open(f)):
        if u.get("on_map"):
            key_votes[(u["designation"], u["formation"])][u["mps"]] += 1
            type_votes[u["type"]][u["mps"]] += 1

global_votes = collections.Counter()
for c in type_votes.values():
    global_votes.update(c)
global_mode = global_votes.most_common(1)[0][0]

result = {}
counts = collections.Counter()
for u in oob:
    key = (u["designation"], u["division"])
    if key in key_votes:
        c = key_votes[key]
        mps, n = c.most_common(1)[0]
        total = sum(c.values())
        confidence = "confirmed" if len(c) == 1 else f"confirmed_majority({n}/{total})"
        source = "unit"
    elif u["type"] in type_votes:
        c = type_votes[u["type"]]
        mps, n = c.most_common(1)[0]
        total = sum(c.values())
        confidence = f"type_fallback(type={u['type']},{n}/{total})"
        source = "type"
    else:
        mps = global_mode
        confidence = "global_fallback(no_on_map_data_for_type)"
        source = "global"
    result[str(u["i"])] = {"mps": mps, "source": source, "confidence": confidence}
    counts[source] += 1

out = {
    "_provenance": (
        "Derived by reference/extraction_tools/derive_unit_mps.py from the "
        "on_map=true records in units_scenario_{enter_rommel,battleaxe,"
        "operation_crusader}.json, cross-referenced against master_oob.json "
        "by (designation, division). NOT part of the original master_oob "
        "10-byte table, which has no mps field. See BUILD_SPEC.md units.py "
        "notes and NOTES.md for the full account."
    ),
    "_counts": dict(counts),
    "units": result,
}
json.dump(out, open(DATA / "unit_mps.json", "w"), indent=1)
print(counts, "-> data/unit_mps.json written")
