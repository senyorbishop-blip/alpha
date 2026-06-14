from pathlib import Path

SRC = Path('client/static/js/character/combat_quick_bar.js').read_text()
ACTIONS = Path('client/static/js/character/combat_quick_actions.js').read_text()

def test_quick_actions_hide_uses_dismiss_state_and_reopen():
    assert 'dismissedForCombatTurn' in SRC
    assert 'dismissedUntilManualOpen' in SRC
    assert 'dismissForTurn' in SRC
    assert 'openManual' in SRC
    assert 'combat-quick-bar-toggle' in SRC

def test_minimize_does_not_dismiss_and_close_stops_propagation():
    assert 'state.minimized = !state.minimized' in SRC
    assert 'ev.stopPropagation(); dismissForTurn(); return;' in SRC
    assert "ev.target.closest('button,[data-qb-minimize],[data-qb-hide]')" in SRC

def test_escape_modal_and_empty_state_and_reset_fallback():
    assert "ev.key === 'Escape'" in SRC
    assert 'resetQuickBarVisibility' in SRC
    assert 'Loading quick actions' in SRC
    assert 'No quick actions are available yet' in SRC
    assert 'ev.stopPropagation(); closeModal(); return;' in ACTIONS
