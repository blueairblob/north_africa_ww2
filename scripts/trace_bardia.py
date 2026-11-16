"""Trace the linked Compass and Bardia research chapters for balance diagnosis."""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import campaign, computer, state as S, turn, view  # noqa: E402
from engine.gamemap import GameMap  # noqa: E402

CHAPTERS = ("compass_opening", "compass_interval", "bardia_assault")
WATCH = (306, 330, 331, 332, 333, 334)


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
        print(f"\n{scenario['id']}")
        for n in range(scenario["turns"]):
            day = date.fromisoformat(scenario["start"]) + timedelta(days=n)
            state = turn.begin_turn(state, gmap, scenario)
            submissions = {side: players[side].orders(view.view(state, gmap, scenario, side))
                           for side in S.SIDES}
            orders = {o["unit"]: o for o in submissions["cw"]["orders"]}
            print(day, "Bardia", state["places"]["Bardia"], "Sollum", state["places"]["Sollum"],
                  "stock", state["ports"].get("Sollum"))
            for uid in WATCH:
                u = S.unit(state, uid)
                if u and u["status"] == "on_map":
                    o = orders.get(uid, {})
                    print(f" {uid} {u['hex']} g{u['group']} {u['steps']}/{u['max']} co{u['cohesion']} ce{u['ceiling']}"
                          f" {'T' if u['traced'] else '-'} st{u['stores']} {'OOS' if u['out_of_stores'] else ''}"
                          f" {o.get('order', 'group')} {o.get('to', '')}")
            state, replies = turn.finish_turn(state, gmap, scenario, submissions)
            for event in state["log"]:
                if event["event"] == "battle":
                    print(" battle", event["hex"], event["attackers"], "vs", event["defenders"],
                          "att/def", event["att"], event["def"], "coh", event["cla"], event["cld"],
                          "retreated", event["retreated"])
                elif scenario["id"] == "bardia_assault" and event["event"] in ("no attack", "stopped"):
                    print(" ", event)
        print("result", state["result"]["winner"], state["result"]["grade"])


if __name__ == "__main__":
    main()
