import contextlib
import io
import unittest
from unittest.mock import patch

from desert_rats import ai, board, data, game, main, units


def make_board(width=100, height=32):
    # default size matches reinforce.STAGING_POINTS, which are fixed
    # real-map coordinates ((98,11) / (0,11)) independent of the board
    # passed in -- a smaller synthetic board would make new_game() unable
    # to find a free staging cell at all.
    grid = tuple(tuple(0 for _ in range(width)) for _ in range(height))
    import desert_rats.board as board_mod

    legend = {board_mod.DESERT: board_mod.TerrainInfo("Desert", "confirmed")}
    return board_mod.Board(width=width, height=height, grid=grid, legend=legend)


def make_oob(entries):
    roster = tuple(
        data.Unit(
            index=i, nationality=nationality, designation=f"Unit {i}", division=None,
            name=f"Unit {i}", x=0, strength=100, type=10, arrival=arrival, morale=50, role=0,
        )
        for i, (nationality, arrival) in enumerate(entries)
    )
    return data.OrderOfBattle(source="test", fields_note="test", units=roster)


def make_scenario(end_day=5):
    return data.Scenario(
        index=1, name="Test Scenario", start_day=1, end_day=end_day,
        british_objectives=(), axis_objectives=(), unit_thresholds={"british": 0, "axis": 0},
    )


class TestBuildOrderProviders(unittest.TestCase):
    def test_ai_mode_uses_ai_plan_turn(self):
        providers = main.build_order_providers("ai", "ai")
        self.assertIs(providers[data.Side.BRITISH], ai.plan_turn)
        self.assertIs(providers[data.Side.AXIS], ai.plan_turn)

    def test_human_mode_uses_human_order_provider(self):
        providers = main.build_order_providers("human", "ai")
        self.assertIs(providers[data.Side.BRITISH], main.human_order_provider)
        self.assertIs(providers[data.Side.AXIS], ai.plan_turn)


class TestRunHeadless(unittest.TestCase):
    def test_runs_a_full_game_with_no_io_and_reaches_a_result(self):
        b = make_board()
        oob = make_oob([(data.Nationality.BRITISH, 0), (data.Nationality.GERMAN, 0)])
        scenario = make_scenario(end_day=3)
        state = main.run_headless(scenario, b, oob)
        self.assertTrue(state.is_over)
        self.assertIsNotNone(state.result)

    def test_respects_side_modes(self):
        b = make_board()
        oob = make_oob([(data.Nationality.BRITISH, 0), (data.Nationality.GERMAN, 0)])
        scenario = make_scenario(end_day=3)
        # both AI, should never block on input()
        with patch("builtins.input", side_effect=AssertionError("should not prompt")):
            state = main.run_headless(scenario, b, oob, british_mode="ai", axis_mode="ai")
        self.assertTrue(state.is_over)

    def test_uses_real_game_data_end_to_end(self):
        real_board = board.load_board()
        real_oob = data.load_master_oob()
        scenario = data.load_scenarios()[0]
        state = main.run_headless(scenario, real_board, real_oob, max_turns=2000)
        self.assertTrue(state.is_over)
        self.assertIsInstance(state.result, game.victory.VictoryLevel)


class TestParseArgs(unittest.TestCase):
    def test_defaults(self):
        args = main.parse_args([])
        self.assertFalse(args.headless)
        self.assertEqual(args.scenario, 1)

    def test_headless_flag_and_scenario(self):
        args = main.parse_args(["--headless", "--scenario", "3"])
        self.assertTrue(args.headless)
        self.assertEqual(args.scenario, 3)


class TestMainHeadless(unittest.TestCase):
    def test_returns_zero_and_prints_a_result(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main.main(["--headless", "--scenario", "1", "--max-turns", "50"])
        self.assertEqual(code, 0)
        self.assertIn("Enter Rommel", buf.getvalue())


class TestPromptScenario(unittest.TestCase):
    def test_returns_the_selected_scenario(self):
        scenarios = data.load_scenarios()
        buf = io.StringIO()
        with patch("builtins.input", side_effect=["2"]), contextlib.redirect_stdout(buf):
            chosen = main._prompt_scenario(scenarios)
        self.assertEqual(chosen.name, "Battleaxe")

    def test_reprompts_on_invalid_choice(self):
        scenarios = data.load_scenarios()
        buf = io.StringIO()
        with patch("builtins.input", side_effect=["nope", "1"]), contextlib.redirect_stdout(buf):
            chosen = main._prompt_scenario(scenarios)
        self.assertEqual(chosen.index, 1)


class TestPromptSideMode(unittest.TestCase):
    def test_human_choice(self):
        with patch("builtins.input", side_effect=["1"]):
            self.assertEqual(main._prompt_side_mode(data.Side.BRITISH), "human")

    def test_ai_choice(self):
        with patch("builtins.input", side_effect=["2"]):
            self.assertEqual(main._prompt_side_mode(data.Side.BRITISH), "ai")

    def test_blank_defaults_to_ai(self):
        with patch("builtins.input", side_effect=[""]):
            self.assertEqual(main._prompt_side_mode(data.Side.BRITISH), "ai")


class TestHumanOrderProvider(unittest.TestCase):
    def _unit(self, nationality, x, y, index=0):
        return units.Unit(
            oob_index=index, nationality=nationality, designation="Test Unit", division=None,
            name="Test Unit", type=10, role=0, strength=100, morale=50, arrival=0,
            x=x, y=y, mps=6,
        )

    def test_setting_an_order_and_destination(self):
        unit = self._unit(data.Nationality.BRITISH, 5, 5)
        b = make_board()
        oob = make_oob([(data.Nationality.BRITISH, 0)])
        state = game.GameState(
            board=b, oob=oob, scenario=make_scenario(), turn_counter=0, clock=0,
            units=[unit], admitted_indices={0},
        )
        flags = None
        buf = io.StringIO()
        # select unit 0, choose Move (1), destination "9,5", then end
        with patch("builtins.input", side_effect=["0", "1", "9,5", ""]), contextlib.redirect_stdout(buf):
            main.human_order_provider(state, data.Side.BRITISH, flags)
        self.assertEqual(unit.order, units.Order.MOVE)
        self.assertEqual((unit.dest_x, unit.dest_y), (9, 5))

    def test_no_units_is_a_silent_no_op(self):
        b = make_board()
        oob = make_oob([])
        state = game.GameState(
            board=b, oob=oob, scenario=make_scenario(), turn_counter=0, clock=0,
            units=[], admitted_indices=set(),
        )
        with patch("builtins.input", side_effect=AssertionError("should not prompt")):
            main.human_order_provider(state, data.Side.BRITISH, None)

    def test_invalid_unit_index_reprompts(self):
        unit = self._unit(data.Nationality.BRITISH, 5, 5)
        b = make_board()
        oob = make_oob([(data.Nationality.BRITISH, 0)])
        state = game.GameState(
            board=b, oob=oob, scenario=make_scenario(), turn_counter=0, clock=0,
            units=[unit], admitted_indices={0},
        )
        buf = io.StringIO()
        with patch("builtins.input", side_effect=["nope", ""]), contextlib.redirect_stdout(buf):
            main.human_order_provider(state, data.Side.BRITISH, None)
        self.assertEqual(unit.order, units.Order.HOLD)


class TestPromptMalta(unittest.TestCase):
    def test_does_not_crash_and_prints_the_no_effect_note(self):
        strings = main.load_ui_strings()
        buf = io.StringIO()
        with patch("builtins.input", side_effect=["1"]), contextlib.redirect_stdout(buf):
            main._prompt_malta(strings)
        self.assertIn(main.MALTA_NOTE, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
