"""Preparation is an optional, dated choice before an assault on intact works."""
import json

from engine import checker, combat, computer, movement, orders, perimeter as P, state as S, turn, victory, view
from helpers import GMAP, scenario, unit
from screen import layout, theme
from screen.session import Session


def position():
    sc = scenario([unit(1, "cw", "motorised", (57, 12), stores=65),
                   unit(2, "cw", "guns", (58, 12), stores=80),
                   unit(3, "axis", "foot", (59, 15))],
                  forts=[[56, 12, 2, "axis"]], perimeters=[[56, 12, "axis"]], turn_days=1)
    sc["par"] = victory.par(sc)
    return sc, S.new_game(sc, GMAP)


def test_tobruk_proxy_is_south_of_road_and_outside_the_town():
    sc, state = position()
    assert checker.problems(sc, GMAP) == []
    assert GMAP.places["Tobruk"]["hex"] == (55, 10)
    assert (56, 12) not in GMAP.on_route
    assert (56, 11) in GMAP.on_route
    assert state["perimeters"] == {"56,12": "axis"}


def test_inf_and_guns_prepare_then_reduce_crossing_cost():
    sc, state = position()
    engineers = {"unit": 1, "order": "prepare", "to": [56, 12]}
    barrage = {"unit": 2, "order": "prepare", "to": [56, 12]}
    assert orders.check_one(state, GMAP, "cw", engineers, set()) is None
    assert orders.check_one(state, GMAP, "cw", barrage, set()) is None
    ctx = {"orders": {1: engineers, 2: barrage, 3: {"unit": 3, "order": "hold"}}}
    P.prepare(state, ctx, sc)
    shown = view.view(state, GMAP, sc, "cw")["perimeter_prep"]
    assert shown["56,12"] == {"engineers": True, "artillery": True}
    assert view.view(state, GMAP, sc, "axis")["perimeter_prep"] == {}
    assert S.unit(state, 1)["stores"] == 40 and S.unit(state, 2)["stores"] == 55
    assert orders.check_one(state, GMAP, "cw", engineers, set()) == "E_PREPARE"
    state = json.loads(S.dumps(state))
    state["turn"] = 2
    P.expire(state, sc)
    assert P.ready(state, (56, 12), "cw", "engineers")
    moving = {"orders": {1: {"unit": 1, "order": "attack", "to": [56, 12]},
                         2: {"unit": 2, "order": "hold"}, 3: {"unit": 3, "order": "hold"}},
              "entered": set(), "next": {}, "mp": {}, "audit": []}
    movement.movement_phase(state, GMAP, moving, sc)
    assert S.unit(state, 1)["hex"] == [56, 12] and S.unit(state, 1)["stores"] == 15
    assert state["perimeters"] == {} and state["perimeter_prep"] == {}


def test_preparation_expires_if_the_assault_is_delayed():
    sc, state = position()
    ctx = {"orders": {1: {"unit": 1, "order": "prepare", "to": [56, 12]},
                      2: {"unit": 2, "order": "hold"}, 3: {"unit": 3, "order": "hold"}}}
    P.prepare(state, ctx, sc)
    state["turn"] = 4
    P.expire(state, sc)
    assert state["perimeter_prep"] == {}
    assert state["perimeters"] == {"56,12": "axis"}


def test_a_battle_interrupts_preparation_work():
    sc, state = position()
    ctx = {"orders": {1: {"unit": 1, "order": "prepare", "to": [56, 12]},
                      2: {"unit": 2, "order": "prepare", "to": [56, 12]},
                      3: {"unit": 3, "order": "hold"}}, "in_battle": {1}}
    P.prepare(state, ctx, sc)
    assert state["perimeter_prep"]["56,12"] == {"side": "cw", "artillery": "1941-11-20"}
    assert S.unit(state, 1)["stores"] == 65


def test_registered_artillery_reduces_only_the_target_fort_bonus():
    sc, state = position()
    S.unit(state, 3)["hex"] = [56, 12]
    battle = {"attackers": [S.unit(state, 1)], "defenders": [S.unit(state, 3)], "hex": (56, 12), "short": set()}
    ctx = {"command": {"cw": [], "axis": []}, "support": {"cw": 0, "axis": 0},
           "orders": {1: {"order": "attack"}, 3: {"order": "hold"}}}
    combat.values(state, GMAP, ctx, battle)
    unprepared = battle["def"]
    state["perimeter_prep"]["56,12"] = {"side": "cw", "artillery": "1941-11-20"}
    combat.values(state, GMAP, ctx, battle)
    assert battle["def"] < unprepared


def test_computer_prepares_a_mapped_breach_when_forces_are_in_range():
    sc, state = position()
    sc["mission"] = {"cw": {"prepare_breach": True, "orders": [
        {"verb": "breach", "hex": [56, 12], "label": "southern crossing"}]}}
    shown = view.view(state, GMAP, sc, "cw")
    planned = computer.ComputerHard(GMAP).orders(shown)
    chosen = {o["unit"]: o for o in planned["orders"]}
    assert chosen[1] == {"unit": 1, "order": "prepare", "to": [56, 12]}
    assert chosen[2] == {"unit": 2, "order": "prepare", "to": [56, 12]}


def test_human_console_offers_a_one_turn_prepare_order():
    sc, _ = position()
    session = Session(sc, GMAP, humans=["cw"])
    assert session.can(1, "prepare") == (True, "")
    assert "prepare" in session.offers(1)
    assert layout.areas(theme.WINDOW)["console"].contains(layout.buttons(theme.WINDOW)["prepare"])
    assert session.give({"unit": 1, "order": "prepare", "to": [56, 12]})["ok"]


def test_preparation_passes_the_full_turn_phase_audit():
    sc, state = position()
    audit = []
    state = turn.begin_turn(state, GMAP, sc, audit)
    state, replies = turn.finish_turn(state, GMAP, sc, {
        "cw": {"orders": [{"unit": 1, "order": "prepare", "to": [56, 12]},
                          {"unit": 2, "order": "prepare", "to": [56, 12]}], "air": "support"},
        "axis": {"orders": [{"unit": 3, "order": "hold"}], "air": "support"},
    }, audit)
    assert audit == [] and all(reply["ok"] for reply in replies["cw"])
    assert state["perimeter_prep"]["56,12"]["engineers"]
    assert state["perimeter_prep"]["56,12"]["artillery"]


def test_preparation_can_turn_a_defended_crossing_into_a_breach():
    troops = [unit(i, "cw", "motorised", (57, 12), stores=275) for i in (1, 2, 3)]
    troops += [unit(10, "cw", "guns", (58, 12), stores=275),
               unit(20, "axis", "foot", (56, 12), steps=8, stores=275)]
    sc = scenario(troops, forts=[[56, 12, 2, "axis"]], perimeters=[[56, 12, "axis"]],
                  turn_days=1, grouped=False)
    sc["par"] = victory.par(sc)
    outcomes = []
    for prepared in (False, True):
        state = S.new_game(sc, GMAP)
        if prepared:
            ctx = {"orders": {u["id"]: ({"order": "prepare", "to": [56, 12]}
                                     if u["id"] in (1, 10) else {"order": "hold"})
                              for u in state["units"]}}
            P.prepare(state, ctx, sc)
        state["turn"] = 2
        submissions = {"cw": {"orders": [{"unit": i, "order": "attack", "to": [56, 12]}
                                         for i in (1, 2, 3)], "air": "support"},
                       "axis": {"orders": [{"unit": 20, "order": "hold"}], "air": "support"}}
        end, _ = turn.finish_turn(state, GMAP, sc, submissions)
        battle = next(e for e in end["log"] if e["event"] == "battle")
        outcomes.append((battle["def"], battle["retreated"], end["perimeters"]))
    assert outcomes[0][0] > outcomes[1][0]
    assert outcomes[0][1:] == (False, {"56,12": "axis"})
    assert outcomes[1][1:] == (True, {})
