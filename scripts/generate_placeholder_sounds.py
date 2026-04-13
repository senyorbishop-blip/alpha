"""
generate_placeholder_sounds.py — Generate placeholder audio files for missing UI sounds.

Usage:
    python scripts/generate_placeholder_sounds.py

Generates:
    client/static/sounds/clack1.ogg  — 0.1s silent placeholder (dice click)
    client/static/sounds/clack2.ogg  — 0.1s silent placeholder (dice click)
    client/static/sounds/clack3.ogg  — 0.1s silent placeholder (dice click)

These are UI click sounds for the dice roller. The dice audio system
(client/static/js/dice/utils/audio.js) already fails gracefully when these
are missing, but the server still logs 404 errors. Running this script
creates minimal silent .ogg files to stop the 404 noise.

For real dice sounds, replace these files with actual short click/clack audio.

Dependencies:
    pip install numpy soundfile
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

SOUNDS_DIR = Path(__file__).parent.parent / "client" / "static" / "sounds"
SAMPLE_RATE = 44100
DURATION_S  = 0.1   # 100ms silent tone


def _make_silent_wav(duration_s: float = 0.1, sample_rate: int = 44100) -> bytes:
    """Generate a minimal valid WAV file containing silence."""
    num_samples  = int(sample_rate * duration_s)
    data_bytes   = b"\x00\x00" * num_samples  # 16-bit PCM silence (mono)
    data_size    = len(data_bytes)
    chunk_size   = 36 + data_size

    header = struct.pack(
        "<4sI4s"      # RIFF header
        "4sIHHIIHH"   # fmt  chunk
        "4sI",        # data chunk header
        b"RIFF", chunk_size, b"WAVE",
        b"fmt ", 16, 1, 1,          # PCM, mono
        sample_rate, sample_rate * 2,  # byte rate, block align
        2, 16,                       # block align, bits per sample
        b"data", data_size,
    )
    return header + data_bytes


def _wav_to_ogg_fallback(wav_bytes: bytes, out_path: Path) -> None:
    """
    Try to convert WAV → OGG using soundfile/pysoundfile.
    Falls back to writing a raw WAV renamed as .ogg if soundfile is unavailable —
    modern browsers accept WAV data even with an .ogg extension for placeholder use.
    """
    try:
        import io
        import numpy as np
        import soundfile as sf

        # Decode the WAV we just built
        buf = io.BytesIO(wav_bytes)
        data, sr = sf.read(buf, dtype="float32")

        # Write as OGG Vorbis
        with sf.SoundFile(
            str(out_path), mode="w", samplerate=sr,
            channels=1, format="OGG", subtype="VORBIS"
        ) as f:
            f.write(data)

        print(f"  [ok] {out_path.name}  (OGG via soundfile)")

    except ImportError:
        # soundfile not installed — write WAV bytes anyway (browsers are lenient)
        out_path.write_bytes(wav_bytes)
        print(
            f"  [ok] {out_path.name}  (WAV bytes, soundfile not installed — "
            "install 'soundfile' + 'numpy' for true OGG output)"
        )
    except Exception as exc:
        out_path.write_bytes(wav_bytes)
        print(f"  [warn] {out_path.name}  wrote WAV fallback ({exc})")


def main() -> None:
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Target directory: {SOUNDS_DIR}")

    wav = _make_silent_wav(DURATION_S, SAMPLE_RATE)

    for name in ("clack1.ogg", "clack2.ogg", "clack3.ogg"):
        out = SOUNDS_DIR / name
        if out.exists():
            print(f"  [skip] {name}  (already exists)")
            continue
        _wav_to_ogg_fallback(wav, out)

    print("\nDone. Re-run the server — clack 404 errors should stop.")
    print(
        "To add real dice sounds, replace client/static/sounds/clack*.ogg "
        "with short (50–200ms) click audio files."
    )


if __name__ == "__main__":
    main()
