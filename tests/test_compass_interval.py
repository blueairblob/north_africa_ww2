"""The opt-in research interval carries a played Compass result to 3 January."""
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from engine import campaign, checker, computer, scenarios, state as S
from helpers import GMAP
from screen.session import Session


DRAFTS = Path(__file__).resolve().parents[1] / "data" / "scenario_drafts"


def load(name):
    return json.loads((DRAFTS / f"{name}.json").read_text(encoding="utf-8"))


def test_interval_is_dated_checked_and_requires_played_compass():
    opening, interval = load("compass_opening"), load("compass_interval")
    assert opening["research_next"] == interval["id"]
    assert date.fromisoformat(opening["start"]) + timedelta(days=opening["turns"]) == date.fromisoformat(interval["start"])
    assert date.fromisoformat(interval["start"]) + timedelta(days=interval["turns"]) == date(1941, 1, 3)
    assert interval["landing_points"] == {"Sollum": 200}
    assert interval["landing_sides"] == {"Sollum": "cw"}
    assert checker.problems(interval, GMAP) == []
    assert interval["id"] not in scenarios.names()
    with pytest.raises(ValueError, match="played campaign chapter"):
        campaign.start(interval, GMAP)


def test_played_compass_continues_through_all_interval_days_and_new_arrivals():
    opening = load("compass_opening")
    players = {side: computer.ComputerHard(GMAP) for side in S.SIDES}
    session = Session(opening, GMAP, humans=[], scripted=players,
                      initial_state=campaign.start(opening, GMAP, seed=1940))
    while not session.state["over"]:
        session.done()
    before = session.state
    next_chapter = session.following_chapter()
    assert next_chapter["id"] == "compass_interval"
    carried = campaign.handoff(before, opening, next_chapter, GMAP, record=session.record)
    for uid in (301, 305, 306, 310, 311, 312, 313, 314, 160, 170):
        assert S.unit(carried, uid) == S.unit(before, uid)
    following = session.continue_campaign(next_chapter)
    assert following.state["ports"]["Sollum"] == {"condition": 100, "fuel": 0, "stores": 0}
    assert all(following.state["places"][n] == before["places"][n] for n in before["places"])
    assert {180, 181, 182, 330, 331, 332, 333, 334} <= {
        u["id"] for u in following.state["units"] if u["status"] == "not_arrived"}
    while not following.state["over"]:
        following.done()
    assert following.state["turn"] == 18 and len(following.record) == 17
    assert all(S.unit(following.state, uid)["status"] == "on_map" for uid in (330, 331, 332, 333, 334))
    assert following.state["places"]["Sollum"] == "cw"
    assert following.state["places"]["Bardia"] == "axis"
    assert len(following.state["campaign"]["history"]) == 1
