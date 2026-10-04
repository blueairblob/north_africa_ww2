"""Supply: landing, the truck haul, HQs and dumps, issue, upkeep, shortage (docs/RULES.md §6)."""
from . import board as B
from . import state as S
from . import units as U
from .gamemap import WEST_ENTRY
from .paths import haul_distances, route

TRIPOLI_CAP = 3000      # tonnes landed at Tripoli per turn
PORT_CAP = {"Benghazi": 1500, "Tobruk": 1200, "Derna": 300, "Bardia": 300,
            "Mersa Matruh": 600, "Alexandria": 20000}       # tonnes landed per turn
RAIL_CAP = 8000         # tonnes per turn issued at the railhead
TRIPOLI_HAUL = 140      # haul cost from Tripoli to the west entry hex
TRIPOLI_DELAY = 2       # turns from landing at Tripoli to being available
PORT_REPAIR = 5         # condition regained per turn
HAUL_BURN_DIV = 2000    # tonne-units hauled per tonne of fuel burnt
REACH = 20              # haul distance within which a unit draws from a depot
REACH_FULL = 8          # haul distance within which a depot fills a unit completely
REACH_FILL_PCT = 50     # how full a depot can make a unit at REACH
DUMP_CAP = 3000         # tonnes of each kind an HQ dump may hold beyond current need
UPKEEP = 50             # tonnes of stores per size per turn
STARVE_COHESION = 10    # cohesion lost per turn out of stores
RESERVE_TURNS = 10      # turns of upkeep a port keeps for the units that draw from it
MORALE_UNSUPPLIED = 30  # off the ceiling of a unit with no depot in reach (20.3.2)
MORALE_THIN = 20        # off the ceiling of a unit at the limit of its depot's reach
MORALE_ORPHAN = 20      # off the ceiling of a unit out of reach of its own HQ
MORALE_WEAK = 40        # off the ceiling of a unit with no strength left; in proportion before that
MORALE_FALL = 10        # cohesion lost per turn above the ceiling

KINDS = ("stores", "fuel")                                   # stores are settled first (6.5.4)


def split(tonnes, fuel_pct):
    fuel = tonnes * fuel_pct // 100                           # 6.3.4
    return fuel, tonnes - fuel


def land(state, gmap, scenario):
    """Repair and landing (6.3)."""
    turn = state["turn"]
    for _, name in gmap.ports:
        port, owner = state["ports"][name], state["places"][name]
        port["condition"] = min(100, port["condition"] + PORT_REPAIR)                         # 6.3.1
        tonnes = PORT_CAP[name] * port["condition"] * S.side_value(scenario, owner, "sea_pct", turn, 100) // 10000
        fuel, stores = split(tonnes, S.side_value(scenario, owner, "fuel_pct", turn, 40))     # 6.3.2
        port["fuel"] += fuel
        port["stores"] += stores
        state["sides"][owner]["landed"] += tonnes                                             # 6.3.6
    tripoli = state["tripoli"]
    while len(tripoli["pipeline"]) >= TRIPOLI_DELAY:                                          # 6.3.5
        fuel, stores = tripoli["pipeline"].pop(0)
        tripoli["fuel"] += fuel
        tripoli["stores"] += stores
    tonnes = TRIPOLI_CAP * S.side_value(scenario, "axis", "sea_pct", turn, 100) // 100        # 6.3.3
    tripoli["pipeline"].append(list(split(tonnes, S.side_value(scenario, "axis", "fuel_pct", turn, 40))))
    state["sides"]["axis"]["landed"] += tonnes


def blocked_for(state, gmap, side):
    """The hexes no supply path of this side may enter (6.4.2)."""
    foe = S.enemy(side)
    held = B.occupied(state)
    mine = {h for h, s in held.items() if s == side}
    return {h for h, s in held.items() if s == foe} | (B.zoc(state, gmap, foe) - mine)


def railhead(state, gmap, scenario, blocked):
    """The effective railhead, or None if the line gives no outlet (6.2.4)."""
    name = S.side_value(scenario, "cw", "railhead", state["turn"], None)
    if name is None or state["places"]["Alexandria"] != "cw":
        return None
    reach = None
    for h in gmap.rail[:gmap.rail.index(gmap.places[name]["hex"]) + 1]:
        if h in blocked:
            break
        reach = h
    return None if reach in (None, gmap.rail[0]) else reach


def outlets(state, gmap, scenario, side, blocked):
    """Where this side's sources issue supply, in outlet order (6.2.5)."""
    out = []
    if side == "axis":
        out.append({"name": "Tripoli", "hex": WEST_ENTRY, "extra": TRIPOLI_HAUL, "stock": state["tripoli"]})
    else:
        head = railhead(state, gmap, scenario, blocked)
        if head:
            out.append({"name": "railhead", "hex": head, "extra": 0, "rail": True,
                        "stock": state["ports"]["Alexandria"]})
    for h, name in gmap.ports:
        if state["places"][name] == side:
            out.append({"name": name, "hex": h, "extra": 0, "stock": state["ports"][name]})
    for o in out:
        o["came"] = {}
        o["dist"] = haul_distances(gmap, o["hex"], blocked, came=o["came"])
    return out


def fill(d):
    """How full a depot at haul distance d can make a unit, per cent (6.6.5)."""
    if d <= REACH_FULL:
        return 100
    return 100 - (100 - REACH_FILL_PCT) * (d - REACH_FULL) // (REACH - REACH_FULL)


def demand(u, kind, d):
    cap = U.stores_cap(u) if kind == "stores" else U.fuel_cap(u)
    return max(0, cap * fill(d) // 100 - u[kind])             # 6.6.6


def largest(top, allowed):
    """The largest whole number from 0 to top for which allowed holds; allowed(0) holds and
    allowed is true up to some number and false above it."""
    lo, hi = 0, top
    while lo < hi:
        mid = (lo + hi + 1) // 2
        lo, hi = (mid, hi) if allowed(mid) else (lo, mid - 1)
    return lo


def haul(state, pool, outlet, hq, H, want):
    """One haul from an outlet to an HQ (6.5). pool holds the lift and rail tonnage left."""
    side_totals = state["sides"][hq["side"]]
    src = outlet["stock"]

    def allowed(f, s):                                        # 6.5.3, and the port's reserve (6.7.5)
        return ((f + s) * H <= pool["lift"] and s <= src["stores"] - outlet.get("reserve", 0)
                and f + -(-(f + s) * H // HAUL_BURN_DIV) <= src["fuel"]
                and (not outlet.get("rail") or f + s <= pool["rail"]))

    s = largest(want["stores"], lambda n: allowed(0, n))     # 6.5.4
    f = largest(want["fuel"], lambda n: allowed(n, s))
    burn = -(-(f + s) * H // HAUL_BURN_DIV)                   # 6.5.2
    pool["lift"] -= (f + s) * H
    if outlet.get("rail"):
        pool["rail"] -= f + s
    src["fuel"] -= f + burn
    src["stores"] -= s
    hq["dump"]["fuel"] += f
    hq["dump"]["stores"] += s
    side_totals["burnt"] += burn
    want["fuel"] -= f
    want["stores"] -= s
    if f + s:
        S.log(state, "haul", side=hq["side"], source=outlet["name"], hq=hq["id"], fuel=f, stores=s,
              burnt=burn, cost=H, route=[list(h) for h in route(outlet["came"], tuple(hq["hex"]))])


def distribute(state, gmap, scenario, side, audit):
    """Trace, haul to HQs, fill dumps and issue to units, for one side (6.4 to 6.8)."""
    totals = state["sides"][side]
    blocked = blocked_for(state, gmap, side)
    outs = outlets(state, gmap, scenario, side, blocked)
    units = S.on_map(state, side)
    hqs = [u for u in units if U.is_hq(u)]
    hq_dist = {u["id"]: haul_distances(gmap, tuple(u["hex"]), blocked, REACH) for u in hqs}
    pool = {"lift": S.side_value(scenario, side, "lift", state["turn"]) * (100 - totals["interdiction"]) // 100,
            "rail": RAIL_CAP}                                 # 6.5.1

    depots = {}                                               # 6.6.2, 6.6.3
    for u in units:
        h, found = tuple(u["hex"]), []
        for hq in hqs:
            if h in hq_dist[hq["id"]]:
                found.append((hq_dist[hq["id"]][h], 0, hq["id"], hq))
        for n, o in enumerate(outs):
            if h in o["dist"] and o["extra"] + o["dist"][h] <= REACH:
                found.append((o["extra"] + o["dist"][h], 1, n, o))
        depots[u["id"]] = sorted(found, key=lambda d: d[:3])
        u["traced"] = bool(found)                             # 6.6.4
        u["ceiling"] = 100 - (MORALE_THIN * (100 - fill(depots[u["id"]][0][0])) // 50 if found else MORALE_UNSUPPLIED)
        if u.get("parent"):                                   # 20.3.2: its own HQ gone, or out of reach
            hq = S.unit(state, u["parent"])
            if hq["status"] != "on_map" or h not in hq_dist[hq["id"]]:
                u["ceiling"] -= MORALE_ORPHAN
        u["ceiling"] -= MORALE_WEAK * (u["max"] - u["steps"]) // u["max"]

    for o in outs:                                            # 6.7.5: what a port keeps for its own
        o["reserve"] = 0 if "extra" in o and o["name"] in ("Tripoli", "railhead") else RESERVE_TURNS * UPKEEP * sum(
            u["size"] for u in units if depots[u["id"]] and depots[u["id"]][0][3] is o)
    by_stock = {}
    for o in outs:                                            # the railhead issues Alexandria's stock: one reserve
        by_stock[id(o["stock"])] = max(by_stock.get(id(o["stock"]), 0), o["reserve"])
    for o in outs:
        o["reserve"] = by_stock[id(o["stock"])]

    def reach_of(hq):
        return sorted((o["extra"] + o["dist"][tuple(hq["hex"])], n) for n, o in enumerate(outs)
                      if tuple(hq["hex"]) in o["dist"])

    served = sorted((reach_of(hq)[0][0], hq["id"], hq) for hq in hqs if reach_of(hq))     # 6.7.1
    gross = {}
    for _, _, hq in served:                                   # 6.7.2
        gross[hq["id"]] = {k: sum(demand(u, k, depots[u["id"]][0][0]) for u in units
                                  if depots[u["id"]] and depots[u["id"]][0][3] is hq) for k in KINDS}
        want = {k: max(0, gross[hq["id"]][k] - hq["dump"][k]) for k in KINDS}
        for H, n in reach_of(hq):
            haul(state, pool, outs[n], hq, H, want)
    on_hand = sum(o["stock"]["fuel"] + o["stock"]["stores"] for o in outs if not o.get("rail")) \
        + sum(hq["dump"]["fuel"] + hq["dump"]["stores"] for hq in hqs)
    before = totals["issued"]
    for u in sorted(units, key=lambda u: (100 * u["stores"] // U.stores_cap(u), u["id"])):   # 6.8.1
        for d, is_outlet, _, depot in depots[u["id"]]:        # 6.8.2
            stock = depot["stock"] if is_outlet else depot["dump"]
            for kind in KINDS:
                n = min(demand(u, kind, d), stock[kind])
                if is_outlet and depot.get("rail"):
                    n = min(n, pool["rail"])
                    pool["rail"] -= n
                stock[kind] -= n
                u[kind] += n
                totals["issued"] += n                         # 6.8.3
    led = {u["parent"] for u in state["units"] if u["parent"]}       # the HQs of divisions build no dumps (20.1.5)
    for _, _, hq in served:                                   # 6.7.3, 6.7.4: dumps, after the units have drawn
        if hq["stationary"] and hq["id"] not in led:
            need = {k: sum(demand(u, k, depots[u["id"]][0][0]) for u in units
                           if depots[u["id"]] and depots[u["id"]][0][3] is hq) for k in KINDS}
            want = {k: max(0, need[k] + DUMP_CAP - hq["dump"][k]) for k in KINDS}
            for H, n in reach_of(hq):
                haul(state, pool, outs[n], hq, H, want)
    if pool["lift"] < 0 or pool["rail"] < 0:
        audit.append(f"I-10 {side} used more lift or rail than it has: {pool}")
    if totals["issued"] - before > on_hand:
        audit.append(f"I-11 {side} units drew {totals['issued'] - before} from depots holding {on_hand}")


def upkeep(state, gmap):
    """Upkeep, and what being out of stores does (6.9.1, 6.10.2)."""
    for u in S.on_map(state):
        due = u["size"] * UPKEEP
        paid = min(due, u["stores"])
        u["stores"] -= paid
        state["sides"][u["side"]]["spent"] += paid
        u["out_of_stores"] = paid < due
    zocs = {side: B.zoc(state, gmap, side) for side in S.SIDES}       # as the units stand when the phase begins
    for u in S.on_map(state):
        if u["out_of_stores"]:
            if u["cohesion"] == 0 and tuple(u["hex"]) in zocs[S.enemy(u["side"])]:
                B.destroy(state, u, "surrendered")            # starving, broken and with the enemy at hand: it gives up
            elif u["cohesion"] == 0:
                u["steps"] -= 1
                if u["steps"] == 0:
                    B.destroy(state, u, "starved")
            else:
                u["cohesion"] = max(0, u["cohesion"] - STARVE_COHESION)
    for u in S.on_map(state):                                 # 20.3.3
        if u["cohesion"] > u["ceiling"]:
            u["cohesion"] = max(u["ceiling"], u["cohesion"] - MORALE_FALL)


def supply_phase(state, gmap, scenario, audit):
    land(state, gmap, scenario)
    for side in S.SIDES:
        distribute(state, gmap, scenario, side, audit)
    upkeep(state, gmap)
