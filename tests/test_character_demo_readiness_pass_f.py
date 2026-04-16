from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_pass_f_checklist_exists_with_required_sections():
    src = _read("docs/founder-beta/character-demo-readiness-pass-f.md")
    assert "Character Demo Readiness — Pass F Lock" in src
    assert "Unsupported-path containment" in src
    assert "Remaining issue classification" in src
    assert "Blockers" in src
    assert "Non-blockers" in src
    assert "Deferred" in src


def test_gateway_levelup_preview_is_opt_in_for_demo_lock():
    src = _read("client/static/js/character/gateway/gateway_modal.js")
    assert "opts.enableLevelupPreview && item.nativeCharacter && item.sourceMode === 'native'" in src


def test_actions_tab_filters_out_unsupported_summon_runtime_rows():
    src = _read("client/static/js/character/tabs/actions_tab.js")
    assert "return !!entry && _summonActionRuntimeSupported(entry);" in src
