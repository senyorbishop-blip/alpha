from server.character.import_normalizer import normalize_ddb_json_payload, normalize_pdf_payload


def test_normalize_ddb_json_payload_produces_canonical_document():
    payload = {
        "data": {
            "id": 987654,
            "name": "Aela",
            "stats": [
                {"id": 1, "value": 10},
                {"id": 2, "value": 14},
                {"id": 3, "value": 12},
                {"id": 4, "value": 8},
                {"id": 5, "value": 13},
                {"id": 6, "value": 16},
            ],
            "classes": [
                {
                    "level": 3,
                    "definition": {"name": "Rogue"},
                    "subclassDefinition": {"name": "Arcane Trickster"},
                }
            ],
            "race": {
                "fullName": "Wood Elf",
                "weightSpeeds": {"normal": {"walk": 35}},
            },
            "background": {"definition": {"name": "Urchin"}},
        }
    }

    result = normalize_ddb_json_payload(payload, external_id="987654")
    doc = result["document"]

    assert doc["schema"] == "casual-dnd.character"
    assert doc["sourceMode"] == "dndbeyond"
    assert doc["identity"]["characterId"] == "987654"
    assert doc["identity"]["name"] == "Aela"
    assert doc["classes"][0]["name"] == "Rogue"
    assert doc["abilities"]["scores"]["dex"] == 14
    assert doc["species"]["name"] == "Wood Elf"
    assert isinstance(result["warnings"], list)


def test_normalize_pdf_payload_reports_missing_content_warnings():
    parsed = {
        "name": "Unknown Hero",
        "stats": [10, 10, 10, 10, 10, 10],
        "classes": [],
        "race": "",
        "background": "",
        "currency": "12 gp, 3 sp",
    }

    result = normalize_pdf_payload(parsed, filename="imported.pdf")

    assert result["document"]["sourceMode"] == "dndbeyond"
    assert result["document"]["equipment"]["currency"]["gp"] == 12
    assert result["document"]["equipment"]["currency"]["sp"] == 3
    assert any("Species" in warning for warning in result["warnings"])
    assert any("Background" in warning for warning in result["warnings"])


def test_ddb_json_import_preserves_playable_inventory_actions_features_and_spells():
    payload = {
        "data": {
            "id": 2468,
            "name": "Borin",
            "stats": [
                {"id": 1, "value": 16},
                {"id": 2, "value": 12},
                {"id": 3, "value": 14},
                {"id": 4, "value": 10},
                {"id": 5, "value": 10},
                {"id": 6, "value": 8},
            ],
            "classes": [
                {
                    "level": 3,
                    "definition": {"name": "Fighter"},
                    "subclassDefinition": {"name": "Champion"},
                    "classFeatures": [
                        {"definition": {"name": "Second Wind", "description": "Regain hit points as a bonus action."}}
                    ],
                }
            ],
            "race": {
                "fullName": "Mountain Dwarf",
                "weightSpeeds": {"normal": {"walk": 25}},
                "racialTraits": [
                    {"definition": {"name": "Dwarven Resilience", "description": "Advantage against poison."}}
                ],
            },
            "background": {"definition": {"name": "Soldier"}},
            "inventory": [
                {
                    "id": 11,
                    "quantity": 1,
                    "equipped": True,
                    "definition": {
                        "id": 101,
                        "name": "Longsword",
                        "filterType": "Weapon",
                        "damage": {"dice": {"diceCount": 1, "diceValue": 8}, "damageType": {"name": "Slashing"}},
                        "properties": [{"name": "Versatile"}],
                    },
                },
                {
                    "id": 12,
                    "quantity": 1,
                    "equipped": True,
                    "definition": {"id": 102, "name": "Shield", "filterType": "Armor", "armorClass": 2},
                },
                {
                    "id": 13,
                    "quantity": 1,
                    "definition": {"id": 103, "name": "Potion of Healing", "filterType": "Potion", "description": "Regain 2d4+2 hit points."},
                },
            ],
            "actions": {
                "class": [
                    {
                        "name": "Second Wind",
                        "snippet": "Regain hit points.",
                        "description": "Use a bonus action to regain hit points.",
                        "activation": {"activationType": 3},
                        "limitedUse": {"maxUses": 1},
                    }
                ]
            },
            "spells": {
                "class": [
                    {"definition": {"name": "Magic Missile"}, "prepared": True},
                    {"definition": {"name": "Not Quite Native Spell"}},
                ]
            },
        }
    }

    result = normalize_ddb_json_payload(payload, external_id="2468")
    doc = result["document"]
    inventory = doc["equipment"]["inventory"]
    by_name = {str(row.get("name") or "").lower(): row for row in inventory}

    assert by_name["longsword"]["damage_dice"] == "1d8"
    assert by_name["longsword"]["damage_type"] == "slashing"
    assert by_name["longsword"]["equipped"] is True
    assert doc["equipment"]["equipped"]["main_hand"]["name"] == "Longsword"
    assert by_name["shield"]["equipment_kind"] == "shield"
    assert doc["equipment"]["equipped"]["off_hand"]["name"] == "Shield"
    assert by_name["potion of healing"]["item_type"] == "potion"

    import_meta = doc["importMeta"]
    assert any(row["name"] == "Second Wind" for row in import_meta["importedActions"])
    assert any(row["name"] == "Dwarven Resilience" for row in import_meta["importedFeatures"])
    assert any(row["id"] == "magic-missile" for row in doc["spellState"]["spellbookEntries"])
    assert any(row["id"] == "not-quite-native-spell" for row in doc["spellState"]["spellbookEntries"])
    assert import_meta["importedInventoryCount"] == 3
    assert any(warning.get("code") == "missing_spell_mapping" for warning in result["warnings"])


def test_ddb_imported_actions_and_features_resolve_into_runtime_cards():
    from server.character.resolver import resolve_character_runtime

    result = normalize_ddb_json_payload(
        {
            "data": {
                "id": 1357,
                "name": "Lyra",
                "stats": [
                    {"id": 1, "value": 8},
                    {"id": 2, "value": 14},
                    {"id": 3, "value": 12},
                    {"id": 4, "value": 16},
                    {"id": 5, "value": 10},
                    {"id": 6, "value": 10},
                ],
                "classes": [{"level": 3, "definition": {"name": "Wizard"}, "subclassDefinition": {"name": "School of Evocation"}}],
                "race": {"fullName": "High Elf"},
                "actions": {
                    "class": [
                        {"name": "Arcane Recovery", "description": "Recover spell slots.", "activation": {"activationType": 7}}
                    ],
                    "item": [
                        {"name": "Wand Spark", "description": "Fire a spark from your wand.", "activation": {"activationType": 1}}
                    ],
                },
                "classFeatures": [
                    {"definition": {"name": "Sculpt Spells", "description": "Protect allies from your evocation spells."}}
                ],
            }
        },
        external_id="1357",
    )

    runtime = resolve_character_runtime(result["document"])["runtime"]
    action_names = {row.get("name") for row in runtime["actions"]}
    passive_names = {row.get("name") for row in runtime["passives"]}
    feature_names = {row.get("name") for row in runtime["classFeatures"]}

    assert "Wand Spark" in action_names
    assert "Arcane Recovery" in passive_names
    assert "Sculpt Spells" in feature_names
