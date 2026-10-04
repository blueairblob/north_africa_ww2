"""A game in progress at the screen: whose turn it is to give orders, the orders given so far,
and the step from one turn to the next. No pygame here.

Orders stand. An order given once is given again every turn until the unit arrives, the
order can no longer be carried out, or an attack fails to drive the defenders back; then the
unit waits for a new one. The engine still
receives one order per unit per turn (docs/RULES.md 8.1.4)."""
from datetime import date, timedelta

from engine import board as B
from engine import orders as O
from engine import paths
from engine import state as S
from engine import units as U
from engine.movement import ALLOWANCE, IMPULSES
from engine.turn import begin_turn, finish_turn
from engine.view import view


# why a standing order ended, to follow the unit's name: "15. Panzer-Division has arrived"
ENDED = {"E_SAME_HEX": "has arrived", "E_COHESION": "is too disorganised to attack", "E_JOIN": "has joined",
         "E_IMPASSABLE": "cannot enter that ground", "E_NO_PATH": "has no way there",
         "E_NOT_ON_ROUTE": "is no longer on a road or track", "E_HQ": "has no fighting units with it"}


def where(gmap, h):
    """A hex in words: "at Tobruk", or "near Sidi Rezegh" for the nearest named place."""
    name, p = min(gmap.places.items(), key=lambda kv: (S.distance(tuple(h), kv[1]["hex"]), kv[0]))
    return f"at {name}" if p["hex"] == tuple(h) else f"near {name}"


ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
HEAVY_PCT = 25          # a unit that lost this share of its strength in a turn "took heavy losses"


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
        self.split = {s: set() for s in S.SIDES}        # units split off this turn, shown at once
        self.names = {}                                 # names the player has given, by leader's id
        self.ended = {s: [] for s in S.SIDES}           # (unit id, why) for orders that ended this turn
        self._begin()

    def _begin(self):
        """The Supply phase, then both sides are shown their views (RULES 5.2)."""
        if not self.state["over"]:
            self.state = begin_turn(self.state, self.gmap, self.scenario)
        self.views = {s: view(self.state, self.gmap, self.scenario, s) for s in S.SIDES}
        self.pending = {s: {} for s in S.SIDES}
        self.split = {s: set() for s in S.SIDES}
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
                    if order["order"] == "join" and code in ("E_JOIN", "E_GROUPED"):
                        self.ended[s].append((uid, "has joined"))
                    elif code not in ("E_NOT_ON_MAP", "E_GROUPED"):      # a unit now led by another needs no word
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
        it is marked alone. Returns the engine's reply (RULES 8.5).

        Splitting a unit off, and joining units already in one hex, show at once: the rules do
        them in the Orders phase, before anything moves (20.2.2, 20.2.4), so doing them now on
        the screen changes nothing in the game. The orders are still recorded as given, so the
        game replays the same from its record."""
        if not order.get("alone") and isinstance(order.get("unit"), int):
            order = dict(order, unit=self.leader(order["unit"]))
        if order.get("unit") in self.split[self.side]:           # split off this turn: its orders stay its own
            order = dict(order, alone=True)
        if order.get("order") == "join" and self.unit(order.get("unit")) and self.unit(order.get("with")) \
                and self.unit(order["unit"])["hex"] == self.unit(order["with"])["hex"]:
            a, b = self.leader(order["unit"]), self.leader(order["with"])
            if a < b:                                            # the higher id joins the lower, which will lead
                order = dict(order, unit=b)
                order["with"] = a
        code = O.check_one(self.state, self.gmap, self.side, order, {})
        if code:
            return {"ok": False, "code": code, "text": O.REPLIES[code]}
        self.pending[self.side][order["unit"]] = order
        self.standing[self.side][order["unit"]] = order
        self._now(order)
        return {"ok": True}

    def _now(self, order):
        """Show at once the grouping an order does in the Orders phase."""
        u, changed = S.unit(self.state, order["unit"]), False
        if order.get("alone") and u["group"] is not None:
            u["group"] = None
            self.split[self.side].add(u["id"])
            changed = True
        if order["order"] == "join":
            other = S.unit(self.state, order["with"])
            if other["hex"] == u["hex"]:
                B.join(self.state, u, other)
                changed = True
        if changed:
            B.regroup(self.state)
            self.views = {s: view(self.state, self.gmap, self.scenario, s) for s in S.SIDES}

    def rename(self, uid, name):
        """Give a group, or a unit, a name of the player's own; an empty name takes it back."""
        key = self.leader(uid)
        if name.strip():
            self.names[key] = name.strip()[:28]
        else:
            self.names.pop(key, None)

    def related_at(self, uid, h):
        """A unit of yours in this hex that uid could join, or None (RULES 20.2.2)."""
        u = self.unit(uid)
        mine = {m["id"] for m in self.members(uid)}
        for m in self.view["units"]:
            if u and m["status"] == "on_map" and tuple(m["hex"]) == tuple(h) and m["id"] not in mine:
                return m["id"]
        return None

    def parties_at(self, h):
        """The leaders of your groups and single units in a hex."""
        return sorted({self.leader(u["id"]) for u in self.view["units"] if u["status"] == "on_map" and tuple(u["hex"]) == tuple(h)})

    def group_all(self, h):
        """Everything of yours in this hex becomes one group, when the turn is played
        (RULES 20.2.2: joined at once, in the Orders phase). Returns how many joined."""
        leads = self.parties_at(h)
        return sum(self.give({"unit": lead, "order": "join", "with": leads[0]})["ok"] for lead in leads[1:])

    def split_up(self, uid):
        """A group breaks up into its units, when the turn is played (RULES 20.2.4)."""
        lead = self.leader(uid)
        return sum(self.give({"unit": m["id"], "order": "hold", "alone": True})["ok"]
                   for m in self.members(lead) if m["id"] != lead)

    def group_name(self, uid):
        """What to call a unit or its group: a division by its HQ; a force made up of units of
        more than one formation "Special Army I", "II" and so on, in the order of their leaders."""
        u = self.unit(uid)
        group = self.members(uid)
        if u and self.leader(uid) in self.names:
            return self.names[self.leader(uid)]
        if u is None or len(group) < 2:
            return u["name"] if u else ""
        if len({U.formation(m) for m in group}) > 1:
            mixed = sorted({self.leader(m["id"]) for m in self.view["units"] if m["status"] == "on_map" and m["group"] is not None
                            and len({U.formation(x) for x in self.members(m["id"])}) > 1})
            return "Special Army Group " + ROMAN[min(mixed.index(self.leader(uid)), len(ROMAN) - 1)]
        return next((m for m in group if m["type"] == "hq"), u)["name"]

    def recall(self, uid):
        """An HQ calls its division in: every related unit not with it is ordered to join it
        (RULES 20.2.9). Returns how many orders were given, or None if this is no division's HQ."""
        strays = self.strays(uid)
        if strays is None:
            return None
        hq = next(m for m in self.members(self.leader(uid)) if m["type"] == "hq")
        return sum(self.give({"unit": i, "order": "join", "with": hq["id"]})["ok"] for i in strays)

    def cancel(self, uid):
        """Take back a unit's order: it waits again, and holds if given none (RULES 8.1.3)."""
        lead = self.leader(uid)
        gone = self.pending[self.side].pop(lead, None)
        self.standing[self.side].pop(lead, None)
        return gone is not None

    def strays(self, uid):
        """The leaders of the units of this HQ's division that are not with it; None if uid is not
        with a division's HQ."""
        u = self.unit(self.leader(uid)) if self.unit(uid) else None
        hq = next((m for m in self.members(u["id"]) if m["type"] == "hq"), None) if u else None
        if hq is None or not any(m.get("parent") == hq["id"] for m in self.view["units"]):
            return None
        with_hq = {m["id"] for m in self.members(hq["id"])}
        return [m["id"] for m in self.view["units"] if m["status"] == "on_map" and m.get("parent") == hq["id"]
                and m["id"] not in with_hq and m["group"] in (None, m["id"])]

    def can(self, uid, name, alone=False):
        """Whether the unit taken up could be given this order now, and if not, why: the words
        for a disabled button."""
        u = self.unit(uid)
        if u is None:
            return False, "Choose one of your units first."
        group = [u] if alone else self.members(uid)
        fighters = [m for m in group if m["type"] != "hq"]
        if name == "road_march" and tuple(u["hex"]) not in self.gmap.on_route:
            return False, "It is not on a road or track: one cannot march in the desert."
        if name == "attack":
            if not fighters:
                return False, "A headquarters does not attack."
            if all(m["cohesion"] < O.ATTACK_MIN for m in fighters):
                return False, "Its morale is too low to attack."
            reach = min(ALLOWANCE[m["type"]] for m in group) // 4 + 1
            if not any(S.distance(tuple(u["hex"]), tuple(e["hex"])) <= reach for e in self.view["enemy"]):
                return False, "No enemy in sight within its reach."
        if name == "dig_in" and not fighters:
            return False, "A headquarters does not dig in."
        if name == "join" and not any(m["status"] == "on_map" and m["id"] not in {g["id"] for g in group}
                                      for m in self.view["units"]):
            return False, "There is no other unit of yours to join."
        if name == "split" and len(self.members(uid)) < 2:
            return False, "It is not in a group."
        if name == "recall" and not self.strays(uid):
            return False, "Only a division's HQ with units away from it can recall."
        return True, ""

    def order_at(self, h):
        """The unit whose ordered way passes through this hex, if any: to find it by its line."""
        for uid, order in sorted(self.pending[self.side].items()):
            p = self.preview(uid, order["order"], order["to"]) if "to" in order else None
            if p and tuple(h) in [tuple(x) for x in p["path"]]:
                return uid
        return None

    def lost_words(self, u, steps):
        """Steps lost, in real terms: "about 20 tanks"."""
        if u.get("real"):
            n, what, began = u["real"]
            return f"about {n * steps // began:,} {'armoured cars' if what == 'cars' else what}"
        return {"armour": f"about {steps * 10} tanks", "guns": f"about {steps * 12} guns",
                "recon": f"about {steps * 15} armoured cars"}.get(u["type"], f"about {steps * 800:,} men")

    def reports(self):
        """What the general is told: at most one thing for each unit or group, and only what
        matters. In order of weight: destroyed, driven back, heavy losses, repulsed, the enemy
        driven back, supply lost, out of fuel, morale low, under half strength, enemy in contact.
        [(words, unit id)]"""
        view, out = self.view, []
        mine = {u["id"]: u for u in view["units"]}
        battles = [e for e in view["events"] if e["event"] == "battle"]
        stopped = {e["unit"]: e["why"] for e in view["events"] if e["event"] == "stopped"}
        repulsed = {uid for uid, why in self.ended[self.side] if why == "was repulsed"}
        for e in view["events"]:                              # those no longer on the map
            if e["event"] == "destroyed" and e["unit"] in mine:
                how = {"starved": "starved and is lost", "surrendered": "was surrounded and surrendered"}.get(e["cause"], "was destroyed")
                out.append((f"{mine[e['unit']]['name']} {how}.", e["unit"]))
        for lead in sorted({self.leader(u["id"]) for u in view["units"] if u["status"] == "on_map"}):
            group = self.members(lead)
            ids = {m["id"] for m in group}
            name = self.group_name(lead)
            fought = [b for b in battles if ids & set(b["attackers"] + b["defenders"])]
            lost = {m["id"]: sum(b["lost"].get(str(m["id"]), 0) for b in fought) for m in group}
            worst = max(group, key=lambda m: lost[m["id"]] * 100 // (m["steps"] + lost[m["id"]]))
            heavy = lost[worst["id"]] * 100 // (worst["steps"] + lost[worst["id"]]) >= HEAVY_PCT
            fell = next((b for b in fought if b["retreated"] and ids & set(b["defenders"])), None)
            won = next((b for b in fought if b["retreated"] and ids & set(b["attackers"])), None)
            weak = [m for m in group if m["type"] != "hq" and m.get("real") and m["steps"] * 2 < m["real"][2]]
            if fell:
                words = f"{name} was driven back {where(self.gmap, fell['hex'])}."
            elif heavy:
                words = f"{name} took heavy losses: {self.lost_words(worst, lost[worst['id']])}."
            elif ids & repulsed:
                words = f"{name} attacked and was repulsed."
            elif won:
                words = f"{name} drove the enemy back {where(self.gmap, won['hex'])}."
            elif any(not m["traced"] or m["out_of_stores"] for m in group):
                words = f"{name} has lost its supply."
            elif any(U.is_vehicle(m) and m["fuel"] < U.step_fuel(m) for m in group):
                words = f"{name} is out of fuel."
            elif any(m["type"] != "hq" and m["cohesion"] < O.ATTACK_MIN for m in group):
                words = f"{name}: morale is low. It cannot attack."
            elif weak:
                words = f"{name} is under half strength and needs reinforcing."
            elif any(stopped.get(i) == "contact" for i in ids):
                words = f"{name}: enemy in contact."
            else:
                continue
            out.append((words, lead))
        return out

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
        play = Playback(self.before[self.side], self.view, span, self.gmap)
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
