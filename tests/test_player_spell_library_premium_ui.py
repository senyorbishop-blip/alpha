from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_player_spell_library_has_state_filters_and_clear_action():
    src = _read("client/templates/play.html")
    assert 'id="cb-lib-state-all"' in src
    assert 'id="cb-lib-state-prepared"' in src
    assert 'id="cb-lib-state-known"' in src
    assert "function clearPlayerSpellLibraryFilters()" in src
    assert "function setPlayerSpellStateFilter(mode)" in src


def test_player_spell_library_cards_expose_cast_and_premium_markers():
    src = _read("client/templates/play.html")
    assert "function castPlayerGrantedSpell(grantId)" in src
    assert "class=\"granted-spell-cast-btn\"" in src
    assert "granted-spell-tag concentration" in src
    assert "granted-spell-tag ritual" in src
    assert "<strong>Save / Attack</strong>" in src
    assert "<strong>Damage / Effect</strong>" in src
    assert "class=\"granted-spell-detail\"" in src


def test_player_spell_library_mobile_first_controls_and_stack_rules():
    # CSS was extracted from play.html into play.css; these rules now live there.
    src = _read("client/static/css/play.css")
    assert ".granted-spell-toolbar { display:flex;" in src
    assert ".granted-spell-filter-chip { border:1px solid" in src
    assert ".granted-spell-cast-btn { font-size:0.68rem;" in src
    assert "@media (max-width: 760px)" in src
    assert ".granted-spell-cast-btn, .granted-spell-prepare, .granted-spell-filter-chip { min-height:40px; }" in src
