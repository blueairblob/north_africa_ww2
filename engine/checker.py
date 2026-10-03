"""The scenario checker: every place, unit and objective is on the map, on ground it can stand
on and where its name says (docs/ENGINEERING_NOTES.md §5). problems() returns what is wrong."""
from datetime import date

from . import state as S
from . import units as U
from .paths import FOOT, least_path
from .recovery import FORT_MAX
from .supply import PORT_CAP
from .victory import par

COUNTERS = 30           # no more than about this many a side (DESIGN.md §14.1)


def problems(scenario, gmap):
    bad = []

    def day(d, what):
        try:
            return date.fromisoformat(d)
        except (TypeError, ValueError):
            bad.append(f"{what}: {d!r} is not a date")

    day(scenario.get("start"), "start")
    owned = [n for side in S.SIDES for n in scenario["owners"][side]]
    if sorted(owned) != sorted(gmap.places):
        odd = set(owned) ^ set(gmap.places) | {n for n in owned if owned.count(n) > 1}
        bad.append(f"owners: every place must have one owner; wrong: {sorted(odd)}")
    for name in scenario.get("ports", {}):
        if name not in PORT_CAP:
            bad.append(f"ports: {name} is not a port")
    for obj in scenario["objectives"]:
        if obj["place"] not in gmap.places:
            bad.append(f"objective {obj['place']} is not a place")
    if sorted(scenario["thresholds"]) != scenario["thresholds"] or len(scenario["thresholds"]) != 3:
        bad.append("thresholds: three rising numbers are needed")
    if not bad and scenario.get("par") != par(scenario):
        bad.append(f"par: must be {par(scenario)}, the Axis lead if nobody moves (RULES 13.6); it is {scenario.get('par')}")

    for side in S.SIDES:
        for name, schedule in scenario["sides"][side].items():
            days = [day(d, f"{side} {name}") for d, _ in schedule]
            if None not in days and (days != sorted(days) or not days or days[0] > day(scenario["start"], "start")):
                bad.append(f"{side} {name}: dates must rise and begin by the start")
        if "lift" not in scenario["sides"][side]:
            bad.append(f"{side}: no lift")
    for _, name in scenario["sides"]["cw"].get("railhead", []):
        if name not in gmap.places or gmap.places[name]["hex"] not in gmap.rail:
            bad.append(f"railhead {name} is not a place on the railway")

    ids, names, where = set(), set(), {}
    for spec in scenario["units"]:
        tag = f"unit {spec.get('id')} {spec.get('name')}"
        if spec["id"] in ids or spec["name"] in names:
            bad.append(f"{tag}: id or name used twice")
        ids.add(spec["id"])
        names.add(spec["name"])
        if spec["side"] not in S.SIDES or spec["type"] not in U.TYPES or spec.get("xp", "regular") not in U.EXPERIENCE:
            bad.append(f"{tag}: side, type or experience unknown")
            continue
        if not 1 <= spec["size"] <= 4 or not 1 <= spec["steps"] <= spec.get("max", spec["steps"]):
            bad.append(f"{tag}: size 1 to 4 and steps 1 to max")
        if U.is_hq(spec) and (spec["steps"] != 1 or spec["size"] != 1):
            bad.append(f"{tag}: an HQ has one step and size 1")
        if spec.get("fuel", 0) > U.fuel_cap(spec) or spec.get("stores", 0) > U.stores_cap(spec):
            bad.append(f"{tag}: holds more than it can carry")
        spot = spec.get("entry") if "arrives" in spec else spec.get("at", spec.get("hex"))
        if isinstance(spot, str) and spot not in gmap.places:
            bad.append(f"{tag}: {spot} is not a place")
            continue
        h = gmap.places[spot]["hex"] if isinstance(spot, str) else tuple(spot or (-1, -1))
        if not gmap.passable(h) or least_path(gmap, h, gmap.base[spec["side"]], FOOT) is None:
            bad.append(f"{tag}: {h} is not ground a unit can stand on and leave")
            continue
        if "arrives" in spec:
            day(spec["arrives"], tag)
        else:
            where.setdefault(h, []).append(spec)
    for h, specs in sorted(where.items()):
        if len({s["side"] for s in specs}) > 1:
            bad.append(f"{h}: both sides start here")
        if sum(not U.is_hq(s) for s in specs) > U.STACK_COMBAT or sum(U.is_hq(s) for s in specs) > U.STACK_HQ:
            bad.append(f"{h}: too many units start here")
    for side in S.SIDES:
        n = sum(s["side"] == side for s in scenario["units"])
        if n > COUNTERS:
            bad.append(f"{side}: {n} counters, over the budget of {COUNTERS}")

    for c, r, level, side in scenario.get("forts", []):
        if not gmap.passable((c, r)) or not 1 <= level <= FORT_MAX or side not in S.SIDES:
            bad.append(f"fort at {(c, r)}: bad hex, level or side")
        if any(s["side"] != side for s in where.get((c, r), [])):
            bad.append(f"fort at {(c, r)}: the other side's units start in it")
    for event in scenario.get("withdrawals", []) + scenario.get("replacements", []):
        if event["unit"] not in ids:
            bad.append(f"event for unit {event['unit']}, which does not exist")
        day(event["date"], "event")
    return bad
