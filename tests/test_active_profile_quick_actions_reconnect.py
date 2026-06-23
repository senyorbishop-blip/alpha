"""Tests for PR 5: active-profile/Quick Actions reconnect hardening.

Covers:
  - authoritative_snapshot's character/spells/inventory hydration_status for
    an active profile that is present, missing, or unselected.
  - the JWT-authenticated reconnect-safe fallbacks in
    resolve_owned_profile_or_403 (active-session-profile / token-linked
    profile) that let a restored session keep granting a user access to
    their own active profile without opening up arbitrary profile_id access.
  - the inventory/equipment summary block on the snapshot.
"""
from pathlib import Path

import server.character.routes as character_routes
from server.character.routes import resolve_owned_profile_or_403
from server.session import Session, Token, User

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _profile(profile_id: str, name: str = "") -> dict:
    return {
        "id": profile_id,
        "name": name or profile_id,
        "nativeCharacter": {
            "identity": {"name": name or profile_id, "className": "Sorcerer"},
            "classes": [{"classId": "sorcerer", "level": 5}],
            "abilities": {},
            "spellState": {"known": ["fireball", "fire-bolt"], "prepared": ["fireball"], "slots": {}, "rituals": []},
        },
    }


def _build_session(*, active_profile_id: str = "f-bishop") -> Session:
    session = Session(id="s-active-profile")
    dm = User(id="dm-1", name="DM", role="dm")
    player = User(id="player-1", name="Bishop", role="player")
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.char_profiles = {"bishop": [_profile("f-bishop", "Bishop")]}
    if active_profile_id:
        session.active_char_profiles = {player.id: active_profile_id}
    return session


def test_authoritative_snapshot_reports_ok_hydration_for_active_profile():
    session = _build_session()
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    payload = msg["payload"]

    assert payload["character"]["active_profile_id"] == "f-bishop"
    assert payload["character"]["hydration_status"] == "ok"
    assert payload["character"]["summary"]["name"] == "Bishop"
    assert payload["spells"]["hydration_status"] == "ok"
    assert payload["spells"]["summary"]["known_count"] == 2


def test_authoritative_snapshot_reports_missing_profile_when_no_active_profile_selected():
    session = _build_session(active_profile_id="")
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    payload = msg["payload"]

    assert payload["character"]["active_profile_id"] == ""
    assert payload["character"]["hydration_status"] == "missing_profile"
    assert payload["spells"]["hydration_status"] == "missing_profile"


def test_authoritative_snapshot_reports_missing_runtime_when_active_profile_row_is_gone():
    # Active profile id is set, but the profile row itself was removed/never
    # restored (e.g. partial DB restore) — this must be distinguishable from
    # "no profile selected" so the client can show a different error.
    session = _build_session(active_profile_id="ghost-profile")
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    payload = msg["payload"]

    assert payload["character"]["active_profile_id"] == "ghost-profile"
    assert payload["character"]["hydration_status"] == "missing_runtime"
    assert payload["spells"]["hydration_status"] == "missing_runtime"


def test_authoritative_snapshot_inventory_summary_includes_equipped_items_for_owner():
    session = _build_session()
    session.player_inventories = {
        "bishop": [
            {"id": "i1", "name": "Thunder Mage Quarterstaff +3", "equipped": True, "rarity": "rare"},
            {"id": "i2", "name": "Dagger", "equipped": True, "rarity": "common"},
            {"id": "i3", "name": "Spare Rope", "equipped": False, "rarity": "common"},
        ]
    }
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    inventory = msg["payload"]["inventory"]

    assert inventory["hydration_status"] == "ok"
    assert inventory["summary"]["item_count"] == 3
    assert inventory["summary"]["equipped_count"] == 2
    names = {item["name"] for item in inventory["summary"]["equipped_items"]}
    assert names == {"Thunder Mage Quarterstaff +3", "Dagger"}


def test_authoritative_snapshot_never_leaks_other_players_inventory_to_a_player():
    session = _build_session()
    session.player_inventories = {
        "bishop": [{"id": "i1", "name": "Bishop's Dagger", "equipped": True}],
        "other player": [{"id": "j1", "name": "Other Player's Secret Ring", "equipped": True}],
    }
    msg = session.to_authoritative_snapshot_for_role("player", "player-1", source="ws_connect")
    assert "Other Player's Secret Ring" not in str(msg["payload"]["inventory"])


def _session_for_spell_access() -> Session:
    session = Session(id="S1")
    dm = User(id="dm-1", name="DM", role="dm")
    player_a = User(id="player-a", name="Player A", role="player")
    session.users = {"dm-1": dm, "player-a": player_a}
    session.char_profiles = {"player a": [_profile("profile-a", "Player A")]}
    return session


def test_active_session_profile_fallback_grants_jwt_user_their_own_active_profile(monkeypatch):
    # Simulates the bug report: the owner-key bucket lookup misses (e.g. the
    # JWT account's display name doesn't match the bucket key after a server
    # restart) but the session already restored active_char_profiles for this
    # user pointing at profile-a — that alone should be enough to authorize.
    session = _session_for_spell_access()
    session.char_profiles = {"someone else": [_profile("profile-a", "Player A")]}
    session.active_char_profiles = {"player-a": "profile-a"}
    auth_user = {"id": "player-a", "name": "Player A"}

    profile = resolve_owned_profile_or_403(session, auth_user, "profile-a")
    assert profile["id"] == "profile-a"


def test_active_session_profile_fallback_does_not_grant_other_profiles(monkeypatch):
    session = _session_for_spell_access()
    session.char_profiles = {
        "someone else": [_profile("profile-a", "Player A")],
        "player b": [_profile("profile-b", "Player B")],
    }
    session.active_char_profiles = {"player-a": "profile-a"}
    auth_user = {"id": "player-a", "name": "Player A"}

    try:
        resolve_owned_profile_or_403(session, auth_user, "profile-b")
        assert False, "expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403


def test_token_linked_profile_fallback_grants_jwt_user_their_linked_profile():
    session = _session_for_spell_access()
    session.char_profiles = {"someone else": [_profile("profile-a", "Player A")]}
    session.tokens["tok-a"] = Token(
        id="tok-a", name="Player A", x=0, y=0, width=40, height=40,
        color="#fff", shape="circle", owner_id="player-a", token_type="player",
        profile_id="profile-a",
    )
    auth_user = {"id": "player-a", "name": "Player A"}

    profile = resolve_owned_profile_or_403(session, auth_user, "profile-a")
    assert profile["id"] == "profile-a"


def test_token_linked_profile_fallback_requires_matching_token_owner():
    session = _session_for_spell_access()
    session.char_profiles = {"someone else": [_profile("profile-a", "Player A")]}
    session.tokens["tok-a"] = Token(
        id="tok-a", name="Someone", x=0, y=0, width=40, height=40,
        color="#fff", shape="circle", owner_id="player-b", token_type="player",
        profile_id="profile-a",
    )
    auth_user = {"id": "player-a", "name": "Player A"}

    try:
        resolve_owned_profile_or_403(session, auth_user, "profile-a")
        assert False, "expected HTTPException"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403


def test_play_html_loads_auth_js_before_first_runtime_script():
    src = PLAY.read_text(encoding="utf-8")
    auth_idx = src.index('<script src="/static/js/auth.js"></script>')
    diagnostics_idx = src.index('<script src="/static/js/core/diagnostics.js"></script>')
    assert auth_idx < diagnostics_idx


def test_play_html_defines_apply_authoritative_character_state():
    src = PLAY.read_text(encoding="utf-8")
    assert "function applyAuthoritativeCharacterState(payload, source)" in src
    assert "window.applyAuthoritativeCharacterState = applyAuthoritativeCharacterState" in src
    assert "character:quick-actions-refresh" in src


def test_play_html_handle_authoritative_snapshot_invokes_character_apply_path():
    src = PLAY.read_text(encoding="utf-8")
    start = src.index("function handleAuthoritativeSnapshot(payload)")
    end = src.index("window.handleAuthoritativeSnapshot = handleAuthoritativeSnapshot;")
    handler = src[start:end]
    assert "applyAuthoritativeCharacterState(" in handler
