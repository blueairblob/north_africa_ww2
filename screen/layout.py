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


def buttons(size):
    """name -> its rectangle in the window."""
    bar = areas(size)["bar"]
    gap, n = 6, len(T.BUTTONS)
    w = (bar.w - gap * (n + 3)) // n
    out, x = {}, bar.x + gap
    for i, (name, _, _) in enumerate(T.BUTTONS):
        if i in (6, 8):
            x += gap * 2                            # a little space before the overlays and End turn
        out[name] = pygame.Rect(x, bar.y + 30, w, bar.h - 36)
        x += w + gap
    return out
