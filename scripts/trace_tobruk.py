"""Trace the linked Tobruk research assault without resetting the played approach."""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import campaign, computer, runner, state as S, turn, view  # noqa: E402
from engine.gamemap import GameMap, distance  # noqa: E402

CHAPTERS = ("compass_opening", "compass_interval", "bardia_assault",
            "tobruk_approach", "tobruk_assault")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1940)
    args = parser.parse_args()
    gmap = GameMap(json.loads((ROOT / "data/map.json").read_text()))
    chapters = [json.loads((ROOT / "data/scenario_drafts" / f"{name}.json").read_text())
                for name in CHAPTERS]
    players = {side: computer.ComputerHard(gmap) for side in S.SIDES}
    state = campaign.start(chapters[0], gmap, seed=args.seed)
    for index, scenario in enumerate(chapters):
        if index:
            state = campaign.handoff(state, chapters[index - 1], scenario, gmap)
        if index < len(chapters) - 1:
            state, _ = runner.play(scenario, gmap, players, initial_state=state, check=False)
            print(scenario["id"], "Bardia", state["places"]["Bardia"],
                  "Tobruk", state["places"]["Tobruk"])
            continue
        for n in range(scenario["turns"]):
            day = date.fromisoformat(scenario["start"]) + timedelta(days=n)
            state = turn.begin_turn(state, gmap, scenario)
            submissions = {side: players[side].orders(view.view(state, gmap, scenario, side))
                           for side in S.SIDES}
            print(day, "Tobruk", state["places"]["Tobruk"], "works", state.get("perimeters"),
                  "prep", state.get("perimeter_prep"))
            for u in S.on_map(state, "cw"):
                if distance(tuple(u["hex"]), (56, 12)) <= 5:
                    order = next((o for o in submissions["cw"]["orders"] if o["unit"] == u["id"]), {})
                    print(" ", u["id"], u["type"], u["hex"], "stores", u["stores"],
                          "cohesion", u["cohesion"], order.get("order", "group"), order.get("to", ""))
            state, _ = turn.finish_turn(state, gmap, scenario, submissions)
            for event in state["log"]:
                if event["event"] in ("perimeter prepared", "perimeter breach", "battle", "captured"):
                    print(" ", event)
        print("result", state["result"]["winner"], state["result"]["grade"])


if __name__ == "__main__":
    main()
