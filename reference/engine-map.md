# Desert Rats — Engine Map

A reverse-engineering map of the game engine's core, recovered from the 48K
binary by disassembling the routines that *read* each data structure (SkoolKit
`sna2skool.py`). Confidence is tagged **[CONFIRMED]** (read directly from the
code), **[LIKELY]** (strongly implied by the access pattern), or
**[CANDIDATE]** (structure is clear, meaning inferred).

The guiding technique throughout: locate a table, find every instruction that
references its address, then disassemble the consumer. The routine tells you
what the numbers mean.

---

## 1. Spatial model

**[CONFIRMED] The logical map is 100 cells wide.** Routine `0x8DE0` stamps bits
onto four cells at `IY+0, IY+1, IY+100, IY+101` — a 2×2 block whose vertical
neighbour is `+100`, so the cell-array row stride is **100**. Unit x-coordinates
run 0–98, which fits a 100-wide grid exactly. (This is the logical grid used for
movement/supply/combat; it is distinct from the *graphical* map, which is
compressed/tile-encoded and drawn separately.)

**[CONFIRMED] Units occupy a 2×2 cell footprint.** The same routine sets a
unit's zone bits on all four cells of its 2×2 block. This matches the on-screen
counter size.

**[LIKELY] Per-cell bit-flag array (stride 100), rebuilt each turn.** Routine
`0x8DE0` and the supply tracer write bit flags into a cell-attribute array:
- **bit 1** — zone of control (stamped as the unit's 2×2 block)
- **bit 2** — road / blocking flag (set when unit field `+1 == 13`)
- **bit 3** — in-supply (set by the network tracer, below)

A unit flag at `(IX+9) bit 4` gates whether a unit projects its zone (probably
"disrupted/out-of-supply ⇒ no ZOC").

---

## 2. Supply system

This is the system the manual leans on, and it is now visible in three pieces.

**[CONFIRMED] Transport-loss curve @ 0xDFE7.**
```
90 80 75 70 65 60 55 50 49 48 47 46 45 44 43 42 41 41 40 40 39 39 38 38 37 37 36 36 36 35 35
```
Routine `0x8656` reads it as `curve[ distance >> 2 ]` and scales the result to a
percentage. So supply *delivered* falls from 90% down to 35% as the **trace
distance** grows (every ~4 cells steps one entry down the curve). This is the
distance penalty the manual describes for tracing supply back toward your board
edge.

**[LIKELY] Supply / control network = coordinate-list tables.**
At `0xE01B, 0xE03D, 0xE069, 0xE07F` sit a series of tables, each a count byte
followed by **variable-length records**: `[len][x][y]…[sub-coords]…` terminated
by `5` (and `255` as a hard end). Routine `0x9225` indexes a table by an entry
number; routine `0x9244` walks a record's coordinate list and, for each cell,
**sets the in-supply bit** (`SET 3,(IY+0)`). In other words, the engine
propagates supply by walking stored coordinate paths and marking cells — the
road/track network (or per-side supply routes) made concrete.

**[LIKELY] Source-proximity check @ 0x86CE / 0x86F7.** Scans the 0xE07F table
against a unit's own cell and its orthogonal neighbours — i.e. "is this unit on
or adjacent to a supply source/network node?"

---

## 3. Movement / cost tables

**[LIKELY] Per-side cost blocks @ 0xDF84 and @ 0xDFB6.** Routine `0x96E0`
computes the address as `base + index*30 (+22)`:
- the `*30` stride mirrors the unit-record size,
- the optional `+22` sub-offset is selected by state vars `0xCAD8` and `0xCAE5`
  (current side / move-type),
- index is small (a side selector).

`0xDF84` holds values in {5,10,15,20} (read as movement-point costs, ×5);
`0xDFB6` holds values in {3..10} (a second cost/factor band). Together they look
like the per-side movement-allowance / terrain-cost parameters.

---

## 4. Combat & the efficiency model **[CONFIRMED]**

Combat is **not** a strength-removal CRT. It is a continuous **efficiency-attrition**
model, which is why the strength byte (record +28) is written only at setup and
never decremented in play.

- **Strength (record +28)** is a *static* base value.
- **Efficiency (record +16)** is the *dynamic* combat state, 0–100.
- **Effective combat power = strength × efficiency / 100.** Routine `0x8613`
  performs exactly this `value × eff / 100` scaling; it's what the Report screen
  shows as STR.

Three primitives drive it:

| Routine | Effect |
|---------|--------|
| `0x8624` | apply loss: `eff = max(0, eff − damage)` |
| `0x8632` | recovery (per turn): `eff += (100 − eff)/16 + 1`, clamped to 100 |
| `0x8613` | scale a value by `eff/100` (effective strength) |

Loss is applied at two sites with **fixed increments**:

- **`0x7A03` — combat resolution.** Computes a combat value from the engaged
  unit's fields (a `field×100/field` ratio), takes a **special branch when
  type == 10 (armour)**, compares against the opponent's value, and on a win
  calls the loss routine with **damage = 10** (a −10 efficiency hit).
- **`0x83DA` — attrition.** Applies a fixed **−3 efficiency** for adverse
  positioning / zone effects.

So a unit ground down in repeated combat loses efficiency in ~10-point steps,
fights progressively weaker (power = strength × eff%), and regenerates toward
100 when it disengages — units degrade and recover rather than vanish. The exact
combat-value comparison still has a couple of unlabeled field inputs, but the
**model and its constants (−10 combat, −3 attrition, /16+1 recovery) are
confirmed from the code.**

### Per-type factor table @ 0xDF38 — status revised
The 6-byte rows at `0xDF38` are **not referenced by any load** (verified by an
exhaustive literal-address search), so they are not consulted by the live combat
path above. They are likely display/setup data or a dormant table; the combat
maths runs off unit fields + the fixed increments, not a per-type CRT.

---

## 5. Naming system (recovered earlier, recapped)

- **Token encoding** — name entries are length-prefixed; a byte `< 0xA5` is a
  literal character, a byte `≥ 0xA5` inserts pool string `#(byte − 0xA5)`,
  expanded recursively. Pool base `0xE123`. [CONFIRMED]
- **Decoders** — token→address `0x7620`; recursive expander `0x7639`;
  two-part unit-name printer `0x7FDA`. [CONFIRMED]
- **Unit name = designation + division.** Designation from record byte **+24**
  → table `0xE3AD` (137 entries); division from byte **+25 − 1** → table
  `0xE2EF` (25 entries), omitted when 0 (independent unit). [CONFIRMED]
- **Order menu** table `0xE6E1` (`M MOVE / A ASSAULT / H HOLD / T TRAVEL /
  R REPORT / D DIVIDE / F FORTIFY / P GO TO PORT`) decodes the order field. [CONFIRMED]

---

## 6. Key state variables (working RAM)

| Addr | Role (inferred) |
|------|-----------------|
| 0xCAD8 | current side / player (gates cost-table sub-offset) |
| 0xCAE5 | move-type or order context (gates +22 offset) |
| 0xCACF | 16-bit index into cost table |
| 0xDF18 | written by 0xAB40 — a scratch/state byte inside the constants page |
| 0x5B00 | text assembly buffer (names/reports built here, then drawn) |

---

## 7. Routine memory map

| Addr | Routine |
|------|---------|
| 0x7620 | token index → pool string address |
| 0x7639 | recursive name expander (writes to 0x5B00) |
| 0x7FDA | unit-name printer (designation + division) |
| 0x7A03 | combat resolution (computes value, applies −10 efficiency; armour special-cased) |
| 0x83DA | attrition (−3 efficiency for adverse position) |
| 0x8613 | scale value by efficiency/100 (effective strength) |
| 0x8624 | apply efficiency loss (clamped to 0) |
| 0x8632 | efficiency recovery per turn ((100−eff)/16 + 1) |
| 0x8656 | supply-delivery curve lookup (`curve[dist>>2]` → %) |
| 0x86CE / 0x86F7 | scan 0xE07F coord-table vs unit cell + neighbours |
| 0x8950 | supply replenishment (trace unit to board edge, reset supply) |
| 0x8DE0 | stamp 2×2 zone-of-control / flag bits (stride-100 cell array) |
| 0x9225 / 0x9244 | walk network coord-lists, mark in-supply cells |
| 0x96E0 | movement / supply cost lookup (0xDF84 / 0xDFB6) |
| 0x9C45 | scenario-setup unpacker: expands source defs at 0xEF58 into 30-byte records |
| 0xAB40 | writes state byte 0xDF18 |

**[CONFIRMED] Unit record base = 0xBA58** (Axis array; British at 0xC070), so the
field offsets are now exact: +0/+1 x/y, +2 MPS, +8 supply, +9 morale, +16
efficiency (dynamic combat state), +17 owner/side, +24 designation index, +25
division index, +26 type, +28 base strength (static).

**[CONFIRMED] Scenario-setup data @ 0xEF58.** Routine `0x9C45` unpacks compact
source unit-definitions (≈10 bytes each: x, y, …, designation, division, type)
into the working records — meaning every scenario's initial order of battle can
be read straight from these source tables, not just the three captured snapshots.

---

## 8. What's bagged vs still at large

**Bagged:** the spatial model (100-wide grid, 2×2 units, per-cell flag array);
the supply distance-decay curve and its propagation mechanism; the movement-cost
table layout; the **combat / efficiency-attrition model** (static strength,
dynamic efficiency, −10 combat / −3 attrition / (100−eff)/16+1 recovery,
effective power = strength × eff%); the entire naming system; the unit-record
field map; and the scenario-setup source tables at 0xEF58.

That's movement, supply, and combat — the full rules trinity — plus naming and
setup. The engine is, in its essentials, recovered.

**Still at large (refinements + open rules — see `prospects.md`):**
1. **Terrain movement cost.** The terrain → MPS lookup in the mover (0x8584 /
   0x64A9 + `CP 5`) is not yet pinned. *The 0xDF84 tables are turn-phased campaign
   schedules, not terrain costs* — index = `turn ÷ 30`, `+22` for side 2, read by
   the 0x96E0 family. Terrain cost is a separate, still-open lookup.
2. **Terrain-type semantics.** 14 = sea and 0 = desert are confirmed (§12); the
   other 14 low-nibble types await the tile/graphic tables (five 256-entry
   accessors at 0xD80E…0xDBAD).
3. **Larger open subsystems** — victory scoring / objectives, reinforcement &
   withdrawal execution, the minor orders, Malta's supply effect, the AI, and
   save/load — are catalogued with hooks in `prospects.md`.

**Resolved this pass:**
- **Travel reach literal.** The multiplier at **0x85CB** halves movement cost on
  Travel (mode 4, `SRL H:RR L`) and adds a half on Assault (mode 2, ×1.5) — the
  arena's 0.5 is exact. Mechanism, 1×1 flag and literal all confirmed.
- **The graphical map is *not* compressed.** Terrain is a flat row-major byte
  array at **0xCB39**, width *(0xCAA7)=100, **100×32**, terrain = low nibble;
  queried by 0x64A9 as `0xCB39 + y*100 + x`. Extracted to
  `terrain_authentic.json` / `.png`, shared across scenarios (§12). The earlier
  "compressed" reading was simply a wrong width.

**Resolved this pass** (top-down access from the tape + data decode — see §11):
- **Flag-array base = 0xAEA1 (44705).** Cell (x,y) at `0xAEA1 + y*100 + x` via
  addresser 0x8D96; a neighbour-stepper (dir 0–3 → IY ±1/±100) sits beside it.
- **Combat value formula.** `(record+3)*100 / MPS` compared to threshold
  `record+13` (or a fixed 20 for armour, type == 10); on ≥ it applies −10
  efficiency and forces the order to HOLD. The two previously-unlabelled inputs
  are +3 (numerator) and +13 (threshold).
- **The "string-pool tail" was a mis-lead.** Tokens 59–93 aren't pool entries —
  they index the **UI message table at 0xE6E1**, now fully decoded
  (`ui_strings.json`): all six scenario names, the eight order names, report
  labels (STR *and* EFF), the seven supply-band names, turn-phase names, the
  victory ladder, the **Malta-status** option, and a JAN–DEC calendar.

**Resolved earlier:** the complete order of battle — all 128 units, three
nationalities (side byte 1=British/2=German/3=Italian) with a reinforcement
`arrival` field — is a single master table at **0xEF58** (`master_oob.json`), so
every scenario derives from one list gated by arrival timing; no per-scenario
snapshots needed.

The toolchain and the programmer's idioms (token-compressed strings, parallel
index tables, IX-relative records, IY-relative stride-100 cells, fixed-increment
efficiency attrition) are now well understood — each remaining item is a tidy
follow-up rather than a fresh excavation.

---

## 9. Load-time structure & program entry **[CONFIRMED — from tape]**

Recovered from the original tape (`Desert_Rats_-_Side_1.tzx`); the auto-run BASIC
loader `DRS` was de-tokenised with SkoolKit `tapinfo.py`.

```basic
10 INK 5: PAPER 5: BORDER 0: CLEAR 24899: LOAD ""SCREEN$ : LOAD ""CODE : LOAD ""CODE
100 RANDOMIZE USR 30332
```

**Load-time memory map** (`CLEAR 24899` ⇒ RAMTOP 24899, everything above is
protected code/data):

| Region | Bytes | Contents |
|--------|-------|----------|
| 0x4000–0x5AFF | 6912 | loading screen (`LOAD ""SCREEN$`) |
| 0x6144–0xAEA0 (24900–44704) | 19805 | **main machine code** — every disassembled routine lives here |
| 0xAEA1–0xC958 (44705–51544) | — | **working RAM** — unit records built at runtime (Axis 0xBA58, British 0xC074); not loaded from tape |
| 0xC959–0xFFFF (51545–65535) | 13991 | **loaded data**: cost tables 0xDF84/0xDFB6, supply curve 0xDFE7, network coords 0xE01B…, string pool 0xE123, division/designation tables 0xE2EF/0xE3AD, order menu 0xE6E1, master OOB 0xEF58, plus menu state vars |

This confirms the earlier inference that the unit records sit in an
*uninitialised gap* between the two loaded blocks — they are assembled by the
setup unpacker, not loaded. The graphical map is not a separate resident block,
so it is packed inside the main code block.

**Program entry.** `RANDOMIZE USR 30332` targets **0x767C**, which is a 4-entry
`JP` dispatch table — the top of the whole call graph:

| Vector | Target | Role |
|--------|--------|------|
| 0 | **0x9A8B** | main / title+options screen (USR lands here) |
| 1 | 0x9B06 | input / movement-cursor loop |
| 2 | 0x9C25 | secondary dispatch |
| 3 | 0x9C45 | scenario-setup unpacker |

Top-level flow, now traceable downward: **0x9A8B** (title/options — reads
selection var **0xCB2D** for side / game-type / players, prints options via token
printer 0x7659) → setup unpacker 0x9C45 → turn loop. Having the entry point makes
the remaining bottom-up gaps (§8 items 1–2) reachable by following calls forward
from 0x9A8B rather than guessing at callers.

---

## 10. Control flow: entry → options → turn loop **[CONFIRMED]**

Walked top-down from the entry point.

- **0x767C** dispatch table → **0x9A8B** title/options screen; prints side /
  game-type / players from menu-state **0xCB2D** via token printer 0x7659, then
  falls through into…
- **0x9B06** options-input loop: reads a key, keys `1`–`5` pick options.
  **`1` starts the game** — first pass calls setup unpacker **0x9C45** (builds the
  unit records from the 0xEF58 master OOB) and sets state=1; once state=1 it
  enters **0x97E0**. **`4` cycles the scenario** via a **25-byte-stride scenario
  table** (index **0xCB12**, pointer **0xCB13**, sub-pointer at entry +2/+3).
- **0x97E0 — the turn loop** (loops at 0x97E3):
  - increments the **turn counter 0xCB0F** at the top of every turn;
  - runs each phase **once per side** via the idiom `LD A,1|2 → 0xCAD8 ; CALL
    phase` (side 1 = British, 2 = Axis) — the same 0xCAD8 that selects the
    movement-cost tables;
  - the movement phase **0x7C1F** walks every unit, reads its order/mode
    (record +12 = IX+16), and writes a **footprint size** (1 travelling / 2
    normal, from record +5 bit 4) and position into working vars
    **0xCAAF / 0xCAB0**;
  - at the loop foot it tests game-state **0xCB29**: ≠ 5 → next turn;
    **== 5 → victory screen** (message token 41).

**New working vars:** turn counter 0xCB0F, game phase/end 0xCB29, footprint size
0xCAAF/0xCAB2, active-unit position 0xCAB0/0xCAB3, menu state 0xCB2D, scenario
index/pointer 0xCB12/0xCB13.

**Reimplementation skeleton** now falls out directly:
`init → title/options (side, game-type, players, scenario) → unpack OOB →
repeat{ per-turn: for each side → supply, movement, combat, display } until
game-state = victory`.

---

## 11. Flag array, combat maths & the UI string table **[CONFIRMED]**

**Per-cell flag array base = 0xAEA1 (44705).** The addresser at 0x8D96 computes a
cell's flag byte as `0xAEA1 + y*100 + x` (16-bit multiply at 0x64F9) and loads it
into IY; the stamp routine 0x8DE0 falls in from 0x8D77 and sets bit 1 across the
unit's 2×2 block — or just IY+0 when the 1×1 travel flag (record +5 bit 4) is set.
A companion stepper advances IY by a direction code 0–3 → ±1 / ±100, confirming
the stride-100 grid a third way. The base sits exactly at the bottom of the
working-RAM gap the loader leaves between the two loaded blocks (§9).

**Combat value (routine 0x7A03).** For the engaged unit,
`value = (record+3) × 100 / MPS(+2)`, compared against `threshold = record+13`
— except armour (type == 10) uses a fixed threshold of 20. On `value ≥ threshold`
the loser takes −10 efficiency and its order is forced to HOLD (3). The two
formerly-unlabelled inputs are thus the **+3 numerator** and the **+13 threshold**.

**UI message table @ 0xE6E1** (printed by 0x7659; length-prefixed, pool-expanded;
zero-length slots pad the index space). Full decode in `ui_strings.json`:
- **Six scenarios:** Enter Rommel · Battleaxe · Operation Crusader · The Battle of
  Gazala · El Alamein · The Desert War.
- **Eight orders:** Move · Assault · Hold · Travel · Report · Divide · Fortify · Go To Port.
- **Report labels:** STR, MPS, SUP, MOR, A/M, EFF, FRT, UNITS, INF, ARM — STR and
  EFF shown separately, the efficiency-attrition model made visible in the UI.
- **Supply bands:** NONE · V LOW · LOW · Q LOW · FAIR · GOOD · V GOOD.
- **Turn phases:** REORG PHASE · FORCES MOVING · REPLACEMENTS (+ THINKING! for AI).
- **Victory ladder:** tactical / major / decisive, British or Axis, or a draw.
- **Newly surfaced mechanics:** a **Malta status** option (Historical / Operation
  Herkules / Not used as base) — an Axis-supply modifier — and a **JAN–DEC
  calendar**, so the turn counter maps to dates, tying directly to the OOB
  `arrival` field.

---

## 12. Terrain map **[CONFIRMED — extracted]**

**Not compressed.** The terrain query at 0x64A9 reads a flat, row-major byte array:
`terrain(x,y) = ( 0xCB39 + y*width + x ) & 15`, with `width = *(0xCAA7) = 100`.
The map is **100 × 32** (region 0xCB39 → the first tile-accessor base 0xD80E). Each
cell byte packs a **graphic/attribute high nibble** and the **terrain type in the
low nibble (0–15)** — gameplay uses the low nibble (`AND 15`, e.g. the `CP 5`
terrain test in the mover).

- **Shared across scenarios** — enter_rommel vs battleaxe differ by 3 cells, all on
  the bottom edge; it is the single North Africa campaign map (Gulf of Sirte →
  Egypt: the Cyrenaica bulge, coastal escarpment, an inland track, the depression).
  Extracted to `terrain_authentic.json` and `terrain_authentic.png`.
- **Terrain-type legend** (low nibble; full table in `terrain_authentic.json`).
  *Confirmed:* **0 = desert (open)**, **14 = sea (impassable)**, **5 = road/track**
  (the mover's `CP 5`; road *connectivity* lives in a separate layer, which is why
  type-5 cells read as sparse rather than continuous). *Likely, from E–W run
  continuity:* **2 & 3 = escarpment** (ridges parallel to the coast; 3 the upper
  coastal ridge). *Point-features* (isolated single cells): coastal ones
  (6, 7, 9, 10, 12 — 10 the most sea-adjacent) are **towns/ports**, inland ones
  (8, 13) **oases/forts**, **15** (fully isolated) reads like an **objective marker**,
  and **1, 4, 11** are mixed **rough/coastal** ground. Point-feature names are
  categorical guesses — telling town from port from oasis needs the manual's terrain
  key or the tile graphics (five 256-entry accessors at
  0xD80E / 0xD90E / 0xDA0E / 0xDB0E / 0xDBAD).
- **Viewport & scroll:** the on-screen test at 0x64B6 gates a **22 × 22** window;
  scroll origin at *(0xCAA5) (x,y). This is why the map is larger than the display.
- **Movement cost:** still open — the terrain → MPS lookup in the mover (0x8584 /
  0x64A9 + `CP 5`) has yet to be pinned. *Correction:* the tables at **0xDF84**
  (with 0xDF3C / 0xDFB6) are **not** movement costs; they are **turn-phased campaign
  schedules** — index = `turn ÷ 30`, `+22` for the second side, ×10-scaled, read by
  the 0x96E0 family (which pulls turn counter 0xCB0F). They sit just before the
  supply curve at 0xDFE8 `[90,80,75,…,35]`.

With this, the spatial model is complete: a 100-wide logical grid, a 100×32 terrain
byte map at 0xCB39, a stride-100 per-cell flag array at 0xAEA1, and a 22×22 scrolling
viewport — everything a 1:1 rewrite needs to reproduce the board itself.

---

## 13. Tier-1 rules recovered

### Victory & objectives — 0x9896, 0x9925, 0x9A3F
- **Front line** = (easternmost Axis unit x, westernmost British unit x), computed by
  0x9896 from record +0; stored at 0xCB27 and compared each turn. A **stalemate
  counter** (0xCB24) plus a **scenario turn-limit** (0xCB16) drive the end state
  (0xCB29 → 5).
- **Scoring is objective-based.** Per-side value routine 0x9925 reads the active
  scenario's 25-byte table entry — **British objectives at entry +8, Axis at +12**
  (two coordinates each) — plus a **unit-count threshold at +21**, combined with the
  surviving-unit counts (0x9A19 → 0xCB2B/2C).
- The two values are compared into a signed result: **British (−) / Draw (0) / Axis
  (+)** × tactical/major/decisive, printed as message 50 ("THE RESULT IS") then
  `50 + E` (E = 4 + score) → messages 51–57.

### Reinforcements — 0x8950
- Each unit carries an **arrival value at record +15** (= OOB byte 3). Every turn
  0x8950 walks the records; any unit with arrival ≠ 0 whose arrival ≤ the current
  game clock (0x8B31/35633) **enters at its side's board-edge staging point** —
  British at **(98,11)** on the east edge, Axis at the west — dropped into the first
  free cell (nudged if occupied). Withdrawal ("UNIT TO BE WITHDRAWN") is the parallel
  exit.

### Terrain & roads — mover 0x84BA, query 0x64A9
- Terrain type = low nibble of the cell byte at `0xCB39 + y*100 + x`. **Type 5 =
  ROAD**: the mover special-cases it, testing a direction bitmask for road
  connectivity — the gate behind Travel's "must be on a road". There is **no
  graduated per-terrain cost table**; step cost is a base amount scaled by the mode
  multiplier (0x85CB: Travel ×0.5, Assault ×1.5), with terrain governing passability
  (sea impassable).

### Combat — resolver 0x7A03
- Engaged-unit value = `(record+3)·100 / MPS(+2)`, compared to threshold `record+13`
  (or a fixed **20 for armour**, type 10); on value ≥ threshold the loser takes −10
  efficiency (0x8624) and is forced to HOLD. `record+3` is a dynamic readiness byte.

### Supply — tracer 0x9225/0x9244, curve 0xDFE8
- In-supply cells are traced from the board edge along the network coordinate lists
  (0xE01B/0xE03D/0xE069/0xE07F); delivered supply falls along the 90→35 curve by
  distance; replenishment at 0x8950. The battalion-draw-from-HQ vs division-trace-to-
  edge distinction is still only partly traced.

---

## 14. Scenarios, clock & Tier-2 findings

### Scenario table — working copy at 0xDE6C (25 B/entry, 6 scenarios)
Copied in from a master at 0xEEC2 at setup. Each entry (decoded → `scenarios.json`):
`+0/1` **start day**, `+2/3` **end day** (= turn limit → 0xCB16); `+7..+14`
**objectives** as `(column, type)` pairs — British at +7/8 & +9/10, Axis at +11/12 &
+13/14 (type codes 0–5, processed by 0x9280); `+21/+22` **unit-count thresholds**
(British, Axis). Remaining bytes (+4..6, +15/16, +18..20) carry scroll origin / config,
not yet all labelled. **Day windows:** Enter Rommel 1–31 · Battleaxe 77–83 · Crusader
233–277 · Gazala 422–460 · El Alamein 572–590 · **The Desert War 1–624** — confirming
each scenario is a day-window into one 624-day timeline; objectives are map columns each
side must hold; thresholds rise across the war (10 → 40).

### Game clock — 0x8B31
The arrival/scenario clock = `(turn counter 0xCB0F + 2) / 3` — one clock unit (≈ a
campaign day) every three turns. A unit enters when this clock ≥ its arrival value
(record +15); a scenario runs while the clock is within [start, end].

### Determinism — no RNG
No `LD A,R`, no FRAMES seed, no RANDOMIZE in the game-logic paths (FRAMES 0x5C78 is read
only at 0x73xx for input/animation timing). Combat and resolution are **fully
deterministic** — odds arithmetic, no dice; a rewrite reproduces outcomes exactly.

### Players / AI — 0xCB2E
0 = two players, 1 = computer plays British, 2 = computer plays Axis (set from menu
messages 91/92). The AI routine itself ("THINKING!") is the large remaining subsystem.

### Minor orders (partial) & Malta (unconfirmed)
Report (order 5) prints the unit report (0x8B32); an order-5 movement handler at 0x9C12
scales a field ×4. Divide / Fortify / Go To Port dispatch isn't cleanly isolated yet.
The "MALTA STATUS?" strings (messages 77–80) exist, but no invocation was found in this
48K image — likely conditional or a 128K-only option.

---

## 15. The AI — "THINKING!" — 0xA39E

Entered from the movement phase when the computer-side selector 0xCB2E matches the side
to move. Prints message 94, then runs a **budget-limited, deterministic, per-unit
heuristic planner** — no search tree, consistent with the engine-wide absence of RNG.

**Main loop.** Seed a decision budget `H = 40`; build target/threat context (0xA9EA,
0xA059, 0xA111); then repeatedly walk the AI's units (next-unit at 0xAC56) and, for each
unmarked one:
- **evaluate its situation** (0x9E7F family) → *offensive* (advance/attack) or
  *defensive / local*;
- *offensive* → pick a target column and path and issue a **Move** toward it (a chain of
  routines 0xA17D → 0xA2C3 → 0xA1EF → 0xA645 → 0xA25F → 0xA6BD; individual roles inferred
  from position in the chain);
- *defensive* → **assault** an adjacent enemy, else **Move** (order 1) toward the target
  at 0xCB32; a special case sets **order 9 (retreat / Go-To-Port)** when the target is the
  board edge (x = 98).

Each full pass over the force costs 10 of the budget; when it's exhausted (`H < 0`) the AI
ends. Units are marked done via bit 5 of record +3.

**Spatial reasoning** runs over the same stride-100 flag array at **0xAEA1**:
- coord → cell address, offset into an operational **band of ±50 columns** around a
  reference x at 0xCB2F (0x9E91);
- direction step, dir 0–3 → IY −100 / +2 / +100 / −2 (±1 row, ±1 *unit*-column) (0x9EB5);
- **directional line-scan** outward up to N cells, testing enemy/ZOC flag bits (0x9EC5).

So the AI "sees" by casting rays across the flag map from each unit within its band, then
seeks objectives, assaults on contact, or retreats to the edge.

**Decision thresholds (recovered).** The offensive/defensive split is spatial: the
band reference **0xCB2F = clamp( (front-line midpoint − 25), 0, 50 )**, where the
midpoint = `(easternmost Axis x + westernmost British x) / 2` (front line from 0x9896).
The in-band test (0x9E7F) then treats a unit as **offensive when it lies within the
50-column window centred on the front** (≈ ±25 columns of the midpoint) and
**defensive** otherwise. Strategic targeting is driven by a **30-slot regional
strength map** (table at 0xD6F1, 7 bytes/slot) built by 0xA9EA. **[RECOVERED --
disassembly + oracle, see reference/diff_harness/ and data/ai_regions.json]:**

- The table is STATIC data: 30 strategic regions, each 7 bytes -- two anchor
  coordinate pairs (well-known locations: (41,10) Tobruk imp 7, (92,16) Alamein
  imp 4, (24,2) Derna, (14,8) Benghazi, ...), importance 0-7 in the low 3 bits
  of byte 4 (upper bits are runtime flags), two runtime accumulators.
- Builder (0xA9EA): resets accumulators and flag bits; per unit, weight =
  strength >> 5, halved again when MPS (+12) < 5; friendly weight goes to
  byte 5 (NOTE: `LD (IY+5),D` -- the original STORES the last friendly weight
  instead of accumulating; enemies at byte 6 accumulate correctly), presence
  flags bit6/bit7, enemy-assaulting flag bit5. H counts friendly units,
  L counts those with MPS >= 36; the mobile-posture bit (0xCB31 bit 2) is set
  when L > 3H/4 (or H/2 with hysteresis when already mobile).
- Region scoring (0xAAE7-0xAB44, exact): no enemy -> 0; enemy with no friendly
  -> 0x60 + importance, gated to the side's reach window (Axis: region index
  <= (0xCB28); British: index > (0xCB27) - 10); enemy >= friendly (contested)
  -> 0x3C + importance; friendly > 2x enemy -> 0x32 + importance (mop-up);
  else 0. Scores are written back into byte 5.
- Target choice (0xA510/0xA537): each side walks the objective ladder at
  0xE07F DIRECTIONALLY (Axis forward/west-to-east, British backward), the
  winner's anchor going to 0xCB32.

Implemented 1:1 in desert_rats/ai_og.py (strategic core, including the
store-bug) wired into ai.plan_turn; region data committed as
data/ai_regions.json via reference/extraction_tools/extract_ai_tables.py.

---

## 16. Presentation layer **[recovered]**

### Graphics data
Tile/sprite bitmaps live at **0xF438** — 8 bytes per 8×8 cell (MSB = leftmost pixel),
~361 cells covering terrain tiles, unit-counter symbols and glyphs. The draw routine
(0x694B) fetches a pattern at `0xF438 + (symbol_code + hi*4 − 1) * 8`. Rendered to
`tiles_sheet.png`; machine-readable spec in `graphics.json`.

### Colour model (confirmed)
A cell's ZX attribute is composed at draw time:
- **paper / bright** from the terrain, via table **0xD80E** indexed by the full cell byte
  (mostly PAPER 6 = desert yellow; ink field varies per feature);
- **ink** from the unit's side, via table **0xCAC5** indexed by side, masked `AND 7` — so
  **British = 1 (blue), German = 0 (black), Italian = 3 (magenta)**, the exact historic
  Spectrum colours. (Raw bytes 24/27 for German/Italian carry unused high bits.)
The unit-counter **symbol** is a UDG chosen from the unit's type (special codes 13/14/15),
drawn over that composed attribute — a counter reads as "side-coloured symbol on the
terrain it stands on".

### Screen model
The map is a scrolling **22×22-cell viewport** (on-screen test 0x64B6) over the 100×32
logical map; scroll origin at 0xCAA5. Units draw as 2×2 counters (1×1 while travelling).

**Open (pixel-exact only):** individual tile → terrain-type assignment (which 0xF438 cell
is which terrain), the exact UI panel layout, and sound — none affecting the rules; the
final cosmetic layer for a pixel-faithful clone.
