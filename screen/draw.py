"""Paints a frame: the base map scaled to the zoom, the counters and overlays on it, the order
bar under it and the panel beside it."""
import os

import pygame

from engine import paths
from engine import units as U
from engine.gamemap import distance
from engine.movement import ALLOWANCE
from engine.supply import REACH, REACH_FULL
from engine.view import SPOT_RANGE, SPOT_RANGE_RECON

from . import theme as T
from .layout import Layout, areas, buttons

ROOT = os.path.dirname(os.path.dirname(__file__))
ART = os.path.join(ROOT, "art", "counters")
BASE = os.path.join(ROOT, "art", "basemap.jpg")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf"
FLAME = {"fire0": (255, 214, 40, 150), "fire1": (226, 52, 24, 150)}        # a burning unit: yellow, then red


class UI:
    """What the player is looking at and doing."""
    def __init__(self):
        self.zoom = T.ZOOM_START
        self.cam = [0.0, 0.0]           # the base-map pixel at the top left of the map area
        self.selected = None            # unit id
        self.mode = None                # an order waiting for its destination
        self.overlays = set()           # "s" supply, "z" zones of control and what is seen
        self.hover = None               # the hex under the mouse
        self.mouse = (0, 0)
        self.message = ""
        self.cover = None               # text shown instead of the map between two players

    @property
    def layout(self):
        return Layout(T.BASE_HEX * self.zoom)


class Painter:
    def __init__(self, gmap):
        pygame.font.init()
        self.gmap = gmap
        self.fonts, self.sprites = {}, {}
        self.base = self.load_base()
        self.back = (None, None)        # the scaled background and what it was made for
        self.reach_cache = (None, None)
        self.zone_cache = (None, None)
        self.playing = False            # the last turn is being played back

    def font(self, px, bold=False):
        px = max(9, int(px))
        if (px, bold) not in self.fonts:
            face = FONT % ("-Bold" if bold else "")
            self.fonts[px, bold] = (pygame.font.Font(face, px) if os.path.exists(face)
                                    else pygame.font.Font(None, int(px * 1.5)))
        return self.fonts[px, bold]

    def text(self, surface, s, pos, px=14, colour=T.INK, bold=False, centre=False, halo=None):
        font = self.font(px, bold)
        img = font.render(str(s), True, colour)
        r = img.get_rect(center=pos) if centre else img.get_rect(topleft=pos)
        if halo:
            ghost = font.render(str(s), True, halo)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                surface.blit(ghost, r.move(dx, dy))
        surface.blit(img, r)
        return r

    # ---- the ground ----------------------------------------------------------------------

    def load_base(self):
        """The base map with its relief (python -m mapgen base), or a plain one drawn here."""
        size = Layout(T.BASE_HEX).size(self.gmap.cols, self.gmap.rows)
        if os.path.exists(BASE):
            img = pygame.image.load(BASE)
            if img.get_size() == size:
                return img.convert() if pygame.display.get_surface() else img
        return self.plain_base(size)

    def plain_base(self, size):
        g, lay = self.gmap, Layout(T.BASE_HEX)
        img = pygame.Surface(size)
        img.fill(T.TERRAIN["~"])
        for c in range(g.cols):
            for r in range(g.rows):
                pygame.draw.polygon(img, T.TERRAIN[g.terrain[r][c]], lay.corners((c, r)))
                pygame.draw.polygon(img, T.GRID, lay.corners((c, r)), 1)
        for (a, b), kind in g.links.items():
            if a < b:
                pygame.draw.line(img, T.ROAD if kind == 2 else T.TRACK, lay.centre(a), lay.centre(b), 5 if kind == 2 else 2)
        for a, b in zip(g.rail, g.rail[1:]):
            pygame.draw.line(img, T.RAIL, lay.centre(a), lay.centre(b), 3)
        for hexside in g.cliffs:
            pygame.draw.line(img, T.SCARP, *lay.side_ends(hexside), 6)
        for name, p in sorted(g.places.items()):
            x, y = lay.centre(p["hex"])
            pygame.draw.circle(img, T.PLACE[p["kind"]], (x, y), 6)
            pygame.draw.circle(img, T.INK, (x, y), 6, 1)
            self.text(img, name, (x + 10, y - 9), 18, halo=T.PAPER)
        return img

    def background(self, size, ui):
        """The part of the base map in view, scaled to the zoom. Kept until the view changes."""
        key = (size, round(ui.cam[0], 1), round(ui.cam[1], 1), round(ui.zoom, 4))
        if self.back[0] != key:
            w, h = size
            src = pygame.Rect(int(ui.cam[0]), int(ui.cam[1]), int(w / ui.zoom) + 1, int(h / ui.zoom) + 1)
            src = src.clip(self.base.get_rect())
            img = pygame.Surface(size)
            img.fill(T.TERRAIN["~"])
            if src.w and src.h:
                part = pygame.transform.smoothscale(self.base.subsurface(src), (int(src.w * ui.zoom), int(src.h * ui.zoom)))
                img.blit(part, (0, 0))
            self.back = (key, img)
        return self.back[1]

    # ---- the map -------------------------------------------------------------------------

    def map(self, surface, session, ui):
        g, lay, view, z = session.gmap, ui.layout, session.view, ui.zoom
        w, h = surface.get_size()
        surface.blit(self.background((w, h), ui), (0, 0))
        ox, oy = int(ui.cam[0]) * z, int(ui.cam[1]) * z

        def at(hx):
            x, y = lay.centre(hx)
            return x - ox, y - oy

        def poly(hx):
            return [(x - ox, y - oy) for x, y in lay.corners(hx)]

        def shown(hx):
            x, y = at(hx)
            return -lay.hex_px < x < w + lay.hex_px and -lay.hex_px < y < h + lay.hex_px

        mine = [u for u in view["units"] if u["status"] == "on_map"]
        for key, (level, owner) in view["forts"].items():            # fortifications
            hx = tuple(int(v) for v in key.split(","))
            if shown(hx):
                cx, cy = at(hx)
                pts = [(cx + (x - cx) * 0.84, cy + (y - cy) * 0.84) for x, y in poly(hx)]
                pygame.draw.polygon(surface, T.INK if owner == session.side else T.SHORT, pts, max(1, int(level * z)))

        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        if "z" in ui.overlays:
            self.zones(veil, session, mine, shown, poly)
        if "s" in ui.overlays:
            for hx, cost in self.reach(session, mine).items():
                if shown(hx):
                    pygame.draw.polygon(veil, T.REACH_FULL if cost <= REACH_FULL else T.REACH, poly(hx))
        surface.blit(veil, (0, 0))
        if "s" in ui.overlays:
            self.hauls(surface, session, at, z)
        self.ways(surface, session, ui, at, z)

        stacks = {}
        for u in mine:
            stacks.setdefault(tuple(u["hex"]), []).append((u, True))
        for e in view["enemy"]:
            stacks.setdefault(tuple(e["hex"]), []).append((e, False))
        for hx in sorted(stacks):
            if shown(hx):
                pile = sorted(stacks[hx], key=lambda p: (p[0]["type"] != "hq", p[0]["id"] == ui.selected, p[0]["id"]))
                for n, (u, own) in enumerate(pile):
                    x, y = at(hx)
                    lift = (n - (len(pile) - 1) / 2) * lay.counter / 4
                    self.counter(surface, session, ui, u, own, (x + lift, y - lift), lay.counter)
        for e in view["events"]:                                     # where last turn's battles were
            if e["event"] == "battle" and shown(tuple(e["hex"])):
                x, y = at(tuple(e["hex"]))
                r = lay.hex_px * 0.46
                star = [(x + (r if k % 2 == 0 else r * 0.55) * pygame.math.Vector2(1, 0).rotate(k * 30).x,
                         y + (r if k % 2 == 0 else r * 0.55) * pygame.math.Vector2(1, 0).rotate(k * 30).y) for k in range(12)]
                pygame.draw.polygon(surface, T.ATTACK, star, max(2, int(3 * z)))
        if ui.hover and g.on_map(ui.hover):
            pygame.draw.polygon(surface, T.SELECT, poly(ui.hover), 2)
            self.tooltip(surface, session, ui, stacks.get(ui.hover, []))

    def stage(self, surface, session, ui, stage):
        """A moment of the last turn being played back (screen/replay.py)."""
        lay, z = ui.layout, ui.zoom
        w, h = surface.get_size()
        surface.blit(self.background((w, h), ui), (0, 0))
        ox, oy = int(ui.cam[0]) * z, int(ui.cam[1]) * z

        def at(where):
            if len(where) == 3:                                      # between two hexes
                (ax, ay), (bx, by), f = lay.centre(where[0]), lay.centre(where[1]), where[2]
                return ax + (bx - ax) * f - ox, ay + (by - ay) * f - oy
            x, y = lay.centre(where)
            return x - ox, y - oy

        if stage["ring"]:
            pts = [(x - ox, y - oy) for x, y in lay.corners(stage["ring"])]
            pygame.draw.polygon(surface, T.ATTACK, pts, max(3, int(5 * z)))
        if stage["line"]:                                            # who strikes whom
            a, b = at(stage["line"][0]), at(stage["line"][1])
            if a != b:
                pygame.draw.line(surface, T.INK, a, b, max(5, int(9 * z)))
                pygame.draw.line(surface, T.SELECT, a, b, max(3, int(5 * z)))
        glow = pygame.Surface((w, h), pygame.SRCALPHA)               # the light of the fire on the ground
        for _, _, _, where, _, _, lit, _ in stage["units"]:
            if lit in FLAME:
                pygame.draw.circle(glow, FLAME[lit][:3] + (70,), at(where), lay.hex_px * 1.1)
        surface.blit(glow, (0, 0))
        ticks = pygame.time.get_ticks()
        for i, u, own, where, scale, solid, lit, shaking in stage["units"]:
            x, y = at(where)
            if shaking:
                x += (ticks // 30 % 3 - 1) * 4 * z
                y += (ticks // 45 % 3 - 1) * 3 * z
            size = max(8, int(lay.counter * scale))
            pad = size + 16
            tile = pygame.Surface((pad, pad), pygame.SRCALPHA)
            self.counter(tile, session, ui, u, False, (pad / 2, pad / 2), size)
            face = pygame.Rect(8, 8, size, size)
            if lit in FLAME:                                         # burning: yellow, red, yellow...
                flame = pygame.Surface(face.size, pygame.SRCALPHA)   # laid over the counter, so its symbol shows
                flame.fill(FLAME[lit])
                tile.blit(flame, face.topleft)
                pygame.draw.rect(tile, FLAME["fire1" if lit == "fire0" else "fire0"][:3] + (255,), face, 4, border_radius=4)
            elif lit == "held":                                      # it stood its ground
                pygame.draw.rect(tile, T.GOOD + (255,), face, 4, border_radius=4)
            elif lit == "firing":                                    # the one striking stands out
                pygame.draw.rect(tile, (255, 255, 255, 255), face.inflate(8, 8), 4, border_radius=6)
                pygame.draw.rect(tile, T.SELECT + (255,), face, 4, border_radius=4)
            tile.set_alpha(int(255 * solid))
            surface.blit(tile, (x - pad / 2, y - pad / 2))
        for where, f in stage["bursts"]:                             # a unit destroyed: rings and sparks
            x, y = at(where)
            for k, colour in enumerate(((255, 230, 120), (255, 140, 40), (160, 40, 20))):
                r = lay.hex_px * (0.3 + 1.3 * f) * (1 - 0.22 * k)
                pygame.draw.circle(surface, colour, (x, y), max(2, r), max(2, int((1 - f) * 10 * z)))
            for k in range(10):
                v = pygame.math.Vector2(lay.hex_px * (0.4 + 1.6 * f), 0).rotate(k * 36 + 11)
                pygame.draw.circle(surface, (255, 220, 120), (x + v.x, y + v.y), max(1, int((1 - f) * 5 * z)))
        if stage["title"]:
            band = pygame.Surface((w, 44), pygame.SRCALPHA)
            band.fill((45, 38, 30, 190))
            surface.blit(band, (0, 0))
            self.text(surface, stage["title"].upper(), (w // 2, 22), 22, T.SELECT, True, True)
        if stage["meter"]:                                           # the rattle seen: one block for each beat of it
            share, live = stage["meter"]
            blocks, lit_n = 40, int(share * 40 + 0.999)
            bw = min(18, (w - 80) // blocks)
            x0 = (w - bw * blocks) // 2
            for k in range(blocks):
                colour = (FLAME["fire0"][:3] if k % 2 == 0 else FLAME["fire1"][:3]) if k < lit_n else (70, 62, 50)
                pygame.draw.rect(surface, colour, (x0 + k * bw, 50, bw - 3, 12 if k < lit_n and live else 8))

    def zones(self, veil, session, mine, shown, poly):
        """Z: what your units see, your zone of control and the enemy's as you know it."""
        g, extra = session.gmap, session.state["sides"][session.side]["recon"]
        own, foe = set(), set()
        for units, zone in ((mine, own), (session.view["enemy"], foe)):
            for u in units:
                if u["type"] != "hq":
                    zone |= {n for _, n, hexside in g.around(tuple(u["hex"])) if hexside not in g.cliffs}
        eyes = [(tuple(u["hex"]), (SPOT_RANGE_RECON if u["type"] == "recon" else SPOT_RANGE) + extra) for u in mine]
        key = (tuple(eyes), tuple(sorted(own)), tuple(sorted(foe)))
        if self.zone_cache[0] != key:                                # worked out once for a position
            tint = {}
            for c in range(g.cols):
                for r in range(g.rows):
                    hx = (c, r)
                    if g.passable(hx):
                        seen = any(distance(hx, e) <= far for e, far in eyes)
                        colour = T.ZOC_FOE if hx in foe else T.ZOC_OWN if hx in own else None if seen else T.UNSEEN
                        if colour:
                            tint[hx] = colour
            self.zone_cache = (key, tint)
        for hx, colour in self.zone_cache[1].items():
            if shown(hx):
                pygame.draw.polygon(veil, colour, poly(hx))

    def reach(self, session, mine):
        """S: the ground your HQs and ports can supply, as far as you know the enemy's positions."""
        g, view = session.gmap, session.view
        blocked = frozenset(tuple(e["hex"]) for e in view["enemy"])
        depots = sorted([tuple(u["hex"]) for u in mine if u["type"] == "hq"]
                        + [g.places[name]["hex"] for name in view["ports"]])
        key = (tuple(depots), blocked)
        if self.reach_cache[0] != key:
            best = {}
            for d in depots:
                for hx, cost in paths.haul_distances(g, d, blocked, REACH).items():
                    best[hx] = min(cost, best.get(hx, 99))
            self.reach_cache = (key, best)
        return self.reach_cache[1]

    def hauls(self, surface, session, at, z):
        """S: this turn's hauls, the line as thick as the tonnes that arrived (RULES 14.6)."""
        for e in session.view["events"]:
            if e["event"] != "haul":
                continue
            tonnes = e["fuel"] + e["stores"]
            pts = [at(tuple(h)) for h in e["route"]]
            if len(pts) > 1:
                pygame.draw.lines(surface, T.SUPPLY, False, pts, max(2, int(min(14, 2 + tonnes // 150) * z)))
            x, y = pts[-1]
            self.text(surface, f"{tonnes} t", (x, y - 42 * z), 13 * max(z, 0.8), T.SUPPLY, True, True, T.PAPER)
        for name, port in session.view["ports"].items():
            x, y = at(session.gmap.places[name]["hex"])
            self.text(surface, f"fuel {port['fuel']} t  stores {port['stores']} t", (x, y - 44 * z),
                      12 * max(z, 0.8), T.SUPPLY, True, True, T.PAPER)

    def ways(self, surface, session, ui, at, z):
        """The paths of the orders given, and of the one being chosen."""
        def draw(u, order, colour):
            p = session.preview(u["id"], order["order"], order["to"]) if "to" in order else None
            if p:
                pts = [at(tuple(u["hex"]))] + [at(h) for h in p["path"]]
                if len(pts) > p["reach"] + 1:
                    pygame.draw.lines(surface, T.PATH_FAR, False, pts[p["reach"]:], max(1, int(2 * z)))
                if p["reach"]:
                    pygame.draw.lines(surface, colour, False, pts[:p["reach"] + 1], max(2, int(5 * z)))
                    pygame.draw.circle(surface, colour, pts[p["reach"]], max(4, int(8 * z)))
                pygame.draw.circle(surface, colour, pts[-1], max(5, int(10 * z)), max(2, int(3 * z)))
            return p
        for uid, order in sorted(session.pending[session.side].items()):
            u = session.unit(uid)
            if u:
                draw(u, order, T.ATTACK if order["order"] == "attack" else T.PATH)
        u = session.unit(ui.selected)
        if u and ui.hover and ui.hover != tuple(u["hex"]) and not ui.cover:
            name = ui.mode or guess(session, ui.hover)
            p = draw(u, {"order": name, "to": ui.hover}, T.SELECT) if name else None
            if p:
                when = "this turn" if p["reach"] == len(p["path"]) else f"{p['reach']} of {len(p['path'])} hexes this turn"
                short = "" if p["enough_fuel"] else "   NOT ENOUGH FUEL"
                ui.message = f"{T.ORDER_NAME[name]} here: {when}, {p['fuel']} t of fuel.{short}   Click to order."

    # ---- a counter -----------------------------------------------------------------------

    def sprite(self, nation, kind, size):
        """A counter picture from art/counters, if there is one (docs/COUNTERS.md)."""
        key = (nation, kind, size)
        if key not in self.sprites:
            path = os.path.join(ART, f"{nation}_{kind}.png")
            self.sprites[key] = (pygame.transform.smoothscale(pygame.image.load(path), size)
                                 if os.path.exists(path) else None)
        return self.sprites[key]

    def counter(self, surface, session, ui, u, own, centre, size):
        nation = session.nation[u["id"]]
        x, y = int(centre[0] - size / 2), int(centre[1] - size / 2)
        face = pygame.Rect(x, y, size, size)
        chosen = u["id"] == ui.selected
        pygame.draw.rect(surface, (30, 26, 20), face.move(2, 2), border_radius=4)             # a little shadow
        pygame.draw.rect(surface, T.FACE[nation], face, border_radius=4)
        pygame.draw.rect(surface, T.SELECT if chosen else T.INK, face, 3 if chosen else 1, border_radius=4)
        big = size >= 34
        box = pygame.Rect(x + size * 0.17, y + size * (0.1 if big else 0.2), size * 0.66, size * (0.42 if big else 0.6))
        art = self.sprite(nation, u["type"], (int(size * 0.9), int(size * 0.54)))
        if art:
            surface.blit(art, (x + size * 0.05, y + size * 0.03))
        else:
            self.symbol(surface, u["type"], box, T.BOX[nation], 2 if size >= 30 else 1)
        if big:
            self.text(surface, u.get("steps", "?"), (x + size * 0.5, y + size * 0.7), size * 0.27, bold=True, centre=True)
        if not own:
            return
        if big:                                                      # stores and cohesion, side by side
            half = (size - 12) // 2
            for n, (share, colour) in enumerate(((u["stores"] / U.stores_cap(u), T.STORES),
                                                 (u["cohesion"] / 100, T.GOOD if u["cohesion"] >= 40 else T.POOR))):
                bx = x + 4 + n * (half + 4)
                pygame.draw.rect(surface, T.PAPER, (bx, y + size - 7, half, 4))
                pygame.draw.rect(surface, colour, (bx, y + size - 7, int(half * share), 4))
        order = session.order_of(u["id"])["order"]
        if order != "hold" and size >= 22:
            tag = pygame.Rect(x + size - size * 0.3, y - size * 0.08, size * 0.38, size * 0.34)
            pygame.draw.rect(surface, T.ATTACK if order == "attack" else T.PATH, tag, border_radius=3)
            self.text(surface, T.ORDER_KEY[order], tag.center, size * 0.24, T.PAPER, True, True)
        short = (not u["traced"]) or u["out_of_stores"] or (U.is_vehicle(u) and u["fuel"] < U.step_fuel(u))
        if short:
            pygame.draw.rect(surface, T.SHORT, face.inflate(6, 6), 3, border_radius=6)

    def symbol(self, surface, kind, box, fill, width):
        """A NATO-style symbol: armour an oval, infantry a cross, motorised a cross on wheels,
        guns a dot, reconnaissance a slash, an HQ a flag."""
        pygame.draw.rect(surface, fill, box)
        pygame.draw.rect(surface, T.INK, box, width)
        if kind == "armour":
            pygame.draw.ellipse(surface, T.INK, box.inflate(-box.w * 0.3, -box.h * 0.4), width)
        elif kind in ("foot", "motorised"):
            pygame.draw.line(surface, T.INK, box.topleft, box.bottomright, width)
            pygame.draw.line(surface, T.INK, box.bottomleft, box.topright, width)
            if kind == "motorised":
                for dx in (0.3, 0.7):
                    pygame.draw.circle(surface, T.INK, (box.x + box.w * dx, box.bottom + max(2, box.h // 6)), max(2, box.h // 7))
        elif kind == "guns":
            pygame.draw.circle(surface, T.INK, box.center, max(2, box.h // 4))
        elif kind == "recon":
            pygame.draw.line(surface, T.INK, box.bottomleft, box.topright, width)
        else:
            pygame.draw.rect(surface, T.INK, (box.x, box.y, box.w // 2, box.h // 2))

    def tooltip(self, surface, session, ui, pile):
        """What is under the mouse, in plain words."""
        g, hx, view = session.gmap, ui.hover, session.view
        lines = []
        for name, p in sorted(g.places.items()):
            if p["hex"] == hx:
                lines.append((f"{name}  ({T.SIDE_NAME[view['places'][name]]})", True))
        for u, own in pile:
            what = f"{u['name']}: {u['type']}, strength {u.get('steps', '?')}"
            lines.append((what if own else "Enemy  " + what, False))
        fort = view["forts"].get(f"{hx[0]},{hx[1]}")
        lines.append((T.TERRAIN_NAME[g.terrain[hx[1]][hx[0]]] + (f", fortified level {fort[0]}" if fort else ""), False))
        font = self.font(13)
        w = max(self.font(13, bold).size(s)[0] for s, bold in lines) + 14
        h = len(lines) * (font.get_height() + 2) + 8
        x = min(ui.mouse[0] + 18, surface.get_width() - w - 4)
        y = min(ui.mouse[1] + 18, surface.get_height() - h - 4)
        tip = pygame.Surface((w, h), pygame.SRCALPHA)
        tip.fill((250, 244, 228, 235))
        pygame.draw.rect(tip, T.INK, tip.get_rect(), 1)
        for n, (s, bold) in enumerate(lines):
            self.text(tip, s, (7, 4 + n * (font.get_height() + 2)), 13, bold=bold)
        surface.blit(tip, (x, y))

    # ---- the order bar -------------------------------------------------------------------

    def bar(self, surface, session, ui, rect):
        pygame.draw.rect(surface, T.INK, rect)
        self.text(surface, ui.message, (rect.x + 10, rect.y + 6), 15, T.PAPER)
        u = session.unit(ui.selected)
        order = session.pending[session.side].get(u["id"], {}).get("order") if u else None
        for name, r in buttons(surface.get_size()).items():
            label, key = next((b[1], b[2]) for b in T.BUTTONS if b[0] == name)
            lit = name == ui.mode or name in ui.overlays or (ui.mode is None and name == order)
            usable = name in ("s", "z", "done") or u is not None
            colour = T.BUTTON_GO if name == "done" else T.BUTTON_ON if lit else T.BUTTON
            pygame.draw.rect(surface, colour if usable else (150, 142, 124), r, border_radius=6)
            self.text(surface, label, (r.centerx, r.centery - 7), 15, T.INK if usable else T.DIM, True, True)
            self.text(surface, key, (r.centerx, r.centery + 12), 11, T.DIM if usable else (120, 112, 98), centre=True)

    # ---- the panel -----------------------------------------------------------------------

    def panel(self, surface, session, ui, rect):
        pygame.draw.rect(surface, T.PAPER, rect)
        pygame.draw.line(surface, T.INK, rect.topleft, rect.bottomleft, 2)
        view, over = session.view, session.state["over"]
        x, y, w = rect.x + 16, rect.y + 12, rect.w - 32

        def line(s="", px=14, colour=T.INK, bold=False, gap=4):
            nonlocal y
            self.text(surface, s, (x, y), px, colour, bold)
            y += self.font(px, bold).get_height() + gap

        def meter(label, value, top, colour, words):
            nonlocal y
            self.text(surface, label, (x, y), 13, T.DIM)
            self.text(surface, words, (x + w - self.font(13).size(words)[0], y), 13)
            y += 18
            pygame.draw.rect(surface, (214, 204, 178), (x, y, w, 9), border_radius=4)
            if top:
                pygame.draw.rect(surface, colour, (x, y, int(w * min(1, value / top)), 9), border_radius=4)
            y += 17

        line(session.scenario["name"], 22, bold=True)
        line(f"{session.day:%d %B %Y}   turn {min(view['turn'], session.scenario['turns'])} of {session.scenario['turns']}", 14, T.DIM)
        banner = pygame.Rect(x, y + 2, w, 30)
        pygame.draw.rect(surface, T.SIDE[session.side], banner, border_radius=6)
        self.text(surface, "Last turn: any key skips" if self.playing else "The game is over" if over
                  else f"{T.SIDE_NAME[session.side]}: give your orders", banner.center, 15, T.PAPER, True, True)
        y += 42
        line(f"Points   Axis {view['vp']['axis']}    Commonwealth {view['vp']['cw']}", 14)
        if over:
            r = session.state["result"]
            line("A draw" if r["winner"] is None else f"{T.SIDE_NAME[r['winner']]}: {r['grade']} victory", 18, T.SHORT, True)
        y += 8
        pygame.draw.line(surface, T.GRID, (x, y), (x + w, y), 2)
        y += 10

        u = None if self.playing else session.unit(ui.selected)
        if u:
            order = session.order_of(u["id"])
            line(u["name"], 19, bold=True)
            line(f"{u['type'].capitalize()}, {u['xp']}.  Moves {ALLOWANCE[u['type']] // 4} hexes of desert a turn.", 12, T.DIM, gap=8)
            meter("Strength", u["steps"], u["max"], T.INK, f"{u['steps']} of {u['max']}")
            meter("Cohesion", u["cohesion"], 100, T.GOOD if u["cohesion"] >= 40 else T.POOR,
                  "fresh" if u["cohesion"] >= 80 else "tired" if u["cohesion"] >= 40 else "cannot attack")
            if U.is_vehicle(u):
                meter("Fuel", u["fuel"], U.fuel_cap(u), T.FUEL, "enough for " + T.count(u["fuel"] // U.step_fuel(u), "hex", "hexes"))
            meter("Stores", u["stores"], U.stores_cap(u), T.STORES, f"{u['stores']} t")
            if u["type"] == "hq":
                line(f"Dump: {u['dump']['fuel']} t fuel, {u['dump']['stores']} t stores", 13)
            if not u["traced"]:
                line("OUT OF SUPPLY: no HQ or port in reach", 13, T.SHORT, True)
            elif u["out_of_stores"]:
                line("OUT OF STORES: losing cohesion", 13, T.SHORT, True)
            else:
                line("In supply", 13, T.GOOD, True)
            y += 4
            if u["id"] in session.pending[session.side]:
                turns = session.turns_to_go(u["id"])
                line(f"Order: {T.ORDER_NAME[order['order']]}", 16, T.PATH, True)
                line(T.ORDER_HELP[order["order"]], 12, T.DIM, gap=2)
                line(f"It stands until done{f': about {turns} turns' if turns and turns > 1 else ''}.", 12, T.DIM, gap=8)
            else:
                line("Waiting for an order", 16, T.ATTACK, True)
                line("With none, it holds its ground.", 12, T.DIM, gap=8)
            for s in ("Click a hex to move there.", "Click an enemy to attack it.",
                      "Keys: M, A or R, arrows, then Enter.", "Space: next unit.  Right-click: let go."):
                line(s, 12, T.DIM, gap=2)
        elif not over and not self.playing:
            mine = [m for m in view["units"] if m["status"] == "on_map"]
            line("What to do", 17, bold=True)
            for s in ("1. Click one of your units.", "2. Click where it should go,", "    or an enemy to attack.",
                      "3. Press End turn.", "An order stands until it is done.", "Units with no order hold their ground."):
                line(s, 13, gap=3)
            y += 6
            waiting = len(session.waiting_units())
            line(f"{waiting} of {T.count(len(mine), 'unit')} {'waits' if waiting == 1 else 'wait'} for orders." if waiting
                 else "All units have orders.", 13, T.PATH, True)
            short = [m for m in mine if not m["traced"] or m["out_of_stores"]]
            if short:
                y += 6
                line("Short of supply (press S):", 13, T.SHORT, True)
                for m in short[:6]:
                    line("  " + m["name"], 12, T.SHORT, gap=2)
        y += 10
        pygame.draw.line(surface, T.GRID, (x, y), (x + w, y), 2)
        y += 8
        events = [e for e in view["events"] if e["event"] not in ("haul", "step")]
        room = (rect.bottom - y) // 17 - 2
        font = self.font(12)
        if self.playing:                                             # nothing is given away before it is seen
            for s in ("Watch and listen.", "", "Each formation strikes in turn.", "The units it hits burn.",
                      "The longer the rattle,", "the harder the blow.", "", "Tanks and infantry rattle.",
                      "Guns sweep upwards.", "", "When all have struck, see who", "falls back and who holds."):
                line(s, 13, T.DIM if s != "Watch and listen." else T.INK, s == "Watch and listen.", 3)
        elif events and room > 0:
            line("Last turn", 14, bold=True)
            told = [row for e in events for row in wrap(font, describe(e, session), w)]
            for row in told[-room:]:
                line(row, 12, gap=2)

    def frame(self, surface, session, ui, stage=None):
        a = areas(surface.get_size())
        self.playing = stage is not None
        if stage:
            self.stage(surface.subsurface(a["map"]), session, ui, stage)
        elif ui.cover:
            pygame.draw.rect(surface, T.INK, a["map"])
            self.text(surface, ui.cover, a["map"].center, 26, T.PAPER, True, True)
        else:
            self.map(surface.subsurface(a["map"]), session, ui)
        self.bar(surface, session, ui, a["bar"])
        self.panel(surface, session, ui, a["panel"])


def guess(session, hx):
    """The order a plain click on this hex gives: attack a seen enemy, otherwise move."""
    if not session.gmap.passable(hx):
        return None
    return "attack" if any(tuple(e["hex"]) == hx for e in session.view["enemy"]) else "move"


def wrap(font, text, width):
    """The text as lines no wider than width, broken between words; later lines are indented."""
    lines, row = [], ""
    for word in text.split():
        trial = f"{row} {word}" if row else word
        if row and font.size(trial)[0] > width:
            lines.append(row)
            row = "   " + word
        else:
            row = trial
    return lines + [row] if row else lines


def whereabouts(gmap, h):
    """A hex in words: "at Tobruk", or "near Sidi Rezegh" for the nearest named place."""
    name, p = min(gmap.places.items(), key=lambda kv: (distance(tuple(h), kv[1]["hex"]), kv[0]))
    return f"at {name}" if p["hex"] == tuple(h) else f"near {name}"


def describe(e, session):
    """An event in a few words."""
    names = {u["id"]: u["name"] for u in session.scenario["units"]}
    who = names.get(e.get("unit"), "")
    kind = e["event"]
    if kind == "battle":
        lost = sum(e["lost"].values())
        return (f"Battle {whereabouts(session.gmap, e['hex'])}: {T.count(lost, 'step')} lost"
                + (", defender retreats" if e["retreated"] else ""))
    if kind == "stopped":
        return f"{who} stopped: {e['why']}"
    if kind == "destroyed":
        return f"{who} {e['cause']}"
    if kind == "no attack":
        return f"{who} did not attack"
    return f"{who} {kind}"
