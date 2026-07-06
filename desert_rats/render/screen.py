"""Authentic screen composer: the original 256x192 play screen, 1:1.

Layout recovered from a real gameplay screenshot by OCR with the game's
own font (see NOTES.md "Authentic screen"):

    +----------------------176px----------------------+---80px---+
    |                                                  | date     |  yellow ink
    |            22x22-cell map viewport               |          |
    |            (pixel-exact tiles + counters)        | order    |  white ink;
    |                                                  | menu     |  selected =
    |                                                  |          |  red paper
    +--------------------------------------------------+----------+
    |  selected unit line (white ink on red paper)   2 cell rows  |
    +--------------------------------------------------------------+

Requires the local-only OG art files (data/tiles_original.json and
data/font_original.json, regenerated from the person's own tape by
reference/extraction_tools/extract_render_tables.py); raises a clear
error otherwise. Only meaningful for the og pack.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .. import packs
from ..board import Board
from ..units import Order, Unit
from .image import render_board_image, _ZX_ATTR_RGB

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    PIL_AVAILABLE = False

SCREEN_W, SCREEN_H = 256, 192
VIEW_CELLS = 22
PANEL_X = VIEW_CELLS * 8          # 176
BOTTOM_Y = VIEW_CELLS * 8         # 176 (two 8px text rows below)

BLACK = _ZX_ATTR_RGB[0]
RED = _ZX_ATTR_RGB[2]
YELLOW = _ZX_ATTR_RGB[6]
WHITE = _ZX_ATTR_RGB[7]

# Panel rows (in 8px character rows), from the screenshot OCR
DATE_ROW = 0
MENU_ROWS = {  # order -> row; None key = the trailing prompt
    Order.HOLD: 8,
}
MENU_LAYOUT = [
    (4, "R REPORT", None),
    (6, "M MOVE", Order.MOVE),
    (7, "A ASSAULT", Order.ASSAULT),
    (8, "H HOLD", Order.HOLD),
    (9, "F FORTIFY", Order.FORTIFY),
    (11, "ENTER TO END", None),
]


def _load_font() -> Optional[list]:
    path = packs.active_pack().resolve("font_original.json")
    if path is None:
        return None
    data = json.loads(Path(path).read_text())
    return data["glyphs"]


def _draw_text(img, glyphs, text: str, x: int, y: int, ink, paper=None) -> None:
    px = img.load()
    for i, ch in enumerate(text):
        code = ord(ch) - 32
        g = glyphs[code] if 0 <= code < len(glyphs) else glyphs[0]
        for r in range(8):
            for c in range(8):
                on = g[r] & (0x80 >> c)
                if on:
                    px[x + i * 8 + c, y + r] = ink
                elif paper is not None:
                    px[x + i * 8 + c, y + r] = paper


def render_screen(
    units,
    board: Board,
    viewport_origin=(0, 0),
    date_lines=("", ""),
    selected_order: Optional[Order] = None,
    status_line: str = "",
    scale: int = 1,
):
    """Compose the authentic 256x192 screen; returns a PIL Image
    (optionally integer-scaled).
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for screen rendering")
    glyphs = _load_font()
    if glyphs is None:
        raise FileNotFoundError(
            "font_original.json not found in the active pack -- regenerate it "
            "locally with reference/extraction_tools/extract_render_tables.py "
            "(og-skin screen rendering needs the local-only art files)"
        )

    img = Image.new("RGB", (SCREEN_W, SCREEN_H), BLACK)

    # map viewport, pixel-exact (8px cells)
    view = render_board_image(
        units, board, origin=viewport_origin, size=VIEW_CELLS, cell_px=8
    )
    img.paste(view.crop((0, 0, PANEL_X, PANEL_X)), (0, 0))

    # side panel
    draw = ImageDraw.Draw(img)
    draw.rectangle([PANEL_X, 0, SCREEN_W - 1, SCREEN_H - 1], fill=BLACK)
    _draw_text(img, glyphs, date_lines[0][:10], PANEL_X + 8, DATE_ROW * 8, YELLOW)
    if len(date_lines) > 1:
        _draw_text(img, glyphs, date_lines[1][:10], PANEL_X + 8, (DATE_ROW + 1) * 8, YELLOW)
    for row, label, order in MENU_LAYOUT:
        if order is not None and order is selected_order:
            # selected order: inverse video, red paper
            draw.rectangle([PANEL_X, row * 8, SCREEN_W - 1, row * 8 + 7], fill=RED)
            _draw_text(img, glyphs, label[:10], PANEL_X, row * 8, BLACK)
        else:
            _draw_text(img, glyphs, label[:10], PANEL_X, row * 8, WHITE)

    # bottom status band: white on red, two character rows
    draw.rectangle([0, BOTTOM_Y, SCREEN_W - 1, SCREEN_H - 1], fill=RED)
    _draw_text(img, glyphs, status_line[:32], 0, BOTTOM_Y, WHITE)

    if scale > 1:
        img = img.resize((SCREEN_W * scale, SCREEN_H * scale), Image.NEAREST)
    return img


def save_screen(path: str, *args, **kwargs) -> None:
    render_screen(*args, **kwargs).save(path)
