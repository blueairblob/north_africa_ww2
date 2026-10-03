"""Players: shown their side's view, they return orders (DESIGN.md §13).
These scripted ones are for testing the rules, not for playing well."""
from .gamemap import distance
from .orders import ORDERS


class DoNothing:
    """Gives no orders: every unit holds."""
    def __init__(self, gmap):
        self.gmap = gmap

    def orders(self, view):
        return {"orders": [], "air": "support"}


class AlwaysAttack(DoNothing):
    """Every fighting unit attacks towards the nearest enemy it can see, or the enemy's base."""
    def orders(self, view):
        foe_base = self.gmap.base["cw" if view["side"] == "axis" else "axis"]
        out = []
        for u in view["units"]:
            if u["status"] != "on_map" or u["type"] == "hq":
                continue
            here = tuple(u["hex"])
            seen = sorted((distance(here, tuple(e["hex"])), tuple(e["hex"])) for e in view["enemy"])
            to = seen[0][1] if seen else foe_base
            name = "attack" if u["cohesion"] >= 40 else "rest"
            out.append({"unit": u["id"], "order": name, "to": list(to)} if name == "attack" and to != here
                       else {"unit": u["id"], "order": "rest"})
        return {"orders": out, "air": "support"}


class AlwaysRetreat(DoNothing):
    """Every unit marches for its own base."""
    def orders(self, view):
        base = self.gmap.base[view["side"]]
        return {"orders": [{"unit": u["id"], "order": "move", "to": list(base)} for u in view["units"]
                           if u["status"] == "on_map" and tuple(u["hex"]) != base], "air": "recon"}


class Explore(DoNothing):
    """Tries everything in turn, sensible or not, legal or not: every order, near and far
    destinations, the sea, off the map, units that are not its own, orders that are not orders."""
    def orders(self, view):
        g, turn, out = self.gmap, view["turn"], []
        ids = [u["id"] for u in view["units"]] + [e["id"] for e in view["enemy"]] + [-1]
        for n, uid in enumerate(ids):
            k = (turn * 7 + uid * 3 + n) % 12
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
            else:
                order = "nonsense" if uid % 2 else {"unit": str(uid), "order": "hold"}
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
