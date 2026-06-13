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
