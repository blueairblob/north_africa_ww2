import unittest

from desert_rats import ai_og, data
from desert_rats.units import Order, Unit


def unit(side, x, y, strength=100, mps=10, order=Order.HOLD):
    nat = data.Nationality.BRITISH if side is data.Side.BRITISH else data.Nationality.GERMAN
    u = Unit(oob_index=0, nationality=nat, designation="t", division="d",
             name="n", type=12, role=0, mps=mps, x=x, y=y,
             strength=strength, morale=50, arrival=0)
    u.order = order
    return u


class TestRecoveredStrategicLayer(unittest.TestCase):
    def test_region_table_loaded(self):
        table = ai_og.regions()
        self.assertEqual(len(table), 30)
        tobruk = next(r for r in table if r["anchor_a"] == [41, 10])
        self.assertEqual(tobruk["importance"], 7)  # highest-value region

    def test_unit_weight_oracle_formula(self):
        # strength >> 5, halved when MPS < 5
        self.assertEqual(ai_og.unit_weight(unit(data.Side.AXIS, 0, 0, strength=100, mps=10)), 3)
        self.assertEqual(ai_og.unit_weight(unit(data.Side.AXIS, 0, 0, strength=100, mps=4)), 1)
        self.assertEqual(ai_og.unit_weight(unit(data.Side.AXIS, 0, 0, strength=64, mps=10)), 2)

    def test_friendly_store_bug_reproduced(self):
        # The original stores the LAST friendly weight instead of summing.
        table = ai_og.regions()
        us = [unit(data.Side.AXIS, 41, 10, strength=200, mps=10),
              unit(data.Side.AXIS, 41, 10, strength=64, mps=10)]
        t = ai_og.build_region_tallies(us, data.Side.AXIS, table)
        idx = ai_og.region_of(41, 10, table)
        self.assertEqual(t[idx]["friendly"], 2)  # 64>>5, not 6+2

    def test_enemy_weights_accumulate(self):
        table = ai_og.regions()
        us = [unit(data.Side.BRITISH, 41, 10, strength=200, mps=10),
              unit(data.Side.BRITISH, 41, 10, strength=64, mps=10)]
        t = ai_og.build_region_tallies(us, data.Side.AXIS, table)
        idx = ai_og.region_of(41, 10, table)
        self.assertEqual(t[idx]["enemy"], 8)  # 6 + 2

    def test_scoring_tiers(self):
        base = {"enemy": 4, "friendly": 0, "enemy_assaulting": False, "importance": 5}
        self.assertEqual(ai_og.score_region(dict(base), 14, data.Side.AXIS), 96 + 5)
        self.assertEqual(ai_og.score_region(dict(base, friendly=4), 14, data.Side.AXIS), 60 + 5)
        self.assertEqual(ai_og.score_region(dict(base, friendly=9), 14, data.Side.AXIS), 50 + 5)
        self.assertEqual(ai_og.score_region(dict(base, friendly=7), 14, data.Side.AXIS), 0)
        self.assertEqual(ai_og.score_region(dict(base, enemy=0), 14, data.Side.AXIS), 0)

    def test_target_prefers_undefended_high_importance(self):
        # An undefended enemy-held Tobruk beats a contested minor region.
        us = [unit(data.Side.BRITISH, 41, 10),                 # enemy holds Tobruk
              unit(data.Side.BRITISH, 92, 16),                 # enemy at Alamein
              unit(data.Side.AXIS, 92, 16)]                    # we contest Alamein
        target = ai_og.choose_target(us, data.Side.AXIS)
        self.assertEqual(target, (41, 10))


if __name__ == "__main__":
    unittest.main()
