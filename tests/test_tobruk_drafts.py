"""The Tobruk research chapters must continue played Compass outcomes."""
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from engine import campaign, checker, computer, reinforce, runner, scenarios, state as S
from helpers import GMAP
from screen.session import Session


DRAFTS = Path(__file__).resolve().parents[1] / "data" / "scenario_drafts"
NAMES = ("compass_opening", "compass_interval", "bardia_assault",
         "tobruk_approach", "tobruk_assault", "derna_pursuit", "beda_fomm_pursuit",
         "cyrenaica_preparation", "cyrenaica_reversal")


def chapters():
    return [json.loads((DRAFTS / f"{name}.json").read_text(encoding="utf-8")) for name in NAMES]


def assert_handoff_keeps_played_state(previous, following, arrivals):
    assert following["places"] == previous["places"]
    old_units = {unit["id"]: unit for unit in previous["units"]}
    new_units = {unit["id"]: unit for unit in following["units"]}
    assert set(new_units) - set(old_units) == set(arrivals)
    assert all(new_units[uid] == unit for uid, unit in old_units.items())
    assert all(new_units[uid]["status"] == "not_arrived" for uid in arrivals)


def test_tobruk_research_chapters_are_contiguous_and_campaign_only():
    scenes = chapters() + [json.loads((DRAFTS / f"{name}.json").read_text(encoding="utf-8"))
                           for name in ("tobruk_siege_opening", "frontier_preparation", "brevity_frontier",
                                        "halfaya_counterstroke", "battleaxe_preparation", "battleaxe_frontier")]
    scenes.append(scenarios.load("frontier_stalemate_1941", DRAFTS))
    scenes.append(scenarios.load("tobruk_relief_1941", DRAFTS))
    scenes.append(scenarios.load("crusader_preparation_1941", DRAFTS))
    scenes.append(scenarios.load("crusader_linked_1941", DRAFTS))
    scenes.append(scenarios.load("cyrenaica_winter_1942", DRAFTS))
    scenes.append(scenarios.load("axis_january_offensive_1942", DRAFTS))
    offensive = scenes[-1]["mission"]
    assert offensive["cw"]["success_grade"] == "tactical"
    assert {o["place"] for o in offensive["cw"]["orders"]} == {"Gazala", "Tobruk", "Mersa Matruh"}
    assert {o["place"] for o in offensive["axis"]["orders"]} == {"Agedabia", "Benghazi"}
    for current, following in zip(scenes, scenes[1:]):
        assert current["research_next"] == following["id"]
        assert date.fromisoformat(current["start"]) + timedelta(
            days=S.turn_days(current) * current["turns"]) == date.fromisoformat(following["start"])
        assert checker.problems(following, GMAP) == []
    assert scenes[3]["turn_days"] == 2 and scenes[4]["turn_days"] == 1
    for scene in scenes[3:]:
        with pytest.raises(ValueError, match="played campaign chapter"):
            campaign.start(scene, GMAP)


def test_linked_trace_carries_actual_control_into_february_1942():
    scenes = chapters()
    players = {side: computer.ComputerHard(GMAP) for side in S.SIDES}
    final, records = campaign.play(scenes, GMAP, players, seed=1940, check=True)
    assert [r["scenario"] for r in records] == list(NAMES)
    assert [h["scenario"] for h in final["campaign"]["history"]] == list(NAMES[:-1])
    assert final["places"]["Bardia"] == "axis" and final["places"]["Tobruk"] == "cw"
    assert all(S.unit(final, uid) is not None for uid in (190, 191, 192, 193, 194, 195, 196))
    assert S.unit(final, 206)["status"] == "on_map"
    assert S.unit(final, 354)["status"] == "on_map" and S.unit(final, 354)["hex"] == [55, 10]
    assert final["result"]["winner"] == "cw"
    siege = json.loads((DRAFTS / "tobruk_siege_opening.json").read_text(encoding="utf-8"))
    assert checker.problems(siege, GMAP) == []
    carried = campaign.handoff(final, scenes[-1], siege, GMAP, record=records[-1]["orders"])
    assert carried["scenario"] == "tobruk_siege_opening" and carried["turn"] == 1
    assert carried["places"] == final["places"] and carried["forts"] == final["forts"]
    assert carried["ports"] == final["ports"] and carried["tripoli"] == final["tripoli"]
    assert carried["units"] == final["units"]
    assert carried["campaign"]["history"][-1]["scenario"] == "cyrenaica_reversal"
    assert (carried["campaign"]["history"][-1]["result"]["mission"]["checks"]["cw"]["commendations"]
            == final["result"]["mission"]["checks"]["cw"]["commendations"])
    siege_end, siege_orders = runner.play(siege, GMAP, players, initial_state=carried, check=True)
    assert siege_end["over"] and siege_end["turn"] == siege["turns"] + 1
    assert len(siege_orders) == siege["turns"]
    prep = json.loads((DRAFTS / "frontier_preparation.json").read_text(encoding="utf-8"))
    prepared = campaign.handoff(siege_end, siege, prep, GMAP, record=siege_orders)
    assert prepared["places"] == siege_end["places"]
    assert all(S.unit(prepared, uid)["status"] == "not_arrived" for uid in (370, 371, 372, 373))
    prep_end, prep_orders = runner.play(prep, GMAP, players, initial_state=prepared, check=True)
    brevity = json.loads((DRAFTS / "brevity_frontier.json").read_text(encoding="utf-8"))
    frontier = campaign.handoff(prep_end, prep, brevity, GMAP, record=prep_orders)
    assert frontier["places"] == prep_end["places"]
    assert all(S.unit(frontier, uid)["steps"] == S.unit(prep_end, uid)["steps"]
               for uid in (370, 371, 372, 373))
    frontier_end, frontier_orders = runner.play(brevity, GMAP, players, initial_state=frontier, check=True)
    assert frontier_end["over"] and len(frontier_orders) == brevity["turns"]
    halfaya = json.loads((DRAFTS / "halfaya_counterstroke.json").read_text(encoding="utf-8"))
    halfaya_state = campaign.handoff(frontier_end, brevity, halfaya, GMAP, record=frontier_orders)
    assert halfaya_state["places"] == frontier_end["places"]
    halfaya_end, halfaya_orders = runner.play(halfaya, GMAP, players, initial_state=halfaya_state, check=True)
    buildup = json.loads((DRAFTS / "battleaxe_preparation.json").read_text(encoding="utf-8"))
    buildup_state = campaign.handoff(halfaya_end, halfaya, buildup, GMAP, record=halfaya_orders)
    assert all(S.unit(buildup_state, uid)["status"] == "not_arrived"
               for uid in (210, 211, 380, 381, 382, 383, 384))
    buildup_end, buildup_orders = runner.play(buildup, GMAP, players, initial_state=buildup_state, check=True)
    assert all(S.unit(buildup_end, uid)["status"] != "not_arrived"
               for uid in (210, 211, 380, 381, 382, 383, 384))
    battleaxe = json.loads((DRAFTS / "battleaxe_frontier.json").read_text(encoding="utf-8"))
    battle_state = campaign.handoff(buildup_end, buildup, battleaxe, GMAP, record=buildup_orders)
    assert battle_state["places"] == buildup_end["places"]
    assert all(S.unit(battle_state, uid)["steps"] == S.unit(buildup_end, uid)["steps"]
               for uid in (210, 211, 380, 381, 382, 383, 384))
    battle_end, battle_orders = runner.play(battleaxe, GMAP, players, initial_state=battle_state, check=True)
    assert battle_end["over"] and len(battle_orders) == battleaxe["turns"]
    stalemate = scenarios.load("frontier_stalemate_1941", DRAFTS)
    assert stalemate["id"] == "frontier_stalemate_1941"
    prepared = campaign.handoff(battle_end, battleaxe, stalemate, GMAP, record=battle_orders)
    assert prepared["places"] == battle_end["places"]
    assert prepared["ports"] == battle_end["ports"] and prepared["tripoli"] == battle_end["tripoli"]
    assert prepared["units"] == battle_end["units"]
    summer_end, summer_orders = runner.play(stalemate, GMAP, players, initial_state=prepared, check=True)
    assert summer_end["over"] and len(summer_orders) == 22
    assert summer_end["campaign"]["history"][-1]["scenario"] == "battleaxe_frontier"
    relief = scenarios.load("tobruk_relief_1941", DRAFTS)
    relief_state = campaign.handoff(summer_end, stalemate, relief, GMAP, record=summer_orders)
    assert relief_state["places"] == summer_end["places"]
    assert relief_state["ports"] == summer_end["ports"] and relief_state["tripoli"] == summer_end["tripoli"]
    assert S.unit(relief_state, 390)["status"] == "not_arrived"
    assert all(S.unit(relief_state, uid) == S.unit(summer_end, uid) for uid in (354, 350, 351, 352, 353))
    relief_end, relief_orders = runner.play(relief, GMAP, players, initial_state=relief_state, check=True)
    assert relief_end["over"] and len(relief_orders) == 30
    assert S.unit(relief_end, 390)["status"] != "not_arrived"
    preparation = scenarios.load("crusader_preparation_1941", DRAFTS)
    next_state = campaign.handoff(relief_end, relief, preparation, GMAP, record=relief_orders)
    assert next_state["places"] == relief_end["places"]
    assert next_state["ports"] == relief_end["ports"] and next_state["tripoli"] == relief_end["tripoli"]
    assert all(S.unit(next_state, uid) == S.unit(relief_end, uid) for uid in (350, 351, 352, 353, 354, 390))
    end, orders = runner.play(preparation, GMAP, players, initial_state=next_state, check=True)
    assert end["over"] and len(orders) == 49
    assert all(S.unit(end, uid)["status"] != "not_arrived" for uid in (391, 392, 393, 394, 395))
    if S.unit(end, 351)["name"] == "2/13th Australian Infantry Battalion":
        assert S.unit(end, 351)["size"] == 1 and S.unit(end, 351)["max"] == 1
    crusader = scenarios.load("crusader_linked_1941", DRAFTS)
    crusader_state = campaign.handoff(end, preparation, crusader, GMAP, record=orders)
    assert crusader_state["places"] == end["places"]
    assert crusader_state["ports"] == end["ports"] and crusader_state["tripoli"] == end["tripoli"]
    assert all(S.unit(crusader_state, uid) == S.unit(end, uid) for uid in (101, 301, 350, 351, 390, 391, 392))
    assert all(S.unit(crusader_state, uid)["status"] == "not_arrived" for uid in (400, 401, 410, 411, 412, 413, 420, 421, 422, 430, 431))
    crusader_end, crusader_orders = runner.play(crusader, GMAP, players, initial_state=crusader_state, check=True)
    assert crusader_end["over"] and len(crusader_orders) == 22
    assert all(S.unit(crusader_end, uid)["status"] != "not_arrived" for uid in (400, 401, 410, 411, 412, 413, 420, 421, 422, 430, 431))
    winter = scenarios.load("cyrenaica_winter_1942", DRAFTS)
    winter_state = campaign.handoff(crusader_end, crusader, winter, GMAP, record=crusader_orders)
    assert_handoff_keeps_played_state(crusader_end, winter_state, (460, 461, 462))
    winter_end, winter_orders = runner.play(winter, GMAP, players, initial_state=winter_state, check=True)
    offensive = scenarios.load("axis_january_offensive_1942", DRAFTS)
    offensive_state = campaign.handoff(winter_end, winter, offensive, GMAP, record=winter_orders)
    assert_handoff_keeps_played_state(winter_end, offensive_state, (440,))
    offensive_end, offensive_orders = runner.play(offensive, GMAP, players, initial_state=offensive_state, check=True)
    assert offensive_end["over"] and len(offensive_orders) == 19


def test_december_australian_evacuates_only_the_relief_remnant():
    scene = scenarios.load("crusader_linked_1941", DRAFTS)
    invalid = json.loads(json.dumps(scene))
    invalid["withdrawals"][0]["if_name"] = "A different formation"
    assert any("conditional name" in issue for issue in checker.problems(invalid, GMAP))
    row = next(r for r in reinforce.timetable(scene, "cw") if r["date"] == "1941-12-10")
    assert row["if_name"] == "2/13th Australian Infantry Battalion"
    game = S.new_game(scene, GMAP, seed=1)
    game["turn"] = S.turn_of(scene, "1941-12-10")
    game["places"]["Tobruk"] = "cw"
    unit = S.unit(game, 351)
    unit["status"] = "on_map"
    unit["hex"] = list(GMAP.places["Tobruk"]["hex"])
    reinforce.reinforcement_phase(game, GMAP, scene)
    assert unit["status"] == "on_map" and unit["name"] == "20th Australian Infantry Brigade"
    unit["name"] = "2/13th Australian Infantry Battalion"
    reinforce.reinforcement_phase(game, GMAP, scene)
    assert unit["status"] == "withdrawn"


def test_old_bardia_save_discovers_a_new_checked_successor():
    scenes = chapters()
    players = {side: computer.ComputerHard(GMAP) for side in S.SIDES}
    session = Session(scenes[0], GMAP, humans=[], scripted=players,
                      initial_state=campaign.start(scenes[0], GMAP, seed=1940))
    for following in scenes[1:3]:
        while not session.state["over"]:
            session.done()
        session = session.continue_campaign(following)
    while not session.state["over"]:
        session.done()
    session.scenario.pop("research_next", None)
    assert session.following_chapter()["id"] == "tobruk_approach"
    next_session = session.continue_campaign(session.following_chapter())
    assert next_session.state["campaign"]["history"][-1]["scenario"] == "bardia_assault"
    assert Session.from_save(next_session.to_save(), GMAP).to_save() == next_session.to_save()
