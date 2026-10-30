"""Compare all computer levels on identical weather seeds and both sides.

    .venv/bin/python scripts/compare_computers.py --seeds 0 1 65 1941 2026
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import checker, players, runner, scenarios  # noqa: E402
from engine.gamemap import GameMap  # noqa: E402

LEVELS = ("computer-easy", "computer", "computer-hard")


def main():
    parser = argparse.ArgumentParser(description="Run every computer level against every other level.")
    parser.add_argument("scenario", nargs="?", default="sidi_rezegh")
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 65, 1941, 2026])
    args = parser.parse_args()
    gmap = GameMap(json.loads((ROOT / "data" / "map.json").read_text()))
    scenario = scenarios.load(args.scenario)
    problems = checker.problems(scenario, gmap)
    if problems:
        parser.error("; ".join(problems))
    print(f"{scenario['name']} · {len(args.seeds)} shared weather seeds: {args.seeds}")
    print("Axis level       Commonwealth level   Axis wins  Draws  CW wins  Mean adjusted margin")
    for axis in LEVELS:
        for cw in LEVELS:
            wins = {"axis": 0, "cw": 0, None: 0}
            margins = []
            for seed in args.seeds:
                state, _ = runner.play(scenario, gmap,
                                       {"axis": players.SCRIPTED[axis](gmap),
                                        "cw": players.SCRIPTED[cw](gmap)}, seed=seed)
                result = state["result"]
                wins[result["winner"]] += 1
                margins.append(result["margin"])
            print(f"{axis:<16} {cw:<20} {wins['axis']:>5} {wins[None]:>6} {wins['cw']:>8} "
                  f"{sum(margins) / len(margins):>12.1f}")
    print("Positive margin favours Axis; negative favours Commonwealth. The grade also uses thresholds.")


if __name__ == "__main__":
    main()
