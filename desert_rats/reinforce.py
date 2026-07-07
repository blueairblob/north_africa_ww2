"""Campaign clock, arrival admission from the master OOB, board-edge staging.

See BUILD_SPEC.md §3.3, §5.6. `mps` is not part of the 10-byte master_oob
table (see data.Unit's docstring); admission uses the per-unit value merged
in from data/unit_mps.json (real for 56/128 units, an evidenced type-level
fallback for the rest -- see NOTES.md). `DEFAULT_MPS` remains as a last-
resort override for callers that construct units outside the OOB pipeline
(e.g. tests).
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

# Last-resort fallback for callers that don't go through admit_reinforcements
# (e.g. constructing a bare Unit directly in a test). Real admission below
# uses oob_unit.mps (see module docstring), not this constant.
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
    mps: Optional[int] = None,
) -> list:
    """Units newly entering play this turn (BUILD_SPEC.md §5.6).

    `already_on_board` is the set of oob_index values ever admitted so far
    (tracked by the caller across turns -- it must include destroyed units
    too, so they don't re-enter). Processes the roster in index order so
    same-day arrivals nudge around each other deterministically.

    Each admitted unit's mps comes from its OOB roster entry (oob_unit.mps,
    merged from data/unit_mps.json) by default. Pass `mps` to force every
    admission this call to a single flat value instead (e.g. tests that
    want a uniform, deterministic MPS regardless of roster data).
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
        unit_mps = mps if mps is not None else oob_unit.mps
        unit = Unit.from_oob(oob_unit, x=x, y=y, mps=unit_mps)
        occupied.update(unit.footprint_cells())
        admitted.append(unit)

    return admitted


def scripted_deployment(entries, oob: OrderOfBattle, board: Board) -> list:
    """Create the scenario-start units at their scripted positions.

    `entries` is a data/deployments.json scenario list ({"oob_index",
    "x", "y"} dicts) recovered from the original's deployment tables (see
    NOTES.md "Deployment & stacking"). Unlike edge admission, scripted
    placement performs NO occupancy nudging: the original deploys
    divisions clustered, frequently with several units sharing a cell --
    that overlap is confirmed original behaviour at setup, and the
    movement rules keep their no-overlap constraint from the first move
    onward.
    """
    units = []
    for entry in entries:
        oob_unit = oob.by_index(entry["oob_index"])
        units.append(
            Unit.from_oob(oob_unit, x=entry["x"], y=entry["y"], mps=oob_unit.mps)
        )
    return units


# ---------------------------------------------------------------------------
# The replacement economy -- RECOVERED from the original (weekly phase at
# 0x953F, monthly income at 0x978E, appliers 0x9567/0x95CA/0x95E6, caps at
# 0x9520, premium condition 0x96C6; disassembled and END-TO-END
# ORACLE-VERIFIED, see NOTES.md "Replacement economy: recovered").
#
# - MONTHLY (clock % 30 == 0): each nationality banks two pools from the
#   0xDEFC monthly-group table x10 x Malta (Axis only, statuses 1/2).
#   Pool A = general replacements; Pool B = armour replacements.
# - WEEKLY (clock % 7 == 0), per nationality:
#     Replacements: units of the side whose ORDER IS HOLD gain
#       min((cap - strength + 1) // 2, rate, pool):
#       premium classes {1, 2, 12} -> cap 170, rate 30, from POOL B;
#       everyone else -> cap by 0x9520 (class 9 -> 100; else role 0/1/2+
#       -> 40/100/200), rate 10, from POOL A.
#     Rebuilds: destroyed-on-map units (strength 0, cooldown clear, not
#       class 9, not role-bit1) are bought back from pool A at their cap
#       cost (half price accepted when the pool is short), returning
#       after a cooldown (~8 days) at efficiency 50.
# ---------------------------------------------------------------------------

PREMIUM_CLASSES = {1, 2, 12}
PREMIUM_CAP = 170
PREMIUM_RATE = 30
NORMAL_RATE = 10
REBUILD_EFFICIENCY = 50
REBUILD_COOLDOWN_DAYS = 8


def strength_cap(unit) -> int:
    """0x9520: class 9 -> 100; else by role 40/100/200."""
    if unit.combat_class == 9:
        return 100
    if unit.role == 0:
        return 40
    if unit.role == 1:
        return 100
    return 200


def monthly_pool_income(state, schedules) -> None:
    """0x978E: pools[nat] += DEFC group x10 x Malta (Axis, status 1/2)."""
    groups = schedules["monthly_unit_schedule"]
    month = min(state.clock // 30, len(groups) - 1)
    group = groups[month]
    malta = schedules["malta_modifier"]
    for nat_index in (1, 2, 3):
        a = group[(nat_index - 1) * 2] * 10
        b = group[(nat_index - 1) * 2 + 1] * 10
        if nat_index != 1 and state.malta_status in (1, 2):
            half = malta["half_1" if state.malta_status == 1 else "half_2"][month]
            a = (a * half + 5) // 10
            b = (b * half + 5) // 10
        state.pools_a[nat_index] = state.pools_a.get(nat_index, 0) + a
        state.pools_b[nat_index] = state.pools_b.get(nat_index, 0) + b


def weekly_replacements(state) -> None:
    """0x9567/0x95CA/0x95E6: replacements and rebuilds, oracle-verified."""
    from .units import Order

    for unit in state.units:
        nat = unit.nationality_index
        if unit.is_destroyed:
            # rebuild path (0x95E6): strength-0, on-map, eligible
            if (unit.strength == 0 and unit.efficiency > 0
                    and getattr(unit, "rebuild_cooldown", 0) == 0
                    and unit.combat_class != 9 and not (unit.role & 2)):
                cost = strength_cap(unit)
                pool = state.pools_a.get(nat, 0)
                paid = cost if pool >= cost else (cost // 2 if pool >= cost // 2 else 0)
                if paid:
                    state.pools_a[nat] = pool - paid
                    unit.rebuild_cooldown = REBUILD_COOLDOWN_DAYS
                    unit.rebuild_strength = paid
                    unit.efficiency = REBUILD_EFFICIENCY
            continue
        if unit.order is not Order.HOLD:
            continue
        premium = unit.combat_class in PREMIUM_CLASSES
        cap = PREMIUM_CAP if premium else strength_cap(unit)
        rate = PREMIUM_RATE if premium else NORMAL_RATE
        deficit = cap - unit.strength
        if deficit <= 0:
            continue
        gain = min((deficit + 1) // 2, rate)
        pools = state.pools_b if premium else state.pools_a
        pool = pools.get(nat, 0)
        gain = min(gain, pool)
        if gain > 0:
            unit.strength += gain
            pools[nat] = pool - gain


def tick_rebuilds(state) -> None:
    """Daily: count down rebuild cooldowns; on expiry the paid strength
    arrives (the +3 in-transit field observed in the oracle)."""
    for unit in state.units:
        cd = getattr(unit, "rebuild_cooldown", 0)
        if cd > 0:
            unit.rebuild_cooldown = cd - 1
            if unit.rebuild_cooldown == 0:
                unit.strength = getattr(unit, "rebuild_strength", 0)
                unit.rebuild_strength = 0


def replacement_phase(state, schedules) -> None:
    """Wire-in point: call once per game day."""
    if state.clock % 30 == 0 and state.clock > 0:
        monthly_pool_income(state, schedules)
    if state.clock % 7 == 0 and state.clock > 0:
        weekly_replacements(state)
    tick_rebuilds(state)
