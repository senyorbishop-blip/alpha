from server.item_compendium import all_items_by_rarity, resolve_item, clear_cache


def _item(name):
    clear_cache()
    found = resolve_item(name)
    assert found, name
    return found


def test_rare_very_rare_and_legendary_batches_load():
    clear_cache()
    rare = {i["name"] for i in all_items_by_rarity("rare")}
    very_rare = {i["name"] for i in all_items_by_rarity("very_rare")}
    legendary = {i["name"] for i in all_items_by_rarity("legendary")}
    assert {"Wand of Fireballs", "Ring of Protection", "Staff of Healing", "Armor +1"} <= rare
    assert {"Staff of Fire", "Staff of Power", "Wand of the War Mage +3", "Armor +2"} <= very_rare
    assert {"Holy Avenger", "Cloak of Invisibility", "Staff of the Magi", "Armor +3"} <= legendary


def test_artifacts_load_and_are_excluded_from_random_loot_by_default():
    clear_cache()
    artifacts = all_items_by_rarity("artifact")
    assert {"Eye of Vecna", "Hand of Vecna", "Wand of Orcus"} <= {i["name"] for i in artifacts}
    assert all(i.get("random_loot_excluded") is True for i in artifacts)
    assert all(i.get("dm_warning") or i.get("artifact_warning") for i in artifacts)


def test_no_duplicate_ids_names_or_slugs_after_upgrade_merge():
    clear_cache()
    items = []
    for rarity in ["rare", "very_rare", "legendary", "artifact"]:
        items.extend(all_items_by_rarity(rarity))
    for field in ["id", "name", "slug"]:
        vals = [str(i.get(field) or "").lower() for i in items if i.get(field)]
        assert len(vals) == len(set(vals)), field


def test_aliases_and_legacy_ids_resolve_to_canonical_items():
    assert resolve_item("+1 Armor")["id"] == "armor-plus1"
    assert resolve_item("mi_armor_1")["id"] == "armor-plus1"
    assert resolve_item("mi_wand_fireballs")["id"] == "wand-of-fireballs"
    assert resolve_item("mi_ring_protection")["id"] == "ring-of-protection"


def test_staff_and_wand_spell_actions_have_charges_and_costs():
    for name, spell in [("Staff of Fire", "fireball"), ("Staff of Power", "fireball"), ("Wand of Fireballs", "fireball")]:
        item = _item(name)
        assert item["charges_max"] > 0
        assert item.get("granted_actions")
        spells = item.get("granted_spells") or []
        assert any((s.get("spell_id") or s.get("id")) == spell and int(s.get("charge_cost") or 0) > 0 for s in spells)


def test_ring_holy_cloak_and_pact_keeper_runtime_metadata():
    ring = _item("Ring of Protection")
    assert ring.get("ac_bonus") == 1 and ring.get("save_bonus") == 1
    holy = _item("Holy Avenger")
    assert holy.get("attack_bonus") == 3 and holy.get("damage_bonus") == 3
    assert holy.get("extra_damage") or any(e.get("type") == "extra_damage" for e in holy.get("passive_effects", []))
    cloak = _item("Cloak of Invisibility")
    assert cloak.get("charges_max", 0) > 0 and cloak.get("limited_uses")
    rod = _item("Rod of the Pact Keeper +2")
    assert rod.get("spell_attack_bonus") == 2
    assert any(e.get("type") == "spell_save_dc_bonus" for e in rod.get("passive_effects", []))


def test_thunder_mage_quarterstaff_runtime_metadata():
    staff = _item("Thunder Mage Quarterstaff, +3")
    assert staff.get("attack_bonus") == 3 and staff.get("damage_bonus") == 3
    assert staff.get("charges_max", 0) >= 10
    assert staff.get("granted_spells")
    assert staff.get("damage_dice")


def test_audit_stub_and_blocked_metadata_is_reportable():
    clear_cache()
    items = all_items_by_rarity("legendary") + all_items_by_rarity("artifact")
    assert any(i.get("stub") for i in items)
    assert any(i.get("blocked_proprietary") for i in items)
