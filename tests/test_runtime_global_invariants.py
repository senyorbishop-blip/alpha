"""Static runtime invariants for the play-page modularization boundary.

These checks protect globals that loaded compatibility modules call and verify
that first-stage UI extractions are actually on the live play.html path.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY_TEMPLATE = ROOT / "client" / "templates" / "play.html"
EDITOR_PANEL = ROOT / "client" / "static" / "js" / "ui" / "editor_panel.js"
CHAT_LOG = ROOT / "client" / "static" / "js" / "ui" / "chat_log.js"


def _script_srcs(html: str) -> list[str]:
    return re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)


def test_loaded_modules_still_have_required_play_globals():
    html = PLAY_TEMPLATE.read_text(encoding="utf-8")
    editor_src = EDITOR_PANEL.read_text(encoding="utf-8")

    required_globals = [
        "setEditorTerrain",
        "setEditorBrush",
        "setEditorWallTool",
        "setEditorFileAsset",
        "setEditorDndPropAsset",
        "setEditorLayerMode",
        "saveEditorMap",
        "clearEditorMap",
    ]
    for name in required_globals:
        assert f"'{name}'" in editor_src or f'"{name}"' in editor_src
        assert re.search(rf"function\s+{name}\s*\(", html), f"missing play.html global {name}"


def test_chat_log_module_is_loaded_before_inline_runtime_and_wrappers_remain_global():
    html = PLAY_TEMPLATE.read_text(encoding="utf-8")
    srcs = _script_srcs(html)

    assert "/static/js/ui/chat_log.js" in srcs
    assert html.index('<script src="/static/js/ui/chat_log.js"></script>') < html.index("const ROLE")
    assert re.search(r"function\s+addLogEntry\s*\(", html)
    assert re.search(r"function\s+isPresenceLogEntry\s*\(", html)
    assert "window.AppUIChatLog.addLogEntry(__createChatLogEnv(), entry)" in html


def test_chat_log_module_owns_rendering_while_play_keeps_only_wrappers():
    html = PLAY_TEMPLATE.read_text(encoding="utf-8")
    module_src = CHAT_LOG.read_text(encoding="utf-8")

    assert "global.AppUIChatLog" in module_src
    assert "feed.appendChild(div)" in module_src
    assert "div.innerHTML" in module_src
    wrapper_slice = html[html.index("function isPresenceLogEntry") : html.index("function addDMNotif")]
    assert "feed.appendChild(div)" not in wrapper_slice
    assert "div.innerHTML" not in wrapper_slice
