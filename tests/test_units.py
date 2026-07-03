import unittest

from desert_rats import data, units


class TestOrderEnum(unittest.TestCase):
    def test_values_match_spec_menu_order(self):
        self.assertEqual(units.Order.MOVE, 1)
        self.assertEqual(units.Order.ASSAULT, 2)
        self.assertEqual(units.Order.HOLD, 3)
        self.assertEqual(units.Order.TRAVEL, 4)
        self.assertEqual(units.Order.REPORT, 5)
        self.assertEqual(units.Order.DIVIDE, 6)
        self.assertEqual(units.Order.FORTIFY, 7)
        self.assertEqual(units.Order.GO_TO_PORT, 8)


class TestDeriveBranch(unittest.TestCase):
    def test_armour(self):
        self.assertEqual(units.derive_branch("Panzer Regt 5"), units.Branch.ARMOUR)
        self.assertEqual(units.derive_branch("132nd Armoured Regt"), units.Branch.ARMOUR)
        self.assertEqual(units.derive_branch("1st Army Tank Brigade"), units.Branch.ARMOUR)

    def test_recce_beats_armour_for_armoured_car_units(self):
        self.assertEqual(units.derive_branch("4th SA Armoured Car Regt"), units.Branch.RECCE)
        self.assertEqual(units.derive_branch("Recce Battalion 3"), units.Branch.RECCE)
        self.assertEqual(units.derive_branch("11th Hussars Bn"), units.Branch.RECCE)
        self.assertEqual(
            units.derive_branch("1st Kings Dragoon Guards Bn"), units.Branch.RECCE
        )

    def test_artillery(self):
        self.assertEqual(units.derive_branch("132nd Artillery Regt"), units.Branch.ARTILLERY)
        self.assertEqual(units.derive_branch("A/T Battalion 39"), units.Branch.ARTILLERY)

    def test_infantry(self):
        self.assertEqual(units.derive_branch("Infantry Regt 115"), units.Branch.INFANTRY)
        self.assertEqual(units.derive_branch("8th Bersaglieri Regt"), units.Branch.INFANTRY)
        self.assertEqual(units.derive_branch("185th Parachute Regt"), units.Branch.INFANTRY)
        self.assertEqual(units.derive_branch("22nd Guards Bde"), units.Branch.INFANTRY)
        self.assertEqual(units.derive_branch("Mg Battalion 8"), units.Branch.INFANTRY)

    def test_other_fallback(self):
        self.assertEqual(units.derive_branch("HQ"), units.Branch.OTHER)
        self.assertEqual(units.derive_branch("Supply Unit"), units.Branch.OTHER)
        self.assertEqual(units.derive_branch("Corpo d'Armata X"), units.Branch.OTHER)


class TestUnitFromOob(unittest.TestCase):
    def setUp(self):
        self.oob = data.load_master_oob()

    def test_copies_static_roster_fields(self):
        oob_unit = self.oob.by_index(0)
        unit = units.Unit.from_oob(oob_unit, x=9, y=24, mps=6)
        self.assertEqual(unit.oob_index, 0)
        self.assertEqual(unit.designation, "Panzer Regt 5")
        self.assertEqual(unit.division, "5th Light Division")
        self.assertEqual(unit.nationality, data.Nationality.GERMAN)
        self.assertEqual(unit.strength, oob_unit.strength)
        self.assertEqual(unit.morale, oob_unit.morale)
        self.assertEqual(unit.arrival, oob_unit.arrival)
        self.assertEqual(unit.type, oob_unit.type)
        self.assertEqual(unit.role, oob_unit.role)

    def test_placement_fields_come_from_caller(self):
        unit = units.Unit.from_oob(self.oob.by_index(0), x=9, y=24, mps=6)
        self.assertEqual((unit.x, unit.y), (9, 24))
        self.assertEqual(unit.mps, 6)

    def test_defaults(self):
        unit = units.Unit.from_oob(self.oob.by_index(0), x=0, y=0, mps=6)
        self.assertEqual(unit.efficiency, 100)
        self.assertEqual(unit.order, units.Order.HOLD)
        self.assertFalse(unit.travel)
        self.assertFalse(unit.caught)
        self.assertIsNone(unit.dest_x)
        self.assertIsNone(unit.dest_y)
        self.assertIsNone(unit.supply)

    def test_side_derivation_matches_oob(self):
        for index in (0, 6, 52):
            oob_unit = self.oob.by_index(index)
            unit = units.Unit.from_oob(oob_unit, x=0, y=0, mps=6)
            self.assertEqual(unit.side, oob_unit.side)


class TestUnitRuntimeState(unittest.TestCase):
    def setUp(self):
        oob_unit = data.load_master_oob().by_index(0)
        self.unit = units.Unit.from_oob(oob_unit, x=9, y=24, mps=6)

    def test_is_mutable(self):
        self.unit.x = 10
        self.unit.efficiency = 90
        self.assertEqual(self.unit.x, 10)
        self.assertEqual(self.unit.efficiency, 90)

    def test_footprint_size_toggles_with_travel(self):
        self.assertEqual(self.unit.footprint_size, 2)
        self.unit.travel = True
        self.assertEqual(self.unit.footprint_size, 1)

    def test_footprint_cells_2x2(self):
        self.unit.x, self.unit.y = 5, 5
        self.assertEqual(
            set(self.unit.footprint_cells()), {(5, 5), (6, 5), (5, 6), (6, 6)}
        )

    def test_footprint_cells_1x1_while_travelling(self):
        self.unit.x, self.unit.y = 5, 5
        self.unit.travel = True
        self.assertEqual(self.unit.footprint_cells(), ((5, 5),))

    def test_is_destroyed_at_zero_efficiency(self):
        self.assertFalse(self.unit.is_destroyed)
        self.unit.efficiency = 0
        self.assertTrue(self.unit.is_destroyed)

    def test_is_armour_type_is_independent_of_branch_heuristic(self):
        # unit 6 (Pavia Division) has type==10 (the armour combat-threshold
        # override) despite being an infantry-style formation by name --
        # exactly the divergence BUILD_SPEC.md §3.2 warns about.
        oob_unit = data.load_master_oob().by_index(6)
        pavia = units.Unit.from_oob(oob_unit, x=0, y=0, mps=6)
        self.assertTrue(pavia.is_armour_type)
        self.assertEqual(pavia.branch, units.Branch.OTHER)

        panzer = self.unit
        self.assertTrue(panzer.is_armour_type)
        self.assertEqual(panzer.branch, units.Branch.ARMOUR)


if __name__ == "__main__":
    unittest.main()
