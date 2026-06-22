from types import SimpleNamespace

from fastapi.testclient import TestClient

import main
import server.character.routes as character_routes


def _csrf_headers(client: TestClient) -> dict:
    client.get("/join")
    token = client.cookies.get("csrf_token") or ""
    return {"X-CSRF-Token": token} if token else {}


def _profile(profile_id: str, known=None, prepared=None) -> dict:
    return {
        "id": profile_id,
        "name": profile_id,
        "nativeCharacter": {
            "identity": {"name": profile_id},
            "classes": [{"classId": "wizard", "level": 5}],
            "abilities": {},
            "spellState": {
                "known": list(known or []),
                "prepared": list(prepared or []),
                "slots": {},
                "rituals": [],
            },
        },
    }


def _session() -> SimpleNamespace:
    dm = SimpleNamespace(id="dm-1", name="Dungeon Master", role="dm")
    player_a = SimpleNamespace(id="player-a", name="Player A", role="player")
    player_b = SimpleNamespace(id="player-b", name="Player B", role="player")
    return SimpleNamespace(
        id="S1",
        dm_id="dm-1",
        users={"dm-1": dm, "player-a": player_a, "player-b": player_b},
        char_profiles={
            "player a": [_profile("profile-a", known=["mage-hand"], prepared=[])],
            "player b": [_profile("profile-b", known=["fireball"], prepared=["fireball"])],
        },
    )


def _install_common_spell_mocks(monkeypatch, session, auth_holder):
    async def _fake_save_campaign(_session):
        return None

    def _fake_manifest(native):
        state = native.get("spellState") or {}
        cards = [
            {"id": spell_id, "isKnown": spell_id in set(state.get("known") or []), "isPrepared": spell_id in set(state.get("prepared") or [])}
            for spell_id in ["mage-hand", "fireball", "shield"]
        ]
        return {
            "known": list(state.get("known") or []),
            "prepared": list(state.get("prepared") or []),
            "slots": state.get("slots") or {},
            "rituals": state.get("rituals") or [],
            "limits": {},
            "validation": {"ok": True},
            "cards": cards,
        }

    def _fake_validate(**kwargs):
        return {
            "ok": True,
            "known": list(kwargs.get("known") or []),
            "prepared": list(kwargs.get("prepared") or []),
            "limits": {},
            "errors": [],
        }

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: auth_holder["user"])
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(character_routes, "save_campaign_async", _fake_save_campaign)
    monkeypatch.setattr(character_routes, "build_character_spell_manifest", _fake_manifest)
    monkeypatch.setattr(character_routes, "repair_spell_state_for_document", lambda *args, **kwargs: None)
    monkeypatch.setattr(character_routes, "validate_spell_selection", _fake_validate)
    monkeypatch.setattr(
        character_routes,
        "list_compendium_spells",
        lambda **kwargs: [
            {"id": "mage-hand", "name": "Mage Hand", "classUnlockLevels": {"wizard": 1}},
            {"id": "fireball", "name": "Fireball", "classUnlockLevels": {"wizard": 5}},
        ],
    )
    monkeypatch.setattr(
        character_routes,
        "get_compendium_spell_by_id",
        lambda spell_id: {"id": spell_id, "name": spell_id.title(), "classUnlockLevels": {"wizard": 1}},
    )


def test_player_can_update_their_own_known_spells(monkeypatch):
    session = _session()
    auth_holder = {"user": {"id": "player-a", "username": "Player A"}}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.post(
            "/api/character/profile-a/spells/known",
            json={"session_id": "s1", "known": ["mage-hand", "shield"]},
            headers=_csrf_headers(client),
        )

    assert res.status_code == 200
    assert res.json()["known"] == ["mage-hand", "shield"]
    assert session.char_profiles["player a"][0]["nativeCharacter"]["spellState"]["known"] == ["mage-hand", "shield"]


def test_player_cannot_update_another_players_known_or_prepared_spells(monkeypatch):
    session = _session()
    auth_holder = {"user": {"id": "player-a", "username": "Player A"}}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        known_res = client.post(
            "/api/character/profile-b/spells/known",
            json={"session_id": "s1", "known": ["mage-hand"]},
            headers=headers,
        )
        prepared_res = client.post(
            "/api/character/profile-b/spells/prepare",
            json={"session_id": "s1", "prepared": []},
            headers=headers,
        )

    assert known_res.status_code == 403
    assert prepared_res.status_code == 403
    assert session.char_profiles["player b"][0]["nativeCharacter"]["spellState"]["known"] == ["fireball"]
    assert session.char_profiles["player b"][0]["nativeCharacter"]["spellState"]["prepared"] == ["fireball"]


def test_player_cannot_hydrate_another_players_spell_manifest(monkeypatch):
    session = _session()
    auth_holder = {"user": {"id": "player-a", "username": "Player A"}}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        manifest_res = client.get("/api/character/profile-b/spells?session_id=s1")
        known_res = client.get("/api/character/profile-b/spells/known?session_id=s1")
        library_res = client.get("/api/spells?profile_id=profile-b&session_id=s1")
        detail_res = client.get("/api/spells/fireball?profile_id=profile-b&session_id=s1")

    assert manifest_res.status_code == 403
    assert known_res.status_code == 403
    assert library_res.status_code == 403
    assert detail_res.status_code == 403


def test_dm_can_hydrate_and_update_player_spell_profiles(monkeypatch):
    session = _session()
    auth_holder = {"user": {"id": "dm-1", "username": "Dungeon Master"}}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        manifest_res = client.get("/api/character/profile-b/spells?session_id=s1")
        library_res = client.get("/api/spells?profile_id=profile-b&session_id=s1")
        update_res = client.post(
            "/api/character/profile-b/spells/known",
            json={"session_id": "s1", "known": ["fireball", "shield"]},
            headers=headers,
        )

    assert manifest_res.status_code == 200
    assert manifest_res.json()["known"] == ["fireball"]
    assert library_res.status_code == 200
    assert library_res.json()["manifest"]["known"] == ["fireball"]
    assert update_res.status_code == 200
    assert session.char_profiles["player b"][0]["nativeCharacter"]["spellState"]["known"] == ["fireball", "shield"]


def test_player_can_update_their_own_prepared_spells(monkeypatch):
    session = _session()
    auth_holder = {"user": {"id": "player-b", "username": "Player B"}}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.post(
            "/api/character/profile-b/spells/prepare",
            json={"session_id": "s1", "prepared": []},
            headers=_csrf_headers(client),
        )

    assert res.status_code == 200
    assert res.json()["prepared"] == []
    assert session.char_profiles["player b"][0]["nativeCharacter"]["spellState"]["prepared"] == []


def test_invalid_prepared_spells_do_not_mutate_native_spell_state(monkeypatch):
    session = _session()
    auth_holder = {"user": {"id": "player-b", "username": "Player B"}}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)
    calls = {"save": 0, "sync": 0}

    async def _fail_on_save(_session):
        calls["save"] += 1

    def _invalid_validate(**kwargs):
        return {
            "ok": False,
            "known": list(kwargs.get("known") or []),
            "prepared": list(kwargs.get("prepared") or []),
            "limits": {"preparedLimit": 1},
            "errors": ["Unknown prepared spell: meteor-swarm"],
        }

    def _record_sync(*args, **kwargs):
        calls["sync"] += 1

    monkeypatch.setattr(character_routes, "save_campaign_async", _fail_on_save)
    monkeypatch.setattr(character_routes, "validate_spell_selection", _invalid_validate)
    monkeypatch.setattr(character_routes, "_sync_native_spellbook_entries", _record_sync)

    native = session.char_profiles["player b"][0]["nativeCharacter"]
    assert native["spellState"]["prepared"] == ["fireball"]

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.post(
            "/api/character/profile-b/spells/prepare",
            json={"session_id": "s1", "prepared": ["meteor-swarm"]},
            headers=_csrf_headers(client),
        )

    assert res.status_code == 400
    assert native["spellState"]["prepared"] == ["fireball"]
    assert calls == {"save": 0, "sync": 0}


def test_session_member_guest_with_no_jwt_can_get_spells_for_owned_profile(monkeypatch):
    """A session-membership guest (no JWT account) who passes the socket/authority
    checks should not be rejected by HTTP reads with a 401 — the session-member
    fallback in resolve_owned_profile_or_403 should grant access to their own profile."""
    session = _session()
    auth_holder = {"user": None}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get(
            "/api/spells?profile_id=profile-a&session_id=s1&user_id=player-a",
        )

    assert res.status_code == 200
    assert res.json()["manifest"]["known"] == ["mage-hand"]


def test_session_member_guest_with_no_jwt_cannot_get_another_members_profile(monkeypatch):
    """The session-membership fallback must still enforce ownership: a guest
    cannot read another member's profile just by changing profile_id."""
    session = _session()
    auth_holder = {"user": None}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get(
            "/api/spells?profile_id=profile-b&session_id=s1&user_id=player-a",
        )

    assert res.status_code == 403


def test_session_member_guest_without_session_id_keeps_public_library_behavior(monkeypatch):
    """Bare /api/spells (no session_id/profile_id) must keep working without auth."""
    session = _session()
    auth_holder = {"user": None}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get("/api/spells")

    assert res.status_code == 200


def test_session_dm_guest_with_no_jwt_can_hydrate_player_profile(monkeypatch):
    """A session-membership DM (no JWT account) keeps session-wide read access."""
    session = _session()
    auth_holder = {"user": None}
    _install_common_spell_mocks(monkeypatch, session, auth_holder)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get(
            "/api/character/profile-b/spells?session_id=s1&user_id=dm-1",
        )

    assert res.status_code == 200
    assert res.json()["known"] == ["fireball"]
