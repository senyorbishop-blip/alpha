import base64
import json

import anyio

from server.character.profile_assets import sanitize_profiles_for_websocket
from server.payload_diagnostics import PAYLOAD_ERROR_BYTES, payload_byte_size, top_level_payload_sizes
from server.session import Session, User
from server.handlers.common import _broadcast_token_state_sync


def _large_data_image(byte_count: int = 900_000) -> str:
    raw = b"\x89PNG\r\n\x1a\n" + (b"x" * byte_count)
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def test_profile_websocket_sync_strips_embedded_assets_and_adds_lazy_metadata():
    profiles = {
        "hero": [
            {
                "id": "pdf-bishop",
                "name": "Bishop",
                "avatarUrl": _large_data_image(),
                "pdfData": "data:application/pdf;base64," + base64.b64encode(b"p" * 700_000).decode("ascii"),
                "charBook": {"name": "Bishop", "avatarUrl": "/static/user_uploads/bishop.png"},
                "nativeCharacter": {"identity": {"name": "Bishop", "portraitUrl": "/static/user_uploads/bishop.png"}},
            }
        ]
    }

    cleaned = sanitize_profiles_for_websocket(profiles)
    encoded = json.dumps(cleaned)

    assert "data:image" not in encoded
    assert "data:application/pdf" not in encoded
    profile = cleaned["hero"][0]
    assert profile["portrait_url"].startswith("/static/user_uploads/")
    assert profile["thumb_url"]
    assert profile["asset_sync"] == {"embedded_assets": False, "lazy_assets": True}
    assert payload_byte_size({"type": "char_profiles_sync", "payload": {"profiles": cleaned["hero"]}}) < PAYLOAD_ERROR_BYTES


def test_state_sync_and_char_profiles_sync_stay_under_512kb_for_normal_join():
    session = Session(id="payload-test")
    player = User(id="p1", name="Hero", role="player", connected=True)
    session.users[player.id] = player
    session.char_profiles = {
        "hero": [
            {
                "id": "pdf-bishop",
                "name": "Bishop",
                "avatarUrl": _large_data_image(),
                "pdfData": "data:application/pdf;base64," + base64.b64encode(b"p" * 700_000).decode("ascii"),
                "charBook": {"name": "Bishop", "avatarUrl": "/static/user_uploads/bishop.png"},
            }
        ]
    }

    state_msg = {"type": "state_sync", "payload": session.to_state_dict_for_role("player", "p1")}
    profiles_msg = {"type": "char_profiles_sync", "payload": {"profiles": state_msg["payload"]["char_profiles"]}}

    assert payload_byte_size(state_msg) < PAYLOAD_ERROR_BYTES
    assert payload_byte_size(profiles_msg) < PAYLOAD_ERROR_BYTES
    assert top_level_payload_sizes(state_msg)[0][1] < PAYLOAD_ERROR_BYTES


def test_token_state_sync_fanout_only_targets_active_connected_sockets(monkeypatch):
    session = Session(id="fanout-test")
    session.users = {
        "active": User(id="active", name="Active", role="player", connected=True),
        "saved": User(id="saved", name="Saved", role="player", connected=False),
    }

    class FakeManager:
        def get_session_connections(self, session_id):
            assert session_id == session.id
            return {"active": object()}

        async def send_to(self, session_id, user_id, message):
            sent.append((session_id, user_id, message["type"]))
            return True

    sent = []
    monkeypatch.setattr("server.handlers.common.manager", FakeManager())

    anyio.run(_broadcast_token_state_sync, session)

    assert sent == [(session.id, "active", "tokens_sync")]
