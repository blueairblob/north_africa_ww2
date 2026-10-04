"""A game in progress at the screen: whose turn it is to give orders, the orders given so far,
and the step from one turn to the next. No pygame here.

Orders stand. An order given once is given again every turn until the unit arrives, the
order can no longer be carried out, or an attack fails to drive the defenders back; then the
unit waits for a new one. The engine still
receives one order per unit per turn (docs/RULES.md 8.1.4)."""
from datetime import date, timedelta

from engine import orders as O
from engine import paths
from engine import state as S
from engine import units as U
from engine.movement import ALLOWANCE, IMPULSES
from engine.turn import begin_turn, finish_turn
from engine.view import view


# why a standing order ended, to follow the unit's name: "15. Panzer-Division has arrived"
ENDED = {"E_SAME_HEX": "has arrived", "E_COHESION": "is too disorganised to attack",
         "E_IMPASSABLE": "cannot enter that ground", "E_NO_PATH": "has no way there",
         "E_NOT_ON_ROUTE": "is no longer on a road or track"}


class Session:
    def __init__(self, scenario, gmap, humans=S.SIDES, scripted=None):
        self.scenario, self.gmap = scenario, gmap
        self.humans = [s for s in S.SIDES if s in humans]
        self.scripted = scripted or {}
        self.nation = {u["id"]: u.get("nation", "cw" if u["side"] == "cw" else "de") for u in scenario["units"]}
        self.state = S.new_game(scenario, gmap)
        self.record, self.replies = [], {}
        self.before, self.watched = None, set()         # last turn's views, and who has watched it
        self.standing = {s: {} for s in S.SIDES}        # the orders that stand from turn to turn
        self.ended = {s: [] for s in S.SIDES}           # (unit id, why) for orders that ended this turn
        self._begin()

    def _begin(self):
        """The Supply phase, then both sides are shown their views (RULES 5.2)."""
        if not self.state["over"]:
            self.state = begin_turn(self.state, self.gmap, self.scenario)
        self.views = {s: view(self.state, self.gmap, self.scenario, s) for s in S.SIDES}
        self.pending = {s: {} for s in S.SIDES}
        for s in S.SIDES:                               # standing orders are given again, if still legal
            self.ended[s] = []
            repulsed = {uid for e in self.views[s]["events"] if e["event"] == "battle" and not e["retreated"]
                        for uid in e["attackers"]}      # attacked, and the defenders did not fall back
            for uid, order in sorted(self.standing[s].items()):
                code = O.check_one(self.state, self.gmap, s, order, {})
                if order["order"] == "attack" and uid in repulsed and code != "E_NOT_ON_MAP":
                    del self.standing[s][uid]           # to attack again is a new decision
                    self.ended[s].append((uid, "was repulsed"))
                elif code is None:
                    self.pending[s][uid] = order
                else:
                    del self.standing[s][uid]
                    if code != "E_NOT_ON_MAP":
                        self.ended[s].append((uid, ENDED.get(code, "cannot carry out its order")))
        self.air = {s: self.state["sides"][s]["air"] for s in S.SIDES}
        self.waiting = [] if self.state["over"] else list(self.humans)

    @property
    def side(self):
        """The side now giving orders; when the game is over, the first human side looks on."""
        return self.waiting[0] if self.waiting else (self.humans or list(S.SIDES))[0]

    @property
    def view(self):
        return self.views[self.side]

    @property
    def day(self):
        start = date.fromisoformat(self.scenario["start"])
        return start + timedelta(days=2 * (self.state["turn"] - 1))

    def unit(self, uid):
        return next((u for u in self.view["units"] if u["id"] == uid and u["status"] == "on_map"), None)

    def order_of(self, uid):
        return self.pending[self.side].get(uid, {"unit": uid, "order": "hold"})

    def leader(self, uid):
        """The unit to order for this one: its group's leader, or itself (RULES 20.2.5)."""
        u = self.unit(uid)
        return uid if u is None or u["group"] is None else u["group"]

    def members(self, uid):
        """The units ordered with this one: its group, or itself alone."""
        u = self.unit(uid)
        return [] if u is None else [m for m in self.view["units"] if m["status"] == "on_map" and
                                     (m["id"] == uid or (u["group"] is not None and m["group"] == u["group"]))]

    def give(self, order):
        """Give or replace a unit's order; an order for a unit in a group is its group's, unless
        it is marked alone. Returns the engine's reply (RULES 8.5)."""
        if not order.get("alone") and isinstance(order.get("unit"), int):
            order = dict(order, unit=self.leader(order["unit"]))
        code = O.check_one(self.state, self.gmap, self.side, order, {})
        if code:
            return {"ok": False, "code": code, "text": O.REPLIES[code]}
        self.pending[self.side][order["unit"]] = order
        self.standing[self.side][order["unit"]] = order
        return {"ok": True}

    def waiting_units(self):
        """The side's units that have no order yet, in the order the screen steps through them."""
        return [u["id"] for u in self.view["units"] if u["status"] == "on_map" and u["id"] not in self.pending[self.side]
                and u["group"] in (None, u["id"])]               # a group waits as one, under its leader

    def turns_to_go(self, uid):
        """How many turns a unit's standing order will take, or None."""
        order = self.pending[self.side].get(uid, {})
        p = self.preview(uid, order["order"], order["to"]) if "to" in order else None
        return -(-len(p["path"]) // p["reach"]) if p and p["reach"] else None

    def preview(self, uid, name, to):
        """The way a unit would go under this order: the hexes, how many it reaches this turn,
        and the MP and fuel for those. None if the order would be rejected."""
        uid = self.leader(uid)
        order = {"unit": uid, "order": name, "to": list(to)}
        u = self.unit(uid)
        if u is None or O.check_one(self.state, self.gmap, self.side, order, {}):
            return None
        group = self.members(uid)
        way = O.full_path(self.gmap, u, order, self.state)
        here, mp, reach = tuple(u["hex"]), 0, 0
        for nxt in way[:IMPULSES]:
            cost = paths.step_cost(self.gmap, here, nxt, self.gmap.side_between(here, nxt), O.mode(group, name))
            if mp + cost > min(ALLOWANCE[m["type"]] for m in group):         # a group goes at its slowest pace
                break
            mp, reach, here = mp + cost, reach + 1, nxt
        wheels = [m for m in group if U.is_vehicle(m)]
        fuel = reach * sum(U.step_fuel(m) for m in wheels)
        return {"path": way, "reach": reach, "mp": mp, "fuel": fuel,
                "enough_fuel": all(reach * U.step_fuel(m) <= m["fuel"] for m in wheels),
                "range": min(m["fuel"] // U.step_fuel(m) for m in wheels) if wheels else None}   # hexes its fuel allows

    def playback(self, span=None):
        """The last turn as this side saw it, once (screen/replay.py); None if there is none.
        span is the columns and rows of hexes the screen has in view."""
        from .replay import Playback
        if self.before is None or self.side in self.watched:
            return None
        self.watched.add(self.side)
        play = Playback(self.before[self.side], self.view, span)
        return play if play.length else None

    def set_air(self, choice):
        if choice in O.AIR:
            self.air[self.side] = choice

    def done(self):
        """This side has given its orders. Returns "pass" if another player is still to give
        orders, "turn" if the turn was played, "over" if the game has ended."""
        self.waiting.pop(0)
        if self.waiting:
            return "pass"
        submissions = {s: {"orders": list(self.pending[s].values()), "air": self.air[s]} for s in self.humans}
        for s, player in self.scripted.items():
            submissions[s] = player.orders(self.views[s])
        self.record.append(submissions)
        self.before = dict(self.views)                   # what each side saw as it gave its orders
        self.watched = set()
        self.state, self.replies = finish_turn(self.state, self.gmap, self.scenario, submissions)
        self._begin()
        return "over" if self.state["over"] else "turn"
