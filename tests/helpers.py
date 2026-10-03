"""Small scenarios for the engine's tests, on the real map."""
import json
from pathlib import Path

from engine.gamemap import GameMap

ROOT = Path(__file__).parent.parent
GMAP = GameMap(json.loads((ROOT / "data" / "map.json").read_text()))
CW_IN_LIBYA = ("Tobruk", "Fort Maddalena", "Jarabub")
AXIS_IN_EGYPT = ("Sollum", "Halfaya Pass")


def owners():
    """The frontier of late 1941: Libya to the Axis but for Tobruk, Egypt to the Commonwealth."""
    axis = [n for n, p in GMAP.places.items()
            if (p["col"] < 68 and n not in CW_IN_LIBYA) or n in AXIS_IN_EGYPT]
    return {"axis": sorted(axis), "cw": sorted(set(GMAP.places) - set(axis))}


def unit(uid, side, kind, where, **more):
    u = {"id": uid, "side": side, "name": f"{side} {kind} {uid}", "type": kind,
         "size": 1, "steps": 6}
    u["at" if isinstance(where, str) else "hex"] = where
    u.update(more)
    return u


def scenario(units, **more):
    s = {"id": "test", "name": "test", "start": "1941-11-18", "turns": 6, "owners": owners(),
         "sides": {"axis": {"lift": [["1941-11-18", 200000]], "air": [["1941-11-18", 1]]},
                   "cw": {"lift": [["1941-11-18", 200000]], "air": [["1941-11-18", 1]],
                          "railhead": [["1941-11-18", "Misheifa"]]}},
         "units": units, "objectives": [{"place": "Tobruk", "turn": 1, "end": 10}],
         "thresholds": [5, 15, 30]}
    s.update(more)
    return s


def small():
    return json.loads((ROOT / "tests" / "scenarios" / "small.json").read_text())


def start(units, **more):
    """A scenario and its opening state."""
    from engine import state as S
    sc = scenario(units, **more)
    return sc, S.new_game(sc, GMAP)


def turn(sc, state, axis=(), cw=(), air="support"):
    """Phases 2 to 8 from the given orders. Returns the new state and the replies."""
    from engine.turn import finish_turn
    return finish_turn(state, GMAP, sc, {"axis": {"orders": list(axis), "air": air},
                                         "cw": {"orders": list(cw), "air": air}})


def by_id(state):
    return {u["id"]: u for u in state["units"]}
