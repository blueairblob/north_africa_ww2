import unittest

from desert_rats import data, reinforce
from desert_rats.units import Order, Unit


def unit(nat, strength, order=Order.HOLD, klass=3, role=1, eff=80):
    u = Unit(oob_index=0, nationality=nat, designation="t", division="d",
             name="n", type=12, role=role, mps=10, x=10, y=10,
             strength=strength, morale=50, arrival=0)
    u.order = order
    u.combat_class = klass
    u.efficiency = eff
    return u


class FakeState:
    def __init__(self, units, clock=7):
        self.units = units
        self.clock = clock
        self.malta_status = 3
        self.pools_a = {1: 100, 2: 0, 3: 0}
        self.pools_b = {1: 200, 2: 0, 3: 0}


class TestRecoveredReplacementEconomy(unittest.TestCase):
    def test_holding_brigade_gains_ten(self):
        # Oracle anchor: str 60, role-1 cap 100, deficit 40 -> +10, pool -10.
        u = unit(data.Nationality.BRITISH, 60)
        s = FakeState([u])
        reinforce.weekly_replacements(s)
        self.assertEqual(u.strength, 70)
        self.assertEqual(s.pools_a[1], 90)

    def test_moving_unit_gets_nothing(self):
        u = unit(data.Nationality.BRITISH, 60, order=Order.MOVE)
        s = FakeState([u])
        reinforce.weekly_replacements(s)
        self.assertEqual((u.strength, s.pools_a[1]), (60, 100))

    def test_premium_class_draws_thirty_from_pool_b(self):
        # Oracle anchor: class 2, str 60, cap 170 -> +30 from pool B.
        u = unit(data.Nationality.BRITISH, 60, klass=2)
        s = FakeState([u])
        reinforce.weekly_replacements(s)
        self.assertEqual(u.strength, 90)
        self.assertEqual((s.pools_a[1], s.pools_b[1]), (100, 170))

    def test_rebuild_pays_now_returns_later_at_eff_50(self):
        # Oracle anchor: destroyed role-1 -> pay 100, cooldown, eff 50.
        u = unit(data.Nationality.BRITISH, 0)
        s = FakeState([u])
        s.pools_a[1] = 300
        reinforce.weekly_replacements(s)
        self.assertEqual(s.pools_a[1], 200)
        self.assertEqual(u.efficiency, 50)
        self.assertEqual(u.strength, 0)  # in transit
        for _ in range(reinforce.REBUILD_COOLDOWN_DAYS):
            reinforce.tick_rebuilds(s)
        self.assertEqual(u.strength, 100)

    def test_class9_and_role_bit1_never_rebuilt(self):
        a = unit(data.Nationality.BRITISH, 0, klass=9)
        b = unit(data.Nationality.BRITISH, 0, role=3)
        s = FakeState([a, b]); s.pools_a[1] = 500
        reinforce.weekly_replacements(s)
        self.assertEqual(s.pools_a[1], 500)

    def test_monthly_income_with_malta(self):
        sched = data.load_schedules()
        s = FakeState([], clock=180)  # month 6
        s.pools_a = {}; s.pools_b = {}
        s.malta_status = 1
        reinforce.monthly_pool_income(s, sched)
        month = 6
        g = sched["monthly_unit_schedule"][month]
        half = sched["malta_modifier"]["half_1"][month]
        self.assertEqual(s.pools_a[1], g[0] * 10)                     # British unmodified
        self.assertEqual(s.pools_a[2], (g[2] * 10 * half + 5) // 10)  # German x Malta


if __name__ == "__main__":
    unittest.main()
