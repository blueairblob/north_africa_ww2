"""Colour compositing model (BUILD_SPEC.md §8).

Confirmed: ink comes from the unit's *nationality* (not just side --
German and Italian, both Axis, have different inks), historic ZX Spectrum
palette: British blue(1), German black(0), Italian magenta(3). Paper comes
from terrain, "mostly PAPER 6 = desert yellow; features vary" -- the
per-terrain-type paper table isn't recovered (§10), so only the one
confirmed distinct case (sea) gets its own paper here; everything else is
desert yellow, a documented simplification, not a lookup gap.

Tile-graphic assignment isn't recovered either (§10), so units/terrain
render as branch-letter glyphs / ASCII terrain symbols rather than the
original's 8x8 tile art -- BUILD_SPEC.md §1/§8 explicitly accepts a
text/terminal renderer; pixel-exactness is a later, optional tier.
"""
from __future__ import annotations

from ..board import ROAD, SEA
from ..data import Nationality
from ..units import Branch

# The historic Spectrum ink codes, kept alongside the terminal ANSI
# mapping below for provenance/fidelity even though only the ANSI codes
# are used to actually draw anything here.
SPECTRUM_INK = {
    Nationality.BRITISH: 1,
    Nationality.GERMAN: 0,
    Nationality.ITALIAN: 3,
}

ANSI_RESET = "\x1b[0m"

# Pure ANSI black (German's ink=0) is usually invisible against a typical
# dark terminal background, so it's rendered bright-black/grey instead --
# a legibility substitution, not a rules change.
ANSI_INK = {
    Nationality.BRITISH: "\x1b[34m",
    Nationality.GERMAN: "\x1b[90m",
    Nationality.ITALIAN: "\x1b[35m",
}

ANSI_PAPER_DESERT = "\x1b[43m"
ANSI_PAPER_SEA = "\x1b[44m"


def terrain_paper(terrain_type: int) -> str:
    return ANSI_PAPER_SEA if terrain_type == SEA else ANSI_PAPER_DESERT


def terrain_glyph(terrain_type: int) -> str:
    if terrain_type == SEA:
        return "~"
    if terrain_type == ROAD:
        return "="
    return "."


BRANCH_GLYPH = {
    Branch.ARMOUR: "A",
    Branch.RECCE: "R",
    Branch.ARTILLERY: "G",
    Branch.INFANTRY: "I",
    Branch.OTHER: "H",
}


def unit_glyph(unit) -> str:
    return BRANCH_GLYPH[unit.branch]
