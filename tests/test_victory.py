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


class FakeScenario:
    """A scenario carrying explicit recovered victory conditions."""
    def __init__(self, brit_obj, axis_obj, brit_thr=0, axis_thr=0):
        self._c = {
            "british_objectives": brit_obj,
            "axis_objectives": axis_obj,
            "british_unit_threshold": brit_thr,
            "axis_unit_threshold": axis_thr,
        }

    @property
    def victory_conditions(self):
        return self._c


class TestRecoveredObjectives(unittest.TestCase):
    def test_type5_keeps_more_than_v_units(self):
        us = [make_unit(data.Nationality.BRITISH, 10, 10, index=i) for i in range(4)]
        self.assertTrue(victory.objective_met(us, [5, 3], data.Side.BRITISH))   # 4 > 3
        self.assertFalse(victory.objective_met(us, [5, 4], data.Side.BRITISH))  # 4 > 4 false

    def test_type3_front_line_position(self):
        # British push west: front (their westernmost x) must be <= V.
        us = [make_unit(data.Nationality.BRITISH, 40, 10)]
        self.assertTrue(victory.objective_met(us, [3, 76], data.Side.BRITISH))
        self.assertFalse(victory.objective_met(us, [3, 20], data.Side.BRITISH))
        # Axis push east: front (their easternmost x) must be >= V.
        them = [make_unit(data.Nationality.GERMAN, 90, 10)]
        self.assertTrue(victory.objective_met(them, [3, 76], data.Side.AXIS))
        self.assertFalse(victory.objective_met(them, [3, 95], data.Side.AXIS))

    def test_type4_contains_the_enemy(self):
        # British hold the Axis front no further east than V.
        us = [make_unit(data.Nationality.BRITISH, 80, 10),
              make_unit(data.Nationality.GERMAN, 30, 10, index=1)]
        self.assertTrue(victory.objective_met(us, [4, 20], data.Side.BRITISH))
        self.assertFalse(victory.objective_met(us, [4, 50], data.Side.BRITISH))


class TestRecoveredScoring(unittest.TestCase):
    def test_each_met_objective_scores_one(self):
        us = [make_unit(data.Nationality.BRITISH, 40, 10, index=i) for i in range(5)]
        us.append(make_unit(data.Nationality.GERMAN, 90, 10, index=9))
        sc = FakeScenario([[3, 76], [5, 3]], [[0, 0], [0, 0]])
        self.assertEqual(victory.score_side(us, sc, data.Side.BRITISH), 2)

    def test_threshold_zeroes_the_score(self):
        # Oracle semantics: falling below the threshold ZEROES the score
        # (it is not a bonus point).
        us = [make_unit(data.Nationality.BRITISH, 40, 10)]
        us.append(make_unit(data.Nationality.GERMAN, 90, 10, index=9))
        sc = FakeScenario([[3, 76], [0, 0]], [[0, 0], [0, 0]], brit_thr=5)
        self.assertEqual(victory.score_side(us, sc, data.Side.BRITISH), 0)

    def test_annihilation_scores_three(self):
        us = [make_unit(data.Nationality.BRITISH, 40, 10)]
        sc = FakeScenario([[0, 0], [0, 0]], [[0, 0], [0, 0]])
        self.assertEqual(victory.score_side(us, sc, data.Side.BRITISH), 3)


class TestRecoveredLadder(unittest.TestCase):
    def _units(self, brit=1, axis=1):
        us = [make_unit(data.Nationality.BRITISH, 40, 10, index=i) for i in range(brit)]
        us += [make_unit(data.Nationality.GERMAN, 90, 10, index=50 + i) for i in range(axis)]
        return us

    def test_equal_scores_draw(self):
        sc = FakeScenario([[0, 0], [0, 0]], [[0, 0], [0, 0]])
        self.assertIs(victory.victory_result(self._units(), sc), victory.VictoryLevel.DRAW)

    def test_winner_score_sets_the_magnitude(self):
        us = self._units(brit=5, axis=1)
        # British meet both objectives (front <= 76; > 3 units) -> score 2
        sc = FakeScenario([[3, 76], [5, 3]], [[0, 0], [0, 0]])
        self.assertIs(victory.victory_result(us, sc), victory.VictoryLevel.BRITISH_MAJOR)
        # One objective only -> tactical
        sc1 = FakeScenario([[3, 76], [5, 9]], [[0, 0], [0, 0]])
        self.assertIs(victory.victory_result(us, sc1), victory.VictoryLevel.BRITISH_TACTICAL)

    def test_annihilation_is_decisive(self):
        us = [make_unit(data.Nationality.BRITISH, 40, 10)]
        sc = FakeScenario([[0, 0], [0, 0]], [[0, 0], [0, 0]])
        self.assertIs(victory.victory_result(us, sc), victory.VictoryLevel.BRITISH_DECISIVE)

    def test_axis_mirrors(self):
        us = self._units(brit=1, axis=5)
        sc = FakeScenario([[0, 0], [0, 0]], [[3, 76], [5, 3]])
        self.assertIs(victory.victory_result(us, sc), victory.VictoryLevel.AXIS_MAJOR)


if __name__ == "__main__":
    unittest.main()
