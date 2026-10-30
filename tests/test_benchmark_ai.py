"""The development benchmark must compare like with like and report legal games."""
from engine import players, scenarios
from engine.computer import ComputerHardBaseline
from helpers import GMAP
from scripts.benchmark_ai import compare, play


def test_paired_benchmark_repeats_exact_match_with_same_seed_and_policy():
    scenario = scenarios.load("sidi_rezegh")
    first = play(scenario, GMAP, "cw", ComputerHardBaseline, players.ComputerOpponent, 1941)
    second = play(scenario, GMAP, "cw", ComputerHardBaseline, players.ComputerOpponent, 1941)
    assert {k: v for k, v in first.items() if k != "seconds"} == {
        k: v for k, v in second.items() if k != "seconds"}
    assert first["invalid"] == 0 and first["turns"] == scenario["turns"]
    assert first["hq_dump_lost"] >= 0 and first["objective_turn_vp"] >= 0


def test_paired_benchmark_reports_candidate_minus_baseline_for_both_sides():
    rows = compare(scenarios.load("sidi_rezegh"), GMAP, ("axis", "cw"), ("standard",), (1941,))
    assert {row["side"] for row in rows} == {"axis", "cw"}
    for row in rows:
        assert row["delta_margin"] == row["candidate"]["margin"] - row["baseline"]["margin"]
        assert row["delta_loss_vp"] == row["candidate"]["loss_vp"] - row["baseline"]["loss_vp"]
        assert row["candidate"]["invalid"] == row["baseline"]["invalid"] == 0
