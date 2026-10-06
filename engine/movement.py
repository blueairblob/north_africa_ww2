"""Simultaneous movement in impulses (docs/RULES.md §9), a group moving as one (20.2.6)."""
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
    """MP for the party's step, with any enemy fortification in the hex entered (9.3). The
    party's mode already costs the step for the member that finds it hardest."""
    cost = step_cost(gmap, here, nxt, gmap.side_between(here, nxt), m["mode"])
    fort = state["forts"].get(S.fort_key(nxt))
    if fort and fort[1] != m["side"]:
        cost += FORT_MP * fort[0]
    return cost


def movement_phase(state, gmap, ctx):
    if sorted(ctx["orders"]) != [u["id"] for u in S.on_map(state)]:
        ctx["audit"].append("I-15 the orders do not match the units on the map")
    movers = {}                                                              # by the id of each party's leader
    for u in S.on_map(state):
        order = ctx["orders"][u["id"]]
        if u["group"] not in (None, u["id"]) or order["order"] not in MOVING:      # 9.1.2; members go with their leader
            continue
        units = S.party(state, u)
        movers[u["id"]] = {"units": units, "side": u["side"], "path": full_path(gmap, u, order, state) or [],
                           "i": 0, "spent": 0, "stopped": False, "mode": mode(units, order["order"]),
                           "allowance": min(ALLOWANCE[v["type"]] for v in units),   # 20.2.6
                           "attack": order["order"] == "attack"}

    def stop(m, why=None):
        m["stopped"] = True
        if why:
            for u in m["units"]:
                S.log(state, "stopped", side=u["side"], unit=u["id"], why=why, hex=u["hex"])

    def passing(m, here, enemy_zoc, foe):
        """The way through the full hexes ahead to the first hex with room, as one step:
        (that hex, the MP for the whole passage, the hexes entered). None if the next hex is
        not full, or the unit could not come out the other side: the path ends there, the enemy
        holds or watches a hex of the passage, or the fuel would not last."""
        there, mine = S.at(state), {u["id"] for u in m["units"]}
        full = lambda h: any(v["id"] not in mine for v in there.get(h, [])) and not B.room(there.get(h, []), m["units"])
        if not full(m["path"][m["i"]]):
            return None
        cur, total, hexes = here, 0, []
        for h in m["path"][m["i"]:]:
            total += cost_of(state, gmap, m, cur, h)
            hexes.append(h)
            if held.get(h) == foe:
                return None
            if not full(h):
                short = any(U.is_vehicle(u) and u["fuel"] < U.step_fuel(u) * len(hexes) for u in m["units"])
                return None if short else (h, total, hexes)
            if h in enemy_zoc:
                return None
            cur = h
        return None

    for impulse in range(1, IMPULSES + 1):
        held = B.occupied(state)
        zocs = {s: B.zoc(state, gmap, s) for s in S.SIDES}
        trying = {}
        for lead in sorted(movers):                                          # 9.5.1
            m = movers[lead]
            if m["stopped"]:
                continue
            if m["i"] >= len(m["path"]):
                stop(m)
                continue
            here, nxt, foe = tuple(m["units"][0]["hex"]), m["path"][m["i"]], S.enemy(m["side"])
            cost = cost_of(state, gmap, m, here, nxt)
            if m["allowance"] * impulse // IMPULSES - m["spent"] < cost:     # 9.4.2
                continue
            if held.get(nxt) == foe:
                stop(m, "contact")
            elif here in zocs[foe] and nxt in zocs[foe]:
                stop(m, "zone of control")
            elif any(U.is_vehicle(u) and u["fuel"] < U.step_fuel(u) for u in m["units"]):
                stop(m, "out of fuel")
            else:
                trying[lead] = (nxt, cost, [nxt])
                through = passing(m, here, zocs[foe], foe)                  # 9.5.8: on through hexes too full to stop in
                if through and m["allowance"] - m["spent"] >= through[1]:
                    if m["allowance"] * impulse // IMPULSES - m["spent"] < through[1]:
                        del trying[lead]                                     # it waits until it can make the whole passage
                    else:
                        trying[lead] = through

        for h in sorted({t[0] for t in trying.values()}):                    # 9.5.3
            here = [lead for lead in sorted(trying) if trying[lead][0] == h]
            sides = {movers[lead]["side"] for lead in here}
            if len(sides) == 2:
                attacking = {movers[lead]["side"] for lead in here if movers[lead]["attack"]}
                winner = attacking.pop() if len(attacking) == 1 else S.priority_side(state["turn"])
                for lead in here:
                    if movers[lead]["side"] != winner:
                        del trying[lead]
                        stop(movers[lead], "contact")

        there, changed = S.at(state), True                                   # 9.5.4, 20.1.4
        while changed:
            changed = False
            leaving = {u["id"] for lead in trying for u in movers[lead]["units"]}
            for h in sorted({t[0] for t in trying.values()}):
                now = [v for v in there.get(h, []) if v["id"] not in leaving]
                for lead in sorted(lead for lead in trying if trying[lead][0] == h):   # lowest id first
                    if B.room(now, movers[lead]["units"]):
                        now = now + movers[lead]["units"]
                    else:
                        del trying[lead]                                      # refused whole; it tries again
                        movers[lead]["full"] = h
                        changed = True
                if changed:
                    break

        for lead in sorted(trying):                                          # 9.5.5, 9.5.6
            nxt, cost, hexes = trying[lead]
            m = movers[lead]
            for u in m["units"]:
                fuel = U.step_fuel(u) * len(hexes) if U.is_vehicle(u) else 0  # 9.7.1
                u["fuel"] -= fuel
                state["sides"][u["side"]]["spent"] += fuel
                B.enter(state, u, nxt, ctx["entered"])
                for h in hexes:                                              # a passage shows every hex it went through
                    S.log(state, "step", side=u["side"], unit=u["id"], impulse=impulse, to=list(h), march=m["mode"] == "march")
            m["spent"] += cost
            m["i"] += len(hexes)
            m["full"] = None

        zocs = {s: B.zoc(state, gmap, s) for s in S.SIDES}                   # 9.5.7
        for lead in sorted(trying):
            m = movers[lead]
            if tuple(m["units"][0]["hex"]) in zocs[S.enemy(m["side"])]:
                stop(m, "contact")

    for lead in sorted(movers):
        m = movers[lead]
        if m.get("full"):                                                    # 9.5.4: still refused when the phase ended
            for u in m["units"]:
                S.log(state, "stopped", side=u["side"], unit=u["id"], why="no room", hex=u["hex"], at=list(m["full"]))
        if m["i"] > IMPULSES or m["spent"] > m["allowance"]:
            ctx["audit"].append(f"I-16 unit {lead} moved {m['i']} hexes for {m['spent']} MP")
        for u in m["units"]:
            ctx["next"][u["id"]] = m["path"][m["i"]] if m["i"] < len(m["path"]) else None
            ctx["mp"][u["id"]] = m["spent"]
            u["cohesion"] = max(0, u["cohesion"] - m["spent"] // MOVE_COHESION_DIV)       # 9.8.1
    for u in S.on_map(state):                                                # 20.2.2: joined, if it got there
        order = ctx["orders"][u["id"]]
        if order["order"] == "join":
            other = S.unit(state, order["with"])
            if other["status"] == "on_map" and other["hex"] == u["hex"] and B.room(
                    [v for v in S.at(state)[tuple(u["hex"])]], [u]):
                B.join(state, u, other)
    B.regroup(state)
    B.settle_owners(state, gmap)                                             # 3.4.2
