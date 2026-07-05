import unittest

from desert_rats import board, data, packs


class TestPackSystem(unittest.TestCase):
    def tearDown(self):
        packs.set_active_pack(packs.DEFAULT_PACK)

    def test_og_is_the_default_active_pack(self):
        packs._active = None  # force re-resolution
        self.assertEqual(packs.active_pack().name, "og")

    def test_available_packs_lists_both(self):
        names = packs.available_packs()
        self.assertIn("og", names)
        self.assertIn("default", names)

    def test_unknown_pack_raises_with_available_list(self):
        with self.assertRaises(FileNotFoundError):
            packs.load_pack("no_such_pack")

    def test_og_resolves_legacy_data(self):
        og = packs.load_pack("og")
        p = og.resolve("terrain_logic.json")
        self.assertIsNotNone(p)
        self.assertIn("data", p.parts)

    def test_default_overrides_terrain_but_inherits_the_rest(self):
        d = packs.load_pack("default")
        terrain = d.resolve("terrain_logic.json")
        self.assertIn("content_packs", terrain.parts)
        oob = d.resolve("master_oob.json")  # inherited via og -> legacy data
        self.assertIn("data", oob.parts)

    def test_switching_packs_changes_the_board(self):
        packs.set_active_pack("og")
        og_board = board.load_board()
        packs.set_active_pack("default")
        default_board = board.load_board()
        self.assertNotEqual(og_board.grid, default_board.grid)
        # both honour the engine contract
        for b in (og_board, default_board):
            self.assertEqual((b.width, b.height), (100, 32))
            self.assertTrue(all(b.terrain_at(x, 0) == board.SEA for x in range(30)))

    def test_default_map_is_deployment_compatible(self):
        # Every inherited deployment coordinate (2x2 footprint) and both
        # staging areas must be on passable land in the default map.
        packs.set_active_pack("default")
        b = board.load_board()
        deployments = data.load_deployments()
        coords = {(98, 11), (1, 24)}
        for entries in deployments.values():
            coords |= {(e["x"], e["y"]) for e in entries}
        for (x, y) in coords:
            self.assertTrue(
                b.footprint_passable(x, y, size=2),
                f"deployment/staging anchor {(x, y)} not passable in default map",
            )

    def test_render_model_is_pack_scoped(self):
        from desert_rats.render import image
        packs.set_active_pack("og")
        self.assertIsNotNone(image._render_model())
        packs.set_active_pack("default")
        self.assertIsNone(image._render_model())  # default pack: no OG render model


if __name__ == "__main__":
    unittest.main()


class TestAtlasFeatureLayer(unittest.TestCase):
    def tearDown(self):
        packs.set_active_pack(packs.DEFAULT_PACK)

    def test_default_pack_provides_features(self):
        from desert_rats.render import image
        packs.set_active_pack("default")
        f = image._features()
        self.assertIsNotNone(f)
        names = {p["name"] for p in f["points"]}
        self.assertIn("Tobruk", names)
        self.assertIn("Halfaya Pass", names)

    def test_og_pack_has_no_feature_layer(self):
        from desert_rats.render import image
        packs.set_active_pack("og")
        self.assertIsNone(image._features())

    def test_default_map_renders_the_atlas_layer(self):
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")
        from desert_rats.render import image
        packs.set_active_pack("default")
        b = board.load_board()
        img = image.render_board_image([], b, cell_px=8)
        colours = set(img.getdata())
        self.assertIn(image.ATLAS_ROAD, colours)   # connected road strokes
        self.assertIn(image.ATLAS_COAST, colours)  # coastline outline
        self.assertIn(image.ATLAS_INK, colours)    # labels/markers

    def test_default_road_network_is_contiguous(self):
        import json
        from desert_rats import packs as p
        grid = json.loads(
            (p.PACKS_DIR / "default" / "terrain_logic.json").read_text()
        )["logic_type_grid"]
        roads = {(x, y) for y in range(32) for x in range(100) if grid[y][x] == 5}
        seen, comps = set(), 0
        for cell in roads:
            if cell in seen:
                continue
            comps += 1
            stack = [cell]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in seen:
                    continue
                seen.add((cx, cy))
                stack.extend(
                    (cx + dx, cy + dy)
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if (cx + dx, cy + dy) in roads
                )
        self.assertLessEqual(comps, 3, f"road network fragmented: {comps} components")
