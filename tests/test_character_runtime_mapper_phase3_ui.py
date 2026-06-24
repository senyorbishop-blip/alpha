from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_mapper_wires_phase3_action_and_spell_surfaces_without_levelup_work():
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "out.nativeActionCards" in src
    assert "out.nativePassives" in src
    assert "out.rulesSpellbook = mergeSpellCards(out.rulesSpellbook, runtimeSpellCards);" in src
    assert "out.spellSlots = formatSpellSlotLines(slots);" in src
    assert "out.spellAbility = spellAbility;" in src
    assert "out.spellSaveDc = String(asInt(spellAccess.saveDc" in src
    assert "out.spellAttack = signed(spellAccess.attackBonus);" in src
    assert "out.actions = actionLines.filter(Boolean).join('\\n');" in src
    assert "out.features = runtimePassives.map(buildPassiveLine).filter(Boolean).join('\\n');" in src
    assert "out.spells = known.map(function mapKnown(name)" in src


def test_mapper_normalizes_structured_spells_object_from_python_charbook():
    """nativeToLegacyCharBook must convert the Python-format {known,prepared,slots} spell
    object to a plain-text string so the Magic tab textarea never shows raw JSON."""
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    # The else-branch must guard against non-array objects only
    assert "!Array.isArray(out.spells)" in src
    # The normalization reads the known list via asArray(spellsObj.known)
    assert "asArray(spellsObj.known)" in src
    # The helper function must be used for name extraction
    assert "extractSpellName" in src
    # The result must be joined into a newline-separated string
    assert "filter(Boolean).join('\\n')" in src


def test_mapper_extracts_saving_throws_from_runtime_combat():
    """nativeToLegacyCharBook must populate out.savingThrows from runtime.combat.savingThrows
    when no user-entered values are already present (fixes empty Skills tab)."""
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "combatData.savingThrows" in src
    assert "abilityKeyToFullName" in src
    assert "out.savingThrows = computedSaves" in src


def test_mapper_builds_native_skills_when_book_skills_missing():
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "function buildNativeSkillMap(doc, runtime)" in src
    assert "var SKILL_TO_ABILITY" in src
    assert "out.skills = buildNativeSkillMap(doc, runtime);" in src


def test_mapper_rebuilds_runtime_hp_from_canonical_sources_before_mapping():
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "function rebuildRuntimeHp(nativeCharacter, nativeRuntime, fallback)" in src
    assert "includeRuntime: false" in src
    assert "var runtimeWithCanonicalHp = rebuildRuntimeHp(nativeCharacter, nativeRuntime" in src
    assert "out.charSheet = nativeToLegacyCharSheet(nativeCharacter, runtimeWithCanonicalHp, source.charSheet);" in src
    assert "out.charBook = nativeToLegacyCharBook(nativeCharacter, runtimeWithCanonicalHp, source.charBook);" in src


def test_mapper_overrides_gear_with_native_equipment_lines():
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "function buildNativeGearLines(doc)" in src
    assert "equipment.inventory" in src
    assert "equipment.equipped" in src
    assert "out.gear = buildNativeGearLines(doc);" in src


def test_mapper_does_not_overwrite_existing_user_saving_throws():
    """When the charBook already has saving throws, runtime computed values must NOT overwrite them."""
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    # Guard clause: only populate if no existing saves are present
    assert "hasExistingSaves" in src
    assert "!hasExistingSaves" in src


def test_extract_spell_name_helper_exists_in_mapper():
    """A dedicated extractSpellName helper must exist to reduce duplicated
    name-extraction logic across the spell normalization code paths."""
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "function extractSpellName(entry)" in src


def test_mapper_prefers_richer_spell_cards_over_stale_existing_spell_cards():
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "function spellCardAutomationScore(card)" in src
    assert "spellCardAutomationScore(card) >= spellCardAutomationScore(existing)" in src


def test_play_html_normalize_book_text_handles_spell_object_structure():
    """normalizeBookText in play.html must convert {known, prepared} objects to readable
    text instead of falling through to JSON.stringify."""
    src = _read("client/templates/play.html")
    # Must check for Array.isArray(value.known) before calling JSON.stringify
    assert "Array.isArray(value.known)" in src
    # The JSON.stringify fallback must still exist but only reached after the known check
    known_idx = src.find("Array.isArray(value.known)")
    stringify_idx = src.find("return JSON.stringify(value, null, 2);", known_idx)
    assert known_idx != -1 and stringify_idx != -1, (
        "Array.isArray(value.known) check must appear before JSON.stringify fallback"
    )


def test_play_html_normalize_book_text_handles_object_items_in_arrays():
    """normalizeBookText must handle array items that are objects (e.g. feat objects)
    by extracting the name/label property instead of returning '[object Object]'."""
    src = _read("client/templates/play.html")
    # The array branch must check for object items
    assert "item.name || item.label || item.id" in src


def test_mapper_exposes_native_resources_and_class_features_for_charbook_and_sheet():
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "out.nativeResources" in src
    assert "out.nativeClassFeatures" in src
    assert "runtime.resources" in src
    assert "runtime.classFeatures" in src


def test_play_html_wires_native_character_book_panels():
    src = _read("client/templates/play.html")
    assert "cb-native-actioncards" in src
    assert "cb-native-resources" in src
    assert "cb-native-features" in src
    assert "function renderNativeCharacterBookPanels()" in src
    assert "function _getNativeCharacterBookActionCards()" in src
    assert "function _getNativeCharacterBookResources()" in src
    assert "function _getNativeCharacterBookFeatures()" in src
    assert "rollNativeActionAttack" in src
    assert "rollNativeActionDamage" in src


def test_play_html_premium_character_book_summary_and_bucket_layout_exists():
    src = _read("client/templates/play.html")
    assert "cb-action-kpis" in src
    assert "cb-magic-kpis" in src
    assert "function _renderCharacterBookKpiCard(label, value, note = '') {" in src
    assert "function _updateCharacterBookPremiumKpis(opts = {}) {" in src
    assert "sheet-book-bucket-title" in src
    assert "rules-card-grid-2" in src


def test_play_html_native_action_resolution_supports_costs_healing_and_save_cards():
    src = _read("client/templates/play.html")
    assert "function _nativeActionResourceCost(card, linkedResource = null)" in src
    assert "function _nativeActionLooksLikeHealing(card)" in src
    assert "function _nativeActionSaveMeta(card)" in src
    assert "function _resolveNativeActionCard(card, opts = {})" in src
    assert "adjustCharHp(Math.max(0, healResult.total || 0))" in src
    assert "saveDC: saveMeta.saveDC" in src
    assert "Resolve / Roll" in src


def test_play_html_native_actions_can_apply_damage_and_healing_to_selected_targets():
    src = _read("client/templates/play.html")
    assert "function _nativeActionSelectedTarget()" in src
    assert "function _canApplyNativeActionToToken(token)" in src
    assert "function _applyNativeActionToToken(token, amount, kind = 'damage')" in src
    assert "sendWS({ type: 'token_hp_update', payload: { token_id: token.id, hp, max_hp: maxHp } });" in src
    assert "sendWS({ type: 'token_edit', payload: { token_id: token.id, tempHp } });" in src
    assert "applied to ${resolution.targetName || 'target'}" in src
    assert "needs DM/owner confirmation" in src



def test_play_html_spellcasting_stage_supports_slot_consumption_and_concentration_tracking():
    src = _read("client/templates/play.html")
    assert "function _consumeSpellSlotLevel(slotLevel)" in src
    assert "function _clearActiveSpellConcentration(reason = '')" in src
    assert "function _startActiveSpellConcentration(spellName)" in src
    assert "function _rollSpellFormula(card, expr, kind = 'damage', opts = {})" in src
    assert "Concentration active" in src
    assert "needs DM/owner confirmation" in src


def test_play_html_cast_rules_spell_routes_through_unified_spell_executor():
    src = _read("client/templates/play.html")
    assert "function castRulesSpell(spellId) {" in src
    assert "_executeCombatSpellCast({" in src
    assert "source: 'rules'" in src
    assert "renderRulesSpellbook();" in src


def test_play_html_local_preview_rolls_queue_authoritative_results_until_3d_dice_are_ready():
    src = _read("client/templates/play.html")
    assert "const _pendingLocalDiceResults = new Map();" in src
    assert "function _queuePendingLocalDiceResult(meta) {" in src
    assert "function _tryApplyPendingLocalDiceResult(rollId = '') {" in src
    assert "const previewMeta = _startLocalDicePreview(diceType, qty, `spell-${kind}`);" in src
    assert "fillDiceResult(Array.isArray(result.rolls) ? result.rolls : [], result.total, diceType, qty, modifier, label, previewMeta);" in src
    assert "localPreviewRoll && _queuePendingLocalDiceResult({" in src
    assert "_logDiceLifecycle('local_result_synced'" in src


def test_play_html_legacy_combat_rolls_use_synced_local_preview_bridge():
    src = _read("client/templates/play.html")
    assert "function _dicePreviewMetaFromExpr(expr, result = null) {" in src
    assert "function _showLegacySyncedLocalDiceResult(opts = {}) {" in src
    assert "opts?.source || 'legacy-local'" in src
    assert "legacy-monster-attack" in src
    assert "legacy-monster-save" in src
    assert "legacy-monster-damage" in src
    assert "legacy-combat-weapon-damage" in src
    assert "legacy-combat-spell-damage" in src
    assert "legacy-combat-custom-damage" in src
    assert "legacy-bestiary-attack" in src


def test_play_html_generates_quick_attack_cards_from_equipped_inventory_weapons():
    src = _read("client/templates/play.html")
    assert "function _abilityModFromCharacterSheet(abilityKey) {" in src
    assert "function _proficiencyBonusFromCharacterSheet() {" in src
    assert "function _buildEquippedInventoryAttackCard(item, idx, slot = '') {" in src
    assert "function _getEquippedInventoryAttackCards() {" in src
    assert "function _getUnifiedQuickAttackCards() {" in src
    assert "Generated from equipped inventory" in src
    assert "source === 'equip_only'" in src
    assert "src === 'weapon' || src === 'equip_only'" in src


def test_play_html_equipment_attack_rules_cover_versatile_offhand_and_ammo_logic():
    src = _read("client/templates/play.html")
    assert "function _formatInventoryWeaponDamageFormula(dice, abilityMod = 0, includeAbilityMod = true) {" in src
    assert "function _findMatchingAmmoInventoryEntry(ammoKind = '') {" in src
    assert "function _consumeInventoryAttackResources(card, mode = 'base') {" in src
    assert "function _canUseVersatileAttackMode(card) {" in src
    assert "function _getInventoryAttackModeMeta(card, mode = 'base') {" in src
    assert "off-hand (no ability mod to damage)" in src
    assert "Consumed 1 ammunition." in src
    assert "Thrown weapon consumed from stack." in src
    assert "rollRulesAttackDamageMode(attackId, mode = 'base')" in src
    assert "combatQuickWeaponAttack(attackId, mode = 'base')" in src
    assert "Versatile" in src
    assert "Throw" in src


def test_play_html_weapon_mastery_and_special_property_automation_exist_for_equipped_attacks():
    src = _read("client/templates/play.html")
    assert "function _inventoryWeaponMasteryId(item, properties = []) {" in src
    assert "function _inventoryWeaponMasteryRulesText(masteryId = '') {" in src
    assert "function _inventoryWeaponPropertyAutomationSummary(item, properties = []) {" in src
    assert "function _canUseLoadingWeaponThisTurn(card) {" in src
    assert "function _applyInventoryWeaponMastery(card, target, outcome = 'hit') {" in src
    assert "Loading weapon already fired this turn." in src
    assert "Topple applied: target is prone." in src
    assert "Push applied: target moved 10 ft." in src
    assert "<strong>Mastery</strong>" in src
    assert "Mastery ${masteryLabel}" in src


def test_play_html_stage13_workbench_ui_flow_exists_for_character_book_rework():
    src = _read("client/templates/play.html")
    assert "sheet-workflow-strip" in src
    assert "Character Sheet" in src
    assert "Notes" in src
    assert "Spells / Features" in src
    assert "sheet-workflow-strip" in src


def test_character_sheet_runtime_stage13_renders_testing_workbench_cards_and_blockers():
    src = _read("client/static/js/character/runtime/character_sheet_runtime.js")
    assert "Needs Attention" in src
    assert "Quick Jump" in src
    assert "Quick Access" in src
    assert "Details need setup" in src
    assert "Open the main sheet view" in src


def test_play_html_stage14_opens_flagship_sheet_after_import_and_from_main_toggle():
    src = _read("client/templates/play.html")
    assert "openCharacterBook('premiumsheet')" in src
    assert "goCharacterBookPage('premiumsheet', true);" in src


def test_stage15_flagship_sheet_surface_exists():
    src = _read("client/static/js/character/character_sheet_container.js")
    assert "Sheet Status" in src
    assert "Ability Scores" in src
    assert "Character Sheet" in src
    assert "function _renderAbilityAudit(charData) {" in src
    assert "function _renderChecklist(charData) {" in src
    assert "function _tabCount(tabId, charData) {" in src
    assert "Traits / Notes" in src
    assert "Magic" in src



def test_character_sheet_container_stage14_builds_flagship_overview_shell():
    src = _read("client/static/js/character/character_sheet_container.js")
    assert "Character Sheet" in src
    assert "id: 'actions'" in src
    assert "id: 'spells'" in src
    assert "id: 'features'" in src
    assert "_activateTab('actions'" in src
    assert "id: 'overview'" not in src



def test_character_sheet_premium_css_stage14_has_flagship_shell_layout_classes():
    src = _read("client/static/css/character-sheet-premium.css")
    assert ".cs-flagship-shell" in src
    assert ".cs-flagship-header" in src
    assert ".cs-summary-grid" in src
    assert ".cs-launch-btn" in src
    assert ".cs-overview-columns" in src
    assert ".cs-status-chip.good" in src



def test_premium_sheet_detail_drawer_hooks_exist():
    src = Path('client/static/js/character/character_sheet_container.js').read_text()
    assert 'openDetailDrawer' in src
    assert 'cs-detail-overlay' in src


def test_actions_tab_stage17_uses_structured_quick_attacks_native_actions_and_resources():
    src = _read("client/static/js/character/tabs/actions_tab.js")
    assert "function _buildQuickAttackCards(charData) {" in src
    assert "function _nativeActionGroups(charData) {" in src
    assert "function _renderResourceSection(resources) {" in src
    assert "Tracked Resources" in src
    assert "Quick Attacks" in src
    assert "Imported / Legacy Attack Lines" in src
    assert "combatCardId" in src
    assert "_summonActionRuntimeSupported" in src


def test_spells_tab_stage17_shows_linked_spell_actions_and_library_together():
    src = _read("client/static/js/character/tabs/spells_tab.js")
    assert "function _normalizeLinkedSpellCards(charData) {" in src
    assert "function _renderStructuredSpellSection(spells, concentrationName) {" in src
    assert "Linked Spell Actions" in src
    assert "Spell Library" in src
    assert "Spell flow" in src
    assert "Concentration status" in src


def test_character_sheet_container_hides_detail_drawer_when_hidden_and_binds_close_button_directly():
    src = _read("client/static/js/character/character_sheet_container.js")
    css = _read("client/static/css/character-sheet-premium.css")
    assert "overlay.__csBound" in src
    assert "closeBtn.addEventListener('click'" in src
    assert "overlay.addEventListener('click'" in src
    assert ".cs-detail-overlay[hidden]" in css
    assert "display: none !important;" in css


def test_features_tab_stage18_renders_traits_build_and_inspect_buttons():
    src = _read("client/static/js/character/tabs/features_tab.js")
    css = _read("client/static/css/character-sheet-premium.css")
    assert "Features at a Glance" in src
    assert "Class & Subclass Features" in src
    assert "Species Traits" in src
    assert "Character Snapshot" in src
    assert "cs-feature-inspect" in src
    assert "data-feature-inspect" in src
    assert "cs-traits-summary-grid" in css
    assert "cs-build-note-grid" in css


def test_player_facing_character_surfaces_avoid_testing_audit_wording():
    files = [
        "client/static/js/character/character_sheet_container.js",
        "client/static/js/character/tabs/actions_tab.js",
        "client/static/js/character/tabs/features_tab.js",
        "client/static/js/character/tabs/spells_tab.js",
    ]
    banned_phrases = [
        "during testing",
        "Concentration audit",
        "audit point",
    ]
    for path in files:
        src = _read(path)
        for phrase in banned_phrases:
            assert phrase not in src


def test_features_tab_stage19_keeps_feature_filters_without_rendering_helper_cards():
    src = _read("client/static/js/character/tabs/features_tab.js")
    css = _read("client/static/css/character-sheet-premium.css")
    assert "Find a Feature" in src
    assert "function _groupFeaturesByLevel(items) {" in src
    assert "data-roadmap-level" in src
    assert "cs-feature-search" in css
    assert "cs-roadmap-grid" in css
    assert "cs-spotlight-grid" in css

    render_template = src[src.index("container.innerHTML = `"):src.index("container.__csCharData = charData || {};")]
    assert "Current Features Only" not in render_template
    assert "Current & Next Unlocks" not in render_template
    assert "Level Roadmap" not in render_template
    assert "_renderCurrentFeaturesNote()" not in render_template
    assert "_renderLevelRoadmap(roadmap, level)" not in render_template


def test_features_tab_stage20_adds_class_playbook_and_connected_system_guidance():
    src = _read("client/static/js/character/tabs/features_tab.js")
    assert "const CLASS_PLAYBOOKS = {" in src
    assert "function _renderPlaybook(charData, sections) {" in src
    assert "Class Guide" in src
    assert "Tracked resources" in src
    assert "function _featureConnectedSystems(feature) {" in src
    assert "function _featureTestingGuidance(feature, charData) {" in src
    assert "function _featureWhenItMatters(feature) {" in src
    assert "Best Time to Use It" in src
    assert "How to Use It" in src
    assert "container.__csCharData = charData || {};" in src


def test_premium_sheet_css_has_stage20_playbook_cards():
    src = _read("client/static/css/character-sheet-premium.css")
    assert ".cs-playbook-grid" in src
    assert ".cs-playbook-card.highlight" in src
    assert ".cs-playbook-chip-row" in src


def test_actions_tab_stage21_adds_test_guidance_and_connected_systems_to_combat_drawer():
    src = _read("client/static/js/character/tabs/actions_tab.js")
    assert "function _actionTestingGuidance(action) {" in src
    assert "function _actionConnectedSystems(action) {" in src
    assert "function _actionExpectedResults(action) {" in src
    assert "How to Test This" in src
    assert "Connected Systems" in src
    assert "Expected Results" in src


def test_spells_tab_stage21_adds_test_guidance_and_connected_systems_to_spell_drawer():
    src = _read("client/static/js/character/tabs/spells_tab.js")
    css = _read("client/static/css/character-sheet-premium.css")
    assert "function _spellTestingGuidance(spell) {" in src
    assert "function _spellConnectedSystems(spell) {" in src
    assert "function _spellExpectedResults(spell) {" in src
    assert "function _spellTestingGuidance(spell) {" in src
    assert "function _spellConnectedSystems(spell) {" in src
    assert "function _spellExpectedResults(spell) {" in src
    assert "{ title: 'At a Glance'" in src
    assert "{ title: 'Casting'" in src
    assert "{ title: 'Roll / Effect'" in src
    assert "Click any linked spell or library row to open a clean spell card" in src
    assert ".cs-inline-hint" in css



def test_feature_spell_and_action_inspectors_include_rules_breakdown_coverage_and_blockers():
    actions = _read("client/static/js/character/tabs/actions_tab.js")
    spells = _read("client/static/js/character/tabs/spells_tab.js")
    features = _read("client/static/js/character/tabs/features_tab.js")
    assert "function _actionRulesBreakdown(action) {" in actions
    assert "function _actionAutomationCoverage(action) {" in actions
    assert "function _actionCommonBlockers(action) {" in actions
    assert "{ title: 'Rules Breakdown', items: _actionRulesBreakdown(action) }" in actions
    assert "{ title: 'Automation Coverage', items: _actionAutomationCoverage(action) }" in actions
    assert "{ title: 'Common Blockers', items: _actionCommonBlockers(action) }" in actions
    assert "function _spellRulesBreakdown(spell) {" in spells
    assert "function _spellAutomationCoverage(spell) {" in spells
    assert "function _spellCommonBlockers(spell) {" in spells
    assert "{ title: 'At a Glance'" in spells
    assert "{ title: 'Casting'" in spells
    assert "{ title: 'Roll / Effect'" in spells
    assert "function _featureRulesBreakdown(feature) {" in features
    assert "function _featureAutomationCoverage(feature) {" in features
    assert "function _featureCommonBlockers(feature) {" in features
    assert "function _featureWhenItMatters(feature) {" in features
    assert "{ title: 'At a Glance'" in features
    assert "{ title: 'How to Use It'" in features
    assert "cs-feature-facts" in features


def test_spells_tab_uses_manifest_route_and_dynamic_filter_labels():
    src = _read("client/static/js/character/tabs/spells_tab.js")
    assert "/api/character/' + encodeURIComponent(ctx.profileId) + '/spells?session_id='" in src
    assert "/spells/known?session_id=" in src
    assert "function _availableFilterLabels(state) {" in src
    assert "function _highestAvailableSpellLevel(state) {" in src


def test_features_tab_hides_spell_progression_bookkeeping_rows():
    src = _read("client/static/js/character/tabs/features_tab.js")
    assert "spellcasting progression" in src
    assert "cantrip|spell" in src


def test_mapper_token_mapping_keeps_native_runtime_hp_authoritative_when_present():
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "var hasAuthoritativeRuntimeHp = Number.isFinite(runtimeMaxHp) && runtimeMaxHp > 0;" in src
    assert "var mappedMaxHp = hasAuthoritativeRuntimeHp ? runtimeMaxHp" in src
    assert "var mappedCurrentHp = hasAuthoritativeRuntimeHp" in src
    assert "var mappedTempHp = hasAuthoritativeRuntimeHp" in src


def test_mapper_logs_hp_conflicts_in_dev_without_switching_authority():
    src = _read("client/static/js/character/runtime/mapper_to_play.js")
    assert "function warnHpConflictInDev(scope, canonicalHp, comparisons)" in src
    assert "warnHpConflictInDev('resolveCanonicalHp'" in src
    assert "warnHpConflictInDev('mapCharacterToToken'" in src


def test_play_html_uses_single_canonical_hp_resolver_for_profile_token_and_sidebar_surfaces():
    src = _read("client/templates/play.html")
    assert "function _resolveCanonicalHpFromProfileAndToken(profile, ownedToken, fallback = {}) {" in src
    assert "source: 'nativeRuntime.hp'" in src
    assert "source: 'ownedToken'" in src
    assert "source: 'legacyProfile'" in src
    assert "const canonicalHp = _resolveCanonicalHpFromProfileAndToken(profile, ownedToken" in src
    assert "const canonicalHp = _resolveCanonicalHpFromProfileAndToken(profile, tok" in src
    assert "profile.nativeRuntime.hp.max = canonicalVitals.maxHp;" in src
    assert "profile.charSheet.hp = { max: canonicalVitals.maxHp, current: boundedCur, temp: boundedTemp };" in src
    assert "profile.charBook.maxHp = canonicalVitals.maxHp;" in src


def test_runtime_mapper_uses_structured_spell_access_cards_before_string_fallbacks():
    src = _read('client/static/js/character/runtime/mapper_to_play.js')
    assert 'var accessCards = asArray(spellAccess.cards);' in src
    assert 'accessCards.forEach(function addAccessCard' in src
    assert 'level_unknown: true' in src
    assert 'spellCardAutomationScore(normalized)' in src


def test_combat_quick_spell_normalizer_reads_runtime_roll_config_aliases():
    src = _read('client/templates/play.html')
    assert 'row.rollConfig?.damageFormula' in src
    assert 'row.rollConfig?.attackType' in src
    assert 'row.rollConfig?.saveType' in src
    assert 'row.higherLevelFormula' in src


def test_play_html_spell_upcast_damage_roll_uses_all_scaled_dice():
    src = _read("client/templates/play.html")
    assert "const formulaChunks = typeof _expandSpellFormulaChunks === 'function' ? _expandSpellFormulaChunks(cleaned) : [];" in src
    assert "formulaChunks.reduce((sum, chunk) => sum + (Math.max(1, parseInt(chunk.qty, 10) || 1)), 0)" in src


def test_play_html_weapon_damage_roll_accepts_inventory_damage_fields_and_slug_fallback():
    src = _read("client/templates/play.html")
    assert "card?.damage_formula || card?.base_damage_formula || card?.damage_dice || card?.damage" in src
    assert "item.damage_dice || item.damage_formula || item.base_damage_formula || item.damage || item.versatile_damage" in src
    assert "('attack-' + slug) === normalizedId" in src
