# Desert Rats (1985, CCS) — Clean-Room Build Specification

**Target:** a faithful, playable reimplementation in **Python 3** of the ZX Spectrum
operational wargame *Desert Rats* (CCS, 1985; original programmer R.T. Smith), built
from this specification and the accompanying extracted data — **not** from the original
machine code or ROM.

This document is implementation-oriented and self-contained. It expresses the recovered
rules as data models and formulas. Provenance (Z80 routine addresses) lives in the
companion `reference/engine-map.md`; you do **not** need it to build, only to audit.

---

## 0. Clean-room note & provenance

All game *logic* below was recovered by disassembly and is described here as
specification, in our own words. All *data* files (order of battle, map, scenarios,
strings, graphics tables) are factual data extracted from the original image. Build the
clone from **this spec + these data files only**. Do not embed the original binary, ROM,
or verbatim machine code. Ship the original game's data only if you have the right to; a
distributable build should be able to run from re-created or user-supplied data of the
same shape.

---

## 1. Product overview

Turn-based operational wargame of the North Africa campaign, 1941–42. A scrolling grid
map from El Agheila to Alexandria; two sides — **British** vs **Axis** (Axis = German +
Italian formations) — manoeuvre divisions/brigades/regiments, trace supply to their
board edge, and fight for objective towns and territory over a historical timeline. One
or two human players; the empty seat is played by the AI. Six scenarios, each a window
into one continuous 624-"day" campaign.

**Deliverable:** a playable Python program reproducing the rules, data, board, victory
conditions and AI below, with a rendering that respects the original's visual identity
(§8). A text/terminal or simple 2D GUI is acceptable; fidelity is about *rules and feel*,
not pixel-exact emulation (that is a later, optional tier).

---

## 2. Determinism — the single most important property

**The engine contains no randomness.** No RNG, no dice, no hidden rolls anywhere in the
game logic (verified: no `R`-register reads, no FRAMES seed, no RANDOMIZE in any logic
path). Every outcome is a pure function of unit state and position.

Consequences for the build:
- Combat and AI must be **deterministic**. Do not add randomness "to feel like a
  wargame".
- This makes the clone **verifiable**: identical inputs must yield identical state. Build
  a state-diff harness (§12) — it both tests the clone and resolves the few remaining
  inferred constants (§10).

---

## 3. Data model

### 3.1 Board / map
- **Logical grid: 100 wide × 32 tall**, row-major. Source: `data/terrain_authentic.json`
  (`grid[y][x]`, `y` 0=north/coast).
- Each cell has a **terrain type 0–15** (see legend in the data file / §8). Confirmed:
  **0 = desert (open)**, **5 = road/track**, **14 = sea (impassable)**; **2 & 3 =
  escarpment**; the rest are coastal/inland point-features (towns/ports/oases) —
  categorised but not individually named.
- **Coordinates:** `x` increases west→east (Axis starts west/low-x, British east/high-x);
  `y` increases north→south (0 = Mediterranean coast).
- **Viewport:** the original scrolls a **22×22-cell** window; a clone may show more, but
  keep the scroll model in mind for UI.
- **Passability:** sea (14) is impassable to land units. Other terrain is passable;
  terrain affects *cost/eligibility* (§5.1), not blanket blocking.

### 3.2 Units
Source of the full roster: `data/master_oob.json` (128 units). Each unit has:

| Field | Meaning | Notes |
|---|---|---|
| `x, y` | current position (top-left of footprint) | |
| `dest_x, dest_y` | move-order destination | null when none |
| `mps` | movement points per turn | per-unit; observed values 0,4,6,7,8,10 |
| `strength` | **static** combat strength | 0–200; does **not** change in play |
| `efficiency` | **dynamic** readiness 0–100 | starts 100; the attrition variable |
| `morale` | morale value | from OOB |
| `supply` | current supply state | derived each turn (§5.4) |
| `nationality` | 1=British, 2=German, 3=Italian | |
| `side` | British, or Axis (German+Italian) | for supply/ZOC/combat |
| `designation`, `division` | names | from `unit_name_tables.json` |
| `type` | behaviour class | *not* a clean branch; see below |
| `arrival` | reinforcement day | enters when clock ≥ this (§5.6) |
| `order` | current order/mode | 1=Move,2=Assault,3=Hold,4=Travel,… (§5.1) |
| `travel` | 1×1 travelling flag | §5.2 |
| `caught` | caught-on-road flag | §5.2 |

- **Footprint:** a unit normally occupies a **2×2** block of cells `(x,y),(x+1,y),
  (x,y+1),(x+1,y+1)`; while travelling it is **1×1** `(x,y)`.
- **`type`** loosely groups units and gates a little combat behaviour (e.g. armour), but
  the unit's *identity/branch* comes from its designation, not this field. Derive a
  display branch (armour/recce/artillery/infantry) from the designation string.
- **Nationality → side:** British → British; German & Italian → Axis.

### 3.3 The clock & calendar
- A running **turn counter** increments each turn.
- The **campaign clock** (used for reinforcements and scenario windows) is
  `clock = (turn_counter + 2) // 3` — i.e. **one campaign "day" every three turns**.
- The campaign spans **days 1–624**; the UI shows a JAN–DEC calendar derived from the
  clock.

---

## 4. Game structure

### 4.1 Top-level flow
```
init
 → title / options screen  (choose: side, game type, number of players, scenario, [Malta])
 → unpack chosen scenario's order of battle
 → TURN LOOP  (see 4.2)  until victory/end state
 → result screen (tactical/major/decisive British/Axis, or draw)
```
Scenario choice selects a 25-byte scenario record (`data/scenarios.json`) giving the
start/end day, objectives and thresholds.

### 4.2 Turn loop
Each turn, in order:
1. increment turn counter; recompute campaign clock.
2. **admit reinforcements** whose `arrival` ≤ clock (§5.6).
3. rebuild the per-cell **ZOC + supply** state (§5.3–5.4).
4. for **each side** (British, then Axis — the engine runs phases once per side):
   - collect/execute **orders** (player input, or AI planning if that side is
     computer-controlled — §6);
   - resolve **movement** (animated step-by-step in the original) and **combat**.
5. apply **attrition / recovery** to efficiency (§5.5).
6. check **victory / end** conditions (§5.7); if met, exit to result screen.
7. render.

Phases are executed once per side using a "current side" selector; keep that structure so
per-side supply/movement/combat are cleanly separable.

---

## 5. Rules

### 5.1 Movement & orders
Orders (menu order → internal use): **1 Move, 2 Assault, 3 Hold, 4 Travel, 5 Report,
6 Divide, 7 Fortify, 8 Go-To-Port**. (Report is display-only; Divide/Fortify/Go-To-Port
effects are inferred — see §10.)

- A unit with a **Move** order advances toward `dest` **one cell per step**, up to its
  **MPS** budget per turn, **stopping on enemy contact** (when it becomes adjacent to an
  enemy). Long moves continue over multiple turns.
- **Step cost** = a base cost per cell scaled by a **mode multiplier**:
  - **Assault (mode 2): ×1.5** cost.
  - **Travel (mode 4): ×0.5** cost (double reach) — see §5.2.
  - otherwise ×1.0.
  There is **no graduated per-terrain cost table**; terrain governs *passability* and
  *road eligibility*, not a per-type toll. (A reasonable base cost is 1 MPS/cell; treat
  the exact base as tunable — see §10.)
- Sea is impassable; a unit may not move into a cell where its footprint would overlap
  sea, another unit, or (for a 2×2) go off-board.

### 5.2 Travel (road movement, 1×1)
- **Travel** requires the unit to be **on or adjacent to a road** (terrain type 5).
- While travelling the unit collapses to a **1×1** footprint (fits the road) and pays
  **×0.5 movement cost** (extended reach).
- On reaching its destination it **re-forms to 2×2** — **unless it is "caught"**: if it
  ends a step **adjacent to an enemy** while travelling, it stays **1×1** and is flagged
  `caught`.
- **Caught-on-road penalty:** a caught/travelling unit takes **double** combat loss if
  attacked (−20 efficiency instead of −10). It is a column on a road, not a formation.

### 5.3 Zone of control (ZOC)
- Each unit projects ZOC over **its footprint cells plus the orthogonally adjacent
  cells**, tagged by side, rebuilt each turn on the per-cell flag grid.
- ZOC **blocks enemy supply tracing** (§5.4) and is used by the AI's threat scan (§6).

### 5.4 Supply
- Supply is **traced from the board edge**: British from the **east** edge, Axis from the
  **west** edge.
- Compute a shortest-path **distance** from each unit to its supply edge across passable
  cells (Dijkstra/BFS), **blocked by enemy units and enemy ZOC**. A unit with no path is
  **out of supply**.
- **Delivered supply level** falls with distance along a fixed curve, indexed by
  `distance >> 2` (i.e. distance/4):
  ```
  [90,80,75,70,65,60,55,50,49,48,47,46,45,44,43,42,41,41,40,40,39,39,38,38,37,37,36,36,36,35,35]
  ```
  (clamp the index to the last entry).
- **Bands** (for display/effects): NONE / V LOW / LOW / Q LOW / FAIR / GOOD / V GOOD.
- Out-of-supply units suffer attrition and reduced combat (§5.5).
- *Inferred:* the original distinguishes small units (draw from an adjacent HQ) from
  divisions/HQs (trace to edge/port). A single edge-trace model is a faithful first
  approximation; refine if validation shows divergence (§10).

### 5.5 Combat
Two quantities per unit: **strength** (static) and **efficiency** (dynamic, 0–100).
- **Effective power** = `strength * efficiency / 100`.
- **Assault resolution** (attacker vs an adjacent defender). The engine compares a
  computed value against a threshold:
  ```
  value      = (combat_readiness * 100) / MPS      # numerator = a dynamic per-unit byte
  threshold  = defender_defence_value              # a per-unit field
             = 20  if the unit is armour (type 10) # fixed override
  if value >= threshold:  loser -= 10 efficiency, and the loser's order is forced to HOLD
  ```
  The exact identity of `combat_readiness` (the "+3 byte") is **inferred** (treat as a
  readiness/strength proxy; see §10). For a first build, a defensible faithful model is:
  attacker vs defender **effective power**, modified by posture/terrain, with the higher
  side winning and the loser taking **−10 efficiency + forced Hold**; the caught-on-road
  doubling (§5.2) applies.
- **Adverse-position / cut-off attrition:** **−3 efficiency** when out of supply or in
  enemy ZOC.
- **Recovery (per turn, when in supply and not in enemy ZOC):**
  `efficiency += (100 - efficiency) // 16 + 1` (capped at 100).
- A unit reduced to **0 efficiency is destroyed/removed**.
- Terrain defensive modifiers (escarpment/marsh favouring the defender) are plausible and
  used in the reference arena, but are **not confirmed** in the original resolver — treat
  as tunable (§10).

### 5.6 Reinforcements & withdrawal
- Each unit has an **`arrival` day**. Each turn, any not-yet-present unit with
  `arrival ≤ clock` **enters** at its side's board-edge staging point — **British at
  ~(98,11) on the east edge, Axis at the west edge** — placed in the first free cell
  (nudge if occupied).
- **Withdrawal** ("unit to be withdrawn next turn") is the parallel exit; the original
  removes scheduled units. Model as an optional per-unit withdrawal day if present in
  data; otherwise omit.

### 5.7 Victory & end conditions
- **Front line** = `(easternmost Axis unit x, westernmost British unit x)`; its **midpoint**
  measures territorial control. Track it each turn (also used by the AI).
- **The game ends** when the turn counter/clock reaches the scenario's **end day** (turn
  limit) or a front-line **stalemate** is detected.
- **Scoring** is **objective-based**: for each side compute a value from the scenario's
  **objective columns** (map x-positions the side is expected to hold; see
  `scenarios.json`) plus **surviving-unit-count thresholds**. Compare the two sides'
  values → a signed result:
  - British **tactical / major / decisive** victory, **draw**, or Axis **tactical /
    major / decisive** victory (result message = one of a 7-way ladder).
- Objectives per scenario are `(column, type)` pairs; "control" = which side holds the
  ground around that column (units east/west of it). *Type-code semantics are partly
  inferred — see §10.*

---

## 6. The AI

A **budget-limited, deterministic, per-unit heuristic planner** (no search tree).

- On a computer-controlled side's turn, seed a **decision budget H = 40**; sweep the
  side's units repeatedly, spending **10 of the budget per full pass** (~4 passes), until
  the budget is exhausted.
- Build a **regional strength map**: a 30-slot table tallying each unit's **weighted
  strength** per side (weight derived from MPS and type) — the AI's threat/opportunity
  assessment. Pick a **target** from it (stored as target coordinates).
- **Per unit**, decide **offensive vs defensive** spatially:
  - compute the **front-line midpoint** `= (easternmost Axis x + westernmost British x)/2`;
  - the operational band reference `= clamp(midpoint − 25, 0, 50)`; a unit within the
    **50-column window centred on the front (≈ ±25 columns of the midpoint) acts
    offensively**, otherwise defensively.
  - **offensive** → choose a target column/path and issue **Move** toward it;
  - **defensive/local** → **Assault** an adjacent enemy if present, else **Move** toward
    the target; if the target is the **board edge** (x = 98), issue a **retreat / Go-To-
    Port** order.
- Perception is by **ray-casting over the ZOC/flag grid**: from each unit, scan outward in
  the four directions (±1 row, ±1 unit-column) within the operational band, testing for
  enemy/ZOC flags.
- *Inferred:* the exact weighting that selects **which** region becomes the target, and
  the precise offensive/defensive score inputs. The spatial band above is confirmed.

---

## 7. Scenarios

Source: `data/scenarios.json` (6 entries). Each scenario is a **day-window into one
624-day timeline**:

| # | Name | Day window |
|---|---|---|
| 1 | Enter Rommel | 1–31 |
| 2 | Battleaxe | 77–83 |
| 3 | Operation Crusader | 233–277 |
| 4 | The Battle of Gazala | 422–460 |
| 5 | El Alamein | 572–590 |
| 6 | The Desert War | 1–624 (full campaign) |

Each entry provides: **start day**, **end day (turn limit)**, **British objectives** and
**Axis objectives** as `(column, type)` pairs, and **unit-count thresholds** per side.
A scenario is populated by taking the master OOB and including every unit whose `arrival`
≤ the scenario window — i.e. the whole game derives from **one master list gated by
arrival time**. (Remaining scenario-record bytes — scroll origin, config — are only
partly labelled; see the file.)

---

## 8. Presentation

Recovered colour/graphics model (spec in `data/graphics.json`, art in
`data/tiles_sheet.png`):

- **Tiles:** 8×8 monochrome cells (8 bytes each, MSB = leftmost pixel) — terrain tiles,
  unit-counter symbols and glyphs. Use `tiles_sheet.png` as the source art; the
  tile↔terrain-type assignment is **not yet mapped** (§10) — assign by inspection or use
  clean substitutes.
- **Colour compositing** (per cell at draw time):
  - **paper/bright** comes from the **terrain** (mostly PAPER 6 = desert yellow; features
    vary);
  - **ink** comes from the **unit's side**: **British = blue (1), German = black (0),
    Italian = magenta (3)** — the historic Spectrum palette. A counter renders as a
    side-coloured symbol over its terrain.
- **Units** draw as **2×2** counters (1×1 while travelling), carrying their symbol and
  strength.
- **Screen:** a scrolling **22×22-cell** viewport over the 100×32 map; info/report panels
  alongside (labels recovered: STR, MPS, SUP, MOR, EFF, etc. — see `ui_strings.json`).
- **All UI text** (menus, prompts, order names, supply bands, result ladder, scenario
  names) is in `data/ui_strings.json` — reuse verbatim for authenticity.

---

## 9. Data files (schemas)

| File | Contents |
|---|---|
| `data/master_oob.json` | 128-unit order of battle: nationality, designation, division, name, x, strength, type, arrival, morale, role. The single source of all units. |
| `data/scenarios.json` | 6 scenarios: start/end day, objectives `(column,type)`, unit thresholds, raw bytes. |
| `data/terrain_authentic.json` | 100×32 terrain grid (`grid[y][x]`, low-nibble type) + terrain legend (confidence-graded). |
| `data/terrain_authentic.png` | Colour render of the terrain map (reference). |
| `data/ui_strings.json` | All UI text: scenario names, order menu, report labels, supply bands, turn phases, victory ladder, Malta options, calendar. |
| `data/unit_name_tables.json` | Designation + division token tables and encoding, for naming. |
| `data/graphics.json` | Tile base/format, terrain attribute table, side-ink table (decoded), draw model, palette. |
| `data/tiles_sheet.png` | Rendered 8×8 tile/sprite/glyph sheet. |

(Legacy per-scenario extracts — `units_scenario_*.json`, `terrain_map.json`,
`strings_table.json` — are superseded by the files above but included for cross-checking.)

---

## 10. Confirmed vs inferred (fidelity ledger)

**Confirmed (build exactly):** no-RNG determinism; 100×32 terrain map + data; 128-unit
OOB with nationalities & arrivals; clock = `(turn+2)/3`; scenario day-windows &
objectives; supply curve `[90…35]` indexed by `dist>>2`; efficiency loss **−10** on
combat loss + forced **Hold**; attrition **−3**; recovery `+(100−eff)//16+1`; **Travel
×0.5 cost / 1×1 footprint**; road = terrain type 5; reinforcement-by-arrival with
edge entry; **geographic/objective victory** with tactical/major/decisive ladder; AI
budget-40 planner with **±25-column offensive band**; nationality colours (British blue /
German black / Italian magenta); tile data at the recovered base.

**Inferred / tunable (agent has latitude; validate against original — §12):**
- the `combat_readiness` numerator's exact meaning (the "+3 byte") and the precise
  odds test;
- the **base movement cost** per cell (assumed uniform; no per-terrain table exists);
- **supply sourcing** split (battalion-from-HQ vs division-to-edge) — single edge-trace
  model used as approximation;
- **Assault ×1.5 / caught-on-road ×2** exact application;
- **minor-order effects** (Divide, Fortify, Go-To-Port) — Report confirmed;
- **schedule tables** (per-month supply/replacement, indexed by clock/30) — located, not
  fully labelled;
- **AI target-region weighting**;
- terrain **point-feature names** (town/port/oasis) and **tile↔terrain assignment**;
- **Malta status** effect (strings present, no invocation found in the 48K image);
- **sound** and exact **UI panel layout** — untouched.

Where inferred, prefer a simple, deterministic model and expose it as a tunable constant;
the diff harness (§12) will pin the true value.

---

## 11. Suggested Python build plan

A clean, testable module layout:
```
desert_rats/
  data.py         # load JSON data into typed structures (Unit, Scenario, Map)
  board.py        # 100x32 map, terrain, passability, coordinates, viewport
  units.py        # Unit model, footprint (2x2 / 1x1), branch derivation
  zoc_supply.py   # per-cell flag grid; ZOC; edge-trace supply + curve + bands
  movement.py     # orders, step cost + mode multipliers, Travel, contact-stop
  combat.py       # effective power, assault resolution, attrition, recovery
  reinforce.py    # clock, arrival admission, edge staging
  victory.py      # front line, objective scoring, tactical/major/decisive
  ai.py           # budget planner, regional strength map, offensive band, ray-scan
  game.py         # turn loop, per-side phases, state machine, end conditions
  render/         # terminal or 2D renderer; colour compositing; tiles
  main.py         # title/options → scenario select → game
tests/
  test_*.py       # unit tests per module + the diff harness (see 12)
```
Build order (each independently testable): **data → board → units → zoc_supply →
movement → combat → reinforce → victory → game (loop) → ai → render**. Get a headless
2-player game correct first; add the AI; add rendering last.

Keep all state in plain, serialisable structures so a full game state can be snapshotted
and diffed (§12). No global RNG; if you ever need tie-breaks, make them deterministic
(e.g. by unit id / scan order).

---

## 12. Validation strategy (how to *prove* faithfulness)

Because the engine is deterministic, faithfulness is testable rather than aspirational:

1. **Golden traces:** run the original in a ZX Spectrum emulator (Fuse) on a chosen
   scenario; at each turn, snapshot the machine and export unit records (positions,
   efficiency, supply) using the field offsets in `reference/engine-map.md`. This yields a
   per-turn "golden" state sequence for fixed inputs.
2. **Diff harness:** run the clone on the same scenario and inputs; compare state turn by
   turn.
3. **Localise divergence:** any mismatch points directly at one inferred constant (§10) —
   fix it, re-run. Validation thus *completes* the reverse-engineering.
4. **Regression bed:** the reference `desert_rats_arena.html` implements much of this rule
   set already and is a useful sanity check for mechanics before the emulator diff.

Acceptance: on each of the six scenarios, the clone's turn-by-turn state matches the
emulator trace (positions and outcomes) for a scripted input sequence.

---

## 13. Open items

See `reference/prospects.md` for the prioritised backlog (terrain-cost base, minor
orders, Malta, schedule-table labels, AI weighting, tile↔terrain mapping, sound, the
128K edition). None blocks a playable faithful build; each is a refinement the diff
harness will help settle.
