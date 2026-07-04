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

    def test_escarpment_cells_show_the_real_extracted_tile_pattern(self):
        # See render/image.py's module docstring: this pattern was
        # extracted pixel-for-pixel from a real gameplay screenshot, not
        # guessed -- unlike road/grid lines, this IS a colour claim about
        # the original.
        b = make_board(width=3, height=1)
        b = b.__class__(
            width=b.width, height=b.height,
            grid=tuple(tuple(2 for _ in range(3)) for _ in range(1)),
            legend=b.legend,
        )
        img = render_image.render_board_image([], b, cell_px=8)
        # Row 2 = 0x09 = 00001001 -> col4 set (ink), col1 unset (paper).
        # Sampled away from y=0/x=0 (grid-line border alpha-blends there).
        self.assertEqual(img.getpixel((4, 2)), render_image.ESCARPMENT_INK)
        self.assertEqual(img.getpixel((1, 2)), render_image.PAPER_DESERT)

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


@unittest.skipUnless(PIL_AVAILABLE, "Pillow not installed")
class TestAuthenticRenderModel(unittest.TestCase):
    """The recovered render model (data/render_model.json -- see
    reference/extraction_tools/extract_render_tables.py) applies when
    rendering the real 100x32 board. These tests hold whether or not the
    local-only tile-art file is present: sea's tile is fully inked
    (coverage 1.0) and desert's fully blank (coverage 0.0), so both paths
    produce the same colour for them.
    """

    @classmethod
    def setUpClass(cls):
        from desert_rats import board as b
        cls.board = b.load_board()
        cls.model = render_image._render_model()

    def test_render_model_is_available_in_repo(self):
        self.assertIsNotNone(self.model)

    def test_sea_renders_ink_blue_not_paper(self):
        # Sea = tile 0x0E, all pixels set -> INK blue over yellow paper.
        img = render_image.render_board_image([], self.board, cell_px=8)
        attrs, grid, coverage, tiles = self.model
        # find a deep-sea cell (full-byte 0x0E) away from coastline art
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell == 0x0E:
                    px = img.getpixel((x * 8 + 4, y * 8 + 4))
                    self.assertEqual(px, (0, 0, 162))
                    return
        self.fail("no 0x0E sea cell found in the recovered grid")

    def test_open_desert_renders_paper_yellow(self):
        img = render_image.render_board_image([], self.board, cell_px=8)
        attrs, grid, coverage, tiles = self.model
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell == 0x00:
                    px = img.getpixel((x * 8 + 4, y * 8 + 4))
                    self.assertEqual(px, (210, 210, 0))
                    return
        self.fail("no 0x00 desert cell found in the recovered grid")

    def test_synthetic_boards_do_not_use_the_real_map_model(self):
        # A small synthetic board must fall back to the legacy flat
        # model, not have the real 100x32 map's tiles painted onto it.
        b = make_board(width=4, height=4)
        img = render_image.render_board_image([], b, cell_px=10)
        self.assertEqual(img.getpixel((15, 15)), render_image.PAPER_DESERT)


if __name__ == "__main__":
    unittest.main()
