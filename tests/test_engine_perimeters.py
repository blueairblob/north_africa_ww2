"""An empty mapped fortress perimeter still needs a supplied infantry assault."""
import copy
import json

from engine import checker, movement, orders, state as S, view
from helpers import GMAP, scenario, unit


def setup(stores=100, kind="motorised"):
    sc = scenario([unit(1, "cw", kind, (66, 14), stores=stores),
                   unit(2, "axis", "foot", (59, 15))],
                  forts=[[66, 13, 2, "axis"]], perimeters=[[66, 13, "axis"]], par=-16)
    return sc, S.new_game(sc, GMAP)


def move(sc, state, name):
    ctx = {"orders": {1: {"unit": 1, "order": name, "to": [66, 13]},
                      2: {"unit": 2, "order": "hold"}},
           "entered": set(), "next": {}, "mp": {}, "audit": []}
    movement.movement_phase(state, GMAP, ctx, sc)
    return ctx


def test_empty_perimeter_requires_infantry_attack_and_pays_stores():
    sc, state = setup()
    assert checker.problems(sc, GMAP) == []
    assert view.view(state, GMAP, sc, "cw")["perimeters"]["66,13"] == "axis"
    assert orders.check_one(state, GMAP, "cw", {"unit": 1, "order": "move", "to": [66, 13]}, set()) == "E_NO_PATH"
    ctx = move(sc, state, "move")
    assert ctx["entered"] == set() and state["perimeters"]["66,13"] == "axis"
    assert S.unit(state, 1)["hex"] == [66, 14]

    ctx = move(sc, state, "attack")
    assert ctx["audit"] == []
    assert S.unit(state, 1)["hex"] == [66, 13]
    assert S.unit(state, 1)["stores"] == 50
    assert "66,13" not in state["perimeters"] and "66,13" not in state["forts"]
    assert any(e["event"] == "perimeter breach" and e["hex"] == [66, 13] for e in state["log"])


def test_insufficient_stores_and_armour_cannot_open_empty_perimeter():
    for kind, stores in (("motorised", 49), ("armour", 100)):
        sc, state = setup(stores, kind)
        ctx = move(sc, state, "attack")
        assert ctx["entered"] == set()
        assert S.unit(state, 1)["hex"] == [66, 14]
        assert state["perimeters"]["66,13"] == "axis"
        assert any(e["event"] == "stopped" and "perimeter" in e["why"] for e in state["log"])


def test_perimeter_state_round_trips_and_legacy_save_needs_no_new_field():
    sc, state = setup()
    restored = json.loads(json.dumps(state))
    assert restored["perimeters"] == state["perimeters"]
    move(sc, restored, "attack")
    assert state["perimeters"]["66,13"] == "axis"
    assert "66,13" not in restored["perimeters"]
    legacy = copy.deepcopy(state)
    del legacy["perimeters"]
    assert view.view(legacy, GMAP, sc, "cw")["perimeters"] == {}


def test_checker_rejects_perimeter_without_matching_fort():
    sc, _ = setup()
    sc["forts"] = []
    assert any("perimeter" in problem for problem in checker.problems(sc, GMAP))
