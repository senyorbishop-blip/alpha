from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_class_feature_templates_include_target_core_features():
    src = _play_html()
    assert 'const CLASS_FEATURE_TEMPLATES = {' in src
    for snippet in [
        "{ key: 'rage'",
        "{ key: 'ki'",
        "{ key: 'sorcery_points'",
        "{ key: 'bardic_inspiration'",
        "{ key: 'wild_shape'",
        "{ key: 'action_surge'",
        "{ key: 'second_wind'",
        "{ key: 'channel_divinity'",
    ]:
        assert snippet in src


def test_subclass_feature_hooks_are_present_for_supported_architecture():
    src = _play_html()
    assert 'const SUBCLASS_FEATURE_HOOKS = {' in src
    assert "'battle master'" in src
    assert "'college of lore'" in src
    assert "'way of shadow'" in src


def test_structured_class_features_are_synchronized_into_character_sheet_state():
    src = _play_html()
    assert '_charSheet.classFeatures = _getStructuredClassFeatures();' in src
    assert 'if (!_charSheet.classFeatureUses || typeof _charSheet.classFeatureUses !== \'object\') _charSheet.classFeatureUses = {};' in src
    assert 'const allowedFeatureKeys = new Set((_charSheet.classFeatures || []).map(feature => String(feature?.key || \'\')).filter(Boolean));' in src
    assert 'const minLevel = _safeCharacterLevel(tpl?.minLevel, 0);' in src
    assert 'if (minLevel > 0 && classLevel > 0 && classLevel < minLevel) return;' in src
    assert 'const nativeClassFeatures = Array.isArray(_charSheet?.nativeClassFeatures)' in src
    assert 'nativeClassFeatures.forEach((row, featureIndex) => {' in src
    assert "description: String(nativeMatch?.description || tpl.description || '').trim()," in src


def test_player_state_panel_renders_structured_class_resources_with_usage_controls():
    src = _play_html()
    assert 'const structuredClassFeatures = _getStructuredClassFeatures();' in src
    assert 'const structuredResourceFeatures = structuredClassFeatures' in src
    assert "onclick=\"adjustClassFeatureUse('" in src
    assert 'No class resource totals found yet. Add entries like “Rage 2/3” in Character Book actions/features.' in src


def test_player_actions_hub_includes_structured_class_feature_actions_and_resource_state():
    src = _play_html()
    assert "source: 'class_feature'" in src
    assert 'if (src === \'class_feature\' && picked.key) adjustClassFeatureUse(picked.key, 1);' in src
    assert 'resource: state ? `${state.summary}${state.max > 0 ? \' uses\' : \'\'}` : (feature.resourceName || \'' in src


def test_character_book_level_derived_progression_helpers_are_present():
    src = _play_html()
    assert "const levelEl = document.getElementById('cb-level');" in src
    assert "const derivedProf = level > 0 ? Math.ceil(level / 4) + 1 : 0;" in src
    assert "profEl.dataset.autoDerivedValue = String(derivedProf);" in src
    assert "hitDiceEl.value = `${level}d${die}`;" in src


def test_mobile_layout_has_large_class_resource_chips():
    src = _play_html()
    assert '.char-state-chip.resource { width: 100%; justify-content: space-between; flex-wrap: wrap; row-gap: 0.2rem; }' in src
