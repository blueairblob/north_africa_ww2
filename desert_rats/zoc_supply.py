"""Per-cell zone-of-control + occupancy flag grid, and edge-traced supply.

See BUILD_SPEC.md §5.3-5.4. Rebuilt once per turn from the live unit list
(§4.2 step 3), then consumed by combat.py (attrition/reduced combat when
out of supply or in enemy ZOC) and later ai.py (ray-cast perception reuses
the same flag grid).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Optional

from .board import Board
from .data import Side, opposing_side
from .units import Unit

_ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))

# BUILD_SPEC.md §5.4: delivered supply level indexed by distance // 4,
# clamped to the last entry.
SUPPLY_CURVE = (
    90, 80, 75, 70, 65, 60, 55, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 41,
    40, 40, 39, 39, 38, 38, 37, 37, 36, 36, 36, 35, 35,
)

# Verbatim from data/ui_strings.json:supply_bands.
NONE, V_LOW, LOW, Q_LOW, FAIR, GOOD, V_GOOD = (
    "NONE", "V LOW", "LOW", "Q LOW", "FAIR", "GOOD", "V GOOD",
)


def _supply_edge_x(side: Side, board: Board) -> int:
    """BUILD_SPEC.md §5.4: British trace to the east edge, Axis to the west."""
    return board.width - 1 if side is Side.BRITISH else 0


@dataclass(frozen=True)
class FlagGrid:
    """Per-cell side-tagged occupancy and ZOC, rebuilt each turn."""

    width: int
    height: int
    zoc: dict
    occupied: dict

    def has_zoc(self, side: Side, x: int, y: int) -> bool:
        return (x, y) in self.zoc[side]

    def is_occupied_by(self, side: Side, x: int, y: int) -> bool:
        return (x, y) in self.occupied[side]


def build_flag_grid(units: Iterable[Unit], board: Board) -> FlagGrid:
    """Project every living unit's occupancy + ZOC onto the flag grid.

    BUILD_SPEC.md §5.3: ZOC covers a unit's footprint cells plus the cells
    orthogonally adjacent to them, tagged by side.
    """
    zoc = {Side.BRITISH: set(), Side.AXIS: set()}
    occupied = {Side.BRITISH: set(), Side.AXIS: set()}

    for unit in units:
        if unit.is_destroyed:
            continue
        cells = set(unit.footprint_cells())
        occupied[unit.side].update(cells)

        projected = set(cells)
        for cx, cy in cells:
            for dx, dy in _ORTHOGONAL:
                nx, ny = cx + dx, cy + dy
                if board.in_bounds(nx, ny):
                    projected.add((nx, ny))
        zoc[unit.side].update(projected)

    return FlagGrid(
        width=board.width,
        height=board.height,
        zoc={side: frozenset(cells) for side, cells in zoc.items()},
        occupied={side: frozenset(cells) for side, cells in occupied.items()},
    )


def trace_supply_distance(unit: Unit, board: Board, flags: FlagGrid) -> Optional[int]:
    """Shortest 4-directional distance from `unit` to its side's board edge.

    BUILD_SPEC.md §5.4: blocked by enemy units and enemy ZOC. Returns None
    if no path exists (the unit is out of supply).
    """
    edge_x = _supply_edge_x(unit.side, board)
    enemy = opposing_side(unit.side)

    start = set(unit.footprint_cells())
    if any(x == edge_x for x, _y in start):
        return 0

    visited = set(start)
    frontier = deque((cell, 0) for cell in start)
    while frontier:
        (x, y), dist = frontier.popleft()
        for dx, dy in _ORTHOGONAL:
            nx, ny = x + dx, y + dy
            cell = (nx, ny)
            if cell in visited:
                continue
            if not board.is_passable(nx, ny):
                continue
            if flags.is_occupied_by(enemy, nx, ny) or flags.has_zoc(enemy, nx, ny):
                continue
            visited.add(cell)
            if nx == edge_x:
                return dist + 1
            frontier.append((cell, dist + 1))
    return None


def supply_level(distance: int) -> int:
    """BUILD_SPEC.md §5.4 curve. ORACLE-VERIFIED against the original
    routine executing under emulation (reference/diff_harness/): the
    index is a = min(distance + 2, 127) >> 2; a == 0 (distance <= 1)
    returns FULL supply (100, a band that is not in the table), else
    curve[a - 1]. Both our earlier distance>>2 and the first audit's
    (distance+2)>>2-into-curve readings were one band off everywhere.
    """
    a = min(distance + 2, 127) >> 2
    if a == 0:
        return 100
    return SUPPLY_CURVE[min(a - 1, len(SUPPLY_CURVE) - 1)]


def supply_band(level: int) -> str:
    """Display band for a supply level.

    DISPLAY ONLY -- not a game mechanic.

    CONFIRMED: these six labels really are supply bands. The unit report
    prints a SUP field (message 14, alongside STR/MPS/MOR/EFF/FRT), and a
    real gameplay screenshot shows "FAIR" in it.

    NOT RECOVERED: the numeric cutoffs. The band-selection code has
    resisted several searches -- there is no base+offset computation onto
    the labels' message indices, and the "SUPPLY LOW" warning the game
    emits (0x8CC4) tests MPS < 10, not a supply percentage, so it is a
    different mechanism. The selector presumably lives in the report
    renderer using a string table we have not yet tied to these indices.

    The thresholds below are therefore OURS, taken from the (oracle-
    verified) curve's own breakpoints. The supply CURVE and its banding
    arithmetic are exact (see supply_level); only this cosmetic label
    mapping is invented, and no engine mechanic depends on it. This is
    the project's LAST open item.
    """
    if level <= 0:
        return NONE
    if level < 40:
        return V_LOW
    if level < 50:
        return LOW
    if level < 60:
        return Q_LOW
    if level < 70:
        return FAIR
    if level < 80:
        return GOOD
    return V_GOOD


def is_out_of_supply(unit: Unit) -> bool:
    return unit.supply == 0


def compute_supply(units: Iterable[Unit], board: Board, flags: Optional[FlagGrid] = None) -> None:
    """Recompute and set `.supply` on every living unit in place.

    Pass a pre-built `flags` (e.g. shared with ZOC-dependent AI perception
    this same turn) to avoid rebuilding it twice.
    """
    units = list(units)
    if flags is None:
        flags = build_flag_grid(units, board)
    for unit in units:
        if unit.is_destroyed:
            continue
        distance = trace_supply_distance(unit, board, flags)
        unit.supply = 0 if distance is None else supply_level(distance)
