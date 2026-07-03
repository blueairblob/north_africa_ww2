import unittest

from desert_rats import ai
from desert_rats import board as board_mod
from desert_rats import data, game, units, zoc_supply


def make_board(width=100, height=32):
    grid = tuple(tuple(board_mod.DESERT for _ in range(width)) for _ in range(height))
    legend = {board_mod.DESERT: board_mod.TerrainInfo("Desert", "confirmed")}
    return board_mod.Board(width=width, height=height, grid=grid, legend=legend)


def make_unit(nationality, x, y, mps=6, strength=100, efficiency=100, index=0):
    return units.Unit(
        oob_index=index,
        nationality=nationality,
        designation="Test Unit",
        division=None,
        name="Test Unit",
        type=10,
        role=0,
        strength=strength,
        morale=50,
        arrival=0,
        x=x,
        y=y,
        mps=mps,
        efficiency=efficiency,
    )


def make_oob(n):
    roster = tuple(
        data.Unit(
            index=i, nationality=data.Nationality.BRITISH, designation=f"U{i}", division=None,
            name=f"U{i}", x=0, strength=100, type=10, arrival=0, morale=50, role=0,
        )
        for i in range(n)
    )
    return data.OrderOfBattle(source="test", fields_note="test", units=roster)


def make_scenario(end_day=10):
    return data.Scenario(
        index=1, name="Test", start_day=1, end_day=end_day,
        british_objectives=(), axis_objectives=(), unit_thresholds={"british": 0, "axis": 0},
    )


def empty_flags(board):
    return zoc_supply.FlagGrid(
        width=board.width, height=board.height,
        zoc={data.Side.BRITISH: frozenset(), data.Side.AXIS: frozenset()},
        occupied={data.Side.BRITISH: frozenset(), data.Side.AXIS: frozenset()},
    )


class TestUnitWeight(unittest.TestCase):
    def test_non_armour_weight_is_mps(self):
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=6)
        unit.type = 12  # not the armour override code
        self.assertEqual(ai.unit_weight(unit), 6)

    def test_armour_weight_is_doubled(self):
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=6)
        unit.type = 10  # armour override code
        self.assertEqual(ai.unit_weight(unit), 12)


class TestRegionIndex(unittest.TestCase):
    def test_first_and_last_columns(self):
        self.assertEqual(ai.region_index(0, 100), 0)
        self.assertEqual(ai.region_index(99, 100), 29)

    def test_monotonic_across_the_board(self):
        indices = [ai.region_index(x, 100) for x in range(100)]
        self.assertEqual(indices, sorted(indices))
        self.assertTrue(all(0 <= r < ai.REGION_COUNT for r in indices))


class TestRegionalStrengthMap(unittest.TestCase):
    def test_tallies_effective_power_weighted_by_mps_and_type(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 10, 5, mps=6, strength=100, efficiency=100)
        unit.type = 10  # armour
        strength_map = ai.build_regional_strength_map([unit], b)
        region = ai.region_index(10, b.width)
        self.assertEqual(strength_map[data.Side.BRITISH][region], 100 * 12)
        self.assertTrue(all(v == 0 for v in strength_map[data.Side.AXIS]))

    def test_destroyed_units_are_excluded(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 10, 5, efficiency=0)
        strength_map = ai.build_regional_strength_map([unit], b)
        self.assertTrue(all(v == 0 for v in strength_map[data.Side.BRITISH]))


class TestPickTargetRegion(unittest.TestCase):
    def test_picks_greatest_relative_advantage(self):
        strength_map = {
            data.Side.BRITISH: [0.0] * ai.REGION_COUNT,
            data.Side.AXIS: [0.0] * ai.REGION_COUNT,
        }
        strength_map[data.Side.BRITISH][5] = 100
        strength_map[data.Side.AXIS][5] = 90
        strength_map[data.Side.BRITISH][10] = 100
        strength_map[data.Side.AXIS][10] = 10
        region = ai.pick_target_region(strength_map, data.Side.BRITISH, [5, 10])
        self.assertEqual(region, 10)

    def test_ties_break_to_lowest_index(self):
        strength_map = {
            data.Side.BRITISH: [0.0] * ai.REGION_COUNT,
            data.Side.AXIS: [0.0] * ai.REGION_COUNT,
        }
        region = ai.pick_target_region(strength_map, data.Side.BRITISH, [7, 3, 5])
        self.assertEqual(region, 3)


class TestIsOffensive(unittest.TestCase):
    def test_within_band_is_offensive(self):
        unit = make_unit(data.Nationality.BRITISH, 40, 5)
        self.assertTrue(ai.is_offensive(unit, midpoint=50))

    def test_outside_band_is_defensive(self):
        unit = make_unit(data.Nationality.BRITISH, 90, 5)
        self.assertFalse(ai.is_offensive(unit, midpoint=50))

    def test_no_front_line_defaults_offensive(self):
        unit = make_unit(data.Nationality.BRITISH, 90, 5)
        self.assertTrue(ai.is_offensive(unit, midpoint=None))


class TestRayScanContact(unittest.TestCase):
    def test_finds_nearest_enemy_zoc_along_a_ray(self):
        b = make_board(30, 30)
        scout = make_unit(data.Nationality.BRITISH, 10, 10, index=0)
        enemy = make_unit(data.Nationality.GERMAN, 15, 10, index=1)
        flags = zoc_supply.build_flag_grid([enemy], b)
        hit = ai.ray_scan_contact(scout, flags, b)
        self.assertIsNotNone(hit)
        self.assertEqual(hit, (14, 10))  # enemy ZOC extends to x=14 (footprint 15,16)

    def test_none_when_nothing_in_range(self):
        b = make_board(30, 30)
        scout = make_unit(data.Nationality.BRITISH, 10, 10, index=0)
        self.assertIsNone(ai.ray_scan_contact(scout, empty_flags(b), b))


class TestPlanTurnIntegration(unittest.TestCase):
    def _state(self, units_list, end_day=10):
        b = make_board()
        oob = make_oob(len(units_list))
        scenario = make_scenario(end_day=end_day)
        return game.GameState(
            board=b, oob=oob, scenario=scenario, turn_counter=0, clock=0,
            units=units_list, admitted_indices=set(range(len(units_list))),
        )

    def test_offensive_unit_gets_a_move_order_toward_the_target(self):
        # both units near each other -> midpoint is near both -> in-band -> offensive
        british = make_unit(data.Nationality.BRITISH, 55, 5, index=0)
        german = make_unit(data.Nationality.GERMAN, 45, 5, index=1)
        state = self._state([british, german])
        flags = zoc_supply.build_flag_grid(state.units, state.board)
        ai.plan_turn(state, data.Side.BRITISH, flags)
        self.assertEqual(british.order, units.Order.MOVE)
        self.assertIsNotNone(british.dest_x)

    def test_defensive_unit_with_adjacent_enemy_assaults(self):
        # Front-line extremes (westernmost British=10, easternmost Axis=90)
        # put the midpoint at 50, band [25,75]. An isolated skirmish near
        # x=15-17 sits outside that band -> defensive -- even though it's
        # a live contact point, it isn't part of the main front.
        british_main = make_unit(data.Nationality.BRITISH, 10, 5, index=0)
        british_defender = make_unit(data.Nationality.BRITISH, 17, 5, index=2)
        german_main = make_unit(data.Nationality.GERMAN, 90, 5, index=1)
        german_adjacent = make_unit(data.Nationality.GERMAN, 15, 5, index=3)
        state = self._state([british_main, british_defender, german_main, german_adjacent])
        flags = zoc_supply.build_flag_grid(state.units, state.board)
        ai.plan_turn(state, data.Side.BRITISH, flags)
        self.assertEqual(british_defender.order, units.Order.ASSAULT)

    def test_plan_turn_only_touches_the_given_side(self):
        british = make_unit(data.Nationality.BRITISH, 50, 5, index=0)
        german = make_unit(data.Nationality.GERMAN, 50, 5, index=1)
        state = self._state([british, german])
        flags = zoc_supply.build_flag_grid(state.units, state.board)
        ai.plan_turn(state, data.Side.BRITISH, flags)
        self.assertEqual(german.order, units.Order.HOLD)

    def test_wired_into_game_play_turn_as_an_order_provider(self):
        british = make_unit(data.Nationality.BRITISH, 55, 5, index=0)
        german = make_unit(data.Nationality.GERMAN, 45, 5, index=1)
        state = self._state([british, german])
        game.play_turn(state, {data.Side.BRITISH: ai.plan_turn, data.Side.AXIS: ai.plan_turn})
        # both sides got orders assigned and the turn advanced without error
        self.assertEqual(state.turn_counter, 1)


if __name__ == "__main__":
    unittest.main()
