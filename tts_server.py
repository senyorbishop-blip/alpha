"""
tts_server.py — FastAPI TTS router and GPU startup sequence.

Startup sequence (called from main.py lifespan via startup_tts()):
  1. Detect CUDA device, log GPU name + VRAM
  2. Load Chatterbox  → CUDA (parallel with Dia)
  3. Load Dia         → CUDA (parallel with Chatterbox)
  4. Load Kokoro      → CPU  (parallel with GPU engines)
  5. Warmup each engine (pre-JIT CUDA kernels)
  6. Pre-generate 20 warmup phrases → RAM cache
  7. Log final status table

API endpoints (mounted at /api/tts by main.py):
  POST /api/tts/speak
  POST /api/tts/speak-npc-conversation
  GET  /api/tts/voices
  GET  /api/tts/status
  GET  /api/tts/warmup-phrases
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from tts_config import VOICE_PRESETS, WARMUP_PHRASES
from tts_cache import get_cache
from tts_engines import ChatterboxEngine, DiaEngine, KokoroEngine
from tts_router import TTSRouter

logger = logging.getLogger("tts_server")

# ---------------------------------------------------------------------------
# Engine singletons — loaded at startup and kept resident in memory/VRAM
# ---------------------------------------------------------------------------
_chatterbox: ChatterboxEngine | None = None
_dia:        DiaEngine        | None = None
_kokoro:     KokoroEngine     | None = None
_router:     TTSRouter        | None = None
_startup_ok: bool = False
_stack_summary: dict = {
    "primary_path": "uninitialised",
    "fallback_path": "uninitialised",
    "notes": [],
}


# ===========================================================================
# startup_tts() — called from main.py lifespan
# ===========================================================================

async def startup_tts() -> None:
    """
    Load all three TTS engines, warm them up, and pre-fill the phrase cache.
    This must be awaited inside the FastAPI lifespan context manager so that
    engines are ready before the first request arrives.
    """
    global _chatterbox, _dia, _kokoro, _router, _startup_ok, _stack_summary

    # ── Step 1: Detect CUDA ─────────────────────────────────────────────────
    gpu_name     = "N/A"
    vram_total   = 0
    cuda_ok      = False

    try:
        import torch
        if torch.cuda.is_available():
            cuda_ok    = True
            gpu_name   = torch.cuda.get_device_name(0)
            props      = torch.cuda.get_device_properties(0)
            vram_total = props.total_memory // 1_048_576
            logger.info(
                f"[TTS] CUDA device: {gpu_name}  "
                f"VRAM: {vram_total} MB  "
                f"CUDA: {torch.version.cuda}"
            )
        else:
            logger.warning(
                "[TTS] CUDA not available — "
                "Chatterbox and Dia will fail gracefully; Kokoro (CPU) active"
            )
    except ImportError:
        logger.warning("[TTS] PyTorch not installed — GPU engines disabled")

    # ── Create engine objects ────────────────────────────────────────────────
    _chatterbox = ChatterboxEngine()
    _dia        = DiaEngine()
    _kokoro     = KokoroEngine()

    # Per-engine timing stats for the final status log
    cb_ms  = 0;  cb_vram  = 0
    dia_ms = 0;  dia_vram = 0
    ko_ms  = 0

    # ── Steps 2-4: Load all engines in parallel threads ─────────────────────
    load_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="tts_load")
    loop      = asyncio.get_event_loop()

    def _load_chatterbox() -> None:
        nonlocal cb_ms, cb_vram
        try:
            _chatterbox.load()
            cb_vram = _chatterbox._vram_mb_loaded
            # Step 5 warmup (Chatterbox)
            cb_ms = round(_chatterbox.warmup())
        except Exception as exc:
            logger.error(f"[TTS] Chatterbox load/warmup FAILED: {exc}", exc_info=True)

    def _load_dia() -> None:
        nonlocal dia_ms, dia_vram
        try:
            _dia.load()
            dia_vram = _dia._vram_mb_loaded
            # Step 5 warmup (Dia)
            dia_ms = round(_dia.warmup())
        except Exception as exc:
            logger.error(f"[TTS] Dia load/warmup FAILED: {exc}", exc_info=True)

    def _load_kokoro() -> None:
        nonlocal ko_ms
        try:
            _kokoro.load()
            # Step 5 warmup (Kokoro)
            ko_ms = round(_kokoro.warmup())
        except Exception as exc:
            logger.error(f"[TTS] Kokoro load/warmup FAILED: {exc}", exc_info=True)

    await asyncio.gather(
        loop.run_in_executor(load_pool, _load_chatterbox),
        loop.run_in_executor(load_pool, _load_dia),
        loop.run_in_executor(load_pool, _load_kokoro),
        return_exceptions=True,
    )
    load_pool.shutdown(wait=False)

    # ── Build router after engines are loaded ────────────────────────────────
    _router = TTSRouter(_chatterbox, _dia, _kokoro)

    if _kokoro.ready:
        logger.info("[TTS] Kokoro engine active — CPU fallback available")
    else:
        logger.warning("[TTS] Kokoro engine NOT ready — no local CPU fallback")

    if _kokoro.ready:
        primary_path = "kokoro"
        fallback_path = "browser_fallback"
    elif _chatterbox.ready or _dia.ready:
        primary_path = "gpu_engine_only"
        fallback_path = "request_failure_no_local_cpu_fallback"
    else:
        primary_path = "unavailable"
        fallback_path = "browser_fallback"

    notes = []
    if _chatterbox.ready and _dia.ready:
        notes.append("GPU engines loaded for optional high-fidelity presets and NPC conversation.")
    elif _chatterbox.ready or _dia.ready:
        notes.append("One GPU engine loaded; some cinematic presets may be unavailable.")
    else:
        notes.append("GPU engines unavailable; narration relies on Kokoro or browser fallback.")
    if _kokoro.ready:
        notes.append("Kokoro is the guaranteed local path for default voice presets in tts_config.py.")
    else:
        notes.append("Kokoro failed to initialise; check /api/tts/status for last_error details.")
    _stack_summary = {
        "primary_path": primary_path,
        "fallback_path": fallback_path,
        "notes": notes,
    }
    logger.info(
        "[TTS] stack summary: primary=%s fallback=%s",
        _stack_summary["primary_path"],
        _stack_summary["fallback_path"],
    )

    # ── Step 6: Pre-generate warmup phrases → RAM cache ─────────────────────
    cache         = get_cache()
    cached_count  = 0
    any_gpu_ready = _chatterbox.ready or _dia.ready
    any_ready     = any_gpu_ready or _kokoro.ready

    if any_ready:
        # Use grand_narrator (Chatterbox) if GPU is up; else system_voice (Kokoro)
        warmup_preset = "grand_narrator" if _chatterbox.ready else "system_voice"

        for phrase in WARMUP_PHRASES:
            if cache.contains(phrase, warmup_preset, 1.0):
                cached_count += 1
                continue
            try:
                audio, eng = await _router.route(phrase, warmup_preset, 1.0, "neutral")
                cache.put(phrase, warmup_preset, 1.0, audio)
                cached_count += 1
                logger.debug(f"[TTS] cached via {eng}: '{phrase[:45]}'")
            except Exception as exc:
                logger.warning(f"[TTS] pre-cache failed for '{phrase[:35]}': {exc}")

    # ── Step 7: Final status log ─────────────────────────────────────────────
    cb_tag  = "GPU ✓" if _chatterbox.ready else "GPU ✗"
    dia_tag = "GPU ✓" if _dia.ready        else "GPU ✗"
    ko_tag  = "CPU ✓" if _kokoro.ready     else "CPU ✗"

    logger.info("✓ Tavern TTS ready")
    logger.info(f"  ├─ Chatterbox  [{cb_tag}]  VRAM: {cb_vram}MB   warmup: {cb_ms}ms")
    logger.info(f"  ├─ Dia         [{dia_tag}]  VRAM: {dia_vram}MB   warmup: {dia_ms}ms")
    logger.info(f"  └─ Kokoro      [{ko_tag}]               warmup: {ko_ms}ms")
    logger.info(f"  └─ RAM cache: {cached_count} phrases pre-rendered")

    _startup_ok = True


# ===========================================================================
# FastAPI router
# ===========================================================================

tts_router = APIRouter(prefix="/api/tts", tags=["tts"])


# ── Request / Response models ────────────────────────────────────────────────

class SpeakRequest(BaseModel):
    text:         str   = Field(..., min_length=1, max_length=4000)
    voice_preset: str   = Field(default="grand_narrator")
    speed:        float = Field(default=1.0, ge=0.5, le=2.0)
    emotion:      str   = Field(default="neutral")


class NPCLine(BaseModel):
    speaker:      str
    text:         str
    voice_preset: str


class NPCConversationRequest(BaseModel):
    lines: list[NPCLine] = Field(..., min_length=1)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _require_router() -> TTSRouter:
    if _router is None:
        raise HTTPException(503, detail="TTS engines not yet initialised — server is still starting up")
    return _router


def _wav_streaming_response(wav_bytes: bytes, cache_hit: bool, engine: str, latency_ms: float) -> StreamingResponse:
    return StreamingResponse(
        iter([wav_bytes]),
        media_type="audio/wav",
        headers={
            "X-TTS-Cache":      "hit" if cache_hit else "miss",
            "X-TTS-Engine":     engine,
            "X-TTS-Latency-Ms": str(round(latency_ms)),
            "Cache-Control":    "no-store",
        },
    )


# ── POST /api/tts/speak ──────────────────────────────────────────────────────

@tts_router.post("/speak")
async def speak(req: SpeakRequest):
    """
    Generate TTS audio for the given text and voice preset.

    1. Check RAM cache → serve instantly on hit (sub-1ms)
    2. Route to engine → generate
    3. Store in RAM cache for future requests
    4. Stream WAV bytes to client
    """
    router = _require_router()

    text  = req.text.strip()
    cache = get_cache()
    t0    = time.perf_counter()

    # Cache hit
    cached = cache.get(text, req.voice_preset, req.speed)
    if cached:
        latency = (time.perf_counter() - t0) * 1_000
        logger.info(
            f"[TTS] CACHE HIT  preset={req.voice_preset}  "
            f"speed={req.speed}  chars={len(text)}  latency_ms={latency:.1f}"
        )
        return _wav_streaming_response(cached, True, "cache", latency)

    # Generate
    try:
        audio, engine = await router.route(
            text, req.voice_preset, req.speed, req.emotion
        )
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc))

    latency = (time.perf_counter() - t0) * 1_000
    logger.info(
        f"[TTS] GENERATED  engine={engine}  preset={req.voice_preset}  "
        f"speed={req.speed}  emotion={req.emotion}  chars={len(text)}  "
        f"bytes={len(audio)}  latency_ms={latency:.1f}"
    )

    cache.put(text, req.voice_preset, req.speed, audio)

    return _wav_streaming_response(audio, False, engine, latency)


# ── POST /api/tts/speak-npc-conversation ────────────────────────────────────

@tts_router.post("/speak-npc-conversation")
async def speak_npc_conversation(req: NPCConversationRequest):
    """
    Generate a multi-speaker NPC conversation as a single WAV clip.
    Uses Dia's [S1]/[S2] speaker tokens for natural transitions.
    """
    if _dia is None or not _dia.ready:
        raise HTTPException(503, detail="Dia engine not ready")

    t0 = time.perf_counter()
    audio = await _dia.generate_conversation([line.model_dump() for line in req.lines])
    latency = (time.perf_counter() - t0) * 1_000

    logger.info(
        f"[TTS] NPC-CONVO  lines={len(req.lines)}  "
        f"bytes={len(audio)}  latency_ms={latency:.1f}"
    )
    return StreamingResponse(iter([audio]), media_type="audio/wav")


# ── GET /api/tts/voices ──────────────────────────────────────────────────────

@tts_router.get("/voices")
async def get_voices():
    """Return all voice presets grouped by display group, with engine readiness flags."""
    grouped: dict[str, list] = {"narrator": [], "npc": [], "system": []}
    for p in VOICE_PRESETS:
        grp = p.get("group", "system")
        if grp in grouped:
            grouped[grp].append(p)

    return {
        "presets": VOICE_PRESETS,
        "grouped": grouped,
        "engines": {
            "kokoro": {"ready": _kokoro.ready if _kokoro else False},
        },
        "stack": _stack_summary,
    }


# ── GET /api/tts/status ──────────────────────────────────────────────────────

@tts_router.get("/status")
async def get_status():
    """Return engine health, VRAM usage, queue depths, and cache statistics."""
    cache = get_cache()
    router_diag = _router.diagnostics() if _router and hasattr(_router, "diagnostics") else {}
    return {
        "tts_available": True,
        "chatterbox": _chatterbox.status() if _chatterbox else {"ready": False},
        "dia":        _dia.status()        if _dia        else {"ready": False},
        "kokoro":     _kokoro.status()     if _kokoro     else {"ready": False},
        "stack":      _stack_summary,
        "routing":    router_diag,
        "cache_hits":    cache.hits(),
        "cache_misses":  cache.misses(),
        "cache_size":    cache.size(),
        "cache_size_mb": round(cache.size_bytes() / 1_048_576, 2),
        "startup_ok":    _startup_ok,
        "startup_error": None,
    }


# ── GET /api/tts/warmup-phrases ──────────────────────────────────────────────

@tts_router.get("/warmup-phrases")
async def get_warmup_phrases():
    """Return the list of pre-cached phrases so the frontend can show quick-insert chips."""
    return {"phrases": WARMUP_PHRASES}
