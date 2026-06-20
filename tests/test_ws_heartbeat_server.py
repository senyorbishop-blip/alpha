"""Server-side heartbeat tolerance (main.py websocket endpoint).

The websocket receive loop is a large endpoint that is not unit-importable in
isolation, so these tests assert the structural invariants that keep active play
from tripping a false heartbeat timeout:

  * the last-seen timestamp is refreshed on ANY valid received frame, not only
    on pong;
  * pong is still recognized and skipped from gameplay dispatch.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"


def _ws_loop_source() -> str:
    src = MAIN.read_text(encoding="utf-8")
    start = src.index("while True:")
    end = src.index("except WebSocketDisconnect:", start)
    return src[start:end]


def test_last_seen_refreshed_on_any_valid_message():
    loop = _ws_loop_source()
    # The timestamp update must appear once the frame is parsed and msg_type is
    # known, and crucially BEFORE the pong-only early continue, so every valid
    # frame refreshes liveness.
    update = '_last_pong["t"] = asyncio.get_running_loop().time()'
    assert update in loop
    update_idx = loop.index(update)
    pong_idx = loop.index('if msg_type == "pong":')
    assert update_idx < pong_idx, "last-seen must update on any message, before the pong skip"


def test_pong_is_still_skipped_from_dispatch():
    loop = _ws_loop_source()
    pong_block = loop[loop.index('if msg_type == "pong":'):]
    # The pong branch must continue (skip handle_message) without falling through
    # to gameplay dispatch.
    first_continue = pong_block.index("continue")
    handle_idx = pong_block.index("handle_message(")
    assert first_continue < handle_idx, "pong must continue before reaching handle_message"


def test_last_seen_not_updated_on_undecodable_frame():
    loop = _ws_loop_source()
    # JSON decode failure must continue BEFORE the liveness refresh so garbage
    # frames cannot keep a dead socket alive.
    decode_continue = loop.index("json.JSONDecodeError")
    update_idx = loop.index('_last_pong["t"] = asyncio.get_running_loop().time()')
    assert decode_continue < update_idx


def test_heartbeat_timeout_still_present():
    # We are making the heartbeat more tolerant, not removing it.
    src = MAIN.read_text(encoding="utf-8")
    assert re.search(r"pong_timeout: float = 60", src)
    assert 'await connection_manager.send_to(session_id, user_id, {"type": "ping"})' in src
