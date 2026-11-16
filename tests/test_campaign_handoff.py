"""A campaign chapter keeps the played war, not the next scenario's historical setup."""
from copy import deepcopy

import pytest

from engine import campaign, checker, mission, players, runner, state as S, victory
from helpers import GMAP, scenario, unit
from screen import saves
from screen.session import Session


def chapters():
    old_units = [unit(1, "cw", "foot", "Mersa Matruh"), unit(2, "axis", "foot", "Sidi Barrani")]
    first = scenario(old_units, id="first", name="First", turns=1)
    first["par"] = victory.par(first)
    following = scenario(old_units + [unit(3, "cw", "foot", "Mersa Matruh")],
                         id="following", name="Following", start="1941-11-20", turns=1)
    following["sides"]["axis"]["lift"][0][0] = "1941-11-20"
    following["sides"]["axis"]["air"][0][0] = "1941-11-20"
    for schedule in following["sides"]["cw"].values():
        schedule[0][0] = "1941-11-20"
    following["par"] = victory.par(following)
    return first, following


def chapter_after_withdrawal():
    first, second = chapters()
    second["sources"] = {"T": "Synthetic test schedule"}
    second["withdrawals"] = [{"date": second["start"], "unit": 1, "src": "T"}]
    third = scenario(second["units"][1:], id="third", name="Third",
                     start="1941-11-22", turns=1)
    for schedule in third["sides"]["axis"].values():
        schedule[0][0] = third["start"]
    for schedule in third["sides"]["cw"].values():
        schedule[0][0] = third["start"]
    third["par"] = victory.par(third)
    return first, second, third


def test_handoff_preserves_played_units_places_and_stocks_and_survives_save(tmp_path):
    first, following = chapters()
    assert not checker.problems(first, GMAP)
    assert not checker.problems(following, GMAP)
    finished, _ = runner.play(first, GMAP, {"axis": players.DoNothing(GMAP),
                                           "cw": players.DoNothing(GMAP)}, seed=1941)
    finished["units"][0]["steps"] -= 1
    finished["units"][0]["cohesion"] = 63
    finished["places"]["Buq Buq"] = "cw"
    before = deepcopy(finished)
    carried = campaign.handoff(finished, first, following, GMAP)
    assert finished == before
    assert carried["units"][0]["steps"] == before["units"][0]["steps"]
    assert carried["units"][0]["cohesion"] == 63
    assert carried["places"]["Buq Buq"] == "cw"
    assert carried["ports"] == before["ports"] and carried["tripoli"] == before["tripoli"]
    assert carried["campaign"]["history"][0]["result"] == before["result"]
    assert carried["scenario"] == "following" and carried["turn"] == 1 and not carried["over"]
    assert [u["id"] for u in carried["units"]] == [1, 2, 3]

    session = Session(following, GMAP, humans=["cw"],
                      scripted={"axis": players.DoNothing(GMAP)}, initial_state=carried)
    saved_path = saves.write(session, tmp_path, auto=True)
    assert saved_path.name == "following-north_africa-autosave.json"
    loaded = saves.read(saved_path, GMAP)
    assert loaded.to_save() == session.to_save()
    assert "north_africa campaign" in saves.about(loaded.to_save())
    session.done()
    loaded.done()
    assert loaded.to_save() == session.to_save()


def test_preservation_order_uses_played_chapter_entry_strength():
    first, following = chapters()
    order = {"verb": "preserve", "units": [1, 3], "minimum_pct": 75,
             "label": "the mobile force"}
    following["mission"] = {"routes": {}, "cw": {"orders": [order]}}
    assert checker.problems(following, GMAP) == []
    finished, _ = runner.play(first, GMAP, {side: players.DoNothing(GMAP) for side in S.SIDES})
    S.unit(finished, 1)["steps"] = 3
    carried = campaign.handoff(finished, first, following, GMAP)
    assert carried["mission_baseline"]["cw"] == {"1": 3, "3": 6}
    saved = Session(following, GMAP, humans=["cw"],
                    scripted={"axis": players.DoNothing(GMAP)}, initial_state=carried).to_save()
    assert Session.from_save(saved, GMAP).state["mission_baseline"] == carried["mission_baseline"]
    assert mission.met(carried, GMAP, "cw", order, following["mission"])
    S.unit(carried, 1)["steps"] = 1
    assert mission.met(carried, GMAP, "cw", order, following["mission"])
    S.unit(carried, 1)["steps"] = 0
    S.unit(carried, 1)["status"] = "destroyed"
    assert not mission.met(carried, GMAP, "cw", order, following["mission"])
    S.unit(carried, 3)["steps"] = 10
    assert not mission.met(carried, GMAP, "cw", order, following["mission"])


def test_handoff_refuses_to_skip_unmodeled_months_or_rename_a_unit():
    first, following = chapters()
    finished, _ = runner.play(first, GMAP, {"axis": players.DoNothing(GMAP),
                                           "cw": players.DoNothing(GMAP)}, seed=0)
    delayed = deepcopy(following)
    delayed["start"] = "1941-12-20"
    with pytest.raises(ValueError, match="gap needs its own resolver"):
        campaign.handoff(finished, first, delayed, GMAP)
    renamed = deepcopy(following)
    renamed["units"][0]["name"] = "another formation"
    with pytest.raises(ValueError, match="changes identity"):
        campaign.handoff(finished, first, renamed, GMAP)
    extended = deepcopy(first)
    extended["turns"] = 2
    with pytest.raises(ValueError, match="early chapter end"):
        campaign.handoff(finished, extended, following, GMAP)
    with pytest.raises(ValueError, match="one order record per turn"):
        campaign.handoff(finished, first, following, GMAP, record=[])


def test_handoff_keeps_an_explicitly_named_relief_remnant():
    first, following = chapters()
    finished, _ = runner.play(first, GMAP, {side: players.DoNothing(GMAP) for side in S.SIDES})
    S.unit(finished, 1)["name"] = "2/13th Battalion"
    following["units"][0]["alternate_names"] = ["2/13th Battalion"]
    carried = campaign.handoff(finished, first, following, GMAP)
    assert S.unit(carried, 1)["name"] == "2/13th Battalion"


def test_handoff_opens_new_landing_point_without_creating_stock():
    from engine import state as S
    from engine.turn import begin_turn

    first, following = chapters()
    following["units"] = deepcopy(first["units"])
    following["landing_points"] = {"Sollum": 200}
    following["ports"] = {"Sollum": {"fuel": 500, "stores": 500}}
    assert not checker.problems(following, GMAP)
    finished, _ = runner.play(first, GMAP, {side: players.DoNothing(GMAP) for side in S.SIDES})
    held = {side: S.holdings(finished, side) for side in S.SIDES}
    carried = campaign.handoff(finished, first, following, GMAP)
    assert carried["ports"]["Sollum"] == {"condition": 100, "fuel": 0, "stores": 0}
    assert {side: S.holdings(carried, side) for side in S.SIDES} == held
    shown = begin_turn(carried, GMAP, following)
    assert shown["ports"]["Sollum"]["fuel"] + shown["ports"]["Sollum"]["stores"] == 200


def test_computer_campaign_runs_both_chapters_from_carried_state():
    from engine import state as S

    first, following = chapters()
    participants = {side: players.ComputerOpponent(GMAP) for side in S.SIDES}
    final, records = campaign.play([first, following], GMAP, participants, seed=1941)
    assert final["over"] and final["scenario"] == "following"
    assert [r["scenario"] for r in records] == ["first", "following"]
    assert len(records[0]["orders"]) == len(records[1]["orders"]) == 1
    assert final["campaign"]["id"] == "north_africa"
    assert final["campaign"]["history"][0]["scenario"] == "first"
    assert final["campaign"]["history"][0]["result"] is not None
    assert final["campaign"]["history"][0]["orders"] == records[0]["orders"]
    assert [u["id"] for u in final["units"]] == [1, 2, 3]
    replayed, again = campaign.play([first, following], GMAP,
                                    {side: players.ComputerOpponent(GMAP) for side in S.SIDES}, seed=1941)
    assert S.dumps(replayed) == S.dumps(final) and again == records


def test_retired_formations_leave_later_rosters_without_losing_campaign_history(tmp_path):
    import pygame
    from engine import state as S
    from engine.view import view
    from screen.app import App

    first, second, third = chapter_after_withdrawal()
    assert not checker.problems(second, GMAP)
    assert not checker.problems(third, GMAP)
    participants = {side: players.DoNothing(GMAP) for side in S.SIDES}
    final, records = campaign.play([first, second, third], GMAP, participants, seed=1941)
    assert final["scenario"] == "third" and final["over"]
    assert [r["scenario"] for r in records] == ["first", "following", "third"]
    assert final["campaign"]["history"][1]["orders"] == records[1]["orders"]
    assert S.unit(final, 1)["status"] == "withdrawn"
    assert {u["id"] for u in view(final, GMAP, third, "cw")["units"]} == {3}
    assert not S.unit(final, 1)["hex"]
    assert not checker.problems(third, GMAP)

    prior, _ = campaign.play([first, second], GMAP,
                             {side: players.DoNothing(GMAP) for side in S.SIDES}, seed=1941)
    carried = campaign.handoff(prior, second, third, GMAP)
    session = Session(third, GMAP, humans=["cw"],
                      scripted={"axis": players.DoNothing(GMAP)}, initial_state=carried)
    restored = saves.read(saves.write(session, tmp_path), GMAP)
    assert restored.to_save() == session.to_save()
    pygame.init()
    app = App(restored, size=(900, 560))
    app.paint(pygame.Surface(app.size))
    restored.done()
    app.paint(pygame.Surface(app.size))


def test_handoff_rejects_omitted_active_unit_and_reused_retired_identity():
    from engine import state as S

    first, second, third = chapter_after_withdrawal()
    played, _ = campaign.play([first, second], GMAP,
                              {side: players.DoNothing(GMAP) for side in S.SIDES})
    assert S.unit(played, 1)["status"] == "withdrawn"
    active_missing = deepcopy(third)
    active_missing["units"] = [u for u in active_missing["units"] if u["id"] != 3]
    active_missing["par"] = victory.par(active_missing)
    with pytest.raises(ValueError, match="Active formation 3"):
        campaign.handoff(played, second, active_missing, GMAP)
    reused = deepcopy(third)
    reused["units"].append(unit(1, "cw", "foot", "Mersa Matruh", name="New formation"))
    reused["par"] = victory.par(reused)
    with pytest.raises(ValueError, match="changes identity"):
        campaign.handoff(played, second, reused, GMAP)


def test_human_session_continues_chapter_with_opponent_and_names(tmp_path):
    first, following = chapters()
    original = Session(first, GMAP, humans=["cw"],
                       scripted={"axis": players.ComputerHard(GMAP)},
                       initial_state=campaign.start(first, GMAP, seed=1941))
    original.names[1] = "Matruh guard"
    original.done()
    assert original.state["over"]
    continued = original.continue_campaign(following)
    assert continued.scenario["id"] == "following"
    assert continued.names == {1: "Matruh guard"}
    assert continued.humans == ["cw"]
    assert type(continued.scripted["axis"]) is players.ComputerHard
    assert continued.state["campaign"]["history"][0]["scenario"] == "first"
    assert continued.state["campaign"]["history"][0]["orders"] == original.record
    saved = saves.write(continued, tmp_path)
    loaded = saves.read(saved, GMAP)
    assert loaded.to_save() == continued.to_save()
    continued.done()
    loaded.done()
    assert loaded.to_save() == continued.to_save()


def test_human_session_keeps_nondefault_campaign_identity():
    first, following = chapters()
    original = Session(first, GMAP, humans=["cw"],
                       scripted={"axis": players.DoNothing(GMAP)},
                       initial_state=campaign.start(first, GMAP, campaign_id="trial"))
    original.done()
    continued = original.continue_campaign(following)
    assert continued.state["campaign"]["id"] == "trial"
    assert continued.state["campaign"]["history"][0]["orders"] == original.record


@pytest.mark.parametrize("humans", [["cw"], []])
def test_result_screen_continues_only_into_checked_next_chapter(tmp_path, monkeypatch, humans):
    import pygame
    from engine import campaigns, scenarios
    from screen.app import App
    from screen.layout import campaign_continue

    first, following = chapters()
    scripted = {side: players.DoNothing(GMAP) for side in ("axis", "cw") if side not in humans}
    original = Session(first, GMAP, humans=humans, scripted=scripted,
                       initial_state=campaign.start(first, GMAP, campaign_id="trial"))
    original.done()
    assert original.state["over"]
    catalog = {"chapters": [{"scenario": "first", "status": "review"},
                            {"scenario": "following", "status": "review"}]}
    monkeypatch.setattr(campaigns, "load", lambda name: catalog)
    monkeypatch.setattr(scenarios, "load", lambda name: following)
    assert original.following_chapter() == following

    pygame.init()
    app = App(original, size=(900, 560))
    app.saves = tmp_path
    surface = pygame.Surface(app.size)
    app.paint(surface)
    app.click(campaign_continue(app.size).center)
    assert app.session.scenario["id"] == "following"
    assert app.session.humans == humans
    assert app.session.state["campaign"]["history"][0]["orders"] == original.record
    assert (tmp_path / "first-trial-autosave.json").exists()


def test_result_screen_hides_continuation_for_an_unmodeled_gap(monkeypatch):
    from engine import campaigns, scenarios

    first, following = chapters()
    delayed = deepcopy(following)
    delayed["start"] = "1941-12-20"
    original = Session(first, GMAP, humans=[],
                       scripted={side: players.DoNothing(GMAP) for side in ("axis", "cw")},
                       initial_state=campaign.start(first, GMAP, campaign_id="trial"))
    original.done()
    monkeypatch.setattr(campaigns, "load", lambda name: {"chapters": [
        {"scenario": "first", "status": "review"}, {"scenario": "following", "status": "review"}]})
    monkeypatch.setattr(scenarios, "load", lambda name: delayed)
    assert original.following_chapter() is None
