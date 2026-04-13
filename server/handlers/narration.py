"""Premium narration handlers — direct HTTP to TTS provider APIs.

No vendor SDKs are imported here. All TTS calls go directly to provider
REST endpoints via the ``requests`` library.

Provider priority:
  1. Gemini TTS   (if GEMINI_API_KEY is set)     — direct HTTP POST
  2. ElevenLabs   (if ELEVENLABS_API_KEY is set) — direct HTTP POST
  3. OpenAI TTS   (if OPENAI_API_KEY is set)     — direct HTTP POST
  4. Browser Web Speech API                      — frontend fallback
"""
import base64
import hashlib
import logging
import os
import struct
import threading
from collections import OrderedDict

import requests

from server.handlers.common import Session, User, manager
from server.session import assistant_dm_has_scope

logger = logging.getLogger(__name__)

# ── Kokoro voice preset lookup ────────────────────────────────────────────────
# Build a map from preset id → {voice_id, speed, emotion} from tts_config.py
# so the local Kokoro TTS engine uses the correct voice for each preset.

try:
    from tts_config import VOICE_PRESETS as _KOKORO_VOICE_PRESETS_LIST
    _KOKORO_PRESET_MAP: dict[str, dict] = {
        p["id"]: p for p in _KOKORO_VOICE_PRESETS_LIST if p.get("id")
    }
except ImportError:
    _KOKORO_PRESET_MAP = {}
except Exception as _exc:
    logger.warning("[Narration] Failed to load Kokoro presets from tts_config: %s", _exc)
    _KOKORO_PRESET_MAP = {}

_KOKORO_DEFAULT_VOICE_ID = "am_michael"
_KOKORO_DEFAULT_SPEED = 1.0
_KOKORO_DEFAULT_EMOTION = "neutral"

# ── Constants ────────────────────────────────────────────────────────────────

_VALID_POLICY_MODES = {"replace_current", "queue_next", "ignore_if_busy"}
_MAX_TEXT_LEN = 2000
_MAX_CACHE_ITEMS = 32
_CACHE_LOCK = threading.Lock()
_TTS_CACHE: "OrderedDict[str, dict]" = OrderedDict()

_EL_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_EL_OUTPUT_FORMAT = "mp3_44100_128"
_EL_TIMEOUT = float(os.environ.get("ELEVENLABS_TTS_TIMEOUT_SEC", "30") or 30)

_OPENAI_TTS_URL = "https://api.openai.com/v1/audio/speech"
_OPENAI_TTS_MODEL = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts").strip() or "gpt-4o-mini-tts"
_OPENAI_TTS_TIMEOUT = float(os.environ.get("OPENAI_TTS_TIMEOUT_SEC", "45") or 45)

_GEMINI_TTS_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_GEMINI_TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts").strip() or "gemini-2.5-flash-preview-tts"
_GEMINI_TTS_TIMEOUT = float(os.environ.get("GEMINI_TTS_TIMEOUT_SEC", "45") or 45)

# ── Voice presets ─────────────────────────────────────────────────────────────
# Voice IDs and model can be overridden via .env / environment variables.

_VOICE_PRESETS = {
    "deep_narrator": {
        "voice_id": os.environ.get("ELEVENLABS_VOICE_DEEP_NARRATOR", "CwhRBWXzGAHq8TQ4Fs17"),
        "model_id": os.environ.get("ELEVENLABS_MODEL_DEEP_NARRATOR", "eleven_multilingual_v2"),
        "settings": {"stability": 0.48, "similarity_boost": 0.78, "style": 0.36, "use_speaker_boost": True},
        "fallback": {"rate": 0.86, "pitch": 0.72, "voice_hints": ["neural", "natural", "daniel", "david", "george", "male", "en-gb", "british"]},
    },
    "grim_villain": {
        "voice_id": os.environ.get("ELEVENLABS_VOICE_GRIM_VILLAIN", "onwK4e9ZLuTAKqWW03F9"),
        "model_id": os.environ.get("ELEVENLABS_MODEL_GRIM_VILLAIN", "eleven_multilingual_v2"),
        "settings": {"stability": 0.58, "similarity_boost": 0.82, "style": 0.62, "use_speaker_boost": True},
        "fallback": {"rate": 0.8, "pitch": 0.64, "voice_hints": ["neural", "david", "daniel", "male", "en-gb", "british"]},
    },
    "mysterious_whisper": {
        "voice_id": os.environ.get("ELEVENLABS_VOICE_MYSTERIOUS_WHISPER", "GBv7mTt0atIp3Br8iCZE"),
        "model_id": os.environ.get("ELEVENLABS_MODEL_MYSTERIOUS_WHISPER", "eleven_multilingual_v2"),
        "settings": {"stability": 0.42, "similarity_boost": 0.74, "style": 0.7, "use_speaker_boost": True},
        "fallback": {"rate": 0.76, "pitch": 0.98, "voice_hints": ["neural", "aria", "zira", "serena", "samantha", "female", "en-gb", "en-us"]},
    },
    "heroic_bard": {
        "voice_id": os.environ.get("ELEVENLABS_VOICE_HEROIC_BARD", "ErXwobaYiN019PkySvjV"),
        "model_id": os.environ.get("ELEVENLABS_MODEL_HEROIC_BARD", "eleven_multilingual_v2"),
        "settings": {"stability": 0.36, "similarity_boost": 0.75, "style": 0.86, "use_speaker_boost": True},
        "fallback": {"rate": 0.98, "pitch": 1.03, "voice_hints": ["neural", "aria", "serena", "samantha", "female", "en-us", "en-gb"]},
    },
}
_DEFAULT_PRESET = "deep_narrator"

_OPENAI_VOICE_MAP = {
    "deep_narrator":      {"voice": os.environ.get("OPENAI_TTS_VOICE_DEEP_NARRATOR", "onyx"),  "instructions": os.environ.get("OPENAI_TTS_INSTRUCTIONS_DEEP_NARRATOR", "Speak like a seasoned fantasy narrator with a warm, grounded gravitas."),           "speed": float(os.environ.get("OPENAI_TTS_SPEED_DEEP_NARRATOR", "0.92") or 0.92)},
    "grim_villain":       {"voice": os.environ.get("OPENAI_TTS_VOICE_GRIM_VILLAIN", "echo"),   "instructions": os.environ.get("OPENAI_TTS_INSTRUCTIONS_GRIM_VILLAIN", "Speak like a menacing fantasy villain with restrained menace and crisp diction."),      "speed": float(os.environ.get("OPENAI_TTS_SPEED_GRIM_VILLAIN", "0.9") or 0.9)},
    "mysterious_whisper": {"voice": os.environ.get("OPENAI_TTS_VOICE_MYSTERIOUS_WHISPER", "sage"),  "instructions": os.environ.get("OPENAI_TTS_INSTRUCTIONS_MYSTERIOUS_WHISPER", "Speak softly and intimately, like a mysterious guide sharing a secret in a dark forest."), "speed": float(os.environ.get("OPENAI_TTS_SPEED_MYSTERIOUS_WHISPER", "0.88") or 0.88)},
    "heroic_bard":        {"voice": os.environ.get("OPENAI_TTS_VOICE_HEROIC_BARD", "verse"),   "instructions": os.environ.get("OPENAI_TTS_INSTRUCTIONS_HEROIC_BARD", "Speak with lively bardic confidence, musical phrasing, and uplifting theatrical energy."),  "speed": float(os.environ.get("OPENAI_TTS_SPEED_HEROIC_BARD", "1.0") or 1.0)},
}

_GEMINI_VOICE_MAP = {
    "deep_narrator":      {"voice_name": os.environ.get("GEMINI_TTS_VOICE_DEEP_NARRATOR", "Charon"),   "style_prompt": os.environ.get("GEMINI_TTS_STYLE_DEEP_NARRATOR", "Speak like a seasoned fantasy narrator with a warm, grounded gravitas and rumbling depth.")},
    "grim_villain":       {"voice_name": os.environ.get("GEMINI_TTS_VOICE_GRIM_VILLAIN", "Fenrir"),    "style_prompt": os.environ.get("GEMINI_TTS_STYLE_GRIM_VILLAIN", "Speak like a menacing fantasy villain with restrained menace and crisp, icy diction.")},
    "mysterious_whisper": {"voice_name": os.environ.get("GEMINI_TTS_VOICE_MYSTERIOUS_WHISPER", "Kore"), "style_prompt": os.environ.get("GEMINI_TTS_STYLE_MYSTERIOUS_WHISPER", "Speak softly and intimately, like a mysterious guide sharing a secret in a dark forest.")},
    "heroic_bard":        {"voice_name": os.environ.get("GEMINI_TTS_VOICE_HEROIC_BARD", "Aoede"),      "style_prompt": os.environ.get("GEMINI_TTS_STYLE_HEROIC_BARD", "Speak with lively bardic confidence, musical phrasing, and uplifting theatrical energy.")},
}

# ── Startup key check (runs once at module import) ────────────────────────────
# We check for the key here so the log appears once at startup, not on every
# request. The SDK import that used to cause the websockets error is gone.

_GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "").strip()

logger.info("[Narration] GEMINI_API_KEY found: %s", bool(_GEMINI_API_KEY))
if _GEMINI_API_KEY:
    logger.info("[Narration] Gemini TTS narration enabled (direct HTTP).")

_ELEVENLABS_API_KEY: str = os.environ.get("ELEVENLABS_API_KEY", "").strip()

logger.info("[Narration] ELEVENLABS_API_KEY found: %s", bool(_ELEVENLABS_API_KEY))
if _ELEVENLABS_API_KEY:
    logger.info("[Narration] ElevenLabs TTS narration enabled (direct HTTP).")

if not _GEMINI_API_KEY and not _ELEVENLABS_API_KEY:
    logger.info("[Narration] No premium TTS key configured; Kokoro local engine will be used.")
    logger.info("[Narration] Set GEMINI_API_KEY in .env to enable Gemini TTS.")


# ── Voice resolution helpers ──────────────────────────────────────────────────

def _normalise_preset(voice_preset: str) -> str:
    normalised = (voice_preset or "").strip().lower().replace(" ", "_").replace("-", "_")
    if normalised in _VOICE_PRESETS:
        return normalised
    # Also accept Kokoro preset IDs (from tts_config.py)
    if normalised in _KOKORO_PRESET_MAP:
        return normalised
    return _DEFAULT_PRESET


def _resolve_voice_config(voice_preset: str) -> dict:
    if not voice_preset:
        return {"preset": _DEFAULT_PRESET, **_VOICE_PRESETS[_DEFAULT_PRESET]}
    normalised = _normalise_preset(voice_preset)
    if normalised in _VOICE_PRESETS:
        return {"preset": normalised, **_VOICE_PRESETS[normalised]}
    # Kokoro preset — use default ElevenLabs config for premium providers
    # but keep the Kokoro preset name so the local engine resolves the right voice.
    if normalised in _KOKORO_PRESET_MAP:
        base = _VOICE_PRESETS[_DEFAULT_PRESET].copy()
        base["preset"] = normalised
        return base
    # Accept a raw ElevenLabs voice ID (alphanumeric, ≥8 chars) as a passthrough.
    if len(voice_preset) >= 8 and voice_preset.replace("-", "").isalnum():
        base = _VOICE_PRESETS[_DEFAULT_PRESET].copy()
        base["voice_id"] = voice_preset
        return {"preset": _DEFAULT_PRESET, **base}
    logger.warning("[Narration] Unknown voice preset %r; defaulting to %s.", voice_preset, _DEFAULT_PRESET)
    return {"preset": _DEFAULT_PRESET, **_VOICE_PRESETS[_DEFAULT_PRESET]}


# ── LRU cache helpers ─────────────────────────────────────────────────────────

def _cache_key(text: str, preset: str, voice_id: str, model_id: str, settings: dict) -> str:
    digest = hashlib.sha256()
    digest.update(text.encode("utf-8"))
    digest.update(preset.encode("utf-8"))
    digest.update(voice_id.encode("utf-8"))
    digest.update(model_id.encode("utf-8"))
    digest.update(repr(sorted(settings.items())).encode("utf-8"))
    return digest.hexdigest()



def _cache_get(key: str):
    with _CACHE_LOCK:
        item = _TTS_CACHE.get(key)
        if item:
            _TTS_CACHE.move_to_end(key)
        return item


def _cache_put(key: str, value: dict):
    with _CACHE_LOCK:
        _TTS_CACHE[key] = value
        _TTS_CACHE.move_to_end(key)
        while len(_TTS_CACHE) > _MAX_CACHE_ITEMS:
            _TTS_CACHE.popitem(last=False)


# ── Audio utilities ───────────────────────────────────────────────────────────

def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Wrap raw signed-16-bit little-endian PCM bytes in a RIFF/WAV container.

    Gemini TTS returns raw PCM at 24000 Hz mono 16-bit LE.  Browsers require
    a proper container (WAV or MP3) for ``decodeAudioData``; raw PCM causes
    "Unable to decode audio data" errors.

    Args:
        pcm_bytes: Raw PCM samples.
        sample_rate: Samples per second (default 24000 — Gemini TTS output).
        channels: Number of audio channels (default 1 — mono).
        sample_width: Bytes per sample (default 2 — 16-bit / 2 bytes).
    """
    data_len = len(pcm_bytes)
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width
    bits_per_sample = sample_width * 8
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_len,      # ChunkSize: 4 (WAVE) + 8+16 (fmt) + 8+data_len (data)
        b'WAVE',
        b'fmt ',
        16,                 # Subchunk1Size for PCM
        1,                  # AudioFormat = PCM
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_len,
    )
    return header + pcm_bytes


def _audio_duration_ms(audio_bytes: bytes, mime_type: str) -> int:
    """Estimate audio duration in milliseconds from byte length and mime type.

    For WAV files, reads the byte-rate from the header for an accurate result.
    For compressed formats (MP3 etc.) falls back to ~128 kbps estimate.
    """
    n = len(audio_bytes)
    if mime_type in ("audio/wav", "audio/wave") and n > 44:
        try:
            # WAV fmt subchunk: byte rate is a 32-bit LE uint at offset 28.
            byte_rate = struct.unpack_from('<I', audio_bytes, 28)[0]
            if byte_rate > 0:
                data_bytes = n - 44  # approximate (standard 44-byte header)
                return max(500, int(data_bytes * 1000 / byte_rate))
        except Exception:
            pass
    # Default: assume ~128 kbps compressed audio (~16 000 bytes per second)
    return max(500, int(n / 16000 * 1000))


async def broadcast_narration_hook(session: Session, payload: dict, audience_user_ids: set[str] | None = None):
    """Broadcast a lightweight narration hook event without generating TTS audio."""
    message = {"type": "narration_hook", "payload": dict(payload or {})}
    if not audience_user_ids:
        await manager.broadcast(session.id, message)
        return
    for user_id in audience_user_ids:
        await manager.send_to(session.id, str(user_id), message)


# ── ElevenLabs direct HTTP helper ────────────────────────────────────────────

def _generate_elevenlabs_tts(text: str, preset: str, voice_id: str, model_id: str, settings: dict) -> tuple[bytes | None, dict]:
    """Call the ElevenLabs TTS REST API directly — no SDK required.

    Returns (mp3_bytes, metadata_dict). On any failure, mp3_bytes is None and
    metadata_dict describes the reason so the caller can fall through to the
    next provider.
    """
    api_key = _ELEVENLABS_API_KEY  # read from module-level constant (set at import)
    if not api_key:
        # Already logged at startup; don't repeat on every request.
        return None, {"provider": "browser_fallback", "cache_hit": False, "reason": "elevenlabs_key_missing"}

    url = _EL_TTS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": settings.get("stability", 0.5),
            "similarity_boost": settings.get("similarity_boost", 0.75),
            "style": settings.get("style", 0.0),
            "use_speaker_boost": settings.get("use_speaker_boost", True),
        },
    }

    try:
        logger.info(
            "[Narration] ElevenLabs request preset=%s voice=%s model=%s",
            preset, voice_id, model_id,
        )
        resp = requests.post(
            url,
            headers=headers,
            json=body,
            params={"output_format": _EL_OUTPUT_FORMAT},
            timeout=_EL_TIMEOUT,
        )
        if not resp.ok:
            snippet = resp.text[:300] if resp.text else "(empty)"
            logger.warning(
                "[Narration] ElevenLabs HTTP %s for preset=%s — %s",
                resp.status_code, preset, snippet,
            )
            return None, {
                "provider": "browser_fallback",
                "cache_hit": False,
                "reason": f"elevenlabs_http_{resp.status_code}",
            }
        audio = resp.content
        logger.info(
            "[Narration] ElevenLabs success preset=%s bytes=%d",
            preset, len(audio),
        )
        return audio, {"provider": "elevenlabs", "cache_hit": False, "reason": None}

    except requests.exceptions.Timeout:
        logger.warning("[Narration] ElevenLabs request timed out preset=%s", preset)
        return None, {"provider": "browser_fallback", "cache_hit": False, "reason": "elevenlabs_timeout"}
    except Exception as exc:
        logger.warning("[Narration] ElevenLabs request error preset=%s: %s", preset, exc)
        return None, {"provider": "browser_fallback", "cache_hit": False, "reason": f"elevenlabs_error:{exc}"}


# ── Gemini TTS direct HTTP helper ─────────────────────────────────────────────

def _generate_gemini_tts(text: str, preset: str) -> tuple[bytes | None, dict]:
    """Call the Gemini TTS REST API directly — no SDK required.

    Uses the ``generateContent`` endpoint with ``speechConfig`` to produce
    styled audio.  Returns (audio_bytes, metadata_dict).  On any failure,
    audio_bytes is ``None`` so the caller falls through to the next provider.
    """
    api_key = _GEMINI_API_KEY
    if not api_key:
        return None, {"provider": "browser_fallback", "cache_hit": False, "reason": "gemini_api_key_missing"}

    voice_cfg = _GEMINI_VOICE_MAP.get(preset) or _GEMINI_VOICE_MAP.get(_DEFAULT_PRESET) or {}
    voice_name = voice_cfg.get("voice_name", "Kore")
    style_prompt = str(voice_cfg.get("style_prompt") or "").strip()

    # Gemini TTS does not support stylePrompt inside speechConfig.  Instead,
    # prepend style/tone instructions to the text so they guide the model.
    # A blank line separates the instruction from the spoken content, which
    # helps the model treat the first line as a directive rather than dialogue.
    prompt_text = f"{style_prompt}\n\n{text}" if style_prompt else text

    url = _GEMINI_TTS_URL.format(model=_GEMINI_TTS_MODEL)
    body: dict = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name,
                    }
                },
            },
        },
    }

    try:
        logger.info(
            "[Narration] Gemini TTS request preset=%s voice=%s model=%s",
            preset, voice_name, _GEMINI_TTS_MODEL,
        )
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json=body,
            timeout=_GEMINI_TTS_TIMEOUT,
        )
        if not resp.ok:
            snippet = resp.text[:300] if resp.text else "(empty)"
            logger.warning(
                "[Narration] Gemini TTS HTTP %s preset=%s — %s",
                resp.status_code, preset, snippet,
            )
            return None, {
                "provider": "browser_fallback",
                "cache_hit": False,
                "reason": f"gemini_http_{resp.status_code}",
            }

        data = resp.json()
        # Extract audio from Gemini generateContent response structure:
        # candidates[0].content.parts[0].inlineData.{mimeType, data}
        candidates = data.get("candidates") or []
        if not candidates:
            logger.warning("[Narration] Gemini TTS returned no candidates for preset=%s", preset)
            return None, {"provider": "browser_fallback", "cache_hit": False, "reason": "gemini_no_candidates"}

        parts = (candidates[0].get("content") or {}).get("parts") or []
        inline_data = None
        for part in parts:
            if "inlineData" in part:
                inline_data = part["inlineData"]
                break

        if not inline_data or not inline_data.get("data"):
            logger.warning("[Narration] Gemini TTS response missing audio data for preset=%s", preset)
            return None, {"provider": "browser_fallback", "cache_hit": False, "reason": "gemini_no_audio_data"}

        audio = base64.b64decode(inline_data["data"])
        raw_mime = inline_data.get("mimeType") or ""
        logger.info(
            "[Narration] Gemini TTS raw mimeType='%s' decoded_bytes=%d preset=%s",
            raw_mime, len(audio), preset,
        )

        # Gemini TTS returns raw signed-16-bit little-endian PCM, not a
        # container format.  The browser's decodeAudioData requires a proper
        # container (WAV or MP3), so we wrap PCM in a WAV header here.
        # Typical Gemini mimeType values: "audio/L16;rate=24000", "audio/pcm",
        # "audio/raw" — or absent entirely.
        mime_lower = raw_mime.lower()
        is_raw_pcm = (
            not raw_mime
            or "l16" in mime_lower
            or "pcm" in mime_lower
            or "raw" in mime_lower
            or mime_lower.startswith("audio/l16")
        )
        if is_raw_pcm:
            # Extract sample rate from mime parameters if present, e.g.
            # "audio/L16;rate=24000"
            sample_rate = 24000  # Gemini TTS default
            for part in raw_mime.split(";"):
                kv = part.strip().split("=", 1)
                if len(kv) == 2 and kv[0].strip().lower() == "rate":
                    try:
                        sample_rate = int(kv[1].strip())
                    except ValueError:
                        pass
            wav_bytes = _pcm_to_wav(audio, sample_rate=sample_rate)
            logger.info(
                "[Narration] Gemini TTS: wrapped PCM→WAV sample_rate=%d pcm_bytes=%d wav_bytes=%d preset=%s",
                sample_rate, len(audio), len(wav_bytes), preset,
            )
            audio = wav_bytes
            mime_type = "audio/wav"
        else:
            mime_type = raw_mime
            logger.info("[Narration] Gemini TTS: using mime_type as-is: '%s' preset=%s", mime_type, preset)

        logger.info(
            "[Narration] Gemini TTS final data URI mime=%s bytes=%d preset=%s",
            mime_type, len(audio), preset,
        )
        return audio, {"provider": "gemini_tts", "cache_hit": False, "reason": None, "mime_type": mime_type}

    except requests.exceptions.Timeout:
        logger.warning("[Narration] Gemini TTS request timed out preset=%s", preset)
        return None, {"provider": "browser_fallback", "cache_hit": False, "reason": "gemini_timeout"}
    except Exception as exc:
        logger.warning("[Narration] Gemini TTS error preset=%s: %s", preset, exc)
        return None, {"provider": "browser_fallback", "cache_hit": False, "reason": f"gemini_error:{exc}"}


# ── OpenAI TTS helper ────────────────────────────────────────────────────────

def _generate_openai_tts(text: str, preset: str) -> tuple[bytes | None, dict]:
    """Call the OpenAI TTS REST API directly — used when ElevenLabs is unavailable."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None, {"provider": "browser_fallback", "cache_hit": False, "reason": "openai_api_key_missing"}

    voice_cfg = _OPENAI_VOICE_MAP.get(preset) or _OPENAI_VOICE_MAP.get(_DEFAULT_PRESET) or {}
    payload = {
        "model": _OPENAI_TTS_MODEL,
        "input": text,
        "voice": voice_cfg.get("voice", "alloy"),
        "response_format": "mp3",
        "speed": max(0.25, min(4.0, float(voice_cfg.get("speed", 1.0) or 1.0))),
    }
    instructions = str(voice_cfg.get("instructions") or "").strip()
    if instructions:
        payload["instructions"] = instructions

    try:
        logger.info(
            "[Narration] OpenAI TTS request preset=%s voice=%s model=%s",
            preset, payload["voice"], payload["model"],
        )
        resp = requests.post(
            _OPENAI_TTS_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=_OPENAI_TTS_TIMEOUT,
        )
        if not resp.ok:
            logger.warning(
                "[Narration] OpenAI TTS HTTP %s preset=%s — %s",
                resp.status_code, preset, resp.text[:300],
            )
            return None, {"provider": "browser_fallback", "cache_hit": False, "reason": f"openai_http_{resp.status_code}"}
        logger.info("[Narration] OpenAI TTS success preset=%s bytes=%d", preset, len(resp.content))
        return resp.content, {"provider": "openai_tts", "cache_hit": False, "reason": None}
    except Exception as exc:
        logger.warning("[Narration] OpenAI TTS error preset=%s: %s", preset, exc)
        return None, {"provider": "browser_fallback", "cache_hit": False, "reason": f"openai_error:{exc}"}


# ── Local Kokoro ONNX helper ─────────────────────────────────────────────────

async def _generate_local_kokoro_tts(text: str, preset: str) -> tuple[bytes | None, dict]:
    """Use the in-process Kokoro ONNX engine as a local TTS provider.

    Imports ``tts_server._kokoro`` lazily so this module can be loaded before
    the TTS startup sequence has run — the engine reference is resolved at
    call time, not at import time.
    """
    try:
        import tts_server as _tts_server  # lazy: avoids circular import at module load
        kokoro = getattr(_tts_server, "_kokoro", None)
        if kokoro is None or not kokoro.ready:
            return None, {
                "provider": "browser_fallback",
                "cache_hit": False,
                "reason": "kokoro_not_ready",
            }
        kokoro_cfg = _KOKORO_PRESET_MAP.get(preset, {})
        wav_bytes = await kokoro.generate(
            text,
            speed=kokoro_cfg.get("speed", _KOKORO_DEFAULT_SPEED),
            emotion=kokoro_cfg.get("default_emotion", _KOKORO_DEFAULT_EMOTION),
            voice_id=kokoro_cfg.get("voice_id", _KOKORO_DEFAULT_VOICE_ID),
            lang=kokoro_cfg.get("lang", "en-us"),
        )
        logger.info(
            "[Narration] Kokoro local TTS generated %d bytes preset=%s",
            len(wav_bytes), preset,
        )
        return wav_bytes, {
            "provider": "kokoro_local",
            "cache_hit": False,
            "reason": None,
            "mime_type": "audio/wav",
        }
    except Exception as exc:
        logger.warning("[Narration] Kokoro local TTS error preset=%s: %s", preset, exc)
        return None, {
            "provider": "browser_fallback",
            "cache_hit": False,
            "reason": f"kokoro_error:{exc}",
        }


# ── Main TTS orchestrator ────────────────────────────────────────────────────

async def _generate_tts(text: str, preset: str, voice_id: str, model_id: str, settings: dict) -> tuple[bytes | None, dict]:
    """Generate TTS audio, trying Gemini → ElevenLabs → OpenAI → browser fallback in order.

    Returns (audio_bytes_or_None, metadata_dict).
    The metadata dict always has keys: provider, cache_hit, reason.
    """
    key = _cache_key(text, preset, voice_id, model_id, settings)
    cached = _cache_get(key)
    if cached:
        logger.info("[Narration] Cache hit preset=%s voice=%s", preset, voice_id)
        return cached["audio"], {**cached["meta"], "cache_hit": True}

    logger.info("[Narration] TTS request started preset=%s gemini=%s elevenlabs=%s",
                preset, bool(_GEMINI_API_KEY), bool(_ELEVENLABS_API_KEY))

    # 1. Try Gemini TTS via direct HTTP (no SDK) — preferred provider.
    if _GEMINI_API_KEY:
        logger.info("[Narration] Provider selected: gemini_tts")
        audio, meta = _generate_gemini_tts(text, preset)
        if audio:
            logger.info("[Narration] Gemini TTS returned %d bytes for preset=%s", len(audio), preset)
            _cache_put(key, {"audio": audio, "meta": meta})
            return audio, meta
        logger.warning("[Narration] Gemini TTS failed for preset=%s reason=%s; trying next provider.",
                       preset, meta.get("reason"))

    # 2. Try ElevenLabs via direct HTTP (no SDK).
    if _ELEVENLABS_API_KEY:
        logger.info("[Narration] Provider selected: elevenlabs")
        audio, meta = _generate_elevenlabs_tts(text, preset, voice_id, model_id, settings)
        if audio:
            logger.info("[Narration] ElevenLabs returned %d bytes for preset=%s", len(audio), preset)
            _cache_put(key, {"audio": audio, "meta": meta})
            return audio, meta
        logger.warning("[Narration] ElevenLabs failed for preset=%s reason=%s; trying next provider.",
                       preset, meta.get("reason"))

    # 3. Try OpenAI TTS as tertiary premium provider.
    logger.info("[Narration] Provider selected: openai_tts")
    audio, meta = _generate_openai_tts(text, preset)
    if audio:
        logger.info("[Narration] OpenAI TTS returned %d bytes for preset=%s", len(audio), preset)
        _cache_put(key, {"audio": audio, "meta": meta})
        return audio, meta

    # 4. Try local Kokoro ONNX engine (in-process, no API key required).
    logger.info("[Narration] Provider selected: kokoro_local")
    audio, meta = await _generate_local_kokoro_tts(text, preset)
    if audio:
        logger.info("[Narration] Kokoro local TTS returned %d bytes for preset=%s", len(audio), preset)
        _cache_put(key, {"audio": audio, "meta": meta})
        return audio, meta
    logger.warning("[Narration] Kokoro local TTS unavailable for preset=%s reason=%s; browser fallback.",
                   preset, meta.get("reason"))

    # 5. All providers unavailable — signal browser fallback.
    reason = meta.get("reason") or "premium_unavailable"
    if reason == "openai_api_key_missing" and not _ELEVENLABS_API_KEY and not _GEMINI_API_KEY:
        reason = "premium_unavailable"
    logger.warning("[Narration] All TTS providers failed for preset=%s; browser fallback. reason=%s",
                   preset, reason)
    return None, {"provider": "browser_fallback", "cache_hit": False, "reason": reason}


# ── WebSocket message handlers ───────────────────────────────────────────────

async def handle_narration_speak(payload: dict, session: Session, user: User):
    """DM-only handler: generate TTS and broadcast narration_speak to all players."""
    if user.role != "dm" and not assistant_dm_has_scope(session, user, "narration.broadcast"):
        return

    text = str(payload.get("text") or "").strip()[:_MAX_TEXT_LEN]
    if not text:
        return

    voice_preset = str(payload.get("voice_preset") or payload.get("voice_id") or "").strip()
    config = _resolve_voice_config(voice_preset)
    policy = str(payload.get("policy") or "replace_current").strip()
    if policy not in _VALID_POLICY_MODES:
        policy = "replace_current"

    audio_bytes, tts_meta = await _generate_tts(
        text=text,
        preset=config["preset"],
        voice_id=config["voice_id"],
        model_id=config["model_id"],
        settings=config["settings"],
    )

    broadcast_payload: dict = {
        "text": text,
        "policy": policy,
        "voice_preset": config["preset"],
        "tts_provider": tts_meta["provider"],
        "tts_cache_hit": bool(tts_meta.get("cache_hit")),
        "tts_fallback_reason": tts_meta.get("reason"),
        "fallback_voice": config["fallback"],
    }
    if audio_bytes:
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        mime_type = tts_meta.get("mime_type") or "audio/mpeg"
        broadcast_payload["audio_data_uri"] = f"data:{mime_type};base64,{audio_b64}"
        broadcast_payload["audio_duration_ms"] = _audio_duration_ms(audio_bytes, mime_type)

    logger.info(
        "[Narration] Broadcast preset=%s provider=%s cache_hit=%s fallback_reason=%s",
        config["preset"],
        broadcast_payload["tts_provider"],
        broadcast_payload["tts_cache_hit"],
        broadcast_payload["tts_fallback_reason"],
    )
    await manager.broadcast(session.id, {"type": "narration_speak", "payload": broadcast_payload})


async def handle_narration_stop(payload: dict, session: Session, user: User):
    """DM-only handler: stop all in-progress narration for the session."""
    if user.role != "dm" and not assistant_dm_has_scope(session, user, "narration.broadcast"):
        return
    await manager.broadcast(session.id, {"type": "narration_stop", "payload": {}})
