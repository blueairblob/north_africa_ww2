"""An explicit quiet-period advance uses ordinary turns and stops at decisions."""
import json

import pytest

pygame = pytest.importorskip("pygame")

from engine import campaign, checker, players, state as S, victory  # noqa: E402
from engine.view import view  # noqa: E402
from helpers import GMAP, scenario, unit  # noqa: E402
from screen.app import App  # noqa: E402
from screen.session import Session  # noqa: E402


def session(extra=()):
    scene = scenario([unit(1, "cw", "foot", "Tobruk"),
                      unit(2, "axis", "foot", "El Agheila"), *extra])
    scene["sources"] = {"T": "Synthetic arrival for fast-advance coverage"}
    scene["par"] = victory.par(scene)
    assert checker.problems(scene, GMAP) == []
    return Session(scene, GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)},
                   initial_state=campaign.start(scene, GMAP))


def test_five_turn_advance_keeps_normal_records_and_can_stop_early():
    game = session()
    count, reason = game.advance_quiet(limit=2)
    assert (count, reason) == (2, "2 quiet turns passed. Review your orders.")
    assert game.state["turn"] == 3 and len(game.record) == 2


def test_advance_stops_at_a_dated_friendly_arrival():
    arriving = unit(3, "cw", "foot", "Mersa Matruh")
    arriving.pop("at")
    arriving.update(entry="Mersa Matruh", arrives="1941-11-20", arrives_src="T")
    game = session([arriving])
    count, reason = game.advance_quiet()
    assert count == 2 and "arrival" in reason
    assert S.unit(game.state, 3)["status"] == "on_map" and len(game.record) == 2


def test_advance_refuses_visible_enemy_and_one_turn_order():
    game = session()
    S.unit(game.state, 2)["hex"] = [56, 11]
    game.views = {s: view(game.state, GMAP, game.scenario, s) for s in S.SIDES}
    assert game.advance_quiet()[0] == 0
    game = session()
    assert game.give({"unit": 1, "order": "rest"})["ok"]
    assert game.advance_quiet()[0] == 0
    assert game.state["turn"] == 1 and not game.record


def test_f6_uses_autosaves_for_each_quiet_turn(tmp_path):
    game = session()
    app = App(game, size=(900, 560))
    app.saves = tmp_path
    assert app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F6))
    assert game.state["turn"] > 1
    saves = list(tmp_path.glob("*-autosave.json"))
    assert len(saves) == 1
    saved = json.loads(saves[0].read_text())
    assert saved["state"]["turn"] == game.state["turn"]
