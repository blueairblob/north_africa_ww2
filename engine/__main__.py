"""Play a scenario between two scripted players with no screen.

    python -m engine crusader attack nothing
    python -m engine crusader attack nothing --seed 1941     with the weather drawn from this seed

The only input and output of the engine package is here.
"""
import json
import sys
from pathlib import Path

from . import checker, players, runner
from . import state as S
from . import weather as W
from .gamemap import GameMap

DATA = Path(__file__).parent.parent / "data"
PLAYERS = players.SCRIPTED


def main(argv):
    seed = 0
    if "--seed" in argv[:-1]:
        at = argv.index("--seed")
        seed, argv = int(argv[at + 1]), argv[:at] + argv[at + 2:]
    if len(argv) != 3 or argv[1] not in PLAYERS or argv[2] not in PLAYERS:
        sys.exit("usage: python -m engine <scenario> <axis player> <cw player> [--seed N]   "
                 f"players: {', '.join(PLAYERS)}")
    gmap = GameMap(json.loads((DATA / "map.json").read_text()))
    scenario = json.loads((DATA / "scenarios" / f"{argv[0]}.json").read_text())
    wrong = checker.problems(scenario, gmap)
    if wrong:
        sys.exit("\n".join(wrong))
    state, record = runner.play(scenario, gmap, {"axis": PLAYERS[argv[1]](gmap), "cw": PLAYERS[argv[2]](gmap)}, seed=seed)
    print(f"{scenario['name']}: {len(record)} turns, invariants held every turn")
    if seed:
        print(f"  weather from seed {seed}: " + ", ".join(
            f"{kind} in {sum(W.of(seed, t, scenario) == kind for t in range(1, len(record) + 1))} turns" for kind in W.KINDS))
    for side in S.SIDES:
        mine = [u for u in state["units"] if u["side"] == side]
        print(f"  {side:4} {state['sides'][side]['vp']:4} points, "
              f"{sum(u['status'] == 'on_map' for u in mine)} of {len(mine)} units on the map, "
              f"{sum(u['status'] == 'destroyed' for u in mine)} destroyed")
    result = state["result"]
    print("  a draw" if result["winner"] is None else f"  {result['winner']}: {result['grade']} victory")


main(sys.argv[1:])
