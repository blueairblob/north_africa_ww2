import unittest

from desert_rats import board


class TestLoadBoard(unittest.TestCase):
    def setUp(self):
        self.board = board.load_board()

    def test_dimensions_match_spec(self):
        self.assertEqual(self.board.width, 100)
        self.assertEqual(self.board.height, 32)
        self.assertEqual(len(self.board.grid), 32)
        self.assertTrue(all(len(row) == 100 for row in self.board.grid))

    def test_known_cells(self):
        self.assertEqual(self.board.terrain_at(0, 10), board.SEA)
        self.assertEqual(self.board.terrain_at(25, 3), board.ESCARPMENT)
        self.assertEqual(self.board.terrain_at(23, 2), board.ROAD)

    def test_top_row_is_entirely_sea(self):
        self.assertTrue(all(self.board.terrain_at(x, 0) == board.SEA for x in range(100)))

    def test_legend_covers_every_terrain_type_present_in_the_grid(self):
        present = {v for row in self.board.grid for v in row}
        self.assertTrue(present.issubset(self.board.legend.keys()))
        # Code-verified logic-type space is 0..8 (see data/terrain_logic.json)
        self.assertEqual(present, set(range(9)))

    def test_terrain_at_out_of_bounds_raises(self):
        with self.assertRaises(IndexError):
            self.board.terrain_at(100, 0)
        with self.assertRaises(IndexError):
            self.board.terrain_at(0, -1)

    def test_in_bounds(self):
        self.assertTrue(self.board.in_bounds(0, 0))
        self.assertTrue(self.board.in_bounds(99, 31))
        self.assertFalse(self.board.in_bounds(100, 0))
        self.assertFalse(self.board.in_bounds(0, 32))
        self.assertFalse(self.board.in_bounds(-1, 0))


class TestPassability(unittest.TestCase):
    def setUp(self):
        self.board = board.load_board()

    def test_sea_is_not_passable(self):
        self.assertFalse(self.board.is_passable(0, 10))

    def test_land_is_passable(self):
        self.assertTrue(self.board.terrain_at(13, 10) != board.SEA)
        self.assertTrue(self.board.is_passable(13, 10))

    def test_is_road(self):
        self.assertTrue(self.board.is_road(23, 2))
        self.assertFalse(self.board.is_road(0, 10))

    def test_off_board_is_not_passable(self):
        self.assertFalse(self.board.is_passable(-1, 0))
        self.assertFalse(self.board.is_passable(100, 0))


class TestFootprint(unittest.TestCase):
    def setUp(self):
        self.board = board.load_board()

    def test_1x1_footprint_is_a_single_cell(self):
        self.assertEqual(self.board.footprint_cells(5, 5, size=1), ((5, 5),))

    def test_2x2_footprint_covers_four_cells(self):
        cells = self.board.footprint_cells(5, 5, size=2)
        self.assertEqual(set(cells), {(5, 5), (6, 5), (5, 6), (6, 6)})

    def test_invalid_footprint_size_raises(self):
        with self.assertRaises(ValueError):
            self.board.footprint_cells(0, 0, size=3)

    def test_footprint_passable_false_when_any_cell_is_sea(self):
        # (21,0) is sea while (22,1) is land -> a 2x2 anchored here straddles the coast
        self.assertEqual(self.board.terrain_at(21, 0), board.SEA)
        self.assertNotEqual(self.board.terrain_at(22, 1), board.SEA)
        self.assertFalse(self.board.footprint_passable(21, 0, size=2))

    def test_footprint_passable_true_on_open_land(self):
        self.assertTrue(self.board.footprint_passable(13, 10, size=2))

    def test_footprint_passable_false_off_board(self):
        self.assertFalse(self.board.footprint_passable(99, 31, size=2))


if __name__ == "__main__":
    unittest.main()
