"""docs/RULES.md §8: the six orders, when each is legal, and the reply when it is not."""
import pytest

from engine import orders
from helpers import GMAP, start, unit

OPEN = [70, 24]                                   # open desert, no road, no escarpment
UNITS = [unit(101, "axis", "armour", OPEN), unit(102, "axis", "foot", [70, 26]),
         unit(103, "axis", "hq", [70, 26]), unit(104, "axis", "armour", "Tobruk", cohesion=30),
         unit(105, "axis", "motorised", "Derna", arrives="1941-12-01", entry="Derna"),
         unit(106, "axis", "motorised", "Gambut"), unit(201, "cw", "armour", [75, 24])]

REJECTED = [                                                         # rule, order, code
    ("8.3", {"unit": 101, "order": "charge"}, "E_ORDER"),
    ("8.3", "nonsense", "E_ORDER"),
    ("8.3", {"unit": 999, "order": "hold"}, "E_UNIT"),
    ("8.3", {"unit": 201, "order": "hold"}, "E_NOT_YOURS"),
    ("8.3", {"unit": 105, "order": "hold"}, "E_NOT_ON_MAP"),
    ("8.4.1", {"unit": 101, "order": "rest", "to": [71, 24]}, "E_DEST"),
    ("8.4.1", {"unit": 103, "order": "dig_in"}, "E_HQ"),
    ("8.4.2", {"unit": 101, "order": "move"}, "E_NO_DEST"),
    ("8.4.2", {"unit": 101, "order": "move", "to": [200, 3]}, "E_OFF_MAP"),
    ("8.4.2", {"unit": 101, "order": "move", "to": [72, 24], "via": [[71, 24]] * 5}, "E_VIA"),
    ("8.4.2", {"unit": 101, "order": "move", "to": OPEN}, "E_SAME_HEX"),
    ("8.4.2", {"unit": 101, "order": "move", "to": [0, 0]}, "E_IMPASSABLE"),
    ("8.4.2", {"unit": 101, "order": "move", "to": [83, 43]}, "E_NO_PATH"),     # land cut off by the depression
    ("8.4.3", {"unit": 103, "order": "attack", "to": [71, 24]}, "E_HQ"),
    ("8.4.3", {"unit": 104, "order": "attack", "to": [56, 11]}, "E_COHESION"),
    ("8.4.4", {"unit": 102, "order": "road_march", "to": [71, 24]}, "E_NOT_ON_ROUTE"),   # foot too must keep to the road
    ("8.4.4", {"unit": 101, "order": "road_march", "to": [71, 24]}, "E_NOT_ON_ROUTE"),
    ("8.4.4", {"unit": 106, "order": "road_march", "to": OPEN}, "E_NOT_ON_ROUTE"),
]


@pytest.mark.parametrize("rule, order, code", REJECTED)
def test_an_illegal_order_is_rejected_with_its_code(rule, order, code):
    _, state = start(UNITS)
    _, _, replies = orders.check(state, GMAP, "axis", {"orders": [order], "air": "support"})
    assert replies[0]["ok"] is False and replies[0]["code"] == code, rule
    assert replies[0]["text"] == orders.REPLIES[code]


def test_the_no_path_hex_is_land_that_nothing_can_reach():
    assert GMAP.passable((83, 43))
    assert all(orders.paths.least_path(GMAP, tuple(OPEN), (83, 43), mode) is None for mode in ("vehicle", "foot"))


def test_legal_orders_are_accepted_and_the_rest_hold():                          # 8.1.3, 8.4
    _, state = start(UNITS)
    given = [{"unit": 101, "order": "attack", "to": [75, 24], "via": [[72, 25]]},
             {"unit": 102, "order": "move", "to": [72, 26]},
             {"unit": 106, "order": "road_march", "to": list(GMAP.places["Bardia"]["hex"])},
             {"unit": 103, "order": "rest"}, {"unit": 104, "order": "dig_in"}]
    accepted, air, replies = orders.check(state, GMAP, "axis", {"orders": given, "air": "recon"})
    assert all(r["ok"] for r in replies) and air == "recon"
    assert [accepted[u]["order"] for u in (101, 102, 103, 104, 106)] == ["attack", "move", "rest", "dig_in", "road_march"]
    assert 105 not in accepted                                                   # not on the map


def test_a_second_order_for_a_unit_is_rejected_and_the_first_stands():           # 8.3 check 5
    _, state = start(UNITS)
    given = [{"unit": 101, "order": "rest"}, {"unit": 101, "order": "dig_in"}]
    accepted, _, replies = orders.check(state, GMAP, "axis", {"orders": given, "air": "support"})
    assert replies[1]["code"] == "E_DUPLICATE" and accepted[101]["order"] == "rest"


def test_a_unit_with_no_order_or_a_rejected_one_holds():                         # 8.1.3, 8.5.2
    _, state = start(UNITS)
    accepted, _, _ = orders.check(state, GMAP, "axis", {"orders": [{"unit": 101, "order": "move"}], "air": "support"})
    assert accepted[101] == {"unit": 101, "order": "hold"} and accepted[102]["order"] == "hold"


def test_an_unknown_air_choice_flies_support_and_says_so():                      # 7.1, 8.5.4
    _, state = start(UNITS)
    _, air, replies = orders.check(state, GMAP, "axis", {"orders": [], "air": "bombs"})
    assert air == "support" and replies[-1]["code"] == "E_AIR"


def test_checking_orders_changes_nothing():                                      # 8.2.2
    from engine import state as S
    _, state = start(UNITS)
    before = S.dumps(state)
    orders.check(state, GMAP, "axis", {"orders": [o for _, o, _ in REJECTED], "air": "x"})
    assert S.dumps(state) == before


def test_a_move_is_legal_with_no_fuel_and_however_far():                         # 8.4.2, 9.7.2
    _, state = start([unit(101, "axis", "armour", OPEN, fuel=0)])
    _, _, replies = orders.check(state, GMAP, "axis", {"orders": [{"unit": 101, "order": "move", "to": [110, 24]}],
                                                       "air": "support"})
    assert replies[0]["ok"]
