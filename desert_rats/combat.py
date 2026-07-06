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
ADVERSE_POSITION_LOSS = 3
RECOVERY_DIVISOR = 16
RECOVERY_MINIMUM = 1
MAX_EFFICIENCY = 100
MIN_EFFICIENCY = 0
PRESSURE_CAP = 255                 # oracle-verified: 8-bit saturating accumulator
FIXED_THRESHOLD_CLASS = 10         # oracle-verified: combat CLASS 10 (an OOB byte,
                                   # NOT the 'type' field; mostly infantry/AT units)
FIXED_THRESHOLD = 20               # oracle-verified (these units crack sooner)
PRESSURE_EXEMPT_CLASS = 13         # oracle-verified via the class-derive routine
                                   # (bit-3 gate); unused by this game's roster
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


def pressure_threshold(unit: Unit) -> Optional[int]:
    """Morale, or the fixed 20 for combat-class-10 units; None for the
    exempt class 13. Oracle-verified: the class byte tested is the unit's
    COMBAT CLASS (data.Unit.combat_class), not its 'type'.
    """
    if unit.combat_class == PRESSURE_EXEMPT_CLASS:
        return None
    if unit.combat_class == FIXED_THRESHOLD_CLASS:
        return FIXED_THRESHOLD
    return unit.morale


def _try_retreat(unit: Unit, all_units: List[Unit], board: Board) -> bool:
    """One-cell diagonal retreat toward the unit's own map edge.

    Oracle-verified: the primary step is (+1,+1) for British units and
    (-1,+1) for Axis (south-east / south-west -- away from the coast,
    toward home); when terrain blocks it, the mirrored diagonal
    (-side_dx,+1) is taken. UNIT OCCUPANCY DOES NOT BLOCK RETREAT (the
    original happily stacks; only terrain passability matters). The
    northward diagonals as further fallbacks are inferred (not yet
    exercised by the harness).
    """
    from .data import Side

    dx = 1 if unit.side is Side.BRITISH else -1
    candidates = [(dx, 1), (-dx, 1), (dx, -1), (-dx, -1)]
    size = unit.footprint_size
    for cdx, cdy in candidates:
        nx, ny = unit.x + cdx, unit.y + cdy
        if board.footprint_passable(nx, ny, size):
            unit.x, unit.y = nx, ny
            return True
    return False


def resolve_pressure(unit: Unit, all_units: List[Unit], board: Board) -> bool:
    """The oracle-verified per-unit combat test; returns True if the unit
    cracked (or broke) this resolution.

    Verified against the original resolver executing under emulation
    (reference/diff_harness/): pressure >= strength destroys the unit
    outright (strength := 0); otherwise value = pressure*100//strength is
    tested against the threshold; at/above it the unit takes a flat -10
    efficiency (the spec's -20 caught-on-road doubling is FALSIFIED --
    travelling units take -10 like everyone else), is forced to HOLD, and
    retreats one diagonal cell toward its own map edge; if terrain blocks
    every candidate, pressure escalates by half again (cap 255), and if
    that reaches strength the unit is destroyed.
    """
    if unit.is_destroyed or unit.pressure == 0 or unit.strength <= 0:
        return False
    if unit.pressure >= unit.strength:
        unit.strength = 0
        unit.pressure = 0
        return True
    threshold = pressure_threshold(unit)
    if threshold is None:
        return False
    value = unit.pressure * 100 // unit.strength
    if value < threshold:
        return False
    apply_efficiency_loss(unit, COMBAT_LOSS)
    unit.order = Order.HOLD
    if not _try_retreat(unit, all_units, board):
        unit.pressure = min(PRESSURE_CAP, unit.pressure + unit.pressure // 2)
        if unit.pressure >= unit.strength:
            unit.strength = 0
            unit.pressure = 0
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
