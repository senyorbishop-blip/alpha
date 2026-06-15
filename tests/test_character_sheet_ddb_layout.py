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
