"""The window: mouse and keys in, frames out. Sleeps while nothing happens."""
import pygame

from . import theme as T
from .draw import UI, Painter, guess
from .layout import Layout, areas, buttons
from .sound import Sounds

GO = {pygame.K_m: "move", pygame.K_a: "attack", pygame.K_r: "road_march"}        # orders with a destination
STAY = {pygame.K_h: "hold", pygame.K_d: "dig_in", pygame.K_t: "rest"}
AIR = {pygame.K_1: "support", pygame.K_2: "interdict", pygame.K_3: "recon"}
SCROLL = {pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0), pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1)}
DRAG = 6                # pixels the mouse must move with the button down to drag the map
FAST = 5                # how much faster the playback runs with F
GLIDE_MS = 180          # how quickly the map goes to a striker


class App:
    def __init__(self, session, size=T.WINDOW):
        self.session, self.ui, self.size = session, UI(), size
        self.painter = Painter(session.gmap)
        self.press = None               # where the left button went down, and whether it has dragged
        self.play, self.play_t, self.sounds, self.fast = None, 0.0, None, False   # last turn being played back
        self.begin_orders()
        self.ui.message = "Click where this unit should go, or an enemy to attack. Orders stand until done."
        self.look_at_own()

    # ---- looking -------------------------------------------------------------------------

    def map_rect(self):
        return areas(self.size)["map"]

    def base_size(self):
        g = self.session.gmap
        return Layout(T.BASE_HEX).size(g.cols, g.rows)

    def zoom_min(self):
        """The zoom at which the whole map just fills the map area."""
        (w, h), (bw, bh) = self.map_rect().size, self.base_size()
        return max(w / bw, h / bh)

    def clamp(self):
        ui, (w, h), (bw, bh) = self.ui, self.map_rect().size, self.base_size()
        ui.zoom = max(self.zoom_min(), min(T.ZOOM_MAX, ui.zoom))
        ui.cam = [max(0.0, min(ui.cam[0], bw - w / ui.zoom)), max(0.0, min(ui.cam[1], bh - h / ui.zoom))]

    def centre_on(self, h):
        x, y = Layout(T.BASE_HEX).centre(h)
        w, hgt = self.map_rect().size
        self.ui.cam = [x - w / self.ui.zoom / 2, y - hgt / self.ui.zoom / 2]
        self.clamp()

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

    # ---- doing ---------------------------------------------------------------------------

    def mine_at(self, h):
        return [u["id"] for u in self.session.view["units"] if u["status"] == "on_map" and tuple(u["hex"]) == h]

    def give(self, name, to=None):
        ui = self.ui
        u = self.session.unit(ui.selected)
        if u is None:
            ui.message = "Click one of your units first."
            return
        order = {"unit": ui.selected, "order": name}
        if to is not None:
            order["to"] = list(to)
        reply = self.session.give(order)
        ui.mode = None
        if not reply["ok"]:
            ui.message = reply["text"]
            return
        said = f"{u['name']}: {T.ORDER_NAME[name]}."
        self.step()                                       # on to the next unit that waits for an order
        left = len(self.session.waiting_units())
        ui.message = said + (f"   {left} more to order." if left else "   All units have orders: press End turn.")

    def step(self):
        """Take up the next unit with no order, bringing it into view; none left, let go."""
        s, ui = self.session, self.ui
        waiting = s.waiting_units()
        ids = [u["id"] for u in s.view["units"] if u["status"] == "on_map"]
        after = [i for i in waiting if ui.selected in ids and ids.index(i) > ids.index(ui.selected)]
        ui.selected = (after or waiting or [None])[0]
        u = s.unit(ui.selected)
        if u:
            x, y = Layout(T.BASE_HEX).centre(tuple(u["hex"]))
            (w, h), z = self.map_rect().size, ui.zoom
            if not (ui.cam[0] + 80 / z < x < ui.cam[0] + (w - 80) / z and ui.cam[1] + 80 / z < y < ui.cam[1] + (h - 80) / z):
                self.centre_on(tuple(u["hex"]))           # the map shifts across only when it must

    def begin_orders(self):
        """A side starts giving orders: say what ended, take up the first unit that waits."""
        s, ui = self.session, self.ui
        ui.selected = None
        self.look_at_own()
        self.step()
        self.begin_message()
        self.watch()

    def begin_message(self):
        s = self.session
        names = {u["id"]: u["name"] for u in s.view["units"]}
        ended = [f"{names[uid]} {why[0].lower() + why[1:]}" for uid, why in s.ended[s.side] if uid in names]
        left = len(s.waiting_units())
        self.ui.message = ("  ".join(ended[:2]) + "   " if ended else "") + (
            f"{left} units wait for orders." if left else "All units have orders: press End turn.")

    def watch(self):
        """Play back the last turn as this side saw it, if it has not watched it yet."""
        self.play, self.play_t, self.fast = self.session.playback(), 0.0, False
        if self.play:
            self.ui.message = "Last turn.   F: faster   any other key or a click: skip"

    def advance(self, ms):
        """Move the playback on by so many milliseconds: sounds, and the map following the battles."""
        if not self.play:
            return
        ms = min(ms, 50) * (FAST if self.fast else 1)     # a long frame never skips a scene
        cues = self.play.cues(self.play_t, self.play_t + ms)
        self.play_t += ms
        if self.sounds and not self.fast:
            for name, amount in cues:
                self.sounds.play(name, amount)
        focus = self.play.stage(self.play_t)["focus"]
        if focus:                                         # the map goes to the striker, smoothly
            x, y = Layout(T.BASE_HEX).centre(focus)
            (w, h), ui = self.map_rect().size, self.ui
            want = (x - w / ui.zoom / 2, y - h / ui.zoom / 2)
            ease = min(1.0, ms / GLIDE_MS)
            ui.cam = [ui.cam[0] + (want[0] - ui.cam[0]) * ease, ui.cam[1] + (want[1] - ui.cam[1]) * ease]
            self.clamp()
        if self.play.done(self.play_t):
            self.stop_watching()
            self.begin_message()                          # back to the orders: say who waits

    def stop_watching(self):
        self.play, self.fast = None, False
        if self.sounds:
            self.sounds.stop()
        self.look_at_own()

    def press_button(self, name):
        ui = self.ui
        if name == "done":
            self.done()
        elif name in ("s", "z"):
            ui.overlays ^= {name}
        elif self.session.unit(ui.selected) is None:
            ui.message = "Click one of your units first."
        elif name in ("move", "attack", "road_march"):
            ui.mode = None if ui.mode == name else name
            ui.message = f"{T.ORDER_NAME[name]}: now click the hex to go to." if ui.mode else ""
        else:
            self.give(name)

    def click(self, pos, button=1):
        ui, s = self.ui, self.session
        if ui.cover:
            ui.cover = None
            return self.begin_orders()
        for name, r in buttons(self.size).items():
            if r.collidepoint(pos):
                return self.press_button(name) if button == 1 else None
        h = self.hex_under(pos)
        if h is None or s.state["over"]:
            return
        if button == 3:                                   # let go
            ui.mode, ui.selected, ui.message = (None, ui.selected, "") if ui.mode else (None, None, "")
            return
        here = self.mine_at(h)
        chosen = s.unit(ui.selected)
        if ui.mode and chosen:
            self.give(ui.mode, h)
        elif here:                                        # your own units: take one, or the next in the pile
            ui.selected = here[(here.index(ui.selected) + 1) % len(here)] if ui.selected in here else here[0]
            ui.message = "Now click where it should go, or an enemy to attack."
        elif chosen and guess(s, h):
            self.give(guess(s, h), h)                     # a plain click: attack a seen enemy, else move

    def next_unit(self):
        """The next unit with no order yet; failing that, the next unit."""
        s, ui = self.session, self.ui
        ids = [u["id"] for u in s.view["units"] if u["status"] == "on_map"]
        if not ids:
            return
        start = ids.index(ui.selected) + 1 if ui.selected in ids else 0
        ring = ids[start:] + ids[:start]
        ui.selected = next((i for i in ring if i not in s.pending[s.side]), ring[0])
        ui.mode = None
        self.centre_on(tuple(s.unit(ui.selected)["hex"]))
        ui.message = "This unit keeps its order." if ui.selected in s.pending[s.side] else "This unit waits for an order."

    def done(self):
        ui, s = self.ui, self.session
        if s.state["over"]:
            return
        what = s.done()
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
        if ui.cover:
            if key in (pygame.K_SPACE, pygame.K_RETURN):
                ui.cover = None
                self.begin_orders()
            return
        if key in GO:
            self.press_button(GO[key])
        elif key in STAY:
            self.give(STAY[key])
        elif key in AIR:
            self.session.set_air(AIR[key])
            ui.message = f"Air force: {AIR[key]}."
        elif key in SCROLL:
            dx, dy = SCROLL[key]
            ui.cam = [ui.cam[0] + dx * T.BASE_HEX * 2, ui.cam[1] + dy * T.BASE_HEX * 2]
            self.clamp()
        elif key in (pygame.K_s, pygame.K_z):
            ui.overlays ^= {pygame.key.name(key)}
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.zoom(T.ZOOM_STEP)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.zoom(1 / T.ZOOM_STEP)
        elif key == pygame.K_HOME:
            self.zoom(0.01)                               # the whole map
        elif key in (pygame.K_TAB, pygame.K_SPACE):
            self.next_unit()
        elif key == pygame.K_ESCAPE:
            ui.mode, ui.selected = (None, ui.selected) if ui.mode else (None, None)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.done()

    def handle(self, event):
        """One event. Returns False when the window is closed."""
        ui = self.ui
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.VIDEORESIZE:
            self.size = (max(900, event.w), max(560, event.h))
            self.clamp()
        elif self.play:                                   # F goes faster; any other key or a click skips
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                self.fast = not self.fast
            elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.stop_watching()
                self.begin_message()
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
        elif event.type == pygame.MOUSEWHEEL:
            self.zoom(T.ZOOM_STEP ** event.y, pygame.mouse.get_pos())
        elif event.type == pygame.MOUSEMOTION:
            ui.mouse = event.pos
            if self.press and (self.press[1] or abs(event.pos[0] - self.press[0][0]) + abs(event.pos[1] - self.press[0][1]) > DRAG):
                self.press[1] = True                      # dragging the map
                ui.cam = [ui.cam[0] - event.rel[0] / ui.zoom, ui.cam[1] - event.rel[1] / ui.zoom]
                self.clamp()
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
            if self.play:                                 # playing back: a frame every sixtieth of a second
                events = pygame.event.get()
                self.advance(clock.tick(60))
            else:                                         # otherwise sleep until something happens
                events = [pygame.event.wait()] + pygame.event.get()
                clock.tick()
            for event in events:
                running = running and self.handle(event)
                if event.type == pygame.VIDEORESIZE:
                    window = pygame.display.set_mode(self.size, pygame.RESIZABLE)
        pygame.quit()
