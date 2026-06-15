from server.character.feature_compendium import load_feature_compendium


def test_feature_compendium_loads_expected_core_classes_and_custom_classes():
    compendium = load_feature_compendium()
    for class_id in [
        'barbarian','bard','cleric','druid','fighter','monk','paladin','ranger','rogue','sorcerer','warlock','wizard','tinker','pirate'
    ]:
        rows = compendium.by_class(class_id)
        assert rows, f'{class_id} should have feature compendium rows'
        assert all(row.get('id') and row.get('name') and row.get('kind') for row in rows)


def test_sorcerer_resource_and_metamagic_records_are_structured():
    compendium = load_feature_compendium()
    font = compendium.lookup('Font of Magic')
    quickened = compendium.lookup('Quickened Spell')
    metamagic = compendium.lookup('Metamagic')
    assert font and (font.get('resource_name') or font.get('uses_formula'))
    assert metamagic and metamagic.get('safe_summary')
    assert quickened and quickened.get('action_type') == 'bonus_action'
    assert quickened.get('resource_name') == 'Sorcery Points'
    assert quickened.get('runtime_hooks')


def test_imported_native_duplicate_merges_and_preserves_private_text():
    compendium = load_feature_compendium()
    merged = compendium.merge_imported_feature({
        'id': 'ddb-font-of-magic',
        'name': 'Font of Magic',
        'source': 'D&D Beyond import',
        'description': 'private character import text',
    })
    assert merged.get('name') == 'Font of Magic'
    assert merged.get('kind') == 'class'
    assert 'private_imported_text' in merged


def test_unknown_imported_feature_stays_visible_needs_review_stub():
    compendium = load_feature_compendium()
    merged = compendium.merge_imported_feature({'name': 'Table Custom Moon Trick', 'description': 'private'})
    assert merged.get('needs_review') is True
    assert merged.get('implementation_status') == 'imported_private_stub'
    assert merged.get('safe_summary')
