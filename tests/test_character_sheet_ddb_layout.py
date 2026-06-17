from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = (ROOT / 'client/static/js/character/character_sheet_container.js').read_text(encoding='utf-8')
ACTIONS = (ROOT / 'client/static/js/character/tabs/actions_tab.js').read_text(encoding='utf-8')
SPELLS = (ROOT / 'client/static/js/character/tabs/spells_tab.js').read_text(encoding='utf-8')
FEATURES = (ROOT / 'client/static/js/character/tabs/features_tab.js').read_text(encoding='utf-8')
CSS = (ROOT / 'client/static/css/character-sheet-premium.css').read_text(encoding='utf-8')


def test_sheet_header_renders_core_identity_and_rest_controls():
    for text in ['portraitUrl', 'cs-hero-name', 'speciesLine', 'classLine', 'Level ', 'XP ', 'Campaign ', 'Short Rest', 'Long Rest', 'Manage/Edit']:
        assert text in SHEET


def test_character_sheet_resolves_portraits_from_expected_sources():
    assert 'function resolveCharacterPortrait(characterRuntime, characterDocument, tokenData)' in SHEET
    assert 'identity.portraitUrl' in SHEET
    assert 'runtime.avatarUrl' in SHEET
    assert "['rawSnapshot', 'decorations', 'avatarUrl']" in SHEET
    assert 'book.avatarUrl' in SHEET
    assert 'token.image_url' in SHEET
    assert "'/static/importer/portraits/class/'" in SHEET
    assert "source: explicit ? 'explicit'" in SHEET
    assert 'global.resolveCharacterPortrait = resolveCharacterPortrait' in SHEET


def test_character_sheet_header_renders_image_with_initials_fallback_and_single_warning():
    assert 'class="cs-portrait-img"' in SHEET
    assert 'data-portrait-url' in SHEET
    assert 'cs-portrait-initials' in SHEET
    assert "frame.classList.add('image-failed')" in SHEET
    assert 'img.dataset.warned' in SHEET
    assert "console.warn('[character-sheet] Portrait failed to load; showing initials fallback.'" in SHEET
    assert 'img.removeAttribute(\'src\')' in SHEET


def test_tab_labels_render_without_visible_count_badges_and_keep_count_data():
    assert 'const count = _tabCount(tab.id, charData || {});' in SHEET
    assert "btn.setAttribute('data-tab-count', count || '');" in SHEET
    assert '<span class="cs-tab-count">' not in SHEET
    for label in ['Actions', 'Spells', 'Inventory', 'Features & Traits', 'Background', 'Notes', 'Extras']:
        assert f'label: \'{label}\'' in SHEET
    assert '.cs-tab-count {' in CSS
    assert 'display: none;' in CSS


def test_active_tab_and_keyboard_navigation_still_change_tabs():
    assert "btn.classList.toggle('active', isActive);" in SHEET
    assert "btn.setAttribute('aria-selected', isActive ? 'true' : 'false');" in SHEET
    assert "tabBar.setAttribute('role', 'tablist');" in SHEET
    assert "btn.setAttribute('role', 'tab');" in SHEET
    assert "if (e.key === 'ArrowRight')" in SHEET
    assert "if (e.key === 'ArrowLeft')" in SHEET
    assert 'btns[next].click();' in SHEET


def test_stat_cards_render_all_six_abilities_with_save_data():
    for ability in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
        assert ability in SHEET
    assert 'cs-ddb-stat-card' in SHEET
    assert 'cs-ddb-save-dot' in SHEET
    assert 'Save ' in SHEET


def test_saves_skills_and_left_column_sections_render():
    for text in ['Saving Throws', 'Skills', 'Passive Scores', 'Senses', 'Armor & Equipped Weapons', 'Proficiencies & Languages', 'Class Resources']:
        assert text in SHEET


def test_actions_tab_groups_economy_and_limited_use_filters():
    for text in ['All</button>', 'Attack</button>', 'Action</button>', 'Bonus Action</button>', 'Reaction</button>', 'Other</button>', 'Limited Use</button>', 'Attacks per Action']:
        assert text in ACTIONS


def test_spells_tab_surfaces_dc_attack_slots_rows_and_upcast_formula():
    for text in ['Spell Save DC', 'Spell Attack', 'cs-slots-row', 'CANTRIP', '9TH', '_spellRollExpressionForLevel', 'Casting Time', 'Components']:
        assert text in SPELLS


def test_features_traits_groups_and_filters_all_requested_sources():
    for text in ['Class Features', 'Subclass Features', 'Species Traits', 'Feats', 'Background Features', 'Item Traits', 'Passive', 'Bonus Action', 'Limited Use', 'Background</div>', 'Items</div>']:
        assert text in FEATURES


def test_sorcerer_resource_controls_have_font_and_metamagic_language():
    for text in ['Sorcery Points', 'Font of Magic', 'Metamagic', 'Quickened', 'Subtle', 'Seeking', 'Heightened']:
        assert text in (ACTIONS + FEATURES + SPELLS)


def test_imported_features_needs_review_readable_and_dedupe_hooks_exist():
    assert 'Needs Review' in FEATURES or 'needsReview' in FEATURES
    assert '_dedupeFeatures' in FEATURES
    assert '_dedupeActionBucket' in ACTIONS
    assert '_dedupeSpellCards' in SPELLS or 'new Set' in SPELLS


def test_scroll_and_responsive_modes_are_single_panel_readable():
    for text in ['cs-ddb-body', 'cs-ddb-left-column', 'cs-ddb-main-panel', '@media (max-width: 980px)', 'overflow:auto']:
        assert text in CSS
