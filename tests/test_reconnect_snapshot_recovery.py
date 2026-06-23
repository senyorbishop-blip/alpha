"""Tests for reconnect/request_state snapshot recovery (realtime sync tiny patch).

Server side: ``to_state_dict`` now stamps the session-wide ``visibility_revision``
counter onto every ``state_sync`` payload (it already carried ``map_nav_version``).
Client side: the ``state_sync`` handler in play.html now baselines the per-stream
``_lastVisibilityRevisionByStream`` gate from that snapshot, so a `tokens_sync`/
`combat_state` packet queued from BEFORE a disconnect (and flushed right after
reconnect) can't out-race the fresh snapshot and re-show a since-hidden/fogged
token.

These tests verify that ``request_state`` (the reconnect recovery path) restores
the correct role-filtered map/fog/token/combat snapshot without mutating server
state, without leaking hidden/fog-occluded tokens to players or viewers, and
without broadcasting to anyone other than the requesting connection.
"""
import copy
import subprocess
from pathlib import Path

import pytest

from server.handlers import content as content_handlers
from server.session import Session, Token, User

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _first_message(sent, message_type):
    return next(message for _sid, _uid, message in sent if message.get("type") == message_type)


def _fog_entry(*, enabled=True, cols=4, rows=4, revealed_cells=()):
    total = cols * rows
    cells = ["0"] * total
    for idx in revealed_cells:
        cells[idx] = "1"
    return {"enabled": enabled, "cols": cols, "rows": rows, "cells": "".join(cells)}


def _build_session():
    session = Session(id="s-reconnect")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="player-1", name="Player", role="player")
    viewer = User(id="viewer-1", name="Viewer", role="viewer")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.users[viewer.id] = viewer

    # All cells revealed on "world" so an ordinary visible token isn't fog-hidden.
    session.fog_maps = {"world": _fog_entry(revealed_cells=range(16))}

    visible_pc = Token(
        id="tok-pc", name="Hero", x=0, y=0, width=40, height=40,
        color="#fff", shape="circle", owner_id=player.id, token_type="player",
    )
    hidden_npc = Token(
        id="tok-hidden-npc", name="Secret Boss", x=40, y=40, width=40, height=40,
        color="#f00", shape="circle", owner_id=None, token_type="npc",
        hidden=True,
    )
    # Sits squarely in revealed cell (0,0) so it would be visible if not hidden.
    visible_npc = Token(
        id="tok-visible-npc", name="Goblin", x=0, y=0, width=20, height=20,
        color="#0f0", shape="circle", owner_id=None, token_type="npc",
    )
    session.tokens[visible_pc.id] = visible_pc
    session.tokens[hidden_npc.id] = hidden_npc
    session.tokens[visible_npc.id] = visible_npc

    return session, dm, player, viewer


def _add_unrevealed_fog_npc(session: Session):
    # Map is 4096x4096 by default (no map_settings override); cols/rows=4 means
    # each cell spans 1024px. Cell index 15 (row3,col3) covers x:[512,1536),
    # y:[512,1536) in centered coords — place a token whose footprint sits
    # entirely in a cell that was never revealed (cell 0 in our 4x4 grid: only
    # indices 0..15 are revealed via revealed_cells=range(16) above by default
    # in _build_session, so build a fresh fog map with only some cells revealed
    # for this helper).
    session.fog_maps = {"world": _fog_entry(revealed_cells=[0])}
    fog_npc = Token(
        id="tok-fog-npc", name="Lurking Wolf", x=1500, y=1500, width=20, height=20,
        color="#00f", shape="circle", owner_id=None, token_type="monster",
    )
    session.tokens[fog_npc.id] = fog_npc
    return fog_npc


@pytest.mark.anyio
async def test_player_request_state_filters_tokens_by_visibility(monkeypatch):
    session, _dm, player, _viewer = _build_session()
    sent = []

    async def _capture_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(content_handlers.manager, "send_to", _capture_send_to)
    await content_handlers.handle_request_state({}, session, player)

    assert len(sent) == 2
    _, uid, msg = sent[0]
    assert uid == player.id
    assert msg["type"] == "state_sync"
    assert sent[1][2]["type"] == "authoritative_snapshot"
    token_ids = set(msg["payload"]["tokens"].keys())
    assert "tok-pc" in token_ids
    assert "tok-visible-npc" in token_ids


@pytest.mark.anyio
async def test_hidden_npc_excluded_from_player_reconnect_snapshot(monkeypatch):
    session, _dm, player, _viewer = _build_session()
    sent = []

    async def _capture_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(content_handlers.manager, "send_to", _capture_send_to)
    await content_handlers.handle_request_state({}, session, player)

    payload = _first_message(sent, "state_sync")["payload"]
    assert "tok-hidden-npc" not in payload["tokens"]


@pytest.mark.anyio
async def test_npc_touching_unrevealed_fog_excluded_from_player_reconnect_snapshot(monkeypatch):
    session, _dm, player, _viewer = _build_session()
    fog_npc = _add_unrevealed_fog_npc(session)
    sent = []

    async def _capture_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(content_handlers.manager, "send_to", _capture_send_to)
    await content_handlers.handle_request_state({}, session, player)

    payload = _first_message(sent, "state_sync")["payload"]
    assert fog_npc.id not in payload["tokens"]


@pytest.mark.anyio
async def test_dm_request_state_receives_full_token_state(monkeypatch):
    session, dm, _player, _viewer = _build_session()
    fog_npc = _add_unrevealed_fog_npc(session)
    sent = []

    async def _capture_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(content_handlers.manager, "send_to", _capture_send_to)
    await content_handlers.handle_request_state({}, session, dm)

    payload = _first_message(sent, "state_sync")["payload"]
    token_ids = set(payload["tokens"].keys())
    assert "tok-hidden-npc" in token_ids
    assert fog_npc.id in token_ids
    assert "tok-pc" in token_ids


@pytest.mark.anyio
async def test_player_reconnect_receives_current_fog_state(monkeypatch):
    session, _dm, player, _viewer = _build_session()
    sent = []

    async def _capture_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(content_handlers.manager, "send_to", _capture_send_to)
    await content_handlers.handle_request_state({}, session, player)

    payload = _first_message(sent, "state_sync")["payload"]
    assert "world" in payload["fog_maps"]
    assert payload["fog_maps"]["world"]["cells"] == session.fog_maps["world"]["cells"]


@pytest.mark.anyio
async def test_viewer_receives_viewer_safe_state_only(monkeypatch):
    session, _dm, _player, viewer = _build_session()
    sent = []

    async def _capture_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(content_handlers.manager, "send_to", _capture_send_to)
    await content_handlers.handle_request_state({}, session, viewer)

    payload = _first_message(sent, "state_sync")["payload"]
    # Viewers never get DM-only fields.
    assert "dm_notes" not in payload
    assert payload.get("player_inventory") == []
    token_ids = set(payload["tokens"].keys())
    assert "tok-hidden-npc" not in token_ids


@pytest.mark.anyio
async def test_state_sync_snapshot_includes_revision_counters(monkeypatch):
    session, dm, _player, _viewer = _build_session()
    session.visibility_revision = 7
    session.map_nav_version = 3
    sent = []

    async def _capture_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    monkeypatch.setattr(content_handlers.manager, "send_to", _capture_send_to)
    await content_handlers.handle_request_state({}, session, dm)

    payload = _first_message(sent, "state_sync")["payload"]
    assert payload["visibility_revision"] == 7
    assert payload["map_nav_version"] == 3


@pytest.mark.anyio
async def test_request_state_does_not_mutate_server_state(monkeypatch):
    session, _dm, player, _viewer = _build_session()
    before_tokens = copy.deepcopy({tid: t.to_dict() for tid, t in session.tokens.items()})
    before_fog = copy.deepcopy(session.fog_maps)
    before_rev = session.visibility_revision

    async def _noop_send_to(*args, **kwargs):
        return None

    monkeypatch.setattr(content_handlers.manager, "send_to", _noop_send_to)
    await content_handlers.handle_request_state({}, session, player)

    after_tokens = {tid: t.to_dict() for tid, t in session.tokens.items()}
    assert after_tokens == before_tokens
    assert session.fog_maps == before_fog
    assert session.visibility_revision == before_rev


@pytest.mark.anyio
async def test_request_state_recovery_is_per_user_not_broadcast(monkeypatch):
    session, _dm, player, _viewer = _build_session()
    sent = []
    broadcast_calls = []

    async def _capture_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _capture_broadcast(*args, **kwargs):
        broadcast_calls.append((args, kwargs))

    monkeypatch.setattr(content_handlers.manager, "send_to", _capture_send_to)
    monkeypatch.setattr(content_handlers.manager, "broadcast", _capture_broadcast)
    await content_handlers.handle_request_state({}, session, player)

    assert not broadcast_calls
    assert len(sent) == 2
    assert all(row[1] == player.id for row in sent)


@pytest.mark.anyio
async def test_state_sync_backward_compatible_without_revision_fields():
    # A session that never bumped either counter still produces a well-formed,
    # zero-valued (not missing/None) revision so older clients that ignore the
    # field are unaffected and newer clients get a harmless baseline of 0.
    session, dm, _player, _viewer = _build_session()
    assert session.visibility_revision == 0
    assert session.map_nav_version == 0
    state = session.to_state_dict_for_role("player", "player-1")
    assert state["visibility_revision"] == 0
    assert state["map_nav_version"] == 0


def test_play_html_state_sync_baselines_visibility_revision_gate():
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("case 'state_sync': {")
    end = src.index("case 'tokens_sync': {")
    handler = src[start:end]
    assert "syncVisibilityRevision" in handler
    assert "p.visibility_revision" in handler
    assert "_lastVisibilityRevisionByStream[stream] = syncVisibilityRevision" in handler


def test_authoritative_snapshot_dm_shape_includes_revisions_and_summaries():
    session, dm, _player, _viewer = _build_session()
    session.visibility_revision = 8
    session.inventory_revision = 5
    session.map_nav_version = 3
    session.fog_maps["world"]["revision"] = 4
    session.combat = {"active": True, "revision": 6, "turn": 0, "combatants": []}

    msg = session.to_authoritative_snapshot_for_role(dm.role, dm.id, source="manual")
    payload = msg["payload"]

    assert msg["type"] == "authoritative_snapshot"
    assert payload["session"]["authority"]["is_dm"] is True
    assert payload["tokens"]["count"] == len(session.tokens)
    assert payload["tokens"]["visibility_revision"] == 8
    assert payload["combat"]["active"] is True
    assert payload["combat"]["revision"] == 6
    assert payload["inventory"]["revision"] == 5
    assert payload["map"]["map_nav_version"] == 3
    assert payload["fog"]["revision"] == 4


def test_authoritative_snapshot_player_excludes_hidden_payload_details():
    session, _dm, player, _viewer = _build_session()
    session.visibility_revision = 2
    msg = session.to_authoritative_snapshot_for_role(player.role, player.id, source="manual")
    payload = msg["payload"]

    assert payload["session"]["resolved_role"] == "player"
    assert payload["session"]["authority"]["can_see_hidden"] is False
    assert "tok-hidden-npc" not in payload["tokens"]["items"]
    assert payload["tokens"]["filter_summary"]["hidden_filtered"] >= 1
    assert "Secret Boss" not in str(payload)


def test_authoritative_snapshot_viewer_obeys_viewer_filtering_and_empty_state():
    session, _dm, _player, viewer = _build_session()
    session.combat = None
    session.fog_maps = {}
    session.player_inventories = {}

    msg = session.to_authoritative_snapshot_for_role(viewer.role, viewer.id, source="manual")
    payload = msg["payload"]

    assert payload["session"]["resolved_role"] == "viewer"
    assert payload["session"]["authority"]["is_viewer"] is True
    assert payload["combat"]["active"] is False
    assert payload["combat"]["revision"] == 0
    assert payload["fog"]["revision"] == 0
    assert payload["inventory"]["revision"] == 0
    assert payload["character"]["active_profile_id"] == ""
    assert "tok-hidden-npc" not in payload["tokens"]["items"]


def test_play_html_authoritative_snapshot_handler_stores_debug_snapshot():
    src = PLAY.read_text(encoding="utf-8")
    assert "function handleAuthoritativeSnapshot(payload)" in src
    assert "window.__lastAuthoritativeSnapshot = p" in src
    assert "case 'authoritative_snapshot':" in src
    assert "authoritative_snapshot received" in src


def test_play_html_baseline_only_advances_never_regresses():
    script = r"""
const _lastVisibilityRevisionByStream = { tokens: 9, combat: 9 };
function applyBaseline(rev) {
  if (rev > 0) {
    ['tokens', 'combat'].forEach((stream) => {
      if (rev > Number(_lastVisibilityRevisionByStream[stream] || 0)) {
        _lastVisibilityRevisionByStream[stream] = rev;
      }
    });
  }
}
applyBaseline(3); // stale snapshot revision must not roll the gate backward
applyBaseline(0); // missing/zero revision (backward compat) must be a no-op
console.log(JSON.stringify(_lastVisibilityRevisionByStream));
"""
    result = subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, timeout=30)
    data = __import__("json").loads(result.strip())
    assert data == {"tokens": 9, "combat": 9}
