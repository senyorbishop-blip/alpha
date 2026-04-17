from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_resolver_uses_document_hp_and_equipment_ac_as_runtime_authority():
    src = _read('server/character/resolver.py')
    assert 'def _runtime_hp_from_document' in src
    assert 'def _compute_equipment_ac' in src
    assert 'runtime["hp"] = _compute_base_hp' in src
    assert 'runtime["ac"] = _compute_equipment_ac' in src
    assert '"tempHP": runtime["hp"]["temp"]' in src


def test_mapper_syncs_spell_math_and_ability_scores_into_sheet_payload():
    src = _read('client/static/js/character/runtime/mapper_to_play.js')
    assert 'out.abilityScores = Object.assign({}, asObject(out.abilityScores), {' in src
    assert 'if (spellAccess.saveDc != null) out.spellSaveDc = String(asInt(spellAccess.saveDc' in src
    assert 'if (spellAccess.attackBonus != null) out.spellAttack = signed(spellAccess.attackBonus);' in src


def test_mapper_keeps_token_vitals_synced_with_runtime_hp_and_senses():
    src = _read('client/static/js/character/runtime/mapper_to_play.js')
    assert 'tempHP: mappedTempHp' in src
    assert 'speed: asInt(combat.speed, asInt(asObject(runtime.speed).walk, asInt(token.speed, 30)))' in src
    assert 'darkvision: asInt(combat.darkvision, asInt(asObject(runtime.senses).darkvision, asInt(token.darkvision, 0)))' in src
    assert 'reach: firstNonEmpty(entry.reach, \'\'),' in src
    assert 'existing.properties = clone(normalized.properties);' in src
    assert 'existing.weapon_properties = clone(normalized.weapon_properties);' in src


def test_actions_tab_prefers_equipped_weapons_and_shows_attack_math_context():
    src = _read('client/static/js/character/tabs/actions_tab.js')
    assert 'const equippedRows = weaponRows.filter(function (row) { return !!row.equipped; });' in src
    assert 'const sourceRows = equippedRows.length ? equippedRows : weaponRows;' in src
    assert "resourceName: ammoKind ? ('Ammo: ' + ammoKind) : ''" in src
    assert "item.equipped ? 'Equipped' : 'Inventory only'" in src
    assert "const hasUsableWeaponCard = combined.some(function (entry) {" in src
    assert "return source === 'weapon' || source === 'equip_only';" in src


def test_spells_tab_uses_shared_spell_access_math_for_attack_and_dc_labels():
    src = _read('client/static/js/character/tabs/spells_tab.js')
    assert 'const spellAccess = charData && charData.spellAccess && typeof charData.spellAccess === \'object\' ? charData.spellAccess : {};' in src
    assert 'spellAccess.attackBonus != null ? String(spellAccess.attackBonus) : \'\'' in src
    assert 'spellAccess.saveDc != null ? String(spellAccess.saveDc) : \'\'' in src
