"""Tests for the single canonical ownership resolver.

These cover the regression where a session-link player (no JWT) whose
combatant / profile is keyed by their resolved ``player_key`` (``auth_<id>``)
was wrongly rejected — initiative rolls silently dropped with "You may only
roll initiative for your own character." and /api/spells returning 401/403 —
even though they legitimately own the thing.

The resolver must still BLOCK a player from another player's combatant/profile.
"""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main
import server.character.routes as character_routes
from server.handlers import combat as combat_handlers
from server.session import (
    Session,
    Token,
    User,
    owner_id_matches_user,
    resolve_owner_identity,
)


# ── Unit: canonical resolver ────────────────────────────────────────────────


def test_resolve_owner_identity_includes_id_name_and_player_key():
    user = User(id="u1", name="Player One", role="player")
    user.player_key = "auth_acct-7"

    identity = resolve_owner_identity(None, user)

    assert identity == {"u1", "player one", "auth_acct-7"}


def test_resolve_owner_identity_handles_missing_player_key():
    user = User(id="u1", name="Player One", role="player")
    assert resolve_owner_identity(None, user) == {"u1", "player one"}


def test_resolve_owner_identity_none_user_is_empty():
    assert resolve_owner_identity(None, None) == set()


def test_owner_id_matches_user_across_all_identity_forms():
    user = User(id="u1", name="Player One", role="player")
    user.player_key = "auth_acct-7"

    # user id, player_key, and (case/space-insensitive) display name all match
    assert owner_id_matches_user("u1", None, user) is True
    assert owner_id_matches_user("auth_acct-7", None, user) is True
    assert owner_id_matches_user("  Player   One ", None, user) is True

    # empty owner and a different user's keys never match
    assert owner_id_matches_user("", None, user) is False
    assert owner_id_matches_user("u2", None, user) is False
    assert owner_id_matches_user("auth_acct-9", None, user) is False
    assert owner_id_matches_user("Player Two", None, user) is False


# ── Combat: session-link player rolls initiative for their own combatant ─────


def _build_combat_session():
    """Session where the player's combatant is keyed by their player_key, the
    case the old _owner_matches_user (id/name only) used to reject."""
    session = Session(id="s1")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="u1", name="Player One", role="player")
    player.player_key = "auth_acct-7"
    other = User(id="u2", name="Player Two", role="player")
    other.player_key = "auth_acct-9"
    session.users[dm.id] = dm
    session.users[player.id] = player
    session.users[other.id] = other
    session.tokens["hero"] = Token(
        id="hero", name="Hero", x=0, y=0, width=1, height=1,
        color="#fff", shape="circle", owner_id="auth_acct-7",
    )
    session.combat = {
        "active": True,
        "turn": 0,
        "round": 1,
        "combatants": [
            # owner_id is the player's player_key, NOT their session user id
            {"id": "cmb-hero", "token_id": "hero", "name": "Hero", "owner_id": "auth_acct-7", "initiative": None, "roll": None, "modifier": 2},
            {"id": "cmb-npc", "token_id": "npc", "name": "Goblin", "owner_id": None, "initiative": None, "roll": None, "modifier": 0},
        ],
    }
    return session, dm, player, other


def _patch_combat_io(monkeypatch, sent_errors):
    async def _fake_broadcast_combat(session):
        return None

    async def _fake_manager_broadcast(*args, **kwargs):
        return None

    async def _fake_send_to(session_id, user_id, message):
        if isinstance(message, dict) and message.get("type") == "error":
            sent_errors.append(message)
        return None

    async def _fake_save(*args, **kwargs):
        return True

    monkeypatch.setattr(combat_handlers, "_broadcast_combat", _fake_broadcast_combat)
    monkeypatch.setattr(combat_handlers.manager, "broadcast", _fake_manager_broadcast)
    monkeypatch.setattr(combat_handlers.manager, "send_to", _fake_send_to)
    monkeypatch.setattr(combat_handlers, "save_campaign_async", _fake_save)


@pytest.mark.anyio
async def test_session_link_player_can_roll_own_combatant_keyed_by_player_key(monkeypatch):
    session, dm, player, other = _build_combat_session()
    sent_errors = []
    _patch_combat_io(monkeypatch, sent_errors)

    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-hero", "roll": 15}, session, player,
    )

    hero = next(c for c in session.combat["combatants"] if c["id"] == "cmb-hero")
    assert hero["initiative"] == 17, "player must be able to roll for their own combatant"
    assert not sent_errors, "no 'roll for your own character' error should be sent"


@pytest.mark.anyio
async def test_session_link_player_blocked_from_other_players_combatant(monkeypatch):
    session, dm, player, other = _build_combat_session()
    sent_errors = []
    _patch_combat_io(monkeypatch, sent_errors)

    # `other` (a different player) tries to roll for the first player's combatant.
    await combat_handlers.handle_combat_roll_initiative(
        {"combatant_id": "cmb-hero", "roll": 15}, session, other,
    )

    hero = next(c for c in session.combat["combatants"] if c["id"] == "cmb-hero")
    assert hero["initiative"] is None, "another player must not roll someone else's initiative"
    assert sent_errors and sent_errors[0]["type"] == "error"


# ── Spells: session-link player (no JWT), profile bucket keyed by player_key ─


def _spell_profile(profile_id: str, known=None) -> dict:
    return {
        "id": profile_id,
        "name": profile_id,
        "nativeCharacter": {
            "identity": {"name": profile_id},
            "classes": [{"classId": "wizard", "level": 5}],
            "abilities": {},
            "spellState": {"known": list(known or []), "prepared": [], "slots": {}, "rituals": []},
        },
    }


def _spell_session() -> SimpleNamespace:
    # Player A is a session-link guest whose stored player_key keys the profile
    # bucket (not their display name) — the unified resolver must still match.
    player_a = SimpleNamespace(id="player-a", name="Player A", role="player", player_key="auth_acct-a")
    player_b = SimpleNamespace(id="player-b", name="Player B", role="player", player_key="auth_acct-b")
    return SimpleNamespace(
        id="S1",
        dm_id="dm-1",
        users={"player-a": player_a, "player-b": player_b},
        char_profiles={
            "auth_acct-a": [_spell_profile("profile-a", known=["mage-hand"])],
            "player b": [_spell_profile("profile-b", known=["fireball"])],
        },
        active_char_profiles={},
        tokens={},
    )


def _install_spell_mocks(monkeypatch, session):
    def _fake_manifest(native):
        state = native.get("spellState") or {}
        return {
            "known": list(state.get("known") or []),
            "prepared": list(state.get("prepared") or []),
            "slots": {}, "rituals": [], "limits": {}, "validation": {"ok": True},
            "cards": [],
        }

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: None)
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(character_routes, "build_character_spell_manifest", _fake_manifest)
    monkeypatch.setattr(character_routes, "build_multiclass_spell_context", lambda native: {"classSourcesBySpell": {}})
    monkeypatch.setattr(character_routes, "list_compendium_spells", lambda **kwargs: [])


def test_session_link_player_gets_200_on_spells_for_own_player_key_bucket(monkeypatch):
    session = _spell_session()
    _install_spell_mocks(monkeypatch, session)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get("/api/spells?profile_id=profile-a&session_id=s1&user_id=player-a")

    assert res.status_code == 200
    assert res.json()["manifest"]["known"] == ["mage-hand"]


def test_session_link_player_gets_403_on_other_players_spells(monkeypatch):
    session = _spell_session()
    _install_spell_mocks(monkeypatch, session)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get("/api/spells?profile_id=profile-b&session_id=s1&user_id=player-a")

    assert res.status_code == 403
