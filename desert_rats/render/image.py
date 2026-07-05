"""PNG map rendering: the confirmed colour model (BUILD_SPEC.md §8, revised
-- see below), drawn as an actual image instead of ANSI text.

Why this module exists: `data/terrain_authentic.png` (a reference asset
bundled with the extraction package) uses a distinct colour for each of the
16 terrain codes. That specific 16-colour palette is **not** recovered game
data -- it's not sourced anywhere in `reference/extraction_tools/`, and was
generated purely for human legibility while reverse-engineering the map
layout (see `overview.py`, which deliberately reuses it for a different,
non-fidelity purpose).

**Revision:** BUILD_SPEC.md §8 originally characterised the real per-cell
paper table (0xD80E) as "mostly PAPER 6 = desert yellow" with nothing else
confirmed. A person-supplied real gameplay screenshot (256x192 -- the
actual ZX Spectrum resolution, not a mockup) disproved the "nothing else"
part: escarpment terrain (types 2/3) renders as a distinct 8x8 tile, red
ink on yellow paper, not flat desert -- see ESCARPMENT_TILE_BYTES below,
extracted pixel-for-pixel from that screenshot. It also confirmed the
22x22 viewport (176px = exactly 22x8) and the exact nation-ink RGB values.
See NOTES.md for the full account and reference/prospects.md #12's status.

Only this module needs Pillow (`pip install desert-rats[image]` /
`pyproject.toml`'s `image` extra); the rest of the engine has zero
third-party dependencies, and the terminal renderer remains the
dependency-free default.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from ..board import Board, DESERT, ESCARPMENT_TYPES, ROAD, SEA, VIEWPORT_SIZE
from ..data import Nationality
from ..units import Unit

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover - exercised only without Pillow
    raise ImportError(
        "render.image requires Pillow: pip install desert-rats[image]"
    ) from exc

# Standard ZX Spectrum hardware RGB values (graphics.json's zx_palette
# names -- these are the well-known hardware colour numbers, not a guess).
_ZX_RGB = {
    0: (0, 0, 0),        # black
    1: (0, 0, 214),      # blue
    2: (214, 0, 0),      # red
    3: (214, 0, 214),    # magenta
    4: (0, 214, 0),      # green
    5: (0, 214, 214),    # cyan
    6: (214, 214, 0),    # yellow
    7: (214, 214, 214),  # white
}
_ZX_BRIGHT_BONUS = 41  # BUILD_SPEC.md §8: "+brightness"


def _zx(code: int, bright: bool = False) -> tuple:
    r, g, b = _ZX_RGB[code]
    if bright and code != 0:
        r, g, b = (min(255, c + _ZX_BRIGHT_BONUS) for c in (r, g, b))
    return (r, g, b)


# BUILD_SPEC.md §8 originally characterised the terrain paper table as
# "mostly PAPER 6 = desert yellow" with nothing else confirmed -- a
# person-supplied real gameplay screenshot (256x192, actual ZX Spectrum
# resolution) DISPROVED that: escarpment terrain (types 2/3) renders as a
# distinct 8x8 tile, red ink on yellow paper, not flat desert. Bytes
# extracted directly from that screenshot (MSB=leftmost pixel, matching
# graphics.json's tile format): repeats every 4 rows.
ESCARPMENT_TILE_BYTES = (0x60, 0x90, 0x09, 0x06, 0x60, 0x90, 0x09, 0x06)
ESCARPMENT_INK = (223, 0, 0)  # sampled directly from the screenshot

# Sampled directly from the same screenshot (not a guess): German ink is
# pure black (matches graphics.json's side_ink_table exactly) and reads
# perfectly clearly against the yellow paper -- unlike the ANSI terminal
# renderer's dark background, there's no legibility problem here to
# substitute around. British ink is a non-bright blue (0,0,162), not the
# brighter blue previously guessed.
NATION_COLOUR = {
    Nationality.BRITISH: (0, 0, 162),
    Nationality.GERMAN: (0, 0, 0),
    Nationality.ITALIAN: (231, 0, 182),
}

PAPER_DESERT = _zx(6)  # confirmed: "mostly PAPER 6 = desert yellow"
PAPER_SEA = _zx(1, bright=True)  # the one other confirmed distinct paper (§8)
# Roads (terrain type 5) are real, confirmed cell data (BUILD_SPEC.md §5.2)
# but their *paper colour* isn't part of the recovered attribute table --
# drawing them as a thin dark line is a legibility aid over real position
# data, not a colour claim about the original.
ROAD_LINE = (90, 78, 40)

GRID_LINE = (0, 0, 0, 40)  # faint, alpha-blended cell separators

# ---------------------------------------------------------------------------
# Authentic render model (recovered from the original tape -- see
# reference/extraction_tools/extract_render_tables.py and NOTES.md).
#
# data/render_model.json (committed): 256-entry attribute table indexed by
# the FULL map cell byte, the full-byte 100x32 tile-index grid, and a
# per-tile ink-coverage fraction.
# data/tiles_original.json (gitignored, local-only -- original pixel art):
# the 256 8-byte tile bitmaps. When present, terrain renders pixel-exact;
# when absent, each cell renders as a paper/ink blend weighted by the
# committed coverage fraction (a close colour approximation with no art).
# ---------------------------------------------------------------------------
# Paths resolve through the active content pack (packs.py): the OG pack
# provides render_model.json (and, locally, tiles_original.json); packs
# without a render model fall back to the flat legend colours below.

# ZX colour number -> RGB, non-bright levels sampled from the real
# gameplay screenshot where observed; standard hardware values otherwise.
_ZX_ATTR_RGB = {
    0: (0, 0, 0), 1: (0, 0, 162), 2: (223, 0, 0), 3: (231, 0, 182),
    4: (0, 199, 0), 5: (0, 199, 199), 6: (210, 210, 0), 7: (202, 202, 202),
}


def _load_render_model():
    """Load (attrs, grid, coverage, tiles_or_None) from the active pack;
    None if the pack provides no render model (renders fall back to the
    flat legend model).
    """
    from .. import packs

    model_path = packs.active_pack().resolve("render_model.json")
    if model_path is None:
        return None
    # A render model describes ONE map: it is only valid if it lives at
    # the same pack level as the terrain. A pack that overrides
    # terrain_logic.json but inherits its parent's render model must NOT
    # have the parent's terrain art painted over its own map.
    terrain_path = packs.active_pack().resolve("terrain_logic.json")
    if terrain_path is not None and terrain_path.parent != model_path.parent:
        return None
    model = json.loads(model_path.read_text())
    tiles = None
    tiles_path = packs.active_pack().resolve("tiles_original.json")
    if tiles_path is not None:
        tiles = json.loads(tiles_path.read_text())["tiles"]
    return (
        model["attribute_table"],
        model["tile_index_grid"],
        model["ink_coverage"],
        tiles,
    )


def _load_features():
    """Atlas feature layer (content_packs/<pack>/features.json): named
    points (town/port/fort/pass), region labels, frontier line. Only
    valid at the same pack level as the terrain it annotates (same rule
    as the render model). Packs without one render terrain only.
    """
    from .. import packs

    fp = packs.active_pack().resolve("features.json")
    if fp is None:
        return None
    tp = packs.active_pack().resolve("terrain_logic.json")
    if tp is not None and tp.parent != fp.parent:
        return None
    return json.loads(fp.read_text())


_features_cache = {}  # pack name -> features dict or None


def _features():
    from .. import packs

    key = packs.active_pack().name
    if key not in _features_cache:
        _features_cache[key] = _load_features()
    return _features_cache[key]


_render_model_cache = {}  # pack name -> model tuple or None


def _render_model():
    from .. import packs

    key = packs.active_pack().name
    if key not in _render_model_cache:
        _render_model_cache[key] = _load_render_model()
    return _render_model_cache[key]


def _attr_colours(attr: int) -> tuple:
    """ZX attribute byte -> (paper_rgb, ink_rgb)."""
    return _ZX_ATTR_RGB[(attr >> 3) & 7], _ZX_ATTR_RGB[attr & 7]


def _blend(paper: tuple, ink: tuple, frac: float) -> tuple:
    return tuple(round(p + (i - p) * frac) for p, i in zip(paper, ink))


def _draw_tile_bitmap(draw, tile_bytes, px0: int, py0: int, cell_px: int, paper, ink) -> None:
    """Draw one 8x8 tile bitmap (MSB=leftmost) scaled to cell_px."""
    draw.rectangle([px0, py0, px0 + cell_px, py0 + cell_px], fill=paper)
    for row in range(8):
        byte = tile_bytes[row]
        if not byte:
            continue
        y0 = py0 + round(row * cell_px / 8)
        y1 = py0 + round((row + 1) * cell_px / 8)
        for col in range(8):
            if byte & (0x80 >> col):
                x0 = px0 + round(col * cell_px / 8)
                x1 = px0 + round((col + 1) * cell_px / 8)
                draw.rectangle([x0, y0, max(x0, x1 - 1), max(y0, y1 - 1)], fill=ink)

# Decode ESCARPMENT_TILE_BYTES (MSB=leftmost pixel) into an 8x8 bool grid
# once, then scale to whatever cell_px the render is using.
_ESCARPMENT_BITS = tuple(
    tuple(bool(byte & (1 << (7 - bit))) for bit in range(8))
    for byte in ESCARPMENT_TILE_BYTES
)


def _draw_escarpment_tile(draw, px0: int, py0: int, cell_px: int) -> None:
    """Draw the real escarpment tile (red hash on the desert paper already
    filled underneath), scaled from its native 8x8 to `cell_px`.
    """
    for row, bits in enumerate(_ESCARPMENT_BITS):
        y0 = py0 + round(row * cell_px / 8)
        y1 = py0 + round((row + 1) * cell_px / 8)
        for col, on in enumerate(bits):
            if not on:
                continue
            x0 = px0 + round(col * cell_px / 8)
            x1 = px0 + round((col + 1) * cell_px / 8)
            draw.rectangle([x0, y0, max(x0, x1 - 1), max(y0, y1 - 1)], fill=ESCARPMENT_INK)


def _terrain_colour(terrain_type: int) -> tuple:
    return PAPER_SEA if terrain_type == SEA else PAPER_DESERT


# --- Atlas layer (packs with features.json and no pixel render model) ---
ATLAS_COAST = (40, 40, 30)
ATLAS_ROAD = (80, 55, 20)
ATLAS_INK = (35, 30, 25)
ATLAS_HALO = (240, 232, 200)
MARSH_STIPPLE = (150, 150, 150)


def _draw_atlas_terrain_extras(draw, board, origin_x, origin_y, width, height, cell_px):
    """Coast outline, connected road strokes, marsh stipple."""
    from .. import board as board_mod

    def centre(x, y):
        return ((x - origin_x) * cell_px + cell_px // 2,
                (y - origin_y) * cell_px + cell_px // 2)

    lw = max(1, cell_px // 5)
    for gy in range(height):
        for gx in range(width):
            x, y = origin_x + gx, origin_y + gy
            if not board.in_bounds(x, y):
                continue
            t = board.terrain_at(x, y)
            px0, py0 = gx * cell_px, gy * cell_px
            if t != board_mod.SEA:
                # coastline: outline edges shared with sea
                for dx, dy, seg in (
                    (0, -1, (px0, py0, px0 + cell_px, py0)),
                    (0, 1, (px0, py0 + cell_px, px0 + cell_px, py0 + cell_px)),
                    (-1, 0, (px0, py0, px0, py0 + cell_px)),
                    (1, 0, (px0 + cell_px, py0, px0 + cell_px, py0 + cell_px)),
                ):
                    nx, ny = x + dx, y + dy
                    if board.in_bounds(nx, ny) and board.terrain_at(nx, ny) == board_mod.SEA:
                        draw.line(seg, fill=ATLAS_COAST, width=max(1, cell_px // 6))
            if t == board_mod.ROAD:
                # connect to road neighbours (E, SE, S, SW) for contiguity
                for dx, dy in ((1, 0), (1, 1), (0, 1), (-1, 1)):
                    nx, ny = x + dx, y + dy
                    if board.in_bounds(nx, ny) and board.terrain_at(nx, ny) == board_mod.ROAD:
                        draw.line([centre(x, y), centre(nx, ny)], fill=ATLAS_ROAD, width=lw)
            if t == getattr(board_mod, "MARSH", -1):
                for sx, sy in ((2, 3), (5, 6), (7, 2)):
                    dx = px0 + sx * cell_px // 8
                    dy = py0 + sy * cell_px // 8
                    draw.rectangle([dx, dy, dx + max(1, cell_px // 8) - 1,
                                    dy + max(1, cell_px // 8) - 1], fill=MARSH_STIPPLE)


def _draw_atlas_features(draw, features, origin_x, origin_y, board, cell_px):
    """Named points, region labels and the frontier wire."""
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    def to_px(x, y):
        return ((x - origin_x) * cell_px + cell_px // 2,
                (y - origin_y) * cell_px + cell_px // 2)

    fx = features.get("frontier_x")
    if fx is not None and origin_x <= fx < origin_x + board.width:
        px = (fx - origin_x) * cell_px
        for y0 in range(0, board.height * cell_px, cell_px):
            draw.line([px, y0, px, y0 + cell_px // 2], fill=ATLAS_INK, width=1)

    def text_with_halo(pos, label, fill):
        if font is None:
            return
        tx, ty = pos
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            draw.text((tx + ox, ty + oy), label, font=font, fill=ATLAS_HALO)
        draw.text((tx, ty), label, font=font, fill=fill)

    for lab in features.get("region_labels", ()):
        tx, ty = to_px(lab["x"], lab["y"])
        spaced = " ".join(lab["name"])
        text_with_halo((tx - 4 * len(lab["name"]), ty - 5), spaced, (120, 105, 80))

    r = max(2, cell_px // 3)
    for pt in features.get("points", ()):
        cx, cy = to_px(pt["x"], pt["y"])
        kind = pt.get("kind", "town")
        if kind == "fort":
            draw.rectangle([cx - r, cy - r, cx + r, cy + r], outline=ATLAS_INK,
                           width=max(1, cell_px // 8))
        elif kind == "port":
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ATLAS_INK,
                         width=max(1, cell_px // 8))
            draw.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=ATLAS_INK)
        elif kind == "pass":
            draw.line([cx - r, cy + r, cx, cy - r], fill=ATLAS_INK, width=1)
            draw.line([cx, cy - r, cx + r, cy + r], fill=ATLAS_INK, width=1)
        else:  # town
            draw.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], fill=ATLAS_INK)
        text_with_halo((cx + r + 2, cy - 5), pt["name"], ATLAS_INK)


def _build_occupancy(units: Iterable[Unit]) -> dict:
    occupancy = {}
    for unit in units:
        if unit.is_destroyed:
            continue
        for cell in unit.footprint_cells():
            occupancy[cell] = unit
    return occupancy


def _load_font(size: int) -> "ImageFont.ImageFont":
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default()


def render_board_image(
    units: Iterable[Unit],
    board: Board,
    origin: Optional[tuple] = None,
    size: Optional[int] = None,
    cell_px: int = 12,
) -> "Image.Image":
    """Render a viewport (or the whole board if origin/size are None) to a
    Pillow Image: desert/sea/escarpment paper, road lines, and 2x2/1x1 unit
    counters coloured by nationality with a strength label -- the
    screenshot-corrected model (see module docstring), actually visible
    instead of raw ANSI escapes.
    """
    if origin is None:
        origin_x, origin_y = 0, 0
        width, height = board.width, board.height
    else:
        origin_x, origin_y = origin
        width = height = size if size is not None else VIEWPORT_SIZE

    occupancy = _build_occupancy(units)
    img = Image.new("RGB", (width * cell_px, height * cell_px), PAPER_DESERT)
    draw = ImageDraw.Draw(img, "RGBA")

    model = _render_model()
    features = _features() if _render_model() is None else None
    # The recovered model describes the real 100x32 map; synthetic boards
    # (tests, experiments) fall through to the legacy flat model.
    if model is not None and (
        len(model[1]) != board.height or len(model[1][0]) != board.width
    ):
        model = None
    for gy in range(height):
        for gx in range(width):
            x, y = origin_x + gx, origin_y + gy
            px0, py0 = gx * cell_px, gy * cell_px
            px1, py1 = px0 + cell_px, py0 + cell_px
            if not board.in_bounds(x, y):
                continue
            if model is not None and y < len(model[1]) and x < len(model[1][y]):
                # Authentic path: full-byte tile index -> attr (+ bitmap
                # if the local tile-art file is present, else a coverage
                # blend). See the render-model comment block above.
                attrs, grid, coverage, tiles = model
                cell = grid[y][x]
                paper, ink = _attr_colours(attrs[cell])
                if tiles is not None:
                    _draw_tile_bitmap(draw, tiles[cell], px0, py0, cell_px, paper, ink)
                else:
                    draw.rectangle([px0, py0, px1, py1], fill=_blend(paper, ink, coverage[cell]))
            else:
                # Legacy flat model (render_model.json absent).
                terrain_type = board.terrain_at(x, y)
                draw.rectangle([px0, py0, px1, py1], fill=_terrain_colour(terrain_type))
                if terrain_type in ESCARPMENT_TYPES:
                    _draw_escarpment_tile(draw, px0, py0, cell_px)
                if terrain_type == ROAD and features is None:
                    draw.line([px0, py0 + cell_px // 2, px1, py0 + cell_px // 2], fill=ROAD_LINE, width=max(1, cell_px // 6))
            draw.rectangle([px0, py0, px1, py1], outline=GRID_LINE, width=1)

    if features is not None:
        _draw_atlas_terrain_extras(draw, board, origin_x, origin_y, width, height, cell_px)
        _draw_atlas_features(draw, features, origin_x, origin_y, board, cell_px)

    font = _load_font(max(8, cell_px - 2))
    drawn_units = set()
    for gy in range(height):
        for gx in range(width):
            x, y = origin_x + gx, origin_y + gy
            unit = occupancy.get((x, y))
            if unit is None or unit.oob_index in drawn_units:
                continue
            drawn_units.add(unit.oob_index)
            cells = list(unit.footprint_cells())
            xs = [c[0] for c in cells]
            ys = [c[1] for c in cells]
            px0 = (min(xs) - origin_x) * cell_px
            py0 = (min(ys) - origin_y) * cell_px
            px1 = (max(xs) - origin_x + 1) * cell_px
            py1 = (max(ys) - origin_y + 1) * cell_px
            colour = NATION_COLOUR[unit.nationality]
            draw.rectangle([px0 + 1, py0 + 1, px1 - 1, py1 - 1], fill=colour, outline=(0, 0, 0))
            label = str(unit.strength)
            tw = draw.textlength(label, font=font) if hasattr(draw, "textlength") else font.getsize(label)[0]
            draw.text(
                (px0 + (px1 - px0 - tw) / 2, py0 + (py1 - py0) / 2 - font.size / 2),
                label,
                fill=(255, 255, 255),
                font=font,
            )

    return img


def save_board_image(
    units: Iterable[Unit],
    board: Board,
    path: str,
    origin: Optional[tuple] = None,
    size: Optional[int] = None,
    cell_px: int = 12,
) -> str:
    """Render and save to `path` (any Pillow-supported extension); returns
    `path` for convenient chaining.
    """
    img = render_board_image(units, board, origin=origin, size=size, cell_px=cell_px)
    img.save(path)
    return path
