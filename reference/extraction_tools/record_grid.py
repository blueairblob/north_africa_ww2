#!/usr/bin/env python3
"""
record_grid.py - reverse a fixed-stride record array (e.g. the Desert Rats
order-of-battle) by laying it out across one or more snapshots and classifying
each byte offset in the record.

Usage:
    python3 record_grid.py --base 0xBA5C --stride 30 [--count 40 | --end 0xBE2B] \
        snap1.szx [snap2.szx snap3.szx ...]

Each offset 0..stride-1 is classified as:
    DYN  - changes across the snapshots  -> dynamic state
           (position, strength, supply, morale, efficiency, order, flags...)
    UNIT - constant across snapshots but varies between records
           -> fixed per-unit attribute (type, side, division, max strength...)
    ----  - constant / zero everywhere -> padding or unused

Then it prints a grid of the records from the FIRST snapshot, with DYN columns
flagged, and a compact per-snapshot comparison of the DYN offsets so you can
read off which field is which.

Requires SkoolKit (pip install skoolkit).
"""
import argparse
from skoolkit.snapshot import get_snapshot, SnapshotError


def load(name):
    m = get_snapshot(name)
    if len(m) != 65536:
        raise SystemExit(f"ERROR: {name} decoded to {len(m)} bytes, not 64K "
                         f"(re-save as a 48K .szx).")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=lambda s: int(s, 0), required=True,
                    help="array start address, e.g. 0xBA5C")
    ap.add_argument("--stride", type=lambda s: int(s, 0), default=30,
                    help="record size in bytes (default 30)")
    ap.add_argument("--count", type=lambda s: int(s, 0), default=None,
                    help="number of records")
    ap.add_argument("--end", type=lambda s: int(s, 0), default=None,
                    help="array end address (alternative to --count)")
    ap.add_argument("--rows", type=lambda s: int(s, 0), default=24,
                    help="records to print in the grid (default 24)")
    ap.add_argument("snaps", nargs="+", help="one or more snapshot files")
    a = ap.parse_args()

    mems = [(n, load(n)) for n in a.snaps]
    base, stride = a.base, a.stride
    if a.end is not None:
        count = (a.end - base + stride) // stride
    elif a.count is not None:
        count = a.count
    else:
        count = 48

    # --- classify each offset ---
    dyn = [False] * stride
    unit = [False] * stride
    for o in range(stride):
        vals0 = set()
        for i in range(count):
            addr = base + i * stride + o
            b0 = mems[0][1][addr]
            vals0.add(b0)
            for _, m in mems[1:]:
                if m[addr] != b0:
                    dyn[o] = True
        if len(vals0) > 1:
            unit[o] = True

    def kind(o):
        return "DYN " if dyn[o] else ("UNIT" if unit[o] else "----")

    print(f"Array @ {base:#06x}  stride {stride}  records {count}  "
          f"snapshots {len(mems)}\n")

    print("Offset map:")
    for o in range(stride):
        bar = "#" * (3 if dyn[o] else (1 if unit[o] else 0))
        print(f"   +{o:02d} (0x{o:02X}) : {kind(o):4}  {bar}")
    dyn_offs = [o for o in range(stride) if dyn[o]]
    unit_offs = [o for o in range(stride) if unit[o]]
    print(f"\n  DYN  offsets (state):       {dyn_offs}")
    print(f"  UNIT offsets (fixed attr):  {unit_offs}\n")

    # --- grid dump from first snapshot ---
    hdr = "        " + " ".join(f"{o:02d}" for o in range(stride))
    flag = "        " + " ".join((" *" if dyn[o] else ("  " if not unit[o]
                                  else " u")) for o in range(stride))
    print("Grid (snapshot 1):  * = DYN offset, u = UNIT offset")
    print(hdr)
    print(flag)
    rows = min(a.rows, count)
    m0 = mems[0][1]
    for i in range(rows):
        addr = base + i * stride
        row = m0[addr:addr + stride]
        if not any(row):
            print(f"  {addr:04X}: (empty slot)")
            continue
        print(f"  {addr:04X}: " + " ".join(f"{b:02X}" for b in row))

    # --- per-snapshot comparison of DYN offsets, for non-empty records ---
    if len(mems) > 1 and dyn_offs:
        print("\nDYN-offset values per snapshot (first non-empty records):")
        print("  rec  off  " + "  ".join(f"{n[:14]:>14}" for n, _ in mems))
        shown = 0
        for i in range(count):
            addr = base + i * stride
            if not any(m0[addr:addr + stride]):
                continue
            for o in dyn_offs:
                vals = [m[addr + o] for _, m in mems]
                if len(set(vals)) > 1:
                    cells = "  ".join(f"{v:>14d}" for v in vals)
                    print(f"  {i:3}  +{o:02d}  {cells}")
            shown += 1
            if shown >= 6:
                break


if __name__ == "__main__":
    main()
