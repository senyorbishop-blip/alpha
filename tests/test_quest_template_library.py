import asyncio
from pathlib import Path

from server.handlers import content
from server.quest_library import (
    build_session_quest_from_template,
    get_quest_template,
    load_builtin_quest_templates,
)
from server.session import Session, User


def test_builtin_quest_template_library_loads_with_variety():
    templates = load_builtin_quest_templates()
    assert len(templates) >= 12
    categories = {str(entry.get("category") or "") for entry in templates}
    assert "bounty_hunt" in categories
    assert "missing_person" in categories
    assert "escort" in categories
    assert "tavern_rumour_lead" in categories


def test_quest_template_library_missing_or_invalid_file_fails_gracefully(tmp_path: Path):
    missing = tmp_path / "does-not-exist.json"
    assert load_builtin_quest_templates(missing) == []

    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")
    assert load_builtin_quest_templates(bad) == []


def test_build_session_quest_from_template_creates_editable_session_record():
    template = get_quest_template("bounty-goblin-captain")
    assert template is not None
    quest = build_session_quest_from_template(template, imported_by="dm-user")
    assert quest["id"].startswith("sq-")
    assert quest["template_id"] == "bounty-goblin-captain"
    assert quest["status"] == "available"
    assert isinstance(quest["objective_list"], list)
    assert quest["source_type"] == "template_import"


def test_ws_import_adds_session_quest_and_broadcasts_role_safe_sync():
    session = Session(id="quest-import")
    dm = User(id="dm1", name="DM", role="dm")
    player = User(id="p1", name="Player", role="player")
    session.users = {dm.id: dm, player.id: player}

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
        asyncio.run(content.handle_quest_template_import({"template_id": "bounty-goblin-captain"}, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    assert len(session.session_quests) == 1
    imported = session.session_quests[0]
    assert imported["template_id"] == "bounty-goblin-captain"
    assert imported["id"].startswith("sq-")
    assert any(msg[2].get("type") == "session_quests_sync" for msg in sent)
    assert any(msg[2].get("type") == "quest_template_import_result" and msg[2].get("payload", {}).get("ok") for msg in sent)


def test_ws_import_unknown_template_returns_error_without_mutation():
    session = Session(id="quest-import-fail")
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
        asyncio.run(content.handle_quest_template_import({"template_id": "unknown-template"}, session, dm))
    finally:
        content.manager.send_to = original_send_to
        content.save_campaign_async = original_save

    assert session.session_quests == []
    failures = [msg for _, _, msg in sent if msg.get("type") == "quest_template_import_result"]
    assert failures
    assert failures[0]["payload"]["ok"] is False
