"""P7 frontend modularization guardrails.

P7 keeps the live play shell thin and protects the chat compose controller as a
real module instead of letting logic drift back into client/templates/play.html.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY_TEMPLATE = ROOT / "client" / "templates" / "play.html"
CHAT_MODULE = ROOT / "client" / "static" / "js" / "ui" / "chat.js"
FRONTEND_DOC = ROOT / "docs" / "frontend-modularization.md"


def test_play_template_stays_thin_and_script_free():
    html = PLAY_TEMPLATE.read_text(encoding="utf-8")

    assert len(html) <= 2048
    assert "<script" not in html.lower()
    assert "function sendChat" not in html
    assert "updateChatTargetVisibility" not in html
    assert "renderChatTargets" not in html


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
