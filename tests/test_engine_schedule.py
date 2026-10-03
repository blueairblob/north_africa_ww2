"""docs/RULES.md §12 and §13: reinforcement, withdrawal, replacement, victory."""
from engine import state as S
from helpers import by_id, start, turn, unit


def play(sc, state, n, **orders):
    for _ in range(n):
        state, _ = turn(sc, state, **orders)
    return state


def test_a_date_belongs_to_one_turn():                                           # 1.9
    sc, _ = start([])
    assert [S.turn_of(sc, d) for d in ("1941-11-01", "1941-11-18", "1941-11-19", "1941-11-20", "1941-11-22")] \
        == [1, 1, 1, 2, 3]


def test_a_unit_arrives_in_the_turn_of_its_date_not_before():                    # 12.1, 12.4
    sc, state = start([unit(105, "axis", "motorised", "Derna", arrives="1941-11-22", entry="Derna")])
    state = play(sc, state, 2)
    assert S.unit(state, 105)["status"] == "not_arrived" and S.unit(state, 105)["hex"] is None
    state = play(sc, state, 1)                                                   # turn 3 holds 22 November
    u = S.unit(state, 105)
    assert u["status"] == "on_map" and u["hex"] == [40, 3] and u["fuel"] == 90
    assert state["sides"]["axis"]["brought"] == 90 + 300                        # full on arrival


def test_a_full_entry_hex_sends_the_arrival_next_door():                         # 12.4: 2
    units = [unit(101, "axis", "foot", "Derna"), unit(102, "axis", "foot", "Derna"),
             unit(105, "axis", "motorised", "Derna", arrives="1941-11-18", entry="Derna")]
    sc, state = start(units)
    state = play(sc, state, 1)
    u = S.unit(state, 105)
    assert u["status"] == "on_map" and S.distance(tuple(u["hex"]), (40, 3)) == 1


def test_an_entry_port_in_enemy_hands_sends_the_arrival_to_its_base():           # 12.4: 3
    sc, state = start([unit(205, "cw", "motorised", "Derna", arrives="1941-11-18", entry="Derna")])
    assert state["places"]["Derna"] == "axis"
    state = play(sc, state, 1)
    u = S.unit(state, 205)
    assert u["status"] == "on_map" and S.distance(tuple(u["hex"]), (40, 3)) in (1, 2, 3)   # nearby, not in the port


def test_with_no_room_anywhere_the_arrival_waits_a_turn():                       # 12.4: 4
    from engine import reinforce
    units = [unit(101, "axis", "foot", "Derna"), unit(105, "axis", "motorised", "Derna", arrives="1941-11-18", entry="Derna")]
    sc, state = start(units)
    full = lambda *a: False
    real = reinforce.B.room
    reinforce.B.room = full
    try:
        state = play(sc, state, 1)
    finally:
        reinforce.B.room = real
    assert S.unit(state, 105)["status"] == "not_arrived"
    assert S.unit(play(sc, state, 1), 105)["status"] == "on_map"


def test_a_withdrawal_removes_the_unit_on_its_date_wherever_it_is():             # 12.2
    units = [unit(101, "axis", "foot", [70, 25], size=2), unit(201, "cw", "armour", [70, 24]),
             unit(102, "axis", "foot", "Derna", arrives="1941-12-20", entry="Derna")]
    sc, state = start(units, objectives=[],
                      withdrawals=[{"date": "1941-11-20", "unit": 101}, {"date": "1941-11-20", "unit": 102}])
    state = play(sc, state, 1)
    assert S.unit(state, 101)["status"] == "on_map"                              # in contact, not yet due
    state = play(sc, state, 1)
    u = by_id(state)
    assert u[101]["status"] == "withdrawn" and u[101]["hex"] is None
    assert u[102]["status"] == "withdrawn"                                       # never arrives
    assert state["sides"]["cw"]["vp"] == 0                                       # not counted as destroyed


def test_replacements_reach_a_unit_in_supply_up_to_its_full_strength():          # 12.3
    units = [unit(201, "cw", "armour", [70, 24], steps=10, max=12), unit(202, "cw", "armour", [72, 24], steps=10, max=20)]
    sc, state = start(units, replacements=[{"date": "1941-11-18", "unit": 201, "steps": 5},
                                           {"date": "1941-11-18", "unit": 202, "steps": 5}])
    S.unit(state, 202)["traced"] = False
    state = play(sc, state, 1)
    assert [u["steps"] for u in state["units"]] == [12, 10]


def test_objectives_score_every_turn_and_again_at_the_end():                     # 13.2, 13.3
    sc, state = start([unit(201, "cw", "foot", "Tobruk"), unit(101, "axis", "foot", "Bardia")], turns=3,
                      objectives=[{"place": "Tobruk", "turn": 2, "end": 7}, {"place": "Bardia", "turn": 1, "end": 4}])
    state = play(sc, state, 2)
    assert state["sides"]["cw"]["vp"] == 4 and state["sides"]["axis"]["vp"] == 2 and not state["over"]
    state = play(sc, state, 1)
    assert state["sides"]["cw"]["vp"] == 6 + 7 and state["sides"]["axis"]["vp"] == 3 + 4
    assert state["over"] and state["turn"] == 4                                  # 13.5, 13.7


def test_the_result_is_graded_by_the_margin():                                   # 13.6
    from engine.victory import victory_phase
    for margin, winner, grade in ((0, None, "draw"), (4, None, "draw"), (5, "axis", "tactical"),
                                  (-14, "cw", "tactical"), (15, "axis", "major"), (-30, "cw", "decisive")):
        sc, state = start([unit(101, "axis", "foot", "Bardia"), unit(201, "cw", "foot", "Tobruk")],
                          turns=1, objectives=[], thresholds=[5, 15, 30])
        state["sides"]["axis" if margin > 0 else "cw"]["vp"] = abs(margin)
        victory_phase(state, sc)
        assert (state["result"]["winner"], state["result"]["grade"]) == (winner, grade), margin


def test_the_game_ends_when_a_side_has_nothing_left():                           # 13.5, 13.4
    ring = [[70, 23], [71, 23], [71, 24], [70, 25], [69, 24], [69, 23]]
    units = [unit(101, "axis", "foot", [70, 24], steps=3, size=3)]
    units += [unit(201 + n, "cw", "armour", h, steps=10) for n, h in enumerate(ring)]
    sc, state = start(units)
    state = play(sc, state, 1, cw=[{"unit": 201 + n, "order": "attack", "to": [70, 24]} for n in range(6)])
    assert state["over"] and state["sides"]["cw"]["vp"] >= 3 * 2


def test_the_result_is_judged_against_standing_still():                         # 13.6
    import json
    from engine import checker, players, runner
    from engine.victory import par
    from helpers import GMAP, ROOT
    sc = json.loads((ROOT / "data" / "scenarios" / "crusader.json").read_text())
    assert par(sc) == sc["par"] == (5 * 22 + 70) - (2 * 22 + 30)                 # 180 for the Axis, 74 for the Commonwealth
    state, _ = runner.play(sc, GMAP, {s: players.DoNothing(GMAP) for s in S.SIDES})
    assert state["result"]["grade"] == "draw" and abs(state["result"]["margin"]) < sc["thresholds"][0]
    assert any("par" in p for p in checker.problems(dict(sc, par=0), GMAP))      # the checker holds it to the sum
    sc, state = start([unit(101, "axis", "foot", "Bardia"), unit(201, "cw", "foot", "Tobruk")], turns=2, par=-4,
                      objectives=[{"place": "Tobruk", "turn": 2}], thresholds=[1, 15, 30])
    state = play(sc, state, 2)
    assert state["sides"]["cw"]["vp"] == 4 and state["result"] == {"winner": None, "grade": "draw", "margin": 0}
