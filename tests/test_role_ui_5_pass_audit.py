"""Guardrails for the DM/Player/Viewer role UI migration audit.

These tests intentionally stay static: the current migration is not ready for
broad deletion of legacy play-page UI. They lock the conservative ownership and
role-visibility conclusions from the five-pass review.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "role-ui-5-pass-audit-20260626.md"
PLAY = ROOT / "client" / "templates" / "play.html"
TABS = ROOT / "client" / "static" / "js" / "ui" / "tabs.js"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_audit_report_records_local_play_html_as_runtime_source_of_truth():
    src = _read(AUDIT)
    assert "local `client/templates/play.html` is present and non-blank" in src
    assert "Frontend live authority: `client/templates/play.html`" in src
    assert "`message_dispatch.js` is only a first-hop dispatcher" in src


def test_audit_matrix_covers_required_role_surfaces():
    src = _read(AUDIT)
    required = [
        "DM | Map controls",
        "DM | Token select/move/edit",
        "DM | Viewer powers approval/granting",
        "Player | Quick actions",
        "Player | Inventory",
        "Player | Combat turn permissions",
        "Viewer | Viewer powers list",
        "Viewer | Cooldowns/charges",
        "Viewer | Role-restricted visibility",
    ]
    for fragment in required:
        assert fragment in src


def test_audit_forbids_deletion_until_legacy_bridges_are_proven_unused():
    src = _read(AUDIT)
    assert "### Safe deletions now\n\nNone." in src
    assert "Keep temporarily as compatibility bridge" in src
    assert "Legacy right tabs" in src
    assert "Left rail flyouts" in src
    assert "Viewer power inline rendering/application" in src


def test_live_play_loads_role_shells_after_ws_dispatch_and_before_inline_runtime():
    src = _read(PLAY)
    order = [
        "/static/js/core/boot_shell.js",
        "/static/js/core/ws.js",
        "/static/js/core/message_dispatch.js",
        "/static/js/ui/player_shell.js",
        "/static/js/ui/tabs.js",
        "/static/js/ui/dm_map_first_shell.js",
        "/static/js/ui/dm_context_render.js",
        "/static/js/ui/dm_panel_mode_bridge.js",
        "/static/js/character/combat_quick_actions.js",
    ]
    positions = [src.index(item) for item in order]
    assert positions == sorted(positions)
    assert "const ROLE       = params.get('role')       || 'viewer';" in src
    assert 'window.__PLAY_BOOT_ROLE = "{{ play_role|default(\'viewer\') }}";' in src


def test_role_visibility_contracts_remain_in_loaded_tab_controller():
    src = _read(TABS)
    assert "function canUsePlayerTabs(env)" in src
    assert "return !isRole(env, 'viewer');" in src
    assert "function canUseDmLibraryTabs(env)" in src
    assert "return isRole(env, 'dm');" in src
    assert "normalizeAllowedTab" in src
