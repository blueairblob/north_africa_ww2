"""docs/RULES.md §21: the weather, the one thing drawn by chance, from a seed."""
import pytest

from engine import checker, invariants, orders, paths, players, runner
from engine import state as S
from engine import weather as W
from engine.gamemap import ROAD, TRACK
from engine.turn import begin_turn
from engine.view import leaks, view
from helpers import GMAP, by_id, scenario, small, turn, unit

# Open desert with no road, track or escarpment: columns 66-80, rows 21-27.
ROAD_RUN = [(69, 16), (70, 17), (71, 17), (72, 17), (73, 16), (74, 16), (75, 16), (76, 16), (77, 15), (78, 16), (79, 16)]


def began(units, kind="clear", seed=1, **more):
    """A scenario in which every turn has this weather, and its state as turn 1 opens."""
    odds = {} if kind == "clear" else {kind: 100}
    sc = scenario(units, weather=[["1941-11-18", odds]], **more)
    state = S.new_game(sc, GMAP, seed)
    W.weather_step(state, sc)
    assert state["weather"] == kind
    return sc, state


def move(uid, to, order="move"):
    return {"unit": uid, "order": order, "to": list(to)}


# ---- the draw ----------------------------------------------------------------------------

def test_the_generator_worked_by_hand():                                         # 21.2.2
    x = 1
    for _ in range(W.WARM + 1):                                                  # eight thrown away, then turn 1's first
        x = x * 48271 % 2147483647
    assert W.draws(1, 1) == (x * 100 // 2147483647, x * 48271 % 2147483647 * 100 // 2147483647) == (26, 74)
    assert [W.draws(1, t) for t in (2, 3, 4)] == [(8, 56), (58, 80), (59, 51)]   # the figures a port must give
    assert [W.draws(1941, t) for t in (1, 2)] == [(30, 15), (81, 71)]
    assert all(0 <= n <= 99 for seed in (1, 2, 2147483646) for t in range(1, 60) for n in W.draws(seed, t))


def test_with_no_seed_there_is_no_weather():                                     # 21.2.1
    sc = scenario([unit(201, "cw", "foot", [70, 24])], weather=[["1941-11-18", {"rain": 100}]])
    state = begin_turn(S.new_game(sc, GMAP), GMAP, sc)
    assert state["seed"] == 0 and state["weather"] == "clear" and W.outlook(0, 1, sc) == "fair"
    for bad in (-1, 2147483647, 1.5, "7"):
        with pytest.raises(ValueError):
            S.new_game(sc, GMAP, bad)


def test_the_weather_of_a_turn_follows_from_the_seed_and_the_month():            # 21.3
    sc = scenario([unit(201, "cw", "foot", [70, 24])], turns=400)               # opens 18 November 1941
    assert W.odds(sc, 1) == (6, 3) and W.odds(sc, 8) == (11, 3) and W.odds(sc, 80) == (2, 14)   # November, December, April
    for seed in (1, 7, 1941):
        assert [W.of(seed, t, sc) for t in range(1, 30)] == [W.of(seed, t, sc) for t in range(1, 30)]
    count = {k: sum(W.of(seed, 10, sc) == k for seed in range(1, 6001)) for k in W.KINDS}       # a December turn
    assert 580 <= count["rain"] <= 740 and 130 <= count["sandstorm"] <= 230                    # about 11 and 3 in 100
    assert len({tuple(W.of(seed, t, sc) for t in range(1, 23)) for seed in range(1, 200)}) > 100   # games differ


def test_a_scenario_may_give_its_own_odds():                                     # 21.3.1
    sc = scenario([unit(201, "cw", "foot", [70, 24])],
                  weather=[["1941-11-18", {"sandstorm": 100}], ["1941-11-22", {}], ["1941-11-24", {"rain": 100}]])
    assert [W.of(5, t, sc) for t in (1, 2, 3, 4, 5)] == ["sandstorm", "sandstorm", "clear", "rain", "rain"]
    assert not any(p.startswith("weather") for p in checker.problems(sc, GMAP))
    for wrong in ([["1941-11-18", {"snow": 5}]], [["1941-11-18", {"rain": 60, "sandstorm": 50}]], [["soon", {}]], [["1941-11-18"]]):
        assert any(p.startswith("weather") for p in checker.problems(dict(sc, weather=wrong), GMAP)), wrong


def test_the_weather_is_settled_before_supply_and_changes_nothing_else():        # 21.3.3, I-18, I-20
    sc = scenario([unit(201, "cw", "foot", [70, 24]), unit(101, "axis", "foot", "Benghazi")],
                  weather=[["1941-11-18", {"rain": 100}]])
    audit = []
    state = begin_turn(S.new_game(sc, GMAP, 3), GMAP, sc, audit)
    assert state["weather"] == "rain" and audit == [] and invariants.check(state, GMAP) == []
    state["weather"] = "snow"
    assert any(b.startswith("I-20") for b in invariants.check(state, GMAP))


# ---- what a side is told -----------------------------------------------------------------

def test_a_side_is_told_this_turns_weather_and_an_outlook_and_never_the_seed():  # 21.5, 14.8, I-17
    sc, state = began([unit(201, "cw", "foot", [70, 24]), unit(101, "axis", "foot", [70, 20])], "sandstorm", seed=11)
    for side in S.SIDES:
        v = view(state, GMAP, sc, side)
        assert v["weather"] == "sandstorm" and v["outlook"] in ("fair", "unsettled")
        assert "seed" not in v and leaks(v, state) == []
        assert leaks(dict(v, seed=11), state) == ["the seed the weather is drawn from"]


def test_the_outlook_is_often_right_and_sometimes_wrong():                       # 21.5.2
    sc = scenario([unit(201, "cw", "foot", [70, 24])], turns=30)
    said = {(word, bad): 0 for word in ("fair", "unsettled") for bad in (True, False)}
    for seed in range(1, 3001):
        for t in range(8, 12):                                                   # December
            said[W.outlook(seed, t, sc), W.of(seed, t + 1, sc) != "clear"] += 1
    bad = said["unsettled", True] + said["fair", True]
    clear = said["unsettled", False] + said["fair", False]
    assert 74 <= said["unsettled", True] * 100 // bad <= 86                      # OUTLOOK_HIT: 80 of 100 bad turns foretold
    assert 12 <= said["unsettled", False] * 100 // clear <= 18                   # OUTLOOK_FALSE: 15 of 100 clear ones too
    assert said["fair", True] > 0                                                # "fair" is no promise


# ---- what it does ------------------------------------------------------------------------

def test_in_a_sandstorm_nothing_is_seen_beyond_the_next_hex():                   # 21.4.2
    foes = [unit(100 + d, "axis", "foot", [70, 24 - d]) for d in (1, 2, 3, 4)]
    for kind, eyes, sees in (("clear", "foot", [101, 102, 103, 104]), ("rain", "foot", [101, 102, 103, 104]),
                             ("sandstorm", "foot", [101]), ("sandstorm", "recon", [101])):
        sc, state = began(foes + [unit(201, "cw", eyes, [70, 24])], kind)
        state["sides"]["cw"]["recon"] = 2                                        # last turn's air reconnaissance: two hexes more
        assert sorted(e["id"] for e in view(state, GMAP, sc, "cw")["enemy"]) == sees, (kind, eyes)


@pytest.mark.parametrize("kind", ["rain", "sandstorm"])
def test_in_bad_weather_nothing_flies(kind):                                     # 21.4.1
    units = [unit(101, "axis", "armour", [70, 25], steps=12), unit(201, "cw", "armour", [70, 24], steps=12)]

    def played(weather, air, cw=()):
        sc, state = began(units, weather)
        sc["sides"]["cw"]["air"] = [["1941-11-18", 3]]                           # three air points for the Commonwealth
        return turn(sc, state, cw=cw, air=air)[0]

    attack = [{"unit": 201, "order": "attack", "to": [70, 25]}]
    value = {w: next(e for e in played(w, "support", attack)["log"] if e["event"] == "battle")["att"] for w in ("clear", kind)}
    assert value["clear"] > value[kind]                                          # the support was worth 15 per cent
    assert [played(w, "recon")["sides"]["cw"]["recon"] for w in ("clear", kind)] == [3, 0]
    assert [played(w, "interdict")["sides"]["axis"]["interdiction"] for w in ("clear", kind)] == [15, 0]


def test_in_a_sandstorm_every_unit_has_half_its_movement():                      # 21.4.3
    for kind, hexes in (("clear", 8), ("sandstorm", 4), ("rain", 4)):            # armour: 32 MP, 4 a hex in open desert
        sc, state = began([unit(201, "cw", "armour", [70, 21])], kind)
        state, _ = turn(sc, state, cw=[move(201, [70, 31])])
        assert by_id(state)[201]["hex"] == [70, 21 + hexes], kind
    for kind, hexes in (("clear", 4), ("sandstorm", 2), ("rain", 4)):            # men on foot: 16 MP; rain does not slow them
        sc, state = began([unit(201, "cw", "foot", [70, 21])], kind)
        state, _ = turn(sc, state, cw=[move(201, [70, 31])])
        assert by_id(state)[201]["hex"] == [70, 21 + hexes], kind


def test_in_rain_a_vehicle_off_the_road_pays_double():                           # 21.4.4
    a, b = ROAD_RUN[0], ROAD_RUN[1]
    track = next((x, y) for (x, y), kind in sorted(GMAP.links.items()) if kind == TRACK
                 and GMAP.side_between(x, y) not in GMAP.passes and not GMAP.rough(y))
    desert = ((70, 24), (70, 25))
    side = GMAP.side_between
    assert GMAP.links[a, b] == ROAD and side(a, b) not in GMAP.passes
    assert [paths.step_cost(GMAP, a, b, side(a, b), m) for m in ("vehicle", "vehicle_mud", "march", "march_mud")] == [4, 4, 2, 2]
    assert [paths.step_cost(GMAP, *track, side(*track), m) for m in ("vehicle", "vehicle_mud", "march", "march_mud")] == [4, 8, 3, 6]
    assert [paths.step_cost(GMAP, *desert, side(*desert), m) for m in ("vehicle", "vehicle_mud", "foot")] == [4, 8, 4]
    assert paths.step_cost(GMAP, *desert, side(*desert), "march_mud") is None    # still no road march off the roads
    tank, man = unit(201, "cw", "armour", [70, 24]), unit(202, "cw", "foot", [70, 24])
    assert orders.mode(tank, "move", "rain") == "vehicle_mud" and orders.mode(tank, "road_march", "rain") == "march_mud"
    assert orders.mode(man, "move", "rain") == "foot" and orders.mode([tank, man], "move", "rain") == "vehicle_mud"
    assert orders.mode(tank, "move", "sandstorm") == "vehicle" == orders.mode(tank, "move")


def test_in_rain_the_way_keeps_to_the_road_and_the_road_is_as_fast_as_ever():    # 21.4.4, 9.2
    a, b = (84, 17), (91, 19)                                                    # both on the coast road, which bends between them
    off = lambda way: [GMAP.links.get((x, y)) for x, y in zip([a] + way, way)].count(None)
    dry, wet = paths.least_path(GMAP, a, b, "vehicle"), paths.least_path(GMAP, a, b, "vehicle_mud")
    assert off(dry) == 5 and off(wet) == 0 and len(wet) == len(dry) + 1          # dry it cuts the corner; wet it goes round
    for kind in ("clear", "rain"):                                               # along the road a lorry goes as far in rain
        sc, state = began([unit(201, "cw", "motorised", list(ROAD_RUN[0]))], kind)
        state, _ = turn(sc, state, cw=[move(201, ROAD_RUN[-1], "road_march")])
        assert by_id(state)[201]["hex"] == list(ROAD_RUN[-1]), kind
        sc, state = began([unit(201, "cw", "motorised", list(ROAD_RUN[0]))], kind)
        state, _ = turn(sc, state, cw=[move(201, ROAD_RUN[-1])])
        assert by_id(state)[201]["hex"] == list(ROAD_RUN[-1]), kind


# ---- whole games -------------------------------------------------------------------------

def test_a_game_with_weather_replays_the_same_and_another_seed_plays_another_game():   # I-1, 21.2.3
    sc = small()
    game = lambda seed: runner.play(sc, GMAP, {"axis": players.AlwaysAttack(GMAP), "cw": players.AlwaysAttack(GMAP)}, seed=seed)
    (first, record), (again, _) = game(77), game(77)
    assert S.dumps(first) == S.dumps(again) and first["seed"] == 77
    seeds = [s for s in range(1, 40) if any(W.of(s, t, sc) != "clear" for t in range(1, len(record) + 1))]
    assert seeds and any(game(s)[0]["units"] != first["units"] for s in seeds[:4])       # the weather changed what happened
    replay = runner.play(sc, GMAP, {s: players.Recorded([turn_[s] for turn_ in record]) for s in S.SIDES}, seed=77)[0]
    assert S.dumps(replay) == S.dumps(first)                                     # scenario, seed and orders are the game
