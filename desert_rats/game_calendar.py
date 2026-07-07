"""Clock -> calendar date, recovered from the original.

Method (reference/diff_harness/): the side-panel date drawer at 0x97E3
was located via the LD HL,(0xCB0F) clock readers, then the clock was
swept 1..730 under emulation and the rendered screen OCR'd with the
game's own font (0xFD00). Result, validated with ZERO mismatches across
days 1..640 against the real calendar:

    clock day N  =  April 1, 1941  +  (N - 1)   [real Gregorian]

Month names use the game's exact forms (four-letter JUNE/JULY/SEPT),
table at 0xE793 (4-byte entries). Ordinal suffixes are standard English
(1st/2nd/3rd/nth with 11th/12th/13th). Anchor: clock 422 = "MAY 27th
1942" -- the Gazala start, matching the reference screenshot
glyph-for-glyph.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple

EPOCH = date(1941, 4, 1)

MONTH_NAMES = ["JAN", "FEB", "MAR", "APR", "MAY", "JUNE",
               "JULY", "AUG", "SEPT", "OCT", "NOV", "DEC"]


def ordinal(day: int) -> str:
    if day % 10 == 1 and day != 11:
        return "st"
    if day % 10 == 2 and day != 12:
        return "nd"
    if day % 10 == 3 and day != 13:
        return "rd"
    return "th"


def clock_to_date(clock: int) -> date:
    return EPOCH + timedelta(days=clock - 1)


def format_date_lines(clock: int) -> Tuple[str, str]:
    """The two yellow panel lines, e.g. ("MAY 27th", "1942")."""
    d = clock_to_date(clock)
    return (f"{MONTH_NAMES[d.month - 1]} {d.day}{ordinal(d.day)}", str(d.year))
