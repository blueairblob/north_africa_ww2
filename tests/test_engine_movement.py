"""docs/RULES.md §9: simultaneous movement in impulses."""
from engine import state as S
from helpers import GMAP, by_id, start, turn, unit

# Open desert with no road, track or escarpment: columns 66-80, rows 21-27.


def move(uid, to, order="move"):
    return {"unit": uid, "order": order, "to": to}


def test_the_test_ground_is_open():
    for c in range(66, 81):
        for r in range(21, 28):
            assert GMAP.terrain[r][c] == "." and (c, r) not in GMAP.on_route
            assert not any(hexside in GMAP.cliffs | GMAP.passes for _, _, hexside in GMAP.around((c, r)))


def test_allowances_in_open_desert():                                            # 9.1.1, 9.3, 9.8.1
    sc, state = start([unit(101, "axis", "armour", [70, 21]), unit(102, "axis", "foot", [72, 21]),
                       unit(103, "axis", "recon", [74, 21], steps=3)])
    state, _ = turn(sc, state, axis=[move(101, [70, 27]), move(102, [72, 27]), move(103, [74, 27])])
    u = by_id(state)
    assert u[101]["hex"] == [70, 27] and u[102]["hex"] == [72, 25] and u[103]["hex"] == [74, 27]
    assert u[102]["cohesion"] == 100 - 16 // 4                                   # foot: 16 MP, 4 hexes
    assert u[101]["cohesion"] == 100 - 24 // 4                                   # six hexes of desert


def test_armour_goes_eight_desert_hexes_and_no_more():                           # 9.10
    sc, state = start([unit(101, "axis", "armour", [66, 24])])
    state, _ = turn(sc, state, axis=[move(101, [80, 24])])
    assert S.unit(state, 101)["hex"][0] - 66 == 8


def test_vehicles_pay_fuel_per_hex_and_foot_pays_none():                         # 9.7.1
    sc, state = start([unit(101, "axis", "armour", [70, 21], size=3), unit(102, "axis", "foot", [72, 21])])
    before = by_id(state)[101]["fuel"]
    state, _ = turn(sc, state, axis=[move(101, [70, 24]), move(102, [72, 23])])
    assert before - by_id(state)[101]["fuel"] == 3 * (3 * 4) and by_id(state)[102]["fuel"] == 0


def test_a_vehicle_with_no_fuel_stays_and_its_order_was_legal():                 # 9.7.2, 6.10.1
    sc, state = start([unit(101, "axis", "armour", [70, 24], fuel=0)])
    state, replies = turn(sc, state, axis=[move(101, [70, 27])])
    assert replies["axis"][0]["ok"] and S.unit(state, 101)["hex"] == [70, 24]
    assert any(e["event"] == "stopped" and e["why"] == "out of fuel" for e in state["log"])


def test_both_sides_into_one_hex_the_priority_side_enters():                     # 9.5.3, 1.6
    sc, state = start([unit(101, "axis", "armour", [70, 22]), unit(201, "cw", "armour", [70, 26])])
    assert S.priority_side(state["turn"]) == "axis"
    state, _ = turn(sc, state, axis=[move(101, [70, 26])], cw=[move(201, [70, 22])])
    u = by_id(state)
    assert u[101]["hex"] == [70, 24] and u[201]["hex"] == [70, 25]


def test_both_sides_into_one_hex_the_attacker_enters():                          # 9.5.3
    sc, state = start([unit(101, "axis", "armour", [70, 22]), unit(201, "cw", "armour", [70, 26], steps=1)])
    state, _ = turn(sc, state, axis=[move(101, [70, 26])], cw=[move(201, [70, 22], "attack")])
    stopped = [e for e in state["log"] if e["event"] == "stopped"]
    assert stopped[0] == {"event": "stopped", "side": "axis", "unit": 101, "why": "contact", "hex": [70, 23]}


def test_two_enemies_changing_places_both_stop():                                # 9.5.2
    sc, state = start([unit(101, "axis", "armour", [70, 24]), unit(201, "cw", "armour", [70, 25])])
    state, _ = turn(sc, state, axis=[move(101, [70, 25])], cw=[move(201, [70, 24])])
    u = by_id(state)
    assert u[101]["hex"] == [70, 24] and u[201]["hex"] == [70, 25]


def test_a_full_hex_refuses_the_highest_id():                                    # 9.5.4, 4.3.1
    sc, state = start([unit(201, "cw", "motorised", [70, 23]), unit(202, "cw", "motorised", [69, 23]),
                       unit(203, "cw", "motorised", [69, 24]), unit(204, "cw", "hq", [71, 23], steps=1),
                       unit(205, "cw", "hq", [71, 24], steps=1)])
    state, _ = turn(sc, state, cw=[move(uid, [70, 24]) for uid in (201, 202, 203, 204, 205)])
    u = by_id(state)
    assert [u[i]["hex"] for i in (201, 202, 203)] == [[70, 24], [70, 24], [69, 24]]
    assert [u[i]["hex"] for i in (204, 205)] == [[70, 24], [71, 24]]              # one HQ a hex


def test_friends_may_change_places():                                            # 9.5.2 is about enemies only
    sc, state = start([unit(201, "cw", "motorised", [70, 23]), unit(202, "cw", "motorised", [70, 24])])
    state, _ = turn(sc, state, cw=[move(201, [70, 24]), move(202, [70, 23])])
    assert [u["hex"] for u in state["units"]] == [[70, 24], [70, 23]]


def test_entering_a_zone_of_control_stops_a_unit():                              # 9.5.7, 9.6
    sc, state = start([unit(101, "axis", "foot", [71, 24]), unit(201, "cw", "armour", [72, 21])])
    state, _ = turn(sc, state, cw=[move(201, [72, 27])])
    assert S.unit(state, 201)["hex"] == [72, 24]                                 # the first hex next to the enemy


def test_a_unit_in_a_zone_of_control_may_step_out_but_not_along_it():            # 9.5.1, 9.6.2
    units = [unit(101, "axis", "foot", [70, 24]), unit(201, "cw", "armour", [70, 23])]
    sc, state = start(units)
    out, _ = turn(sc, state, cw=[move(201, [70, 21])])
    assert S.unit(out, 201)["hex"] == [70, 21]
    along, _ = turn(sc, state, cw=[move(201, [71, 23])])
    assert S.unit(along, 201)["hex"] == [70, 23]


def test_an_hq_that_moves_keeps_only_what_it_can_carry():                        # 6.11.4, 9.9
    sc, state = start([unit(204, "cw", "hq", [70, 24], steps=1, dump={"fuel": 1000, "stores": 200})])
    state, _ = turn(sc, state, cw=[move(204, [70, 25])])
    hq = S.unit(state, 204)
    assert hq["dump"] == {"fuel": 300, "stores": 200} and hq["stationary"] is False
    assert state["sides"]["cw"]["lost"] == 700
