from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding='utf-8')


def test_play_page_contains_player_actions_hub_markup_and_renderer():
    src = _read('client/templates/play.html')
    assert 'id="player-actions-hub"' in src
    assert 'function renderPlayerActionsHub()' in src
    assert 'function playerUseAction(source, id, options)' in src


def test_player_actions_hub_includes_requested_categories_and_spell_markers():
    src = _read('client/templates/play.html')
    assert "['Attacks', 'Bonus Actions', 'Reactions', 'Class Features', 'Spells']" in src
    assert "if (card.concentration || card.is_concentration) badges.push('Concentration');" in src
    assert "if (card.ritual || card.is_ritual) badges.push('Ritual');" in src


def test_player_actions_hub_is_mobile_first():
    # CSS was extracted from play.html into play.css; these rules now live there.
    src = _read('client/static/css/play.css')
    assert '.player-action-use-btn { width: 100%; min-height: 40px; }' in src
    assert '.player-action-meta { grid-template-columns: 1fr; }' in src


def test_player_weapon_action_execution_accepts_runtime_id_name_and_slug_fallbacks():
    # The weapon slug-fallback was refactored out of playerUseAction into the
    # shared findCombatWeapon resolver, which still accepts a raw id, a
    # case-insensitive name, or a slug.
    src = _read('client/templates/play.html')
    assert "function findCombatWeapon(input)" in src
    assert "const rawLower = raw.toLowerCase();" in src
    assert "const rawSlug = _combatQuickSlug(raw);" in src
    assert "keys.map(k => k.toLowerCase()).includes(rawLower)" in src
    assert "slugs.includes(rawSlug)" in src


def test_player_actions_hub_and_selector_are_autosave_guarded():
    src = _read('client/templates/play.html')
    autosave_guard = src[src.index("function __isCharProfileRenderStackActive"):src.index("function scheduleCharBookQuickPanelSync")]
    assert "renderPlayerActionsHub" in autosave_guard
    assert "selectQuickActions" in autosave_guard
    hub = src[src.index("function renderPlayerActionsHub()"):src.index("function setPlayerActionsDensity")]
    assert "scheduleCharProfileAutosave" not in hub
    assert "markCharProfileDirty" not in hub
