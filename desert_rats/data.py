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

from . import packs

DATA_DIR = Path(__file__).resolve().parent.parent / "data"  # legacy; loaders go through packs
MASTER_OOB_PATH = DATA_DIR / "master_oob.json"
SCENARIOS_PATH = DATA_DIR / "scenarios.json"
UNIT_MPS_PATH = DATA_DIR / "unit_mps.json"
DEPLOYMENTS_PATH = DATA_DIR / "deployments.json"


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
    (position, efficiency, order, travel, caught, ...) belongs to
    units.py/reinforce.py, not this static roster.

    `mps` is NOT part of the 10-byte table (it has no mps field at all) --
    it's merged in from data/unit_mps.json, derived from a *different*,
    live-state table observed in the superseded per-scenario snapshot files
    (see reference/extraction_tools/derive_unit_mps.py). `mps_confidence`
    records how: "confirmed" (seen on-map for exactly this unit),
    "confirmed_majority(...)" (seen for this unit across snapshots with one
    dissenting reading, e.g. an off-map zero), "type_fallback(...)" (no
    direct sighting; majority value for other on-map units sharing this
    unit's `type` code), or "global_fallback(...)" (type never sighted
    on-map either; overall majority value). 56/128 units are "unit"-sourced,
    67/128 "type"-sourced, 5/128 "global"-sourced -- see NOTES.md.
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
    # Defaults let existing tests build a bare Unit(...) without mps data;
    # load_master_oob() always supplies real values from unit_mps.json.
    mps: int = 6
    mps_confidence: str = "not_from_oob_pipeline"

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


def _load_unit_mps(path: Optional[Path] = None) -> dict:
    """Load data/unit_mps.json's per-index mps table.

    Derived data (see reference/extraction_tools/derive_unit_mps.py), not
    part of the original 10-byte master_oob table -- see Unit's docstring.
    """
    path = Path(path) if path is not None else packs.active_pack().resolve("unit_mps.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["units"]


def load_master_oob(
    path: Optional[Path] = None, mps_path: Optional[Path] = None
) -> OrderOfBattle:
    """Load and parse data/master_oob.json into an OrderOfBattle.

    mps is merged in from data/unit_mps.json (see Unit's docstring); pass
    mps_path to override its location (e.g. in tests).
    """
    path = Path(path) if path is not None else packs.active_pack().resolve("master_oob.json")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    mps_table = _load_unit_mps(mps_path)

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
            mps=mps_table[str(u["i"])]["mps"],
            mps_confidence=mps_table[str(u["i"])]["confidence"],
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
    path = Path(path) if path is not None else packs.active_pack().resolve("scenarios.json")
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


def load_deployments(path: Optional[Path] = None) -> dict:
    """Load data/deployments.json: scenario index (int) -> list of
    {"oob_index", "x", "y"} scripted starting placements.

    Recovered from the original's per-scenario deployment lists (see
    reference/extraction_tools/extract_deployments.py and NOTES.md):
    initial deployment is scripted historical data -- divisions deploy
    clustered, often sharing cells -- and edge staging applies only to
    later reinforcements. Returns {} if the file is absent so synthetic
    setups degrade to edge staging.
    """
    path = Path(path) if path is not None else packs.active_pack().resolve("deployments.json")
    if path is None or not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw["scenarios"].items()}
