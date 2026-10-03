"""The screen (DESIGN.md §12): its geometry, a game in progress, and that a frame can be drawn
with no window. What it looks like needs eyes; these check what it does."""
import json
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
pygame = pytest.importorskip("pygame")

from engine import players                                        # noqa: E402
from helpers import GMAP, ROOT, small                             # noqa: E402
from screen import layout, theme                                  # noqa: E402
from screen.app import App                                        # noqa: E402
from screen.layout import Layout                                  # noqa: E402
from screen.session import Session                                # noqa: E402


def crusader():
    return json.loads((ROOT / "data" / "scenarios" / "crusader.json").read_text())


def test_a_hex_is_as_many_pixels_across_as_asked_and_the_counter_fits_in_it():   # docs/COUNTERS.md
    lay = Layout(96)
    (x0, _), (x1, _) = lay.corners((10, 10))[0], lay.corners((10, 10))[3]
    assert round(x0 - x1) == 96 and lay.counter == 61
    _, y0 = lay.centre((10, 10))
    _, y1 = lay.centre((10, 11))
    assert round(y1 - y0) == 83


def test_the_base_map_is_the_size_the_screen_expects():
    from mapgen import render
    assert render.BASE_HEX == theme.BASE_HEX
    if (ROOT / "art" / "basemap.jpg").exists():
        assert pygame.image.load(str(ROOT / "art" / "basemap.jpg")).get_size() == Layout(theme.BASE_HEX).size(GMAP.cols, GMAP.rows)


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
    assert len(colours) > 6 and "Move here" in app.ui.message


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
    assert app.ui.zoom == app.zoom_min() and app.ui.cam[0] + w / app.ui.zoom <= bw + 1 and app.ui.cam[1] + h / app.ui.zoom <= bh + 1
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
    app.key(pygame.K_t)
    assert app.session.order_of(101)["order"] == "rest" and app.ui.selected == 102      # and on to the next
    app.click(spot((59, 11)))
    app.click(spot((60, 12)))                                      # a plain click on open ground: move
    assert app.session.order_of(101) == {"unit": 101, "order": "move", "to": [60, 12]}
    app.click(spot((57, 11)))                                      # a click on your own unit takes it up
    assert app.ui.selected == 109
    assert (55, 10) in {tuple(e["hex"]) for e in app.session.view["enemy"]}
    app.click(spot((55, 10)))                                      # ...and on an enemy in sight: attack
    assert app.session.order_of(109) == {"unit": 109, "order": "attack", "to": [55, 10]}
    app.click(spot((57, 11)))
    app.click(layout.buttons(app.size)["dig_in"].center)           # the order bar
    assert app.session.order_of(109)["order"] == "dig_in"
    app.click(layout.buttons(app.size)["s"].center)
    assert app.ui.overlays == {"s"}
    app.key(pygame.K_3)
    assert app.session.air["axis"] == "recon"
    app.click(layout.buttons(app.size)["done"].center)
    assert "still wait for orders" in app.ui.message and app.session.side == "axis"   # units wait: asked once
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
    assert s.pending["axis"][101]["to"] == far and s.pending["axis"][106]["order"] == "dig_in"   # given again
    assert s.unit(101)["hex"] != [59, 11] and s.ended["axis"] == []
    s.done()
    assert s.unit(101)["hex"] == far and 101 not in s.pending["axis"]            # arrived: it waits again
    assert s.ended["axis"] == [(101, "has arrived")] and 101 in s.waiting_units()
    assert s.record[1]["axis"]["orders"] == [{"unit": 101, "order": "move", "to": far}, {"unit": 106, "order": "dig_in"}]


def test_the_screen_steps_through_the_units_that_wait():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["axis"], scripted={"cw": players.DoNothing(GMAP)}))
    assert app.ui.selected == 101                                 # the first unit is taken up for you
    app.key(pygame.K_h)
    assert app.session.order_of(101)["order"] == "hold" and app.ui.selected == 102      # ...then the next
    for _ in range(17):
        app.key(pygame.K_h)
    assert app.session.waiting_units() == [] and "End turn" in app.ui.message
    app.key(pygame.K_RETURN)
    assert app.session.state["turn"] == 2 and app.session.waiting_units() == []          # the orders stand


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
    from screen.replay import BEAT_MS, LEAD_MS
    play, s = played([unit(101, "axis", "armour", [70, 25], steps=20), unit(201, "cw", "armour", [70, 24], steps=20),
                      unit(202, "cw", "foot", [69, 24], steps=9)],
                     cw=[{"unit": 201, "order": "attack", "to": [70, 25]}, {"unit": 202, "order": "attack", "to": [70, 25]}])
    battle = next(e for e in s.view["events"] if e["event"] == "battle")
    (t1, e1, first), (t2, e2, second), (t3, e3, reply) = scenes(play, "strike")
    assert (first["by"], first["on"], first["arm"]) == ([201], [101], "armour")
    assert (second["by"], second["on"], second["arm"]) == ([202], [101], "foot")
    assert reply["by"] == [101] and reply["on"] == [201, 202] and reply["reply"]
    assert e1 <= t2 and e2 <= t3                                                # never two at once
    assert first["damage"] + second["damage"] <= battle["cld"] and reply["damage"] == battle["cla"]
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
    assert outcome["gone"] == [101] and outcome["burst"] == [101] and ("boom", 0) in play.cues(0, play.length)
    assert at(play.stage(start - 10), 101) is not None and at(play.stage(start + 100), 101)[5] == 1.0   # still there
    assert play.stage(start + 1000)["bursts"] and at(play.stage(play.length), 101) is None
    assert at(play.stage(play.length), 201)[3] == (70, 24)                      # the victors follow up

    play, _ = played([unit(101, "axis", "foot", [70, 25], steps=3), unit(201, "cw", "armour", [70, 24], steps=15),
                      unit(102, "axis", "guns", [66, 25], steps=6), unit(202, "cw", "armour", [66, 24], steps=6)],
                     cw=[{"unit": 201, "order": "attack", "to": [70, 25]}, {"unit": 202, "order": "attack", "to": [66, 25]}])
    start, end, outcome = scenes(play, "outcome")[0]
    assert set(outcome["slides"]) == {101, 201} and outcome["held"] == [102, 202]
    last = scenes(play, "strike")[-1]
    assert at(play.stage(last[1] - 10), 101)[3] == (70, 25)                     # it has not fallen back yet
    assert at(play.stage(start + 800), 102)[6] == "held"
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
    assert app.play is None and not app.fast and "wait for orders" in app.ui.message
    app.done()
    assert app.session.state["turn"] == 3


# ---- found by playtest -------------------------------------------------------------------

def test_when_the_playback_runs_out_the_message_goes_back_to_the_orders():
    pygame.init()
    app = App(Session(crusader(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)}))
    app.done()
    assert "skip" in app.ui.message
    while app.play:
        app.advance(50)
    assert "skip" not in app.ui.message and "wait for orders" in app.ui.message


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


def test_with_no_human_the_screen_gives_the_engine_command_that_works():
    import subprocess
    import sys
    run = subprocess.run([sys.executable, "-m", "screen", "crusader", "--axis", "nothing", "--cw", "nothing"],
                         cwd=ROOT, capture_output=True, text=True)
    hint = run.stderr.strip().splitlines()[-1].split()
    assert run.returncode != 0 and hint == ["python", "-m", "engine", "crusader", "nothing", "nothing"]
    again = subprocess.run([sys.executable] + hint[1:], cwd=ROOT, capture_output=True, text=True)
    assert again.returncode == 0 and "invariants held" in again.stdout           # the command it gives works


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
    assert s.give({"unit": 201, "order": "attack", "to": [70, 25]})["ok"]       # to attack again is a new decision


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
    assert "Move here" in app.ui.message                             # the way is previewed as with the mouse
    keys(app, "RETURN")
    assert app.session.pending["cw"][201] == {"unit": 201, "order": "move", "to": [66, 21]}
    assert app.session.state["turn"] == 1 and app.ui.mode is None and app.ui.selected == 202
    keys(app, "a", "LEFT", "ESCAPE")                                 # Escape cancels
    assert app.ui.mode is None and 202 not in app.session.pending["cw"]
    keys(app, "m", "RETURN")                                         # Enter with no hex chosen: nothing happens
    assert app.session.state["turn"] == 1 and "Choose the hex" in app.ui.message
    keys(app, "ESCAPE", "RETURN")
    assert app.session.state["turn"] == 1 and "still wait for orders" in app.ui.message    # asked once
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
    for _ in range(8):                                               # the automatic step after each order
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
    assert "1 more to order" in app.ui.message
    app.ui.selected = None
    app.begin_message()
    assert app.ui.message == "1 unit waits for orders."
    keys(app, "RETURN")
    assert app.ui.message.startswith("1 unit still waits for orders and will hold its ground.")
    told = describe({"event": "battle", "hex": [55, 10], "lost": {"1": 1, "2": 0}, "retreated": False}, s)
    assert told == "Battle at Tobruk: 1 step lost"


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
    assert "Right arrow: next" in app.ui.message
    app.advance(40)
    keys(app, "RIGHT")
    assert app.play is not None and app.play_t == starts[1] and ("stop", 0) in app.sounds.played
    keys(app, "n")
    assert app.play_t == starts[2]
    for _ in starts[2:]:
        keys(app, "RIGHT")
    assert app.play is None and "wait" in app.ui.message             # past the last scene: back to the orders


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
    battle = next(e for e in s.view["events"] if e["event"] == "battle")
    assert battle["cla"] == COH_MIN and [x[2]["by"] for x in scenes(play, "strike")] == [[201]]
    play, s = played([unit(101, "axis", "guns", [70, 25], steps=6), unit(201, "cw", "armour", [70, 24], steps=20)],
                     cw=[{"unit": 201, "order": "attack", "to": [70, 25]}])
    assert [x[2]["reply"] for x in scenes(play, "strike")] == [False, True]      # a reply that hurt is shown


def test_the_end_of_a_game_says_how_the_result_was_reached():        # C, E
    from screen.draw import score_lines
    view = {"vp": {"axis": 252, "cw": 112}, "kills": {"axis": 90, "cw": 20}, "par": 106}
    assert score_lines(view) == ["Axis: 162 for places + 90 for units = 252",
                                 "Commonwealth: 92 for places + 20 for units = 112",
                                 "Standing still, the Axis leads by 106.", "Against that: Axis by 34."]
    pygame.init()
    s = Session(small(), GMAP, humans=["cw"], scripted={"axis": players.AlwaysAttack(GMAP)})
    while not s.state["over"]:
        s.done()
    app = App(s)
    app.play = None
    surface = pygame.Surface(theme.WINDOW)
    app.paint(surface)                                               # the panel draws the breakdown and the losses
    assert s.view["par"] == small()["par"] and set(s.view["kills"]) == {"axis", "cw"}
    assert all(u["fate"] for u in s.view["units"] if u["status"] in ("destroyed", "withdrawn"))
