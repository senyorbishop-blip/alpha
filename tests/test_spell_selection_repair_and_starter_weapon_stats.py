from server.character.progression import build_levelup_preview
from server.character.service import normalize_incoming_document
from server.character.spell_compendium import repair_spell_state_for_document


def test_repair_spell_state_removes_wrong_class_spell_from_warlock():
    document = {
        "classes": [{"classId": "warlock", "level": 3, "subclassId": "fiend-patron"}],
        "abilities": {"scores": {"cha": 18}},
        "spellState": {
            "known": ["eldritch-blast", "healing-word"],
            "prepared": [],
        },
    }

    result = repair_spell_state_for_document(
        document,
        class_id="warlock",
        class_level=3,
        abilities=document.get("abilities"),
        subclass_id="fiend-patron",
    )

    assert result["changed"] is True
    assert "healing-word" in result["removedKnown"]
    assert "healing-word" not in (document.get("spellState") or {}).get("known", [])


def test_levelup_preview_repairs_stale_illegal_spell_state_for_warlock():
    document = {
        "identity": {"name": "Nyx"},
        "classes": [{"classId": "warlock", "level": 3, "subclassId": "fiend-patron"}],
        "abilities": {"scores": {"cha": 18, "con": 14}},
        "spellState": {
            "known": ["eldritch-blast", "mage-hand", "healing-word", "hex", "armor-of-agathys"],
            "prepared": [],
        },
    }

    preview = build_levelup_preview(document)
    assert preview["nextLevel"] == 4
    spell_choices = preview.get("spellChoices") or {}
    option_ids = [str(row.get("id") or "") for row in (spell_choices.get("levelledOptions") or []) if isinstance(row, dict)]
    assert "healing-word" not in option_ids


def test_normalize_incoming_document_enriches_starter_weapon_damage_fields():
    normalized = normalize_incoming_document(
        {
            "class": {"id": "sorcerer"},
            "progression": {"level": 1},
            "equipment": {
                "choices": ["Quarterstaff", "Dagger ×2"],
                "inventory": [
                    {"name": "Quarterstaff", "qty": 1, "equipment_kind": "weapon", "item_type": "weapon"},
                    {"name": "Dagger", "qty": 2, "equipment_kind": "weapon", "item_type": "weapon"},
                ],
                "currency": {"gp": 15},
            },
            "spellbook": {"known": [], "prepared": []},
        }
    )

    inventory = ((normalized.get("equipment") or {}).get("inventory") or [])
    by_name = {str(row.get("name") or "").lower(): row for row in inventory if isinstance(row, dict)}

    quarterstaff = by_name.get("quarterstaff") or {}
    dagger = by_name.get("dagger") or {}

    assert quarterstaff.get("damage_dice") == "1d6"
    assert quarterstaff.get("versatile_damage") == "1d8"
    assert quarterstaff.get("damage_type") == "bludgeoning"
    assert dagger.get("damage_dice") == "1d4"
    assert dagger.get("damage_type") == "piercing"
