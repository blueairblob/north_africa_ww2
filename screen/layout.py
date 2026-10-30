"""Where hexes are on the screen: the generator's hex geometry, in pixels."""
import pygame

from mapgen import hexgrid as H

from . import theme as T


class Layout:
    """Hex geometry at so many pixels across a hex. Positions are map pixels: the map's
    north-west corner is (0, 0)."""
    def __init__(self, hex_px):
        self.hex_px = hex_px
        self.scale = hex_px / (2 * H.SIZE)          # pixels per kilometre

    def centre(self, h):
        x, y = H.centre(h[0], h[1])
        return x * self.scale, y * self.scale

    def hex_at(self, x, y):
        return H.hex_at(x / self.scale, y / self.scale)

    def corners(self, h):
        return [(x * self.scale, y * self.scale) for x, y in H.corners(h[0], h[1])]

    def side_ends(self, hexside):
        a, b, _ = H.edge(*hexside)
        return (a[0] * self.scale, a[1] * self.scale), (b[0] * self.scale, b[1] * self.scale)

    def size(self, cols, rows):
        """The size of the whole map, as mapgen.render.draw_map makes it."""
        return (int((H.COL_STEP * cols + H.SIZE) * self.scale) + 2,
                int((H.ROW_STEP * (rows + 0.5)) * self.scale) + 2)

    @property
    def counter(self):
        return int(self.hex_px * T.COUNTER)


def areas(size, collapsed=False):
    """The map, message line, optional details panel, and persistent command console."""
    w, h = size
    pw = 0 if collapsed else T.PANEL
    return {"map": pygame.Rect(0, 0, w - pw, h - T.CONSOLE - T.BAR),
            "bar": pygame.Rect(0, h - T.CONSOLE - T.BAR, w - pw, T.BAR),
            "panel": pygame.Rect(w - pw, 0, pw, h - T.CONSOLE),
            "console": pygame.Rect(0, h - T.CONSOLE, w, T.CONSOLE)}


def playback_controls(size, collapsed=False, spectator=False):
    """Small replay actions in the command footer, clear of the battlefield."""
    area = areas(size, collapsed)["console"]
    names = ("pause", "back", "next", "speed", "skip") if spectator else ("back", "next", "speed", "skip")
    widths, gap = tuple(48 if name != "skip" else 55 for name in names), 2
    x = area.right - sum(widths) - gap * (len(names) - 1) - 20
    y = area.centery - 16
    return {name: pygame.Rect(x + sum(widths[:n]) + gap * n, y, widths[n], 32)
            for n, name in enumerate(names)}


def title_button(size):
    """The single start action on the opening card; window X remains the exit."""
    w, h = size
    return pygame.Rect(w // 2 - 122, h // 2 + 170, 244, 48)


BUTTON_H, GAP, EDGE = 36, 7, 22
TABS_Y, TAB_H = 148, 30  # below the command-side header, date and score
HEAD_Y = TABS_Y + TAB_H + 10                # the header of the unit taken up: its tile, or a group's name and units
ORDERS_Y = HEAD_Y + T.TILE_H + 12           # legacy unit-header baseline for details text


def footer_flag(size):
    """The side/formation flag, sized to read without taking space from the orders."""
    console = areas(size)["console"]
    identity = min(280, max(168, console.w // 5))
    w, h = (64, 44) if identity >= 240 else (52, 38)
    return pygame.Rect(console.x + 14, console.centery - h // 2, w, h)


def buttons(size):
    """Stable, responsive command-console rectangles (including disabled orders)."""
    console = areas(size)["console"]
    names = [b[0] for b in T.BUTTONS]
    identity = min(280, max(168, console.w // 5))
    navigation = min(256, max(170, console.w // 5))
    x0, right = identity + 12, console.right - navigation - 12
    width = right - x0
    columns = 9 if width >= 765 else 5
    rows = 1 if columns == 9 else 2
    cell = (width - GAP * (columns - 1)) // columns
    height = 44 if rows == 1 else 37
    top = console.y + (console.h - height * rows - GAP * (rows - 1)) // 2
    out = {}
    for i, name in enumerate(names[:9]):
        out[name] = pygame.Rect(x0 + (i % columns) * (cell + GAP),
                                top + (i // columns) * (height + GAP), cell, height)
    half = (navigation - GAP) // 2
    out[names[9]] = pygame.Rect(right + 6, console.y + 25, half, 50)
    out[names[10]] = pygame.Rect(right + 6 + half + GAP, console.y + 25, half, 50)
    return out


def tabs(size):
    """The panel's three tabs and, at its foot, the box to tick for a
    reminder of units with no order: name -> rectangle."""
    panel = areas(size)["panel"]
    x0, w = panel.x + EDGE, panel.w - 2 * EDGE
    third = (w - 2 * GAP) // 3
    foot = panel.bottom - 8
    out = {name: pygame.Rect(x0 + n * (third + GAP), panel.y + TABS_Y, third, TAB_H)
           for n, name in enumerate(("unit", "orders", "timetable"))}
    out["remind"] = pygame.Rect(x0, foot - 28, w, 22)
    return out


def details_toggle(size, collapsed=False):
    """A visible disclosure at the right edge of the map, in either panel state."""
    edge = areas(size, collapsed)["map"].right
    return pygame.Rect(edge - 29, T.MASTHEAD + 8, 28, 34)


def game(size, opened, collapsed=False):
    """The Game button beside Layers and, when opened, a row above it for each thing it does:
    name -> rectangle. The button itself is "game"."""
    area = areas(size, collapsed)["map"]
    out = {"game": pygame.Rect(area.x + 124, area.bottom - 46, 92, 34)}
    if opened:
        for n, (name, _, _) in enumerate(reversed(T.GAME)):
            out[name] = pygame.Rect(area.x + 124, area.bottom - 46 - (n + 1) * 36, 170, 32)
    return out


def saves_list(size, n, collapsed=False):
    """The list of saved games, over the middle of the map: "box", a row for each numbered
    from 0, and "close"."""
    area = areas(size, collapsed)["map"]
    box = pygame.Rect(0, 0, min(860, area.w - 40), 46 + max(n, 1) * 36 + 50)
    box.center = area.center
    out = {"box": box, "close": pygame.Rect(box.centerx - 60, box.bottom - 44, 120, 34)}
    for k in range(n):
        out[k] = pygame.Rect(box.x + 10, box.y + 42 + k * 36, box.w - 20, 32)
    return out


def layers(size, opened, collapsed=False):
    """The Layers button in the map's bottom-left corner and, when opened, a row above it for
    each layer: name -> rectangle. The button itself is "layers"."""
    area = areas(size, collapsed)["map"]
    out = {"layers": pygame.Rect(area.x + 12, area.bottom - 46, 104, 34)}
    if opened:
        names = ("k", "weather", "s", "z", "pictures", "nato")
        for n, name in enumerate(reversed(names)):
            out[name] = pygame.Rect(area.x + 12, area.bottom - 46 - (n + 1) * 36, 150, 32)
    return out


def air_controls(size, opened=False, collapsed=False):
    """Persistent air-effort selector in the message strip; choices rise over the map."""
    area = areas(size, collapsed)["bar"]
    button = pygame.Rect(area.right - 206, area.y + 2, 194, area.h - 4)
    out = {"air": button}
    if opened:
        for n, choice in enumerate(("support", "interdict", "recon")):
            out[choice] = pygame.Rect(button.right - 250, button.top - 8 - (3 - n) * 39, 250, 37)
    return out
