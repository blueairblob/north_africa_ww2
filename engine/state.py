"""The game state: one plain structure that goes to JSON and back (docs/RULES.md §2)."""
import json
from datetime import date

from . import units as U
from .gamemap import distance  # noqa: F401  (hex distance, 1.4)

SIDES = ("axis", "cw")
TOTALS = ("brought", "landed", "issued", "spent", "burnt", "lost")


def enemy(side):
    return "cw" if side == "axis" else "axis"                   # 1.6


def priority_side(turn):
    return "axis" if turn % 2 else "cw"                         # 1.6


def turn_of(scenario, day):
    """The turn a date belongs to (1.9)."""
    days = (date.fromisoformat(day) - date.fromisoformat(scenario["start"])).days
    return max(1, days // 2 + 1)


def value_at(scenario, schedule, turn, default=0):
    """A scenario value that changes by date: the latest entry at or before this turn (12.6)."""
    value = default
    for day, v in schedule:
        if turn_of(scenario, day) <= turn:
            value = v
    return value


def side_value(scenario, side, name, turn, default=0):
    return value_at(scenario, scenario["sides"][side].get(name, []), turn, default)


def new_game(scenario, gmap):
    """The state at the start of turn 1."""
    owner = {name: side for side in SIDES for name in scenario["owners"][side]}
    state = {
        "scenario": scenario["id"], "turn": 1, "over": False, "result": None,
        "units": [], "places": {name: owner[name] for name in sorted(gmap.places)},
        "ports": {name: {"condition": 100, "fuel": 0, "stores": 0} for _, name in gmap.ports},
        "tripoli": {"fuel": 0, "stores": 0, "pipeline": []},
        "forts": {}, "log": [],
        "sides": {s: dict({"vp": 0, "air": "support", "interdiction": 0, "recon": 0},
                          **{t: 0 for t in TOTALS}) for s in SIDES},
    }
    for name, stock in scenario.get("ports", {}).items():
        state["ports"][name].update(stock)
    state["tripoli"].update(scenario.get("tripoli", {}))
    for c, r, level, side in scenario.get("forts", []):
        state["forts"][fort_key((c, r))] = [level, side]
    for spec in sorted(scenario["units"], key=lambda s: s["id"]):
        u = {"id": spec["id"], "side": spec["side"], "name": spec["name"], "type": spec["type"],
             "size": spec["size"], "xp": spec.get("xp", "regular"),
             "steps": spec["steps"], "max": spec.get("max", spec["steps"]),
             "hex": None, "cohesion": spec.get("cohesion", 100), "fuel": 0, "stores": 0,
             "out_of_stores": False, "traced": True, "status": "not_arrived"}
        u["fuel"] = spec.get("fuel", U.fuel_cap(u))
        u["stores"] = spec.get("stores", U.stores_cap(u))
        if U.is_hq(u):
            u["stationary"] = True
            u["dump"] = dict({"fuel": 0, "stores": 0}, **spec.get("dump", {}))
        if "arrives" not in spec:
            u["hex"] = list(spec["hex"]) if "hex" in spec else list(gmap.places[spec["at"]]["hex"])
            u["status"] = "on_map"
        state["units"].append(u)
    for side in SIDES:
        state["sides"][side]["brought"] = holdings(state, side)
    return state


def fort_key(h):
    return f"{h[0]},{h[1]}"


def on_map(state, side=None):
    """Units on the map, by id (1.8)."""
    return [u for u in state["units"] if u["status"] == "on_map" and side in (None, u["side"])]


def unit(state, uid):
    for u in state["units"]:
        if u["id"] == uid:
            return u
    return None


def at(state):
    """hex -> the units in it."""
    out = {}
    for u in on_map(state):
        out.setdefault(tuple(u["hex"]), []).append(u)
    return out


def carried(u):
    """Tonnes a unit holds, with its dump if it is an HQ."""
    return u["fuel"] + u["stores"] + (u["dump"]["fuel"] + u["dump"]["stores"] if U.is_hq(u) else 0)


def holdings(state, side):
    """Tonnes a side has in stocks, pipeline, dumps and units on the map (invariant I-9)."""
    total = sum(carried(u) for u in on_map(state, side))
    for name, port in state["ports"].items():
        if state["places"][name] == side:
            total += port["fuel"] + port["stores"]
    if side == "axis":
        total += state["tripoli"]["fuel"] + state["tripoli"]["stores"]
        total += sum(f + s for f, s in state["tripoli"]["pipeline"])
    return total


def log(state, kind, side=None, **what):
    """An event of this turn; side says who may see it (None: nobody but the engine's tests)."""
    state["log"].append(dict({"event": kind, "side": side}, **what))


def dumps(state):
    """The state as text, the same for the same state on any machine (invariant I-1)."""
    return json.dumps(state, sort_keys=True, separators=(",", ":"))
