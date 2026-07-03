#!/usr/bin/env python3
"""
find_unit.py - locate unit record(s) by map position and print every field.

Workflow to label the stat bytes for certain:
  1. In Fuse, put the cursor on a unit and press R to read its Report
     (STR / MPS / SUP / MOR / A/M / EFF / FRT) and note its map square.
  2. Run this with that --xy; it prints all 30 offsets in decimal so you can
     see which offset holds each reported number.

Usage:
    python3 find_unit.py --bases 0xBA5C,0xC074 --stride 30 --count 60 \
        --xy 14,24 scenario_enter_rommel.szx

If nothing matches, the on-screen cursor coordinates may be offset from the
stored ones by a map origin; try --xoff/--yoff or nearby X,Y values.
"""
import argparse
from skoolkit.snapshot import get_snapshot, SnapshotError

TYPE_GUESS = {}  # fill in once +26 type codes are known


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bases", required=True,
                    help="comma-separated array base addresses, e.g. 0xBA5C,0xC074")
    ap.add_argument("--stride", type=lambda s: int(s, 0), default=30)
    ap.add_argument("--count", type=lambda s: int(s, 0), default=60)
    ap.add_argument("--xy", required=True, help="X,Y to match (e.g. 14,24)")
    ap.add_argument("--xoff", type=lambda s: int(s, 0), default=0,
                    help="offset of the X byte in the record (default 0)")
    ap.add_argument("--yoff", type=lambda s: int(s, 0), default=1,
                    help="offset of the Y byte in the record (default 1)")
    ap.add_argument("snap")
    a = ap.parse_args()

    try:
        m = get_snapshot(a.snap)
    except SnapshotError as e:
        raise SystemExit(f"ERROR reading {a.snap}: {e}")
    if len(m) != 65536:
        raise SystemExit(f"ERROR: {a.snap} is not a 48K snapshot ({len(m)} bytes).")

    bases = [int(b, 0) for b in a.bases.split(",")]
    X, Y = (int(v) for v in a.xy.split(","))
    stride = a.stride
    found = 0

    for bi, base in enumerate(bases):
        side = chr(ord("A") + bi)
        for i in range(a.count):
            addr = base + i * stride
            row = m[addr:addr + stride]
            if row[a.xoff] == X and row[a.yoff] == Y:
                found += 1
                uid = row[24] if stride > 24 else "?"
                print(f"array {side}  record {i}  @ {addr:04X}  id={uid}")
                for o in range(stride):
                    b = row[o]
                    print(f"  +{o:02d} (0x{o:02X}) : {b:3d}  0x{b:02X}")
                print()

    if not found:
        print(f"No record with +{a.xoff}={X}, +{a.yoff}={Y}.")
        print("The cursor coords may differ from stored coords by a map origin -")
        print("try nearby X,Y, or swap with --xoff/--yoff if X/Y are reversed.")


if __name__ == "__main__":
    main()
