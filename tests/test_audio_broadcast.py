"""
tests/test_audio_broadcast.py — Tests for the audio broadcasting system.

Validates:
1. Dice roll broadcasts include sounds metadata
2. Sound engine handles dice roll SFX IDs
3. Session sound_state is persisted and sent on reconnect
4. TTS narration broadcast includes audio data
5. Viewer connections receive audio events (no filter)
"""
import sys
import os
import inspect
import asyncio
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Task 1 — Dice roll broadcast includes sounds
# ---------------------------------------------------------------------------


def test_dice_roll_handler_broadcasts_sounds():
    """handle_dice_roll must include a 'sounds' dict in the broadcast payload."""
    from server.handlers.content import handle_dice_roll
    src = inspect.getsource(handle_dice_roll)
    assert '"sounds"' in src or "'sounds'" in src, (
        "handle_dice_roll must include 'sounds' key in the broadcast payload"
    )


def test_dice_result_sound_classification():
    """The _result_sound helper must produce valid sound keys."""
    from server.handlers.content import handle_dice_roll
    src = inspect.getsource(handle_dice_roll)
    # Verify the helper classifies nat20, nat1, high, low
    assert "dice_nat20" in src, "Must classify natural 20 rolls"
    assert "dice_nat1" in src, "Must classify natural 1 rolls"
    assert "dice_high" in src, "Must classify high rolls"
    assert "dice_low" in src, "Must classify low rolls"


def test_dice_roll_sound_key_format():
    """Roll sound key must follow dice_roll_d{type} format."""
    from server.handlers.content import handle_dice_roll
    src = inspect.getsource(handle_dice_roll)
    assert "dice_roll_d" in src, (
        "Roll sound must use format 'dice_roll_d{type}'"
    )


# ---------------------------------------------------------------------------
# Task 2 — TTS narration indicator
# ---------------------------------------------------------------------------


def test_tts_client_has_narration_indicator():
    """tts_client.js must contain the narration playing indicator."""
    tts_path = os.path.join(PROJECT_ROOT, "client", "static", "tts_client.js")
    with open(tts_path, "r") as f:
        src = f.read()
    assert "tts-narration-indicator" in src, (
        "tts_client.js must create a narration playing indicator element"
    )
    assert "Narration playing" in src, (
        "tts_client.js must show 'Narration playing' text"
    )


# ---------------------------------------------------------------------------
# Task 2b — Narrator TTS word-tracking scroll (Issue 4)
# ---------------------------------------------------------------------------

_NARRATION_JS_PATH = os.path.join(
    PROJECT_ROOT, "client", "static", "js", "ui", "narration.js"
)


def test_narration_js_has_scroll_into_view():
    """narration.js _startReveal must call scrollIntoView for word tracking."""
    with open(_NARRATION_JS_PATH, "r") as f:
        src = f.read()
    assert "scrollIntoView" in src, (
        "narration.js _startReveal must call scrollIntoView to follow the current word"
    )
    assert "behavior: 'smooth'" in src or 'behavior: "smooth"' in src, (
        "scrollIntoView must use smooth scrolling (behavior: 'smooth')"
    )
    assert "block: 'center'" in src or 'block: "center"' in src, (
        "scrollIntoView must center the word in the view (block: 'center')"
    )


def test_narration_js_uses_span_for_current_word():
    """narration.js _startReveal must wrap the current word in a <span> element."""
    with open(_NARRATION_JS_PATH, "r") as f:
        src = f.read()
    assert "narration-current-word" in src, (
        "narration.js must create a span#narration-current-word for the active word"
    )
    assert "createElement('span')" in src or 'createElement("span")' in src, (
        "narration.js must build the highlight span via document.createElement"
    )


def test_play_html_narration_body_is_scrollable():
    """play.html .narration-scroll-body must have max-height and overflow-y for scrolling."""
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r") as f:
        src = f.read()
    assert "narration-scroll-body" in src, (
        "play.html must define .narration-scroll-body CSS"
    )
    assert "overflow-y" in src, (
        ".narration-scroll-body in play.html must set overflow-y to enable scrolling"
    )
    assert "max-height" in src, (
        ".narration-scroll-body in play.html must set max-height to cap the panel height"
    )


# ---------------------------------------------------------------------------
# Task 3 — Viewer mode receives all audio events
# ---------------------------------------------------------------------------


def test_broadcast_sends_to_all_connections():
    """ConnectionManager.broadcast must send to ALL connections (no role filter)."""
    from server.connections import ConnectionManager
    src = inspect.getsource(ConnectionManager.broadcast)
    # Must NOT have role-based filtering — sends to all UIDs
    assert "role" not in src.lower() or "exclude_user" in src, (
        "broadcast() must not filter by role — viewers must receive audio events"
    )


def test_viewer_filter_only_restricts_sending():
    """The viewer WebSocket filter must only restrict outgoing messages, not incoming.

    The viewer send allow-list moved from main.py's _VIEWER_ALLOWED into the
    central WS role policy (server/handlers/ws_permissions.py) as the
    VIEWER_ALLOWED_MESSAGE_TYPES frozenset.
    """
    from server.handlers.ws_permissions import VIEWER_ALLOWED_MESSAGE_TYPES
    # The viewer allow-list should only gate what viewers can SEND
    assert VIEWER_ALLOWED_MESSAGE_TYPES, "Viewer allow-list must exist"
    assert 'viewer_power_use' in VIEWER_ALLOWED_MESSAGE_TYPES, (
        "Viewers can send viewer_power_use"
    )


# ---------------------------------------------------------------------------
# Task 4 — Player volume controls
# ---------------------------------------------------------------------------


def test_player_volume_panel_exists():
    """play.html must have the player volume control sliders."""
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r") as f:
        src = f.read()
    assert "sound-player-master-vol" in src, "Master volume slider must exist"
    assert "sound-player-ambient-vol" in src, "Ambient volume slider must exist"
    assert "sound-player-sfx-vol" in src, "SFX volume slider must exist"


def test_player_volume_handler_exists():
    """play.html must define _playerVolChange function."""
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r") as f:
        src = f.read()
    assert "_playerVolChange" in src, (
        "play.html must define _playerVolChange handler for volume sliders"
    )


def test_volume_persisted_to_localstorage():
    """AudioManager volume methods must persist to localStorage."""
    se_path = os.path.join(PROJECT_ROOT, "client", "static", "js", "ui", "sound_engine.js")
    with open(se_path, "r") as f:
        src = f.read()
    assert "tavern_vol_master" in src, "Master volume must be persisted to localStorage"
    assert "tavern_vol_ambient" in src, "Ambient volume must be persisted to localStorage"
    assert "tavern_vol_sfx" in src, "SFX volume must be persisted to localStorage"


# ---------------------------------------------------------------------------
# Task 5 — Connection resilience: init_audio
# ---------------------------------------------------------------------------


def test_init_audio_sent_on_connect():
    """main.py websocket_endpoint must send init_audio on connect."""
    main_path = os.path.join(PROJECT_ROOT, "main.py")
    with open(main_path, "r") as f:
        src = f.read()
    assert '"init_audio"' in src or "'init_audio'" in src, (
        "Server must send init_audio message on WebSocket connect"
    )


def test_init_audio_includes_ambient():
    """init_audio payload must include ambient track and volume."""
    main_path = os.path.join(PROJECT_ROOT, "main.py")
    with open(main_path, "r") as f:
        src = f.read()
    assert '"ambient"' in src, "init_audio must include ambient track key"
    assert '"ambient_volume"' in src, "init_audio must include ambient_volume"


def test_session_sound_state_field():
    """Session model must have a sound_state field."""
    from server.session import Session
    import dataclasses
    fields = {f.name for f in dataclasses.fields(Session)}
    assert "sound_state" in fields, "Session must have sound_state field"


def test_sound_handler_persists_state():
    """handle_sound_set_ambient must save track to session.sound_state."""
    from server.handlers.sound import handle_sound_set_ambient
    src = inspect.getsource(handle_sound_set_ambient)
    assert 'sound_state["track"]' in src, (
        "handle_sound_set_ambient must persist track to session.sound_state"
    )


def test_client_handles_init_audio():
    """play.html must handle the init_audio WebSocket message."""
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r") as f:
        src = f.read()
    assert "'init_audio'" in src or '"init_audio"' in src, (
        "play.html must handle init_audio WebSocket message"
    )


def test_client_handles_narration_hook_event():
    """play.html must handle lightweight narration_hook trigger events."""
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r") as f:
        src = f.read()
    assert "case 'narration_hook':" in src, "play.html must handle narration_hook events"
    assert "_narrationManager.showHook" in src, "narration_hook should route through NarrationManager.showHook"


# ---------------------------------------------------------------------------
# SoundEngine — dice SFX procedural synthesis
# ---------------------------------------------------------------------------


def test_sound_engine_handles_dice_roll_sfx():
    """SoundEngine.playSfx must handle dice_roll_d* IDs."""
    se_path = os.path.join(PROJECT_ROOT, "client", "static", "js", "ui", "sound_engine.js")
    with open(se_path, "r") as f:
        src = f.read()
    assert "dice_roll_" in src, "SoundEngine must handle dice_roll_d* SFX IDs"
    assert "dice_high" in src, "SoundEngine must handle dice_high SFX"
    assert "dice_low" in src, "SoundEngine must handle dice_low SFX"
    assert "dice_nat20" in src, "SoundEngine must handle dice_nat20 SFX"
    assert "dice_nat1" in src, "SoundEngine must handle dice_nat1 SFX"


def test_play_html_plays_dice_audio_for_other_players():
    """play.html dice_result handler must play audio for other players' rolls."""
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r") as f:
        src = f.read()
    assert "p.sounds" in src, (
        "dice_result handler must check for sounds in the payload"
    )
    assert "p.user_id !== USER_ID" in src, (
        "Dice audio should play for rolls from OTHER users"
    )


def test_play_html_marks_sound_and_narration_authoritative():
    """play.html should document the authoritative Stage 2 sound/narration path."""
    play_path = os.path.join(PROJECT_ROOT, "client", "templates", "play.html")
    with open(play_path, "r", encoding="utf-8") as f:
        src = f.read()
    assert 'sound_engine.js + narration.js are authoritative' in src, (
        'play.html should document that sound_engine.js and narration.js are the live audio path'
    )
    assert '/static/js/ui/sound_engine.js' in src
    assert '/static/js/ui/narration.js' in src
    assert '/static/ambient_engine.js' in src
    assert '/static/sfx_engine.js' in src


def test_procedural_audio_modules_marked_fallback_only():
    """Procedural ambient/SFX files should identify themselves as fallback compatibility layers."""
    ambient_path = os.path.join(PROJECT_ROOT, 'client', 'static', 'ambient_engine.js')
    sfx_path = os.path.join(PROJECT_ROOT, 'client', 'static', 'sfx_engine.js')
    with open(ambient_path, 'r', encoding='utf-8') as f:
        ambient_src = f.read()
    with open(sfx_path, 'r', encoding='utf-8') as f:
        sfx_src = f.read()
    assert 'compatibility/fallback procedural ambient synthesizer' in ambient_src
    assert 'Do not treat it as a peer runtime authority' in ambient_src
    assert 'compatibility/fallback procedural SFX library' in sfx_src
    assert 'Do not treat it as a peer runtime authority' in sfx_src
