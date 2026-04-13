from pathlib import Path


def _play_html() -> str:
    return Path('client/templates/play.html').read_text(encoding='utf-8')


def test_player_quick_summary_includes_state_panel_mount():
    src = _play_html()
    assert 'id="char-state-panel"' in src
    assert 'class="char-state-panel"' in src


def test_player_state_panel_renders_core_status_sections():
    src = _play_html()
    assert 'function renderPlayerStatePanel()' in src
    assert 'Conditions' in src
    assert 'Temporary Effects' in src
    assert 'Spell Slots' in src
    assert 'Class Resources' in src
    assert 'Death Saves:' in src
    assert 'Concentrating' in src


def test_player_state_panel_supports_quick_spell_slot_adjustment():
    src = _play_html()
    assert 'function adjustSpellSlotQuick(level, delta)' in src
    assert "adjustSpellSlotQuick('" in src
