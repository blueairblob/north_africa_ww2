import unittest

from desert_rats import board as board_mod
from desert_rats import combat, data, units, zoc_supply


def make_board(width=20, height=20):
    grid = tuple(tuple(board_mod.DESERT for _ in range(width)) for _ in range(height))
    legend = {board_mod.DESERT: board_mod.TerrainInfo("Desert", "confirmed")}
    return board_mod.Board(width=width, height=height, grid=grid, legend=legend)


def make_unit(nationality, x, y, strength=100, efficiency=100, caught=False,
              order=units.Order.ASSAULT, index=0):
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
        efficiency=efficiency,
        order=order,
        caught=caught,
    )


def empty_flags(board):
    return zoc_supply.FlagGrid(
        width=board.width,
        height=board.height,
        zoc={data.Side.BRITISH: frozenset(), data.Side.AXIS: frozenset()},
        occupied={data.Side.BRITISH: frozenset(), data.Side.AXIS: frozenset()},
    )


class TestEffectivePower(unittest.TestCase):
    def test_full_efficiency(self):
        unit = make_unit(data.Nationality.BRITISH, 0, 0, strength=100, efficiency=100)
        self.assertEqual(combat.effective_power(unit), 100)

    def test_half_efficiency_halves_power(self):
        unit = make_unit(data.Nationality.BRITISH, 0, 0, strength=100, efficiency=50)
        self.assertEqual(combat.effective_power(unit), 50)

    def test_zero_efficiency_is_zero_power(self):
        unit = make_unit(data.Nationality.BRITISH, 0, 0, strength=200, efficiency=0)
        self.assertEqual(combat.effective_power(unit), 0)


class TestPressureModel(unittest.TestCase):
    """The recovered per-unit combat model (BUILD_SPEC.md §5.5 addendum):
    pressure accumulates from adjacent enemies; value = pressure*100//strength
    tested against morale (or the fixed 20 for combat-class-10 units); at or
    above threshold: -10 efficiency, forced Hold, retreat attempt, x1.5
    escalation when trapped.
    """

    def test_pressure_accumulates_from_adjacent_enemy(self):
        u = make_unit(data.Nationality.BRITISH, 0, 0)
        e = make_unit(data.Nationality.GERMAN, 2, 0, strength=100, efficiency=100)
        combat.apply_combat_pressure([u], [u, e])
        self.assertEqual(u.pressure, 100 // combat.PRESSURE_INFLOW_DIVISOR)

    def test_pressure_resets_out_of_contact(self):
        u = make_unit(data.Nationality.BRITISH, 0, 0)
        u.pressure = 40
        combat.apply_combat_pressure([u], [u])
        self.assertEqual(u.pressure, 0)

    def test_pressure_caps_at_255(self):
        u = make_unit(data.Nationality.BRITISH, 0, 0)
        u.pressure = 250
        e = make_unit(data.Nationality.GERMAN, 2, 0, strength=200, efficiency=100)
        combat.apply_combat_pressure([u], [u, e])
        self.assertEqual(u.pressure, combat.PRESSURE_CAP)

    def test_below_threshold_no_effect(self):
        u = make_unit(data.Nationality.BRITISH, 0, 0, strength=100)
        u.type = 12          # not the class-10 fixed-threshold override
        u.morale = 50
        u.pressure = 49  # value 49 < morale 50
        board = make_board()
        cracked = combat.resolve_pressure(u, [u], board)
        self.assertFalse(cracked)
        self.assertEqual(u.efficiency, 100)

    def test_at_threshold_loses_10_and_holds(self):
        u = make_unit(data.Nationality.BRITISH, 5, 5, strength=100, efficiency=100)
        u.morale = 50
        u.order = units.Order.MOVE
        u.pressure = 50  # value 50 >= morale 50
        board = make_board()
        cracked = combat.resolve_pressure(u, [u], board)
        self.assertTrue(cracked)
        self.assertEqual(u.efficiency, 90)
        self.assertIs(u.order, units.Order.HOLD)

    def test_class_10_uses_fixed_threshold_20(self):
        u = make_unit(data.Nationality.BRITISH, 5, 5, strength=100)
        u.type = combat.ARMOUR_COMBAT_CLASS
        u.morale = 90  # would NOT crack on morale; must crack on the fixed 20
        u.pressure = 20
        self.assertEqual(combat.pressure_threshold(u), combat.ARMOUR_FIXED_THRESHOLD)
        cracked = combat.resolve_pressure(u, [u], make_board())
        self.assertTrue(cracked)

    def test_caught_unit_takes_double_loss(self):
        u = make_unit(data.Nationality.BRITISH, 5, 5, strength=100, caught=True)
        u.travel = True
        u.morale = 10
        u.pressure = 50
        combat.resolve_pressure(u, [u], make_board())
        self.assertEqual(u.efficiency, 100 - combat.CAUGHT_ON_ROAD_LOSS)

    def test_cracked_unit_retreats_away_from_enemy(self):
        u = make_unit(data.Nationality.BRITISH, 5, 5, strength=100)
        u.morale = 10
        u.pressure = 50
        e = make_unit(data.Nationality.GERMAN, 3, 5)
        combat.resolve_pressure(u, [u, e], make_board())
        self.assertEqual((u.x, u.y), (6, 5))  # one cell away from the enemy

    def test_trapped_unit_escalates_pressure_by_half(self):
        # Box the unit in with enemies/board edge so no retreat cell exists.
        u = make_unit(data.Nationality.BRITISH, 0, 0, strength=200)
        u.morale = 10
        u.pressure = 100
        blockers = [
            make_unit(data.Nationality.GERMAN, 2, 0),
            make_unit(data.Nationality.GERMAN, 0, 2),
            make_unit(data.Nationality.GERMAN, 2, 2),
        ]
        combat.resolve_pressure(u, [u] + blockers, make_board())
        self.assertEqual(u.pressure, 150)

    def test_efficiency_loss_clamps_at_zero(self):
        u = make_unit(data.Nationality.BRITISH, 5, 5, strength=100, efficiency=5)
        u.morale = 10
        u.pressure = 50
        combat.resolve_pressure(u, [u], make_board())
        self.assertEqual(u.efficiency, 0)
        self.assertTrue(u.is_destroyed)


class TestAdversePosition(unittest.TestCase):
    def test_out_of_supply_is_adverse(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 5, 5)
        unit.supply = 0
        self.assertTrue(combat.is_in_adverse_position(unit, empty_flags(b)))

    def test_in_enemy_zoc_is_adverse(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 5, 5)
        unit.supply = 50
        enemy = make_unit(data.Nationality.GERMAN, 6, 5, index=1)
        flags = zoc_supply.build_flag_grid([enemy], b)
        self.assertTrue(combat.is_in_adverse_position(unit, flags))

    def test_in_supply_and_clear_of_enemy_zoc_is_not_adverse(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 5, 5)
        unit.supply = 50
        self.assertFalse(combat.is_in_adverse_position(unit, empty_flags(b)))


class TestApplyAttrition(unittest.TestCase):
    def test_adverse_units_lose_three_efficiency(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=50)
        unit.supply = 0
        combat.apply_attrition([unit], empty_flags(b))
        self.assertEqual(unit.efficiency, 47)

    def test_safe_units_are_unaffected(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=50)
        unit.supply = 50
        combat.apply_attrition([unit], empty_flags(b))
        self.assertEqual(unit.efficiency, 50)

    def test_destroyed_units_are_skipped(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=0)
        unit.supply = 0
        combat.apply_attrition([unit], empty_flags(b))
        self.assertEqual(unit.efficiency, 0)


class TestRecover(unittest.TestCase):
    def test_recovery_formula(self):
        unit = make_unit(data.Nationality.BRITISH, 0, 0, efficiency=50)
        combat.recover(unit)
        # (100-50)//16 + 1 = 3 + 1 = 4
        self.assertEqual(unit.efficiency, 54)

    def test_recovery_caps_at_100(self):
        unit = make_unit(data.Nationality.BRITISH, 0, 0, efficiency=99)
        combat.recover(unit)
        self.assertEqual(unit.efficiency, 100)

    def test_recovery_at_full_efficiency_stays_capped(self):
        unit = make_unit(data.Nationality.BRITISH, 0, 0, efficiency=100)
        combat.recover(unit)
        self.assertEqual(unit.efficiency, 100)


class TestApplyRecovery(unittest.TestCase):
    def test_safe_units_recover(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=50)
        unit.supply = 50
        combat.apply_recovery([unit], empty_flags(b))
        self.assertEqual(unit.efficiency, 54)

    def test_adverse_units_do_not_recover(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=50)
        unit.supply = 0
        combat.apply_recovery([unit], empty_flags(b))
        self.assertEqual(unit.efficiency, 50)

    def test_destroyed_units_are_skipped(self):
        b = make_board()
        unit = make_unit(data.Nationality.BRITISH, 5, 5, efficiency=0)
        unit.supply = 50
        combat.apply_recovery([unit], empty_flags(b))
        self.assertEqual(unit.efficiency, 0)


if __name__ == "__main__":
    unittest.main()
