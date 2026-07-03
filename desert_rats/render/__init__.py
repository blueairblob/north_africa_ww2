"""Text/terminal renderer: colour compositing (nationality ink over terrain
paper), scrolling 22x22 viewport, unit reports, UI text.

See BUILD_SPEC.md §8. A text/terminal renderer is an explicitly acceptable
fidelity tier; pixel-exact tile art is a later, optional tier (§10).
"""
from .palette import (
    ANSI_INK,
    ANSI_PAPER_DESERT,
    ANSI_PAPER_SEA,
    ANSI_RESET,
    BRANCH_GLYPH,
    SPECTRUM_INK,
    terrain_glyph,
    terrain_paper,
    unit_glyph,
)
from .strings import UiStrings, clean, load_ui_strings, order_label, victory_level_text
from .terminal import (
    calendar_month,
    clamp_viewport_origin,
    format_status_line,
    format_unit_report,
    render_cell,
    render_viewport,
)

__all__ = [
    "ANSI_INK",
    "ANSI_PAPER_DESERT",
    "ANSI_PAPER_SEA",
    "ANSI_RESET",
    "BRANCH_GLYPH",
    "SPECTRUM_INK",
    "terrain_glyph",
    "terrain_paper",
    "unit_glyph",
    "UiStrings",
    "clean",
    "load_ui_strings",
    "order_label",
    "victory_level_text",
    "calendar_month",
    "clamp_viewport_origin",
    "format_status_line",
    "format_unit_report",
    "render_cell",
    "render_viewport",
]
