"""Bounded whole-turn attack packages for the computer's visible battlefield.

This planner sees only a side view. It compares the current orders with a few
one-formation redirects, keeping the rest of the turn intact. The estimate is
deliberately coarse; the rules engine still resolves the actual battle.
"""
from . import combat as C
from . import orders as O
from . import paths
from . import tactics
from . import units as U
from . import weather as W
from .gamemap import distance
from .movement import ALLOWANCE

MAX_ROUTE = 3
MAX_REDIRECTS = 12
SAFE_OTHER_ODDS = 1.6


def _known_zoc(gmap, enemy_hexes):
    return {h for foe in enemy_hexes for _, h, _ in gmap.around(foe)}


def _can_join(gmap, view, lead, members, target, enemy_hexes, zoc):
    """A visible, plausible route into contact during this movement phase."""
    here = tuple(lead["hex"])
    if not 1 <= distance(here, target) <= MAX_ROUTE:
        return False
    if any(u["type"] != "hq" and u["cohesion"] < O.ATTACK_MIN for u in members):
        return False
    if any(not u["traced"] or u["out_of_stores"] for u in members) or not tactics.stores_safe([(lead, members)]):
        return False
    mode = O.mode(members, "attack", view["weather"])
    route = paths.least_path(gmap, here, target, mode)
    if not route or len(route) > MAX_ROUTE or any(h in enemy_hexes for h in route[:-1]):
        return False
    allowance = W.allowance(view["weather"], min(ALLOWANCE[u["type"]] for u in members))
    spent, cur = 0, here
    for i, nxt in enumerate(route[:-1]):
        if i < len(route) - 2 and nxt in zoc:
            return False             # would stop before reaching the attack hex
        if cur in zoc and nxt in zoc:
            return False
        side = gmap.side_between(cur, nxt)
        cost = paths.step_cost(gmap, cur, nxt, side, mode)
        if cost is None:
            return False
        spent += cost
        cur = nxt
    if spent > allowance:
        return False
    return all(not U.is_vehicle(u) or u["fuel"] >= U.step_fuel(u) * (len(route) + 2) for u in members)


def _objective_values(gmap, view):
    return {tuple(gmap.places[o["place"]]["hex"]): o.get("end", 0) + 2 * o.get("turn", 0)
            for o in view["objectives"] if o["place"] in gmap.places and view["places"].get(o["place"]) != view["side"]}


def _battle_score(gmap, view, target, attackers, defenders, objective_value):
    if not attackers:
        return 0.0
    eligible = [(lead, [u for u in members if u["type"] == "hq" or u["cohesion"] >= O.ATTACK_MIN])
                for lead, members in attackers]
    ratio = tactics.odds(gmap, view, eligible, defenders, target)
    if ratio <= 0:
        return 0.0
    attacker_steps = sum(u["steps"] for _, members in eligible for u in members if u["type"] != "hq")
    defender_steps = sum(tactics.ENEMY_STEPS[e["type"]] * tactics.STRENGTH_SHARE.get(e.get("strength"), 1.0)
                         for e in defenders)
    # The combat rules drive defenders back when their cohesion loss exceeds
    # the attackers'. This is a conservative approximation, not a prediction.
    capture = max(0.0, min(0.9, (ratio - 0.8) / 1.4))
    enemy_loss = defender_steps * min(C.STEP_MAX / 100, C.STEP_LOSS / 100 * ratio)
    own_loss = attacker_steps * min(C.STEP_MAX / 100, C.STEP_LOSS / 100 / ratio)
    return objective_value * capture + 1.5 * enemy_loss - 2.0 * own_loss


def _score(gmap, view, formations, orders, defenders, objectives, enemy_hexes, zoc):
    by_id = {lead["id"]: (lead, members) for lead, members in formations}
    assigned = {}
    for order in orders.values():
        if order["order"] != "attack" or order["unit"] not in by_id:
            continue
        target = tuple(order["to"])
        if target not in defenders:
            continue
        lead, members = by_id[order["unit"]]
        if _can_join(gmap, view, lead, members, target, enemy_hexes, zoc):
            assigned.setdefault(target, []).append((lead, members))
    return sum(_battle_score(gmap, view, target, groups, defenders[target], objectives.get(target, 0))
               for target, groups in assigned.items())


def coordinate(gmap, view, given, formations, protected=()):
    """Return the best of baseline and at most 12 one-formation attack packages."""
    defenders = {}
    for enemy in view["enemy"]:
        defenders.setdefault(tuple(enemy["hex"]), []).append(enemy)
    if not defenders:
        return given
    objectives = _objective_values(gmap, view)
    enemy_hexes = set(defenders)
    zoc = _known_zoc(gmap, enemy_hexes)
    orders = {order["unit"]: order for order in given["orders"]}
    by_id = {lead["id"]: (lead, members) for lead, members in formations}
    held = {tuple(gmap.places[o["place"]]["hex"]) for o in view["objectives"]
            if o["place"] in gmap.places and view["places"].get(o["place"]) == view["side"]}
    baseline = _score(gmap, view, formations, orders, defenders, objectives, enemy_hexes, zoc)
    best_score, best = baseline, None
    tried = 0
    for target in sorted(objectives, key=lambda h: (-objectives[h], h)):
        if target not in defenders:
            continue
        attackers = [uid for uid, order in orders.items() if order["order"] == "attack"
                     and tuple(order["to"]) == target and uid in by_id
                     and _can_join(gmap, view, *by_id[uid], target, enemy_hexes, zoc)]
        if not attackers:
            continue
        # Do not add strength to an attack already likely to win. Concentration
        # is useful when it turns an uncertain battle, not when it abandons a
        # second front for a marginal improvement to an overwhelming one.
        if tactics.odds(gmap, view, [by_id[uid] for uid in attackers], defenders[target], target) >= 1.2:
            continue
        for uid in sorted(by_id):
            if uid in protected or uid in attackers:
                continue
            lead, members = by_id[uid]
            old = orders.get(uid)
            if (old is None or old["order"] != "attack" or tuple(old["to"]) in objectives
                    or tuple(old["to"]) not in defenders):
                continue
            old_target = tuple(old["to"])
            remaining = [by_id[other] for other, order in orders.items()
                         if other != uid and other in by_id and order["order"] == "attack"
                         and tuple(order["to"]) == old_target
                         and _can_join(gmap, view, *by_id[other], old_target, enemy_hexes, zoc)]
            # The visible-strength estimate is rough. Leave a sizeable margin
            # for the other attack before lending it a formation.
            if (not remaining or tactics.odds(gmap, view, remaining, defenders[old_target], old_target)
                    < SAFE_OTHER_ODDS):
                continue
            if tuple(lead["hex"]) in held:
                continue
            if not _can_join(gmap, view, lead, members, target, enemy_hexes, zoc):
                continue
            trial = dict(orders)
            trial[uid] = {"unit": uid, "order": "attack", "to": list(target)}
            score = _score(gmap, view, formations, trial, defenders, objectives, enemy_hexes, zoc)
            if score > best_score + 0.5:
                best_score, best = score, trial[uid]
            tried += 1
            if tried >= MAX_REDIRECTS:
                break
        if tried >= MAX_REDIRECTS:
            break
    if best is not None:
        given["orders"] = [best if o["unit"] == best["unit"] else o for o in given["orders"]]
    return given
