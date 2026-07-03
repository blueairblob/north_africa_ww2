#!/usr/bin/env python3
"""
diff_snapshots.py - find RAM regions that differ across ZX Spectrum snapshots.

Usage:
    python3 diff_snapshots.py [--all] [--gap N] snap1.z80 snap2.z80 [snap3.z80 ...]

Reads each snapshot's 48K RAM and reports contiguous address ranges where the
byte differs between ANY of the snapshots. Across per-scenario snapshots, the
differing RAM is the per-scenario data: the order-of-battle is the largest
structured block among the candidates.

By default, pixel/attribute (screen) and ROM system-variable areas are summarised
as noise and hidden, because the map view legitimately differs between scenarios.
Use --all to show them too.

Requires SkoolKit (pip install skoolkit) in the active environment.
"""
import sys
from skoolkit.snapshot import get_snapshot, SnapshotError

ROM_END     = 0x4000   # 16384  RAM starts here
DISPLAY_END = 0x5800   # 22528  end of pixel display file
ATTR_END    = 0x5B00   # 23296  end of attribute file
SYSVARS_END = 0x5CB6   # ~23734 end of ROM system variables / start of usable RAM


def region_tag(addr):
    if addr < DISPLAY_END:  return "SCREEN"   # 4000-57FF pixels  (noise: map view)
    if addr < ATTR_END:     return "ATTR"     # 5800-5AFF colour  (noise)
    if addr < SYSVARS_END:  return "SYSVAR"   # 5B00-5CB5 ROM area (noise)
    return "RAM"                              # >= 5CB6 game code/data (CANDIDATE)


def coalesce(addrs, gap):
    """Merge sorted addresses into (start, end) ranges.

    `gap` = number of identical bytes tolerated between two differing runs.
    gap=0 merges only adjacent differing bytes; gap=8 bridges runs separated
    by up to 8 unchanged bytes (e.g. struct fields that happen to match).
    """
    if not addrs:
        return []
    ranges = []
    start = prev = addrs[0]
    for a in addrs[1:]:
        if a - prev <= gap + 1:
            prev = a
        else:
            ranges.append((start, prev))
            start = prev = a
    ranges.append((start, prev))
    return ranges


def main(argv):
    show_all = False
    gap = 8
    files = []
    it = iter(argv)
    for a in it:
        if a == "--all":
            show_all = True
        elif a == "--gap":
            gap = int(next(it))
        else:
            files.append(a)

    if len(files) < 2:
        print(__doc__)
        return 1

    mems = []
    for n in files:
        try:
            m = get_snapshot(n)
        except SnapshotError as e:
            print(f"ERROR reading {n}: {e}")
            print("  SkoolKit could not decode this snapshot. If Fuse wrote it as .z80,")
            print("  re-save it as .szx instead (File > Save Snapshot, name it *.szx),")
            print("  with the Machine set to Spectrum 48K.")
            return 2
        if len(m) != 65536:
            print(f"ERROR: {n} decoded to {len(m)} bytes, not 64K - looks like a 128K")
            print("  snapshot. Re-save it as a 48K .szx, or extend this script with page=.")
            return 2
        mems.append(m)
        print(f"loaded {n}  ({len(m)} bytes)")
    print()

    base = mems[0]
    diffs = [addr for addr in range(ROM_END, 0x10000)
             if any(m[addr] != base[addr] for m in mems[1:])]

    if not diffs:
        print("No RAM differences between snapshots.")
        return 0

    ranges = coalesce(diffs, gap)

    candidates = [(s, e) for (s, e) in ranges if region_tag(s) == "RAM"]
    noise      = [(s, e) for (s, e) in ranges if region_tag(s) != "RAM"]

    def emit(rngs):
        print(f"  {'range (hex)':<13} {'range (dec)':<15} {'len':>6}  tag     bytes at start")
        print("  " + "-" * 70)
        for s, e in rngs:
            length = e - s + 1
            vals = " ".join(f"{m[s]:02X}" for m in mems)
            print(f"  {s:04X}-{e:04X}    {s:5d}-{e:<5d}   {length:5d}  {region_tag(s):<6}  {vals}")

    print(f"CANDIDATE game-data regions (differ across snapshots, gap<= {gap}):")
    print(f"  {len(candidates)} ranges, "
          f"{sum(e - s + 1 for s, e in candidates)} bytes total\n")
    emit(sorted(candidates))

    print("\nLargest candidates (likely tables - OOB / scenario state):")
    for s, e in sorted(candidates, key=lambda r: r[1] - r[0], reverse=True)[:8]:
        print(f"  {s:04X}-{e:04X}  ({e - s + 1} bytes)")

    nbytes = sum(e - s + 1 for s, e in noise)
    print(f"\nScreen/ROM noise hidden: {len(noise)} ranges, {nbytes} bytes "
          f"(use --all to show).")
    if show_all and noise:
        print()
        emit(sorted(noise))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
