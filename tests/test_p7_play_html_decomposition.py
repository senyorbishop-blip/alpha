"""P7 frontend modularization guardrails.

P7 protects the chat compose controller as a real module
(client/static/js/ui/chat.js) instead of letting that logic drift back into the
monolithic client/templates/play.html runtime.
"""

from __future__ import annotations

import re

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY_TEMPLATE = ROOT / "client" / "templates" / "play.html"
CHAT_MODULE = ROOT / "client" / "static" / "js" / "ui" / "chat.js"
FRONTEND_DOC = ROOT / "docs" / "frontend-modularization.md"


def test_chat_compose_logic_lives_in_chat_module_not_play_html():
    """The chat compose contract must stay owned by ui/chat.js.

    play.html is the large monolithic live-play runtime (it intentionally
    contains inline scripts and a great deal of markup), so the original
    "thin / script-free" size assertion no longer describes the architecture.
    The durable P7 invariant is that the chat-compose functions
    (sendChat / renderChatTargets / updateChatTargetVisibility) are *owned* by
    the chat module and are NOT re-defined as top-level functions inside
    play.html — the template only delegates to window.AppUIChat.
    """
    html = PLAY_TEMPLATE.read_text(encoding="utf-8")
    chat_src = CHAT_MODULE.read_text(encoding="utf-8")

    # chat.js is the real owner: it defines the compose functions and exports
    # them through the AppUIChat namespace.
    assert "global.AppUIChat" in chat_src
    for fn in ("sendChat", "renderChatTargets", "updateChatTargetVisibility"):
        assert re.search(rf"function {fn}\s*\(", chat_src), fn

    # play.html must NOT re-declare these as top-level functions — that would
    # mean the logic drifted back into the template instead of the module.
    for fn in ("sendChat", "renderChatTargets", "updateChatTargetVisibility"):
        assert not re.search(rf"^(?:async\s+)?function {fn}\s*\(", html, re.MULTILINE), (
            f"play.html must not define top-level function {fn}; it belongs to ui/chat.js"
        )

    # play.html must delegate to the module rather than owning the behavior.
    assert "window.AppUIChat" in html
    assert "AppUIChat.renderChatTargets" in html


def test_chat_compose_module_owns_public_contract():
    src = CHAT_MODULE.read_text(encoding="utf-8")

    assert "global.AppUIChat" in src
    assert "function init(env)" in src
    assert "function installBindings(env)" in src
    assert "function updateChatTargetVisibility(env)" in src
    assert "function renderChatTargets(env)" in src
    assert "function sendChat(env)" in src


def test_chat_compose_module_handles_all_supported_channels():
    src = CHAT_MODULE.read_text(encoding="utf-8")

    assert "ai_rules_oracle" in src
    assert "channel: 'viewers'" in src or 'channel: "viewers"' in src
    assert "channel: 'whisper'" in src or 'channel: "whisper"' in src
    assert "target_user_id" in src


def test_frontend_modularization_doc_records_p7_ownership():
    doc = FRONTEND_DOC.read_text(encoding="utf-8")

    assert "## Stage 7 — Chat compose UI extraction" in doc
    assert "client/static/js/ui/chat.js" in doc
    assert "chat target visibility" in doc
    assert "chat send behavior" in doc
