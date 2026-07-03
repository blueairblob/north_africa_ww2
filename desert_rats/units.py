"""Runtime unit model: position, footprint (2x2 / 1x1 while travelling),
dest/order/travel/caught state, and branch derivation from designation.

See BUILD_SPEC.md §3.2. This module builds runtime `Unit`s from the static
roster (`data.Unit`) but does not itself place them on the board — initial
(x, y) is assigned by the caller (reinforce.py) at reinforcement entry.
`mps` defaults to the roster's `data.Unit.mps` (merged from
data/unit_mps.json -- see that module's docstring) but can be overridden by
the caller, e.g. reinforce.admit_reinforcements' flat-mps test override.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Optional

from .board import Board
from .data import SIDE_OF_NATIONALITY, Nationality, Side
from .data import Unit as OobUnit

# BUILD_SPEC.md §5.5: the assault-resolution threshold uses a fixed
# override "20 if the unit is armour (type 10)" — this is the one place
# the raw `type` code (as opposed to the designation-derived branch) is
# load-bearing for rules.
ARMOUR_TYPE_CODE = 10


class Order(IntEnum):
    """Order/mode codes, in the original menu order (BUILD_SPEC.md §5.1)."""

    MOVE = 1
    ASSAULT = 2
    HOLD = 3
    TRAVEL = 4
    REPORT = 5
    DIVIDE = 6
    FORTIFY = 7
    GO_TO_PORT = 8


class Branch(str, Enum):
    """Display branch, derived from the designation string, not `type`.

    BUILD_SPEC.md §3.2: "`type` ... is *not* a clean branch ... the unit's
    identity/branch comes from its designation, not this field." The
    keyword mapping below is a best-effort heuristic (unconfirmed), not a
    recovered table — treat it as tunable/display-only.
    """

    ARMOUR = "Armour"
    RECCE = "Recce"
    ARTILLERY = "Artillery"
    INFANTRY = "Infantry"
    OTHER = "Other"


# Checked in order; first match wins. Armoured-car and recce-named units
# are cavalry/reconnaissance formations even though "Armoured" also appears
# in pure tank formation names, so recce keywords are checked first.
_RECCE_KEYWORDS = ("armoured car", "armored car", "recce", "reconnaissance", "hussars", "dragoon")
_ARTILLERY_KEYWORDS = ("artillery", "a/t battalion", "a/t bn", "anti-tank", "anti tank")
_ARMOUR_KEYWORDS = ("panzer", "armoured", "armored", "tank")
_INFANTRY_KEYWORDS = (
    "infantry", "rifle", "bersaglieri", "parachute", "guards", "mg battalion",
    "motor", "lorried",
)


def derive_branch(designation: str) -> Branch:
    """Best-effort display branch from a unit's designation text."""
    text = designation.lower()
    if any(kw in text for kw in _RECCE_KEYWORDS):
        return Branch.RECCE
    if any(kw in text for kw in _ARTILLERY_KEYWORDS):
        return Branch.ARTILLERY
    if any(kw in text for kw in _ARMOUR_KEYWORDS):
        return Branch.ARMOUR
    if any(kw in text for kw in _INFANTRY_KEYWORDS):
        return Branch.INFANTRY
    return Branch.OTHER


@dataclass
class Unit:
    """A unit's full runtime state (BUILD_SPEC.md §3.2). Mutable — position,
    efficiency, orders, etc. change every turn.
    """

    oob_index: int
    nationality: Nationality
    designation: str
    division: Optional[str]
    name: str
    type: int
    role: int
    strength: int
    morale: int
    arrival: int
    x: int
    y: int
    mps: int
    dest_x: Optional[int] = None
    dest_y: Optional[int] = None
    efficiency: int = 100
    supply: Optional[int] = None
    order: Order = Order.HOLD
    travel: bool = False
    caught: bool = False

    @property
    def side(self) -> Side:
        return SIDE_OF_NATIONALITY[self.nationality]

    @property
    def branch(self) -> Branch:
        return derive_branch(self.designation)

    @property
    def is_armour_type(self) -> bool:
        """Whether `type` is the combat-threshold armour override (§5.5)."""
        return self.type == ARMOUR_TYPE_CODE

    @property
    def footprint_size(self) -> int:
        """2x2 normally, 1x1 while travelling (BUILD_SPEC.md §5.2)."""
        return 1 if self.travel else 2

    def footprint_cells(self) -> tuple[tuple[int, int], ...]:
        return Board.footprint_cells(self.x, self.y, self.footprint_size)

    @property
    def is_destroyed(self) -> bool:
        """BUILD_SPEC.md §5.5: a unit reduced to 0 efficiency is destroyed."""
        return self.efficiency <= 0

    @classmethod
    def from_oob(
        cls,
        oob_unit: OobUnit,
        *,
        x: int,
        y: int,
        mps: int,
        dest_x: Optional[int] = None,
        dest_y: Optional[int] = None,
        efficiency: int = 100,
        supply: Optional[int] = None,
        order: Order = Order.HOLD,
        travel: bool = False,
        caught: bool = False,
    ) -> "Unit":
        """Build runtime state for a roster entry entering the board.

        `x`, `y` have no source in data/master_oob.json (a unit's live
        board position is assigned at reinforcement entry, not roster load)
        so the caller must supply them — typically reinforce.py placing the
        unit at its side's board-edge staging point. `mps` is required too;
        callers normally pass `oob_unit.mps` (see the module docstring).
        """
        return cls(
            oob_index=oob_unit.index,
            nationality=oob_unit.nationality,
            designation=oob_unit.designation,
            division=oob_unit.division,
            name=oob_unit.name,
            type=oob_unit.type,
            role=oob_unit.role,
            strength=oob_unit.strength,
            morale=oob_unit.morale,
            arrival=oob_unit.arrival,
            x=x,
            y=y,
            mps=mps,
            dest_x=dest_x,
            dest_y=dest_y,
            efficiency=efficiency,
            supply=supply,
            order=order,
            travel=travel,
            caught=caught,
        )
