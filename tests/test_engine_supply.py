"""docs/RULES.md §6: supply."""
from engine import paths, supply
from engine import state as S
from engine.turn import begin_turn
from helpers import GMAP, by_id, scenario, start, unit

PLACE = {name: list(p["hex"]) for name, p in GMAP.places.items()}
NO_LIFT = {"axis": {"lift": [["1941-11-18", 0]]}, "cw": {"lift": [["1941-11-18", 0]], "railhead": [["1941-11-18", "Misheifa"]]}}


def test_haul_distances_worked_by_hand():                                        # 19.1, 6.4.3
    for a, b, d in (("Tobruk", "Gambut", 12), ("Bardia", "Fort Capuzzo", 8), ("Derna", "Gazala", 22),
                    ("Benghazi", "Tobruk", 98), ("El Agheila", "Tobruk", 150), ("Mersa Matruh", "Sollum", 52),
                    ("Alexandria", "El Alamein", 22)):
        assert paths.haul_distances(GMAP, tuple(PLACE[a]))[tuple(PLACE[b])] == d, (a, b)


def test_fill_falls_with_distance_from_the_depot():                              # 6.6.5
    assert [supply.fill(d) for d in (0, 8, 11, 14, 20)] == [100, 100, 88, 75, 50]


def test_landing_at_a_port_and_its_fuel_share():                                 # 6.3
    sc, state = start([], ports={"Benghazi": {"condition": 50}})
    sc["sides"]["axis"].update(sea_pct=[["1941-11-18", 60]], fuel_pct=[["1941-11-18", 30]])
    state = begin_turn(state, GMAP, sc)
    port = state["ports"]["Benghazi"]
    assert port["condition"] == 55                                               # 6.3.1
    assert port["fuel"] + port["stores"] == 1500 * 55 * 60 // 10000              # 6.3.2
    assert port["fuel"] == 495 * 30 // 100                                       # 6.3.4


def test_tripoli_landings_arrive_two_turns_later():                              # 6.3.5
    sc, state = start([])
    stock = []
    for _ in range(4):
        state = begin_turn(state, GMAP, sc)
        stock.append(state["tripoli"]["fuel"] + state["tripoli"]["stores"])
        state["turn"] += 1
    assert stock == [0, 0, 3000, 6000]


def test_a_haul_uses_lift_and_burns_fuel_by_distance():                          # 6.5
    units = [unit(104, "axis", "hq", "Gazala", steps=1, fuel=120, stores=300),
             unit(101, "axis", "foot", "Gazala", size=3, stores=0)]
    sc, state = start(units, ports={"Derna": {"fuel": 1000, "stores": 5000}})
    sc["sides"]["axis"]["lift"] = [["1941-11-18", 22 * 500]]                     # enough for 500 tonnes at distance 22
    state = begin_turn(state, GMAP, sc)
    hq, foot = by_id(state)[104], by_id(state)[101]
    assert foot["stores"] == 500 - 150                                           # what came, less upkeep (6.9.1)
    assert hq["dump"] == {"fuel": 0, "stores": 0}                                # 6.5.4: stores first, all issued
    assert state["sides"]["axis"]["issued"] == 500                               # 6.5.2: all the lift, no more
    assert state["sides"]["axis"]["burnt"] == -(-500 * 22 // 2000)               # 6 tonnes of fuel


def test_no_lift_no_haul_but_a_port_feeds_units_close_by():                      # 6.5.3, 6.6.2, 6.8.3
    units = [unit(104, "axis", "hq", "Gazala", steps=1), unit(101, "axis", "foot", "Gazala", stores=0),
             unit(102, "axis", "foot", "Derna", stores=0)]
    sc, state = start(units, ports={"Derna": {"fuel": 0, "stores": 5000}}, sides=NO_LIFT)
    state = begin_turn(state, GMAP, sc)
    u = by_id(state)
    assert u[102]["stores"] == 300 - 50 and u[102]["traced"]                     # drew from the port
    assert u[101]["stores"] == 0 and u[101]["out_of_stores"] and u[101]["cohesion"] == 90     # 6.10.2
    assert u[101]["traced"]                                                      # an HQ in reach, though empty (6.6.4)


def test_the_railway_carries_supply_to_the_railhead_for_nothing():               # 6.2.4
    units = [unit(204, "cw", "hq", "Misheifa", steps=1), unit(201, "cw", "foot", "Misheifa", stores=0)]
    sc, state = start(units, ports={"Alexandria": {"fuel": 500, "stores": 500}}, sides=NO_LIFT)
    state = begin_turn(state, GMAP, sc)
    assert by_id(state)[201]["stores"] == 250 and state["sides"]["cw"]["burnt"] == 0


def test_an_enemy_on_the_line_pulls_the_railhead_back():                         # 6.2.4, 6.4.2
    cut = list(GMAP.rail[40])
    units = [unit(204, "cw", "hq", "Misheifa", steps=1), unit(201, "cw", "foot", "Misheifa", stores=0),
             unit(101, "axis", "armour", cut)]
    sc, state = start(units, ports={"Alexandria": {"fuel": 500, "stores": 500}}, sides=NO_LIFT)
    blocked = supply.blocked_for(state, GMAP, "cw")
    assert GMAP.rail.index(supply.railhead(state, GMAP, sc, blocked)) < 39
    state = begin_turn(state, GMAP, sc)
    assert by_id(state)[201]["stores"] == 0


def test_an_enemy_across_the_road_blocks_the_supply_path():                      # 6.4.2
    sc, state = start([unit(201, "cw", "armour", "Tmimi")])
    blocked = supply.blocked_for(state, GMAP, "axis")
    assert tuple(PLACE["Tmimi"]) in blocked and len(blocked) > 1                 # the unit and its zone of control
    d = paths.haul_distances(GMAP, tuple(PLACE["Derna"]), blocked)
    assert d[tuple(PLACE["Gazala"])] > 22                                        # round, not through


def test_a_starving_unit_falls_apart_then_loses_steps():                         # 6.10.2
    sc, state = start([unit(101, "axis", "foot", [70, 25], stores=0, cohesion=10, steps=2)], sides=NO_LIFT)
    seen = []
    for _ in range(3):
        state = begin_turn(state, GMAP, sc)
        u = S.unit(state, 101)
        seen.append((u["cohesion"], u["steps"], u["status"]))
    assert seen == [(0, 2, "on_map"), (0, 1, "on_map"), (0, 0, "destroyed")]


def test_a_cut_made_after_the_supply_phase_changes_nothing_until_the_next():     # 6.11.1
    from helpers import turn
    units = [unit(104, "axis", "hq", "Gazala", steps=1), unit(101, "axis", "foot", "Gazala"),
             unit(201, "cw", "armour", [50, 9])]
    sc, state = start(units, ports={"Derna": {"fuel": 1000, "stores": 5000}})
    state = begin_turn(state, GMAP, sc)
    before = by_id(state)[101]["stores"]
    state, _ = turn(sc, state, cw=[{"unit": 201, "order": "move", "to": PLACE["Tmimi"]}])
    assert by_id(state)[101]["stores"] == before


def test_units_draw_before_dumps_are_filled():                                   # 6.7.3, 6.8
    units = [unit(104, "axis", "hq", "Gazala", steps=1), unit(101, "axis", "foot", "Derna", stores=0)]
    sc, state = start(units, ports={"Derna": {"condition": 0, "fuel": 100, "stores": 300}})
    sc["sides"]["axis"]["sea_pct"] = [["1941-11-18", 0]]                         # nothing lands: only the 300 tonnes
    state = begin_turn(state, GMAP, sc)
    u = by_id(state)
    assert u[101]["stores"] == 300 - 50                                          # the garrison had it, not the dump
    assert u[104]["dump"]["stores"] == 0 and state["ports"]["Derna"]["stores"] == 0


def test_a_port_keeps_a_reserve_for_the_units_that_draw_from_it():               # 6.7.5
    units = [unit(104, "axis", "hq", "Gazala", steps=1), unit(101, "axis", "foot", "Derna", size=2),
             unit(102, "axis", "foot", "Gazala", stores=0)]
    sc, state = start(units, ports={"Derna": {"condition": 0, "fuel": 500, "stores": 1400}})
    sc["sides"]["axis"]["sea_pct"] = [["1941-11-18", 0]]
    state = begin_turn(state, GMAP, sc)
    hq, port = by_id(state)[104], state["ports"]["Derna"]
    assert port["stores"] == supply.RESERVE_TURNS * supply.UPKEEP * 2            # ten turns for the garrison: 1000 tonnes
    assert hq["dump"]["stores"] + by_id(state)[102]["stores"] + 50 == 400        # the HQ had only what was above it
    assert by_id(state)[101]["stores"] == 600 - 100                              # the garrison itself was full: it drew nothing
