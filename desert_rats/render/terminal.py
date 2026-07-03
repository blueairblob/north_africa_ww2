"""Text/terminal rendering: scrolling viewport, unit counters, reports.

See BUILD_SPEC.md §8. A text renderer is explicitly an acceptable tier
("fidelity is about rules and feel, not pixel-exact emulation") -- this
draws the confirmed 22x22 scrolling viewport over the 100x32 map, with
2x2/1x1 unit counters coloured by nationality per palette.py.
"""
from __future__ import annotations

from typing import Iterable, Optional

from .. import zoc_supply
from ..board import Board, VIEWPORT_SIZE
from ..units import Unit
from ..victory import VictoryLevel
from .palette import ANSI_INK, ANSI_RESET, terrain_glyph, terrain_paper, unit_glyph
from .strings import UiStrings, victory_level_text

# BUILD_SPEC.md §10: the turn/day <-> calendar-month mapping isn't
# recovered (only that a schedule table exists indexed by turn/30 --
# reference/prospects.md #6); 30 days/month is the simplest deterministic
# reading of that same divisor, reused here for display purposes only.
CALENDAR_DAYS_PER_MONTH = 30


def clamp_viewport_origin(center_x: int, center_y: int, board: Board, size: int = VIEWPORT_SIZE) -> tuple:
    """Top-left of a `size`x`size` viewport centred on (center_x, center_y),
    clamped to stay on the board (BUILD_SPEC.md §8's 22x22 scrolling window).
    """
    half = size // 2
    max_x = max(board.width - size, 0)
    max_y = max(board.height - size, 0)
    origin_x = min(max(center_x - half, 0), max_x)
    origin_y = min(max(center_y - half, 0), max_y)
    return origin_x, origin_y


def _build_occupancy(units: Iterable[Unit]) -> dict:
    occupancy = {}
    for unit in units:
        if unit.is_destroyed:
            continue
        for cell in unit.footprint_cells():
            occupancy[cell] = unit
    return occupancy


def render_cell(unit: Optional[Unit], terrain_type: int, use_color: bool = True) -> str:
    char = unit_glyph(unit) if unit is not None else terrain_glyph(terrain_type)
    if not use_color:
        return char
    ink = ANSI_INK[unit.nationality] if unit is not None else ANSI_RESET
    return f"{terrain_paper(terrain_type)}{ink}{char}{ANSI_RESET}"


def render_viewport(
    units: Iterable[Unit],
    board: Board,
    origin: tuple,
    size: int = VIEWPORT_SIZE,
    use_color: bool = True,
) -> str:
    """A `size`x`size` text grid starting at `origin`, one row per line.

    Off-board cells (the viewport may run past the map edge for a
    board smaller than `size`) render as blank spaces.
    """
    origin_x, origin_y = origin
    occupancy = _build_occupancy(units)

    lines = []
    for y in range(origin_y, origin_y + size):
        row = []
        for x in range(origin_x, origin_x + size):
            if not board.in_bounds(x, y):
                row.append(" ")
                continue
            row.append(render_cell(occupancy.get((x, y)), board.terrain_at(x, y), use_color))
        lines.append("".join(row))
    return "\n".join(lines)


def format_unit_report(unit: Unit, strings: UiStrings) -> str:
    """A one-line report using the confirmed STR/MPS/SUP/MOR/EFF labels
    from data/ui_strings.json (BUILD_SPEC.md §8). A/M, FRT, UNITS, INF,
    ARM have no clean equivalent in the current runtime model and are
    omitted rather than guessed.
    """
    labels = strings.report_labels  # STR, MPS, SUP, MOR, A/M, EFF, FRT, UNITS, INF, ARM
    band = zoc_supply.supply_band(unit.supply) if unit.supply is not None else zoc_supply.NONE
    fields = [
        (labels[0], unit.strength),
        (labels[1], unit.mps),
        (labels[2], band),
        (labels[3], unit.morale),
        (labels[5], unit.efficiency),
    ]
    return "  ".join(f"{label} {value}" for label, value in fields)


def calendar_month(clock: int, strings: UiStrings) -> str:
    index = (clock // CALENDAR_DAYS_PER_MONTH) % len(strings.calendar)
    return strings.calendar[index]


def format_status_line(
    turn_counter: int,
    clock: int,
    scenario_name: str,
    strings: UiStrings,
    result: Optional[VictoryLevel] = None,
) -> str:
    month = calendar_month(clock, strings)
    line = f"Turn {turn_counter}  Day {clock} ({month})  {scenario_name}"
    if result is not None:
        line += f"  -- {victory_level_text(result, strings)}"
    return line
