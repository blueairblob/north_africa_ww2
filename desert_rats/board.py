"""The 100x32 terrain map: load, coordinate/passability queries, footprint.

Loads data/terrain_authentic.json. Per-terrain movement *cost* is not
modelled here — BUILD_SPEC.md §5.1 notes there is no per-terrain toll table
(only a road-based mode multiplier, which belongs to movement.py); this
module only exposes terrain type lookup and blanket sea impassability.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TERRAIN_PATH = DATA_DIR / "terrain_authentic.json"

WIDTH = 100
HEIGHT = 32
VIEWPORT_SIZE = 22

DESERT = 0
ROAD = 5
SEA = 14
# Types 2/3 in data/terrain_authentic.json's legend ("Escarpment (E-W
# ridge)" / "Escarpment / coastal ridge"). Confirmed to render as a
# distinct tile (not flat desert) by a real gameplay screenshot -- see
# render/image.py's ESCARPMENT_TILE_BYTES and NOTES.md.
ESCARPMENT_TYPES = (2, 3)


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
    """Load and parse data/terrain_authentic.json into a Board."""
    path = Path(path) if path is not None else TERRAIN_PATH
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    grid = tuple(tuple(row) for row in raw["grid"])
    legend = {
        int(k): TerrainInfo(name=v["name"], confidence=v["confidence"])
        for k, v in raw["legend"].items()
    }

    width, height = raw["width"], raw["height"]
    if len(grid) != height or any(len(row) != width for row in grid):
        got_w = len(grid[0]) if grid else 0
        raise ValueError(
            f"terrain_authentic.json declares {width}x{height} but grid is {got_w}x{len(grid)}"
        )

    return Board(width=width, height=height, grid=grid, legend=legend)
