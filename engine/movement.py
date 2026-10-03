"""Simultaneous movement in impulses (docs/RULES.md §9)."""
from . import board as B
from . import state as S
from . import units as U
from .orders import MOVING, full_path, mode
from .paths import step_cost

IMPULSES = 24           # impulses in a Movement phase; also the most hexes a unit can move
ALLOWANCE = {"foot": 16, "armour": 32, "guns": 32, "motorised": 40, "hq": 40, "recon": 48}   # MP per turn
MOVE_COHESION_DIV = 4   # MP spent per point of cohesion lost
FORT_MP = 2             # MP per level to enter a hex with an enemy fortification


def cost_of(state, gmap, m, here, nxt):
    """MP for the unit's step, with any enemy fortification in the hex entered (9.3)."""
    cost = step_cost(gmap, here, nxt, gmap.side_between(here, nxt), m["mode"])
    fort = state["forts"].get(S.fort_key(nxt))
    if fort and fort[1] != m["u"]["side"]:
        cost += FORT_MP * fort[0]
    return cost


def movement_phase(state, gmap, ctx):
    if sorted(ctx["orders"]) != [u["id"] for u in S.on_map(state)]:
        ctx["audit"].append("I-15 the orders do not match the units on the map")
    movers = {}
    for u in S.on_map(state):
        order = ctx["orders"][u["id"]]
        if order["order"] in MOVING:                                         # 9.1.2
            movers[u["id"]] = {"u": u, "path": full_path(gmap, u, order) or [], "i": 0, "spent": 0,
                               "stopped": False, "mode": mode(u, order["order"]),
                               "attack": order["order"] == "attack"}

    def stop(m, why=None):
        m["stopped"] = True
        if why:
            S.log(state, "stopped", side=m["u"]["side"], unit=m["u"]["id"], why=why, hex=m["u"]["hex"])

    for impulse in range(1, IMPULSES + 1):
        held = B.occupied(state)
        zocs = {s: B.zoc(state, gmap, s) for s in S.SIDES}
        trying = {}
        for uid in sorted(movers):                                           # 9.5.1
            m = movers[uid]
            u = m["u"]
            if m["stopped"]:
                continue
            if m["i"] >= len(m["path"]):
                stop(m)
                continue
            here, nxt, foe = tuple(u["hex"]), m["path"][m["i"]], S.enemy(u["side"])
            cost = cost_of(state, gmap, m, here, nxt)
            if ALLOWANCE[u["type"]] * impulse // IMPULSES - m["spent"] < cost:      # 9.4.2
                continue
            if held.get(nxt) == foe:
                stop(m, "contact")
            elif here in zocs[foe] and nxt in zocs[foe]:
                stop(m, "zone of control")
            elif U.is_vehicle(u) and u["fuel"] < U.step_fuel(u):
                stop(m, "out of fuel")
            else:
                trying[uid] = (nxt, cost)

        for h in sorted({nxt for nxt, _ in trying.values()}):                # 9.5.3
            here = [uid for uid in sorted(trying) if trying[uid][0] == h]
            sides = {movers[uid]["u"]["side"] for uid in here}
            if len(sides) == 2:
                attacking = {movers[uid]["u"]["side"] for uid in here if movers[uid]["attack"]}
                winner = attacking.pop() if len(attacking) == 1 else S.priority_side(state["turn"])
                for uid in here:
                    if movers[uid]["u"]["side"] != winner:
                        del trying[uid]
                        stop(movers[uid], "contact")

        there, changed = S.at(state), True                                   # 9.5.4
        while changed:
            changed = False
            for h in sorted({nxt for nxt, _ in trying.values()}):
                staying = [v for v in there.get(h, []) if v["id"] not in trying]
                for hq, limit in ((False, U.STACK_COMBAT), (True, U.STACK_HQ)):
                    entering = [uid for uid in sorted(trying)
                                if trying[uid][0] == h and U.is_hq(movers[uid]["u"]) == hq]
                    over = len([v for v in staying if U.is_hq(v) == hq]) + len(entering) - limit
                    for uid in reversed(entering[max(0, len(entering) - over):] if over > 0 else []):
                        del trying[uid]
                        changed = True

        for uid in sorted(trying):                                           # 9.5.5, 9.5.6
            nxt, cost = trying[uid]
            m = movers[uid]
            u = m["u"]
            fuel = U.step_fuel(u) if U.is_vehicle(u) else 0                   # 9.7.1
            u["fuel"] -= fuel
            state["sides"][u["side"]]["spent"] += fuel
            m["spent"] += cost
            m["i"] += 1
            B.enter(state, u, nxt, ctx["entered"])

        zocs = {s: B.zoc(state, gmap, s) for s in S.SIDES}                   # 9.5.7
        for uid in sorted(trying):
            u = movers[uid]["u"]
            if tuple(u["hex"]) in zocs[S.enemy(u["side"])]:
                stop(movers[uid], "contact")

    for uid in sorted(movers):
        m = movers[uid]
        ctx["next"][uid] = m["path"][m["i"]] if m["i"] < len(m["path"]) else None
        ctx["mp"][uid] = m["spent"]
        if m["i"] > IMPULSES or m["spent"] > ALLOWANCE[m["u"]["type"]]:
            ctx["audit"].append(f"I-16 unit {uid} moved {m['i']} hexes for {m['spent']} MP")
        m["u"]["cohesion"] = max(0, m["u"]["cohesion"] - m["spent"] // MOVE_COHESION_DIV)    # 9.8.1
    B.settle_owners(state, gmap)                                             # 3.4.2

