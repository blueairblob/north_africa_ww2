"""Budget-limited deterministic heuristic planner (BUILD_SPEC.md §6).

Confirmed (§10): H=40 budget, ±25-column offensive band. Unconfirmed: the
exact per-unit MPS/type weighting, the target-region selection weighting,
and the offensive/defensive score inputs beyond the spatial band -- this
module implements the spec's own described *shape* with simple,
deterministic, documented choices wherever the exact formula isn't
recovered.

`plan_turn` is an OrderProvider (see game.py's module docstring) -- pass
`{Side.AXIS: ai.plan_turn}` (or British, for a computer-controlled
British side) to `game.play_turn`/`run_until_over`.
"""
from __future__ import annotations

from typing import Iterable, List, Optional

from . import reinforce, victory
from .board import Board
from .combat import effective_power
from .data import Side, opposing_side
from .game import GameState, find_adjacent_enemy
from .units import Order, Unit
from .zoc_supply import FlagGrid

# BUILD_SPEC.md §10, confirmed.
AI_BUDGET = 40
AI_BUDGET_PER_PASS = 10
AI_PASSES = AI_BUDGET // AI_BUDGET_PER_PASS  # 4
AI_BAND_HALF_WIDTH = 25

REGION_COUNT = 30

_ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))


def unit_weight(unit: Unit) -> float:
    """BUILD_SPEC.md §6: "weight derived from MPS and type" -- the exact
    formula is unrecovered; armour counts double, scaled by MPS.
    """
    return unit.mps * (2 if unit.is_armour_type else 1)


def region_index(x: int, board_width: int) -> int:
    """Which of the 30 regional-strength-map slots `x` falls into."""
    return x * REGION_COUNT // board_width


def region_bounds(region: int, board_width: int) -> tuple:
    low = region * board_width // REGION_COUNT
    high = (region + 1) * board_width // REGION_COUNT - 1
    return low, max(low, high)


def build_regional_strength_map(units: Iterable[Unit], board: Board) -> dict:
    """30-slot per-side weighted-strength tally (BUILD_SPEC.md §6)."""
    strength = {Side.BRITISH: [0.0] * REGION_COUNT, Side.AXIS: [0.0] * REGION_COUNT}
    for unit in units:
        if unit.is_destroyed:
            continue
        region = region_index(unit.x, board.width)
        strength[unit.side][region] += effective_power(unit) * unit_weight(unit)
    return strength


def _band_regions(midpoint: Optional[float], board_width: int) -> List[int]:
    """Region indices within BUILD_SPEC.md §6's ±25-column offensive band."""
    if midpoint is None:
        return list(range(REGION_COUNT))
    low_x = max(0, int(midpoint) - AI_BAND_HALF_WIDTH)
    high_x = min(board_width - 1, int(midpoint) + AI_BAND_HALF_WIDTH)
    return list(range(region_index(low_x, board_width), region_index(high_x, board_width) + 1))


def pick_target_region(
    strength_map: dict,
    side: Side,
    band: List[int],
    midpoint: Optional[float] = None,
    board_width: Optional[int] = None,
) -> int:
    """The contested band region with the greatest (own - enemy) strength
    advantage.

    BUILD_SPEC.md §6's target-region weighting is unrecovered; "attack
    where you have the biggest relative edge" is the simplest deterministic
    reading -- but only among regions with actual enemy presence
    (`hostile[r] > 0`). Without that restriction, an empty region trivially
    maximises `own - hostile` (it's just `own[r]`, biggest wherever a
    side's own units already are), so early in a scenario -- before either
    side's forward units are anywhere near the band -- this would target a
    side's *own* rear/staging area and never actually advance. When no
    band region is contested at all, fall back to the region containing
    the current front-line midpoint (which itself shifts as either side's
    forward units move, so this still converges turn over turn), rather
    than an arbitrary lowest-index tie-break.
    """
    enemy = opposing_side(side)
    own, hostile = strength_map[side], strength_map[enemy]
    contested = [r for r in band if hostile[r] > 0]
    if contested:
        return max(contested, key=lambda r: (own[r] - hostile[r], -r))
    if midpoint is not None and board_width is not None:
        clamped_x = int(max(0, min(midpoint, board_width - 1)))
        return region_index(clamped_x, board_width)
    return band[len(band) // 2]


def _region_target_xy(region: int, side: Side, units: Iterable[Unit], board: Board) -> tuple:
    low, high = region_bounds(region, board.width)
    x = (low + high) // 2
    enemy = opposing_side(side)
    enemy_ys = [u.y for u in units if not u.is_destroyed and u.side is enemy and low <= u.x <= high]
    y = sum(enemy_ys) // len(enemy_ys) if enemy_ys else board.height // 2
    return (x, y)


def is_offensive(unit: Unit, midpoint: Optional[float]) -> bool:
    """BUILD_SPEC.md §6, confirmed: within ±25 columns of the front-line
    midpoint acts offensively; otherwise defensively. No front line (a
    side wiped out) defaults to offensive -- push forward.
    """
    return midpoint is None or abs(unit.x - midpoint) <= AI_BAND_HALF_WIDTH


def ray_scan_contact(unit: Unit, flags: FlagGrid, board: Board, max_range: int = AI_BAND_HALF_WIDTH):
    """BUILD_SPEC.md §6: ray-cast the four cardinal directions from `unit`
    for the nearest enemy ZOC cell. Returns (x, y) of the nearest hit
    across all four rays, or None.
    """
    enemy = opposing_side(unit.side)
    best, best_dist = None, None
    for dx, dy in _ORTHOGONAL:
        for step in range(1, max_range + 1):
            x, y = unit.x + dx * step, unit.y + dy * step
            if not board.in_bounds(x, y):
                break
            if flags.has_zoc(enemy, x, y):
                if best_dist is None or step < best_dist:
                    best, best_dist = (x, y), step
                break
    return best


def _nearest_enemy_y(unit: Unit, units: List[Unit]) -> int:
    """The row of the closest living enemy to `unit`, or its own row if no
    enemy is left -- used so units angle toward an actual opponent instead
    of holding a rigid row that may never line up with the enemy's.
    """
    enemy_side = opposing_side(unit.side)
    living_enemies = [u for u in units if not u.is_destroyed and u.side is enemy_side]
    if not living_enemies:
        return unit.y
    nearest = min(living_enemies, key=lambda e: abs(e.x - unit.x) + abs(e.y - unit.y))
    return nearest.y


def _decide_unit(
    unit: Unit,
    units: List[Unit],
    board: Board,
    flags: FlagGrid,
    target: tuple,
    midpoint: Optional[float],
) -> None:
    # An adjacent enemy takes priority over offensive/defensive posture --
    # BUILD_SPEC.md §6 only mentions the assault-if-adjacent check under
    # "defensive/local", but an *offensive* unit that has closed to contact
    # needs it too: otherwise it just keeps re-issuing Move toward a target
    # beyond the enemy, which movement.py correctly halts on contact (its
    # own contact-stop rule) but never converts into a fight -- observed in
    # practice as two adjacent units sitting frozen turn after turn.
    adjacent_enemy = find_adjacent_enemy(unit, units)
    if adjacent_enemy is not None:
        unit.order = Order.ASSAULT
        unit.dest_x = unit.dest_y = None
        return

    # Every unit of a side shares the same regional `target`; chasing its
    # exact (x, y) would collapse the whole side onto one cell (they'd pile
    # up and block each other well short of the enemy -- observed in
    # practice as the front freezing turns before any real contact). Chase
    # the target's column but each unit's own nearest-enemy row, so the
    # side spreads out in x while still converging on real contact in y
    # (reinforcement admission can land units on rows that never line up
    # with the enemy's if they just held a fixed row).
    target_x, target_y = target[0], _nearest_enemy_y(unit, units)

    if is_offensive(unit, midpoint):
        unit.order = Order.MOVE
        unit.dest_x, unit.dest_y = target_x, target_y
        return

    nearby = ray_scan_contact(unit, flags, board)
    if nearby is not None:
        unit.order = Order.MOVE
        unit.dest_x, unit.dest_y = nearby
        return

    # BUILD_SPEC.md §6: no local threat and no offensive mandate -- retreat
    # if the region target IS the side's own board edge, else advance on it.
    home_edge_x = reinforce.STAGING_POINTS[unit.side][0]
    unit.order = Order.GO_TO_PORT if target_x == home_edge_x else Order.MOVE
    unit.dest_x, unit.dest_y = target_x, target_y


def plan_turn(state: GameState, side: Side, flags: FlagGrid) -> None:
    """AI order-selection for one side's turn -- an OrderProvider for
    game.play_turn (BUILD_SPEC.md §6).

    The original's "budget 40 / 4 passes" (§10, confirmed) presumably lets
    later passes react to provisional orders assigned earlier in the same
    sweep; this model's per-unit decision is a pure function of state that
    doesn't change mid-sweep, so repeated passes would be no-ops here --
    one pass is used, with the budget constants kept above for fidelity.
    """
    strength_map = build_regional_strength_map(state.units, state.board)
    midpoint = victory.front_line_midpoint(state.units)
    band = _band_regions(midpoint, state.board.width)
    target_region = pick_target_region(strength_map, side, band, midpoint, state.board.width)
    target = _region_target_xy(target_region, side, state.units, state.board)

    for unit in state.units:
        if unit.side is side and not unit.is_destroyed:
            _decide_unit(unit, state.units, state.board, flags, target, midpoint)
