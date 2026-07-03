# Clean-Room Build Brief — Desert Rats (Python faithful clone)

## Your remit
Build a faithful, playable **Python 3** reimplementation of *Desert Rats* (CCS, 1985)
from the materials in this package. Work **only** from:
- `BUILD_SPEC.md` — the authoritative product/rules specification;
- `data/*` — extracted game data (order of battle, map, scenarios, strings, graphics);
- `reference/engine-map.md` — provenance/audit trail (read-only reference; you do not need
  it to implement, only to resolve ambiguity or during validation);
- `reference/prospects.md` — the open-items backlog;
- `reference/desert_rats_arena.html` — a partial reference implementation / mechanics
  sanity-check.

Do **not** consult, embed, decompile, or copy the original ZX Spectrum binary, ROM, or
machine code. This is a clean-room build: logic is reconstructed from the written
specification, not transcribed from the original program. The data files are factual game
data; keep the code independent of any original executable.

## What "faithful" means here (in priority order)
1. **Rules & data correctness** — movement, Travel, combat (efficiency attrition), supply
   tracing, ZOC, reinforcements, objective victory, the turn loop, and the six scenarios,
   using the constants in `BUILD_SPEC.md`.
2. **Determinism** — no randomness anywhere; identical inputs must produce identical
   state. This is non-negotiable and is what makes the clone verifiable.
3. **The AI** — the budget-limited heuristic planner (§6 of the spec).
4. **Visual identity** — the colour model (British blue / German black / Italian magenta
   over desert-yellow terrain), 2×2 counters, scrolling map, and the original UI strings.
   Pixel-exactness is *not* required for acceptance.

## Method
1. Read `BUILD_SPEC.md` end to end first.
2. Implement in the module order given in spec §11, headless and test-first.
3. Get a correct **2-player** game before adding the AI or rendering.
4. Where the spec marks a value **inferred/tunable** (§10), implement the simplest
   deterministic model and expose it as a named constant — do not invent randomness or
   elaborate mechanics to fill gaps.
5. Stand up the **diff harness** early (spec §12): it both tests the clone and pins the
   inferred constants against emulator traces.

## Deliverables expected of you
- A runnable Python package (layout per spec §11) that plays all six scenarios.
- A test suite, including the state-diff harness scaffold.
- A short `NOTES.md` recording every decision you made at an *inferred/tunable* point,
  with the constant's location in code, so later validation can adjust it.
- No dependency on the original binary at runtime.

## Acceptance
- Headless 2-player games run end-to-end on all six scenarios and reach a victory result.
- Given a scripted input sequence, state is reproducible run-to-run (determinism).
- Mechanics match the reference arena's behaviour on shared cases; where the emulator diff
  harness is available, turn-by-turn state matches the golden trace (positions/outcomes).

## Boundaries / non-goals (for this pass)
- Sound, pixel-exact tiles, and the exact UI panel geometry are optional polish, not
  acceptance criteria.
- The 128K-only features (e.g. Malta status) are out of scope unless data is provided.
