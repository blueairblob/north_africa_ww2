"""The Crusader scenario: checked, and played to the end by scripted players."""
import json

import pytest

from engine import checker, players, runner
from engine import state as S
from engine.turn import begin_turn, finish_turn
from helpers import GMAP, ROOT, small


def crusader():
    return json.loads((ROOT / "data" / "scenarios" / "crusader.json").read_text())


def test_the_scenarios_pass_the_checker():
    assert checker.problems(crusader(), GMAP) == []
    assert checker.problems(small(), GMAP) == []


def test_a_divisions_hq_feeds_its_units_and_builds_no_dump():                    # 20.1.5, 6.7.3
    sc = crusader()
    state = S.new_game(sc, GMAP)
    for _ in range(3):
        state = begin_turn(state, GMAP, sc)
        state["turn"] += 1
    u = {x["id"]: x for x in state["units"]}
    assert u[110]["dump"]["stores"] < 1000 and u[101]["dump"]["stores"] >= 2500    # a division's HQ; the Panzergruppe's


def test_the_checker_finds_what_is_wrong():
    sc = crusader()
    for n, where in ((0, [0, 0]), (1, [83, 43])):                # in the sea; on land nothing can leave
        sc["units"][n].pop("at", None)
        sc["units"][n]["hex"] = where
    sc["units"][2].pop("hex", None)
    sc["units"][2]["at"] = "Atlantis"
    sc["owners"]["axis"].remove("Bardia")
    sc["objectives"].append({"place": "Atlantis", "turn": 1})
    lost = dict(sc["units"][3], id=999, name="Lost division", at="Tobruk")     # an enemy in Tobruk
    lost.pop("hex", None)
    sc["units"].append(lost)
    sc["units"].append(dict(sc["units"][4]))                     # a repeated id
    found = "\n".join(checker.problems(sc, GMAP))
    for clue in ("unit 101", "unit 102", "Atlantis is not a place", "owners", "objective Atlantis",
                 "both sides start here", "used twice"):
        assert clue in found, clue


def test_everyone_starts_in_supply():                            # 6.6.4
    sc = crusader()
    state = begin_turn(S.new_game(sc, GMAP), GMAP, sc)
    assert [u["name"] for u in S.on_map(state) if not u["traced"]] == []


def test_the_scenario_runs_22_turns_from_18_november():          # 1.9
    sc = crusader()
    assert S.turn_of(sc, "1941-12-30") == sc["turns"] == 22 and len(sc["units"]) == 91


def test_crusader_shows_each_division_as_its_units_grouped_under_its_hq():       # 20.1, 20.2.1, 20.4
    sc = crusader()
    state = S.new_game(sc, GMAP)
    u = {x["id"]: x for x in state["units"]}
    assert [u[i]["group"] for i in (110, 111, 112, 113, 114)] == [110] * 5      # 15. Panzer-Division, in one hex
    assert u[142]["parent"] == 140 and u[142]["group"] is None                  # Savona's regiment at Capuzzo, apart
    assert u[111]["real"] == [133, "tanks", 13] and u[111]["steps"] == 13 and u[311]["steps"] == 17
    assert all(x["real"] and x.get("src") is None for x in state["units"] if x["type"] != "hq")
    assert all(spec["src"] in sc["sources"] for spec in sc["units"] if spec["type"] != "hq")
    tanks = {side: sum(x["real"][0] for x in state["units"] if x["side"] == side and x["real"] and x["real"][1] == "tanks")
             for side in S.SIDES}
    assert tanks == {"axis": 395, "cw": 680}


def test_crusaders_timetable_is_the_campaigns_and_every_date_names_its_source():  # 12.1, 12.7
    sc = crusader()
    name = {spec["id"]: spec["name"] for spec in sc["units"]}
    assert [(e["date"], name[e["unit"]]) for e in sc["withdrawals"]] == [
        ("1941-11-27", "7th Armoured Brigade"), ("1941-12-01", "2nd New Zealand Division"),
        ("1941-12-01", "4th New Zealand Brigade"), ("1941-12-01", "6th New Zealand Brigade"),
        ("1941-12-01", "New Zealand Divisional Artillery")]
    assert [(e["date"], name[e["unit"]], e["tanks"], e.get("via")) for e in sc["replacements"]] == [
        ("1941-11-27", "4th Armoured Brigade", 33, None), ("1941-12-06", "4th Armoured Brigade", 38, None),
        ("1941-12-22", "22nd Armoured Brigade", 60, None), ("1941-12-19", "Panzer-Regiment 8", 22, "Benghazi"),
        ("1941-12-27", "Panzer-Regiment 8", 23, None)]
    coming = [spec for spec in sc["units"] if "arrives" in spec]
    assert [(spec["arrives"], spec["entry"]) for spec in coming] == [("1941-12-02", "Buq Buq")] * 5
    assert [spec["name"] for spec in coming][0] == "2nd South African Division" and {spec.get("parent", 360) for spec in coming} == {360}
    dated = sc["withdrawals"] + sc["replacements"]
    assert all(e["src"] in sc["sources"] for e in dated) and all(spec["arrives_src"] in sc["sources"] for spec in coming)
    assert all("basis" in e for e in sc["replacements"])            # each size is worked out from the source, and says how


def test_the_timetable_falls_on_its_days_when_nobody_moves():                    # 12.2 to 12.4, 1.9
    sc = crusader()
    state = S.new_game(sc, GMAP)
    seen = {}
    for _ in range(sc["turns"]):
        state, _ = finish_turn(begin_turn(state, GMAP, sc), GMAP, sc, {})
        for e in state["log"]:
            if e["event"] in ("withdrawn", "arrived", "replaced", "not_replaced"):
                seen.setdefault((state["turn"] - 1, e["event"]), []).append(e["unit"])
    assert seen == {(5, "withdrawn"): [312], (5, "replaced"): [311], (7, "withdrawn"): [330, 331, 333, 334],
                    (8, "arrived"): [360, 361, 362, 363, 364], (10, "replaced"): [311], (16, "replaced"): [111],
                    (18, "replaced"): [313], (20, "replaced"): [111]}
    u = {x["id"]: x for x in state["units"]}
    assert u[332]["status"] == u[335]["status"] == "on_map" and u[360]["group"] == u[364]["group"] == 360


@pytest.mark.parametrize("axis, cw", [("nothing", "attack"), ("attack", "attack"), ("explore", "explore")])
def test_crusader_plays_to_the_end_with_the_invariants_holding(axis, cw):
    kinds = {"nothing": players.DoNothing, "attack": players.AlwaysAttack, "explore": players.Explore}
    state, record = runner.play(crusader(), GMAP, {"axis": kinds[axis](GMAP), "cw": kinds[cw](GMAP)})
    assert state["over"] and len(record) == 22


def refused(axis, cw):
    """Play Crusader; the share of each side's orders the engine accepted, and the final state."""
    from engine.view import view
    from engine.turn import finish_turn
    sc = crusader()
    P = {"axis": players.SCRIPTED[axis](GMAP), "cw": players.SCRIPTED[cw](GMAP)}
    state, given, taken = S.new_game(sc, GMAP), {s: 0 for s in S.SIDES}, {s: 0 for s in S.SIDES}
    while not state["over"]:
        state = begin_turn(state, GMAP, sc)
        state, replies = finish_turn(state, GMAP, sc, {s: P[s].orders(view(state, GMAP, sc, s)) for s in S.SIDES})
        for s in S.SIDES:
            given[s] += len(replies[s])
            taken[s] += sum(r["ok"] for r in replies[s])
    return {s: taken[s] * 100 // max(1, given[s]) for s in S.SIDES}, state


def test_the_scripted_players_orders_are_accepted_and_they_change_the_game():
    share, fought = refused("attack", "retreat")
    assert share["axis"] >= 90 and share["cw"] >= 90, share          # they order groups as groups (20.2.5)
    _, still = refused("nothing", "nothing")
    _, pushed = refused("attack", "nothing")
    place = lambda st: sorted((u["id"], u["hex"], u["steps"]) for u in st["units"])
    assert place(pushed) != place(still)                             # an attacker is not the same as nobody
    assert sum(u["status"] == "destroyed" for u in fought["units"]) + sum(u["status"] == "destroyed" for u in pushed["units"]) > 0
