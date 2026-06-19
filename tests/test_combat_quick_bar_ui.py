from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_combat_quick_bar_modules_are_loaded_after_character_actions():
    src = _read('client/templates/play.html')
    actions_idx = src.index('/static/js/character/tabs/actions_tab.js')
    selectors_idx = src.index('/static/js/character/combat_quick_selectors.js')
    bar_idx = src.index('/static/js/character/combat_quick_bar.js')
    assert actions_idx < selectors_idx < bar_idx
    assert 'getCombatQuickBarRuntime' in src
    assert 'executeCombatQuickBarSpell' in src
    assert 'combatQuickCastSpell(spellId)' in src
    assert '_spellCardAttackKindForCombat' in src
    assert 'window.CombatQuickBar.render' in src


def test_actions_tab_exports_shared_quick_action_selector_model():
    src = _read('client/static/js/character/tabs/actions_tab.js')
    assert 'function buildQuickActionModel(charData)' in src
    assert 'primaryActions' in src
    assert 'bonusActions' in src
    assert 'reactions' in src
    assert 'quickBarCanUse' in src
    assert 'global.ActionsTab = { initActionsTab, buildQuickActionModel }' in src


def test_combat_quick_selectors_keep_expected_shape_and_reuse_actions_tab():
    src = _read('client/static/js/character/combat_quick_selectors.js')
    assert 'ActionsTab.buildQuickActionModel' in src
    assert 'selectQuickActions' in src
    assert 'primaryActions' in src
    assert 'bonusActions' in src
    assert 'reactions' in src
    assert 'topSpells' in src
    assert 'resources' in src
    assert 'concentration' in src
    assert 'markUsed' in src
    assert 'quickBarAttackText' in src
    assert 'quickBarAttackKind' in src
    assert 'quickBarDamageText' in src
    assert 'quickBarSaveText' in src
    assert 'quickBarRangeText' in src
    assert '_spellQuickScore' in src


def test_combat_quick_bar_has_required_player_controls_and_states():
    src = _read('client/static/js/character/combat_quick_bar.js')
    assert 'combat-quick-bar' in src
    assert 'toggleManual' in src
    assert 'pointerdown' in src
    assert 'localStorage' in src
    assert 'Open Full Sheet' in src
    assert 'data-qb-open-notes' in src
    assert 'openCharacterStickyNotes' in src
    assert 'Atk ' in src
    assert 'Spell atk ' in src
    assert 'Dmg ' in src
    assert 'Used this turn' in src
    assert 'Needs target' in src
    assert 'Needs slot' in src
    assert 'Concentration:' in src


def test_combat_quick_bar_supports_custom_top_five_and_inventory_refresh():
    selectors = _read('client/static/js/character/combat_quick_selectors.js')
    bar = _read('client/static/js/character/combat_quick_bar.js')
    play = _read('client/templates/play.html')
    assert 'QUICK_PICK_LIMIT = 5' in selectors
    assert 'combat_quick_bar.picks.' in selectors
    assert 'toggleQuickPick' in selectors
    assert 'allSpells' in selectors
    assert 'Customize Top 5' in bar
    assert 'data-qb-pick-key' in bar
    assert 'data-qb-pin' in bar
    assert "window.CombatQuickBar.render();\n  if (typeof requestCharacterBookOverviewRender === 'function') requestCharacterBookOverviewRender('player_inventory_sync');" in play


def test_combat_quick_spells_enrich_selected_names_from_spell_library_for_roll_cards():
    src = _read('client/templates/play.html')
    assert 'function _combatQuickSpellLibraryCardFromName(nameOrId)' in src
    assert 'function _combatQuickNormalizeSpellCard(raw, fallback = {})' in src
    assert "_currentSpellSelectionNames(_charSheet).forEach((name, idx) =>" in src
    assert "addSpellCard(_combatQuickNormalizeSpellCard(libraryCard, { name, source: 'Selected spell state' })" in src
    assert 'damage_upcast_per_level: perSlotFormula' in src
    assert 'save_ability: saveAbility' in src
    assert 'attack_bonus: row.attack_bonus || row.attackBonus || _charSheet?.spellAttack' in src
    assert 'card: normalizedCard' in src


def test_combat_quick_spells_parse_leveled_spell_text_for_quick_actions():
    play = _read('client/templates/play.html')
    selectors = _read('client/static/js/character/combat_quick_selectors.js')
    assert 'function _combatQuickResolveSpellLevel(row, fallback = {})' in play
    assert "row?.level_school, row?.levelSchool, row?.section" in play
    assert 'const resolvedLevel = _combatQuickResolveSpellLevel(raw || {}, meta || {});' in play
    assert ('level: _combatQuickResolveSpellLevel(normalizedCard, card || {})' in play or
            'level: resolvedLevel,' in play), \
        "play.html must resolve spell level in _getCombatQuickSpells"
    assert 'function _parseSpellLevelText()' in selectors
    assert 'const fromText = _parseSpellLevelText(levelText);' in selectors
    assert 'const fromOptions = _baseLevelFromCastOptions((card && card.cast_options) || (spell && spell.cast_options));' in selectors


def test_combat_quick_actions_open_modal_flows_instead_of_immediate_spell_cast():
    play = _read('client/templates/play.html')
    bar = _read('client/static/js/character/combat_quick_bar.js')
    actions = _read('client/static/js/character/combat_quick_actions.js')
    actions_idx = play.index('/static/js/character/combat_quick_actions.js')
    selectors_idx = play.index('/static/js/character/combat_quick_selectors.js')
    assert actions_idx < selectors_idx
    assert 'return window.CombatQuickActions.openSpellAction(spell);' in play
    assert 'openCombatQuickBarWeaponAction(action)' in bar
    assert 'data-cqa-cast' in actions
    assert 'data-cqa-spell-attack' in actions
    assert 'data-cqa-spell-damage' in actions
    assert 'data-cqa-spell-save' in actions
    assert 'data-cqa-weapon-attack' in actions
    assert 'data-cqa-weapon-damage' in actions
    assert 'data-cqa-weapon-crit' in actions


def test_combat_quick_spell_level_missing_data_is_unknown_not_cantrip():
    play = _read('client/templates/play.html')
    selectors = _read('client/static/js/character/combat_quick_selectors.js')
    assert 'Unknown spell level' in play
    assert 'Unknown spell level' in selectors
    assert 'return null;' in selectors
    assert "spellLevel === null ? 'Unknown spell level'" in play
    assert "console.warn('[CombatQuickActions] Spell metadata missing; showing safe fallback.'" in play
    assert 'level_unknown: true' in play


def test_combat_quick_bar_resizes_downward_and_persists_height():
    src = _read('client/static/js/character/combat_quick_bar.js')
    assert 'convert the default bottom anchor' in src
    assert "root.style.top = Math.max" in src
    assert "root.style.height = Math.max(140, Math.min(global.innerHeight * 0.85" in src
    assert "root.style.maxHeight = Math.max(120" not in src


def test_quick_spell_and_weapon_damage_have_fallbacks_for_roll_buttons():
    play = _read('client/templates/play.html')
    assert 'function _combatQuickFallbackSpellDamage(name, slotLevel)' in play
    assert "'fireball': { level: 3, formula: '8d6'" in play
    assert "dmgExpr = _combatQuickFallbackSpellDamage" in play
    assert "const _cardHasDamage = (card) => !!String(card?.damage_formula || card?.base_damage_formula || card?.damage || '').trim();" in play
    assert "if (!_cardHasDamage(combined[existingIdx]) && _cardHasDamage(card))" in play
    assert "Equip it from inventory or add damage dice in the item library" in play


def test_combat_quick_spell_upcast_options_scale_damage_by_slot_level():
    play = _read('client/templates/play.html')
    assert 'function _combatQuickScaleSpellFormula(baseFormula, perSlotFormula, extraLevels)' in play
    assert 'for (let castLevel = level + 1; castLevel <= 9; castLevel += 1)' in play
    assert 'formula: _combatQuickScaleSpellFormula(baseFormula, perSlotFormula, castLevel - level)' in play
    assert 'const exactCastOption = card.cast_options && card.cast_options[String(effectiveSlot)];' in play
    assert 'let dmgExpr = exactCastOption?.formula' in play
    assert 'if (!exactCastOption && baseLevel > 0 && effectiveSlot > baseLevel)' in play


def test_quick_weapon_rolls_use_safe_context_and_modal_damage_formula():
    play = _read('client/templates/play.html')
    actions = _read('client/static/js/character/combat_quick_actions.js')
    assert 'function getSafeRollContext()' in play
    assert 'window.getSafeRollContext = getSafeRollContext;' in play
    assert 'function normalizeWeaponDamage(action, item)' in play
    assert 'const displayedFormula = normalizeWeaponDamage(card, card) || damageMeta.formula;' in play
    assert 'const rollFormula = critical ? _combatQuickCriticalFormula(displayedFormula) : displayedFormula;' in play
    assert 'roll_context: context' in play
    assert 'formulaUsed: `1d20${bonusStr}`' in play
    assert 'vs ${context.targetName || \'No target\'}' in play
    assert 'displayDamageFormula = normalizeWeaponDamage(card, card)' in actions
    assert 'safeWeaponDamage(Object.assign({}, card, { damage_formula: displayDamageFormula' in actions
    assert 'Could not roll \' + (card.name || \'weapon\') + \' damage: missing roll formula' in actions


def test_quick_weapon_modal_accepts_staff_like_items_and_magic_actions():
    actions = _read('client/static/js/character/combat_quick_actions.js')
    assert "if (actionOrId && typeof actionOrId === 'object') return actionOrId;" in actions
    assert "['Used This Turn', usedThisTurn ? 'Yes' : 'No']" in actions
    assert '<strong>Magic Item Actions</strong>' in actions
    assert 'data-cqa-related-roll="attack"' in actions
    assert 'data-cqa-related-roll="damage"' in actions
    assert 'data-cqa-related-roll="save"' in actions
    assert 'Use Charge / Cast' in actions
