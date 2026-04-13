import asyncio

from server.handlers import content
from server.session import Session, User


def test_char_profile_upsert_persists_personalization_fields():
    session = Session(id="sess-personal")
    player = User(id="p1", name="Lyra", role="player")
    session.users[player.id] = player

    sent = []

    async def _fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save_campaign_async = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        payload = {
            "id": "profile_lyra",
            "name": "Lyra",
            "color": "#55ffaa",
            "accentColor": "#33ccff",
            "diceTheme": "amethyst",
            "portraitFrame": "rune",
            "tagline": "Starfall answers only to the bold.",
            "charBook": {"name": "Lyra"},
            "charSheet": {"name": "Lyra"},
        }
        asyncio.run(content.handle_char_profile_upsert(payload, session, player))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save_campaign_async

    owner_key = "lyra"
    assert owner_key in session.char_profiles
    saved = session.char_profiles[owner_key][0]
    assert saved["accentColor"] == "#33ccff"
    assert saved["diceTheme"] == "amethyst"
    assert saved["portraitFrame"] == "rune"
    assert saved["tagline"] == "Starfall answers only to the bold."
    assert any(msg[2].get("type") == "char_profiles_sync" for msg in sent)


def test_char_profile_upsert_truncates_personalization_fields():
    session = Session(id="sess-personal-truncate")
    player = User(id="p2", name="Nim", role="player")
    session.users[player.id] = player

    async def _fake_send_to(*_args, **_kwargs):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save_campaign_async = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_char_profile_upsert({
            "id": "profile_nim",
            "name": "Nim",
            "accentColor": "#" + ("1" * 40),
            "diceTheme": "x" * 60,
            "portraitFrame": "y" * 60,
            "tagline": "z" * 300,
        }, session, player))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save_campaign_async

    saved = session.char_profiles["nim"][0]
    assert len(saved["accentColor"]) == 16
    assert len(saved["diceTheme"]) == 24
    assert len(saved["portraitFrame"]) == 24
    assert len(saved["tagline"]) == 120


def test_char_profile_upsert_keeps_species_and_legacy_race_fields():
    session = Session(id="sess-species")
    player = User(id="p3", name="Tamsin", role="player")
    session.users[player.id] = player

    async def _fake_send_to(*_args, **_kwargs):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save_campaign_async = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_char_profile_upsert({
            "id": "profile_species",
            "name": "Tamsin",
            "charBook": {
                "name": "Tamsin",
                "species": "Fairy",
                "importedRace": "Eladrin",
                "race": "Fairy",
            },
            "charSheet": {
                "name": "Tamsin",
                "species": "Fairy",
                "importedRace": "Eladrin",
                "race": "Fairy",
            },
        }, session, player))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save_campaign_async

    saved = session.char_profiles["tamsin"][0]
    assert saved["charBook"]["species"] == "Fairy"
    assert saved["charBook"]["importedRace"] == "Eladrin"
    assert saved["charSheet"]["species"] == "Fairy"
    assert saved["charSheet"]["importedRace"] == "Eladrin"


def test_char_profile_upsert_keeps_class_and_species_identity_fields():
    session = Session(id="sess-class-species")
    player = User(id="p4", name="Iri", role="player")
    session.users[player.id] = player

    async def _fake_send_to(*_args, **_kwargs):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save_campaign_async = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_char_profile_upsert({
            "id": "profile_iri",
            "name": "Iri",
            "charBook": {
                "name": "Iri",
                "className": "Wizard",
                "subclass": "Evocation",
                "species": "Elf",
                "background": "Sage",
            },
            "charSheet": {
                "name": "Iri",
                "classes": [{"name": "Wizard", "level": 5, "subclass": "Evocation"}],
                "species": "Elf",
                "background": "Sage",
            },
        }, session, player))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save_campaign_async

    saved = session.char_profiles["iri"][0]
    assert saved["charBook"]["className"] == "Wizard"
    assert saved["charBook"]["subclass"] == "Evocation"
    assert saved["charBook"]["species"] == "Elf"
    assert saved["charBook"]["background"] == "Sage"
    assert saved["charSheet"]["classes"][0]["name"] == "Wizard"
    assert saved["charSheet"]["species"] == "Elf"


def test_char_profile_upsert_resolves_and_persists_canonical_level():
    session = Session(id="sess-level")
    player = User(id="p5", name="Mira", role="player")
    session.users[player.id] = player

    async def _fake_send_to(*_args, **_kwargs):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save_campaign_async = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_char_profile_upsert({
            "id": "profile_mira",
            "name": "Mira",
            "charBook": {"level": 7},
            "charSheet": {
                "classes": [{"name": "Rogue", "level": 3}, {"name": "Wizard", "level": 4}],
            },
        }, session, player))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save_campaign_async

    saved = session.char_profiles["mira"][0]
    assert saved["level"] == 7
    assert saved["charSheet"]["level"] == 7
    assert saved["charSheet"]["totalLevel"] == 7


def test_char_profile_level_change_keeps_class_and_species_data_stable():
    session = Session(id="sess-level-stable")
    player = User(id="p6", name="Ari", role="player")
    session.users[player.id] = player

    async def _fake_send_to(*_args, **_kwargs):
        return None

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save_campaign_async = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        base = {
            "id": "profile_ari",
            "name": "Ari",
            "charBook": {"className": "Druid", "species": "Elf", "level": 4},
            "charSheet": {"classes": [{"name": "Druid", "level": 4}], "species": "Elf"},
            "level": 4,
        }
        asyncio.run(content.handle_char_profile_upsert(base, session, player))
        leveled = {
            **base,
            "charBook": {**base["charBook"], "level": 5},
            "charSheet": {"classes": [{"name": "Druid", "level": 5}], "species": "Elf"},
            "level": 5,
        }
        asyncio.run(content.handle_char_profile_upsert(leveled, session, player))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save_campaign_async

    saved = session.char_profiles["ari"][0]
    assert saved["level"] == 5
    assert saved["charBook"]["className"] == "Druid"
    assert saved["charBook"]["species"] == "Elf"
    assert saved["charSheet"]["classes"][0]["name"] == "Druid"
    assert saved["charSheet"]["species"] == "Elf"
