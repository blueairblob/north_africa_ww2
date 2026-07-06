"""Oracle diff-harness: execute the ORIGINAL game's routines under CPU
emulation and sweep them as ground-truth oracles against the Python
engine.

Requires: pip install z80 (a Z80 CPU emulator with a Python API) and the
person's own tape image. No ZX ROM is needed: the ROM area is filled
with RET opcodes (any ROM call returns immediately) and the target
routines are self-contained computation.

Technique: load the 64K memory reconstructed from the tape; zero the
128x30-byte runtime unit-record region; craft a record at slot 1; push a
sentinel return address onto a scratch stack; point PC at the routine;
run to the sentinel; diff registers and the record.

Run:  python3 reference/diff_harness/harness.py /path/to/tape.tzx
Writes results/*.json (facts for BUILD_SPEC/NOTES; see the probes below
for what each pins).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "extraction_tools"))
from extract_render_tables import load_tzx_memory

import z80

HERE = Path(__file__).resolve().parent
SENTINEL, STACK = 0x3F00, 0x5F00
REC = 0xBA3A + 30          # runtime record slot 1
RECORDS = (0xBA3A, 0xBA3A + 128 * 30)

ROUTINES = {
    "recovery": 0x8632,
    "supply": 0x8648,
    "resolver": 0x7A03,
    "resolver_gate": 0x79F1,
    "class_derive": 0x643F,
}


class Oracle:
    def __init__(self, tape_path):
        mem = bytearray(load_tzx_memory(tape_path))
        mem[0:0x4000] = b"\xC9" * 0x4000
        mem[RECORDS[0]:RECORDS[1]] = bytes(RECORDS[1] - RECORDS[0])
        self.base = bytes(mem)

    def machine(self):
        m = z80.Z80Machine()
        m.set_memory_block(0, self.base)
        return m

    @staticmethod
    def call(m, addr, max_ticks=3_000_000):
        m.sp = STACK - 2
        m.memory[STACK - 2] = SENTINEL & 0xFF
        m.memory[STACK - 1] = SENTINEL >> 8
        m.pc = addr
        m.set_breakpoint(SENTINEL)
        t = 0
        while m.pc != SENTINEL and t < max_ticks:
            m.ticks_to_stop = 100_000
            m.run()
            t += 100_000
        return m.pc == SENTINEL

    def unit(self, m, *, klass=12, strength=100, pressure=0, x=50, y=25,
             flags9=0, morale=50, order=1, eff=90, nat=2, derived=0):
        r = m.memory
        r[REC + 1] = klass
        r[REC + 2] = strength
        r[REC + 3] = pressure
        r[REC + 4] = x
        r[REC + 5] = y
        r[REC + 7] = 0x04            # on-map
        r[REC + 9] = flags9
        r[REC + 13] = morale
        r[REC + 0x10] = order
        r[REC + 0x14] = eff
        r[REC + 0x15] = nat
        r[REC + 0x1B] = derived
        m.ix = REC

    def record_diff(self, m, before):
        after = bytes(m.memory[REC:REC + 30])
        return {i: (before[i], after[i]) for i in range(30) if before[i] != after[i]}

    def snapshot(self, m):
        return bytes(m.memory[REC:REC + 30])


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    o = Oracle(sys.argv[1])
    out = {}

    # --- recovery: eff += (100-eff)>>4 + 1 (cap 100)
    rec = []
    for eff in range(0, 101):
        m = o.machine()
        m.memory[REC + 0x14] = eff
        m.ix = REC
        o.call(m, ROUTINES["recovery"])
        rec.append(m.memory[REC + 0x14])
    out["recovery"] = rec

    # --- supply: HL_out = HL_in * band / 100; band = 100 if
    #     min(d+2,127)>>2 == 0 else curve[that-1]
    sup = {}
    for d in list(range(0, 24)) + [30, 60, 100, 122, 127, 200]:
        m = o.machine()
        m.memory[REC + 8] = min(d, 255)
        m.memory[REC + 9] = 0x01
        m.ix = REC
        m.hl = 100
        o.call(m, ROUTINES["supply"])
        sup[d] = m.hl
    out["supply_percent_by_distance_hl100"] = sup

    # --- class -> derived flags byte (the +0x1B gate source)
    cd = {}
    for klass in range(0, 16):
        m = o.machine()
        m.a = klass
        o.call(m, ROUTINES["class_derive"])
        cd[klass] = m.a
    out["class_derived_byte"] = cd

    # --- resolver behaviour matrix
    res = []
    for morale, klass in [(50, 12), (50, 10), (10, 12)]:
        for p in (0, 10, 19, 20, 21, 49, 50, 51):
            m = o.machine()
            o.unit(m, klass=klass, morale=morale, pressure=p)
            before = o.snapshot(m)
            o.call(m, ROUTINES["resolver"])
            res.append({"morale": morale, "class": klass, "pressure": p,
                        "diff": {str(k): v for k, v in o.record_diff(m, before).items()}})
    out["resolver_matrix"] = res

    # --- destroy-at-strength via the gate entry
    dst = []
    for p in (99, 100, 150, 255):
        m = o.machine()
        o.unit(m, pressure=p, strength=100, morale=10)
        before = o.snapshot(m)
        o.call(m, ROUTINES["resolver_gate"])
        dst.append({"pressure": p,
                    "diff": {str(k): v for k, v in o.record_diff(m, before).items()}})
    out["gate_matrix"] = dst

    results = HERE / "results"
    results.mkdir(exist_ok=True)
    (results / "oracle_results.json").write_text(json.dumps(out, indent=1))
    print(f"wrote {results/'oracle_results.json'}")


if __name__ == "__main__":
    main()
