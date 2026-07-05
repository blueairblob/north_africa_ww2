import unittest

from desert_rats import board as board_mod
from desert_rats import data, game, units


def make_board(width=100, height=32, road_cells=()):
    road = set(road_cells)
    grid = tuple(
        tuple(board_mod.ROAD if (x, y) in road else board_mod.DESERT for x in range(width))
        for y in range(height)
    )
    legend = {
        board_mod.DESERT: board_mod.TerrainInfo("Desert", "confirmed"),
        board_mod.ROAD: board_mod.TerrainInfo("Road", "confirmed"),
    }
    return board_mod.Board(width=width, height=height, grid=grid, legend=legend)


def make_oob(entries):
    """entries: list of (nationality, arrival) tuples."""
    roster = tuple(
        data.Unit(
            index=i,
            nationality=nationality,
            designation=f"Unit {i}",
            division=None,
            name=f"Unit {i}",
            x=0,
            strength=100,
            type=10,
            arrival=arrival,
            morale=50,
            role=0,
        )
        for i, (nationality, arrival) in enumerate(entries)
    )
    return data.OrderOfBattle(source="test", fields_note="test", units=roster)


def make_scenario(start_day=1, end_day=10, british_objectives=(), axis_objectives=(), thresholds=None):
    return data.Scenario(
        index=1,
        name="Test Scenario",
        start_day=start_day,
        end_day=end_day,
        british_objectives=tuple(british_objectives),
        axis_objectives=tuple(axis_objectives),
        unit_thresholds=thresholds or {"british": 0, "axis": 0},
    )


def make_unit(nationality, x, y, mps=6, order=units.Order.HOLD, dest_x=None, dest_y=None,
              efficiency=100, index=0):
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
        mps=mps,
        order=order,
        dest_x=dest_x,
        dest_y=dest_y,
        efficiency=efficiency,
    )


class TestNewGame(unittest.TestCase):
    def test_turn_counter_and_clock_match_scenario_start_day(self):
        b = make_board()
        oob = make_oob([(data.Nationality.BRITISH, 0)])
        scenario = make_scenario(start_day=77)
        state = game.new_game(scenario, b, oob)
        self.assertEqual(state.clock, 77)
        self.assertEqual(reinforce_clock(state.turn_counter), 77)

    def test_only_units_arrived_by_start_day_are_present(self):
        b = make_board()
        oob = make_oob([(data.Nationality.BRITISH, 0), (data.Nationality.BRITISH, 50)])
        scenario = make_scenario()
        state = game.new_game(scenario, b, oob)
        self.assertEqual({u.oob_index for u in state.units}, {0})
        self.assertEqual(state.admitted_indices, {0})

    def test_not_over_at_start(self):
        b = make_board()
        oob = make_oob([(data.Nationality.BRITISH, 0)])
        state = game.new_game(make_scenario(), b, oob)
        self.assertFalse(state.is_over)
        self.assertIsNone(state.result)


def reinforce_clock(turn_counter):
    from desert_rats import reinforce
    return reinforce.campaign_clock(turn_counter)


class TestFindAdjacentEnemy(unittest.TestCase):
    def test_finds_adjacent_enemy(self):
        a = make_unit(data.Nationality.BRITISH, 5, 5, index=0)
        b = make_unit(data.Nationality.GERMAN, 7, 5, index=1)
        self.assertIs(game.find_adjacent_enemy(a, [a, b]), b)

    def test_none_when_not_adjacent(self):
        a = make_unit(data.Nationality.BRITISH, 5, 5, index=0)
        b = make_unit(data.Nationality.GERMAN, 50, 5, index=1)
        self.assertIsNone(game.find_adjacent_enemy(a, [a, b]))

    def test_ignores_same_side_and_destroyed(self):
        a = make_unit(data.Nationality.BRITISH, 5, 5, index=0)
        ally = make_unit(data.Nationality.BRITISH, 7, 5, index=1)
        dead_enemy = make_unit(data.Nationality.GERMAN, 7, 5, efficiency=0, index=2)
        self.assertIsNone(game.find_adjacent_enemy(a, [a, ally, dead_enemy]))

    def test_deterministic_tie_break_by_lowest_index(self):
        a = make_unit(data.Nationality.BRITISH, 5, 5, index=0)
        enemy_hi = make_unit(data.Nationality.GERMAN, 7, 5, index=5)
        enemy_lo = make_unit(data.Nationality.GERMAN, 5, 7, index=2)
        self.assertIs(game.find_adjacent_enemy(a, [a, enemy_hi, enemy_lo]), enemy_lo)


class TestPlayTurn(unittest.TestCase):
    def _state(self, units_list, end_day=10):
        b = make_board()
        oob = make_oob([(data.Nationality.BRITISH, 0)] * len(units_list))
        scenario = make_scenario(end_day=end_day)
        return game.GameState(
            board=b,
            oob=oob,
            scenario=scenario,
            turn_counter=0,
            clock=0,
            units=units_list,
            admitted_indices=set(range(len(units_list))),
        )

    def test_turn_counter_and_clock_advance(self):
        state = self._state([])
        game.play_turn(state)
        self.assertEqual(state.turn_counter, 1)
        self.assertEqual(state.clock, 1)

    def test_movement_advances_units_with_orders_already_set(self):
        mover = make_unit(data.Nationality.BRITISH, 5, 5, order=units.Order.MOVE, dest_x=8, dest_y=5)
        state = self._state([mover])
        game.play_turn(state)
        self.assertEqual((mover.x, mover.y), (8, 5))

    def test_order_provider_runs_before_movement(self):
        mover = make_unit(data.Nationality.BRITISH, 5, 5)
        state = self._state([mover])

        def set_move_order(state, side, flags):
            for u in state.units:
                if u.side is side:
                    u.order = units.Order.MOVE
                    u.dest_x, u.dest_y = 9, 5

        game.play_turn(state, {data.Side.BRITISH: set_move_order})
        self.assertEqual((mover.x, mover.y), (9, 5))

    def test_combat_phase_builds_pressure_and_cracks_units(self):
        # Recovered model: adjacency builds pressure each turn until the
        # morale test fails, costing -10 efficiency and forcing Hold.
        strong = make_unit(data.Nationality.BRITISH, 5, 5, index=0)
        weak = make_unit(data.Nationality.GERMAN, 7, 5, index=1)
        strong.strength, weak.strength = 200, 100
        weak.morale = 10   # cracks quickly under pressure
        weak.type = 12     # morale threshold, not the class-10 override
        state = self._state([strong, weak])
        start_eff = weak.efficiency
        for _ in range(6):
            game.play_turn(state)
            if weak.efficiency < start_eff:
                break
        self.assertLess(weak.efficiency, start_eff)
        self.assertGreater(weak.pressure, 0)

    def test_attrition_and_recovery_apply_after_movement(self):
        safe_unit = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=50)
        state = self._state([safe_unit])
        game.play_turn(state)
        # not out of supply/in enemy ZOC (no enemies at all) -> recovers
        self.assertEqual(safe_unit.efficiency, 54)

    def test_destroyed_units_are_pruned_at_turn_end(self):
        dead = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=0)
        state = self._state([dead])
        game.play_turn(state)
        self.assertEqual(state.units, [])

    def test_game_ends_when_clock_reaches_end_day(self):
        state = self._state([], end_day=1)
        game.play_turn(state)
        self.assertTrue(state.is_over)
        self.assertIsNotNone(state.result)

    def test_play_turn_is_a_no_op_once_over(self):
        state = self._state([], end_day=1)
        game.play_turn(state)
        self.assertEqual(state.turn_counter, 1)
        game.play_turn(state)
        self.assertEqual(state.turn_counter, 1)


class TestRunUntilOver(unittest.TestCase):
    def test_runs_until_end_day(self):
        b = make_board()
        oob = make_oob([])
        scenario = make_scenario(end_day=3)
        state = game.new_game(scenario, b, oob)
        game.run_until_over(state)
        self.assertTrue(state.is_over)
        self.assertEqual(state.clock, 3)

    def test_respects_max_turns_safety_cap(self):
        b = make_board()
        oob = make_oob([])
        scenario = make_scenario(end_day=10**9)
        state = game.new_game(scenario, b, oob)
        game.run_until_over(state, max_turns=5)
        self.assertFalse(state.is_over)
        self.assertEqual(state.turn_counter, 6)  # start_day=1 -> initial turn_counter=1, +5 turns


if __name__ == "__main__":
    unittest.main()
