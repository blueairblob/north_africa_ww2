"""A reviewer can start, leave, and resume without command-line arguments."""
import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from engine import scenarios, scenario_options  # noqa: E402
from engine import campaigns  # noqa: E402
from engine.players import ComputerOpponent  # noqa: E402
from helpers import GMAP  # noqa: E402
from screen import paths, preferences, saves  # noqa: E402
from screen.app import App  # noqa: E402
from screen.front import card_rect, controls, history_pages  # noqa: E402
from screen.session import Session  # noqa: E402


def menu_app(tmp_path, size=(900, 560)):
    pygame.init()
    session = Session(scenarios.load("sidi_rezegh"), GMAP, humans=["cw"],
                      scripted={"axis": ComputerOpponent(GMAP)}, seed=1941)
    app = App(session, size=size, review_menu=True)
    app.saves = tmp_path / "saves"
    app.settings_path = tmp_path / "preferences.json"
    app.screenshots = tmp_path / "screenshots"
    return app


def press(app, name):
    pos = controls(app.size, app.front.page)[name].center
    return app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_review_menu_starts_both_scenarios_and_keeps_player_choices(tmp_path):
    app = menu_app(tmp_path)
    assert app.front.page == "home" and not app.has_started
    press(app, "new")
    assert app.front.page == "setup"
    press(app, "scenario_next")
    assert app.front.scenario == "crusader"
    press(app, "axis_prev")
    assert app.front.axis == "computer-easy"
    press(app, "cw_next")
    assert app.front.cw == "computer-easy"
    press(app, "start")
    assert app.front is None and app.has_started
    assert app.session.scenario["id"] == "crusader"
    assert app.session.humans == []
    assert all(player.level == "easy" for player in app.session.scripted.values())
    assert app.session.to_save()["scripted"] == {"axis": "computer-easy", "cw": "computer-easy"}


def test_campaign_research_trial_is_visible_and_starts_in_september_1940(tmp_path):
    app = menu_app(tmp_path)
    assert app.front.research_start == "italian_frontier_1940"
    assert "research" in controls(app.size, "home")
    press(app, "research")
    assert app.front.page == "setup" and app.front.mode == "research"
    assert app.front.scenario == "italian_frontier_1940"
    press(app, "scenario_next")
    press(app, "shipping_next")
    assert app.front.scenario == "italian_frontier_1940" and app.front.shipping == "baseline"
    press(app, "axis_next")
    press(app, "start")
    assert app.front is None and app.has_started
    assert app.session.scenario["id"] == "italian_frontier_1940"
    assert app.session.state["campaign"] == {"id": "north_africa", "history": []}
    assert app.session.scenario["research_next"] == "italian_invasion_1940"
    saved = app.save(auto=True)
    restored = saves.read(saved, GMAP)
    assert restored.to_save() == app.session.to_save()


def test_backing_out_of_research_setup_restores_the_battle_choice(tmp_path):
    app = menu_app(tmp_path)
    press(app, "research")
    press(app, "back")
    press(app, "new")
    assert app.front.mode == "battle" and app.front.scenario == "sidi_rezegh"
    press(app, "start")
    assert app.session.scenario["id"] == "sidi_rezegh"


def test_campaign_menu_waits_for_a_reviewed_1940_opening(tmp_path):
    app = menu_app(tmp_path)
    assert app.front.campaign_start is None
    press(app, "campaign")
    assert app.front.page == "home"
    assert "historical review" in app.front.message


@pytest.mark.parametrize("human", [True, False])
def test_campaign_menu_starts_a_carried_game_with_selected_players(tmp_path, monkeypatch, human):
    monkeypatch.setattr(campaigns, "load", lambda name="north_africa": {
        "chapters": [{"scenario": "sidi_rezegh", "status": "review"}]})
    app = menu_app(tmp_path)
    assert app.front.campaign_start == "sidi_rezegh"
    press(app, "campaign")
    assert app.front.page == "setup" and app.front.mode == "campaign"
    press(app, "scenario_next")
    assert app.front.scenario == "sidi_rezegh"
    if not human:
        press(app, "cw_next")
    press(app, "start")
    assert app.session.humans == (["cw"] if human else [])
    assert app.session.state["campaign"] == {"id": "north_africa", "history": []}
    saved = app.save(auto=True)
    assert saved.name == "sidi_rezegh-north_africa-autosave.json"
    restored = saves.read(saved, app.session.gmap)
    assert restored.to_save() == app.session.to_save()


def test_experimental_shipping_choice_is_separate_and_survives_save(tmp_path):
    base = scenarios.load("sidi_rezegh")
    assert scenario_options.apply(base, "less_interdiction")["sides"]["axis"]["sea_pct"][0][1] == 55
    assert base["sides"]["axis"]["sea_pct"][0][1] == 40
    app = menu_app(tmp_path)
    press(app, "new")
    press(app, "shipping_next")
    assert app.front.shipping == "less_interdiction"
    press(app, "start")
    assert app.session.scenario["sides"]["axis"]["sea_pct"][0][1] == 55
    assert app.session.scenario["assumption"] == "less_interdiction"
    saved = app.save(auto=True)
    assert saved.name == "sidi_rezegh-less_interdiction-autosave.json"
    restored = Session.from_save(json.loads(saved.read_text()), GMAP)
    assert restored.scenario == app.session.scenario
    assert "Experimental: +15 sea points" in saves.about(restored.to_save())


def test_review_menu_saves_on_exit_and_continues_without_losing_orders(tmp_path):
    app = menu_app(tmp_path)
    press(app, "new")
    press(app, "start")
    app.session.set_air("recon")
    before = app.session.to_save()
    assert app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.front.page == "pause"
    assert not press(app, "quit")
    save = app.saves / "sidi_rezegh-autosave.json"
    assert json.loads(save.read_text())["air"]["cw"] == "recon"
    reopened = menu_app(tmp_path)
    assert press(reopened, "continue")
    assert reopened.front is None and reopened.has_started
    assert reopened.session.to_save() == before


def test_help_options_and_front_screens_leave_the_turn_intact(tmp_path):
    app = menu_app(tmp_path)
    before = app.session.to_save()
    for page in ("home", "setup", "help", "options", "pause"):
        app.front.page = page
        canvas = pygame.Surface(app.size)
        app.paint(canvas)
        card = card_rect(app.size)
        assert all(card.contains(rect) for rect in controls(app.size, page).values())
    assert not controls(app.size, "options")["game_files"].colliderect(controls(app.size, "options")["back"])
    app.front.page = "home"
    press(app, "options")
    press(app, "symbols")
    press(app, "sound")
    assert app.ui.symbols == "nato" and not app.options["sound"]
    assert preferences.read(app.settings_path)["symbols"] == "nato"
    restored = menu_app(tmp_path)
    restored.apply_options(preferences.read(restored.settings_path))
    assert restored.ui.symbols == "nato" and not restored.options["sound"]
    press(app, "back")
    press(app, "help")
    press(app, "next")
    assert app.front.help_page == 1
    press(app, "back")
    assert app.front.page == "home" and app.session.to_save() == before
    press(app, "new")
    press(app, "start")
    game = app.session.to_save()
    assert app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1))
    assert app.front.page == "help"
    press(app, "back")
    assert app.front is None and app.session.to_save() == game


def test_historical_briefing_and_debrief_are_accessible_without_changing_play(tmp_path, monkeypatch):
    app = menu_app(tmp_path)
    press(app, "new")
    press(app, "history")
    assert app.front.page == "history" and app.front.history_episode["id"] == "sidi_rezegh_1941"
    assert "BEFORE" in history_pages(app.front.history_episode)[0][0]
    canvas = pygame.Surface(app.size)
    app.paint(canvas)
    assert all(card_rect(app.size).contains(rect) for rect in controls(app.size, "history").values())
    press(app, "next")
    press(app, "next")
    assert history_pages(app.front.history_episode)[app.front.history_page][0] == "PERIOD · ARCHIVE IMAGE"
    app.paint(canvas)
    opened = []
    monkeypatch.setattr("screen.app.webbrowser.open", opened.append)
    press(app, "image_source")
    assert opened == [app.front.history_episode["period_image"]["source"]]
    press(app, "back")
    assert app.front.page == "setup"
    press(app, "start")
    before = app.session.to_save()
    app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    press(app, "history")
    while app.front.history_page < len(history_pages(app.front.history_episode)) - 1:
        press(app, "next")
    assert "AFTER" in history_pages(app.front.history_episode)[app.front.history_page][0]
    assert "Tobruk" in history_pages(app.front.history_episode)[app.front.history_page][1][0]
    app.paint(canvas)
    press(app, "back")
    assert app.front.page == "pause"
    press(app, "resume")
    assert app.front is None and app.session.to_save() == before


def test_escape_can_pause_playback_and_hotseat_cover_without_losing_either(tmp_path):
    app = menu_app(tmp_path)
    press(app, "new")
    press(app, "start")
    playback = object()
    app.play, app.play_t = playback, 17.0
    app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.front.page == "pause"
    press(app, "resume")
    assert app.front is None and app.play is playback and app.play_t == 17.0
    app.play = None
    app.ui.cover = "Commonwealth orders"
    app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert app.front.page == "pause"
    press(app, "resume")
    assert app.front is None and app.ui.cover == "Commonwealth orders"


def test_bad_preferences_are_ignored_and_window_size_is_bounded(tmp_path):
    path = tmp_path / "preferences.json"
    path.write_text('{"sound": "off", "symbols": "unknown", "window": [100, 50000]}')
    assert preferences.read(path) == preferences.DEFAULTS
    preferences.write(path, {"sound": False, "symbols": "nato", "window": [1000, 700]})
    assert preferences.read(path)["window"] == [1000, 700]
    assert preferences.read(path)["sound"] is False


def test_packaged_game_uses_writable_windows_app_data(tmp_path, monkeypatch):
    monkeypatch.delenv("BENGHAZI_USER_DATA", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    assert paths.user_folder("saves") == tmp_path / "Benghazi Handicap" / "saves"
    assert paths.user_folder("screenshots") == tmp_path / "Benghazi Handicap" / "screenshots"


def test_options_shows_game_files_path_and_opens_the_os_file_manager(tmp_path, monkeypatch):
    root = tmp_path / "Benghazi Handicap"
    monkeypatch.setenv("BENGHAZI_USER_DATA", str(root))
    app = menu_app(tmp_path)
    app.front.page = "options"
    shown = []
    fitted = app.painter.fitted
    app.painter.fitted = lambda surface, words, *a, **k: (shown.append(str(words)), fitted(surface, words, *a, **k))
    app.paint(pygame.Surface(app.size))
    assert paths.display_user_root() in shown
    launched = []
    if os.name == "nt":
        monkeypatch.setattr(paths.os, "startfile", lambda path: launched.append(path))
    else:
        monkeypatch.setattr(paths.subprocess, "Popen", lambda args, **kwargs: launched.append(args))
    before = app.session.to_save()
    press(app, "game_files")
    opener = "explorer.exe" if os.environ.get("WSL_DISTRO_NAME") else "open" if paths.sys.platform == "darwin" else "xdg-open"
    target = paths.display_user_root() if os.environ.get("WSL_DISTRO_NAME") else str(root)
    assert launched == ([str(root)] if os.name == "nt" else [[opener, target]])
    assert (root / "saves").is_dir() and (root / "screenshots").is_dir()
    assert app.session.to_save() == before


def test_options_reports_when_file_manager_cannot_open(tmp_path, monkeypatch):
    from screen import app as app_module
    app = menu_app(tmp_path)
    app.front.page = "options"
    monkeypatch.setattr(app_module, "open_game_files", lambda: (_ for _ in ()).throw(OSError("no file manager")))
    assert press(app, "game_files")
    assert "no file manager" in app.front.message
