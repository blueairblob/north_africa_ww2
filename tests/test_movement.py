import unittest

from desert_rats import board as board_mod
from desert_rats import data, movement, units, zoc_supply


def make_board(width, height, road_cells=(), sea_cells=()):
    road = set(road_cells)
    sea = set(sea_cells)

    def terrain(x, y):
        if (x, y) in sea:
            return board_mod.SEA
        if (x, y) in road:
            return board_mod.ROAD
        return board_mod.DESERT

    grid = tuple(tuple(terrain(x, y) for x in range(width)) for y in range(height))
    legend = {
        board_mod.DESERT: board_mod.TerrainInfo("Desert", "confirmed"),
        board_mod.ROAD: board_mod.TerrainInfo("Road", "confirmed"),
        board_mod.SEA: board_mod.TerrainInfo("Sea", "confirmed"),
    }
    return board_mod.Board(width=width, height=height, grid=grid, legend=legend)


def make_unit(nationality, x, y, mps=6, order=units.Order.MOVE, dest_x=None, dest_y=None,
              travel=False, caught=False, index=0):
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
        travel=travel,
        caught=caught,
    )


def empty_flags(board):
    return zoc_supply.FlagGrid(
        width=board.width,
        height=board.height,
        zoc={data.Side.BRITISH: frozenset(), data.Side.AXIS: frozenset()},
        occupied={data.Side.BRITISH: frozenset(), data.Side.AXIS: frozenset()},
    )


class TestStepCost(unittest.TestCase):
    def test_move_is_base_cost(self):
        self.assertEqual(movement.step_cost(units.Order.MOVE), 1.0)

    def test_assault_is_1_5x(self):
        self.assertEqual(movement.step_cost(units.Order.ASSAULT), 1.5)

    def test_travel_is_half(self):
        self.assertEqual(movement.step_cost(units.Order.TRAVEL), 0.5)

    def test_hold_defaults_to_base(self):
        self.assertEqual(movement.step_cost(units.Order.HOLD), 1.0)


class TestStepsAvailable(unittest.TestCase):
    def test_move_steps_equal_mps(self):
        unit = make_unit(data.Nationality.BRITISH, 0, 0, mps=6, order=units.Order.MOVE)
        self.assertEqual(movement.steps_available(unit), 6)

    def test_travel_doubles_reach(self):
        unit = make_unit(data.Nationality.BRITISH, 0, 0, mps=6, order=units.Order.TRAVEL)
        self.assertEqual(movement.steps_available(unit), 12)

    def test_assault_reduces_reach(self):
        unit = make_unit(data.Nationality.BRITISH, 0, 0, mps=6, order=units.Order.ASSAULT)
        self.assertEqual(movement.steps_available(unit), 4)


class TestAdvanceUnitBasicMove(unittest.TestCase):
    def test_moves_toward_destination_one_axis_priority(self):
        b = make_board(20, 20)
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=3, dest_x=9, dest_y=5)
        movement.advance_unit(unit, b, empty_flags(b))
        self.assertEqual((unit.x, unit.y), (8, 5))

    def test_stops_at_destination_without_wasting_extra_steps(self):
        b = make_board(20, 20)
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=10, dest_x=6, dest_y=5)
        movement.advance_unit(unit, b, empty_flags(b))
        self.assertEqual((unit.x, unit.y), (6, 5))

    def test_no_op_without_destination(self):
        b = make_board(20, 20)
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=6)
        movement.advance_unit(unit, b, empty_flags(b))
        self.assertEqual((unit.x, unit.y), (5, 5))

    def test_no_op_for_hold_order(self):
        b = make_board(20, 20)
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=6, order=units.Order.HOLD,
                          dest_x=15, dest_y=5)
        movement.advance_unit(unit, b, empty_flags(b))
        self.assertEqual((unit.x, unit.y), (5, 5))

    def test_larger_delta_axis_moves_first(self):
        b = make_board(20, 20)
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=1, dest_x=15, dest_y=6)
        movement.advance_unit(unit, b, empty_flags(b))
        self.assertEqual((unit.x, unit.y), (6, 5))


class TestAdvanceUnitBlocking(unittest.TestCase):
    def test_sea_stops_movement(self):
        b = make_board(20, 20, sea_cells={(9, 5), (9, 6)})
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=10, dest_x=12, dest_y=5)
        movement.advance_unit(unit, b, empty_flags(b))
        # anchor x=8 would cover column 9 (sea) too, so it halts one cell earlier
        self.assertEqual((unit.x, unit.y), (7, 5))

    def test_off_board_stops_movement(self):
        b = make_board(10, 10)
        unit = make_unit(data.Nationality.BRITISH, 7, 5, mps=10, dest_x=9, dest_y=5)
        movement.advance_unit(unit, b, empty_flags(b))
        # width=10 -> max valid top-left x for a 2x2 footprint is 8
        self.assertEqual((unit.x, unit.y), (8, 5))

    def test_other_units_footprint_blocks_movement(self):
        b = make_board(20, 20)
        blocker = make_unit(data.Nationality.GERMAN, 9, 5, index=1)
        flags = zoc_supply.build_flag_grid([blocker], b)
        mover = make_unit(data.Nationality.BRITISH, 5, 5, mps=10, dest_x=12, dest_y=5)
        movement.advance_unit(mover, b, flags)
        self.assertEqual((mover.x, mover.y), (7, 5))


class TestContactStop(unittest.TestCase):
    def test_move_order_halts_on_enemy_contact(self):
        b = make_board(20, 20)
        enemy = make_unit(data.Nationality.GERMAN, 10, 5, index=1)
        flags = zoc_supply.build_flag_grid([enemy], b)
        mover = make_unit(data.Nationality.BRITISH, 5, 5, mps=10, dest_x=15, dest_y=5)
        movement.advance_unit(mover, b, flags)
        # enemy ZOC covers x=9 (footprint 10-11, orthogonal neighbour x=9);
        # mover should halt the instant its footprint enters that ZOC.
        self.assertTrue(any(flags.has_zoc(data.Side.AXIS, cx, cy) for cx, cy in mover.footprint_cells()))
        self.assertNotEqual((mover.x, mover.y), (15, 5))

    def test_assault_order_also_halts_on_contact(self):
        b = make_board(20, 20)
        enemy = make_unit(data.Nationality.GERMAN, 10, 5, index=1)
        flags = zoc_supply.build_flag_grid([enemy], b)
        mover = make_unit(data.Nationality.BRITISH, 5, 5, mps=10, order=units.Order.ASSAULT,
                           dest_x=15, dest_y=5)
        movement.advance_unit(mover, b, flags)
        self.assertNotEqual((mover.x, mover.y), (15, 5))


class TestTravel(unittest.TestCase):
    def test_cannot_start_travel_without_road_access(self):
        b = make_board(20, 20)
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=6, order=units.Order.TRAVEL,
                          dest_x=15, dest_y=5)
        movement.advance_unit(unit, b, empty_flags(b))
        self.assertFalse(unit.travel)
        self.assertEqual((unit.x, unit.y), (5, 5))

    def test_starting_travel_collapses_footprint_and_moves_at_double_reach(self):
        b = make_board(20, 20, road_cells={(5, 5)})
        # dest is farther than this turn's budget so travel is still en route
        # afterwards, letting us check the mid-route 1x1/double-reach state.
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=6, order=units.Order.TRAVEL,
                          dest_x=30, dest_y=5)
        movement.advance_unit(unit, b, empty_flags(b))
        self.assertTrue(unit.travel)
        self.assertEqual(unit.footprint_size, 1)
        self.assertEqual((unit.x, unit.y), (17, 5))  # 6 mps / 0.5 cost = 12 steps

    def test_reforms_to_2x2_on_arrival_when_not_caught(self):
        b = make_board(20, 20, road_cells={(5, 5)})
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=4, order=units.Order.TRAVEL,
                          dest_x=13, dest_y=5)
        movement.advance_unit(unit, b, empty_flags(b))
        self.assertEqual((unit.x, unit.y), (13, 5))
        self.assertFalse(unit.travel)
        self.assertFalse(unit.caught)

    def test_stays_1x1_and_flagged_caught_on_enemy_contact_while_travelling(self):
        b = make_board(20, 20, road_cells={(5, 5)})
        enemy = make_unit(data.Nationality.GERMAN, 10, 5, index=1)
        flags = zoc_supply.build_flag_grid([enemy], b)
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=6, order=units.Order.TRAVEL,
                          dest_x=17, dest_y=5)
        movement.advance_unit(unit, b, flags)
        self.assertTrue(unit.caught)
        self.assertTrue(unit.travel)
        self.assertEqual(unit.footprint_size, 1)
        self.assertNotEqual((unit.x, unit.y), (17, 5))

    def test_travel_continues_across_turns_when_not_finished(self):
        b = make_board(20, 20, road_cells={(5, 5)})
        unit = make_unit(data.Nationality.BRITISH, 5, 5, mps=2, order=units.Order.TRAVEL,
                          dest_x=17, dest_y=5)
        movement.advance_unit(unit, b, empty_flags(b))
        self.assertTrue(unit.travel)
        self.assertNotEqual((unit.x, unit.y), (17, 5))
        first_stop = (unit.x, unit.y)

        movement.advance_unit(unit, b, empty_flags(b))
        self.assertNotEqual((unit.x, unit.y), first_stop)


if __name__ == "__main__":
    unittest.main()
