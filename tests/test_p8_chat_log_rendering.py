"""P8 chat-log rendering guardrails.

The chat compose module owns sending messages; the chat log module owns what
appears in the visible feed. These tests protect that boundary so presence spam,
viewer-channel styling, whisper styling, and escaping do not drift back into the
play template.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY_TEMPLATE = ROOT / "client" / "templates" / "play.html"
CHAT_LOG_MODULE = ROOT / "client" / "static" / "js" / "ui" / "chat_log.js"
FRONTEND_DOC = ROOT / "docs" / "frontend-modularization.md"


def test_play_template_keeps_only_chat_log_compatibility_wrappers():
    html = PLAY_TEMPLATE.read_text(encoding="utf-8")
    wrapper_slice = html[html.index("function isPresenceLogEntry") : html.index("function addDMNotif")]

    assert "function addLogEntry" in wrapper_slice
    assert "function isPresenceLogEntry" in wrapper_slice
    assert "window.AppUIChatLog.addLogEntry(__createChatLogEnv(), entry)" in wrapper_slice
    assert "feed.appendChild" not in wrapper_slice
    assert "div.innerHTML" not in wrapper_slice


def test_chat_log_module_owns_public_contract():
    src = CHAT_LOG_MODULE.read_text(encoding="utf-8")

    assert "global.AppUIChatLog" in src
    assert "function isPresenceLogEntry(entry)" in src
    assert "function addLogEntry(env, entry)" in src


def test_chat_log_filters_presence_noise():
    src = CHAT_LOG_MODULE.read_text(encoding="utf-8")

    assert " joined as " in src
    assert " connected." in src
    assert " disconnected." in src
    assert " returned to the session." in src
    assert "if (isPresenceLogEntry(entry)) return" in src


def test_chat_log_only_renders_chat_entries():
    src = CHAT_LOG_MODULE.read_text(encoding="utf-8")

    assert "entry.type !== 'chat'" in src or 'entry.type !== "chat"' in src
    assert "log-feed" in src
    assert "feed.appendChild" in src


def test_chat_log_preserves_viewer_and_whisper_channel_tags():
    src = CHAT_LOG_MODULE.read_text(encoding="utf-8")

    assert "channel-viewers" in src
    assert "channel-whisper" in src
    assert "👁" in src
    assert "🤫" in src
    assert "private" in src


def test_chat_log_escapes_user_role_and_message_fields():
    src = CHAT_LOG_MODULE.read_text(encoding="utf-8")

    assert "env.escHtml(entry.role" in src
    assert "env.escHtml(entry.user" in src
    assert "env.escHtml(entry.message" in src
    assert "innerHTML" in src


def test_frontend_modularization_doc_records_p8_ownership():
    doc = FRONTEND_DOC.read_text(encoding="utf-8")

    assert "## Stage 8 — Chat log rendering extraction" in doc
    assert "client/static/js/ui/chat_log.js" in doc
    assert "presence-log filtering" in doc
    assert "visible chat-log entry rendering" in doc
