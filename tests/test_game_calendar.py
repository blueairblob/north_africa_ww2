import unittest
from datetime import date

from desert_rats import game_calendar as cal


class TestRecoveredCalendar(unittest.TestCase):
    def test_epoch_is_april_1_1941(self):
        self.assertEqual(cal.format_date_lines(1), ("APR 1st", "1941"))

    def test_gazala_anchor_matches_the_screenshot(self):
        self.assertEqual(cal.format_date_lines(422), ("MAY 27th", "1942"))

    def test_game_month_forms(self):
        # four-letter JUNE/JULY/SEPT, three-letter rest (table at 0xE793)
        self.assertEqual(cal.format_date_lines(91), ("JUNE 30th", "1941"))
        self.assertEqual(cal.format_date_lines(181), ("SEPT 28th", "1941"))
        self.assertEqual(cal.format_date_lines(122), ("JULY 31st", "1941"))

    def test_ordinals(self):
        self.assertEqual(cal.ordinal(1), "st")
        self.assertEqual(cal.ordinal(2), "nd")
        self.assertEqual(cal.ordinal(3), "rd")
        self.assertEqual(cal.ordinal(4), "th")
        self.assertEqual(cal.ordinal(11), "th")
        self.assertEqual(cal.ordinal(12), "th")
        self.assertEqual(cal.ordinal(13), "th")
        self.assertEqual(cal.ordinal(21), "st")
        self.assertEqual(cal.ordinal(31), "st")

    def test_real_calendar_boundaries(self):
        # Feb 1942 is not a leap February
        self.assertEqual(cal.clock_to_date(337), date(1942, 3, 3))
        self.assertEqual(cal.format_date_lines(334), ("FEB 28th", "1942"))
        self.assertEqual(cal.format_date_lines(335), ("MAR 1st", "1942"))


if __name__ == "__main__":
    unittest.main()
