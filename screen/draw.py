"""Paints the zoomable map, counters, detail ledger and persistent command console."""
import math
import os

import pygame

from engine import orders as O
from engine import paths
from engine import units as U
from mapgen import geo
from mapgen import hexgrid as H
from engine.gamemap import distance
from engine.movement import ALLOWANCE
from engine.supply import REACH, REACH_FULL
from engine.view import spot_range

from . import theme as T
from .layout import EDGE, HEAD_Y, Layout, air_controls, areas, buttons, details_toggle, footer_flag, game, layers, saves_list, tabs
from .session import GOES, where
from .pictures import AIR_LABELS, air_example, aircraft, picture

ROOT = os.path.dirname(os.path.dirname(__file__))
ART = os.path.join(ROOT, "art", "counters")
BASE = os.path.join(ROOT, "art", "basemap.jpg")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif%s.ttf"
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
        self.details_collapsed = False   # the map takes the details panel's space when closed
        self.weather_visible = True      # the map's weather chip is a visual preference
        self.alone = False              # the unit taken up is one of a group, to be ordered by itself
        self.chooser = None             # a hex with several of your units in it, and which: a list to choose from
        self.layers_open = False        # the Layers list in the map's corner is showing
        self.air_open = False           # air-effort choices above the message strip
        self.game_open = False          # the Game list beside it is showing: Save, Load, Screenshot
        self.saves = None               # the saved games listed to choose from, [(file, words)], or None
        self.editing = None             # the name being typed for the group taken up, or None
        self.tab = "unit"               # the panel's tab: the unit taken up, "orders", every unit's order, or "timetable"
        self.scroll = 0                 # how far down the list of orders is scrolled, in rows
        self.panel_scroll = 0           # the side panel's position in a short window
        self.remind = True              # End turn asks once more when units with no order were not gone through
        self.preview = ""               # what a click here would do, while a unit is taken up and a hex pointed at

    @property
    def layout(self):
        return Layout(T.BASE_HEX * self.zoom)


def tint(colour, k):
    """A colour made paler (k above 0) or darker (k below 0)."""
    return tuple(int(c + (255 - c) * k) if k > 0 else int(c * (1 + k)) for c in colour)


def slab(base, w, h, edge, corner, grain=True, band=None, strip=0):
    """A flat piece lit from the top left: paler at the top, its edge bevelled, a speckle in it
    that is the same every time, its corners rounded; and a band of another colour across the
    top, strip pixels deep, if one is given."""
    img = pygame.Surface((w, h), pygame.SRCALPHA)
    for cy in range(h):
        row = tint(band if band and cy < strip else base, 0.16 - 0.34 * cy / h)       # lighter at the top
        for cx in range(w):
            speck = (cx * 73856093 ^ cy * 19349663) % 13 - 6 if grain else 0
            img.set_at((cx, cy), tuple(max(0, min(255, c + speck)) for c in row))
    if band:
        pygame.draw.line(img, tint(band, -0.42), (0, strip), (w, strip), 1)
    top = band or base
    pygame.draw.polygon(img, tint(top, 0.5), [(0, 0), (w, 0), (w - edge, edge), (edge, edge)])
    pygame.draw.polygon(img, tint(base, 0.5), [(0, 0), (edge, edge), (edge, h - edge), (0, h)])
    pygame.draw.polygon(img, tint(base, -0.42), [(w, h), (0, h), (edge, h - edge), (w - edge, h - edge), (w - edge, edge), (w, 0)])
    shape = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(shape, (255, 255, 255, 255), shape.get_rect(), border_radius=corner)
    img.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)                       # round the corners off
    pygame.draw.rect(img, T.INK, img.get_rect(), 1, border_radius=corner)
    return img


def pointed(surface, colour, centre, r, points=5, inner=0.42):
    """A star of so many points, one of them upward."""
    cx, cy = centre
    pygame.draw.polygon(surface, colour, [(cx + (r if n % 2 == 0 else r * inner) * math.sin(math.pi * n / points),
                                           cy - (r if n % 2 == 0 else r * inner) * math.cos(math.pi * n / points))
                                          for n in range(2 * points)])


def union(surface, box):
    """The Union Flag, filling the box: its two saltires, then the cross over them."""
    part = pygame.Surface(box.size)
    part.fill(T.FLAG_BLUE)
    w, h = box.size
    for thick, colour in ((0.22, T.FLAG_WHITE), (0.08, T.FLAG_RED)):
        for a, b in (((-w, -h), (2 * w, 2 * h)), ((-w, 2 * h), (2 * w, -h))):
            pygame.draw.line(part, colour, a, b, max(1, int(h * thick)))
    for thick, colour in ((0.34, T.FLAG_WHITE), (0.2, T.FLAG_RED)):
        pygame.draw.rect(part, colour, (w / 2 - h * thick / 2, 0, h * thick, h))
        pygame.draw.rect(part, colour, (0, h / 2 - h * thick / 2, w, h * thick))
    surface.blit(part, box)


def flag(which, w, h):
    """A flag as it was in 1941 (docs/COUNTERS.md, with the source of each): the Union Flag; New
    Zealand's and Australia's blue ensigns; India's red ensign with the Star of India; the Union
    of South Africa's flag of 1928; Poland's; the Kingdom of Italy's tricolour with the arms of
    Savoy; and for Germany the black cross its army painted on its vehicles, which is not the
    flag it flew. Drawn large and brought down, so that its edges are smooth."""
    k = 4
    big, wide, high = pygame.Surface((w * k, h * k)), w * k, h * k
    white, red, blue = T.FLAG_WHITE, T.FLAG_RED, T.FLAG_BLUE
    canton = pygame.Rect(0, 0, wide // 2, high // 2)
    if which == "uk":
        union(big, big.get_rect())
    elif which == "nz":                                              # the Southern Cross: four red stars edged white
        big.fill(blue)
        union(big, canton)
        for fx, fy, r in ((0.75, 0.2, 0.1), (0.865, 0.42, 0.085), (0.64, 0.46, 0.1), (0.75, 0.78, 0.115)):
            pointed(big, white, (wide * fx, high * fy), high * (r + 0.035))
            pointed(big, red, (wide * fx, high * fy), high * r)
    elif which == "au":                                              # the Commonwealth Star of seven points, and the Southern Cross
        big.fill(blue)
        union(big, canton)
        pointed(big, white, (wide * 0.25, high * 0.75), high * 0.19, 7, 0.5)
        for fx, fy, r, points in ((0.75, 0.83, 0.09, 7), (0.625, 0.44, 0.09, 7), (0.75, 0.17, 0.09, 7), (0.86, 0.37, 0.09, 7),
                                  (0.8, 0.54, 0.05, 5)):
            pointed(big, white, (wide * fx, high * fy), high * r, points, 0.5)
    elif which == "in":                                              # the Star of India under its crown, on the fly
        big.fill(red)
        union(big, canton)
        cx, cy = wide * 0.75, high * 0.56
        pointed(big, (236, 190, 60), (cx, cy), high * 0.27, 16, 0.6)
        pygame.draw.circle(big, (120, 180, 226), (cx, cy), high * 0.14)
        pointed(big, white, (cx, cy), high * 0.09)
        pygame.draw.polygon(big, (236, 190, 60), [(cx - high * 0.1, cy - high * 0.3), (cx - high * 0.13, cy - high * 0.46),
                                                  (cx - high * 0.05, cy - high * 0.39), (cx, cy - high * 0.5),
                                                  (cx + high * 0.05, cy - high * 0.39), (cx + high * 0.13, cy - high * 0.46),
                                                  (cx + high * 0.1, cy - high * 0.3)])
    elif which == "sa":                                              # orange, white and blue, and the three small flags on the white
        for n, colour in enumerate(((240, 116, 22), white, blue)):
            pygame.draw.rect(big, colour, (0, n * high // 3, wide, high - n * high // 3))
        fw, fh = int(wide * 0.15), int(high * 0.25)
        first = pygame.Rect(wide // 2 - fw * 3 // 2 - 2, high // 2 - fh // 2, fw, fh)
        union(big, first)
        free = first.move(fw + 2, 0)                                 # the Orange Free State's, hung downward
        for n in range(7):
            pygame.draw.rect(big, white if n % 2 == 0 else (240, 116, 22), (free.x + n * fw // 7, free.y, fw - n * fw // 7, fh))
        for n, colour in enumerate((red, white, blue)):
            pygame.draw.rect(big, colour, (free.x + fw * 4 // 7 + n * fw // 7, free.y, fw // 7 + 1, fh * 3 // 7))
        vier = free.move(fw + 2, 0)                                  # the South African Republic's: green at the hoist
        for n, colour in enumerate((red, white, blue)):
            pygame.draw.rect(big, colour, (vier.x, vier.y + n * fh // 3, fw, fh - n * fh // 3))
        pygame.draw.rect(big, (0, 122, 77), (vier.x, vier.y, fw // 4, fh))
        for box in (first, free, vier):
            pygame.draw.rect(big, T.INK, box, 1)
    elif which == "pl":
        big.fill(white)
        pygame.draw.rect(big, (212, 33, 61), (0, high // 2, wide, high - high // 2))
    elif which == "it":
        for n, colour in enumerate(((0, 140, 69), white, (205, 33, 42))):
            pygame.draw.rect(big, colour, (n * wide // 3, 0, wide - n * wide // 3, high))
        arms = pygame.Rect(0, 0, high * 0.36, high * 0.46)
        arms.center = (wide // 2, high // 2)
        pygame.draw.rect(big, (0, 70, 160), arms.inflate(high * 0.1, high * 0.1), border_bottom_left_radius=arms.w // 2,
                         border_bottom_right_radius=arms.w // 2)
        pygame.draw.rect(big, (205, 33, 42), arms, border_bottom_left_radius=arms.w // 2, border_bottom_right_radius=arms.w // 2)
        pygame.draw.rect(big, white, (arms.centerx - arms.w * 0.14, arms.y, arms.w * 0.28, arms.h))
        pygame.draw.rect(big, white, (arms.x, arms.centery - arms.w * 0.22, arms.w, arms.w * 0.28))
    else:
        big.fill(T.FACE["de"])
        for thick, colour in ((0.36, white), (0.2, T.INK)):
            pygame.draw.rect(big, colour, (wide / 2 - high * thick / 2, high * 0.12, high * thick, high * 0.76))
            pygame.draw.rect(big, colour, (wide / 2 - high * 0.38, high / 2 - high * thick / 2, high * 0.76, high * thick))
    img = pygame.transform.smoothscale(big, (w, h))
    pygame.draw.rect(img, T.INK, img.get_rect(), 1)
    return img


class Painter:
    def __init__(self, gmap):
        pygame.font.init()
        self.gmap = gmap
        self.fonts, self.sprites, self.faces, self.shadows = {}, {}, {}, {}
        self.base = self.load_base()
        self.back = (None, None)        # the scaled background and what it was made for
        self.reach_cache = (None, None)
        self.zone_cache = (None, None)
        self.named = {p["hex"] for p in gmap.places.values()}       # hexes with a place in them
        self.playing = False            # the last turn is being played back
        self.member_rects = {}          # the rows of a group's units in the panel, to click
        self.chooser_rects, self.report_rects, self.back_rect, self.tips = {}, {}, None, []
        self.scroll_rects, self.cycle_rects = {}, {}
        self.panel_scroll_rects, self.order_rects = {}, {}
        self.panel_scroll_max, self.panel_body, self.panel_subject = 0, None, None
        self.panel_content_bottom = None
        self.panel_canvas = None
        self.weather_rect = None        # the weather's chip on the map, to tap
        self.skies = {}                 # the wash laid over the map in bad weather, by size and kind
        self.pencil_rect = None

    def font(self, px, bold=False, serif=False):
        px = max(9, int(px))
        key = (px, bold, serif)
        if key not in self.fonts:
            face = (SERIF if serif else FONT) % ("-Bold" if bold else "")
            if os.path.exists(face):
                self.fonts[key] = pygame.font.Font(face, px)
            else:
                family = "Georgia" if serif else "DejaVu Sans"
                self.fonts[key] = pygame.font.SysFont(family, px, bold=bold)
        return self.fonts[key]

    def text(self, surface, s, pos, px=14, colour=T.INK, bold=False, centre=False, halo=None, serif=False):
        font = self.font(px, bold, serif)
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

    def legend(self, surface, ui):
        """What the layers that are on are showing, beside the Layers list."""
        rows = []
        if "s" in ui.overlays:
            rows += [("line", T.HAUL, "A haul to an HQ this turn: thicker, more tonnes"),
                     ("tint", T.REACH_FULL, "Ground an HQ or port keeps fully supplied"),
                     ("tint", T.REACH, "Ground it reaches, but only in part"),
                     ("box", T.SUPPLY, "What a port holds; an HQ's haul when it is taken up")]
        if "z" in ui.overlays:
            rows += [("tint", T.ZOC_OWN, "Your zone of control"), ("tint", T.ZOC_FOE, "The enemy's, where you see him"),
                     ("tint", T.UNSEEN, "Ground none of your units can see")]
        if not rows:
            return
        anchor = pygame.Rect(12, surface.get_height() - 46, 104, 34)
        box = pygame.Rect(anchor.x + 170, anchor.bottom - len(rows) * 22 - 14, 372, len(rows) * 22 + 12)
        pygame.draw.rect(surface, T.PAPER, box, border_radius=6)
        pygame.draw.rect(surface, T.INK, box, 2, border_radius=6)
        for n, (kind, colour, words) in enumerate(rows):
            y = box.y + 8 + n * 22
            swatch = pygame.Rect(box.x + 10, y + 2, 30, 14)
            if kind == "line":
                pygame.draw.line(surface, T.INK, swatch.midleft, swatch.midright, 7)
                pygame.draw.line(surface, colour, swatch.midleft, swatch.midright, 5)
            elif kind == "box":
                pygame.draw.rect(surface, (250, 244, 228), swatch, border_radius=3)
                pygame.draw.rect(surface, colour, swatch, 2, border_radius=3)
            else:                                                    # a tint, as it looks over the desert
                pygame.draw.rect(surface, T.TERRAIN["."], swatch)
                veil = pygame.Surface(swatch.size, pygame.SRCALPHA)
                veil.fill(colour)
                surface.blit(veil, swatch.topleft)
                pygame.draw.rect(surface, T.INK, swatch, 1)
            self.text(surface, words, (box.x + 50, y + 1), 12)

    def key(self, surface):
        """The key to the map and the counters, in the map's bottom right corner."""
        rows = (("road", "Coast road"), ("track", "Desert track"), ("rail", "Railway"), ("scarp", "Escarpment: vehicles cross at a pass"),
                ("lane", "Sea lane"), ("fort", "Fortified hex"), ("port", "Port"), ("town", "Town"), ("site", "Other place"),
                ("battle", "Where a battle was fought last turn"),
                ("armour", "Tanks"), ("motorised", "Motorised infantry"), ("foot", "Infantry on foot"), ("guns", "Guns"),
                ("recon", "Reconnaissance vehicles"), ("hq", "Headquarters"), ("fuel", "Out of fuel"), ("trouble", "In trouble: supply or morale"))
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

    def sky(self, surface, kind):
        """Bad weather seen on the map: a wash over the ground, under the counters, which stay
        the loudest thing on it. Sand-coloured with streaks for a storm, grey with slanting
        lines for rain. Made once for a size and kept."""
        if kind in (None, "clear"):
            return
        w, h = surface.get_size()
        if (w, h, kind) not in self.skies:
            wash = pygame.Surface((w, h), pygame.SRCALPHA)
            wash.fill((214, 172, 96, 74) if kind == "sandstorm" else (62, 84, 112, 60))
            n = 0
            for y in range(-h, h, 9 if kind == "rain" else 13):      # a stated pattern, the same every time
                n += 1
                x = (n * 197) % 61
                if kind == "rain":
                    for x0 in range(x - 60, w, 61):
                        pygame.draw.line(wash, (214, 226, 240, 70), (x0, y + x0 // 3), (x0 - 7, y + x0 // 3 + 21), 1)
                else:
                    for x0 in range(x - 200, w, 233):
                        pygame.draw.line(wash, (246, 222, 170, 60), (x0, y + h), (x0 + 150 + n % 5 * 20, y + h - 4), 3)
            self.skies = {(w, h, kind): wash}
        surface.blit(self.skies[w, h, kind], (0, 0))

    def weather_chip(self, surface, kind, outlook, top=10, right_pad=10):
        """The weather, in the map's top right corner: a small picture, its name, and the word
        on the next two days. A tap says what it does."""
        if kind is None:
            self.weather_rect = None
            return
        name = {"clear": "Clear", "rain": "Rain", "sandstorm": "Sandstorm"}[kind]
        wide = max(self.font(15, True).size(name)[0], self.font(12).size("Outlook: " + outlook)[0]) + 62
        r = pygame.Rect(surface.get_width() - wide - right_pad, top, wide, 46)
        chip = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(chip, (250, 244, 228, 235), chip.get_rect(), border_radius=8)
        pygame.draw.rect(chip, T.SHORT if kind != "clear" else T.INK, chip.get_rect(), 2 if kind != "clear" else 1, border_radius=8)
        cx, cy = 26, 23
        if kind == "clear":                                          # a sun
            pygame.draw.circle(chip, (236, 170, 40), (cx, cy), 9)
            for k in range(8):
                v = pygame.math.Vector2(15, 0).rotate(k * 45)
                pygame.draw.line(chip, (236, 170, 40), (cx + v.x * 0.8, cy + v.y * 0.8), (cx + v.x, cy + v.y), 2)
        elif kind == "rain":                                         # a cloud, and what falls from it
            for dx, dy, rad in ((-7, -3, 7), (2, -6, 9), (9, -2, 6)):
                pygame.draw.circle(chip, (96, 110, 130), (cx + dx, cy + dy), rad)
            for dx in (-8, 0, 8):
                pygame.draw.line(chip, (50, 96, 170), (cx + dx, cy + 6), (cx + dx - 4, cy + 15), 2)
        else:                                                        # blown sand
            for dy, long in ((-9, 26), (-2, 34), (5, 22), (11, 30)):
                pygame.draw.line(chip, (190, 140, 60), (cx - 16 + (dy % 5), cy + dy), (cx - 16 + (dy % 5) + long, cy + dy), 3)
        surface.blit(chip, r.topleft)
        self.text(surface, name, (r.x + 52, r.y + 5), 15, T.SHORT if kind != "clear" else T.INK, True)
        self.text(surface, "Outlook: " + outlook, (r.x + 52, r.y + 26), 12, T.DIM)
        self.weather_rect = r

    def map(self, surface, session, ui):
        g, lay, view, z = session.gmap, ui.layout, session.view, ui.zoom
        w, h = surface.get_size()
        surface.blit(self.background((w, h), ui), (0, 0))
        self.sky(surface, session.weather)
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
                    surface.blit(self.face(nation, size), (x - size / 2 + k * size * 0.055, y - size / 2 - k * size * 0.055))
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
            mover = ui.chooser.get("mover")                              # a unit already taken up could come here
            acts = [(("move",), f"Move {session.group_name(mover)} here")] if session.unit(mover) else []
            acts += [(("group",), "Group all here into one")] if len(rows) > 1 else []       # and what can be done with them
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
            if stacks.get(ui.hover) or ui.hover in self.named or f"{ui.hover[0]},{ui.hover[1]}" in view["forts"]:
                self.tooltip(surface, session, ui, stacks.get(ui.hover, []))     # only where there is something to say
        self.weather_rect = None
        if ui.weather_visible:
            self.weather_chip(surface, session.weather, view["outlook"], top=T.MASTHEAD + 12, right_pad=45)
        if "k" in ui.overlays:
            self.key(surface)
        if ui.layers_open:
            self.legend(surface, ui)
        window = (w + (0 if ui.details_collapsed else T.PANEL), h + T.BAR + T.CONSOLE)
        if ui.layers_open:
            menu = layers(window, True, ui.details_collapsed)
            box = pygame.Rect(menu["k"].x - 4, menu["k"].y - 30, 160,
                              menu["nato"].bottom - menu["k"].y + 34)
            pygame.draw.rect(surface, T.PAPER, box, border_radius=6)
            pygame.draw.rect(surface, T.INK, box, 2, border_radius=6)
            self.text(surface, "MAP LAYERS", (box.x + 12, box.y + 7), 12, T.DIM, True)
        for name, r in layers(window, ui.layers_open, ui.details_collapsed).items():
            label = {"layers": "Layers", "k": "Terrain key", "weather": "Weather chip",
                     "s": "Supply", "z": "Zones", "pictures": "Pictures", "nato": "NATO"}[name]
            on = (ui.layers_open if name == "layers" else ui.weather_visible if name == "weather"
                  else ui.symbols == name if name in ("pictures", "nato") else name in ui.overlays)
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
        for name, r in game(window, ui.game_open, ui.details_collapsed).items():
            pygame.draw.rect(surface, T.BUTTON_ON if r.collidepoint(ui.mouse) and name != "game" else T.PAPER, r, border_radius=6)
            pygame.draw.rect(surface, T.INK, r, 2, border_radius=6)
            if name == "game":                                       # three lines: a list of things to do
                for k in range(3):
                    pygame.draw.line(surface, T.INK, (r.x + 11, r.y + 11 + k * 6), (r.x + 25, r.y + 11 + k * 6), 2)
                self.text(surface, "Game", (r.x + 34, r.y + 8), 14, bold=True)
            else:
                label, key = next((b[1], b[2]) for b in T.GAME if b[0] == name)
                self.text(surface, label, (r.x + 12, r.y + 7), 14, bold=True)
                self.text(surface, key, (r.right - 8 - self.font(10).size(key)[0], r.y + 4), 10, T.DIM)
        if ui.saves is not None:                                     # the saved games, to choose one
            rows = saves_list(window, len(ui.saves), ui.details_collapsed)
            pygame.draw.rect(surface, T.PAPER, rows["box"], border_radius=8)
            pygame.draw.rect(surface, T.INK, rows["box"], 2, border_radius=8)
            self.text(surface, "Load a saved game" if ui.saves else "No games have been saved yet",
                      (rows["box"].x + 14, rows["box"].y + 10), 16, bold=True)
            for k, (_, words) in enumerate(ui.saves):
                while self.font(13).size(words)[0] > rows[k].w - 20:             # as much as fits
                    words = words[:-1]
                pygame.draw.rect(surface, T.BUTTON_ON if rows[k].collidepoint(ui.mouse) else T.BUTTON, rows[k], border_radius=4)
                pygame.draw.rect(surface, T.INK, rows[k], 1, border_radius=4)
                self.text(surface, words, (rows[k].x + 10, rows[k].y + 7), 13)
            pygame.draw.rect(surface, T.BUTTON, rows["close"], border_radius=6)
            pygame.draw.rect(surface, T.INK, rows["close"], 1, border_radius=6)
            self.text(surface, "Close", rows["close"].center, 14, T.INK, True, True)

    def stage(self, surface, session, ui, stage):
        """A moment of the last turn being played back (screen/replay.py)."""
        lay, z = ui.layout, ui.zoom
        w, h = surface.get_size()
        surface.blit(self.background((w, h), ui), (0, 0))
        then = session.before[session.side] if session.before and session.state["seed"] else None
        self.sky(surface, then and then["weather"])                 # the weather of the turn being played back
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
        if then:
            self.weather_chip(surface, then["weather"], then["outlook"], top=54)
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
        eyes = [(tuple(u["hex"]), spot_range(session.state, u, extra)) for u in mine]
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
        """The paths of the orders given, and of the one being chosen: a way is tried out under
        the pointer only once Move, Attack or March has been pressed. A unit that holds, or
        is already on its way, trails no line."""
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
        if u and ui.mode and ui.hover and ui.hover != tuple(u["hex"]) and not ui.cover:
            name = ui.mode
            p = draw(u, {"order": name, "to": ui.hover}, T.PREVIEW) if name != "join" else None
            if p:
                turns = -(-len(p["path"]) // p["reach"]) if p["reach"] else 0
                when = "this turn" if turns == 1 else f"about {turns} turns" if turns else "it cannot set off"
                dry = p["range"] is not None and p["range"] < len(p["path"])
                fuel = f"   Its fuel gives out after {T.fuel_words(p['range'])}, at the cross." if dry else ""
                ui.preview = f"{T.order_name(name, session.members(u['id']))} here: {when}.{fuel}   Click to order."

    # ---- a counter -----------------------------------------------------------------------

    def sprite(self, nation, kind, size, variant=None):
        """The unit's historically chosen variant, then the kind's painted or drawn fallback."""
        key = (nation, kind, size, variant)
        if key not in self.sprites:
            paths = ([os.path.join(ART, "variants", f"{nation}_{variant}.png")] if variant else [])
            paths += [os.path.join(ART, where, f"{nation}_{kind}.png") for where in ("artist", "")]
            path = next((p for p in paths if os.path.exists(p)), None)
            self.sprites[key] = pygame.transform.smoothscale(pygame.image.load(path), size) if path else None
        return self.sprites[key]

    def face(self, nation, size):
        """A counter's face as a thing lying on the map: lit from the top left, its edge bevelled,
        a little grain in it (docs/COUNTERS.md)."""
        key = (nation, size)
        if key not in self.faces:
            self.faces[key] = slab(T.FACE[nation], size, size, max(1, size // 16), max(3, size // 9), size >= 24)
        return self.faces[key]

    def shadow(self, w, h, reach, corner):
        """The soft shadow a counter or a tile casts, reach pixels beyond its edge."""
        key = (w, h, reach, corner)
        if key not in self.shadows:
            img = pygame.Surface((w + 2 * reach, h + 2 * reach), pygame.SRCALPHA)
            for k in range(reach):                                   # darker ring inside paler ring
                pygame.draw.rect(img, (24, 18, 10, 110 * (k + 1) // reach), img.get_rect().inflate(-2 * k, -2 * k),
                                 border_radius=corner + reach - k)
            self.shadows[key] = img
        return self.shadows[key]

    def notch(self, surface, session, uid, x, y, w, span, deep):
        """The mark of a unit's division in the middle of the top edge, span pixels wide: one
        colour to each division of a side."""
        if uid not in session.division:
            return
        mid = x + w / 2
        pts = [(mid - span / 2, y + 1), (mid - span * 0.39, y + deep), (mid + span * 0.39, y + deep), (mid + span / 2, y + 1)]
        pygame.draw.polygon(surface, T.DIVISION[session.division[uid][1] % len(T.DIVISION)], pts)
        pygame.draw.lines(surface, T.INK, False, pts, 1)

    def fitted(self, surface, words, centre, px, colour, room, least=9):
        """Bold words centred here, in the largest size from px down that fits the room; at the
        least size, as many letters as fit."""
        words = str(words)
        while px > least and self.font(px, True).size(words)[0] > room:
            px -= 1
        while len(words) > 1 and self.font(px, True).size(words)[0] > room:
            words = words[:-1]
        self.text(surface, words, centre, px, colour, True, True)

    def counter(self, surface, session, ui, u, own, centre, size, taken=None, pile=1, ours=(), hq=False):
        nation = session.nation[u["id"]]
        x, y = int(centre[0] - size / 2), int(centre[1] - size / 2)
        face = pygame.Rect(x, y, size, size)
        chosen = u["id"] == ui.selected if taken is None else taken
        reach = max(2, size // 14) * (2 if chosen else 1)                                  # taken up, it casts a longer shadow
        surface.blit(self.shadow(size, size, reach, max(3, size // 9)), (x - reach // 2, y - reach // 3))
        surface.blit(self.face(nation, size), face)
        mark, edge = T.MARK[nation], max(1, size // 16)
        if chosen:                                                   # a bold yellow border that pulses gently
            beat = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 260)
            glow = tuple(int(c + (255 - c) * 0.7 * beat) for c in T.SELECT)
            pygame.draw.rect(surface, T.INK, face.inflate(4, 4), max(5, size // 9) + 2, border_radius=6)
            pygame.draw.rect(surface, glow, face.inflate(2, 2), max(5, size // 9), border_radius=6)
        big, named = size >= 34, size >= T.NAMED                     # named: at the closest zoom, its name along the top
        if size >= 22:
            self.notch(surface, session, u["id"], x, y, size, size * 0.4, max(3, size // 18))
        if named:
            inset = max(5, size // 9) if chosen else edge            # the border of the one taken up is wider
            self.fitted(surface, T.short(u["name"]), (x + size * 0.5, y + size * 0.15), size * 0.125, mark, size - 2 * inset - 4)
        low = 0.1 if named else 0                                    # the picture makes room for the name
        box = pygame.Rect(x + size * 0.17, y + size * (0.22 if named else 0.1 if big else 0.2), size * 0.66,
                          size * (0.36 if named else 0.42 if big else 0.6))
        art = ui.symbols != "nato" and self.sprite(nation, u["type"], (int(size * (0.92 - low)), int(size * (0.552 - low * 0.6))), session.counter_art.get(u["id"]))
        if art:
            surface.blit(art, (x + size * (0.04 + low / 2), y + size * (0.045 + low * 1.5)))
        elif ui.symbols == "nato":
            self.symbol(surface, u["type"], box, T.BOX[nation], 2 if size >= 30 else 1)
        else:
            area = pygame.Rect(x + size * 0.12, y + size * (0.2 if named or not big else 0.08), size * 0.76,
                               size * (0.44 if named else 0.5 if big else 0.6))
            picture(surface, u["type"], area, mark, T.FACE[nation])
        flag = hq and u["type"] != "hq" and own                      # a headquarters is in the pile
        if named:                                                    # strength on the left, and on the right its pace
            self.text(surface, u.get("steps", "?"), (x + size * (0.37 if flag else 0.3), y + size * 0.77), size * 0.19, mark, True, True)
        elif big:
            self.text(surface, u.get("steps", "?"), (x + size * 0.5, y + size * 0.71), size * 0.25, mark, True, True)
        tag = pygame.Rect(x - 6, y - 14, 26, 22) if named else pygame.Rect(x - size * 0.08, y - size * 0.08, size * 0.36, size * 0.34)
        if pile > 1 and size >= 22:                                  # how many units are in the pile
            pygame.draw.rect(surface, T.PAPER, tag, border_radius=3)
            pygame.draw.rect(surface, T.INK, tag, 1, border_radius=3)
            self.text(surface, pile, tag.center, min(size * 0.24, 15), T.INK, True, True)
        if not own:
            return
        if named:                                                    # hexes of open desert in a turn, in this weather
            pace = session.allowance(session.members(u["id"])) // paths.OPEN_COST
            ax, my, r = x + size * 0.52, y + size * 0.77, size * 0.055
            pygame.draw.polygon(surface, T.PACE[nation], [(ax, my - r), (ax + r * 1.5, my), (ax, my + r)])     # an arrowhead: it goes
            self.text(surface, pace, (x + size * 0.775, my), size * 0.19, T.PACE[nation], True, True)
        if big:                                                      # stores and cohesion, side by side
            half = (size - 2 * edge - 12) // 2                       # inside the bevelled edge
            for n, (share, colour) in enumerate(((u["stores"] / U.stores_cap(u), T.STORES),
                                                 (u["cohesion"] / 100, T.GOOD if u["cohesion"] >= 40 else T.POOR))):
                bx = x + edge + 4 + n * (half + 4)
                pygame.draw.rect(surface, T.PAPER, (bx, y + size - edge - 6, half, 4))
                pygame.draw.rect(surface, colour, (bx, y + size - edge - 6, int(half * share), 4))
        order = session.order_of(session.leader(u["id"]))["order"]
        if order != "hold" and size >= 22:
            tag = tag.move(size - 14, 0) if named else pygame.Rect(x + size - size * 0.3, y - size * 0.08, size * 0.38, size * 0.34)
            pygame.draw.rect(surface, T.ATTACK if order == "attack" else T.PATH, tag, border_radius=3)
            self.text(surface, T.ORDER_KEY[order], tag.center, min(size * 0.24, 15), T.PAPER, True, True)
        if flag and size >= 22:                                      # a small flag
            fx, fy, fh = x + size * (0.12 if named else 0.1), y + size * (0.66 if named else 0.61), size * (0.2 if named else 0.26)   # beside the number, clear of the picture
            pygame.draw.line(surface, mark, (fx, fy), (fx, fy + fh), max(1, size // 30))
            pygame.draw.polygon(surface, mark, [(fx, fy), (fx + fh * 0.7, fy + fh * 0.25), (fx, fy + fh * 0.5)])
        if size >= 18:
            r = max(5, int(size * 0.17))
            self.badge(surface, problem(ours or [u]) if own else None, (x + size - r * 0.6, y + size * 0.5), r)

    def tile(self, surface, session, u, rect):
        """The unit taken up as one large tile in the panel: its name and division, its picture,
        and round it what the player needs of it, each with its word (docs/COUNTERS.md)."""
        nation, (x, y, w, h), strip = session.nation[u["id"]], rect, 44
        key = ("tile", nation, w, h)
        if key not in self.faces:
            self.faces[key] = slab(T.TILE, w, h, 5, 14, band=T.FACE[nation], strip=strip)
        surface.blit(self.shadow(w, h, 6, 14), (x - 3, y - 2))
        surface.blit(self.faces[key], rect)
        self.notch(surface, session, u["id"], x, y, w, 110, 7)
        head = session.division.get(u["id"])
        flies = session.flag[u["id"]]
        if ("flag", flies) not in self.faces:
            self.faces["flag", flies] = flag(flies, *T.FLAG)
        spot = pygame.Rect((x + w - T.FLAG[0] - 11, y + 8), T.FLAG)                  # its country's flag, top right
        surface.blit(self.faces["flag", flies], spot)
        self.tips.append((spot, T.FLAG_NAME[flies]))
        clear = w - 2 * (T.FLAG[0] + 18)                              # centred clear of the flag; a long name moves left of it
        if self.font(11, True).size(u["name"])[0] <= clear:
            self.fitted(surface, u["name"], (x + w / 2, y + 20), 17, T.MARK[nation], clear, 11)
        else:
            self.fitted(surface, u["name"], (x + (w - T.FLAG[0] - 11) / 2 + 4, y + 20), 17, T.MARK[nation], w - T.FLAG[0] - 34, 11)
        under = session.title[head[0]] if head and head[0] != u["id"] else T.TYPE_NAME[u["type"]]
        self.text(surface, under, (x + w / 2, y + 35), 12, T.MARK[nation], False, True)
        area = pygame.Rect(x + w / 2 - 90, y + strip + 4, 180, 108)
        art = self.sprite(nation, u["type"], area.size, session.counter_art.get(u["id"]))
        if art:
            surface.blit(art, area)
        else:
            picture(surface, u["type"], area.inflate(-30, -24), T.INK, T.TILE)
        if note := session.art_note.get(u["id"]):
            # Keep the hover target off the strength and movement facts beside the picture.
            self.tips.append((pygame.Rect(x + w // 2 - 48, y + strip + 4, 96, 108), note))
        now, level = T.strength_now(u), T.morale(u["cohesion"])
        hexes = u["fuel"] // U.step_fuel(u) if U.is_vehicle(u) else None
        pace = session.allowance([u]) // paths.OPEN_COST
        slots = [(44, 88, f"{now[0]:,}", now[2], "", T.strength_colour(u), T.strength_tip(u)),
                 (w - 44, 88, pace, "move" if pace == 1 else "moves", "", T.STRONG,
                  "Hexes a turn across open desert in this weather. Travel by road goes farther."),
                 (44, 146, level[0], "morale", level[1].lower(), T.GOOD if u["cohesion"] >= 40 else T.POOR,
                  f"Morale {level[0]} of 9: {level[1].lower()}" + ("" if u["cohesion"] >= 40 else ". Too low to attack"))]
        if hexes is not None:
            slots.append((w - 44, 146, f"{hexes * 10:,}", "km of fuel", "", T.FUEL if hexes else T.SHORT, "Fuel for " + T.fuel_words(hexes)))
        for cx, cy, figure, word, more, colour, tip in slots:
            self.fitted(surface, figure, (x + cx, y + cy), 30, colour, 80, 14)
            self.text(surface, word, (x + cx, y + cy + 22), 12, T.DIM, False, True)
            if more:
                self.text(surface, more, (x + cx, y + cy + 36), 11, T.DIM, False, True)
            self.tips.append((pygame.Rect(x + cx - 42, y + cy - 20, 84, 64), tip))
        rank = U.EXPERIENCE.index(u["xp"]) + 1                       # experience: one pip green, three veteran
        for k in range(len(U.EXPERIENCE)):
            c = (x + w / 2 - 44 + 13 * k, y + 168)
            pygame.draw.circle(surface, T.INK if k < rank else T.TILE, c, 4)
            pygame.draw.circle(surface, T.INK, c, 4, 1)
        self.text(surface, u["xp"], (x + w / 2 - 2, y + 161), 11, T.DIM)
        bar = pygame.Rect(x + w / 2 - 46, y + 180, 92, 7)
        pygame.draw.rect(surface, T.PAPER, bar)
        pygame.draw.rect(surface, T.STORES, (bar.x, bar.y, int(bar.w * min(1, u["stores"] / U.stores_cap(u))), bar.h))
        pygame.draw.rect(surface, T.INK, bar, 1)
        self.text(surface, "stores", (x + w / 2, y + 196), 11, T.DIM, False, True)
        self.tips.append((pygame.Rect(bar.x, y + 158, bar.w, 20), f"Experience: {u['xp']}"))
        self.tips.append((pygame.Rect(bar.x, bar.y - 2, bar.w, 26), f"{u['stores']} tonnes of stores"))

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

    def card(self, session, lead):
        """A unit or group of yours in a few short lines: strength, morale, fuel, supply, its
        order, and what is wrong. [(words, bold, colour)]"""
        group, side = session.members(lead), session.side
        lines = [(session.group_name(lead) + (f"  ({len(group)} units)" if len(group) > 1 else ""), True, T.INK)]
        sums = {}
        for m in group:                                              # strength, added up by kind: tanks, men, guns
            now = T.strength_now(m)
            if now and m["type"] != "hq" or len(group) == 1:
                sums[now[2]] = sums.get(now[2], 0) + now[0]
        fighters = [m for m in group if m["type"] != "hq"] or group
        level, word = T.morale(min(m["cohesion"] for m in fighters))
        lines.append((", ".join(f"{n:,} {what}" for what, n in sums.items()) + f"   Morale {level} {word.lower()}", False, T.INK))
        wheels = [m for m in group if U.is_vehicle(m)]
        fuel = f"Fuel {min(m['fuel'] // U.step_fuel(m) for m in wheels) * 10} km   " if wheels else ""
        cut = any(not m["traced"] for m in group)
        short = any(m["out_of_stores"] for m in group)
        lines.append((fuel + ("OUT OF SUPPLY" if cut else "Out of stores" if short else "In supply"), False,
                      T.SHORT if cut or short else T.INK))
        order = session.pending[side].get(lead)
        if order is None:
            lines.append(("Order: Hold", False, T.INK))
        else:
            turns = session.turns_to_go(lead)
            lines.append(("Order: " + T.order_name(order["order"], group)
                          + (" " + where(session.gmap, order["to"]) if "to" in order else "")
                          + (f", {turns} turns" if turns and turns > 1 else ""), False, T.INK))
        wrong = []                                                   # what is wrong, shortly
        if any(U.is_vehicle(m) and m["fuel"] < U.step_fuel(m) for m in group):
            wrong.append("no fuel to move")
        if any(m["type"] != "hq" and m["cohesion"] < O.ATTACK_MIN for m in group):
            wrong.append("morale too low to attack")
        if any(m.get("real") and m["type"] != "hq" and m["steps"] * 2 < m["real"][2] for m in group):
            wrong.append("under half strength")
        stopped = {e["unit"]: e["why"] for e in session.view["events"] if e["event"] == "stopped"}
        if any(stopped.get(m["id"]) == "no room" for m in group):
            wrong.append("kept out of a full hex")
        if wrong:
            lines.append(("! " + "; ".join(wrong), False, T.SHORT))
        return lines

    def tooltip(self, surface, session, ui, pile):
        """What is under the mouse: the place, a small card for each unit or group of yours, the
        enemy seen, the ground."""
        g, hx, view = session.gmap, ui.hover, session.view
        lines = []
        for name, p in sorted(g.places.items()):
            if p["hex"] == hx:
                lines.append((f"{name}  ({T.SIDE_NAME[view['places'][name]]})", True, T.INK))
        for lead in sorted({session.leader(u["id"]) for u, own in pile if own}):
            lines += self.card(session, lead)
        for u, own in pile:
            if not own:
                lines.append((f"Enemy  {u['name']}: {T.TYPE_NAME[u['type']].lower()}"
                              + (f", {u['strength']}" if "strength" in u else ""), False, T.INK))
        fort = view["forts"].get(f"{hx[0]},{hx[1]}")
        lines.append((T.TERRAIN_NAME[g.terrain[hx[1]][hx[0]]] + (f", fortified level {fort[0]}" if fort else ""), False, T.DIM))
        font = self.font(13)
        w = max(self.font(13, bold).size(s)[0] for s, bold, _ in lines) + 14
        h = len(lines) * (font.get_height() + 2) + 8
        x = min(ui.mouse[0] + 18, surface.get_width() - w - 4)
        y = min(ui.mouse[1] + 18, surface.get_height() - h - 4)
        tip = pygame.Surface((w, h), pygame.SRCALPHA)
        tip.fill((250, 244, 228, 240))
        pygame.draw.rect(tip, T.INK, tip.get_rect(), 1)
        for n, (s, bold, colour) in enumerate(lines):
            self.text(tip, s, (7, 4 + n * (font.get_height() + 2)), 13, colour, bold)
        surface.blit(tip, (x, y))

    # ---- the message line and the panel --------------------------------------------------

    def bar(self, surface, session, ui, rect):
        """One line of instruction, tied to what is happening: what a click would do while a
        unit is taken up and a hex pointed at, otherwise the last thing said."""
        pygame.draw.rect(surface, T.INK, rect)
        words = ui.preview or ui.message
        font = self.font(14)
        available = (air_controls(surface.get_size(), collapsed=ui.details_collapsed)["air"].left - rect.x - 20
                     if not ui.cover and not self.playing and not session.state["over"] else rect.w - 20)
        if font.size(words)[0] > available:
            while words and font.size(words + "…")[0] > available:
                words = words[:-1]
            words = words.rstrip() + "…"
        previous = surface.get_clip()
        surface.set_clip(pygame.Rect(rect.x, rect.y, available + 18, rect.h))
        self.text(surface, words, (rect.x + 10, rect.y + 7), 14, T.PAPER)
        surface.set_clip(previous)

    def air_orders(self, surface, session, ui):
        """The current turn's air effort is visible even when unit details are hidden."""
        if ui.cover or self.playing or session.state["over"]:
            return
        controls = air_controls(surface.get_size(), ui.air_open, ui.details_collapsed)
        button = controls["air"]
        current = session.air[session.side]
        grounded = session.weather in ("rain", "sandstorm")
        points = session.view["air_points"]
        pygame.draw.rect(surface, T.BUTTON_ON if ui.air_open else T.BUTTON, button, border_radius=4)
        pygame.draw.rect(surface, T.INK, button, 1, border_radius=4)
        primary_icon = pygame.Rect(button.x + 4, button.y + 3, 27, 24)
        alternate_icon = pygame.Rect(button.x + 32, button.y + 3, 27, 24)
        primary_model = air_example(session.side, "button", session.day)
        aircraft(surface, session.side, primary_icon, T.INK, T.BUTTON_ON, model=primary_model)
        aircraft(surface, session.side, alternate_icon, T.INK, T.BUTTON_ON, "fighter_alt")
        self.fitted(surface, f"AIR · {current.upper()}", (button.x + 118, button.y + 12), 13,
                    T.INK, 106, 10)
        self.text(surface, "▲" if ui.air_open else "▼", (button.right - 18, button.y + 6), 12, T.INK, True)
        primary, alternate = (AIR_LABELS[air_example(session.side, choice, session.day)]
                              for choice in ("button", "fighter_alt"))
        # The named targets precede the parent button: Painter.tip shows the first match.
        for icon, model in ((primary_icon, primary), (alternate_icon, alternate)):
            self.tips.append((icon, f"{model}: fighter example; air points pool types."))
        early = (" C.200s also served during this period; the icon shows one type."
                 if primary_model == "macchi202" else "")
        self.tips.append((button, f"Pooled air effort (1–3); {primary} and {alternate} are examples.{early}"))
        if not ui.air_open:
            return
        box = pygame.Rect(controls["support"].x - 4, controls["support"].y - 44, 222,
                          button.top - controls["support"].y + 40)
        pygame.draw.rect(surface, T.PAPER, box, border_radius=5)
        pygame.draw.rect(surface, T.INK, box, 2, border_radius=5)
        status = ("NO FLIGHTS · " + session.weather.upper() if grounded else
                  f"{points} AIR {'POINT' if points == 1 else 'POINTS'} THIS TURN")
        self.fitted(surface, status, (box.centerx, box.y + 12), 12,
                    T.SHORT if grounded else T.DIM, box.w - 12, 10)
        self.fitted(surface, "AIRCRAFT SHOWN ARE EXAMPLES", (box.centerx, box.y + 28), 10,
                    T.DIM, box.w - 12, 8)
        descriptions = {"support": "+5% in battle / point", "interdict": "−5% enemy lift / point",
                        "recon": "+1 spotting hex / point"}
        for n, choice in enumerate(("support", "interdict", "recon"), 1):
            row = controls[choice]
            pygame.draw.rect(surface, T.BUTTON_ON if choice == current else T.BUTTON, row, border_radius=3)
            pygame.draw.rect(surface, T.INK, row, 1, border_radius=3)
            aircraft(surface, session.side, pygame.Rect(row.x + 4, row.y + 4, 32, 29),
                     T.INK, T.BUTTON_ON, choice)
            example = AIR_LABELS[air_example(session.side, choice, session.day)]
            # Name the type visibly: at 32 px a Blenheim and a Boston cannot
            # reliably be distinguished by silhouette alone.
            self.fitted(surface, f"{n} {choice.title()} · {example}",
                        (row.x + 118, row.y + 9), 12, T.INK, row.w - 64, 10)
            self.text(surface, descriptions[choice], (row.x + 43, row.y + 18), 10, T.DIM)
            if choice == current:
                self.text(surface, "✓", (row.right - 18, row.y + 9), 14, T.INK, True)
            self.tips.append((row, "Example: " + AIR_LABELS[air_example(session.side, choice, session.day)]
                              + "; air points pool multiple types."))

    def masthead(self, surface, session, ui, map_area):
        """Field Atlas title band: map context stays visible even with details closed."""
        band = pygame.Rect(map_area.x, map_area.y, map_area.w, T.MASTHEAD)
        pygame.draw.rect(surface, T.COMMAND[session.side], band)
        pygame.draw.line(surface, T.GRID, band.bottomleft, band.bottomright, 2)
        compact = band.w < 760
        self.text(surface, session.scenario["name"], (band.x + 22, band.y + (12 if compact else 7)),
                  22 if compact else 27, T.PAPER, True, serif=True)
        if band.w >= 1080:
            self.text(surface, f"N O R T H   A F R I C A   ·   {session.day:%d %B %Y}".upper(),
                      (band.x + 360, band.y + 19), 12, T.PAPER, serif=True)
        badge_x = band.right
        if ui.details_collapsed and band.w >= 760:
            label = T.SIDE_NAME[session.side].upper() + " · ORDERS"
            badge_x = band.right - 16 - 48 - self.font(13, True, serif=True).size(label)[0]
            flies = "uk" if session.side == "cw" else "de"
            badge = ("side_badge", flies)
            if badge not in self.faces:
                self.faces[badge] = flag(flies, 38, 28)
            surface.blit(self.faces[badge], (badge_x, band.y + 13))
            self.text(surface, label, (badge_x + 48, band.y + 19), 13, T.PAPER, True, serif=True)
        scale_x = min(band.right - 145, badge_x - 145)
        scale_y = band.y + 37
        if scale_x > band.x + (315 if compact else 735):
            km = 5 if 10 * ui.layout.scale > 55 else 20 if 10 * ui.layout.scale < 30 else 10
            step = round(km * ui.layout.scale)
            pygame.draw.line(surface, T.PAPER, (scale_x, scale_y), (scale_x + 2 * step, scale_y), 1)
            for n in range(3):
                px = scale_x + n * step
                pygame.draw.line(surface, T.PAPER, (px, scale_y), (px, scale_y - 6), 1)
                self.text(surface, f"{n * km}" + (" km" if n == 2 else ""),
                          (px, scale_y - 21), 10, T.PAPER, serif=True)
        if not ui.cover:
            north_x, north_y = map_area.right - 64, T.MASTHEAD + 98
            pygame.draw.polygon(surface, T.INK, [(north_x, north_y - 20), (north_x - 6, north_y + 2),
                                                 (north_x, north_y - 2), (north_x + 6, north_y + 2)])
            self.text(surface, "N", (north_x, north_y + 11), 12, T.INK, True, True, serif=True)

    def action_icon(self, surface, name, rect, colour):
        """Small map-table symbols, drawn as vectors so every command remains recognisable."""
        x, cy = rect.x + 17, rect.centery + 2
        if name in ("move", "next", "road_march"):
            if name == "road_march":
                for dx in (-10, -4, 2):
                    pygame.draw.line(surface, colour, (x + dx, cy), (x + dx + 3, cy), 2)
            else:
                pygame.draw.line(surface, colour, (x - 10, cy), (x + 3, cy), 3)
            pygame.draw.polygon(surface, colour, [(x + 8, cy), (x + 1, cy - 6), (x + 1, cy + 6)])
        elif name == "attack":
            pygame.draw.polygon(surface, colour, star(x, cy, 10))
        elif name == "hold":
            pts = [(x + 9 * math.cos(math.pi * k / 4), cy + 9 * math.sin(math.pi * k / 4)) for k in range(8)]
            pygame.draw.polygon(surface, colour, pts, 2)
        elif name == "dig_in":
            pygame.draw.line(surface, colour, (x - 11, cy + 5), (x + 10, cy + 5), 2)
            for dx in (-7, 0, 7):
                pygame.draw.line(surface, colour, (x + dx, cy + 5), (x + dx + 4, cy - 3), 2)
        elif name == "rest":
            self.text(surface, "Zz", (x - 9, cy - 11), 15, colour, True, serif=True)
        elif name == "join":
            for dx in (-7, 0, 7):
                pygame.draw.circle(surface, colour, (x + dx, cy - 5), 3)
                pygame.draw.rect(surface, colour, (x + dx - 2, cy, 4, 7))
        elif name == "split":
            for direction in (-1, 1):
                pygame.draw.line(surface, colour, (x, cy), (x + direction * 9, cy), 2)
                pygame.draw.polygon(surface, colour, [(x + direction * 11, cy),
                                                     (x + direction * 5, cy - 4), (x + direction * 5, cy + 4)])
        elif name == "recall":
            pygame.draw.arc(surface, colour, (x - 9, cy - 10, 17, 17), 0.3, 5.2, 2)
            pygame.draw.polygon(surface, colour, [(x - 10, cy + 2), (x - 10, cy - 5), (x - 3, cy + 1)])
        elif name == "done":
            pygame.draw.rect(surface, colour, (x - 8, cy - 10, 16, 20), 2)
            pygame.draw.circle(surface, colour, (x + 3, cy), 2)

    def buttons(self, surface, session, ui):
        """The persistent command console. The unit's own order is lit, and a
        click on it takes the order back; with none, Hold is lit, which is what it will do. A
        button that cannot be used is greyed, and says why when pointed at."""
        u = None if self.playing or ui.cover else session.unit(ui.selected)
        console = areas(surface.get_size())["console"]
        pygame.draw.rect(surface, T.COMMAND[session.side], console)
        pygame.draw.line(surface, T.GRID, console.topleft, console.topright, 2)
        for yy in (console.y + 8, console.bottom - 7):
            pygame.draw.line(surface, T.SIDE[session.side], (console.left + 8, yy), (console.right - 8, yy), 1)
        grid = buttons(surface.get_size())
        for xx in (grid["move"].x - 10, grid["next"].x - 10):
            pygame.draw.line(surface, T.GRID, (xx, console.y + 18), (xx, console.bottom - 18), 1)
        emblem = footer_flag(surface.get_size())
        fx, fy = emblem.topleft
        if u:
            flies = session.flag[u["id"]]
            key = ("console_flag", flies, emblem.size)
            if key not in self.faces:
                self.faces[key] = flag(flies, *emblem.size)
            surface.blit(self.faces[key], emblem.topleft)
            label = u["name"] if ui.alone else session.group_name(u["id"])
            identity_end = buttons(surface.get_size())["move"].x - 12
            name_x = emblem.right + 10
            room = identity_end - name_x - 4
            self.fitted(surface, label, (name_x + room / 2, console.y + 32), 16, T.PAPER, room, 10)
            self.fitted(surface, "This unit alone" if ui.alone else T.SIDE_NAME[session.side],
                        (name_x + room / 2, console.y + 54), 12, T.PAPER, room, 10)
        else:
            flies = "uk" if session.side == "cw" else "de"
            key = ("console_flag", flies, emblem.size)
            if key not in self.faces:
                self.faces[key] = flag(flies, *emblem.size)
            surface.blit(self.faces[key], emblem.topleft)
            self.fitted(surface, T.SIDE_NAME[session.side], (emblem.right + 10 +
                        (buttons(surface.get_size())["move"].x - emblem.right - 26) / 2, console.centery),
                        16, T.PAPER, buttons(surface.get_size())["move"].x - emblem.right - 26, 10)
        has = session.pending[session.side].get(session.leader(u["id"]), {}).get("order") if u and not ui.alone else None
        would = ui.mode or has or "hold"                             # with no order a unit holds (RULES 8.1.3)
        offered = session.offers(ui.selected, ui.alone) if u else []
        if not self.playing and not session.state["over"] and not ui.details_collapsed:
            box = tabs(surface.get_size())["remind"]
            tick = pygame.Rect(box.x, box.y + 2, 18, 18)
            pygame.draw.rect(surface, (255, 255, 255), tick, border_radius=3)
            pygame.draw.rect(surface, T.INK, tick, 1, border_radius=3)
            if ui.remind:
                pygame.draw.lines(surface, T.INK, False, [(tick.x + 4, tick.y + 9), (tick.x + 8, tick.y + 13), (tick.x + 14, tick.y + 4)], 3)
            self.text(surface, "Remind me of units not gone through", (box.x + 26, box.y + 3), 12)
        for name, r in buttons(surface.get_size()).items():
            label, key = next((b[1], b[2]) for b in T.BUTTONS if b[0] == name)
            if name == "next" and u and has and session.leader(u["id"]) in session.waiting_units():
                label = "Keep order"                                 # its order stands from before: one tap lets it
            if name == "road_march" and u:
                label = T.order_name(name, [u] if ui.alone else session.members(u["id"]))
            usable, why = ((True, "") if name == "done" else session.can(ui.selected, name, ui.alone) if u and name != "next"
                           else (False, "Choose one of your units first."))
            if name == "next":                                       # nobody left to order: nothing to go on to
                usable, why = (True, "") if session.waiting_units() and not self.playing else (False, "Every unit has been gone through.")
            if name not in ("next", "done") and (name not in offered or (ui.tab != "unit" and not ui.details_collapsed)):
                usable, why = False, "Choose a unit on the Unit tab to give this order."
            if name == has and u and not ui.mode and (ui.tab == "unit" or ui.details_collapsed):
                usable = True
            lit = u is not None and usable and name == would
            colour = (T.BUTTON_GO if name == "done"                 # End turn is always there to press
                      else T.BUTTON_ON if lit or name == "next" else T.BUTTON)      # Next unit is lit while any unit waits
            pygame.draw.rect(surface, colour if usable else (206, 198, 178), r, border_radius=6)
            pygame.draw.rect(surface, T.INK if usable else (150, 140, 120), r, 1, border_radius=6)
            icon_ink = T.INK if usable else (150, 140, 120)
            self.action_icon(surface, name, r, icon_ink)
            self.fitted(surface, label, (r.x + 31 + (r.w - 33) / 2, r.centery), 13,
                        icon_ink, r.w - 36, 9)
            self.text(surface, key, (r.right - 6 - self.font(10).size(key)[0], r.y + 3), 10, T.DIM)
            if lit and name == has and not ui.mode:
                self.tips.append((r, "This is its order. Click to take it back."))
            elif lit and not has and not ui.mode:
                self.tips.append((r, "With no other order it holds."))
            elif not usable:
                self.tips.append((r, why))

    def orders_list(self, surface, session, ui, x, y, w, foot):
        """The Unit orders tab: every unit or group of the side and what it is to do this turn,
        to scroll through. A tap on a row takes that unit up."""
        side = session.side
        leads = sorted({session.leader(m["id"]) for m in session.view["units"] if m["status"] == "on_map"})
        waiting = session.waiting_units()
        self.text(surface, f"{len(leads)} units and groups: {len(waiting)} still to go through" if waiting
                  else f"{len(leads)} units and groups: all gone through", (x, y), 12, T.DIM)
        y += 20
        room = max(1, (foot - y - 26) // 25)
        ui.scroll = max(0, min(ui.scroll, len(leads) - room))
        for lead in leads[ui.scroll:ui.scroll + room]:
            m, nation = session.unit(lead), session.nation[lead]
            row = pygame.Rect(x, y, w, 23)
            pygame.draw.rect(surface, T.BUTTON_ON if lead == session.leader(ui.selected) else T.BUTTON, row, border_radius=4)
            mini = pygame.Rect(x + 3, y + 2, 30, 19)
            pygame.draw.rect(surface, T.FACE[nation], mini, border_radius=3)
            show = next((g for g in session.members(lead) if g["type"] != "hq"), m)
            picture(surface, show["type"], mini.inflate(-6, -5), T.MARK[nation], T.FACE[nation])
            order = session.pending[side].get(lead)
            does = "Hold" if order is None else T.order_name(order["order"], session.members(lead)) + (
                " " + where(session.gmap, order["to"]) if "to" in order else "") + (", stands" if lead in waiting else "")
            while self.font(12, True).size(does)[0] > w - 150:
                does = does[:-1]
            wide = self.font(12, True).size(does)[0]
            self.text(surface, does, (row.right - 6 - wide, y + 4), 12, T.DIM if order is None else T.INK, True)
            words = row_name(session, m)
            while self.font(12).size(words)[0] > w - 54 - wide:              # as much of the name as fits
                words = words[:-1]
            self.text(surface, words, (x + 40, y + 4), 12)
            self.report_rects[("order", lead)] = (row, lead)
            y += 25
        self.arrows(surface, ui, x, y, w, len(leads), room)

    def arrows(self, surface, ui, x, y, w, n, room):
        """Under a list longer than its room: two arrows to tap, and which rows are showing."""
        self.scroll_rects = {}
        if n > room:                                                 # more than fit: two arrows, or the wheel
            for k, (name, points) in enumerate((("up", ((0, 12), (10, 2), (20, 12))), ("down", ((0, 2), (10, 12), (20, 2))))):
                r = pygame.Rect(x + w - 76 + k * 40, y + 2, 36, 20)
                usable = ui.scroll > 0 if name == "up" else ui.scroll + room < n
                pygame.draw.rect(surface, T.BUTTON if usable else (206, 198, 178), r, border_radius=4)
                pygame.draw.rect(surface, T.INK if usable else (150, 140, 120), r, 1, border_radius=4)
                pygame.draw.polygon(surface, T.INK if usable else (150, 140, 120), [(r.x + 8 + px, r.y + 3 + py) for px, py in points])
                self.scroll_rects[name] = r
            self.text(surface, f"{ui.scroll + 1} to {min(n, ui.scroll + room)} of {n}", (x, y + 5), 12, T.DIM)

    def timetable_list(self, surface, session, ui, x, y, w, foot):
        """The Timetable tab: what is called away, what arrives or is made good, and anything
        else, each kind under its heading and on the day it happened, soonest first, to scroll
        through. A tap on an event goes to its unit."""
        aim = session.scenario.get("aim", {}).get(session.side)
        if aim:                                                      # a short scenario has one aim: said here, in its words
            self.text(surface, "Your aim", (x, y), 13, bold=True)
            y += 19
            for row in wrap(self.font(12), aim, w):
                self.text(surface, row.strip(), (x, y), 12)
                y += 15
            y += 9
        rows = session.timetable()
        ahead = [r for r in rows if not r["past"]]
        self.text(surface, f"{T.count(len(ahead), 'event')} to come, on the dates of 1941" if ahead
                  else "Nothing more is due before the end" if rows else "Nothing is due in this battle", (x, y), 12, T.DIM)
        y += 22
        font, items = self.font(12), []                              # each section's heading, then its events, soonest first
        for kinds, title in T.TIMETABLE:
            mine = [r for r in rows if (r["kind"] in kinds if kinds else not any(r["kind"] in k for k, _ in T.TIMETABLE))]
            items.append((None, [title, "" if mine else "none"], 0, 24))
            for r in mine:                                           # each event: its day, its words, why it happened
                lines = [s.strip() for s in wrap(font, r["words"], w - 12)]
                plain = len(lines)
                lines += [s.strip() for s in wrap(font, r["note"], w - 12)] if r["note"] else []
                items.append((r, lines, plain, 20 + len(lines) * 15 + 9))
        room, used = 0, 0                                            # as many whole rows as fit from where it is scrolled to
        ui.scroll = max(0, min(ui.scroll, len(items) - 1))
        for item in items[ui.scroll:]:
            used += item[3]
            if y + used > foot - 26:
                break
            room += 1
        room = max(1, room)
        for r, lines, plain, high in items[ui.scroll:ui.scroll + room]:
            if r is None:                                            # a heading: the kind of event under it
                self.text(surface, lines[0], (x, y + 4), 13, bold=True)
                self.text(surface, lines[1], (x + self.font(13, True).size(lines[0])[0] + 10, y + 5), 12, T.DIM)
                pygame.draw.line(surface, T.DIM, (x, y + 21), (x + w, y + 21), 1)
                y += high
                continue
            ink = T.DIM if r["past"] else T.INK
            box = pygame.Rect(x, y, w, high - 4)
            pygame.draw.rect(surface, T.BUTTON, box, border_radius=4)
            if r["turn"] == session.view["turn"]:                    # due as this turn ends
                pygame.draw.rect(surface, T.PATH, box, 2, border_radius=4)
            self.text(surface, f"{r['day'].day} {r['day']:%B}", (x + 6, y + 3), 12, ink, True)
            self.text(surface, r["when"], (box.right - 6 - font.size(r["when"])[0], y + 3), 12, T.DIM if r["past"] else T.PATH)
            for k, text in enumerate(lines):
                self.text(surface, text, (x + 6, y + 20 + k * 15), 12, ink if k < plain else T.DIM)
            if r["unit"] is not None:
                self.report_rects[("due", r["turn"], r["words"])] = (box, r["unit"])
                self.tips.append((box, "Click to go to this unit."))
            y += high
        self.arrows(surface, ui, x, y, w, len(items), room)

    def cannot(self, session, ui, u, line, w):
        """Under the unit taken up: what became of its order last turn, and why each greyed order
        cannot be given now. In words on the panel, not only when pointed at."""
        said = session.said[session.side].get(session.leader(u["id"]))
        for row in wrap(self.font(12, True), said, w) if said and not ui.alone else []:
            line(row.strip(), 12, T.SHORT, True)
        for name, why in session.blocked(ui.selected, ui.alone):
            label = T.order_name(name, [u] if ui.alone else session.members(u["id"])) if name == "road_march" else T.ORDER_NAME[name]
            for row in wrap(self.font(12), f"{label}: {why}", w):
                line(row.strip(), 12, T.SHORT)

    def roster(self, surface, session, ui, u, group, rect):
        """A group as its order of battle: its HQ's card across the top, with the flag, the
        group's name and a pencil to change it, and under it an indented illustrated row for
        each member, joined to the card by a line. A click on the card or a row
        takes that unit up by itself (docs/COUNTERS.md)."""
        x, y, w, h = rect
        lead = next((m for m in group if m["type"] == "hq"), None)
        units = [m for m in group if m is not lead]
        nation = session.nation[u["id"]]
        card = pygame.Rect(x, y, w, 50)
        key = ("roster", nation, w)
        if key not in self.faces:
            self.faces[key] = slab(T.FACE[nation], w, card.h, 4, 10)
        surface.blit(self.shadow(w, card.h, 4, 10), (x - 2, y - 1))
        surface.blit(self.faces[key], card)
        self.notch(surface, session, u["id"], x, y, w, 90, 6)
        flies = session.flag[u["id"]]
        if ("flag", flies) not in self.faces:
            self.faces["flag", flies] = flag(flies, *T.FLAG)
        spot = pygame.Rect((x + 10, y + 11), T.FLAG)
        surface.blit(self.faces["flag", flies], spot)
        self.tips.append((spot, T.FLAG_NAME[flies]))
        room = w - T.FLAG[0] - 62
        if ui.editing is not None:                                   # the name being changed: the words typed
            box = pygame.Rect(spot.right + 8, y + 6, room + 4, 22)
            pygame.draw.rect(surface, (255, 255, 255), box, border_radius=4)
            pygame.draw.rect(surface, T.PATH, box, 2, border_radius=4)
            caret = "|" if pygame.time.get_ticks() // 400 % 2 == 0 else ""
            self.text(surface, ui.editing + caret, (box.x + 4, box.y + 2), 14, bold=True)
        else:
            self.fitted(surface, session.group_name(u["id"]), (spot.right + 10 + room / 2, y + 17), 16, T.MARK[nation], room, 11)
        under = (lead["name"] + ", " if lead and lead["name"] != session.group_name(u["id"]) else "") + \
            f"{len(group)} units: one order moves them all"
        self.fitted(surface, under, (spot.right + 10 + room / 2, y + 36), 11, T.MARK[nation], room, 9)
        self.pencil_rect = pygame.Rect(x + w - 30, y + 14, 22, 22)  # a pencil: its body, and its point
        r = self.pencil_rect
        pygame.draw.rect(surface, T.BUTTON, r, border_radius=4)
        pygame.draw.rect(surface, T.INK, r, 1, border_radius=4)
        pygame.draw.line(surface, T.INK, (r.x + 15, r.y + 5), (r.x + 8, r.y + 12), 4)
        pygame.draw.polygon(surface, T.INK, [(r.x + 5, r.y + 17), (r.x + 6, r.y + 12), (r.x + 10, r.y + 16)])
        self.tips.append((r, "Change the name. Enter keeps it; Escape leaves it."))
        if lead:
            self.member_rects[lead["id"]] = pygame.Rect(x, y, w - 36, card.h)
            self.tips.append((self.member_rects[lead["id"]], f"{lead['name']}: its headquarters. Click to order it by itself."))
        if not units:
            return
        trunk, top = x + 10, card.bottom + 10
        pygame.draw.line(surface, T.INK, (trunk, card.bottom), (trunk, top + (len(units) - 1) * 37 + 16), 1)
        for k, m in enumerate(units):
            row = pygame.Rect(x + 20, top + k * 37, w - 22, 33)
            pygame.draw.line(surface, T.INK, (trunk, row.centery), (row.x, row.centery), 1)
            pygame.draw.rect(surface, (250, 244, 228), row, border_radius=3)
            pygame.draw.rect(surface, T.GRID, row, 1, border_radius=3)
            nation = session.nation[m["id"]]
            icon = pygame.Rect(row.x + 4, row.y + 4, 35, 25)
            sprite = self.sprite(nation, m["type"], icon.size, session.counter_art.get(m["id"]))
            if sprite:
                surface.blit(sprite, icon)
            else:
                picture(surface, m["type"], icon, T.INK, T.PAPER)
            self.fitted(surface, T.short(m["name"]), (row.x + 118, row.centery - 1),
                        12, T.INK, 148, 10)
            self.text(surface, str(m["steps"]), (row.right - 47, row.y + 8), 13, T.INK, True)
            pygame.draw.rect(surface, T.GOOD if m["traced"] else T.SHORT,
                             (row.right - 20, row.y + 7, 8, 19), border_radius=2)
            self.member_rects[m["id"]] = row
            self.tips.append((row, f"{m['name']}: {T.strength_tip(m)}. Click to order it by itself."))

    def mini_tile(self, surface, session, m, rect):
        """One unit of a group in its order of battle: a small tile with its short name in its
        nation's band, its picture, its strength and a mark if anything is wrong."""
        nation, (x, y, w, h) = session.nation[m["id"]], rect
        key = ("mini", nation, w, h)
        if key not in self.faces:
            self.faces[key] = slab(T.TILE, w, h, 3, 8, band=T.FACE[nation], strip=17)
        surface.blit(self.shadow(w, h, 3, 8), (x - 2, y - 1))
        surface.blit(self.faces[key], rect)
        self.fitted(surface, T.short(m["name"]), (x + w / 2, y + 9), 12, T.MARK[nation], w - 8, 8)
        words = T.strength(m).replace("about ", "")
        pic_h = max(14, h - 17 - 20)
        art = (min(w - 10, pic_h * 5 // 3), min(pic_h, (w - 10) * 3 // 5))
        place = pygame.Rect(0, 0, *art)
        place.center = (x + w // 2, y + 17 + pic_h // 2 + 1)
        sprite = self.sprite(nation, m["type"], art, session.counter_art.get(m["id"]))
        if sprite:
            surface.blit(sprite, place)
        else:
            picture(surface, m["type"], place.inflate(-6, -4), T.INK, T.TILE)
        self.fitted(surface, words, (x + w / 2, y + h - 10), 12, T.strength_colour(m), w - 8, 8)
        self.badge(surface, problem([m]), (x + w - 9, y + 26), 7)
        self.member_rects[m["id"]] = rect
        self.tips.append((rect, f"{m['name']}: {T.strength_tip(m)}. Click to order it by itself."))

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

    def intelligence(self, surface, session, members, x, y, w, foot):
        """Compact field-ledger facts derived from the selected formation, never mockup data."""
        if not members or y + 118 > foot:
            return y
        formation = [m for m in members if m["type"] != "hq"] or members
        steps = sum(m["steps"] for m in formation)
        maximum = sum(m.get("max", m["steps"]) for m in formation)
        supplied = all(m["traced"] and not m["out_of_stores"] for m in members)
        hx, hy = members[0]["hex"]
        terrain = T.TERRAIN_NAME[session.gmap.terrain[hy][hx]].title()
        weather = session.weather.title() if session.weather else "—"
        facts = (("STRENGTH", f"{steps} / {maximum} steps"),
                 ("SUPPLY", "In supply" if supplied else "Short of supply"),
                 ("MOVEMENT", f"{session.allowance(members)} MP this turn"),
                 ("TERRAIN / WEATHER", f"{terrain} · {weather}"))
        pygame.draw.line(surface, T.GRID, (x, y), (x + w, y), 2)
        self.text(surface, "FIELD INTELLIGENCE", (x, y + 8), 12, T.DIM, True, serif=True)
        top = y + 30
        for n, (title, value) in enumerate(facts):
            col, row = n % 2, n // 2
            box = pygame.Rect(x + col * (w // 2), top + row * 44, w // 2 - 5, 42)
            pygame.draw.rect(surface, (247, 239, 220), box, border_radius=3)
            pygame.draw.rect(surface, T.GRID, box, 1, border_radius=3)
            self.text(surface, title, (box.x + 9, box.y + 5), 10, T.DIM, True)
            self.fitted(surface, value, (box.centerx, box.y + 28), 13,
                        T.SHORT if title == "SUPPLY" and not supplied else T.INK, box.w - 15, 10)
        return top + 88

    def panel(self, surface, session, ui, rect):
        pygame.draw.rect(surface, T.PAPER, rect)
        for grain_y in range(rect.y + 68, rect.bottom, 8):
            pygame.draw.line(surface, (235, 225, 203), (rect.x + 1, grain_y), (rect.right - 1, grain_y))
        pygame.draw.line(surface, T.INK, rect.topleft, rect.bottomleft, 2)
        view, over = session.view, session.state["over"]
        x, y, w = rect.x + EDGE, rect.y + 12, rect.w - 2 * EDGE
        foot = tabs(surface.get_size())["remind"].y - 8             # the text stops above the reminder box and the two buttons
        under = HEAD_Y + T.TILE_H + 12

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

        band = pygame.Rect(rect.x, rect.y, rect.w, T.MASTHEAD)
        pygame.draw.rect(surface, T.COMMAND[session.side], band)
        flies = "uk" if session.side == "cw" else "de"
        badge = ("side_badge", flies)
        if badge not in self.faces:
            self.faces[badge] = flag(flies, 38, 28)
        surface.blit(self.faces[badge], (x, band.y + 12))
        side_line = ("LAST TURN · WATCH" if self.playing else "BATTLE CONCLUDED" if over
                     else f"{T.SIDE_NAME[session.side].upper()}  ·  GIVE ORDERS")
        self.text(surface, side_line, (x + 50, band.y + 16), 15, T.PAPER, True, serif=True)
        pygame.draw.line(surface, T.GRID, band.bottomleft, band.bottomright, 2)
        self.text(surface, "Unit Details", (x, 65), 24, T.INK, True, serif=True)
        self.text(surface, f"{session.day:%d %B %Y}  ·  TURN {min(view['turn'], session.scenario['turns'])} / {session.scenario['turns']}",
                  (x, 103), 12, T.DIM, True)
        self.text(surface, f"AXIS {view['vp']['axis']}    COMMONWEALTH {view['vp']['cw']}", (x, 124), 11, T.DIM)
        pygame.draw.line(surface, T.GRID, (x, 143), (x + w, 143), 1)

        u = None if self.playing or ui.cover else session.unit(ui.selected)
        group = session.members(u["id"]) if u else []
        self.member_rects, self.report_rects, self.back_rect, self.tips = {}, {}, None, []
        self.pencil_rect, self.scroll_rects, self.cycle_rects = None, {}, {}
        if not over and not self.playing:                            # the tabs: this unit, or every unit's order
            for name, words in (("unit", "Unit"), ("orders", "Unit orders"), ("timetable", "Timetable")):
                r = tabs(surface.get_size())[name]
                on = ui.tab == name
                pygame.draw.rect(surface, T.PAPER if on else T.BUTTON, r, border_top_left_radius=6, border_top_right_radius=6)
                pygame.draw.rect(surface, T.INK, r, 2 if on else 1, border_top_left_radius=6, border_top_right_radius=6)
                self.text(surface, words, r.center, 13, T.INK if on else T.DIM, on, True, serif=True)
                due = session.due_now() if name == "timetable" else 0
                if due:                                              # what the timetable does as this turn ends: plan for it now
                    spot = (r.right - 9, r.y + 3)
                    pygame.draw.circle(surface, T.SHORT, spot, 10)
                    pygame.draw.circle(surface, T.INK, spot, 10, 1)
                    self.text(surface, str(due), spot, 12, T.PAPER, True, True)
                    self.tips.append((pygame.Rect(spot[0] - 10, spot[1] - 10, 20, 20),
                                      f"{T.count(due, 'timetable event')} at the end of this turn: plan for {'it' if due == 1 else 'them'} now."))
            y = tabs(surface.get_size())["unit"].bottom + 10
            if ui.tab != "unit":
                (self.orders_list if ui.tab == "orders" else self.timetable_list)(surface, session, ui, x, y, w, foot)
                return
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
        elif u and len(group) > 1 and not ui.alone:                  # a group: its order of battle, and what binds them
            area = pygame.Rect(x, y, w, max(T.TILE_H, 64 + (len(group) - 1) * 37))
            pygame.draw.rect(surface, T.SELECT, area.inflate(10, 10), 3, border_radius=14)          # the one taken up
            self.roster(surface, session, ui, u, group, area)
            y = area.bottom + 12
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
                if u["id"] in session.waiting_units():
                    line("From an earlier turn. Space keeps it.", 12, T.DIM)
            else:
                line("Order: Hold", 15, T.PATH, True, gap=2)
            self.cannot(session, ui, u, line, w)
            line("Click a row above to order that unit by itself.", 12, T.DIM)
            y = self.intelligence(surface, session, group, x, y + 5, w, foot)
        elif u:
            card = pygame.Rect(x, y, w, T.TILE_H)                    # its tile is its header: the orders are under it
            pygame.draw.rect(surface, T.SELECT, card.inflate(10, 10), 3, border_radius=18)                  # the one taken up
            self.tile(surface, session, u, card)
            y = under
            if u["type"] == "hq":
                line(f"Dump: {u['dump']['fuel']} t fuel, {u['dump']['stores']} t stores", 13)
            if not u["traced"]:
                line("OUT OF SUPPLY: no HQ or port in reach", 13, T.SHORT, True)
            elif u["out_of_stores"]:
                line("OUT OF STORES: morale is falling", 13, T.SHORT, True)
            else:
                line("In supply", 13, T.GOOD, True)
            grouped = ui.alone and len(session.members(session.leader(u["id"]))) > 1
            stops = session.stack(u["id"])
            if grouped:                                              # chosen from a group: the button back to it says so
                self.back_rect = pygame.Rect(x, y + 2, 150, 26)
                pygame.draw.rect(surface, T.BUTTON, self.back_rect, border_radius=5)
                pygame.draw.rect(surface, T.INK, self.back_rect, 1, border_radius=5)
                self.text(surface, "< Back to group", self.back_rect.center, 13, bold=True, centre=True)
                self.tips.append((self.back_rect, "This unit was chosen from its group. Go back to the whole group."))
            if len(stops) > 1:                                       # more of yours in its hex: which this is, an arrow each way
                now = (u["id"], True) if ui.alone else (session.leader(u["id"]), False)
                chip = pygame.Rect(x + 160, y + 2, 96, 26)           # to the right of Back to group, clear of the tile
                pygame.draw.rect(surface, T.BUTTON, chip, border_radius=5)
                pygame.draw.rect(surface, T.INK, chip, 1, border_radius=5)
                self.text(surface, f"{stops.index(now) + 1 if now in stops else 1} of {len(stops)}", chip.center, 13, bold=True, centre=True)
                for step, cx in ((-1, chip.x + 11), (1, chip.right - 11)):
                    pygame.draw.polygon(surface, T.INK, [(cx + 5 * step, chip.centery), (cx - 3 * step, chip.centery - 6), (cx - 3 * step, chip.centery + 6)])
                    self.cycle_rects[step] = pygame.Rect(chip.x if step < 0 else chip.centerx, chip.y, chip.w // 2, chip.h)
                self.tips.append((chip, "The units of yours in this hex. The arrows, the mouse wheel over the tile, or Page Up and Page Down go through them."))
            if grouped or len(stops) > 1:
                y += 34
            if u["id"] in session.pending[session.side]:
                order = session.order_of(u["id"])
                turns = session.turns_to_go(u["id"])
                more = f", about {turns} turns" if turns and turns > 1 else ""
                line(f"Order: {T.ORDER_NAME[order['order']]}{more}", 15, T.PATH, True, gap=2)
                line("From an earlier turn. Space keeps it." if u["id"] in session.waiting_units()
                     else T.ORDER_HELP[order["order"]], 12, T.DIM)
            elif ui.alone:
                line("An order now splits it off. Split leaves it here.", 12, T.DIM)
            else:
                line("Order: Hold", 15, T.PATH, True, gap=2)
                line("With no other order it holds. Space goes on.", 12, T.DIM)
            self.cannot(session, ui, u, line, w)
            y = self.intelligence(surface, session, [u], x, y + 8, w, foot)
        elif not over and not self.playing:                          # nothing taken up: who still waits, each a tap away
            waiting = session.waiting_units()
            line(f"{T.count(len(waiting), 'unit')} still to go through" if waiting
                 else "Every unit gone through. Press End turn.", 15, T.PATH, True, gap=8)
            room = max(0, (foot - y) // 2 // 25)                     # the top half of the space; reports have the rest
            for uid in waiting[:room]:
                m = session.unit(uid)
                nation = session.nation[uid]
                row = pygame.Rect(x, y, w, 23)
                pygame.draw.rect(surface, T.BUTTON, row, border_radius=4)
                mini = pygame.Rect(x + 3, y + 2, 30, 19)
                pygame.draw.rect(surface, T.FACE[nation], mini, border_radius=3)
                show = next((g for g in session.members(uid) if g["type"] != "hq"), m)
                picture(surface, show["type"], mini.inflate(-6, -5), T.MARK[nation], T.FACE[nation])
                words = row_name(session, m)
                while self.font(12).size(words)[0] > w - 64:                 # as much of the name as fits
                    words = words[:-1]
                self.text(surface, words, (x + 40, y + 4), 12)
                self.badge(surface, problem(session.members(uid)), (row.right - 12, row.centery), 8)
                self.report_rects[("wait", uid)] = (row, uid)
                y += 25
            if len(waiting) > room:
                line(f"and {len(waiting) - room} more: press Next unit.", 12, T.DIM)
            carrying = len(waiting) - len(session.idle_units())
            if carrying:                                             # those with a standing order: seen, then kept or changed
                line(f"{carrying} of them {'carries on with its order' if carrying == 1 else 'carry on with their orders'}; "
                     "the rest hold.", 12, T.DIM)
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
        self.panel_content_bottom = max(y + 8, under + 8)

    def frame(self, surface, session, ui, stage=None):
        a = areas(surface.get_size(), ui.details_collapsed)
        self.playing = stage is not None
        ui.preview = ""
        if stage:
            self.stage(surface.subsurface(a["map"]), session, ui, stage)
        elif ui.cover:
            pygame.draw.rect(surface, T.INK, a["map"])
            self.text(surface, ui.cover, a["map"].center, 26, T.PAPER, True, True)
        else:
            self.map(surface.subsurface(a["map"]), session, ui)
        if ui.details_collapsed:
            self.panel_scroll_max, self.panel_body, self.panel_scroll_rects = 0, None, {}
            self.member_rects, self.report_rects, self.back_rect, self.pencil_rect = {}, {}, None, None
            self.cycle_rects, self.scroll_rects, self.tips = {}, {}, []
        elif a["panel"].h < 780 and ui.tab == "unit":
            self.compact_panel(surface, session, ui, a["panel"])
        else:
            self.panel_scroll_max, self.panel_body, self.panel_scroll_rects = 0, None, {}
            self.order_rects = buttons(surface.get_size())
            self.panel(surface, session, ui, a["panel"])
        self.masthead(surface, session, ui, a["map"])
        self.bar(surface, session, ui, a["bar"])
        self.buttons(surface, session, ui)
        self.air_orders(surface, session, ui)
        if not stage:
            toggle = details_toggle(surface.get_size(), ui.details_collapsed)
            pygame.draw.rect(surface, T.PAPER, toggle, border_radius=4)
            pygame.draw.rect(surface, T.INK, toggle, 1, border_radius=4)
            arrow = ">" if ui.details_collapsed else "<"
            self.text(surface, arrow, toggle.center, 20, T.INK, True, True)
            self.tips.append((toggle, "Show unit details" if ui.details_collapsed else "Hide unit details"))
        if not stage:
            self.tip(surface, ui)

    def compact_panel(self, surface, session, ui, panel):
        logical_size = (surface.get_width(), max(T.WINDOW[1] + T.CONSOLE, surface.get_height()))
        if self.panel_canvas is None or self.panel_canvas.get_size() != logical_size:
            self.panel_canvas = pygame.Surface(logical_size)
        canvas = self.panel_canvas
        self.panel_content_bottom = None
        self.panel(canvas, session, ui, areas(logical_size)["panel"])
        top = tabs(surface.get_size())["unit"].bottom + 10
        bottom = tabs(surface.get_size())["remind"].y - 8
        body = pygame.Rect(panel.x, top, panel.w, bottom - top)
        logical_bottom = tabs(logical_size)["remind"].y - 8
        self.panel_scroll_max = max(0, min(logical_bottom, self.panel_content_bottom or logical_bottom) - bottom)
        subject = (ui.selected, ui.alone, ui.tab)
        if subject != self.panel_subject:
            ui.panel_scroll = 0
        self.panel_subject = subject
        ui.panel_scroll = max(0, min(ui.panel_scroll, self.panel_scroll_max))
        self.panel_body = body
        surface.blit(canvas, panel.topleft, pygame.Rect(panel.x, 0, panel.w, top))
        surface.blit(canvas, body.topleft, body.move(0, ui.panel_scroll))
        pygame.draw.rect(surface, T.PAPER, (panel.x, bottom, panel.w, panel.bottom - bottom))
        pygame.draw.line(surface, T.INK, panel.topleft, panel.bottomleft, 2)

        def visible(rect):
            moved = rect.move(0, -ui.panel_scroll)
            return moved.clip(body) if moved.colliderect(body) else None

        self.order_rects = buttons(surface.get_size())
        self.member_rects = {key: moved for key, rect in self.member_rects.items() if (moved := visible(rect))}
        self.cycle_rects = {key: moved for key, rect in self.cycle_rects.items() if (moved := visible(rect))}
        self.scroll_rects = {key: moved for key, rect in self.scroll_rects.items() if (moved := visible(rect))}
        self.report_rects = {key: (moved, uid) for key, (rect, uid) in self.report_rects.items()
                             if (moved := visible(rect))}
        self.back_rect = visible(self.back_rect) if self.back_rect else None
        self.pencil_rect = visible(self.pencil_rect) if self.pencil_rect else None
        self.tips = [(shown, words) for rect, words in self.tips
                     if (shown := rect if rect.bottom <= body.top else visible(rect))]

        self.panel_scroll_rects = {}
        if not self.panel_scroll_max:
            return
        for name, y, points in (("up", body.top + 6, ((8, 5), (3, 16), (13, 16))),
                                ("down", body.bottom - 30, ((3, 7), (13, 7), (8, 18)))):
            rect = pygame.Rect(panel.right - 18, y, 16, 24)
            self.panel_scroll_rects[name] = rect
            usable = ui.panel_scroll > 0 if name == "up" else ui.panel_scroll < self.panel_scroll_max
            pygame.draw.rect(surface, T.BUTTON if usable else T.PAPER, rect, border_radius=4)
            pygame.draw.rect(surface, T.INK if usable else T.DIM, rect, 1, border_radius=4)
            pygame.draw.polygon(surface, T.INK if usable else T.DIM,
                                [(rect.x + x, rect.y + y) for x, y in points])



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
