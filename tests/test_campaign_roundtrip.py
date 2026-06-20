import sqlite3
import tempfile
import time
from pathlib import Path

from tests.test_persistence_schema import _build_session, _cleanup_modules, _reload_db_modules



def test_campaign_roundtrip_preserves_inventory_combat_editor_and_viewer_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            from server.restore import restore_session_from_db

            session = _build_session()
            session.combat = {
                "active": True,
                "turn": 1,
                "combatants": [{"id": "c1", "token_id": "tok1", "name": "Hero", "initiative": 15}],
                "round": 3,
                "movement": {"token_id": "tok1", "used": 10},
                "selected_target_id": "tok2",
                "pending_attack": {"attacker_id": "tok1", "target_id": "tok2"},
            }
            session.player_inventories = {"p1": [{"item_id": "rope", "name": "Rope", "qty": 1}]}
            session.player_gold = {"p1": {"gp": 15}}
            session.party_loot_log = [{"id": "loot1", "item": "Gemstone"}]
            session.viewer_profiles = {"user:v1": {"label": "Viewer 1"}}
            session.viewer_pending_actions = {"pending1": {"viewer_key": "user:v1", "kind": "heal"}}
            session.viewer_power_catalog = {"heal": {"name": "Heal"}}
            session.handouts = [{"id": "h1", "title": "Clue", "recipients": "all"}]
            session.discovery_cards = [{"id": "d1", "title": "Footprints", "visibility": "private_player", "target_user_id": "p1", "acknowledged_by": []}]
            session.private_story_hooks = [{"id": "hook1", "title": "Family Crest", "body": "You recognize this crest.", "kind": "prompt", "status": "active", "target_user_id": "p1", "persistent": False}]
            session.quest_templates = [{"id": "qt1", "title": "Lost Relic", "source_type": "premade", "status": "template"}]
            session.session_quests = [{
                "id": "sq1",
                "template_id": "qt1",
                "title": "Lost Relic",
                "status": "active",
                "source_type": "custom",
                "required_guild_rank_id": "trusted",
                "required_guild_rank_points": 3,
                "lock_visibility": "listed",
            }]
            session.quest_board_bindings = [{"id": "qb1", "board_id": "board-town", "quest_ids": ["sq1"], "status": "active"}]
            session.editor_layers = {"world": {"1,1": "stone"}}
            session.editor_walls = {"world": [{"id": "w1", "x1": 0, "y1": 0, "x2": 50, "y2": 0}]}
            session.editor_props = {"world": [{"id": "p1", "kind": "chest", "x": 10, "y": 20, "interactable": {"enabled": True, "actions": [{"id": "inspect", "label": "Inspect"}], "kind": "loot"}}]}
            session.editor_paths = {"world": [{"id": "path1", "points": [{"x": 0, "y": 0}, {"x": 10, "y": 10}]}]}
            session.editor_labels = {"world": [{"id": "label1", "text": "Entrance", "x": 5, "y": 5}]}
            session.editor_markers = {"world": [{"id": "marker1", "label": "X", "x": 7, "y": 8}]}
            session.editor_lights = {"world": [{"id": "light1", "x": 4, "y": 6, "radius": 25}]}
            session.map_settings = {"world": {"editor_mode": "world", "weather": {"enabled": True, "intensity": 0.8}}}
            from server.session import POI
            session.pois = {
                "poi-1": POI(id="poi-1", x=5, y=5, name="Shrine", interactable={"enabled": True, "kind": "poi", "actions": ["inspect", "ask_party"]})
            }
            session.sound_state = {"track": "tavern", "volume": 0.4, "fade_ms": 500}
            session.weather_state = {"weather_type": "fog", "intensity": 0.7, "wind_angle": 45, "wind_speed": 0.2, "map_context": "world"}

            assert db_mod.save_campaign(session) is True
            loaded = db_mod.load_campaign(session.id)
            assert loaded is not None
            restored, _ = restore_session_from_db(loaded)

            assert restored.combat["active"] is True
            assert restored.combat["round"] == 3
            assert restored.player_inventories["p1"][0]["name"] == "Rope"
            assert restored.player_gold["p1"]["gp"] == 15
            assert restored.party_loot_log[0]["item"] == "Gemstone"
            assert restored.viewer_profiles["user:v1"]["label"] == "Viewer 1"
            assert restored.viewer_pending_actions["pending1"]["kind"] == "heal"
            assert restored.viewer_power_catalog["heal"]["name"] == "Heal"
            assert restored.handouts[0]["title"] == "Clue"
            assert restored.discovery_cards[0]["title"] == "Footprints"
            assert restored.private_story_hooks[0]["title"] == "Family Crest"
            assert restored.quest_templates[0]["id"] == "qt1"
            assert restored.session_quests[0]["template_id"] == "qt1"
            assert restored.session_quests[0]["required_guild_rank_id"] == "trusted"
            assert restored.session_quests[0]["required_guild_rank_points"] == 3
            assert restored.quest_board_bindings[0]["quest_ids"] == ["sq1"]
            assert restored.editor_layers["world"] == {"1,1": "stone"}
            assert restored.editor_props["world"][0]["kind"] == "chest"
            assert restored.editor_props["world"][0]["interactable"]["kind"] == "loot"
            assert restored.pois["poi-1"].interactable["actions"][1]["id"] == "ask_party"
            assert restored.map_documents["world"]["layers"]["lights"][0]["id"] == "light1"
            assert restored.sound_state["track"] == "tavern"
            assert restored.weather_state["weather_type"] == "fog"
        finally:
            _cleanup_modules(paths_mod, db_mod)



def test_restore_legacy_campaign_without_map_documents_rebuilds_validated_docs():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            from server.restore import restore_session_from_db

            session = _build_session()
            session.editor_layers = {"crypt": {"2,2": "moss"}}
            session.editor_walls = {"crypt": [{"id": "w1", "x1": 1, "y1": 2, "x2": 3, "y2": 4}]}
            session.editor_props = {"crypt": [{"id": "p1", "kind": "door", "x": 9, "y": 8}]}
            session.map_settings = {"crypt": {"editor_mode": "tactical"}}
            assert db_mod.save_campaign(session) is True

            db_path = Path(tmpdir) / "test_campaigns.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute("UPDATE campaigns SET map_documents=? WHERE id=?", ('{}', session.id))

            loaded = db_mod.load_campaign(session.id)
            restored, _ = restore_session_from_db(loaded)

            assert restored.editor_layers["crypt"] == {"2,2": "moss"}
            assert restored.map_documents["crypt"]["layers"]["terrain"]["cells"] == {"2,2": "moss"}
            assert restored.map_documents["crypt"]["layers"]["walls"][0]["id"] == "w1"
            assert restored.map_documents["crypt"]["layers"]["props"][0]["kind"] == "door"
        finally:
            _cleanup_modules(paths_mod, db_mod)



def test_restore_prefers_legacy_editor_state_when_map_documents_field_is_corrupt():
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            from server.restore import restore_session_from_db

            session = _build_session()
            session.editor_layers = {"world": {"9,9": "lava"}}
            session.editor_labels = {"world": [{"id": "label1", "text": "Boss", "x": 11, "y": 12}]}
            assert db_mod.save_campaign(session) is True

            db_path = Path(tmpdir) / "test_campaigns.db"
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "UPDATE campaigns SET map_documents=?, editor_layers=?, editor_labels=? WHERE id=?",
                    ('{"broken"', '{"world":{"9,9":"lava"}}', '{"world":[{"id":"label1","text":"Boss","x":11,"y":12}]}', session.id),
                )

            loaded = db_mod.load_campaign(session.id)
            restored, _ = restore_session_from_db(loaded)

            assert loaded["map_documents"] == {}
            assert restored.editor_layers["world"] == {"9,9": "lava"}
            assert restored.editor_labels["world"][0]["text"] == "Boss"
            assert restored.map_documents["world"]["layers"]["terrain"]["cells"] == {"9,9": "lava"}
        finally:
            _cleanup_modules(paths_mod, db_mod)


def test_campaign_roundtrip_preserves_dm_player_key():
    """A returning DM must keep its auth linkage (player_key) across save/restore.

    Without persisting the DM's player_key, authority resolution after a server
    restart treats the authenticated DM as a stranger/viewer, which denies the
    websocket handshake and leaves the play page stuck on "Connecting…".
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        paths_mod, db_mod = _reload_db_modules(tmpdir)
        try:
            from server.restore import restore_session_from_db

            session = _build_session()
            session.users["dm1"].player_key = "auth_deadbeefcafe"

            assert db_mod.save_campaign(session) is True
            loaded = db_mod.load_campaign(session.id)
            assert loaded is not None
            assert loaded.get("dm_player_key") == "auth_deadbeefcafe"

            restored, _ = restore_session_from_db(loaded)
            assert restored.dm_id == "dm1"
            assert restored.users["dm1"].player_key == "auth_deadbeefcafe"
        finally:
            _cleanup_modules(paths_mod, db_mod)
