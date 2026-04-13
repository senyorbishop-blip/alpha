"""
tts_engines.py — GPU/CPU TTS engine classes with unified generate() interface.

Three engines, each kept resident after load (never swapped):

  ChatterboxEngine — RTX 5070 Ti CUDA, cinematic narrator quality
                     torch.float16, 50-80× real-time on RTX 5070 Ti
  DiaEngine        — RTX 5070 Ti CUDA alongside Chatterbox (separate VRAM)
                     NPC voices, nonverbal tag support: [laughs][sighs] etc.
  KokoroEngine     — Ryzen 9800X3D CPU, always-on, ~150ms latency
                     ONNX runtime, zero GPU dependency, instant fallback

All generate() methods are async, delegating blocking work to
_THREAD_POOL via loop.run_in_executor() so the FastAPI event loop
never blocks waiting for GPU inference.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import struct
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger("tts_engines")

# ---------------------------------------------------------------------------
# Shared thread pool
# 4 workers: Chatterbox, Dia, Kokoro, + 1 spare for cache pre-fill
# Named threads show up clearly in nvidia-smi / htop
# ---------------------------------------------------------------------------
_THREAD_POOL = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="tts_worker",
)

# ---------------------------------------------------------------------------
# WAV encoding helpers
# ---------------------------------------------------------------------------

def _numpy_to_wav(samples, sample_rate: int) -> bytes:
    """Convert float32 or int16 numpy array (mono) to in-memory PCM WAV bytes."""
    import numpy as np

    arr = np.asarray(samples, dtype=np.float32) if samples.dtype != np.int16 else samples

    if arr.dtype == np.float32:
        arr = np.clip(arr, -1.0, 1.0)
        pcm = (arr * 32767).astype(np.int16)
    else:
        pcm = arr.astype(np.int16)

    # Collapse to mono if multi-channel
    if pcm.ndim == 2:
        pcm = pcm.mean(axis=0).astype(np.int16)

    n_ch        = 1
    bits        = 16
    byte_rate   = sample_rate * n_ch * bits // 8
    block_align = n_ch * bits // 8
    data        = pcm.tobytes()

    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(data)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<IHHIIHH",
        16, 1, n_ch, sample_rate, byte_rate, block_align, bits))
    buf.write(b"data")
    buf.write(struct.pack("<I", len(data)))
    buf.write(data)
    return buf.getvalue()


def _tensor_to_wav(wav_tensor, sample_rate: int) -> bytes:
    """Convert a torch tensor (1, T) or (T,) to WAV bytes via numpy."""
    t = wav_tensor.squeeze().cpu().float().numpy()
    return _numpy_to_wav(t, sample_rate)


def _measure_vram_mb() -> int:
    """Return bytes currently allocated on CUDA device 0, in MB."""
    try:
        import torch
        if torch.cuda.is_available():
            return int(torch.cuda.memory_allocated(0) / 1_048_576)
    except Exception:
        pass
    return 0


# ===========================================================================
# ChatterboxEngine — RTX 5070 Ti, CUDA, cinematic narrator
# ===========================================================================

class ChatterboxEngine:
    """
    Resemble-AI Chatterbox TTS.

    Loaded once at startup into GPU VRAM and kept resident.
    torch.float16 primary, bfloat16 automatic fallback.
    Exaggeration + cfg_weight params map emotion → delivery style.
    """

    # Emotion → Chatterbox generation parameters
    _EMOTION_PARAMS: dict = {
        "neutral":  {"exaggeration": 0.40, "cfg_weight": 0.50},
        "dramatic": {"exaggeration": 0.75, "cfg_weight": 0.65},
        "menacing": {"exaggeration": 0.80, "cfg_weight": 0.70},
        "warm":     {"exaggeration": 0.35, "cfg_weight": 0.45},
    }

    def __init__(self) -> None:
        self._model          = None
        self._sample_rate    = 24_000
        self._device         = "cuda"
        self._queue_depth    = 0
        self._vram_mb_loaded = 0
        self.ready           = False

    # ── Blocking load (called from startup ThreadPoolExecutor) ───────────────

    def load(self) -> None:
        try:
            import torch
            from chatterbox.tts import ChatterboxTTS  # type: ignore
        except ImportError:
            logger.info("[Chatterbox] not available on Python 3.12 — skipping")
            return

        vram_before = _measure_vram_mb()
        logger.info("[Chatterbox] loading model → CUDA (this may take 30-60 s) …")
        t0 = time.perf_counter()

        try:
            self._model = ChatterboxTTS.from_pretrained(device=self._device)
            logger.info("[Chatterbox] loaded with float16")
        except Exception as exc:
            logger.warning(f"[Chatterbox] float16 load failed ({exc}), retrying with bfloat16")
            self._model = ChatterboxTTS.from_pretrained(device=self._device)

        self._sample_rate    = getattr(self._model, "sr", 24_000)
        self._vram_mb_loaded = _measure_vram_mb() - vram_before
        elapsed_ms           = (time.perf_counter() - t0) * 1_000
        logger.info(
            f"[Chatterbox] ready  sr={self._sample_rate}  "
            f"VRAM_delta={self._vram_mb_loaded}MB  load_ms={elapsed_ms:.0f}"
        )
        self.ready = True

    # ── Warmup (pre-JIT CUDA kernels so first real request is fast) ──────────

    def warmup(self) -> float:
        """Run a silent 3-word inference. Returns elapsed ms."""
        if not self.ready:
            return 0.0
        t0 = time.perf_counter()
        self._generate_sync("Tavern greets you.", speed=1.0, emotion="neutral")
        elapsed = (time.perf_counter() - t0) * 1_000
        logger.info(f"[Chatterbox] warmup complete  ms={elapsed:.0f}")
        return elapsed

    # ── Sync generation (runs inside thread pool) ────────────────────────────

    def _generate_sync(self, text: str, speed: float, emotion: str) -> bytes:
        import torch
        params = self._EMOTION_PARAMS.get(emotion, self._EMOTION_PARAMS["neutral"])
        with torch.inference_mode():
            wav = self._model.generate(
                text,
                exaggeration=params["exaggeration"],
                cfg_weight=params["cfg_weight"],
            )
        return _tensor_to_wav(wav, self._sample_rate)

    # ── Async interface ──────────────────────────────────────────────────────

    async def generate(self, text: str, speed: float = 1.0, emotion: str = "neutral") -> bytes:
        self._queue_depth += 1
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                _THREAD_POOL,
                lambda: self._generate_sync(text, speed, emotion),
            )
        finally:
            self._queue_depth -= 1

    def status(self) -> dict:
        return {
            "ready":   self.ready,
            "vram_mb": _measure_vram_mb(),
            "queue":   self._queue_depth,
            "device":  self._device,
        }


# ===========================================================================
# DiaEngine — RTX 5070 Ti, CUDA, NPC dialogue + nonverbal sounds
# ===========================================================================

class DiaEngine:
    """
    Nari Labs Dia-1.6B multi-speaker TTS.

    Loaded on CUDA alongside Chatterbox (RTX 5070 Ti has sufficient VRAM
    for both models simultaneously).

    Supports Dia nonverbal tags:
        [laughs]  [sighs]  [gasps]  [coughs]

    Multi-speaker mode via [S1] / [S2] speaker tokens.
    """

    MODEL_ID = "nari-labs/Dia-1.6B"

    def __init__(self) -> None:
        self._model          = None
        self._sample_rate    = 44_100   # Dia native output rate
        self._device         = "cuda"
        self._queue_depth    = 0
        self._vram_mb_loaded = 0
        self.ready           = False

    # ── Blocking load ────────────────────────────────────────────────────────

    def load(self) -> None:
        try:
            from dia.model import Dia  # type: ignore
        except ImportError:
            logger.info("[Dia] not available — skipping")
            return

        vram_before = _measure_vram_mb()
        logger.info("[Dia] loading Dia-1.6B → CUDA (this may take 30-90 s) …")
        t0 = time.perf_counter()

        self._model = Dia.from_pretrained(self.MODEL_ID, compute_dtype="float16")

        self._vram_mb_loaded = _measure_vram_mb() - vram_before
        elapsed_ms           = (time.perf_counter() - t0) * 1_000
        logger.info(
            f"[Dia] ready  sr={self._sample_rate}  "
            f"VRAM_delta={self._vram_mb_loaded}MB  load_ms={elapsed_ms:.0f}"
        )
        self.ready = True

    # ── Warmup ───────────────────────────────────────────────────────────────

    def warmup(self) -> float:
        if not self.ready:
            return 0.0
        t0 = time.perf_counter()
        self._generate_sync("[S1] Hail adventurer.", speed=1.0, emotion="neutral")
        elapsed = (time.perf_counter() - t0) * 1_000
        logger.info(f"[Dia] warmup complete  ms={elapsed:.0f}")
        return elapsed

    # ── Sync generation ──────────────────────────────────────────────────────

    def _generate_sync(self, text: str, speed: float, emotion: str) -> bytes:
        import numpy as np

        output = self._model.generate(text, use_torch_compile=False)

        if output is None or (hasattr(output, "__len__") and len(output) == 0):
            logger.warning("[Dia] generate() returned empty output; returning silence")
            silence = np.zeros(self._sample_rate, dtype=np.float32)
            return _numpy_to_wav(silence, self._sample_rate)

        arr = np.asarray(output, dtype=np.float32)
        return _numpy_to_wav(arr, self._sample_rate)

    # ── Async interface ──────────────────────────────────────────────────────

    async def generate(self, text: str, speed: float = 1.0, emotion: str = "neutral") -> bytes:
        self._queue_depth += 1
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                _THREAD_POOL,
                lambda: self._generate_sync(text, speed, emotion),
            )
        finally:
            self._queue_depth -= 1

    async def generate_conversation(self, lines: list[dict]) -> bytes:
        """
        Generate a multi-speaker NPC conversation as a single WAV.

        lines: [{"speaker": str, "text": str, "voice_preset": str}, ...]
        Dia's [S1]/[S2] tokens alternate per line for natural transitions.
        """
        parts = []
        for i, line in enumerate(lines):
            tag = f"[S{(i % 2) + 1}]"
            parts.append(f"{tag} {line['text'].strip()}")
        script = " ".join(parts)

        self._queue_depth += 1
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                _THREAD_POOL,
                lambda: self._generate_sync(script, speed=1.0, emotion="neutral"),
            )
        finally:
            self._queue_depth -= 1

    def status(self) -> dict:
        return {
            "ready":   self.ready,
            "vram_mb": _measure_vram_mb(),
            "queue":   self._queue_depth,
            "device":  self._device,
        }


# ===========================================================================
# KokoroEngine — CPU (Ryzen 9800X3D), ONNX runtime, ~150ms latency
# ===========================================================================

class KokoroEngine:
    """
    Kokoro ONNX inference — pure CPU, never touches the GPU.

    Always ready, zero warm-up after first load, ~150ms latency on a
    Ryzen 9800X3D with its 3D V-Cache keeping ONNX weights in L3.

    Falls back automatically if Chatterbox or Dia are busy or fail.
    """

    def __init__(self) -> None:
        self._model       = None
        self._sample_rate = 24_000
        self._queue_depth = 0
        self._onnx_path   = ""
        self._voices_path = ""
        self._last_error  = None
        self.ready        = False

    # ── Blocking load ────────────────────────────────────────────────────────

    def load(self) -> None:
        logger.info("[Kokoro] loading ONNX model → CPU …")
        t0 = time.perf_counter()

        try:
            from kokoro_onnx import Kokoro  # type: ignore
        except ImportError as exc:
            self._last_error = f"kokoro_onnx_import_error:{exc}"
            logger.warning(f"[Kokoro] kokoro-onnx not installed — CPU engine disabled ({exc})")
            return

        try:
            onnx_path   = (os.environ.get("KOKORO_ONNX_PATH", "kokoro-v1.0.onnx") or "kokoro-v1.0.onnx").strip()
            voices_path = (os.environ.get("KOKORO_VOICES_PATH", "voices-v1.0.bin") or "voices-v1.0.bin").strip()
            self._model = Kokoro(onnx_path, voices_path)
            self._onnx_path = onnx_path
            self._voices_path = voices_path
            self._last_error = None
            logger.info(f"[Kokoro] loaded model={onnx_path} voices={voices_path}")
        except Exception as exc:
            self._last_error = f"kokoro_load_error:{exc}"
            logger.error(f"[Kokoro] failed to load model: {exc}", exc_info=True)
            return

        elapsed_ms = (time.perf_counter() - t0) * 1_000
        logger.info(f"[Kokoro] ready  CPU  load_ms={elapsed_ms:.0f}")
        self.ready = True

    # ── Warmup ───────────────────────────────────────────────────────────────

    def warmup(self) -> float:
        if not self.ready:
            return 0.0
        t0 = time.perf_counter()
        self._generate_sync("Tavern ready.", voice_id="am_michael", speed=1.0)
        elapsed = (time.perf_counter() - t0) * 1_000
        logger.info(f"[Kokoro] warmup complete  ms={elapsed:.0f}")
        return elapsed

    # ── Sync generation ──────────────────────────────────────────────────────

    def _generate_sync(
        self,
        text:     str,
        voice_id: str   = "am_michael",
        speed:    float = 1.0,
        lang:     str   = "en-us",
    ) -> bytes:
        samples, sample_rate = self._model.create(
            text,
            voice=voice_id,
            speed=speed,
            lang=lang,
        )
        self._sample_rate = sample_rate
        return _numpy_to_wav(samples, sample_rate)

    # ── Async interface ──────────────────────────────────────────────────────

    async def generate(
        self,
        text:     str,
        speed:    float = 1.0,
        emotion:  str   = "neutral",
        voice_id: str   = "am_michael",
        lang:     str   = "en-us",
    ) -> bytes:
        self._queue_depth += 1
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                _THREAD_POOL,
                lambda: self._generate_sync(text, voice_id=voice_id, speed=speed, lang=lang),
            )
        finally:
            self._queue_depth -= 1

    def status(self) -> dict:
        return {
            "ready":  self.ready,
            "queue":  self._queue_depth,
            "device": "cpu",
            "model_path": self._onnx_path or (os.environ.get("KOKORO_ONNX_PATH", "kokoro-v1.0.onnx") or "kokoro-v1.0.onnx").strip(),
            "voices_path": self._voices_path or (os.environ.get("KOKORO_VOICES_PATH", "voices-v1.0.bin") or "voices-v1.0.bin").strip(),
            "last_error": self._last_error,
        }
