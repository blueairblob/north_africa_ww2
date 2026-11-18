"""A deterministic opponent using only the view given to a human player.

Public High Command orders and point objectives shape its sectors. No enemy
strength, position or supply outside the side view is read.
"""
from . import orders as O
from . import mission as M
from . import paths
from . import perimeter as P
from . import tactics
from . import units as U
from .board import HQ_CARRY
from .gamemap import distance
from .movement import turn_allowance
from .supply import REACH


class ComputerOpponent:
    """Standard opponent for either side of the desert campaign."""

    level = "standard"
    road_weight = 3
    held_divisor = 3
    assignment_penalty = 12
    threat_range = 3
    rest_below = O.ATTACK_MIN
    dig_limit = 3
    use_road_march = True
    use_interdict = True
    guard_objective = False
    mission_enabled = True

    def __init__(self, gmap):
        self.gmap = gmap
        self.days = 2
        self.blocked_perimeters = frozenset()
        self.avoid_attack = frozenset()

    def _objectives(self, view):
        """Public objectives form a stable plan, including the short game's two road goals."""
        road = {o["place"] for o in view["objectives"]} >= {"Sidi Rezegh", "Belhamed"}
        out = []
        for obj in view["objectives"]:
            name = obj["place"]
            if name not in self.gmap.places:
                continue
            points = obj.get("end", 0) + 3 * obj.get("turn", 0)
            if road and name in ("Sidi Rezegh", "Belhamed"):
                points *= self.road_weight
            if view["places"].get(name) == view["side"]:
                points = max(1, points // self.held_divisor)
            out.append((name, tuple(self.gmap.places[name]["hex"]), points))
        if self.mission_enabled:
            out = self._mission_goals(view, out)
        return out

    def _mission_orders(self, view):
        return view.get("mission", {}).get(view["side"], {}).get("orders", []) if self.mission_enabled else []

    def _mission_goals(self, view, goals):
        """Put unfulfilled place orders and visible route blockers ahead of point raids."""
        own = {tuple(u["hex"]) for u in view["units"] if u["status"] == "on_map"}
        secure = {tuple(u["hex"]) for u in view["units"] if u["status"] == "on_map" and u["type"] != "hq"}
        visible = {tuple(u["hex"]) for u in view["enemy"]}
        mission = view["mission"]
        extra = []
        for order in self._mission_orders(view):
            verb = order["verb"]
            if verb in ("hold", "reach"):
                name = order["place"]
                if verb == "reach" and name in view.get("mission_reached", []):
                    continue
                h = tuple(self.gmap.places[name]["hex"])
                if h not in (secure if verb == "hold" else own):
                    extra.append((name, h, 240))
            elif verb == "stage":
                h = tuple(order["hex"])
                if h not in secure:
                    extra.append((f"stage:{order['label']}", h, 240))
            elif verb == "breach":
                h = tuple(order["hex"])
                if M.breach_key(order) not in view.get("mission_reached", []) and h not in secure:
                    extra.append((f"breach:{order['label']}", h, 500))
            elif verb in ("clear", "deny"):
                route = mission["routes"][order["route"]]
                path = [tuple(h) for h in route["hexes"]]
                if verb == "clear":
                    extra += [(f"clear:{order['route']}:{h}", h, 210) for h in path if h in visible]
                elif not secure.intersection(path):
                    # Reoccupy the central corridor when no friendly unit blocks it.
                    middle = path[len(path) // 2]
                    extra.append((f"deny:{order['route']}", middle, 220))
            elif verb == "surround":
                centre = self.gmap.places[order["place"]]["hex"]
                extra += [(f"surround:{order['place']}:{h}", h, 150) for _, h, _ in self.gmap.around(centre)
                          if h not in own]
        by_name = {name: (name, h, value) for name, h, value in goals}
        for name, h, value in extra:
            old = by_name.get(name)
            by_name[name] = (name, h, max(value, old[2]) if old else value)
        return list(by_name.values())

    def _mission_anchors(self, view, formations):
        """Keep one fighting formation on each occupied hold/deny target."""
        orders = self._mission_orders(view)
        if not orders:
            return set()
        mission = view["mission"]
        fighting = [(lead, members) for lead, members in formations if any(m["type"] != "hq" for m in members)]
        anchors = set()

        def protect(hexes):
            if any(lead["id"] in anchors and tuple(lead["hex"]) in hexes for lead, _ in fighting):
                return
            choices = [(len(members), -sum(m["steps"] for m in members), lead["id"])
                       for lead, members in fighting if lead["id"] not in anchors and tuple(lead["hex"]) in hexes]
            if choices:
                anchors.add(min(choices)[2])

        for order in orders:
            if order["verb"] == "hold":
                protect({tuple(self.gmap.places[order["place"]]["hex"])})
            elif order["verb"] == "deny":
                protect({tuple(h) for h in mission["routes"][order["route"]]["hexes"]})
            elif order["verb"] == "stage":
                protect({tuple(order["hex"])})
        return anchors

    def _sector(self, here, goals, assigned):
        """Choose a valuable nearby objective, spreading formations across the front."""
        if self.level == "easy":
            return min(goals, key=lambda goal: (distance(here, goal[1]) + 3 * assigned.get(goal[0], 0),
                                                -goal[2], goal[0]))
        penalty = self.assignment_penalty
        return max(goals, key=lambda goal: (goal[2] * 100 // (distance(here, goal[1]) + 4)
                                            - penalty * assigned.get(goal[0], 0), -distance(here, goal[1]), goal[0]))

    def _route(self, here, target, members, name, weather):
        mode = O.mode(members, name, weather)
        blocked = (self.blocked_perimeters - ({target} if name == "attack" else set())) | self.avoid_attack
        return paths.least_path(self.gmap, here, target, mode, blocked)

    def _staging(self, here, target, members, weather, occupied, foes):
        """Keep additional formations beside a goal instead of ordering all into one hex."""
        choices = [h for _, h, _ in self.gmap.around(target)
                   if occupied.get(h, 0) < U.STACK_FORMATIONS and h not in foes]
        for h in sorted(choices, key=lambda h: (distance(here, h), h)):
            if self._route(here, h, members, "move", weather) is not None:
                return h
        return target

    def _destination(self, here, target, members, weather, action):
        """Try the chosen ground, then a reachable neighbour when cliffs block it."""
        candidates = [target] + [h for _, h, _ in self.gmap.around(target)]
        for h in candidates:
            if h != here and self._route(here, h, members, action, weather) is not None:
                return h
        return None

    def _travel_leg(self, here, target, members, weather, foes, fuel_hexes):
        """Use a safe route leg on the approach, even when the final goal needs an attack."""
        if here not in self.gmap.on_route or fuel_hexes < 4:
            return None
        # A town can be off the road; stop on a nearby route before the assault.
        ends = [target] if target in self.gmap.on_route else sorted(
            (h for h in self.gmap.on_route if distance(h, target) <= 2),
            key=lambda h: (distance(h, target), distance(here, h), h))[:8]
        paths_to = [(self._route(here, end, members, "road_march", weather), end) for end in ends]
        paths_to = [(path, end) for path, end in paths_to if path]
        if not paths_to:
            return None
        path, _ = min(paths_to, key=lambda item: (len(item[0]) + 2 * distance(item[1], target), item[1]))
        if len(path) < 4 or len(path) > 2 * distance(here, target) + 4:
            return None
        danger = {h for foe, _ in foes for _, h, _ in self.gmap.around(foe)} | {foe for foe, _ in foes}
        allowance = turn_allowance(members, self.days)
        mode = O.mode(members, "road_march", weather)
        spent, cur, safe = 0, here, []
        for h in path:
            if h in danger or len(safe) >= fuel_hexes:
                break
            cost = paths.step_cost(self.gmap, cur, h, self.gmap.side_between(cur, h), mode)
            if cost is None or spent + cost > allowance:
                break
            spent += cost
            safe.append(h)
            cur = h
        # Advance materially toward the goal; avoid vulnerable road columns
        # for a short hop or a detour that makes no operational progress.
        if len(safe) < 4 or distance(safe[-1], target) > distance(here, target) - 3:
            return None
        return safe[-1]

    def _travel_entry(self, here, target, members, weather, foes, fuel_hexes):
        """Approach a nearby road only when it saves a substantial long journey."""
        if here in self.gmap.on_route or distance(here, target) < 9 or fuel_hexes < 8:
            return None
        danger = {h for foe, _ in foes for _, h, _ in self.gmap.around(foe)} | {foe for foe, _ in foes}
        ends = [target] if target in self.gmap.on_route else [
            h for h in self.gmap.on_route if distance(h, target) <= 2]
        choices = []
        for entry in sorted((h for h in self.gmap.on_route if distance(here, h) <= 2),
                            key=lambda h: (distance(here, h), h)):
            approach = self._route(here, entry, members, "move", weather)
            if not approach or any(h in danger for h in approach):
                continue
            for end in sorted(ends, key=lambda h: (distance(entry, h), h))[:5]:
                road = self._route(entry, end, members, "road_march", weather)
                if road is None or len(road) < 5:
                    continue
                # A road diversion should beat a direct desert crossing by
                # more than the extra turn needed to change movement orders.
                score = 4 * len(approach) + 3 * len(road) + 4 * distance(end, target)
                if score + 8 < 4 * distance(here, target):
                    choices.append((score, len(approach), entry))
        return min(choices)[2] if choices else None

    def _unblock_mission_routes(self, view, formations, orders, anchors):
        """Move a spare formation aside when it fills the first step to a hold objective."""
        if not self.mission_enabled:
            return
        holds = {tuple(self.gmap.places[o["place"]]["hex"]): view["places"].get(o["place"]) == view["side"]
                 for o in self._mission_orders(view) if o["verb"] == "hold"}
        targets = {h for h, ours in holds.items() if not ours}
        if not targets:
            return
        by_id = {lead["id"]: (lead, members) for lead, members in formations}
        by_hex = {}
        for lead, members in formations:
            by_hex.setdefault(tuple(lead["hex"]), []).append((lead, members))
        visible = {tuple(e["hex"]) for e in view["enemy"]}
        given = {o["unit"]: o for o in orders}
        for uid, order in sorted(given.items()):
            if order["order"] not in ("move", "attack") or tuple(order["to"]) not in targets:
                continue
            lead, members = by_id[uid]
            here = tuple(lead["hex"])
            path = self._route(here, tuple(order["to"]), members, order["order"], view["weather"])
            if not path:
                continue
            blocked = path[0]
            occupants = by_hex.get(blocked, [])
            if len(U.stacked(m for _, group in occupants for m in group)) < U.STACK_FORMATIONS:
                continue
            choices = []
            for spare, group in occupants:
                old = given[spare["id"]]
                if spare["id"] in anchors or old["order"] in ("move", "road_march", "join"):
                    continue
                old_target = tuple(old["to"]) if "to" in old else tuple(order["to"])
                for _, h, _ in self.gmap.around(blocked):
                    if h in visible or h in path or h == here:
                        continue
                    there = by_hex.get(h, [])
                    if len(U.stacked(m for _, other in there for m in other)) >= U.STACK_FORMATIONS:
                        continue
                    route = self._route(blocked, h, group, "move", view["weather"])
                    if route != [h]:
                        continue
                    choices.append((distance(h, old_target), distance(h, tuple(order["to"])),
                                    spare["id"], h, old))
            if choices:
                _, _, _, destination, spare_order = min(choices)
                spare_order.update(order="move", to=list(destination))
                # If this stack itself is a held mission place, its guard can
                # join the adjacent assault. The spare stays close enough to
                # return next turn, while the stronger attacker can push on.
                target = tuple(order["to"])
                if blocked in holds and target in visible:
                    defenders = [e for e in view["enemy"] if tuple(e["hex"]) == target]
                    for guard, group in occupants:
                        guard_order = given[guard["id"]]
                        if (guard["id"] not in anchors or guard_order is spare_order
                                or guard_order["order"] not in ("hold", "dig_in")
                                or any(m["type"] != "hq" and m["cohesion"] < O.ATTACK_MIN for m in group)
                                or any(not m["traced"] or m["out_of_stores"] for m in group)
                                or self._route(blocked, target, group, "attack", view["weather"]) != [target]):
                            continue
                        if tactics.odds(self.gmap, view, [(lead, members), (guard, group)], defenders, target) >= 1.0:
                            guard_order.update(order="attack", to=list(target))
                            break
                return

    def _avoid_hopeless_first_contact(self, view, formations, orders):
        """Do not send a small party through a visible, overwhelming armoured screen."""
        by_id = {lead["id"]: (lead, members) for lead, members in formations}
        defenders = {}
        for enemy in view["enemy"]:
            defenders.setdefault(tuple(enemy["hex"]), []).append(enemy)
        contacts = {}
        for order in orders:
            if order["order"] != "attack" or order["unit"] not in by_id:
                continue
            lead, members = by_id[order["unit"]]
            path = self._route(tuple(lead["hex"]), tuple(order["to"]), members,
                               "attack", view["weather"])
            first = next((h for h in path or [] if h in defenders), None)
            if first is not None:
                contacts.setdefault(first, []).append(order)
        for first, attack_orders in contacts.items():
            defending = defenders[first]
            if not any(u["type"] == "armour" for u in defending):
                continue
            attackers = [by_id[o["unit"]] for o in attack_orders]
            if tactics.odds(self.gmap, view, attackers, defending, first) >= 0.4:
                continue
            for order in attack_orders:
                if len(by_id[order["unit"]][1]) <= 2:
                    order.pop("to", None)
                    order["order"] = "hold"

    def orders(self, view):
        from .players import parties

        self.days = view.get("turn_days", 2)
        side = view["side"]
        self.blocked_perimeters = frozenset(tuple(int(x) for x in key.split(","))
                                            for key, owner in view.get("perimeters", {}).items() if owner != side)
        goals = self._objectives(view)
        foes = sorted((tuple(e["hex"]), e["id"]) for e in view["enemy"])
        formations = sorted(parties(view), key=lambda party: party[0]["id"])
        mission_anchors = self._mission_anchors(view, formations)
        mission_orders = self._mission_orders(view)
        prep_orders, assigned_prep = {}, set()
        for goal in (mission_orders if view.get("mission", {}).get(side, {}).get("prepare_breach") else ()):
            if goal["verb"] != "breach":
                continue
            target = tuple(goal["hex"])
            key = f"{target[0]},{target[1]}"
            if view.get("perimeters", {}).get(key) in (None, side):
                continue
            ready = view.get("perimeter_prep", {}).get(key, {})
            for lead, members in formations:
                roles = {P.ROLE[u["type"]] for u in members if u["type"] in P.ROLE
                         and distance(tuple(u["hex"]), target) <= P.RANGE[u["type"]]
                         and not u["out_of_stores"] and u["stores"] >= u["size"] * P.PREP_STORES}
                if any(not ready.get(role) and (key, role) not in assigned_prep for role in roles):
                    prep_orders[lead["id"]] = target
                    assigned_prep.update((key, role) for role in roles if not ready.get(role))
        avoid_attack = ({tuple(self.gmap.places[name]["hex"])
                         for name in view.get("mission", {}).get(side, {}).get("avoid_attack", [])}
                        if self.mission_enabled else set())
        if self.mission_enabled:
            avoid_attack.update(tuple(h) for h in view.get("mission", {}).get(side, {}).get("avoid_attack_hexes", []))
        secure_hexes = {tuple(u["hex"]) for u in view["units"]
                        if u["status"] == "on_map" and u["type"] != "hq"}
        if any(order["verb"] == "breach" and M.breach_key(order) not in view.get("mission_reached", [])
               and tuple(order["hex"]) not in secure_hexes for order in mission_orders):
            avoid_attack.update(tuple(self.gmap.places[order["place"]]["hex"])
                                for order in mission_orders if order["verb"] == "hold")
        avoid_attack.update(prep_orders.values())
        self.avoid_attack = frozenset(avoid_attack)
        mission_holds = {order["place"] for order in mission_orders if order["verb"] == "hold"}
        route_blockers = set()
        if mission_holds and all(view["places"].get(place) == side for place in mission_holds):
            routes = view.get("mission", {}).get("routes", {})
            for mission_order in mission_orders:
                if mission_order["verb"] == "clear" and mission_order["route"] in routes:
                    route_blockers.update(tuple(h) for h in routes[mission_order["route"]]["hexes"])
        occupied = {}
        for lead, _ in formations:
            h = tuple(lead["hex"])
            occupied[h] = occupied.get(h, 0) + 1
        assigned, orders = {}, []
        for lead, members in formations:
            here = tuple(lead["hex"])
            fighters = [m for m in members if m["type"] != "hq"]
            fighting = bool(fighters) and any(m["cohesion"] >= O.ATTACK_MIN for m in fighters)
            if lead["id"] in prep_orders:
                orders.append({"unit": lead["id"], "order": "prepare", "to": list(prep_orders[lead["id"]])})
                continue
            cut_off = any(not m["traced"] for m in members)
            short_of_stores = any(m["out_of_stores"] for m in members)
            fuel_hexes = min((m["fuel"] // U.step_fuel(m) for m in members if U.is_vehicle(m)), default=99)
            nearest = min(foes, key=lambda foe: (distance(here, foe[0]), foe)) if foes else None
            threat = nearest and distance(here, nearest[0]) <= self.threat_range

            if not fighters:
                # A detached divisional HQ rejoins its own troops; it does
                # not lead a lone charge against an objective.
                children = [m for party, group in formations for m in group
                            if m.get("parent") == lead["id"] and party["id"] != lead["id"]]
                child = min(children, key=lambda m: (distance(here, tuple(m["hex"])), m["id"])) if children else None
                if child and not threat and self._route(here, tuple(child["hex"]), members, "join", view["weather"]) is not None:
                    orders.append({"unit": lead["id"], "order": "join", "with": child["id"]})
                else:
                    orders.append({"unit": lead["id"], "order": "hold"})
                continue

            if min(m["cohesion"] for m in fighters) < self.rest_below:
                orders.append({"unit": lead["id"], "order": "hold" if self.level == "hard" and threat else "rest"})
                continue
            if lead["id"] in mission_anchors:
                fort = view["forts"].get(f"{here[0]},{here[1]}")
                dug = fort and fort[1] == side and fort[0] >= self.dig_limit
                orders.append({"unit": lead["id"], "order": "hold" if dug or short_of_stores else "dig_in"})
                continue
            if self.guard_objective and threat and any(
                    tuple(self.gmap.places[obj["place"]]["hex"]) == here and obj.get("end", 0) >= 20
                    and view["places"].get(obj["place"]) == side
                    and (not mission_orders or obj["place"] in mission_holds)
                    for obj in view["objectives"]):
                # The mission's chosen garrison already secures this hex.
                # Let a second formation engage a visible route blocker.
                covered = any(other["id"] != lead["id"] and other["id"] in mission_anchors
                              and tuple(other["hex"]) == here for other, _ in formations)
                if not covered:
                    fort = view["forts"].get(f"{here[0]},{here[1]}")
                    dug = fort and fort[1] == side and fort[0] >= self.dig_limit
                    orders.append({"unit": lead["id"], "order": "hold" if dug or short_of_stores else "dig_in"})
                    continue
            if cut_off and fuel_hexes >= 2:
                friendly_ports = [tuple(self.gmap.places[name]["hex"]) for name in view["ports"]]
                rear = min(friendly_ports + [self.gmap.base[side]], key=lambda h: (distance(here, h), h))
                to = self._destination(here, rear, members, view["weather"], "move")
                orders.append({"unit": lead["id"], "order": "move", "to": list(to)} if to else
                              {"unit": lead["id"], "order": "hold"})
                continue
            if cut_off or short_of_stores or fuel_hexes < 2:
                orders.append({"unit": lead["id"], "order": "hold"})
                continue
            if not goals and not nearest:
                orders.append({"unit": lead["id"], "order": "hold"})
                continue

            goal = self._sector(here, goals, assigned) if goals else None
            if goal:
                assigned[goal[0]] = assigned.get(goal[0], 0) + 1
            target = goal[1] if goal else nearest[0]
            stage_goal = bool(goal and goal[0].startswith(("stage:", "breach:")))
            # A visible nearby enemy calls for an attack. Headquarters alone
            # avoid combat and move only towards their assigned sector.
            if fighting and threat and not stage_goal:
                blocker = min((foe for foe in foes if foe[0] in route_blockers
                               and distance(here, foe[0]) <= self.threat_range),
                              key=lambda foe: (distance(here, foe[0]), foe), default=None)
                target, action = (blocker or nearest)[0], "attack"
            elif stage_goal:
                barrier = view.get("perimeters", {}).get(f"{target[0]},{target[1]}")
                has_infantry = any(m["type"] in ("foot", "motorised") for m in members)
                action = "attack" if fighting and (target in {h for h, _ in foes}
                                                    or (barrier is not None and barrier != side and has_infantry)) else "move"
            elif goal and view["places"].get(goal[0]) != side and fighting:
                action = "attack"
            else:
                action = "move"
            if action == "attack" and target in avoid_attack:
                orders.append({"unit": lead["id"], "order": "hold"})
                continue
            if goal and target == goal[1] and here != target and not threat \
                    and (assigned[goal[0]] > U.STACK_FORMATIONS or occupied.get(target, 0) >= U.STACK_FORMATIONS):
                target = self._staging(here, target, members, view["weather"], occupied,
                                       {h for h, _ in foes})
            if here == target:
                # Fortify a held objective when there is time and stores.
                fort = view["forts"].get(f"{here[0]},{here[1]}")
                dug = fort and fort[1] == side and fort[0] >= self.dig_limit
                name = "dig_in" if fighters and not dug and all(m["stores"] > 0 for m in members) else "hold"
                orders.append({"unit": lead["id"], "order": name})
                continue
            target = self._destination(here, target, members, view["weather"], action)
            if target is None:
                orders.append({"unit": lead["id"], "order": "hold"})
                continue
            if self.use_road_march and not threat:
                entry = self._travel_entry(here, target, members, view["weather"], foes, fuel_hexes)
                if entry is not None:
                    target, action = entry, "move"
            if self.use_road_march and not threat and distance(here, target) > 5:
                travel = self._travel_leg(here, target, members, view["weather"], foes, fuel_hexes)
                if travel is not None:
                    target, action = travel, "road_march"
            orders.append({"unit": lead["id"], "order": action, "to": list(target)})
            occupied[target] = occupied.get(target, 0) + 1

        self._unblock_mission_routes(view, formations, orders, mission_anchors)
        self._avoid_hopeless_first_contact(view, formations, orders)
        attacks = any(order["order"] == "attack" for order in orders)
        air = "support" if attacks else "interdict" if foes and self.use_interdict else "recon"
        return {"orders": orders, "air": air}


class ComputerEasy(ComputerOpponent):
    """Shorter planning horizon, less digging and fewer long road marches."""

    level = "easy"
    threat_range = 2
    rest_below = 60
    dig_limit = 1
    use_road_march = True
    use_interdict = False


class ComputerPoints(ComputerOpponent):
    """Previous point-only Standard planner for paired comparisons."""

    mission_enabled = False


class ComputerHard(ComputerOpponent):
    """Concentrates on key ground and can send a supported mobile desert flank."""

    level = "hard"
    road_weight = 4
    assignment_penalty = 8
    dig_limit = 4
    guard_objective = True
    tactical_enabled = False
    coordination_enabled = True
    limit_dump_discard = True

    FLANK_OFFSETS = ((-4, 3), (-3, 3), (-2, 3), (-4, 4), (-3, 4), (-2, 4),
                     (2, 3), (3, 3), (4, 3), (2, 4), (3, 4), (4, 4))

    def __init__(self, gmap):
        super().__init__(gmap)
        self.flank = None
        self.flank_used = False

    def to_save(self):
        return {"flank": self.flank, "flank_used": self.flank_used}

    def restore(self, data):
        self.flank = data.get("flank")
        self.flank_used = data.get("flank_used", False)

    def _flank_plan(self, view, formations):
        """Find one supply-supported desert approach using only known enemies and public goals."""
        if len(view["objectives"]) < 6 or view["turn"] > 2:
            return None                         # the five-turn battle is too short for a deep sweep
        side = view["side"]
        enemy = {tuple(u["hex"]) for u in view["enemy"]}
        parent_ids = {u["parent"] for u in view["units"] if u.get("parent")}
        headquarters = [u for lead, members in formations for u in members
                        if u["id"] == lead["id"] and u["type"] == "hq" and len(members) == 1
                        and u["id"] not in parent_ids and u["traced"] and not u["out_of_stores"]
                        and min(u["dump"].values()) >= 300 and u["fuel"] >= 12 * U.step_fuel(u)]
        if len(headquarters) < 2:               # keep another command HQ serving the main force
            return None
        goals = [o for o in view["objectives"] if view["places"].get(o["place"]) != side
                 and o["place"] in self.gmap.places]
        candidates = []
        anchors = self._mission_anchors(view, formations)
        for lead, members in formations:
            if lead["id"] in anchors:
                continue
            mobile = [u for u in members if u["type"] in ("armour", "motorised")]
            if not mobile or any(not u["traced"] or u["out_of_stores"] for u in members):
                continue
            if min(u["fuel"] // U.step_fuel(u) for u in members if U.is_vehicle(u)) < 14:
                continue
            here = tuple(lead["hex"])
            if any(distance(here, h) <= 2 for h in enemy):
                continue
            hq = min(headquarters, key=lambda u: (distance(here, tuple(u["hex"])), u["id"]))
            hq_here = tuple(hq["hex"])
            if distance(here, hq_here) > 3:
                continue
            dump_discard = sum(max(0, stock - HQ_CARRY) for stock in hq["dump"].values())
            mode = O.mode(members, "move", view["weather"])
            for goal in goals:
                # A moving HQ destroys most of a full dump. Do not pay that
                # price merely to raid a low-value objective.
                if self.limit_dump_discard and dump_discard > 2 * HQ_CARRY and goal.get("end", 0) < 20:
                    continue
                target = tuple(self.gmap.places[goal["place"]]["hex"])
                direct = self._route(here, target, members, "move", view["weather"])
                if direct is None or not 7 <= len(direct) <= 17:
                    continue
                value = goal.get("end", 0) + 3 * goal.get("turn", 0)
                if goal["place"] in ("Sidi Rezegh", "Belhamed"):
                    value *= 3
                for dx, dy in self.FLANK_OFFSETS:
                    waypoint = (target[0] + dx, target[1] + dy)
                    if not self.gmap.passable(waypoint):
                        continue
                    if min(distance(waypoint, h) for h in direct) < 3:
                        continue
                    route = self._route(here, waypoint, members, "move", view["weather"])
                    hq_route = self._route(hq_here, waypoint, [hq], "move", view["weather"])
                    if not route or not hq_route or not 6 <= len(route) <= 14 or len(hq_route) > 14:
                        continue
                    if sum(h not in self.gmap.on_route for h in route) < 4:
                        continue
                    if any(distance(h, foe) <= 2 for h in route + hq_route for foe in enemy):
                        continue
                    if target not in paths.haul_distances(self.gmap, waypoint, limit=REACH):
                        continue
                    score = value * 100 // (len(route) + 4) - len(hq_route) + min(distance(waypoint, h) for h in direct)
                    candidates.append((score, -lead["id"], -hq["id"], goal["place"], lead["id"], hq["id"], waypoint))
        if not candidates:
            return None
        _, _, _, name, lead_id, hq_id, waypoint = max(candidates)
        origin = next(u["hex"] for u in view["units"] if u["id"] == hq_id)
        lead_origin = next(u["hex"] for u in view["units"] if u["id"] == lead_id)
        return {"lead": lead_id, "hq": hq_id, "goal": name, "waypoint": list(waypoint),
                "origin": origin, "lead_origin": lead_origin, "started": view["turn"], "phase": "approach"}

    def _tactical_orders(self, view, given, formations):
        """Reject clearly poor adjacent attacks using visible defenders and own stores."""
        if self.coordination_enabled:
            from .coordinated import coordinate
            protected = set((self.flank["lead"], self.flank["hq"])) if self.flank else set()
            protected |= self._mission_anchors(view, formations)
            given = coordinate(self.gmap, view, given, formations, protected)
        if not self.tactical_enabled:
            return given
        by_id = {lead["id"]: (lead, members) for lead, members in formations}
        defenders = {}
        for enemy in view["enemy"]:
            defenders.setdefault(tuple(enemy["hex"]), []).append(enemy)
        attacks = {}
        for order in given["orders"]:
            if order["order"] != "attack" or order["unit"] not in by_id:
                continue
            target = tuple(order["to"])
            lead, members = by_id[order["unit"]]
            if target in defenders and distance(tuple(lead["hex"]), target) == 1:
                attacks.setdefault(target, []).append((order, lead, members))
        for target, entries in attacks.items():
            groups = [(lead, members) for _, lead, members in entries]
            ratio = tactics.odds(self.gmap, view, groups, defenders[target], target)
            if ratio >= 0.8 and tactics.stores_safe(groups):
                continue
            for order, lead, members in entries:
                retreat = tactics.retreat_hex(self.gmap, view, lead, members) if ratio < 0.5 else None
                if retreat is not None:
                    order.update(order="move", to=list(retreat))
                else:
                    order.clear()
                    order.update(unit=lead["id"], order="hold")
        # Support also strengthens defence; retain the original air choice
        # when a ground attack is cancelled after the air plan was made.
        return given

    def orders(self, view):
        from .players import parties

        given = super().orders(view)
        formations = parties(view)
        if self.flank is None and not self.flank_used:
            self.flank = self._flank_plan(view, formations)
            self.flank_used = self.flank is not None
        plan = self.flank
        if plan is None:
            return self._tactical_orders(view, given, formations)
        by_id = {lead["id"]: (lead, members) for lead, members in formations}
        lead, members = by_id.get(plan["lead"], (None, []))
        hq = by_id.get(plan["hq"], (None, []))[0]
        target = tuple(self.gmap.places[plan["goal"]]["hex"])
        waypoint = tuple(plan["waypoint"])
        if hq is None:
            self.flank = None
            return self._tactical_orders(view, given, formations)
        if plan["phase"] == "approach" and view["places"].get(plan["goal"]) == view["side"]:
            plan["phase"] = "withdraw"
        if (lead is None or view["turn"] - plan["started"] > 6
                or any(not u["traced"] or u["out_of_stores"] for u in members + [hq])
                or any(U.is_vehicle(u) and u["fuel"] < 2 * U.step_fuel(u) for u in members + [hq])
                or any(distance(tuple(hq["hex"]), tuple(foe["hex"])) <= 1 for foe in view["enemy"])
                or (plan["phase"] == "approach" and lead is not None
                    and any(distance(tuple(lead["hex"]), tuple(foe["hex"])) <= 1 for foe in view["enemy"]))):
            plan["phase"] = "return"
        if plan["phase"] == "withdraw" and distance(tuple(lead["hex"]), waypoint) <= 1:
            plan["phase"] = "return"
        chosen = {order["unit"]: order for order in given["orders"]}
        if plan["phase"] == "withdraw":
            chosen[lead["id"]] = {"unit": lead["id"], "order": "move", "to": list(waypoint)}
            chosen[hq["id"]] = {"unit": hq["id"], "order": "hold"}
            given["orders"] = [chosen[order["unit"]] for order in given["orders"]]
            return self._tactical_orders(view, given, formations)
        if plan["phase"] == "return":
            here = tuple(hq["hex"])
            lead_home = lead is None or distance(tuple(lead["hex"]), tuple(plan["lead_origin"])) <= 1
            hq_home = distance(here, tuple(plan["origin"])) <= 1
            if lead_home and hq_home:
                self.flank = None
                return self._tactical_orders(view, given, formations)
            if not hq_home:
                to = self._destination(here, tuple(plan["origin"]), [hq], view["weather"], "move")
                chosen[hq["id"]] = ({"unit": hq["id"], "order": "move", "to": list(to)} if to else
                                    {"unit": hq["id"], "order": "hold"})
            if lead is not None and not lead_home:
                to = self._destination(tuple(lead["hex"]), tuple(plan["lead_origin"]), members, view["weather"], "move")
                chosen[lead["id"]] = ({"unit": lead["id"], "order": "move", "to": list(to)} if to else
                                      {"unit": lead["id"], "order": "hold"})
            given["orders"] = [chosen[order["unit"]] for order in given["orders"]]
            return self._tactical_orders(view, given, formations)
        near = distance(tuple(lead["hex"]), waypoint) <= 1
        hq_near = distance(tuple(hq["hex"]), waypoint) <= 1
        if near and hq_near:
            chosen[lead["id"]] = {"unit": lead["id"], "order": "attack", "to": list(target)}
            chosen[hq["id"]] = {"unit": hq["id"], "order": "hold"}
        else:
            chosen[lead["id"]] = ({"unit": lead["id"], "order": "hold"} if near else
                                  {"unit": lead["id"], "order": "move", "to": list(waypoint)})
            chosen[hq["id"]] = ({"unit": hq["id"], "order": "hold"} if hq_near else
                                {"unit": hq["id"], "order": "move", "to": list(waypoint)})
        given["orders"] = [chosen[order["unit"]] for order in given["orders"]]
        given["air"] = "support" if any(order["order"] == "attack" for order in given["orders"]) else given["air"]
        return self._tactical_orders(view, given, formations)


class ComputerHardBaseline(ComputerHard):
    """Hard before coordinated attack planning, retained for paired benchmarks."""

    tactical_enabled = False
    coordination_enabled = False


class ComputerHardPoints(ComputerHard):
    """Previous point-only Hard planner for paired mission comparisons."""

    mission_enabled = False


class ComputerHardTactical(ComputerHard):
    """Experimental attack filter; benchmark evidence does not support release yet."""

    tactical_enabled = True
    coordination_enabled = False


class ComputerHardCoordinated(ComputerHard):
    """Explicit alias for the playable coordinated Hard policy in benchmarks."""

    coordination_enabled = True


class ComputerHardUnrestrictedFlank(ComputerHardBaseline):
    """The previous Hard raid policy, before moving-HQ dump cost was considered."""

    limit_dump_discard = False


class ComputerHardBeforeFlank(ComputerHardBaseline):
    """The Hard policy before the one-off desert raid was added."""

    def _flank_plan(self, view, formations):
        return None
