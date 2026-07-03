"""End-to-end smoke tests using the real game data (data/*.json).

CLEANROOM_BRIEF.md's acceptance criterion: "Headless 2-player games run
end-to-end on all six scenarios and reach a victory result." The point of
this test is that the full pipeline (data -> board -> reinforce ->
zoc_supply -> movement -> combat -> ai -> victory) runs to completion
without crashing, deterministically, on the real 128-unit roster and
100x32 map -- both with no orders issued at all (everything holds, which
should reach a quick stalemate) and with ai.plan_turn driving both sides.
"""
import unittest

from desert_rats import ai, board, data, game


class TestScenariosRunToCompletion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = board.load_board()
        cls.oob = data.load_master_oob()
        cls.scenarios = data.load_scenarios()

    def test_every_scenario_reaches_a_result_with_no_orders(self):
        for scenario in self.scenarios:
            with self.subTest(scenario=scenario.name):
                state = game.new_game(scenario, self.board, self.oob)
                game.run_until_over(state, max_turns=2000)
                self.assertTrue(state.is_over, f"{scenario.name} never reached a result")
                self.assertIsInstance(state.result, game.victory.VictoryLevel)

    def test_every_scenario_reaches_a_result_with_the_ai_driving_both_sides(self):
        providers = {data.Side.BRITISH: ai.plan_turn, data.Side.AXIS: ai.plan_turn}
        for scenario in self.scenarios:
            with self.subTest(scenario=scenario.name):
                state = game.new_game(scenario, self.board, self.oob)
                game.run_until_over(state, providers, max_turns=3000)
                self.assertTrue(state.is_over, f"{scenario.name} never reached a result")
                self.assertIsInstance(state.result, game.victory.VictoryLevel)

    def test_a_scenario_run_is_deterministic(self):
        scenario = self.scenarios[0]
        state_a = game.new_game(scenario, self.board, self.oob)
        game.run_until_over(state_a)
        state_b = game.new_game(scenario, self.board, self.oob)
        game.run_until_over(state_b)

        self.assertEqual(state_a.result, state_b.result)
        self.assertEqual(state_a.clock, state_b.clock)
        self.assertEqual(
            [(u.oob_index, u.x, u.y, u.efficiency) for u in state_a.units],
            [(u.oob_index, u.x, u.y, u.efficiency) for u in state_b.units],
        )

    def test_an_ai_driven_scenario_run_is_deterministic(self):
        scenario = self.scenarios[1]
        providers = {data.Side.BRITISH: ai.plan_turn, data.Side.AXIS: ai.plan_turn}
        state_a = game.new_game(scenario, self.board, self.oob)
        game.run_until_over(state_a, providers)
        state_b = game.new_game(scenario, self.board, self.oob)
        game.run_until_over(state_b, providers)

        self.assertEqual(state_a.result, state_b.result)
        self.assertEqual(
            [(u.oob_index, u.x, u.y, u.efficiency) for u in state_a.units],
            [(u.oob_index, u.x, u.y, u.efficiency) for u in state_b.units],
        )


if __name__ == "__main__":
    unittest.main()
