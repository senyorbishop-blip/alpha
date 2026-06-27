"""Guardrails for viewer power target/source selection refreshes.

Viewer panels can render before authoritative token projection finishes during
initial state sync or reconnect. If they are not refreshed after token snapshots
and token events, the viewer's target/source dropdown stays empty and map AOE
controls can be armed against stale context.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAY_HTML = ROOT / "client" / "templates" / "play.html"


def _function_body(src: str, name: str) -> str:
    start = src.index(f"function {name}(")
    brace = src.index("{", start)
    depth = 0
    for i in range(brace, len(src)):
        ch = src[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
    raise AssertionError(f"Unbalanced braces while scanning {name}")


def test_token_snapshot_refreshes_viewer_power_targets_after_projection():
    src = PLAY_HTML.read_text(encoding="utf-8")
    body = _function_body(src, "applyAuthoritativeTokenSnapshot")
    apply_idx = body.index("applyAuthoritativeTokenSync(p)")
    refresh_idx = body.index("refreshViewerPowerTargetsAfterTokenChange")
    assert apply_idx < refresh_idx, "viewer target dropdown must refresh after tokens are projected"


def test_single_token_events_refresh_viewer_power_targets():
    src = PLAY_HTML.read_text(encoding="utf-8")
    body = _function_body(src, "applyAuthoritativeTokenEvent")
    assert "refreshViewerPowerTargetsAfterTokenChange" in body


def test_viewer_power_target_refresh_is_viewer_only_and_renders_panel():
    src = PLAY_HTML.read_text(encoding="utf-8")
    body = _function_body(src, "refreshViewerPowerTargetsAfterTokenChange")
    assert "ROLE !== 'viewer'" in body
    assert "renderViewerPanel()" in body
