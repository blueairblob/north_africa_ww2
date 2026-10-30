"""Two computer players can be watched in the pygame window without a human order."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from engine import invariants, players, scenarios
from helpers import GMAP
from screen.app import App
from screen.layout import playback_controls, title_button
from screen.replay import Playback, displayed_hex
from screen.session import Session


def spectators():
    return Session(scenarios.load("sidi_rezegh"), GMAP, humans=[],
                   scripted={side: players.ComputerOpponent(GMAP) for side in ("axis", "cw")}, seed=1941)


def test_spectator_match_advances_pauses_and_finishes_without_human_orders():
    pygame.init()
    session = spectators()
    app = App(session)
    app.title = True
    for _ in range(20):
        app.tick(50)
    assert session.state["turn"] == 1
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=title_button(app.size).center))
    for _ in range(14):
        app.tick(50)
    assert session.state["turn"] == 2 and app.play and app.fast
    controls = playback_controls(app.size, spectator=True)
    assert "pause" in controls
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=controls["pause"].center))
    clock = app.play_t
    for _ in range(20):
        app.tick(50)
    assert app.ui.playback_paused and app.play_t == clock
    app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    app.tick(50)
    assert not app.ui.playback_paused and app.play_t > clock
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=controls["speed"].center))
    assert not app.fast and not app.spectator_fast
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=controls["speed"].center))
    assert app.fast and app.spectator_fast

    for _ in range(10000):
        if session.state["over"] and not app.play:
            break
        app.tick(50)
    assert session.state["over"] and not app.play and len(session.record) == 5
    assert app.ui.message.startswith("Game over:")
    seen = []
    original = app.painter.text
    app.painter.text = lambda surface, words, *args, **kwargs: (seen.append(str(words)),
                                                               original(surface, words, *args, **kwargs))
    app.paint(pygame.Surface(app.size))
    assert "ORDERS FROM HIGH COMMAND" in seen and "FIELD ASSESSMENT" in seen
    assert any("VICTORY" in words for words in seen)
    assert {"United Kingdom", "New Zealand", "Union of South Africa"} <= {tip for _, tip in app.painter.tips}


def test_spectator_save_restores_both_computer_players():
    session = spectators()
    session.done()
    saved = session.to_save()
    assert saved["humans"] == [] and saved["scripted"] == {"axis": "computer", "cw": "computer"}
    resumed = Session.from_save(saved, GMAP)
    assert not resumed.humans and all(type(player) is players.ComputerOpponent for player in resumed.scripted.values())
    assert resumed.state == session.state and resumed.record == session.record


def test_computer_replays_never_show_opponents_in_the_same_hex():
    session = spectators()
    for _ in range(session.scenario["turns"]):
        session.done()
        assert invariants.check(session.state, GMAP) == []
        for side in ("axis", "cw"):
            play = Playback(session.before[side], session.views[side], gmap=GMAP)
            for t in range(0, play.length, 110):
                held = {}
                for _, _, own, where, *_ in play.stage(t)["units"]:
                    h = displayed_hex(where)
                    assert h not in held or held[h] == own, (side, t, h)
                    held[h] = own


def test_spectator_title_and_command_panel_name_each_computers_level():
    pygame.init()
    session = Session(scenarios.load("sidi_rezegh"), GMAP, humans=[],
                      scripted={"axis": players.ComputerEasy(GMAP), "cw": players.ComputerHard(GMAP)}, seed=1941)
    app = App(session)
    seen = []
    original = app.painter.text
    app.painter.text = lambda surface, words, *args, **kwargs: (seen.append(str(words)),
                                                               original(surface, words, *args, **kwargs))
    app.title = True
    app.paint(pygame.Surface(app.size))
    assert "Axis Easy · Commonwealth Hard · Watch Axis view" in seen
    seen.clear()
    app.title = False
    app.paint(pygame.Surface(app.size))
    assert "AXIS EASY · COMMONWEALTH HARD" in seen
