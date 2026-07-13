# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A clean-room handoff bundle for building a faithful **Python 3** reimplementation of
*Desert Rats* (CCS, 1985), a ZX Spectrum operational wargame of the North Africa campaign.
The repo currently contains the **specification and extracted game data only** — the
`desert_rats/` package and `tests/` directories exist but are **empty**; no implementation
has been written yet. There are no commits in this repo yet either.

**Read in this order before writing any code:**
1. `CLEANROOM_BRIEF.md` — the build remit, method, acceptance criteria, and hard boundary:
   do not consult, decompile, or copy the original Z80 binary/ROM. Build only from the spec
   and data files below.
2. `BUILD_SPEC.md` — the authoritative, implementation-oriented rules/data specification.
   This is the primary reference for all game logic; it is self-contained.
3. `reference/prospects.md` — prioritised backlog of what's still inferred vs. confirmed.
4. `reference/engine-map.md` — the reverse-engineering provenance/audit trail (Z80 routine
   addresses). Read-only; needed only to resolve ambiguity, not to implement.

## Non-negotiable design constraint: determinism

**The original engine has no RNG anywhere** (verified — no dice, no seeded randomness in
any logic path). The clone must be equally deterministic: identical inputs → identical
state, always. Do not add randomness for "wargame feel." This is what makes the clone
testable — a state-diff harness (BUILD_SPEC.md §12) can compare turn-by-turn state against
emulator golden traces. Any tie-break must be deterministic (e.g. by unit id / scan order).

## Intended architecture (per BUILD_SPEC.md §11)

The package does not exist yet, but the spec prescribes this module layout and build order.
Build and test each module before moving to the next — get a correct headless 2-player game
working before AI or rendering:

```
desert_rats/
  data.py         # load JSON data (data/*.json) into typed structures (Unit, Scenario, Map)
  board.py        # 100x32 map, terrain, passability, coordinates, viewport
  units.py        # Unit model, footprint (2x2 normal / 1x1 travelling), branch derivation
  zoc_supply.py   # per-cell flag grid; zone of control; edge-trace supply + curve + bands
  movement.py     # orders, step cost + mode multipliers, Travel, contact-stop
  combat.py       # effective power, assault resolution, attrition, recovery
  reinforce.py    # clock, arrival admission, edge staging
  victory.py      # front line, objective scoring, tactical/major/decisive ladder
  ai.py           # budget-limited planner, regional strength map, offensive band, ray-scan
  game.py         # turn loop, per-side phases, state machine, end conditions
  render/         # terminal or 2D renderer; colour compositing; tiles
  main.py         # title/options -> scenario select -> game
tests/
  test_*.py       # unit tests per module + the state-diff harness (BUILD_SPEC.md §12)
```

Build order: **data → board → units → zoc_supply → movement → combat → reinforce →
victory → game (loop) → ai → render**. Keep all state in plain, serialisable structures so a
full game snapshot can be diffed against a golden trace.

## Core rules to internalise (full detail in BUILD_SPEC.md)

- **One master OOB, one 624-day timeline.** `data/master_oob.json` has all 128 units; each
  scenario (`data/scenarios.json`, 6 of them) is just a day-window that includes units by
  `arrival ≤ scenario window`. There is no per-scenario unit data beyond that filter.
- **Campaign clock:** `clock = (turn_counter + 2) // 3` — one campaign "day" per 3 turns.
- **Sides:** British (blue) vs Axis = German (black) + Italian (magenta). Nationality field
  1/2/3 maps to British/German/Italian; side is derived (German+Italian → Axis).
- **Board:** 100 wide × 32 tall, row-major, `grid[y][x]`. x: west(Axis)→east(British).
  y: 0 = Mediterranean coast (north). Terrain type 0=desert/open, 5=road/track,
  14=sea/impassable, 2&3=escarpment.
- **Units** normally occupy a 2×2 footprint; while under a Travel order they collapse to
  1×1 (road movement, ×0.5 cost, re-forms to 2×2 on arrival unless "caught" adjacent to an
  enemy, which doubles combat loss).
- **Supply** is traced from each side's board edge (British: east, Axis: west) via
  shortest path blocked by enemy units/ZOC; delivered level follows a fixed curve indexed
  by `distance // 4` (§5.4). Out-of-supply units suffer attrition.
- **Combat:** `effective_power = strength * efficiency / 100`. Loser takes −10 efficiency
  (−20 if caught-on-road) and is forced to Hold. Out-of-supply/in-enemy-ZOC attrition is
  −3/turn; recovery is `+= (100 - efficiency) // 16 + 1` per turn when safe. 0 efficiency =
  unit destroyed.
- **Turn loop** (BUILD_SPEC.md §4.2): increment turn/clock → admit reinforcements → rebuild
  ZOC+supply → for each side (British, then Axis) collect/execute orders and resolve
  movement+combat → apply attrition/recovery → check victory → render.
- **AI** (BUILD_SPEC.md §6): deterministic budget-limited heuristic planner (budget H=40,
  no search tree), not min-max/game-tree search. Units within ±25 columns of the front-line
  midpoint act offensively; others act defensively.

## Confirmed vs. inferred constants

BUILD_SPEC.md §10 has the authoritative ledger. In short: map data, OOB, clock formula,
supply curve, combat efficiency deltas, Travel cost/footprint rules, and AI band width are
**confirmed** — implement exactly. Things like the exact combat "readiness" numerator
semantics, base per-cell movement cost, supply sourcing split (HQ-local vs edge-trace),
minor order effects (Divide/Fortify/Go-To-Port), and AI target-region weighting are
**inferred/tunable** — implement the simplest deterministic model, expose it as a named
constant, and let the validation harness (§12) pin the true value later. Do not invent
extra mechanics or randomness to fill these gaps.

## Data files (`data/`)

Load these, do not hand-transcribe rules from them beyond what BUILD_SPEC.md §9 documents:
- `master_oob.json` — the 128-unit order of battle (single source of all units).
- `scenarios.json` — the 6 scenario day-windows, objectives, thresholds.
- `terrain_authentic.json` — the 100×32 terrain grid (legacy; `terrain_logic.json` supersedes it for game logic).
- `ui_strings.json` — all UI text; reuse verbatim for authenticity (menus, orders, supply
  bands, victory ladder, calendar).
- `unit_name_tables.json` — designation/division name tables.
- `graphics.json` — tile/colour/draw model. The source ART is **not committed**:
  regenerate it locally from your own tape (see "Original art" in README.md).
- `units_scenario_*.json`, `terrain_map.json`, `strings_table.json` are **superseded**
  legacy extracts, kept only for cross-checking — don't build against them.

## Reference material (not build inputs)

- `reference/desert_rats_arena.html` — the pre-oracle playable JS prototype, SUPERSEDED
  as a front-end by `arena/` (engine-backed web application; see README "The application").
  Keep it only as a historical mechanics reference; never update its embedded JS engine.
- `reference/desert_rats_board.html` — map + named-units viewer.
- `reference/extraction_tools/*.py` — the SkoolKit-based scripts used to originally extract
  `data/*` from ZX Spectrum snapshots (diff snapshots, extract OOB, digitize map, etc). Only
  relevant if re-deriving or auditing data, not for game implementation.
- `py3/` is a Python 3.12 venv with only `skoolkit` installed — it supports the extraction
  tools above (disassembly/snapshot analysis), not the game implementation itself. Use your
  own environment/dependencies for building `desert_rats/`.

## Validation strategy

Because the engine is deterministic, faithfulness is provable, not just aspirational
(BUILD_SPEC.md §12): run the original in a ZX Spectrum emulator (Fuse) to produce golden
per-turn state traces, then diff the clone's state turn-by-turn on the same scripted input.
Any mismatch points at exactly one inferred constant in §10 to fix. Stand this harness up
early — it doubles as the test suite's backbone.
