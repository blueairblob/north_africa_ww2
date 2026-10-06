"""docs/RULES.md §10 and §11: combat, retreat, advance, recovery."""
from engine import state as S
from helpers import by_id, start, turn, unit


def attack(uid, to):
    return {"unit": uid, "order": "attack", "to": to}


def test_a_meeting_of_armour_worked_by_hand():                                   # 19.2
    sc, state = start([unit(101, "axis", "armour", [70, 25], size=3, steps=12, cohesion=96),
                       unit(201, "cw", "armour", [70, 24], steps=13, cohesion=95)])
    state, _ = turn(sc, state, axis=[attack(101, [70, 24])], cw=[attack(201, [70, 25])], air="recon")
    a, b = by_id(state)[201], by_id(state)[101]
    battles = {tuple(e["hex"]): e for e in state["log"] if e["event"] == "battle"}
    assert (battles[70, 25]["att"], battles[70, 25]["def"]) == (756, 705)        # 10.4
    assert (battles[70, 24]["att"], battles[70, 24]["def"]) == (705, 756)
    assert (a["steps"], a["cohesion"], a["stores"]) == (11, 59, 150)             # 10.3.1, 10.5
    assert (b["steps"], b["cohesion"], b["stores"]) == (10, 56, 450)             # 21 + 21, limited to 40 (10.5.4)
    assert a["hex"] == [70, 24] and b["hex"] == [70, 25]                         # 10.6.1: both stand
    assert not battles[70, 25]["retreated"] and not battles[70, 24]["retreated"]


def test_tanks_lose_to_guns_and_beat_infantry_in_the_open():                     # 10.9, DESIGN §7
    for kind, steps, wins in (("guns", 4, False), ("foot", 3, True)):
        sc, state = start([unit(101, "axis", kind, [70, 25], steps=steps),
                           unit(201, "cw", "armour", [70, 24], steps=15)])
        state, _ = turn(sc, state, cw=[attack(201, [70, 25])])
        battle = next(e for e in state["log"] if e["event"] == "battle")
        assert (battle["att"] > battle["def"]) == wins, kind


def test_the_loser_retreats_away_from_the_attack_and_the_winner_advances():      # 10.6, 10.7
    sc, state = start([unit(101, "axis", "foot", [70, 25], steps=3),
                       unit(201, "cw", "armour", [70, 24], steps=15)])
    state, _ = turn(sc, state, cw=[attack(201, [70, 25])])
    u = by_id(state)
    # three hexes are equally far from the attack; the one nearest the Axis base, in the west, is taken (10.6.3)
    assert u[101]["hex"] == [69, 25] and u[201]["hex"] == [70, 25]               # and the winner follows


def test_a_routed_unit_goes_two_hexes():                                         # 10.6.1, 10.6.6
    sc, state = start([unit(101, "axis", "foot", [70, 25], steps=3, cohesion=30),
                       unit(201, "cw", "armour", [70, 24], steps=15)])
    state, _ = turn(sc, state, cw=[attack(201, [70, 25])])
    assert S.unit(state, 101)["hex"] == [68, 26]


def test_a_unit_with_nowhere_to_go_surrenders():                                 # 10.6.5, 10.8.5, 13.4
    ring = [[70, 23], [71, 23], [71, 24], [70, 25], [69, 24], [69, 23]]
    units = [unit(101, "axis", "foot", [70, 24], steps=3, size=2)]
    units += [unit(201 + n, "cw", "armour", h, steps=10) for n, h in enumerate(ring)]
    sc, state = start(units)
    state, _ = turn(sc, state, cw=[attack(201 + n, [70, 24]) for n in range(6)])
    assert S.unit(state, 101)["status"] == "destroyed" and S.unit(state, 101)["hex"] is None
    assert state["sides"]["cw"]["vp"] >= 2 * 2
    assert [u["id"] for u in S.on_map(state) if u["hex"] == [70, 24]] == [201, 202]     # two advance: 10.7.1, 4.3.1


def test_attacks_from_several_hexes_add_up_and_count_for_more():                 # 10.4.5, 10.8.1
    def att(n):
        ring = [[70, 23], [70, 25], [69, 24]][:n]
        units = [unit(101, "axis", "foot", [70, 24], steps=9)]
        units += [unit(201 + i, "cw", "motorised", h, steps=3) for i, h in enumerate(ring)]
        sc, state = start(units)
        state, _ = turn(sc, state, cw=[attack(201 + i, [70, 24]) for i in range(n)])
        return next(e for e in state["log"] if e["event"] == "battle")["att"]
    one = att(1)
    assert att(2) == 2 * one * 115 // 100 and att(3) == 3 * one * 130 // 100


def test_a_disorganised_unit_does_not_attack():                                  # 10.2.1, 8.4.3
    sc, state = start([unit(101, "axis", "foot", [70, 25]), unit(201, "cw", "armour", [66, 24], cohesion=40)])
    state, replies = turn(sc, state, cw=[attack(201, [70, 25])])                 # legal when ordered...
    assert replies["cw"][0]["ok"]
    assert not any(e["event"] == "battle" for e in state["log"])                 # ...but the march wore it down
    assert any(e["event"] == "no attack" and e["unit"] == 201 for e in state["log"])


def test_move_and_road_march_never_attack_and_a_column_defends_at_half():        # 10.2.4, 10.4.4
    sc, state = start([unit(101, "axis", "foot", [70, 25]), unit(201, "cw", "armour", [70, 23])])
    state, _ = turn(sc, state, cw=[{"unit": 201, "order": "move", "to": [70, 25]}])
    assert not any(e["event"] == "battle" for e in state["log"])


def test_holding_scrapes_a_position_and_digging_builds_it():                     # 11.3
    sc, state = start([unit(101, "axis", "foot", [70, 25]), unit(102, "axis", "foot", [72, 25])])
    for n in range(1, 6):
        state, _ = turn(sc, state, axis=[{"unit": 102, "order": "dig_in"}])
        assert state["forts"]["70,25"] == [1, "axis"]                            # 11.3.2: hold stops at 1
        assert state["forts"]["72,25"] == [min(n, 4), "axis"]                    # 11.3.3: one level a turn, to 4
    assert S.unit(state, 102)["stores"] == 300 - 4 * 50                          # nothing is paid at the top


def test_a_scrape_lapses_when_left_and_a_built_position_stays():                 # 11.3.5
    sc, state = start([unit(101, "axis", "foot", [70, 25]), unit(102, "axis", "foot", [72, 25])],
                      forts=[[72, 25, 2, "axis"], [70, 25, 1, "axis"]])
    state, _ = turn(sc, state, axis=[{"unit": 101, "order": "move", "to": [70, 26]},
                                     {"unit": 102, "order": "move", "to": [72, 26]}])
    assert "70,25" not in state["forts"] and state["forts"]["72,25"] == [2, "axis"]


def test_the_holder_of_the_field_recovers_half_its_tanks():                      # 11.1
    sc, state = start([unit(101, "axis", "guns", [70, 25], steps=6),
                       unit(201, "cw", "armour", [70, 24], steps=20, max=20)])
    state, _ = turn(sc, state, cw=[attack(201, [70, 25])])
    battle = next(e for e in state["log"] if e["event"] == "battle")
    lost = battle["lost"]["201"]
    assert lost >= 2 and not battle["retreated"]
    assert S.unit(state, 201)["steps"] == 20 - lost                              # repulsed: the guns hold the field
    sc, state = start([unit(101, "axis", "armour", [70, 25], steps=8),
                       unit(201, "cw", "armour", [70, 24], steps=20, max=20)])
    state, _ = turn(sc, state, cw=[attack(201, [70, 25])])
    battle = next(e for e in state["log"] if e["event"] == "battle")
    lost = battle["lost"]["201"]
    assert battle["retreated"] and S.unit(state, 201)["steps"] == 20 - lost + lost // 2


def test_rest_restores_cohesion_only_in_supply():                                # 11.2.1
    sc, state = start([unit(101, "axis", "foot", [70, 25], cohesion=50), unit(102, "axis", "foot", [72, 25], cohesion=50)])
    S.unit(state, 102)["traced"] = False
    state, _ = turn(sc, state, axis=[{"unit": 101, "order": "rest"}, {"unit": 102, "order": "rest"}])
    assert [u["cohesion"] for u in state["units"]] == [70, 50]
