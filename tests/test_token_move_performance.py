"""Token movement performance guard tests."""

from __future__ import annotations

from types import SimpleNamespace

from server.handlers import token_move_performance as perf


def _session():
    return SimpleNamespace(id="S1")


def _token():
    return SimpleNamespace(id="T1", map_context="world")


def test_tiny_same_cell_move_skips_heavy_work(monkeypatch):
    monkeypatch.setenv("TOKEN_MOVE_GRID_PX", "50")
    monkeypatch.setenv("TOKEN_MOVE_MIN_HEAVY_DISTANCE_PX", "3")

    decision = perf.decide_token_move_heavy_work(
        _session(),
        _token(),
        old_x=100,
        old_y=100,
        new_x=101,
        new_y=101,
        now=1000,
    )

    assert decision.run_heavy_work is False
    assert decision.reason == "tiny_same_cell_move"


def test_grid_cell_change_runs_heavy_work(monkeypatch):
    monkeypatch.setenv("TOKEN_MOVE_GRID_PX", "50")

    decision = perf.decide_token_move_heavy_work(
        _session(),
        _token(),
        old_x=149,
        old_y=100,
        new_x=151,
        new_y=100,
        now=1000,
    )

    assert decision.run_heavy_work is True
    assert decision.reason == "grid_cell_changed"


def test_final_drag_move_runs_heavy_work_even_same_cell(monkeypatch):
    monkeypatch.setenv("TOKEN_MOVE_GRID_PX", "50")

    decision = perf.decide_token_move_heavy_work(
        _session(),
        _token(),
        old_x=100,
        old_y=100,
        new_x=101,
        new_y=101,
        payload={"final": True},
        now=1000,
    )

    assert decision.run_heavy_work is True
    assert decision.reason == "final_move"


def test_same_cell_heavy_work_is_throttled(monkeypatch):
    monkeypatch.setenv("TOKEN_MOVE_GRID_PX", "50")
    monkeypatch.setenv("TOKEN_MOVE_MIN_HEAVY_DISTANCE_PX", "0")
    monkeypatch.setenv("TOKEN_MOVE_HEAVY_INTERVAL_SECONDS", "0.12")
    session = _session()
    token = _token()

    first = perf.decide_token_move_heavy_work(
        session,
        token,
        old_x=100,
        old_y=100,
        new_x=105,
        new_y=105,
        now=1000.0,
    )
    assert first.run_heavy_work is True
    assert first.reason == "interval_elapsed"
    perf.mark_token_move_heavy_work_ran(session, token, now=1000.0)

    second = perf.decide_token_move_heavy_work(
        session,
        token,
        old_x=105,
        old_y=105,
        new_x=110,
        new_y=110,
        now=1000.05,
    )

    assert second.run_heavy_work is False
    assert second.reason == "throttled_same_cell_move"


def test_same_cell_heavy_work_runs_after_interval(monkeypatch):
    monkeypatch.setenv("TOKEN_MOVE_GRID_PX", "50")
    monkeypatch.setenv("TOKEN_MOVE_MIN_HEAVY_DISTANCE_PX", "0")
    monkeypatch.setenv("TOKEN_MOVE_HEAVY_INTERVAL_SECONDS", "0.12")
    session = _session()
    token = _token()
    perf.mark_token_move_heavy_work_ran(session, token, now=1000.0)

    decision = perf.decide_token_move_heavy_work(
        session,
        token,
        old_x=105,
        old_y=105,
        new_x=110,
        new_y=110,
        now=1000.2,
    )

    assert decision.run_heavy_work is True
    assert decision.reason == "interval_elapsed"


def test_map_context_change_runs_heavy_work():
    decision = perf.decide_token_move_heavy_work(
        _session(),
        _token(),
        old_x=100,
        old_y=100,
        new_x=101,
        new_y=101,
        payload={"old_map_context": "world", "map_context": "dungeon"},
        now=1000,
    )

    assert decision.run_heavy_work is True
    assert decision.reason == "map_context_changed"
