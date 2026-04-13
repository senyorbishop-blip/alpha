import asyncio
from pathlib import Path

from server.handlers import content
from server.prep_pack_library import get_prep_pack, load_builtin_prep_packs
from server.session import Session, User


def test_builtin_prep_pack_library_loads_catalog_with_content():
    packs = load_builtin_prep_packs()
    assert len(packs) >= 2
    assert any(str(p.get("category") or "") == "starter_region" for p in packs)
    assert any(len(p.get("quests") or []) > 0 for p in packs)


def test_prep_pack_library_missing_or_invalid_file_fails_gracefully(tmp_path: Path):
    missing = tmp_path / "does-not-exist.json"
    assert load_builtin_prep_packs(missing) == []

    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")
    assert load_builtin_prep_packs(bad) == []


def test_prep_pack_import_adds_editable_session_content_and_broadcasts():
    session = Session(id="prep-pack-import")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="p1", name="Player", role="player")
    session.users = {dm.id: dm, player.id: player}

    sent = []
    broadcast = []

    async def _fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _fake_broadcast(session_id, message, exclude_user=None):
        broadcast.append((session_id, message, exclude_user))

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_broadcast = content.manager.broadcast
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.manager.broadcast = _fake_broadcast
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_prep_pack_import({"pack_id": "starter-town-brightwater"}, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.manager.broadcast = original_broadcast
        content.save_campaign_async = original_save

    assert session.session_quests, "prep pack should seed at least one quest"
    assert session.handouts, "prep pack should seed at least one handout"
    assert session.encounter_templates, "prep pack should seed at least one encounter template"
    assert session.pois, "prep pack should seed at least one POI"
    assert session.session_quests[0]["source_type"] == "prep_pack_import"
    assert any(msg[2].get("type") == "prep_pack_import_result" and msg[2].get("payload", {}).get("ok") for msg in sent)
    assert any(msg[1].get("type") == "poi_created" for msg in broadcast)


def test_prep_pack_import_unknown_pack_returns_error_without_mutation():
    session = Session(id="prep-pack-import-fail")
    dm = User(id="dm1", name="DM", role="dm")
    session.users = {dm.id: dm}

    sent = []

    async def _fake_send_to(session_id, user_id, message):
        sent.append((session_id, user_id, message))

    async def _fake_save_campaign_async(_session):
        return True

    original_send_to = content.manager.send_to
    original_save = content.save_campaign_async
    content.manager.send_to = _fake_send_to
    content.save_campaign_async = _fake_save_campaign_async
    try:
        asyncio.run(content.handle_prep_pack_import({"pack_id": "missing-pack"}, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    assert session.session_quests == []
    assert session.handouts == []
    assert session.encounter_templates == []
    assert session.pois == {}
    failures = [msg for _, _, msg in sent if msg.get("type") == "prep_pack_import_result"]
    assert failures
    assert failures[0]["payload"]["ok"] is False


def test_get_prep_pack_returns_deepcopy():
    pack = get_prep_pack("starter-town-brightwater")
    assert pack is not None
    pack["name"] = "Mutated"
    pack_again = get_prep_pack("starter-town-brightwater")
    assert pack_again is not None
    assert pack_again["name"] != "Mutated"
