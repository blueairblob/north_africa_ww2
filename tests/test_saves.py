"""Saved games (screen/saves.py): a game taken up from a save goes on exactly as it would have."""
import json
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pygame = pytest.importorskip("pygame")

from engine import players                                        # noqa: E402
from engine import state as S                                     # noqa: E402
from helpers import GMAP, ROOT                                    # noqa: E402
from screen import layout, saves, theme                           # noqa: E402
from screen.app import App                                        # noqa: E402
from screen.session import Session                                # noqa: E402


def crusader():
    return json.loads((ROOT / "data" / "scenarios" / "crusader.json").read_text())


def game(seed=65, turns=2):
    """A game against the attacker, some turns in, with orders standing and some given this turn."""
    s = Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)}, seed=seed)
    far = list(GMAP.places["Bardia"]["hex"])
    assert s.give({"unit": 310, "order": "move", "to": far})["ok"] and s.give({"unit": 320, "order": "dig_in"})["ok"]
    for _ in range(turns):
        s.done()
    s.rename(310, "The Desert Rats")
    s.keep(310)
    assert s.give({"unit": 330, "order": "rest"})["ok"]
    s.set_air("recon")
    return s


def orders_for(s, turn):
    """The same orders for either of two games at the same point."""
    bot = players.AlwaysAttack(GMAP)
    return bot.orders(s.view)["orders"][turn % 3::4]


def test_a_game_taken_up_from_a_save_is_the_same_game_and_goes_on_the_same(tmp_path):
    a = game()
    path = saves.write(a, tmp_path)
    assert path.parent == tmp_path and path.name.startswith("crusader-turn03-") and not list(tmp_path.glob("*.part"))
    b = saves.read(path, GMAP)
    assert S.dumps(b.state) == S.dumps(a.state) and b.state["seed"] == 65 and b.record == a.record
    assert (b.side, b.humans, b.waiting, b.air) == (a.side, a.humans, a.waiting, a.air)
    assert type(b.scripted["axis"]) is players.AlwaysAttack
    for field in ("standing", "pending", "said", "kept", "split", "ended", "names", "watched", "views", "before"):
        assert getattr(b, field) == getattr(a, field), field         # the orders given so far, and those that stand
    assert b.standing["cw"][310]["order"] == "move" and b.pending["cw"][330]["order"] == "rest"
    assert 310 not in b.waiting_units() and b.group_name(310) == "The Desert Rats"
    assert b.reports() == a.reports() and b.weather == a.weather
    for turn in range(3):                                             # played on with the same orders, they stay the same
        for s in (a, b):
            for order in orders_for(s, turn):
                s.give(order)
            s.done()
        assert S.dumps(b.state) == S.dumps(a.state) and b.standing == a.standing and b.ended == a.ended
    assert {a.state["turn"], b.state["turn"]} == {6}
    assert len({v["weather"] for v in (a.view, b.view)}) == 1


def test_a_file_that_is_no_save_of_this_version_is_refused_in_plain_words(tmp_path):
    a = game(turns=1)
    path = saves.write(a, tmp_path)
    good = json.loads(path.read_text())
    for name, spoil in (("format", lambda d: d.update(format=99)), ("state", lambda d: d["state"].pop("weather")),
                        ("units", lambda d: d["state"]["units"][0].update(cohesion=500)),
                        ("scenario", lambda d: d["scenario"].update(start="never")),
                        ("pending", lambda d: d.pop("pending"))):
        data = json.loads(json.dumps(good))
        spoil(data)
        (tmp_path / "bad.json").write_text(json.dumps(data))
        with pytest.raises(ValueError, match="saved game"):
            saves.read(tmp_path / "bad.json", GMAP)
    (tmp_path / "bad.json").write_text("not a game at all")
    with pytest.raises(ValueError, match="cannot be read"):
        saves.read(tmp_path / "bad.json", GMAP)
    with pytest.raises(ValueError, match="cannot be read"):
        saves.read(tmp_path / "none.json", GMAP)
    assert [f.name for f, _ in saves.listing(tmp_path)] == [path.name]      # only the real save is listed


def test_the_list_is_newest_first_and_an_autosave_replaces_the_last(tmp_path):
    a = game(turns=1)
    first = saves.write(a, tmp_path)
    os.utime(first, ns=(1, 1))                                        # saved long ago
    auto = saves.write(a, tmp_path, auto=True)
    a.done()
    assert saves.write(a, tmp_path, auto=True) == auto and len(list(tmp_path.glob("*.json"))) == 2
    found = saves.listing(tmp_path)
    assert [f for f, _ in found] == [auto, first] and saves.newest(tmp_path) == auto
    assert "Operation Crusader, turn 3 of 22, 22 November 1941: Commonwealth to order" in found[0][1]
    assert "(autosave)" in found[0][1] and "(autosave)" not in found[1][1] and "turn 2 of 22" in found[1][1]
    assert saves.listing(tmp_path / "nowhere") == [] and saves.newest(tmp_path / "nowhere") is None


def test_the_game_button_saves_and_loads_by_tap_and_by_key(tmp_path):
    pygame.init()
    surface = pygame.Surface(theme.WINDOW)
    app = App(game())
    s = app.session
    app.click(layout.game(app.size, False)["game"].center)
    assert app.ui.game_open
    app.click(layout.game(app.size, True)["save"].center)            # nowhere to save: said, and nothing written
    assert "nowhere to save" in app.ui.message and not app.ui.game_open
    app.saves = tmp_path
    app.key(pygame.K_F9)
    app.paint(surface)
    assert app.ui.saves == [] and "No games" in app.ui.message
    app.click(layout.saves_list(app.size, 0)["close"].center)
    assert app.ui.saves is None
    app.click(layout.game(app.size, False)["game"].center)
    app.paint(surface)                                               # the list is painted
    app.click(layout.game(app.size, True)["save"].center)
    saved = list(tmp_path.glob("crusader-turn03-*.json"))
    assert len(saved) == 1 and saved[0].name in app.ui.message
    for _ in range(2):                                               # the game goes on two turns: an autosave each
        app.done()
        app.stop_watching()
    assert s.state["turn"] == 5 and (tmp_path / "crusader-autosave.json").exists()
    os.utime(saved[0], ns=(1, 1))
    app.ui.zoom, app.ui.remind = 0.5, False
    app.click(layout.game(app.size, False)["game"].center)
    app.click(layout.game(app.size, True)["load"].center)
    app.paint(surface)
    assert [f.name for f, _ in app.ui.saves] == ["crusader-autosave.json", saved[0].name]
    app.click(layout.saves_list(app.size, 2)[1].center)              # the older one, saved by hand
    assert app.session is not s and app.session.state["turn"] == 3 and app.ui.saves is None
    assert app.ui.message.startswith("Loaded: Operation Crusader, turn 3 of 22")
    assert app.session.pending["cw"][330]["order"] == "rest" and app.session.air["cw"] == "recon"
    assert app.ui.selected in app.session.waiting_units() and (app.ui.zoom, app.ui.remind) == (0.5, False)
    app.paint(surface)
    app.key(pygame.K_F5)                                             # by key
    assert len(list(tmp_path.glob("crusader-turn03-*.json"))) == 2
    app.key(pygame.K_F9)
    app.key(pygame.K_h)                                              # any key puts the list away, and gives no order
    assert app.ui.saves is None and "no game was loaded" in app.ui.message
    (tmp_path / "zz.json").write_text(json.dumps({"format": 1}))
    turn = app.session.state["turn"]
    assert app.load(tmp_path / "zz.json") is False and app.session.state["turn"] == turn      # refused: this game stays
    assert "does not fit" in app.ui.message


def test_leaving_the_window_saves_the_orders_given_so_far(tmp_path):
    pygame.init()
    app = App(game())
    app.saves = tmp_path
    assert app.session.give({"unit": 340, "order": "hold"})["ok"]
    assert app.handle(pygame.event.Event(pygame.QUIT)) is False
    again = saves.read(saves.newest(tmp_path), GMAP)
    assert again.pending["cw"][340]["order"] == "hold" and again.state["turn"] == 3


def test_a_game_for_two_at_one_screen_comes_back_covered_for_the_side_that_was_ordering(tmp_path):
    pygame.init()
    s = Session(crusader(), GMAP, seed=4)
    assert s.give({"unit": 101, "order": "rest"})["ok"]
    assert s.done() == "pass" and s.side == "cw"                     # the Axis has handed in; the Commonwealth is ordering
    app = App(Session(crusader(), GMAP))
    assert app.load(saves.write(s, tmp_path)) and app.session.side == "cw"
    assert app.ui.cover.startswith("Commonwealth") and app.session.pending["axis"][101]["order"] == "rest"
    app.key(pygame.K_SPACE)
    assert app.ui.cover is None and app.ui.selected in app.session.waiting_units()
