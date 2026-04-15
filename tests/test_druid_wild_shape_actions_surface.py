from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_actions_tab_wild_shape_updates_combat_profile_and_temp_hp():
    src = _read('client/static/js/character/tabs/actions_tab.js')
    assert 'transformedCombatProfile' in src
    assert 'originalTempHp' in src
    assert 'tempHp: _num(charData && charData.tempHp, 0)' in src


def test_actions_tab_wild_shape_attacks_are_structured_and_routed_to_native_action_use():
    src = _read('client/static/js/character/tabs/actions_tab.js')
    assert 'damageText: damageText' in src
    assert 'save: saveDcText' in src
    assert "source: 'native_action'" in src
    assert 'Wild Shape attacks are currently driving your attack surface.' in src


def test_actions_tab_keeps_unarmed_strike_fallback_on_quick_surface():
    src = _read('client/static/js/character/tabs/actions_tab.js')
    assert 'function _unarmedStrikeCard(charData) {' in src
    assert "push(_unarmedStrikeCard(charData || {}));" in src
    assert 'Default melee strike available even when you have no weapon equipped.' in src
