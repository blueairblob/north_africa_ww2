"""Orders, step cost + mode multipliers, Travel, contact-stop.

See BUILD_SPEC.md §5.1-5.2. Operates on a single per-turn `FlagGrid`
snapshot (built once by zoc_supply.build_flag_grid, per the turn loop's
"rebuild ZOC+supply" step, §4.2) rather than recomputing it per step —
game.py decides whether/when to rebuild it between units.
"""
from __future__ import annotations

from .board import Board
from .data import Side, opposing_side
from .units import Order, Unit
from .zoc_supply import FlagGrid

# BUILD_SPEC.md §10: no per-terrain cost table exists; 1 MPS/cell is the
# spec's own suggested defensible default for the (unrecovered) base cost.
BASE_STEP_COST = 1.0

# BUILD_SPEC.md §5.1: Assault x1.5, Travel x0.5 (double reach); everything
# else x1.0.
MODE_MULTIPLIERS = {
    Order.ASSAULT: 1.5,
    Order.TRAVEL: 0.5,
}

# Orders that drive self-movement. Hold/Report are inert by definition;
# Divide/Fortify/Go-To-Port effects beyond Report are unconfirmed
# (BUILD_SPEC.md §10) and are not modelled as movement here.
_MOVING_ORDERS = (Order.MOVE, Order.ASSAULT, Order.TRAVEL)

_ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))


def step_cost(order: Order) -> float:
    """MPS cost to advance one cell under an order's mode multiplier."""
    return BASE_STEP_COST * MODE_MULTIPLIERS.get(order, 1.0)


def steps_available(unit: Unit) -> int:
    """How many single-cell steps `unit`'s MPS budget affords this turn."""
    return int(unit.mps // step_cost(unit.order))


def _has_road_access(x: int, y: int, board: Board) -> bool:
    """BUILD_SPEC.md §5.2: Travel needs the unit on or adjacent to a road."""
    if board.is_road(x, y):
        return True
    for dx, dy in _ORTHOGONAL:
        nx, ny = x + dx, y + dy
        if board.in_bounds(nx, ny) and board.is_road(nx, ny):
            return True
    return False


def can_start_travel(unit: Unit, board: Board) -> bool:
    return _has_road_access(unit.x, unit.y, board)


def _is_in_contact(unit: Unit, flags: FlagGrid) -> bool:
    """Whether any of `unit`'s footprint cells lie in the enemy's ZOC.

    Enemy ZOC is defined as the enemy's footprint cells plus their
    orthogonal neighbours (BUILD_SPEC.md §5.3), which is exactly
    "adjacent to or in contact with an enemy" — the trigger for §5.1's
    contact-stop and §5.2's caught-on-road flag.
    """
    enemy = opposing_side(unit.side)
    return any(flags.has_zoc(enemy, cx, cy) for cx, cy in unit.footprint_cells())


def _step_toward(x: int, y: int, dest_x: int, dest_y: int) -> tuple[int, int]:
    """One orthogonal cell step toward (dest_x, dest_y).

    The axis with the larger remaining distance moves first (deterministic
    tie-break: x before y on equal distance) -- movement/ZOC elsewhere in
    the spec is orthogonal-only, so diagonal stepping is not modelled.
    """
    dx = dest_x - x
    dy = dest_y - y
    if dx == 0 and dy == 0:
        return x, y
    if abs(dx) >= abs(dy):
        return x + (1 if dx > 0 else -1), y
    return x, y + (1 if dy > 0 else -1)


def _blocked_by_other_units(unit: Unit, nx: int, ny: int, size: int, flags: FlagGrid) -> bool:
    """BUILD_SPEC.md §5.1: a footprint may not overlap another unit."""
    own_current = set(unit.footprint_cells())
    other_occupied = (flags.occupied[Side.BRITISH] | flags.occupied[Side.AXIS]) - own_current
    return any(cell in other_occupied for cell in Board.footprint_cells(nx, ny, size))


def advance_unit(unit: Unit, board: Board, flags: FlagGrid) -> None:
    """Advance `unit` toward its destination for one turn, in place.

    No-op for orders that don't drive movement or when there's no
    destination. Stops early on contact with an enemy (Move/Assault) or
    flags `caught` and stops (Travel) -- BUILD_SPEC.md §5.1-5.2.
    """
    if unit.order not in _MOVING_ORDERS or unit.dest_x is None or unit.dest_y is None:
        return

    if unit.order is Order.TRAVEL and not unit.travel:
        if not can_start_travel(unit, board):
            return
        unit.travel = True

    remaining = steps_available(unit)
    size = unit.footprint_size

    while remaining > 0 and (unit.x, unit.y) != (unit.dest_x, unit.dest_y):
        nx, ny = _step_toward(unit.x, unit.y, unit.dest_x, unit.dest_y)
        if not board.footprint_passable(nx, ny, size) or _blocked_by_other_units(
            unit, nx, ny, size, flags
        ):
            break

        unit.x, unit.y = nx, ny
        remaining -= 1

        if unit.order is Order.TRAVEL:
            if _is_in_contact(unit, flags):
                unit.caught = True
                break
        elif _is_in_contact(unit, flags):
            break

    reached_dest = (unit.x, unit.y) == (unit.dest_x, unit.dest_y)
    if unit.order is Order.TRAVEL and reached_dest and not unit.caught:
        unit.travel = False
