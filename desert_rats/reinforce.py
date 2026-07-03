"""Campaign clock, arrival admission from the master OOB, board-edge staging.

See BUILD_SPEC.md §3.3, §5.6. `mps` has no source in data/master_oob.json
(see units.py's module docstring) -- a genuine, unresolved data gap, not
listed as a numbered item in BUILD_SPEC.md §10 but the same kind of thing:
admission here assigns every unit a single flat, named, tunable MPS value
rather than inventing a per-unit table with no basis in the recovered data.
"""
from __future__ import annotations

from typing import Iterable, Optional

from .board import Board
from .data import OrderOfBattle, Side
from .units import Unit

# BUILD_SPEC.md §3.3: one campaign "day" every three turns.
CLOCK_DIVISOR = 3
CLOCK_OFFSET = 2

CAMPAIGN_START_DAY = 1
CAMPAIGN_END_DAY = 624

# BUILD_SPEC.md §5.6: "British at ~(98,11) on the east edge, Axis at the
# west edge" -- the Axis row isn't given a specific figure, so it mirrors
# the British one as a reasonable, documented default.
STAGING_POINTS = {
    Side.BRITISH: (98, 11),
    Side.AXIS: (0, 11),
}

# Bound on how far admission will nudge a reinforcement from its staging
# point to find a free footprint -- a safety cap, not a rules value.
MAX_NUDGE_RADIUS = 30

# Genuinely unrecovered (see module docstring); 6 is a commonly-observed
# value among the per-unit mps figures BUILD_SPEC.md §3.2 mentions.
DEFAULT_MPS = 6


def campaign_clock(turn_counter: int) -> int:
    """BUILD_SPEC.md §3.3: clock = (turn_counter + 2) // 3."""
    return (turn_counter + CLOCK_OFFSET) // CLOCK_DIVISOR


def _ring_offsets(max_radius: int):
    """(dx, dy) offsets in expanding square rings, centre first -- a
    deterministic nudge-search order.
    """
    yield (0, 0)
    for r in range(1, max_radius + 1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) == r:
                    yield (dx, dy)


def find_free_staging_cell(
    side: Side,
    board: Board,
    occupied: Iterable[tuple],
    base: Optional[tuple] = None,
) -> tuple:
    """First free 2x2 footprint near a side's staging point (§5.6's "nudge
    if occupied"), searching outward in a deterministic ring order.
    """
    occupied = set(occupied)
    bx, by = base if base is not None else STAGING_POINTS[side]
    for dx, dy in _ring_offsets(MAX_NUDGE_RADIUS):
        x, y = bx + dx, by + dy
        if not board.footprint_passable(x, y, 2):
            continue
        if any(cell in occupied for cell in Board.footprint_cells(x, y, 2)):
            continue
        return (x, y)
    raise RuntimeError(f"no free staging cell found near ({bx}, {by}) for {side}")


def admit_reinforcements(
    oob: OrderOfBattle,
    already_on_board: set,
    current_units: Iterable[Unit],
    day: int,
    board: Board,
    mps: int = DEFAULT_MPS,
) -> list:
    """Units newly entering play this turn (BUILD_SPEC.md §5.6).

    `already_on_board` is the set of oob_index values ever admitted so far
    (tracked by the caller across turns -- it must include destroyed units
    too, so they don't re-enter). Processes the roster in index order so
    same-day arrivals nudge around each other deterministically.
    """
    occupied = set()
    for unit in current_units:
        if not unit.is_destroyed:
            occupied.update(unit.footprint_cells())

    admitted = []
    for oob_unit in oob:
        if oob_unit.index in already_on_board or oob_unit.arrival > day:
            continue
        x, y = find_free_staging_cell(oob_unit.side, board, occupied)
        unit = Unit.from_oob(oob_unit, x=x, y=y, mps=mps)
        occupied.update(unit.footprint_cells())
        admitted.append(unit)

    return admitted
