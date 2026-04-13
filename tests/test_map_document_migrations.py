import time



def test_migrate_map_document_normalizes_nested_layers_and_meta():
    from server.map_migrations import migrate_map_document

    doc = migrate_map_document(
        {
            "map_context": "dungeon-a",
            "map_type": "INVALID",
            "grid": {"tile_size_px": "70", "feet_per_tile": "10", "snap": "false"},
            "assets": {
                "background_url": 123,
                "background_layers": [
                    {"id": "bg1", "url": "/maps/one.webp", "opacity": 3, "visible": "0"},
                    "bad",
                ],
            },
            "settings": {"editor_mode": "bad", "weather": {"intensity": 9}},
            "meta": {"name": "Dungeon A", "updated_at": "1700"},
            "layers": {
                "terrain": {"cells": {"1,2": "grass", "3,4": 2, "": "drop"}},
                "walls": [{"id": "w1", "x1": "1", "y1": 2, "x2": 3, "y2": 4, "door": "yes"}, None],
                "props": [{
                    "id": "p1",
                    "x": "10",
                    "y": "20",
                    "width": "30",
                    "height": 40,
                    "kind": "chest",
                    "interactable": {"enabled": True, "actions": ["inspect"]},
                }],
                "paths": [{"id": "path1", "points": [{"x": "1", "y": 2}, "bad"]}],
                "labels": [{"id": "l1", "text": "Trap", "x": 1, "y": 2, "font_size": "18"}],
                "markers": [{"id": "m1", "label": "Start", "x": 5, "y": 6}],
                "lights": [{"id": "light1", "x": 7, "y": 8, "radius": "120", "intensity": 4}],
                "hazards": [{"id": "hz1", "name": "Pit", "shape": "circle", "radius": "15"}],
            },
        },
        map_context="world",
    )

    assert doc["map_context"] == "dungeon-a"
    assert doc["map_type"] == "tactical"
    assert doc["grid"] == {"tile_size_px": 70, "feet_per_tile": 10, "snap": False}
    assert doc["assets"]["background_url"] == "123"
    assert len(doc["assets"]["background_layers"]) == 1
    assert doc["assets"]["background_layers"][0]["opacity"] == 1.0
    assert doc["settings"]["weather"]["intensity"] == 1.0
    assert doc["meta"]["name"] == "Dungeon A"
    assert isinstance(doc["meta"]["updated_at"], float)
    assert doc["layers"]["terrain"]["cells"] == {"1,2": "grass", "3,4": "2"}
    assert doc["layers"]["walls"][0]["door"] is True
    assert doc["layers"]["props"][0]["width"] == 30.0
    assert doc["layers"]["props"][0]["interactable"]["enabled"] is True
    assert doc["layers"]["props"][0]["interactable"]["actions"][0]["id"] == "inspect"
    assert doc["layers"]["paths"][0]["points"] == [{"x": 1.0, "y": 2.0}]
    assert doc["layers"]["labels"][0]["font_size"] == 18
    assert doc["layers"]["lights"][0]["intensity"] == 1.0
    assert doc["layers"]["hazards"][0]["map_context"] == "dungeon-a"



def test_hydrate_session_from_map_documents_rebuilds_legacy_state_from_validated_docs():
    from server.map_document import hydrate_session_from_map_documents
    from server.session import Session

    session = Session(id="map-doc-test", created_at=time.time())
    docs = {
        "crypt": {
            "map_context": "crypt",
            "settings": {"editor_mode": "world"},
            "layers": {
                "terrain": {"cells": {"1,1": "stone"}},
                "walls": [{"id": "w1", "x1": 0, "y1": 0, "x2": 10, "y2": 0}],
                "props": [{"id": "p1", "kind": "chest", "x": 4, "y": 5, "interactable": {"enabled": True, "actions": ["inspect"]}}],
                "paths": [{"id": "path1", "points": [{"x": 1, "y": 1}]}],
                "labels": [{"id": "label1", "text": "North", "x": 2, "y": 3}],
                "markers": [{"id": "marker1", "label": "Entry", "x": 6, "y": 7}],
                "lights": [{"id": "light1", "x": 8, "y": 9, "radius": 20}],
                "hazards": [{"id": "haz1", "name": "Gas", "x": 1, "y": 2, "width": 3, "height": 4}],
            },
        }
    }

    hydrated = hydrate_session_from_map_documents(session, docs)

    assert "crypt" in hydrated
    assert session.editor_layers["crypt"] == {"1,1": "stone"}
    assert session.editor_walls["crypt"][0]["id"] == "w1"
    assert session.editor_props["crypt"][0]["kind"] == "chest"
    assert session.editor_props["crypt"][0]["interactable"]["actions"][0]["id"] == "inspect"
    assert session.map_settings["crypt"]["editor_mode"] == "world"
    assert session.editor_paths["crypt"][0]["id"] == "path1"
    assert session.editor_labels["crypt"][0]["text"] == "North"
    assert session.editor_markers["crypt"][0]["label"] == "Entry"
    assert session.editor_lights["crypt"][0]["radius"] == 20.0
    assert session.hazard_zones["haz1"]["map_context"] == "crypt"


def test_migrate_map_document_preserves_interactable_prop_metadata():
    from server.map_migrations import migrate_map_document

    doc = migrate_map_document(
        {
            "map_context": "world",
            "layers": {
                "props": [{
                    "id": "p-int",
                    "kind": "statue",
                    "x": 10,
                    "y": 20,
                    "interactable": {
                        "enabled": True,
                        "kind": "world_object",
                        "prompt": "The statue's eyes seem to follow you.",
                        "actions": [
                            {"id": "inspect", "label": "Inspect"},
                            {"id": "attempt_skill_action", "label": "Religion", "skill": "religion"},
                        ],
                        "permissions": {"allow_players": True, "allow_viewers": False},
                        "visibility": {"mode": "public", "discovery_visibility": "private_player"},
                        "discovery_hook": "statue-clue",
                    },
                }]
            },
        }
    )

    interactable = doc["layers"]["props"][0]["interactable"]
    assert interactable["enabled"] is True
    assert interactable["kind"] == "world_object"
    assert interactable["actions"][1]["id"] == "attempt_skill_action"
    assert interactable["actions"][1]["skill"] == "religion"
    assert interactable["permissions"]["allow_players"] is True
    assert interactable["visibility"]["discovery_visibility"] == "private_player"
    assert interactable["discovery_hook"] == "statue-clue"



def test_build_map_documents_from_session_preserves_existing_background_layers():
    from server.map_document import build_map_documents_from_session
    from server.session import Session

    session = Session(id="build-map-docs", created_at=time.time())
    session.map_settings = {"world": {"editor_mode": "world"}}
    session.map_documents = {
        "world": {
            "map_context": "world",
            "assets": {
                "background_layers": [{"id": "bg1", "url": "/maps/world.webp", "opacity": 0.5, "visible": True}]
            },
            "meta": {"name": "Overworld"},
        }
    }

    docs = build_map_documents_from_session(session)

    assert docs["world"]["assets"]["background_layers"][0]["id"] == "bg1"
    assert docs["world"]["meta"]["name"] == "Overworld"
    assert docs["world"]["map_type"] == "world"


def test_map_document_scene_serialization_roundtrips_walls_doors_props_and_poi_markers():
    from server.map_document import build_map_document, hydrate_session_from_map_documents
    from server.session import POI, Session

    session = Session(id="scene-roundtrip", created_at=time.time())
    session.map_image_url = "/static/maps/world.png"
    session.pois["poi-inn"] = POI(id="poi-inn", x=5, y=5, name="Inn", local_map_url="/static/maps/inn.png")
    session.editor_layers = {"poi-inn": {"1,1": "3", "2,2": "6"}}
    session.editor_walls = {
        "poi-inn": [
            {"id": "wall-1", "x1": 0, "y1": 0, "x2": 10, "y2": 0, "door": False},
            {"id": "door-1", "x1": 4, "y1": 0, "x2": 6, "y2": 0, "door": True, "open": True},
        ]
    }
    session.editor_props = {
        "poi-inn": [{"id": "prop-1", "kind": "chest", "x": 7, "y": 8, "rotation": 90, "map_context": "poi-inn"}]
    }
    session.editor_markers = {
        "poi-inn": [{"id": "marker-1", "kind": "poi", "label": "Back to World", "x": 9, "y": 4, "linked_poi_id": "poi-inn"}]
    }
    session.map_settings = {"poi-inn": {"editor_mode": "tactical"}}

    built = build_map_document(session, "poi-inn")

    assert built["map_context"] == "poi-inn"
    assert built["assets"]["background_url"] == "/static/maps/inn.png"
    assert built["layers"]["terrain"]["cells"] == {"1,1": "3", "2,2": "6"}
    assert len(built["layers"]["walls"]) == 2
    assert built["layers"]["walls"][1]["door"] is True
    assert built["layers"]["walls"][1]["open"] is True
    assert built["layers"]["props"][0]["kind"] == "chest"
    assert built["layers"]["markers"][0]["linked_poi_id"] == "poi-inn"

    restored = Session(id="scene-roundtrip-restored", created_at=time.time())
    hydrate_session_from_map_documents(restored, {"poi-inn": built})

    assert restored.editor_layers["poi-inn"] == {"1,1": "3", "2,2": "6"}
    assert restored.editor_walls["poi-inn"][1]["door"] is True
    assert restored.editor_walls["poi-inn"][1]["open"] is True
    assert restored.editor_props["poi-inn"][0]["kind"] == "chest"
    assert restored.editor_markers["poi-inn"][0]["linked_poi_id"] == "poi-inn"


def test_map_document_roundtrip_preserves_guild_board_prop_fields():
    from server.map_document import build_map_document, hydrate_session_from_map_documents
    from server.session import Session

    session = Session(id="guild-board-roundtrip", created_at=time.time())
    session.editor_props = {
        "world": [{
            "id": "prop-guild-board",
            "kind": "custom_asset",
            "name": "Town Guild Board",
            "asset_id": "guild_board",
            "x": 120,
            "y": 180,
            "w": 2,
            "h": 2,
            "rotation": 0,
            "map_context": "world",
        }]
    }

    built = build_map_document(session, "world")
    prop = built["layers"]["props"][0]
    assert prop["kind"] == "custom_asset"
    assert prop["asset_id"] == "guild_board"
    assert prop["name"] == "Town Guild Board"

    restored = Session(id="guild-board-roundtrip-restored", created_at=time.time())
    hydrate_session_from_map_documents(restored, {"world": built})
    restored_prop = restored.editor_props["world"][0]
    assert restored_prop["kind"] == "custom_asset"
    assert restored_prop["asset_id"] == "guild_board"
    assert restored_prop["name"] == "Town Guild Board"
