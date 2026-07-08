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

    def test_target_is_first_in_band_enemy_region(self):
        # Under the recovered band-gated ladder walk, with the frontier
        # set so only Tobruk is in band, Tobruk is the target.
        us = [unit(data.Side.BRITISH, 41, 10),                 # enemy holds Tobruk
              unit(data.Side.BRITISH, 92, 16),                 # enemy at Alamein
              unit(data.Side.AXIS, 92, 16)]                    # we contest Alamein
        target = ai_og.choose_target(us, data.Side.AXIS, frontier=30)
        self.assertEqual(target, (41, 10))


if __name__ == "__main__":
    unittest.main()


class TestRecoveredLadderWalk(unittest.TestCase):
    def test_band_gate_selects_first_in_band_enemy_region(self):
        # Two enemy-held regions; only the one whose anchor column lies
        # in [frontier, frontier+50) qualifies.
        table = ai_og.regions()
        tobruk = next(r for r in table if r["anchor_a"] == [41, 10])
        alamein = next(r for r in table if r["anchor_a"] == [92, 16])
        us = [unit(data.Side.BRITISH, 41, 10),   # enemy holds Tobruk (x41)
              unit(data.Side.BRITISH, 92, 16)]   # enemy holds Alamein (x92)
        # frontier 30: band [30,80) includes Tobruk(41), excludes Alamein(92)
        t = ai_og.choose_target(us, data.Side.AXIS, frontier=30)
        self.assertEqual(t, (41, 10))
        # frontier 70: band [70,120) now includes Alamein, excludes Tobruk
        t = ai_og.choose_target(us, data.Side.AXIS, frontier=70)
        self.assertEqual(t, (92, 16))

    def test_walk_direction_differs_by_side(self):
        # Prove the directional walk on a synthetic 2-region table so the
        # test does not depend on the real map's geography: two enemy-held
        # regions in the same band, at region indices 0 and 1. Axis walks
        # ascending (picks index 0), British descending (picks index 1).
        table = [
            {"index": 0, "anchor_a": [45, 12], "anchor_b": [45, 12], "importance": 3},
            {"index": 1, "anchor_a": [50, 14], "anchor_b": [50, 14], "importance": 3},
        ]
        us = [unit(data.Side.BRITISH, 45, 12), unit(data.Side.BRITISH, 50, 14),
              unit(data.Side.AXIS, 45, 12), unit(data.Side.AXIS, 50, 14)]
        axis_t = ai_og.choose_target(us, data.Side.AXIS, table=table, frontier=40)
        brit_t = ai_og.choose_target(us, data.Side.BRITISH, table=table, frontier=40)
        self.assertEqual(axis_t, (45, 12))   # Axis: lower index first
        self.assertEqual(brit_t, (50, 14))   # British: higher index first
        self.assertNotEqual(axis_t, brit_t)



    def test_out_of_band_falls_back_to_scoring(self):
        # Enemy far outside the band -> ladder yields nothing -> the
        # scoring fallback still returns a sensible in-reach target.
        us = [unit(data.Side.BRITISH, 41, 10)]
        t = ai_og.choose_target(us, data.Side.AXIS, frontier=95)
        self.assertIsNotNone(t)
