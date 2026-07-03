import unittest

from desert_rats import data, units, victory


def make_unit(nationality, x, y=10, efficiency=100, index=0):
    return units.Unit(
        oob_index=index,
        nationality=nationality,
        designation="Test Unit",
        division=None,
        name="Test Unit",
        type=10,
        role=0,
        strength=100,
        morale=50,
        arrival=0,
        x=x,
        y=y,
        mps=6,
        efficiency=efficiency,
    )


def make_scenario(british_objectives=(), axis_objectives=(), thresholds=None, end_day=31):
    return data.Scenario(
        index=1,
        name="Test Scenario",
        start_day=1,
        end_day=end_day,
        british_objectives=tuple(british_objectives),
        axis_objectives=tuple(axis_objectives),
        unit_thresholds=thresholds or {"british": 0, "axis": 0},
    )


class TestFrontLine(unittest.TestCase):
    def test_returns_easternmost_axis_and_westernmost_british(self):
        u = [
            make_unit(data.Nationality.GERMAN, 10, index=0),
            make_unit(data.Nationality.GERMAN, 20, index=1),
            make_unit(data.Nationality.BRITISH, 60, index=2),
            make_unit(data.Nationality.BRITISH, 80, index=3),
        ]
        self.assertEqual(victory.front_line(u), (20, 60))

    def test_none_when_a_side_has_no_living_units(self):
        u = [make_unit(data.Nationality.BRITISH, 60, index=0)]
        self.assertIsNone(victory.front_line(u))

    def test_destroyed_units_are_excluded(self):
        u = [
            make_unit(data.Nationality.GERMAN, 20, efficiency=0, index=0),
            make_unit(data.Nationality.GERMAN, 10, index=1),
            make_unit(data.Nationality.BRITISH, 60, index=2),
        ]
        self.assertEqual(victory.front_line(u), (10, 60))

    def test_midpoint(self):
        u = [
            make_unit(data.Nationality.GERMAN, 20, index=0),
            make_unit(data.Nationality.BRITISH, 60, index=1),
        ]
        self.assertEqual(victory.front_line_midpoint(u), 40)

    def test_midpoint_none_when_undefined(self):
        self.assertIsNone(victory.front_line_midpoint([]))


class TestStalemate(unittest.TestCase):
    def test_false_before_enough_history(self):
        history = [50.0] * (victory.STALEMATE_TURNS - 1)
        self.assertFalse(victory.is_stalemate(history))

    def test_true_when_unchanged_for_the_full_window(self):
        history = [50.0] * victory.STALEMATE_TURNS
        self.assertTrue(victory.is_stalemate(history))

    def test_false_when_midpoint_moved_within_the_window(self):
        history = [50.0] * (victory.STALEMATE_TURNS - 1) + [51.0]
        self.assertFalse(victory.is_stalemate(history))

    def test_false_when_recent_history_has_none(self):
        history = [None] * victory.STALEMATE_TURNS
        self.assertFalse(victory.is_stalemate(history))


class TestGameOver(unittest.TestCase):
    def test_over_when_clock_reaches_end_day(self):
        scenario = make_scenario(end_day=31)
        self.assertTrue(victory.is_game_over(31, scenario, []))
        self.assertFalse(victory.is_game_over(30, scenario, []))

    def test_over_on_stalemate_before_end_day(self):
        scenario = make_scenario(end_day=624)
        history = [42.0] * victory.STALEMATE_TURNS
        self.assertTrue(victory.is_game_over(5, scenario, history))


class TestControlsColumn(unittest.TestCase):
    def test_nearest_units_side_controls(self):
        u = [
            make_unit(data.Nationality.GERMAN, 10, index=0),
            make_unit(data.Nationality.BRITISH, 90, index=1),
        ]
        self.assertEqual(victory.controls_column(u, 15), data.Side.AXIS)
        self.assertEqual(victory.controls_column(u, 85), data.Side.BRITISH)

    def test_none_with_no_living_units(self):
        self.assertIsNone(victory.controls_column([], 50))


class TestScoring(unittest.TestCase):
    def test_objective_points_awarded_to_controlling_side(self):
        scenario = make_scenario(british_objectives=((50, 3), (76, 3)))
        u = [make_unit(data.Nationality.BRITISH, 50, index=0), make_unit(data.Nationality.BRITISH, 76, index=1)]
        self.assertEqual(victory.count_controlled_objectives(u, scenario.british_objectives, data.Side.BRITISH), 2)

    def test_unit_threshold_bonus(self):
        scenario = make_scenario(thresholds={"british": 2, "axis": 0})
        below = [make_unit(data.Nationality.BRITISH, 50, index=0)]
        at_threshold = [
            make_unit(data.Nationality.BRITISH, 50, index=0),
            make_unit(data.Nationality.BRITISH, 51, index=1),
        ]
        self.assertEqual(victory.score_side(below, scenario, data.Side.BRITISH), 0)
        self.assertEqual(victory.score_side(at_threshold, scenario, data.Side.BRITISH), 1)


class TestVictoryResult(unittest.TestCase):
    def test_draw_on_equal_score(self):
        scenario = make_scenario()
        u = [make_unit(data.Nationality.GERMAN, 10, index=0), make_unit(data.Nationality.BRITISH, 90, index=1)]
        self.assertEqual(victory.victory_result(u, scenario), victory.VictoryLevel.DRAW)

    def test_british_tactical_victory(self):
        scenario = make_scenario(british_objectives=((50, 3),))
        u = [
            make_unit(data.Nationality.BRITISH, 50, index=0),
            make_unit(data.Nationality.GERMAN, 10, index=1),
        ]
        self.assertEqual(victory.victory_result(u, scenario), victory.VictoryLevel.BRITISH_TACTICAL)

    def test_british_major_victory(self):
        scenario = make_scenario(british_objectives=((50, 3), (60, 3)))
        u = [
            make_unit(data.Nationality.BRITISH, 50, index=0),
            make_unit(data.Nationality.BRITISH, 60, index=1),
            make_unit(data.Nationality.GERMAN, 10, index=2),
        ]
        self.assertEqual(victory.victory_result(u, scenario), victory.VictoryLevel.BRITISH_MAJOR)

    def test_british_decisive_victory(self):
        scenario = make_scenario(
            british_objectives=((50, 3), (60, 3)), thresholds={"british": 1, "axis": 99}
        )
        u = [
            make_unit(data.Nationality.BRITISH, 50, index=0),
            make_unit(data.Nationality.BRITISH, 60, index=1),
            make_unit(data.Nationality.GERMAN, 10, index=2),
        ]
        self.assertEqual(victory.victory_result(u, scenario), victory.VictoryLevel.BRITISH_DECISIVE)

    def test_axis_tactical_victory_mirrors_british(self):
        scenario = make_scenario(axis_objectives=((10, 3),))
        u = [
            make_unit(data.Nationality.GERMAN, 10, index=0),
            make_unit(data.Nationality.BRITISH, 90, index=1),
        ]
        self.assertEqual(victory.victory_result(u, scenario), victory.VictoryLevel.AXIS_TACTICAL)


if __name__ == "__main__":
    unittest.main()
