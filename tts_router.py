"""
tts_router.py — Request routing logic and Dia nonverbal tag injection.

Routing priority:
  voice_preset.engine == "chatterbox"  →  ChatterboxEngine (GPU)
  voice_preset.engine == "dia"         →  DiaEngine (GPU, inject tags)
  voice_preset.engine == "kokoro"      →  KokoroEngine (CPU)
  any engine FAILS or not ready        →  KokoroEngine (CPU fallback)

Nonverbal injection (Dia only):
  inject_nonverbals(text, preset_id, emotion) → tagged_text
  Rules defined in spec; never >2 tags per response;
  never mid-word or inside dialogue quotes.
"""

from __future__ import annotations

import logging
import random
import re
import time
from typing import TYPE_CHECKING

from tts_config import PRESET_BY_ID

if TYPE_CHECKING:
    from tts_engines import ChatterboxEngine, DiaEngine, KokoroEngine

logger = logging.getLogger("tts_router")


# ===========================================================================
# Nonverbal tag injection helpers
# ===========================================================================

def _sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?]+", text))


def _sentence_boundary_positions(text: str) -> list[int]:
    """Return character positions AFTER each sentence-ending punctuation + whitespace."""
    return [m.end() for m in re.finditer(r"[.!?]+\s+", text)]


def _inside_quotes(text: str, pos: int) -> bool:
    """Return True if character position is inside a double-quote span."""
    before = text[:pos]
    # Odd number of quotes means we're inside a quoted string
    return before.count('"') % 2 == 1


def _insert_tag_at_boundaries(
    text:        str,
    tag:         str,
    probability: float = 0.30,
    max_inserts: int   = 1,
) -> str:
    """Insert `tag` at random sentence boundaries respecting quote constraints."""
    boundaries = _sentence_boundary_positions(text)
    if not boundaries:
        return text

    inserted = 0
    offset   = 0
    for raw_pos in boundaries:
        if inserted >= max_inserts:
            break
        if random.random() >= probability:
            continue
        pos = raw_pos + offset
        if _inside_quotes(text, pos):
            continue
        text    = text[:pos] + tag + " " + text[pos:]
        offset += len(tag) + 1
        inserted += 1

    return text


def inject_nonverbals(text: str, preset_id: str, emotion: str) -> str:
    """
    Inject Dia nonverbal tags into text according to voice preset rules.

    Contract:
      - Never inject more than 2 tags per response
      - Never inject mid-word
      - Never inject inside dialogue quotes
    """
    tags_injected = 0

    # Rule 1: dramatic + ellipsis → [sighs]
    if emotion == "dramatic" and "..." in text and tags_injected < 2:
        text = text.replace("...", "[sighs]", 1)
        tags_injected += 1

    # Rule 2: tavern_keeper + ends with "!" → append [laughs]
    if (
        preset_id == "tavern_keeper"
        and text.rstrip().endswith("!")
        and tags_injected < 2
    ):
        text = text.rstrip() + " [laughs]"
        tags_injected += 1

    # Rule 3: dwarven_elder + >2 sentences → [coughs] between sentences (30%)
    if (
        preset_id == "dwarven_elder"
        and _sentence_count(text) > 2
        and tags_injected < 2
    ):
        text = _insert_tag_at_boundaries(
            text, "[coughs]", probability=0.30, max_inserts=1
        )
        tags_injected += 1

    # Rule 4: wounded_guard → [coughs] after every 2 sentences
    if preset_id == "wounded_guard" and tags_injected < 2:
        sentences_seen = 0
        result         = []
        for ch in text:
            result.append(ch)
            if ch in ".!?":
                sentences_seen += 1
                if sentences_seen % 2 == 0 and tags_injected < 2:
                    result.append(" [coughs]")
                    tags_injected += 1
        text = "".join(result)

    # Rule 5: shadow_villain + menacing → occasional [sighs]
    if (
        preset_id == "shadow_villain"
        and emotion == "menacing"
        and tags_injected < 2
    ):
        text = _insert_tag_at_boundaries(
            text, "[sighs]", probability=0.40, max_inserts=1
        )
        tags_injected += 1

    return text


# ===========================================================================
# TTSRouter
# ===========================================================================

class TTSRouter:
    """
    Routes each TTS generate request to the appropriate engine.

    Falls back to KokoroEngine (CPU) if:
      - the target GPU engine is not ready (failed to load)
      - the target GPU engine raises an exception during inference
      - the GPU is detected as busy (queue_depth > threshold)
    """

    _GPU_BUSY_THRESHOLD = 3   # fall back if queue depth exceeds this

    def __init__(
        self,
        chatterbox: "ChatterboxEngine",
        dia:        "DiaEngine",
        kokoro:     "KokoroEngine",
    ) -> None:
        self._chatterbox = chatterbox
        self._dia        = dia
        self._kokoro     = kokoro
        self._last_route: dict = {
            "target_engine": None,
            "engine_used": None,
            "fallback_active": False,
            "fallback_reason": None,
            "error": None,
            "timestamp": None,
        }

    # ── Public routing entry point ───────────────────────────────────────────

    async def route(
        self,
        text:           str,
        voice_preset_id: str,
        speed:          float,
        emotion:        str,
    ) -> tuple[bytes, str]:
        """
        Returns (wav_bytes, engine_name).
        engine_name is one of: "chatterbox" | "dia" | "kokoro" | "kokoro_fallback"
        """
        preset = PRESET_BY_ID.get(voice_preset_id)
        if not preset:
            logger.warning(
                f"[TTSRouter] unknown preset '{voice_preset_id}'; "
                f"falling back to system_voice"
            )
            preset = PRESET_BY_ID["system_voice"]

        target_engine = preset["engine"]
        # Honour caller's speed override, otherwise use preset default
        effective_speed = speed if speed != 1.0 else preset["speed"]
        effective_emotion = emotion or preset.get("default_emotion", "neutral")
        fallback_reason = None

        # ── Try target engine ────────────────────────────────────────────────
        try:
            if target_engine == "chatterbox":
                audio, name = await self._try_chatterbox(
                    text, effective_speed, effective_emotion
                )
                if audio is not None:
                    self._set_last_route(target_engine, name, False, None, None)
                    return audio, name
                fallback_reason = "chatterbox_unavailable_or_busy"

            elif target_engine == "dia":
                audio, name = await self._try_dia(
                    text, voice_preset_id, effective_speed, effective_emotion
                )
                if audio is not None:
                    self._set_last_route(target_engine, name, False, None, None)
                    return audio, name
                fallback_reason = "dia_unavailable_or_busy"

            elif target_engine == "kokoro":
                voice_id = preset.get("voice_id", "am_michael")
                lang = preset.get("lang", "en-us")
                audio = await self._kokoro.generate(
                    text, effective_speed, effective_emotion, voice_id=voice_id, lang=lang
                )
                self._set_last_route(target_engine, "kokoro", False, None, None)
                return audio, "kokoro"

        except Exception as exc:
            fallback_reason = f"{target_engine}_error"
            logger.error(
                f"[TTSRouter] target engine={target_engine} FAILED: {exc}",
                exc_info=True,
            )
            self._set_last_route(target_engine, None, True, fallback_reason, str(exc))

        # ── CPU fallback ─────────────────────────────────────────────────────
        audio, engine_name = await self._fallback_kokoro(text)
        self._set_last_route(
            target_engine,
            engine_name,
            True,
            fallback_reason or "target_engine_unavailable",
            None,
        )
        return audio, engine_name

    # ── Engine-specific helpers ──────────────────────────────────────────────

    async def _try_chatterbox(
        self, text: str, speed: float, emotion: str
    ) -> tuple[bytes | None, str]:
        if not self._chatterbox.ready:
            logger.warning("[TTSRouter] Chatterbox not ready; routing to Kokoro")
            return None, ""
        if self._chatterbox._queue_depth > self._GPU_BUSY_THRESHOLD:
            logger.warning("[TTSRouter] Chatterbox queue full; routing to Kokoro")
            return None, ""
        audio = await self._chatterbox.generate(text, speed, emotion)
        return audio, "chatterbox"

    async def _try_dia(
        self, text: str, preset_id: str, speed: float, emotion: str
    ) -> tuple[bytes | None, str]:
        if not self._dia.ready:
            logger.warning("[TTSRouter] Dia not ready; routing to Kokoro")
            return None, ""
        if self._dia._queue_depth > self._GPU_BUSY_THRESHOLD:
            logger.warning("[TTSRouter] Dia queue full; routing to Kokoro")
            return None, ""
        tagged = inject_nonverbals(text, preset_id, emotion)
        dia_text = f"[S1] {tagged}"
        audio = await self._dia.generate(dia_text, speed, emotion)
        return audio, "dia"

    async def _fallback_kokoro(self, text: str) -> tuple[bytes, str]:
        if not self._kokoro.ready:
            raise RuntimeError(
                "All TTS engines unavailable: Chatterbox and Dia failed, "
                "Kokoro not loaded."
            )
        logger.warning("[TTSRouter] using Kokoro CPU fallback")
        audio = await self._kokoro.generate(
            text, speed=1.0, emotion="neutral", voice_id="am_michael"
        )
        return audio, "kokoro_fallback"

    def _set_last_route(
        self,
        target_engine: str | None,
        engine_used: str | None,
        fallback_active: bool,
        fallback_reason: str | None,
        error: str | None,
    ) -> None:
        self._last_route = {
            "target_engine": target_engine,
            "engine_used": engine_used,
            "fallback_active": bool(fallback_active),
            "fallback_reason": fallback_reason,
            "error": error,
            "timestamp": int(time.time()),
        }

    def diagnostics(self) -> dict:
        return dict(self._last_route)
