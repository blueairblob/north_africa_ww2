"""A turn: eight phases in order (docs/RULES.md §5). Each phase is one function in its own module."""
import copy

from . import state as S
from .air import air_phase
from .combat import combat_phase
from .movement import movement_phase
from .orders import check
from .recovery import recovery_phase
from .reinforce import reinforcement_phase
from .supply import supply_phase
from .victory import victory_phase


def begin_turn(state, gmap, scenario):
    """Phase 1, Supply. The state it returns is what the players are shown (5.2)."""
    state = copy.deepcopy(state)
    supply_phase(state, gmap, scenario)
    return state


def finish_turn(state, gmap, scenario, submissions):
    """Phases 2 to 8, from both sides' orders. Returns the new state and each side's replies."""
    state = copy.deepcopy(state)
    state["log"] = []
    ctx = {"orders": {}, "air": {}, "support": {}, "entered": set(), "next": {}, "mp": {},
           "retreated": set(), "in_battle": set(), "battles": []}
    replies = {}
    for side in S.SIDES:                                         # phase 2
        orders, ctx["air"][side], replies[side] = check(state, gmap, side, submissions.get(side))
        ctx["orders"].update(orders)
    air_phase(state, scenario, ctx)                              # phase 3
    movement_phase(state, gmap, ctx)                             # phase 4
    combat_phase(state, gmap, ctx)                               # phase 5
    recovery_phase(state, ctx)                                   # phase 6
    reinforcement_phase(state, gmap, scenario)                   # phase 7
    victory_phase(state, scenario)                               # phase 8
    return state, replies
