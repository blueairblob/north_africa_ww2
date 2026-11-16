"""After the fighting: recovered tanks, rest, digging (docs/RULES.md §11)."""
from . import state as S
from . import units as U

RECOVER_PCT = 50        # share of its lost tank steps the field's holder gets back
REST_GAIN = 20          # cohesion regained by resting
HOLD_GAIN = 5           # cohesion regained by holding
FORT_MAX = 4            # highest fortification level
DIG_STORES = 50         # tonnes of stores per size to raise a level


def recovery_phase(state, ctx, scenario):
    for battle in ctx["battles"]:                                            # 11.1
        if not battle["fought"]:
            continue
        holders = battle["attackers"] if battle["retreated"] else battle["defenders"]
        for u in holders:
            if u["type"] == "armour" and u["status"] == "on_map":
                u["steps"] = min(u["max"], u["steps"] + battle["lost"][u["id"]] * RECOVER_PCT // 100)

    for u in S.on_map(state):                                                # 11.2.1
        gain = {"rest": REST_GAIN, "hold": HOLD_GAIN}.get(ctx["orders"][u["id"]]["order"], 0)
        gain = gain * S.turn_days(scenario) // 2
        if gain and u["traced"] and not u["out_of_stores"] and u["id"] not in ctx["in_battle"]:
            u["cohesion"] = max(u["cohesion"], min(u["ceiling"], u["cohesion"] + gain))   # 20.3.4

    there = S.at(state)
    days = S.turn_days(scenario)
    prior_work = state.get("fort_work", {})
    next_work = {}
    for h in sorted(there):                                                  # 11.3
        stood = [u for u in there[h] if not U.is_hq(u) and u["id"] not in ctx["retreated"]]
        key = S.fort_key(h)
        level = state["forts"][key][0] if key in state["forts"] else 0
        diggers = [u for u in stood if ctx["orders"][u["id"]]["order"] == "dig_in"
                   and u["stores"] >= u["size"] * DIG_STORES * days // 2]
        owner = stood[0]["side"] if stood else None
        earlier = prior_work.get(key)
        progress = earlier[1] if earlier and earlier[0] == owner else 0
        if diggers and level < FORT_MAX:                                     # 11.3.3
            u = diggers[0]
            spent = u["size"] * DIG_STORES * days // 2
            u["stores"] -= spent
            state["sides"][u["side"]]["spent"] += spent
            progress += days
            if progress >= 2:
                level += 1
                progress -= 2
                state["forts"][key] = [level, u["side"]]
            if progress and level < FORT_MAX:
                next_work[key] = [u["side"], progress]
        elif level == 0 and any(ctx["orders"][u["id"]]["order"] == "hold" for u in stood):
            progress += days
            if progress >= 2:
                state["forts"][key] = [1, owner]                             # 11.3.2
            else:
                next_work[key] = [owner, progress]
    if "fort_work" in state or next_work:
        state["fort_work"] = next_work
    held = {S.fort_key(h) for h in there}
    for key in sorted(state["forts"]):                                       # 11.3.5
        if state["forts"][key][0] == 1 and key not in held:
            del state["forts"][key]
