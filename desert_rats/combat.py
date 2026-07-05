"""Effective power, the recovered combat-pressure model, adverse-position
attrition, recovery.

See BUILD_SPEC.md §5.5 and its addendum. A disassembly audit of the
original resolver (documented in NOTES.md "Combat 1:1 audit") replaced the
earlier placeholder (symmetric attacker-vs-defender power comparison) with
the model the original actually runs:

* Each unit carries a combat-PRESSURE accumulator (runtime byte, starts 0
  at placement), fed by contact with the enemy.
* Per resolution: value = pressure * 100 // strength, tested against a
  THRESHOLD = the unit's MORALE (or the fixed 20 for combat-class-10
  units). At/above threshold the unit takes -10 efficiency, its order is
  forced to HOLD, and it attempts a one-cell retreat; if it cannot
  retreat, pressure escalates by half again (x1.5, capped 255).
* Confirmed pieces: the x100/strength odds form, morale-as-threshold, the
  class-10 fixed threshold 20, -10 loss, forced Hold, the x1.5 escalation
  and 255 cap, and the -3 attrition / recovery formulas.
* Inferred pieces (named constants below, for the diff harness): the
  pressure INFLOW rate from adjacent enemies, pressure decay out of
  contact, and the retreat direction order. The -20 caught-on-road
  doubling is retained from the spec but the audit found no distinct
  call site for it -- flagged in NOTES.md.
"""
from __future__ import annotations

from typing import Iterable, List, Optional

from .board import Board
from .data import opposing_side
from .units import Order, Unit
from .zoc_supply import FlagGrid, is_out_of_supply

# Confirmed values (BUILD_SPEC.md §5.5 + addendum).
COMBAT_LOSS = 10
CAUGHT_ON_ROAD_LOSS = 2 * COMBAT_LOSS  # spec value; no distinct call site found in audit
ADVERSE_POSITION_LOSS = 3
RECOVERY_DIVISOR = 16
RECOVERY_MINIMUM = 1
MAX_EFFICIENCY = 100
MIN_EFFICIENCY = 0
PRESSURE_CAP = 255                 # confirmed: 8-bit accumulator, saturating
ARMOUR_COMBAT_CLASS = 10           # confirmed: class-10 override
ARMOUR_FIXED_THRESHOLD = 20        # confirmed
# Inferred, tunable (see module docstring):
PRESSURE_INFLOW_DIVISOR = 10       # inflow = adjacent enemy effective power // this
PRESSURE_DECAY_OUT_OF_CONTACT = True  # pressure resets when no enemy is adjacent


def effective_power(unit: Unit) -> float:
    """BUILD_SPEC.md §5.5: strength * efficiency / 100 (confirmed helper)."""
    return unit.strength * unit.efficiency / 100


def apply_efficiency_loss(unit: Unit, amount: int) -> None:
    unit.efficiency = max(MIN_EFFICIENCY, unit.efficiency - amount)


def _adjacent_enemies(unit: Unit, units: List[Unit]) -> List[Unit]:
    enemy_side = opposing_side(unit.side)
    cells = set(unit.footprint_cells())
    halo = set(cells)
    for cx, cy in cells:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            halo.add((cx + dx, cy + dy))
    out = []
    for other in units:
        if other.side is not enemy_side or other.is_destroyed:
            continue
        if halo & set(other.footprint_cells()):
            out.append(other)
    return out


def apply_combat_pressure(side_units: List[Unit], all_units: List[Unit]) -> None:
    """Accumulate combat pressure on `side_units` from adjacent enemies.

    Inflow rate is INFERRED (PRESSURE_INFLOW_DIVISOR): the original's scan
    loop adds an enemy-derived, saturating amount per pass; the exact
    scaling awaits the diff harness. Out of contact, pressure resets
    (PRESSURE_DECAY_OUT_OF_CONTACT -- also inferred).
    """
    for unit in side_units:
        if unit.is_destroyed:
            continue
        enemies = _adjacent_enemies(unit, all_units)
        if not enemies:
            if PRESSURE_DECAY_OUT_OF_CONTACT:
                unit.pressure = 0
            continue
        inflow = sum(int(effective_power(e)) // PRESSURE_INFLOW_DIVISOR for e in enemies)
        unit.pressure = min(PRESSURE_CAP, unit.pressure + inflow)


def pressure_threshold(unit: Unit) -> int:
    """Morale, or the fixed 20 for combat-class-10 units (confirmed)."""
    if unit.type == ARMOUR_COMBAT_CLASS:
        return ARMOUR_FIXED_THRESHOLD
    return unit.morale


def _try_retreat(unit: Unit, all_units: List[Unit], board: Board) -> bool:
    """One-cell retreat attempt, away from the nearest adjacent enemy.

    The original tries a coded direction then its opposite; the direction
    ORDER here (primary axis away from the enemy, then the perpendicular
    pair) is inferred. Deterministic; respects passability, bounds and the
    movement-time no-overlap rule.
    """
    enemies = _adjacent_enemies(unit, all_units)
    if enemies:
        e = min(enemies, key=lambda u: u.oob_index)
        dx = 0 if unit.x == e.x else (1 if unit.x > e.x else -1)
        dy = 0 if unit.y == e.y else (1 if unit.y > e.y else -1)
        directions = [(dx, 0), (0, dy), (0, -dy), (-dx, 0)]
        directions = [d for d in directions if d != (0, 0)]
        directions += [d for d in ((1, 0), (-1, 0), (0, 1), (0, -1)) if d not in directions]
    else:
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    occupied = set()
    for other in all_units:
        if other is unit or other.is_destroyed:
            continue
        occupied.update(other.footprint_cells())

    size = unit.footprint_size
    for dx, dy in directions:
        nx, ny = unit.x + dx, unit.y + dy
        if not board.footprint_passable(nx, ny, size):
            continue
        cells = set(Board.footprint_cells(nx, ny, size))
        if cells & occupied:
            continue
        unit.x, unit.y = nx, ny
        return True
    return False


def resolve_pressure(unit: Unit, all_units: List[Unit], board: Board) -> bool:
    """Run the recovered per-unit combat test; returns True if the unit
    cracked (took the loss) this resolution.
    """
    if unit.is_destroyed or unit.pressure == 0 or unit.strength <= 0:
        return False
    value = unit.pressure * 100 // unit.strength
    if value < pressure_threshold(unit):
        return False
    loss = CAUGHT_ON_ROAD_LOSS if unit.caught else COMBAT_LOSS
    apply_efficiency_loss(unit, loss)
    unit.order = Order.HOLD
    if not _try_retreat(unit, all_units, board):
        unit.pressure = min(PRESSURE_CAP, unit.pressure + unit.pressure // 2)
    return True


def is_in_adverse_position(unit: Unit, flags: FlagGrid) -> bool:
    """Out of supply, or standing in enemy ZOC (BUILD_SPEC.md §5.5)."""
    if is_out_of_supply(unit):
        return True
    enemy = opposing_side(unit.side)
    return any(flags.has_zoc(enemy, cx, cy) for cx, cy in unit.footprint_cells())


def apply_attrition(units: Iterable[Unit], flags: FlagGrid) -> None:
    """-3 efficiency for every living unit in an adverse position (§5.5)."""
    for unit in units:
        if unit.is_destroyed:
            continue
        if is_in_adverse_position(unit, flags):
            apply_efficiency_loss(unit, ADVERSE_POSITION_LOSS)


def recover(unit: Unit) -> None:
    """BUILD_SPEC.md §5.5: += (100 - efficiency) // 16 + 1, capped at 100."""
    gain = (MAX_EFFICIENCY - unit.efficiency) // RECOVERY_DIVISOR + RECOVERY_MINIMUM
    unit.efficiency = min(MAX_EFFICIENCY, unit.efficiency + gain)


def apply_recovery(units: Iterable[Unit], flags: FlagGrid) -> None:
    """Recovery applies exactly when NOT in an adverse position (§5.5) --
    i.e. in supply and not in enemy ZOC.
    """
    for unit in units:
        if unit.is_destroyed:
            continue
        if not is_in_adverse_position(unit, flags):
            recover(unit)
