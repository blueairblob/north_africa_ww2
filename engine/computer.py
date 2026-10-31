"""A deterministic opponent using only the view given to a human player.

The plan comes from the public scenario objectives. Formations choose a sector,
then an order; no enemy strength, position or supply outside the view is read.
"""
from . import orders as O
from . import paths
from . import tactics
from . import units as U
from .board import HQ_CARRY
from .gamemap import distance
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

    def __init__(self, gmap):
        self.gmap = gmap

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
        return out

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
        return paths.least_path(self.gmap, here, target, mode)

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

    def orders(self, view):
        from .players import parties

        side = view["side"]
        goals = self._objectives(view)
        foes = sorted((tuple(e["hex"]), e["id"]) for e in view["enemy"])
        formations = sorted(parties(view), key=lambda party: party[0]["id"])
        occupied = {}
        for lead, _ in formations:
            h = tuple(lead["hex"])
            occupied[h] = occupied.get(h, 0) + 1
        assigned, orders = {}, []
        for lead, members in formations:
            here = tuple(lead["hex"])
            fighters = [m for m in members if m["type"] != "hq"]
            fighting = bool(fighters) and any(m["cohesion"] >= O.ATTACK_MIN for m in fighters)
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
            if self.guard_objective and threat and any(
                    tuple(self.gmap.places[obj["place"]]["hex"]) == here and obj.get("end", 0) >= 20
                    and view["places"].get(obj["place"]) == side for obj in view["objectives"]):
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
            # A visible nearby enemy calls for an attack. Headquarters alone
            # avoid combat and move only towards their assigned sector.
            if fighting and threat:
                target, action = nearest[0], "attack"
            elif goal and view["places"].get(goal[0]) != side and fighting:
                action = "attack"
            else:
                action = "move"
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
            # An unthreatened long road leg is worth taking, but only for
            # vehicles with fuel. The path checker enforces roads throughout.
            if self.use_road_march and action == "move" and not threat and distance(here, target) > 5 and fuel_hexes >= 6 \
                    and here in self.gmap.on_route and target in self.gmap.on_route \
                    and self._route(here, target, members, "road_march", view["weather"]) is not None:
                action = "road_march"
            orders.append({"unit": lead["id"], "order": action, "to": list(target)})
            occupied[target] = occupied.get(target, 0) + 1

        attacks = any(order["order"] == "attack" for order in orders)
        air = "support" if attacks else "interdict" if foes and self.use_interdict else "recon"
        return {"orders": orders, "air": air}


class ComputerEasy(ComputerOpponent):
    """Shorter planning horizon, less digging and fewer long road marches."""

    level = "easy"
    threat_range = 2
    rest_below = 60
    dig_limit = 1
    use_road_march = False
    use_interdict = False


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
        for lead, members in formations:
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
                direct = paths.least_path(self.gmap, here, target, mode)
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
                    route = paths.least_path(self.gmap, here, waypoint, mode)
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
            protected = (self.flank["lead"], self.flank["hq"]) if self.flank else ()
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
