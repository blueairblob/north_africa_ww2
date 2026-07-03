"""Static roster and scenario data: load data/master_oob.json and
data/scenarios.json into typed structures. The terrain grid lives in
board.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MASTER_OOB_PATH = DATA_DIR / "master_oob.json"
SCENARIOS_PATH = DATA_DIR / "scenarios.json"


class Nationality(str, Enum):
    BRITISH = "British"
    GERMAN = "German"
    ITALIAN = "Italian"


class Side(str, Enum):
    BRITISH = "British"
    AXIS = "Axis"


SIDE_OF_NATIONALITY = {
    Nationality.BRITISH: Side.BRITISH,
    Nationality.GERMAN: Side.AXIS,
    Nationality.ITALIAN: Side.AXIS,
}


def opposing_side(side: Side) -> Side:
    return Side.AXIS if side is Side.BRITISH else Side.BRITISH


@dataclass(frozen=True)
class Unit:
    """One master order-of-battle roster entry (data/master_oob.json).

    Fields mirror the packed 10-byte OOB record (table at 0xEF58). `x` is
    that record's raw positioning byte, used by the original unpacker to
    place units within a formation at setup time — it is *not* a live
    board coordinate (observed range ~1-12, far smaller than the 100-wide
    map). A unit's actual (x, y) on the map is assigned at reinforcement
    entry (BUILD_SPEC.md §5.6) and changes during play; that runtime state
    (position, mps, efficiency, order, travel, caught, ...) belongs to
    units.py/reinforce.py, not this static roster.
    """

    index: int
    nationality: Nationality
    designation: str
    division: Optional[str]
    name: str
    x: int
    strength: int
    type: int
    arrival: int
    morale: int
    role: int

    @property
    def side(self) -> Side:
        return SIDE_OF_NATIONALITY[self.nationality]


@dataclass(frozen=True)
class OrderOfBattle:
    """The full master roster plus its source metadata."""

    source: str
    fields_note: str
    units: tuple[Unit, ...]

    def __len__(self) -> int:
        return len(self.units)

    def __iter__(self):
        return iter(self.units)

    def by_index(self, index: int) -> Unit:
        return self.units[index]

    def by_side(self, side: Side) -> tuple[Unit, ...]:
        return tuple(u for u in self.units if u.side is side)

    def by_nationality(self, nationality: Nationality) -> tuple[Unit, ...]:
        return tuple(u for u in self.units if u.nationality is nationality)

    def arriving_by(self, day: int) -> tuple[Unit, ...]:
        """Units whose arrival day has passed by the given campaign day.

        This is the arrival-gate filter BUILD_SPEC.md §7 describes: every
        scenario is populated by taking this master OOB and including every
        unit whose arrival <= the scenario window.
        """
        return tuple(u for u in self.units if u.arrival <= day)


def load_master_oob(path: Optional[Path] = None) -> OrderOfBattle:
    """Load and parse data/master_oob.json into an OrderOfBattle."""
    path = Path(path) if path is not None else MASTER_OOB_PATH
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    units = tuple(
        Unit(
            index=u["i"],
            nationality=Nationality(u["nationality"]),
            designation=u["designation"],
            division=u["division"],
            name=u["name"],
            x=u["x"],
            strength=u["strength"],
            type=u["type"],
            arrival=u["arrival"],
            morale=u["morale"],
            role=u["role"],
        )
        for u in raw["units"]
    )

    if len(units) != raw["count"]:
        raise ValueError(
            f"master_oob.json declares count={raw['count']} but has {len(units)} units"
        )

    return OrderOfBattle(source=raw["source"], fields_note=raw["fields"], units=units)


@dataclass(frozen=True)
class Scenario:
    """One of the 6 day-windows into the 624-day campaign (data/scenarios.json).

    `british_objectives`/`axis_objectives` are (column, type) pairs -- map
    x-columns that side is expected to hold. The `type` code's exact
    semantics are partly inferred (BUILD_SPEC.md §10); victory.py treats
    every objective as equally weighted.
    """

    index: int
    name: str
    start_day: int
    end_day: int
    british_objectives: tuple[tuple[int, int], ...]
    axis_objectives: tuple[tuple[int, int], ...]
    unit_thresholds: dict


def load_scenarios(path: Optional[Path] = None) -> tuple[Scenario, ...]:
    """Load and parse data/scenarios.json into the 6 Scenarios, in order."""
    path = Path(path) if path is not None else SCENARIOS_PATH
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    return tuple(
        Scenario(
            index=s["index"],
            name=s["name"],
            start_day=s["start_day"],
            end_day=s["end_day"],
            british_objectives=tuple(tuple(pair) for pair in s["british_objectives"]),
            axis_objectives=tuple(tuple(pair) for pair in s["axis_objectives"]),
            unit_thresholds=dict(s["unit_thresholds"]),
        )
        for s in raw["scenarios"]
    )
