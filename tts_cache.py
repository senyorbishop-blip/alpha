"""
tts_cache.py — Thread-safe LRU RAM cache for pre-generated TTS audio.

Capacity : 500 MB maximum
Key      : (text_hash, voice_preset_id, speed_rounded)
Eviction : LRU (least-recently-used) when capacity is exceeded
Thread   : fully thread-safe via threading.Lock (safe to call from
           asyncio.run_in_executor threads and from the event loop)
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Optional, Tuple

logger = logging.getLogger("tts_cache")

MAX_BYTES: int = 500 * 1024 * 1024  # 500 MB

# Key type: (16-char sha256 prefix of text, preset_id, speed rounded to 2dp)
CacheKey = Tuple[str, str, float]


def _make_key(text: str, voice_preset_id: str, speed: float) -> CacheKey:
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return (text_hash, voice_preset_id, round(speed, 2))


class TTSCache:
    """
    Thread-safe LRU cache backed by collections.OrderedDict.

    Usage:
        cache = TTSCache()
        audio = cache.get(text, preset_id, speed)   # None on miss
        cache.put(text, preset_id, speed, wav_bytes) # evicts LRU if full
        stats = cache.status()                        # monitoring dict
    """

    def __init__(self, max_bytes: int = MAX_BYTES) -> None:
        self._max_bytes = max_bytes
        self._cache: OrderedDict[CacheKey, bytes] = OrderedDict()
        self._size_bytes: int = 0
        self._lock = threading.Lock()
        self._hits: int = 0
        self._misses: int = 0

    # ── Public read/write ────────────────────────────────────────────────────

    def get(self, text: str, voice_preset_id: str, speed: float = 1.0) -> Optional[bytes]:
        """Return cached WAV bytes or None on miss. Promotes key to MRU."""
        key = _make_key(text, voice_preset_id, speed)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)   # mark as recently used
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def put(self, text: str, voice_preset_id: str, speed: float, audio_bytes: bytes) -> None:
        """Insert or update an entry, evicting LRU entries to stay under budget."""
        if not audio_bytes:
            return
        key = _make_key(text, voice_preset_id, speed)
        entry_size = len(audio_bytes)

        with self._lock:
            # Update existing entry
            if key in self._cache:
                self._size_bytes -= len(self._cache[key])
                del self._cache[key]

            # Evict LRU entries until there is room
            while self._size_bytes + entry_size > self._max_bytes and self._cache:
                evict_key, evict_val = self._cache.popitem(last=False)
                self._size_bytes -= len(evict_val)
                logger.debug(f"[TTSCache] evicted LRU entry key={evict_key[0]}…{evict_key[1]}")

            self._cache[key] = audio_bytes
            self._size_bytes += entry_size

    def contains(self, text: str, voice_preset_id: str, speed: float = 1.0) -> bool:
        key = _make_key(text, voice_preset_id, speed)
        with self._lock:
            return key in self._cache

    # ── Metrics ──────────────────────────────────────────────────────────────

    def size(self) -> int:
        """Number of entries currently in cache."""
        with self._lock:
            return len(self._cache)

    def size_bytes(self) -> int:
        """Total bytes currently held in cache."""
        with self._lock:
            return self._size_bytes

    def hits(self) -> int:
        return self._hits

    def misses(self) -> int:
        return self._misses

    def status(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "entries":   len(self._cache),
                "size_mb":   round(self._size_bytes / (1024 * 1024), 2),
                "max_mb":    round(self._max_bytes / (1024 * 1024), 0),
                "hits":      self._hits,
                "misses":    self._misses,
                "hit_rate":  round(self._hits / max(1, total) * 100, 1),
            }


# ---------------------------------------------------------------------------
# Module-level singleton — shared across the entire app process
# ---------------------------------------------------------------------------

_tts_cache = TTSCache()


def get_cache() -> TTSCache:
    """Return the process-level TTS cache singleton."""
    return _tts_cache
