"""Paints a frame: the base map scaled to the zoom, the counters and overlays on it, the order
bar under it and the panel beside it."""
import math
import os

import pygame

from engine import paths
from engine import units as U
from mapgen import geo
from mapgen import hexgrid as H
from engine.gamemap import distance
from engine.movement import ALLOWANCE
from engine.supply import REACH, REACH_FULL
from engine.view import SPOT_RANGE, SPOT_RANGE_RECON

from . import theme as T
from .layout import EDGE, Layout, areas, buttons, layers
from .pictures import picture

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
        self.mouse = (-1, -1)           # where the mouse is in the window; off it until it moves
        self.message = ""
        self.cover = None               # text shown instead of the map between two players
        self.symbols = "pictures"       # what a counter shows: "pictures", or "nato" for NATO-style symbols
        self.alone = False              # the unit taken up is one of a group, to be ordered by itself
        self.chooser = None             # a hex with several of your units in it, and which: a list to choose from
        self.layers_open = False        # the Layers list in the map's corner is showing
        self.editing = None             # the name being typed for the group taken up, or None

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
        self.member_rects = {}          # the rows of a group's units in the panel, to click
        self.chooser_rects, self.report_rects, self.back_rect, self.tips = {}, {}, None, []
        self.pencil_rect = None

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
        """The part of the base map in view, scaled to the zoom, on paper, with the map's neat
        border where its edge shows. Kept until the view changes."""
        key = (size, round(ui.cam[0], 1), round(ui.cam[1], 1), round(ui.zoom, 4))
        if self.back[0] != key:
            w, h = size
            z, cx, cy = ui.zoom, int(ui.cam[0]), int(ui.cam[1])
            src = pygame.Rect(cx, cy, int(w / z) + 1, int(h / z) + 1).clip(self.base.get_rect())
            img = pygame.Surface(size)
            img.fill(T.PAPER)
            if src.w and src.h:
                part = pygame.transform.smoothscale(self.base.subsurface(src), (int(src.w * z), int(src.h * z)))
                img.blit(part, ((src.x - cx) * z, (src.y - cy) * z))
            self.border(img, cx, cy, z)
            self.back = (key, img)
        return self.back[1]

    def border(self, img, cx, cy, z):
        """The neat line round the map with the degrees marked, as on a map of the period."""
        bw, bh = self.base.get_size()
        edge = pygame.Rect(-cx * z, -cy * z, bw * z, bh * z)
        gap = 9 * z
        pygame.draw.rect(img, T.INK, edge, max(1, int(1.5 * z)))
        pygame.draw.rect(img, T.INK, edge.inflate(2 * gap, 2 * gap), max(2, int(4 * z)))
        px = T.BASE_HEX / (2 * H.SIZE)                             # base-map pixels to the kilometre
        size = max(9, int(12 * z))
        for lon in range(int(geo.LON_W) + 1, int(geo.LON_E) + 1):
            x = edge.x + geo.to_km(lon, geo.LAT_N)[0] * px * z
            for y0, y1, ty in ((edge.y - gap, edge.y + 6 * z, edge.y - gap - size), (edge.bottom - 6 * z, edge.bottom + gap, edge.bottom + gap + size)):
                pygame.draw.line(img, T.INK, (x, y0), (x, y1), max(1, int(1.5 * z)))
                self.text(img, f"{lon}°E", (x, ty), size, T.INK, centre=True)
        for lat in range(int(geo.LAT_S) + 1, int(geo.LAT_N) + 1):
            y = edge.y + geo.to_km(geo.LON_W, lat)[1] * px * z
            for x0, x1, tx in ((edge.x - gap, edge.x + 6 * z, edge.x - gap - size * 1.4), (edge.right - 6 * z, edge.right + gap, edge.right + gap + size * 1.4)):
                pygame.draw.line(img, T.INK, (x0, y), (x1, y), max(1, int(1.5 * z)))
                self.text(img, f"{lat}°N", (tx, y), size, T.INK, centre=True)

    def key(self, surface):
        """The key to the map and the counters, in the map's bottom right corner."""
        rows = (("road", "Coast road"), ("track", "Desert track"), ("rail", "Railway"), ("scarp", "Escarpment: vehicles cross at a pass"),
                ("lane", "Sea lane"), ("fort", "Fortified hex"), ("port", "Port"), ("town", "Town"), ("site", "Other place"),
                ("battle", "Where a battle was fought last turn"),
                ("armour", "Tanks"), ("motorised", "Motorised infantry"), ("foot", "Infantry on foot"), ("guns", "Guns"),
                ("recon", "Armoured cars"), ("hq", "Headquarters"), ("fuel", "Out of fuel"), ("trouble", "In trouble: supply or morale"))
        w, h = surface.get_size()
        box = pygame.Rect(w - 300, h - len(rows) * 21 - 44, 288, len(rows) * 21 + 34)
        pygame.draw.rect(surface, T.PAPER, box, border_radius=6)
        pygame.draw.rect(surface, T.INK, box, 2, border_radius=6)
        self.text(surface, "Key", (box.x + 10, box.y + 6), 14, bold=True)
        for n, (what, words) in enumerate(rows):
            y = box.y + 30 + n * 21
            a, b, mid = (box.x + 12, y + 8), (box.x + 48, y + 8), (box.x + 30, y + 8)
            if what == "road":
                pygame.draw.line(surface, T.ROAD, a, b, 4)
            elif what == "track":
                broken(surface, T.TRACK, [a, b], 3, 8, 5)
            elif what == "rail":
                pygame.draw.line(surface, T.RAIL, a, b, 2)
                for k in range(4):
                    pygame.draw.line(surface, T.RAIL, (a[0] + 6 + k * 9, y + 4), (a[0] + 6 + k * 9, y + 12), 1)
            elif what == "scarp":
                pygame.draw.line(surface, T.SCARP, a, b, 4)
                for k in range(5):
                    pygame.draw.line(surface, T.SCARP, (a[0] + 3 + k * 8, y + 8), (a[0] + 3 + k * 8, y + 13), 1)
            elif what == "lane":
                broken(surface, (84, 124, 156), [a, b], 2, 6, 5)
            elif what == "fort":
                pygame.draw.polygon(surface, T.INK, [(mid[0] + 9 * math.cos(math.radians(60 * k)), mid[1] + 9 * math.sin(math.radians(60 * k))) for k in range(6)], 2)
            elif what in T.PLACE:
                pygame.draw.circle(surface, T.PLACE[what], mid, 6)
                pygame.draw.circle(surface, T.INK, mid, 6, 1)
            elif what in ("fuel", "trouble"):
                self.badge(surface, what, mid, 8)
            elif what == "battle":
                pygame.draw.polygon(surface, T.ATTACK, star(mid[0], mid[1], 9), 2)
            else:
                mini = pygame.Rect(box.x + 14, y, 32, 18)
                pygame.draw.rect(surface, T.FACE["cw"], mini, border_radius=3)
                picture(surface, what, mini.inflate(-6, -4), T.MARK["cw"], T.FACE["cw"])
            self.text(surface, words, (box.x + 58, y + 1), 12)

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
                pile = sorted(stacks[hx], key=lambda p: (T.ARM.index(p[0]["type"]), p[0]["id"]))
                taken = [p for p in pile if p[1] and ui.selected in (p[0]["id"], session.leader(p[0]["id"]))]
                u, own = (taken or pile)[0]                          # one counter for the pile: the unit taken up, or its chief arm
                x, y = at(hx)
                size, nation = lay.counter, session.nation[u["id"]]
                for k in range(min(len(pile), 3) - 1, 0, -1):        # the edges of the units beneath it, close in
                    edge = pygame.Rect(x - size / 2 + k * size * 0.055, y - size / 2 - k * size * 0.055, size, size)
                    pygame.draw.rect(surface, T.FACE[nation], edge, border_radius=4)
                    pygame.draw.rect(surface, T.INK, edge, 1, border_radius=4)
                if taken:                                            # the unit taken up floats above the map
                    size, y = int(size * 1.14), y - size * 0.07
                self.counter(surface, session, ui, u, own, (x, y), size, bool(taken), len(pile),
                             [p[0] for p in pile if p[1]], any(p[0]["type"] == "hq" for p in pile))
        if "s" in ui.overlays:
            self.callouts(surface, session, ui, at, z, shown)
        for e in view["events"]:                                     # where last turn's battles were
            if e["event"] == "battle" and shown(tuple(e["hex"])):
                x, y = at(tuple(e["hex"]))
                pygame.draw.polygon(surface, T.ATTACK, star(x, y, lay.hex_px * 0.46), max(2, int(3 * z)))
        self.chooser_rects = {}
        if ui.chooser:                                               # which of the units here?
            x, y = at(ui.chooser["hex"])
            rows = [(uid, session.unit(uid)) for uid in ui.chooser["ids"] if session.unit(uid)]
            acts = [(("group",), "Group all here into one")] if len(rows) > 1 else []        # and what can be done with them
            acts += [(("split", uid), "Split up " + session.group_name(uid)) for uid, u in rows if len(session.members(uid)) > 1]
            wide = max([self.font(13, True).size(row_name(session, u))[0] + 80 for _, u in rows]
                       + [self.font(13).size(words)[0] + 30 for _, words in acts])
            high = len(rows) * 28 + len(acts) * 26 + 30
            box = pygame.Rect(min(x + lay.counter * 0.6, w - wide - 6), max(4, min(y - 14, h - high - 8)), wide, high)
            pygame.draw.rect(surface, T.PAPER, box, border_radius=6)
            pygame.draw.rect(surface, T.INK, box, 2, border_radius=6)
            self.text(surface, "Which one?" if len(rows) > 1 else "Orders for the stack", (box.x + 8, box.y + 5), 12, T.DIM)
            for n, (what, words) in enumerate(acts):
                row = pygame.Rect(box.x + 4, box.y + 24 + len(rows) * 28 + n * 26, box.w - 8, 24)
                pygame.draw.rect(surface, T.BUTTON_ON if row.collidepoint(ui.mouse) else T.BUTTON, row, border_radius=4)
                pygame.draw.rect(surface, T.INK, row, 1, border_radius=4)
                self.text(surface, words, (row.x + 10, row.y + 4), 13)
                self.chooser_rects[what] = row
            for n, (uid, u) in enumerate(rows):
                row = pygame.Rect(box.x + 4, box.y + 22 + n * 28, box.w - 8, 26)
                if row.collidepoint(ui.mouse):
                    pygame.draw.rect(surface, T.BUTTON_ON, row, border_radius=4)
                mini = pygame.Rect(row.x + 4, row.y + 3, 32, 20)
                pygame.draw.rect(surface, T.FACE[session.nation[uid]], mini, border_radius=3)
                show = next((m for m in session.members(uid) if m["type"] != "hq"), u)
                picture(surface, show["type"], mini.inflate(-6, -5), T.MARK[session.nation[uid]], T.FACE[session.nation[uid]])
                self.text(surface, row_name(session, u), (row.x + 42, row.y + 5), 13, bold=True)
                self.badge(surface, problem(session.members(uid)), (row.right - 14, row.centery), 9)
                self.chooser_rects[uid] = row
        elif ui.hover and g.on_map(ui.hover):
            pygame.draw.polygon(surface, T.SELECT, poly(ui.hover), 2)
            self.tooltip(surface, session, ui, stacks.get(ui.hover, []))
        if "k" in ui.overlays:
            self.key(surface)
        for name, r in layers((w + T.PANEL, h + T.BAR), ui.layers_open).items():      # the Layers button, in the corner
            label = "Layers" if name == "layers" else next(b[1] for b in T.LAYERS if b[0] == name)
            on = ui.layers_open if name == "layers" else name in ui.overlays
            pygame.draw.rect(surface, T.BUTTON_ON if on and name != "layers" else T.PAPER, r, border_radius=6)
            pygame.draw.rect(surface, T.INK, r, 2, border_radius=6)
            if name == "layers":                                     # three sheets, one on another
                for k in range(3):
                    cx, cy = r.x + 18, r.centery - 5 + k * 5
                    pygame.draw.polygon(surface, T.INK, [(cx - 9, cy), (cx, cy - 4), (cx + 9, cy), (cx, cy + 4)], 2)
                self.text(surface, label, (r.x + 34, r.y + 8), 14, bold=True)
            else:
                pygame.draw.rect(surface, T.INK, (r.x + 9, r.y + 8, 16, 16), 2, border_radius=3)
                if on:
                    pygame.draw.lines(surface, T.INK, False, [(r.x + 12, r.y + 16), (r.x + 16, r.y + 21), (r.x + 23, r.y + 10)], 3)
                self.text(surface, label, (r.x + 34, r.y + 7), 14, bold=True)

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
        for where, f, kind in stage["bursts"]:                       # a unit destroyed: rings and sparks
            x, y = at(where)
            if kind == "flag":                                       # a unit surrendering: a white flag goes up
                top = y - lay.hex_px * (0.3 + 0.7 * min(1.0, f * 2))
                pygame.draw.line(surface, T.INK, (x, y), (x, top), max(2, int(4 * z)))
                cloth = pygame.Rect(x, top, lay.hex_px * 0.55, lay.hex_px * 0.36)
                pygame.draw.rect(surface, (255, 255, 255), cloth)
                pygame.draw.rect(surface, T.INK, cloth, max(1, int(2 * z)))
                continue
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
            if e["event"] == "haul":
                pts = [at(tuple(h)) for h in e["route"]]
                if len(pts) > 1:
                    wide = max(2, int(min(14, 2 + (e["fuel"] + e["stores"]) // 150) * z))
                    pygame.draw.lines(surface, T.INK, False, pts, wide + 2)
                    pygame.draw.lines(surface, T.HAUL, False, pts, wide)

    def callouts(self, surface, session, ui, at, z, shown):
        """S: the figures, each in a box of its own on a short leader, clear of the counters:
        what each port holds, and what the HQ taken up or pointed at was hauled this turn."""
        g, view = session.gmap, session.view
        notes = []
        for name, port in sorted(view["ports"].items()):
            if shown(g.places[name]["hex"]):
                notes.append((g.places[name]["hex"], (-1, -1), [f"{name} port", f"fuel {port['fuel']:,} t   stores {port['stores']:,} t"]))
        got = {}
        for e in view["events"]:
            if e["event"] == "haul":
                got[e["hq"]] = got.get(e["hq"], 0) + e["fuel"] + e["stores"]
        asked = {session.leader(ui.selected)} if session.unit(ui.selected) else set()
        for uid, tonnes in sorted(got.items()):
            u = session.unit(uid)
            if u and shown(tuple(u["hex"])) and (session.leader(uid) in asked or tuple(u["hex"]) == ui.hover):
                notes.append((tuple(u["hex"]), (1, 1), [u["name"][:26], f"hauled {tonnes:,} t this turn"]))
        font = self.font(12)
        for hx, (dx, dy), rows in notes:
            x, y = at(hx)
            wide = max(self.font(12, n == 0).size(r)[0] for n, r in enumerate(rows)) + 14
            high = len(rows) * (font.get_height() + 2) + 8
            reach = 46 * max(z, 0.7)
            box = pygame.Rect(0, 0, wide, high)
            box.center = (x + dx * (reach + wide / 2), y + dy * (reach * 0.8 + high / 2))
            box.clamp_ip(surface.get_rect().inflate(-8, -8))
            pygame.draw.line(surface, T.INK, (x, y), box.center, 2)
            pygame.draw.circle(surface, T.INK, (x, y), 3)
            pygame.draw.rect(surface, (250, 244, 228), box, border_radius=5)
            pygame.draw.rect(surface, T.SUPPLY, box, 2, border_radius=5)
            for n, r in enumerate(rows):
                self.text(surface, r, (box.x + 7, box.y + 4 + n * (font.get_height() + 2)), 12, T.INK if n else T.SUPPLY, n == 0)

    def ways(self, surface, session, ui, at, z):
        """The paths of the orders given, and of the one being chosen."""
        def draw(u, order, colour):
            p = session.preview(u["id"], order["order"], order["to"]) if "to" in order else None
            if p:
                pts = [at(tuple(u["hex"]))] + [at(h) for h in p["path"]]
                a, b = p["reach"], 2 * p["reach"]                    # this turn, the next, and beyond
                wide = max(2, int(5 * z))
                for ink, more in ((T.INK, 3), (colour, 0)):          # dark under bright, to show on sand
                    if a:
                        pygame.draw.lines(surface, ink, False, pts[:a + 1], wide + more)
                        pygame.draw.circle(surface, ink, pts[a], max(4, int(8 * z)) + more // 2)
                        broken(surface, ink, pts[a:b + 1], wide + more, 14 * z, 10 * z)          # dashes
                        broken(surface, ink, pts[b:], wide + more, 4 * z, 10 * z)                # dots
                    else:
                        broken(surface, ink, pts, wide + more, 4 * z, 10 * z)
                dry = p["range"]
                if dry is not None and dry < len(p["path"]):         # where its fuel gives out
                    x, y = pts[dry]
                    r = max(5, int(9 * z))
                    pygame.draw.line(surface, T.SHORT, (x - r, y - r), (x + r, y + r), max(2, int(4 * z)))
                    pygame.draw.line(surface, T.SHORT, (x - r, y + r), (x + r, y - r), max(2, int(4 * z)))
                pygame.draw.circle(surface, colour, pts[-1], max(5, int(10 * z)), max(2, int(3 * z)))
            return p
        for uid, order in sorted(session.pending[session.side].items()):
            u = session.unit(uid)
            if u:
                draw(u, order, T.ATTACK if order["order"] == "attack" else T.PATH)
        u = session.unit(ui.selected)
        if u and ui.hover and ui.hover != tuple(u["hex"]) and not ui.cover:
            name = ui.mode or guess(session, ui.hover)
            p = draw(u, {"order": name, "to": ui.hover}, T.PREVIEW) if name and name != "join" else None
            if p:
                turns = -(-len(p["path"]) // p["reach"]) if p["reach"] else 0
                when = "this turn" if turns == 1 else f"about {turns} turns" if turns else "it cannot set off"
                dry = p["range"] is not None and p["range"] < len(p["path"])
                fuel = f"   Its fuel gives out after {T.fuel_words(p['range'])}, at the cross." if dry else ""
                ui.message = f"{T.ORDER_NAME[name]} here: {when}.{fuel}   Click to order."

    # ---- a counter -----------------------------------------------------------------------

    def sprite(self, nation, kind, size):
        """A counter picture from art/counters, if there is one (docs/COUNTERS.md)."""
        key = (nation, kind, size)
        if key not in self.sprites:
            path = os.path.join(ART, f"{nation}_{kind}.png")
            self.sprites[key] = (pygame.transform.smoothscale(pygame.image.load(path), size)
                                 if os.path.exists(path) else None)
        return self.sprites[key]

    def counter(self, surface, session, ui, u, own, centre, size, taken=None, pile=1, ours=(), hq=False):
        nation = session.nation[u["id"]]
        x, y = int(centre[0] - size / 2), int(centre[1] - size / 2)
        face = pygame.Rect(x, y, size, size)
        chosen = u["id"] == ui.selected if taken is None else taken
        drop = max(4, size // 9) if chosen else 2                                          # taken up, it casts a longer shadow
        pygame.draw.rect(surface, (30, 26, 20), face.move(drop, drop), border_radius=4)
        pygame.draw.rect(surface, T.FACE[nation], face, border_radius=4)
        mark = T.MARK[nation]
        if chosen:                                                   # a bold yellow border that pulses gently
            beat = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 260)
            glow = tuple(int(c + (255 - c) * 0.7 * beat) for c in T.SELECT)
            pygame.draw.rect(surface, T.INK, face.inflate(4, 4), max(5, size // 9) + 2, border_radius=6)
            pygame.draw.rect(surface, glow, face.inflate(2, 2), max(5, size // 9), border_radius=6)
        else:
            pygame.draw.rect(surface, T.INK, face, 1, border_radius=4)
        big = size >= 34
        box = pygame.Rect(x + size * 0.17, y + size * (0.1 if big else 0.2), size * 0.66, size * (0.42 if big else 0.6))
        art = self.sprite(nation, u["type"], (int(size * 0.9), int(size * 0.54)))
        if art:
            surface.blit(art, (x + size * 0.05, y + size * 0.03))
        elif ui.symbols == "nato":
            self.symbol(surface, u["type"], box, T.BOX[nation], 2 if size >= 30 else 1)
        else:
            area = pygame.Rect(x + size * 0.12, y + size * (0.08 if big else 0.2), size * 0.76, size * (0.5 if big else 0.6))
            picture(surface, u["type"], area, mark, T.FACE[nation])
        if big:
            self.text(surface, u.get("steps", "?"), (x + size * 0.5, y + size * 0.7), size * 0.27, mark, True, True)
        if pile > 1 and size >= 22:                                  # how many units are in the pile
            tag = pygame.Rect(x - size * 0.08, y - size * 0.08, size * 0.36, size * 0.34)
            pygame.draw.rect(surface, T.PAPER, tag, border_radius=3)
            pygame.draw.rect(surface, T.INK, tag, 1, border_radius=3)
            self.text(surface, pile, tag.center, size * 0.24, T.INK, True, True)
        if not own:
            return
        if big:                                                      # stores and cohesion, side by side
            half = (size - 12) // 2
            for n, (share, colour) in enumerate(((u["stores"] / U.stores_cap(u), T.STORES),
                                                 (u["cohesion"] / 100, T.GOOD if u["cohesion"] >= 40 else T.POOR))):
                bx = x + 4 + n * (half + 4)
                pygame.draw.rect(surface, T.PAPER, (bx, y + size - 7, half, 4))
                pygame.draw.rect(surface, colour, (bx, y + size - 7, int(half * share), 4))
        order = session.order_of(session.leader(u["id"]))["order"]
        if order != "hold" and size >= 22:
            tag = pygame.Rect(x + size - size * 0.3, y - size * 0.08, size * 0.38, size * 0.34)
            pygame.draw.rect(surface, T.ATTACK if order == "attack" else T.PATH, tag, border_radius=3)
            self.text(surface, T.ORDER_KEY[order], tag.center, size * 0.24, T.PAPER, True, True)
        if hq and u["type"] != "hq" and size >= 22:                  # a headquarters is in the pile: a small flag
            fx, fy, fh = x + size * 0.07, y + size * 0.44, size * 0.26
            pygame.draw.line(surface, mark, (fx, fy), (fx, fy + fh), max(1, size // 30))
            pygame.draw.polygon(surface, mark, [(fx, fy), (fx + fh * 0.7, fy + fh * 0.25), (fx, fy + fh * 0.5)])
        if size >= 18:
            r = max(5, int(size * 0.17))
            self.badge(surface, problem(ours or [u]) if own else None, (x + size - r * 0.6, y + size * 0.5), r)

    def badge(self, surface, trouble, centre, r):
        """The trouble badge: a black drop on yellow for no fuel, otherwise "!"; nothing if all is well."""
        if not trouble:
            return
        bx, by = centre
        pygame.draw.circle(surface, T.BADGE, (bx, by), r)
        pygame.draw.circle(surface, T.INK, (bx, by), r, 1)
        if trouble == "fuel":
            pygame.draw.circle(surface, T.INK, (bx, by + r * 0.22), r * 0.42)
            pygame.draw.polygon(surface, T.INK, [(bx, by - r * 0.72), (bx - r * 0.38, by + r * 0.1), (bx + r * 0.38, by + r * 0.1)])
        else:
            self.text(surface, "!", (bx, by), r * 1.5, T.INK, True, True)

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

    # ---- the message line and the panel --------------------------------------------------

    def bar(self, surface, session, ui, rect):
        pygame.draw.rect(surface, T.INK, rect)
        self.text(surface, ui.message, (rect.x + 10, rect.y + 7), 14, T.PAPER)

    def buttons(self, surface, session, ui):
        """The orders and End turn, at the foot of the panel. The unit's own order is lit, and a
        click on it takes the order back; with none, the order a click on the map would give is
        lit. A button that cannot be used is greyed, and says why when pointed at."""
        u = None if self.playing else session.unit(ui.selected)
        has = session.pending[session.side].get(session.leader(u["id"]), {}).get("order") if u and not ui.alone else None
        would = ui.mode or has
        if u and not would:                                          # a plain click moves, or attacks an enemy in sight
            would = (guess(session, ui.hover) if ui.hover and ui.hover != tuple(u["hex"]) else None) or "move"
        for name, r in buttons(surface.get_size()).items():
            label, key = next((b[1], b[2]) for b in T.BUTTONS if b[0] == name)
            if name == "road_march" and u:
                label = T.order_name(name, [u] if ui.alone else session.members(u["id"]))
            usable, why = ((True, "") if name == "done" else session.can(ui.selected, name, ui.alone) if u and name != "next"
                           else (False, "Choose one of your units first."))
            if name == "next":                                       # nobody left to order: nothing to go on to
                usable, why = (True, "") if session.waiting_units() and not self.playing else (False, "Every unit has its order.")
            if name == has and u and not ui.mode:                    # its own order is always lit, and can be taken back
                usable = True
            lit = u is not None and usable and name == would
            colour = T.BUTTON_GO if name == "done" else T.BUTTON_ON if lit else T.BUTTON
            pygame.draw.rect(surface, colour if usable else (206, 198, 178), r, border_radius=6)
            pygame.draw.rect(surface, T.INK if usable else (150, 140, 120), r, 1, border_radius=6)
            self.text(surface, label, (r.centerx - 8, r.centery), 14, T.INK if usable else (150, 140, 120), True, True)
            self.text(surface, key, (r.right - 6 - self.font(10).size(key)[0], r.y + 3), 10, T.DIM)
            if lit and name == has and not ui.mode:
                self.tips.append((r, "This is its order. Click to take it back."))
            elif not usable:
                self.tips.append((r, why))

    def name_line(self, surface, session, ui, u, x, y, w):
        """A group's name, with a pencil to change it; while it is being changed, the words typed."""
        self.pencil_rect = pygame.Rect(x + w - 22, y, 22, 22)
        if ui.editing is not None:
            box = pygame.Rect(x - 2, y - 2, w - 26, 24)
            pygame.draw.rect(surface, (255, 255, 255), box, border_radius=4)
            pygame.draw.rect(surface, T.PATH, box, 2, border_radius=4)
            caret = "|" if pygame.time.get_ticks() // 400 % 2 == 0 else ""
            self.text(surface, ui.editing + caret, (x + 3, y + 1), 15, bold=True)
        else:
            self.text(surface, session.group_name(u["id"])[:30], (x, y), 17, bold=True)
        r = self.pencil_rect                                         # a pencil: its body, and its point
        pygame.draw.rect(surface, T.BUTTON, r, border_radius=4)
        pygame.draw.rect(surface, T.INK, r, 1, border_radius=4)
        pygame.draw.line(surface, T.INK, (r.x + 15, r.y + 5), (r.x + 8, r.y + 12), 4)
        pygame.draw.polygon(surface, T.INK, [(r.x + 5, r.y + 17), (r.x + 6, r.y + 12), (r.x + 10, r.y + 16)])
        self.tips.append((r, "Change the name. Enter keeps it; Escape leaves it."))

    def tip(self, surface, ui):
        """The words for whatever in the panel is under the mouse."""
        for r, words in self.tips:
            if r.collidepoint(ui.mouse) and words:
                font = self.font(12)
                box = pygame.Rect(0, 0, font.size(words)[0] + 14, font.get_height() + 10)
                box.bottomright = (min(surface.get_width() - 6, ui.mouse[0] + 10), ui.mouse[1] - 8)
                box.x = max(6, box.x)
                pygame.draw.rect(surface, (250, 244, 228), box, border_radius=4)
                pygame.draw.rect(surface, T.INK, box, 1, border_radius=4)
                self.text(surface, words, (box.x + 7, box.y + 5), 12)
                return

    def panel(self, surface, session, ui, rect):
        pygame.draw.rect(surface, T.PAPER, rect)
        pygame.draw.line(surface, T.INK, rect.topleft, rect.bottomleft, 2)
        view, over = session.view, session.state["over"]
        x, y, w = rect.x + EDGE, rect.y + 12, rect.w - 2 * EDGE
        foot = buttons(surface.get_size())["move"].y - 12           # the text stops above the buttons

        def line(s="", px=14, colour=T.INK, bold=False, gap=4):
            nonlocal y
            self.text(surface, s, (x, y), px, colour, bold)
            y += self.font(px, bold).get_height() + gap

        def rule():
            nonlocal y
            y += 6
            pygame.draw.line(surface, T.GRID, (x, y), (x + w, y), 2)
            y += 10

        def meter(label, value, top, colour, words, ink=T.INK, tip=""):
            nonlocal y
            self.text(surface, label, (x, y), 13, T.DIM)
            self.text(surface, words, (x + 78, y), 13, ink, True)
            self.tips.append((pygame.Rect(x, y - 2, w, 30), tip))
            y += 19
            pygame.draw.rect(surface, (214, 204, 178), (x, y, w, 7), border_radius=3)
            if top:
                pygame.draw.rect(surface, colour, (x, y, int(w * max(0, min(1, value / top))), 7), border_radius=3)
            y += 14

        line(session.scenario["name"], 21, bold=True, gap=2)
        line(f"{session.day:%d %B %Y}   turn {min(view['turn'], session.scenario['turns'])} of {session.scenario['turns']}", 13, T.DIM, gap=6)
        banner = pygame.Rect(x, y, w, 28)
        pygame.draw.rect(surface, T.SIDE[session.side], banner, border_radius=6)
        self.text(surface, "Last turn: watch and listen" if self.playing else "The game is over" if over
                  else f"{T.SIDE_NAME[session.side]}: give your orders", banner.center, 14, T.PAPER, True, True)
        y += 36
        line(f"Points:  Axis {view['vp']['axis']}   Commonwealth {view['vp']['cw']}", 13, gap=0)
        rule()

        u = None if self.playing else session.unit(ui.selected)
        group = session.members(u["id"]) if u else []
        self.member_rects, self.report_rects, self.back_rect, self.tips = {}, {}, None, []
        self.pencil_rect = None
        if over and not self.playing:                                # the result, and how it was reached
            r = session.state["result"]
            line("A draw" if r["winner"] is None else f"{T.SIDE_NAME[r['winner']]}: {r['grade']} victory", 18, T.SHORT, True)
            for row in score_lines(view):
                line(row, 12, gap=2)
            lost = [m for m in view["units"] if m["fate"]]
            if lost:
                y += 4
                line("Your losses", 13, bold=True)
                for m in lost[:8]:
                    line(f"{m['name'][:26]}: {m['fate']['cause']}, turn {m['fate']['turn']}", 12, gap=2)
        elif u and len(group) > 1 and not ui.alone:                  # a group: its units, and what binds them
            self.name_line(surface, session, ui, u, x, y, w)
            y += 24
            pygame.draw.rect(surface, T.SELECT, pygame.Rect(x - 6, y - 26, w + 12, 26 + 24), 3, border_radius=8)   # the one taken up
            line(f"{len(group)} units in a group: one order moves them all.", 12, T.DIM, gap=10)
            for m in group[:9]:
                nation = session.nation[m["id"]]
                row = pygame.Rect(x, y, w, 22)
                mini = pygame.Rect(x, y + 1, 30, 19)
                pygame.draw.rect(surface, T.FACE[nation], mini, border_radius=3)
                picture(surface, m["type"], mini.inflate(-6, -5), T.MARK[nation], T.FACE[nation])
                self.text(surface, m["name"][:25], (x + 38, y + 3), 12)
                words = T.strength(m).replace("about ", "")
                self.text(surface, words, (x + w - self.font(12).size(words)[0], y + 3), 12, T.strength_colour(m))
                self.member_rects[m["id"]] = row
                self.tips.append((row, T.strength_tip(m) + ". Click to order it by itself."))
                y += 23
            y += 4
            low = min(group, key=lambda m: m["cohesion"])
            level, word = T.morale(low["cohesion"])
            meter("Morale", level, 9, T.GOOD if low["cohesion"] >= 40 else T.POOR, word + " (the lowest)")
            wheels = [m for m in group if U.is_vehicle(m)]
            if wheels:
                least = min(wheels, key=lambda m: m["fuel"] * 100 // max(1, U.fuel_cap(m)))
                meter("Fuel", least["fuel"], U.fuel_cap(least),
                      T.FUEL, "for " + T.fuel_words(min(m["fuel"] // U.step_fuel(m) for m in wheels)))
            if any(not m["traced"] or m["out_of_stores"] for m in group):
                line("SHORT OF SUPPLY", 13, T.SHORT, True)
            if u["id"] in session.pending[session.side]:
                order = session.order_of(u["id"])
                turns = session.turns_to_go(u["id"])
                more = f", about {turns} turns" if turns and turns > 1 else ""
                line(f"Order: {T.ORDER_NAME[order['order']]}{more}", 15, T.PATH, True, gap=2)
            else:
                line("Waiting for an order", 15, T.ATTACK, True, gap=2)
            line("Click a unit above to order it by itself.", 12, T.DIM)
        elif u:
            if ui.alone and len(session.members(session.leader(u["id"]))) > 1:   # back to the group it was chosen from
                head = session.unit(session.leader(u["id"]))
                self.back_rect = pygame.Rect(x, y, w, 24)
                pygame.draw.rect(surface, T.BUTTON, self.back_rect, border_radius=5)
                pygame.draw.rect(surface, T.INK, self.back_rect, 1, border_radius=5)
                self.text(surface, "< Back to " + row_name(session, head)[:30], (x + 8, y + 4), 12, bold=True)
                y += 32
            nation = session.nation[u["id"]]
            pygame.draw.rect(surface, T.SELECT, pygame.Rect(x - 6, y - 5, w + 12, 60), 3, border_radius=8)   # the one taken up
            card = pygame.Rect(x, y, 76, 50)                         # the unit's picture beside its name
            pygame.draw.rect(surface, T.FACE[nation], card, border_radius=6)
            pygame.draw.rect(surface, T.INK, card, 1, border_radius=6)
            picture(surface, u["type"], card.inflate(-14, -12), T.MARK[nation], T.FACE[nation])
            for n, row in enumerate(wrap(self.font(16, True), u["name"], w - 88)[:2]):
                self.text(surface, row.strip(), (x + 88, y + n * 20), 16, bold=True)
            self.text(surface, f"{T.TYPE_NAME[u['type']]}, {u['xp']}", (x + 88, y + 34), 12, T.DIM)
            y += 62
            level, word = T.morale(u["cohesion"])
            now = T.strength_now(u)
            meter("Strength", now[0], now[1], T.strength_colour(u), T.strength(u), T.strength_colour(u), T.strength_tip(u))
            meter("Morale", level, 9, T.GOOD if u["cohesion"] >= 40 else T.POOR,
                  word + ("" if u["cohesion"] >= 40 else ": too low to attack"))
            if U.is_vehicle(u):
                meter("Fuel", u["fuel"], U.fuel_cap(u), T.FUEL, "for " + T.fuel_words(u["fuel"] // U.step_fuel(u)))
            meter("Stores", u["stores"], U.stores_cap(u), T.STORES, f"{u['stores']} tonnes")
            if u["type"] == "hq":
                line(f"Dump: {u['dump']['fuel']} t fuel, {u['dump']['stores']} t stores", 13)
            if not u["traced"]:
                line("OUT OF SUPPLY: no HQ or port in reach", 13, T.SHORT, True)
            elif u["out_of_stores"]:
                line("OUT OF STORES: morale is falling", 13, T.SHORT, True)
            else:
                line("In supply", 13, T.GOOD, True)
            if u["id"] in session.pending[session.side]:
                order = session.order_of(u["id"])
                turns = session.turns_to_go(u["id"])
                more = f", about {turns} turns" if turns and turns > 1 else ""
                line(f"Order: {T.ORDER_NAME[order['order']]}{more}", 15, T.PATH, True, gap=2)
                line(T.ORDER_HELP[order["order"]], 12, T.DIM)
            elif ui.alone:
                line("Chosen from its group", 15, T.ATTACK, True, gap=2)
                line("An order now splits it off. Split leaves it here.", 12, T.DIM)
            else:
                line("Waiting for an order", 15, T.ATTACK, True, gap=2)
                line("Click the map, or press a button below.", 12, T.DIM)
        elif not over and not self.playing:
            mine = [m for m in view["units"] if m["status"] == "on_map"]
            waiting = len(session.waiting_units())
            line("Click one of your units,", 14, gap=2)
            line("then click where it should go.", 14, gap=8)
            line(f"{waiting} of {T.count(len(mine), 'unit')} {'waits' if waiting == 1 else 'wait'} for orders." if waiting
                 else "All units have orders.", 13, T.PATH, True)
            short = [m for m in mine if not m["traced"] or m["out_of_stores"]]
            if short:
                y += 4
                line("Short of supply:", 13, T.SHORT, True)
                for m in short[:5]:
                    line("  " + m["name"], 12, T.SHORT, gap=2)
        rule()
        font = self.font(12)
        room = (foot - y) // 21 - 1
        if self.playing:                                             # nothing is given away before it is seen
            for row in ("Each formation strikes in turn.", "The units it hits burn.",
                        "The longer the rattle, the harder the blow.", "Then see who falls back and who holds.")[:max(0, room)]:
                line(row, 12, T.DIM, gap=2)
        elif not over and room > 1:                                  # reports: what the general is told
            told = session.reports()
            if told:
                line("Reports", 13, bold=True)
            for n, (what, uid) in enumerate(told):
                words = what if isinstance(what, str) else describe(what, session)
                lines = [r.strip() for r in wrap(font, words, w - 34)][:3]       # the whole of it, on as many lines as it needs
                if y + len(lines) * 16 + 6 > foot:
                    break
                who = next((m for m in view["units"] if m["id"] == uid), None)
                row = pygame.Rect(x, y, w, len(lines) * 16 + 4)
                if who:                                              # the unit reporting: click to go to it
                    nation = session.nation[uid]
                    mini = pygame.Rect(x, y, 26, 17)
                    pygame.draw.rect(surface, T.FACE[nation], mini, border_radius=3)
                    pygame.draw.rect(surface, T.INK, mini, 1, border_radius=3)
                    picture(surface, who["type"], mini.inflate(-6, -5), T.MARK[nation], T.FACE[nation])
                    if who["status"] == "on_map":
                        self.report_rects[n] = (row, uid)
                        self.tips.append((row, "Click to go to this unit."))
                for k, text in enumerate(lines):
                    self.text(surface, text, (x + 32, y + 1 + k * 16), 12)
                y += len(lines) * 16 + 7
        self.buttons(surface, session, ui)

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
        self.panel(surface, session, ui, a["panel"])
        self.bar(surface, session, ui, a["bar"])
        if not stage:
            self.tip(surface, ui)


def guess(session, hx):
    """The order a plain click on this hex gives: attack a seen enemy, otherwise move."""
    if not session.gmap.passable(hx):
        return None
    return "attack" if any(tuple(e["hex"]) == hx for e in session.view["enemy"]) else "move"


def star(x, y, r):
    """The points of the star that marks where a battle was fought last turn."""
    return [(x + (r if k % 2 == 0 else r * 0.55) * math.cos(math.radians(k * 30)),
             y + (r if k % 2 == 0 else r * 0.55) * math.sin(math.radians(k * 30))) for k in range(12)]


def row_name(session, u):
    """A unit or its group by name: a division by its HQ's, a made-up force as a Special Army."""
    group = session.members(u["id"])
    return session.group_name(u["id"]) + (f"  ({len(group)} units)" if len(group) > 1 else "")


def problem(units):
    """What is wrong with these units of yours, for the badge: "fuel" if a vehicle among them
    cannot move a hex, "trouble" if any is out of supply, out of stores or too shaken to
    attack, else None."""
    if any(U.is_vehicle(u) and u["fuel"] < U.step_fuel(u) for u in units):
        return "fuel"
    if any(not u["traced"] or u["out_of_stores"] or (u["type"] != "hq" and u["cohesion"] < 40) for u in units):
        return "trouble"
    return None


def broken(surface, colour, pts, width, dash, gap):
    """A line of dashes (or, with a short dash, dots) along the points."""
    left, on = dash, True
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        done = 0.0
        while length - done > 0.01:
            step = min(left, length - done)
            if on:
                a = (x0 + (x1 - x0) * done / length, y0 + (y1 - y0) * done / length)
                b = (x0 + (x1 - x0) * (done + step) / length, y0 + (y1 - y0) * (done + step) / length)
                pygame.draw.line(surface, colour, a, b, int(width))
            done, left = done + step, left - step
            if left <= 0.01:
                on = not on
                left = dash if on else gap


def score_lines(view):
    """How the result was reached: each side's points for places and for units destroyed, what
    standing still would have given, and so the margin (RULES 13.6)."""
    out = []
    for side in ("axis", "cw"):
        kills, total = view["kills"][side], view["vp"][side]
        out.append(f"{T.SIDE_NAME[side]}: {total - kills} for places + {kills} for units = {total}")
    par, lead = view["par"], view["vp"]["axis"] - view["vp"]["cw"]
    out.append(f"Standing still, the Axis leads by {par}." if par >= 0 else f"Standing still, the Commonwealth leads by {-par}.")
    margin = lead - par
    out.append("Against that: level." if margin == 0
               else f"Against that: {T.SIDE_NAME['axis' if margin > 0 else 'cw']} by {abs(margin)}.")
    return out


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
        return f"Battle {whereabouts(session.gmap, e['hex'])}" + (": the defenders fell back" if e["retreated"] else "")
    if kind == "stopped":
        return f"{who} stopped: {e['why']}"
    if kind == "destroyed":
        return f"{who} {e['cause']}"
    if kind == "no attack":
        return f"{who} did not attack"
    return f"{who} {kind}"
