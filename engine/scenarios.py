"""Scenario files (data/scenarios), read into what the engine is given (docs/RULES.md 2.4).
The one place besides __main__ where the engine reads a file."""
import json
from pathlib import Path

from . import state as S

FOLDER = Path(__file__).parent.parent / "data" / "scenarios"


def names(folder=FOLDER):
    return sorted(f.stem for f in Path(folder).glob("*.json"))


def load(name, folder=FOLDER):
    """The scenario of this name. One cut from another names its base and gives only what
    differs: it is the base up to its own last turn (2.4)."""
    scenario = json.loads((Path(folder) / f"{name}.json").read_text(encoding="utf-8"))
    if "base" not in scenario:
        return scenario
    whole = load(scenario.pop("base"), folder)
    whole.update(scenario)

    def late(day):
        return S.turn_of(whole, day) > whole["turns"]
    whole["units"] = [u for u in whole["units"] if "arrives" not in u or not late(u["arrives"])]
    here = {u["id"] for u in whole["units"]}
    for kind in ("withdrawals", "replacements"):
        whole[kind] = [e for e in whole.get(kind, []) if e["unit"] in here and not late(e["date"])]
    return whole
