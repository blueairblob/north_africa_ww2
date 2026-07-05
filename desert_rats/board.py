"""The 100x32 terrain map: load, coordinate/passability queries, footprint.

Loads data/terrain_logic.json -- the CODE-VERIFIED terrain typing. The
original movement code derives a cell's type as type_table[cell_byte] & 15
(table 0xD90E), NOT as the cell byte's own low nibble; the earlier
terrain_authentic.json grid (low-nibble types) is wrong for 2011 of 3200
cells and is retained only for provenance/cross-checking. Real type
legend (see data/terrain_logic.json and NOTES.md): 0 = open desert
(including all decorative coast/border/label art -- passable), 1 = sea
(impassable), 4 = escarpment, 5 = road, 6 = marsh/depression, 2/3/7/8
unknown-but-small (2 is passable: the British staging cell (98,11) sits
on one).

Per-terrain movement *cost* is not modelled here; the road discount and
mode multipliers belong to movement.py. This module exposes terrain type
lookup and blanket sea impassability.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import packs

DATA_DIR = Path(__file__).resolve().parent.parent / "data"  # legacy
TERRAIN_PATH = DATA_DIR / "terrain_logic.json"  # legacy; load_board goes through packs

WIDTH = 100
HEIGHT = 32
VIEWPORT_SIZE = 22

# Code-verified logic types (type_table[cell] & 15 -- see module docstring).
DESERT = 0
SEA = 1
ROAD = 5  # the mover's road test is literally: type == 5
ESCARPMENT = 4
MARSH = 6
ESCARPMENT_TYPES = (ESCARPMENT,)  # kept as a tuple for renderer reuse


@dataclass(frozen=True)
class TerrainInfo:
    name: str
    confidence: str


@dataclass(frozen=True)
class Board:
    """100x32 terrain grid. `grid[y][x]`; y=0 is the north/Mediterranean coast,
    x increases west (Axis side) to east (British side).
    """

    width: int
    height: int
    grid: tuple[tuple[int, ...], ...]
    legend: dict[int, TerrainInfo]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def terrain_at(self, x: int, y: int) -> int:
        if not self.in_bounds(x, y):
            raise IndexError(f"({x}, {y}) is outside the {self.width}x{self.height} board")
        return self.grid[y][x]

    def is_sea(self, x: int, y: int) -> bool:
        return self.terrain_at(x, y) == SEA

    def is_road(self, x: int, y: int) -> bool:
        return self.terrain_at(x, y) == ROAD

    def is_passable(self, x: int, y: int) -> bool:
        """Blanket passability: sea blocks land units, everything else is open.

        BUILD_SPEC.md §3.1: terrain affects cost/eligibility, not blanket
        blocking, beyond sea.
        """
        return self.in_bounds(x, y) and not self.is_sea(x, y)

    @staticmethod
    def footprint_cells(x: int, y: int, size: int = 2) -> tuple[tuple[int, int], ...]:
        """Cells covered by a unit's footprint: 2x2 normally, 1x1 while travelling.

        Pure geometry (no board state needed) so units.py can reuse it too.
        """
        if size == 1:
            return ((x, y),)
        if size == 2:
            return ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1))
        raise ValueError(f"footprint size must be 1 or 2, got {size}")

    def footprint_passable(self, x: int, y: int, size: int = 2) -> bool:
        """Whether every cell of a footprint is on-board and not sea.

        Does not check other units' occupancy — that needs live game state
        and belongs to units.py/movement.py.
        """
        return all(self.is_passable(cx, cy) for cx, cy in self.footprint_cells(x, y, size))

    def legend_for(self, terrain_type: int) -> TerrainInfo:
        return self.legend[terrain_type]


def load_board(path: Optional[Path] = None) -> Board:
    """Load and parse data/terrain_logic.json into a Board.

    The grid is the code-verified logic_type_grid (see module docstring);
    legend entries carry the confidence notes from the extraction.
    """
    path = Path(path) if path is not None else packs.active_pack().resolve("terrain_logic.json")
    if path is None:
        raise FileNotFoundError(
            f"active content pack {packs.active_pack().name!r} provides no terrain_logic.json"
        )
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    grid = tuple(tuple(row) for row in raw["logic_type_grid"])
    legend = {
        int(k): TerrainInfo(name=v, confidence="see data/terrain_logic.json")
        for k, v in raw["legend"].items()
    }

    if len(grid) != HEIGHT or any(len(row) != WIDTH for row in grid):
        got_w = len(grid[0]) if grid else 0
        raise ValueError(
            f"terrain_logic.json grid is {got_w}x{len(grid)}, expected {WIDTH}x{HEIGHT}"
        )

    return Board(width=WIDTH, height=HEIGHT, grid=grid, legend=legend)
