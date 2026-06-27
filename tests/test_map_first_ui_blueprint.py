from pathlib import Path

BLUEPRINT = Path('docs/ui-map-first-blueprint.md')
TOKENS = Path('client/static/css/map-first-ui-tokens.css')


def _doc() -> str:
    return BLUEPRINT.read_text(encoding='utf-8')


def _tokens() -> str:
    return TOKENS.read_text(encoding='utf-8')


def test_map_first_blueprint_exists_and_sets_main_direction():
    assert BLUEPRINT.exists()
    text = _doc()
    assert 'Map first. Tools appear only when the selected mode needs them.' in text
    assert 'The map should always feel like the table.' in text
    for region in ['Top session bar', 'Left mode rail', 'Centre map stage', 'Right context panel', 'Bottom quick strip']:
        assert region in text


def test_dm_mode_rail_and_context_panel_cover_core_dm_functions():
    text = _doc()
    for mode in ['Run Game', 'Combat', 'Map Build', 'NPC/Monster', 'Loot/Shop', 'Session Tools', 'Viewer Powers', 'Debug']:
        assert mode in text
    for function in ['tokens', 'fog', 'walls', 'doors', 'props', 'lighting/weather', 'bestiary', 'inventory control', 'shops', 'handouts', 'journal', 'narration', 'sound', 'polls', 'save/autosave', 'diagnostics']:
        assert function in text


def test_player_and_viewer_stay_map_first_and_compact():
    text = _doc()
    for phrase in [
        'Player view also stays map-first',
        'compact HUD by default',
        'no giant full width panel unless opened',
        'Quick Actions drawer',
        'character sheet drawer',
        'inventory drawer',
        'spellbook drawer',
        'rest confirmation panel',
        'Viewer view stays map-first and stream friendly',
        'minimal overlay',
        'compact viewer powers panel',
    ]:
        assert phrase in text


def test_debug_and_clutter_are_closed_by_default():
    text = _doc()
    for phrase in ['Debug must be closed by default', 'Debug is closed by default', 'no debug panel', 'The map must remain the largest element']:
        assert phrase in text


def test_map_first_tokens_exist_for_future_ui_work():
    assert TOKENS.exists()
    css = _tokens()
    required_tokens = [
        '--mf-bg-void', '--mf-surface-glass', '--mf-cyan', '--mf-gold', '--mf-purple',
        '--mf-role-dm', '--mf-role-player', '--mf-role-viewer',
        '--mf-topbar-height', '--mf-left-rail-width', '--mf-right-context-width',
        '--mf-bottom-strip-height', '--mf-player-hud-width', '--mf-viewer-panel-width',
        '--mf-drawer-width', '--mf-z-debug', '--mf-state-loading', '--mf-state-error',
        '--mf-state-success', '--mf-state-warning',
    ]
    for token in required_tokens:
        assert token in css


def test_blueprint_does_not_authorize_a_full_screen_rewrite():
    text = _doc()
    assert 'This is a foundation document only' in text
    assert 'Do not rebuild every screen in this phase' in text
    assert 'Do not change gameplay behaviour' in text
