"""Front line, objective scoring, tactical/major/decisive victory ladder.

See BUILD_SPEC.md §5.7. The objective type-code semantics and the exact
scoring/threshold formulas are unrecovered (BUILD_SPEC.md §10 -- "type-code
semantics are partly inferred"); this module implements the spec's own
described *shape* (objective control + unit-count thresholds -> a signed
7-way ladder) with simple, deterministic, documented choices everywhere
the exact formula isn't recovered.
"""
from __future__ import annotations

from enum import Enum
from typing import Iterable, Optional, Sequence

from .data import Scenario, Side
from .units import Unit

# Inferred (§10): how many turns of an unchanged front-line midpoint counts
# as a stalemate end condition.
STALEMATE_TURNS = 10

# Inferred (§10): the magnitude bands mapping a score margin to
# tactical/major/decisive -- objective counts here are small (typically
# 2 objectives + 1 unit-threshold point per side), so unit-sized bands.
# margin 1 = tactical (the fallthrough case below), 2 = major, 3+ = decisive.
_MAJOR_MARGIN = 2


class VictoryLevel(Enum):
    BRITISH_DECISIVE = "Decisive British victory"
    BRITISH_MAJOR = "Major British victory"
    BRITISH_TACTICAL = "British tactical victory"
    DRAW = "Draw"
    AXIS_TACTICAL = "Axis tactical victory"
    AXIS_MAJOR = "Major Axis victory"
    AXIS_DECISIVE = "Decisive Axis victory"


def front_line(units: Iterable[Unit]) -> Optional[tuple[int, int]]:
    """(easternmost Axis x, westernmost British x); None if either side has
    no living units (BUILD_SPEC.md §5.7).
    """
    axis_x = [u.x for u in units if not u.is_destroyed and u.side is Side.AXIS]
    british_x = [u.x for u in units if not u.is_destroyed and u.side is Side.BRITISH]
    if not axis_x or not british_x:
        return None
    return (max(axis_x), min(british_x))


def front_line_midpoint(units: Iterable[Unit]) -> Optional[float]:
    """BUILD_SPEC.md §5.7/§6: midpoint of the front line, or None if
    undefined (a side has been wiped out).
    """
    line = front_line(units)
    if line is None:
        return None
    axis_x, british_x = line
    return (axis_x + british_x) / 2


def is_stalemate(midpoint_history: Sequence[Optional[float]]) -> bool:
    """True if the front-line midpoint hasn't moved for STALEMATE_TURNS
    consecutive turns.
    """
    if len(midpoint_history) < STALEMATE_TURNS:
        return False
    recent = midpoint_history[-STALEMATE_TURNS:]
    return recent[0] is not None and all(m == recent[0] for m in recent)


def is_game_over(clock: int, scenario: Scenario, midpoint_history: Sequence[Optional[float]]) -> bool:
    """BUILD_SPEC.md §5.7: end day reached, or a front-line stalemate."""
    return clock >= scenario.end_day or is_stalemate(midpoint_history)


def controls_column(units: Iterable[Unit], column: int) -> Optional[Side]:
    """Which side's nearest living unit is closest to `column`.

    BUILD_SPEC.md §5.7: "control" = which side holds the ground around
    that column. Proximity-of-nearest-unit is the simplest deterministic
    reading of that description.
    """
    best_side = None
    best_distance = None
    for unit in units:
        if unit.is_destroyed:
            continue
        distance = abs(unit.x - column)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_side = unit.side
    return best_side


def count_controlled_objectives(
    units: Iterable[Unit], objectives: Iterable[tuple[int, int]], side: Side
) -> int:
    units = list(units)
    return sum(1 for column, _type in objectives if controls_column(units, column) is side)


def score_side(units: Iterable[Unit], scenario: Scenario, side: Side) -> int:
    """Objective control points + a unit-count-threshold point (§5.7)."""
    units = list(units)
    objectives = scenario.british_objectives if side is Side.BRITISH else scenario.axis_objectives
    threshold_key = "british" if side is Side.BRITISH else "axis"

    points = count_controlled_objectives(units, objectives, side)

    surviving = sum(1 for u in units if not u.is_destroyed and u.side is side)
    threshold = scenario.unit_thresholds.get(threshold_key, 0)
    if surviving >= threshold:
        points += 1

    return points


def victory_result(units: Iterable[Unit], scenario: Scenario) -> VictoryLevel:
    """BUILD_SPEC.md §5.7: compare both sides' scores into the 7-way ladder."""
    units = list(units)
    margin = score_side(units, scenario, Side.BRITISH) - score_side(units, scenario, Side.AXIS)

    if margin == 0:
        return VictoryLevel.DRAW
    if margin > 0:
        if margin >= _MAJOR_MARGIN + 1:
            return VictoryLevel.BRITISH_DECISIVE
        if margin >= _MAJOR_MARGIN:
            return VictoryLevel.BRITISH_MAJOR
        return VictoryLevel.BRITISH_TACTICAL
    magnitude = -margin
    if magnitude >= _MAJOR_MARGIN + 1:
        return VictoryLevel.AXIS_DECISIVE
    if magnitude >= _MAJOR_MARGIN:
        return VictoryLevel.AXIS_MAJOR
    return VictoryLevel.AXIS_TACTICAL
