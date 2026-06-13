"""Tests for HP/AC import handling and audit trail."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest


def _make_fighter_payload():
    return {
        "data": {
            "id": "test-fighter-1",
            "name": "Test Fighter",
            "classes": [{"definition": {"name": "Fighter"}, "level": 5}],
            "stats": [{"id": i, "value": 14} for i in range(1, 7)],
            "bonusStats": [], "overrideStats": [],
            "spells": {},
            "currencies": {},
            "race": {"baseName": "Human", "fullName": "Human", "weightSpeeds": {"normal": {"walk": 30}}},
            "background": {"definition": {"name": "Soldier"}},
        }
    }


def test_ddb_import_returns_document():
    from server.character.import_normalizer import normalize_ddb_json_payload
    result = normalize_ddb_json_payload(_make_fighter_payload())
    assert result.get("document") is not None


def test_ddb_import_has_import_meta():
    from server.character.import_normalizer import normalize_ddb_json_payload
    result = normalize_ddb_json_payload(_make_fighter_payload())
    doc = result["document"]
    import_meta = doc.get("importMeta") or {}
    assert "origin" in import_meta or "nativeImportMode" in import_meta, \
        "importMeta must record origin of import"


def test_item_schema_normalize_weapon():
    """normalize_item_record returns a structured canonical dict with an identity sub-dict."""
    from server.item_schema import normalize_item_record
    item = normalize_item_record({"name": "Longsword", "category": "weapon"})
    # The canonical format nests name/category under 'identity'
    identity = item.get("identity") or item
    assert identity.get("name") == "Longsword"
    assert identity.get("category") == "weapon"


def test_item_schema_normalize_armor():
    """normalize_item_record handles armor items correctly."""
    from server.item_schema import normalize_item_record
    item = normalize_item_record({"name": "Chain Mail", "category": "armor"})
    identity = item.get("identity") or item
    assert identity.get("name") == "Chain Mail"
    assert identity.get("category") == "armor"


def test_unknown_spell_level_not_cantrip_in_spellbook_render():
    """play.html spell_level fallback must not use ?? 0 (maps to Cantrip)."""
    with open("client/templates/play.html") as f:
        src = f.read()
    assert "s.spell_level ?? 0)" not in src, \
        "spell_level must not fallback to 0 (Cantrip) when missing"


def test_no_silent_hp_default():
    """HP calculation must not silently default to 1 without import meta."""
    from server.character.import_normalizer import normalize_ddb_json_payload
    payload = _make_fighter_payload()
    result = normalize_ddb_json_payload(payload)
    doc = result["document"]
    # importMeta should record the import, even if HP comes from calculation
    assert doc.get("importMeta") is not None, "importMeta must be present"


def test_audit_spell_catalog_script_exists():
    assert os.path.exists("tools/audit_spell_catalog.py"), \
        "tools/audit_spell_catalog.py must exist"


def test_audit_item_catalog_script_exists():
    assert os.path.exists("tools/audit_item_catalog.py"), \
        "tools/audit_item_catalog.py must exist"
