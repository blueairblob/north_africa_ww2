"""Combat: battles, values, losses, retreat and advance (docs/RULES.md §10)."""
from . import board as B
from . import state as S
from . import units as U
from .gamemap import distance
from .orders import ATTACK_MIN

# per step: attack on soft, attack on hard, defence against soft, defence against hard (10.9)
VALUES = {"armour": (6, 6, 4, 6), "motorised": (12, 6, 18, 9), "foot": (9, 3, 18, 6),
          "guns": (12, 12, 12, 30), "recon": (2, 1, 2, 2), "hq": (0, 0, 3, 3)}
XP = {"green": 80, "regular": 100, "veteran": 120}
ATTACK_STORES = 100     # tonnes of stores per size to attack
DEFEND_STORES = 50      # tonnes of stores per size to defend
UPHILL_PCT = 50         # attack value across a pass, uphill
REST_PCT = 75           # defence value of a resting unit
COLUMN_PCT = 25         # defence value of a unit on a road march
FLANK_PCT = 15          # added per extra hex attacked from
ROUGH_PCT = 50          # added to defence in rough
TOWN_PCT = 50           # added to defence in a port or town
FORT_PCT = 25           # added to defence per fortification level
COH_LOSS = 20           # cohesion lost by each side at even odds
COH_MIN, COH_MAX = 5, 60
STEP_LOSS = 10          # per cent of steps lost at even odds
STEP_MAX = 40           # most per cent of steps lost in a battle
RETREAT_MARGIN = 5      # how much more cohesion the defenders must lose to be driven back
ROUT_COHESION = 20      # below this a retreating unit goes two hexes


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def find_battles(state, gmap, ctx):
    """Who attacks which hex (10.1, 10.2)."""
    held, there, battles = B.occupied(state), S.at(state), {}
    for u in S.on_map(state):
        order = ctx["orders"][u["id"]]
        if order["order"] != "attack" or U.is_hq(u):
            continue
        if u["cohesion"] < ATTACK_MIN:                                       # 10.2.1
            S.log(state, "no attack", side=u["side"], unit=u["id"], why="too disorganised")
            continue
        here, foe = tuple(u["hex"]), S.enemy(u["side"])
        can = [n for _, n, hexside in gmap.around(here)                      # 10.2.3
               if held.get(n) == foe and hexside not in gmap.cliffs]
        nxt = ctx["next"].get(u["id"])
        if nxt in can:                                                       # 10.2.2
            target = nxt
        elif can:
            target = min(can, key=lambda h: (distance(h, tuple(order["to"])), h))
        else:
            S.log(state, "no attack", side=u["side"], unit=u["id"], why="no enemy in reach")
            continue
        battle = battles.setdefault(target, {"hex": target, "attackers": [], "defenders": there[target],
                                             "short": set(), "fought": False, "retreated": False})
        battle["attackers"].append(u)
    return [battles[h] for h in sorted(battles)]


def pay(state, battles):
    """Stores for fighting; a unit that cannot pay in full is short for that battle (10.3.1)."""
    bills = []
    for battle in battles:
        bills += [(u["id"], 0, u, ATTACK_STORES, battle) for u in battle["attackers"]]
        bills += [(u["id"], 1, u, DEFEND_STORES, battle) for u in battle["defenders"]]
    for _, _, u, rate, battle in sorted(bills, key=lambda b: b[:2]):
        due = u["size"] * rate
        paid = min(due, u["stores"])
        u["stores"] -= paid
        state["sides"][u["side"]]["spent"] += paid
        if paid < due:
            battle["short"].add(u["id"])


def efficiency(u, battle):
    cf = 50 + u["cohesion"] // 2                                             # 10.4.2
    sf = 50 if u["id"] in battle["short"] or u["out_of_stores"] else 100
    return cf * XP[u["xp"]] * sf


def values(state, gmap, ctx, battle):
    """The attack and defence totals of a battle (10.4)."""
    att, dfn, h = battle["attackers"], battle["defenders"], battle["hex"]
    sd = sum(u["steps"] for u in dfn if not U.is_hard(u))
    hd = sum(u["steps"] for u in dfn if U.is_hard(u))
    sa = sum(u["steps"] for u in att if not U.is_hard(u))
    ha = sum(u["steps"] for u in att if U.is_hard(u))
    total, battle["av"] = 0, {}
    for u in att:                                                            # 10.4.3
        a_soft, a_hard, _, _ = VALUES[u["type"]]
        hexside = gmap.side_between(tuple(u["hex"]), h)
        uphill = hexside in gmap.passes and gmap.high[hexside] == h
        battle["av"][u["id"]] = (10 * u["steps"] * (a_soft * sd + a_hard * hd) * efficiency(u, battle)
                                 * (UPHILL_PCT if uphill else 100)) // ((sd + hd) * 10 ** 8)
        total += battle["av"][u["id"]]
    froms = {tuple(u["hex"]) for u in att}
    battle["from"] = sorted(froms)
    battle["stood"] = [tuple(u["hex"]) for u in att]                         # where each attacker fought from
    battle["att"] = (total * (100 + FLANK_PCT * (len(froms) - 1))
                     * (100 + ctx["support"][att[0]["side"]])) // 10000     # 10.4.5
    total = 0
    for u in dfn:                                                            # 10.4.4
        _, _, d_soft, d_hard = VALUES[u["type"]]
        order = ctx["orders"][u["id"]]["order"]
        posture = REST_PCT if order == "rest" else COLUMN_PCT if order == "road_march" else 100
        total += (10 * u["steps"] * (d_soft * sa + d_hard * ha) * efficiency(u, battle)
                  * posture) // ((sa + ha) * 10 ** 8)
    fort = state["forts"].get(S.fort_key(h))
    ground = ((ROUGH_PCT if gmap.rough(h) else 0) + (TOWN_PCT if h in gmap.town_hexes else 0)
              + (FORT_PCT * fort[0] if fort and fort[1] == dfn[0]["side"] else 0))
    battle["def"] = max(1, (total * (100 + ground) * (100 + ctx["support"][dfn[0]["side"]])) // 10000)
    battle["steps"] = (sa + ha, sd + hd)


def share(units, lost):
    """Which units lose the steps: the one with most left, lowest id; an HQ last (10.5.3)."""
    left = {u["id"]: u["steps"] for u in units}
    out = {u["id"]: 0 for u in units}
    for _ in range(lost):
        pick = [u for u in units if not U.is_hq(u) and left[u["id"]] > 0]
        pick = pick or [u for u in units if left[u["id"]] > 0]
        if not pick:
            break
        u = max(pick, key=lambda u: (left[u["id"]], -u["id"]))
        left[u["id"]] -= 1
        out[u["id"]] += 1
    return out


def losses(battle):
    """Cohesion and step losses of a fought battle (10.5.1 to 10.5.3)."""
    att, dfn = battle["att"], battle["def"]
    battle["cla"] = clamp(COH_LOSS * dfn // att, COH_MIN, COH_MAX)
    battle["cld"] = clamp(COH_LOSS * att // dfn, COH_MIN, COH_MAX)
    a_steps, d_steps = battle["steps"]
    battle["lost"] = {**share(battle["attackers"], a_steps * min(STEP_MAX, STEP_LOSS * dfn // att) // 100),
                      **share(battle["defenders"], d_steps * min(STEP_MAX, STEP_LOSS * att // dfn) // 100)}


def retreat_hexes(state, gmap, u, here, froms, stack, barred=None):
    """The hexes next to here that u may retreat into, best first (10.6.2, 10.6.3).
    With stack False, those that fail only for want of room."""
    foe = S.enemy(u["side"])
    held, there, foe_zoc = B.occupied(state), S.at(state), B.zoc(state, gmap, foe)
    out = []
    for d, n, hexside in gmap.around(here):
        if hexside in gmap.cliffs and U.is_vehicle(u):
            continue
        if held.get(n) == foe or (n in foe_zoc and held.get(n) != u["side"]) or n in froms:
            continue
        if n in (tuple(u["hex"]), barred) or B.room(there.get(n, []), u) != stack:
            continue
        out.append(((-sum(distance(n, f) for f in froms), distance(n, gmap.base[u["side"]]), d), n))
    return [n for _, n in sorted(out)]


def retreat(state, gmap, ctx, u, froms):
    """One unit's retreat, or its surrender (10.6)."""
    hexes = 2 if u["cohesion"] < ROUT_COHESION else 1                        # 10.6.1
    ctx["retreated"].add(u["id"])
    here = tuple(u["hex"])
    first = retreat_hexes(state, gmap, u, here, froms, True)
    if not first:
        for through in retreat_hexes(state, gmap, u, here, froms, False):    # 10.6.4
            beyond = retreat_hexes(state, gmap, u, through, froms, True)
            if beyond:
                B.enter(state, u, beyond[0], ctx["entered"])
                S.log(state, "retreated", side=u["side"], unit=u["id"], to=list(beyond[0]))
                return
        B.destroy(state, u, "surrendered")                                   # 10.6.5
        return
    B.enter(state, u, first[0], ctx["entered"])
    if hexes == 2:                                                           # 10.6.6
        second = retreat_hexes(state, gmap, u, first[0], froms, True, barred=here)
        if second:
            B.enter(state, u, second[0], ctx["entered"])
    S.log(state, "retreated", side=u["side"], unit=u["id"], to=u["hex"])


def combat_phase(state, gmap, ctx):
    battles = find_battles(state, gmap, ctx)
    pay(state, battles)
    for battle in battles:
        values(state, gmap, ctx, battle)
        battle["fought"] = battle["att"] > 0                                 # 10.4.6
        if battle["fought"]:
            losses(battle)

    coh, steps = {}, {}                                                      # 10.5.4, 10.5.6
    for battle in battles:
        if not battle["fought"]:
            continue
        for u in battle["attackers"] + battle["defenders"]:
            attacker = any(v is u for v in battle["attackers"])
            coh[u["id"]] = coh.get(u["id"], 0) + (battle["cla"] if attacker else battle["cld"])
            steps[u["id"]] = steps.get(u["id"], 0) + battle["lost"][u["id"]]
            ctx["in_battle"].add(u["id"])
    for uid in sorted(coh):
        u = S.unit(state, uid)
        u["cohesion"] = max(0, u["cohesion"] - coh[uid])
        u["steps"] = max(0, u["steps"] - steps[uid])
    for uid in sorted(coh):
        u = S.unit(state, uid)
        if u["steps"] == 0:
            B.destroy(state, u, "combat")

    for battle in battles:                                                   # 10.6.7
        alive = [u for u in battle["defenders"] if u["status"] == "on_map"]
        if battle["fought"] and battle["cld"] >= battle["cla"] + RETREAT_MARGIN:
            battle["retreated"] = True
            for u in alive:
                retreat(state, gmap, ctx, u, battle["from"])
        elif battle["fought"] and not alive:
            battle["retreated"] = True                                       # none survived (11.1.1)

    for battle in battles:                                                   # 10.7.1
        if not battle["fought"] or B.occupied(state).get(battle["hex"]) == battle["defenders"][0]["side"]:
            continue
        for u in battle["attackers"]:
            if (u["status"] == "on_map" and u["id"] not in ctx["retreated"]
                    and B.room(S.at(state).get(battle["hex"], []), u)):
                B.enter(state, u, battle["hex"], ctx["entered"])             # 10.7.2
                S.log(state, "advanced", side=u["side"], unit=u["id"], to=list(battle["hex"]))
    B.settle_owners(state, gmap)                                             # 10.7.3

    for u in S.on_map(state):                                                # 9.9.1
        if U.is_hq(u) and u["id"] not in ctx["entered"]:
            u["stationary"] = True
    for battle in battles:
        if battle["fought"]:
            fought = battle["attackers"] + battle["defenders"]
            report = {"hex": list(battle["hex"]), "att": battle["att"], "def": battle["def"],
                      "cla": battle["cla"], "cld": battle["cld"],
                      "av": {str(k): v for k, v in sorted(battle["av"].items())},
                      "where": dict({str(u["id"]): list(h) for u, h in zip(battle["attackers"], battle["stood"])},
                                    **{str(u["id"]): list(battle["hex"]) for u in battle["defenders"]}),
                      "destroyed": [u["id"] for u in fought if u["status"] == "destroyed"],
                      "attackers": [u["id"] for u in battle["attackers"]],
                      "defenders": [u["id"] for u in battle["defenders"]],
                      "lost": {str(k): v for k, v in sorted(battle["lost"].items())},
                      "retreated": battle["retreated"]}
            S.log(state, "battle", side="both", sides=[battle["attackers"][0]["side"],
                                                       battle["defenders"][0]["side"]], **report)
    ctx["battles"] = battles
