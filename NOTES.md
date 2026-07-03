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
  - **Still not fully closed:** the *other* 14 terrain codes' paper/ink are
    still unconfirmed beyond desert/sea/escarpment — this screenshot only
    covered one scene near Gazala. `reference/prospects.md` #12 (tile
    tables) should be updated to reflect escarpment as resolved rather
    than fully open; the remaining codes are still open.
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
