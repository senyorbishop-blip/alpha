import contextlib
import sqlite3
from pathlib import Path

import pytest


def _patch_rules_db(tmp_path, monkeypatch):
    import server.rules_db as rules_db

    db_path = str(tmp_path / "rules_custom_spells.db")

    @contextlib.contextmanager
    def patched_get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    monkeypatch.setattr(rules_db, "get_conn", patched_get_conn)
    rules_db.init_rules_db()
    return rules_db


def test_custom_spell_insert_read_supports_dm_authored_fields(tmp_path, monkeypatch):
    rules_db = _patch_rules_db(tmp_path, monkeypatch)

    saved = rules_db.upsert_custom_spell(
        "session-a",
        "dm-a",
        {
            "name": "Moonlit Lance",
            "spell_level": 2,
            "school": "Evocation",
            "casting_time": "1 action",
            "range": "90 feet",
            "components": "V, S",
            "duration": "Instantaneous",
            "description": "Make a ranged spell attack with a silver lance of light.",
            "attack_type": "ranged_spell_attack",
            "damage_type": "radiant",
            "damageFormula": "3d8",
            "classes": ["Cleric"],
            "class_lists": ["Cleric", "Wizard"],
            "tags": ["damage", "custom"],
        },
    )

    loaded = rules_db.get_custom_spell("session-a", saved["id"])
    assert loaded["name"] == "Moonlit Lance"
    assert loaded["spell_level"] == 2
    assert loaded["school"] == "Evocation"
    assert loaded["range"] == "90 feet"
    assert loaded["components"] == "V, S"
    assert loaded["duration"] == "Instantaneous"
    assert loaded["base_effect_text"] == "Make a ranged spell attack with a silver lance of light."
    assert loaded["attack_type"] == "ranged_spell_attack"
    assert loaded["damage_type"] == "radiant"
    assert loaded["base_damage_formula"] == "3d8"
    assert loaded["class_lists"] == ["Cleric", "Wizard"]
    assert loaded["tags"] == ["damage", "custom"]
    assert loaded["is_homebrew"] is True
    assert loaded["created_by_dm"] is True


def test_imported_only_spell_can_be_converted_to_custom_and_merged_into_library(tmp_path, monkeypatch):
    rules_db = _patch_rules_db(tmp_path, monkeypatch)

    imported_entry = {
        "id": "starfall-aegis",
        "name": "Starfall Aegis",
        "matchedNative": False,
        "level": 3,
        "school": "Abjuration",
        "castingTime": "1 reaction",
        "range": "Self",
        "components": "V",
        "duration": "1 round",
        "notes": "Imported character sheet facts preserved for DM review.",
    }
    library_with_fallback = rules_db.get_spell_library("session-b", [imported_entry])
    fallback = next(row for row in library_with_fallback if row.get("name") == "Starfall Aegis")
    assert fallback["spell_source"] == "imported"
    assert fallback["importedOnly"] is True
    assert fallback["needsReview"] is True

    custom = rules_db.upsert_custom_spell(
        "session-b",
        "dm-b",
        {
            "name": imported_entry["name"],
            "spell_level": imported_entry["level"],
            "school": imported_entry["school"],
            "casting_time": imported_entry["castingTime"],
            "range": imported_entry["range"],
            "components": imported_entry["components"],
            "duration": imported_entry["duration"],
            "base_effect_text": imported_entry["notes"],
            "tags": ["imported", "reviewed"],
        },
    )

    merged_after_conversion = rules_db.get_spell_library("session-b", [imported_entry])
    reviewed = [row for row in merged_after_conversion if row.get("name") == "Starfall Aegis"]
    assert len(reviewed) == 1
    assert reviewed[0]["id"] == custom["id"]
    assert reviewed[0]["spell_source"] == "custom"
    assert not reviewed[0].get("importedOnly")


def test_future_import_matches_converted_custom_spell(tmp_path, monkeypatch):
    rules_db = _patch_rules_db(tmp_path, monkeypatch)
    custom = rules_db.upsert_custom_spell(
        "session-c",
        "dm-c",
        {
            "name": "Frostfire Rebuke",
            "spell_level": 1,
            "school": "Evocation",
            "casting_time": "1 reaction",
            "range": "60 feet",
            "components": "V, S",
            "duration": "Instantaneous",
            "base_effect_text": "A reviewed homebrew reaction from an imported sheet.",
            "save_ability": "DEX",
            "damage_type": "cold/fire",
            "base_damage_formula": "2d6",
        },
    )

    from server.rules_engine import enrich_spellbook

    character = {"spellbookEntries": [{"name": "Frostfire Rebuke", "source": "D&D Beyond import"}]}
    enriched = enrich_spellbook(character, rules_db.get_official_spells(), rules_db.get_custom_spells("session-c"))

    assert enriched["unmatched"] == []
    assert enriched["review_queue"] == []
    assert enriched["spell_cards"][0]["id"] == custom["id"]
    assert enriched["spell_cards"][0]["source_tag"] == "DM custom"


def test_no_dnd_beyond_compendium_scraper_or_bypass_code_added():
    production_roots = [Path("server"), Path("client/static/js"), Path("client/templates")]
    scanned_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for root in production_roots
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".js", ".html"}
    ).lower()

    assert "dndbeyond.com/spells" not in scanned_text
    assert "dndbeyond.com/sources" not in scanned_text
    assert "dndbeyond.com/magic-items" not in scanned_text
    assert "beautifulsoup" not in scanned_text
    assert "selenium" not in scanned_text
    assert "playwright" not in scanned_text
    assert "paid compendium" not in scanned_text
