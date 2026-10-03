"""docs/RULES.md §14: what each side can see, and §5.1: what each phase may change."""
from engine import turn as T
from engine.view import view
from helpers import GMAP, start, turn, unit

HIDDEN = {"cohesion", "fuel", "stores", "size", "out_of_stores", "traced", "status", "max", "side"}


def seen(units, side="cw", recon=0):
    sc, state = start(units)
    state["sides"][side]["recon"] = recon
    return {e["id"]: e for e in view(state, GMAP, sc, side)["enemy"]}


def test_units_spot_two_hexes_and_recon_four():                                  # 14.3
    foes = [unit(100 + d, "axis", "foot", [70 + d * 0, 24 - d]) for d in (1, 2, 3, 4, 5)]
    assert sorted(seen(foes + [unit(201, "cw", "foot", [70, 24])])) == [101, 102]
    assert sorted(seen(foes + [unit(201, "cw", "recon", [70, 24])])) == [101, 102, 103, 104]


def test_air_reconnaissance_adds_to_every_units_range():                         # 14.3, 7.5
    foes = [unit(100 + d, "axis", "foot", [70, 24 - d]) for d in (1, 2, 3, 4, 5)]
    assert sorted(seen(foes + [unit(201, "cw", "foot", [70, 24])], recon=2)) == [101, 102, 103, 104]


def test_steps_show_only_next_to_your_own_units_and_the_rest_never():            # 14.4, 14.8
    e = seen([unit(101, "axis", "foot", [70, 23]), unit(102, "axis", "foot", [70, 22]),
              unit(201, "cw", "foot", [70, 24])])
    assert e[101]["steps"] == 6 and "steps" not in e[102]
    assert not (set(e[101]) | set(e[102])) & HIDDEN


def test_a_view_shows_your_own_side_in_full_and_no_enemy_supply():               # 14.2, 14.8
    sc, state = start([unit(101, "axis", "hq", "Gambut", steps=1, dump={"fuel": 5, "stores": 7}),
                       unit(201, "cw", "foot", "Tobruk")])
    cw, axis = view(state, GMAP, sc, "cw"), view(state, GMAP, sc, "axis")
    assert [u["id"] for u in cw["units"]] == [201] and cw["tripoli"] is None
    assert set(cw["ports"]) == {n for n, side in state["places"].items() if side == "cw" and n in state["ports"]}
    assert axis["units"][0]["dump"] == {"fuel": 5, "stores": 7} and axis["tripoli"] is not None
    assert cw["places"] == axis["places"] == state["places"] and cw["vp"] == axis["vp"]
    assert "7" not in str(cw["enemy"]) and "lift" in cw


def test_an_enemy_fortification_shows_only_within_spotting_range():              # 14.5
    sc, state = start([unit(201, "cw", "foot", [70, 24])], forts=[[70, 22, 2, "axis"], [70, 20, 3, "axis"], [72, 24, 1, "cw"]])
    assert view(state, GMAP, sc, "cw")["forts"] == {"70,22": [2, "axis"], "72,24": [1, "cw"]}


def test_a_side_is_told_of_the_battles_it_fought_and_no_other_enemy_event():     # 14.6
    units = [unit(101, "axis", "foot", [70, 25]), unit(102, "axis", "armour", [60, 25]),
             unit(201, "cw", "armour", [70, 24], steps=15)]
    sc, state = start(units)
    state, _ = turn(sc, state, axis=[{"unit": 102, "order": "move", "to": [61, 25]}],
                    cw=[{"unit": 201, "order": "attack", "to": [70, 25]}])
    cw = [e["event"] for e in view(state, GMAP, sc, "cw")["events"]]
    axis = [e["event"] for e in view(state, GMAP, sc, "axis")["events"]]
    assert "battle" in cw and "battle" in axis and "advanced" in cw and "advanced" not in axis
    assert "retreated" in axis and "retreated" not in cw


def test_checking_orders_changes_no_state_and_each_phase_only_what_it_may():     # 5.1, I-18
    sc, state = start([unit(101, "axis", "armour", [70, 25]), unit(201, "cw", "armour", [70, 23])])
    audit = []
    state = T.begin_turn(state, GMAP, sc, audit)
    T.finish_turn(state, GMAP, sc, {"axis": {"orders": [{"unit": 101, "order": "attack", "to": [70, 23]}]}}, audit)
    assert audit == []


def test_a_phase_that_oversteps_is_caught():                                     # I-18
    sc, state = start([unit(101, "axis", "armour", [70, 25])])
    real = T.air_phase
    T.air_phase = lambda state, scenario, ctx: (real(state, scenario, ctx), state["units"][0].update(hex=[70, 26]))
    try:
        audit = []
        T.finish_turn(state, GMAP, sc, {}, audit)
    finally:
        T.air_phase = real
    assert audit == ["I-18 the air phase changed ['unit.hex']"]
