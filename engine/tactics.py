"""Conservative local attack assessment from a computer player's limited view.

Enemy step counts and cohesion are unknown. Type-based estimates are deliberately
coarse; a battle estimate is a reason to reject a clearly bad attack, not a
prediction of the engine's hidden combat roll.
"""
from . import combat as C
from . import paths
from . import units as U
from .gamemap import distance
from .supply import REACH, UPKEEP

# Typical strengths by counter class, used only when the enemy is visible.
# These are priors, never copied from the hidden scenario or state.
ENEMY_STEPS = {"armour": 13, "motorised": 3, "foot": 3, "guns": 4, "recon": 3, "hq": 1}
STRENGTH_SHARE = {"at strength": 1.0, "worn": 0.5, "weak": 0.25}


def odds(gmap, view, groups, defenders, target):
    """Approximate attack/defence ratio; group entries are (leader, members)."""
    attackers = [u for _, members in groups for u in members if u["type"] != "hq"]
    if not attackers or not defenders:
        return 0.0
    hard_d = sum(ENEMY_STEPS[e["type"]] * STRENGTH_SHARE.get(e.get("strength"), 1.0)
                 for e in defenders if U.is_hard(e))
    soft_d = sum(ENEMY_STEPS[e["type"]] * STRENGTH_SHARE.get(e.get("strength"), 1.0)
                 for e in defenders if not U.is_hard(e))
    hard_a = sum(u["steps"] for u in attackers if U.is_hard(u))
    soft_a = sum(u["steps"] for u in attackers if not U.is_hard(u))
    attack = 0.0
    for u in attackers:
        soft, hard, _, _ = C.VALUES[u["type"]]
        match = (soft * soft_d + hard * hard_d) / (soft_d + hard_d)
        supply = 0.5 if u["out_of_stores"] or u["stores"] < u["size"] * C.ATTACK_STORES else 1.0
        attack += u["steps"] * match * (50 + u["cohesion"] / 2) / 100 * C.XP[u["xp"]] / 100 * supply
    attack *= 1 + C.FLANK_PCT * (len({tuple(lead["hex"]) for lead, _ in groups}) - 1) / 100
    defence = 0.0
    for e in defenders:
        _, _, soft, hard = C.VALUES[e["type"]]
        steps = ENEMY_STEPS[e["type"]] * STRENGTH_SHARE.get(e.get("strength"), 1.0)
        match = (soft * soft_a + hard * hard_a) / (soft_a + hard_a)
        defence += steps * match * 0.9 * C.XP[e["xp"]] / 100
    fort = view["forts"].get(f"{target[0]},{target[1]}")
    ground = (C.ROUGH_PCT if gmap.rough(target) else 0) + (C.TOWN_PCT if target in gmap.town_hexes else 0)
    if fort and fort[1] != view["side"]:
        ground += C.FORT_PCT * fort[0]
    return attack / max(1.0, defence * (1 + ground / 100))


def stores_safe(groups):
    """Attacking consumes stores before the next supply issue."""
    return all(u["stores"] >= u["size"] * (C.ATTACK_STORES + UPKEEP)
               for _, members in groups for u in members if u["type"] != "hq")


def retreat_hex(gmap, view, lead, members):
    """A one-hex withdrawal away from spotted enemies, preserving an owned objective."""
    here = tuple(lead["hex"])
    if any(tuple(gmap.places[o["place"]]["hex"]) == here and view["places"].get(o["place"]) == view["side"]
           for o in view["objectives"]):
        return None
    foes = [tuple(e["hex"]) for e in view["enemy"]]
    if not foes:
        return None
    old = min(distance(here, h) for h in foes)
    depots = [tuple(u["hex"]) for u in view["units"] if u["status"] == "on_map" and u["type"] == "hq"
              and not u["out_of_stores"] and min(u["dump"].values()) > 0]
    depots += [tuple(gmap.places[name]["hex"]) for name, stock in view["ports"].items()
               if stock["fuel"] > 0 and stock["stores"] > 0]
    if not depots:
        return None
    own = {tuple(u["hex"]) for u in view["units"] if u["status"] == "on_map"}
    blocked = ({h for foe in foes for _, h, _ in gmap.around(foe)} | set(foes)) - own
    supply = [paths.haul_distances(gmap, depot, blocked=blocked, limit=REACH) for depot in depots]
    old_supply = min((d[here] for d in supply if here in d), default=REACH + 1)
    options = []
    for _, h, hexside in gmap.around(here):
        if hexside in gmap.cliffs and any(U.is_vehicle(u) for u in members):
            continue
        if min(distance(h, foe) for foe in foes) <= old or min(distance(h, foe) for foe in foes) <= 1:
            continue
        haul = min((d[h] for d in supply if h in d), default=REACH + 1)
        if haul > REACH or haul > old_supply:
            continue
        if any(tuple(u["hex"]) == h for u in view["units"] if u["status"] == "on_map"):
            continue
        options.append((haul, h))
    return min(options)[1] if options else None
