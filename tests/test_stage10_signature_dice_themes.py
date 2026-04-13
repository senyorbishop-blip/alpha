from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding='utf-8')


def test_dice_theme_library_includes_signature_presets():
    src = _read('client/static/js/dice/ui/DiceTheme.js')
    assert "'dragonforge-royal'" in src
    assert "'moonsteel-oath'" in src
    assert "'voidfire-sigil'" in src
    assert 'premium:      true' in src


def test_play_page_exposes_signature_theme_action_and_grouping():
    src = _read('client/templates/play.html')
    assert 'applySignatureDiceTheme()' in src
    assert 'Signature Themes' in src
    assert 'function _getSignatureDiceThemes()' in src
    assert 'showToast(`Signature style ready: ${pick.label}`);' in src
