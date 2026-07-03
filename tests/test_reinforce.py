import unittest

from desert_rats import board as board_mod
from desert_rats import data, reinforce, units


def make_desert_board(width=100, height=32):
    grid = tuple(tuple(board_mod.DESERT for _ in range(width)) for _ in range(height))
    legend = {board_mod.DESERT: board_mod.TerrainInfo("Desert", "confirmed")}
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


def make_unit(nationality, x, y, index=0):
    return units.Unit(
        oob_index=index,
        nationality=nationality,
        designation="Existing",
        division=None,
        name="Existing",
        type=10,
        role=0,
        strength=100,
        morale=50,
        arrival=0,
        x=x,
        y=y,
        mps=6,
    )


class TestCampaignClock(unittest.TestCase):
    def test_known_values(self):
        self.assertEqual(reinforce.campaign_clock(0), 0)
        self.assertEqual(reinforce.campaign_clock(1), 1)
        self.assertEqual(reinforce.campaign_clock(3), 1)
        self.assertEqual(reinforce.campaign_clock(4), 2)
        self.assertEqual(reinforce.campaign_clock(6), 2)
        self.assertEqual(reinforce.campaign_clock(7), 3)

    def test_one_day_every_three_turns(self):
        clocks = [reinforce.campaign_clock(t) for t in range(1, 10)]
        # day advances by exactly 1 every 3 turns
        self.assertEqual(clocks, [1, 1, 1, 2, 2, 2, 3, 3, 3])


class TestFindFreeStagingCell(unittest.TestCase):
    def test_returns_base_when_free(self):
        b = make_desert_board(20, 20)
        cell = reinforce.find_free_staging_cell(data.Side.BRITISH, b, set(), base=(10, 10))
        self.assertEqual(cell, (10, 10))

    def test_nudges_away_when_base_is_occupied(self):
        b = make_desert_board(20, 20)
        occupied = set(board_mod.Board.footprint_cells(10, 10, 2))
        cell = reinforce.find_free_staging_cell(data.Side.BRITISH, b, occupied, base=(10, 10))
        self.assertNotEqual(cell, (10, 10))
        new_footprint = set(board_mod.Board.footprint_cells(*cell, 2))
        self.assertFalse(new_footprint & occupied)

    def test_nudges_away_from_sea(self):
        b = make_desert_board(20, 20, )
        sea_grid = tuple(
            tuple(board_mod.SEA if (x, y) in board_mod.Board.footprint_cells(10, 10, 2) else board_mod.DESERT
                  for x in range(20))
            for y in range(20)
        )
        blocked_board = board_mod.Board(
            width=20, height=20, grid=sea_grid,
            legend={board_mod.DESERT: board_mod.TerrainInfo("D", "c"), board_mod.SEA: board_mod.TerrainInfo("S", "c")},
        )
        cell = reinforce.find_free_staging_cell(data.Side.BRITISH, blocked_board, set(), base=(10, 10))
        self.assertNotEqual(cell, (10, 10))
        self.assertTrue(blocked_board.footprint_passable(*cell, 2))

    def test_deterministic(self):
        b = make_desert_board(20, 20)
        occupied = set(board_mod.Board.footprint_cells(10, 10, 2))
        cell1 = reinforce.find_free_staging_cell(data.Side.BRITISH, b, occupied, base=(10, 10))
        cell2 = reinforce.find_free_staging_cell(data.Side.BRITISH, b, occupied, base=(10, 10))
        self.assertEqual(cell1, cell2)


class TestAdmitReinforcements(unittest.TestCase):
    def test_only_arrived_units_are_admitted(self):
        b = make_desert_board()
        oob = make_oob([(data.Nationality.BRITISH, 0), (data.Nationality.BRITISH, 5), (data.Nationality.GERMAN, 10)])
        admitted = reinforce.admit_reinforcements(oob, set(), [], day=5, board=b)
        self.assertEqual({u.oob_index for u in admitted}, {0, 1})

    def test_already_on_board_units_are_skipped(self):
        b = make_desert_board()
        oob = make_oob([(data.Nationality.BRITISH, 0), (data.Nationality.BRITISH, 0)])
        admitted = reinforce.admit_reinforcements(oob, {0}, [], day=0, board=b)
        self.assertEqual({u.oob_index for u in admitted}, {1})

    def test_admitted_units_get_the_given_mps(self):
        b = make_desert_board()
        oob = make_oob([(data.Nationality.BRITISH, 0)])
        admitted = reinforce.admit_reinforcements(oob, set(), [], day=0, board=b, mps=8)
        self.assertEqual(admitted[0].mps, 8)

    def test_default_mps_is_used_when_not_specified(self):
        b = make_desert_board()
        oob = make_oob([(data.Nationality.BRITISH, 0)])
        admitted = reinforce.admit_reinforcements(oob, set(), [], day=0, board=b)
        self.assertEqual(admitted[0].mps, reinforce.DEFAULT_MPS)

    def test_admitted_units_use_their_own_oob_mps_when_not_overridden(self):
        # Unlike the coincidental default=6 case above, this exercises real
        # per-unit sourcing: two units in the same OOB with different mps
        # must be admitted with their own value, not a shared flat one.
        b = make_desert_board()
        roster = tuple(
            data.Unit(
                index=i, nationality=data.Nationality.BRITISH,
                designation=f"Unit {i}", division=None, name=f"Unit {i}",
                x=0, strength=100, type=10, arrival=0, morale=50, role=0,
                mps=mps, mps_confidence="confirmed",
            )
            for i, mps in enumerate([4, 10])
        )
        oob = data.OrderOfBattle(source="test", fields_note="test", units=roster)
        admitted = reinforce.admit_reinforcements(oob, set(), [], day=0, board=b)
        self.assertEqual([u.mps for u in admitted], [4, 10])

    def test_british_units_stage_at_the_east_edge_point(self):
        b = make_desert_board()
        oob = make_oob([(data.Nationality.BRITISH, 0)])
        admitted = reinforce.admit_reinforcements(oob, set(), [], day=0, board=b)
        self.assertEqual((admitted[0].x, admitted[0].y), reinforce.STAGING_POINTS[data.Side.BRITISH])

    def test_axis_units_stage_at_the_west_edge_point(self):
        b = make_desert_board()
        oob = make_oob([(data.Nationality.GERMAN, 0)])
        admitted = reinforce.admit_reinforcements(oob, set(), [], day=0, board=b)
        self.assertEqual((admitted[0].x, admitted[0].y), reinforce.STAGING_POINTS[data.Side.AXIS])

    def test_same_day_arrivals_of_the_same_side_do_not_overlap(self):
        b = make_desert_board()
        oob = make_oob([(data.Nationality.BRITISH, 0), (data.Nationality.BRITISH, 0)])
        admitted = reinforce.admit_reinforcements(oob, set(), [], day=0, board=b)
        self.assertEqual(len(admitted), 2)
        footprint_a = set(admitted[0].footprint_cells())
        footprint_b = set(admitted[1].footprint_cells())
        self.assertFalse(footprint_a & footprint_b)

    def test_existing_units_at_the_staging_point_force_a_nudge(self):
        b = make_desert_board()
        occupying_unit = make_unit(data.Nationality.BRITISH, *reinforce.STAGING_POINTS[data.Side.BRITISH])
        oob = make_oob([(data.Nationality.BRITISH, 0)])
        admitted = reinforce.admit_reinforcements(oob, set(), [occupying_unit], day=0, board=b)
        self.assertNotEqual((admitted[0].x, admitted[0].y), reinforce.STAGING_POINTS[data.Side.BRITISH])
        self.assertFalse(set(admitted[0].footprint_cells()) & set(occupying_unit.footprint_cells()))


if __name__ == "__main__":
    unittest.main()
