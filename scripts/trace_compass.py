"""Reproduce the research draft's opening turns without adding it to the game menu."""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import computer, players, runner, state as S  # noqa: E402
from engine.gamemap import GameMap  # noqa: E402

PLACES = ("Nibeiwa", "Sidi Barrani", "Maktila", "Buq Buq", "Sofafi")
FORMATION_IDS = (120, 130, 140, 303, 304, 305, 306, 311, 312, 313, 314)
ACTORS = {"passive": players.DoNothing, "standard": computer.ComputerOpponent,
          "hard": computer.ComputerHard}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--axis", choices=ACTORS, default="hard")
    parser.add_argument("--cw", choices=ACTORS, default="hard")
    parser.add_argument("--seed", type=int, default=1940)
    parser.add_argument("--turns", type=int, default=3)
    args = parser.parse_args()
    sc = json.loads((ROOT / "data/scenario_drafts/compass_opening.json").read_text(encoding="utf-8"))
    gmap = GameMap(json.loads((ROOT / "data/map.json").read_text(encoding="utf-8")))
    if not 1 <= args.turns <= sc["turns"]:
        parser.error(f"turns must be between 1 and {sc['turns']}")
    print(f"Compass draft; Axis {args.axis}, Commonwealth {args.cw}; seed {args.seed}")
    for n in range(1, args.turns + 1):
        state, record = runner.play(sc, gmap, {"axis": ACTORS[args.axis](gmap),
                                                "cw": ACTORS[args.cw](gmap)}, turns=n, seed=args.seed)
        day = date.fromisoformat(sc["start"]) + timedelta(days=n - 1)
        held = ", ".join(f"{name}: {state['places'][name]}" for name in PLACES)
        print(f"\n{day}: {held}")
        for uid in FORMATION_IDS:
            u = S.unit(state, uid)
            side = u["side"]
            order = next((o for o in record[-1][side]["orders"] if o["unit"] == uid), None)
            action = order["order"] + (f" to {order['to']}" if "to" in order else "") if order else "group order"
            print(f"  {uid} {u['name']}: {u['status']} at {u['hex']}, {u['steps']} steps; {action}")
        for event in state["log"]:
            if event["event"] == "battle":
                print(f"  Battle at {event['hex']}: {event['attackers']} attacked {event['defenders']}")


if __name__ == "__main__":
    main()
