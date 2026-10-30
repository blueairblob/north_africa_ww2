"""Paired AI comparison on identical scenarios, opponents and weather seeds.

The game state is inspected only by this offline harness; players receive their
ordinary side views. Positive paired margin means the candidate did better.
"""
import argparse
import json
from pathlib import Path
import random
import statistics
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import invariants, players, scenarios, state as S  # noqa: E402
from engine.computer import ComputerHardBaseline, ComputerHardBeforeFlank, ComputerHardTactical, ComputerHardUnrestrictedFlank  # noqa: E402
from engine.gamemap import GameMap  # noqa: E402
from engine.turn import begin_turn, finish_turn  # noqa: E402
from engine.view import leaks, view  # noqa: E402


OPPONENTS = {"easy": players.ComputerEasy, "standard": players.ComputerOpponent,
             "hard": ComputerHardBaseline, "passive": players.DoNothing}
POLICIES = {"hard": players.ComputerHard, "tactical": ComputerHardTactical,
            "baseline": ComputerHardBaseline, "unrestricted": ComputerHardUnrestrictedFlank,
            "pre-flank": ComputerHardBeforeFlank}


def play(scenario, gmap, side, policy, opponent, seed):
    """One audited match; the metrics use full state only after orders are chosen."""
    bots = {side: policy(gmap), S.enemy(side): opponent(gmap)}
    state = S.new_game(scenario, gmap, seed)
    shortages = untraced = invalid = turns = 0
    hq_dump_lost = objective_turn_vp = 0
    flank_goals, captured_flank_goals = set(), set()
    cpu = 0.0
    while not state["over"]:
        state = begin_turn(state, gmap, scenario)
        bad = invariants.check(state, gmap)
        if bad:
            raise AssertionError(("supply", state["turn"], bad))
        shown = {s: view(state, gmap, scenario, s) for s in S.SIDES}
        if any(leaks(shown[s], state) for s in S.SIDES):
            raise AssertionError(("view leak", state["turn"]))
        own = shown[side]["units"]
        shortages += sum(u["status"] == "on_map" and u["out_of_stores"] for u in own)
        untraced += sum(u["status"] == "on_map" and not u["traced"] for u in own)
        given = {}
        for s in S.SIDES:
            if s == side:
                start = perf_counter()
                given[s] = bots[s].orders(shown[s])
                cpu += perf_counter() - start
            else:
                given[s] = bots[s].orders(shown[s])
        plan = getattr(bots[side], "flank", None)
        if plan:
            flank_goals.add(plan["goal"])
        dump_before = sum(sum(u["dump"].values()) for u in state["units"]
                          if u["side"] == side and u["type"] == "hq")
        state, replies = finish_turn(state, gmap, scenario, given)
        dump_after = sum(sum(u["dump"].values()) for u in state["units"]
                         if u["side"] == side and u["type"] == "hq")
        hq_dump_lost += dump_before - dump_after
        objective_turn_vp += sum(obj.get("turn", 0) for obj in scenario["objectives"]
                                 if state["places"][obj["place"]] == side)
        captured_flank_goals |= {goal for goal in flank_goals if state["places"].get(goal) == side}
        invalid += sum(not r["ok"] for s in S.SIDES for r in replies[s])
        bad = invariants.check(state, gmap)
        if bad:
            raise AssertionError(("turn", state["turn"], bad))
        turns += 1
    totals = state["sides"]
    return {"seed": seed, "winner": state["result"]["winner"],
            "margin": state["result"]["margin"] * (1 if side == "axis" else -1),
            "objective_vp": totals[side]["vp"] - totals[side]["kills"],
            "objective_turn_vp": objective_turn_vp,
            "loss_vp": totals[S.enemy(side)]["kills"],
            "supply_lost": totals[side]["lost"], "hq_dump_lost": hq_dump_lost,
            "flank_started": sorted(flank_goals), "flank_captured": sorted(captured_flank_goals),
            "shortages": shortages,
            "untraced": untraced, "invalid": invalid, "turns": turns,
            "seconds": round(cpu, 3)}


def compare(scenario, gmap, sides, opponents, seeds, baseline="baseline", candidate="tactical"):
    rows = []
    for side in sides:
        for opponent_name in opponents:
            opponent = OPPONENTS[opponent_name]
            for seed in seeds:
                baseline_result = play(scenario, gmap, side, POLICIES[baseline], opponent, seed)
                candidate_result = play(scenario, gmap, side, POLICIES[candidate], opponent, seed)
                rows.append({"scenario": scenario["id"], "side": side, "opponent": opponent_name,
                             "seed": seed, "baseline_policy": baseline, "candidate_policy": candidate,
                             "baseline": baseline_result, "candidate": candidate_result,
                             "delta_margin": candidate_result["margin"] - baseline_result["margin"],
                             "delta_loss_vp": candidate_result["loss_vp"] - baseline_result["loss_vp"]})
    return rows


def interval(deltas):
    """A descriptive paired bootstrap interval; small samples remain uncertain."""
    if len(deltas) < 2:
        return None
    rng = random.Random(0)
    means = sorted(statistics.mean(rng.choices(deltas, k=len(deltas))) for _ in range(2000))
    return means[50], means[1949]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", nargs="?", default="sidi_rezegh", choices=("sidi_rezegh", "crusader"))
    parser.add_argument("--seeds", type=int, nargs="+", default=(0, 1, 65, 1941, 2026))
    parser.add_argument("--sides", nargs="+", choices=S.SIDES, default=S.SIDES)
    parser.add_argument("--opponents", nargs="+", choices=OPPONENTS, default=("standard", "hard"))
    parser.add_argument("--baseline", choices=("baseline", "unrestricted", "pre-flank"), default="baseline")
    parser.add_argument("--candidate", choices=("tactical", "hard"), default="tactical")
    parser.add_argument("--json", action="store_true", help="Print full paired results as JSON")
    args = parser.parse_args()
    gmap = GameMap(json.loads((ROOT / "data" / "map.json").read_text()))
    rows = compare(scenarios.load(args.scenario), gmap, args.sides, args.opponents, args.seeds,
                   baseline=args.baseline, candidate=args.candidate)
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    print("Positive Δmargin favours candidate; positive Δloss means more of its units were destroyed.")
    for side in args.sides:
        for opponent in args.opponents:
            group = [r for r in rows if r["side"] == side and r["opponent"] == opponent]
            if group:
                deltas = [r["delta_margin"] for r in group]
                ci = interval(deltas)
                print(f"{args.scenario:12} {side:4} vs {opponent:9} n={len(group):2} "
                      f"Δmargin={statistics.mean(deltas):+6.1f} "
                      f"Δloss={statistics.mean(r['delta_loss_vp'] for r in group):+6.1f} "
                      f"range=[{min(deltas):+d},{max(deltas):+d}] "
                      f"bootstrap95={f'[{ci[0]:+.1f},{ci[1]:+.1f}]' if ci else 'n/a'} "
                      f"invalid={sum(r['candidate']['invalid'] for r in group)}")


if __name__ == "__main__":
    main()
