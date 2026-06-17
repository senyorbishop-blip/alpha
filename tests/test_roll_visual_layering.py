from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client" / "templates" / "play.html"
ONBOARDING = ROOT / "client" / "static" / "js" / "ui" / "onboarding.js"


def _read(path):
    return path.read_text(encoding="utf-8")


def test_roll_visuals_use_single_portal_above_sheet_below_onboarding():
    play = _read(PLAY)
    onboarding = _read(ONBOARDING)

    assert "--z-roll-visuals: 16000;" in play
    assert "#roll-visual-portal" in play
    assert "<div id=\"roll-visual-portal\"" in play
    assert "z-index: 15600;" in play  # character sheet modal layer
    assert "z-index:20000;" in onboarding  # onboarding intentionally wins


def test_live_roll_surfaces_are_portaled():
    play = _read(PLAY)

    assert "['dice-overlay-bg', 'dice-3d-wrap', 'dice-roll-banner', 'dice-result-popup', 'combat-result-card']" in play
    assert "window.ensureRollVisualPortal = ensureRollVisualPortal;" in play
    assert "function _showCombatResultCard(opts)" in play
    assert "portal.appendChild(card);" in play
    assert "ensureRollVisualPortal();\n  // ── 3-D only path" in play


def test_roll_layering_manual_qa_contract_is_documented():
    play = _read(PLAY)
    assert "Roll visuals portal: dice canvas, roll result card, and roll result popup live above sheet/drawer surfaces." in play
    assert "Dice result popup — always above character sheet/drawers, below onboarding" in play
