"""Who is where: zones of control, stacking, ownership, and what entering a hex does
(docs/RULES.md §3.4, §4.3, §6.11.4, §9.6)."""
from . import state as S
from . import units as U
from . import victory

PORT_CAPTURE_PCT = 25   # condition of a port just captured (3.4.3)
HQ_CARRY = 300          # tonnes of each kind a moving HQ keeps (6.11.4)


def occupied(state):
    """hex -> the side whose units are in it (4.3.2: never both)."""
    return {tuple(u["hex"]): u["side"] for u in S.on_map(state)}


def zoc(state, gmap, side):
    """The hexes in a side's zone of control (9.6.1)."""
    out = set()
    for u in S.on_map(state, side):
        if U.is_hq(u):
            continue
        for _, n, hexside in gmap.around(tuple(u["hex"])):
            if hexside not in gmap.cliffs:
                out.add(n)
    return out


def room(units_there, comers):
    """Whether a hex holding these units has room for the comers, a unit or a list of units
    of one side: the units of at most STACK_FORMATIONS formations may share a hex (20.1.4)."""
    comers = comers if isinstance(comers, list) else [comers]
    ids = {u["id"] for u in comers}
    there = {U.formation(v) for v in units_there if v["id"] not in ids}
    return len(there | {U.formation(u) for u in comers}) <= U.STACK_FORMATIONS


def regroup(state):
    """Put the groups right after units have moved, fallen back or been lost: a group is the
    related units still in its leader's hex, led by the lowest id; one alone is no group (20.2)."""
    groups = {}
    for u in state["units"]:
        if u["group"] is not None:
            if u["status"] == "on_map":
                groups.setdefault(u["group"], []).append(u)
            else:
                u["group"] = None
    for members in groups.values():
        lead = members[0]                                       # units are kept in id order
        stay = [u for u in members if u["hex"] == lead["hex"]]
        for u in members:
            u["group"] = lead["id"] if u in stay and len(stay) > 1 else None
        rest = [u for u in members if u not in stay]            # those left elsewhere group among themselves
        for h in sorted({tuple(u["hex"]) for u in rest}):
            left = [u for u in rest if tuple(u["hex"]) == h]
            for u in left:
                u["group"] = left[0]["id"] if len(left) > 1 else None


def join(state, u, other):
    """Group u with a related unit in its hex, and so with that unit's group (20.2.2)."""
    members = S.party(state, u) + S.party(state, other)
    lead = min(v["id"] for v in members)
    for v in members:
        v["group"] = lead


def enter(state, u, h, entered):
    """Put a unit in a hex it has moved, retreated or advanced into."""
    u["hex"] = list(h)
    entered.add(u["id"])
    fort = state["forts"].get(S.fort_key(h))
    if fort and fort[1] != u["side"]:
        del state["forts"][S.fort_key(h)]                       # 9.5.6
    if U.is_hq(u):
        u["stationary"] = False                                 # 9.9.1
        for kind in ("fuel", "stores"):                         # 6.11.4
            left = max(0, u["dump"][kind] - HQ_CARRY)
            u["dump"][kind] -= left
            state["sides"][u["side"]]["lost"] += left


def remove(state, u, status):
    """Take a unit off the map: destroyed or withdrawn. What it held is lost (6.11.4, 12.2)."""
    state["sides"][u["side"]]["lost"] += S.carried(u)
    u["fuel"] = u["stores"] = 0
    if U.is_hq(u):
        u["dump"] = {"fuel": 0, "stores": 0}
    u["status"], u["hex"] = status, None
    if status == "destroyed":
        u["steps"] = 0


def destroy(state, u, cause):
    """A unit destroyed in combat, by surrender or by starvation (4.2.1, 10.6.5, 6.10.2)."""
    S.log(state, "destroyed", side=u["side"], unit=u["id"], cause=cause, hex=u["hex"])
    if cause == "surrendered":                                               # both sides see a surrender (14.6)
        S.log(state, "surrender", side="both", sides=list(S.SIDES), unit=u["id"], hex=u["hex"])
    u["fate"] = {"cause": cause, "turn": state["turn"]}                      # 13.4
    victory.unit_lost(state, u)
    remove(state, u, "destroyed")


def settle_owners(state, gmap):
    """A place goes to the side with units in its hex (3.4.2); a captured port is wrecked (3.4.3)."""
    held = occupied(state)
    for name in sorted(gmap.places):
        side = held.get(gmap.places[name]["hex"])
        if side and side != state["places"][name]:
            old = state["places"][name]
            state["places"][name] = side
            if name in state["ports"]:
                port = state["ports"][name]
                state["sides"][old]["lost"] += port["fuel"] + port["stores"]
                port.update(fuel=0, stores=0, condition=PORT_CAPTURE_PCT)
            S.log(state, "captured", place=name, by=side)
