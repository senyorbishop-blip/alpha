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


def test_combat_quick_bar_has_required_player_controls_and_states():
    src = _read('client/static/js/character/combat_quick_bar.js')
    assert 'combat-quick-bar' in src
    assert 'toggleManual' in src
    assert 'pointerdown' in src
    assert 'localStorage' in src
    assert 'Open Full Sheet' in src
    assert 'Used this turn' in src
    assert 'Needs target' in src
    assert 'Needs slot' in src
    assert 'Concentration:' in src
