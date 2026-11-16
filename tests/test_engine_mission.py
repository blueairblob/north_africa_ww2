"""High Command verbs use the map and units, not points or stale place ownership."""
from copy import deepcopy
import json
from pathlib import Path

from engine import checker, mission, scenarios, state as S
from engine.victory import result_for
from helpers import GMAP
from screen.draw import result_assessment


def test_sidi_rezegh_track_is_a_vehicle_pass_but_northern_cliff_still_constrains():
    assert GMAP.side_between((56, 13), (57, 12)) in GMAP.passes
    assert not GMAP.cliff_between((56, 13), (57, 12))
    assert GMAP.cliff_between((56, 12), (56, 11))


def at(side, h):
    return {"side": side, "status": "on_map", "hex": list(h)}


def position():
    return {"sides": {"axis": {"vp": 99}, "cw": {"vp": 106}},
            "places": {"Sidi Rezegh": "axis", "Belhamed": "axis", "Tobruk": "cw"},
            "units": [at("axis", (57, 11)), at("cw", (55, 10))]}


def test_the_reported_sidi_rezegh_position_is_an_axis_mission_victory():
    sc, state = scenarios.load("sidi_rezegh"), position()
    verdict = result_for(state, sc, GMAP)
    assert (verdict["winner"], verdict["grade"], verdict["margin"]) == ("axis", "tactical", -47)
    assert [c["met"] for c in verdict["mission"]["checks"]["cw"]["checks"]] == [False, False, False]
    assert verdict["mission"]["checks"]["axis"]["complete"]


def test_a_relief_victory_needs_occupied_places_and_an_unblocked_corridor():
    sc, state = scenarios.load("sidi_rezegh"), position()
    state["units"] = [at("cw", (56, 13)), at("cw", (57, 12)), at("cw", (55, 10))]
    state["places"].update({"Sidi Rezegh": "cw", "Belhamed": "cw"})
    verdict = result_for(state, sc, GMAP)
    assert verdict["winner"] == "cw" and verdict["grade"] == "major"
    assert verdict["mission"]["checks"]["cw"]["complete"]
    state["units"].append(at("axis", (57, 11)))
    verdict = result_for(state, sc, GMAP)
    assert verdict["winner"] == "axis" and verdict["grade"] == "tactical"
    state["units"] = [at("cw", (55, 10))]  # clear but neither side achieves its orders
    assert result_for(state, sc, GMAP)["grade"] == "draw"


def test_hold_requires_occupation_reach_persists_and_surround_checks_all_neighbours():
    sc = scenarios.load("sidi_rezegh")
    state = position()
    hold = {"verb": "hold", "place": "Sidi Rezegh"}
    state["places"]["Sidi Rezegh"] = "cw"
    assert not mission.met(state, GMAP, "cw", hold, sc["mission"])
    state["units"].append(at("cw", (56, 13)))
    assert mission.met(state, GMAP, "cw", hold, sc["mission"])
    sc["mission"]["cw"]["orders"] = [{"verb": "reach", "place": "Sidi Rezegh"}]
    mission.record_reached(state, sc, GMAP)
    state["units"].pop()
    assert mission.met(state, GMAP, "cw", sc["mission"]["cw"]["orders"][0], sc["mission"])
    state["units"] = [at("axis", (56, 13))] + [at("cw", h) for _, h, _ in GMAP.around((56, 13))]
    surround = {"verb": "surround", "place": "Sidi Rezegh"}
    assert mission.met(state, GMAP, "cw", surround, sc["mission"])
    state["units"].pop()
    assert not mission.met(state, GMAP, "cw", surround, sc["mission"])


def test_staging_order_needs_a_fighting_unit_on_the_marked_hex():
    sc = scenarios.load("sidi_rezegh")
    order = {"verb": "stage", "hex": [66, 13], "label": "Bardia western approach"}
    sc["mission"]["cw"]["orders"] = [order]
    assert mission.problems(sc, GMAP) == []
    state = {"units": [{"side": "cw", "status": "on_map", "type": "hq", "hex": [66, 13]}]}
    assert not mission.met(state, GMAP, "cw", order, sc["mission"])
    state["units"].append({"side": "cw", "status": "on_map", "type": "foot", "hex": [66, 13]})
    assert mission.met(state, GMAP, "cw", order, sc["mission"])
    bad = deepcopy(sc)
    bad["mission"]["cw"]["orders"][0]["hex"] = [66, 12, 11]
    assert any("stage needs" in problem for problem in mission.problems(bad, GMAP))


def test_breach_is_recorded_when_fighting_troops_end_a_turn_on_the_perimeter():
    sc = scenarios.load("sidi_rezegh")
    order = {"verb": "breach", "hex": [66, 13], "label": "western Bardia perimeter"}
    sc["mission"]["cw"]["orders"] = [order]
    assert mission.problems(sc, GMAP) == []
    state = {"units": [{"side": "cw", "status": "on_map", "type": "hq", "hex": [66, 13]}]}
    mission.record_reached(state, sc, GMAP)
    assert not mission.met(state, GMAP, "cw", order, sc["mission"])
    state["units"].append({"side": "cw", "status": "on_map", "type": "foot", "hex": [66, 13]})
    mission.record_reached(state, sc, GMAP)
    state["units"].pop()
    order["label"] = "an edited western perimeter description"
    assert mission.met(state, GMAP, "cw", order, sc["mission"])
    bad = deepcopy(sc)
    bad["mission"]["cw"]["orders"][0]["hex"] = [66, 13, 12]
    assert any("breach needs" in problem for problem in mission.problems(bad, GMAP))


def test_a_route_must_follow_its_named_places_and_declared_terrain():
    sc = scenarios.load("sidi_rezegh")
    assert mission.problems(sc, GMAP) == []
    sc["mission"]["routes"]["Coast approach"] = {
        "terrain": "road", "from": "Tobruk", "via": [], "to": "Gambut",
        "hexes": [[55, 10], [56, 11], [57, 11], [58, 12], [59, 11], [60, 12], [61, 12]]}
    rail = list(reversed(GMAP.rail[GMAP.rail.index(GMAP.places["Fort Capuzzo"]["hex"]):
                                   GMAP.rail.index(GMAP.places["Belhamed"]["hex"]) + 1]))
    sc["mission"]["routes"]["Rail approach"] = {
        "terrain": "rail", "from": "Belhamed", "via": [], "to": "Fort Capuzzo",
        "hexes": [list(h) for h in rail]}
    assert mission.problems(sc, GMAP) == []
    bad = deepcopy(sc)
    bad["mission"]["routes"]["Tobruk relief corridor"]["terrain"] = "road"
    assert any("not all road" in problem for problem in mission.problems(bad, GMAP))
    bad = deepcopy(sc)
    bad["mission"]["routes"]["Tobruk relief corridor"]["hexes"][2] = [70, 24]
    assert any("touch" in problem for problem in mission.problems(bad, GMAP))
    bad = deepcopy(sc)
    bad["mission"]["routes"]["Tobruk relief corridor"]["hexes"][2] = [56, 12]
    assert any("cannot be traversed by vehicles" in problem for problem in mission.problems(bad, GMAP))


def test_optional_commendation_uses_actual_strength_without_changing_victory():
    path = Path(__file__).resolve().parents[1] / "data/scenario_drafts/cyrenaica_reversal.json"
    sc = json.loads(path.read_text(encoding="utf-8"))
    assert checker.problems(sc, GMAP) == []
    state = S.new_game(sc, GMAP)
    order = sc["mission"]["cw"]["commendations"][0]["order"]
    original = mission.preserve_progress(state, "cw", order)[1]
    assert original > 0
    assert mission.assessment(state, sc, GMAP)["cw"]["commendations"][0]["met"]
    earned = result_for(state, sc, GMAP)
    assert any("High Command commendation" in line for line in
               result_assessment({"places": state["places"], "result": earned}, sc))
    for uid in order["units"]:
        S.unit(state, uid)["steps"] = 0
        S.unit(state, uid)["status"] = "destroyed"
    missed = result_for(state, sc, GMAP)
    assert (missed["winner"], missed["grade"], missed["margin"]) == (
        earned["winner"], earned["grade"], earned["margin"])
    assert not missed["mission"]["checks"]["cw"]["commendations"][0]["met"]
    assert not any("High Command commendation" in line for line in
                   result_assessment({"places": state["places"], "result": missed}, sc))
