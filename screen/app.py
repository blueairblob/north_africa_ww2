"""The window: mouse and keys in, frames out. Sleeps while nothing happens."""
import math
import time
import traceback

import pygame

from engine import units as U

from . import saves
from . import theme as T
from .draw import UI, Painter
from .layout import Layout, areas, buttons, game, layers, saves_list, tabs
from .session import GOES
from .sound import Sounds

GO = {pygame.K_m: "move", pygame.K_a: "attack", pygame.K_t: "road_march",        # orders with a destination
      pygame.K_j: "join", pygame.K_x: "split", pygame.K_c: "recall",             # the three for groups
      pygame.K_h: "hold", pygame.K_d: "dig_in", pygame.K_r: "rest"}              # and those that stay
AIR = {pygame.K_1: "support", pygame.K_2: "interdict", pygame.K_3: "recon"}
SCROLL = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}
DRAG = 14               # pixels the mouse must move with the button down to drag the map
FAST = 3                # how much faster the playback runs with F; its rattles are as much shorter
GLIDE_MS = 110          # how quickly the map glides to where it is going
CURSOR_EDGE = 2.5       # hexes from the edge of the view at which the map follows the keyboard cursor
PLAY_ZOOM = 1.0         # the playback is never watched from further out than this
EDGE_PX = 26            # with a unit taken up, the mouse this near the map's edge scrolls the map
EDGE_SPEED = 0.9        # base-map pixels a millisecond


class App:
    def __init__(self, session, size=T.WINDOW):
        self.session, self.ui, self.size = session, UI(), size
        self.painter = Painter(session.gmap)
        self.press = None               # where the left button went down, and whether it has dragged
        self.play, self.play_t, self.sounds, self.fast = None, 0.0, None, False   # last turn being played back
        self.target = None              # where the map is gliding to
        self.last = None                # the unit last taken up by Next, so Next goes on from it
        self.zoom_back = None           # the zoom to return to when the playback ends
        self.confirm = self.asked = False   # End turn has been pressed once with units still waiting
        self.log = None                 # a file that records what each click and key did (--log)
        self.clicked = None             # where the click being logged fell
        self.refused = None             # the engine's reply code for the last order refused, for the log
        self.saves = None               # the folder games are saved in; with none (tests) nothing is written
        self.begin_orders()
        self.ui.message = self.sky_words() + "Each unit holds unless ordered: press Move or Attack, then click the hex. Space goes on to the next."
        u = session.unit(self.ui.selected)
        if u:
            self.centre_on(tuple(u["hex"]))               # the first unit to order starts in the middle

    # ---- looking -------------------------------------------------------------------------

    def map_rect(self):
        return areas(self.size)["map"]

    def base_size(self):
        g = self.session.gmap
        return Layout(T.BASE_HEX).size(g.cols, g.rows)

    def zoom_min(self):
        """The zoom at which the whole map, with the paper round its border, just fills the map area."""
        (w, h), (bw, bh) = self.map_rect().size, self.base_size()
        return max(w / (bw + 2 * T.MARGIN), h / (bh + 2 * T.MARGIN))

    def clamp(self):
        """Keep the view on the map, and a margin of paper beyond it for its border."""
        ui, (w, h), (bw, bh) = self.ui, self.map_rect().size, self.base_size()
        ui.zoom = max(self.zoom_min(), min(T.ZOOM_MAX, ui.zoom))
        ui.cam = [max(-T.MARGIN, min(ui.cam[0], bw + T.MARGIN - w / ui.zoom)),
                  max(-T.MARGIN, min(ui.cam[1], bh + T.MARGIN - h / ui.zoom))]

    def centre_on(self, h):
        """Put a hex in the middle of the map area, at once."""
        x, y = Layout(T.BASE_HEX).centre(h)
        w, hgt = self.map_rect().size
        self.ui.cam = [x - w / self.ui.zoom / 2, y - hgt / self.ui.zoom / 2]
        self.clamp()
        self.target = None

    def glide_to(self, h):
        """Bring a hex to the middle of the map area, smoothly (tick does the moving)."""
        here = list(self.ui.cam)
        self.centre_on(h)
        self.target, self.ui.cam = list(self.ui.cam), here

    def tick(self, ms):
        """Time passes: the playback moves on, and the map glides towards where it is going."""
        self.advance(ms)
        dx, dy = self.edge()
        if dx or dy:                                      # planning a move past the edge of the view
            before = list(self.ui.cam)
            self.ui.cam = [self.ui.cam[0] + dx * EDGE_SPEED * min(ms, 50) / self.ui.zoom,
                           self.ui.cam[1] + dy * EDGE_SPEED * min(ms, 50) / self.ui.zoom]
            self.clamp()
            self.target = None
            if self.ui.cam != before:
                self.ui.hover = self.hex_under(self.ui.mouse)
        if self.target:
            ms = min(ms, 50) * (FAST if self.fast else 1)
            ease, cam = 1 - math.exp(-ms / GLIDE_MS), self.ui.cam
            self.ui.cam = [cam[0] + (self.target[0] - cam[0]) * ease, cam[1] + (self.target[1] - cam[1]) * ease]
            if abs(self.target[0] - self.ui.cam[0]) + abs(self.target[1] - self.ui.cam[1]) < 1:
                self.ui.cam, self.target = self.target, None

    def edge(self):
        """The way the map should scroll because the mouse is at its edge while a unit is being
        ordered: (dx, dy), each -1, 0 or 1."""
        area = self.map_rect()
        x, y = self.ui.mouse
        if self.play or self.ui.cover or self.session.unit(self.ui.selected) is None or not area.collidepoint((x, y)):
            return 0, 0
        return ((x > area.right - EDGE_PX) - (x < area.x + EDGE_PX), (y > area.bottom - EDGE_PX) - (y < area.y + EDGE_PX))

    @property
    def busy(self):
        """Something is moving on the screen, so frames must keep coming: the playback, the map
        gliding or scrolling at its edge, or the pulse round the unit taken up."""
        return bool(self.play or self.target or self.session.unit(self.ui.selected))

    def span(self):
        """The columns and rows of hexes that fit in the map area, with a margin."""
        (w, h), px = self.map_rect().size, self.ui.layout.hex_px
        return max(3, int(w / (px * 0.75)) - 3), max(3, int(h / (px * 0.866)) - 3)

    def spot(self, h):
        """Where a hex's centre is in the window."""
        x, y = self.ui.layout.centre(h)
        return x - int(self.ui.cam[0]) * self.ui.zoom, y - int(self.ui.cam[1]) * self.ui.zoom

    def look_at_own(self):
        """Centre on the middle of the side's units."""
        mine = [u["hex"] for u in self.session.view["units"] if u["status"] == "on_map"]
        if mine:
            cols, rows = sorted(h[0] for h in mine), sorted(h[1] for h in mine)
            self.centre_on((cols[len(cols) // 2], rows[len(rows) // 2]))

    def hex_under(self, pos):
        if not self.map_rect().collidepoint(pos):
            return None
        ui = self.ui
        h = Layout(T.BASE_HEX).hex_at(int(ui.cam[0]) + pos[0] / ui.zoom, int(ui.cam[1]) + pos[1] / ui.zoom)
        return h if self.session.gmap.on_map(h) else None

    def zoom(self, factor, about=None):
        """Zoom in or out, keeping the point under the mouse where it is."""
        ui = self.ui
        mx, my = about if about and self.map_rect().collidepoint(about) else self.map_rect().center
        bx, by = ui.cam[0] + mx / ui.zoom, ui.cam[1] + my / ui.zoom
        ui.zoom = max(self.zoom_min(), min(T.ZOOM_MAX, ui.zoom * factor))
        ui.cam = [bx - mx / ui.zoom, by - my / ui.zoom]
        self.clamp()
        self.target = None

    # ---- doing ---------------------------------------------------------------------------

    def mine_at(self, h):
        return [u["id"] for u in self.session.view["units"] if u["status"] == "on_map" and tuple(u["hex"]) == h]

    def give(self, name, to=None, with_unit=None):
        ui = self.ui
        u = self.session.unit(ui.selected)
        if u is None:
            ui.message = "Click one of your units first."
            return
        order = {"unit": ui.selected, "order": name}
        if to is not None:
            order["to"] = list(to)
        if with_unit is not None:
            order["with"] = with_unit
        if ui.alone:
            order["alone"] = True                         # one of a group, ordered by itself: it splits off
        reply = self.session.give(order)
        if not reply["ok"]:                               # the order key and the cursor stay as they were
            ui.message, self.refused = reply["text"], reply["code"]
            return
        ui.mode, ui.alone = None, False
        said = f"{self.session.group_name(u['id'])}: {T.order_name(name, self.session.members(u['id']))}."
        if to is not None and self.session.crowded(u["id"], to):  # accepted, but as things stand it will not get in
            said += f" That hex holds {U.STACK_FORMATIONS} formations already: it gets in only if one leaves."
        self.step()                                       # on to the next unit that waits, taken up and brought to the middle
        ui.hover = None                                   # no line trails the pointer for it until the pointer moves
        left = len(self.session.waiting_units())
        ui.message = said + "   " + self.left_words()

    def left_words(self):
        """How many units the player has still to go through this turn, in words."""
        s = self.session
        left, idle = len(s.waiting_units()), len(s.idle_units())
        if not left:
            return "Every unit has been gone through: press End turn."
        if left == idle:
            return f"{left} more to go through: they hold unless ordered."
        return f"{left} more to go through: {idle} holding, {left - idle} carrying on with " \
               f"{'its order' if left - idle == 1 else 'their orders'}."

    def step(self):
        """Take up the next unit not yet dealt with this turn, bringing it into view; none left, let go."""
        s, ui = self.session, self.ui
        ui.alone = False
        waiting = s.waiting_units()
        ids = [u["id"] for u in s.view["units"] if u["status"] == "on_map"]
        after = [i for i in waiting if ui.selected in ids and ids.index(i) > ids.index(ui.selected)]
        self.last = ui.selected = (after or waiting or [None])[0]
        u = s.unit(ui.selected)
        if u:
            self.glide_to(tuple(u["hex"]))                # the unit being ordered comes to the middle

    def begin_orders(self):
        """A side starts giving orders: say what ended, take up the first unit that waits."""
        s, ui = self.session, self.ui
        ui.selected = None
        self.look_at_own()
        self.step()
        self.begin_message()
        self.watch()

    def sky_words(self):
        """Bad weather, said first as a side begins its orders."""
        return {"rain": "Rain today.   ", "sandstorm": "A sandstorm today.   "}.get(self.session.weather, "")

    def begin_message(self):
        s = self.session
        names = {u["id"]: u["name"] for u in s.view["units"]}
        ended = [f"{names[uid]} {why}." for uid, why in s.ended[s.side] if uid in names]
        left, idle = len(s.waiting_units()), len(s.idle_units())
        carry = f"   {left - idle} more carry on with their orders." if left > idle else ""
        self.ui.message = self.sky_words() + ("  ".join(ended[:2]) + "   " if ended else "") + (
            f"{T.count(idle, 'unit')} {'holds' if idle == 1 else 'hold'} unless ordered." + carry +
            "   Space goes on to the next; press an order to change one." if left
            else "Every unit has been gone through: press End turn.")

    def watch(self):
        """Play back the last turn as this side saw it, if it has not watched it yet."""
        before = self.ui.zoom
        if self.ui.zoom < PLAY_ZOOM:                      # zoomed out, the counters are dots: come in to watch
            self.zoom(PLAY_ZOOM / self.ui.zoom)
        self.play, self.play_t, self.fast = self.session.playback(self.span()), 0.0, False
        self.zoom_back = before if self.play else None
        if not self.play and self.ui.zoom != before:
            self.zoom(before / self.ui.zoom)
        if self.play:
            self.ui.message = "Last turn.   F: faster   Right arrow: next   any other key or a click: skip it all"

    def advance(self, ms):
        """Move the playback on by so many milliseconds: sounds, and the map following the battles."""
        if not self.play:
            return
        ms = min(ms, 50) * (FAST if self.fast else 1)     # a long frame never skips a scene
        cues = self.play.cues(self.play_t, self.play_t + ms)
        self.play_t += ms
        if self.sounds:
            for name, amount in cues:                     # played fast, a rattle is as much shorter: still the result
                if not self.fast:
                    self.sounds.play(name, amount)
                elif name != "tick":
                    self.sounds.play(name, amount // FAST)
        focus = self.play.stage(self.play_t)["focus"]
        if focus:                                         # the map goes to what is happening
            self.glide_to(focus)
        if self.play.done(self.play_t):
            self.stop_watching()
            self.begin_message()                          # back to the orders: say who waits

    def skip_scene(self):
        """On to the next strike, group of movers or the outcome."""
        if self.sounds:
            self.sounds.stop()
        self.play_t = self.play.next_scene(self.play_t)
        if self.play.done(self.play_t):
            self.stop_watching()
            self.begin_message()

    def stop_watching(self):
        self.play, self.fast = None, False
        if self.sounds:
            self.sounds.stop()
        if self.zoom_back and self.zoom_back != self.ui.zoom:      # back to the zoom the player had
            self.zoom(self.zoom_back / self.ui.zoom)
        self.zoom_back = None
        u = self.session.unit(self.ui.selected)
        if u:
            self.glide_to(tuple(u["hex"]))                # back to the unit waiting for its order
        else:
            self.look_at_own()

    # ---- saved games ---------------------------------------------------------------------

    def save(self, auto=False):
        """Save the game as it stands; returns the file, or None. An autosave says nothing."""
        ui = self.ui
        if self.saves is None:
            ui.message = ui.message if auto else "This game was started with nowhere to save."
            return None
        try:
            path = saves.write(self.session, self.saves, auto)
        except OSError as e:
            ui.message = ui.message if auto else f"The game could not be saved: {e.strerror or e}."
            return None
        if not auto:
            ui.message = f"Game saved, with the orders given so far: {path.name}"
        return path

    def open_saves(self):
        """List the saved games over the map, to choose one."""
        self.ui.saves = saves.listing(self.saves) if self.saves is not None else []
        self.ui.message = ("Tap a saved game to go on with it. It takes the place of the game on the screen: save that first to keep it."
                           if self.ui.saves else "No games have been saved yet.")

    def load(self, path):
        """Take up the game in a file in place of this one; True if it was. A file that cannot be
        read leaves this game as it is, and says why."""
        try:
            session = saves.read(path, self.session.gmap)
        except ValueError as e:
            self.ui.message = str(e)
            return False
        self.take(session)
        if not self.play:
            self.ui.message = "Loaded: " + saves.about(session.to_save()) + ".   " + self.left_words()
        return True

    def take(self, session):
        """Go on with another game: the map is looked at as before, everything else begins anew."""
        old, self.session, self.ui = self.ui, session, UI()
        self.ui.zoom, self.ui.symbols, self.ui.remind, self.ui.overlays = old.zoom, old.symbols, old.remind, old.overlays
        self.painter.reach_cache = self.painter.zone_cache = (None, None)
        self.play, self.target, self.last, self.zoom_back = None, None, None, None
        self.confirm = self.asked = False
        if len(session.humans) > 1 and not session.state["over"]:    # two at one screen: covered until the right one sits down
            self.ui.cover = f"{T.SIDE_NAME[session.side]}: your orders. Click or press Space."
        else:
            self.begin_orders()
        u = session.unit(self.ui.selected)
        if u and not self.play:
            self.centre_on(tuple(u["hex"]))

    def press_button(self, name):
        ui = self.ui
        s = self.session
        if name == "done":
            return self.end_turn()
        if name == "next":
            return self.next_unit()
        if s.unit(ui.selected) is None:
            ui.message = "Click one of your units first."
            return
        has = None if ui.alone else s.pending[s.side].get(s.leader(ui.selected), {}).get("order")
        ok, why = s.can(ui.selected, name, ui.alone)
        if not ok and has != name:                        # a button that is greyed says why
            ui.message = why
            return
        if has == name and ui.mode is None and name not in GOES:      # Hold, Dig in or Rest, pressed again: taken back
            s.cancel(ui.selected)
            ui.message = f"{T.ORDER_NAME[name]} cancelled. It holds unless given another order."
        elif name == "split":                             # leave the group, and stay
            if ui.alone:
                self.give("hold")
            else:
                ui.message = ("Click a unit in the list on the right, then Split." if len(self.session.members(ui.selected)) > 1
                              else "This unit is not in a group.")
        elif name == "recall":                            # the HQ calls its division in
            given = self.session.recall(ui.selected)
            ui.message = ("Only a division's HQ can recall its units." if given is None
                          else "All its units are with it already." if given == 0
                          else f"{T.count(given, 'unit')} recalled to the HQ.")
        elif name == "join":
            ui.mode = None if ui.mode == name else name
            ui.hover = tuple(self.session.unit(ui.selected)["hex"]) if ui.mode else ui.hover
            ui.message = "Join: click a unit of the same division, or choose it with the arrow keys and press Enter." if ui.mode else ""
            ui.message += self.as_it_was(has, name)
        elif name in ("hold", "dig_in", "rest"):
            self.give(name)
        elif name in ("move", "attack", "road_march"):
            ui.mode = None if ui.mode == name else name
            ui.hover = tuple(self.session.unit(ui.selected)["hex"]) if ui.mode else ui.hover     # the cursor starts on the unit
            ui.message = (f"{T.ORDER_NAME[name]}: click the hex, or choose it with the arrow keys and press Enter."
                          if ui.mode else "") + self.as_it_was(has, name)

    def as_it_was(self, has, name):
        """Said when the button of the order a unit already has is pressed: it is sent somewhere
        else only by the click that follows, and until then its order is as it was."""
        if has != name:
            return ""
        return ("   Until then its order is as it was; Hold stops it." if self.ui.mode
                else f"Its order is as it was: {T.ORDER_NAME[name]}.")

    def cursor(self, dx, dy):
        """Move the keyboard's hex cursor. Up and down go along the column. Left and right go to
        the next column on the same row, so the cursor zigzags half a hex and never drifts."""
        ui, g = self.ui, self.session.gmap
        c, r = ui.hover or tuple(self.session.unit(ui.selected)["hex"])
        ui.hover = (max(0, min(g.cols - 1, c + dx)), max(0, min(g.rows - 1, r + dy)))
        x, y = self.spot(ui.hover)
        edge, (w, h) = CURSOR_EDGE * ui.layout.hex_px, self.map_rect().size
        if not (edge < x < w - edge and edge < y < h - edge):
            self.glide_to(ui.hover)                       # the map follows the cursor
        ui.mouse = (int(max(0, min(w - 1, x))), int(max(0, min(h - 1, y))))

    def end_turn(self):
        """End turn, asked for by key or button: once more to be sure if units still wait."""
        left = len(self.session.idle_units())
        if left and self.ui.remind and not self.asked and not self.session.state["over"]:
            self.confirm = True
            self.ui.message = (f"{T.count(left, 'unit')} {'has' if left == 1 else 'have'} not been gone through and will "
                               f"hold {'its' if left == 1 else 'their'} ground. Press End turn again to end the turn.")
            return
        self.done()

    def click(self, pos, button=1):
        ui, s = self.ui, self.session
        self.asked, self.confirm = self.confirm, False
        if ui.cover:
            ui.cover = None
            return self.begin_orders()
        if ui.chooser:                                    # the list over a hex of yours: one of its rows, or away
            picked = next((key for key, r in self.painter.chooser_rects.items() if r.collidepoint(pos)), None)
            h, ui.chooser = ui.chooser["hex"], None
            if picked == ("move",):
                self.give("move", h)
            elif picked == ("group",):
                n = s.group_all(h)
                ui.message = f"{T.count(n + 1, 'unit or group', 'units and groups')} here will form one group when the turn is played."
            elif isinstance(picked, tuple):
                n = s.split_up(picked[1])
                ui.message = f"{s.group_name(picked[1])} will break up into its {n + 1} units when the turn is played."
            elif picked is not None:
                ui.selected, ui.alone, ui.mode = picked, False, None
                self.taken_words()
            else:
                ui.message = "The list is closed: nothing was chosen."
            return
        if ui.saves is not None:                          # the list of saved games: one of its rows, or away
            rows = saves_list(self.size, len(ui.saves))
            picked = next((k for k, r in rows.items() if isinstance(k, int) and r.collidepoint(pos)), None)
            found, ui.saves = ui.saves, None
            if picked is None:
                ui.message = "The list is closed: no game was loaded."
            else:
                self.load(found[picked][0])
            return
        for name, r in game(self.size, ui.game_open).items():          # the Game button and its list
            if r.collidepoint(pos) and button == 1:
                ui.game_open, ui.layers_open = name == "game" and not ui.game_open, False
                if name == "save":
                    self.save()
                elif name == "load":
                    self.open_saves()
                return
        chip = self.painter.weather_rect                  # the weather on the map: a tap says what it does
        if chip and not self.play and chip.move(self.map_rect().topleft).collidepoint(pos):
            ui.message = s.weather_words()
            return
        for name, r in layers(self.size, ui.layers_open).items():      # the Layers button and its list
            if r.collidepoint(pos) and button == 1:
                if name == "layers":
                    ui.layers_open, ui.game_open = not ui.layers_open, False
                else:
                    ui.overlays ^= {name}
                return
        if not self.play and not s.state["over"] and button == 1:      # the panel's tabs, its list's arrows, the reminder box
            for name, r in tabs(self.size).items():
                if r.collidepoint(pos) and name == "remind":
                    ui.remind = not ui.remind
                    ui.message = ("End turn will ask once more when units with no order have not been gone through." if ui.remind
                                  else "End turn will not ask: units with no order hold their ground.")
                    return
                if r.collidepoint(pos):
                    ui.tab, ui.scroll = name, 0
                    ui.message = "Every unit and its order. Tap one to take it up." if name == "orders" else ""
                    return
            for name, r in self.painter.scroll_rects.items():
                if r.collidepoint(pos):
                    ui.scroll += -3 if name == "up" else 3
                    return
        offered = s.offers(ui.selected, ui.alone) if ui.tab == "unit" else []
        for name, r in buttons(self.size).items():        # an order is there to press only when it is shown
            if r.collidepoint(pos) and (name in ("next", "done") or name in offered):
                return self.press_button(name) if button == 1 else None
        if self.painter.pencil_rect and self.painter.pencil_rect.collidepoint(pos) and s.unit(ui.selected):
            ui.editing = s.group_name(ui.selected)        # the pencil: type a new name for the group
            ui.message = "Type the name. Enter keeps it; Escape leaves it as it was."
            return
        ui.editing = None
        if self.painter.back_rect and self.painter.back_rect.collidepoint(pos):    # back to the group
            ui.selected, ui.alone, ui.mode = s.leader(ui.selected), False, None
            return
        for row, uid in self.painter.report_rects.values():            # a report: go to the unit that made it
            if row.collidepoint(pos) and button == 1 and s.unit(uid):
                ui.selected, ui.alone, ui.mode, ui.tab = s.leader(uid), False, None, "unit"
                self.glide_to(tuple(s.unit(uid)["hex"]))
                self.taken_words()
                return
        for uid, r in self.painter.member_rects.items():  # a unit in the panel's list: take it up by itself
            if r.collidepoint(pos) and button == 1:
                ui.selected, ui.alone, ui.mode = uid, True, None
                ui.message = "This unit alone: an order now splits it from its group. Split leaves it where it is."
                return
        h = self.hex_under(pos)
        if h is None or s.state["over"]:                  # nothing to order there; say so
            if areas(self.size)["map"].collidepoint(pos):
                ui.message = "The game is over." if s.state["over"] else "That is off the map."
            return
        if button == 3:                                   # on your own units: what can be done with the stack
            if self.mine_at(h) and not ui.mode:
                chosen = s.unit(ui.selected)
                ui.chooser = {"hex": h, "ids": s.parties_at(h),
                              "mover": s.leader(ui.selected) if chosen and h != tuple(chosen["hex"]) else None}
                ui.message = "Choose a unit, or group or split the stack."
            else:                                         # elsewhere: let go
                ui.mode, ui.selected, ui.message = (None, ui.selected, "") if ui.mode else (None, None, "")
            return
        here = self.mine_at(h)
        chosen = s.unit(ui.selected)
        away = chosen is not None and h != tuple(chosen["hex"])          # a unit is taken up, and the click is elsewhere
        if ui.mode == "join" and chosen:
            self.join_at(h)
        elif ui.mode and chosen and not (here and away and ui.mode not in ("move", "road_march")):
            self.give(ui.mode, h)                         # an order pressed first goes where the click is
        elif here:                                        # your own units: the click takes them up, whatever is in hand
            ui.alone, ui.mode = False, None
            here = sorted({s.leader(i) for i in here})    # a group is taken up as one, by its leader
            if len(here) > 1:
                ui.chooser = {"hex": h, "ids": here, "mover": s.leader(ui.selected) if away else None}
                ui.message = "Several of your units are here: choose one from the list."
            elif chosen and here[0] == s.leader(ui.selected):
                ui.message = (f"{s.group_name(here[0])} is taken up already, and this is where it is. "
                              "Press Move or Attack, then click where it should go.")
            else:
                was = f"{s.group_name(ui.selected)} put down.   " if chosen else ""
                ui.selected = here[0]
                self.taken_words(was)
        elif chosen is None and s.order_at(h) is not None:               # a click on an order's line finds its unit
            ui.selected = s.order_at(h)
            self.glide_to(tuple(s.unit(ui.selected)["hex"]))
            ui.message = "This is the unit with that order. Press its lit button to send it elsewhere, or Hold to stop it."
        elif chosen:                                      # a plain click gives no order: the unit keeps to what it has
            order = s.pending[s.side].get(s.leader(ui.selected))
            doing = T.order_name(order["order"], s.members(ui.selected)) if order else "Hold"
            ui.message = (f"{s.group_name(ui.selected)} keeps to its order, {doing}. "
                          "To send it there, press Move or Attack first, then click the hex.")
        else:
            ui.message = "No unit is taken up. Click one of your units first."

    def join_at(self, h):
        """Join the unit taken up to a unit of its division in this hex."""
        other = self.session.related_at(self.ui.selected, h)
        if other is None:
            self.ui.message = "There is no other unit of yours there."
        else:
            self.give("join", with_unit=other)

    def next_unit(self):
        """On to the next unit not yet dealt with this turn. The unit in hand is let stand as it
        is, with its standing order or, with none, holding: this is the one key that says
        "carry on"."""
        s, ui = self.session, self.ui
        said = ""
        if s.unit(ui.selected) and s.leader(ui.selected) in s.waiting_units():
            lead = s.leader(ui.selected)
            s.keep(lead)
            order = s.pending[s.side].get(lead)
            said = (f"{s.group_name(lead)} carries on: {T.order_name(order['order'], s.members(lead))}.   " if order
                    else f"{s.group_name(lead)} holds.   ")
        waiting = s.waiting_units()
        ui.mode, ui.alone, ui.chooser = None, False, None
        if not waiting:
            ui.selected, ui.message = None, said + "Every unit has been gone through: press End turn."
            return
        after = [i for i in waiting if s.unit(ui.selected) and i > s.leader(ui.selected)]
        self.last = ui.selected = (after or waiting)[0] if ui.selected is not None or self.last is None else \
            ([i for i in waiting if i > self.last] or waiting)[0]
        self.glide_to(tuple(s.unit(ui.selected)["hex"]))  # it is brought to the middle, taken up and lit
        self.taken_words(said)

    def taken_words(self, before=""):
        """The message for a unit just taken up: what it will do, and how to change that."""
        s, ui = self.session, self.ui
        lead = s.leader(ui.selected)
        order = s.pending[s.side].get(lead)
        name = s.group_name(lead)
        if order is None:
            ui.message = before + f"{name} holds. Space goes on; press an order to change it."
        elif lead in s.waiting_units():
            ui.message = before + (f"{name} carries on with its order, {T.order_name(order['order'], s.members(lead))}. "
                                   "Space keeps it; any order changes it.")
        else:
            ui.message = before + (f"{name} has its order, {T.order_name(order['order'], s.members(lead))}. " + (
                "Press its lit button to send it elsewhere, or Hold to stop it." if order["order"] in GOES
                else "Press an order to change it, or its lit button to take it back."))

    def done(self):
        ui, s = self.ui, self.session
        if s.state["over"]:
            return
        what = s.done()
        self.save(auto=True)                              # every time orders are handed in: the game can be gone on with
        ui.selected, ui.mode = None, None
        self.painter.reach_cache = (None, None)
        if what == "over":
            ui.message = "The game is over."
            self.watch()
        elif len(s.humans) > 1:
            ui.cover = f"{T.SIDE_NAME[s.side]}: your orders. Click or press Space."
            ui.message = "Orders are hidden from the other player." if what == "pass" else "The turn has been played."
        else:
            self.begin_orders()

    def key(self, key):
        ui = self.ui
        self.asked, self.confirm = self.confirm, False
        if ui.cover:
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                ui.cover = None
                self.begin_orders()
            return
        if ui.saves is not None:                          # the list of saved games is up: any key puts it away
            ui.saves, ui.message = None, "The list is closed: no game was loaded."
        elif key == pygame.K_F5:
            self.save()
        elif key == pygame.K_F9:
            self.open_saves()
        elif ui.mode and self.session.unit(ui.selected) and key in SCROLL:     # choosing a destination
            self.cursor(*SCROLL[key])
        elif ui.mode and self.session.unit(ui.selected) and key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if ui.mode == "join" and ui.hover:
                self.join_at(ui.hover)
            elif ui.hover and ui.hover != tuple(self.session.unit(ui.selected)["hex"]):
                self.give(ui.mode, ui.hover)              # Enter confirms the destination; it never ends the turn here
            else:
                ui.message = "Choose the hex with the arrow keys first, or press Escape."
        elif key in GO:
            self.press_button(GO[key])
        elif key in AIR:
            self.session.set_air(AIR[key])
            ui.message = f"Air force: {AIR[key]}."
        elif key in SCROLL:
            dx, dy = SCROLL[key]
            ui.cam = [ui.cam[0] + dx * T.BASE_HEX * 2, ui.cam[1] + dy * T.BASE_HEX * 2]
            self.clamp()
            self.target = None
        elif key in (pygame.K_s, pygame.K_z, pygame.K_k):
            ui.overlays ^= {pygame.key.name(key)}
        elif key == pygame.K_l:
            ui.layers_open = not ui.layers_open
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.zoom(T.ZOOM_STEP)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.zoom(1 / T.ZOOM_STEP)
        elif key == pygame.K_F3:                          # counters: pictures or NATO-style symbols
            ui.symbols = "nato" if ui.symbols == "pictures" else "pictures"
            ui.message = "Counters show " + ("NATO-style symbols." if ui.symbols == "nato" else "pictures.")
        elif key == pygame.K_HOME:
            self.zoom(0.01)                               # the whole map
        elif key in (pygame.K_TAB, pygame.K_SPACE, pygame.K_n):
            self.next_unit()
        elif key == pygame.K_ESCAPE:
            if ui.chooser or ui.layers_open or ui.game_open:
                ui.chooser, ui.layers_open, ui.game_open = None, False, False
            else:
                ui.mode, ui.selected = (None, ui.selected) if ui.mode else (None, None)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.end_turn()

    def note(self, what, before):
        """One line in the play log: when, what was done, and what the screen made of it."""
        ui, s = self.ui, self.session
        named = lambda uid: f"{uid} {s.group_name(uid)}" if s.unit(uid) else "nothing"
        flags = lambda mode, alone, menu: "".join(f", {k}" for k in (mode, "alone" * alone, "menu" * menu) if k)
        order = s.pending[s.side].get(s.leader(before[0])) if s.unit(before[0]) else None
        at = self.hex_under(self.clicked) if self.clicked else ui.hover      # the hex the click fell on, as the map stood
        state = "".join(f" {k}" for k, on in (("playback", self.play), ("cover", ui.cover), ("over", s.state["over"]),
                                              ("gliding", self.target), (f"tab-{ui.tab}", ui.tab != "unit")) if on)
        self.log.write(f"{time.strftime('%H:%M:%S')} | turn {s.state['turn']} {s.side} | {what} | hex {at}{state} | "
                       f"had {named(before[0])}{flags(*before[1:])} | has {named(ui.selected)}"
                       f"{flags(ui.mode, ui.alone, bool(ui.chooser))} | its order {order} | "
                       f"refused {self.refused} | to go through {len(s.waiting_units())} | {ui.message}\n")
        self.log.flush()

    def handle(self, event):
        """One event, recorded in the play log if there is one: a line for each key and each
        click, none for the button going down. Returns False when the window is closed."""
        down = event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.play
        if self.log is None or down or event.type not in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) \
                or (event.type == pygame.MOUSEBUTTONUP and (event.button != 1 or not self.press)):
            return self.handle_one(event)
        ui = self.ui
        before, self.refused = (ui.selected, ui.mode, ui.alone, bool(ui.chooser)), None
        self.clicked = getattr(event, "pos", None)
        what = f"key {pygame.key.name(event.key)}" if event.type == pygame.KEYDOWN else \
            ("drag of the map, no click" if self.press and self.press[1] else
             f"{'right click' if event.button == 3 else 'click'} at {event.pos}") + (" during the playback" if self.play else "")
        try:
            return self.handle_one(event)
        except Exception:
            self.log.write(traceback.format_exc())
            raise
        finally:
            self.note(what, before)

    def handle_one(self, event):
        ui = self.ui
        if event.type == pygame.QUIT:
            self.save(auto=True)                          # left in the middle of a turn: the orders given so far are kept
            return False
        if event.type == pygame.VIDEORESIZE:
            self.size = (max(900, event.w), max(560, event.h))
            self.clamp()
        elif self.play:                                   # F goes faster; any other key or a click skips
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                self.fast = not self.fast
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RIGHT, pygame.K_n):
                self.skip_scene()
            elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.stop_watching()
                self.begin_message()
        elif event.type == pygame.KEYDOWN and ui.editing is not None:       # typing a group's name
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.session.rename(ui.selected, ui.editing)
                ui.message, ui.editing = f"Named {self.session.group_name(ui.selected)}.", None
            elif event.key == pygame.K_ESCAPE:
                ui.editing = None
            elif event.key == pygame.K_BACKSPACE:
                ui.editing = ui.editing[:-1]
            elif getattr(event, "unicode", "") and event.unicode.isprintable() and len(ui.editing) < 28:
                ui.editing += event.unicode
        elif event.type == pygame.KEYDOWN:
            self.key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.press = [event.pos, False]
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.click(event.pos, 3)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.press:
            if not self.press[1]:
                self.click(event.pos, 1)
            self.press = None
        elif event.type == getattr(pygame, "WINDOWLEAVE", -1):
            ui.mouse = self.map_rect().center             # the mouse has left: no scrolling at the edge
        elif event.type == pygame.MOUSEWHEEL and ui.tab == "orders" and areas(self.size)["panel"].collidepoint(pygame.mouse.get_pos()):
            ui.scroll = max(0, ui.scroll - event.y)       # over the list of orders, the wheel scrolls it
        elif event.type == pygame.MOUSEWHEEL:
            self.zoom(T.ZOOM_STEP ** event.y, pygame.mouse.get_pos())
        elif event.type == pygame.MOUSEMOTION:
            ui.mouse = event.pos
            if self.press and (self.press[1] or abs(event.pos[0] - self.press[0][0]) + abs(event.pos[1] - self.press[0][1]) > DRAG):
                self.press[1] = True                      # dragging the map
                ui.cam = [ui.cam[0] - event.rel[0] / ui.zoom, ui.cam[1] - event.rel[1] / ui.zoom]
                self.clamp()
                self.target = None
            ui.hover = None if self.press and self.press[1] else self.hex_under(event.pos)
        return True

    def paint(self, surface):
        stage = self.play.stage(self.play_t) if self.play else None
        self.painter.frame(surface, self.session, self.ui, stage)

    def run(self):
        pygame.init()
        pygame.display.set_caption("Benghazi Handicap")
        window = pygame.display.set_mode(self.size, pygame.RESIZABLE)
        self.painter.base = self.painter.base.convert()
        if len(self.session.humans) > 1:
            self.ui.cover = f"{T.SIDE_NAME[self.session.side]}: your orders. Click or press Space."
        self.sounds = Sounds()
        clock, running = pygame.time.Clock(), True
        while running:
            self.paint(window)
            pygame.display.flip()
            if self.busy:                                 # something is moving: frames keep coming
                events = pygame.event.get()
                self.tick(clock.tick(60 if self.play or self.target or any(self.edge()) else 30))
            else:                                         # otherwise sleep until something happens
                events = [pygame.event.wait()] + pygame.event.get()
                clock.tick()
            for event in events:
                running = running and self.handle(event)
                if event.type == pygame.VIDEORESIZE:
                    window = pygame.display.set_mode(self.size, pygame.RESIZABLE)
        pygame.quit()
