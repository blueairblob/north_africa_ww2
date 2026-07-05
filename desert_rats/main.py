"""Entry point: title/options screen -> scenario select -> game.

See BUILD_SPEC.md §4.1. `run_headless()` is the primary testable path (no
interactive I/O, AI-driven by default) satisfying CLEANROOM_BRIEF.md's
"headless 2-player games run end-to-end ... reach a victory result"
acceptance criterion. `main()`/`run_interactive()` are a thin CLI wrapper
around it that additionally supports human-controlled sides through
simple text prompts -- one or two human players, per BUILD_SPEC.md §1,
with the empty seat(s) played by ai.plan_turn.
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Callable, Dict, Optional

from . import ai, game
from .board import Board, load_board
from .data import OrderOfBattle, Scenario, Side, load_master_oob, load_scenarios
from .render import (
    clamp_viewport_origin,
    clean,
    format_status_line,
    load_ui_strings,
    order_label,
    render_viewport,
)
from .render.strings import UiStrings
from .units import Order
from .victory import front_line_midpoint

# BUILD_SPEC.md §1/§10 and CLEANROOM_BRIEF.md's boundaries: Malta is a
# 128K-only feature with "no invocation found in the 48K image" -- the menu
# is shown for title-screen authenticity only and has no gameplay effect.
MALTA_NOTE = (
    "Malta status has no gameplay effect in this build "
    "(BUILD_SPEC.md §10: no invocation found in the 48K image)."
)

OrderMode = str  # "ai" or "human"


def build_order_providers(british_mode: OrderMode, axis_mode: OrderMode) -> Dict[Side, Callable]:
    modes = {Side.BRITISH: british_mode, Side.AXIS: axis_mode}
    return {side: (ai.plan_turn if mode == "ai" else human_order_provider) for side, mode in modes.items()}


def run_headless(
    scenario: Scenario,
    board: Board,
    oob: OrderOfBattle,
    british_mode: OrderMode = "ai",
    axis_mode: OrderMode = "ai",
    max_turns: int = game.DEFAULT_MAX_TURNS,
    watch: bool = False,
    delay: float = 0.0,
    snapshot_dir: Optional[str] = None,
) -> game.GameState:
    """Run a full game with no interactive I/O. Defaults to AI vs AI.

    `watch=True` renders the board after every turn (still no input
    prompts) -- the "watch two AIs fight it out" mode. `delay` paces
    playback when watching; ignored otherwise.

    `snapshot_dir`, if given, writes both a tactical PNG (render.image,
    the confirmed in-game colour model) and a strategic overview PNG
    (render.overview, pubmap_units.png-style terrain legend + unit dots)
    after every turn -- requires the optional `image` extra: `pip install
    desert-rats[image]`. Independent of `watch`; useful for headless runs
    where you want to inspect the game visually afterwards rather than
    live in a terminal.
    """
    providers = build_order_providers(british_mode, axis_mode)
    state = game.new_game(scenario, board, oob)

    snapshot = None
    if snapshot_dir is not None:
        from .render import image as render_image
        from .render import overview as render_overview
        import os

        os.makedirs(snapshot_dir, exist_ok=True)

        def snapshot(turn_state: game.GameState) -> None:
            turn = turn_state.turn_counter
            render_image.save_board_image(
                turn_state.units, board, os.path.join(snapshot_dir, f"turn_{turn:04d}_tactical.png")
            )
            render_overview.save_overview_image(
                turn_state.units, board, os.path.join(snapshot_dir, f"turn_{turn:04d}_overview.png")
            )

    if not watch and snapshot is None:
        game.run_until_over(state, providers, max_turns=max_turns)
        return state

    strings = load_ui_strings() if watch else None
    turns_played = 0
    while not state.is_over and turns_played < max_turns:
        game.play_turn(state, providers)
        turns_played += 1
        if snapshot is not None:
            snapshot(state)
        if watch:
            _render_turn(state, board, strings, clear_screen=True)
            if delay:
                time.sleep(delay)
    return state


def human_order_provider(state: game.GameState, side: Side, flags) -> None:
    """An OrderProvider that prompts on stdin/stdout for one side's orders."""
    strings = load_ui_strings()
    own_units = [u for u in state.units if u.side is side and not u.is_destroyed]
    if not own_units:
        return

    print(f"\n-- {side.value} orders --")
    for i, unit in enumerate(own_units):
        print(
            f"  [{i}] {unit.name} @ ({unit.x},{unit.y})  "
            f"order={order_label(unit.order, strings)}  eff={unit.efficiency}"
        )

    while True:
        raw = input("Unit index to order (blank to end orders phase): ").strip()
        if not raw:
            return
        try:
            unit = own_units[int(raw)]
        except (ValueError, IndexError):
            print("Invalid unit index.")
            continue
        _prompt_unit_order(unit, strings)


def _prompt_unit_order(unit, strings: UiStrings) -> None:
    print("Orders: " + ", ".join(f"{o.value}={order_label(o, strings)}" for o in Order))
    raw = input(f"Order for {unit.name} [{unit.order.value}]: ").strip()
    if raw:
        try:
            unit.order = Order(int(raw))
        except ValueError:
            print("Invalid order, unchanged.")
            return

    if unit.order in (Order.MOVE, Order.ASSAULT, Order.TRAVEL):
        raw_dest = input(f"Destination x,y [{unit.dest_x},{unit.dest_y}]: ").strip()
        if raw_dest:
            try:
                x_str, y_str = raw_dest.split(",")
                unit.dest_x, unit.dest_y = int(x_str), int(y_str)
            except ValueError:
                print("Invalid destination, unchanged.")


def _prompt_scenario(scenarios) -> Scenario:
    print("Scenarios:")
    for s in scenarios:
        print(f"  {s.index}) {s.name}  (day {s.start_day}-{s.end_day})")
    while True:
        choice = input(f"Select scenario [1-{len(scenarios)}]: ").strip()
        for s in scenarios:
            if choice == str(s.index):
                return s
        print("Invalid choice.")


def _prompt_side_mode(side: Side) -> OrderMode:
    while True:
        choice = (input(f"{side.value} controlled by (1) Human (2) AI [2]: ").strip() or "2")
        if choice == "1":
            return "human"
        if choice == "2":
            return "ai"
        print("Invalid choice.")


def _prompt_malta(strings: UiStrings) -> None:
    print()
    for line in strings.malta_options:
        print(f"  {clean(line)}")
    input("Malta status [any key to continue]: ")
    print(MALTA_NOTE)


def _camera_center(state: game.GameState, board: Board) -> tuple:
    """Where to point the viewport: the midpoint of the closest living
    British/Axis pair (i.e. wherever the actual fighting is), falling back
    to victory.front_line_midpoint if one side has no units left.

    victory.front_line_midpoint (easternmost Axis, westernmost British)/2
    is the right metric for scoring, but a poor camera target early on --
    with the two sides' starting positions ~85 columns apart on a 100-wide
    map, that midpoint sits in empty desert between them until contact.
    """
    living = [u for u in state.units if not u.is_destroyed]
    british = [u for u in living if u.side is Side.BRITISH]
    axis = [u for u in living if u.side is Side.AXIS]

    if not british or not axis:
        midpoint = front_line_midpoint(state.units)
        center_x = int(midpoint) if midpoint is not None else board.width // 2
        return center_x, board.height // 2

    closest_pair = min(
        ((b, a) for b in british for a in axis),
        key=lambda pair: abs(pair[0].x - pair[1].x) + abs(pair[0].y - pair[1].y),
    )
    b, a = closest_pair
    return (b.x + a.x) // 2, (b.y + a.y) // 2


def _render_turn(state: game.GameState, board: Board, strings: UiStrings, clear_screen: bool = False) -> None:
    if clear_screen and sys.stdout.isatty():
        print("\x1b[2J\x1b[H", end="")  # clear + cursor home, so frames animate in place
    print()
    print(format_status_line(state.turn_counter, state.clock, state.scenario.name, strings, state.result))
    center_x, center_y = _camera_center(state, board)
    origin = clamp_viewport_origin(center_x, center_y, board)
    print(render_viewport(state.units, board, origin, use_color=sys.stdout.isatty()))


def run_interactive() -> game.GameState:
    board = load_board()
    oob = load_master_oob()
    scenarios = load_scenarios()
    strings = load_ui_strings()

    print("=" * 40)
    print("DESERT RATS")
    print("=" * 40)

    scenario = _prompt_scenario(scenarios)
    british_mode = _prompt_side_mode(Side.BRITISH)
    axis_mode = _prompt_side_mode(Side.AXIS)
    _prompt_malta(strings)

    providers = build_order_providers(british_mode, axis_mode)
    state = game.new_game(scenario, board, oob)

    while not state.is_over:
        game.play_turn(state, providers)
        _render_turn(state, board, strings)

    return state


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Desert Rats")
    parser.add_argument("--headless", action="store_true", help="run AI vs AI with no prompts")
    parser.add_argument(
        "--pack",
        default=None,
        help="content pack to play (see content_packs/); default: og",
    )
    parser.add_argument("--scenario", type=int, default=1, help="scenario index for --headless (1-6)")
    parser.add_argument("--max-turns", type=int, default=game.DEFAULT_MAX_TURNS)
    parser.add_argument(
        "--watch", action="store_true",
        help="render the board after every turn in --headless mode (AI vs AI, no prompts)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.3,
        help="seconds to pause between turns with --watch (default 0.3; 0 = as fast as possible)",
    )
    parser.add_argument(
        "--snapshot-dir", type=str, default=None,
        help="write both a tactical PNG (render.image) and a strategic overview "
        "PNG (render.overview) after every turn to this directory "
        "(requires the 'image' extra: pip install desert-rats[image])",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    if args.pack:
        from . import packs
        pack = packs.set_active_pack(args.pack)
        print(f"content pack: {pack.title}")

    if args.headless:
        board = load_board()
        oob = load_master_oob()
        scenarios = load_scenarios()
        scenario = next((s for s in scenarios if s.index == args.scenario), scenarios[0])
        strings = load_ui_strings()

        state = run_headless(
            scenario, board, oob, max_turns=args.max_turns, watch=args.watch,
            delay=args.delay, snapshot_dir=args.snapshot_dir,
        )
        print(format_status_line(state.turn_counter, state.clock, state.scenario.name, strings, state.result))
        return 0

    run_interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())
