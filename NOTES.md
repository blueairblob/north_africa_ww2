# NOTES — inferred/tunable decisions

Per `CLEANROOM_BRIEF.md`'s deliverables: every point where `BUILD_SPEC.md` §10
marks a value as inferred or leaves a formula unrecovered, and the choice made
here to fill it in. Each entry names the constant/function and its file so a
later validation pass (§12, diff against emulator golden traces) knows exactly
what to adjust and where. Ordered by module build order.

## units.py

- **`ARMOUR_TYPE_CODE = 10`** — the one place the raw OOB `type` field is
  load-bearing for rules (combat's armour threshold override, §5.5).
  Everywhere else, "branch" is derived from designation text, not `type`.
- **`derive_branch()` / `_RECCE_KEYWORDS` / `_ARTILLERY_KEYWORDS` /
  `_ARMOUR_KEYWORDS` / `_INFANTRY_KEYWORDS`** — display branch
  (armour/recce/artillery/infantry/other) is a keyword heuristic over the
  designation string. BUILD_SPEC.md §3.2 says branch comes from designation
  but gives no table; this mapping is unconfirmed and display-only (doesn't
  affect any rule).
- **`mps` has no source in `data/master_oob.json` at all** — confirmed: the
  table's own `fields` string lists 10 fields and mps isn't one of them.
  **Update: closed, to the extent the current data allows.** The three
  superseded per-scenario snapshot files (`units_scenario_enter_rommel.json`,
  `_battleaxe.json`, `_operation_crusader.json`) turn out to be pulled from a
  *different*, live-state table that does carry a real per-unit mps byte for
  every `on_map: true` record. `reference/extraction_tools/derive_unit_mps.py`
  cross-references those on-map sightings against `master_oob.json` by
  `(designation, division)` and writes `data/unit_mps.json`, which
  `data.load_master_oob()` now merges into every roster `Unit` as `.mps` /
  `.mps_confidence`. Breakdown across the 128 units:
  - **56 "unit"** — directly observed on-map for exactly that unit (a real
    recovered value, "confirmed", or "confirmed_majority(n/total)" where one
    of the 3 snapshots disagreed — almost always because the unit was
    off-map with an uninitialised/zeroed mps byte in that particular
    snapshot, outvoted by the others).
  - **67 "type"** — never directly observed (arrives in a scenario window
    none of the 3 snapshots cover, e.g. Gazala/Alamein-era units), so
    fallback to the majority mps value seen among *other* on-map units
    sharing this unit's `type` code. Confidence varies a lot by type: type 5
    is unanimous (10/10 sightings all mps=4), type 10 is 43/55 = 78% for its
    mode, but type 12 is only 26/41 = 63% — `type` genuinely doesn't cleanly
    determine mps (consistent with BUILD_SPEC §3.2's "not a clean branch"
    note about `type`), so these 67 values are a real but imperfect guess.
  - **5 "global"** — `type` itself never sighted on-map in any snapshot
    (types 3, 4, 6 combined); falls back to the overall majority mps (6)
    across every sighting, the least-informed tier.
  - `reinforce.admit_reinforcements` now sources mps from each unit's own
    `oob_unit.mps` by default; the old flat-value `mps=` parameter still
    exists as an explicit override (used by tests wanting a uniform value).
  - Still open: the 67+5 unconfirmed units remain a genuine gap the diff
    harness (§12) should close for real once golden traces exist — this
    change replaces "no data, flat guess for everyone" with "real data
    where it exists, an evidenced per-type guess elsewhere," not a full
    recovery.

## zoc_supply.py

- **`supply_band()` thresholds** (`NONE`/`V_LOW`/`LOW`/`Q_LOW`/`FAIR`/`GOOD`/
  `V_GOOD` cutoffs) — band *names* are confirmed
  (`data/ui_strings.json:supply_bands`), but the numeric thresholds mapping a
  supply level to a band are not recovered. Chosen to align with the supply
  curve's own breakpoints (BUILD_SPEC §5.4's curve steps by 5 down to level
  50, then flattens): ≥80 V GOOD, 70-79 GOOD, 60-69 FAIR, 50-59 Q LOW, 40-49
  LOW, 1-39 V LOW, 0 (no path) NONE.

## movement.py

- **`BASE_STEP_COST = 1.0`** — no per-terrain cost table exists in the
  original; BUILD_SPEC §10 explicitly suggests 1 MPS/cell as the defensible
  default, used verbatim.
- **`_step_toward()` axis-priority stepping** — the exact per-turn pathing
  algorithm for a Move/Assault/Travel order isn't specified beyond "advances
  toward dest one cell per step." Implemented as: move the axis with the
  larger remaining delta first, ties broken toward x. Diagonal movement is
  not modelled (ZOC/adjacency elsewhere in the spec is orthogonal-only).
- **Travel's road-adjacency check applies only at the *start* of a Travel
  order**, not re-checked every step en route. BUILD_SPEC §5.2 says Travel
  "requires the unit to be on or adjacent to a road" without saying whether
  that's continuously enforced; continuous enforcement would need real road
  connectivity data we don't have a model for yet.
- **Divide/Fortify/Go-To-Port drive no movement** (`_MOVING_ORDERS` excludes
  them) — their effects are explicitly unconfirmed per §10; modelling them as
  inert (Hold-equivalent, for movement purposes) is the simplest deterministic
  default. `ai.py` still *issues* Go-To-Port when appropriate; it just has no
  movement effect yet.

## combat.py

- **The entire assault-resolution model.** The literal recovered formula
  (`value = combat_readiness*100/MPS` vs a `defender_defence_value`
  threshold) depends on the "+3 byte"/`combat_readiness` numerator, which is
  unidentified (§10). Implemented BUILD_SPEC's own suggested fallback
  instead: compare `effective_power` (strength × efficiency / 100) head to
  head, higher side wins. The confirmed parts (−10 efficiency loss, −20 if
  caught-on-road, forced Hold on the loser, −3 adverse-position attrition,
  the `(100−eff)//16+1` recovery formula) are all applied exactly as
  specified.
- No terrain/posture defensive modifiers are applied — BUILD_SPEC §5.5 notes
  these are plausible (used in the reference arena) but not confirmed in the
  original resolver; omitted rather than guessed.
- The armour `type==10` combat-threshold override from the literal formula is
  *not* carried into this simplified effective-power model — BUILD_SPEC's own
  suggested fallback doesn't mention it, and effective_power comparison
  already has no natural place for a flat threshold override.

## reinforce.py

- **`DEFAULT_MPS = 6`** — see units.py entry above. Every admitted unit
  currently gets this single flat value regardless of type/designation. 6 was
  chosen as a commonly-observed figure among the few MPS values BUILD_SPEC
  §3.2 mentions having seen (0,4,6,7,8,10), not derived from any table.
- **`STAGING_POINTS[Side.AXIS] = (0, 11)`** — BUILD_SPEC §5.6 gives British's
  entry point explicitly (~98,11) but only says "Axis at the west edge" for
  Axis, no y. Mirrored British's row (11) as the simplest symmetric default.
  (In practice this cell is sea on the real map — `find_free_staging_cell`'s
  nudge search relocates it, currently landing at (0, 21); worth checking
  against the original's actual Axis entry point if it's ever recovered.)
- **`find_free_staging_cell()`'s ring-search order and `MAX_NUDGE_RADIUS`** —
  BUILD_SPEC only says "nudge if occupied"; the deterministic expanding-ring
  search order is an implementation choice, not a recovered algorithm.

## victory.py

This module is almost entirely inferred — BUILD_SPEC §10 explicitly flags
"type-code semantics are partly inferred" and gives no scoring formula, only
the shape (objective control + unit-count thresholds → 7-way ladder).

- **`controls_column()`** — "control" = whichever side's *nearest living
  unit* is closest to the objective's column. The objective's `type` code
  (2nd element of each `(column, type)` pair) is read from the data but
  currently ignored entirely by scoring — its effect (weight? category?) is
  unrecovered.
- **`score_side()`** — one point per controlled objective, +1 more if
  surviving unit count ≥ the scenario's threshold for that side. The
  threshold's actual semantics (is it a floor for "still combat effective,"
  or something else entirely?) are a guess: floor-for-bonus was chosen as the
  simplest interpretation.
- **`_MAJOR_MARGIN = 2`** (tactical/major/decisive cutoffs) — magnitude bands
  over the score margin (1=tactical, 2=major, 3+=decisive). No numeric
  cutoffs are recovered; picked to fit the small score ranges this model
  produces (typically -3..+3).
- **`STALEMATE_TURNS = 10`** — BUILD_SPEC §5.7 mentions a "front-line
  stalemate" end condition with no detection criteria given at all. 10
  consecutive turns (~3 campaign days) of an unchanged front-line midpoint
  was chosen as a simple, deterministic default. This is the most consequential
  inferred constant so far in practice — with no orders issued at all, every
  scenario currently ends via stalemate well before its actual end day (see
  `tests/test_integration.py`), which is *plausible* (no movement really is a
  stalemate) but means this constant directly shapes how long test games run.

## ai.py

Per BUILD_SPEC §10, only H=40 budget and the ±25-column offensive band are
confirmed; everything else about the AI's target selection is inferred.

- **`unit_weight()`** — "weight derived from MPS and type" (§6) with no
  formula given. Implemented as `mps * (2 if armour else 1)`.
- **`pick_target_region()`** — the *contested* band region (hostile
  strength > 0) with the greatest (own − enemy) weighted-strength
  advantage, i.e. "attack where you have the biggest relative edge." The
  original's actual target-weighting is explicitly unrecovered.
  The "contested" restriction was added after finding the naive
  own-minus-hostile maximization degenerates when a region has zero enemy
  presence: the score there reduces to just `own[r]`, trivially maximized
  wherever a side's own units are already concentrated (e.g. its staging
  cluster) — so the AI would "target" its own rear and never advance at
  all. With no contested region in the band (common early on, when the two
  sides' start positions are ~85 columns apart on a 100-wide map and
  neither is anywhere near the other), it now falls back to the region
  containing the current front-line midpoint instead, which shifts as
  either side's forward units move and so converges turn over turn.
- **`REGION_COUNT = 30`** — taken directly from BUILD_SPEC's "30-slot table"
  description; how those 30 slots map to the 100-wide board (evenly, by
  `x*30//width`) is not specified, just assumed uniform.
- **`_decide_unit()`'s per-unit target column, and its `dest_y` choice
  (`_nearest_enemy_y()`)** — every unit of a side shares the one regional
  `target` from `pick_target_region()`, so chasing its exact (x, y) made
  the whole side converge on a single cell: the first unit to arrive
  blocked everyone else's footprint from reaching the same spot, freezing
  the front turns before real contact. Each unit now chases the target's
  *column* but its own nearest-living-enemy *row* -- this both spreads the
  side across the front (distinct rows) and steers toward an actual
  opponent rather than a row fixed at reinforcement-admission time (which
  can land the two sides on rows that never line up in y at all).
- **Adjacent-enemy check runs before the offensive/defensive split, for
  every unit** — BUILD_SPEC §6 only mentions "Assault an adjacent enemy if
  present" under the defensive/local branch, but an *offensive* unit that
  has closed to contact needs the same check: without it, it keeps
  re-issuing Move toward a target beyond the enemy, which movement.py
  correctly halts on contact (its own contact-stop rule) but never turns
  into a fight -- observed as two adjacent units sitting frozen
  indefinitely. Checking adjacency first, before is_offensive(), fixed it.
- **Single-pass planning instead of the described 40-budget/4-pass sweep** —
  since this model's per-unit decision is a pure function of state that
  doesn't change mid-sweep, repeated passes would be no-ops here. The budget
  constants are kept as named values for fidelity/documentation even though
  only one effective pass runs. If a future revision makes passes
  state-dependent (e.g. units reacting to teammates' just-assigned orders),
  this would need revisiting.
- **`ray_scan_contact()`'s `max_range = AI_BAND_HALF_WIDTH` (25)** — BUILD_SPEC
  describes ray-casting "within the operational band" without giving an exact
  range; reused the band half-width as the scan range.
- **Divide/Fortify never issued** — the AI's decision tree only ever picks
  Move, Assault, or Go-To-Port (matching BUILD_SPEC §6's description exactly);
  Divide/Fortify aren't part of the described AI behaviour at all.

## render/

- **`palette.py` terrain paper (terminal.py, ANSI)** — only sea gets a
  distinct paper (blue); everything else is desert yellow. This is a
  **known simplification specific to the ANSI terminal renderer**, kept
  as-is (see `image.py` below for where the fuller model now lives) —
  ANSI's coarse 8-colour-plus-bright palette doesn't have room for a
  proper 8x8 tile pattern the way `image.py` does.
- **`image.py` — a real PNG renderer, corrected against a real gameplay
  screenshot.** First pass reused `terminal.py`'s "mostly desert yellow,
  only sea distinct" model, reasoning that `data/terrain_authentic.png`'s
  16-colour palette wasn't recovered game data (still true — see below)
  and that BUILD_SPEC §8's own characterisation of the paper table was the
  best available evidence. **That reasoning was incomplete.** The person
  supplied a real gameplay screenshot (256x192 pixels — the actual ZX
  Spectrum hardware resolution, not a mockup or emulator chrome) which
  shows escarpment terrain (types 2/3) rendering as a distinct 8x8 tile —
  red ink hash pattern on yellow paper — not flat desert. I extracted the
  exact tile bitmap pixel-for-pixel from the screenshot:
  `ESCARPMENT_TILE_BYTES = (0x60, 0x90, 0x09, 0x06)` repeating (MSB=leftmost
  pixel, matching graphics.json's documented tile format) — this is now a
  **confirmed** value, sourced from direct visual evidence rather than
  disassembly, and `image.py` draws it for terrain types 2/3. The same
  screenshot also **validated** two things already in BUILD_SPEC as
  confirmed: the viewport is exactly 176px wide = 22 cells @ 8px (§8's
  22x22 claim), and unit counters occupy a 16x16px block = 2x2 cells (§3.2's
  2x2 footprint claim). And it corrected the nation-ink RGB values sampled
  from the actual rendering: German is pure black `(0,0,0)` (the ANSI
  renderer's grey substitution for dark-terminal legibility was solving a
  problem that doesn't exist here, since the PNG's background is desert
  yellow, not black — reverted to the confirmed value), British is a
  non-bright blue `(0,0,162)` (previously guessed as ZX bright blue),
  Italian is `(231,0,182)` (close to the previous magenta guess, tightened
  to the sampled value).
  - **Update: closed via tape extraction.** The person supplied the
    original tape image; `reference/extraction_tools/extract_render_tables.py`
    reconstructs memory from the TZX and recovers the full render model.
    Key discovery: **the map cell byte is a full-byte tile index**, not
    just "type in low nibble" — rendering looks up a 256-entry attribute
    table at 0xD80E and 8-byte tile bitmaps at 0xF6D8 **by the whole
    byte**; the low nibble is only the game-logic type mask. Notable
    decoded facts: sea (tile 0x0E) is a fully-inked tile — its blue is
    INK blue over yellow PAPER, not blue paper; open desert (0x00) is a
    blank tile (pure paper); the escarpment art (e.g. 0x6E) is yellow
    paper / red ink, matching the screenshot-extracted bitmap exactly
    (which is also how the tile base address was located: memory search
    for that bitmap, then confirmed by the blank/solid tiles and a 94.8%
    sea-mask agreement between a full-map reconstruction and
    pubmap_units.png). Committed as `data/render_model.json` (attribute
    table + full-byte tile-index grid + per-tile ink-coverage fractions —
    factual data). **Tile bitmaps are original pixel art and are NOT
    committed** (`data/tiles_original.json`, gitignored): regenerate
    locally with the extraction script; `render/image.py` renders
    pixel-exact terrain when that file is present and a per-cell
    paper/ink coverage blend when it isn't. The flat legacy model remains
    as the fallback for synthetic boards and for clones without
    `render_model.json`.
  - Also noted: 32 of 3200 cells differ in low nibble between the
    tape-loaded map at 0xCB39 and `data/terrain_authentic.json` — likely
    a snapshot-state difference in the original extraction; worth a
    diff-harness look eventually, harmless for now.
  - **`data/terrain_authentic.png`'s 16-colour debug legend is still not
    recovered game data** — this correction doesn't change that finding,
    it just means the *real* palette turned out to have more structure
    than "only sea is different" (an incomplete but not fabricated
    reading of BUILD_SPEC §8's own hedge — "features vary").
  - Road-cell line overlay and grid lines are unaffected — still a
    legibility choice over real position data, not a colour claim.
- Tile-graphic assignment is entirely unrecovered** (§10) — units and
  terrain render as ASCII/branch-letter glyphs in the terminal renderer, or
  flat coloured blocks in `image.py`, not the original's 8x8 tile art.
  BUILD_SPEC §1/§8 explicitly accept this tier; pixel-exact tiles are
  optional/later (`reference/prospects.md` #12/#13).
- **`overview.py` (new) — a strategic overview map, styled after the
  person-supplied `pubmap_units.png` reference.** Explicitly *not* a
  fidelity claim (see its own module docstring, and `image.py`'s entry
  above for why): it reuses the exact 16-colour terrain-code legend
  sampled from `data/terrain_authentic.png` (the extraction tooling's
  debug legibility palette) so it's visually comparable to that reference
  and to `pubmap_units.png`, plus a small dot per living unit coloured by
  nationality. Real-world town labels (`APPROXIMATE_TOWN_COLUMNS`) are
  **off by default** and, when enabled, are positioned from real-world
  coastal road distances between El Agheila and Alexandria as a rough
  orientation aid — not decoded game data (terrain point-feature naming is
  still an open item, `reference/prospects.md` #11). Wired into
  `main.py --snapshot-dir` alongside `image.py`'s tactical render — every
  turn now writes both a `_tactical.png` and an `_overview.png`.
- **German ink rendered as bright-black/grey, not pure black** — pure ANSI
  black is usually invisible against a typical dark terminal background.
  Legibility substitution only; the confirmed Spectrum ink codes
  (British=1, German=0, Italian=3) are kept as `SPECTRUM_INK` for provenance.
- **`CALENDAR_DAYS_PER_MONTH = 30`** (`render/terminal.py`, `calendar_month()`)
  — the turn/day↔calendar-month mapping isn't recovered. 30 days/month
  reuses the same divisor `reference/prospects.md` #6 notes for the
  turn-phased schedule tables (indexed by `turn÷30`), as the simplest
  deterministic guess. Display-only, no gameplay effect.

## main.py

- **Malta menu is shown but has no gameplay effect at all** — consistent
  with BUILD_SPEC.md §10 ("no invocation found in the 48K image") and
  CLEANROOM_BRIEF.md's boundaries (128K-only features out of scope unless
  data is provided). The prompt exists purely for title-screen authenticity;
  `MALTA_NOTE` says so explicitly to the player.
- **No literal reproduction of the original's title/options screen layout
  or wording beyond the scenario list and Malta options** — BUILD_SPEC.md §8
  explicitly treats exact UI panel geometry as optional polish, not an
  acceptance criterion. `run_interactive()`'s menu flow (scenario → British
  mode → Axis mode → Malta) is original orchestration code, not recovered
  from the source.

## Schedule tables & Malta (tape extraction, follow-up pass)

- **The §10 "schedule tables" are now structurally recovered** — see
  `data/schedules.json` and `reference/extraction_tools/extract_schedules.py`.
  Four tables, all indexed by month (`turn ÷ 30`, turn counter at 0xCB0F),
  22 monthly entries per side, values ×10 on read, read by the 0x96E0
  routine family (whose index arithmetic, side offsets and scaling were
  pinned by targeted disassembly of the readers — analysis-side work in
  the engine-map tradition; no machine code is transcribed into the
  engine):
  - `monthly_unit_schedule` (0xDEFC): 22 × 6-byte groups; the reader
    consumes `[side][q0|q1]` per group (bytes 4–5 unread by this family).
  - `monthly_side_rate` (0xDF84): 22 per side. Side 1 ramps 5→20 across
    the war; side 2 flat 10 peaking 15 in months 13–14 (the Gazala
    window) — historically shaped like British buildup vs Axis peak,
    which is the basis for the side-1=British hypothesis. Semantics
    (supply rate vs replacement points) are a hypothesis for the diff
    harness, marked as such in the data file.
  - `malta_modifier` (0xDFB6): 22 × 2 halves, applied by 0x9704 to the
    **Axis side only**, gated by a selector at 0xCB25 (1 → half 1,
    2 → half 2, 3 → bypass). **This corrects engine-map.md**: the Malta
    option's invocation does exist in the 48K image — it modulates
    Axis-side scheduled values monthly. The exact arithmetic 0x82DF
    applies is still open.
  - Extraction includes a supply-curve (0xDFE8) byte-match alignment
    check so a wrong/shifted tape image fails loudly.
- **The engine does not consume these tables yet.** Wiring them in
  (probably in `reinforce.py`/`zoc_supply.py`) is follow-up work — do it
  alongside diff-harness validation so the semantic hypotheses get
  settled rather than baked in as guesses.

## Travel & combat 1:1 audit, deployment recovery, terrain-typing correction (tape disassembly)

Prompted by the person noticing units arriving unstacked (the original
deploys formations together) and asking whether Travel and Combat are 1:1
with the source. The audit read the original's mover, resolver and setup
routines directly. Findings, in decreasing order of impact:

- **Terrain typing was wrong.** A cell's terrain type is
  `type_table[cell_byte] & 15` via a 256-entry table at 0xD90E — NOT the
  cell byte's own low nibble, which `terrain_authentic.json` assumed and
  which misclassifies 2011/3200 cells. Code-verified type space is 0–8:
  0 desert (incl. all decorative coast/border/label art — passable),
  1 sea (impassable), 4 escarpment, 5 road (the mover's road test is
  literally `type == 5`), 6 marsh; 2/3/7/8 are small unknowns (type 2
  includes the British staging cell (98,11) and is passable).
  `data/terrain_logic.json` now supersedes the old grid;
  `desert_rats/board.py` loads it (SEA=1, ROAD=5, ESCARPMENT=4, MARSH=6).
  A road-DIRECTION table at 0xDA0E gates the road cost discount by step
  direction — located, arithmetic not yet applied in the clone (open).

- **Deployment & stacking.** Initial deployment is scripted data, not
  edge staging: scenario records at 0xDE53 (25 bytes, 1-based index)
  carry an offset (bytes 4–5) into a deployment region at 0xEABF; each
  list is [count] then (slot, x, y) triplets, slot 1-based into the
  roster. The placement routine (0x93AF) writes those coordinates
  directly. Divisions deploy clustered — frequently several units on the
  SAME cell (e.g. Ariete's four units on one cell in Enter Rommel) — so
  co-location at setup is confirmed original behaviour; our movement
  rules keep no-overlap from the first move onward. Extracted to
  `data/deployments.json` (day-window cross-check against scenarios.json
  on extraction); `reinforce.scripted_deployment()` + `game.new_game()`
  use it, with edge staging retained for post-start reinforcements and
  for synthetic scenarios. Also observed at the placement/arrival site:
  efficiency is adjusted by a day-based term and the arrival field is
  zeroed on entry — NOT yet modelled (open).

- **Travel is 1:1.** The mode multiplier routine applies exactly
  Assault ×1.5 (HL += HL/2) and Travel ×0.5 (HL /= 2) to the step cost;
  the road test masks to type 5; the footprint scan iterates the 2×2
  block and collapses to 1×1 when the travel flag (state-byte bit 4) is
  set. `movement.py` needed no changes.

- **Combat was NOT 1:1 — model replaced.** The engine-map's mysterious
  "+3 byte" is a per-unit combat-PRESSURE accumulator: zeroed at
  placement, 8-bit saturating, fed by a scan loop adding enemy-derived
  amounts. Resolution per unit: value = pressure × 100 / strength,
  tested against the unit's MORALE (or the fixed 20 for combat-class-10
  units); at/above threshold → −10 efficiency (call site confirmed),
  order forced to HOLD, one-cell retreat attempt (a coded direction,
  then its opposite); if the retreat fails, pressure escalates ×1.5
  (cap 255); pressure ≥ strength routes to a separate break path whose
  semantics are still open. `combat.py` rewritten accordingly
  (`apply_combat_pressure`, `pressure_threshold`, `resolve_pressure`);
  the old symmetric power-comparison `resolve_assault` is gone.
  Inferred constants exposed for the diff harness:
  `PRESSURE_INFLOW_DIVISOR` (inflow = adjacent enemy effective power //
  10), `PRESSURE_DECAY_OUT_OF_CONTACT` (reset when no enemy adjacent),
  and the retreat direction order. NOTE: the −3 attrition call site is
  confirmed, but NO distinct −20 caught-on-road call site exists — the
  ×2 doubling is retained provisionally and flagged for the harness.

- **Supply index bias.** The curve is indexed by `(distance + 2) >> 2`,
  not `distance >> 2` — fixed in `zoc_supply.py` (shifts every band
  boundary by two cells).

Test suite updated throughout (board coordinates re-verified against the
code-verified grid; combat tests rewritten for the pressure model;
overview legend rekeyed to the 0–8 type space). All passing.

## Content-pack seam (generic engine, swappable theatres/skins)

Motivated by two goals: a public build that carries no original-game
expression, and support for other strategy theatres on the same engine.

- **Architecture** (`desert_rats/packs.py`): a pack is a directory under
  `content_packs/` with a `pack.json` manifest (`name`, `title`,
  optional `inherits`, og-only `legacy_data`). File resolution walks the
  pack, its ancestors, then — if the chain allows — the historical
  top-level `data/` directory. All loaders (`board.load_board`,
  `data.load_master_oob/scenarios/deployments`, `render.strings`,
  `render.image`'s render model) resolve through the ACTIVE pack;
  explicit path arguments still override for tests/tools. The active
  pack defaults to `og` (exact pre-seam behaviour) and is switched with
  `--pack` on the CLI or `packs.set_active_pack()`.
- **`og` pack**: transitional thin manifest over the existing `data/`
  directory. Long-term it is generated entirely locally from the
  person's own tape by the extraction tools (as
  `data/tiles_original.json` already is), and the public repo ships only
  the engine plus clean packs.
- **`default` pack**: the historical North Africa theatre with an
  ORIGINAL map — `tools/build_default_map.py` rasterizes a hand-authored
  polyline of the real coastline (public-knowledge geography: El Agheila
  → Benghazi → the Cyrenaica bulge → Tobruk → Sollum → El Alamein →
  Alexandria), the coastal road and the Agedabia–Mechili inland track,
  the Jebel Akhdar and Sollum escarpments, and the Qattara Depression,
  into the engine's 100x32 grid. A small affine frame calibration plus a
  feathered coastline-constraint pass keep every inherited deployment /
  staging coordinate on passable land (asserted at build time and in
  tests). Other layers currently inherit from og; migrating them to
  clean equivalents (own strings, own names, sourced OOB) is staged
  follow-up work per the layering plan.
- **Render-model scoping bug caught by tests**: a pack that overrides
  terrain but inherits its parent's render model must not have the
  parent's terrain art painted over its own map — the model is only
  used when it resolves at the same pack level as the terrain.
- Verified: full deterministic headless game on the default pack;
  pack switching changes the board; OG behaviour byte-identical
  (suite unchanged before/after the seam).

## Atlas feature layer for the default pack

The first default-pack map was game-logic terrain only — no names, forts
or region features, and the road stroke had gaps (a builder bug: sampled
every second column, skipped sea cells). Both addressed:

- `tools/build_default_map.py` now draws the coastal road cell-by-cell
  along the eased coast profile with vertical steps filled, and the
  inland track contiguously; the build asserts the road network forms at
  most 3 (currently 1) 8-connected components.
- The builder also emits `content_packs/default/features.json`: an
  original compilation of well-known places of the theatre (towns,
  ports, forts, Halfaya Pass), region labels (LIBYA, EGYPT, CYRENAICA,
  QATTARA DEPRESSION, JEBEL AKHDAR) and the Libyan-Egyptian frontier
  wire, positioned by real lon/lat through the map's projection.
- `render/image.py` gained an atlas layer for packs that provide
  features.json (and no pixel render model): coastline outlining,
  connected road strokes, marsh stipple, kind-specific markers
  (fort=square, port=circle, town=dot, pass=chevron), haloed name
  labels, letter-spaced region labels, dashed frontier. Feature layers
  follow the same pack-level scoping rule as render models (only valid
  alongside the terrain they annotate); the OG pack is untouched (its
  names are baked into its tile art).

## Period-atlas restyle of the default map

Feedback: the first atlas pass was still visually unclear (ZX palette,
per-cell grid lines, tiny bitmap font). Restyled the atlas mode around
standard period-cartography conventions — the generic visual language of
mid-century theatre maps, not any particular published map:

- Palette: cream paper, pale blue sea, thin dark coastline, brown road
  strokes, tan relief fill with hachure ticks for escarpments, grey
  stipple for the Depression. No cell grid in atlas mode.
- Typography: DejaVu Serif for settlement labels, Serif Italic
  (letter-spaced caps) for region and sea names, with paper-coloured
  halos; falls back to the bitmap font if truetype is unavailable.
- Furniture: north arrow (top right) and a 100 km scale bar (bottom
  right) driven by `km_per_cell`, which the builder now computes from
  the projection and stores in features.json.
- Place compilation extended with more well-known locations of the
  theatre (Bir Hacheim, Sidi Rezegh, Bir el Gubi, Gabr Saleh, Gambut,
  Fort Capuzzo, Sidi Omar, Tmimi, Beda Fomm, Ben Gania), region labels
  (WESTERN DESERT, LIBYAN DESERT) and the MEDITERRANEAN SEA label — all
  positioned by own approximate lon/lat (public-knowledge geography).
  Off-map places (Jalo Oasis, Cairo, Suez) deliberately omitted.
- OG rendering is untouched throughout (atlas mode only activates for
  packs providing features.json without a pixel render model).

## Map-image skins: the cartographic image IS the map

Architecture change per the person's direction: the 100x32 grid is the
invisible engine underlay; a pack's visual layer can be a full
cartographic IMAGE, with counters transposed onto it through a
calibration mapping grid coordinates to image pixels.

- A pack provides `map.png` + `map_calibration.json`
  (`cell_to_px_x/y = [a, b]`, i.e. px = a*grid + b, axis-aligned
  affine). `tools/calibrate_map_image.py` fits the calibration by least
  squares from anchor points ("Tobruk is at pixel (X,Y)"), reporting
  residuals so a bad anchor is obvious; two anchors minimum, more for a
  fit. Same pack-level scoping rule as the render model and features.
- `render/image.py`: when a calibrated map image resolves, the renderer
  crops the source region for the cell viewport and scales it so each
  cell lands exactly on the output cell lattice — the counter-drawing
  code needed NO changes. Precedence: pixel render model (og) →
  map image → live atlas layer → legacy flat. `use_map_image=False`
  bypasses (used by the bake tool and the atlas-layer tests).
- The default pack's `map.png` (3200x1024, committed) is baked by
  `tools/build_default_map_image.py` from the pack's own atlas layer —
  original work end to end. Rebuild order: build_default_map.py →
  build_default_map_image.py.
- USER-SUPPLIED ARCHIVE SCANS: fully supported — drop the scan at
  content_packs/<pack>/map.png, pick a few identifiable places, run the
  calibration tool. But period map scans are frequently still in
  copyright: treat such an image exactly like data/tiles_original.json —
  keep it local, do NOT commit it to the public repo. The committed
  default map must remain our own work.
- Verified: viewport crops of the image skin are pixel-consistent with
  the full render (test), counters transpose correctly in play.

## Vector-drawn map image (replacing the grid-rasterized bake)

Feedback: the baked map image still looked nothing like professional
cartography. Root cause: it was rendered FROM the 100x32 cell grid, so
it carried a staircase coastline and chunky roads at any resolution.
`tools/build_default_map_image.py` rewritten to draw the image directly
from the VECTOR source shared with the terrain builder -- the eased
coast profile (upsampled + smoothed), the road and relief control
polylines, and the place compilation -- at 32px/cell (3200x1024):

- smooth anti-aliased coastline with a near-shore tint band over pale sea;
- relief as blurred tan strokes with perpendicular hachure ticks
  (Jebel Akhdar, Sollum, Gazala ridges);
- the Qattara Depression as a soft blob with stipple;
- the coastal road as a smooth offset of the coast path, the inland
  track dashed; dashed frontier wire;
- serif settlement labels with paper halos, italic letter-spaced region
  names, sea name, north arrow, 100 km scale bar.

Alignment with the playable grid is preserved because the image and the
grid derive from the same projection and the same eased profile
(sub-cell visual smoothness only). The game view downsamples the bake
with LANCZOS: ~6,800 distinct colours in a 1000px view vs ~40 for the
old grid render. The image remains ORIGINAL work drawn with generic
period-atlas conventions; it reproduces no published map's artwork
(user-supplied scans remain the local-only route for that look).

## Refocus: vector map parked; authentic OG screen recovered

Per the person's direction the vector atlas map is ABANDONED (hand-
authored polylines are not survey-accurate geography) and effort
refocuses on a 1:1 original game skin. The pack seam, the image-skin
architecture (map.png + calibration) and the calibration tool all REMAIN
-- they are the delivery mechanism for a future geographically-real map
skin; only the committed vector-drawn map.png/map_calibration.json were
removed from the default pack. The default pack falls back to its live
atlas layer.

The 1:1 OG experience gained its missing piece -- the AUTHENTIC SCREEN:

- The game's own text FONT was located at 0xFD00 (96 ASCII glyphs, 8
  bytes each; NOT the ZX ROM font -- the ROM 'A' bitmap is absent from
  memory, and the base was pinned by reverse-searching screenshot glyph
  bitmaps). Extracted by extract_render_tables.py to
  data/font_original.json -- GITIGNORED original pixel art, same policy
  as the tiles.
- The original 256x192 screen layout was recovered by OCR'ing the real
  gameplay screenshot WITH that font: 22x22-cell map viewport top-left;
  an 80px black side panel carrying the date in yellow ("MAY 27th" /
  "1942") and the order menu in white (R REPORT / M MOVE / A ASSAULT /
  H HOLD / F FORTIFY / ENTER TO END) with the SELECTED order in inverse
  video on red paper; and a two-row red bottom band showing the selected
  unit's designation in white ("201st Guards Brigade" in the reference
  scene).
- render/screen.py composes that screen 1:1 from game state (pixel-exact
  viewport via the recovered tiles, panel text in the recovered font,
  selection inverse video, red status band), with integer scaling.
  It requires the local-only art files and says so clearly when absent.
- Fidelity fix: the debug cell grid is now confined to the legacy flat
  render path -- the original screen has no grid, so the authentic tile
  path (and atlas/image modes) no longer draw it.
- Open for full screen fidelity: the clock->calendar-date mapping (the
  original shows "MAY 27th 1942" at the Gazala start; the formula is not
  yet recovered -- render_screen takes the date as input meanwhile), and
  the right-hand end of the status band (cursor/extra info glyphs).

## Diff harness v1: the original's routines as executable oracles

The planned "diff harness against an emulator trace" landed in a stronger
form than trace-diffing: `reference/diff_harness/harness.py` loads the
64K memory reconstructed from the person's own tape into a Z80 CPU
emulator (pip `z80`; no ZX ROM needed -- the ROM area is RET-filled and
the target routines are self-contained), crafts unit records, CALLS the
original routines directly, and diffs the results against the Python
engine across swept inputs. Probes live in the harness; raw outputs in
`reference/diff_harness/results/oracle_results.json`.

Verified 1:1 (previously implemented correctly):
- recovery: eff += (100-eff)>>4 + 1, cap 100 (101/101 sweep match);
- the odds form value = pressure*100/strength vs threshold; morale as
  the default threshold; -10 on crack; forced HOLD; escalation x1.5
  exactly (50->75, 60->90), cap 255.

Corrected by the oracle (engine updated):
- SUPPLY BANDS were one off everywhere, in both our old and first-audit
  readings: a = min(distance+2, 127) >> 2; a == 0 (distance <= 1) is a
  FULL-supply band (100) that is not in the 31-value table; otherwise
  curve[a-1]. Also pinned: the routine SCALES its input by the band
  percentage (supply = base * band / 100), and with the in-supply flag
  clear it passes the input through unchanged with A=0.
- The -20 CAUGHT-ON-ROAD DOUBLING IS FALSIFIED: travelling/caught units
  take the flat -10 like everyone else (swept across flag/order
  combinations). Constant removed.
- RETREAT is a nationality-coded diagonal toward the unit's own map
  edge -- British (+1,+1), Axis (-1,+1) -- NOT away-from-enemy; when
  terrain blocks it the mirrored diagonal is taken; UNIT OCCUPANCY DOES
  NOT BLOCK IT (five stacked blockers ignored; only terrain matters).
  Northward fallbacks remain inferred.
- BREAK PATH DECODED: pressure >= strength destroys the unit outright
  (strength := 0, pressure := 0) -- both at the pre-test gate and after
  a trapped escalation reaches strength. Unit.is_destroyed now also
  covers strength <= 0.
- THE 'x' FIELD IN master_oob IS THE COMBAT CLASS (range 1-13), not a
  position: class 10 (six infantry/AT formations -- NOT armour, the old
  "armour override" story is wrong) uses the fixed threshold 20 and so
  cracks sooner; class 13 (unused by this roster) is exempt entirely,
  via bit 3 of the derived byte the class-derive routine (0x643F)
  produces. Exposed as data.Unit.combat_class / Unit.combat_class.
- Cracking also clears the in-supply flag (bit 0 of the state byte) --
  recorded; not separately modelled since our supply recomputes per turn.

Confirmed live but not yet pinned to formulas (next harness targets):
- 0x96DD is the whole monthly REPLACEMENT PHASE: with turn/side/Malta
  set it read exactly the right schedule cells (monthly_side_rate and
  malta_modifier for the crafted month/side/half) then scanned all 128
  records at stride 30 -- but a lone desert unit received no writes, so
  application is gated (port/position conditions suspected). It ends in
  a print-and-wait loop, so full-phase probing needs qualification
  conditions or a breakpoint before the report.
- The pressure INFLOW loop (scaling of enemy-derived amounts) and the
  clock->calendar date mapping remain open.

## Pressure inflow: decoded shape (harness follow-up)

Partial decode of the pressure-inflow chain (fed into the resolver we
oracle-verified above), captured for the next harness round:

- The neighbour ring-walk at 0x84CC-0x84E0 visits adjacent cells (a
  direction bitmask in A, shifted per step); for each occupied cell it
  resolves the occupant record and calls the contribution routine.
- Per-adjacent-enemy contribution (0x82FD), oracle-verified: returns
  A := 1, doubled if the subject's role byte (IX+0x16) bit 0 is set, and
  doubled AGAIN if a class/terrain-derived value (HL, seeded 100 then
  scaled by the class table at 0x8286 and the terrain adjuster at
  0x82B2) is below a threshold held at 0xCAFF. Net: 1, 2, or 4 per
  adjacent enemy -- a small COUNT-like amount.
- Class multiplier table (0x8286), % of input:
  {1:60,2:60,3:30,4:30,5:50,6:50,7:70,8:50,9:30,10:20,11:50,12:50,13:0}.
- Terrain adjuster (0x82B2) is the identity for logic types 0-8 at
  HL=100 (may differ for raw cell bytes -- untested).

IMPLICATION: the engine's inferred PRESSURE_INFLOW_DIVISOR=10
(inflow = adjacent effective power // 10) is wrong in kind -- the
original accumulates a small 1/2/4 count per adjacent enemy, not a
power fraction. NOT yet changed in combat.py: doing so correctly needs
the 0xCAFF threshold source pinned (it is cold-zero at rest, so it is
set per-resolution from the subject -- suspected strength or strength
x1.5 under assault). Flagged here so the model is corrected from a
known shape rather than re-guessed.

## The AI's decision layer: recovered and implemented

The last major 1:1 gap. Combined disassembly (0xA9EA builder,
0xAAE7-0xAB44 scoring, 0xA510/0xA537 chooser) with oracle sweeps; full
detail in reference/engine-map.md §15. Highlights: the 0xD6F1 table is
STATIC data (30 strategic regions with anchors at the theatre's
well-known locations and importance 0-7); unit weight = strength >> 5
(halved when MPS < 5); scoring tiers 96/60/50 + importance with per-side
reach windows; side-directional objective-ladder walk. The original has
a store-instead-of-accumulate bug on the friendly weight -- reproduced
deliberately for 1:1. Strategic core in desert_rats/ai_og.py (unit
tested against the oracle values), wired into ai.plan_turn; regions
committed as data/ai_regions.json. Remaining inferred: ladder-walk
tie-breaking beyond side direction, and the 0xCB27/0xCB28 frontier
maintenance (currently permissive defaults).

## Pressure inflow: RECOVERED (0xCAFF pinned; projection model implemented)

The follow-up above is closed. Key steps: the 0xCAFF writer is 0x816E
(inside the 0x8130 averager): the threshold is the AVERAGE class/terrain
value of the pressed cell's occupants -- and since both the per-occupant
value and the average use the SUBJECT's class and the SAME cell terrain,
the comparison is constant-vs-own-average and never doubles; the
effective split weight is 1 << role_bit0 only. The full chain
(prologue 0x834F + tail, helpers 0x8286/0x82B2/0x82C9/0x82DF/0x82F0/
0x841B/0x8424/0x6454/0x6C8C) was disassembled, and the composed formula
END-TO-END ORACLE-VERIFIED (signature: A=count, B=direction, D/E=y/x,
HL=slot list; 0xCB02 = pressed-cell divisor):

  outgoing = strength x1.5(assault)
             x tenths[terr(subject)][class]/10   (0xDD94: 11-byte blocks
               PER CLASS-COLUMN indexed by terrain row -- 0x6C8C is
               11*col + row; class->column at 0xDB8F)
             x fortify_tenths/10                  (record +0x1E, default 10)
             x efficiency/100  / pressed_cells    (0xCB02)
  per defender:
             x class_pct[subject_class]/100       (0x8286)
             x tenths[class][row 10]/10 x band%/100  ONLY when supplied
               (out-of-supply defenders take ~x2.2 -- verified 15 -> 33)
             x1.5 if the defender assaults
             x1.0 net if travelling (the x0.5 mode and x2 caught bits
               CANCEL: "caught on road" = loss of protection, not double)
             x2 if immobile (mps == 0)
             x (1 << role_bit0) / total_weights, capped 255;
             also accumulated at +0x17 with the max tracked at 0xCB04.

Engine: apply_combat_pressure rewritten to this projection model;
PRESSURE_INFLOW_DIVISOR removed; tables committed as
data/combat_tables.json (extract_combat_tables.py). Fortification
surfaces as unit.fortify_tenths (default 10) -- wiring the FORTIFY order
to it is noted as follow-up. Out-of-contact decay remains the last
inferred combat behaviour.

## Clock -> calendar: recovered

The side-panel date drawer is at 0x97E3 (found among the
LD HL,(0xCB0F) clock readers by calling each under emulation and
OCR'ing the rendered screen with the game's own font). The clock was
then swept 1..730 and every rendered date read back: ZERO mismatches
against the real Gregorian calendar across days 1..640 (the campaign's
span). The rule is simply

    clock day N = April 1, 1941 + (N - 1)

with the game's month forms (JAN FEB MAR APR MAY JUNE JULY AUG SEPT OCT
NOV DEC -- table at 0xE793, 4-byte entries) and standard English
ordinals. Anchor: clock 422 = "MAY 27th 1942" (Gazala start), matching
the reference screenshot glyph-for-glyph. Implemented in
desert_rats/game_calendar.py; render_screen now takes clock= and
formats the panel date itself. The authentic screen no longer needs any
hand-fed inputs.

## Replacement economy: recovered (the last systemic gap)

The earlier probe failed because 0x96DD is only the RATE READER; the
real system, disassembled and end-to-end oracle-verified:

- MONTHLY tick (0x978E, clock % 30 == 0): each NATIONALITY banks two
  pools from the 0xDEFC monthly table x10 x Malta (Axis, statuses 1/2):
  pool A (general) at 0xCB18/1A/1C, pool B (armour) at 0xCB1E/20/22.
  This corrects the extraction's old layout note -- all three
  nationality pairs are read ('unread' was wrong).
- WEEKLY phase (0x953F, clock % 7 == 0), per nationality:
  - REPLACEMENTS (0x9567): only units whose ORDER IS HOLD qualify
    (the gate that defeated the first probe). Gain =
    min((cap - strength + 1)//2, rate, pool). Premium classes {1,2,12}
    (0x96C6): cap 170, rate 30, from POOL B (oracle: 60 -> 90, pool
    200 -> 170). Everyone else: cap from 0x9520 (class 9 -> 100; else
    role 0/1/2+ -> 40/100/200), rate 10, POOL A (oracle: 60 -> 70,
    pool 100 -> 90).
  - REBUILDS (0x95E6): destroyed-on-map units (strength 0, cooldown
    +0x13 clear, not class 9, not role-bit1, +0x1D prerequisite clear)
    are bought back from pool A at cap cost (half price accepted);
    oracle: pay 100 now, strength parked in-transit (+3), efficiency
    set to 50, cooldown ~8 days -- the unit returns when it expires.
    This also closes the arrival-efficiency gap (rebuilt arrivals: 50).
- Engine: reinforce.replacement_phase wired into the daily turn tick;
  GameState gains malta_status and per-nationality pools; caps/rates as
  constants; six oracle-anchored tests.

## Closing sweep: the last inferred behaviours resolved

- FORTIFY FIELD: the +0x1E outgoing-pressure multiplier's ONLY writer is
  the record unpacker (0x9C94), copying OOB byte 9 -- the 'type' field.
  It is a static per-unit stat (distribution centred on 10 = x1.0, up to
  14 = x1.4); the FORTIFY order never touches it. Engine:
  Unit.fortify_tenths is set from oob.type at from_oob.
- OUT-OF-CONTACT DECAY: FALSIFIED. Audit of every pressure write found
  no ambient reset; pressure persists and is cleared only by the
  retreat-step executor (0x89A9 -- the engine now zeroes pressure on a
  successful crack-retreat), the break path, and rebuild arrival.
- REBUILD ARRIVAL CONFIRMED at 0x93D7: strength := the in-transit +3
  value, pressure cleared, unit set on-map and in-supply -- exactly the
  transfer the economy implementation inferred. Scheduled (non-rebuild)
  arrivals init at 0x80A5: efficiency 100, cap strength in transit.
  A timeout loop at 0x945E clears units whose counter passes +0x13
  (recorded; edge case, not modelled).
- ROAD-DIRECTION ARITHMETIC DECODED: 0xDA0E is the third per-cell byte
  table (sibling of attrs/types): a direction bitmask (low nibble =
  pathing connectivity used by the mover at 0x6BA7/0x6BC3; high nibble
  gates the road factor). 0x8592 -- whose ONLY caller is the pressure
  prologue -- applies tenths[class][row 9]/10 when the unit sits on a
  road connected in the direction it presses: a PRESSURE mechanic, not
  movement cost. Extracted to data/road_masks.json; applied in
  apply_combat_pressure with the dominant-axis direction code.
- AI LADDER TIE-BREAKING: remains the project's ONE inferred detail
  (side-directional walk implemented; the exact 0xA46D/0xA4D3 evaluator
  internals undecoded). Documented as such.

## AI ladder tie-breaking: RECOVERED (no inferred behaviours remain)

The project's last inferred detail is closed. The ladder evaluators
0xA46D (British, ascending IX) and 0xA4D3 (Axis, descending IX)
flood-walk the objective ladder, and the "tie-break" is the column-band
gate 0x9E7F: an objective qualifies iff its column x satisfies
frontier <= x < frontier + 50 (frontier = 0xCB2F), i.e. a 50-cell window
ahead of the front. Gate boundaries oracle-verified exactly (inclusive
low, exclusive high, via the routine's INC C). choose_target now walks
the ladder in the side's direction and returns the first in-band,
enemy-held region's anchor, with the earlier scoring model retained only
as an early-game fallback (no frontier contact). The ENTIRE engine is
now free of inferred mechanics -- every behaviour is disassembly-read or
oracle-verified against the original.
