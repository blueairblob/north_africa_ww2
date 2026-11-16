"""Plays any two players against each other with no screen (DESIGN.md §13)."""
from copy import deepcopy

from . import invariants
from . import state as S
from .turn import begin_turn, finish_turn
from .view import leaks, view


def play(scenario, gmap, players, turns=None, check=True, seed=0, initial_state=None):
    """Play to the end, or for so many turns. Returns the final state and the record:
    one entry per turn holding each side's submission. The scenario, the seed and the record
    are the game."""
    if initial_state is None:
        state = S.new_game(scenario, gmap, seed)
    else:
        if (initial_state.get("scenario") != scenario["id"] or initial_state.get("over")
                or (seed and initial_state.get("seed") != seed)):
            raise ValueError("The supplied state does not begin this scenario and seed.")
        bad = invariants.check(initial_state, gmap)
        if bad:
            raise ValueError("The supplied state fails the engine invariants: " + "; ".join(bad))
        state = deepcopy(initial_state)
    record = []
    while not state["over"] and (turns is None or state["turn"] <= turns):
        audit = [] if check else None
        state = shown = begin_turn(state, gmap, scenario, audit)
        if check:                                         # the Supply phase can lose units too: check after it as well
            bad = invariants.check(state, gmap)
            assert not bad, f"turn {state['turn']}, after the Supply phase: {bad}"
        views = {side: view(state, gmap, scenario, side) for side in S.SIDES}
        submissions = {side: players[side].orders(views[side]) for side in S.SIDES}
        record.append(submissions)
        turn = state["turn"]
        state, _ = finish_turn(state, gmap, scenario, submissions, audit)
        if check:
            bad = audit + invariants.check(state, gmap) + [f"I-17 {side} view: {x}" for side in S.SIDES
                                                   for x in leaks(views[side], shown)]
            assert not bad, f"turn {turn}: {bad}"
    return state, record
