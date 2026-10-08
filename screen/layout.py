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


def areas(size):
    """The window's parts: the map, the order bar under it, the panel on the right."""
    w, h = size
    return {"map": pygame.Rect(0, 0, w - T.PANEL, h - T.BAR),
            "bar": pygame.Rect(0, h - T.BAR, w - T.PANEL, T.BAR),
            "panel": pygame.Rect(w - T.PANEL, 0, T.PANEL, h)}


BUTTON_H, GAP, EDGE = 36, 7, 16
TABS_Y, TAB_H = 128, 26  # the panel's tabs: the unit taken up, every unit's order, and the timetable
ORDERS_Y = 230          # where the orders begin in the panel: under the header of the unit taken up


def buttons(size):
    """name -> its rectangle in the window: under the unit's header, the six orders in two rows
    of three and Join, Split and Recall in a third, each always in its own place; and at the
    foot of the panel, Next unit and End turn."""
    panel = areas(size)["panel"]
    names = [b[0] for b in T.BUTTONS]
    x0, w = panel.x + EDGE, panel.w - 2 * EDGE
    third, half = (w - 2 * GAP) // 3, (w - GAP) // 2
    y = panel.y + ORDERS_Y                                               # the orders: under the unit's header
    out = {}
    for i, name in enumerate(names[:9]):
        out[name] = pygame.Rect(x0 + (i % 3) * (third + GAP), y + (i // 3) * (BUTTON_H + GAP), third, BUTTON_H)
    y = panel.bottom - EDGE - BUTTON_H - 6
    out[names[9]] = pygame.Rect(x0, y, half, BUTTON_H + 6)                 # Next unit, and End turn beside it
    out[names[10]] = pygame.Rect(x0 + half + GAP, y, half, BUTTON_H + 6)
    return out


def tabs(size):
    """The panel's three tabs and, above Next unit and End turn, the box to tick for a
    reminder of units with no order: name -> rectangle."""
    panel = areas(size)["panel"]
    x0, w = panel.x + EDGE, panel.w - 2 * EDGE
    third = (w - 2 * GAP) // 3
    foot = buttons(size)["next"].y
    out = {name: pygame.Rect(x0 + n * (third + GAP), panel.y + TABS_Y, third, TAB_H)
           for n, name in enumerate(("unit", "orders", "timetable"))}
    out["remind"] = pygame.Rect(x0, foot - 28, w, 22)
    return out


def game(size, opened):
    """The Game button beside Layers and, when opened, a row above it for each thing it does:
    name -> rectangle. The button itself is "game"."""
    area = areas(size)["map"]
    out = {"game": pygame.Rect(area.x + 124, area.bottom - 46, 92, 34)}
    if opened:
        for n, (name, _, _) in enumerate(reversed(T.GAME)):
            out[name] = pygame.Rect(area.x + 124, area.bottom - 46 - (n + 1) * 36, 170, 32)
    return out


def saves_list(size, n):
    """The list of saved games, over the middle of the map: "box", a row for each numbered
    from 0, and "close"."""
    area = areas(size)["map"]
    box = pygame.Rect(0, 0, min(860, area.w - 40), 46 + max(n, 1) * 36 + 50)
    box.center = area.center
    out = {"box": box, "close": pygame.Rect(box.centerx - 60, box.bottom - 44, 120, 34)}
    for k in range(n):
        out[k] = pygame.Rect(box.x + 10, box.y + 42 + k * 36, box.w - 20, 32)
    return out


def layers(size, opened):
    """The Layers button in the map's bottom-left corner and, when opened, a row above it for
    each layer: name -> rectangle. The button itself is "layers"."""
    area = areas(size)["map"]
    out = {"layers": pygame.Rect(area.x + 12, area.bottom - 46, 104, 34)}
    if opened:
        for n, (name, _, _) in enumerate(reversed(T.LAYERS)):
            out[name] = pygame.Rect(area.x + 12, area.bottom - 46 - (n + 1) * 36, 150, 32)
    return out
