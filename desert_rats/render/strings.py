"""Load data/ui_strings.json and expose it as typed, still-verbatim text.

BUILD_SPEC.md §8: "All UI text ... is in data/ui_strings.json — reuse
verbatim for authenticity." `UiStrings` holds the raw extracted strings
unmodified; `clean()` is a separate, opt-in helper for display use that
strips the trailing " /" line-continuation artifact left over from the
original's packed text layout (not meaningful content) -- callers that
want the truly raw text can skip it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .. import packs
from typing import Optional

from ..units import Order
from ..victory import VictoryLevel

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
UI_STRINGS_PATH = DATA_DIR / "ui_strings.json"


@dataclass(frozen=True)
class UiStrings:
    scenarios: tuple
    orders: tuple
    report_labels: tuple
    supply_bands: tuple
    turn_phases: tuple
    victory_levels: tuple
    malta_options: tuple
    calendar: tuple
    all_messages: tuple


def load_ui_strings(path: Optional[Path] = None) -> UiStrings:
    path = Path(path) if path is not None else packs.active_pack().resolve("ui_strings.json")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    return UiStrings(
        scenarios=tuple(raw["scenarios"]),
        orders=tuple(raw["orders"]),
        report_labels=tuple(raw["report_labels"]),
        supply_bands=tuple(raw["supply_bands"]),
        turn_phases=tuple(raw["turn_phases"]),
        victory_levels=tuple(raw["victory_levels"]),
        malta_options=tuple(raw["malta_options"]),
        calendar=tuple(raw["calendar"]),
        all_messages=tuple(raw["all_messages"]),
    )


def clean(text: str) -> str:
    """Strip the trailing " /" line-continuation artifact for display."""
    return text[:-2] if text.endswith(" /") else text


def order_label(order: Order, strings: UiStrings) -> str:
    """data/ui_strings.json's `orders` list is in the same M/A/H/T/R/D/F/P
    order as units.Order's menu-order values (BUILD_SPEC.md §5.1), so the
    IntEnum's 1-based value indexes it directly.
    """
    return clean(strings.orders[order.value - 1])


# VictoryLevel's declaration order isn't the source list's order (the
# source groups British tactical->major->decisive, then Axis the same way;
# VictoryLevel groups British decisive->major->tactical) -- map explicitly
# rather than relying on either enum's member order.
_VICTORY_LEVEL_STRING_INDEX = {
    VictoryLevel.BRITISH_TACTICAL: 1,
    VictoryLevel.BRITISH_MAJOR: 2,
    VictoryLevel.BRITISH_DECISIVE: 3,
    VictoryLevel.DRAW: 4,
    VictoryLevel.AXIS_TACTICAL: 5,
    VictoryLevel.AXIS_MAJOR: 6,
    VictoryLevel.AXIS_DECISIVE: 7,
}


def victory_level_text(level: VictoryLevel, strings: UiStrings) -> str:
    return clean(strings.victory_levels[_VICTORY_LEVEL_STRING_INDEX[level]])
