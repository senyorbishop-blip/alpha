from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_monster_quick_rolls_do_not_emit_chat_messages():
    src = _read("client/templates/play.html")
    assert "function _monsterQuickRollAttack(action, target, token) {" in src
    assert "function _monsterQuickRunSaveDc(action, token) {" in src
    assert "function _showMonsterDamagePrompt(action, targetName) {" in src
    assert "⚔ **${token?.name || 'Monster'}** uses **${normalized.name}**" not in src
    assert "🛡 **${target.name || 'Target'}** rolls" not in src
    assert "⚔ **${normalized.name}** damage vs ${targetName || 'target'}" not in src
