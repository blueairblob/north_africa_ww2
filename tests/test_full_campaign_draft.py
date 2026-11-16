"""The open campaign's first and last research chapters stay linked."""
from datetime import date, timedelta
from pathlib import Path

from engine import campaign, checker, reinforce, runner, scenarios, state as S, victory
from helpers import GMAP


DRAFTS = Path(__file__).resolve().parents[1] / "data" / "scenario_drafts"


def test_september_opening_places_sourced_forces():
    opening_scene = scenarios.load("italian_frontier_1940", DRAFTS)
    opening = campaign.start(opening_scene, GMAP)
    assert opening["places"]["Sidi Barrani"] == "cw"
    assert opening["places"]["Sollum"] == "cw"
    assert opening["places"]["Bardia"] == "axis"
    assert S.unit(opening, 140)["hex"] == [55, 10]  # 4th Blackshirt reserve at Tobruk
    assert S.unit(opening, 170)["hex"] == [56, 12]  # 64th Catanzaro reserve nearby
    assert S.unit(opening, 312)["hex"] == [68, 16]  # Support Group on the frontier


def test_research_chain_has_no_date_gap_through_november_1942():
    names = []
    current = "italian_frontier_1940"
    while current:
        assert current not in names
        names.append(current)
        scene = scenarios.load(current, DRAFTS)
        assert checker.problems(scene, GMAP) == []
        successor = scene.get("research_next")
        if successor:
            next_scene = scenarios.load(successor, DRAFTS)
            assert date.fromisoformat(scene["start"]) + timedelta(days=scene["turn_days"] * scene["turns"]) == date.fromisoformat(next_scene["start"])
        current = successor
    assert names[-1] == "november_pursuit_1942"
    assert len(names) == 33
    assert date.fromisoformat(scene["start"]) + timedelta(days=scene["turn_days"] * scene["turns"]) == date(1942, 12, 1)


def test_documented_later_arrivals_are_absent_before_their_entry_chapters():
    frontier = scenarios.load("italian_frontier_1940", DRAFTS)
    invasion = scenarios.load("italian_invasion_1940", DRAFTS)
    camps = scenarios.load("italian_camps_1940", DRAFTS)
    assert all(306 not in {unit["id"] for unit in scene["units"]} for scene in (frontier, invasion))
    assert next(unit for unit in camps["units"] if unit["id"] == 306)["arrives"] == "1940-09-24"
    assert [row["unit"] for row in reinforce.timetable(camps, "cw") if row["date"] == "1940-09-24"] == [306]
    opening = S.new_game(camps, GMAP, seed=3)
    assert S.unit(opening, 306)["status"] == "not_arrived"
    opening["turn"] = S.turn_of(camps, "1940-09-24")
    reinforce.reinforcement_phase(opening, GMAP, camps)
    assert S.unit(opening, 306)["status"] == "on_map"
    early = scenarios.load("frontier_stalemate_1941", DRAFTS)
    relief = scenarios.load("tobruk_relief_1941", DRAFTS)
    crusader = scenarios.load("crusader_linked_1941", DRAFTS)
    gazala = scenarios.load("gazala_preparation_1942", DRAFTS)
    assert 480 not in {unit["id"] for unit in early["units"]}
    assert next(unit for unit in relief["units"] if unit["id"] == 480)["arrives"] == "1941-09-01"
    mobile = S.new_game(relief, GMAP, seed=3)
    assert S.unit(mobile, 480)["status"] == "not_arrived"
    mobile["turn"] = S.turn_of(relief, "1941-09-01")
    reinforce.reinforcement_phase(mobile, GMAP, relief)
    assert S.unit(mobile, 480)["status"] == "on_map"
    assert all(480 in {unit["id"] for unit in scene["units"]} for scene in (crusader, gazala))
    assert "TR41" in gazala["sources"] and "RTR40" in camps["sources"]
    assert {481, 482}.isdisjoint({unit["id"] for unit in scenarios.load("crusader_preparation_1941", DRAFTS)["units"]})
    assert {481, 482} <= {unit["id"] for unit in crusader["units"]}
    assert "CR41" in crusader["sources"] and "CR41" in gazala["sources"]
    opening_crusader = S.new_game(crusader, GMAP, seed=3)
    reinforce.reinforcement_phase(opening_crusader, GMAP, crusader)
    assert all(S.unit(opening_crusader, uid)["status"] == "on_map" for uid in (481, 482))


def test_australian_greece_transfer_frees_roster_space_for_december_south_africans():
    relief = scenarios.load("tobruk_relief_1941", DRAFTS)
    preparation = scenarios.load("crusader_preparation_1941", DRAFTS)
    crusader = scenarios.load("crusader_linked_1941", DRAFTS)
    aussies = {330, 331, 332, 333, 334}
    assert aussies <= {unit["id"] for unit in relief["units"]}
    assert aussies.isdisjoint({unit["id"] for unit in preparation["units"]})
    assert {470, 471}.isdisjoint({unit["id"] for unit in preparation["units"]})
    assert {470, 471} <= {unit["id"] for unit in crusader["units"]}
    assert [row["unit"] for row in reinforce.timetable(crusader, "cw") if row["date"] == "1941-12-02"] == [470, 471]


def test_21st_panzer_redesignation_keeps_unit_identity_and_lost_units_lost():
    relief = scenarios.load("tobruk_relief_1941", DRAFTS)
    preparation = scenarios.load("crusader_preparation_1941", DRAFTS)
    assert checker.problems(relief, GMAP) == [] and checker.problems(preparation, GMAP) == []
    assert [row["unit"] for row in reinforce.timetable(relief, "axis")
            if row["kind"] == "redesignation"] == [201, 202, 203, 204]
    game = S.new_game(relief, GMAP, seed=3)
    prior_steps = {uid: S.unit(game, uid)["steps"] for uid in (201, 202, 203, 204)}
    lost = S.unit(game, 203)
    lost.update(status="destroyed", steps=0, hex=None, fate={"cause": "combat", "turn": 1})
    game["turn"] = S.turn_of(relief, "1941-08-15")
    reinforce.reinforcement_phase(game, GMAP, relief)
    for uid in (201, 202, 204):
        assert S.unit(game, uid)["name"].startswith("21st Panzer Division")
        assert S.unit(game, uid)["steps"] == prior_steps[uid]
        assert next(unit for unit in preparation["units"] if unit["id"] == uid)["name"] == S.unit(game, uid)["name"]
    assert lost["name"] == "5th Light Division anti-tank guns" and lost["status"] == "destroyed"
    assert next(unit for unit in preparation["units"] if unit["id"] == 203)["alternate_names"] == [lost["name"]]


def test_1942_missing_formations_join_in_sourced_periods_without_exceeding_counter_limit():
    from engine.checker import COUNTERS

    gazala = scenarios.load("gazala_preparation_1942", DRAFTS)
    alamein = scenarios.load("alamein_preparation_1942", DRAFTS)
    finale = scenarios.load("second_alamein_1942", DRAFTS)
    assert next(unit for unit in gazala["units"] if unit["id"] == 473)["arrives"] == "1942-05-01"
    assert {474, 475, 476}.isdisjoint({unit["id"] for unit in gazala["units"]})
    assert [row["unit"] for row in reinforce.timetable(alamein, "cw") if row["date"] == "1942-09-14"] == [474, 475, 476]
    assert {474, 475, 476} <= {unit["id"] for unit in finale["units"]}
    assert sum(unit["side"] == "cw" for unit in finale["units"]) <= COUNTERS


def test_withdrawn_australian_division_returns_by_identity_but_destroyed_unit_does_not():
    scene = scenarios.load("first_alamein_1942", DRAFTS)
    assert checker.problems(scene, GMAP) == []
    timetable = reinforce.timetable(scene, "cw")
    assert [row["unit"] for row in timetable if row["date"] == "1942-07-04"] == [350, 351, 352, 353]
    assert all(row["date"] >= scene["start"] for row in timetable)
    game = S.new_game(scene, GMAP, seed=1)
    game["turn"] = S.turn_of(scene, "1942-07-04")
    for uid in (350, 351, 352):
        unit = S.unit(game, uid)
        unit.update(status="withdrawn", hex=None, fuel=0, stores=0, fate={"cause": "withdrawn", "turn": 1})
    remnant = S.unit(game, 351)
    remnant.update(name="2/13th Australian Infantry Battalion", size=1, steps=1, max=1,
                   real=[800, "men", 1])
    lost = S.unit(game, 353)
    lost.update(status="destroyed", hex=None, steps=0, fuel=0, stores=0,
                fate={"cause": "combat", "turn": 1})
    reinforce.reinforcement_phase(game, GMAP, scene)
    assert all(S.unit(game, uid)["status"] == "on_map" for uid in (350, 351, 352))
    assert remnant["name"] == "20th Australian Infantry Brigade" and remnant["size"] == 2
    assert remnant["steps"] > 1 and remnant["fate"] is None
    assert lost["status"] == "destroyed" and lost["steps"] == 0


def test_final_campaign_assessment_uses_strategic_holdings_and_history():
    scene = scenarios.load("november_pursuit_1942", DRAFTS)
    game = S.new_game(scene, GMAP, seed=1)
    game["campaign"] = {"id": "north_africa", "history": [
        {"result": {"mission": {"checks": {"cw": {"complete": True}, "axis": {"complete": False}}}}}]}
    chapter = {"winner": None, "grade": "draw", "margin": 0,
               "mission": {"checks": {"cw": {"complete": True}, "axis": {"complete": False}}}}
    for place in ("Alexandria", "El Alamein", "Tobruk", "Sidi Barrani", "Benghazi"):
        game["places"][place] = "cw"
    assessed = victory.campaign_result(game, chapter)
    assert assessed["winner"] == "cw" and assessed["grade"] == "decisive"
    assert assessed["campaign"]["missions_met"] == {"cw": 2, "axis": 0}
    assert assessed["campaign"]["chapters"] == 2
    game["places"]["Alexandria"] = "axis"
    assessed = victory.campaign_result(game, chapter)
    assert assessed["winner"] == "axis" and assessed["grade"] == "decisive"


def test_finale_records_a_campaign_verdict_when_its_last_turn_resolves():
    scene = scenarios.load("november_pursuit_1942", DRAFTS)
    game = S.new_game(scene, GMAP, seed=7)
    game["campaign"] = {"id": "north_africa", "history": []}

    class NoOrders:
        def orders(self, view):
            return {}

    players = {side: NoOrders() for side in S.SIDES}
    finished, orders = runner.play(scene, GMAP, players, initial_state=game, check=True)
    assert finished["over"] and len(orders) == scene["turns"]
    assert finished["result"]["campaign"]["chapters"] == 1
    assert set(finished["result"]["campaign"]["places"]) == {
        "Alexandria", "El Alamein", "Mersa Matruh", "Sidi Barrani",
        "Bardia", "Tobruk", "Benghazi", "El Agheila"}
