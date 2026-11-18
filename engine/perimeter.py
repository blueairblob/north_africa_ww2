"""Short-lived engineer and artillery preparation for mapped fortress crossings."""
from datetime import date, timedelta

from . import state as S

PREP_STORES = 25            # tonnes per size; a game estimate, not a historical expenditure
PREP_DAYS = 2              # a prepared crossing or registered barrage is usable for two days
RANGE = {"foot": 1, "motorised": 1, "guns": 2}
ROLE = {"foot": "engineers", "motorised": "engineers", "guns": "artillery"}


def today(scenario, turn):
    return date.fromisoformat(scenario["start"]) + timedelta(days=(turn - 1) * S.turn_days(scenario))


def ready(state, h, side, role):
    work = state.get("perimeter_prep", {}).get(S.fort_key(h), {})
    return work.get("side") == side and bool(work.get(role))


def expire(state, scenario):
    """Clear work past its dated window, including across a linked chapter handoff."""
    day = today(scenario, state["turn"])
    for key, work in list(state.get("perimeter_prep", {}).items()):
        for role in ("engineers", "artillery"):
            if work.get(role) and date.fromisoformat(work[role]) < day:
                del work[role]
        if not any(work.get(role) for role in ("engineers", "artillery")):
            del state["perimeter_prep"][key]


def prepare(state, ctx, scenario):
    """A formation spends a turn and stores preparing one still-intact enemy perimeter."""
    through = (today(scenario, state["turn"]) + timedelta(days=PREP_DAYS)).isoformat()
    for u in S.on_map(state):
        order = ctx["orders"][u["id"]]
        if order["order"] != "prepare" or u["type"] not in ROLE:
            continue
        h = tuple(order["to"])
        key = S.fort_key(h)
        if state.get("perimeters", {}).get(key) != S.enemy(u["side"]):
            continue
        if (S.distance(tuple(u["hex"]), h) > RANGE[u["type"]] or u["out_of_stores"]
                or u["id"] in ctx.get("in_battle", set())):
            continue
        role = ROLE[u["type"]]
        due = u["size"] * PREP_STORES
        if u["stores"] < due:
            continue
        work = state.setdefault("perimeter_prep", {}).setdefault(key, {"side": u["side"]})
        if work.get("side") != u["side"] or work.get(role):
            continue
        u["stores"] -= due
        state["sides"][u["side"]]["spent"] += due
        work[role] = through
        S.log(state, "perimeter prepared", side=u["side"], hex=list(h), unit=u["id"], role=role)
