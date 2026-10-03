"""The six orders: when each is legal and the reply when it is not (docs/RULES.md §8)."""
from . import paths
from . import state as S
from . import units as U

ORDERS = ("move", "attack", "hold", "dig_in", "road_march", "rest")
MOVING = ("move", "attack", "road_march")
AIR = ("support", "interdict", "recon")
VIA_MAX = 4             # points on the way in one order
ATTACK_MIN = 40         # least cohesion to be given, or to carry out, an attack

REPLIES = {
    "E_ORDER": "That is not one of the six orders.",
    "E_UNIT": "There is no such unit.",
    "E_NOT_YOURS": "That unit is not yours.",
    "E_NOT_ON_MAP": "That unit is not on the map.",
    "E_DUPLICATE": "That unit already has an order this turn.",
    "E_DEST": "That order takes no destination.",
    "E_NO_DEST": "That order needs a destination.",
    "E_OFF_MAP": "The destination is off the map.",
    "E_VIA": "Too many points on the way.",
    "E_SAME_HEX": "The unit is already there.",
    "E_IMPASSABLE": "The unit cannot enter that ground.",
    "E_NO_PATH": "There is no way there for this unit.",
    "E_HQ": "A headquarters cannot do that.",
    "E_COHESION": "The unit is too disorganised to attack.",
    "E_FOOT": "Foot infantry cannot road march.",
    "E_NOT_ON_ROUTE": "A road march must start, pass and end on a road or track.",
    "E_AIR": "That is not an air mission; support is flown.",
}


def mode(u, name):
    """How the unit's steps are costed under this order (9.3)."""
    if name == "road_march":
        return paths.MARCH
    return paths.VEHICLE if U.is_vehicle(u) else paths.FOOT


def _hex(v):
    ok = isinstance(v, (list, tuple)) and len(v) == 2 and all(type(x) is int for x in v)
    return tuple(v) if ok else None


def full_path(gmap, u, order):
    """The hexes the unit is to enter, in order, or None if there is no way (9.2)."""
    here, out = tuple(u["hex"]), []
    for stop in [tuple(v) for v in order.get("via", [])] + [tuple(order["to"])]:
        leg = paths.least_path(gmap, here, stop, mode(u, order["order"]))
        if leg is None:
            return None
        out += leg
        here = stop
    return out


def check_one(state, gmap, side, order, seen):
    """The code that rejects this order, or None if it is legal (8.3, 8.4)."""
    if not isinstance(order, dict) or order.get("order") not in ORDERS or type(order.get("unit")) is not int:
        return "E_ORDER"
    name, u = order["order"], S.unit(state, order["unit"])
    if u is None:
        return "E_UNIT"
    if u["side"] != side:
        return "E_NOT_YOURS"
    if u["status"] != "on_map":
        return "E_NOT_ON_MAP"
    if u["id"] in seen:
        return "E_DUPLICATE"
    if name not in MOVING:                                      # 8.4.1
        if "to" in order or "via" in order:
            return "E_DEST"
        return "E_HQ" if name == "dig_in" and U.is_hq(u) else None
    if name == "attack":                                        # 8.4.3
        if U.is_hq(u):
            return "E_HQ"
        if u["cohesion"] < ATTACK_MIN:
            return "E_COHESION"
    if name == "road_march" and not U.is_vehicle(u):            # 8.4.4
        return "E_FOOT"
    if "to" not in order:                                       # 8.4.2
        return "E_NO_DEST"
    via = order.get("via", [])
    stops = [_hex(v) for v in (via if isinstance(via, list) else [None])] + [_hex(order["to"])]
    if any(h is None or not gmap.on_map(h) for h in stops):
        return "E_OFF_MAP"
    if len(stops) - 1 > VIA_MAX:
        return "E_VIA"
    here = tuple(u["hex"])
    if stops[-1] == here:
        return "E_SAME_HEX"
    if not all(gmap.passable(h) for h in stops):
        return "E_IMPASSABLE"
    if name == "road_march" and not all(h in gmap.on_route for h in [here] + stops):
        return "E_NOT_ON_ROUTE"
    if full_path(gmap, u, order) is None:
        return "E_NO_PATH"
    return None


def check(state, gmap, side, submission):
    """Check a side's orders and air choice. Returns (orders by unit id, air choice, replies).
    Changes no state (8.2.2). Units without an accepted order hold (8.1.3)."""
    submission = submission if isinstance(submission, dict) else {}
    listed = submission.get("orders", [])
    accepted, replies = {}, []
    for order in (listed if isinstance(listed, list) else []):
        code = check_one(state, gmap, side, order, accepted)
        uid = order.get("unit") if isinstance(order, dict) else None
        if code:
            replies.append({"unit": uid, "ok": False, "code": code, "text": REPLIES[code]})
        else:
            accepted[uid] = {k: order[k] for k in ("unit", "order", "to", "via") if k in order}
            replies.append({"unit": uid, "ok": True})
    air = submission.get("air")
    if air not in AIR:                                          # 7.1, 8.5.4
        replies.append({"unit": None, "ok": False, "code": "E_AIR", "text": REPLIES["E_AIR"]})
        air = "support"
    for u in S.on_map(state, side):
        accepted.setdefault(u["id"], {"unit": u["id"], "order": "hold"})
    return accepted, air, replies
