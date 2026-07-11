"""Web arena server: the oracle-verified engine behind a thin HTTP API.

This replaces reference/desert_rats_arena.html's *embedded JS engine* with
the real one. The browser client (arena/static/index.html) holds no rules
at all -- it renders state JSON and stages orders; every mechanic (supply
banding, combat, movement, replacements, calendar, AI) runs in
desert_rats/, the single source of truth (286-test suite).

Run:  uvicorn arena.server:app --reload   (or: python -m arena)
Then open http://127.0.0.1:8000/

Sessions are in-memory and single-process -- this is a local application
server, not a deployment target.
"""
from __future__ import annotations

import itertools
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from desert_rats import ai, game, game_calendar
from desert_rats.board import Board, load_board
from desert_rats.data import OrderOfBattle, Side, load_master_oob, load_scenarios
from desert_rats.render.overview import (
    APPROXIMATE_TOWN_COLUMNS,
    NATION_DOT_COLOUR,
    TERRAIN_LEGEND_COLOUR,
)
from desert_rats.units import Order, Unit
from desert_rats.victory import front_line_midpoint
from desert_rats.zoc_supply import supply_band

app = FastAPI(title="Desert Rats Arena", version="2.0")

# ── Static data, loaded once ────────────────────────────────────────────
_BOARD: Board = load_board()
_OOB: OrderOfBattle = load_master_oob()
_SCENARIOS = load_scenarios()

_ids = itertools.count(1)


class Session:
    def __init__(self, state: game.GameState, modes: Dict[Side, str]):
        self.state = state
        self.modes = modes  # side -> "human" | "ai"
        self.log: List[str] = []


_SESSIONS: Dict[int, Session] = {}


# ── Request models ──────────────────────────────────────────────────────
class NewGameRequest(BaseModel):
    scenario_index: int
    british: str = Field("human", pattern="^(human|ai)$")
    axis: str = Field("ai", pattern="^(human|ai)$")


class UnitOrder(BaseModel):
    oob_index: int
    order: int
    dest_x: Optional[int] = None
    dest_y: Optional[int] = None


class OrdersRequest(BaseModel):
    orders: List[UnitOrder]


# ── Serialization ───────────────────────────────────────────────────────
def _unit_json(u: Unit) -> dict:
    return {
        "oob_index": u.oob_index,
        "name": u.name,
        "designation": u.designation,
        "division": u.division,
        "nationality": u.nationality.value if hasattr(u.nationality, "value") else str(u.nationality),
        "side": "BRITISH" if u.side is Side.BRITISH else "AXIS",
        "branch": u.branch.value,
        "x": u.x,
        "y": u.y,
        "footprint": u.footprint_size,
        "strength": u.strength,
        "efficiency": u.efficiency,
        "morale": u.morale,
        "supply": u.supply,
        "supply_band": supply_band(u.supply) if u.supply is not None else None,
        "order": int(u.order),
        "order_name": u.order.name,
        "travel": u.travel,
        "dest_x": u.dest_x,
        "dest_y": u.dest_y,
    }


def _state_json(session: Session, game_id: int) -> dict:
    s = session.state
    line1, line2 = game_calendar.format_date_lines(s.clock)
    return {
        "game_id": game_id,
        "scenario": {"index": s.scenario.index, "name": s.scenario.name},
        "turn": s.turn_counter,
        "clock": s.clock,
        "date": [line1, line2],
        "modes": {("british" if k is Side.BRITISH else "axis"): v for k, v in session.modes.items()},
        "midpoint": front_line_midpoint(s.units),
        "result": s.result.name if s.result is not None else None,
        "units": [_unit_json(u) for u in s.units if not u.is_destroyed],
        "pools": {"general": s.pools_a, "armour": s.pools_b},
        "log": session.log[-40:],
    }


def _get(game_id: int) -> Session:
    session = _SESSIONS.get(game_id)
    if session is None:
        raise HTTPException(404, "no such game")
    return session


# ── API ─────────────────────────────────────────────────────────────────
@app.get("/api/scenarios")
def scenarios() -> list:
    return [
        {
            "index": sc.index,
            "name": sc.name,
            "start_day": sc.start_day,
            "end_day": sc.end_day,
            "start_date": " ".join(game_calendar.format_date_lines(sc.start_day)),
        }
        for sc in _SCENARIOS
    ]


@app.get("/api/map")
def map_data() -> dict:
    """Static per-campaign map payload: terrain grid + display legend.

    Legend colours/towns come from render.overview -- the debug-legibility
    convention behind pubmap_units.png, NOT a recovered palette (see that
    module's docstring). The client is a skin; swapping this endpoint's
    payload is the content-pack seam for future surfaces.
    """
    grid = [[_BOARD.terrain_at(x, y) for x in range(_BOARD.width)] for y in range(_BOARD.height)]
    return {
        "width": _BOARD.width,
        "height": _BOARD.height,
        "terrain": grid,
        "legend": {str(k): list(v) for k, v in TERRAIN_LEGEND_COLOUR.items()},
        "nation_colours": {
            (k.value if hasattr(k, "value") else str(k)): list(v)
            for k, v in NATION_DOT_COLOUR.items()
        },
        "towns": APPROXIMATE_TOWN_COLUMNS,
    }


@app.post("/api/games")
def new_game(req: NewGameRequest) -> dict:
    matches = [sc for sc in _SCENARIOS if sc.index == req.scenario_index]
    if not matches:
        raise HTTPException(400, "unknown scenario index")
    state = game.new_game(matches[0], _BOARD, _OOB)
    modes = {Side.BRITISH: req.british, Side.AXIS: req.axis}
    game_id = next(_ids)
    session = Session(state, modes)
    session.log.append(f"Scenario {matches[0].name} opened.")
    _SESSIONS[game_id] = session
    return _state_json(session, game_id)


@app.get("/api/games/{game_id}")
def get_state(game_id: int) -> dict:
    return _state_json(_get(game_id), game_id)


@app.post("/api/games/{game_id}/orders")
def stage_orders(game_id: int, req: OrdersRequest) -> dict:
    """Stage human orders on units; nothing advances until end-turn."""
    session = _get(game_id)
    state = session.state
    by_index = {u.oob_index: u for u in state.units}
    for o in req.orders:
        unit = by_index.get(o.oob_index)
        if unit is None or unit.is_destroyed:
            raise HTTPException(400, f"unit {o.oob_index} not on the board")
        if session.modes[unit.side] != "human":
            raise HTTPException(403, f"unit {o.oob_index} is AI-controlled")
        try:
            unit.order = Order(o.order)
        except ValueError:
            raise HTTPException(400, f"unknown order code {o.order}")
        if o.dest_x is not None and o.dest_y is not None:
            if not (0 <= o.dest_x < _BOARD.width and 0 <= o.dest_y < _BOARD.height):
                raise HTTPException(400, "destination off-board")
            unit.dest_x, unit.dest_y = o.dest_x, o.dest_y
    return _state_json(session, game_id)


@app.post("/api/games/{game_id}/end-turn")
def end_turn(game_id: int) -> dict:
    session = _get(game_id)
    state = session.state
    if state.is_over:
        raise HTTPException(409, "game is over")
    providers = {
        side: ai.plan_turn for side, mode in session.modes.items() if mode == "ai"
    }
    before = {u.oob_index for u in state.units}
    game.play_turn(state, providers)
    after = {u.oob_index for u in state.units}
    for gone in sorted(before - after):
        session.log.append(f"Unit destroyed: {_OOB.units[gone].name}")
    for new in sorted(after - before):
        session.log.append(f"Reinforcement arrived: {_OOB.units[new].name}")
    if state.result is not None:
        session.log.append(f"GAME OVER: {state.result.name}")
    return _state_json(session, game_id)


# ── Client ──────────────────────────────────────────────────────────────
_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(_STATIC / "index.html"))
