import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY = ROOT / "client/templates/play.html"


def _src():
    return PLAY.read_text(encoding="utf-8")


def _func_body(src: str, name: str) -> str:
    start = src.index(f"function {name}")
    sig_end = src.index(")", start)
    brace = src.index("{", sig_end)
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    raise AssertionError(f"function {name} not closed")


def test_rendering_player_actions_hub_does_not_schedule_profile_autosave():
    body = _func_body(_src(), "renderPlayerActionsHub")
    assert "__enterCharRenderScope('renderPlayerActionsHub')" in body
    assert "scheduleCharProfileAutosave" not in body
    assert "markCharProfileDirty" not in body


def test_is_player_action_used_this_turn_is_read_only():
    body = _func_body(_src(), "_isPlayerActionUsedThisTurn")
    assert "_buildActionEconomyState" not in body
    assert "_saveActionEconomyRuntime" not in body
    assert "scheduleCharProfileAutosave" not in body
    assert "markCharProfileDirty" not in body


def test_build_action_economy_state_does_not_save_during_render():
    body = _func_body(_src(), "_buildActionEconomyState")
    assert "_saveActionEconomyRuntime" not in body
    assert "Read-only render snapshot" in body


def test_repeated_player_actions_render_cannot_trigger_schedule_save_reentry():
    src = _src()
    schedule = _func_body(src, "scheduleCharProfileAutosave")
    save_runtime = _func_body(src, "_saveActionEconomyRuntime")
    forbidden = _func_body(src, "__charProfileForbiddenAutosaveStack")
    assert "renderPlayerActionsHub" in forbidden
    assert "__warnBlockedCharAutosave('scheduleCharProfileAutosave'" in schedule
    assert "__deferCharProfileAutosaveUntilRenderUnwinds(reason)" not in schedule
    assert "__warnBlockedCharAutosave('_saveActionEconomyRuntime'" in save_runtime


def test_collect_profile_read_only_mode_does_not_init_or_seed_character_book():
    body = _func_body(_src(), "collectCurrentCharProfile")
    assert "const readOnlyCollect" in body
    guarded = re.search(r"if \(!readOnlyCollect\) \{(?P<body>.*?)\n  \}", body, re.S)
    assert guarded, "init/seed calls must be guarded behind !readOnlyCollect"
    assert "initCharacterBook();" in guarded.group("body")
    assert "seedCharacterBookFromCurrentState();" in guarded.group("body")


def test_quick_selector_preserves_unavailable_saved_picks_without_repair_save_or_warn():
    selector = (ROOT / "client/static/js/character/combat_quick_selectors.js").read_text(encoding="utf-8")
    body = _func_body(selector, "selectQuickActions")
    assert "disabledSavedPick" in body
    assert "Preserve disabled placeholders silently" in body
    assert "console.warn" not in body
    assert "scheduleCharProfileAutosave" not in body
    assert "markCharProfileDirty" not in body
    assert "localStorage.setItem" not in body
