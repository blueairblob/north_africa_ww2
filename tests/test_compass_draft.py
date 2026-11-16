"""Research gate for Compass; this draft is intentionally outside the review menu."""
import json
import subprocess
import sys
from pathlib import Path

from engine import checker, computer, players, runner, scenarios
from engine import state as S
from engine.turn import begin_turn
from helpers import GMAP
from screen import saves
from screen.session import Session


DRAFT = Path(__file__).resolve().parents[1] / "data" / "scenario_drafts" / "compass_opening.json"
ROOT = DRAFT.parents[2]


def draft():
    return json.loads(DRAFT.read_text(encoding="utf-8"))


def test_compass_draft_is_legal_supplied_and_not_a_review_scenario():
    sc = draft()
    assert "compass_opening" not in scenarios.names()
    assert checker.problems(sc, GMAP) == []
    opening = begin_turn(S.new_game(sc, GMAP), GMAP, sc)
    assert all(u["traced"] for u in S.on_map(opening))
    assert sc["turn_days"] == 1 and sc["turns"] == 8
    assert [S.turn_of(sc, w["date"]) for w in sc["withdrawals"]] == [6] * 4
    assert {w["unit"] for w in sc["withdrawals"]} == {302, 303, 304, 307}
    assert next(u for u in sc["units"] if u["id"] == 305)["parent"] == 301
    assert all(w["unit"] not in {305, 306} for w in sc["withdrawals"])


def test_compass_daily_trial_reaches_sidi_with_the_indian_withdrawal():
    sc = draft()
    for opponent in (players.DoNothing, computer.ComputerOpponent):
        state, record = runner.play(sc, GMAP, {"axis": opponent(GMAP), "cw": opponent(GMAP)}, seed=1940)
        assert state["over"] and len(record) == sc["turns"]
        assert all(S.unit(state, uid)["status"] == "withdrawn" for uid in (302, 303, 304, 307))
        assert S.unit(state, 305)["status"] == "on_map" and S.unit(state, 306)["status"] == "on_map"
    # The draft's date-sensitive result is tracked without claiming historical validation.
    assert state["places"]["Nibeiwa"] == "cw"
    assert state["mission_reached"]["cw"] == ["Nibeiwa"]
    assert state["places"]["Sidi Barrani"] == "cw"
    hard = {side: computer.ComputerHard(GMAP) for side in S.SIDES}
    third_day, _ = runner.play(sc, GMAP, hard, turns=3, seed=1940)
    assert third_day["places"]["Sidi Barrani"] == "cw"
    assert all(S.unit(third_day, uid)["status"] == "on_map" for uid in (302, 303, 304, 307))


def test_compass_draft_can_be_opened_and_saved_for_human_review(tmp_path):
    shot = tmp_path / "compass-trial.png"
    run = subprocess.run([sys.executable, "-m", "screen", "--trial", "compass_opening",
                          "--axis", "computer-hard", "--at", "Nibeiwa", "--shot", str(shot)],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert shot.exists() and shot.stat().st_size > 0
    session = Session(draft(), GMAP, humans=["cw"], scripted={"axis": players.ComputerHard(GMAP)}, seed=1940)
    restored = saves.read(saves.write(session, tmp_path), GMAP)
    assert restored.to_save() == session.to_save()
    assert restored.scenario["id"] == "compass_opening" and restored.scenario["turn_days"] == 1
