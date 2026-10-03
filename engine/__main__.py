"""Play a scenario between two scripted players with no screen.

    python -m engine crusader attack nothing

The only input and output of the engine package is here.
"""
import json
import sys
from pathlib import Path

from . import checker, players, runner
from . import state as S
from .gamemap import GameMap

DATA = Path(__file__).parent.parent / "data"
PLAYERS = {"nothing": players.DoNothing, "attack": players.AlwaysAttack,
           "retreat": players.AlwaysRetreat, "explore": players.Explore}


def main(argv):
    if len(argv) != 3 or argv[1] not in PLAYERS or argv[2] not in PLAYERS:
        sys.exit(f"usage: python -m engine <scenario> <axis player> <cw player>   players: {', '.join(PLAYERS)}")
    gmap = GameMap(json.loads((DATA / "map.json").read_text()))
    scenario = json.loads((DATA / "scenarios" / f"{argv[0]}.json").read_text())
    wrong = checker.problems(scenario, gmap)
    if wrong:
        sys.exit("\n".join(wrong))
    state, record = runner.play(scenario, gmap, {"axis": PLAYERS[argv[1]](gmap), "cw": PLAYERS[argv[2]](gmap)})
    print(f"{scenario['name']}: {len(record)} turns, invariants held every turn")
    for side in S.SIDES:
        mine = [u for u in state["units"] if u["side"] == side]
        print(f"  {side:4} {state['sides'][side]['vp']:4} points, "
              f"{sum(u['status'] == 'on_map' for u in mine)} of {len(mine)} units on the map, "
              f"{sum(u['status'] == 'destroyed' for u in mine)} destroyed")
    result = state["result"]
    print("  a draw" if result["winner"] is None else f"  {result['winner']}: {result['grade']} victory")


main(sys.argv[1:])
