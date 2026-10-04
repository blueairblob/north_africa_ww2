"""Players: shown their side's view, they return orders (DESIGN.md §13).
These scripted ones are for testing the rules, not for playing well."""
from .gamemap import distance
from .orders import ORDERS


def parties(view):
    """The side's units as they are ordered: each group under its leader, and each unit that is
    in no group, as (leader, members) (RULES 20.2.5)."""
    on_map = [u for u in view["units"] if u["status"] == "on_map"]
    return [(u, [m for m in on_map if m["id"] == u["id"] or (u["group"] is not None and m["group"] == u["group"])])
            for u in on_map if u["group"] in (None, u["id"])]


class DoNothing:
    """Gives no orders: every unit holds."""
    def __init__(self, gmap):
        self.gmap = gmap

    def orders(self, view):
        return {"orders": [], "air": "support"}


class AlwaysAttack(DoNothing):
    """Every unit or group that can fight attacks towards the nearest enemy it can see, or the
    enemy's base; one too shaken to attack rests."""
    def orders(self, view):
        foe_base = self.gmap.base["cw" if view["side"] == "axis" else "axis"]
        out = []
        for lead, members in parties(view):
            fighters = [m for m in members if m["type"] != "hq"]
            if not fighters:
                continue                                             # a headquarters by itself holds
            here = tuple(lead["hex"])
            seen = sorted((distance(here, tuple(e["hex"])), tuple(e["hex"])) for e in view["enemy"])
            to = seen[0][1] if seen else foe_base
            fit = any(m["cohesion"] >= 40 for m in fighters)
            out.append({"unit": lead["id"], "order": "attack", "to": list(to)} if fit and to != here
                       else {"unit": lead["id"], "order": "rest"})
        return {"orders": out, "air": "support"}


class AlwaysRetreat(DoNothing):
    """Every unit or group marches for its own base."""
    def orders(self, view):
        base = self.gmap.base[view["side"]]
        return {"orders": [{"unit": lead["id"], "order": "move", "to": list(base)} for lead, _ in parties(view)
                           if tuple(lead["hex"]) != base], "air": "recon"}


class Explore(DoNothing):
    """Tries everything in turn, sensible or not, legal or not: every order, near and far
    destinations, the sea, off the map, units that are not its own, units inside groups, joins
    and splits, orders that are not orders."""
    def orders(self, view):
        g, turn, out = self.gmap, view["turn"], []
        ids = [u["id"] for u in view["units"]] + [e["id"] for e in view["enemy"]] + [-1]
        for n, uid in enumerate(ids):
            k = (turn * 7 + uid * 3 + n) % 15
            here = next((tuple(u["hex"]) for u in view["units"] if u["id"] == uid and u["hex"]), (60, 15))
            far = g.base["cw" if (turn + uid) % 2 else "axis"]
            spots = [far, (here[0] + k % 5 - 2, here[1] + k % 3 - 1), here, (0, 0), (g.cols + 3, 2),
                     tuple(view["enemy"][0]["hex"]) if view["enemy"] else far]
            to = list(spots[(turn + uid + n) % len(spots)])
            if k < 6:
                order = {"unit": uid, "order": ORDERS[k]}
                if ORDERS[k] in ("move", "attack", "road_march") or (turn + uid) % 5 == 0:
                    order["to"] = to
                if k % 2 and (turn + uid) % 3 == 0:
                    order["via"] = [list(spots[1]), list(far)][: 1 + turn % 2] * (1 + 4 * (uid % 7 == 0))
            elif k < 9:
                order = {"unit": uid, "order": ("move", "attack", "road_march")[k - 6], "to": to}
            elif k == 9:
                order = {"unit": uid, "order": "charge"}
            elif k == 10:
                order = {"unit": uid, "order": "move"}
            elif k == 11:
                order = "nonsense" if uid % 2 else {"unit": str(uid), "order": "hold"}
            elif k == 12:                                           # join whoever comes next in the list, friend or foe
                order = {"unit": uid, "order": "join", "with": ids[(n + 1 + turn) % len(ids)]}
            elif k == 13:                                           # split off, and go somewhere
                order = {"unit": uid, "order": "move", "to": to, "alone": True}
            else:
                order = {"unit": uid, "order": "hold", "alone": True}
            out.append(order)
            if k == 3:
                out.append({"unit": uid, "order": "hold"})          # a second order for the same unit
        return {"orders": out, "air": ("support", "interdict", "recon", "bombs")[turn % 4]}


class Recorded:
    """Plays back the orders of an earlier game, turn by turn."""
    def __init__(self, submissions):
        self.submissions = list(submissions)

    def orders(self, view):
        return self.submissions[view["turn"] - 1]


SCRIPTED = {"nothing": DoNothing, "attack": AlwaysAttack, "retreat": AlwaysRetreat, "explore": Explore}
