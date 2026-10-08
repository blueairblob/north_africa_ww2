"""What each side can see (docs/RULES.md §14). A player is given this and nothing else."""
from . import state as S
from . import weather as W
from .gamemap import distance

SPOT_RANGE = 2          # hexes at which any unit spots
SPOT_RANGE_RECON = 4    # hexes at which a recon unit spots


def spot_range(state, u, extra):
    """How far this unit spots: by its type, further with air recon, less in a sandstorm (14.3, 21.4.2)."""
    return W.sight(state["weather"], (SPOT_RANGE_RECON if u["type"] == "recon" else SPOT_RANGE) + extra)


def view(state, gmap, scenario, side):
    mine = S.on_map(state, side)
    extra = state["sides"][side]["recon"]                                    # 7.5

    def spotted(h):                                                          # 14.3
        return any(distance(h, tuple(u["hex"])) <= spot_range(state, u, extra) for u in mine)

    def adjacent(h):
        return any(distance(h, tuple(u["hex"])) == 1 for u in mine)

    seen = []
    for u in S.on_map(state, S.enemy(side)):                                 # 14.4
        h = tuple(u["hex"])
        if spotted(h):
            e = {k: u[k] for k in ("id", "name", "type", "hex", "xp")}
            if adjacent(h):
                e["steps"] = u["steps"]
            seen.append(e)
    forts = {}
    for key, (level, owner) in sorted(state["forts"].items()):               # 14.5
        if owner == side or spotted(tuple(int(x) for x in key.split(","))):
            forts[key] = [level, owner]
    specs = {spec["id"]: spec for spec in scenario["units"]}
    return {
        "side": side, "turn": state["turn"], "over": state["over"], "result": state["result"],
        "weather": state["weather"],                                         # 21.5: this turn's, and a word on the next
        "outlook": W.outlook(state["seed"], state["turn"], scenario),
        "units": [dict(u) for u in state["units"] if u["side"] == side],
        "arrivals": [{"unit": u["id"], "date": specs[u["id"]]["arrives"]} for u in state["units"]
                     if u["side"] == side and u["status"] == "not_arrived"],
        "withdrawals": [w for w in scenario.get("withdrawals", []) if S.unit(state, w["unit"])["side"] == side],
        "enemy": seen, "forts": forts, "places": dict(state["places"]),
        "ports": {n: dict(p) for n, p in state["ports"].items() if state["places"][n] == side},
        "tripoli": {k: (v if k != "pipeline" else [list(x) for x in v]) for k, v in state["tripoli"].items()}
        if side == "axis" else None,
        "lift": S.side_value(scenario, side, "lift", state["turn"]),
        "air_points": S.side_value(scenario, side, "air", state["turn"]),
        "vp": {s: state["sides"][s]["vp"] for s in S.SIDES},
        "kills": {s: state["sides"][s]["kills"] for s in S.SIDES},               # the part of vp for units destroyed
        "par": scenario.get("par", 0),
        "objectives": scenario["objectives"],
        "events": [dict(e) for e in state["log"]                             # 14.6
                   if e["side"] == side or (e["side"] == "both" and side in e["sides"])],
    }


def leaks(v, state):
    """What a view holds that it must not (invariant I-17, 14.8)."""
    side, out = v["side"], []
    if "seed" in v:
        out.append("the seed the weather is drawn from")
    for e in v["enemy"]:
        if set(e) - {"id", "name", "type", "hex", "xp", "steps"}:
            out.append(f"enemy unit {e['id']} shows {sorted(e)}")
    for u in v["units"]:
        if u["side"] != side:
            out.append(f"unit {u['id']} of the other side")
    if any(state["places"][n] != side for n in v["ports"]):
        out.append("an enemy port's stock")
    return out

