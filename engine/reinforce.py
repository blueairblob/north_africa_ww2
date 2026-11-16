"""Arrivals, withdrawals and replacements by date (docs/RULES.md §12)."""
from . import board as B
from . import state as S
from . import units as U
from .gamemap import distance

ARRIVE_RADIUS = 3       # how far from its entry hex a unit may arrive


def entry_ok(state, gmap, u, h, held, there):
    """12.4 test 1: the entry hex itself."""
    places = [name for name, p in gmap.places.items() if p["hex"] == h]
    ours = all(state["places"][name] == u["side"] for name in places)
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
        places = [name for name, p in gmap.places.items() if p["hex"] == h]
        if any(state["places"][name] != u["side"] for name in places) or held.get(h) == S.enemy(u["side"]):
            continue  # an enemy-held entry cannot spawn a unit beside it
        if entry_ok(state, gmap, u, h, held, there):
            return h
        n = near(state, gmap, u, h, held_by_foe, there)
        if n:
            return n
    return None                                                              # 12.4: 4


def reinforcement_phase(state, gmap, scenario):
    turn = state["turn"]
    for change in sorted(scenario.get("redesignations", []), key=lambda e: e["unit"]):
        if S.turn_of(scenario, change["date"]) != turn:
            continue
        u = S.unit(state, change["unit"])
        if u["status"] in ("on_map", "not_arrived") and u["name"] == change["from"]:
            u["name"] = change["name"]
            S.log(state, "redesignated", side=u["side"], unit=u["id"],
                  old_name=change["from"], name=u["name"])
    for w in sorted(scenario.get("withdrawals", []), key=lambda w: w["unit"]):          # 12.2
        u = S.unit(state, w["unit"])
        if S.turn_of(scenario, w["date"]) == turn and u["status"] in ("on_map", "not_arrived"):
            if "if_name" in w and u["name"] != w["if_name"]:
                S.log(state, "not_withdrawn", side=u["side"], unit=u["id"], place=w.get("if_near"))
                continue
            if "if_near" in w and (u["status"] != "on_map"
                    or state["places"][w["if_near"]] != u["side"]
                    or distance(tuple(u["hex"]), gmap.places[w["if_near"]]["hex"]) > w["radius"]):
                S.log(state, "not_withdrawn", side=u["side"], unit=u["id"], place=w["if_near"])
                continue
            if "remain_as" in w:
                remain = w["remain_as"]
                old_name = u["name"]
                steps = U.steps_for(remain["men"], "men")
                u.update(name=remain["name"], size=1, steps=min(u["steps"], steps), max=steps,
                         real=[remain["men"], "men", steps])
                for kind, cap in (("fuel", U.fuel_cap(u)), ("stores", U.stores_cap(u))):
                    excess = max(0, u[kind] - cap)
                    u[kind] -= excess
                    state["sides"][u["side"]]["lost"] += excess
                S.log(state, "remnant", side=u["side"], unit=u["id"], old_name=old_name,
                      name=u["name"], place=w["if_near"])
                continue
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
        spec = specs.get(u["id"])
        if spec is None:
            if u["status"] not in ("destroyed", "withdrawn"):
                raise ValueError(f"Active formation {u['id']} is missing from this chapter.")
            continue
        if u["status"] != "not_arrived" or S.turn_of(scenario, spec["arrives"]) > turn:
            continue
        entry = spec["entry"]
        h = arrival_hex(state, gmap, u, gmap.places[entry]["hex"] if isinstance(entry, str) else tuple(entry))
        if h is None:
            continue
        brought = S.carried(u)
        u["status"] = "on_map"
        B.enter(state, u, h, set())
        if U.is_hq(u):
            u["stationary"] = True
        # B.enter may discard an HQ dump above its travelling allowance.
        # Count all stock that entered the theatre; the discarded part is
        # recorded separately in lost by B.enter.
        state["sides"][u["side"]]["brought"] += brought
        S.log(state, "arrived", side=u["side"], unit=u["id"], hex=list(h))
        came.setdefault((h, U.formation(u)), []).append(u)
    for event in sorted(scenario.get("returns", []), key=lambda e: e["unit"]):
        if S.turn_of(scenario, event["date"]) > turn:
            continue
        u = S.unit(state, event["unit"])
        if u["status"] != "withdrawn":
            continue
        rebuilt = event.get("return_as")
        candidate = dict(u, size=rebuilt["size"]) if rebuilt is not None else u
        h = arrival_hex(state, gmap, candidate, gmap.places[event["entry"]]["hex"])
        if h is None:
            continue
        if rebuilt is not None:
            steps = U.steps_for(rebuilt["men"], "men")
            u.update(name=rebuilt["name"], size=rebuilt["size"], steps=steps, max=steps,
                     real=[rebuilt["men"], "men", steps])
        u["status"], u["fate"] = "on_map", None
        B.enter(state, u, h, set())
        if U.is_hq(u):
            u["stationary"] = True
        S.log(state, "arrived", side=u["side"], unit=u["id"], hex=list(h))
        came.setdefault((h, U.formation(u)), []).append(u)
    for together in came.values():                                           # 12.4: a division comes up as one
        if len(together) > 1:
            for u in together:
                u["group"] = together[0]["id"]
    # A dated withdrawal can empty a position after the Recovery phase.
    occupied = {S.fort_key(h) for h in S.at(state)}
    for key in list(state.get("fort_work", {})):
        if key not in occupied:
            del state["fort_work"][key]
    for key, (level, _) in list(state["forts"].items()):
        if level == 1 and key not in occupied:
            del state["forts"][key]


def timetable(scenario, side):
    """A side's dated events in the order they fall due: what arrives, what is made good and
    what is called away, each with its turn (12.1, 14.2)."""
    specs = {spec["id"]: spec for spec in scenario["units"]}
    rows = []
    for spec in scenario["units"]:
        if "arrives" in spec:
            rows.append(dict({"kind": "arrival", "unit": spec["id"], "date": spec["arrives"], "entry": spec["entry"]},
                             **({"note": spec["arrives_note"]} if "arrives_note" in spec else {})))
    for event in scenario.get("returns", []):
        rows.append({"kind": "arrival", "unit": event["unit"], "date": event["date"],
                     "entry": event["entry"], "note": event.get("note", "Returning formation")})
    for event in scenario.get("redesignations", []):
        rows.append({"kind": "redesignation", "unit": event["unit"], "date": event["date"],
                     "name": event["name"], "note": event.get("note", "Formation redesignated")})
    for kind, key in (("withdrawal", "withdrawals"), ("replacement", "replacements")):
        for e in scenario.get(key, []):
            row = {"kind": kind, "unit": e["unit"], "date": e["date"]}
            if kind == "replacement":
                row["n"], row["what"] = U.counted(e)
                if "via" in e:
                    row["via"] = e["via"]
            if "note" in e:
                row["note"] = e["note"]
            if kind == "withdrawal" and "if_near" in e:
                row["if_near"] = e["if_near"]
            if kind == "withdrawal" and "if_name" in e:
                row["if_name"] = e["if_name"]
            if kind == "withdrawal" and "remain_as" in e:
                row["remain_as"] = e["remain_as"]["name"]
            rows.append(row)
    rows = [dict(r, turn=S.turn_of(scenario, r["date"])) for r in rows
            if specs[r["unit"]]["side"] == side
            and scenario["start"] <= r["date"]
            and S.turn_of(scenario, r["date"]) <= scenario["turns"]]
    return sorted(rows, key=lambda r: (r["turn"], ("redesignation", "withdrawal", "replacement", "arrival").index(r["kind"]), r["unit"]))
