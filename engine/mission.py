"""Executable High Command orders. A route is an explicit, inspectable map path."""
from . import state as S
from . import paths
from .gamemap import ROAD

VERBS = {"hold", "clear", "deny", "reach", "surround", "stage", "breach", "preserve"}
GRADES = {"tactical", "major", "decisive"}


def breach_key(order):
    """Stable campaign progress key independent of the displayed description."""
    return f"breach:{order['hex'][0]},{order['hex'][1]}"


def problems(scenario, gmap):
    mission = scenario.get("mission", {})
    if not isinstance(mission, dict) or set(mission) - {"routes", *S.SIDES}:
        return ["mission: expected routes and side orders"]
    bad = []
    routes = mission.get("routes", {})
    if not isinstance(routes, dict):
        return ["mission routes: expected named routes"]
    for name, route in routes.items():
        if not isinstance(name, str) or not name or not isinstance(route, dict):
            bad.append("mission route: expected a name and map path")
            continue
        if set(route) != {"terrain", "from", "to", "via", "hexes"} or route.get("terrain") not in ("road", "rail", "corridor"):
            bad.append(f"mission route {name}: expected terrain, from, to, via and hexes")
            continue
        names = [route["from"], *route["via"], route["to"]] if isinstance(route["via"], list) else []
        hexes = route["hexes"]
        if (not names or any(n not in gmap.places for n in names) or not isinstance(hexes, list)
                or len(hexes) < 2 or any(not isinstance(h, list) or len(h) != 2 or
                not all(type(v) is int for v in h) or not gmap.passable(tuple(h)) for h in hexes)):
            bad.append(f"mission route {name}: named places and passable hexes are required")
            continue
        path = [tuple(h) for h in hexes]
        positions = [gmap.places[n]["hex"] for n in names]
        if path[0] != positions[0] or path[-1] != positions[-1] or [h for h in path if h in positions] != positions:
            bad.append(f"mission route {name}: path must pass through its named places in order")
        if any(b not in [n for _, n, _ in gmap.around(a)] for a, b in zip(path, path[1:])):
            bad.append(f"mission route {name}: every hex must touch the next")
        if route["terrain"] == "road" and any(gmap.links.get((a, b)) != ROAD for a, b in zip(path, path[1:])):
            bad.append(f"mission route {name}: path is not all road")
        if route["terrain"] == "rail" and any((a, b) not in set(zip(gmap.rail, gmap.rail[1:])) |
                                           set(zip(gmap.rail[1:], gmap.rail)) for a, b in zip(path, path[1:])):
            bad.append(f"mission route {name}: path is not all rail")
        if route["terrain"] == "corridor" and any(
                gmap.side_between(a, b) is None or
                paths.step_cost(gmap, a, b, gmap.side_between(a, b), paths.VEHICLE) is None
                for a, b in zip(path, path[1:])):
            bad.append(f"mission route {name}: corridor cannot be traversed by vehicles")
    for side in S.SIDES:
        spec = mission.get(side)
        if spec is None:
            continue
        if (not isinstance(spec, dict) or set(spec) - {"orders", "success_grade", "failure_grade", "avoid_attack", "avoid_attack_hexes", "commendations"}
                or not isinstance(spec.get("orders"), list) or not spec["orders"]
                or any(spec.get(k) not in GRADES for k in ("success_grade", "failure_grade") if k in spec)):
            bad.append(f"mission {side}: expected orders and an optional success or failure grade")
            continue
        avoid = spec.get("avoid_attack", [])
        if not isinstance(avoid, list) or any(name not in gmap.places for name in avoid):
            bad.append(f"mission {side}: avoid_attack needs named places")
        avoid_hexes = spec.get("avoid_attack_hexes", [])
        if (not isinstance(avoid_hexes, list) or any(
                not isinstance(h, list) or len(h) != 2 or any(type(n) is not int for n in h)
                or not gmap.passable(tuple(h)) for h in avoid_hexes)):
            bad.append(f"mission {side}: avoid_attack_hexes needs passable hexes")
        awards = spec.get("commendations", [])
        if not isinstance(awards, list):
            bad.append(f"mission {side}: commendations must be a list")
            awards = []
        titles = set()
        for award in awards:
            if (not isinstance(award, dict) or set(award) != {"title", "order"}
                    or not isinstance(award.get("title"), str) or not award["title"].strip()
                    or award["title"] in titles or not isinstance(award.get("order"), dict)):
                bad.append(f"mission {side}: commendation needs a unique title and order")
                continue
            titles.add(award["title"])
        for order in [*spec["orders"], *(a["order"] for a in awards if isinstance(a, dict) and isinstance(a.get("order"), dict))]:
            if not isinstance(order, dict) or order.get("verb") not in VERBS:
                bad.append(f"mission {side}: unknown order")
                continue
            verb = order["verb"]
            if verb in ("clear", "deny"):
                if set(order) != {"verb", "route"} or order["route"] not in routes:
                    bad.append(f"mission {side}: {verb} needs a named route")
            elif verb in ("stage", "breach"):
                h = order.get("hex")
                if (set(order) != {"verb", "hex", "label"} or not isinstance(h, list) or len(h) != 2
                        or any(type(v) is not int for v in h) or not gmap.passable(tuple(h))
                        or not isinstance(order.get("label"), str) or not order["label"].strip()):
                    bad.append(f"mission {side}: {verb} needs a passable hex and label")
            elif verb == "preserve":
                units = order.get("units")
                specs = {u["id"]: u for u in scenario["units"]}
                if (set(order) != {"verb", "units", "minimum_pct", "label"}
                        or not isinstance(units, list) or not units
                        or any(type(uid) is not int or uid not in specs or specs[uid]["side"] != side for uid in units)
                        or len(set(units)) != len(units)
                        or type(order.get("minimum_pct")) is not int or not 1 <= order["minimum_pct"] <= 100
                        or not isinstance(order.get("label"), str) or not order["label"].strip()):
                    bad.append(f"mission {side}: preserve needs own units, a percentage and label")
            elif set(order) != {"verb", "place"} or order["place"] not in gmap.places:
                bad.append(f"mission {side}: {verb} needs a named place")
    return bad


def describe(order, mission):
    verb = order["verb"]
    if verb in ("stage", "breach"):
        return ("Stage at " if verb == "stage" else "Breach ") + order["label"]
    if verb == "preserve":
        return f"Preserve at least {order['minimum_pct']}% of {order['label']}"
    target = order["route"] if verb in ("clear", "deny") else order["place"]
    return {"hold": "Occupy", "clear": "Clear", "deny": "Block", "reach": "Reach", "surround": "Surround"}[verb] + " " + target


def preserve_progress(state, side, order):
    """Surviving and original steps of a named force, capped per formation."""
    baseline = state.get("mission_baseline", {}).get(side, {})
    original = [baseline.get(str(uid), 0) for uid in order["units"]]
    surviving = sum(min(before, u["steps"]) for uid, before in zip(order["units"], original)
                    if (u := S.unit(state, uid)) is not None and u["status"] != "destroyed")
    return surviving, sum(original)


def met(state, gmap, side, order, mission):
    """Assess an order at the end of a turn, from actual on-map units."""
    occupied = {tuple(u["hex"]): u["side"] for u in S.on_map(state)}
    verb = order["verb"]
    if verb == "preserve":
        baseline = state.get("mission_baseline", {}).get(side, {})
        if not all(baseline.get(str(uid), 0) for uid in order["units"]):
            return False
        surviving, original = preserve_progress(state, side, order)
        return surviving * 100 >= original * order["minimum_pct"]
    if verb in ("stage", "breach"):
        if verb == "breach" and breach_key(order) in state.get("mission_reached", {}).get(side, []):
            return True
        return any(u["side"] == side and u["type"] != "hq" and u["status"] == "on_map"
                   and u["hex"] == order["hex"] for u in state["units"])
    if verb in ("clear", "deny"):
        path = [tuple(h) for h in mission["routes"][order["route"]]["hexes"]]
        return (all(occupied.get(h) != S.enemy(side) for h in path) if verb == "clear"
                else any(occupied.get(h) == side for h in path))
    place = order["place"]
    h = gmap.places[place]["hex"]
    if verb == "hold":
        return state["places"][place] == side and occupied.get(h) == side
    if verb == "reach":
        return place in state.get("mission_reached", {}).get(side, []) or occupied.get(h) == side
    # Surround means a held enemy place with every passable neighbouring hex occupied.
    return occupied.get(h) == S.enemy(side) and all(occupied.get(n) == side for _, n, _ in gmap.around(h))


def assessment(state, scenario, gmap):
    """Per-side order checks and whether the side completed every required order."""
    mission = scenario.get("mission", {})
    out = {}
    for side in S.SIDES:
        spec = mission.get(side)
        if spec:
            checks = []
            for order in spec["orders"]:
                description = describe(order, mission)
                if order["verb"] == "preserve":
                    surviving, original = preserve_progress(state, side, order)
                    description += f" ({surviving * 100 // original if original else 0}% of entry strength remains)"
                checks.append({"order": description, "met": met(state, gmap, side, order, mission)})
            awards = [{"title": award["title"], "order": describe(award["order"], mission),
                       "met": met(state, gmap, side, award["order"], mission)}
                      for award in spec.get("commendations", [])]
            out[side] = {"complete": all(c["met"] for c in checks), "checks": checks,
                         "commendations": awards}
    return out


def record_reached(state, scenario, gmap):
    """A reach order counts once a unit has ended any turn at the named place."""
    mission = scenario.get("mission", {})
    for side in S.SIDES:
        spec = mission.get(side, {})
        for order in [*spec.get("orders", []), *(a["order"] for a in spec.get("commendations", []))]:
            if order["verb"] == "reach" and any(tuple(u["hex"]) == gmap.places[order["place"]]["hex"]
                                                 for u in S.on_map(state, side)):
                reached = state.setdefault("mission_reached", {}).setdefault(side, [])
                if order["place"] not in reached:
                    reached.append(order["place"])
            elif order["verb"] == "breach" and any(u["type"] != "hq" and u["hex"] == order["hex"]
                                                     for u in S.on_map(state, side)):
                reached = state.setdefault("mission_reached", {}).setdefault(side, [])
                key = breach_key(order)
                if key not in reached:
                    reached.append(key)
