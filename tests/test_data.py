import unittest

from desert_rats import data


class TestLoadMasterOob(unittest.TestCase):
    def setUp(self):
        self.oob = data.load_master_oob()

    def test_loads_all_128_units(self):
        self.assertEqual(len(self.oob), 128)

    def test_indices_are_contiguous_and_match_position(self):
        for position, unit in enumerate(self.oob):
            self.assertEqual(unit.index, position)

    def test_by_index_returns_matching_unit(self):
        unit = self.oob.by_index(0)
        self.assertEqual(unit.designation, "Panzer Regt 5")
        self.assertEqual(unit.division, "5th Light Division")
        self.assertEqual(unit.nationality, data.Nationality.GERMAN)

    def test_unit_with_no_division_is_none(self):
        unit = self.oob.by_index(4)
        self.assertEqual(unit.designation, "Mg Battalion 8")
        self.assertIsNone(unit.division)

    def test_side_derivation(self):
        german = self.oob.by_index(0)
        italian = self.oob.by_index(6)
        british = self.oob.by_index(52)
        self.assertEqual(german.side, data.Side.AXIS)
        self.assertEqual(italian.side, data.Side.AXIS)
        self.assertEqual(british.side, data.Side.BRITISH)

    def test_by_side_partitions_the_whole_roster(self):
        british = self.oob.by_side(data.Side.BRITISH)
        axis = self.oob.by_side(data.Side.AXIS)
        self.assertEqual(len(british) + len(axis), len(self.oob))
        self.assertTrue(all(u.nationality is data.Nationality.BRITISH for u in british))
        self.assertTrue(all(u.side is data.Side.AXIS for u in axis))

    def test_by_nationality_matches_by_side_for_axis(self):
        axis = set(u.index for u in self.oob.by_side(data.Side.AXIS))
        german = set(u.index for u in self.oob.by_nationality(data.Nationality.GERMAN))
        italian = set(u.index for u in self.oob.by_nationality(data.Nationality.ITALIAN))
        self.assertEqual(axis, german | italian)

    def test_arriving_by_gates_on_arrival_day(self):
        day_zero = self.oob.arriving_by(0)
        self.assertTrue(all(u.arrival <= 0 for u in day_zero))
        self.assertTrue(any(u.arrival == 0 for u in day_zero))

        full_campaign = self.oob.arriving_by(624)
        self.assertEqual(len(full_campaign), len(self.oob))

    def test_arriving_by_is_monotonically_non_decreasing(self):
        earlier = len(self.oob.arriving_by(10))
        later = len(self.oob.arriving_by(200))
        self.assertLessEqual(earlier, later)

    def test_unit_is_immutable(self):
        unit = self.oob.by_index(0)
        with self.assertRaises(AttributeError):
            unit.strength = 999

    def test_load_rejects_mismatched_count(self, ):
        import json
        import tempfile
        from pathlib import Path

        with open(data.MASTER_OOB_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        raw["count"] = raw["count"] + 1

        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad_oob.json"
            bad_path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(ValueError):
                data.load_master_oob(bad_path)


class TestUnitMps(unittest.TestCase):
    """Every real unit gets a real, positive per-unit mps from
    data/unit_mps.json (not the flat DEFAULT_MPS placeholder) -- see
    data.Unit's docstring and NOTES.md.
    """

    @classmethod
    def setUpClass(cls):
        cls.oob = data.load_master_oob()

    def test_every_unit_has_a_positive_mps(self):
        for unit in self.oob:
            self.assertGreater(unit.mps, 0, unit.name)

    def test_mps_confidence_is_one_of_the_documented_sources(self):
        valid_prefixes = ("confirmed", "type_fallback", "global_fallback")
        for unit in self.oob:
            self.assertTrue(
                unit.mps_confidence.startswith(valid_prefixes),
                f"{unit.name}: unexpected mps_confidence {unit.mps_confidence!r}",
            )

    def test_a_directly_observed_unit_gets_its_confirmed_value(self):
        # Panzer Regt 5, 5th Light Division (oob index 0) is on_map=true
        # with mps=6 in units_scenario_enter_rommel.json.
        unit = self.oob.by_index(0)
        self.assertEqual(unit.mps, 6)
        self.assertEqual(unit.mps_confidence, "confirmed")

    def test_mps_path_override_is_used(self):
        oob = data.load_master_oob(mps_path=data.UNIT_MPS_PATH)
        self.assertEqual(oob.by_index(0).mps, self.oob.by_index(0).mps)


class TestLoadScenarios(unittest.TestCase):
    def setUp(self):
        self.scenarios = data.load_scenarios()

    def test_loads_all_6_scenarios(self):
        self.assertEqual(len(self.scenarios), 6)

    def test_indices_are_1_through_6_in_order(self):
        self.assertEqual([s.index for s in self.scenarios], [1, 2, 3, 4, 5, 6])

    def test_enter_rommel_fields(self):
        enter_rommel = self.scenarios[0]
        self.assertEqual(enter_rommel.name, "Enter Rommel")
        self.assertEqual(enter_rommel.start_day, 1)
        self.assertEqual(enter_rommel.end_day, 31)
        self.assertEqual(enter_rommel.british_objectives, ((50, 3), (76, 3)))
        self.assertEqual(enter_rommel.axis_objectives, ((95, 4), (76, 1)))
        self.assertEqual(enter_rommel.unit_thresholds, {"british": 10, "axis": 10})

    def test_full_campaign_scenario_spans_the_whole_timeline(self):
        full_campaign = self.scenarios[-1]
        self.assertEqual(full_campaign.name, "The Desert War")
        self.assertEqual(full_campaign.start_day, 1)
        self.assertEqual(full_campaign.end_day, 624)


if __name__ == "__main__":
    unittest.main()
