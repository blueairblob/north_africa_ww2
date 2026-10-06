"""A turn: eight phases in order (docs/RULES.md §5). Each phase is one function in its own module."""
import copy

from . import board as B
from . import state as S
from .air import air_phase
from .combat import combat_phase
from .movement import movement_phase
from .orders import check
from .recovery import recovery_phase
from .reinforce import reinforcement_phase
from .supply import supply_phase
from .victory import victory_phase

LOG = {"log"} | {f"sides.{t}" for t in S.TOTALS}     # any phase may log and count supply (5.1)
GONE = {"unit.status", "unit.hex", "unit.steps", "unit.fuel", "unit.stores", "unit.dump", "unit.fate", "unit.group",
        "sides.vp", "sides.kills"}
CAPTURE = {"places", "ports", "forts"}
MAY_CHANGE = {                                       # what each phase may change (5.1)
    "supply": {"ports", "tripoli", "unit.dump", "unit.fuel", "unit.stores", "unit.out_of_stores", "unit.group",
               "unit.traced", "unit.cohesion", "unit.ceiling"} | GONE,
    "orders": {"unit.group"},
    "air": {"sides.air", "sides.interdiction", "sides.recon"},
    "movement": {"unit.hex", "unit.fuel", "unit.cohesion", "unit.stationary", "unit.dump", "unit.group"} | CAPTURE,
    "combat": {"unit.cohesion", "unit.stationary"} | GONE | CAPTURE,
    "recovery": {"unit.steps", "unit.cohesion", "unit.stores", "forts"},
    "reinforcement": {"unit.stationary", "forts"} | GONE - {"sides.vp", "sides.kills"},
    "victory": {"sides.vp", "turn", "over", "result"},
}


def group_orders(state, orders):
    """Splits and joins take effect, and every member of a group has its leader's order (20.2)."""
    for uid in sorted(orders):                                   # 20.2.4: split off
        if orders[uid].get("alone"):
            S.unit(state, uid)["group"] = None
    B.regroup(state)
    for uid in sorted(orders):                                   # 20.2.2: joined at once, in the same hex
        order, u = orders[uid], S.unit(state, uid)
        if order["order"] == "join":
            other = S.unit(state, order["with"])
            if other["hex"] == u["hex"]:
                theirs = orders[other["group"] or other["id"]]   # the group carries on with the order of the unit joined
                B.join(state, u, other)
                orders[u["group"]] = dict({k: v for k, v in theirs.items() if k != "alone"}, unit=u["group"])
    for u in S.on_map(state):                                    # 20.2.5
        lead = u["group"]
        if lead is not None and lead != u["id"]:
            orders[u["id"]] = dict({k: v for k, v in orders[lead].items() if k != "alone"}, unit=u["id"])


def changed(before, after):
    """The names of the parts of the state that differ (invariant I-18)."""
    out = {k for k in after if k not in ("units", "sides") and before[k] != after[k]}
    for a, b in zip(before["units"], after["units"]):
        out |= {f"unit.{k}" for k in b if a[k] != b[k]}
    for side in S.SIDES:
        out |= {f"sides.{k}" for k, v in after["sides"][side].items() if before["sides"][side][k] != v}
    return out


def run(name, phase, state, audit):
    """Run one phase; with an audit list, note anything it changed that it may not."""
    before = copy.deepcopy(state) if audit is not None else None
    result = phase()
    if audit is not None:
        extra = changed(before, state) - MAY_CHANGE[name] - LOG
        if extra:
            audit.append(f"I-18 the {name} phase changed {sorted(extra)}")
    return result


def begin_turn(state, gmap, scenario, audit=None):
    """Phase 1, Supply. The state it returns is what the players are shown (5.2)."""
    state = copy.deepcopy(state)
    notes = [] if audit is None else audit
    run("supply", lambda: supply_phase(state, gmap, scenario, notes), state, audit)
    return state


def finish_turn(state, gmap, scenario, submissions, audit=None):
    """Phases 2 to 8, from both sides' orders. Returns the new state and each side's replies."""
    state = copy.deepcopy(state)
    state["log"] = []
    ctx = {"orders": {}, "air": {}, "support": {}, "entered": set(), "next": {}, "mp": {},
           "retreated": set(), "in_battle": set(), "battles": [], "audit": [] if audit is None else audit}
    replies = {}

    def take_orders():
        for side in S.SIDES:
            orders, ctx["air"][side], replies[side] = check(state, gmap, side, submissions.get(side))
            ctx["orders"].update(orders)
        group_orders(state, ctx["orders"])

    run("orders", take_orders, state, audit)                                     # phase 2
    run("air", lambda: air_phase(state, scenario, ctx), state, audit)            # phase 3
    run("movement", lambda: movement_phase(state, gmap, ctx), state, audit)      # phase 4
    run("combat", lambda: combat_phase(state, gmap, ctx), state, audit)          # phase 5
    run("recovery", lambda: recovery_phase(state, ctx), state, audit)            # phase 6
    run("reinforcement", lambda: reinforcement_phase(state, gmap, scenario), state, audit)   # phase 7
    run("victory", lambda: victory_phase(state, scenario), state, audit)         # phase 8
    return state, replies
