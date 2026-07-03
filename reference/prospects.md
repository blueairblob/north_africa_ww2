# Desert Rats — Remaining Excavation Prospects

*Working backlog toward a full 1:1 reimplementation. Companion to `engine-map.md`.*

**Where we stand.** The engine is mapped end to end: load/entry structure, control
flow and the turn loop, movement + Travel (1×1 / ×0.5 cost), efficiency-attrition
combat, the supply curve and edge-tracing, ZOC, the complete 128-unit OOB (three
nationalities + arrival schedule), every UI string, the six scenarios, and the
authentic 100×32 terrain map. What follows is what's left, grouped by how much it
blocks a *playable, faithful* rewrite rather than a *pixel-faithful* one.

---

## Tier 1 — core rules a 1:1 still needs

> **Status after excavation (see `engine-map.md` §13):** #2 victory, #3
> reinforcement, #1 terrain/road cost, and #4 combat structure are now **recovered**;
> #5 supply is recovered except the battalion-vs-division sourcing split. What remains
> of Tier 1 is narrow: the objective **coordinates** (need the scenario-table decode,
> Tier 2 #9), the `record+3` combat-numerator's exact semantic, and the supply
> sourcing split. Hooks and findings below; ✔ = done, ◑ = partial.

1. **Terrain movement cost.** How a cell's terrain type (low nibble) becomes an MPS
   cost in the mover. *Note: the 0xDF84 tables are NOT this — see the correction
   below.* **Hook:** the per-step cost in the movement phase (0x8584, and the mover
   under 0x7C1F), the terrain read at 0x64A9 and its `CP 5` test. Expect either a
   small 16-entry per-terrain table or a flat base with a road discount feeding the
   0x85CB ×0.5/×1.5 mode multiplier.

2. **Victory scoring & objectives.** How game-state `0xCB29` reaches 5 and how
   tactical / major / decisive is chosen (messages 51–57). **Hook:** the loop-foot
   test in 0x97E0; the "THE RESULT IS" branch; candidate objective/coordinate
   tables at 0xE01B / 0xE03D / 0xE069 / 0xE07F. Find the VP accumulator + thresholds.

3. **Reinforcement & withdrawal execution.** How the OOB `arrival` field admits units
   on the right date, and the "UNIT TO BE WITHDRAWN NEXT TURN" path. **Hook:** setup
   unpacker 0x9C45 + the turn-loop "REPLACEMENTS" phase; the turn↔calendar mapping.

4. **Combat resolution, in full.** The `+3` numerator's exact meaning (a dynamic
   readiness value?), the odds test `value = (+3)*100 / MPS` vs `+13` (or 20 for
   armour), and which terrain/posture defensive modifiers are actually applied.
   **Hook:** resolver 0x7A03 + apply-loss 0x8624 + adverse-position attrition 0x83DA.

5. **Supply sourcing detail.** Battalion/brigade "draw from adjacent HQ" vs
   division/HQ "trace to board edge"; the network coordinate tables
   0xE01B / 0xE03D / 0xE069 / 0xE07F (roads? tracks? ports?) walked by 0x9225 /
   0x9244. **Hook:** replenishment routine 0x8950.

---

## Tier 2 — completeness

> **Status after excavation (see `engine-map.md` §14):** #9 scenario table
> **✔ decoded** (`scenarios.json` — start/end days, objectives, thresholds); #10 RNG
> **✔ resolved** — the engine is deterministic, no dice; #6 schedule tables **◑**
> characterised (clock = `(turn+2)/3`, ~monthly supply/replacement). Remaining: #7
> minor orders (Report done; Divide/Fortify/Go-To-Port dispatch ◑), and #8 Malta
> (strings exist but no invocation found in the 48K image — likely 128K-only).
> Bonus finds: AI-side selector 0xCB2E, and the game clock.

6. **Turn-phased schedule tables** 0xDF3C / 0xDF84 / 0xDFB6. *Confirmed:* indexed by
   `turn ÷ 30`, per-side (+22 offset), ×10-scaled, consumed by the 0x96E0 family.
   Label each precisely (supply points? INF vs ARM replacements? reinforcement
   rate?) from its consumer, and confirm whether ÷30 means a month.

7. **The minor orders** — Divide, Fortify, Report, Go To Port. Effects on the record:
   Divide (2×2 → two 1×1?), Fortify (dig-in / defensive bonus), Go To Port (supply /
   evacuation). **Hook:** order dispatch off the input loop; order codes in record +12.

8. **Malta status effect.** How Historical / Operation Herkules / Not-used-as-base
   modifies Axis supply. **Hook:** the menu var (set at option 77–80) applied in the
   supply calc.

9. **Scenario table** — the 25-byte entries at pointer 0xCB13 (index 0xCB12). Decode
   the fields: start date, Malta default, map window / scroll origin, victory
   thresholds, first-wave gating.

10. **Randomness.** Whether combat/AI use an RNG and where it lives (R register? a
    seeded LCG in RAM?). Determines whether outcomes are deterministic. **Hook:**
    scan the combat and AI paths for a random source.

---

## Tier 3 — fidelity & presentation

> **Status:** #14 the **AI is now mapped** (`engine-map.md` §15) — a budget-limited,
> deterministic, per-unit heuristic planner at 0xA39E that scans the flag map within a
> ±50-column band and issues Move/Assault/Retreat orders; open sub-questions are the
> offensive/defensive score thresholds and objective-target selection. The rest of
> Tier 3 (terrain-type names, tile/graphic tables, rendering, save/load) is
> comparatively mechanical.

11. **Terrain-type semantics** — name the other 14 low-nibble types (escarpment,
    road, town, port, salt-marsh, depression…). **Hook:** cross-reference the
    published map + the tile tables.

12. **Tile / graphic tables** — the five 256-entry accessors at
    0xD80E / 0xD90E / 0xDA0E / 0xDB0E / 0xDBAD, and the cell byte's **high nibble**
    graphic role. Needed for pixel-faithful tiles.

13. **Map & unit rendering** — the draw/scroll routines behind the 22×22 viewport
    (0x64xx family) and the unit-counter sprites, for an authentic display.

14. **The AI ("THINKING!")** — the computer-player logic for single-player games.
    **Hook:** dispatch vector 0x9C25, or a dedicated phase routine. Likely the single
    largest remaining subsystem.

15. **Save / load format** — the byte layout behind SAVE GAME / LOAD NEW GAME.

---

## Correction logged this pass

The tables at **0xDF84** (and 0xDF3C / 0xDFB6), previously tagged "per-side movement
cost", are **turn-phased campaign schedules**: index = `turn ÷ 30`, `+22` for the
second side, ×10-scaled, read by the 0x96E0 family (which pulls the turn counter
0xCB0F). Terrain movement cost is a **separate, still-open** lookup — now Tier 1 #1.

---

## Suggested order of attack

For a playable 1:1, Tier 1 in order (1 → 5) closes the rules. Tier 2 makes it
*complete*; Tier 3 makes it *look and feel* like the original. The single highest-
leverage next dig is **#2 (victory/objectives)** — without it the game has no end
condition — closely followed by **#1 (terrain cost)** and **#3 (reinforcements)**,
after which the recovered rules could be assembled into a self-contained engine and
regression-tested against the arena.
