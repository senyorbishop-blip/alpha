import asyncio
from pathlib import Path
import pytest

from server.handlers.map_editor import handle_map_set_url
from server.handlers import tokens as token_handlers
from server.restore import restore_session_from_db
from server.http.session_access import can_user_place_creatures
from server.session import POI, Session, User, Token


class FakeRequest:
    def __init__(self, user=None):
        self.state = type('State', (), {'user': user})()
        self.cookies = {}
        self.headers = {}


def test_can_user_place_creatures_allows_true_dm_even_in_player_preview():
    session = Session(id='TEST1')
    dm = User(id='dm-user', name='DM', role='dm')
    session.users[dm.id] = dm
    session.dm_id = dm.id

    permission = can_user_place_creatures(
        session,
        user=dm,
        mode='player_preview',
        request=FakeRequest({'id': 'dm-user'}),
        fallback_user_id='dm-user',
    )

    assert permission['allowed'] is True
    assert permission['preview_mode'] is True
    assert permission['authority']['is_session_dm'] is True


def test_map_set_url_updates_poi_scene_without_overwriting_world_map():
    session = Session(id='TEST2')
    dm = User(id='dm-user', name='DM', role='dm')
    session.users[dm.id] = dm
    session.dm_id = dm.id
    session.map_image_url = '/static/maps/world.png'
    session.pois['poi-1'] = POI(id='poi-1', x=0, y=0, name='Inn', local_map_url='/static/maps/old-poi.png')

    asyncio.run(handle_map_set_url({'map_image_url': '/static/maps/new-poi.png', 'map_context': 'poi-1', 'poi_id': 'poi-1'}, session, dm))

    assert session.map_image_url == '/static/maps/world.png'
    assert session.pois['poi-1'].local_map_url == '/static/maps/new-poi.png'
    assert session.map_documents['poi-1']['assets']['background_url'] == '/static/maps/new-poi.png'


def test_map_exit_paths_restore_tokens_after_scene_clear():
    source = Path("client/templates/play.html").read_text(encoding="utf-8")

    close_start = source.index("function closeLocalMap(options = {}) {")
    close_end = source.index("function jumpToDepth(targetDepth) {", close_start)
    close_body = source[close_start:close_end]
    assert close_body.index("clearRenderedSceneState();") < close_body.index("_restoreVisibleTokensForContext(targetCtx);")

    exit_start = source.index("function handleLocalMapExit(payload = {}) {")
    exit_end = source.index("// ═══════════════════════════════════════════════════════════════════", exit_start)
    exit_body = source[exit_start:exit_end]
    assert exit_body.index("clearRenderedSceneState();") < exit_body.index("_restoreVisibleTokensForContext('world');")


def test_restore_normalizes_token_map_context_to_known_scene():
    payload = {
        "id": "RESTORE_CTX_1",
        "dm_name": "DM",
        "player_invite": "PLAY1234",
        "viewer_invite": "VIEW1234",
        "created_at": 0,
        "map_image_url": "/static/maps/world.png",
        "map_documents": {"world": {"assets": {"background_url": "/static/maps/world.png"}}},
        "pois": [{"id": "poi-1", "x": 0, "y": 0, "name": "Inn", "map_context": "world"}],
        "tokens": [
            {"id": "tok-valid", "name": "Hero", "x": 0, "y": 0, "width": 40, "height": 40, "color": "#fff", "shape": "circle", "owner_id": "p1", "map_context": "poi-1"},
            {"id": "tok-bad", "name": "Ghost", "x": 0, "y": 0, "width": 40, "height": 40, "color": "#fff", "shape": "circle", "owner_id": None, "map_context": "deleted-poi"},
        ],
        "users": {},
    }

    restored, _ = restore_session_from_db(payload)

    assert restored.tokens["tok-valid"].map_context == "poi-1"
    assert restored.tokens["tok-bad"].map_context == "world"


def test_play_html_uses_authoritative_token_projection_context_helper():
    source = Path("client/templates/play.html").read_text(encoding="utf-8")
    assert "function _getAuthoritativeTokenDrawContext()" in source
    assert "const drawCtx = _getAuthoritativeTokenDrawContext();" in source


def test_state_sync_stale_dm_nav_guard_keeps_map_loaded():
    source = Path("client/templates/play.html").read_text(encoding="utf-8")
    anchor = "if (!shouldTrustServerNav) {"
    start = source.index(anchor)
    end = source.index("} else {", start)
    guard_body = source[start:end]
    assert "if (onLocal) {" in guard_body
    assert "if (ROLE === 'dm' && !_currentPoi && dmPoi) {" in guard_body
    assert "_currentPoi = dmPoi;" in guard_body
    assert "_dmMapContext = dmPoi.id || dmCtx;" in guard_body
    assert "loadMapImage(mapUrl, true);" in guard_body
    assert "else if (_worldMapImageUrl) {" in guard_body
    assert "_dmMapContext = 'world';" in guard_body
    assert "loadMapImage(_worldMapImageUrl, true);" in guard_body


def test_viewer_state_includes_dm_scene_context_tokens():
    session = Session(id="VIEWER-CTX")
    dm = User(id="dm-user", name="DM", role="dm")
    viewer = User(id="viewer-user", name="Watcher", role="viewer")
    session.dm_id = dm.id
    session.users = {dm.id: dm, viewer.id: viewer}
    session.dm_map_context = "poi-inn"
    session.tokens = {
        "tok-local": Token(
            id="tok-local",
            name="Scene Token",
            x=0.0,
            y=0.0,
            width=40.0,
            height=40.0,
            color="#fff",
            shape="circle",
            owner_id=None,
            map_context="poi-inn",
        )
    }

    state = session.to_state_dict_for_role("viewer", viewer.id)

    assert "poi-inn" in session.visible_map_contexts_for_user(viewer.id)
    assert "tok-local" in state["tokens"]


@pytest.mark.anyio
async def test_scene_trigger_zone_enter_fires_action_bundle(monkeypatch):
    session = Session(id="TRIG-1")
    dm = User(id="dm", name="DM", role="dm")
    player = User(id="p1", name="Player", role="player")
    session.dm_id = dm.id
    session.users = {dm.id: dm, player.id: player}
    session.world_state = {
        "scene_trigger_zones": {
            "zone-a": {
                "id": "zone-a",
                "map_context": "world",
                "bounds": {"shape": "rect", "x": 40, "y": 40, "width": 40, "height": 40},
                "trigger_once": False,
                "repeatable": True,
                "visibility": {"mode": "party"},
                "on_enter": [
                    {"type": "ambient_profile", "payload": {"track": "forest", "volume": 0.6}},
                    {"type": "weather_preset", "payload": {"preset": "rain", "intensity": 0.8}},
                    {"type": "set_world_state_flag", "payload": {"key": "entered_grove", "value": True}},
                ],
                "on_exit": [],
            }
        }
    }
    tok = Token(id="tok", name="Hero", x=10, y=10, width=40, height=40, color="#fff", shape="circle", owner_id=player.id)
    session.tokens[tok.id] = tok

    sent = []

    async def _noop(*args, **kwargs):
        return None

    async def _broadcast(_sid, message, **kwargs):
        sent.append(message)

    monkeypatch.setattr(token_handlers, "_broadcast_token_event", _noop)
    monkeypatch.setattr(token_handlers, "_process_hazard_triggers_for_token", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)
    monkeypatch.setattr(token_handlers.manager, "broadcast", _broadcast)

    await token_handlers.handle_token_move({"token_id": tok.id, "x": 50, "y": 50}, session, player)

    assert session.sound_state["track"] == "forest"
    assert session.weather_state["weather_type"] == "rain"
    assert session.world_state["world_state_flags"]["entered_grove"] is True
    assert any(msg["type"] == "sound_set_ambient" for msg in sent)
    assert any(msg["type"] == "weather_sync" for msg in sent)


@pytest.mark.anyio
async def test_scene_trigger_zone_trigger_once_consumes(monkeypatch):
    session = Session(id="TRIG-2")
    dm = User(id="dm", name="DM", role="dm")
    player = User(id="p1", name="Player", role="player")
    session.dm_id = dm.id
    session.users = {dm.id: dm, player.id: player}
    session.world_state = {
        "scene_trigger_zones": {
            "once": {
                "id": "once",
                "map_context": "world",
                "bounds": {"shape": "rect", "x": 100, "y": 100, "width": 20, "height": 20},
                "trigger_once": True,
                "visibility": {"mode": "party"},
                "on_enter": [{"type": "set_world_state_flag", "payload": {"key": "once_flag", "value": 1}}],
                "on_exit": [],
            }
        }
    }
    tok = Token(id="tok", name="Hero", x=10, y=10, width=40, height=40, color="#fff", shape="circle", owner_id=player.id)
    session.tokens[tok.id] = tok

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(token_handlers, "_broadcast_token_event", _noop)
    monkeypatch.setattr(token_handlers, "_process_hazard_triggers_for_token", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)

    await token_handlers.handle_token_move({"token_id": tok.id, "x": 105, "y": 105}, session, player)
    first_consumed = list(session.world_state.get("scene_trigger_runtime", {}).get("consumed_zone_ids", []))
    await token_handlers.handle_token_move({"token_id": tok.id, "x": 30, "y": 30}, session, player)
    await token_handlers.handle_token_move({"token_id": tok.id, "x": 106, "y": 106}, session, player)

    assert "once" in first_consumed
    assert session.world_state["world_state_flags"]["once_flag"] == 1


@pytest.mark.anyio
async def test_scene_trigger_zone_repeatable_ambient_retriggers(monkeypatch):
    session = Session(id="TRIG-3")
    dm = User(id="dm", name="DM", role="dm")
    player = User(id="p1", name="Player", role="player")
    session.dm_id = dm.id
    session.users = {dm.id: dm, player.id: player}
    session.world_state = {
        "scene_trigger_zones": {
            "loop": {
                "id": "loop",
                "map_context": "world",
                "bounds": {"shape": "rect", "x": 200, "y": 200, "width": 20, "height": 20},
                "trigger_once": False,
                "cooldown_ms": 0,
                "debounce_ms": 0,
                "visibility": {"mode": "party"},
                "on_enter": [{"type": "ambient_profile", "payload": {"track": "dungeon"}}],
                "on_exit": [],
            }
        }
    }
    tok = Token(id="tok", name="Hero", x=10, y=10, width=40, height=40, color="#fff", shape="circle", owner_id=player.id)
    session.tokens[tok.id] = tok
    ambient_calls = []

    async def _noop(*args, **kwargs):
        return None

    async def _broadcast(_sid, message, **kwargs):
        if message.get("type") == "sound_set_ambient":
            ambient_calls.append(message)

    monkeypatch.setattr(token_handlers, "_broadcast_token_event", _noop)
    monkeypatch.setattr(token_handlers, "_process_hazard_triggers_for_token", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)
    monkeypatch.setattr(token_handlers.manager, "broadcast", _broadcast)

    await token_handlers.handle_token_move({"token_id": tok.id, "x": 205, "y": 205}, session, player)
    await token_handlers.handle_token_move({"token_id": tok.id, "x": 150, "y": 150}, session, player)
    await token_handlers.handle_token_move({"token_id": tok.id, "x": 206, "y": 206}, session, player)

    assert len(ambient_calls) == 2


@pytest.mark.anyio
async def test_scene_trigger_zone_visibility_owner_only_prevents_spoilers(monkeypatch):
    session = Session(id="TRIG-4")
    dm = User(id="dm", name="DM", role="dm")
    owner = User(id="p1", name="Owner", role="player")
    other = User(id="p2", name="Other", role="player")
    session.dm_id = dm.id
    session.users = {dm.id: dm, owner.id: owner, other.id: other}
    session.world_state = {
        "scene_trigger_zones": {
            "secret": {
                "id": "secret",
                "map_context": "world",
                "bounds": {"shape": "rect", "x": 20, "y": 20, "width": 20, "height": 20},
                "trigger_once": False,
                "visibility": {"mode": "owner_only"},
                "on_enter": [{"type": "living_world_event", "payload": {"event_type": "world_state_flag_set", "summary": "Secret found"}}],
                "on_exit": [],
            }
        }
    }
    tok = Token(id="tok", name="Owner Token", x=0, y=0, width=40, height=40, color="#fff", shape="circle", owner_id=owner.id)
    session.tokens[tok.id] = tok
    delivered = []

    async def _noop(*args, **kwargs):
        return None

    async def _send_to(_sid, user_id, message):
        if message.get("type") == "world_event_notice":
            delivered.append(str(user_id))

    monkeypatch.setattr(token_handlers, "_broadcast_token_event", _noop)
    monkeypatch.setattr(token_handlers, "_process_hazard_triggers_for_token", _noop)
    monkeypatch.setattr(token_handlers, "save_campaign_async", _noop)
    monkeypatch.setattr(token_handlers.manager, "send_to", _send_to)

    await token_handlers.handle_token_move({"token_id": tok.id, "x": 25, "y": 25}, session, owner)

    assert set(delivered) == {"dm", "p1"}
