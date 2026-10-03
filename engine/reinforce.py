"""Arrivals, withdrawals and replacements by date (docs/RULES.md §12)."""
from . import board as B
from . import state as S
from . import units as U
from .gamemap import distance

ARRIVE_RADIUS = 3       # how far from its entry hex a unit may arrive


def entry_ok(state, gmap, u, h, held, there):
    """12.4 test 1: the entry hex itself."""
    places = [name for name, p in gmap.places.items() if p["hex"] == h]
    ours = all(state["places"][name] == u["side"] for name in places) or h == gmap.base[u["side"]]
    return ours and held.get(h) != S.enemy(u["side"]) and B.room(there.get(h, []), u)


def near(state, gmap, u, h, held, there):
    """12.4 test 2: the nearest other hex within ARRIVE_RADIUS that will do."""
    foe_zoc = B.zoc(state, gmap, S.enemy(u["side"]))
    best = None
    for c in range(h[0] - ARRIVE_RADIUS, h[0] + ARRIVE_RADIUS + 1):
        for r in range(h[1] - ARRIVE_RADIUS, h[1] + ARRIVE_RADIUS + 1):
            n = (c, r)
            if (0 < distance(h, n) <= ARRIVE_RADIUS and gmap.passable(n) and n not in held
                    and n not in foe_zoc and B.room(there.get(n, []), u)):
                best = min(best or (99, n), (distance(h, n), n))
    return best[1] if best else None


def arrival_hex(state, gmap, u, entry):
    held, there = B.occupied(state), S.at(state)
    held_by_foe = {h: s for h, s in held.items() if s != u["side"]}
    for h in (entry, gmap.base[u["side"]]):                                  # 12.4: 1, 2, then 3
        if entry_ok(state, gmap, u, h, held, there):
            return h
        n = near(state, gmap, u, h, held_by_foe, there)
        if n:
            return n
    return None                                                              # 12.4: 4


def reinforcement_phase(state, gmap, scenario):
    turn = state["turn"]
    for w in sorted(scenario.get("withdrawals", []), key=lambda w: w["unit"]):          # 12.2
        u = S.unit(state, w["unit"])
        if S.turn_of(scenario, w["date"]) == turn and u["status"] in ("on_map", "not_arrived"):
            S.log(state, "withdrawn", side=u["side"], unit=u["id"])
            if u["status"] == "on_map":
                B.remove(state, u, "withdrawn")
            u["status"], u["fate"] = "withdrawn", {"cause": "withdrawn", "turn": turn}
    for rep in sorted(scenario.get("replacements", []), key=lambda r: r["unit"]):       # 12.3
        u = S.unit(state, rep["unit"])
        if S.turn_of(scenario, rep["date"]) == turn and u["status"] == "on_map" and u["traced"]:
            u["steps"] = min(u["max"], u["steps"] + rep["steps"])
    specs = {spec["id"]: spec for spec in scenario["units"]}
    for u in state["units"]:                                                 # 12.4
        spec = specs[u["id"]]
        if u["status"] != "not_arrived" or S.turn_of(scenario, spec["arrives"]) > turn:
            continue
        entry = spec["entry"]
        h = arrival_hex(state, gmap, u, gmap.places[entry]["hex"] if isinstance(entry, str) else tuple(entry))
        if h is None:
            continue
        u["status"] = "on_map"
        B.enter(state, u, h, set())
        if U.is_hq(u):
            u["stationary"] = True
        state["sides"][u["side"]]["brought"] += S.carried(u)
        S.log(state, "arrived", side=u["side"], unit=u["id"], hex=list(h))
