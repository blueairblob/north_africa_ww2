"""The screen (DESIGN.md §12): its geometry, a game in progress, and that a frame can be drawn
with no window. What it looks like needs eyes; these check what it does."""
import json
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame = pytest.importorskip("pygame")

from engine import players                                        # noqa: E402
from engine import state as S                                     # noqa: E402
from engine.view import view                                     # noqa: E402
from helpers import GMAP, ROOT, small                             # noqa: E402
from screen import layout, theme                                  # noqa: E402
from screen.app import App                                        # noqa: E402
from screen.layout import Layout                                  # noqa: E402
from screen.session import Session                                # noqa: E402


def crusader():
    """Crusader with whole divisions as its counters: fewer units, and ids these tests know."""
    return json.loads((ROOT / "tests" / "scenarios" / "divisions.json").read_text())


def regiments():
    """Crusader as it is played: each division as its units, grouped under its HQ."""
    return json.loads((ROOT / "data" / "scenarios" / "crusader.json").read_text())


@pytest.mark.parametrize("close_event,busy", [(pygame.WINDOWCLOSE, True), (pygame.QUIT, False)])
def test_window_close_autosaves_exits_and_does_not_reopen_on_pending_resize(tmp_path, monkeypatch, close_event, busy):
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    app.saves = tmp_path
    app.session.set_air("recon")                  # a choice made during the turn must survive closing
    if not busy:
        app.ui.selected = None                   # this uses the sleeping event.wait branch
    monkeypatch.setattr(app, "paint", lambda surface: None)
    close = pygame.event.Event(close_event)
    resize = pygame.event.Event(pygame.VIDEORESIZE, w=1200, h=700)
    monkeypatch.setattr(pygame.event, "get", lambda: [close, resize] if busy else [resize])
    monkeypatch.setattr(pygame.event, "wait", lambda: close)
    real_set_mode = pygame.display.set_mode
    modes = []

    def set_mode(*args, **kwargs):
        modes.append(args[0])
        return real_set_mode(*args, **kwargs)

    monkeypatch.setattr(pygame.display, "set_mode", set_mode)
    app.run()
    saved = json.loads((tmp_path / "crusader-autosave.json").read_text())
    assert saved["air"]["cw"] == "recon" and saved["auto"]
    assert modes == [theme.WINDOW]               # no resize recreates the window after its close
    assert not pygame.get_init()


def test_f12_saves_the_current_rendered_view_without_changing_play(tmp_path, monkeypatch):
    pygame.init()
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 0)  # freeze selection pulse between renders
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}), size=(900, 560))
    app.screenshots = tmp_path / "shots"
    expected = pygame.Surface(app.size)
    app.paint(expected)
    before = app.session.to_save()

    assert app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F12))
    paths = list(app.screenshots.glob("*.png"))
    assert len(paths) == 1 and paths[0].name.startswith("crusader-")
    first = paths[0]
    shot = pygame.image.load(str(first))
    assert shot.get_size() == app.size
    assert pygame.image.tostring(shot, "RGB") == pygame.image.tostring(expected, "RGB")
    assert app.session.to_save() == before
    assert "Screenshot saved" in app.ui.message

    app.ui.details_collapsed = True
    app.ui.symbols = "nato"
    assert app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F12))
    paths = list(app.screenshots.glob("*.png"))
    assert len(paths) == 2  # each press keeps the earlier view, even in the same second
    second = next(path for path in paths if path != first)
    assert pygame.image.tostring(pygame.image.load(str(second)), "RGB") != pygame.image.tostring(shot, "RGB")


@pytest.mark.parametrize("mode", ["cover", "editing", "playback", "saves"])
def test_f12_is_available_while_another_ui_mode_has_the_keyboard(tmp_path, monkeypatch, mode):
    pygame.init()
    app = App(Session(regiments(), GMAP))
    app.screenshots = tmp_path
    monkeypatch.setattr(app, "paint", lambda surface: surface.fill("red"))
    if mode == "cover":
        app.ui.cover = "Other player's turn"
    elif mode == "editing":
        app.ui.editing = "New name"
    elif mode == "playback":
        app.play = object()
    else:
        app.ui.saves = []
    assert app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F12))
    assert len(list(tmp_path.glob("*.png"))) == 1
    assert (app.play is not None if mode == "playback" else getattr(app.ui, mode) is not None)


def test_game_menu_offers_the_same_screenshot_capture(tmp_path):
    pygame.init()
    app = App(Session(regiments(), GMAP), size=(900, 560))
    app.screenshots = tmp_path
    app.click(layout.game(app.size, False)["game"].center)
    assert app.ui.game_open
    app.click(layout.game(app.size, True)["screenshot"].center)
    assert not app.ui.game_open
    assert len(list(tmp_path.glob("*.png"))) == 1
    assert "Screenshot saved" in app.ui.message


def test_f12_reports_capture_errors_without_interrupting_the_game(tmp_path, monkeypatch):
    pygame.init()
    app = App(Session(regiments(), GMAP))
    app.screenshots = tmp_path
    monkeypatch.setattr(app, "paint", lambda surface: None)

    def fail(*args):
        raise OSError("disk is full")

    monkeypatch.setattr(pygame.image, "save", fail)
    assert app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F12))
    assert "disk is full" in app.ui.message
    assert not list(tmp_path.glob("*.png"))


def test_air_selector_has_distinct_1941_theatre_aircraft_silhouettes():
    from screen.pictures import AIR_EXAMPLES, aircraft
    assert AIR_EXAMPLES == {
        "cw": {"button": "hurricane", "fighter_alt": "tomahawk", "support": "hurricane",
               "interdict": "blenheim", "recon": "boston"},
        "axis": {"button": "macchi", "fighter_alt": "bf109", "support": "stuka",
                 "interdict": "ju88", "recon": "bf110"},
    }
    for size in ((23, 21), (80, 60)):
        silhouettes = {}
        for side in ("cw", "axis"):
            for choice in ("button", "fighter_alt", "support", "interdict", "recon"):
                surface = pygame.Surface(size)
                surface.fill("white")
                aircraft(surface, side, surface.get_rect(), (35, 25, 18), (230, 210, 160), choice)
                pixels = pygame.image.tostring(surface, "RGB")
                assert pixels != b"\xff" * len(pixels)
                silhouettes[side, choice] = pixels
        assert silhouettes["cw", "button"] != silhouettes["axis", "button"]
        # Bf 110 reconnaissance must show two engines, not the old anonymous single.
        blank = pygame.Surface(size)
        blank.fill("white")
        aircraft(blank, "axis", blank.get_rect(), (35, 25, 18), (230, 210, 160), "recon")
        assert blank.get_at((round(size[0] * 0.34), round(size[1] * 0.26)))[:3] != (255, 255, 255)
        # The Bf 110's paired tail fins also project beyond the Ju 88 tail.
        ju88 = pygame.Surface(size)
        ju88.fill("white")
        aircraft(ju88, "axis", ju88.get_rect(), (35, 25, 18), (230, 210, 160), "interdict")
        at_fin = (round(size[0] * 0.25), round(size[1] * 0.75))
        assert blank.get_at(at_fin)[:3] != ju88.get_at(at_fin)[:3]
        for side in ("cw", "axis"):
            assert silhouettes[side, "button"] != silhouettes[side, "fighter_alt"]
            assert len({silhouettes[side, choice] for choice in ("support", "interdict", "recon")}) == 3


def test_axis_italian_fighter_example_changes_only_after_the_documented_arrival():
    from datetime import date
    from screen.pictures import AIR_EXAMPLES, AIR_LABELS, air_example, aircraft

    assert air_example("axis", "button", date(1941, 11, 24)) == "macchi"
    assert air_example("axis", "button", date(1941, 11, 25)) == "macchi"
    assert air_example("axis", "button", date(1941, 11, 26)) == "macchi202"
    assert air_example("axis", "fighter_alt", date(1941, 11, 26)) == "bf109"
    assert all(air_example("cw", choice, date(1941, 12, 25)) == model
               for choice, model in AIR_EXAMPLES["cw"].items())
    for size in ((27, 24), (80, 60)):
        radial, inline = pygame.Surface(size), pygame.Surface(size)
        for canvas, model in ((radial, "macchi"), (inline, "macchi202")):
            canvas.fill("white")
            aircraft(canvas, "axis", canvas.get_rect(), (35, 25, 18), (230, 210, 160), model=model)
        assert pygame.image.tostring(radial, "RGB") != pygame.image.tostring(inline, "RGB")

    app = App(Session(regiments(), GMAP, humans=["axis"]))
    app.paint(pygame.Surface(app.size))
    controls = layout.air_controls(app.size, False)
    button_tip = lambda: next(words for rect, words in app.painter.tips if rect == controls["air"])
    assert AIR_LABELS["macchi"] in button_tip()
    app.session.state["turn"] = 5  # 26 November: first two-day turn after the arrival.
    app.paint(pygame.Surface(app.size))
    assert app.session.day == date(1941, 11, 26)
    assert AIR_LABELS["macchi202"] in button_tip()
    assert "C.200s also served during this period" in button_tip()
    assert any(words.startswith("Macchi C.202: fighter example") for _, words in app.painter.tips)


def test_air_menu_identifies_examples_without_assigning_a_type_to_air_points():
    pygame.init()
    for side, examples in (("cw", ("Hurricane", "Blenheim", "Boston")),
                           ("axis", ("Ju 87", "Ju 88", "Bf 110"))):
        app = App(Session(regiments(), GMAP, humans=[side]))
        app.ui.air_open = True
        labels = []
        original_fitted = app.painter.fitted

        def record_label(surface, words, centre, px, colour, room, least=9):
            labels.append(words)
            return original_fitted(surface, words, centre, px, colour, room, least)

        app.painter.fitted = record_label
        app.paint(pygame.Surface(app.size))
        controls = layout.air_controls(app.size, True)
        assert controls["air"].w == 194  # two fighter examples and a legible order label
        from screen.pictures import AIR_EXAMPLES, AIR_LABELS
        fighters = [AIR_LABELS[AIR_EXAMPLES[side][choice]] for choice in ("button", "fighter_alt")]
        assert any(rect == controls["air"] and all(model in words for model in fighters)
                   for rect, words in app.painter.tips)
        for offset, model in zip((4, 32), fighters):
            icon = pygame.Rect(controls["air"].x + offset, controls["air"].y + 3, 27, 24)
            assert any(rect == icon and words.startswith(model + ": fighter example")
                       for rect, words in app.painter.tips)
            assert next(words for rect, words in app.painter.tips if rect.collidepoint(icon.center)).startswith(model)
        for n, (choice, model) in enumerate(zip(("support", "interdict", "recon"), examples), 1):
            assert any(rect == controls[choice] and model in words and "pool multiple types" in words
                       for rect, words in app.painter.tips)
            title = f"{n} {choice.title()} · {model}"
            assert title in labels
            assert app.painter.font(12, True).size(title)[0] <= controls[choice].w - 64


def test_a_hex_is_as_many_pixels_across_as_asked_and_the_counter_fits_in_it():   # docs/COUNTERS.md
    lay = Layout(96)
    (x0, _), (x1, _) = lay.corners((10, 10))[0], lay.corners((10, 10))[3]
    assert round(x0 - x1) == 96 and lay.counter == 71
    _, y0 = lay.centre((10, 10))
    _, y1 = lay.centre((10, 11))
    assert round(y1 - y0) == 83


def test_the_base_map_is_the_size_the_screen_expects():
    from mapgen import render
    assert render.BASE_HEX == theme.BASE_HEX
    if (ROOT / "art" / "basemap.jpg").exists():
        assert pygame.image.load(str(ROOT / "art" / "basemap.jpg")).get_size() == Layout(theme.BASE_HEX).size(GMAP.cols, GMAP.rows)


def test_a_short_window_scrolls_the_panel_without_covering_its_controls():
    pygame.init()
    app = App(Session(regiments(), GMAP), size=(900, 560))
    app.ui.selected = 110
    surface = pygame.Surface(app.size)
    app.paint(surface)
    painter = app.painter
    footer = layout.buttons(app.size)["next"]
    assert painter.panel_body.bottom < footer.top
    assert painter.panel_scroll_max > 0
    assert set(painter.order_rects) == set(layout.buttons(app.size))
    assert layout.areas(app.size)["console"].contains(painter.order_rects["split"])
    assert painter.member_rects

    app.click(painter.panel_scroll_rects["down"].center)
    app.paint(surface)
    assert app.ui.panel_scroll == 80
    assert painter.order_rects["split"] == layout.buttons(app.size)["split"]
    assert painter.order_rects["next"] == footer
    app.click(painter.order_rects["split"].center)
    assert "Click a unit in the details hierarchy" in app.ui.message


def test_the_panel_scroll_resets_for_another_unit():
    pygame.init()
    app = App(Session(regiments(), GMAP), size=(900, 560))
    surface = pygame.Surface(app.size)
    app.paint(surface)
    app.click(app.painter.panel_scroll_rects["down"].center)
    app.paint(surface)
    assert app.ui.panel_scroll > 0
    app.ui.selected = 120
    app.paint(surface)
    assert app.ui.panel_scroll == 0


def test_details_can_collapse_without_losing_the_map_or_command_console():
    pygame.init()
    app = App(Session(regiments(), GMAP))
    app.ui.selected = 110
    surface = pygame.Surface(app.size)
    app.paint(surface)
    old = app.map_rect()
    assert app.painter.member_rects and old.w == app.size[0] - theme.PANEL
    app.click(layout.details_toggle(app.size).center)
    app.paint(surface)
    assert app.ui.details_collapsed and app.map_rect().w == app.size[0]
    assert not app.painter.member_rects
    assert all(layout.areas(app.size)["console"].contains(rect) for rect in layout.buttons(app.size).values())
    assert layout.layers(app.size, False, True)["layers"].right < app.map_rect().right
    app.click(layout.buttons(app.size)["move"].center)
    assert app.ui.mode == "move"
    app.click(layout.details_toggle(app.size, True).center)
    app.paint(surface)
    assert not app.ui.details_collapsed and app.map_rect() == old and app.painter.member_rects
    app.click(layout.details_toggle(app.size).center)
    app.click(layout.buttons(app.size)["split"].center)
    assert not app.ui.details_collapsed and "details hierarchy" in app.ui.message


def test_map_layers_hold_weather_terrain_and_counter_style_preferences():
    pygame.init()
    app = App(Session(regiments(), GMAP))
    surface = pygame.Surface(app.size)
    app.paint(surface)
    app.click(layout.layers(app.size, False)["layers"].center)
    menu = layout.layers(app.size, True)
    assert all(name in menu for name in ("k", "weather", "s", "z", "pictures", "nato"))
    assert app.ui.weather_visible and app.ui.symbols == "pictures"
    app.click(menu["k"].center)
    app.click(menu["weather"].center)
    app.click(menu["nato"].center)
    app.paint(surface)
    assert app.ui.overlays == {"k"} and not app.ui.weather_visible
    assert app.painter.weather_rect is None and app.ui.symbols == "nato"
    app.click(menu["pictures"].center)
    assert app.ui.symbols == "pictures"


def test_air_effort_is_visible_clickable_and_keeps_keyboard_parity():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    original = app.ui.selected
    for size, collapsed in ((theme.WINDOW, False), ((900, 560), False), (theme.WINDOW, True)):
        app.size, app.ui.details_collapsed = size, collapsed
        surface = pygame.Surface(size)
        app.paint(surface)
        closed = layout.air_controls(size, collapsed=collapsed)
        button = closed["air"]
        assert layout.areas(size, collapsed)["bar"].contains(button)
        assert button.left > layout.layers(size, False, collapsed)["layers"].right
        app.click(button.center)
        assert app.ui.air_open and app.ui.selected == original
        popup = layout.air_controls(size, True, collapsed)
        assert set(popup) == {"air", "support", "interdict", "recon"}
        assert all(row.bottom < button.top and row.left >= 0 for name, row in popup.items() if name != "air")
        app.key(pygame.K_ESCAPE)
        assert not app.ui.air_open and app.ui.selected == original
        app.click(button.center)
        app.paint(surface)
        app.click(popup["recon"].center)
        assert app.session.air["cw"] == "recon" and not app.ui.air_open and app.ui.selected == original
        app.key(pygame.K_2)
        assert app.session.air["cw"] == "interdict"
        app.click(button.center)
        app.click(popup["support"].center)
        assert app.session.air["cw"] == "support"
        app.click(button.center)
        app.click((button.left - 4, button.centery))
        assert not app.ui.air_open and app.session.air["cw"] == "support"  # dismissal is not an order


def test_interdict_selector_says_what_changes_and_when():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    app.key(pygame.K_2)
    assert app.session.air["cw"] == "interdict"
    assert "enemy truck lift" in app.ui.message and "next turn's supply phase" in app.ui.message
    assert f"−{5 * app.session.view['air_points']}%" in app.ui.message
    app.ui.air_open = True
    seen = []
    original = app.painter.text
    app.painter.text = lambda surface, words, *a, **k: (seen.append(str(words)), original(surface, words, *a, **k))
    app.paint(pygame.Surface(app.size))
    assert any("truck lift" in words and "next turn" in words for words in seen)


def test_grounded_air_effort_explains_that_the_choice_has_no_flights():
    from helpers import scenario, unit
    pygame.init()
    sc = scenario([unit(201, "cw", "armour", [70, 21]), unit(101, "axis", "foot", [70, 24])],
                  weather=[["1941-11-18", {"rain": 100}]])
    app = App(Session(sc, GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}, seed=5))
    assert app.session.weather == "rain"
    seen = []
    text = app.painter.text
    app.painter.text = lambda surface, words, *a, **k: (seen.append(words), text(surface, words, *a, **k))
    button = layout.air_controls(app.size)["air"]
    app.click(button.center)
    app.paint(pygame.Surface(app.size))
    assert "NO FLIGHTS · RAIN" in seen
    app.click(layout.air_controls(app.size, True)["interdict"].center)
    assert app.session.air["cw"] == "interdict" and "No aircraft fly in rain" in app.ui.message


def test_the_hex_under_a_point_is_the_hex_whose_centre_it_is():
    for z in (96, 64, 20):
        lay = Layout(z)
        for h in ((0, 0), (1, 0), (55, 10), (122, 43), (61, 12)):
            x, y = lay.centre(h)
            assert lay.hex_at(x, y) == h and lay.hex_at(x + z * 0.2, y - z * 0.2) == h


def test_two_players_at_one_screen_give_orders_in_turn():
    s = Session(small(), GMAP)
    assert s.side == "axis" and s.view["side"] == "axis"
    assert s.give({"unit": 201, "order": "rest"})["code"] == "E_NOT_YOURS"       # RULES 8.3
    assert s.give({"unit": 101, "order": "move", "to": [60, 12]})["ok"]
    assert s.order_of(101)["order"] == "move" and s.order_of(102)["order"] == "hold"
    assert s.give({"unit": 101, "order": "rest"})["ok"] and s.order_of(101)["order"] == "rest"   # replaced
    assert s.done() == "pass" and s.side == "cw" and s.state["turn"] == 1
    assert s.pending["cw"] == {} and 101 not in [u["id"] for u in s.view["units"]]
    assert s.done() == "turn" and s.state["turn"] == 2 and s.side == "axis"
    assert s.record[0]["axis"]["orders"] == [{"unit": 101, "order": "rest"}]


def test_a_rejected_order_gives_the_engines_sentence_and_changes_nothing():      # RULES 8.5
    s = Session(small(), GMAP)
    reply = s.give({"unit": 101, "order": "move", "to": [0, 0]})
    assert reply == {"ok": False, "code": "E_IMPASSABLE", "text": "The unit cannot enter that ground."}
    assert s.pending["axis"] == {}


def test_one_player_against_a_scripted_one_plays_to_the_end():
    sc = small()
    s = Session(sc, GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)})
    for _ in range(sc["turns"]):
        assert s.side == "cw"
        s.give({"unit": 202, "order": "dig_in"})
        last = s.done()
    assert last == "over" and s.state["over"] and len(s.record) == sc["turns"]
    assert s.view["result"] == s.state["result"]                   # the player looks on at the end


def test_the_preview_shows_the_way_and_what_it_costs():           # RULES 9.2, 9.3, 9.7.1
    s = Session(crusader(), GMAP)
    p = s.preview(101, "move", (61, 12))                           # 15th Panzer to Gambut, along the coast road
    assert p["path"] == [(60, 12), (61, 12)] and p["reach"] == 2
    assert p["mp"] == 8 and p["fuel"] == 2 * 3 * 4 and p["enough_fuel"]
    march = s.preview(101, "road_march", (67, 13))                 # on to Bardia by road
    assert march["reach"] == len(march["path"]) and march["mp"] < 32
    assert s.preview(101, "move", (0, 0)) is None                  # the sea: the order would be rejected
    foot = s.preview(106, "move", (45, 10))                        # Brescia, on foot, west past Gazala
    assert foot["reach"] <= 4 < len(foot["path"]) and foot["fuel"] == 0


def test_the_supply_phase_tells_the_screen_its_hauls_and_their_routes():         # RULES 14.6
    s = Session(crusader(), GMAP)
    for _ in range(3):
        s.done(), s.done()
    hauls = [e for e in s.views["axis"]["events"] if e["event"] == "haul"]
    assert hauls and all(e["side"] == "axis" for e in hauls)
    hqs = {u["id"]: u["hex"] for u in s.views["axis"]["units"] if u["type"] == "hq"}
    assert all(e["route"][-1] == hqs[e["hq"]] and e["fuel"] + e["stores"] > 0 for e in hauls)
    assert not [e for e in s.views["cw"]["events"] if e["event"] == "haul" and e["side"] == "axis"]


@pytest.mark.parametrize("zoom, overlays", [(1.0, ""), (0.4, "sz"), (2.0, "s")])
def test_a_frame_is_drawn_without_a_window(zoom, overlays):
    pygame.init()
    app = App(Session(crusader(), GMAP))
    app.ui.zoom, app.ui.overlays, app.ui.selected, app.ui.mode, app.ui.hover = zoom, set(overlays), 101, "move", (61, 12)
    app.centre_on((59, 11))
    surface = pygame.Surface(theme.WINDOW)
    app.paint(surface)
    colours = {tuple(surface.get_at((x, y)))[:3] for x in range(0, 1000, 37) for y in range(0, 700, 41)}
    assert len(colours) > 6 and "Move here" in app.ui.preview


def test_zooming_keeps_the_point_under_the_mouse_and_never_leaves_the_map():
    pygame.init()
    app = App(Session(crusader(), GMAP))
    app.centre_on((60, 22))                                        # mid-map, so the edges do not interfere
    spot = (400, 300)
    for factor in (1.2, 1.2, 0.8, 0.8, 1.5):
        before = app.hex_under(spot)
        app.zoom(factor, spot)
        assert app.hex_under(spot) == before
    app.zoom(0.001)                                                # as far out as it goes: the whole map
    w, h = app.map_rect().size
    bw, bh = app.base_size()
    margin = theme.MARGIN + 1                                      # the paper round the map's border may show, no more
    assert app.ui.zoom == app.zoom_min() and -margin <= app.ui.cam[0] and -margin <= app.ui.cam[1]
    assert app.ui.cam[0] + w / app.ui.zoom <= bw + margin and app.ui.cam[1] + h / app.ui.zoom <= bh + margin
    app.zoom(1000)
    assert app.ui.zoom == theme.ZOOM_MAX


def test_dragging_moves_the_map_and_is_not_a_click():
    pygame.init()
    app = App(Session(crusader(), GMAP))
    cam = list(app.ui.cam)
    events = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(500, 400), button=1),
              pygame.event.Event(pygame.MOUSEMOTION, pos=(460, 380), rel=(-40, -20), buttons=(1, 0, 0)),
              pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(460, 380), button=1)]
    for e in events:
        app.handle(e)
    assert app.ui.cam == [cam[0] + 40, cam[1] + 20] and app.session.pending["axis"] == {}


def test_keys_and_clicks_give_orders():
    pygame.init()
    app = App(Session(crusader(), GMAP))
    def spot(h):
        x, y = app.ui.layout.centre(h)
        return x - int(app.ui.cam[0]) * app.ui.zoom, y - int(app.ui.cam[1]) * app.ui.zoom

    app.centre_on((59, 11))
    app.click(spot((59, 11)))
    assert app.ui.selected == 101                                  # clicked 15th Panzer
    app.key(pygame.K_r)
    assert app.session.order_of(101)["order"] == "rest" and app.ui.selected == 102      # and on to the next
    app.ui.selected = None
    app.click(spot((59, 11)))
    app.click(spot((60, 12)))                                      # a plain click on open ground gives no order
    assert app.session.order_of(101)["order"] == "rest" and "press Move or Attack first" in app.ui.message
    app.key(pygame.K_m)
    app.click(spot((60, 12)))                                      # Move pressed first: the click is where it goes
    assert app.session.order_of(101) == {"unit": 101, "order": "move", "to": [60, 12]}
    app.ui.selected = None
    app.click(spot((57, 11)))                                      # nothing taken up: a click on your own unit takes it up
    assert app.ui.selected == 109
    assert (55, 10) in {tuple(e["hex"]) for e in app.session.view["enemy"]}
    app.click(spot((55, 10)))                                      # a plain click on an enemy in sight gives no order either
    assert 109 not in app.session.pending["axis"]
    app.key(pygame.K_a)
    app.click(spot((55, 10)))                                      # Attack pressed first
    assert app.session.order_of(109) == {"unit": 109, "order": "attack", "to": [55, 10]}
    app.ui.selected = None
    app.click(spot((57, 11)))
    app.click(layout.buttons(app.size)["dig_in"].center)           # the order bar
    assert app.session.order_of(109)["order"] == "dig_in"
    app.click(layout.layers(app.size, False)["layers"].center)      # the Layers button in the map's corner
    assert app.ui.layers_open and app.ui.overlays == set()
    app.click(layout.layers(app.size, True)["s"].center)
    assert app.ui.overlays == {"s"}
    app.key(pygame.K_3)
    assert app.session.air["axis"] == "recon"
    app.click(layout.buttons(app.size)["done"].center)
    assert "not been gone through" in app.ui.message and app.session.side == "axis"   # units not looked at: asked once
    app.click(layout.buttons(app.size)["done"].center)
    assert app.ui.cover and app.session.side == "cw"                # the screen is covered between players
    app.key(pygame.K_SPACE)
    assert app.ui.cover is None and app.ui.selected in app.session.waiting_units()   # the first that waits


def test_an_order_stands_until_the_unit_arrives():               # RULES 8.1.4
    s = Session(crusader(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)})
    far = list(GMAP.places["Bardia"]["hex"])                     # more than a turn away for 15th Panzer
    assert s.give({"unit": 101, "order": "move", "to": far})["ok"] and s.turns_to_go(101) == 2
    assert s.give({"unit": 106, "order": "dig_in"})["ok"]
    assert 101 not in s.waiting_units() and 102 in s.waiting_units()
    s.done()
    assert s.pending["axis"][101]["to"] == far                   # given again
    assert s.pending["axis"][106] == {"unit": 106, "order": "dig_in"}  # Dig in stands too, until the works are complete
    assert 106 in s.waiting_units() and 106 not in s.idle_units()      # and is shown again with its order
    assert 101 in s.waiting_units() and 101 not in s.idle_units()      # the mover is shown again too, with its order
    s.keep(101)
    assert 101 not in s.waiting_units()                          # kept: dealt with for this turn
    assert s.unit(101)["hex"] != [59, 11] and s.ended["axis"] == []
    s.done()
    assert s.unit(101)["hex"] == far and 101 not in s.pending["axis"]            # arrived: it waits again
    assert s.ended["axis"] == [(101, "has arrived")] and 101 in s.waiting_units()
    assert "has arrived" in s.said["axis"][101]
    assert s.record[1]["axis"]["orders"] == [{"unit": 101, "order": "move", "to": far}, {"unit": 106, "order": "dig_in"}]


def test_dig_in_stands_until_the_works_are_complete():
    from engine.recovery import FORT_MAX
    s = Session(crusader(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)})
    assert s.give({"unit": 106, "order": "dig_in"})["ok"]
    s.done()
    assert s.standing["axis"][106]["order"] == "dig_in" and s.ended["axis"] == []
    s.state["forts"][S.fort_key(tuple(s.unit(106)["hex"]))] = [FORT_MAX, "axis"]      # nothing more can be dug here
    s.done()
    assert 106 not in s.standing["axis"] and 106 not in s.pending["axis"] and 106 in s.idle_units()
    assert s.ended["axis"] == [(106, "has finished digging in")] and "It holds" in s.said["axis"][106]


def test_a_click_on_the_map_gives_no_order_until_an_order_is_pressed():
    """With no order a unit holds, and Hold is the button lit. A unit trails no line under the
    pointer, and a click on the map changes nothing, until Move, Attack or March is pressed:
    so a unit on its way keeps its route whatever is clicked."""
    pygame.init()
    surface = pygame.Surface(theme.WINDOW)
    app = App(Session(crusader(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    s, grid = app.session, layout.buttons(app.size)
    inside = lambda name: tuple(surface.get_at((grid[name].x + 6, grid[name].centery)))[:3]
    app.ui.hover = (62, 14)
    app.paint(surface)
    assert app.ui.selected == 101 and app.ui.preview == ""           # taken up with no order: no way is tried out
    assert inside("hold") == theme.BUTTON_ON and inside("move") == theme.BUTTON
    assert (grid["hold"], "With no other order it holds.") in app.painter.tips
    app.centre_on((59, 11))
    app.click(app.spot((62, 14)))
    assert 101 not in s.pending["axis"] and app.ui.selected == 101 and "keeps to its order, Hold" in app.ui.message
    far = list(GMAP.places["Bardia"]["hex"])
    assert s.give({"unit": 101, "order": "move", "to": far})["ok"]
    app.ui.selected, app.ui.hover = 101, (62, 14)
    app.paint(surface)
    assert app.ui.preview == "" and inside("move") == theme.BUTTON_ON and inside("hold") == theme.BUTTON
    app.centre_on((59, 11))
    app.click(app.spot((62, 14)))                                    # a stray click: its route is as it was
    assert s.pending["axis"][101]["to"] == far and "keeps to its order, Move" in app.ui.message
    app.key(pygame.K_m)                                              # its lit order pressed: taken back, and it holds
    app.paint(surface)
    assert 101 not in s.pending["axis"] and inside("hold") == theme.BUTTON_ON and inside("move") == theme.BUTTON
    app.key(pygame.K_m)
    app.ui.hover = (62, 14)
    app.paint(surface)
    assert app.ui.preview.startswith("Move here")                    # Move pressed: now the way is tried out
    app.click(app.spot((62, 14)))
    assert s.pending["axis"][101]["to"] == [62, 14] and app.ui.mode is None


def test_a_formation_told_to_hold_is_offered_again_next_turn():
    """Hold and Rest are for one turn, and every formation is stepped to every turn."""
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    everyone = s.waiting_units()
    far = [40, 22]                                                  # days away
    assert s.give({"unit": everyone[0], "order": "move", "to": far})["ok"]
    for lead in everyone[1:]:
        assert s.give({"unit": lead, "order": ("hold", "rest", "dig_in")[lead % 3] if s.can(lead, "dig_in")[0] else "hold"})["ok"]
    assert s.waiting_units() == []
    dug = {lead for lead in everyone[1:] if s.pending["cw"][lead]["order"] == "dig_in"}
    app.key(pygame.K_RETURN)
    assert s.state["turn"] == 2 and set(everyone) <= set(s.waiting_units())       # every one of them is stepped to again
    done = {uid for uid, why in s.ended["cw"] if why == "has finished digging in"}      # Tobruk's works, made complete
    assert done and done < dug and s.standing["cw"].keys() == {everyone[0]} | dug - done    # Dig in stands until then
    assert set(everyone[1:]) - (dug - done) <= set(s.idle_units())                          # the rest hold again
    app.stop_watching()
    app.ui.selected = everyone[0]
    app.paint(pygame.Surface(theme.WINDOW))
    app.key(pygame.K_SPACE)                                         # one key keeps the order that stands
    assert everyone[0] not in s.waiting_units() and "carries on" in app.ui.message
    assert s.pending["cw"][everyone[0]]["to"] == far and app.ui.selected == everyone[1]
    idle = next(lead for lead in everyone[1:] if lead not in s.pending["cw"])
    app.ui.selected = idle
    app.key(pygame.K_SPACE)                                         # and lets a unit with no order stand as it is: it holds
    assert idle not in s.waiting_units() and idle not in s.pending["cw"] and "holds" in app.ui.message


def test_a_formation_with_low_morale_shows_attack_greyed_with_its_reason():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    assert s.can(307, "attack") == (True, "")                       # 70th Division, in Tobruk, facing the siege
    for m in s.state["units"]:
        if m["id"] == 307 or m.get("group") == 307:
            m["cohesion"] = 10
    s.views = {side: view(s.state, GMAP, s.scenario, side) for side in ("axis", "cw")}
    assert "attack" in s.offers(307) and ("attack", "morale too low. Rest to recover.") in s.blocked(307)
    assert "attack" not in s.offers(301)                            # an army HQ never attacks: not shown at all
    app.ui.selected = 307
    app.centre_on(tuple(s.unit(307)["hex"]))
    seen = []
    app.painter.text = lambda surface, words, *a, **k: seen.append(words)
    app.paint(pygame.Surface(theme.WINDOW))
    assert "Attack: morale too low. Rest to recover." in seen       # on the panel, without pointing at anything
    app.click(layout.buttons(app.size)["attack"].center)
    assert app.ui.message == "Its morale is too low to attack. Rest to recover." and app.ui.mode is None


def test_a_click_that_changes_nothing_says_why():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    app.ui.selected = 304
    app.centre_on((64, 23))
    app.click(app.spot(tuple(s.unit(304)["hex"])))                  # the hex it is in
    assert "is taken up already" in app.ui.message and app.ui.selected == 304
    app.click(app.spot((64, 22)))                                   # another of yours
    assert app.ui.message.startswith("22nd Guards Brigade put down.") and app.ui.selected == 310
    app.ui.selected = None
    app.click(app.spot((66, 26)))                                   # empty desert, nothing in hand
    assert app.ui.message == "No unit is taken up. Click one of your units first."
    app.click(app.spot((64, 22)), 3)
    app.paint(pygame.Surface(theme.WINDOW))
    app.click((5, 5))                                               # away from the list
    assert "nothing was chosen" in app.ui.message


def test_the_screen_steps_through_the_units_that_wait():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    assert app.ui.selected == 101                                 # the first unit is taken up for you
    app.key(pygame.K_h)
    assert app.session.order_of(101)["order"] == "hold" and app.ui.selected == 102 and "more to go through" in app.ui.message
    assert app.ui.hover is None                                     # the next is taken up, with no line trailing the pointer
    app.click(layout.buttons(app.size)["next"].center)              # Next unit lets it hold: on to the one after
    assert app.ui.selected == 103 and app.target is not None and "holds" in app.ui.message
    assert 102 not in app.session.waiting_units() and 102 not in app.session.pending["axis"]
    while app.session.waiting_units():
        app.key(pygame.K_h)                                         # each order goes on to the next that waits
    assert "End turn" in app.ui.message and app.ui.selected is None
    app.key(pygame.K_RETURN)
    assert app.session.state["turn"] == 2 and app.session.pending["axis"] == {}          # Hold was for one turn
    assert app.session.waiting_units() == app.session.idle_units() != []                  # so every unit is offered again


# ---- the last turn played back (screen/replay.py) ----------------------------------------

def played(units, axis=(), cw=(), side="cw"):
    """A one-turn game on open desert, and the playback of that turn for one side."""
    from helpers import scenario
    from screen.replay import Playback
    s = Session(scenario(units), GMAP)
    for order in axis:
        assert s.give(order)["ok"]
    s.done()
    for order in cw:
        assert s.give(order)["ok"]
    s.done()
    return Playback(s.before[side], s.views[side]), s


def at(stage, uid):
    return next((u for u in stage["units"] if u[0] == uid), None)


def test_a_road_march_is_shown_at_half_size_until_it_arrives():
    from helpers import unit
    from screen.replay import MARCH_SCALE
    gambut, bardia = list(GMAP.places["Gambut"]["hex"]), list(GMAP.places["Bardia"]["hex"])
    play, s = played([unit(101, "axis", "motorised", gambut), unit(102, "axis", "motorised", [70, 24]),
                      unit(201, "cw", "foot", "Alexandria")],
                     axis=[{"unit": 101, "order": "road_march", "to": bardia}, {"unit": 102, "order": "move", "to": [70, 26]}],
                     side="axis")
    move = play.timeline[0]
    assert move[2]["kind"] == "move" and move[2]["tracks"][101]["march"] and not move[2]["tracks"][102]["march"]
    mid, end = play.stage(move[1] * 0.3), play.stage(play.length)
    assert at(mid, 101)[4] == MARCH_SCALE and at(mid, 102)[4] == 1.0          # a quarter of the area on the road
    assert at(end, 101)[4] == 1.0 and at(end, 101)[3] == tuple(bardia)       # full size again on arrival
    assert len(at(mid, 101)[3]) in (2, 3)                                    # on a hex, or between two


def scenes(play, kind):
    return [x for x in play.timeline if x[2]["kind"] == kind]


def test_strikes_are_shown_one_at_a_time_attackers_first_then_the_reply():
    from helpers import unit
    from screen.replay import BEAT_MS, LEAD_MS, harm
    play, s = played([unit(101, "axis", "armour", [70, 25], steps=20), unit(201, "cw", "armour", [70, 24], steps=20),
                      unit(202, "cw", "foot", [69, 24], steps=9)],
                     cw=[{"unit": 201, "order": "attack", "to": [70, 25]}, {"unit": 202, "order": "attack", "to": [70, 25]}])
    battle = next(e for e in s.views["cw"]["events"] if e["event"] == "battle")
    (t1, e1, first), (t2, e2, second), (t3, e3, reply) = scenes(play, "strike")
    assert (first["by"], first["on"], first["arm"]) == ([201], [101], "armour")
    assert (second["by"], second["on"], second["arm"]) == ([202], [101], "foot")
    assert reply["by"] == [101] and reply["on"] == [201, 202] and reply["reply"]
    assert e1 <= t2 and e2 <= t3                                                # never two at once
    assert "cld" not in battle and first["damage"] + second["damage"] <= harm(battle, "cld")   # the enemy's loss is not told
    assert reply["damage"] == battle["cla"]
    assert first["damage"] > second["damage"]                                   # the tanks did most of it
    assert all(e - t >= BEAT_MS for t, e, _ in scenes(play, "strike"))          # a steady beat
    lead = play.stage(t1 + 100)
    assert at(lead, 201)[6] == "firing" and at(lead, 101)[6] is None and lead["focus"] == (70, 24)
    mid = play.stage(t1 + LEAD_MS + 10)
    assert at(mid, 101)[6] in ("fire0", "fire1") and at(mid, 101)[7] and at(mid, 202)[6] is None
    lights = {at(play.stage(t1 + LEAD_MS + ms), 101)[6] for ms in range(0, first["rattle"], 20)}
    assert lights == {"fire0", "fire1"}                                         # yellow and red by turns
    quiet = play.stage(t1 + LEAD_MS + first["rattle"] + 50)
    assert at(quiet, 101)[6] is None and quiet["meter"] == (first["rattle"] / 3000, False)   # the silence after
    back = play.stage(t3 + LEAD_MS + 10)
    assert at(back, 101)[6] == "firing" and at(back, 201)[6] in ("fire0", "fire1") and back["title"] == "The reply"


def test_the_rattle_is_as_long_as_the_damage_up_to_a_limit_and_each_arm_has_its_own():
    from helpers import unit
    from screen.replay import RATTLE_MAX, rattle_ms
    from screen.sound import RATE, Sounds, fire
    assert rattle_ms(0) == 0 and rattle_ms(5) < rattle_ms(20) < rattle_ms(60) <= rattle_ms(90) == RATTLE_MAX
    for arm in ("armour", "guns", "foot", "recon"):
        assert len(fire(arm, 900)) == RATE * 900 // 1000 and len(fire(arm, 2000)) > len(fire(arm, 900))
    assert len({fire(arm, 600).tobytes() for arm in ("armour", "guns", "foot", "recon")}) == 4
    play, _ = played([unit(101, "axis", "guns", [70, 25], steps=6), unit(201, "cw", "armour", [70, 24], steps=20)],
                     cw=[{"unit": 201, "order": "attack", "to": [70, 25]}])
    cues = [c for c in play.cues(0, play.length) if c[0].startswith("fire:")]
    assert [c[0] for c in cues] == ["fire:armour", "fire:guns"]                 # the tanks, then the guns' reply
    assert cues[1][1] > cues[0][1]                                              # the guns did the tanks more harm
    sounds = Sounds()
    sounds.ok = False
    sounds.play("boom")                                                         # no device: silence, no error
    sounds.stop()


def test_nothing_is_settled_until_every_strike_has_been_shown():
    from helpers import unit
    ring = [[70, 23], [71, 23], [71, 24], [70, 25], [69, 24], [69, 23]]
    units = [unit(101, "axis", "foot", [70, 24], steps=3)] + [unit(201 + n, "cw", "armour", h, steps=10) for n, h in enumerate(ring)]
    play, _ = played(units, cw=[{"unit": 201 + n, "order": "attack", "to": [70, 24]} for n in range(6)])
    assert len(scenes(play, "strike")) == 6                                     # six attackers; the reply did the least there is
    start, end, outcome = scenes(play, "outcome")[0]
    assert outcome["gone"] == [101] and outcome["flags"] == [101] and outcome["burst"] == []     # surrounded: it surrenders
    assert ("fall", 0) in play.cues(0, play.length) and ("boom", 0) not in play.cues(0, play.length)
    assert at(play.stage(start - 10), 101) is not None and at(play.stage(start + 100), 101)[5] == 1.0   # still there
    assert play.stage(start + 1000)["bursts"] and at(play.stage(play.length), 101) is None
    assert at(play.stage(play.length), 201)[3] == (70, 24)                      # the victors follow up

    play, _ = played([unit(101, "axis", "foot", [70, 25], steps=3), unit(201, "cw", "armour", [70, 24], steps=15),
                      unit(102, "axis", "guns", [66, 25], steps=6), unit(202, "cw", "armour", [66, 24], steps=6)],
                     cw=[{"unit": 201, "order": "attack", "to": [70, 25]}, {"unit": 202, "order": "attack", "to": [66, 25]}])
    (start, end, outcome), (start2, _, others) = scenes(play, "outcome")
    assert set(outcome["slides"]) == {101} and set(outcome["advance"]) == {201}  # one battle: who falls back, who follows
    assert outcome["focus"] == (70, 25) and others["held"] == [102, 202] and not others["slides"]
    last = scenes(play, "strike")[-1]
    assert at(play.stage(last[1] - 10), 101)[3] == (70, 25)                     # it has not fallen back yet
    from screen import replay
    fallen = start + replay.HOLD_MS + replay.FALL_MS                            # the retreat is over
    assert play.stage(start + 100)["title"] == "axis foot 101 falls back"
    assert at(play.stage(fallen + 300), 101)[3] == ((70, 25), (69, 25), 1.0)    # the beaten are out of the hex,
    assert at(play.stage(fallen + 300), 201)[3] == (70, 24)                     # and the victor has not moved: the hex is seen empty
    assert play.stage(fallen + 300)["ring"] == (70, 25)
    going = play.stage(fallen + replay.EMPTY_MS + 300)
    assert going["title"] == "cw armour 201 advances into the hex" and at(going, 201)[3][:2] == ((70, 24), (70, 25))
    assert at(play.stage(start2 + 800), 102)[6] == "held"
    assert at(play.stage(play.length), 101)[3] == (69, 25) and ("fall", 0) in play.cues(0, play.length)


def test_the_window_plays_the_turn_back_goes_faster_with_f_and_any_other_key_ends_it():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)}))
    assert app.play is None                                         # nothing to play before the first turn
    app.done()
    assert app.play is not None and len(scenes(app.play, "strike")) >= 2 and "skip" in app.ui.message
    surface = pygame.Surface(theme.WINDOW)
    for _ in range(30):
        app.advance(1000)                                           # a long frame moves the clock 50 ms, no more
        app.paint(surface)
    assert app.play_t == 30 * 50
    app.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f))
    app.advance(40)
    assert app.fast and app.play_t == 30 * 50 + 40 * 3
    app.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    assert app.play is None and not app.fast and "hold unless ordered" in app.ui.message
    app.done()
    assert app.session.state["turn"] == 3


def test_playback_actions_are_clickable_without_accidentally_skipping_the_turn():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)}))
    app.done()
    assert app.play is not None
    controls = layout.playback_controls(app.size)
    assert all(layout.areas(app.size)["console"].contains(rect) for rect in controls.values())
    surface = pygame.Surface(app.size)
    app.paint(surface)

    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 100)))
    assert app.play is not None and not app.fast
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=controls["speed"].center))
    assert app.fast and app.play is not None
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=controls["next"].center))
    assert app.play is not None and app.play_t > 0
    app.advance(40)
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=controls["back"].center))
    assert app.play_t == app.play.timeline[1][0]
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=controls["back"].center))
    assert app.play_t == 0
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=controls["skip"].center))
    assert app.play is None and not app.fast and "hold unless ordered" in app.ui.message


@pytest.mark.parametrize("size", [(900, 560), (1400, 860)])
def test_title_screen_has_a_clickable_start_and_preserves_the_game(size):
    pygame.init()
    app = App(Session(regiments(), GMAP), size=size)
    before = app.session.to_save()
    app.title = True
    surface = pygame.Surface(size)
    app.paint(surface)
    title = pygame.image.tostring(surface, "RGB")
    assert surface.get_at((size[0] // 2, size[1] // 2))[:3] != (0, 0, 0)
    assert surface.get_rect().contains(layout.title_button(size))
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10)))
    assert app.title
    app.handle_one(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                      pos=layout.title_button(size).center))
    assert not app.title and app.session.to_save() == before
    app.paint(surface)
    assert pygame.image.tostring(surface, "RGB") != title
    app.title = True
    app.handle_one(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert not app.title


def test_title_screen_names_the_computer_opponent_and_human_side():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.ComputerOpponent(GMAP)}))
    app.title = True
    seen = []
    original = app.painter.text
    app.painter.text = lambda surface, words, *a, **k: (seen.append(str(words)), original(surface, words, *a, **k))
    app.paint(pygame.Surface(app.size))
    assert "You command Commonwealth · Computer commands Axis" in seen


def test_window_icon_is_a_transparent_hex_with_visible_center():
    from screen.branding import icon

    mark = icon(64)
    assert mark.get_size() == (64, 64)
    assert mark.get_at((0, 0)).a == 0
    assert mark.get_at((32, 32)).a == 255


# ---- found by playtest -------------------------------------------------------------------

def test_when_the_playback_runs_out_the_message_goes_back_to_the_orders():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)}))
    app.done()
    assert "skip" in app.ui.message
    while app.play:
        app.advance(50)
    assert "skip" not in app.ui.message and "hold unless ordered" in app.ui.message


def test_panel_text_is_wrapped_between_words_never_cut():
    from screen.draw import Painter, wrap
    pygame.init()
    font = Painter(GMAP).font(12)
    text = "Battle near Sidi Rezegh: 4 steps lost, defender retreats"
    rows = wrap(font, text, 150)
    assert len(rows) > 1 and all(font.size(r)[0] <= 150 for r in rows)
    assert " ".join(r.strip() for r in rows) == text
    assert wrap(font, "short", 150) == ["short"] and wrap(font, "", 150) == []


def test_a_battle_is_named_by_the_nearest_place_not_by_hex_numbers():
    from screen.draw import describe, whereabouts
    assert whereabouts(GMAP, (55, 10)) == "at Tobruk" and whereabouts(GMAP, [56, 14]) == "near Sidi Rezegh"
    s = Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)})
    s.done()
    told = [describe(e, s) for e in s.view["events"] if e["event"] == "battle"]
    assert told and all("Battle at " in t or "Battle near " in t for t in told)
    assert not any(ch.isdigit() for t in told for ch in t.split(":")[0])


def test_with_no_human_the_screen_can_render_a_spectator_view(tmp_path):
    import subprocess
    import sys
    shot = tmp_path / "spectator.png"
    run = subprocess.run([sys.executable, "-m", "screen", "sidi_rezegh", "--axis", "computer",
                          "--cw", "computer", "--seed", "1941", "--shot", str(shot)],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert shot.exists() and shot.stat().st_size > 0


def test_a_burning_counter_still_shows_its_symbol():
    from screen.replay import LEAD_MS
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)}))
    app.done()
    start, _, strike = next(x for x in app.play.timeline if x[2]["kind"] == "strike" and x[2]["rattle"] > 200)
    app.play_t = start + LEAD_MS + 10
    stage = app.play.stage(app.play_t)
    burning = next(u for u in stage["units"] if u[6] in ("fire0", "fire1"))
    app.ui.zoom = 1.5
    app.centre_on(burning[3])
    surface = pygame.Surface(theme.WINDOW)
    app.painter.frame(surface, app.session, app.ui, stage)
    x, y = app.ui.layout.centre(burning[3])
    x, y = int(x - int(app.ui.cam[0]) * app.ui.zoom), int(y - int(app.ui.cam[1]) * app.ui.zoom)
    half = app.ui.layout.counter // 2 - 6
    inside = {tuple(surface.get_at((x + dx, y + dy)))[:3] for dx in range(-half, half, 2) for dy in range(-half, half, 2)}
    assert len(inside) >= 4                                         # face, box, lines and number, all tinted


def test_a_standing_attack_ends_when_the_defenders_do_not_fall_back():
    from helpers import scenario, unit
    s = Session(scenario([unit(101, "axis", "guns", [70, 25], steps=8), unit(201, "cw", "armour", [70, 24], steps=6),
                          unit(102, "axis", "foot", [66, 25], steps=3), unit(202, "cw", "armour", [66, 23], steps=15)]),
                GMAP, humans=["cw"])
    s.give({"unit": 201, "order": "attack", "to": [70, 25]})       # tanks on to guns: it fails
    s.give({"unit": 202, "order": "attack", "to": [66, 25]})       # tanks on to a weak brigade, from two hexes away
    s.done()
    assert (201, "was repulsed") in s.ended["cw"] and 201 not in s.pending["cw"] and 201 in s.waiting_units()
    battle = [e for e in s.view["events"] if e["event"] == "battle" and 202 in e["attackers"]]
    assert battle and battle[0]["retreated"]                       # the other attack drove its enemy back...
    assert (202, "was repulsed") not in s.ended["cw"] and (202, "has arrived") in s.ended["cw"]   # ...and followed up
    again = s.give({"unit": 201, "order": "attack", "to": [70, 25]})            # to attack again is a new decision,
    assert again["ok"] == (s.unit(201)["cohesion"] >= 40)                        # open to it unless it is too worn


# ---- found by the second playtest --------------------------------------------------------

def keys(app, *names):
    for name in names:
        app.handle(pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, "K_" + name)))


def settle(app):
    """Let the map finish gliding."""
    for _ in range(400):
        if not app.target:
            break
        app.tick(16)
    assert app.target is None


def test_a_keyboard_only_player_can_choose_a_destination_and_enter_does_not_end_the_turn():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    assert app.ui.selected == 201 and app.session.unit(201)["hex"] == [64, 22]
    cam = list(app.ui.cam)
    keys(app, "m")
    assert app.ui.mode == "move" and app.ui.hover == (64, 22) and "arrow keys" in app.ui.message
    keys(app, "RIGHT", "RIGHT", "UP")
    assert app.ui.hover == (66, 21) and app.ui.cam == cam            # the cursor moved, not the map
    surface = pygame.Surface(theme.WINDOW)
    app.paint(surface)
    assert "Move here" in app.ui.preview                             # the way is previewed as with the mouse
    keys(app, "RETURN")
    assert app.session.pending["cw"][201] == {"unit": 201, "order": "move", "to": [66, 21]}
    assert app.session.state["turn"] == 1 and app.ui.mode is None and app.ui.selected == 202   # on to the next
    keys(app, "a")                                                   # no enemy within reach: Attack is greyed
    assert app.ui.mode is None and "No enemy in sight" in app.ui.message
    keys(app, "m", "LEFT", "ESCAPE")                                 # Escape cancels
    assert app.ui.mode is None and 202 not in app.session.pending["cw"]
    keys(app, "m", "RETURN")                                         # Enter with no hex chosen: nothing happens
    assert app.session.state["turn"] == 1 and "Choose the hex" in app.ui.message
    keys(app, "ESCAPE", "RETURN")
    assert app.session.state["turn"] == 1 and "not been gone through" in app.ui.message    # asked once
    keys(app, "RIGHT", "RETURN")
    assert app.session.state["turn"] == 1                            # another key in between: asked again
    keys(app, "RETURN")
    assert app.session.state["turn"] == 2                            # twice running: the turn ends
    assert app.session.unit(201)["hex"] == [66, 21]


def test_left_and_right_keep_to_the_row_and_the_map_follows_the_cursor():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    keys(app, "m")
    for _ in range(30):
        keys(app, "RIGHT")
    assert app.ui.hover == (94, 22)                                  # the same row all the way
    settle(app)
    assert app.map_rect().collidepoint(app.spot(app.ui.hover))       # and still in view
    for _ in range(200):
        keys(app, "DOWN", "RIGHT")
    assert app.ui.hover == (GMAP.cols - 1, GMAP.rows - 1)            # it stops at the edge of the map


def test_the_unit_taken_up_for_orders_is_brought_to_the_middle():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    middle = app.map_rect().center
    for _ in range(8):                                               # the first at the start, then each by Next unit
        settle(app)
        x, y = app.spot(tuple(app.session.unit(app.ui.selected)["hex"]))
        assert abs(x - middle[0]) <= 2 and abs(y - middle[1]) <= 2, app.ui.selected
        keys(app, "h")
    keys(app, "TAB")                                                 # and Tab does the same
    assert app.target is not None                                    # by a glide, not a jump
    settle(app)
    x, y = app.spot(tuple(app.session.unit(app.ui.selected)["hex"]))
    assert abs(x - middle[0]) <= 2 and abs(y - middle[1]) <= 2


def test_every_unit_is_on_the_screen_while_it_moves():
    from engine.gamemap import distance
    from screen.replay import MOVE_LEAD_MS
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)}))
    s = app.session
    for u in s.view["units"]:                                        # every unit at the nearest enemy in sight
        if u["type"] != "hq" and s.view["enemy"]:
            e = min(s.view["enemy"], key=lambda e: (distance(tuple(u["hex"]), tuple(e["hex"])), e["id"]))
            s.give({"unit": u["id"], "order": "attack", "to": e["hex"]})
    app.done()
    moves = scenes(app.play, "move")
    movers = [i for _, _, sc in moves for i in sc["tracks"]]
    assert len(moves) > 1 and len(movers) == len(set(movers)) >= 12  # in groups, each unit in one
    seen, area = 0, app.map_rect()
    while app.play and app.play_t < moves[-1][1]:
        app.tick(16)
        for start, end, sc in moves:
            if start + MOVE_LEAD_MS <= app.play_t < end:             # this group is on the move
                stage = app.play.stage(app.play_t)
                for i, _, _, where, *_ in stage["units"]:
                    if i in sc["tracks"]:
                        a = app.spot(where[0]) if len(where) == 3 else app.spot(where)
                        b = app.spot(where[1]) if len(where) == 3 else a
                        f = where[2] if len(where) == 3 else 0
                        assert area.collidepoint(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), (i, app.play_t)
                        seen += 1
    assert seen > 500


def test_a_march_too_long_to_fit_is_followed_by_the_map():
    from helpers import scenario, unit
    from screen.replay import Playback
    s = Session(scenario([unit(102, "axis", "recon", "Tobruk", steps=3), unit(201, "cw", "foot", "Alexandria")]),
                GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)})
    s.give({"unit": 102, "order": "road_march", "to": list(GMAP.places["Fort Capuzzo"]["hex"])})
    s.done()
    play = Playback(s.before["axis"], s.view, span=(8, 6))
    start, end, move = play.timeline[0]
    assert move["follow"] == 102
    spots = {play.stage(start + ms)["focus"] for ms in range(600, end - start, 200)}
    assert len(spots) > 3                                            # the focus goes along the road with it


# ---- found by the third playtest ---------------------------------------------------------

def test_one_of_a_thing_is_not_plural():
    from helpers import scenario, unit
    from screen.draw import describe
    assert (theme.count(1, "step"), theme.count(2, "step"), theme.count(1, "hex", "hexes"), theme.count(0, "unit")) \
        == ("1 step", "2 steps", "1 hex", "0 units")
    pygame.init()
    s = Session(scenario([unit(101, "axis", "armour", [70, 25], steps=12), unit(201, "cw", "armour", [70, 24], steps=13),
                          unit(202, "cw", "foot", [72, 24])]), GMAP, humans=["cw"])
    app = App(s)
    keys(app, "h")
    assert "1 more to go through" in app.ui.message
    app.begin_message()
    assert app.ui.message.startswith("1 unit holds unless ordered.")
    keys(app, "RETURN")
    assert app.ui.message.startswith("1 unit has not been gone through and will hold its ground.")
    told = describe({"event": "battle", "hex": [55, 10], "lost": {"1": 1, "2": 0}, "retreated": False}, s)
    assert told == "Battle at Tobruk" and "step" not in s.lost_words({"type": "armour", "real": [100, "tanks", 10]}, 2)
    assert s.lost_words({"type": "armour", "real": [100, "tanks", 10]}, 2) == "about 20 tanks"


def test_an_order_that_ends_is_told_as_a_sentence():
    from helpers import scenario, unit
    pygame.init()
    s = Session(scenario([unit(101, "axis", "foot", [70, 28]), unit(201, "cw", "armour", [66, 24], cohesion=41, name="4th Armoured Brigade"),
                          unit(202, "cw", "foot", [72, 24], name="2nd Division")]), GMAP, humans=["cw"])
    s.give({"unit": 201, "order": "attack", "to": [70, 28]})        # the march will wear it below what an attack needs
    s.give({"unit": 202, "order": "move", "to": [72, 25]})
    app = App(s)
    app.done()
    app.play = None
    app.begin_message()
    assert app.ui.message.startswith("4th Armoured Brigade is too disorganised to attack.  2nd Division has arrived.")
    assert "The unit" not in app.ui.message and "the unit" not in app.ui.message


def test_a_rejected_destination_keeps_the_order_and_the_cursor():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    assert app.ui.selected == 101 and app.session.unit(101)["hex"] == [59, 11]
    keys(app, "m", "RIGHT", "RETURN")                              # (60, 11) is the sea
    assert app.ui.message == "The unit cannot enter that ground."
    assert app.ui.mode == "move" and app.ui.hover == (60, 11) and app.ui.selected == 101
    keys(app, "DOWN", "RETURN")                                    # carry on from there: (60, 12) is land
    assert app.session.pending["axis"][101] == {"unit": 101, "order": "move", "to": [60, 12]} and app.ui.mode is None


# ---- decisions A to E --------------------------------------------------------------------

class Heard:
    """A stand-in for the sound device that notes what it was asked to play."""
    def __init__(self):
        self.played = []

    def play(self, name, amount=0):
        self.played.append((name, amount))

    def stop(self):
        self.played.append(("stop", 0))


def watching():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)}))
    app.done()
    app.sounds = Heard()
    return app


def test_a_key_skips_one_scene_and_leaves_the_rest_playing():       # A
    app = watching()
    starts = [start for start, _, _ in app.play.timeline]
    assert "Left/Right" in app.ui.message and "Done skips" in app.ui.message
    app.advance(40)
    keys(app, "RIGHT")
    assert app.play is not None and app.play_t == starts[1] and ("stop", 0) in app.sounds.played
    keys(app, "LEFT")
    assert app.play_t == starts[0]
    keys(app, "RIGHT")
    keys(app, "n")
    assert app.play_t == starts[2]
    for _ in starts[2:]:
        keys(app, "RIGHT")
    assert app.play is None and "hold unless ordered" in app.ui.message      # past the last scene: back to the orders


def test_fast_playback_keeps_a_shorter_rattle():                     # A
    from screen.app import FAST
    from screen.replay import LEAD_MS
    app = watching()
    start, _, strike = next(x for x in app.play.timeline if x[2]["kind"] == "strike" and x[2]["rattle"])
    app.play_t = start + LEAD_MS - 1
    keys(app, "f")
    app.advance(10)
    assert ("fire:" + strike["arm"], strike["rattle"] // FAST) in app.sounds.played
    assert not any(name == "tick" for name, _ in app.sounds.played)


def test_a_reply_that_did_the_least_there_is_is_not_shown():         # A
    from engine.combat import COH_MIN
    from helpers import unit
    play, s = played([unit(101, "axis", "foot", [70, 25], steps=3), unit(201, "cw", "armour", [70, 24], steps=15)],
                     cw=[{"unit": 201, "order": "attack", "to": [70, 25]}])
    battle = next(e for e in s.views["cw"]["events"] if e["event"] == "battle")
    assert battle["cla"] == COH_MIN and [x[2]["by"] for x in scenes(play, "strike")] == [[201]]
    play, s = played([unit(101, "axis", "guns", [70, 25], steps=6), unit(201, "cw", "armour", [70, 24], steps=20)],
                     cw=[{"unit": 201, "order": "attack", "to": [70, 25]}])
    assert [x[2]["reply"] for x in scenes(play, "strike")] == [False, True]      # a reply that hurt is shown


def test_the_end_of_a_game_says_how_the_result_was_reached():        # C, E
    from screen.draw import result_assessment, score_lines
    view = {"vp": {"axis": 252, "cw": 112}, "kills": {"axis": 90, "cw": 20}, "par": 106}
    assert score_lines(view) == ["Axis: 252 points (162 for ground held; 90 for enemy losses).",
                                 "Commonwealth: 112 points (92 for ground held; 20 for enemy losses).",
                                 "Against the starting position: Axis gained 34 points."]
    report_view = {"places": {"Sidi Rezegh": "axis", "Belhamed": "axis", "Tobruk": "cw"}}
    assert "denying a link" in result_assessment(report_view, {"id": "sidi_rezegh"})[0]
    report_view["places"]["Sidi Rezegh"] = report_view["places"]["Belhamed"] = "cw"
    assert "securing a link" in result_assessment(report_view, {"id": "sidi_rezegh"})[0]
    report_view["places"]["Belhamed"] = "axis"
    assert "Neither side fully met" in result_assessment(report_view, {"id": "sidi_rezegh"})[0]
    pygame.init()
    s = Session(small(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)})
    while not s.state["over"]:
        s.done()
    app = App(s)
    app.play = None
    assert app.ui.message.startswith("Game over:")
    drawn = []
    original = app.painter.text
    app.painter.text = lambda surface, words, pos, *a, **k: (drawn.append((str(words), pos)),
                                                              original(surface, words, pos, *a, **k))
    labels = []
    fitted = app.painter.fitted
    app.painter.fitted = lambda surface, words, *a, **k: (labels.append(str(words)),
                                                         fitted(surface, words, *a, **k))
    for size in (theme.WINDOW, (900, 560)):
        app.size = size
        app.paint(pygame.Surface(size))                               # the result must clear the header at both sizes
        heading = next(pos for words, pos in drawn if words == "Battle Result")
        verdict = "A draw" if s.state["result"]["winner"] is None else \
                  f"{theme.SIDE_NAME[s.state['result']['winner']]}: {s.state['result']['grade']} victory"
        result = next(pos for words, pos in drawn if words == verdict)
        assessment = next(pos for words, pos in drawn if words == "FIELD ASSESSMENT")
        assert heading[1] == 65 and result[1] >= layout.HEAD_Y and assessment[1] > result[1]
        assert "Game over" in labels
        assert any(rect == layout.buttons(size)["done"] and "battle has ended" in tip
                   for rect, tip in app.painter.tips)
        drawn.clear()
        labels.clear()
    assert s.view["par"] == small()["par"] and set(s.view["kills"]) == {"axis", "cw"}
    assert all(u["fate"] for u in s.view["units"] if u["status"] in ("destroyed", "withdrawn"))
    app.click(layout.buttons(app.size)["done"].center)
    assert "no next turn" in app.ui.message


# ---- the owner's notes on the screen -----------------------------------------------------

def test_morale_is_told_in_nine_named_levels_and_strength_in_real_terms():
    assert [theme.morale(c)[0] for c in (0, 11, 12, 39, 40, 50, 99, 100)] == [1, 1, 2, 4, 4, 5, 9, 9]
    assert theme.morale(0)[1] == "Very poor" and theme.morale(60)[1] == "Normal" and theme.morale(100)[1] == "Excellent"
    assert len(theme.MORALE) == 9
    assert theme.strength({"type": "armour", "steps": 13}) == "about 130 tanks"
    assert theme.strength({"type": "foot", "steps": 9}) == "about 7,200 men"
    assert theme.strength({"type": "hq", "steps": 1}) == "about 300 men"        # an HQ: a nominal figure
    assert theme.strength({"type": "foot"}) == ""                                # an enemy not seen close


def test_the_orders_are_in_the_console_and_travel_is_the_road_march():
    area, where = layout.areas(theme.WINDOW), layout.buttons(theme.WINDOW)
    for size, minimum in ((theme.WINDOW, (64, 44)), ((900, 560), (52, 38))):
        emblem = layout.footer_flag(size)
        assert emblem.size == minimum
        assert layout.areas(size)["console"].contains(emblem)
        assert emblem.right + 10 < layout.buttons(size)["move"].left - 10
    assert len(where) == 11 and all(area["console"].contains(r) for r in where.values())
    assert not any(a.colliderect(b) for n, a in where.items() for m, b in where.items() if n < m)
    assert theme.ORDER_NAME["road_march"] == "Travel" and ("road_march", "Travel", "T") in theme.BUTTONS
    assert ("rest", "Rest", "R") in theme.BUTTONS
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    app.click(where["road_march"].center)
    assert app.ui.mode == "road_march"


def test_counters_show_pictures_unless_nato_symbols_are_chosen():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    app.ui.zoom = 1.5
    app.centre_on((64, 22))
    frames = []
    for _ in range(2):
        surface = pygame.Surface(theme.WINDOW)
        app.paint(surface)
        frames.append(pygame.image.tostring(surface.subsurface(layout.areas(theme.WINDOW)["map"]), "RGB"))
        keys(app, "F3")
    assert app.ui.symbols == "pictures" and frames[0] != frames[1]              # F3 changed what the counters show
    assert "pictures" in app.ui.message


def test_the_way_shows_how_far_the_fuel_goes():
    from helpers import scenario, unit
    s = Session(scenario([unit(101, "axis", "armour", [66, 24], fuel=20), unit(201, "cw", "foot", "Alexandria")]),
                GMAP, humans=["axis"])
    p = s.preview(101, "move", (76, 24))
    assert p["range"] == 5 and len(p["path"]) == 10 and p["reach"] == 8          # five hexes of fuel, ten to go
    pygame.init()
    app = App(s)
    app.ui.mode, app.ui.hover = "move", (76, 24)
    app.paint(pygame.Surface(theme.WINDOW))
    assert "about 2 turns" in app.ui.preview and "fuel gives out after 50 km (5 hexes)" in app.ui.preview
    assert s.preview(101, "move", (68, 24))["range"] == 5 and "foot" not in app.ui.message


def test_at_the_screen_a_group_is_taken_up_and_ordered_as_one():     # RULES 20.2.5
    from helpers import scenario, unit
    units = [unit(110, "axis", "hq", [70, 24], steps=1), unit(111, "axis", "armour", [70, 24], parent=110, fuel=40),
             unit(112, "axis", "motorised", [70, 24], parent=110), unit(201, "cw", "foot", "Alexandria")]
    s = Session(scenario(units), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)})
    assert s.waiting_units() == [110] and s.leader(112) == 110 and [m["id"] for m in s.members(111)] == [110, 111, 112]
    p = s.preview(112, "move", (80, 24))
    wheels = {m["id"]: m["fuel"] for m in s.members(110)}            # refuelled by the HQ in the Supply phase
    assert p["reach"] == 8 and p["range"] == min(wheels[110] // 2, wheels[111] // 4, wheels[112] // 3)   # the tanks' pace
    assert s.give({"unit": 112, "order": "move", "to": [74, 24]})["ok"] and s.pending["axis"] == {
        110: {"unit": 110, "order": "move", "to": [74, 24]}}
    pygame.init()
    app = App(s)
    app.ui.selected = None
    app.centre_on((70, 24))
    app.click(app.spot((70, 24)))
    assert app.ui.selected == 110                                    # a click on the stack takes up the group
    s.done()
    assert {tuple(u["hex"]) for u in s.view["units"]} == {(74, 24)} or len({tuple(u["hex"]) for u in s.view["units"]}) == 1


# ---- groups at the screen (RULES 20.2) ---------------------------------------------------

def test_a_division_is_one_pile_on_the_map_and_one_card_in_the_panel():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    s = app.session
    assert s.waiting_units()[:4] == [101, 102, 103, 104] and 111 not in s.waiting_units()   # a group waits as one
    app.ui.selected = None                                          # nothing taken up: a click takes up what is there
    app.centre_on((59, 11))
    app.click(app.spot((59, 11)))
    assert app.ui.selected == 110 and [m["id"] for m in s.members(110)] == [110, 111, 112, 113, 114]
    surface = pygame.Surface(theme.WINDOW)
    app.paint(surface)
    assert sorted(app.painter.member_rects) == [110, 111, 112, 113, 114]         # its units are listed, to click
    assert theme.strength(s.unit(111)) == "about 133 tanks"                      # the scenario's figure, not steps
    assert s.give({"unit": 113, "order": "move", "to": [61, 12]})["ok"] and list(s.pending["axis"]) == [110]


def test_split_takes_a_unit_out_of_its_group_and_join_puts_it_back():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    s = app.session
    app.ui.selected = None
    app.centre_on((59, 11))
    app.click(app.spot((59, 11)))
    app.paint(pygame.Surface(theme.WINDOW))
    app.click(layout.buttons(app.size)["split"].center)
    assert "details hierarchy" in app.ui.message                                  # nothing chosen from the group yet
    app.paint(pygame.Surface(theme.WINDOW))
    app.click(app.painter.member_rects[111].center)                              # the panzer regiment, by itself
    assert app.ui.selected == 111 and app.ui.alone
    keys(app, "m")
    app.click(app.spot((61, 12)))                                                # off to Gambut alone
    assert s.pending["axis"][111] == {"unit": 111, "order": "move", "to": [61, 12], "alone": True} and not app.ui.alone
    assert s.unit(111)["group"] is None and [m["id"] for m in s.members(110)] == [110, 112, 113, 114]   # split at once
    s.done()
    assert s.unit(111)["hex"] == [61, 12] and s.unit(111)["group"] is None
    assert [m["id"] for m in s.members(110)] == [110, 112, 113, 114]
    app.ui.selected = 111
    keys(app, "j")
    assert app.ui.mode == "join"
    app.centre_on((59, 11))
    app.click(app.spot((58, 12)))                                                # nobody of yours is there
    assert "no other unit of yours" in app.ui.message and app.ui.mode == "join"
    app.click(app.spot((59, 11)))
    assert s.pending["axis"][111] == {"unit": 111, "order": "join", "with": 110}
    s.done()
    assert s.unit(111)["hex"] == [59, 11] and s.unit(111)["group"] == 110 and (111, "has joined") in s.ended["axis"]


def test_recall_brings_a_division_in_to_its_hq():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    s = app.session
    app.ui.selected = 140                                                        # Savona's HQ: one regiment is at Capuzzo
    keys(app, "c")
    assert "1 unit recalled" in app.ui.message and s.pending["axis"][142] == {"unit": 142, "order": "join", "with": 140}
    keys(app, "c")
    app.ui.selected = 101
    keys(app, "c")
    assert "Only a division's HQ" in app.ui.message                              # the Panzergruppe leads no division
    for _ in range(3):
        s.done()
    assert s.unit(142)["group"] == 140 and s.unit(142)["hex"] == s.unit(140)["hex"]
    app.ui.selected = 140
    keys(app, "c")
    assert "away from it" in app.ui.message                                      # nothing left to recall: the button says why


# ---- the owner's second list -------------------------------------------------------------

def test_a_button_that_cannot_be_used_says_why():                    # 3a, 3c
    pygame.init()
    s = Session(regiments(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)})
    assert s.can(170, "road_march")[1].startswith("It is not on a road or track")                  # Brescia, off the road
    from helpers import scenario, unit
    desert = Session(scenario([unit(101, "axis", "armour", [70, 24]), unit(201, "cw", "foot", "Alexandria")]), GMAP, humans=["axis"])
    assert desert.can(101, "road_march") == (False, "It is not on a road or track: one cannot march in the desert.")
    assert s.can(110, "road_march") == (True, "")                                                  # 15. Panzer, on the coast road
    assert desert.can(101, "attack") == (False, "No enemy in sight within its reach.")             # nobody for miles
    assert s.can(200, "attack") == (True, "")                                                      # Bologna, facing Tobruk
    assert s.can(101, "attack")[1] == "A headquarters does not attack." and s.can(101, "dig_in")[0] is False
    assert s.can(107, "join") == (True, "")                                                        # any unit of yours may be joined
    assert s.can(107, "split")[1] == "It is not in a group."
    assert not s.can(110, "split")[0] and s.can(next(m["id"] for m in s.members(110) if m["id"] != 110), "split", True)[0]
    assert s.can(110, "recall")[0] is False and s.can(140, "recall") == (True, "")                  # Savona has a regiment away
    assert s.can(142, "join") == (True, "")
    app = App(s)
    app.ui.selected = 170
    assert s.offers(170) == ["move", "attack", "road_march", "hold", "dig_in", "rest", "join", "split"]   # March greyed, not hidden
    assert s.blocked(170) == [("road_march", "not on a road or track.")]
    app.click(layout.buttons(app.size)["road_march"].center)                                       # greyed: pressed, it says why
    assert app.ui.mode is None and "march" in app.ui.message
    keys(app, "t")                                                                                 # by key, it says why
    assert app.ui.mode is None and "cannot march in the desert" in app.ui.message


def test_pressing_a_units_own_order_takes_it_back():                 # 3b
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    s = app.session
    app.ui.selected = 110
    keys(app, "d")
    assert s.pending["axis"][110]["order"] == "dig_in"
    app.ui.selected = 110
    app.click(layout.buttons(app.size)["dig_in"].center)
    assert 110 not in s.pending["axis"] and 110 not in s.standing["axis"] and "cancelled" in app.ui.message
    assert 110 in s.waiting_units()


def test_a_crowded_hex_offers_a_list_to_choose_from():               # 1g
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    app.ui.selected = None
    app.centre_on((55, 10))
    app.click(app.spot((55, 10)))                                    # Tobruk: 70th Division and the tank brigade
    assert app.ui.chooser == {"hex": (55, 10), "ids": [307, 350], "mover": None} and app.ui.selected is None
    app.paint(pygame.Surface(theme.WINDOW))
    app.click(app.painter.chooser_rects[307].center)
    assert app.ui.selected == 307 and app.ui.chooser is None
    app.click(app.spot((55, 10)))
    app.paint(pygame.Surface(theme.WINDOW))
    app.click((5, 5))                                                # a click elsewhere puts the list away
    assert app.ui.chooser is None and app.ui.selected == 307


def test_a_click_on_an_orders_line_finds_its_unit():                 # 2a
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    s.give({"unit": 310, "order": "move", "to": [60, 18]})
    way = s.preview(310, "move", (60, 18))["path"]
    assert s.order_at(way[2]) == 310 and s.order_at((100, 30)) is None
    app.ui.selected = None
    app.centre_on(way[2])
    app.click(app.spot(way[2]))
    assert app.ui.selected == 310 and "unit with that order" in app.ui.message


def test_the_map_scrolls_when_the_mouse_is_at_its_edge_while_a_unit_is_taken_up():    # 2b
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    settle(app)
    area, cam = app.map_rect(), list(app.ui.cam)
    app.ui.mouse = (area.right - 5, area.centery)
    assert app.edge() == (1, 0)
    for _ in range(10):
        app.tick(16)
    assert app.ui.cam[0] > cam[0] + 100 and app.ui.cam[1] == cam[1]
    app.ui.mouse = area.center
    assert app.edge() == (0, 0)
    app.ui.selected, app.ui.mouse = None, (area.right - 5, area.centery)
    assert app.edge() == (0, 0)                                      # nothing taken up: the map stays


def test_nz_divisional_cavalry_strength_is_not_presented_as_only_armoured_cars():
    s = Session(regiments(), GMAP, humans=["cw"])
    nz, cars = s.unit(335), s.unit(305)
    assert theme.strength_now(nz) == (30, 30, "scout vehicles")
    assert theme.strength(nz) == "about 30 scout vehicles"
    assert theme.strength(s.unit(305)) == "about 60 armoured cars"
    assert "not a vehicle inventory" in theme.strength_tip(nz)
    assert s.lost_words(nz, 1).endswith("scout vehicles")
    assert s.lost_words(cars, 1).endswith("armoured cars")
    assert Session.from_save(s.to_save(), GMAP).counter_art[335] == "mkvi_light"
    assert "scout vehicles" in theme.CLAIMED
    s.views["axis"]["events"] = [{"event": "battle", "sides": ["axis", "cw"],
                                  "attackers": [111], "defenders": [335],
                                  "lost": {"335": 1}, "backed": None}]
    assert "15 scout vehicles" in s.claims("axis")[0][0]


def test_strength_is_coloured_by_how_much_is_left_and_the_tooltip_gives_the_figures():    # 3e, 1b
    full = {"type": "armour", "steps": 10, "real": [100, "tanks", 10]}
    assert [theme.strength_colour(dict(full, steps=n)) for n in (10, 8, 6, 4)] == [theme.INK, theme.STRONG, theme.WORN, theme.WEAK]
    assert theme.strength_tip(dict(full, steps=8)) == "about 80 of 100 tanks (80%, 20 lost)"
    assert "nominal" in theme.strength_tip({"type": "hq", "steps": 1}) and theme.strength_colour({"type": "hq", "steps": 1}) == theme.INK


def test_reports_are_one_a_unit_and_only_what_matters_and_a_back_button_returns_to_the_group():   # 3f, 3g
    pygame.init()
    s = Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)})
    from engine.gamemap import distance
    for _ in range(3):                                               # three turns of everyone at the nearest enemy in sight
        for lead in s.waiting_units():
            u = s.unit(lead)
            if s.view["enemy"] and s.can(lead, "attack")[0]:
                e = min(s.view["enemy"], key=lambda e: (distance(tuple(u["hex"]), tuple(e["hex"])), e["id"]))
                s.give({"unit": lead, "order": "attack", "to": e["hex"]})
        s.done()
    told = s.reports()
    words = [w for w, _ in told]
    assert told and all(isinstance(w, str) for w in words)
    own = [uid for _, uid in told if uid is not None]
    assert len(set(own)) == len(own)                                  # one for each unit or group, no more
    assert not any("step" in w or "haul" in w or "arrived" in w for w in words)      # no arithmetic, no routine
    kinds = ("driven back", "heavy losses", "repulsed", "drove the enemy", "lost its supply", "out of fuel", "morale is low",
             "under half strength", "enemy in contact", "destroyed", "surrendered", "starved", "could not go on",
             "We claim", "stood behind")
    assert all(any(k in w for k in kinds) for w in words), words
    app = App(s)
    app.play = None
    app.paint(pygame.Surface(theme.WINDOW))
    row, uid = next(iter(app.painter.report_rects.values()))
    app.click(row.center)
    assert app.ui.selected == s.leader(uid) and app.target is not None
    app.ui.selected = 310
    app.paint(pygame.Surface(theme.WINDOW))
    app.click(app.painter.member_rects[312].center)
    app.paint(pygame.Surface(theme.WINDOW))
    assert app.ui.alone and app.painter.back_rect.y < layout.areas(app.size)["console"].top
    app.click(app.painter.back_rect.center)
    assert app.ui.selected == 310 and not app.ui.alone


def test_a_counter_shows_trouble_with_a_badge_and_which_kind():      # 1e
    from screen.draw import problem
    ok = {"type": "armour", "size": 1, "fuel": 100, "traced": True, "out_of_stores": False, "cohesion": 90}
    assert problem([ok]) is None
    assert problem([ok, dict(ok, fuel=3)]) == "fuel"
    assert problem([dict(ok, traced=False)]) == "trouble" and problem([dict(ok, cohesion=30)]) == "trouble"
    assert problem([dict(ok, type="hq", cohesion=10)]) is None       # an HQ's morale is no trouble


# ---- the owner's third list --------------------------------------------------------------

def test_men_on_foot_march_the_road_and_the_button_says_march():
    from helpers import scenario, unit
    tobruk, gambut = list(GMAP.places["Tobruk"]["hex"]), list(GMAP.places["Gambut"]["hex"])
    s = Session(scenario([unit(101, "axis", "foot", tobruk), unit(102, "axis", "motorised", tobruk), unit(201, "cw", "foot", "Alexandria")]),
                GMAP, humans=["axis"])
    assert theme.order_name("road_march", [s.unit(101)]) == "March" and theme.order_name("road_march", [s.unit(102)]) == "Travel"
    assert s.can(101, "road_march") == (True, "")
    p, q = s.preview(101, "road_march", tuple(gambut)), s.preview(102, "road_march", tuple(gambut))
    assert p["reach"] == 5 and p["fuel"] == 0 and q["reach"] == len(q["path"]) == 6      # five hexes on foot; lorries all the way
    pygame.init()
    app = App(s)
    app.ui.selected = 101
    keys(app, "t")
    assert app.ui.mode == "road_march"
    app.click(app.spot(tuple(gambut)))
    assert "March" in app.ui.message and s.pending["axis"][101]["order"] == "road_march"


def test_the_supply_layer_puts_port_figures_in_a_callout_and_haul_figures_on_request():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    app.ui.overlays = {"s"}
    app.ui.selected = None
    app.centre_on(GMAP.places["Bardia"]["hex"])
    plain, shown = pygame.Surface(theme.WINDOW), pygame.Surface(theme.WINDOW)
    app.paint(plain)
    app.ui.selected = 120                                          # 21. Panzer-Division: what its HQ was hauled
    app.paint(shown)
    area = layout.areas(theme.WINDOW)["map"]
    assert pygame.image.tostring(plain.subsurface(area), "RGB") != pygame.image.tostring(shown.subsurface(area), "RGB")


def test_a_unit_in_trouble_is_marked_in_the_list_over_a_crowded_hex():
    from screen.draw import problem
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    next(u for u in s.view["units"] if u["id"] == 307)["fuel"] = 0   # the tank brigade in Tobruk has run dry
    assert problem(s.members(307)) == "fuel" and problem(s.members(350)) is None
    app.ui.selected = None
    app.centre_on((55, 10))
    app.click(app.spot((55, 10)))
    marked, clean = pygame.Surface(theme.WINDOW), pygame.Surface(theme.WINDOW)
    app.paint(marked)
    next(u for u in s.view["units"] if u["id"] == 307)["fuel"] = 120
    app.paint(clean)
    row = app.painter.chooser_rects[307]
    assert pygame.image.tostring(marked.subsurface(row), "RGB") != pygame.image.tostring(clean.subsurface(row), "RGB")


def test_the_map_has_a_border_at_its_edge_and_a_key_among_its_layers():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    app.ui.cam = [-1000.0, -1000.0]
    app.clamp()
    assert app.ui.cam == [-theme.MARGIN, -theme.MARGIN]              # the north-west corner, with its margin of paper
    surface = pygame.Surface(theme.WINDOW)
    app.paint(surface)
    assert tuple(surface.get_at((6, 6)))[:3] == theme.COMMAND["cw"]  # field-atlas masthead
    assert tuple(surface.get_at((6, 60)))[:3] == theme.PAPER          # paper outside the border
    line = int(theme.MARGIN - 9) + 1
    assert tuple(surface.get_at((line, 60)))[:3] == theme.INK         # the neat line
    assert [name for name, _, _ in theme.LAYERS] == ["s", "z", "k"] and "k" in layout.layers(app.size, True)
    before = pygame.image.tostring(surface, "RGB")
    keys(app, "k")
    app.paint(surface)
    assert app.ui.overlays == {"k"} and pygame.image.tostring(surface, "RGB") != before


# ---- the owner's fourth list -------------------------------------------------------------

def test_a_right_click_on_a_stack_offers_to_group_it_or_split_it():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    app.ui.selected = None
    app.centre_on((55, 10))
    app.click(app.spot((55, 10)), 3)                                 # Tobruk: 70th Division and the tank brigade
    assert app.ui.chooser == {"hex": (55, 10), "ids": [307, 350], "mover": None}
    app.paint(pygame.Surface(theme.WINDOW))
    assert {("group",), ("split", 350), 307, 350} == set(app.painter.chooser_rects)
    app.click(app.painter.chooser_rects[("group",)].center)
    assert s.pending["cw"][350] == {"unit": 350, "order": "join", "with": 307} and "one group" in app.ui.message
    assert s.unit(350)["group"] == 307 and len(s.members(307)) == 6  # at once, not when the turn is played
    assert s.group_name(307) == "Special Army Group I" and s.group_name(310) == "7th Armoured Division"
    assert s.waiting_units().count(307) == 1 and 350 not in s.waiting_units()      # and it is ordered as one
    assert s.give({"unit": 352, "order": "dig_in"})["ok"] and s.pending["cw"][307]["order"] == "dig_in"
    s.done()
    assert s.unit(350)["group"] == 307 and len(s.members(307)) == 6
    app.click(app.spot((55, 10)), 3)                                 # one group there now: the menu offers to split it
    app.paint(pygame.Surface(theme.WINDOW))
    app.click(app.painter.chooser_rects[("split", 307)].center)
    assert "break up" in app.ui.message
    assert all(u["group"] is None for u in s.members(307)) and len(s.parties_at((55, 10))) == 6    # at once
    s.done()
    assert len(s.parties_at((55, 10))) == 6
    app.ui.selected = 310
    app.click(app.spot((56, 8)), 3)                                  # a right click away from your units still lets go
    assert app.ui.selected is None and app.ui.chooser is None


def test_an_enemy_seen_to_move_is_shown_going_round_a_cliff_not_through_it():
    from screen.replay import seen_way
    from mapgen.hexgrid import neighbour
    from screen.replay import least_path
    c, r, d = next(side for side in sorted(GMAP.cliffs) if GMAP.passable((side[0], side[1]))
                   and GMAP.passable(neighbour(*side)) and least_path(GMAP, (side[0], side[1]), neighbour(*side), "vehicle"))
    a, b = (c, r), neighbour(c, r, d)                                # two hexes with a cliff between them
    way = seen_way(GMAP, "armour", a, b)
    hexes = [h for _, h in way]
    assert hexes[0] == a and hexes[-1] == b and len(hexes) > 2
    assert not any(GMAP.cliff_between(x, y) for x, y in zip(hexes, hexes[1:]))
    assert [i for i, _ in way] == sorted(i for i, _ in way) and way[-1][0] == 24
    assert seen_way(None, "armour", a, b) == [(0, a), (24, b)]       # with no map to go by, a straight line


# ---- the owner's fifth list --------------------------------------------------------------

def test_a_game_with_grouping_done_at_the_screen_replays_the_same_from_its_orders():      # RULES 2.3, 20.2
    from engine import runner
    from engine import state as S
    s = Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)})
    s.group_all((55, 10))                                           # 70th Division and the tank brigade, one force
    s.give({"unit": 307, "order": "move", "to": [56, 11]})
    s.give({"unit": 312, "order": "move", "to": [62, 20], "alone": True})     # a brigade split from its division
    s.done()
    s.give({"unit": 312, "order": "move", "to": [61, 19]})          # it is still its own, and the record must say so
    s.split_up(330)                                                 # the New Zealanders break up
    s.give({"unit": 331, "order": "move", "to": [67, 18]})
    s.done()
    s.done()
    again, _ = runner.play(regiments(), GMAP, {side: players.Recorded([t[side] for t in s.record]) for side in S.SIDES},
                           turns=len(s.record))
    again = __import__("engine.turn", fromlist=["begin_turn"]).begin_turn(again, GMAP, regiments())
    assert S.dumps(again) == S.dumps(s.state)


def test_a_group_can_be_given_a_name_of_the_players_own():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    s.group_all((55, 10))
    app.ui.selected = 307
    app.paint(pygame.Surface(theme.WINDOW))
    assert s.group_name(307) == "Special Army Group I" and app.painter.pencil_rect is not None
    app.click(app.painter.pencil_rect.center)
    assert app.ui.editing == "Special Army Group I"
    for _ in range(25):
        app.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode=""))
    for ch in "Tobforce":
        app.handle(pygame.event.Event(pygame.KEYDOWN, key=ord(ch.lower()), unicode=ch))
    assert app.ui.editing == "Tobforce" and s.pending["cw"].get(307, {}).get("order") != "road_march"   # T typed, not Travel
    app.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\\r"))
    assert app.ui.editing is None and s.group_name(307) == "Tobforce" and s.group_name(352) == "Tobforce"
    s.rename(307, "")
    assert s.group_name(307) == "Special Army Group I"


def test_a_click_on_your_own_unit_always_takes_it_up_whatever_is_in_hand():
    """After every order the screen takes up the next unit, so a unit is nearly always in hand.
    A click on another of your units, ordered already or not, takes that one up at once."""
    pygame.init()
    surface = pygame.Surface(theme.WINDOW)
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    assert s.give({"unit": 310, "order": "hold"})["ok"]             # 7th Armoured Division has its order
    app.ui.selected = 304                                           # 22nd Guards Brigade is in hand
    app.centre_on((64, 23))
    app.click(app.spot((64, 22)))                                   # a click on 7th Armoured
    assert app.ui.selected == 310 and app.ui.chooser is None and 304 not in s.pending["cw"]
    assert "has its order, Hold" in app.ui.message
    app.ui.selected, app.ui.mode = 304, "attack"                    # an order pressed that cannot go there
    app.click(app.spot((64, 22)))
    assert app.ui.selected == 310 and app.ui.mode is None           # still takes the unit up
    app.ui.selected, app.ui.mode = 304, "move"                      # Move pressed first: the unit in hand goes there
    app.click(app.spot((64, 22)))
    assert s.pending["cw"][304] == {"unit": 304, "order": "move", "to": [64, 22]}
    app.ui.selected = 304
    app.click(app.spot((64, 22)), 3)                                # the stack's menu offers the move too
    app.paint(surface)
    assert ("move",) in app.painter.chooser_rects


def test_next_unit_is_greyed_when_every_unit_has_its_order_and_a_units_own_order_is_always_lit():
    from helpers import scenario, unit
    pygame.init()
    s = Session(scenario([unit(101, "axis", "armour", [70, 24]), unit(201, "cw", "foot", "Alexandria")]), GMAP, humans=["axis"])
    app = App(s)
    app.paint(pygame.Surface(theme.WINDOW))
    nxt = layout.buttons(app.size)["next"]
    assert not any(r == nxt for r, _ in app.painter.tips)           # a unit waits: Next unit is live
    s.give({"unit": 101, "order": "attack", "to": [80, 24]})        # an attack far away: no enemy near, yet it is its order
    app.ui.selected = 101
    app.paint(pygame.Surface(theme.WINDOW))
    assert (nxt, "Every unit has been gone through.") in app.painter.tips
    assert (layout.buttons(app.size)["attack"], "This is its order. Click to take it back.") in app.painter.tips
    app.click(layout.buttons(app.size)["attack"].center)            # its lit button pressed again: the attack is taken back
    assert app.ui.mode is None and 101 not in s.pending["axis"] and 101 not in s.standing["axis"]
    assert app.ui.message.startswith("Attack cancelled. It holds") and 101 in s.waiting_units()
    app.paint(pygame.Surface(theme.WINDOW))
    assert (layout.buttons(app.size)["hold"], "With no other order it holds.") in app.painter.tips     # Hold is lit again
    app.click(layout.buttons(app.size)["move"].center)              # Move pressed with no order: a place to go is asked for
    assert app.ui.mode == "move" and 101 not in s.pending["axis"]
    app.click(layout.buttons(app.size)["move"].center)              # and unpressed before a hex is chosen: nothing is ordered
    assert app.ui.mode is None and 101 not in s.pending["axis"] and "no order was given" in app.ui.message
    for name, order in (("move", {"to": [72, 24]}), ("road_march", {"to": [72, 24]}), ("rest", {})):   # every order's button is the same
        if not s.give({"unit": 101, "order": name, **order})["ok"]:
            continue
        app.ui.selected = 101
        app.click(layout.buttons(app.size)[name].center)
        assert 101 not in s.pending["axis"] and "cancelled" in app.ui.message, name


def test_fuel_is_told_in_kilometres_with_the_hexes_beside():
    assert theme.fuel_words(30) == "300 km (30 hexes)" and theme.fuel_words(1) == "10 km (1 hex)"


def test_a_surrender_is_reported_and_shown_as_a_white_flag():        # RULES 6.10.2, 14.6
    from helpers import scenario, unit
    from screen.replay import HOLD_MS
    units = [unit(101, "axis", "foot", [70, 25], stores=0, cohesion=10, name="Lost Battalion"), unit(102, "axis", "foot", [60, 30]),
             unit(201, "cw", "armour", [70, 24])]
    sc = scenario(units)
    sc["sides"]["axis"]["lift"] = [["1941-11-18", 0]]
    s = Session(sc, GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)})
    s.done()                                                         # it starves to nothing, then gives up
    assert "The enemy's Lost Battalion surrendered near" in " ".join(w for w, _ in s.reports())
    play = s.playback()
    start, end, outcome = scenes(play, "outcome")[0]
    assert outcome["flags"] == [101] and outcome["burst"] == []
    mid = play.stage(start + HOLD_MS + 60)
    assert [kind for _, _, kind in mid["bursts"]] == ["flag"]
    pygame.init()
    app = App(s)
    app.play, app.play_t = play, start + HOLD_MS + 60
    app.centre_on((70, 25))
    app.paint(pygame.Surface(theme.WINDOW))                          # the flag is drawn without error
    assert at(play.stage(play.length), 101) is None


# ---- the third review --------------------------------------------------------------------

def test_the_playback_is_watched_close_in_and_the_zoom_returns_after():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)}))
    app.zoom(0.01)
    far = app.ui.zoom
    assert far < 0.5
    app.done()
    assert app.play is not None and app.ui.zoom == 1.0              # counters are legible while it plays
    keys(app, "ESCAPE")
    assert app.play is None and app.ui.zoom == far                   # and the player's zoom comes back


def test_the_instruction_line_follows_the_state_and_the_tooltip_keeps_quiet_on_empty_desert():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    surface = pygame.Surface(theme.WINDOW)
    app.ui.hover = (60, 30)
    app.paint(surface)
    assert app.ui.preview == ""                                      # a unit is taken up, and holds: nothing claimed
    app.ui.mode = "move"
    app.paint(surface)
    assert app.ui.preview.startswith("Move here")                    # Move pressed: what a click would do
    app.ui.selected, app.ui.mode = None, None
    app.paint(surface)
    assert app.ui.preview == ""                                      # nothing taken up: nothing claimed
    said = []
    app.painter.tooltip = lambda *args: said.append(app.ui.hover)
    for hx in ((60, 30), tuple(GMAP.places["Tobruk"]["hex"]), (64, 22)):          # empty desert; a place; your own units
        app.ui.hover = hx
        app.centre_on(hx)
        app.paint(surface)
    assert said == [tuple(GMAP.places["Tobruk"]["hex"]), (64, 22)]               # no "open desert" box following the pointer


# ---- the four panel items ----------------------------------------------------------------

def test_the_orders_stay_in_the_console_and_only_those_it_can_take_are_actionable():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    where = layout.buttons(app.size)
    assert all(layout.areas(app.size)["console"].contains(rect) for rect in where.values())
    assert where["next"].y > 700
    assert s.offers(310) == ["move", "attack", "road_march", "hold", "dig_in", "rest", "join", "split"]     # no strays to recall
    assert s.offers(301) == ["move", "road_march", "hold", "rest", "join"]                    # an army HQ alone, at Fort Maddalena
    assert s.offers(None) == [] and s.offers(999) == []
    s.give({"unit": 310, "order": "attack", "to": [56, 13]})
    assert "attack" in s.offers(310)
    quiet = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    quiet.ui.selected = None
    quiet.click(where["dig_in"].center)                             # nothing taken up: no order to press
    assert quiet.session.pending["cw"] == {} and quiet.ui.selected is None


def test_with_nothing_taken_up_the_panel_lists_who_waits_and_a_tap_goes_there():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    app.ui.selected = None
    app.paint(pygame.Surface(theme.WINDOW))
    rows = {key[1]: row for key, (row, uid) in app.painter.report_rects.items() if key[0] == "wait"}
    assert list(rows)[:4] == app.session.waiting_units()[:4] and len(rows) >= 8
    app.click(rows[330].center)                                     # 2nd New Zealand Division
    assert app.ui.selected == 330 and app.target is not None
    settle(app)
    x, y = app.spot(tuple(app.session.unit(330)["hex"]))
    assert abs(x - app.map_rect().centerx) <= 2 and abs(y - app.map_rect().centery) <= 2


def test_the_layers_list_explains_what_is_on():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    plain, told = pygame.Surface(theme.WINDOW), pygame.Surface(theme.WINDOW)
    app.ui.layers_open = True
    app.paint(plain)
    app.ui.overlays = {"z"}
    app.paint(told)
    anchor = layout.layers(app.size, True)["layers"]
    box = pygame.Rect(anchor.x + 170, anchor.bottom - 80, 372, 78)
    assert pygame.image.tostring(plain.subsurface(box), "RGB") != pygame.image.tostring(told.subsurface(box), "RGB")


def test_a_unit_ordered_off_that_never_left_says_so():
    from helpers import scenario, unit
    s = Session(scenario([unit(101, "axis", "foot", [70, 25]), unit(102, "axis", "foot", [71, 24]),
                          unit(201, "cw", "armour", [70, 24], name="Stuck Brigade"), unit(202, "cw", "foot", [60, 30], name="Free Brigade")]),
                GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)})
    s.give({"unit": 201, "order": "move", "to": [71, 25]})          # from one enemy zone straight into another: not allowed
    s.give({"unit": 202, "order": "move", "to": [60, 28]})
    s.done()
    assert s.unit(201)["hex"] == [70, 24] and s.unit(202)["hex"] == [60, 28]
    for u in s.view["units"]:                                       # in this bare scenario nobody is supplied: set that aside
        u["traced"], u["out_of_stores"] = True, False
    told = dict((uid, words) for words, uid in s.reports())
    assert told[201] == "Stuck Brigade could not move: the enemy is in its way." and 202 not in told


def test_a_group_strikes_once_not_once_for_each_of_its_units():
    from helpers import unit
    from screen.replay import harm
    units = [unit(110, "axis", "hq", [70, 24], steps=1), unit(111, "axis", "armour", [70, 24], parent=110, steps=12),
             unit(112, "axis", "motorised", [70, 24], parent=110), unit(113, "axis", "guns", [70, 24], parent=110, steps=4),
             unit(120, "axis", "foot", [69, 25]), unit(201, "cw", "foot", [70, 25], steps=9)]
    play, s = played(units, axis=[{"unit": 110, "order": "attack", "to": [70, 25]}, {"unit": 120, "order": "attack", "to": [70, 25]}],
                     side="axis")
    battle = next(e for e in s.views["axis"]["events"] if e["event"] == "battle")
    strikes = [x[2] for x in scenes(play, "strike") if not x[2]["reply"]]
    assert [st["by"] for st in strikes] == [[111, 112, 113], [120]]              # the division as one, then the lone battalion
    assert strikes[0]["arm"] == "armour" and strikes[1]["arm"] == "foot"         # heard as its chief arm
    assert strikes[0]["damage"] + strikes[1]["damage"] <= harm(battle, "cld") and strikes[0]["damage"] > strikes[1]["damage"]
    mid = play.stage(scenes(play, "strike")[0][0] + 100)
    assert [at(mid, i)[6] for i in (111, 112, 113)] == ["firing"] * 3 and at(mid, 120)[6] is None


def test_the_play_log_records_what_each_click_did(tmp_path):
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    app.log = open(tmp_path / "play.log", "w", encoding="utf-8")
    app.ui.selected = 304
    app.centre_on((64, 23))
    spot = app.spot((64, 22))
    app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=spot))
    app.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=spot))
    app.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, unicode=""))
    app.ui.selected = 310
    app.give("move", (60, 0))                                       # the sea: refused, and the reply's code goes in the line
    app.note("an order", (310, None, False, False))
    app.log.close()
    lines = (tmp_path / "play.log").read_text().splitlines()
    assert len(lines) == 3                                          # one line for the click, not one down and one up
    assert "| click at" in lines[0] and "had 304 22nd Guards Brigade" in lines[0] and "has 310 7th Armoured Division" in lines[0]
    assert lines[0][2] == ":" and "key escape" in lines[1] and "refused E_" in lines[2]


def test_the_unit_orders_tab_lists_every_unit_and_its_order_and_a_tap_takes_one_up():
    pygame.init()
    surface = pygame.Surface(theme.WINDOW)
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    assert s.give({"unit": 310, "order": "dig_in"})["ok"]
    seen = []
    text = app.painter.text
    app.painter.text = lambda surface, words, *a, **k: (seen.append(words), text(surface, words, *a, **k))
    app.click(layout.tabs(app.size)["orders"].center)
    app.paint(surface)
    assert app.ui.tab == "orders" and "Dig in" in seen and "Hold" in seen
    leads = sorted({s.leader(u["id"]) for u in s.view["units"] if u["status"] == "on_map"})
    rows = {uid for _, uid in app.painter.report_rects.values()}
    assert rows == set(leads)                                        # all of them fit at this size
    app.click(layout.buttons(app.size)["hold"].center)               # no order buttons on this tab: a row of the list is there
    assert not s.pending["cw"].keys() - {310}                        # so the click gives no order
    app.click(layout.tabs(app.size)["orders"].center)
    app.paint(surface)
    row = next(r for r, uid in app.painter.report_rects.values() if uid == 310)
    app.click(row.center)
    assert app.ui.selected == 310 and app.ui.tab == "unit" and "has its order, Dig in" in app.ui.message
    app.size = (1400, 560)                                           # a short window: the list scrolls
    app.ui.tab = "orders"
    app.paint(pygame.Surface(app.size))
    shown = len(app.painter.report_rects)
    assert shown < len(leads) and set(app.painter.scroll_rects) == {"up", "down"}
    assert not app.painter.panel_scroll_rects  # one scroll mechanism per tab
    for _ in leads:
        if leads[-1] in {uid for _, uid in app.painter.report_rects.values()}:
            break
        app.click(app.painter.scroll_rects["down"].center)
        app.paint(pygame.Surface(app.size))
    assert leads[-1] in {uid for _, uid in app.painter.report_rects.values()}


def test_next_unit_is_lit_and_end_turn_names_its_confirmation_when_reminders_are_on():
    pygame.init()
    surface = pygame.Surface(theme.WINDOW)
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    grid = layout.buttons(app.size)
    inside = lambda name: tuple(surface.get_at((grid[name].x + 6, grid[name].centery)))[:3]
    app.paint(surface)
    assert inside("next") == theme.BUTTON_ON and inside("done") == theme.BUTTON_GO     # units wait: Next lit, End turn green
    for lead in s.waiting_units():
        s.give({"unit": lead, "order": "hold"})
    app.paint(surface)
    assert inside("next") not in (theme.BUTTON_ON, theme.BUTTON) and inside("done") == theme.BUTTON_GO
    s.cancel(310)
    app.click(layout.tabs(app.size)["remind"].center)                # the reminder off
    assert app.ui.remind is False and "will not ask" in app.ui.message
    app.key(pygame.K_RETURN)
    assert s.state["turn"] == 2                                      # ended at once, with a unit unordered
    app.stop_watching()
    app.click(layout.tabs(app.size)["remind"].center)                # and on again
    app.click(grid["done"].center)
    assert s.state["turn"] == 2 and "not been gone through" in app.ui.message
    assert "Click Confirm turn" in app.ui.message and app.ui.end_confirmation
    app.paint(surface)
    assert inside("done") == theme.BUTTON_ON
    app.click(grid["done"].center)
    assert s.state["turn"] == 3 and not app.ui.end_confirmation


def test_a_move_the_stacking_limit_keeps_out_is_warned_of_and_then_reported():
    """A third formation ordered on to a stack of two: the order is accepted, the unit never
    moves, and it must say why. An HQ is let in: it does not count (RULES 20.1.4)."""
    from helpers import scenario, unit
    pygame.init()
    units = [unit(201, "cw", "motorised", [70, 24]), unit(202, "cw", "motorised", [70, 24]),
             unit(204, "cw", "motorised", [71, 23]), unit(205, "cw", "hq", [71, 23], steps=1),
             unit(101, "axis", "foot", "Tripoli" if "Tripoli" in GMAP.places else "Benghazi")]
    app = App(Session(scenario(units), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    assert s.crowded(204, (70, 24)) and not s.crowded(204, (70, 23))
    assert not s.crowded(205, (70, 24))                              # the owner's case: a lone HQ may join any stack
    app.ui.selected = 204
    app.give("move", (70, 24))
    assert s.pending["cw"][204]["to"] == [70, 24] and "holds 2 formations already" in app.ui.message
    for lead in s.waiting_units():
        s.give({"unit": lead, "order": "hold"})
    s.done()
    assert s.unit(204)["hex"] == [71, 23]                            # it did not get in
    assert "already holds 2 formations" in s.said["cw"][204]         # said on the unit when it is taken up
    assert any("could not go on" in w and uid == 204 for w, uid in s.reports())
    app.click((300, 5000))                                           # a click nowhere changes nothing, quietly; one off the map says so
    app.ui.cam, app.ui.message = [-40, -40], ""
    app.click((2, theme.MASTHEAD + 6))  # below the masthead: still outside the map's neat line
    assert app.ui.message == "That is off the map."


def test_the_tooltip_over_your_own_units_is_a_small_card_for_each_unit_or_group():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    assert s.give({"unit": 310, "order": "move", "to": [60, 14]})["ok"]
    card = [words for words, _, _ in app.painter.card(s, 310)]
    assert card[0] == "7th Armoured Division  (5 units)" and "tanks" in card[1] and "Morale" in card[1]
    assert card[2].startswith("Fuel ") and card[2].endswith("In supply") and card[3].startswith("Order: Move ")
    assert len(card) == 4                                            # nothing wrong: no fifth line
    for m in s.view["units"]:
        if m["id"] == 307 or m.get("group") == 307:
            m["cohesion"], m["traced"] = 10, False
    card = app.painter.card(s, 307)
    assert ("Order: Hold", False, theme.INK) in card and any("OUT OF SUPPLY" in w for w, _, _ in card)
    assert card[-1][0] == "! morale too low to attack" and card[-1][2] == theme.SHORT
    seen = []
    text = app.painter.text
    app.painter.text = lambda surface, words, *a, **k: (seen.append(words), text(surface, words, *a, **k))
    h = tuple(s.unit(307)["hex"])                                    # Tobruk: two parties, a card each
    app.centre_on(h)
    app.ui.hover, app.ui.mouse = h, tuple(int(v) for v in app.spot(h))
    app.paint(pygame.Surface(theme.WINDOW))
    assert "32nd Army Tank Brigade" in seen and "70th Division  (5 units)" in seen


def test_the_weather_is_shown_and_felt_and_a_tap_says_what_it_does():            # RULES 21.4, 21.5
    from helpers import scenario, unit
    pygame.init()
    surface = pygame.Surface(theme.WINDOW)
    units = [unit(201, "cw", "armour", [70, 21]), unit(101, "axis", "foot", [70, 24]), unit(102, "axis", "foot", [70, 22])]

    def game(kind, seed=5):
        sc = scenario(units, weather=[["1941-11-18", {kind: 100} if kind else {}]])
        return App(Session(sc, GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}, seed=seed))

    clear, storm, rain, none = game(None), game("sandstorm"), game("rain"), game("sandstorm", seed=0)
    assert [a.session.weather for a in (clear, storm, rain, none)] == ["clear", "sandstorm", "rain", None]
    reach = lambda a: a.session.preview(201, "move", (78, 21))["reach"]
    assert [reach(a) for a in (clear, storm, rain, none)] == [8, 4, 4, 8]         # half the allowance; double the cost; no weather
    assert storm.session.reports()[0] == ("Sandstorm: no aircraft fly, nothing is seen beyond the next hex, "
                                          "and all movement is halved.", None)
    assert [e["id"] for e in storm.session.view["enemy"]] == [102] and len(clear.session.view["enemy"]) == 1   # 101 is three off
    assert "A sandstorm today." in storm.ui.message and "today" not in clear.ui.message
    for app in (clear, storm, rain, none):
        app.stop_watching()
        app.centre_on((70, 22))
        app.paint(surface)
    assert none.painter.weather_rect is None and clear.painter.weather_rect is not None      # no seed: no weather shown at all
    pale = lambda a: tuple(surface.get_at((30, 300)))[:3] if a.paint(surface) is None else None
    assert pale(storm) != pale(clear) != pale(rain)                               # the wash over the map
    chip = rain.painter.weather_rect.move(rain.map_rect().topleft)
    assert not chip.colliderect(layout.details_toggle(rain.size))
    rain.click(chip.center)
    assert rain.ui.message.startswith("Rain: no aircraft fly") and "Outlook for the next two days" in rain.ui.message
    assert rain.ui.selected == 201                                                # the tap ordered nothing


def test_the_timetable_tab_lists_what_history_sends_and_takes_and_a_tap_goes_to_the_unit():   # RULES 12.8
    pygame.init()
    surface = pygame.Surface(theme.WINDOW)
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s = app.session
    seen = []
    text = app.painter.text
    app.painter.text = lambda surface, words, *a, **k: (seen.append(words), text(surface, words, *a, **k))
    app.click(layout.tabs(app.size)["timetable"].center)             # by a tap on its tab, like everything else
    app.paint(surface)
    assert app.ui.tab == "timetable"
    assert [(f"{r['day']:%d %b}", r["when"], r["words"]) for r in s.timetable()] == [
        ("27 Nov", "in 4 turns", "7th Armoured Brigade is withdrawn."),
        ("27 Nov", "in 4 turns", "4th Armoured Brigade receives 33 tanks."),
        ("01 Dec", "in 6 turns", "4 units of 2nd New Zealand Division are withdrawn."),
        ("02 Dec", "in 7 turns", "5 units of 2nd South African Division arrive at Buq Buq."),
        ("06 Dec", "in 9 turns", "4th Armoured Brigade receives 38 tanks."),
        ("22 Dec", "in 17 turns", "22nd Armoured Brigade receives 60 tanks.")]     # its own side's, and nothing of the enemy's
    for words in ("27 November", "in 4 turns", "7th Armoured Brigade is withdrawn.", "Tanks from the reserve and the workshops."):
        assert words in seen, words
    heads = [seen.index(w) for w in ("Withdrawals", "7th Armoured Brigade is withdrawn.",
                                     "4 units of 2nd New Zealand Division are withdrawn.", "Reinforcements",
                                     "4th Armoured Brigade receives 33 tanks.")]
    assert heads == sorted(heads)                                    # each kind under its heading, soonest first
    seen.clear()
    app.ui.scroll = 6                                                  # the High Command aim takes room; later events scroll
    app.paint(surface)
    assert "22nd Armoured Brigade receives 60 tanks." in seen and "Other" in seen and "none" in seen
    assert [r["kind"] for r in s.timetable()] == ["withdrawal", "replacement", "withdrawal", "arrival", "replacement", "replacement"]
    assert s.due_now() == 0 and not [tip for _, tip in app.painter.tips if "at the end of this turn" in tip]   # no bubble on the tab yet
    assert not [b for b in ("move", "attack", "hold") if b in seen]  # no order buttons on this tab
    app.ui.scroll = 0
    app.paint(surface)
    box = next(row for key, (row, uid) in app.painter.report_rects.items() if key[0] == "due" and uid == 312)
    app.click(box.center)                                            # a tap on an event goes to its unit
    assert app.ui.tab == "unit" and app.ui.selected == s.leader(312)
    axis = Session(regiments(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)})
    assert [r["words"] for r in axis.timetable()] == ["Panzer-Regiment 8 receives 22 tanks through Benghazi.",
                                                      "Panzer-Regiment 8 receives 23 tanks."]


def test_the_reports_say_what_the_timetable_will_do_this_turn_and_what_it_did():   # RULES 12.8
    s = Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)})
    while s.state["turn"] < 5:
        s.done()
    told = [words for words, _ in s.reports()]
    assert s.due_now() == 2                                         # the tab's bubble: two events fall as this turn ends
    pygame.init()
    app = App(s)
    app.paint(pygame.Surface(theme.WINDOW))
    spot = next(r for r, tip in app.painter.tips if tip == "2 timetable events at the end of this turn: plan for them now.")
    assert spot.colliderect(layout.tabs(app.size)["timetable"])
    assert "At the end of this turn: 7th Armoured Brigade is withdrawn." in told
    assert "At the end of this turn: 4th Armoured Brigade receives 33 tanks." in told
    S.unit(s.state, 311)["steps"] = 5                               # the brigade has been in a fight
    s.done()
    told = dict(s.reports())
    assert "7th Armoured Brigade has been withdrawn." in told and s.unit(312) is None
    assert told["4th Armoured Brigade received replacements: it now has about 78 tanks."] == 311
    first = s.timetable()[0]
    assert (first["past"], first["when"], first["words"]) == (True, "turn 5", "7th Armoured Brigade was withdrawn.")
    while s.state["turn"] < 9:
        s.done()
    assert dict(s.reports())["5 units of 2nd South African Division have arrived at Buq Buq."] == 360
    assert s.leader(364) == 360 and len(s.members(360)) == 5         # the division came up as one group
    assert s.leader(335) == 332 and s.unit(330) is None              # the New Zealanders left behind carry on together
    s = Session(regiments(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)})
    while s.state["turn"] < 16:
        s.done()
    s.state["places"]["Benghazi"] = "cw"                             # the port the tanks were to land at has fallen
    s.done()
    assert dict(s.reports())["Replacements for Panzer-Regiment 8 were lost: Benghazi is in enemy hands."] == 111



# ---- the tile layout: a name, a division's notch, and the unit taken up as a tile (docs/COUNTERS.md) ----

def test_a_units_name_is_cut_down_for_its_counter_and_fits_it_whole():
    pygame.init()
    assert theme.short("4th Armoured Brigade") == "4 Armd Bde" and theme.short("1st South African Division artillery") == "1 SA Div Arty"
    assert theme.short("Panzer-Regiment 8") == "Pz.Rgt. 8" and theme.short("132 Reggimento carri") == "132 Carri"
    assert theme.short("Eighth Army") == "Eighth Army"              # nothing to cut: it stays
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    closest = Layout(theme.BASE_HEX * theme.ZOOM_MAX).counter
    assert closest >= theme.NAMED > Layout(theme.BASE_HEX * theme.ZOOM_MAX / theme.ZOOM_STEP).counter   # named at the closest zoom only
    room = closest - 2 * (closest // 16) - 4                        # between the bevelled edges
    for u in regiments()["units"]:
        assert app.painter.font(9, True).size(theme.short(u["name"]))[0] <= room, u["name"]


def test_each_division_of_a_side_has_a_notch_of_its_own():
    s = Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)})
    assert s.division[311] == s.division[310] == (310, 0) and s.division[321] == (320, 1)   # by the HQs' ids, within a side
    assert s.division[111] == (110, 0) and s.division[201] == (200, 9)
    assert 306 not in s.division and 301 not in s.division          # a unit of no division has no notch
    for side in ("axis", "cw"):
        places = {s.division[u["id"]] for u in regiments()["units"] if u["side"] == side and u["id"] in s.division}
        assert len({n for _, n in places}) == len(places) <= len(theme.DIVISION)             # no two share a colour


def test_the_unit_taken_up_is_a_tile_in_the_panel_and_at_the_closest_zoom_its_counter_is_named():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s, seen = app.session, []
    words = app.painter.text
    app.painter.text = lambda surface, said, *a, **k: (seen.append(str(said)), words(surface, said, *a, **k))
    app.ui.selected, app.ui.alone = 311, True                       # 4th Armoured Brigade, by itself
    app.centre_on(tuple(s.unit(311)["hex"]))
    app.paint(pygame.Surface(theme.WINDOW))
    for said in ("4th Armoured Brigade", "7th Armoured Division", "166", "tanks", "8", "open hexes", "300", "km of fuel",
                 "9", "morale", "excellent", "regular", "stores"):
        assert said in seen, said
    assert "4 Armd Bde" not in seen                                  # at the opening zoom a counter has no name
    tips = [tip for _, tip in app.painter.tips]
    assert "about 166 of 166 tanks (100%, 0 lost)" in tips and "Fuel for 300 km (30 hexes)" in tips
    assert "250 tonnes of stores" in tips and "Experience: regular" in tips
    assert "Hexes a turn across open desert in this weather. Travel by road goes farther." in tips
    flown = [box for box, tip in app.painter.tips if tip == "United Kingdom"]                           # its flag, top right
    panel = layout.areas(app.size)["panel"]
    assert len(flown) == 1 and flown[0].size == theme.FLAG and layout.HEAD_Y < flown[0].top < layout.HEAD_Y + 20
    assert panel.right - 60 < flown[0].right < panel.right
    del seen[:]
    app.ui.zoom = theme.ZOOM_MAX
    app.centre_on(tuple(s.unit(311)["hex"]))
    app.paint(pygame.Surface(theme.WINDOW))
    assert "4 Armd Bde" in seen and "XXX Corps" in seen             # the counters' names, cut down
    del seen[:]
    app.ui.selected, app.ui.zoom = 341, theme.ZOOM_START            # 5th Indian Brigade: men on foot
    app.centre_on(tuple(s.unit(341)["hex"]))
    app.paint(pygame.Surface(theme.WINDOW))
    assert "men" in seen and "4" in seen and "km of fuel" not in seen           # four hexes a turn, and no fuel to show


def test_recon_details_use_plain_strength_one_supply_line_and_a_clear_split_action():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    app.ui.selected, app.ui.alone = 335, True
    drawn = []
    original = app.painter.text
    app.painter.text = lambda surface, words, pos, *a, **k: (drawn.append((str(words), pos)), original(surface, words, pos, *a, **k))
    app.paint(pygame.Surface(app.size))
    words = [value for value, _ in drawn]
    assert "Full strength" in words and "2 / 2 steps" not in words
    assert words.count("In supply") == 1
    assert "Mk VI light tank (example)" in words and "open hexes" in words
    assert "48 MP = 12 open hexes" in words
    assert any(value.startswith("18 November 1941") and pos[0] < layout.areas(app.size)["panel"].x
               for value, pos in drawn)
    assert app.session.can(335, "split", True)[0]
    app.ui.selected, app.ui.alone = 330, False
    app.paint(pygame.Surface(app.size))
    assert not app.session.can(330, "split", False)[0]
    assert any(rect == layout.buttons(app.size)["split"] and "Click a unit" in tip
               for rect, tip in app.painter.tips)


def test_scenarios_say_each_side_its_aim_on_the_timetable_tab():           # RULES 13.1, 2.4
    from engine import scenarios
    pygame.init()
    surface = pygame.Surface(theme.WINDOW)
    for side, other, aim in (("cw", "axis", "Open the road into Tobruk"), ("axis", "cw", "Keep Tobruk shut in")):
        app = App(Session(scenarios.load("sidi_rezegh"), GMAP, humans=[side], scripted={other: players.DoNothing(GMAP)}))
        seen = []
        text = app.painter.text
        app.painter.text = lambda surface, words, *a, **k: (seen.append(words), text(surface, words, *a, **k))
        app.click(layout.tabs(app.size)["timetable"].center)
        app.paint(surface)
        said = " ".join(str(words) for words in seen)
        assert "Your aim" in seen and aim in said and "Sidi Rezegh and Belhamed" in said, side
        assert "TURN 1 / 5" in said and "Sidi Rezegh" in seen                    # name in masthead, turn in details
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    seen = []
    text = app.painter.text
    app.painter.text = lambda surface, words, *a, **k: (seen.append(words), text(surface, words, *a, **k))
    app.click(layout.tabs(app.size)["timetable"].center)
    app.paint(surface)
    said = " ".join(str(words) for words in seen)
    assert "Your aim" in seen and "Relieve Tobruk" in said


def test_a_commonwealth_unit_flies_its_own_countrys_flag():
    from screen import draw
    pygame.init()
    s = Session(regiments(), GMAP)
    name = {u["id"]: u["name"] for u in regiments()["units"]}
    flown = {code: sorted(name[uid] for uid, c in s.flag.items() if c == code) for code in theme.FLAG_NAME}
    assert flown["nz"] == ["2nd New Zealand Division", "4th New Zealand Brigade", "5th New Zealand Brigade",
                           "6th New Zealand Brigade", "New Zealand Divisional Artillery", "New Zealand Divisional Cavalry"]
    assert flown["in"] == ["11th Indian Brigade", "4th Indian Division", "4th Indian Division artillery",
                           "5th Indian Brigade", "7th Indian Brigade"]
    assert len(flown["sa"]) == 9 and flown["pl"] == ["Polish Carpathian Brigade"] and flown["au"] == []
    assert {"Eighth Army", "70th Division", "14th Brigade", "4th Armoured Brigade"} <= set(flown["uk"])
    assert "Panzer-Regiment 8" in flown["de"] and "Ariete" in flown["it"] and len(s.flag) == len(name)
    assert theme.flag_of("cw", "Divisional Cavalry", "2nd New Zealand Division") == "nz"      # by its division, its own name silent
    assert theme.flag_of("cw", "2/13th Australian Battalion", "70th Division") == "au"        # its own name before its division's
    assert theme.flag_of("it", "Polish volunteers") == "it"
    drawn = {code: pygame.image.tostring(draw.flag(code, *theme.FLAG), "RGB") for code in theme.FLAG_NAME}
    assert len(set(drawn.values())) == len(drawn) == 8               # each has a drawing, and no two are the same
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    for uid, country in ((331, "New Zealand"), (341, "India"), (321, "Union of South Africa"), (308, "Poland")):
        app.ui.selected, app.ui.alone = uid, True
        app.paint(pygame.Surface(theme.WINDOW))
        assert country in [tip for _, tip in app.painter.tips], uid


def test_the_wheel_and_the_keys_over_the_tile_go_through_the_units_in_its_hex():
    """Over the unit taken up in the panel, the wheel, Up and Down, and anywhere Page Up and Page
    Down, take up the next of yours in its hex: each group, then each of its units by itself.
    The tile's own arrows do the same by a tap."""
    pygame.init()
    surface = pygame.Surface(theme.WINDOW)
    app = App(Session(regiments(), GMAP, humans=["cw"], scripted={"axis": players.DoNothing(GMAP)}))
    s, panel = app.session, layout.areas(app.size)["panel"]
    wheel = lambda y: app.handle_one(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=y))
    assert s.stack(311) == [(310, False), (310, True), (311, True), (312, True), (313, True), (314, True)]   # 7th Armoured Division
    assert s.stack(350)[:3] == [(307, False), (350, False), (350, True)]         # Tobruk: the tank brigade, then 70th Division
    app.ui.selected, app.ui.alone = 311, True
    app.ui.mouse = (panel.centerx, layout.HEAD_Y + 60)                           # the pointer on the tile
    wheel(-1)
    assert (app.ui.selected, app.ui.alone) == (312, True) and app.ui.message.startswith("4 of 6 in this hex: 7th Armoured Brigade by itself")
    wheel(1)
    wheel(1)
    assert (app.ui.selected, app.ui.alone) == (310, True)                        # up: the one before, and before that
    app.key(pygame.K_UP)
    assert (app.ui.selected, app.ui.alone) == (310, False) and app.ui.message == "1 of 6 in this hex: 7th Armoured Division."
    app.key(pygame.K_UP)
    assert (app.ui.selected, app.ui.alone) == (314, True)                        # and round to the last
    app.key(pygame.K_DOWN)
    assert (app.ui.selected, app.ui.alone) == (310, False)
    zoom, cam = app.ui.zoom, list(app.ui.cam)
    app.ui.mouse = layout.areas(app.size)["map"].center                          # off the tile, the wheel and the arrows are the map's
    app.key(pygame.K_DOWN)
    assert (app.ui.selected, app.ui.alone) == (310, False) and app.ui.cam != cam
    app.key(pygame.K_PAGEDOWN)                                                   # Page Down goes through them wherever the pointer is
    assert (app.ui.selected, app.ui.alone) == (310, True)
    app.key(pygame.K_PAGEUP)
    app.ui.selected, app.ui.alone = 313, True
    app.paint(surface)
    assert set(app.painter.cycle_rects) == {-1, 1}                               # which this is, with an arrow each way
    back, before = app.painter.back_rect, app.painter.cycle_rects[-1]
    assert before.left > back.right and before.centery == back.centery           # beside Back to group, and off the tile
    assert before.top > layout.HEAD_Y + theme.TILE_H
    app.click(app.painter.cycle_rects[1].center)
    assert (app.ui.selected, app.ui.alone) == (314, True)
    app.paint(surface)
    app.click(app.painter.cycle_rects[-1].center)
    assert (app.ui.selected, app.ui.alone) == (313, True)
    app.ui.selected, app.ui.alone = 304, False                                   # 22nd Guards Brigade: alone in its hex
    app.paint(surface)
    assert s.stack(304) == [(304, False)] and app.painter.cycle_rects == {}
    app.key(pygame.K_PAGEDOWN)
    assert app.ui.selected == 304 and app.ui.message == "Nothing else of yours is in this hex."


def test_after_a_battle_the_side_claims_the_enemys_losses_and_names_the_hq_behind_it():
    from helpers import unit
    units = [unit(101, "axis", "armour", [70, 25], steps=6, tanks=60), unit(201, "cw", "armour", [70, 24], steps=15),
             unit(301, "cw", "hq", [72, 24], steps=1, name="XXX Corps")]
    _, s = played(units, cw=[{"unit": 201, "order": "attack", "to": [70, 25]}])
    battle = next(e for e in s.views["cw"]["events"] if e["event"] == "battle")
    claimed = battle["lost"]["101"] * 10
    lines = [w for w, _ in s.claims("cw")]
    assert lines == [f"We claim about {claimed} tanks of the enemy's knocked out.", "XXX Corps stood behind our attack."]
    assert all("XXX Corps" not in w for w, _ in s.claims("axis"))                     # the enemy's HQ is not named to the Axis


def test_a_group_is_shown_as_its_order_of_battle_its_hq_on_top_and_a_tile_for_each_unit():
    pygame.init()
    app = App(Session(regiments(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    app.ui.selected, app.ui.alone = 110, False
    app.paint(pygame.Surface(theme.WINDOW))
    rects = app.painter.member_rects
    hq, rows = rects[110], [rects[i] for i in (111, 112, 113, 114)]
    assert all(hq.bottom < row.top for row in rows)                              # the HQ's card above its units
    assert len({row.size for row in rows}) == 1 and not any(a.colliderect(b) for a in rows for b in rows if a is not b)
    assert all(row.bottom < layout.areas(app.size)["console"].top for row in rows)
    assert app.painter.pencil_rect and not hq.colliderect(app.painter.pencil_rect)   # the name can still be changed
    app.click(hq.center)
    assert app.ui.selected == 110 and app.ui.alone                               # the HQ by itself
