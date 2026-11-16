"""Calendar and physical budgets for daily chapters and legacy two-day games."""
import json
from datetime import date

from engine import checker, players, runner, state as S, victory, weather
from engine.movement import turn_allowance
from engine.turn import begin_turn
from helpers import GMAP, scenario, unit
from screen import saves
from screen.session import Session


def test_daily_turn_uses_one_calendar_day_and_half_the_physical_budget():
    troops = [unit(101, "axis", "foot", "Bardia"), unit(201, "cw", "foot", "Mersa Matruh")]
    two = scenario(troops, turns=2)
    one = scenario(troops, turns=2, turn_days=1)
    two["par"], one["par"] = victory.par(two), victory.par(one)
    assert S.turn_of(two, "1941-11-19") == 1
    assert S.turn_of(one, "1941-11-19") == 2
    assert checker.problems(one, GMAP) == []
    assert checker.problems(dict(one, turn_days=3), GMAP) == ["turn_days: must be 1 or 2"]

    daily = begin_turn(S.new_game(one, GMAP), GMAP, one)
    legacy = begin_turn(S.new_game(two, GMAP), GMAP, two)
    assert daily["sides"]["cw"]["landed"] * 2 == legacy["sides"]["cw"]["landed"]
    assert turn_allowance([S.unit(daily, 201)], 1) * 2 == turn_allowance([S.unit(legacy, 201)], 2)
    assert S.unit(daily, 201)["stores"] > S.unit(legacy, 201)["stores"]

    session = Session(one, GMAP, humans=[], scripted={s: players.DoNothing(GMAP) for s in S.SIDES})
    assert session.day == date(1941, 11, 18)
    assert "next day" in session.weather_words()
    session.done()
    assert session.day == date(1941, 11, 19)
    assert "19 November 1941" in saves.about(session.to_save())


def test_daily_weather_and_mixed_length_campaign_handoff():
    from engine import campaign

    troops = [unit(101, "axis", "foot", "Bardia"), unit(201, "cw", "foot", "Mersa Matruh")]
    first = scenario(troops, id="daily", turns=1, turn_days=1)
    second = scenario(troops, id="following", start="1941-11-19", turns=1)
    for side in S.SIDES:
        for schedule in second["sides"][side].values():
            schedule[0][0] = second["start"]
    first["par"], second["par"] = victory.par(first), victory.par(second)
    finished, _ = runner.play(first, GMAP, {s: players.DoNothing(GMAP) for s in S.SIDES})
    carried = campaign.handoff(finished, first, second, GMAP)
    assert carried["campaign"]["history"][0]["ended"] == "1941-11-18"
    assert carried["scenario"] == "following" and carried["turn"] == 1

    daily = scenario(troops, start="1941-01-31", turn_days=1)
    assert weather.odds(daily, 1) != weather.odds(daily, 2)


def test_daily_fieldworks_take_two_working_days_and_survive_a_save():
    from engine import invariants, view
    from helpers import start, turn

    sc, state = start([unit(101, "axis", "foot", [70, 25]),
                       unit(102, "axis", "foot", [72, 25]),
                       unit(201, "cw", "hq", "Alexandria", steps=1)], turn_days=1)
    dig = [{"unit": 102, "order": "dig_in"}]
    state, _ = turn(sc, state, axis=dig)
    assert state["forts"] == {}
    assert state["fort_work"] == {"70,25": ["axis", 1], "72,25": ["axis", 1]}
    assert view.view(state, GMAP, sc, "axis")["fort_work"] == {"70,25": 1, "72,25": 1}
    assert view.view(state, GMAP, sc, "cw")["fort_work"] == {}
    state = json.loads(S.dumps(state))
    state, _ = turn(sc, state, axis=dig)
    assert state["forts"] == {"70,25": [1, "axis"], "72,25": [1, "axis"]}
    assert state["fort_work"] == {}
    state, _ = turn(sc, state, axis=dig)
    assert state["fort_work"] == {"72,25": ["axis", 1]}
    state, _ = turn(sc, state, axis=[{"unit": 102, "order": "rest"}])
    assert state["fort_work"] == {}
    state, _ = turn(sc, state, axis=dig)
    assert state["fort_work"] == {"72,25": ["axis", 1]}
    state, _ = turn(sc, state, axis=dig)
    assert state["forts"]["72,25"] == [2, "axis"] and state["fort_work"] == {}
    assert S.unit(state, 102)["stores"] == 300 - 5 * 25
    assert invariants.check(state, GMAP) == []


def test_dated_withdrawal_clears_unfinished_and_shallow_fieldworks():
    from engine import invariants
    from helpers import start, turn

    troops = [unit(101, "axis", "foot", [70, 25]),
              unit(102, "axis", "foot", [72, 25]),
              unit(201, "cw", "hq", "Alexandria", steps=1)]
    sc, state = start(troops, turn_days=1,
                      withdrawals=[{"date": "1941-11-18", "unit": 101, "src": "test"}])
    state, _ = turn(sc, state)
    assert S.unit(state, 101)["status"] == "withdrawn"
    assert "70,25" not in state["fort_work"]
    assert state["fort_work"]["72,25"] == ["axis", 1]
    assert invariants.check(state, GMAP) == []

    sc, state = start(troops, withdrawals=[{"date": "1941-11-18", "unit": 101, "src": "test"}])
    state, _ = turn(sc, state)
    assert "70,25" not in state["forts"]
    assert state["forts"]["72,25"] == [1, "axis"]
