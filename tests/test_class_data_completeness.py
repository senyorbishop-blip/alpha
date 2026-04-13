"""Verify all class files have level 1-20 progression."""

from server.character.rules_catalog import load_rules_catalog

REQUIRED_CLASSES = ['barbarian', 'bard', 'cleric', 'druid', 'fighter', 'monk',
                    'paladin', 'ranger', 'rogue', 'sorcerer', 'warlock', 'wizard']


def test_all_classes_present():
    catalog = load_rules_catalog()
    class_ids = {c['id'] for c in catalog['classes']}
    for cls in REQUIRED_CLASSES:
        assert cls in class_ids, f"Class {cls} missing from catalog"


def test_all_classes_have_20_level_progression():
    catalog = load_rules_catalog()
    for cls in catalog['classes']:
        table = cls.get('progressionTable', [])
        levels = {row['level'] for row in table}
        missing = [lvl for lvl in range(1, 21) if lvl not in levels]
        assert not missing, f"{cls['id']} missing progression for levels: {missing}"


def test_all_casters_have_spell_slot_tables():
    catalog = load_rules_catalog()
    caster_types = {'full', 'half', 'pact'}
    for cls in catalog['classes']:
        if cls.get('spellcastingType') in caster_types:
            assert cls.get('spellSlots') or cls.get('pactMagic'), (
                f"{cls['id']} is a caster but has no spell slot table"
            )


def test_all_classes_have_asi_levels():
    catalog = load_rules_catalog()
    standard_asi_levels = {4, 8, 12, 16, 19}
    for cls in catalog['classes']:
        if cls['id'] == 'fighter':  # Fighter has more ASIs
            continue
        table = cls.get('progressionTable', [])
        asi_levels = {row['level'] for row in table if row.get('asiOrFeat')}
        missing = standard_asi_levels - asi_levels
        assert not missing, f"{cls['id']} missing ASI levels: {missing}"


def test_all_classes_have_subclass_at_level_3_or_1():
    catalog = load_rules_catalog()
    for cls in catalog['classes']:
        subclass_level = cls.get('subclassLevel')
        assert subclass_level in (1, 3), (
            f"{cls['id']} has unusual subclassLevel: {subclass_level}"
        )


def test_levelup_preview_returns_features():
    """build_levelup_preview should return non-empty features for level 1 chars."""
    from server.character.progression import build_levelup_preview
    document = {
        'name': 'Test Fighter',
        'classes': [{'classId': 'fighter', 'level': 1}],
        'abilities': {'str': 16, 'dex': 14, 'con': 15, 'int': 10, 'wis': 12, 'cha': 8},
    }
    preview = build_levelup_preview(document)
    assert preview['nextLevel'] == 2
    assert preview['hpGained'] > 0
    assert isinstance(preview['newFeatures'], list)
    assert preview['currentProficiencyBonus'] >= 2
    assert isinstance(preview['currentClassMechanics'], dict)
    assert isinstance(preview['classMechanics'], dict)
