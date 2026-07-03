"""Effective power, assault resolution, adverse-position attrition, recovery.

See BUILD_SPEC.md §5.5. The exact "combat_readiness" numerator (the "+3
byte") is unrecovered (BUILD_SPEC.md §10). This module implements the
spec's own suggested defensible fallback instead of the literal formula:
attacker vs defender effective power, higher side wins, the loser takes
-10 efficiency (-20 if caught on a road) and is forced to Hold.
"""
from __future__ import annotations

from typing import Iterable, Optional

from .data import opposing_side
from .units import Order, Unit
from .zoc_supply import FlagGrid, is_out_of_supply

# BUILD_SPEC.md §5.5, confirmed values.
COMBAT_LOSS = 10
CAUGHT_ON_ROAD_LOSS = 2 * COMBAT_LOSS
ADVERSE_POSITION_LOSS = 3
RECOVERY_DIVISOR = 16
RECOVERY_MINIMUM = 1
MAX_EFFICIENCY = 100
MIN_EFFICIENCY = 0


def effective_power(unit: Unit) -> float:
    """BUILD_SPEC.md §5.5: strength * efficiency / 100."""
    return unit.strength * unit.efficiency / 100


def apply_efficiency_loss(unit: Unit, amount: int) -> None:
    unit.efficiency = max(MIN_EFFICIENCY, unit.efficiency - amount)


def resolve_assault(attacker: Unit, defender: Unit) -> Optional[Unit]:
    """Resolve one assault between adjacent units, in place.

    Returns the losing unit, or None on an exact tie (no loss applied).
    The loser takes -10 efficiency (-20 if it was caught on a road) and its
    order is forced to Hold (BUILD_SPEC.md §5.5).
    """
    attack_power = effective_power(attacker)
    defence_power = effective_power(defender)

    if attack_power == defence_power:
        return None

    loser = defender if attack_power > defence_power else attacker
    loss = CAUGHT_ON_ROAD_LOSS if loser.caught else COMBAT_LOSS
    apply_efficiency_loss(loser, loss)
    loser.order = Order.HOLD
    return loser


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
