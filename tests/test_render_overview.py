import unittest

from desert_rats import board as board_mod
from desert_rats import data, units

try:
    from desert_rats.render import overview as render_overview
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def make_board(width=30, height=30, sea_cells=(), escarpment_cells=()):
    sea = set(sea_cells)
    escarpment = set(escarpment_cells)

    def terrain(x, y):
        if (x, y) in sea:
            return board_mod.SEA
        if (x, y) in escarpment:
            return 2
        return board_mod.DESERT

    grid = tuple(tuple(terrain(x, y) for x in range(width)) for y in range(height))
    legend = {
        board_mod.DESERT: board_mod.TerrainInfo("Desert", "confirmed"),
        board_mod.SEA: board_mod.TerrainInfo("Sea", "confirmed"),
        2: board_mod.TerrainInfo("Escarpment", "likely"),
    }
    return board_mod.Board(width=width, height=height, grid=grid, legend=legend)


def make_unit(nationality, x, y, index=0):
    return units.Unit(
        oob_index=index, nationality=nationality, designation="Test Unit",
        division=None, name="Test Unit", type=10, role=0, strength=100,
        morale=50, arrival=0, x=x, y=y, mps=6, efficiency=100,
    )


@unittest.skipUnless(PIL_AVAILABLE, "Pillow not installed")
class TestRenderOverviewImage(unittest.TestCase):
    def test_image_dimensions_match_board_times_cell_px(self):
        b = make_board(width=20, height=10)
        img = render_overview.render_overview_image([], b, cell_px=5)
        self.assertEqual(img.size, (100, 50))

    def test_sea_and_desert_use_the_documented_legend_colours(self):
        b = make_board(width=4, height=4, sea_cells=[(0, 0)])
        img = render_overview.render_overview_image([], b, cell_px=10)
        self.assertEqual(img.getpixel((5, 5)), render_overview.TERRAIN_LEGEND_COLOUR[board_mod.SEA])
        self.assertEqual(img.getpixel((35, 35)), render_overview.TERRAIN_LEGEND_COLOUR[board_mod.DESERT])

    def test_escarpment_gets_its_own_legend_colour(self):
        b = make_board(width=4, height=4, escarpment_cells=[(1, 1)])
        img = render_overview.render_overview_image([], b, cell_px=10)
        self.assertEqual(img.getpixel((15, 15)), render_overview.TERRAIN_LEGEND_COLOUR[2])

    def test_units_are_drawn_as_dots_coloured_by_nationality(self):
        b = make_board(width=10, height=10)
        u_brit = make_unit(data.Nationality.BRITISH, 1, 1, index=0)
        u_german = make_unit(data.Nationality.GERMAN, 6, 6, index=1)
        img = render_overview.render_overview_image([u_brit, u_german], b, cell_px=10)
        brit_px = img.getpixel((int(2.0 * 10), int(2.0 * 10)))
        german_px = img.getpixel((int(7.0 * 10), int(7.0 * 10)))
        self.assertEqual(brit_px, render_overview.NATION_DOT_COLOUR[data.Nationality.BRITISH])
        self.assertEqual(german_px, render_overview.NATION_DOT_COLOUR[data.Nationality.GERMAN])

    def test_destroyed_units_are_not_drawn(self):
        b = make_board(width=10, height=10)
        u = make_unit(data.Nationality.BRITISH, 1, 1, index=0)
        u.efficiency = 0
        img = render_overview.render_overview_image([u], b, cell_px=10)
        px = img.getpixel((int(2.0 * 10), int(2.0 * 10)))
        self.assertNotEqual(px, render_overview.NATION_DOT_COLOUR[data.Nationality.BRITISH])

    def test_labels_off_by_default_does_not_error_and_matches_no_label_output(self):
        b = make_board(width=100, height=32)
        img_default = render_overview.render_overview_image([], b, cell_px=4)
        img_explicit_off = render_overview.render_overview_image([], b, cell_px=4, labels=False)
        self.assertEqual(list(img_default.getdata()), list(img_explicit_off.getdata()))

    def test_labels_true_changes_the_image(self):
        b = make_board(width=100, height=32)
        img_off = render_overview.render_overview_image([], b, cell_px=4)
        img_on = render_overview.render_overview_image([], b, cell_px=4, labels=True)
        self.assertNotEqual(list(img_off.getdata()), list(img_on.getdata()))

    def test_custom_town_columns_override_the_default_set(self):
        b = make_board(width=100, height=32)
        img_default_labels = render_overview.render_overview_image([], b, cell_px=4, labels=True)
        img_custom_labels = render_overview.render_overview_image(
            [], b, cell_px=4, labels=True, town_columns={"Nowhere": 50}
        )
        self.assertNotEqual(list(img_default_labels.getdata()), list(img_custom_labels.getdata()))

    def test_save_overview_image_writes_a_real_png(self):
        import tempfile
        import os

        b = make_board(width=10, height=10)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "overview.png")
            returned = render_overview.save_overview_image([], b, path, cell_px=5)
            self.assertEqual(returned, path)
            with Image.open(path) as reopened:
                reopened.verify()


if __name__ == "__main__":
    unittest.main()
