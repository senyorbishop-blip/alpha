from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding='utf-8')


def test_play_page_contains_player_actions_hub_markup_and_renderer():
    src = _read('client/templates/play.html')
    assert 'id="player-actions-hub"' in src
    assert 'function renderPlayerActionsHub()' in src
    assert 'function playerUseAction(source, id)' in src


def test_player_actions_hub_includes_requested_categories_and_spell_markers():
    src = _read('client/templates/play.html')
    assert "['Attacks', 'Bonus Actions', 'Reactions', 'Class Features', 'Spells']" in src
    assert "if (card.concentration || card.is_concentration) badges.push('Concentration');" in src
    assert "if (card.ritual || card.is_ritual) badges.push('Ritual');" in src


def test_player_actions_hub_is_mobile_first():
    src = _read('client/templates/play.html')
    assert '.player-action-use-btn { width: 100%; min-height: 40px; }' in src
    assert '.player-action-meta { grid-template-columns: 1fr; }' in src
