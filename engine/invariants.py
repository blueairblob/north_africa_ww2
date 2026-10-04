"""What must hold after every turn (docs/RULES.md §15). check() returns the breaches found."""
from . import state as S
from . import units as U
from .recovery import FORT_MAX


def check(state, gmap):
    bad = []
    there = S.at(state)
    for h, us in sorted(there.items()):
        if len({u["side"] for u in us}) > 1:
            bad.append(f"I-2 both sides in {h}")
        if len({U.formation(u) for u in us}) > U.STACK_FORMATIONS:
            bad.append(f"I-3 too many formations in {h}")
        if not gmap.passable(h):
            bad.append(f"I-4 units in impassable {h}")
    for u in state["units"]:
        name = f"unit {u['id']}"
        if u["status"] == "on_map":
            if not 1 <= u["steps"] <= u["max"]:
                bad.append(f"I-5 {name} has {u['steps']} steps")
        elif u["hex"] is not None:
            bad.append(f"I-5 {name} is {u['status']} but on the map")
        if not 0 <= u["cohesion"] <= 100:
            bad.append(f"I-6 {name} cohesion {u['cohesion']}")
        if not (0 <= u["fuel"] <= U.fuel_cap(u) and 0 <= u["stores"] <= U.stores_cap(u)):
            bad.append(f"I-7 {name} holds fuel {u['fuel']}, stores {u['stores']}")
        if U.is_hq(u) and min(u["dump"].values()) < 0:
            bad.append(f"I-8 {name} dump {u['dump']}")
    stocks = list(state["ports"].values()) + [state["tripoli"]]
    if any(min(s["fuel"], s["stores"]) < 0 for s in stocks) or any(min(p) < 0 for p in state["tripoli"]["pipeline"]):
        bad.append("I-8 a stock is negative")
    for u in state["units"]:
        if u["group"] is not None:                              # I-19
            lead = S.unit(state, u["group"])
            members = S.party(state, u)
            if (u["status"] != "on_map" or lead["hex"] != u["hex"] or U.formation(lead) != U.formation(u)
                    or lead["id"] != min(m["id"] for m in members) or len(members) < 2):
                bad.append(f"I-19 unit {u['id']} is wrongly grouped under {u['group']}")
    for side in S.SIDES:
        t = state["sides"][side]
        if t["brought"] + t["landed"] != S.holdings(state, side) + t["spent"] + t["burnt"] + t["lost"]:
            bad.append(f"I-9 {side} supply not conserved: {t}, holds {S.holdings(state, side)}")
    for name, port in state["ports"].items():
        if not 0 <= port["condition"] <= 100:
            bad.append(f"I-12 {name} condition {port['condition']}")
    for key, (level, owner) in state["forts"].items():
        h = tuple(int(x) for x in key.split(","))
        if not 1 <= level <= FORT_MAX or any(u["side"] != owner for u in there.get(h, [])):
            bad.append(f"I-13 fortification at {key}: level {level}, {owner}")
    if any(owner not in S.SIDES for owner in state["places"].values()) or set(state["places"]) != set(gmap.places):
        bad.append("I-14 a place without one owner")
    return bad
