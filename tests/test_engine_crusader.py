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


def test_a_divisions_hq_feeds_its_units_and_builds_no_dump():                    # 20.1.5, 6.7.3
    sc = crusader()
    state = S.new_game(sc, GMAP)
    for _ in range(3):
        state = begin_turn(state, GMAP, sc)
        state["turn"] += 1
    u = {x["id"]: x for x in state["units"]}
    assert u[110]["dump"]["stores"] < 1000 and u[101]["dump"]["stores"] >= 2500    # a division's HQ; the Panzergruppe's


def test_the_checker_finds_what_is_wrong():
    sc = crusader()
    for n, where in ((0, [0, 0]), (1, [83, 43])):                # in the sea; on land nothing can leave
        sc["units"][n].pop("at", None)
        sc["units"][n]["hex"] = where
    sc["units"][2].pop("hex", None)
    sc["units"][2]["at"] = "Atlantis"
    sc["owners"]["axis"].remove("Bardia")
    sc["objectives"].append({"place": "Atlantis", "turn": 1})
    lost = dict(sc["units"][3], id=999, name="Lost division", at="Tobruk")     # an enemy in Tobruk
    lost.pop("hex", None)
    sc["units"].append(lost)
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
    assert S.turn_of(sc, "1941-12-30") == sc["turns"] == 22 and len(sc["units"]) == 91


def test_crusader_shows_each_division_as_its_units_grouped_under_its_hq():       # 20.1, 20.2.1, 20.4
    sc = crusader()
    state = S.new_game(sc, GMAP)
    u = {x["id"]: x for x in state["units"]}
    assert [u[i]["group"] for i in (110, 111, 112, 113, 114)] == [110] * 5      # 15. Panzer-Division, in one hex
    assert u[142]["parent"] == 140 and u[142]["group"] is None                  # Savona's regiment at Capuzzo, apart
    assert u[111]["real"] == [133, "tanks", 13] and u[111]["steps"] == 13 and u[311]["steps"] == 17
    assert all(x["real"] and x.get("src") is None for x in state["units"] if x["type"] != "hq")
    assert all(spec["src"] in sc["sources"] for spec in sc["units"] if spec["type"] != "hq")
    tanks = {side: sum(x["real"][0] for x in state["units"] if x["side"] == side and x["real"] and x["real"][1] == "tanks")
             for side in S.SIDES}
    assert tanks == {"axis": 395, "cw": 680}


@pytest.mark.parametrize("axis, cw", [("nothing", "attack"), ("attack", "attack"), ("explore", "explore")])
def test_crusader_plays_to_the_end_with_the_invariants_holding(axis, cw):
    kinds = {"nothing": players.DoNothing, "attack": players.AlwaysAttack, "explore": players.Explore}
    state, record = runner.play(crusader(), GMAP, {"axis": kinds[axis](GMAP), "cw": kinds[cw](GMAP)})
    assert state["over"] and len(record) == 22
