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


class TestResolveAssault(unittest.TestCase):
    def test_stronger_attacker_wins_defender_loses_efficiency(self):
        attacker = make_unit(data.Nationality.BRITISH, 0, 0, strength=200, efficiency=100)
        defender = make_unit(data.Nationality.GERMAN, 1, 0, strength=100, efficiency=100, index=1)
        loser = combat.resolve_assault(attacker, defender)
        self.assertIs(loser, defender)
        self.assertEqual(defender.efficiency, 90)
        self.assertEqual(attacker.efficiency, 100)

    def test_stronger_defender_wins_attacker_loses_efficiency(self):
        attacker = make_unit(data.Nationality.BRITISH, 0, 0, strength=50, efficiency=100)
        defender = make_unit(data.Nationality.GERMAN, 1, 0, strength=200, efficiency=100, index=1)
        loser = combat.resolve_assault(attacker, defender)
        self.assertIs(loser, attacker)
        self.assertEqual(attacker.efficiency, 90)

    def test_loser_order_is_forced_to_hold(self):
        attacker = make_unit(data.Nationality.BRITISH, 0, 0, strength=200, efficiency=100)
        defender = make_unit(data.Nationality.GERMAN, 1, 0, strength=100, efficiency=100, index=1)
        combat.resolve_assault(attacker, defender)
        self.assertEqual(defender.order, units.Order.HOLD)

    def test_tie_produces_no_loser_or_change(self):
        attacker = make_unit(data.Nationality.BRITISH, 0, 0, strength=100, efficiency=100)
        defender = make_unit(data.Nationality.GERMAN, 1, 0, strength=100, efficiency=100, index=1)
        loser = combat.resolve_assault(attacker, defender)
        self.assertIsNone(loser)
        self.assertEqual(attacker.efficiency, 100)
        self.assertEqual(defender.efficiency, 100)

    def test_caught_on_road_doubles_the_loss(self):
        attacker = make_unit(data.Nationality.BRITISH, 0, 0, strength=200, efficiency=100)
        defender = make_unit(
            data.Nationality.GERMAN, 1, 0, strength=100, efficiency=100, caught=True, index=1
        )
        combat.resolve_assault(attacker, defender)
        self.assertEqual(defender.efficiency, 80)

    def test_efficiency_loss_clamps_at_zero(self):
        attacker = make_unit(data.Nationality.BRITISH, 0, 0, strength=200, efficiency=100)
        defender = make_unit(
            data.Nationality.GERMAN, 1, 0, strength=100, efficiency=5, caught=True, index=1
        )
        combat.resolve_assault(attacker, defender)
        self.assertEqual(defender.efficiency, 0)
        self.assertTrue(defender.is_destroyed)


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
