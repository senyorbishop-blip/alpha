"""
tts_config.py — Voice presets and warmup phrases for Tavern TTS.

17 presets, all routed through Kokoro v1.0 (voices-v1.0.bin):
  NARRATORS — deep, authoritative narrator voices
  NPC VOICES — character voices for NPCs
  SYSTEM     — neutral fallback for UI confirmations
"""

from __future__ import annotations
from typing import List

# ---------------------------------------------------------------------------
# Type hint (TypedDict not enforced at runtime — just for IDE clarity)
# ---------------------------------------------------------------------------

VOICE_PRESETS: List[dict] = [

    # ── NARRATOR VOICES (Kokoro) ──────────────────────────────────────────
    {
        "id":               "grand_narrator",
        "label":            "The Grand Narrator",
        "engine":           "kokoro",
        "group":            "narrator",
        "voice_id":         "am_echo",
        "lang":             "en-us",
        "speed":            0.88,
        "default_emotion":  "dramatic",
        "nonverbal_style":  None,
        "description":      "Deep, authoritative — am_echo",
        "tags":             ["narrator", "epic", "cinematic", "warm"],
    },
    {
        "id":               "royal_herald",
        "label":            "The Royal Herald",
        "engine":           "kokoro",
        "group":            "narrator",
        "voice_id":         "bm_george",
        "lang":             "en-us",
        "speed":            1.00,
        "default_emotion":  "neutral",
        "nonverbal_style":  None,
        "description":      "British male, formal — bm_george",
        "tags":             ["narrator", "formal", "authoritative"],
    },
    {
        "id":               "ancient_tome",
        "label":            "Voice of the Tome",
        "engine":           "kokoro",
        "group":            "narrator",
        "voice_id":         "bf_emma",
        "lang":             "en-us",
        "speed":            0.80,
        "default_emotion":  "neutral",
        "nonverbal_style":  None,
        "description":      "British female, mystical — bf_emma",
        "tags":             ["narrator", "ancient", "slow", "reverent"],
    },
    {
        "id":               "battle_commander",
        "label":            "The War Commander",
        "engine":           "kokoro",
        "group":            "narrator",
        "voice_id":         "am_fenrir",
        "lang":             "en-us",
        "speed":            1.05,
        "default_emotion":  "dramatic",
        "nonverbal_style":  None,
        "description":      "Strong male — am_fenrir",
        "tags":             ["narrator", "combat", "urgent"],
    },

    # ── NPC VOICES (Kokoro) ───────────────────────────────────────────────
    {
        "id":               "tavern_keeper",
        "label":            "The Innkeeper",
        "engine":           "kokoro",
        "group":            "npc",
        "voice_id":         "am_michael",
        "lang":             "en-us",
        "speed":            1.05,
        "default_emotion":  "warm",
        "nonverbal_style":  None,
        "description":      "Warm, friendly — am_michael",
        "tags":             ["npc", "tavern", "gruff", "warm"],
    },
    {
        "id":               "shadow_villain",
        "label":            "Voice of Darkness",
        "engine":           "kokoro",
        "group":            "npc",
        "voice_id":         "am_adam",
        "lang":             "en-us",
        "speed":            0.85,
        "default_emotion":  "menacing",
        "nonverbal_style":  None,
        "description":      "Deep, ominous — am_adam",
        "tags":             ["npc", "villain", "menacing", "cold"],
    },
    {
        "id":               "ancient_oracle",
        "label":            "The Oracle",
        "engine":           "kokoro",
        "group":            "npc",
        "voice_id":         "af_nova",
        "lang":             "en-us",
        "speed":            0.75,
        "default_emotion":  "neutral",
        "nonverbal_style":  None,
        "description":      "Ethereal female — af_nova",
        "tags":             ["npc", "oracle", "ethereal", "mystic"],
    },
    {
        "id":               "elven_sage",
        "label":            "The Elven Sage",
        "engine":           "kokoro",
        "group":            "npc",
        "voice_id":         "bf_alice",
        "lang":             "en-us",
        "speed":            0.90,
        "default_emotion":  "warm",
        "nonverbal_style":  None,
        "description":      "British female, wise — bf_alice",
        "tags":             ["npc", "elf", "wise", "musical"],
    },
    {
        "id":               "dwarven_elder",
        "label":            "The Dwarven Elder",
        "engine":           "kokoro",
        "group":            "npc",
        "voice_id":         "bm_daniel",
        "lang":             "en-us",
        "speed":            0.95,
        "default_emotion":  "neutral",
        "nonverbal_style":  None,
        "description":      "Gruff British male — bm_daniel",
        "tags":             ["npc", "dwarf", "gruff", "proud"],
    },
    {
        "id":               "wandering_bard",
        "label":            "The Bard",
        "engine":           "kokoro",
        "group":            "npc",
        "voice_id":         "af_bella",
        "lang":             "en-us",
        "speed":            1.10,
        "default_emotion":  "warm",
        "nonverbal_style":  None,
        "description":      "Expressive female — af_bella",
        "tags":             ["npc", "bard", "lyrical", "upbeat"],
    },
    {
        "id":               "mysterious_witch",
        "label":            "Voice of the Coven",
        "engine":           "kokoro",
        "group":            "npc",
        "voice_id":         "af_nicole",
        "lang":             "en-us",
        "speed":            0.82,
        "default_emotion":  "neutral",
        "nonverbal_style":  None,
        "description":      "Mysterious female — af_nicole",
        "tags":             ["npc", "witch", "mysterious", "conspiratorial"],
    },
    {
        "id":               "wounded_guard",
        "label":            "The Wounded Guard",
        "engine":           "kokoro",
        "group":            "npc",
        "voice_id":         "am_eric",
        "lang":             "en-us",
        "speed":            1.00,
        "default_emotion":  "neutral",
        "nonverbal_style":  None,
        "description":      "Strained male — am_eric",
        "tags":             ["npc", "guard", "pained", "terse"],
    },

    # ── SYSTEM VOICE (Kokoro default) ─────────────────────────────────────
    {
        "id":               "system_voice",
        "label":            "System",
        "engine":           "kokoro",
        "group":            "system",
        "voice_id":         "af_heart",
        "lang":             "en-us",
        "speed":            1.00,
        "default_emotion":  "neutral",
        "nonverbal_style":  None,
        "description":      "Default UI voice — af_heart",
        "tags":             ["system", "fallback", "neutral"],
    },
]

# Fast O(1) lookup by preset ID
PRESET_BY_ID: dict = {p["id"]: p for p in VOICE_PRESETS}

# ---------------------------------------------------------------------------
# 20 pre-cached D&D phrases — generated at startup and held in RAM
# ---------------------------------------------------------------------------

WARMUP_PHRASES: List[str] = [
    "Roll for initiative.",
    "Make a perception check.",
    "You enter the tavern.",
    "A figure emerges from the shadows.",
    "The dungeon door creaks open.",
    "Roll for stealth.",
    "You hear footsteps approaching.",
    "The ancient runes begin to glow.",
    "Your torch flickers and dies.",
    "Make a strength saving throw.",
    "The ground trembles beneath your feet.",
    "A cold wind sweeps through the corridor.",
    "You find a locked chest.",
    "The creature lets out a terrible roar.",
    "Roll for deception.",
    "The bridge begins to collapse.",
    "You discover a hidden door.",
    "The tavern falls silent.",
    "Make a wisdom saving throw.",
    "Victory! The enemy is defeated.",
]

# ---------------------------------------------------------------------------
# Kokoro v1.0 voice catalogue (voices-v1.0.bin)
# ---------------------------------------------------------------------------

KOKORO_VOICES: dict = {
    # American Female
    "af_heart":   {"lang": "en-us", "gender": "female", "description": "American female, default"},
    "af_bella":   {"lang": "en-us", "gender": "female", "description": "American female, expressive"},
    "af_nicole":  {"lang": "en-us", "gender": "female", "description": "American female, mysterious"},
    "af_aoede":   {"lang": "en-us", "gender": "female", "description": "American female"},
    "af_kore":    {"lang": "en-us", "gender": "female", "description": "American female"},
    "af_sarah":   {"lang": "en-us", "gender": "female", "description": "American female, clear"},
    "af_nova":    {"lang": "en-us", "gender": "female", "description": "American female, ethereal"},
    "af_sky":     {"lang": "en-us", "gender": "female", "description": "American female"},
    "af_alloy":   {"lang": "en-us", "gender": "female", "description": "American female"},
    "af_jessica": {"lang": "en-us", "gender": "female", "description": "American female"},
    "af_river":   {"lang": "en-us", "gender": "female", "description": "American female"},
    # American Male
    "am_adam":    {"lang": "en-us", "gender": "male",   "description": "American male, deep ominous"},
    "am_echo":    {"lang": "en-us", "gender": "male",   "description": "American male, authoritative"},
    "am_eric":    {"lang": "en-us", "gender": "male",   "description": "American male, strained"},
    "am_fenrir":  {"lang": "en-us", "gender": "male",   "description": "American male, strong"},
    "am_liam":    {"lang": "en-us", "gender": "male",   "description": "American male"},
    "am_michael": {"lang": "en-us", "gender": "male",   "description": "American male, warm friendly"},
    "am_onyx":    {"lang": "en-us", "gender": "male",   "description": "American male"},
    "am_puck":    {"lang": "en-us", "gender": "male",   "description": "American male"},
    "am_santa":   {"lang": "en-us", "gender": "male",   "description": "American male"},
    # British Female
    "bf_alice":   {"lang": "en-gb", "gender": "female", "description": "British female, wise"},
    "bf_emma":    {"lang": "en-gb", "gender": "female", "description": "British female, mystical"},
    "bf_isabella":{"lang": "en-gb", "gender": "female", "description": "British female"},
    "bf_lily":    {"lang": "en-gb", "gender": "female", "description": "British female"},
    # British Male
    "bm_daniel":  {"lang": "en-gb", "gender": "male",   "description": "British male, gruff"},
    "bm_fable":   {"lang": "en-gb", "gender": "male",   "description": "British male"},
    "bm_george":  {"lang": "en-gb", "gender": "male",   "description": "British male, formal"},
    "bm_lewis":   {"lang": "en-gb", "gender": "male",   "description": "British male"},
}
