"""The Bardia assault is linked and judged by more than town ownership."""
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from engine import campaign, checker, computer, scenarios, state as S, victory
from helpers import GMAP
from screen.session import Session


DRAFTS = Path(__file__).resolve().parents[1] / "data" / "scenario_drafts"


def load(name):
    return json.loads((DRAFTS / f"{name}.json").read_text(encoding="utf-8"))


def test_bardia_draft_is_checked_linked_and_requires_a_played_interval():
    interval, assault = load("compass_interval"), load("bardia_assault")
    assert interval["research_next"] == assault["id"]
    assert date.fromisoformat(interval["start"]) + timedelta(days=interval["turns"]) == date.fromisoformat(assault["start"])
    assert assault["turn_days"] == 1 and assault["turns"] == 3
    assert checker.problems(assault, GMAP) == []
    assert GMAP.side_between((66, 14), (66, 13)) in GMAP.passes
    assert GMAP.side_between((67, 13), (67, 14)) in GMAP.passes
    assert assault["id"] not in scenarios.names()
    with pytest.raises(ValueError, match="played campaign chapter"):
        campaign.start(assault, GMAP)


def test_holding_bardia_town_does_not_win_while_southern_sector_is_contested():
    assault = load("bardia_assault")
    state = {"sides": {"axis": {"vp": 0}, "cw": {"vp": 0}},
             "places": {"Bardia": "cw", "Tobruk": "axis"},
             "units": [{"side": "cw", "status": "on_map", "type": "foot", "hex": [66, 13]},
                       {"side": "cw", "status": "on_map", "type": "foot", "hex": [67, 13]},
                       {"side": "axis", "status": "on_map", "type": "foot", "hex": [66, 14]}]}
    result = victory.result_for(state, assault, GMAP)
    assert result["winner"] is None
    assert [c["met"] for c in result["mission"]["checks"]["cw"]["checks"]] == [True, True, False]
    state["units"].pop()
    result = victory.result_for(state, assault, GMAP)
    assert result["winner"] == "cw" and result["grade"] == "major"


def test_three_chapter_research_run_preserves_history_and_delays_the_assault():
    opening = load("compass_opening")
    players = {side: computer.ComputerHard(GMAP) for side in S.SIDES}
    session = Session(opening, GMAP, humans=[], scripted=players,
                      initial_state=campaign.start(opening, GMAP, seed=1940))
    for expected, turns in (("compass_interval", 8), ("bardia_assault", 17)):
        while not session.state["over"]:
            session.done()
        assert len(session.record) == turns
        if expected == "bardia_assault":
            assert all(not (o["order"] == "attack" and o.get("to") == [67, 13])
                       for entry in session.record for o in entry["cw"]["orders"])
        following = session.following_chapter()
        assert following and following["id"] == expected
        before = session.state
        session = session.continue_campaign(following)
        for uid in (306, 331, 332, 333, 334):
            if S.unit(before, uid):
                assert S.unit(session.state, uid)["steps"] == S.unit(before, uid)["steps"]
    while not session.state["over"]:
        session.done()
        if len(session.record) == 1:
            assert "breach:66,13" in session.state["mission_reached"]["cw"]
            assert session.state["places"]["Bardia"] == "axis"
            assert all(o.get("to") != [67, 13] for o in session.record[0]["cw"]["orders"])
        elif len(session.record) == 2:
            assert any(e["event"] == "battle" and e["hex"] == [67, 13]
                       and 306 in e["attackers"] for e in session.state["log"])
    assert len(session.record) == 3 and session.state["turn"] == 4
    assert [h["scenario"] for h in session.state["campaign"]["history"]] == [
        "compass_opening", "compass_interval"]
    assert session.state["result"]["winner"] == "axis"
    assert not session.state["result"]["mission"]["checks"]["cw"]["complete"]
