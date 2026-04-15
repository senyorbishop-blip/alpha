from types import SimpleNamespace

from fastapi.testclient import TestClient

import main
import server.character.routes as character_routes


def _csrf_headers(client: TestClient) -> dict:
    client.get("/join")
    token = client.cookies.get("csrf_token") or ""
    return {"X-CSRF-Token": token} if token else {}



def test_character_library_requires_auth(monkeypatch):
    monkeypatch.setattr(character_routes, "get_request_user", lambda request: None)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get("/api/character/library?session_id=s1")

    assert res.status_code == 401



def test_character_library_returns_legacy_and_native_profile_summaries(monkeypatch):
    auth_user = {"id": "user-1", "username": "Lyra"}

    session = SimpleNamespace(
        char_profiles={
            "lyra": [
                {
                    "id": "profile-native",
                    "name": "Lyra Moonfall",
                    "sourceMode": "native",
                    "classSummary": "Wizard (Evocation)",
                    "level": 5,
                },
                {
                    "id": "profile-legacy",
                    "name": "Ari",
                    "charBook": {"className": "Druid", "subclass": "Moon", "level": 4},
                    "charSheet": {"classes": [{"name": "Druid", "level": 4}]},
                },
            ]
        }
    )

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: auth_user)
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get("/api/character/library?session_id=s1")

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["session_id"] == "S1"
    assert len(payload["profiles"]) == 2

    first = payload["profiles"][0]
    assert first["id"] == "profile-native"
    assert first["name"] == "Lyra Moonfall"
    assert first["classSummary"] == "Wizard (Evocation)"
    assert first["level"] == 5
    assert first["sourceMode"] == "native"

    second = payload["profiles"][1]
    assert second["id"] == "profile-legacy"
    assert second["classSummary"] == "Druid (Moon)"
    assert second["level"] == 4
    assert second["sourceMode"] == "legacy"



def test_character_library_empty_when_session_missing(monkeypatch):
    monkeypatch.setattr(character_routes, "get_request_user", lambda request: {"id": "user-1", "username": "Nomad"})
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: None)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get("/api/character/library?session_id=missing")

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["profiles"] == []


def test_character_library_include_native_returns_native_document_when_requested(monkeypatch):
    auth_user = {"id": "user-1", "username": "Lyra"}
    session = SimpleNamespace(
        char_profiles={
            "lyra": [
                {
                    "id": "profile-native",
                    "name": "Lyra Moonfall",
                    "sourceMode": "native",
                    "nativeCharacter": {"identity": {"name": "Lyra Moonfall"}, "classes": [{"classId": "wizard", "level": 2}]},
                }
            ]
        }
    )

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: auth_user)
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get("/api/character/library?session_id=s1&include_native=1")

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["profiles"][0]["id"] == "profile-native"
    assert isinstance(payload["profiles"][0].get("nativeCharacter"), dict)


def test_character_save_persists_native_profile_with_compatibility_payloads(monkeypatch):
    auth_user = {"id": "user-7", "username": "Nova"}
    session = SimpleNamespace(char_profiles={})
    saved = {"value": False}

    async def _fake_save_campaign(_session):
        saved["value"] = True

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: auth_user)
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(character_routes, "save_campaign_async", _fake_save_campaign)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        res = client.post(
            "/api/character/save",
            json={
                "session_id": "s1",
                "character_document": {
                    "sourceMode": "native",
                    "identity": {"name": "Nova Starfall"},
                    "species": {"name": "Elf", "speed": 35},
                    "classes": [{"name": "Wizard", "subclass": "Evocation", "level": 3}],
                    "abilities": {"scores": {"int": 16, "con": 12}},
                },
            },
            headers=headers,
        )

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["session_id"] == "S1"
    assert payload["profile"]["sourceMode"] == "native"

    stored_profiles = session.char_profiles.get("nova", [])
    assert len(stored_profiles) == 1
    stored = stored_profiles[0]
    assert stored["name"] == "Nova Starfall"
    assert isinstance(stored.get("charBook"), dict)
    assert isinstance(stored.get("charSheet"), dict)
    assert isinstance(stored.get("nativeCharacter"), dict)
    assert isinstance(stored.get("nativeRuntime"), dict)
    assert saved["value"] is True


def test_character_save_accepts_builder_draft_payload(monkeypatch):
    auth_user = {"id": "user-8", "username": "Aster"}
    session = SimpleNamespace(char_profiles={})

    async def _fake_save_campaign(_session):
        return None

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: auth_user)
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(character_routes, "save_campaign_async", _fake_save_campaign)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        res = client.post(
            "/api/character/save",
            json={
                "session_id": "s1",
                "character_document": {
                    "identity": {"name": "Aster Vale", "pronouns": "they/them"},
                    "species": {"id": "human"},
                    "origins": {
                        "backgroundId": "sage",
                        "languages": ["Common", "Elvish"],
                        "proficiencies": ["Arcana", "History"],
                    },
                    "class": {"id": "Rogue"},
                    "progression": {"level": 2, "talents": ["rogue-shadowstep"]},
                    "abilities": {"str": 8, "dex": 16, "con": 12, "int": 14, "wis": 10, "cha": 13},
                    "spellbook": {"known": ["minor illusion"], "prepared": ["disguise self"]},
                    "equipment": {"choices": ["Rapier", "Thieves' Tools"], "currency": {"gp": 15}},
                },
            },
            headers=headers,
        )

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["profile"]["name"] == "Aster Vale"
    assert payload["profile"]["sourceMode"] == "native"

    stored = session.char_profiles.get("aster", [])[0]
    assert stored["charSheet"]["totalLevel"] == 2
    assert stored["nativeCharacter"]["classes"][0]["classId"] == "Rogue"
    assert stored["nativeCharacter"]["background"]["id"] == "sage"
    assert stored["nativeCharacter"]["background"]["proficiencies"] == ["Arcana", "History"]
    assert stored["nativeCharacter"]["spellState"]["known"] == ["spell_minor_illusion"]
    assert stored["nativeCharacter"]["equipment"]["currency"]["gp"] == 15
    assert stored["nativeCharacter"]["talents"][0]["talentId"] == "rogue-shadowstep"


def test_character_content_catalog_requires_auth(monkeypatch):
    monkeypatch.setattr(character_routes, "get_request_user", lambda request: None)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get("/api/character/content/catalog")

    assert res.status_code == 401


def test_character_content_catalog_returns_species_classes_and_subclasses(monkeypatch):
    monkeypatch.setattr(character_routes, "get_request_user", lambda request: {"id": "u1", "username": "builder"})
    monkeypatch.setattr(
        character_routes,
        "get_builder_rules_catalog",
        lambda: {
            "rulesetId": "5e2024",
            "species": [
                {"id": "human", "displayName": "Human", "movement": {"walk": 30}, "traits": []},
            ],
            "classes": [
                {
                    "id": "fighter",
                    "displayName": "Fighter",
                    "subclassLevel": 3,
                    "progressionSummary": [{"level": 1, "summary": "Starter"}],
                },
            ],
            "subclasses": [
                {
                    "id": "champion",
                    "classId": "fighter",
                    "displayName": "Champion",
                    "flavorText": "Wins by consistency and superior fundamentals.",
                    "featureUnlocksByLevel": {"3": ["champion-improved-critical"]},
                    "features": [{"id": "champion-improved-critical", "displayName": "Improved Critical", "level": 3}],
                    "featureDefinitions": {"champion-improved-critical": {"summary": "Crit on 19-20."}},
                }
            ],
            "talents": [
                {
                    "id": "fighter-bulwark-stance",
                    "displayName": "Bulwark Stance",
                    "classRestrictions": ["fighter"],
                    "minimumLevel": 2,
                    "grants": [{"type": "derived_tag", "value": "talent:bulwark"}],
                    "tags": ["starter"],
                    "source": "casualdnd_talent",
                }
            ],
        },
    )

    with TestClient(main.app, raise_server_exceptions=False) as client:
        res = client.get("/api/character/content/catalog?rules_mode=casual")

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["rulesMode"] == "casual"
    assert payload["rulesetId"] == "5e2024"
    assert payload["species"][0]["id"] == "human"
    assert payload["classes"][0]["id"] == "fighter"
    assert payload["subclassesByClass"]["fighter"][0]["id"] == "champion"
    assert payload["subclassesByClass"]["fighter"][0]["flavorText"] == "Wins by consistency and superior fundamentals."
    assert payload["subclassesByClass"]["fighter"][0]["features"][0]["id"] == "champion-improved-critical"
    assert payload["subclassesByClass"]["fighter"][0]["featureDefinitions"]["champion-improved-critical"]["summary"] == "Crit on 19-20."
    assert payload["talentsByClass"]["fighter"][0]["id"] == "fighter-bulwark-stance"
    assert payload["talents"][0]["source"] == "casualdnd_talent"


def test_character_levelup_preview_returns_summary_and_choices(monkeypatch):
    monkeypatch.setattr(character_routes, "get_request_user", lambda request: {"id": "u1", "username": "builder"})

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        res = client.post(
            "/api/character/levelup/preview",
            json={
                "character_document": {
                    "sourceMode": "native",
                    "identity": {"name": "Bran"},
                    "classes": [{"classId": "fighter", "level": 2}],
                    "abilities": {"scores": {"con": 14}},
                }
            },
            headers=headers,
        )

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["nextLevelSummary"]["fromClassLevel"] == 2
    assert payload["nextLevelSummary"]["toClassLevel"] == 3
    assert isinstance(payload["unlockedFeatures"], list)
    assert any(choice["type"] == "subclass" for choice in payload["requiredChoices"])


def test_character_profile_delete_requires_auth(monkeypatch):
    monkeypatch.setattr(character_routes, "get_request_user", lambda request: None)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        res = client.delete("/api/character/profile/profile-1?session_id=s1", headers=headers)

    assert res.status_code == 401


def test_character_profile_delete_requires_session_id(monkeypatch):
    monkeypatch.setattr(character_routes, "get_request_user", lambda request: {"id": "u1", "username": "Lyra"})

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        res = client.delete("/api/character/profile/profile-1", headers=headers)

    assert res.status_code == 400
    assert "session_id" in res.json()["detail"]


def test_character_profile_delete_returns_404_for_unknown_session(monkeypatch):
    monkeypatch.setattr(character_routes, "get_request_user", lambda request: {"id": "u1", "username": "Lyra"})
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: None)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        res = client.delete("/api/character/profile/profile-1?session_id=missing", headers=headers)

    assert res.status_code == 404


def test_character_profile_delete_returns_404_when_profile_not_found(monkeypatch):
    auth_user = {"id": "u1", "username": "Lyra"}
    session = SimpleNamespace(
        char_profiles={
            "lyra": [{"id": "other-profile", "name": "Other"}]
        }
    )

    async def _fake_save_campaign(_session):
        return None

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: auth_user)
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(character_routes, "save_campaign_async", _fake_save_campaign)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        res = client.delete("/api/character/profile/nonexistent?session_id=s1", headers=headers)

    assert res.status_code == 404


def test_character_profile_delete_removes_profile_and_persists(monkeypatch):
    auth_user = {"id": "u1", "username": "Lyra"}
    session = SimpleNamespace(
        char_profiles={
            "lyra": [
                {"id": "keep-me", "name": "Keep"},
                {"id": "delete-me", "name": "ToDelete"},
            ]
        }
    )
    saved = {"value": False}

    async def _fake_save_campaign(_session):
        saved["value"] = True

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: auth_user)
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(character_routes, "save_campaign_async", _fake_save_campaign)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        res = client.delete("/api/character/profile/delete-me?session_id=s1", headers=headers)

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["profile_id"] == "delete-me"

    remaining = session.char_profiles.get("lyra", [])
    assert len(remaining) == 1
    assert remaining[0]["id"] == "keep-me"
    assert saved["value"] is True


def test_character_profile_delete_survives_reload_library_excludes_deleted(monkeypatch):
    """After delete, a fresh library fetch must not return the deleted profile."""
    auth_user = {"id": "u1", "username": "Lyra"}
    session = SimpleNamespace(
        char_profiles={
            "lyra": [
                {"id": "profile-a", "name": "Aria"},
                {"id": "profile-b", "name": "Beron"},
            ]
        }
    )

    async def _fake_save_campaign(_session):
        return None

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: auth_user)
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(character_routes, "save_campaign_async", _fake_save_campaign)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        del_res = client.delete("/api/character/profile/profile-a?session_id=s1", headers=headers)
        assert del_res.status_code == 200

        # Simulate a full page reload: re-fetch the library
        lib_res = client.get("/api/character/library?session_id=s1")
        assert lib_res.status_code == 200
        profiles = lib_res.json()["profiles"]
        ids = [p["id"] for p in profiles]
        assert "profile-a" not in ids
        assert "profile-b" in ids


def test_character_profile_delete_removes_duplicate_owner_buckets(monkeypatch):
    """Delete should remove profile across owner aliases to avoid stale roster rows."""
    auth_user = {"id": "u1", "username": "Lyra", "character_name": "Lyra Prime"}
    session = SimpleNamespace(
        char_profiles={
            "lyra prime": [
                {"id": "profile-a", "name": "Aria"},
            ],
            "lyra": [
                {"id": "profile-a", "name": "Aria"},
                {"id": "profile-b", "name": "Beron"},
            ],
            "u1": [
                {"id": "profile-a", "name": "Aria"},
            ],
        }
    )

    async def _fake_save_campaign(_session):
        return None

    monkeypatch.setattr(character_routes, "get_request_user", lambda request: auth_user)
    monkeypatch.setattr(character_routes, "get_or_restore_session", lambda session_id: session)
    monkeypatch.setattr(character_routes, "save_campaign_async", _fake_save_campaign)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        headers = _csrf_headers(client)
        del_res = client.delete("/api/character/profile/profile-a?session_id=s1", headers=headers)
        assert del_res.status_code == 200

    assert [row["id"] for row in session.char_profiles["lyra prime"]] == []
    assert [row["id"] for row in session.char_profiles["lyra"]] == ["profile-b"]
    assert [row["id"] for row in session.char_profiles["u1"]] == []
