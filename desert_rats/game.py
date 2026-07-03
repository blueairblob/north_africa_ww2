"""Turn loop, per-side phases, state machine, end conditions.

See BUILD_SPEC.md §4.2. AI order-selection (ai.py) doesn't exist yet in
the build order (§11: game.py comes before ai.py), so a side's orders are
supplied by an injected `OrderProvider` callback -- for now callers (tests,
or a human-vs-human harness) can drive both sides directly; once ai.py
exists, its planner is just another OrderProvider passed in here, with no
change to the turn loop itself. Rendering (§4.2 step 7) is render.py's
job, built last, and has no hook here yet either.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from . import combat, movement, reinforce, victory
from .board import Board
from .data import OrderOfBattle, Scenario, Side, opposing_side
from .units import Order, Unit
from .zoc_supply import FlagGrid, build_flag_grid, compute_supply

# Safety cap for run_until_over -- not a rules value, just a bug backstop.
DEFAULT_MAX_TURNS = 10_000

OrderProvider = Callable[["GameState", Side, FlagGrid], None]


@dataclass
class GameState:
    board: Board
    oob: OrderOfBattle
    scenario: Scenario
    turn_counter: int
    clock: int
    units: List[Unit]
    admitted_indices: Set[int]
    midpoint_history: List[Optional[float]] = field(default_factory=list)
    result: Optional[victory.VictoryLevel] = None

    @property
    def is_over(self) -> bool:
        return self.result is not None


def new_game(scenario: Scenario, board: Board, oob: OrderOfBattle) -> GameState:
    """Set up a scenario's starting roster (BUILD_SPEC.md §4.1).

    Scenarios are windows into one continuous 624-day campaign, so the
    turn counter is initialised to the smallest turn whose campaign clock
    equals the scenario's start day (inverting §3.3's clock formula), not
    reset to 0 -- otherwise a mid-campaign scenario like Battleaxe (day 77)
    would incorrectly start with only day-0 units present.
    """
    turn_counter = 3 * scenario.start_day - 2
    clock = reinforce.campaign_clock(turn_counter)

    starting_units = reinforce.admit_reinforcements(oob, set(), [], clock, board)
    admitted_indices = {u.oob_index for u in starting_units}

    return GameState(
        board=board,
        oob=oob,
        scenario=scenario,
        turn_counter=turn_counter,
        clock=clock,
        units=starting_units,
        admitted_indices=admitted_indices,
    )


def _footprints_are_adjacent(a: Unit, b: Unit) -> bool:
    a_cells = set(a.footprint_cells())
    b_cells = set(b.footprint_cells())
    if a_cells & b_cells:
        return True
    for cx, cy in a_cells:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (cx + dx, cy + dy) in b_cells:
                return True
    return False


def find_adjacent_enemy(unit: Unit, units: List[Unit]) -> Optional[Unit]:
    """The lowest-oob_index living enemy adjacent to `unit` (deterministic
    tie-break for a unit with more than one adjacent target).
    """
    enemy_side = opposing_side(unit.side)
    candidates = [
        u for u in units
        if u.side is enemy_side and not u.is_destroyed and _footprints_are_adjacent(unit, u)
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda u: u.oob_index)


def _resolve_combat_for_side(state: GameState, side: Side) -> None:
    for unit in state.units:
        if unit.is_destroyed or unit.side is not side or unit.order is not Order.ASSAULT:
            continue
        enemy = find_adjacent_enemy(unit, state.units)
        if enemy is not None:
            combat.resolve_assault(unit, enemy)


def play_turn(state: GameState, order_providers: Optional[Dict[Side, OrderProvider]] = None) -> None:
    """Advance `state` by one turn in place (BUILD_SPEC.md §4.2). No-op if
    the game has already ended.
    """
    if state.is_over:
        return

    order_providers = order_providers or {}

    state.turn_counter += 1
    state.clock = reinforce.campaign_clock(state.turn_counter)

    newly_admitted = reinforce.admit_reinforcements(
        state.oob, state.admitted_indices, state.units, state.clock, state.board
    )
    state.units.extend(newly_admitted)
    state.admitted_indices.update(u.oob_index for u in newly_admitted)

    flags = build_flag_grid(state.units, state.board)
    compute_supply(state.units, state.board, flags)

    for side in (Side.BRITISH, Side.AXIS):
        provider = order_providers.get(side)
        if provider is not None:
            provider(state, side, flags)

        for unit in state.units:
            if unit.side is side and not unit.is_destroyed:
                movement.advance_unit(unit, state.board, flags)

        _resolve_combat_for_side(state, side)

    combat.apply_attrition(state.units, flags)
    combat.apply_recovery(state.units, flags)

    state.midpoint_history.append(victory.front_line_midpoint(state.units))

    if victory.is_game_over(state.clock, state.scenario, state.midpoint_history):
        state.result = victory.victory_result(state.units, state.scenario)

    state.units = [u for u in state.units if not u.is_destroyed]


def run_until_over(
    state: GameState,
    order_providers: Optional[Dict[Side, OrderProvider]] = None,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> GameState:
    """Play turns until the game ends or `max_turns` is hit (a bug
    backstop, not a rules value -- BUILD_SPEC.md §5.7's own end conditions
    are what actually stop play).
    """
    turns_played = 0
    while not state.is_over and turns_played < max_turns:
        play_turn(state, order_providers)
        turns_played += 1
    return state
