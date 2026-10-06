"""docs/RULES.md §20: formations, groups (join, split), and the morale ceiling."""
from engine import invariants, orders, supply
from engine import state as S
from engine.turn import begin_turn
from helpers import GMAP, by_id, start, turn, unit

HQ, TANKS, RIFLES, GUNS = 110, 111, 112, 113


def division(at=(70, 24), **more):
    """A division in one hex: its HQ, tanks, lorried infantry and guns."""
    return [unit(HQ, "axis", "hq", list(at), steps=1), unit(TANKS, "axis", "armour", list(at), parent=HQ, steps=12),
            unit(RIFLES, "axis", "motorised", list(at), parent=HQ), unit(GUNS, "axis", "guns", list(at), parent=HQ, steps=4)]


def move(uid, to, order="move", **more):
    return dict({"unit": uid, "order": order, "to": to}, **more)


def test_related_units_that_start_together_start_as_a_group():                   # 20.2.1
    sc, state = start(division() + [unit(120, "axis", "foot", [70, 24])])
    u = by_id(state)
    assert [u[i]["group"] for i in (HQ, TANKS, RIFLES, GUNS)] == [HQ] * 4 and u[120]["group"] is None
    assert [m["id"] for m in S.party(state, u[GUNS])] == [HQ, TANKS, RIFLES, GUNS]
    assert invariants.check(state, GMAP) == []
    sc, state = start(division(), grouped=False)
    assert all(u["group"] is None for u in state["units"])


def test_a_group_has_one_order_and_moves_as_one_at_its_slowest_pace():           # 20.2.5, 20.2.6
    sc, state = start(division((66, 24)) + [unit(120, "axis", "motorised", [66, 26])])
    state, replies = turn(sc, state, axis=[move(HQ, [80, 24]), move(120, [80, 26])])
    u = by_id(state)
    assert all(r["ok"] for r in replies["axis"])
    assert len({tuple(u[i]["hex"]) for i in (HQ, TANKS, RIFLES, GUNS)}) == 1      # together
    assert S.distance(tuple(u[HQ]["hex"]), (66, 24)) == 8                        # eight hexes: the tanks' pace
    assert S.distance(tuple(u[120]["hex"]), (66, 26)) == 10                      # lorries alone go ten
    assert u[TANKS]["fuel"] == 120 - 8 * 4 and u[RIFLES]["fuel"] == 90 - 8 * 3    # each pays its own fuel
    assert u[RIFLES]["cohesion"] == 100 - 32 // 4 and all(u[i]["group"] == HQ for i in (HQ, TANKS, RIFLES, GUNS))


def test_an_order_for_a_member_is_refused_unless_it_is_split_off():              # 20.2.4, 20.2.5
    sc, state = start(division())
    _, _, replies = orders.check(state, GMAP, "axis", {"orders": [move(TANKS, [72, 24])], "air": "support"})
    assert replies[0]["code"] == "E_GROUPED" and replies[0]["text"] == orders.REPLIES["E_GROUPED"]
    state, replies = turn(sc, state, axis=[move(TANKS, [72, 24], alone=True)])
    u = by_id(state)
    assert replies["axis"][0]["ok"] and u[TANKS]["hex"] == [72, 24] and u[TANKS]["group"] is None
    assert [u[i]["hex"] for i in (HQ, RIFLES, GUNS)] == [[70, 24]] * 3 and [u[i]["group"] for i in (HQ, RIFLES, GUNS)] == [HQ] * 3


def test_when_the_leader_splits_off_the_rest_stay_grouped_under_the_next():      # 20.2.1, 20.2.4
    sc, state = start(division())
    state, _ = turn(sc, state, axis=[move(HQ, [70, 26], alone=True)])
    u = by_id(state)
    assert u[HQ]["hex"] == [70, 26] and u[HQ]["group"] is None
    assert [u[i]["group"] for i in (TANKS, RIFLES, GUNS)] == [TANKS] * 3 and u[TANKS]["hex"] == [70, 24]


def test_join_goes_to_a_related_unit_and_groups_with_it():                       # 20.2.2
    units = division() + [unit(114, "axis", "recon", [70, 27], parent=HQ, steps=3), unit(120, "axis", "foot", [68, 24])]
    sc, state = start(units)
    state, replies = turn(sc, state, axis=[{"unit": 114, "order": "join", "with": HQ}])
    u = by_id(state)
    assert replies["axis"][0]["ok"] and u[114]["hex"] == [70, 24] and u[114]["group"] == HQ
    assert invariants.check(state, GMAP) == []


def test_join_in_the_same_hex_is_at_once_and_the_group_keeps_its_order():        # 20.2.2
    sc, state = start(division((66, 24)), grouped=False)
    state["units"][1]["group"] = state["units"][2]["group"] = TANKS             # tanks and infantry grouped; guns and HQ loose
    given = [move(TANKS, [69, 24]), {"unit": GUNS, "order": "join", "with": RIFLES}]
    state, replies = turn(sc, state, axis=given)
    u = by_id(state)
    assert all(r["ok"] for r in replies["axis"])
    assert [u[i]["hex"] for i in (TANKS, RIFLES, GUNS)] == [[69, 24]] * 3 and u[HQ]["hex"] == [66, 24]
    assert [u[i]["group"] for i in (TANKS, RIFLES, GUNS)] == [TANKS] * 3


def test_units_of_different_divisions_can_form_a_group_within_the_stacking_limit():   # 20.2.1, 20.1.4
    sc, state = start(division() + [unit(120, "axis", "foot", [70, 26])])
    state, replies = turn(sc, state, axis=[{"unit": 120, "order": "join", "with": HQ}])
    u = by_id(state)
    assert replies["axis"][0]["ok"] and u[120]["hex"] == [70, 24] and u[120]["group"] == HQ
    assert invariants.check(state, GMAP) == []
    state, _ = turn(sc, state, axis=[move(HQ, [70, 22])])
    assert {tuple(x["hex"]) for x in state["units"]} == {(70, 22)}               # the made-up force moves as one


def test_a_unit_cannot_join_the_enemy_itself_or_its_own_group():                 # 20.2.3
    sc, state = start(division() + [unit(120, "axis", "foot", [70, 26]), unit(201, "cw", "foot", "Tobruk")])
    for who, other in ((HQ, HQ), (HQ, TANKS), (HQ, 201), (HQ, 999), (HQ, None)):
        _, _, replies = orders.check(state, GMAP, "axis", {"orders": [{"unit": who, "order": "join", "with": other}], "air": "support"})
        assert replies[0]["code"] == "E_JOIN", (who, other)


def test_men_on_foot_march_the_road_and_a_group_with_them_goes_at_their_rate():   # 8.4.4, 9.3, 20.2.6
    gambut, bardia = list(GMAP.places["Gambut"]["hex"]), list(GMAP.places["Bardia"]["hex"])
    units = [unit(HQ, "axis", "hq", gambut, steps=1), unit(TANKS, "axis", "armour", gambut, parent=HQ),
             unit(RIFLES, "axis", "foot", gambut, parent=HQ), unit(120, "axis", "foot", "Tobruk"), unit(121, "axis", "foot", "Derna")]
    sc, state = start(units)
    tobruk = tuple(GMAP.places["Tobruk"]["hex"])
    given = [move(HQ, bardia, "road_march"), move(120, gambut, "road_march"), move(121, list(tobruk))]
    state, replies = turn(sc, state, axis=given)
    u = by_id(state)
    assert all(r["ok"] for r in replies["axis"])
    road = [tuple(h) for h in orders.paths.least_path(GMAP, tobruk, tuple(gambut), "foot_march")]
    assert tuple(u[120]["hex"]) == road[4]                                       # five road hexes: sixteen MP at three each
    assert u[TANKS]["hex"] == u[RIFLES]["hex"] and S.distance(tuple(u[TANKS]["hex"]), tuple(gambut)) <= 5    # the tanks keep his pace
    assert orders.paths.least_path(GMAP, (70, 24), (72, 24), "foot_march") is None                          # no marching in the desert


def test_a_group_out_of_fuel_stops_whole():                                      # 20.2.6
    sc, state = start(division((66, 24)))
    S.unit(state, GUNS)["fuel"] = 2 * 2                                          # the guns have fuel for two hexes
    state, _ = turn(sc, state, axis=[move(HQ, [74, 24])])
    assert len({tuple(u["hex"]) for u in state["units"]}) == 1                    # together still
    assert S.distance(tuple(state["units"][0]["hex"]), (66, 24)) == 2            # two hexes, and no further
    assert any(e["event"] == "stopped" and e["why"] == "out of fuel" and e["unit"] == TANKS for e in state["log"])


def test_a_group_falls_back_as_one_and_surrenders_as_one():                      # 20.2.7
    sc, state = start(division((70, 25)) + [unit(201, "cw", "armour", [70, 24], steps=30, xp="veteran"),
                                             unit(202, "cw", "armour", [71, 24], steps=30, xp="veteran")])
    for u in state["units"][:4]:
        u["steps"] = 1 if u["type"] != "armour" else 2
    state, _ = turn(sc, state, cw=[{"unit": 201, "order": "attack", "to": [70, 25]}, {"unit": 202, "order": "attack", "to": [70, 25]}])
    alive = [u for u in state["units"] if u["side"] == "axis" and u["status"] == "on_map"]
    assert len({tuple(u["hex"]) for u in alive}) <= 1 and all(u["hex"] != [70, 25] for u in alive)   # together, elsewhere
    assert invariants.check(state, GMAP) == []


def test_morale_has_a_ceiling_from_supply_strength_and_its_own_hq():             # 20.3
    assert (supply.MORALE_UNSUPPLIED, supply.MORALE_THIN, supply.MORALE_ORPHAN, supply.MORALE_WEAK, supply.MORALE_FALL) == (30, 20, 20, 40, 10)
    units = division((70, 24)) + [unit(114, "axis", "recon", [60, 26], parent=HQ, steps=3),
                                   unit(120, "axis", "foot", [50, 26], steps=3, max=6)]
    sc, state = start(units)
    state = begin_turn(state, GMAP, sc)
    u = by_id(state)
    assert u[TANKS]["ceiling"] == 100 and u[TANKS]["cohesion"] == 100            # beside its HQ: nothing off
    assert u[114]["ceiling"] == 100 - 30 - 20 and u[114]["cohesion"] == 90       # no depot, and out of its HQ's reach: falls 10 a turn
    assert u[120]["ceiling"] == 100 - 30 - 40 * 3 // 6                           # no depot, and at half strength
    for _ in range(5):
        state = begin_turn(state, GMAP, sc)
    assert by_id(state)[114]["cohesion"] == 50                                   # down to the ceiling and no further...
    S.unit(state, 114)["stores"] = 300
    state, _ = turn(sc, state, axis=[{"unit": 114, "order": "rest"}])
    assert by_id(state)[114]["cohesion"] == 50                                   # ...and rest cannot lift it above


def test_a_group_follows_up_as_one_with_its_hq():                                # 20.2.7, 10.7
    sc, state = start(division((70, 24)) + [unit(201, "cw", "foot", [70, 25], steps=2)])
    state, _ = turn(sc, state, axis=[{"unit": HQ, "order": "attack", "to": [70, 25]}])
    u = by_id(state)
    assert [u[i]["hex"] for i in (HQ, TANKS, RIFLES, GUNS)] == [[70, 25]] * 4     # the HQ went in with them
    assert [u[i]["group"] for i in (HQ, TANKS, RIFLES, GUNS)] == [HQ] * 4 and invariants.check(state, GMAP) == []


def test_a_group_that_loses_its_leader_outside_combat_closes_up_and_can_still_be_ordered():   # 20.2.8
    from engine.turn import begin_turn as supply_phase
    specs = division((70, 25))
    specs[0].update(stores=0, cohesion=0)                                       # the HQ starves, broken, beside the enemy
    sc, state = start(specs + [unit(201, "cw", "armour", [70, 24])])
    sc["sides"]["axis"]["lift"] = [["1941-11-18", 0]]
    state = supply_phase(state, GMAP, sc)
    u = by_id(state)
    assert u[HQ]["status"] == "destroyed" and u[HQ]["group"] is None             # it surrendered (6.10.2)
    assert [u[i]["group"] for i in (TANKS, RIFLES, GUNS)] == [TANKS] * 3         # the rest close up under the next
    assert invariants.check(state, GMAP) == []
    _, _, replies = orders.check(state, GMAP, "axis", {"orders": [move(TANKS, [70, 27])], "air": "support"})
    assert replies[0]["ok"]                                                      # and can be ordered
    sc, state = start(division((70, 25)), withdrawals=[{"date": "1941-11-18", "unit": HQ}])
    state, _ = turn(sc, state)
    assert [x["group"] for x in state["units"]] == [None, TANKS, TANKS, TANKS] and invariants.check(state, GMAP) == []
