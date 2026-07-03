#!/usr/bin/env python3
"""
extract_oob.py - extract the Desert Rats order-of-battle from snapshots to JSON.

Two 30-byte unit-record arrays, one per side (confirmed via the in-game Report
for the British 2nd Armoured Division, which lives in Array B):
    Array A @ 0xBA5C  = AXIS
    Array B @ 0xC074  = BRITISH

Decoded 30-byte record (* = confirmed against the Report screen):
    +00 x*           +08 supply*        +16 efficiency*     +24 id*
    +01 y*           +09 morale*        +23 0x90 marker*    +25 order~
    +02 mps*         +26 type*          +27 division~       +28 strength~
    +06 dest_x*      +07 dest_y*        +29 raw       (rest kept in raw_hex)

Confirmed by report (British 2nd Armoured): MPS=+02, SUP=+08 (raw 32 shown as
"FAIR"), MOR=+09, EFF=+16. Strength (+28) is the per-unit relative value; the
Report's STR is a scaled divisional aggregate. Division (+27) and order (+25)
are still being firmed up.

Usage:
    python3 extract_oob.py scenario_enter_rommel.szx [more.szx ...] [--outdir .]
"""
import argparse, json, os
from skoolkit.snapshot import get_snapshot

STRIDE = 30
ARRAYS = [("A", 0xBA5C, 33), ("B", 0xC074, 43)]  # (side, base, max_records)


ARMY = {"A": "Axis", "B": "British"}


def parse_unit(r, side, slot, addr):
    return {
        "id": r[24],
        "side": side,
        "army": ARMY[side],
        "type": r[26],
        "division": r[27],       # tentative
        "x": r[0], "y": r[1],
        "dest_x": r[6], "dest_y": r[7],
        "on_map": bool(r[0] or r[1]),
        "moving": (r[0], r[1]) != (r[6], r[7]),
        "mps": r[2],             # confirmed
        "strength": r[28],       # relative (display is a scaled aggregate)
        "supply": r[8],          # confirmed (band: ~32 -> "FAIR")
        "morale": r[9],          # confirmed
        "efficiency": r[16],     # confirmed
        "order": r[25],          # tentative
        "slot": slot,
        "addr": f"0x{addr:04X}",
        "raw_hex": bytes(r).hex(),
    }


def extract(mem):
    units = []
    for side, base, n in ARRAYS:
        for i in range(n):
            a = base + i * STRIDE
            r = mem[a:a + STRIDE]
            if not any(r):
                continue
            if r[23] != 0x90:        # require the record marker => real slot
                continue
            units.append(parse_unit(r, side, i, a))
    return units


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snaps", nargs="+")
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    for n in a.snaps:
        mem = get_snapshot(n)
        units = extract(mem)
        stem = os.path.splitext(os.path.basename(n))[0]
        out = os.path.join(a.outdir, f"units_{stem}.json")
        with open(out, "w") as f:
            json.dump(units, f, indent=2)

        a_units = [u for u in units if u["side"] == "A"]
        b_units = [u for u in units if u["side"] == "B"]
        a_map = sum(u["on_map"] for u in a_units)
        b_map = sum(u["on_map"] for u in b_units)
        print(f"{stem}: {len(units)} units  "
              f"(A: {len(a_units)} present / {a_map} on-map, "
              f"B: {len(b_units)} present / {b_map} on-map)  -> {out}")


if __name__ == "__main__":
    main()
