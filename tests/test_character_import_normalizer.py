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
    assert doc["importMeta"]["sourceType"] == "dndbeyond"
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

    assert result["document"]["sourceMode"] == "pdf"
    assert result["document"]["importMeta"]["sourceType"] == "pdf"
    assert result["document"]["equipment"]["currency"]["gp"] == 12
    assert result["document"]["equipment"]["currency"]["sp"] == 3
    assert any(warning.get("code") == "ambiguous_species" for warning in result["warnings"])
    assert any(warning.get("code") == "partial_pdf_fields" and warning.get("details", {}).get("field") == "background" for warning in result["warnings"])


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


def test_pdf_import_with_attacks_creates_runtime_action_cards():
    result = normalize_pdf_payload(
        {
            "name": "Ser Kael",
            "race": "Human",
            "background": "Soldier",
            "classes": [{"name": "Fighter", "level": 3}],
            "stats": [16, 12, 14, 10, 10, 8],
            "maxHp": 28,
            "currentHp": 21,
            "tempHp": 4,
            "ac": 18,
            "speed": 30,
            "initiative": 1,
            "profBonus": 2,
            "attacks": [
                {"name": "Longsword", "attack": "+5", "damage": "1d8+3 slashing", "notes": "Versatile 1d10."}
            ],
        },
        filename="kael.pdf",
    )

    doc = result["document"]
    imported = doc["importMeta"]["importedActions"]
    assert imported[0]["name"] == "Longsword"
    assert imported[0]["classification"] == "attack"
    assert imported[0]["damage"]["formula"] == "1d8+3"
    assert doc["maxHP"] == 28
    assert doc["currentHP"] == 21
    assert doc["tempHP"] == 4
    assert doc["ac"] == 18

    from server.character.resolver import resolve_character_runtime

    runtime = resolve_character_runtime(doc)["runtime"]
    assert any(action.get("name") == "Longsword" for action in runtime["actions"])
    assert runtime["combat"]["currentHP"] == 21
    assert runtime["combat"]["tempHP"] == 4
    assert runtime["combat"]["ac"] == 18


def test_pdf_import_with_skills_keeps_skill_data():
    result = normalize_pdf_payload(
        {
            "name": "Nyx",
            "race": "Tiefling",
            "background": "Charlatan",
            "classes": [{"name": "Rogue", "level": 2}],
            "stats": [8, 16, 12, 13, 10, 14],
            "skills": {"Stealth": "+7", "Perception": "+4", "Deception": "+6"},
            "profSkills": ["Stealth", "Deception"],
            "savingThrows": {"Dexterity": "+5", "Intelligence": "+3"},
            "passivePerception": 14,
            "passiveInsight": 10,
            "passiveInvestigation": 13,
        },
        filename="nyx.pdf",
    )

    doc = result["document"]
    assert doc["abilities"]["skills"]["stealth"]["total"] == 7
    assert doc["abilities"]["skills"]["stealth"]["proficient"] is True
    assert doc["abilities"]["saves"]["dex"] == 5
    assert doc["passives"]["perception"] == 14

    from server.character.resolver import resolve_character_runtime

    runtime = resolve_character_runtime(doc)["runtime"]
    assert runtime["skills"]["deception"]["total"] == 6
    assert runtime["combat"]["savingThrows"]["dex"] == 5
    assert runtime["senses"]["passiveInvestigation"] == 13


def test_pdf_import_with_spells_maps_known_and_preserves_unknown_spells():
    result = normalize_pdf_payload(
        {
            "name": "Mira",
            "race": "High Elf",
            "background": "Sage",
            "classes": [{"name": "Wizard", "level": 3}],
            "stats": [8, 14, 12, 16, 10, 10],
            "spellbookEntries": [
                {"name": "Magic Missile", "prepared": True, "section": "1st Level"},
                {"name": "Moonlit Spoon", "section": "Cantrip", "notes": "Homebrew cantrip."},
            ],
        },
        filename="mira.pdf",
    )

    doc = result["document"]
    entries = {entry["name"]: entry for entry in doc["spellState"]["spellbookEntries"]}
    assert entries["Magic Missile"]["id"] == "magic-missile"
    assert entries["Magic Missile"]["matchedNative"] is True
    assert entries["Moonlit Spoon"]["id"] == "moonlit-spoon"
    assert entries["Moonlit Spoon"]["matchedNative"] is False
    assert "magic-missile" in doc["spellState"]["known"]
    assert any(warning.get("code") == "missing_spells" for warning in result["warnings"])


def test_pdf_import_with_missing_data_warns_but_still_imports():
    result = normalize_pdf_payload(
        {"name": "Sparse", "stats": [10, 10, 10, 10, 10, 10], "classes": []},
        filename="sparse.pdf",
    )

    doc = result["document"]
    warning_codes = {warning.get("code") for warning in result["warnings"]}
    assert doc["identity"]["name"] == "Sparse"
    assert doc["classes"][0]["classId"] == "adventurer"
    assert {"missing_inventory", "missing_spells", "partial_pdf_fields", "ambiguous_class", "ambiguous_species"}.issubset(warning_codes)


def test_import_review_model_marks_missing_spell_item_feature_and_source_type():
    from server.character.import_review import build_import_review

    document = {
        "sourceMode": "pdf",
        "identity": {"name": "Review Hero", "displayName": "Review Hero"},
        "species": {"name": "Human"},
        "background": {"name": "Sage"},
        "classes": [{"name": "Wizard", "level": 5, "subclass": "School of Evocation"}],
        "maxHP": 30,
        "ac": 12,
        "equipment": {"inventory": [{"name": "Quarterstaff"}]},
        "spellState": {
            "spellbookEntries": [
                {"name": "Magic Missile", "matchedNative": True},
                {"name": "Homebrew Spark", "matchedNative": False},
            ]
        },
        "importMeta": {
            "sourceType": "pdf",
            "warnings": [
                {"code": "missing_inventory", "message": "No shield found."},
                {"code": "unknown_feat", "message": "Feature was preserved as text."},
            ],
        },
    }

    review = build_import_review(document, runtime={"hp": {"max": 30}, "ac": 12})

    assert review["sourceType"] == "pdf"
    assert review["characterName"] == "Review Hero"
    assert review["reviewStatus"] == "needs_review"
    assert review["canContinueToPlay"] is True
    assert "Magic Missile" in review["spellsMatched"]
    assert "Homebrew Spark" in review["spellsImportedOnly"]
    assert "Homebrew Spark" not in review["spellsMissing"]
    assert "Quarterstaff" in review["itemsMatched"]
    assert review["itemsMissing"]
    assert review["featuresMissing"]


def test_imported_unmatched_spell_builds_rollable_fallback_manifest_card():
    from server.character.spell_compendium import build_character_spell_manifest, get_spell_by_id
    from server.character.resolver import resolve_character_runtime

    document = {
        "classes": [{"classId": "wizard", "level": 3}],
        "abilities": {"scores": {"int": 16}},
        "spellState": {
            "known": ["magic-missile"],
            "prepared": ["magic-missile"],
            "spellbookEntries": [
                {"id": "magic-missile", "name": "Magic Missile", "matchedNative": True, "prepared": True},
                {
                    "id": "moonlit-spoon",
                    "spellId": "homebrew-42",
                    "name": "Moonlit Spoon",
                    "matchedNative": False,
                    "prepared": True,
                    "level": 1,
                    "school": "Evocation",
                    "castingTime": "1 action",
                    "range": "60 feet",
                    "components": "V, S",
                    "duration": "Instantaneous",
                    "attackType": "Ranged spell attack",
                    "damageFormula": "2d6+3",
                    "damageType": "radiant",
                    "notes": "Hurl a silver spoon made of moonlight.",
                },
            ],
        },
    }

    manifest = build_character_spell_manifest(document)
    fallback = next(card for card in manifest["cards"] if card["id"] == "moonlit-spoon")
    native = next(card for card in manifest["cards"] if card["id"] == "magic-missile")

    assert fallback["source"] == "imported"
    assert fallback["matchedNative"] is False
    assert fallback["needsReview"] is True
    assert fallback["importedOnly"] is True
    assert fallback["isPrepared"] is True
    assert fallback["attackType"] == "Ranged spell attack"
    assert fallback["damageFormula"] == "2d6+3"
    assert fallback["rollConfig"]["damageFormula"] == "2d6+3"
    assert "Hurl a silver spoon" in fallback["description"]
    assert native.get("source") != "imported"
    assert not native.get("importedOnly")
    assert native["name"] == get_spell_by_id("magic-missile")["name"]

    runtime = resolve_character_runtime(document)["runtime"]
    runtime_fallback = next(card for card in runtime["spellAccess"]["cards"] if card["id"] == "moonlit-spoon")
    assert runtime_fallback["damageFormula"] == "2d6+3"
    assert runtime_fallback["rollConfig"]["damageFormula"] == "2d6+3"


def test_imported_unmatched_spell_without_formula_is_readable_and_needs_review():
    from server.character.spell_compendium import build_character_spell_manifest

    manifest = build_character_spell_manifest({
        "classes": [{"classId": "wizard", "level": 1}],
        "abilities": {"scores": {"int": 16}},
        "spellState": {
            "spellbookEntries": [
                {
                    "id": "quiet-lantern",
                    "name": "Quiet Lantern",
                    "matchedNative": False,
                    "level": "Cantrip",
                    "school": "Illusion",
                    "castingTime": "1 action",
                    "range": "Touch",
                    "duration": "1 hour",
                    "notes": "Create a hooded light only allies can see.",
                }
            ]
        },
    })

    fallback = next(card for card in manifest["cards"] if card["id"] == "quiet-lantern")
    assert fallback["source"] == "imported"
    assert fallback["needsReview"] is True
    assert fallback["importedOnly"] is True
    assert fallback["damageFormula"] == ""
    assert fallback["rollConfig"]["damageFormula"] == ""
    assert "Create a hooded light" in fallback["description"]


def test_import_review_lists_unmatched_spells_as_imported_only():
    from server.character.import_review import build_import_review

    review = build_import_review(
        {
            "identity": {"name": "Review Mage"},
            "species": {"name": "Human"},
            "background": {"name": "Sage"},
            "classes": [{"name": "Wizard", "level": 1}],
            "maxHP": 8,
            "ac": 12,
            "spellState": {
                "spellbookEntries": [
                    {"name": "Magic Missile", "matchedNative": True},
                    {"name": "Moonlit Spoon", "matchedNative": False},
                ]
            },
            "importMeta": {"sourceType": "pdf", "warnings": []},
        },
        runtime={"hp": {"max": 8}, "ac": 12},
    )

    assert "Magic Missile" in review["spellsMatched"]
    assert "Moonlit Spoon" in review["spellsImportedOnly"]
    assert "Moonlit Spoon" not in review["spellsMissing"]
    assert review["reviewStatus"] == "needs_review"


def test_imported_fallback_cards_preserve_unmatched_depth_and_roll_formula():
    from server.character.resolver import build_imported_action_card, build_imported_feature_card, resolve_character_runtime

    result = normalize_ddb_json_payload(
        {
            "data": {
                "id": 4242,
                "name": "Mira",
                "stats": [
                    {"id": 1, "value": 10},
                    {"id": 2, "value": 16},
                    {"id": 3, "value": 12},
                    {"id": 4, "value": 10},
                    {"id": 5, "value": 13},
                    {"id": 6, "value": 10},
                ],
                "classes": [
                    {
                        "level": 4,
                        "definition": {"name": "Rogue"},
                        "subclassDefinition": {
                            "name": "Thief",
                            "classFeatures": [
                                {"definition": {"name": "Rooftop Runner", "description": "Move across rooftops without slowing."}}
                            ],
                        },
                        "classFeatures": [
                            {"definition": {"name": "Pocket Sand", "description": "Blind a nearby foe until the DM resolves it."}}
                        ],
                    }
                ],
                "race": {
                    "fullName": "Forest Gnome",
                    "racialTraits": [
                        {"definition": {"name": "Small Beast Speech", "description": "Communicate simple ideas with small beasts."}}
                    ],
                },
                "background": {"definition": {"name": "Guild Artisan", "featureName": "Guild Access", "featureDescription": "Request modest guild assistance."}},
                "feats": [
                    {"definition": {"name": "Kitchen Duelist", "description": "Use cooking tools in flashy ways."}}
                ],
                "actions": {
                    "class": [
                        {
                            "name": "Pocket Sand",
                            "description": "Throw sand at a target.",
                            "activation": {"activationType": 1},
                            "limitedUse": {"maxUses": 2, "numberUsed": 1, "resetTypeDescription": "Short Rest"},
                            "definition": {"damage": {"dice": {"diceCount": 1, "diceValue": 4}, "damageType": {"name": "bludgeoning"}}},
                        }
                    ],
                    "bonus": [
                        {"name": "Duck Behind Barrel", "description": "Take cover in a chaotic tavern.", "activation": {"activationType": 3}}
                    ],
                },
            }
        },
        external_id="4242",
    )
    doc = result["document"]
    runtime = resolve_character_runtime(doc)["runtime"]

    action = next(row for row in runtime["actions"] if row.get("name") == "Pocket Sand")
    assert action["damageFormula"] == "1d4"
    assert action["damage"] == "1d4"
    assert action["usage"] == "1/2 uses"
    assert action["recovery"] == "Short rest"
    assert action["needsReview"] is True

    assert any(row.get("name") == "Duck Behind Barrel" for row in runtime["bonusActions"])
    assert any(row.get("name") == "Small Beast Speech" and row.get("sourceType") == "species" for row in runtime["classFeatures"])
    assert any(row.get("name") == "Kitchen Duelist" and row.get("sourceType") == "feat" for row in runtime["classFeatures"])
    assert any(row.get("name") == "Guild Access" and row.get("sourceType") == "background" for row in runtime["classFeatures"])
    assert any(row.get("name") == "Rooftop Runner" and row.get("sourceType") == "subclass" for row in runtime["classFeatures"])
    assert any(row.get("needsReview") for row in runtime["nativeFeatures"])
    assert runtime["nativeActions"]["actions"]

    direct_feature = build_imported_feature_card({"name": "Mystery Ribbon"}, {"native_names": set()})
    direct_action = build_imported_action_card({"name": "Mystery Shove", "damageFormula": "1d6"}, {"native_names": set()})
    assert direct_feature["description"] == "Needs DM review."
    assert direct_feature["needsReview"] is True
    assert direct_action["damage"] == "1d6"
    assert direct_action["needsReview"] is True


def test_imported_barbarian_rage_marks_matched_when_native_exists():
    from server.character.resolver import resolve_character_runtime

    result = normalize_ddb_json_payload(
        {
            "data": {
                "id": 5252,
                "name": "Korga",
                "stats": [
                    {"id": 1, "value": 16},
                    {"id": 2, "value": 12},
                    {"id": 3, "value": 14},
                    {"id": 4, "value": 8},
                    {"id": 5, "value": 10},
                    {"id": 6, "value": 10},
                ],
                "classes": [
                    {
                        "level": 2,
                        "definition": {"name": "Barbarian"},
                        "classFeatures": [
                            {"definition": {"name": "Rage", "description": "Imported rage text."}}
                        ],
                    }
                ],
                "race": {"fullName": "Human"},
                "actions": {
                    "class": [
                        {"name": "Rage", "description": "Enter rage.", "activation": {"activationType": 3}, "limitedUse": {"maxUses": 2, "resetTypeDescription": "Long Rest"}}
                    ]
                },
            }
        },
        external_id="5252",
    )

    runtime = resolve_character_runtime(result["document"])["runtime"]
    rage_features = [row for row in runtime["classFeatures"] if row.get("name") == "Rage"]
    rage_actions = [row for row in runtime["bonusActions"] if row.get("name") == "Rage"]
    assert rage_features
    assert rage_actions
    assert any(row.get("needsReview") is False for row in rage_features)
    assert any(row.get("needsReview") is False for row in rage_actions)
    assert any(row.get("trackUses") for row in rage_actions)
