"""Front line, objective scoring, tactical/major/decisive victory ladder.

RECOVERED from the original (scorer 0x9925, ladder 0x9A07, objective
handlers 0x9970; conditions in data/victory_conditions.json). This
replaces the earlier spec-shaped guess, which was structurally wrong: the
ladder is NOT margin-based, and the unit threshold ADDS nothing -- it
ZEROES a side's score when its surviving-unit count falls below it.

Per side (0-3 points):
  +1 for each of its TWO objectives met (type codes below);
  score := 3 outright if the enemy has been annihilated;
  score := 0 if own surviving units < the side's threshold.
Ladder (0x9A07): equal scores -> DRAW; otherwise the WINNER'S OWN SCORE
gives the magnitude -- 1 tactical, 2 major, 3 decisive.

Objective type codes:
  0 none; 1 reach the far map edge; 3 hold the front line at/beyond
  column V; 4 hold the ENEMY's front line no further than column V;
  5 keep more than V units on the map.
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


def _front_column(units, side: Side) -> Optional[int]:
    """The side's front-line column (0xCB07/0xCB08): the easternmost Axis
    unit / the westernmost British unit."""
    xs = [u.x for u in units if not u.is_destroyed and u.side is side]
    if not xs:
        return None
    return max(xs) if side is Side.AXIS else min(xs)


def objective_met(units, objective, side: Side, board_width: int = 100) -> bool:
    """One recovered objective test (handlers dispatched at 0x9970)."""
    code, value = objective
    units = list(units)
    if code == 0:
        return False
    if code == 1:
        # reach the far map edge (the side's advance edge)
        edge = board_width - 1
        return any(not u.is_destroyed and u.side is side
                   and (u.x >= edge - 2 if side is Side.BRITISH else u.x <= 2)
                   for u in units)
    if code == 3:
        front = _front_column(units, side)
        if front is None:
            return False
        # British push west (front <= V); Axis push east (front >= V)
        return front <= value if side is Side.BRITISH else front >= value
    if code == 4:
        enemy = Side.AXIS if side is Side.BRITISH else Side.BRITISH
        front = _front_column(units, enemy)
        if front is None:
            return True   # no enemy left: trivially contained
        return front >= value if side is Side.BRITISH else front <= value
    if code == 5:
        alive = sum(1 for u in units if not u.is_destroyed and u.side is side)
        return alive > value
    return False


def score_side(units, scenario, side: Side) -> int:
    """0-3 points, per the recovered scorer (0x9925)."""
    units = list(units)
    conditions = scenario.victory_conditions
    objectives = (conditions["british_objectives"] if side is Side.BRITISH
                  else conditions["axis_objectives"])
    threshold = (conditions["british_unit_threshold"] if side is Side.BRITISH
                 else conditions["axis_unit_threshold"])

    enemy = Side.AXIS if side is Side.BRITISH else Side.BRITISH
    enemy_alive = sum(1 for u in units if not u.is_destroyed and u.side is enemy)
    own_alive = sum(1 for u in units if not u.is_destroyed and u.side is side)

    if enemy_alive == 0:
        points = 3                                  # annihilation
    else:
        points = sum(1 for o in objectives if objective_met(units, o, side))

    if own_alive < threshold:                       # ZEROED, not bonused
        return 0
    return min(points, 3)

def victory_result(units, scenario) -> VictoryLevel:
    """The recovered ladder (0x9A07): equal -> DRAW; else the WINNER'S OWN
    score is the magnitude (1 tactical / 2 major / 3 decisive)."""
    units = list(units)
    brit = score_side(units, scenario, Side.BRITISH)
    axis = score_side(units, scenario, Side.AXIS)
    if brit == axis:
        return VictoryLevel.DRAW
    if brit > axis:
        return {1: VictoryLevel.BRITISH_TACTICAL,
                2: VictoryLevel.BRITISH_MAJOR,
                3: VictoryLevel.BRITISH_DECISIVE}[max(1, min(brit, 3))]
    return {1: VictoryLevel.AXIS_TACTICAL,
            2: VictoryLevel.AXIS_MAJOR,
            3: VictoryLevel.AXIS_DECISIVE}[max(1, min(axis, 3))]
