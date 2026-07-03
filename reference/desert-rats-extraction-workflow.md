# Desert Rats — OOB & Map Table Extraction Workflow

Goal: locate and dump the **order-of-battle** (per-scenario unit rosters) and the **terrain map**
from the 48K *Desert Rats* image, as clean data files (JSON/CSV/PNG) you can feed into a modern
reimplementation.

This is a **targeted data-extraction** job, not a full disassembly. You only need to understand
two data structures and the handful of routines that touch them. Everything below is organised
around that.

---

## Tools

| Tool | Role | Source |
|---|---|---|
| **SkoolKit** (Python 3.10+, v9.6/10.x) | `tap2sna.py` (tape→snapshot), `sna2ctl.py` (code/data split), `sna2skool.py` (disassembly), `trace.py`/`rzxplay.py` (execution maps, 48K+128K) | skoolkit.ca · pypi.org/project/skoolkit |
| **Fuse** | Emulator + **Profiler** (Machine ▸ Profiler) to produce a code-execution map; debugger with memory breakpoints | sourceforge / fuse-emulator |
| **Spectrum Analyser** | Emulator + interactive disassembler: format memory as Byte/Word/Char-Map/Bitmap, breakpoints on code/memory/IN/OUT, value search | colourclash.co.uk/spectrum-analyser · github.com/dpt/8BitAnalysers |
| Python + a few lines of NumPy/PIL | Render candidate blocks as grids/images; emit final JSON/CSV | — |

> Optional heavyweight: Ghidra (community Z80 processor module) or IDA Pro, if you prefer a
> graph-view disassembler over SkoolKit's skool-file workflow. Not required for data extraction.

48K vs 128K: **start with the 48K image** — it's a single flat address space (0x4000–0xFFFF),
no RAM paging. The 128K version pages extra banks at 0xC000 and may hold the two added scenarios
in other banks; tackle it only after the 48K extraction works.

---

## Phase 0 — Get the right snapshot (most important step)

A tape game unpacks itself, and this engine almost certainly stores each scenario's OOB
**packed**, expanding it into a working array only when that scenario starts. So a snapshot of
the freshly-loaded main menu will NOT contain an instantiated roster.

1. Get the original `.tzx`/`.tap` (archive.org, World of Spectrum, Spectrum Computing).
2. Convert and/or capture snapshots:
   ```
   tap2sna.py "Desert Rats.tzx" desertrats_loaded.z80
   ```
   If the loader is non-standard and `tap2sna.py` chokes, load in Fuse instead and save a
   snapshot manually.
3. **Capture multiple snapshots at distinct moments** (load each in Fuse, play to the point, save):
   - `00_menu.z80` — main menu, just loaded
   - `s3_t1.z80` — scenario 3 (Enter Rommel) at turn 1, units placed
   - `s5_t1.z80` — scenario 5 (Crusader) at turn 1
   - one more mid-combat snapshot (units at reduced strength) for the combat-field crib later
4. **Diff** the per-scenario turn-1 snapshots. The regions that change between scenarios but are
   stable within a scenario are your OOB working-array candidates. The regions identical across
   all scenarios are engine/map candidates.

---

## Phase 1 — Static triage: separate code from data

Build a code-execution map first; it makes the code/data split far more reliable.

1. In **Fuse**: Machine ▸ Profiler ▸ Start. Then *exercise everything* — select each scenario,
   scroll the whole map, move units, fortify, force combats, trigger retreats, open every report
   screen. The more code paths you hit, the better. Stop the profiler; save `desertrats.map`.
   (Alternatively use SkoolKit's `trace.py` or `rzxplay.py` on a recorded RZX to produce the map.)
2. Generate a control file using the map:
   ```
   sna2ctl.py -m desertrats.map desertrats_loaded.z80 > desertrats.ctl
   sna2skool.py -c desertrats.ctl desertrats_loaded.z80 > desertrats.skool
   ```
3. Skim the `.ctl`/`.skool` for **large contiguous DATA blocks that were never executed**. These
   are your prime candidates for the map array and the OOB/setup tables. Note their address ranges.

---

## Phase 2 — Find the MAP via the render anchor (don't hunt blindly)

Let the draw routine point you at the data.

1. In **Spectrum Analyser** (or Fuse's debugger), set a **breakpoint on memory reads** that fire
   while the map window redraws — easiest trigger: scroll the map one column and watch what runs.
   You're looking for a routine that reads a region **sequentially/linearly** and writes tiles to
   screen memory (0x4000–0x57FF). The region it reads across is the **terrain array**.
2. Confirm the structure of that region:
   - It should be a `width × height` grid of small byte values. There are ~11–12 terrain types
     (sea, salt marsh, escarpment, steep escarpment, rough, ridge, fortification, fort, road,
     track, town, port), so expect a **small distinct value-set** — possibly nibble-packed
     (two cells per byte). Count distinct values in the block to sanity-check.
   - Look for a stride: each map row is `width` bytes; the draw routine's inner/outer loop counts
     reveal `width` and `height`.
3. Dump the block and **render it** as a colored grid:
   ```python
   import numpy as np
   from PIL import Image
   raw = open("map_block.bin","rb").read()
   W, H = 0, 0          # fill in from the loop counts you observed
   grid = np.frombuffer(raw[:W*H], dtype=np.uint8).reshape(H, W)
   # map each terrain code to an RGB colour, then upscale and save
   Image.fromarray(colourise(grid)).resize((W*8, H*8), Image.NEAREST).save("map.png")
   ```
   Eyeball `map.png` against the in-game map and the booklet's "North African Theatre" map. When
   the coastline, the Tobruk–Benghazi–El Agheila road, and the escarpment lines match, the block
   and your `(W, H)` are correct.
4. Build the **terrain legend** by correlating byte values with appearance: place known features
   under the cursor in-game, or note which code the draw routine maps to the road/town/port tile.

> Note: roads, tracks, ports and towns may live in the **same** array as terrain, or in a parallel
> overlay array (the supply tracer needs road/track/port topology, so it's read by a *second*
> routine — breakpoint on the supply check to find it if it's separate).

---

## Phase 3 — Find the OOB via known-value cribs

Unit records are almost certainly **fixed-size structs in a contiguous table**. Find one record,
learn the stride, and the whole table falls out.

### Crib A — coordinate search (fast, reliable)
1. In a scenario snapshot, pick a unit whose map square you can read off screen → get `(x, y)`.
2. Search the working-array region (from the Phase-0 diff) for the byte pair `x, y` appearing
   close together. Each hit is a candidate unit record.
3. Move that unit one square, re-snapshot, search again: the record whose `(x,y)` changed by
   exactly your move is the real one. Its address is your anchor.
4. The constant **gap between consecutive records** is the struct stride. Walk the table at that
   stride; the run ends where the records stop looking unit-shaped → that's the roster length
   (cross-check against the scenario's unit count).

### Crib B — changed-value search for the field offsets
1. From the mid-combat snapshot pair, take a unit whose **strength** dropped from N to N−k.
2. Use the emulator's "search for changed value" (POKE-finder style) to find the byte that went
   N → N−k inside that unit's record. That pins the **STR field offset** within the struct.
3. Repeat to locate other fields by causing isolated changes: order it to Hold and watch the
   **order/flags** byte; let efficiency drop in combat for **EFF**; deplete supply for **SUP**;
   etc. Map every field offset against the stat model (type, size, side, division, STR, MPS, MOR,
   atkMod, EFF, SUP, x, y, order/flags).

### Crib C — manual cross-checks
Use documented numbers to validate, not just to search:
- Per-scenario unit *counts* must match the roster length you found.
- The Gazala equipment table (Allied 424 medium / 425 light tanks; Axis 282/228/50; etc.) and the
  El Alamein 2:1 ratio give order-of-magnitude checks on aggregate strengths.
- Side/type distributions should match the historical orders of battle in the booklet.

### Per-scenario rosters
Because 8 scenarios share one engine, expect **8 packed setup tables** in the loaded image plus a
**table of 8 pointers** near the scenario-select routine. Two ways to get all eight:
- **Dynamic:** snapshot each scenario at turn 1 (Phase 0) and dump the working array each time.
- **Static:** find the 8-entry pointer table (often right before/after the scenario menu code),
  follow each pointer to its packed setup block, and find the unpacker (the routine that runs once
  at scenario start) to learn the packing scheme.

---

## Phase 4 — Decode and dump to data files

Once stride + field offsets (OOB) and `(W, H)` + legend (map) are known, write a small reader that
walks the snapshot bytes and emits clean data:

```python
# OOB → units.json
recs = []
addr = OOB_START
while addr < OOB_END:
    r = mem[addr:addr+STRIDE]
    recs.append({
        "side":  SIDE[r[OFF_SIDE]],
        "type":  TYPE[r[OFF_TYPE]],
        "size":  SIZE[r[OFF_SIZE]],
        "div":   r[OFF_DIV],
        "str":   r[OFF_STR],
        "x":     r[OFF_X], "y": r[OFF_Y],
        "order": ORDER[r[OFF_ORDER]],
        # mps, mor, atkMod, eff, sup ...
    })
    addr += STRIDE
json.dump(recs, open("units.json","w"), indent=2)
```

```python
# map → terrain.json (+ map.png from Phase 2)
terrain = [[ legend[ mem[MAP_START + y*W + x] ] for x in range(W)] for y in range(H)]
json.dump({"w": W, "h": H, "terrain": terrain}, open("terrain.json","w"))
```

Produce one `units.json` per scenario, one shared `terrain.json`, plus the road/track/port overlay.

---

## Phase 5 — Validate

- Re-render `terrain.json` and overlay each scenario's `units.json`; compare side-by-side with the
  live emulator at turn 1. Positions and counts should match exactly.
- Replay a couple of turns in your own engine vs. the original and check that supply reachability
  (the colinear road-trace to the board edge) lights up the same units. This simultaneously
  validates the map's road topology and the OOB positions.
- Discrepancies usually mean a wrong stride, a nibble-packed field you read as a whole byte, or an
  overlay array you missed.

---

## Order of attack (suggested)

1. Phase 0 snapshots (menu + per-scenario turn-1 + mid-combat).
2. Phase 2 map first — it's the easier, more visual win and gives you a confidence boost plus the
   coordinate system the OOB uses.
3. Phase 3 OOB using the coordinates you now understand.
4. Decode, dump, validate.
5. Only then, if you want the *rules constants* too (combat formula, supply costs, AI), return to
   the `.skool` disassembly from Phase 1 and work outward from the routines your breakpoints
   already identified — the map-draw, supply-check, and combat-resolve routines are now known
   entry points.

---

## Practical gotchas

- **Snapshot timing** (Phase 0) is the #1 cause of "the data isn't there" — capture after scenario
  setup, not at the menu.
- **Packing/RLE:** if a candidate block reads as noise but is accessed as data, it's packed. Find
  the unpacker (runs once), snapshot *after* it, work on the expanded form.
- **Nibble packing:** terrain and some unit fields may be 4-bit. If distinct-value counts look
  doubled or values look interleaved, try reading high/low nibbles separately.
- **Two arrays for the map:** terrain vs. road/supply overlay may be separate — the supply tracer
  reads the one you care about for line-of-supply.
- **Custom loader:** if `tap2sna.py` fails, go through Fuse and save a `.z80`/`.szx` snapshot;
  Spectrum Analyser also wants `.z80`/`.sna`, not `.tzx`.
