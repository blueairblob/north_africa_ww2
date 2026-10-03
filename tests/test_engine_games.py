"""Whole games with no screen: the same game twice, replays, and every pair of scripted players
with the invariants of docs/RULES.md §15 asserted after every turn."""
import pytest

from engine import players, runner
from engine import state as S
from helpers import GMAP, small

PLAYERS = {"nothing": players.DoNothing, "attack": players.AlwaysAttack,
           "retreat": players.AlwaysRetreat, "explore": players.Explore}


def play(axis, cw):
    return runner.play(small(), GMAP, {"axis": PLAYERS[axis](GMAP), "cw": PLAYERS[cw](GMAP)})


@pytest.mark.parametrize("axis", PLAYERS)
@pytest.mark.parametrize("cw", PLAYERS)
def test_every_pair_of_players_plays_to_the_end_with_the_invariants_holding(axis, cw):
    state, record = play(axis, cw)                                               # I-2 to I-17 inside
    assert state["over"] and state["result"]["grade"] in ("draw", "tactical", "major", "decisive")
    assert len(record) == small()["turns"]


def test_the_same_game_twice_is_the_same_game():                                 # I-1
    assert S.dumps(play("explore", "attack")[0]) == S.dumps(play("explore", "attack")[0])


def test_a_game_is_its_scenario_and_its_orders():                                # 2.3
    state, record = play("attack", "explore")
    again, _ = runner.play(small(), GMAP, {side: players.Recorded([t[side] for t in record]) for side in S.SIDES})
    assert S.dumps(again) == S.dumps(state)


def test_the_state_survives_being_written_out_and_read_back():                   # 2.1
    import json
    state, _ = play("attack", "attack")
    assert json.loads(S.dumps(state)) == state
