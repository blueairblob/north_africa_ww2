"""arena/server.py: the application layer must be a pure pass-through --
no rules of its own, state faithfully serialized, orders validated.

Skipped wholesale when fastapi isn't installed (`pip install .[web]`):
the engine suite must stay dependency-free.
"""
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from arena import server  # noqa: E402
from desert_rats.data import Side  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(server.app)


def _new_game(client, **kw):
    body = {"scenario_index": 2, "british": "human", "axis": "ai"}
    body.update(kw)
    r = client.post("/api/games", json=body)
    assert r.status_code == 200
    return r.json()


def test_map_payload_matches_board(client):
    m = client.get("/api/map").json()
    assert (m["width"], m["height"]) == (server._BOARD.width, server._BOARD.height)
    assert len(m["terrain"]) == m["height"]
    assert all(len(row) == m["width"] for row in m["terrain"])
    # every terrain code present in the grid must have a legend colour
    codes = {c for row in m["terrain"] for c in row}
    assert codes <= {int(k) for k in m["legend"]}


def test_scenarios_are_the_six_windows(client):
    names = [s["name"] for s in client.get("/api/scenarios").json()]
    assert len(names) == 6 and "Operation Crusader" in names


def test_new_game_state_mirrors_engine(client):
    g = _new_game(client)
    session = server._SESSIONS[g["game_id"]]
    assert g["turn"] == session.state.turn_counter
    assert g["clock"] == session.state.clock
    assert len(g["units"]) == sum(1 for u in session.state.units if not u.is_destroyed)
    assert g["date"][1] in ("1941", "1942")  # calendar epoch honoured


def test_order_staging_validates_side_and_bounds(client):
    g = _new_game(client)
    gid = g["game_id"]
    axis_unit = next(u for u in g["units"] if u["side"] == "AXIS")
    brit_unit = next(u for u in g["units"] if u["side"] == "BRITISH")
    # AI-controlled unit refuses human orders
    r = client.post(f"/api/games/{gid}/orders",
                    json={"orders": [{"oob_index": axis_unit["oob_index"], "order": 1,
                                      "dest_x": 0, "dest_y": 0}]})
    assert r.status_code == 403
    # off-board destination refused
    r = client.post(f"/api/games/{gid}/orders",
                    json={"orders": [{"oob_index": brit_unit["oob_index"], "order": 1,
                                      "dest_x": 999, "dest_y": 0}]})
    assert r.status_code == 400
    # valid order lands on the engine unit
    r = client.post(f"/api/games/{gid}/orders",
                    json={"orders": [{"oob_index": brit_unit["oob_index"], "order": 4,
                                      "dest_x": brit_unit["x"] + 3, "dest_y": brit_unit["y"]}]})
    assert r.status_code == 200
    engine_unit = next(u for u in server._SESSIONS[gid].state.units
                       if u.oob_index == brit_unit["oob_index"])
    assert int(engine_unit.order) == 4
    assert engine_unit.dest_x == brit_unit["x"] + 3


def test_end_turn_advances_engine_turn(client):
    g = _new_game(client, british="ai", axis="ai")
    gid = g["game_id"]
    t0 = g["turn"]
    s = client.post(f"/api/games/{gid}/end-turn").json()
    assert s["turn"] == t0 + 1
    # a second consecutive AI turn also works (flags rebuilt each turn)
    s = client.post(f"/api/games/{gid}/end-turn").json()
    assert s["turn"] == t0 + 2


def test_ui_layout_comes_from_the_renderer(client):
    ui = client.get("/api/ui").json()
    assert ui["view_cells"] == 22 and ui["panel_x"] == 176
    labels = [m["label"] for m in ui["menu"]]
    assert "M MOVE" in labels and "ENTER TO END" in labels


def test_screen_endpoint_serves_png_and_clamps(client):
    g = _new_game(client)
    gid = g["game_id"]
    r = client.get(f"/api/games/{gid}/screen", params={"ox": 9999, "oy": -5})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:4] == b"\x89PNG"


def test_unknown_game_is_404(client):
    assert client.get("/api/games/99999").status_code == 404
