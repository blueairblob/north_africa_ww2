# Desert Rats — Clean-Room Recreation Package

Everything needed to build a faithful **Python** reimplementation of the 1985 ZX Spectrum
wargame *Desert Rats* (CCS; original programmer R.T. Smith), reconstructed by disassembly
and data extraction from the original image.

> **Start here:** read `CLEANROOM_BRIEF.md` (the remit), then `BUILD_SPEC.md` (the full
> rules & data spec). Build from those plus `data/`. Do **not** use the original binary.

## What this is
A self-contained handoff bundle: a product/rules specification, the extracted game data,
and a provenance/audit trail — enough for a clean-room agent (or developer) to build a
playable, rules-faithful clone and to *verify* it (the engine is fully deterministic, so
faithfulness is testable — see spec §12).

## Contents
```
BUILD_SPEC.md         Authoritative build specification (PRD): model, rules, constants,
                      build plan, validation strategy, confirmed-vs-inferred ledger.
CLEANROOM_BRIEF.md    The building agent's remit, method, acceptance criteria, boundaries.
README.md             This file.

data/                 Extracted game data — the build inputs:
  master_oob.json         128-unit order of battle (nationality, names, strength,
                          arrival day, type) — the single source of all units.
  scenarios.json          6 scenarios: day-window, objectives, unit thresholds.
  terrain_authentic.json  100x32 terrain grid (low-nibble type) + graded legend.
  terrain_authentic.png   Colour render of the map (reference).
  ui_strings.json         All UI text (menus, orders, bands, victory ladder, calendar).
  unit_name_tables.json   Designation/division tables + token encoding.
  graphics.json           Tile base/format, colour tables (decoded), draw model, palette.
  tiles_sheet.png         Rendered 8x8 tile/sprite/glyph sheet (source art).
  unit_mps.json            Per-unit movement points, derived (not part of the original
                          10-byte OOB table) -- see NOTES.md and
                          reference/extraction_tools/derive_unit_mps.py.
  render_model.json       Recovered render model: 256-entry attribute table (0xD80E),
                          full-byte 100x32 tile-index grid (0xCB39), per-tile ink
                          coverage. Tile BITMAPS are original pixel art and are NOT
                          committed -- regenerate data/tiles_original.json locally with
                          reference/extraction_tools/extract_render_tables.py.
  (units_scenario_*.json, terrain_map.json, strings_table.json — superseded, kept for
   cross-checking.)

reference/            Provenance & audit trail (not required to build):
  engine-map.md           Full reverse-engineering map (addresses, routines, structures)
                          across 16 sections — the detective log behind the spec.
  prospects.md            Prioritised backlog of remaining/open items.
  desert_rats_arena.html  Reference implementation / mechanics sanity-check (playable).
  desert_rats_board.html  Map + named-units viewer.
  desert-rats-mechanics-spec.md, desert-rats-extraction-workflow.md   Earlier notes.
  extraction_tools/       Python scripts used to extract the data (for re-derivation).
```

## How to use
1. **Read** `CLEANROOM_BRIEF.md` then `BUILD_SPEC.md`.
2. **Load** `data/*` into typed structures (spec §3, §9).
3. **Implement** in the module order in spec §11 — headless, test-first; get a correct
   2-player game before AI and rendering.
4. For anything the spec marks **inferred/tunable** (§10), use the simplest deterministic
   model and expose it as a named constant. Do **not** add randomness.
5. **Validate** with the diff harness (§12): compare turn-by-turn state against an
   emulator trace; divergences pin the inferred constants.

## Key facts to internalise first
- **No RNG anywhere** — the engine is deterministic; outcomes are a pure function of
  state. This is what makes the clone verifiable.
- **One master OOB + one 624-day timeline**; each scenario is a day-window that includes
  units by arrival date.
- **Three nationalities, two sides:** British (blue) vs Axis = German (black) + Italian
  (magenta).
- **Confirmed vs inferred** is spelled out in spec §10 — build the confirmed parts
  exactly; treat the rest as tunable and let validation settle them.

## Status
Reverse-engineering is functionally complete: load structure, control flow, turn loop,
movement/Travel, combat, supply, ZOC, reinforcements, victory, scenarios, the AI, and the
presentation/colour model are all mapped. Remaining items are refinements (spec §10,
`reference/prospects.md`), not blockers. What's left is to **build and validate**.

## Provenance / licensing note
Game *logic* is described here as an original specification. Game *data* was extracted
from the original image and is included for reconstruction. Respect the original's
copyright: build the clone from this spec and data; do not redistribute the original
binary/ROM. A shippable build should run from re-created or user-supplied data of the same
shape.
