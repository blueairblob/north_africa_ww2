"""Scenario files (data/scenarios), read into what the engine is given (docs/RULES.md 2.4).
The one place besides __main__ where the engine reads a file."""
import json
from datetime import date
from pathlib import Path

from . import state as S

FOLDER = Path(__file__).parent.parent / "data" / "scenarios"


def names(folder=FOLDER):
    return sorted(f.stem for f in Path(folder).glob("*.json"))


def load(name, folder=FOLDER):
    """The scenario of this name. One cut from another names its base and gives only what
    differs: it is the base up to its own last turn (2.4). A linked chapter
    may add units and update non-identity fields without copying the roster.
    A sourced redesignation can change a name while preserving the unit id."""
    scenario = json.loads((Path(folder) / f"{name}.json").read_text(encoding="utf-8"))
    if "base" not in scenario:
        return scenario
    whole = load(scenario.pop("base"), folder)
    added_units = scenario.pop("add_units", [])
    unit_updates = scenario.pop("unit_updates", {})
    retired_units = set(scenario.pop("retire_units", []))
    sources = scenario.pop("sources", {})
    whole.update(scenario)
    whole["sources"] = {**whole.get("sources", {}), **sources}
    before = {spec["id"] for spec in whole["units"]}
    if not retired_units <= before or retired_units & {spec["id"] for spec in added_units}:
        raise ValueError("A retired unit must exist in the preceding roster and cannot be added again.")
    whole["units"] = [spec for spec in whole["units"] if spec["id"] not in retired_units] + added_units
    by_id = {spec["id"]: spec for spec in whole["units"]}
    for uid, changes in unit_updates.items():
        spec = by_id[int(uid)]
        if set(changes) & {"id", "side", "type"}:
            raise ValueError("A chapter unit update cannot replace a formation's identity.")
        if "name" in changes and (spec["name"] not in changes.get("alternate_names", [])
                                  or changes.get("redesignation_src") not in whole["sources"]):
            raise ValueError("A formation redesignation needs its old name and a scenario source.")
        spec.update(changes)

    def late(day):
        return S.turn_of(whole, day) > whole["turns"]
    whole["units"] = [u for u in whole["units"] if "arrives" not in u or not late(u["arrives"])]
    here = {u["id"] for u in whole["units"]}
    for kind in ("withdrawals", "replacements", "returns", "redesignations"):
        whole[kind] = [e for e in whole.get(kind, []) if e["unit"] in here and not late(e["date"])]
    for kind in ("returns", "redesignations"):
        whole[kind] = [e for e in whole.get(kind, [])
                       if date.fromisoformat(e["date"]) >= date.fromisoformat(whole["start"])]
    return whole
