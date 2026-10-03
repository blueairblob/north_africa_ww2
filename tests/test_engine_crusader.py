"""The Crusader scenario: checked, and played to the end by scripted players."""
import json

import pytest

from engine import checker, players, runner
from engine import state as S
from engine.turn import begin_turn
from helpers import GMAP, ROOT, small


def crusader():
    return json.loads((ROOT / "data" / "scenarios" / "crusader.json").read_text())


def test_the_scenarios_pass_the_checker():
    assert checker.problems(crusader(), GMAP) == []
    assert checker.problems(small(), GMAP) == []


def test_the_checker_finds_what_is_wrong():
    sc = crusader()
    sc["units"][0]["hex"] = [0, 0]                               # in the sea
    sc["units"][1]["hex"] = [83, 43]                             # land nothing can leave
    sc["units"][2]["at"] = "Atlantis"
    sc["owners"]["axis"].remove("Bardia")
    sc["objectives"].append({"place": "Atlantis", "turn": 1})
    sc["units"].append(dict(sc["units"][3], id=999, name="Lost division", at="Tobruk"))     # an enemy in Tobruk
    sc["units"].append(dict(sc["units"][4]))                     # a repeated id
    found = "\n".join(checker.problems(sc, GMAP))
    for clue in ("unit 101", "unit 102", "Atlantis is not a place", "owners", "objective Atlantis",
                 "both sides start here", "used twice"):
        assert clue in found, clue


def test_everyone_starts_in_supply():                            # 6.6.4
    sc = crusader()
    state = begin_turn(S.new_game(sc, GMAP), GMAP, sc)
    assert [u["name"] for u in S.on_map(state) if not u["traced"]] == []


def test_the_scenario_runs_22_turns_from_18_november():          # 1.9
    sc = crusader()
    assert S.turn_of(sc, "1941-12-30") == sc["turns"] == 22 and len(sc["units"]) == 35


@pytest.mark.parametrize("axis, cw", [("nothing", "attack"), ("attack", "attack"), ("explore", "explore")])
def test_crusader_plays_to_the_end_with_the_invariants_holding(axis, cw):
    kinds = {"nothing": players.DoNothing, "attack": players.AlwaysAttack, "explore": players.Explore}
    state, record = runner.play(crusader(), GMAP, {"axis": kinds[axis](GMAP), "cw": kinds[cw](GMAP)})
    assert state["over"] and len(record) == 22
