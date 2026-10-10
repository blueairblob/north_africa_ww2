"""The scenario files: every one is checked, and one cut from another is its base up to its last turn."""
import json

import pytest

from engine import checker, players, runner, scenarios
from engine import state as S
from helpers import GMAP, scenario, unit


def test_every_scenario_passes_the_checker():
    assert scenarios.names() == ["crusader", "sidi_rezegh"]
    for name in scenarios.names():
        assert checker.problems(scenarios.load(name), GMAP) == [], name


def test_a_scenario_cut_from_another_is_its_base_up_to_its_last_turn(tmp_path):   # 2.4
    base = scenario([unit(1, "cw", "armour", "Tobruk"), unit(2, "cw", "foot", "Tobruk"),
                     unit(3, "cw", "foot", None, arrives="1941-11-22", entry="Buq Buq"),
                     unit(4, "cw", "foot", None, arrives="1941-11-24", entry="Buq Buq")],
                    id="long", name="Long", ports={"Tobruk": {"fuel": 10, "stores": 20}},
                    withdrawals=[{"date": "1941-11-23", "unit": 1}, {"date": "1941-11-24", "unit": 2}],
                    replacements=[{"date": "1941-11-20", "unit": 2, "steps": 1}, {"date": "1941-11-26", "unit": 4, "steps": 1}])
    (tmp_path / "long.json").write_text(json.dumps(base))
    (tmp_path / "short.json").write_text(json.dumps({"id": "short", "base": "long", "name": "Short", "turns": 3,
                                                     "objectives": [{"place": "Bardia", "end": 5}]}))
    assert scenarios.load("long", tmp_path) == base                 # a whole scenario is read as it is written
    short = scenarios.load("short", tmp_path)
    assert (short["id"], short["name"], short["turns"], short["objectives"]) == ("short", "Short", 3, [{"place": "Bardia", "end": 5}])
    assert "base" not in short and short["ports"] == base["ports"] and short["start"] == base["start"]
    assert [u["id"] for u in short["units"]] == [1, 2, 3]            # turn 3 is 22 and 23 November: the 24th is too late
    assert [e["unit"] for e in short["withdrawals"]] == [1] and [e["unit"] for e in short["replacements"]] == [2]


def test_sidi_rezegh_is_crusaders_first_five_turns():                # 2.4, 1.9
    whole, sc = scenarios.load("crusader"), scenarios.load("sidi_rezegh")
    assert S.turn_of(sc, "1941-11-27") == sc["turns"] == 5 and sc["start"] == whole["start"] == "1941-11-18"
    late = [u["id"] for u in whole["units"] if "arrives" in u]
    assert late == [360, 361, 362, 363, 364]                         # 2nd South African Division, 2 December
    assert sc["units"] == [u for u in whole["units"] if u["id"] not in late]
    assert [(e["date"], e["unit"]) for e in sc["withdrawals"] + sc["replacements"]] == [("1941-11-27", 312), ("1941-11-27", 311)]
    assert all(sc[k] == whole[k] for k in ("owners", "sides", "ports", "tripoli", "forts", "sources"))


def test_sidi_rezegh_has_one_aim_and_its_grades_are_what_it_says():  # 13.6
    sc = scenarios.load("sidi_rezegh")
    swing = {o["place"]: 2 * o["end"] for o in sc["objectives"]}     # a place changing hands by the end: lost by one, won by the other
    t1, t2, t3 = sc["thresholds"]
    assert swing["Sidi Rezegh"] == swing["Belhamed"]
    assert t1 <= swing["Belhamed"] < t2 <= 2 * swing["Belhamed"] < t3 <= 2 * swing["Belhamed"] + swing["El Adem"]
    assert sc["owners"]["cw"].count("Tobruk") == 1 and all(o["place"] in sc["owners"]["axis"] for o in sc["objectives"][:3])
    assert set(sc["aim"]) == set(S.SIDES) and all("Sidi Rezegh and Belhamed" in words for words in sc["aim"].values())
    sc["aim"] = {"cw": "Open the road."}
    assert checker.problems(sc, GMAP) == ["aim: a sentence for each side is needed"]


@pytest.mark.parametrize("axis, cw", [("nothing", "nothing"), ("nothing", "attack"), ("attack", "attack"), ("explore", "explore")])
def test_sidi_rezegh_plays_to_the_end_with_the_invariants_holding(axis, cw):
    sc = scenarios.load("sidi_rezegh")
    state, record = runner.play(sc, GMAP, {"axis": players.SCRIPTED[axis](GMAP), "cw": players.SCRIPTED[cw](GMAP)})
    assert state["over"] and len(record) == 5
    if axis == cw == "nothing":                                      # standing still is level
        assert state["result"] == {"winner": None, "grade": "draw", "margin": 0}
