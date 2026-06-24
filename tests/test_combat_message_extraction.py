from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_combat_message_module_exists_and_exports_handler():
    src = read("client/static/js/gameplay/combat_messages.js")
    assert "global.AppCombatMessages" in src
    assert "handleIncoming" in src
    assert "isCombatMessageType" in src
    assert "combat_state" in src
    assert "combat_attack_result" in src
    assert "combat_move_state" in src
    assert "token_move_denied" in src


def test_message_dispatch_routes_combat_before_legacy_with_fallback():
    src = read("client/static/js/core/message_dispatch.js")
    assert "tryHandleCombatMessage(msg, runtimeEnv)" in src
    assert "runtimeEnv.handleLegacyMessage(msg)" in src
    assert src.index("tryHandleCombatMessage(msg, runtimeEnv)") < src.index("runtimeEnv.handleLegacyMessage(msg)")
    assert "legacy combat handlers remain active" in src


def test_combat_module_delegates_to_existing_runtime_functions():
    src = read("client/static/js/gameplay/combat_messages.js")
    assert "combatApplyState" in src
    assert "showCombatAttackResult" in src
    assert "setCombatMovement" in src
    assert "renderCombat" in src
    assert "clearPendingMoveConfirmForToken" in src


def test_dispatcher_knows_combat_message_types():
    src = read("client/static/js/core/message_dispatch.js")
    for message_type in (
        "combat_state",
        "combat_attack_result",
        "combat_move_state",
        "combat_move_preview_result",
        "combat_initiative_rolled",
        "token_move_denied",
    ):
        assert message_type in src
