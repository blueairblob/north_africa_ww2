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
from desert_rats.render import screen as og_screen
from desert_rats.render.image import render_board_image
from desert_rats.units import Order, Unit
from desert_rats.victory import front_line_midpoint
from desert_rats.zoc_supply import supply_band

import io

from fastapi import Response

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


# ── Authentic screen ────────────────────────────────────────────────────
def _og_art_available() -> bool:
    """Whether the local-only original art (font/tiles) is present. These
    are gitignored by design (private extractions, never redistributed);
    without them the screen endpoint degrades to the attribute-blend
    viewport + a plain-font panel with identical geometry."""
    try:
        return og_screen._load_font() is not None
    except Exception:
        return False


@app.get("/api/ui")
def ui_layout() -> dict:
    """Screen geometry + panel menu for the client's click mapping. The
    client stays rule-free: even the menu rows come from the renderer."""
    return {
        "screen_w": og_screen.SCREEN_W,
        "screen_h": og_screen.SCREEN_H,
        "view_cells": og_screen.VIEW_CELLS,
        "panel_x": og_screen.PANEL_X,
        "bottom_y": og_screen.BOTTOM_Y,
        "menu": [
            {"row": row, "label": label, "order": (int(order) if order is not None else None)}
            for row, label, order in og_screen.MENU_LAYOUT
        ],
        "og_art": _og_art_available(),
    }


def _fallback_screen(state: game.GameState, origin, selected_order, status_line):
    """Same 256x192 composition as render_screen, PIL default font --
    used only when the local og art files are absent."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (og_screen.SCREEN_W, og_screen.SCREEN_H), og_screen.BLACK)
    view = render_board_image(state.units, state.board, origin=origin,
                              size=og_screen.VIEW_CELLS, cell_px=8)
    img.paste(view.crop((0, 0, og_screen.PANEL_X, og_screen.PANEL_X)), (0, 0))
    draw = ImageDraw.Draw(img)
    line1, line2 = game_calendar.format_date_lines(state.clock)
    draw.text((og_screen.PANEL_X + 8, 0), line1[:10], fill=og_screen.YELLOW)
    draw.text((og_screen.PANEL_X + 8, 8), line2[:10], fill=og_screen.YELLOW)
    for row, label, order in og_screen.MENU_LAYOUT:
        if order is not None and order is selected_order:
            draw.rectangle([og_screen.PANEL_X, row * 8, og_screen.SCREEN_W - 1, row * 8 + 7],
                           fill=og_screen.RED)
            draw.text((og_screen.PANEL_X, row * 8), label[:10], fill=og_screen.BLACK)
        else:
            draw.text((og_screen.PANEL_X, row * 8), label[:10], fill=og_screen.WHITE)
    draw.rectangle([0, og_screen.BOTTOM_Y, og_screen.SCREEN_W - 1, og_screen.SCREEN_H - 1],
                   fill=og_screen.RED)
    draw.text((0, og_screen.BOTTOM_Y), status_line[:32], fill=og_screen.WHITE)
    return img


@app.get("/api/games/{game_id}/screen")
def screen_png(game_id: int, ox: int = 0, oy: int = 0,
               sel: Optional[int] = None) -> Response:
    """The authentic 256x192 screen as PNG: viewport at (ox, oy), the
    selected unit's order in inverse video, its name on the status band --
    rendered by desert_rats.render.screen (pixel-exact with the local og
    art present)."""
    session = _get(game_id)
    state = session.state
    max_ox = max(0, _BOARD.width - og_screen.VIEW_CELLS)
    max_oy = max(0, _BOARD.height - og_screen.VIEW_CELLS)
    ox = min(max(ox, 0), max_ox)
    oy = min(max(oy, 0), max_oy)

    selected = next((u for u in state.units if u.oob_index == sel), None) if sel is not None else None
    selected_order = selected.order if selected is not None else None
    if state.result is not None:
        status = f"GAME OVER {state.result.name.replace('_', ' ')}"
    elif selected is not None:
        status = selected.name
    else:
        status = ""

    try:
        img = og_screen.render_screen(
            state.units, state.board, viewport_origin=(ox, oy),
            clock=state.clock, selected_order=selected_order,
            status_line=status,
        )
    except FileNotFoundError:
        img = _fallback_screen(state, (ox, oy), selected_order, status)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png",
                    headers={"Cache-Control": "no-store"})


# ── Client ──────────────────────────────────────────────────────────────
_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(_STATIC / "index.html"))
