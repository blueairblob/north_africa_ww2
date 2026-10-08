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
    B.regroup(state)                                                         # 20.2.8
    for rep in sorted(scenario.get("replacements", []), key=lambda r: (r["unit"], r["date"])):   # 12.3
        u = S.unit(state, rep["unit"])
        if S.turn_of(scenario, rep["date"]) != turn:
            continue
        via = rep.get("via")
        why = ("gone" if u["status"] != "on_map" else "port" if via and state["places"][via] != u["side"]
               else "cut off" if not u["traced"] else None)
        if why:
            S.log(state, "not_replaced", side=u["side"], unit=u["id"], why=why)
            continue
        got = min(u["max"] - u["steps"], U.steps_for(*U.counted(rep)))
        u["steps"] += got
        S.log(state, "replaced", side=u["side"], unit=u["id"], steps=got)
    specs = {spec["id"]: spec for spec in scenario["units"]}
    came = {}
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
        came.setdefault((h, U.formation(u)), []).append(u)
    for together in came.values():                                           # 12.4: a division comes up as one
        if len(together) > 1:
            for u in together:
                u["group"] = together[0]["id"]


def timetable(scenario, side):
    """A side's dated events in the order they fall due: what arrives, what is made good and
    what is called away, each with its turn (12.1, 14.2)."""
    specs = {spec["id"]: spec for spec in scenario["units"]}
    rows = []
    for spec in scenario["units"]:
        if "arrives" in spec:
            rows.append(dict({"kind": "arrival", "unit": spec["id"], "date": spec["arrives"], "entry": spec["entry"]},
                             **({"note": spec["arrives_note"]} if "arrives_note" in spec else {})))
    for kind, key in (("withdrawal", "withdrawals"), ("replacement", "replacements")):
        for e in scenario.get(key, []):
            row = {"kind": kind, "unit": e["unit"], "date": e["date"]}
            if kind == "replacement":
                row["n"], row["what"] = U.counted(e)
                if "via" in e:
                    row["via"] = e["via"]
            if "note" in e:
                row["note"] = e["note"]
            rows.append(row)
    rows = [dict(r, turn=S.turn_of(scenario, r["date"])) for r in rows if specs[r["unit"]]["side"] == side]
    return sorted(rows, key=lambda r: (r["turn"], ("withdrawal", "replacement", "arrival").index(r["kind"]), r["unit"]))
