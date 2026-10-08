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


def test_a_replacement_is_counted_as_the_histories_count_it_and_the_side_is_told():   # 12.3, 12.8
    units = [unit(201, "cw", "armour", [70, 24], steps=10, tanks=100, max=16), unit(101, "axis", "armour", "Derna", steps=10, tanks=100, max=16),
             unit(102, "axis", "armour", "Benghazi", steps=10, tanks=100, max=16),
             unit(103, "axis", "armour", "Gazala", steps=10, tanks=100, max=11)]
    sc, state = start(units, objectives=[], replacements=[
        {"date": "1941-11-18", "unit": 201, "tanks": 33}, {"date": "1941-11-18", "unit": 101, "tanks": 22, "via": "Tobruk"},
        {"date": "1941-11-18", "unit": 102, "tanks": 22, "via": "Benghazi"}, {"date": "1941-11-18", "unit": 103, "tanks": 38}])
    state = play(sc, state, 1)
    u = by_id(state)
    assert [u[i]["steps"] for i in (201, 101, 102, 103)] == [13, 10, 12, 11]    # 33 tanks are 3 steps; Tobruk is not the Axis's; a full unit takes what it can
    told = [(e["unit"], e["event"], e.get("steps", e.get("why"))) for e in state["log"] if "replaced" in e["event"]]
    assert told == [(101, "not_replaced", "port"), (102, "replaced", 2), (103, "replaced", 1), (201, "replaced", 3)]
    assert [e["side"] for e in state["log"] if "replaced" in e["event"]] == ["axis", "axis", "axis", "cw"]


def test_a_division_that_arrives_together_arrives_as_a_group():                  # 12.4, 20.2.1
    come = dict(arrives="1941-11-18", entry="Sidi Barrani")
    units = [unit(210, "cw", "hq", "Sidi Barrani", steps=1, **come), unit(211, "cw", "foot", "Sidi Barrani", parent=210, **come),
             unit(212, "cw", "foot", "Sidi Barrani", parent=210, **come), unit(220, "cw", "foot", "Sidi Barrani", **come)]
    sc, state = start(units, objectives=[])
    assert all(u["group"] is None and u["status"] == "not_arrived" for u in state["units"])
    state = play(sc, state, 1)
    u = by_id(state)
    assert [u[i]["group"] for i in (210, 211, 212, 220)] == [210, 210, 210, None]
    assert len({tuple(u[i]["hex"]) for i in (210, 211, 212)}) == 1
    from engine import invariants
    from helpers import GMAP
    assert invariants.check(state, GMAP) == []


def test_units_whose_hq_is_withdrawn_do_not_count_it_lost():                     # 12.2, 20.3.2
    from engine.turn import begin_turn
    from helpers import GMAP

    def ceilings(**more):
        units = [unit(210, "cw", "hq", "Mersa Matruh", steps=1), unit(211, "cw", "foot", "Mersa Matruh", parent=210)]   # at a port: fed with or without the HQ
        sc, state = start(units, objectives=[], **more)
        state = play(sc, state, 1)
        return by_id(begin_turn(state, GMAP, sc))
    stays = ceilings()
    left = ceilings(withdrawals=[{"date": "1941-11-18", "unit": 210}])
    assert left[210]["status"] == "withdrawn" and left[211]["ceiling"] == stays[211]["ceiling"]
    from engine import board, supply
    sc, state = start([unit(210, "cw", "hq", "Mersa Matruh", steps=1), unit(211, "cw", "foot", "Mersa Matruh", parent=210)], objectives=[])
    board.destroy(state, S.unit(state, 210), "destroyed")                        # an HQ lost in battle is another matter
    assert by_id(begin_turn(state, GMAP, sc))[211]["ceiling"] == stays[211]["ceiling"] - supply.MORALE_ORPHAN


def test_a_side_is_shown_its_own_timetable_in_the_order_it_falls_due():          # 12.8, 14.2, 14.8
    from engine.view import view
    from helpers import GMAP
    units = [unit(201, "cw", "armour", [70, 24], tanks=100), unit(202, "cw", "foot", "Tobruk"),
             unit(203, "cw", "foot", "Sidi Barrani", arrives="1941-11-22", entry="Sidi Barrani", arrives_note="From the Delta."),
             unit(101, "axis", "foot", "Derna")]
    sc, state = start(units, withdrawals=[{"date": "1941-11-24", "unit": 202, "note": "To Syria."}, {"date": "1941-11-20", "unit": 101}],
                      replacements=[{"date": "1941-11-20", "unit": 201, "tanks": 30, "via": "Tobruk"}])
    assert view(state, GMAP, sc, "cw")["timetable"] == [
        {"kind": "replacement", "unit": 201, "date": "1941-11-20", "n": 30, "what": "tanks", "via": "Tobruk", "turn": 2},
        {"kind": "arrival", "unit": 203, "date": "1941-11-22", "entry": "Sidi Barrani", "note": "From the Delta.", "turn": 3},
        {"kind": "withdrawal", "unit": 202, "date": "1941-11-24", "note": "To Syria.", "turn": 4}]
    assert view(state, GMAP, sc, "axis")["timetable"] == [{"kind": "withdrawal", "unit": 101, "date": "1941-11-20", "turn": 2}]


def test_the_checker_refuses_a_dated_event_with_no_source_or_outside_the_game():  # 12.7
    from engine import checker
    from helpers import GMAP, small
    assert checker.problems(small(), GMAP) == []
    sc = small()
    del sc["withdrawals"][0]["src"]
    sc["replacements"][0]["src"] = "Z"                                           # a letter the scenario does not explain
    sc["replacements"] += [{"date": "1942-06-01", "unit": 201, "steps": 1, "src": "T"},
                           {"date": "1941-11-20", "unit": 201, "men": 500, "src": "T"},
                           {"date": "1941-11-20", "unit": 201, "steps": 1, "tanks": 10, "src": "T"},
                           {"date": "1941-11-20", "unit": 201, "steps": 1, "via": "Atlantis", "src": "T"}]
    del next(u for u in sc["units"] if u["id"] == 105)["arrives_src"]
    found = "\n".join(checker.problems(sc, GMAP))
    for clue in ("withdrawal for unit 107: its date names no source", "replacement for unit 201: its date names no source",
                 "arrival: its date names no source", "1942-06-01 falls after the last turn", "brings men, which is not what the unit is counted in",
                 "needs one whole number", "Atlantis is not a place"):
        assert clue in found, clue


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


def test_a_unit_destroyed_scores_for_the_enemy_and_its_fate_is_recorded():       # 13.4
    from engine.turn import begin_turn
    from helpers import GMAP
    ring = [[70, 23], [71, 23], [71, 24], [70, 25], [69, 24], [69, 23]]
    units = [unit(101, "axis", "foot", [70, 24], steps=3, size=3), unit(102, "axis", "foot", [60, 25], stores=0, cohesion=0, steps=1)]
    units += [unit(201 + n, "cw", "armour", h, steps=10) for n, h in enumerate(ring)]
    sc, state = start(units, objectives=[])
    state = begin_turn(state, GMAP, sc)                                          # 102 starves in the Supply phase
    state = play(sc, state, 1, cw=[{"unit": 201 + n, "order": "attack", "to": [70, 24]} for n in range(6)])
    u = by_id(state)
    assert u[101]["fate"] == {"cause": "surrendered", "turn": 1} and u[102]["fate"] == {"cause": "starved", "turn": 1}
    assert u[201]["fate"] is None
    assert state["sides"]["cw"]["kills"] == state["sides"]["cw"]["vp"] == 5 * 3 + 5 * 1
    sc, state = start([unit(101, "axis", "foot", "Bardia")], withdrawals=[{"date": "1941-11-18", "unit": 101}], objectives=[])
    state = play(sc, state, 1)
    assert by_id(state)[101]["fate"] == {"cause": "withdrawn", "turn": 1} and state["sides"]["cw"]["kills"] == 0
