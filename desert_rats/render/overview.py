"""Full-map strategic overview: terrain-code legend colours + unit dots,
in the style of the `pubmap_units.png` reference image the person supplied.

This is deliberately NOT a fidelity claim about the original ZX Spectrum
display -- see `image.py`'s docstring and NOTES.md for why. Two things are
true at once:

1. `image.py` / `terminal.py` render the *confirmed* in-game colour model
   (mostly desert-yellow paper, sea as the one distinct exception) because
   that's what the original screen actually showed.
2. This module renders a *different, additional* artifact: a labelled
   campaign-overview map, useful the way a paper map alongside a wargame
   is useful, not because it reproduces the original's screen. Its palette
   reuses the exact 16 colours sampled from data/terrain_authentic.png (one
   solid colour per terrain code 0-15) purely so this overview is visually
   comparable to that reference image and to pubmap_units.png -- it is
   still the extraction tooling's debug legibility legend, not recovered
   game data (see image.py's docstring for the full account).

Real-world place names are OFF by default (`labels=False`). When enabled,
`APPROXIMATE_TOWN_COLUMNS` places them at grid columns estimated from
real-world coastal road distances between El Agheila and Alexandria -- a
geographic approximation for orientation, not anything decoded from the
game (BUILD_SPEC.md §10 / reference/prospects.md #11 both still list
terrain point-feature naming as unrecovered). Treat these positions as
illustrative; override with your own `town_columns` dict if you have
better ones.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional

from ..board import Board
from ..data import Nationality
from ..units import Unit

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - exercised only without Pillow
    raise ImportError(
        "render.overview requires Pillow: pip install desert-rats[image]"
    ) from exc

# Sampled directly from data/terrain_authentic.png (one solid RGB per
# terrain code, confirmed 100% consistent across all cells of that code in
# that image) -- see this module's docstring. NOT the recovered in-game
# attribute table (still unrecovered; reference/prospects.md #12).
TERRAIN_LEGEND_COLOUR = {
    0: (214, 197, 110),   # desert (open)
    1: (198, 175, 70),    # rough / coastal strip
    2: (150, 80, 40),     # escarpment (E-W ridge)
    3: (120, 64, 30),     # escarpment / coastal ridge
    4: (90, 110, 50),     # coastal feature (town?)
    5: (60, 60, 60),      # road/track
    6: (130, 130, 130),   # coastal point (town/port)
    7: (160, 160, 160),   # coastal point (town)
    8: (195, 195, 195),   # inland point (oasis/fort)
    9: (95, 158, 160),    # coastal point
    10: (224, 190, 140),  # port / coastal town
    11: (200, 130, 60),   # broken / rough ground
    12: (70, 130, 180),   # coastal point
    13: (112, 128, 144),  # inland point (oasis/fort)
    14: (12, 50, 200),    # sea (impassable)
    15: (230, 230, 230),  # isolated key point (objective marker?)
}

# BUILD_SPEC.md §8 / graphics.json side_ink_table -- reused from image.py
# for consistency between the tactical and overview renderers.
NATION_DOT_COLOUR = {
    Nationality.BRITISH: (30, 60, 255),
    Nationality.GERMAN: (20, 20, 20),
    Nationality.ITALIAN: (230, 30, 200),
}

# See module docstring: approximate grid columns (0-100) for orientation
# only, estimated from real-world coastal road distances, NOT decoded game
# data. Pass your own `town_columns` to render_overview_image() to override.
APPROXIMATE_TOWN_COLUMNS: Dict[str, int] = {
    "El Agheila": 0,
    "Agedabia": 9,
    "Benghazi": 22,
    "Barce": 32,
    "Derna": 37,
    "Gazala": 54,
    "Tobruk": 58,
    "Bardia": 64,
    "Sidi Barani": 70,
    "Matruh": 77,
    "El Alamein": 94,
    "Alexandria": 100,
}
# All labelled towns sit on/near the coast in the reference image.
TOWN_LABEL_ROW = 2


def _load_font(size: int) -> "ImageFont.ImageFont":
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def render_overview_image(
    units: Iterable[Unit],
    board: Board,
    cell_px: int = 8,
    labels: bool = False,
    town_columns: Optional[Dict[str, int]] = None,
    dot_radius: Optional[int] = None,
) -> "Image.Image":
    """Whole-board overview: terrain-legend colours + a small dot per
    living unit, coloured by nationality. `labels=True` adds the
    approximate town-name annotation layer (see module docstring).
    """
    width_px, height_px = board.width * cell_px, board.height * cell_px
    img = Image.new("RGB", (width_px, height_px), TERRAIN_LEGEND_COLOUR[0])
    draw = ImageDraw.Draw(img)

    for y in range(board.height):
        for x in range(board.width):
            terrain_type = board.terrain_at(x, y)
            colour = TERRAIN_LEGEND_COLOUR.get(terrain_type, TERRAIN_LEGEND_COLOUR[0])
            px0, py0 = x * cell_px, y * cell_px
            draw.rectangle([px0, py0, px0 + cell_px, py0 + cell_px], fill=colour)

    dot_radius = dot_radius if dot_radius is not None else max(2, cell_px // 3)
    for unit in units:
        if unit.is_destroyed:
            continue
        cells = list(unit.footprint_cells())
        cx = sum(c[0] for c in cells) / len(cells) + 0.5
        cy = sum(c[1] for c in cells) / len(cells) + 0.5
        px, py = cx * cell_px, cy * cell_px
        colour = NATION_DOT_COLOUR[unit.nationality]
        draw.ellipse(
            [px - dot_radius, py - dot_radius, px + dot_radius, py + dot_radius],
            fill=colour,
            outline=(255, 255, 255),
        )

    if labels:
        columns = town_columns if town_columns is not None else APPROXIMATE_TOWN_COLUMNS
        font = _load_font(max(10, cell_px))
        for name, col in columns.items():
            x = min(max(col, 0), board.width - 1) * cell_px
            y = TOWN_LABEL_ROW * cell_px
            draw.text((x, y), name, fill=(255, 255, 255), font=font,
                      stroke_width=1, stroke_fill=(0, 0, 0))

    return img


def save_overview_image(
    units: Iterable[Unit],
    board: Board,
    path: str,
    cell_px: int = 8,
    labels: bool = False,
    town_columns: Optional[Dict[str, int]] = None,
) -> str:
    img = render_overview_image(units, board, cell_px=cell_px, labels=labels, town_columns=town_columns)
    img.save(path)
    return path
