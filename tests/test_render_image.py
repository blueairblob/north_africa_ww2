import unittest

from desert_rats import board as board_mod
from desert_rats import data, units

try:
    from desert_rats.render import image as render_image
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def make_board(width=30, height=30, road_cells=(), sea_cells=()):
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


def make_unit(nationality, x, y, index=0, strength=100, travel=False, caught=False):
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
        mps=6,
        efficiency=100,
        travel=travel,
        caught=caught,
    )


@unittest.skipUnless(PIL_AVAILABLE, "Pillow not installed")
class TestRenderBoardImage(unittest.TestCase):
    def test_full_board_image_has_expected_pixel_dimensions(self):
        b = make_board(width=10, height=8)
        img = render_image.render_board_image([], b, cell_px=4)
        self.assertEqual(img.size, (40, 32))

    def test_sea_cells_are_a_different_colour_from_desert(self):
        b = make_board(width=4, height=4, sea_cells=[(0, 0)])
        img = render_image.render_board_image([], b, cell_px=10)
        sea_pixel = img.getpixel((5, 5))
        desert_pixel = img.getpixel((35, 35))
        self.assertNotEqual(sea_pixel, desert_pixel)
        self.assertEqual(desert_pixel, render_image.PAPER_DESERT)

    def test_only_sea_gets_a_distinct_paper_everything_else_is_desert(self):
        # BUILD_SPEC.md §8: paper is "mostly PAPER 6 = desert yellow" with
        # no other confirmed per-terrain-type colours -- road cells get a
        # line overlay (real position data) but the same desert paper.
        b = make_board(width=3, height=1, road_cells=[(1, 0)])
        img = render_image.render_board_image([], b, cell_px=10)
        corner_off_the_road_line = img.getpixel((11, 1))
        self.assertEqual(corner_off_the_road_line, render_image.PAPER_DESERT)

    def test_units_of_different_nationalities_render_different_colours(self):
        b = make_board(width=10, height=10)
        u_brit = make_unit(data.Nationality.BRITISH, 0, 0, index=0)
        u_german = make_unit(data.Nationality.GERMAN, 4, 4, index=1)
        u_italian = make_unit(data.Nationality.ITALIAN, 7, 7, index=2)
        img = render_image.render_board_image([u_brit, u_german, u_italian], b, cell_px=10)

        colours = {
            img.getpixel((5, 5)),
            img.getpixel((45, 45)),
            img.getpixel((75, 75)),
        }
        self.assertEqual(len(colours), 3, "expected 3 distinct nationality colours")

    def test_a_2x2_unit_covers_a_2x2_cell_block(self):
        b = make_board(width=10, height=10)
        u = make_unit(data.Nationality.BRITISH, 2, 2, index=0)
        img = render_image.render_board_image([u], b, cell_px=10)
        # Sample all four footprint cells' centres -- all should carry the
        # unit's colour, not the desert paper.
        for gx, gy in [(2, 2), (3, 2), (2, 3), (3, 3)]:
            px = img.getpixel((gx * 10 + 5, gy * 10 + 5))
            self.assertNotEqual(px, render_image.PAPER_DESERT)

    def test_a_travelling_1x1_unit_only_covers_one_cell(self):
        b = make_board(width=10, height=10)
        u = make_unit(data.Nationality.BRITISH, 2, 2, index=0, travel=True)
        img = render_image.render_board_image([u], b, cell_px=10)
        self.assertEqual(list(u.footprint_cells()), [(2, 2)])
        neighbour = img.getpixel((3 * 10 + 5, 2 * 10 + 5))
        self.assertEqual(neighbour, render_image.PAPER_DESERT)

    def test_destroyed_units_are_not_drawn(self):
        b = make_board(width=10, height=10)
        u = make_unit(data.Nationality.BRITISH, 2, 2, index=0)
        u.efficiency = 0
        self.assertTrue(u.is_destroyed)
        img = render_image.render_board_image([u], b, cell_px=10)
        px = img.getpixel((2 * 10 + 5, 2 * 10 + 5))
        self.assertEqual(px, render_image.PAPER_DESERT)

    def test_viewport_origin_and_size_crop_the_render(self):
        b = make_board(width=30, height=30)
        img = render_image.render_board_image([], b, origin=(5, 5), size=10, cell_px=4)
        self.assertEqual(img.size, (40, 40))

    def test_save_board_image_writes_a_real_png(self):
        import tempfile
        import os

        b = make_board(width=5, height=5)
        u = make_unit(data.Nationality.BRITISH, 0, 0, index=0)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.png")
            returned = render_image.save_board_image([u], b, path, cell_px=6)
            self.assertEqual(returned, path)
            self.assertTrue(os.path.exists(path))
            with Image.open(path) as reopened:
                reopened.verify()


if __name__ == "__main__":
    unittest.main()
