import unittest

from desert_rats import board as board_mod
from desert_rats import data, units, zoc_supply


def make_board(width, height, sea_cells=()):
    sea = set(sea_cells)
    grid = tuple(
        tuple(board_mod.SEA if (x, y) in sea else board_mod.DESERT for x in range(width))
        for y in range(height)
    )
    legend = {
        board_mod.DESERT: board_mod.TerrainInfo("Desert (open)", "confirmed"),
        board_mod.SEA: board_mod.TerrainInfo("Sea", "confirmed"),
    }
    return board_mod.Board(width=width, height=height, grid=grid, legend=legend)


def make_unit(nationality, x, y, index=0, efficiency=100, travel=False):
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
        travel=travel,
    )


class TestBuildFlagGrid(unittest.TestCase):
    def test_footprint_and_orthogonal_neighbours_are_tagged(self):
        b = make_board(10, 10)
        unit = make_unit(data.Nationality.BRITISH, 5, 5)
        flags = zoc_supply.build_flag_grid([unit], b)

        footprint = {(5, 5), (6, 5), (5, 6), (6, 6)}
        expected_neighbours = {(4, 5), (5, 4), (7, 5), (6, 4), (4, 6), (5, 7), (7, 6), (6, 7)}
        expected_zoc = footprint | expected_neighbours

        self.assertEqual(set(flags.zoc[data.Side.BRITISH]), expected_zoc)
        self.assertEqual(set(flags.occupied[data.Side.BRITISH]), footprint)
        self.assertEqual(len(flags.zoc[data.Side.BRITISH]), 12)

    def test_diagonal_cells_are_not_zoc(self):
        b = make_board(10, 10)
        unit = make_unit(data.Nationality.GERMAN, 5, 5)
        flags = zoc_supply.build_flag_grid([unit], b)
        self.assertFalse(flags.has_zoc(data.Side.AXIS, 4, 4))
        self.assertFalse(flags.has_zoc(data.Side.AXIS, 7, 7))

    def test_destroyed_units_are_excluded(self):
        b = make_board(10, 10)
        unit = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=0)
        flags = zoc_supply.build_flag_grid([unit], b)
        self.assertEqual(flags.occupied[data.Side.BRITISH], frozenset())
        self.assertEqual(flags.zoc[data.Side.BRITISH], frozenset())

    def test_sides_are_independent(self):
        b = make_board(10, 10)
        british = make_unit(data.Nationality.BRITISH, 1, 1, index=0)
        german = make_unit(data.Nationality.GERMAN, 8, 8, index=1)
        flags = zoc_supply.build_flag_grid([british, german], b)
        self.assertTrue(flags.is_occupied_by(data.Side.BRITISH, 1, 1))
        self.assertFalse(flags.is_occupied_by(data.Side.AXIS, 1, 1))
        self.assertTrue(flags.is_occupied_by(data.Side.AXIS, 8, 8))


class TestTraceSupplyDistance(unittest.TestCase):
    def test_open_board_distance_is_from_the_nearest_footprint_edge(self):
        b = make_board(8, 2)  # edge_x = 7
        unit = make_unit(data.Nationality.BRITISH, 0, 0)  # footprint x in {0,1}
        flags = zoc_supply.build_flag_grid([unit], b)
        # nearest footprint column to the edge is x=1 -> 7 - 1 = 6 steps
        self.assertEqual(zoc_supply.trace_supply_distance(unit, b, flags), 6)

    def test_axis_traces_to_the_west_edge(self):
        b = make_board(8, 2)
        unit = make_unit(data.Nationality.GERMAN, 6, 0)  # footprint x in {6,7}
        flags = zoc_supply.build_flag_grid([unit], b)
        # nearest footprint column to x=0 is x=6 -> 6 steps
        self.assertEqual(zoc_supply.trace_supply_distance(unit, b, flags), 6)

    def test_footprint_already_touching_edge_is_zero(self):
        b = make_board(8, 2)
        unit = make_unit(data.Nationality.BRITISH, 6, 0)  # covers x=6,7 -> touches edge_x=7
        flags = zoc_supply.build_flag_grid([unit], b)
        self.assertEqual(zoc_supply.trace_supply_distance(unit, b, flags), 0)

    def test_full_width_enemy_occupation_blocks_the_path(self):
        b = make_board(8, 4)
        unit = make_unit(data.Nationality.BRITISH, 0, 0)
        blockers = [make_unit(data.Nationality.GERMAN, 4, y, index=i) for i, y in enumerate((0, 2))]
        flags = zoc_supply.build_flag_grid(blockers, b)
        # sanity: column x=4 fully occupied by Axis across all 4 rows
        self.assertTrue(all(flags.is_occupied_by(data.Side.AXIS, 4, y) for y in range(4)))
        self.assertIsNone(zoc_supply.trace_supply_distance(unit, b, flags))

    def test_enemy_zoc_alone_blocks_the_path_without_occupation(self):
        b = make_board(8, 4)
        unit = make_unit(data.Nationality.BRITISH, 0, 0)
        flags = zoc_supply.FlagGrid(
            width=b.width,
            height=b.height,
            zoc={data.Side.AXIS: frozenset((4, y) for y in range(4)), data.Side.BRITISH: frozenset()},
            occupied={data.Side.AXIS: frozenset(), data.Side.BRITISH: frozenset()},
        )
        self.assertIsNone(zoc_supply.trace_supply_distance(unit, b, flags))

    def test_sea_blocks_the_path(self):
        b = make_board(8, 2, sea_cells={(4, 0), (4, 1)})
        unit = make_unit(data.Nationality.BRITISH, 0, 0)
        flags = zoc_supply.build_flag_grid([unit], b)
        self.assertIsNone(zoc_supply.trace_supply_distance(unit, b, flags))


class TestSupplyCurve(unittest.TestCase):
    def test_distance_zero_is_full_supply(self):
        # Oracle-verified: distances 0-1 sit in a FULL-supply band (100)
        # that precedes the 31-value curve entirely.
        self.assertEqual(zoc_supply.supply_level(0), 100)

    def test_supply_bands_oracle_verified(self):
        # Verified against the original routine under emulation:
        # a = min(d+2,127)>>2; a==0 -> 100 (full); else curve[a-1].
        self.assertEqual(zoc_supply.supply_level(0), 100)
        self.assertEqual(zoc_supply.supply_level(1), 100)
        self.assertEqual(zoc_supply.supply_level(2), 90)
        self.assertEqual(zoc_supply.supply_level(5), 90)
        self.assertEqual(zoc_supply.supply_level(6), 80)
        self.assertEqual(zoc_supply.supply_level(10), 75)
        self.assertEqual(zoc_supply.supply_level(30), 50)
        self.assertEqual(zoc_supply.supply_level(60), 43)
        self.assertEqual(zoc_supply.supply_level(127), 35)
        self.assertEqual(zoc_supply.supply_level(500), 35)

    def test_clamps_to_the_last_entry_for_far_distances(self):
        far = zoc_supply.supply_level(1000)
        self.assertEqual(far, zoc_supply.SUPPLY_CURVE[-1])
        self.assertEqual(zoc_supply.supply_level(122), far)  # saturation begins at d=122 (oracle-verified band arithmetic)


class TestSupplyBand(unittest.TestCase):
    def test_bands_across_the_range(self):
        cases = [
            (0, zoc_supply.NONE),
            (1, zoc_supply.V_LOW),
            (39, zoc_supply.V_LOW),
            (40, zoc_supply.LOW),
            (49, zoc_supply.LOW),
            (50, zoc_supply.Q_LOW),
            (59, zoc_supply.Q_LOW),
            (60, zoc_supply.FAIR),
            (69, zoc_supply.FAIR),
            (70, zoc_supply.GOOD),
            (79, zoc_supply.GOOD),
            (80, zoc_supply.V_GOOD),
            (90, zoc_supply.V_GOOD),
        ]
        for level, expected in cases:
            with self.subTest(level=level):
                self.assertEqual(zoc_supply.supply_band(level), expected)


class TestComputeSupply(unittest.TestCase):
    def test_sets_supply_for_every_living_unit(self):
        b = make_board(8, 2)
        unit = make_unit(data.Nationality.BRITISH, 0, 0)
        zoc_supply.compute_supply([unit], b)
        self.assertEqual(unit.supply, zoc_supply.supply_level(6))

    def test_out_of_supply_unit_gets_zero(self):
        b = make_board(8, 4)
        cut_off = make_unit(data.Nationality.BRITISH, 0, 0, index=0)
        wall = [
            make_unit(data.Nationality.GERMAN, 4, 0, index=1),
            make_unit(data.Nationality.GERMAN, 4, 2, index=2),
        ]
        zoc_supply.compute_supply([cut_off] + wall, b)
        self.assertEqual(cut_off.supply, 0)
        self.assertTrue(zoc_supply.is_out_of_supply(cut_off))

    def test_destroyed_units_are_skipped(self):
        b = make_board(8, 2)
        dead = make_unit(data.Nationality.BRITISH, 0, 0, efficiency=0)
        zoc_supply.compute_supply([dead], b)
        self.assertIsNone(dead.supply)


if __name__ == "__main__":
    unittest.main()
