from server.character.resolver import resolve_character_runtime


def _doc(class_id, level=5, spells=None, inventory=None, imported_features=None):
    return {
        "name": f"{class_id.title()} Five",
        "species": {"id": "human", "name": "Human", "speed": 30},
        "abilities": {"scores": {"str": 16, "dex": 14, "con": 14, "int": 12, "wis": 14, "cha": 16}},
        "classes": [{"classId": class_id, "name": class_id.title(), "level": level}],
        "spellState": {"known": spells or [], "prepared": spells or [], "slots": {"1": {"max": 4, "used": 0}, "2": {"max": 3, "used": 0}, "3": {"max": 2, "used": 0}}},
        "equipment": {"inventory": inventory or []},
        "importMeta": {"importedFeatures": imported_features or []},
    }


def _runtime(doc):
    return resolve_character_runtime(doc)["runtime"]["characterSheetRuntime"]


def _names(rows):
    return {str(r.get("name") or r.get("displayName") or "").lower() for r in rows if isinstance(r, dict)}


def _resource_ids(rt):
    return {str(r.get("id") or "").lower(): r for r in rt["resources"]}


def _assert_common(rt):
    for key in ["identity", "abilities", "saves", "skills", "passiveScores", "senses", "defenses", "conditions", "hp", "ac", "speed", "initiative", "proficiencyBonus", "resources", "attacks", "actions", "bonusActions", "reactions", "limitedUseActions", "spells", "itemSpells", "features", "traits", "feats", "backgroundFeatures", "itemTraits", "inventory", "warnings", "needsReview"]:
        assert key in rt
    assert isinstance(rt["resources"], list)
    assert len(_names(rt["features"])) == len([n for n in _names(rt["features"])])
    for r in rt["resources"]:
        assert {"id", "name", "current", "max", "recovery", "source", "linkedFeatures", "linkedActions", "spendable", "restReset"} <= set(r)


def test_level_five_class_fixture_matrix_runtime_sections_and_expected_resources():
    expectations = {
        "barbarian": "rage_uses",
        "bard": "bardic_inspiration",
        "cleric": "channel_divinity",
        "druid": "wild_shape",
        "fighter": "action_surge",
        "monk": "focus_points",
        "paladin": "lay_on_hands",
        "ranger": None,
        "rogue": None,
        "warlock": "pact_slots",
        "wizard": "arcane_recovery",
    }
    for class_id, resource_id in expectations.items():
        rt = _runtime(_doc(class_id, spells=["cure-wounds"] if class_id in {"bard", "cleric", "druid", "paladin", "ranger"} else ["fireball"] if class_id in {"wizard", "warlock"} else []))
        _assert_common(rt)
        if resource_id:
            assert resource_id in _resource_ids(rt), class_id
        action_names = _names(rt["actions"] + rt["bonusActions"] + rt["reactions"] + rt["limitedUseActions"])
        assert action_names or rt["attacks"]


def test_sorcerer_imported_pdf_features_merge_without_duplicates():
    rt = _runtime(_doc("sorcerer", level=19, spells=["fire-bolt", "scorching-ray", "fireball"], imported_features=[
        {"name": "Font of Magic", "sourceType": "class"},
        {"name": "Metamagic", "sourceType": "class"},
        {"name": "Wild Magic Surge", "sourceType": "subclass"},
    ]))
    _assert_common(rt)
    names = [n for n in _names(rt["features"])]
    assert "font of magic" in names
    assert "metamagic" in names
    assert len([r for r in rt["features"] if str(r.get("name") or "").lower() == "font of magic"]) == 1
    assert "sorcery_points" in _resource_ids(rt)


def test_item_runtime_separates_item_spells_attacks_charges_and_traits():
    rt = _runtime(_doc("wizard", spells=["fireball"], inventory=[
        {"id": "thunder-mage-quarterstaff-plus-3", "name": "Thunder Mage Quarterstaff, +3", "equipped": True, "attuned": True, "charges_current": 7},
        {"id": "wand-of-fireballs", "name": "Wand of Fireballs", "equipped": True, "attuned": True, "charges_current": 5},
        {"id": "ring-of-protection", "name": "Ring of Protection", "equipped": True, "attuned": True},
    ]))
    _assert_common(rt)
    assert any("thunder mage quarterstaff" in str(a.get("name") or "").lower() for a in rt["attacks"])
    item_spell_names = _names(rt["itemSpells"])
    assert "fireball" in item_spell_names
    assert "thunderwave" in item_spell_names
    assert all(str(s.get("sourceType") or s.get("source") or "").lower() != "item_spell" for s in rt["spells"])
    assert any(str(r.get("source")) == "item" and "charges" in str(r.get("name") or "").lower() for r in rt["resources"])
    assert any(str(t.get("source")) == "item" for t in rt["itemTraits"])


def _item_named(rt, name):
    return next(row for row in rt["attacks"] if name.lower() in str(row.get("name") or "").lower())


def test_magic_item_plus_three_weapon_modifiers_flow_to_runtime_attacks():
    rt = _runtime(_doc("fighter", inventory=[{
        "id": "longsword-plus-3",
        "name": "Longsword +3",
        "equipment_kind": "weapon",
        "equipped": True,
        "damage_dice": "1d8",
        "damage_type": "slashing",
        "modifiers": [
            {"type": "weapon_attack_bonus", "value": 3},
            {"type": "weapon_damage_bonus", "value": 3},
        ],
    }]))
    attack = _item_named(rt, "Longsword")
    assert attack["attackBonus"] == 9  # STR +3, proficiency +3 at level 5, item +3
    assert attack["damage"]["formula"] == "1d8+3"


def test_spell_attack_bonus_item_flows_to_item_spell_card_preview():
    rt = _runtime(_doc("wizard", spells=[], inventory=[{
        "id": "arcane-focus-of-accuracy",
        "name": "Arcane Focus of Accuracy",
        "equipment_kind": "wand",
        "equipped": True,
        "requires_attunement": True,
        "attuned": True,
        "item_spell_attack_bonus": 7,
        "modifiers": [{"type": "spell_attack_bonus", "value": 2}],
        "granted_spells": [{"id": "fire-bolt", "name": "Fire Bolt", "charge_cost": 0, "cast_level": 0, "uses_item_attack_bonus": True}],
    }]))
    spell = next(row for row in rt["itemSpells"] if row["id"] == "fire-bolt")
    assert spell["spellAttackBonus"] == 9
    assert spell["attackBonus"] == 9
    assert spell["itemName"] == "Arcane Focus of Accuracy"


def test_item_with_three_charges_grants_spell_and_resource_cost():
    rt = _runtime(_doc("wizard", spells=[], inventory=[{
        "id": "wand-of-magic-missiles",
        "name": "Wand of Magic Missiles",
        "equipment_kind": "wand",
        "equipped": True,
        "charges_max": 3,
        "charges_current": 3,
        "recharge_type": "dawn",
        "granted_spells": [{"id": "magic-missile", "name": "Magic Missile", "charge_cost": 1, "cast_level": 1}],
    }]))
    resource = next(row for row in rt["resources"] if row["source"] == "item")
    spell = next(row for row in rt["itemSpells"] if row["id"] == "magic-missile")
    assert resource["current"] == 3
    assert resource["max"] == 3
    assert spell["chargeCost"] == 1
    assert spell["resourceCost"] == {"resourceId": resource["id"], "amount": 1}


def test_unattuned_attunement_item_does_not_apply_bonuses_or_spells():
    rt = _runtime(_doc("fighter", inventory=[{
        "id": "attunement-longsword-plus-3",
        "name": "Attunement Longsword +3",
        "equipment_kind": "weapon",
        "equipped": True,
        "requires_attunement": True,
        "attuned": False,
        "damage_dice": "1d8",
        "modifiers": [{"type": "weapon_attack_bonus", "value": 3}, {"type": "weapon_damage_bonus", "value": 3}],
        "granted_spells": [{"id": "magic-missile", "name": "Magic Missile", "charge_cost": 1}],
    }]))
    assert not any("attunement longsword" in str(row.get("name") or "").lower() for row in rt["attacks"])
    assert not rt["itemSpells"]
