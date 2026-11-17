"""The scenario checker: every place, unit and objective is on the map, on ground it can stand
on and where its name says (docs/ENGINEERING_NOTES.md §5). problems() returns what is wrong."""
from datetime import date, timedelta

from . import state as S
from . import units as U
from .paths import FOOT, least_path
from .recovery import FORT_MAX
from .supply import PORT_CAP
from .victory import par
from . import mission as M
from .weather import KINDS

COUNTERS = 60           # no more than about this many a side (DESIGN.md §14.1)


def problems(scenario, gmap):
    bad = []

    def day(d, what):
        try:
            return date.fromisoformat(d)
        except (TypeError, ValueError):
            bad.append(f"{what}: {d!r} is not a date")

    first = day(scenario.get("start"), "start")
    if type(S.turn_days(scenario)) is not int or S.turn_days(scenario) not in (1, 2):
        bad.append("turn_days: must be 1 or 2")
        return bad
    known = scenario.get("sources", {})

    def dated(d, src, what):                                     # 12.7: a date in the game, from a named source
        when = day(d, what)
        if when and first and (when - first).days >= S.turn_days(scenario) * scenario["turns"]:
            bad.append(f"{what}: {d} falls after the last turn")
        if src not in known:
            bad.append(f"{what}: its date names no source (one of the letters in the scenario's sources)")
    for entry in scenario.get("weather", []):                    # 21.3.1: the scenario's own odds
        ok = isinstance(entry, list) and len(entry) == 2 and isinstance(entry[1], dict)
        if ok:
            day(entry[0], "weather")
            ok = (set(entry[1]) <= set(KINDS[1:]) and all(isinstance(v, int) and v >= 0 for v in entry[1].values())
                  and sum(entry[1].values()) <= 100)
        if not ok:
            bad.append(f"weather: {entry!r} must be a date and the per cent of turns with rain and with sandstorm")
    owned = [n for side in S.SIDES for n in scenario["owners"][side]]
    if sorted(owned) != sorted(gmap.places):
        odd = set(owned) ^ set(gmap.places) | {n for n in owned if owned.count(n) > 1}
        bad.append(f"owners: every place must have one owner; wrong: {sorted(odd)}")
    for name in scenario.get("ports", {}):
        if name not in PORT_CAP and name not in scenario.get("landing_points", {}):
            bad.append(f"ports: {name} is not a port")
    for name, cap in scenario.get("landing_points", {}).items():
        if name not in gmap.places or name in PORT_CAP or type(cap) is not int or cap <= 0:
            bad.append(f"landing_points: {name} needs a non-port map place and a positive two-day capacity")
    for name, side in scenario.get("landing_sides", {}).items():
        if name not in scenario.get("landing_points", {}) or side not in S.SIDES:
            bad.append(f"landing_sides: {name} needs a landing point and axis or cw")
    seen_access, last_access = set(), {}
    for event in scenario.get("port_access", []):
        if not isinstance(event, dict) or set(event) != {"port", "side", "date", "pct", "src"}:
            bad.append("port_access: expected port, side, date, pct and source")
            continue
        if (not isinstance(event["port"], str) or
                (event["port"] not in PORT_CAP and event["port"] not in scenario.get("landing_points", {})) or
                event["side"] not in S.SIDES):
            bad.append("port_access: expected an existing port and side")
        if type(event["pct"]) is not int or not 0 <= event["pct"] <= 100:
            bad.append("port_access: percentage must be 0 to 100")
        when = day(event["date"], "port_access")
        if when and first and not first <= when < first + timedelta(days=S.turn_days(scenario) * scenario["turns"]):
            bad.append("port_access: date must fall within the chapter")
        if not isinstance(event["src"], str) or event["src"] not in known:
            bad.append("port_access: date names no scenario source")
        key = (event["port"], event["side"], event["date"])
        pair = (event["port"], event["side"])
        if when and all(isinstance(v, str) for v in pair):
            if pair in last_access and when < last_access[pair]:
                bad.append("port_access: dates must rise for each side and port")
            last_access[pair] = when
        if all(isinstance(v, str) for v in key):
            if key in seen_access:
                bad.append("port_access: duplicate date for one side and port")
            seen_access.add(key)
    for obj in scenario["objectives"]:
        if obj["place"] not in gmap.places:
            bad.append(f"objective {obj['place']} is not a place")
    aim = scenario.get("aim")
    if aim is not None and not (isinstance(aim, dict) and set(aim) == set(S.SIDES) and all(isinstance(v, str) and v for v in aim.values())):
        bad.append("aim: a sentence for each side is needed")
    if "campaign_finale" in scenario and type(scenario["campaign_finale"]) is not bool:
        bad.append("campaign_finale: expected true or false")
    bad += M.problems(scenario, gmap)
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
        alt_names = spec.get("alternate_names", [])
        if (not isinstance(alt_names, list) or any(not isinstance(n, str) or not n or n == spec["name"]
                                                   for n in alt_names) or len(alt_names) != len(set(alt_names))):
            bad.append(f"{tag}: alternate names must be distinct nonempty formation names")
        if "redesignation_src" in spec and spec["redesignation_src"] not in known:
            bad.append(f"{tag}: redesignation names no scenario source")
        if spec["side"] not in S.SIDES or spec["type"] not in U.TYPES or spec.get("xp", "regular") not in U.EXPERIENCE:
            bad.append(f"{tag}: side, type or experience unknown")
            continue
        if "steps" not in spec and U.real_of(spec) is None:
            bad.append(f"{tag}: needs steps or a real strength (tanks, men, guns or cars)")
            continue
        steps = U.steps_of(spec)
        if not 1 <= spec["size"] <= 4 or not 1 <= steps <= spec.get("max", steps):
            bad.append(f"{tag}: size 1 to 4 and steps 1 to max")
        if U.is_hq(spec) and (steps != 1 or spec["size"] != 1):
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
            dated(spec["arrives"], spec.get("arrives_src"), f"{tag}: arrival")
        else:
            where.setdefault(h, []).append(spec)
    hqs = {s["id"]: s for s in scenario["units"] if s.get("type") == "hq"}
    for spec in scenario["units"]:                              # 20.1.2
        parent = spec.get("parent")
        if parent is not None and (parent not in hqs or hqs[parent]["side"] != spec["side"] or parent == spec["id"]):
            bad.append(f"unit {spec['id']} {spec['name']}: its parent must be an HQ of its own side")
    for h, specs in sorted(where.items()):
        if len({s["side"] for s in specs}) > 1:
            bad.append(f"{h}: both sides start here")
        if len(U.stacked(specs)) > U.STACK_FORMATIONS:
            bad.append(f"{h}: too many formations start here")
    for side in S.SIDES:
        n = sum(s["side"] == side for s in scenario["units"])
        if n > COUNTERS:
            bad.append(f"{side}: {n} counters, over the budget of {COUNTERS}")

    for c, r, level, side in scenario.get("forts", []):
        if not gmap.passable((c, r)) or not 1 <= level <= FORT_MAX or side not in S.SIDES:
            bad.append(f"fort at {(c, r)}: bad hex, level or side")
        if any(s["side"] != side for s in where.get((c, r), [])):
            bad.append(f"fort at {(c, r)}: the other side's units start in it")
    forts = {(c, r): (level, side) for c, r, level, side in scenario.get("forts", [])}
    perimeters = set()
    for entry in scenario.get("perimeters", []):
        if (not isinstance(entry, list) or len(entry) != 3
                or any(type(x) is not int for x in entry[:2]) or entry[2] not in S.SIDES):
            bad.append("perimeter: expected a hex and defending side")
            continue
        c, r, side = entry
        if (c, r) in perimeters or (c, r) not in forts or forts[(c, r)][1] != side or forts[(c, r)][0] < 2:
            bad.append(f"perimeter at {(c, r)}: needs one matching level-2-or-higher fort")
        perimeters.add((c, r))
    specs = {s["id"]: s for s in scenario["units"]}
    seen_redesignations = set()
    for event in scenario.get("redesignations", []):
        what = f"redesignation for unit {event.get('unit')}"
        spec = specs.get(event.get("unit"))
        if spec is None:
            bad.append(f"{what}, which does not exist")
            continue
        dated(event.get("date"), event.get("src"), what)
        if (not isinstance(event.get("from"), str) or not isinstance(event.get("name"), str)
                or not event["name"] or event["from"] == event["name"]
                or event["from"] not in [spec["name"], *spec.get("alternate_names", [])]):
            bad.append(f"{what}: needs this formation's old name and a new name")
        key = (event["unit"], event.get("date"))
        if key in seen_redesignations:
            bad.append(f"{what}: duplicate date")
        seen_redesignations.add(key)
    for event in scenario.get("returns", []):
        what = f"return for unit {event.get('unit')}"
        if event.get("unit") not in specs:
            bad.append(f"{what}, which does not exist")
            continue
        dated(event.get("date"), event.get("src"), what)
        if not isinstance(event.get("entry"), str) or event["entry"] not in gmap.places:
            bad.append(f"{what}: entry needs a named place")
        rebuilt = event.get("return_as")
        if rebuilt is not None and (specs[event["unit"]]["type"] != "foot"
                or not isinstance(rebuilt, dict) or set(rebuilt) != {"name", "men", "size"}
                or rebuilt.get("name") != specs[event["unit"]]["name"]
                or type(rebuilt.get("men")) is not int or rebuilt["men"] < 1
                or type(rebuilt.get("size")) is not int or not 1 <= rebuilt["size"] <= 4):
            bad.append(f"{what}: return_as needs this infantry formation's name, men and size")
    for kind in ("withdrawals", "replacements"):
        for event in scenario.get(kind, []):
            what = f"{kind[:-1]} for unit {event.get('unit')}"
            if event.get("unit") not in ids:
                bad.append(f"{what}, which does not exist")
                continue
            dated(event.get("date"), event.get("src"), what)
            if kind == "withdrawals":
                if "if_name" in event and (not isinstance(event["if_name"], str)
                        or event["if_name"] not in [specs[event["unit"]]["name"],
                                                     *specs[event["unit"]].get("alternate_names", [])]):
                    bad.append(f"{what}: conditional name must identify this formation or a listed remnant")
                remnant = event.get("remain_as")
                if remnant is not None and ("if_near" not in event or specs[event["unit"]]["type"] != "foot"
                        or not isinstance(remnant, dict) or set(remnant) != {"name", "men", "size"}
                        or not isinstance(remnant.get("name"), str) or not remnant["name"]
                        or type(remnant.get("men")) is not int or remnant["men"] < 1
                        or type(remnant.get("size")) is not int or remnant["size"] != 1):
                    bad.append(f"{what}: remain_as needs a named one-size infantry remnant near a port")
                if "if_near" in event:
                    if (event["if_near"] not in gmap.places or type(event.get("radius")) is not int
                            or not 0 <= event["radius"] <= 3):
                        bad.append(f"{what}: conditional relief needs a place and radius 0–3")
                elif "radius" in event:
                    bad.append(f"{what}: radius needs if_near")
                continue
            given, real = U.counted(event), U.real_of(specs[event["unit"]])
            if not given or not isinstance(given[0], int) or given[0] < 1:
                bad.append(f"{what}: needs one whole number of steps, tanks, men, guns or cars")
            elif given[1] != "steps" and (real is None or real[1] != given[1]):
                bad.append(f"{what}: brings {given[1]}, which is not what the unit is counted in")
            if "via" in event and event["via"] not in gmap.places:
                bad.append(f"{what}: {event['via']} is not a place")
    return bad
