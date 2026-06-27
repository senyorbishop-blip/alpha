"""Weather system: canonical normalization, backward-compatible migration,
audio family routing, and client preset distinctness guards.

These cover the atmosphere upgrade where Storm became a first-class preset
(heavy rain + wind + lightning + thunder + darkened scene) distinct from plain
rain, and the weather state shape was unified across the editor + persistence
schemas while staying backward compatible with already-saved maps.
"""
from __future__ import annotations

import json
from pathlib import Path

from server.editor_schema import (
    canonical_weather_type,
    normalize_map_settings,
    normalize_weather_block,
)
from server.persistence_schema import normalize_weather_state
import server.ambient_audio as ambient_audio


# ── canonical_weather_type ──────────────────────────────────────────────

def test_canonical_type_maps_legacy_aliases():
    assert canonical_weather_type("stormy") == "storm"
    assert canonical_weather_type("sandstorm") == "sand"
    assert canonical_weather_type("snowy") == "snow"
    assert canonical_weather_type("cloudy") == "fog"
    assert canonical_weather_type("downpour") == "heavy_rain"
    assert canonical_weather_type("magical") == "arcane_storm"


def test_canonical_type_is_case_and_space_insensitive():
    assert canonical_weather_type("  Heavy Rain ") == "heavy_rain"
    assert canonical_weather_type("ARCANE STORM") == "arcane_storm"


def test_canonical_type_unknown_falls_back_to_none():
    assert canonical_weather_type("tornado_of_frogs") == "none"
    assert canonical_weather_type("") == "none"
    assert canonical_weather_type(None) == "none"


def test_canonical_type_passthrough_for_known_values():
    for known in ("none", "rain", "heavy_rain", "storm", "snow",
                  "blizzard", "fog", "ash", "sand", "arcane_storm"):
        assert canonical_weather_type(known) == known


# ── persistence weather_state normalization ─────────────────────────────

def test_weather_state_migrates_legacy_editor_shape():
    # Old runtime stored {type, wind}; new shape uses {weather_type, wind_speed}.
    out = normalize_weather_state({"type": "stormy", "wind": 0.8, "intensity": 0.9})
    assert out["weather_type"] == "storm"
    assert out["wind_speed"] == 0.8
    assert out["intensity"] == 0.9
    # New canonical fields receive safe defaults.
    assert out["darkness"] == 0.0
    assert out["lightning_frequency"] == 0.5
    assert out["audio_linked"] is True


def test_weather_state_clamps_and_defaults():
    out = normalize_weather_state({"weather_type": "rain", "intensity": 3,
                                   "wind_angle": 999, "wind_speed": -1})
    assert out["intensity"] == 1.0
    assert out["wind_angle"] == 360.0
    assert out["wind_speed"] == 0.0
    assert out["map_context"] == "world"


def test_weather_state_unknown_type_falls_back():
    out = normalize_weather_state({"weather_type": "meteor_shower"})
    assert out["weather_type"] == "none"


def test_weather_state_preserves_new_fields():
    out = normalize_weather_state({
        "weather_type": "storm", "darkness": 0.5,
        "lightning_frequency": 0.9, "audio_linked": False,
    })
    assert out["darkness"] == 0.5
    assert out["lightning_frequency"] == 0.9
    assert out["audio_linked"] is False


# ── editor map-settings weather block ───────────────────────────────────

def test_weather_block_migrates_old_map_safely():
    block = normalize_weather_block({"enabled": True, "type": "rain", "wind": 0.4})
    assert block["enabled"] is True
    assert block["type"] == "rain"
    assert block["weather_type"] == "rain"   # mirrored under both names
    assert block["wind_speed"] == 0.4
    assert block["wind"] == 0.4              # legacy mirror retained


def test_weather_block_accepts_runtime_shape():
    block = normalize_weather_block({"weather_type": "stormy", "wind_speed": 0.6,
                                     "wind_angle": 120, "darkness": 0.3})
    assert block["type"] == "storm"
    assert block["wind_speed"] == 0.6
    assert block["wind_angle"] == 120.0
    assert block["darkness"] == 0.3


def test_map_settings_weather_unknown_type_falls_back():
    settings = normalize_map_settings({"weather": {"type": "lava_rain", "intensity": 0.7}})
    assert settings["weather"]["type"] == "none"
    assert settings["weather"]["intensity"] == 0.7


def test_map_settings_weather_defaults_when_missing():
    settings = normalize_map_settings({})
    w = settings["weather"]
    assert w["enabled"] is False
    assert w["type"] == "none"
    assert w["wind_speed"] == 0.2
    assert w["audio_linked"] is True


# ── audio family routing ────────────────────────────────────────────────

def test_storm_audio_no_longer_battle_family():
    # The headline audio fix: Storm gets a dedicated weather loop, not battle.
    assert ambient_audio.normalize_ambient_profile("storm") == "weather"
    assert ambient_audio.normalize_ambient_profile("storm") != "battle"


def test_weather_audio_variants_route_to_weather_family():
    for track in ("rain", "heavy_rain", "blizzard", "wind"):
        assert ambient_audio.normalize_ambient_profile(track) == "weather"


def test_battle_family_still_intact():
    assert ambient_audio.normalize_ambient_profile("battle") == "battle"
    assert ambient_audio.normalize_ambient_profile("boss_battle") == "battle"


def test_audio_manifest_exposes_weather_tracks(tmp_path):
    ambient_audio.ensure_ambient_audio_assets(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    tracks = manifest["tracks"]
    for track in ("storm", "rain", "heavy_rain", "blizzard", "wind"):
        assert track in tracks, f"missing weather track {track}"
        assert tracks[track]["family"] == "weather"
    # Storm's file is the weather loop, not the battle loop.
    assert "storm_loop" in tracks["storm"]["files"][0]
    assert "battle_loop" not in tracks["storm"]["files"][0]


# ── client preset distinctness guards (static checks on play.html) ──────

def _play_html() -> str:
    root = Path(__file__).resolve().parent.parent
    return (root / "client" / "templates" / "play.html").read_text()


def test_client_defines_canonical_weather_presets():
    html = _play_html()
    assert "WEATHER_PRESETS" in html
    for preset in ("rain:", "heavy_rain:", "storm:", "snow:", "blizzard:",
                   "fog:", "ash:", "sand:", "arcane_storm:"):
        assert preset in html, f"missing preset {preset}"


def test_client_storm_is_distinct_from_rain():
    """Storm must carry lightning + heavier atmosphere that plain rain lacks."""
    html = _play_html()
    # Storm preset line declares lightning; the light-rain preset does not.
    storm_line = next(l for l in html.splitlines() if l.strip().startswith("storm:"))
    rain_line = next(l for l in html.splitlines() if l.strip().startswith("rain:"))
    assert "lightning:{" in storm_line.replace(" ", "")
    assert "lightning:null" in rain_line.replace(" ", "")
    # Storm darkens the scene noticeably more than light rain.
    assert "darkness:0.34" in storm_line.replace(" ", "")
    assert "darkness:0.06" in rain_line.replace(" ", "")


def test_client_respects_reduced_motion():
    html = _play_html()
    assert "prefers-reduced-motion" in html
    assert "reducedMotion" in html
