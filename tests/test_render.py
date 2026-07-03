import unittest

from desert_rats import board as board_mod
from desert_rats import data, render, units
from desert_rats.victory import VictoryLevel


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


def make_unit(nationality, x, y, designation="Panzer Regt 5", strength=100, mps=6,
              morale=50, efficiency=100, supply=None, order=units.Order.HOLD, index=0):
    return units.Unit(
        oob_index=index,
        nationality=nationality,
        designation=designation,
        division=None,
        name=designation,
        type=10,
        role=0,
        strength=strength,
        morale=morale,
        arrival=0,
        x=x,
        y=y,
        mps=mps,
        efficiency=efficiency,
        supply=supply,
        order=order,
    )


class TestLoadUiStrings(unittest.TestCase):
    def setUp(self):
        self.strings = render.load_ui_strings()

    def test_loads_all_categories(self):
        self.assertEqual(len(self.strings.scenarios), 6)
        self.assertEqual(len(self.strings.orders), 8)
        self.assertEqual(len(self.strings.supply_bands), 7)
        self.assertEqual(len(self.strings.victory_levels), 8)

    def test_clean_strips_trailing_slash_marker(self):
        self.assertEqual(render.clean("M MOVE /"), "M MOVE")
        self.assertEqual(render.clean("A DRAW"), "A DRAW")


class TestOrderLabel(unittest.TestCase):
    def test_matches_menu_order(self):
        strings = render.load_ui_strings()
        self.assertEqual(render.order_label(units.Order.MOVE, strings), "M MOVE")
        self.assertEqual(render.order_label(units.Order.GO_TO_PORT, strings), "P GO TO PORT")
        self.assertEqual(render.order_label(units.Order.HOLD, strings), "H HOLD")


class TestVictoryLevelText(unittest.TestCase):
    def test_every_level_resolves_to_a_distinct_string(self):
        strings = render.load_ui_strings()
        texts = {level: render.victory_level_text(level, strings) for level in VictoryLevel}
        self.assertEqual(len(set(texts.values())), len(VictoryLevel))

    def test_draw_text_is_verbatim(self):
        strings = render.load_ui_strings()
        self.assertEqual(render.victory_level_text(VictoryLevel.DRAW, strings), "A DRAW")


class TestPalette(unittest.TestCase):
    def test_terrain_glyphs(self):
        self.assertEqual(render.terrain_glyph(board_mod.SEA), "~")
        self.assertEqual(render.terrain_glyph(board_mod.ROAD), "=")
        self.assertEqual(render.terrain_glyph(board_mod.DESERT), ".")

    def test_unit_glyph_by_branch(self):
        armour = make_unit(data.Nationality.GERMAN, 0, 0, designation="Panzer Regt 5")
        infantry = make_unit(data.Nationality.BRITISH, 0, 0, designation="Infantry Regt 1")
        self.assertEqual(render.unit_glyph(armour), "A")
        self.assertEqual(render.unit_glyph(infantry), "I")

    def test_ink_differs_by_nationality_even_within_axis(self):
        ink = render.ANSI_INK
        self.assertNotEqual(ink[data.Nationality.GERMAN], ink[data.Nationality.ITALIAN])
        self.assertNotEqual(ink[data.Nationality.GERMAN], ink[data.Nationality.BRITISH])


class TestClampViewportOrigin(unittest.TestCase):
    def test_centres_when_room_available(self):
        b = make_board(30, 30)
        origin = render.clamp_viewport_origin(15, 15, b, size=22)
        self.assertEqual(origin, (4, 4))

    def test_clamps_at_the_low_edge(self):
        b = make_board(30, 30)
        origin = render.clamp_viewport_origin(0, 0, b, size=22)
        self.assertEqual(origin, (0, 0))

    def test_clamps_at_the_high_edge(self):
        b = make_board(30, 30)
        origin = render.clamp_viewport_origin(29, 29, b, size=22)
        self.assertEqual(origin, (8, 8))


class TestRenderViewport(unittest.TestCase):
    def test_plain_grid_shows_terrain_and_unit_glyphs(self):
        b = make_board(10, 10, sea_cells={(0, 0)})
        unit = make_unit(data.Nationality.BRITISH, 5, 5, designation="Panzer Regt 5")
        text = render.render_viewport([unit], b, origin=(0, 0), size=10, use_color=False)
        lines = text.splitlines()
        self.assertEqual(lines[0][0], "~")
        self.assertEqual(lines[5][5], "A")
        self.assertEqual(lines[5][6], "A")  # 2x2 footprint
        self.assertEqual(lines[6][5], "A")
        self.assertEqual(lines[1][1], ".")

    def test_off_board_cells_are_blank(self):
        b = make_board(5, 5)
        text = render.render_viewport([], b, origin=(0, 0), size=10, use_color=False)
        lines = text.splitlines()
        self.assertEqual(lines[0][9], " ")

    def test_destroyed_units_do_not_appear(self):
        b = make_board(10, 10)
        unit = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=0)
        text = render.render_viewport([unit], b, origin=(0, 0), size=10, use_color=False)
        self.assertNotIn("A", text)
        self.assertNotIn("I", text)

    def test_colored_output_includes_ansi_codes(self):
        b = make_board(10, 10)
        unit = make_unit(data.Nationality.BRITISH, 5, 5)
        text = render.render_viewport([unit], b, origin=(0, 0), size=10, use_color=True)
        self.assertIn("\x1b[", text)


class TestFormatUnitReport(unittest.TestCase):
    def test_includes_confirmed_fields(self):
        strings = render.load_ui_strings()
        unit = make_unit(
            data.Nationality.BRITISH, 5, 5, strength=100, mps=6, morale=50, efficiency=90, supply=75
        )
        report = render.format_unit_report(unit, strings)
        self.assertIn("STR 100", report)
        self.assertIn("MPS 6", report)
        self.assertIn("MOR 50", report)
        self.assertIn("EFF 90", report)
        self.assertIn("SUP", report)

    def test_unset_supply_reports_none_band(self):
        strings = render.load_ui_strings()
        unit = make_unit(data.Nationality.BRITISH, 5, 5, supply=None)
        report = render.format_unit_report(unit, strings)
        self.assertIn("SUP NONE", report)


if __name__ == "__main__":
    unittest.main()
