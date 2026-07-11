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
  terrain_logic.json      CODE-VERIFIED terrain typing: type_table (0xD90E), road-
                          direction table (0xDA0E), logic_type_grid = table[cell]&15.
                          Supersedes terrain_authentic.json's grid for game logic
                          (which is wrong for 2011/3200 cells) -- see NOTES.md.
  deployments.json        Per-scenario scripted starting deployments (0xDE53/0xEABF):
                          divisions deploy clustered at historical positions, often
                          sharing cells. Edge staging is only for later reinforcements.
  schedules.json          Turn-phased campaign schedule tables (0xDEFC/0xDF84/0xDFB6),
                          indexed by turn/30, incl. the Axis-only Malta modifier --
                          structure confirmed, value semantics hypotheses; see NOTES.md
                          and reference/extraction_tools/extract_schedules.py.
  (units_scenario_*.json, terrain_map.json, strings_table.json — superseded, kept for
   cross-checking.)

reference/            Provenance & audit trail (not required to build):
  engine-map.md           Full reverse-engineering map (addresses, routines, structures)
                          across 16 sections — the detective log behind the spec.
  prospects.md            Prioritised backlog of remaining/open items.
  desert_rats_arena.html  Reference implementation / mechanics sanity-check (playable).
                          SUPERSEDED as a playable front-end by arena/ (see below);
                          kept as a pre-oracle mechanics reference only.
  desert_rats_board.html  Map + named-units viewer.
  desert-rats-mechanics-spec.md, desert-rats-extraction-workflow.md   Earlier notes.
  extraction_tools/       Python scripts used to extract the data (for re-derivation).
```

## Content packs
The engine is generic; everything expressive lives in swappable packs under
`content_packs/` (see `desert_rats/packs.py`). `--pack default` plays the
historical North Africa theatre on an ORIGINAL map digitized from real
geography (`tools/build_default_map.py`); `--pack og` (the default for now)
plays the original 1985 data. A pack.json manifest can inherit another pack
and override any file. A pack may also provide a full cartographic map
IMAGE (`map.png` + `map_calibration.json`, fitted from anchor points by
`tools/calibrate_map_image.py`): the 100x32 grid stays the invisible
engine underlay and counters are transposed onto the image. The default
pack ships a baked 3200x1024 image of its own atlas. User-supplied
archive scans work too but are often still in copyright -- keep them
local and uncommitted (same policy as data/tiles_original.json). Long-term: the og pack is generated locally from your
own tape by reference/extraction_tools/, and the public repo ships only the
engine + clean packs.

## The application (web arena)

`arena/` is the application layer: a FastAPI server exposing the verified
engine over HTTP, plus a single-page browser client whose playfield is the
**authentic 256×192 game screen**, rendered server-side by
`desert_rats/render/screen.py` (22×22-cell viewport at 8px cells, side
panel with date and order menu, red status band) and displayed
integer-scaled with hard pixels. Clicks are mapped back onto the screen:
the viewport selects units and sets destinations, the panel rows issue
orders, ENTER ends the turn; arrow keys scroll the viewport and a small
overview minimap (navigation chrome, not part of the screen) jumps it.
The client holds **no rules and no art** — every mechanic runs in
`desert_rats/`, so the arena can never drift from the oracle-verified
engine the way the old embedded-JS prototype did.

Pixel authenticity follows the pack rules: with the local-only og art
present (`data/tiles_original.json`, `data/font_original.json` — private
extractions from your own tape via
`reference/extraction_tools/extract_render_tables.py`, gitignored, never
redistributed) the screen is pixel-exact; without them the server
degrades to the attribute-blend viewport and a plain-font panel with
identical geometry, and the client shows a warning.

```
pip install .[web]
python -m arena          # then open http://127.0.0.1:8000/
```

Pick a scenario and side modes (human/AI per side). AI seats are played
by `ai.plan_turn` (the recovered original planner). The screen endpoint
(`/api/games/{id}/screen`) plus the map payload (`/api/map`) are the
content-pack seam for future surfaces — a War Office skin is just a
different render behind the same API, no rule changes.

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
