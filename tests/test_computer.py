"""The computer opponent takes the same view and order interface as a person."""
from copy import deepcopy

import pytest

from engine import invariants, players, runner, scenarios
from engine import state as S
from engine import view as V
from engine.computer import ComputerHardBaseline, ComputerHardTactical, ComputerHardUnrestrictedFlank
from engine.turn import begin_turn, finish_turn
from helpers import GMAP
from screen.session import Session


@pytest.mark.parametrize("scenario_name,seed", [("sidi_rezegh", 1941), ("crusader", 65)])
def test_computer_plays_whole_games_with_legal_orders_and_only_its_view(scenario_name, seed):
    scenario = scenarios.load(scenario_name)
    bots = {side: players.ComputerOpponent(GMAP) for side in S.SIDES}
    state = S.new_game(scenario, GMAP, seed)
    ordered = 0
    while not state["over"]:
        state = begin_turn(state, GMAP, scenario)
        assert not invariants.check(state, GMAP)
        shown = {side: V.view(state, GMAP, scenario, side) for side in S.SIDES}
        snapshot = deepcopy(shown)
        submissions = {side: bots[side].orders(shown[side]) for side in S.SIDES}
        assert shown == snapshot                                    # the player cannot change its input
        assert submissions == {side: bots[side].orders(shown[side]) for side in S.SIDES}
        assert all(not V.leaks(shown[side], state) for side in S.SIDES)
        ordered += sum(len(given["orders"]) for given in submissions.values())
        state, replies = finish_turn(state, GMAP, scenario, submissions)
        assert all(reply["ok"] for side in S.SIDES for reply in replies[side])
        assert not invariants.check(state, GMAP)
    assert ordered > 0 and state["turn"] == scenario["turns"] + 1


def test_computer_side_survives_a_save_and_plays_the_same_next_turn():
    scenario = scenarios.load("sidi_rezegh")
    original = Session(scenario, GMAP, humans=["cw"], scripted={"axis": players.ComputerOpponent(GMAP)}, seed=1941)
    saved = original.to_save()
    assert saved["scripted"] == {"axis": "computer"}
    loaded = Session.from_save(saved, GMAP)
    assert type(loaded.scripted["axis"]) is players.ComputerOpponent
    original.done()
    loaded.done()
    assert S.dumps(loaded.state) == S.dumps(original.state)
    assert loaded.record == original.record


def test_commonwealth_computer_opens_the_road_against_a_passive_axis():
    scenario = scenarios.load("sidi_rezegh")
    sides = {"axis": players.DoNothing(GMAP), "cw": players.ComputerOpponent(GMAP)}
    state, record = runner.play(scenario, GMAP, sides, seed=1941)
    assert state["places"]["Sidi Rezegh"] == state["places"]["Belhamed"] == "cw"
    repeated, same_record = runner.play(scenario, GMAP, sides, seed=1941)
    assert S.dumps(repeated) == S.dumps(state) and same_record == record


def test_difficulty_levels_make_distinct_orders_from_the_same_axis_view():
    scenario = scenarios.load("sidi_rezegh")
    state = begin_turn(S.new_game(scenario, GMAP, 1941), GMAP, scenario)
    shown = V.view(state, GMAP, scenario, "axis")
    snapshot = deepcopy(shown)
    orders = [cls(GMAP).orders(shown) for cls in
              (players.ComputerEasy, players.ComputerOpponent, players.ComputerHard)]
    assert shown == snapshot
    assert len({str(given) for given in orders}) == 3
    for given in orders:
        _, replies = finish_turn(state, GMAP, scenario, {"axis": given, "cw": {"orders": [], "air": "recon"}})
        assert all(reply["ok"] for reply in replies["axis"])


@pytest.mark.parametrize("kind,cls", [("computer-easy", players.ComputerEasy),
                                      ("computer", players.ComputerOpponent),
                                      ("computer-hard", players.ComputerHard)])
def test_difficulty_level_survives_a_save_and_replays_the_next_turn(kind, cls):
    scenario = scenarios.load("sidi_rezegh")
    original = Session(scenario, GMAP, humans=[], scripted={"axis": cls(GMAP), "cw": cls(GMAP)}, seed=1941)
    saved = original.to_save()
    assert saved["scripted"] == {"axis": kind, "cw": kind}
    loaded = Session.from_save(saved, GMAP)
    assert all(type(player) is cls for player in loaded.scripted.values())
    original.done()
    loaded.done()
    assert S.dumps(loaded.state) == S.dumps(original.state)


def test_hard_commonwealth_raids_with_armour_and_hq_then_withdraws():
    scenario = scenarios.load("crusader")
    session = Session(scenario, GMAP, humans=[], scripted={"axis": players.ComputerOpponent(GMAP),
                                                         "cw": ComputerHardUnrestrictedFlank(GMAP)}, seed=1941)
    bot = session.scripted["cw"]
    opening = bot.orders(session.views["cw"])
    assert bot.flank is not None
    assert bot.flank["lead"] == 310 and bot.flank["hq"] == 302
    assert bot.flank["goal"] == "Sidi Rezegh"
    assert bot.flank["waypoint"][1] > GMAP.places["Sidi Rezegh"]["hex"][1]
    assert {o["unit"]: o["order"] for o in opening["orders"] if o["unit"] in (302, 310)} == {302: "move", 310: "move"}
    assert opening == bot.orders(session.views["cw"])
    for turn in range(6):
        session.done()
        assert not invariants.check(session.state, GMAP)
        assert all(reply["ok"] for side in S.SIDES for reply in session.replies[side])
        if turn == 2:
            assert session.state["places"]["Sidi Rezegh"] == "cw"
    assert any(order["unit"] == 310 and order["order"] == "attack" and order["to"] == [56, 13]
               for turn in session.record for order in turn["cw"]["orders"])
    assert all(any(order["unit"] == 310 and order["order"] == "move" for order in session.record[i]["cw"]["orders"])
               for i in (3, 4))
    assert next(u for u in session.state["units"] if u["id"] == 302)["hex"] == [64, 23]
    assert next(u for u in session.state["units"] if u["id"] == 310)["hex"] == [64, 22]


def test_hard_prices_moving_hq_dump_before_committing_desert_raid():
    scenario = scenarios.load("crusader")
    session = Session(scenario, GMAP, humans=[], seed=1941)
    full_dump = players.ComputerHard(GMAP)
    assert full_dump.orders(session.views["cw"])["orders"] and full_dump.flank is None
    S.unit(session.state, 302)["dump"] = {"fuel": 400, "stores": 400}
    shown = V.view(session.state, GMAP, scenario, "cw")
    bot = players.ComputerHard(GMAP)
    bot.orders(shown)
    assert bot.flank is not None and bot.flank["hq"] == 302 and bot.flank["goal"] == "Sidi Rezegh"


def test_experimental_tactics_rejects_weak_attack_without_changing_playable_hard():
    session = Session(scenarios.load("sidi_rezegh"), GMAP, humans=[], seed=1941)
    shown = deepcopy(session.views["cw"])
    baseline = ComputerHardBaseline(GMAP).orders(shown)
    candidate = ComputerHardTactical(GMAP).orders(shown)
    assert players.ComputerHard(GMAP).orders(shown) == baseline
    old = next(o for o in baseline["orders"] if o["unit"] == 308)
    new = next(o for o in candidate["orders"] if o["unit"] == 308)
    assert old == {"unit": 308, "order": "attack", "to": [53, 10]}
    assert new == {"unit": 308, "order": "hold"}
    assert shown == session.views["cw"]


def test_active_flank_survives_save_and_replays_same_turn():
    scenario = scenarios.load("crusader")
    original = Session(scenario, GMAP, humans=[], scripted={"axis": players.ComputerOpponent(GMAP),
                                                          "cw": players.ComputerHard(GMAP)}, seed=1941)
    S.unit(original.state, 302)["dump"] = {"fuel": 400, "stores": 400}
    original.state["sides"]["cw"]["lost"] += 5200  # preserve the supply ledger in this constructed state
    original.views["cw"] = V.view(original.state, GMAP, scenario, "cw")
    original.done()
    saved = deepcopy(original.to_save())
    assert saved["scripted_state"]["cw"]["flank"]["phase"] == "approach"
    loaded = Session.from_save(saved, GMAP)
    assert loaded.scripted["cw"].flank == original.scripted["cw"].flank
    for _ in range(5):
        original.done()
        loaded.done()
        assert S.dumps(loaded.state) == S.dumps(original.state)
        assert loaded.record == original.record
