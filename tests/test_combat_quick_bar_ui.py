from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAY_HTML = ROOT / "client" / "templates" / "play.html"
SELECTORS_JS = ROOT / "client" / "static" / "js" / "character" / "combat_quick_selectors.js"
BAR_JS = ROOT / "client" / "static" / "js" / "character" / "combat_quick_bar.js"
BAR_CSS = ROOT / "client" / "static" / "css" / "combat-quick-bar.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_play_html_loads_combat_quick_bar_after_live_character_actions():
    src = _read(PLAY_HTML)
    actions_idx = src.index('/static/js/character/tabs/actions_tab.js')
    container_idx = src.index('/static/js/character/character_sheet_container.js')
    bridge_idx = src.index('window.CombatQuickRuntime')
    selectors_idx = src.index('/static/js/character/combat_quick_selectors.js')
    bar_idx = src.index('/static/js/character/combat_quick_bar.js')

    assert '/static/css/combat-quick-bar.css' in src
    assert bridge_idx < selectors_idx
    assert actions_idx < container_idx < selectors_idx < bar_idx


def test_combat_quick_runtime_bridge_keeps_play_html_as_state_owner():
    src = _read(PLAY_HTML)
    assert 'getCombat: () => _combat' in src
    assert 'getCharSheet: () => _charSheet' in src
    assert 'getTokens: () => tokens' in src
    assert 'getRole: () => ROLE' in src


def test_combat_quick_selectors_reuse_existing_action_and_spell_helpers():
    src = _read(SELECTORS_JS)
    assert 'selectCombatQuickActions' in src
    assert 'env.getPlayerActionsSections' in src
    assert 'env.getCombatQuickSpells' in src
    assert 'env.getSpellSlotRemaining' in src
    assert 'env.evaluateActionAvailability' in src
    assert 'primaryActions' in src
    assert 'bonusActions' in src
    assert 'reactions' in src
    assert 'topSpells' in src
    assert 'resources' in src
    assert 'concentration' in src


def test_combat_quick_bar_is_draggable_toggleable_and_uses_existing_runtime_actions():
    src = _read(BAR_JS)
    assert 'toggleCombatQuickBar' in src
    assert 'mousedown' in src and 'touchstart' in src
    assert 'localStorage' in src
    assert 'combatQuickCastSpell' in src
    assert 'playerUseAction' in src
    assert 'openCharacterBook' in src
    assert '_patchRenderCombat' in src


def test_combat_quick_bar_css_defines_visual_states():
    src = _read(BAR_CSS)
    for token in [
        '.combat-quick-bar',
        '.combat-quick-bar-toggle',
        '.state-used-this-turn',
        '.state-out-of-uses',
        '.state-needs-target',
        '.state-needs-spell-slot',
        '.state-concentration-active',
    ]:
        assert token in src


def test_combat_quick_selectors_cover_bard_fighter_monk_and_no_spell_clutter_cases():
    src = _read(SELECTORS_JS)
    assert 'bardic inspiration' in src.lower()
    assert 'action surge' in src.lower()
    assert 'martial arts' in src.lower()
    assert 'ki' in src.lower()
    assert '_spellHasUsefulRoll' in src
    assert 'filter(function (spell)' in src
