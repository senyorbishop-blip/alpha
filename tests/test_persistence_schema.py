import importlib
import io
import os
import sqlite3
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path


def _reload_db_modules(tmpdir: str):
    os.environ["DND_DATA_DIR"] = tmpdir
    os.environ["DND_DB_PATH"] = str(Path(tmpdir) / "test_campaigns.db")

    import server.paths as paths_mod
    import server.db as db_mod

    importlib.reload(paths_mod)
    importlib.reload(db_mod)
    db_mod.init_db()
    return paths_mod, db_mod



def _cleanup_modules(paths_mod, db_mod):
    del os.environ["DND_DATA_DIR"]
    del os.environ["DND_DB_PATH"]
    importlib.reload(paths_mod)
    importlib.reload(db_mod)



def _build_session():
    from server.session import Session, User

    session = Session(id="persist-test", player_invite="PLAY01", viewer_invite="VIEW01", created_at=time.time())
    session.name = "Persistence Test"
    session.dm_map_context = "world"
    session.dm_current_map_url = None
    session.dm_nav_intent = 0
    session.users = {"dm1": User(id="dm1", name="DM", role="dm")}
    session.dm_id = "dm1"
    session.pois = {}
    session.log = []
    return session



def test_save_campaign_normalizes_persisted_state_before_write():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            session = _build_session()
            session.combat = {"active": 1, "turn": "3", "combatants": "bad-data"}
            session.map_settings = {"world": {"editor_mode": "INVALID", "weather": {"intensity": 9}}}
            session.player_inventories = []
            session.viewer_power_catalog = []
            session.handouts = {"oops": True}
            session.discovery_cards = {"oops": True}
            session.private_story_hooks = {"oops": True}
            session.encounter_templates = {"oops": True}

            assert db_mod.save_campaign(session) is True

            loaded = db_mod.load_campaign(session.id)
            assert loaded is not None
            assert loaded["combat"]["combatants"] == []
            assert loaded["combat"]["turn"] == 3
            assert loaded["player_inventories"] == {}
            assert loaded["viewer_power_catalog"] == {}
            assert loaded["handouts"] == []
            assert loaded["discovery_cards"] == []
            assert loaded["private_story_hooks"] == []
            assert loaded["encounter_templates"] == []
            assert loaded["map_settings"]["world"]["editor_mode"] == "tactical"
            assert session.map_documents["world"]["settings"]["weather"]["intensity"] == 1.0
        finally:
            _cleanup_modules(paths_mod, db_mod)



def test_load_campaign_normalizes_invalid_json_field_shapes():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            session = _build_session()
            assert db_mod.save_campaign(session) is True

            db_path = Path(os.environ["DND_DB_PATH"])
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    UPDATE campaigns
                    SET combat=?, player_inventories=?, handouts=?, map_settings=?, map_documents=?
                    , discovery_cards=?, private_story_hooks=?
                    WHERE id=?
                    """,
                    (
                        '[]',
                        '[]',
                        '{"broken":true}',
                        '[]',
                        '[]',
                        '{"broken":true}',
                        '{"broken":true}',
                        session.id,
                    ),
                )

            loaded = db_mod.load_campaign(session.id)
            assert loaded is not None
            assert loaded["combat"]["combatants"] == []
            assert loaded["combat"]["active"] is False
            assert loaded["player_inventories"] == {}
            assert loaded["handouts"] == []
            assert loaded["discovery_cards"] == []
            assert loaded["private_story_hooks"] == []
            assert loaded["map_settings"] == {}
            assert loaded["map_documents"] == {}
        finally:
            _cleanup_modules(paths_mod, db_mod)


def test_load_campaign_quarantines_single_bad_json_field_and_logs_it():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            session = _build_session()
            session.handouts = [{"id": "h1", "title": "Note"}]
            session.player_gold = {"p1": {"gp": 12}}
            assert db_mod.save_campaign(session) is True

            db_path = Path(os.environ["DND_DB_PATH"])
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    UPDATE campaigns
                    SET handouts=?, player_gold=?
                    WHERE id=?
                    """,
                    (
                        '{"broken"',
                        '{"p1":{"gp":12}}',
                        session.id,
                    ),
                )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                loaded = db_mod.load_campaign(session.id)

            assert loaded is not None
            assert loaded["handouts"] == []
            assert loaded["player_gold"] == {"p1": {"gp": 12}}
            output = stdout.getvalue()
            assert "field=handouts" in output
            assert "reason=invalid_json" in output
        finally:
            _cleanup_modules(paths_mod, db_mod)


def test_save_campaign_logs_large_field_warning_once():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            session = _build_session()
            session.handouts = [{"id": "h1", "body": "x" * 600000}]

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                assert db_mod.save_campaign(session) is True
                assert db_mod.save_campaign(session) is True

            output = stdout.getvalue()
            assert output.count("field=handouts") == 1
            assert "reason=large_field" in output
        finally:
            _cleanup_modules(paths_mod, db_mod)


def test_save_and_restore_persist_sound_weather_and_viewer_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            session = _build_session()
            session.sound_state = {"track": "battle", "volume": 2, "fade_ms": 9000, "pre_combat_track": "tavern"}
            session.weather_state = {"weather_type": "rain", "intensity": 3, "wind_angle": 999, "wind_speed": -1, "map_context": "crypt"}
            session.viewer_pending_actions = {"pending1": {"viewer_key": "user:v1", "kind": "heal"}}
            session.active_poll = {
                "id": "poll1",
                "title": "Treasure Vote",
                "question": "Open the chest?",
                "options": ["Yes", "No"],
                "votes": {"u1": 0, "u2": "1", "u3": 99},
                "created_at": 10,
                "closes_at": 30,
                "closed": False,
                "results_mode": "final",
                "authority_note": "The DM keeps final say.",
                "closed_reason": "active",
            }
            session.show_viewer_presence = True

            assert db_mod.save_campaign(session) is True

            loaded = db_mod.load_campaign(session.id)
            assert loaded is not None
            assert loaded["sound_state"] == {
                "track": "battle",
                "volume": 1.0,
                "fade_ms": 5000,
                "pre_combat_track": "tavern",
            }
            assert loaded["weather_state"] == {
                "weather_type": "rain",
                "intensity": 1.0,
                "wind_angle": 360.0,
                "wind_speed": 0.0,
                "map_context": "crypt",
            }
            assert loaded["viewer_pending_actions"] == {"pending1": {"viewer_key": "user:v1", "kind": "heal"}}
            assert loaded["active_poll"]["title"] == "Treasure Vote"
            assert loaded["active_poll"]["votes"] == {"u1": 0, "u2": 1}
            assert loaded["active_poll"]["results_mode"] == "final"
            assert loaded["show_viewer_presence"] is True

            from server.restore import restore_session_from_db

            restored, _ = restore_session_from_db(loaded)
            assert restored.sound_state["track"] == "battle"
            assert restored.weather_state["weather_type"] == "rain"
            assert restored.viewer_pending_actions["pending1"]["viewer_key"] == "user:v1"
            assert restored.active_poll["id"] == "poll1"
            assert restored.active_poll["title"] == "Treasure Vote"
            assert restored.active_poll["results_mode"] == "final"
            assert restored.show_viewer_presence is True
        finally:
            _cleanup_modules(paths_mod, db_mod)


def test_save_and_restore_persist_world_state_foundation():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            session = _build_session()
            session.world_state = {
                "world_state_flags": {"bridge_repaired": True},
                "discovered_pois": {"poi-bridge": {"discovered_at": 123.0, "discoverer": "u1"}},
                "cleared_or_completed_locations": {"camp-wolves": {"status": "cleared"}},
                "unlocked_services": {"town-oakhaven": ["blacksmith", "temple"]},
                "region_state": {"ashen-marches": {"danger": "high"}},
                "town_state": {"oakhaven": {"prosperity": "recovering"}},
                "faction_world_flags": {"iron-lanterns": {"favor": 2}},
                "faction_reputation": {
                    "iron-lanterns": {"id": "iron-lanterns", "name": "Iron Lanterns", "reputation": 7, "visibility": "party"}
                },
                "world_event_flags": {"blood_moon": False},
                "world_change_history": [
                    {
                        "id": "wch-1",
                        "ts": 42,
                        "kind": "encounter_cleared",
                        "scope": "poi",
                        "ref_id": "camp-wolves",
                        "summary": "The wolf camp was cleared.",
                        "meta": {"party": ["u1"]},
                    }
                ],
            }

            assert db_mod.save_campaign(session) is True
            loaded = db_mod.load_campaign(session.id)
            assert loaded is not None
            assert loaded["world_state"]["world_state_flags"]["bridge_repaired"] is True
            assert loaded["world_state"]["discovered_pois"]["poi-bridge"]["discoverer"] == "u1"
            assert loaded["world_state"]["faction_reputation"]["iron-lanterns"]["reputation"] == 7
            assert loaded["world_state"]["world_change_history"][0]["kind"] == "encounter_cleared"

            from server.restore import restore_session_from_db

            restored, _ = restore_session_from_db(loaded)
            assert restored.world_state["town_state"]["oakhaven"]["prosperity"] == "recovering"
            assert restored.world_state["faction_reputation"]["iron-lanterns"]["name"] == "Iron Lanterns"
            assert restored.world_state["world_change_history"][0]["ref_id"] == "camp-wolves"
        finally:
            _cleanup_modules(paths_mod, db_mod)


def test_save_and_restore_persist_quest_foundation_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            session = _build_session()
            session.quest_templates = [{
                "id": "qt-alpha",
                "title": "Bandit Menace",
                "summary": "Reports of raids near the old bridge.",
                "description": "Track and stop the raiding party threatening trade routes.",
                "category": "bounty",
                "difficulty": "medium",
                "tier": "tier-1",
                "status": "template",
                "source_type": "premade",
                "faction_tags": ["guild-iron-lantern"],
                "linked_poi_ids": ["poi-bridge"],
                "objective_list": [{"id": "obj-1", "title": "Investigate", "status": "pending"}],
                "reward_bundle": {"xp": 300, "gold": 150, "items": [{"item_id": "potion_healing", "qty": 2}]},
                "stage_list": [{"id": "stage-1", "name": "Hunt", "status": "active", "objective_ids": ["obj-1"]}],
                "current_stage_id": "stage-1",
                "meta": {"template_pack": "starter"},
            }]
            session.session_quests = [{
                "id": "sq-alpha",
                "template_id": "qt-alpha",
                "title": "Bandit Menace (Active)",
                "source_type": "custom",
                "status": "active",
                "progress": {"objective_status": {"obj-1": "complete"}},
                "campaign_id": session.id,
                "session_id": session.id,
            }]
            session.quest_board_bindings = [{
                "id": "qb-1",
                "board_type": "guild_board",
                "board_id": "board-town-square",
                "poi_id": "poi-bridge",
                "quest_ids": ["sq-alpha"],
                "status": "active",
            }]

            assert db_mod.save_campaign(session) is True
            loaded = db_mod.load_campaign(session.id)
            assert loaded is not None

            assert loaded["quest_templates"][0]["id"] == "qt-alpha"
            assert loaded["quest_templates"][0]["objective_list"][0]["id"] == "obj-1"
            assert loaded["session_quests"][0]["template_id"] == "qt-alpha"
            assert loaded["quest_board_bindings"][0]["quest_ids"] == ["sq-alpha"]

            from server.restore import restore_session_from_db

            restored, _ = restore_session_from_db(loaded)
            assert restored.quest_templates[0]["title"] == "Bandit Menace"
            assert restored.session_quests[0]["progress"]["objective_status"]["obj-1"] == "complete"
            assert restored.quest_board_bindings[0]["board_id"] == "board-town-square"
        finally:
            _cleanup_modules(paths_mod, db_mod)


def test_restore_session_from_db_normalizes_legacy_payload_defaults():
    from server.restore import restore_session_from_db

    restored, _ = restore_session_from_db(
        {
            "id": "restore-test",
            "name": "Restore Test",
            "dm_name": "DM",
            "player_invite": "PLAY02",
            "viewer_invite": "VIEW02",
            "created_at": time.time(),
            "fog_maps": {"world": {"enabled": 1, "cols": "8", "rows": "8", "cells": [1, 0, 1]}},
            "combat": [],
            "journal_entries": {},
            "library_entries": {},
            "item_library_entries": {},
            "char_profiles": [],
            "player_inventories": [],
            "player_gold": [],
            "party_loot_log": {},
            "viewer_profiles": [],
            "viewer_power_catalog": [],
            "hazard_zones": [],
            "handouts": {},
            "encounter_templates": {},
            "map_documents": {},
            "editor_layers": [],
            "editor_walls": [],
            "editor_props": [],
            "map_settings": {"world": {"editor_mode": "nope"}},
            "editor_paths": [],
            "editor_labels": [],
            "editor_markers": [],
            "editor_lights": [],
            "players": [],
            "pois": [],
            "tokens": [],
            "logs": [],
        }
    )

    assert restored.combat["combatants"] == []
    assert restored.journal_entries == []
    assert restored.player_inventories == {}
    assert restored.handouts == []
    assert restored.encounter_templates == []
    assert restored.quest_templates == []
    assert restored.session_quests == []
    assert restored.quest_board_bindings == []
    assert restored.editor_layers == {}
    assert restored.map_settings["world"]["editor_mode"] == "tactical"
    assert restored.fog_maps["world"]["cells"] == "101"
    assert restored.world_state == {
        "world_state_flags": {},
        "discovered_pois": {},
        "cleared_or_completed_locations": {},
        "unlocked_services": {},
        "region_state": {},
        "town_state": {},
        "faction_world_flags": {},
        "faction_reputation": {},
        "world_event_flags": {},
        "world_change_history": [],
        "recent_events": [],
        "unlocked_handout_ids": [],
        "discovery_ids": [],
        "event_messages": [],
        "quest_refresh_ids": [],
        "scene_trigger_zones": {},
        "scene_trigger_runtime": {"consumed_zone_ids": [], "last_trigger_at": {}},
    }



def test_save_campaign_roundtrips_poi_player_visibility_flag():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            from server.session import POI

            session = _build_session()
            session.pois = {
                "poi-hidden": POI(id="poi-hidden", x=10, y=20, name="Secret Shrine", revealed_to_players=False),
                "poi-visible": POI(id="poi-visible", x=30, y=40, name="Town Gate", revealed_to_players=True),
            }

            assert db_mod.save_campaign(session) is True

            loaded = db_mod.load_campaign(session.id)
            assert loaded is not None
            by_id = {poi["id"]: poi for poi in loaded["pois"]}
            assert by_id["poi-hidden"]["revealed_to_players"] == 0
            assert by_id["poi-visible"]["revealed_to_players"] == 1

            from server.restore import restore_session_from_db

            restored, _ = restore_session_from_db(loaded)
            assert restored.pois["poi-hidden"].revealed_to_players is False
            assert restored.pois["poi-visible"].revealed_to_players is True
        finally:
            _cleanup_modules(paths_mod, db_mod)

def test_load_campaign_invalid_poi_interactable_json_falls_back_to_empty_dict():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            from server.session import POI

            session = _build_session()
            session.pois = {
                "poi-1": POI(id="poi-1", x=1, y=2, name="Shrine")
            }
            assert db_mod.save_campaign(session) is True

            db_path = Path(os.environ["DND_DB_PATH"])
            with sqlite3.connect(db_path) as conn:
                conn.execute("UPDATE pois SET interactable=? WHERE id=?", ('{\"broken\"', "poi-1"))

            loaded = db_mod.load_campaign(session.id)
            assert loaded is not None
            assert loaded["pois"][0]["interactable"] == {}
        finally:
            _cleanup_modules(paths_mod, db_mod)
