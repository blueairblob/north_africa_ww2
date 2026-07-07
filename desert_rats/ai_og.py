"""The ORIGINAL game's AI decision layer, recovered by disassembly and
oracle execution (reference/diff_harness/, reference/engine-map.md §15).

Recovered structure ("THINKING!", entry 0xA39E):

STRATEGIC LAYER (this module's core -- was the "still fuzzy" part):
- 30 static strategic REGIONS (data/ai_regions.json; anchors + importance
  0-7). Each unit belongs to the region with the nearest anchor.
- Per-region tallies (builder 0xA9EA, disassembled):
  unit weight = strength >> 5, halved again when MPS < 5;
  friendly weight (note: the ORIGINAL STORES the last friendly unit's
  weight instead of accumulating -- `LD (IY+5),D` where `LD (IY+5),A`
  was clearly intended; we reproduce the bug for 1:1), enemy weight
  (summed correctly), presence flags, enemy-assaulting flag.
- Force posture: H = friendly unit count, L = count with MPS >= 36;
  the "mobile posture" flag is set when L exceeds 3/4 of H (or 1/2 with
  hysteresis when already mobile) -- disassembled at 0xAA7C-0xAA9A.
- REGION SCORING (0xAAE7-0xAB44, disassembled -- exact):
    no enemy weight              -> 0
    enemy, friendly = 0          -> 96 + importance, only within the
                                    side's reach window (per-side
                                    frontier bound; Axis: region index
                                    <= axis_bound; British: index >
                                    british_bound - 10)
    enemy >= friendly (contested)-> 60 + importance
    friendly > 2 x enemy         -> 50 + importance (mop up)
    otherwise                    -> 0
- TARGET: the best-scoring region's anchor becomes the side target
  (0xCB32); the chooser walks the objective ladder DIRECTIONALLY
  (Axis west->east, British east->west; 0xA510/0xA537).

PER-UNIT LAYER (recovered earlier, engine-map §15):
- Budget-limited passes (H = 40, each full pass costs 10).
- A unit within the 50-column band centred on the front-line midpoint
  is OFFENSIVE (moves toward the target); outside it is DEFENSIVE:
  assault an adjacent enemy if any, else move toward the target;
  a unit whose target is the board edge (x = 98) is sent to port.

Everything labelled "exact" above is disassembled/oracle-verified; the
ladder-walk tie-breaking beyond side direction is inferred (documented
in NOTES.md).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import packs
from .data import Side
from .units import Order, Unit

DECISION_BUDGET = 40
PASS_COST = 10
BAND_HALF_WIDTH = 25
FAST_MPS = 36
SLOW_MPS = 5
EDGE_PORT_X = 98

SCORE_UNDEFENDED = 96
SCORE_CONTESTED = 60
SCORE_MOP_UP = 50


def _load_regions() -> List[dict]:
    path = packs.active_pack().resolve("ai_regions.json")
    if path is None:
        return []
    return json.loads(Path(path).read_text())["regions"]


_regions_cache: Dict[str, List[dict]] = {}


def regions() -> List[dict]:
    key = packs.active_pack().name
    if key not in _regions_cache:
        _regions_cache[key] = _load_regions()
    return _regions_cache[key]


def unit_weight(unit: Unit) -> int:
    """Oracle-verified: strength >> 5, halved again when MPS < 5."""
    w = unit.strength >> 5
    if unit.mps < SLOW_MPS:
        w >>= 1
    return w


def region_of(x: int, y: int, table: List[dict]) -> int:
    """Nearest-anchor region assignment (squared euclidean, both anchors)."""
    best, best_d = 0, None
    for r in table:
        for ax, ay in (r["anchor_a"], r["anchor_b"]):
            if ax == 0 and ay == 0:
                continue
            d = (x - ax) ** 2 + (y - ay) ** 2
            if best_d is None or d < best_d:
                best, best_d = r["index"], d
    return best


def build_region_tallies(units: List[Unit], side: Side, table: List[dict]):
    """The 0xA9EA builder: per-region friendly/enemy weights + flags.
    Reproduces the original's store-instead-of-accumulate on the
    friendly weight (1:1 bug compatibility).
    """
    tallies = {r["index"]: {"friendly": 0, "enemy": 0,
                            "enemy_assaulting": False,
                            "importance": r["importance"]}
               for r in table}
    for u in units:
        if u.is_destroyed:
            continue
        idx = region_of(u.x, u.y, table)
        w = unit_weight(u)
        if u.side is side:
            tallies[idx]["friendly"] = w          # original bug: store, not add
        else:
            tallies[idx]["enemy"] += w            # enemies accumulate correctly
            if u.order is Order.ASSAULT:
                tallies[idx]["enemy_assaulting"] = True
    return tallies


def score_region(t: dict, index: int, side: Side,
                 axis_bound: int = 29, british_bound: int = 10) -> int:
    """The exact 0xAAE7-0xAB44 scoring."""
    enemy, friendly = t["enemy"], t["friendly"]
    if enemy == 0:
        return 0
    if friendly > enemy:
        if enemy * 2 < friendly:
            return SCORE_MOP_UP + t["importance"]
        return 0
    if friendly == 0:
        if side is Side.BRITISH:
            if index <= british_bound - 10:
                return 0
        else:
            if index > axis_bound:
                return 0
        return SCORE_UNDEFENDED + t["importance"]
    return SCORE_CONTESTED + t["importance"]


def choose_target(units: List[Unit], side: Side,
                  table: Optional[List[dict]] = None) -> Optional[Tuple[int, int]]:
    """Score all regions and return the best region's primary anchor;
    ties broken in the side's advance direction (Axis prefers the
    western/earlier region, British the eastern/later -- the
    directional ladder walk)."""
    table = table if table is not None else regions()
    if not table:
        return None
    tallies = build_region_tallies(units, side, table)
    order = sorted(tallies.keys())
    if side is Side.BRITISH:
        order = list(reversed(order))
    best_idx, best_score = None, 0
    for idx in order:
        s = score_region(tallies[idx], idx, side)
        if s > best_score:
            best_idx, best_score = idx, s
    if best_idx is None:
        return None
    r = next(r for r in table if r["index"] == best_idx)
    ax, ay = r["anchor_a"]
    if ax == 0 and ay == 0:
        ax, ay = r["anchor_b"]
    return ax, ay


# The per-unit layer (band test, assault-on-contact, move-to-target,
# edge-retreat) lives in ai.py, recovered earlier from the same
# disassembly; ai.plan_turn now takes its strategic target from
# choose_target above.
