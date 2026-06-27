"""Generate repo-safe ambient loop assets and manifest metadata on startup."""
from __future__ import annotations

import json
import math
import random
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22_050
DURATION_SEC = 22
FRAME_COUNT = SAMPLE_RATE * DURATION_SEC
FADE_SAMPLES = int(SAMPLE_RATE * 0.35)
MANIFEST_VERSION = "20260328"

TRACK_VARIANTS = {
    "forest": ["forest", "wilderness_night", "swamp", "mountain_pass"],
    "tavern": ["tavern", "inn_night", "marketplace", "city", "harbor", "campfire"],
    "dungeon": ["dungeon", "crypt", "cave", "temple", "castle_hall", "tension"],
    "battle": ["battle", "boss_battle", "coastal", "auto"],
    # Dedicated weather family — storm no longer borrows the battle loop.
    # First entry ("storm") provides the canonical generated asset.
    "weather": ["storm", "rain", "heavy_rain", "blizzard", "wind"],
}
_TRACK_TO_FAMILY = {
    str(track).strip().lower(): family
    for family, tracks in TRACK_VARIANTS.items()
    for track in tracks
}
ASSET_SPECS = {
    f"{track}_loop_{MANIFEST_VERSION}.wav": kind
    for kind, tracks in TRACK_VARIANTS.items()
    for track in tracks[:1]
}


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _env(index: int) -> float:
    if index < FADE_SAMPLES:
        return index / FADE_SAMPLES
    if index > FRAME_COUNT - FADE_SAMPLES:
        return (FRAME_COUNT - index) / FADE_SAMPLES
    return 1.0


def _forest(t: float, low: float, high: float) -> tuple[float, float]:
    # Wind: amplitude-modulated low noise only — high component removed (was static)
    wind_am = 0.65 + 0.35 * math.sin(2 * math.pi * 0.047 * t + 0.3)
    wind = 0.14 * low * wind_am
    # Leaves: very faint high-freq texture, kept extremely quiet to avoid hiss
    leaves = 0.007 * high * (0.8 + 0.2 * math.sin(2 * math.pi * 0.13 * t + 0.5))
    # Birds: varied calls with frequency modulation for natural-sounding trills
    bird = 0.0
    for start, freq, rate in (
        (2.5, 1320, 12.0), (5.8, 1560, 0.0), (9.1, 980, 9.0),
        (12.2, 1200, 15.0), (15.7, 1440, 0.0), (19.3, 1080, 11.0),
    ):
        dt = (t - start) % DURATION_SEC
        if 0 < dt < 0.55:
            mod = 1.0 + (0.18 * math.sin(2 * math.pi * rate * dt) if rate > 0 else 0)
            bird += 0.07 * math.sin(2 * math.pi * freq * mod * dt) * math.exp(-6.5 * dt)
    # Brook: harmonic blend for bubbling water texture
    brook = (
        0.022 * math.sin(2 * math.pi * 220 * t)
        + 0.013 * math.sin(2 * math.pi * 330 * t + 0.3)
        + 0.009 * math.sin(2 * math.pi * 440 * t + 0.8)
    ) * (0.7 + 0.3 * math.sin(2 * math.pi * 0.025 * t))
    base = wind + leaves + bird + brook
    return base * 0.93, base * 1.07


def _tavern(t: float, low: float, high: float) -> tuple[float, float]:
    # Crowd voices: sine oscillators at voice-range frequencies with independent AM at
    # speaking cadence (1-3 Hz). Sounds like overlapping conversation, not wind or sea.
    voices = (
        0.038 * math.sin(2 * math.pi * 280 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 2.1 * t + 0.0))
        + 0.036 * math.sin(2 * math.pi * 340 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 1.6 * t + 1.2))
        + 0.030 * math.sin(2 * math.pi * 420 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 2.7 * t + 2.4))
        + 0.030 * math.sin(2 * math.pi * 200 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 1.3 * t + 0.8))
        + 0.024 * math.sin(2 * math.pi * 500 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 3.0 * t + 3.7))
        + 0.022 * math.sin(2 * math.pi * 370 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 2.4 * t + 5.1))
    )
    # Quiet background noise for room body (removed slow sea-wave swell)
    room_noise = 0.025 * low
    # Fireplace: 55 Hz warmth + octave (no high-freq noise)
    hearth = 0.030 * math.sin(2 * math.pi * 55 * t) + 0.015 * math.sin(2 * math.pi * 110 * t)
    # Mug clinks: fundamental + harmonic, sharp transient decay
    mug = 0.0
    for start, freq in (
        (1.5, 900), (4.9, 740), (7.6, 1050), (10.3, 820), (13.8, 970), (17.1, 860), (20.4, 790),
    ):
        dt = (t - start) % DURATION_SEC
        if 0 < dt < 0.18:
            mug += (
                0.09 * math.sin(2 * math.pi * freq * dt)
                + 0.045 * math.sin(2 * math.pi * freq * 2.3 * dt)
            ) * math.exp(-28 * dt)
    # Lute melody with harmonics
    melody = (220.0, 246.94, 261.63, 293.66, 329.63, 293.66, 261.63, 246.94)
    note_idx = int((t % (len(melody) * 1.1)) / 1.1) % len(melody)
    nf = melody[note_idx]
    lute = (
        0.030 * math.sin(2 * math.pi * nf * t)
        + 0.015 * math.sin(2 * math.pi * nf * 2 * t) * 0.6
        + 0.008 * math.sin(2 * math.pi * nf * 3 * t) * 0.3
    )
    base = voices + room_noise + hearth + lute + mug
    return base * 0.97, base * 1.03


def _dungeon(t: float, low: float, high: float) -> tuple[float, float]:
    # Deep stone rumble: two frequencies for thickness
    rumble = (
        0.13 * math.sin(2 * math.pi * 50 * t)
        + 0.05 * math.sin(2 * math.pi * 73 * t)
    ) * (0.52 + 0.48 * math.sin(2 * math.pi * 0.033 * t))
    # Air/wind through cracks: modulated noise
    wind_mod = 0.62 + 0.38 * math.sin(2 * math.pi * 0.077 * t + 1.1)
    air = 0.09 * low * wind_mod
    # Water drips: resonant frequency sweep + harmonic, echo-like decay
    drip = 0.0
    for start, freq in ((3.1, 1100), (6.8, 1350), (10.5, 920), (14.2, 1180), (18.4, 1040)):
        dt = (t - start) % DURATION_SEC
        if 0 < dt < 0.40:
            f = freq * max(0.3, 1 - dt * 1.0)
            drip += (
                0.09 * math.sin(2 * math.pi * f * dt)
                + 0.035 * math.sin(2 * math.pi * f * 2.1 * dt)
            ) * math.exp(-12 * dt)
    # Ominous detuned drone (slight beating between two close frequencies)
    drone = (
        0.022 * math.sin(2 * math.pi * 110.0 * t)
        + 0.022 * math.sin(2 * math.pi * 110.4 * t)
    )
    # Subsonic presence
    sub = 0.04 * math.sin(2 * math.pi * 32 * t)
    base = rumble + air + drip + drone + sub
    return base * 1.02, base * 0.98


def _battle(t: float, low: float, high: float) -> tuple[float, float]:
    # Battle strings: D minor chord (D3-F3-A3) with fast tremolo (7 Hz).
    # Tremolo strings are the hallmark of battle/combat music — NOT sawtooth drones.
    tremolo = 0.5 + 0.5 * abs(math.sin(2 * math.pi * 7.0 * t))
    strings = (
        0.055 * math.sin(2 * math.pi * 146.83 * t)   # D3
        + 0.050 * math.sin(2 * math.pi * 174.61 * t)  # F3 (minor third)
        + 0.040 * math.sin(2 * math.pi * 220.00 * t)  # A3 (fifth)
        + 0.025 * math.sin(2 * math.pi * 293.66 * t)  # D4 (octave)
    ) * tremolo
    # Driving kick at 120 BPM — heavy and impactful
    beat_pos = (t * 2.0) % 1.0
    kick = 0.22 * math.sin(2 * math.pi * 80 * t) * math.exp(-25 * beat_pos) if beat_pos < 0.20 else 0.0
    # Snare accent on off-beats (quiet — avoids static)
    snare_pos = ((t + 0.25) * 2.0) % 1.0
    snare = 0.025 * high * math.exp(-30 * snare_pos) if snare_pos < 0.10 else 0.0
    # Horn stab accent on strong beats
    horn = 0.05 * math.sin(2 * math.pi * 220 * t) * max(0.0, math.sin(2 * math.pi * 0.5 * t))
    # Minimal noise bed — just enough for presence, not a machine-room rumble
    bed = 0.025 * low
    base = strings + kick + snare + horn + bed
    return base * 1.02, base * 0.98


def _storm(t: float, low: float, high: float) -> tuple[float, float]:
    # Steady rain: bright filtered noise, gently amplitude-modulated for life.
    rain = 0.10 * high * (0.85 + 0.15 * math.sin(2 * math.pi * 0.7 * t))
    # Hiss/body bed from the low-passed noise.
    body = 0.06 * low
    # Wind gusts: slow swelling low-noise envelope.
    gust = 0.07 * low * (0.5 + 0.5 * math.sin(2 * math.pi * 0.05 * t + 0.6))
    # Distant thunder: low-frequency rumble bursts at a few points in the loop,
    # with a soft attack and a long decay so it reads as far-off, not percussive.
    thunder = 0.0
    for start, freq in ((4.0, 48.0), (11.5, 38.0), (17.0, 55.0)):
        dt = (t - start) % DURATION_SEC
        if 0 < dt < 2.4:
            env = math.exp(-1.8 * dt) * (1 - math.exp(-30 * dt))
            thunder += (
                0.5 * math.sin(2 * math.pi * freq * dt)
                + 0.3 * math.sin(2 * math.pi * freq * 1.5 * dt)
            ) * env * 0.5
    sub = 0.03 * math.sin(2 * math.pi * 30 * t)
    base = rain + body + gust + thunder + sub
    return base * 0.98, base * 1.02


_RENDERERS = {"forest": _forest, "tavern": _tavern, "dungeon": _dungeon, "battle": _battle, "weather": _storm}


def _write_wave(path: Path, kind: str) -> None:
    renderer = _RENDERERS[kind]
    rng = random.Random(f"ambient::{kind}::{MANIFEST_VERSION}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        low_state = 0.0
        high_state = 0.0
        for i in range(FRAME_COUNT):
            t = i / SAMPLE_RATE
            white_1 = rng.uniform(-1, 1)
            white_2 = rng.uniform(-1, 1)
            low_state = low_state * 0.97 + white_1 * 0.03
            high = (white_2 - high_state) * 0.6
            high_state = white_2
            left, right = renderer(t, low_state, high)
            gain = _env(i)
            wav_file.writeframesraw(struct.pack("<hh", int(_clamp(left * gain) * 32767), int(_clamp(right * gain) * 32767)))
        wav_file.writeframes(b"")


def _manifest_payload(audio_dir: Path) -> dict:
    canonical = {
        "forest": f"/static/assets/audio/forest_loop_{MANIFEST_VERSION}.wav",
        "tavern": f"/static/assets/audio/tavern_loop_{MANIFEST_VERSION}.wav",
        "dungeon": f"/static/assets/audio/dungeon_loop_{MANIFEST_VERSION}.wav",
        "battle": f"/static/assets/audio/battle_loop_{MANIFEST_VERSION}.wav",
        "weather": f"/static/assets/audio/storm_loop_{MANIFEST_VERSION}.wav",
    }
    labels = {
        "forest": "Forest", "wilderness_night": "Wilderness Night", "swamp": "Swamp", "mountain_pass": "Mountain Pass",
        "tavern": "Tavern", "inn_night": "Inn Night", "marketplace": "Marketplace", "city": "City", "harbor": "Harbor", "campfire": "Campfire",
        "dungeon": "Dungeon", "crypt": "Crypt", "cave": "Cave", "temple": "Temple", "castle_hall": "Castle Hall", "tension": "Tension / Stealth",
        "battle": "Battle", "boss_battle": "Boss Battle", "coastal": "Coastal", "auto": "Auto",
        "storm": "Storm", "rain": "Rain", "heavy_rain": "Heavy Rain", "blizzard": "Blizzard", "wind": "Wind",
    }
    tracks = {}
    for kind, aliases in TRACK_VARIANTS.items():
        for alias in aliases:
            tracks[alias] = {
                "label": labels[alias],
                "files": [canonical[kind]],
                "family": kind,
                "layers": ["bed", "detail", "texture"],
                "fallback": f"procedural_{kind}",
                "asset_probe": "enabled",
            }
    return {"version": MANIFEST_VERSION, "tracks": tracks}


def ensure_ambient_audio_assets(audio_dir: Path) -> None:
    for filename, kind in ASSET_SPECS.items():
        asset_path = audio_dir / filename
        if not asset_path.exists() or asset_path.stat().st_size <= 1024:
            _write_wave(asset_path, kind)
    manifest_path = audio_dir / "manifest.json"
    # Only write the manifest if it doesn't exist or is still the old list-based schema (schema < 2).
    # The repo ships manifest.json at schema 2 with layered stems, stingers, and SFX — preserve it.
    _should_write = True
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
            if int(existing.get("schema", 1)) >= 2:
                _should_write = False
        except Exception:
            pass
    if _should_write:
        manifest_path.write_text(json.dumps(_manifest_payload(audio_dir), indent=2))


def normalize_ambient_profile(track: str) -> str:
    """Resolve an ambience alias to a canonical family key used by the live sound system."""
    key = str(track or "").strip().lower()
    if not key:
        return "silence"
    return _TRACK_TO_FAMILY.get(key, key if key in {"forest", "tavern", "dungeon", "battle", "weather", "silence"} else "silence")
