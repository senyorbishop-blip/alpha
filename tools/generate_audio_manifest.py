#!/usr/bin/env python3
"""
generate_audio_manifest.py — produce an upgraded, layered audio manifest for the
existing SoundEngine. Keeps the 25 scene keys the engine already knows, but gives
each scene DISTINCT layered stems (bed / detail one-shots / texture / optional
music), adds scene-matching rules for auto area-music, plus combat tiers and
event stingers.

Filenames are the assets to SOURCE (see SOUND_DESIGN_PLAN.md). The engine resolves
manifest → files; this defines the contract. Run: python3 generate_audio_manifest.py
"""
import json, pathlib

BASE = "/static/assets/audio"
VER = "20260701"

def bed(name, gain=0.7):   return {"file": f"{BASE}/beds/{name}.ogg", "gain": gain, "loop": True}
def tex(name, gain=0.3):   return {"file": f"{BASE}/texture/{name}.ogg", "gain": gain, "loop": True}
def music(name, gain=0.5): return {"file": f"{BASE}/music/{name}.ogg", "gain": gain, "loop": True, "stream": True}
def detail(files, lo=7, hi=20, gain=0.5):
    return {"oneshots": [f"{BASE}/detail/{f}.ogg" for f in files], "min_gap_s": lo, "max_gap_s": hi, "gain": gain}

# scene table: key -> (label, family, bed, detail one-shots, texture, music?, scene_match)
SCENES = {
  # ── wilderness ───────────────────────────────────────────────
  "forest":          ("Forest", "wilderness", "forest_day_bed",
                       ["bird_call_1","bird_call_2","branch_creak","leaf_rustle"], "wind_soft",
                       "forest_theme", {"terrain":["grass","forest"],"poi_types":["wilds","grove"],"tags":["wilderness","day"]}),
  "wilderness_night":("Wilderness Night","wilderness","forest_night_bed",
                       ["owl_hoot","cricket_swell","distant_howl","twig_snap"], "wind_soft",
                       None, {"terrain":["grass","forest"],"tags":["wilderness","night"]}),
  "swamp":           ("Swamp","wilderness","swamp_bed",
                       ["frog_croak","bubble_pop","insect_drone","water_drip"], "wind_low",
                       None, {"terrain":["swamp","marsh"],"tags":["wilderness"]}),
  "mountain_pass":   ("Mountain Pass","wilderness","mountain_wind_bed",
                       ["rock_clatter","eagle_cry","gust_swell"], "wind_high",
                       "mountain_theme", {"terrain":["mountain","snow"],"poi_types":["pass","peak"]}),
  "coastal":         ("Coastline","wilderness","seashore_bed",
                       ["gull_cry","wave_break","rope_creak"], "wind_sea",
                       "coast_theme", {"terrain":["beach","coast"],"poi_types":["shore"],"tags":["water"]}),
  "cave":            ("Cave","wilderness","cave_bed",
                       ["water_drip","pebble_fall","distant_rumble","bat_flutter"], "cave_air",
                       None, {"terrain":["cave","underground"],"poi_types":["cave","cavern"]}),
  # ── settlement ───────────────────────────────────────────────
  "tavern":          ("Tavern","settlement","tavern_room_bed",
                       ["mug_clink","crowd_laugh","chair_scrape","coin_drop"], "hearth_crackle",
                       "tavern_theme", {"poi_types":["tavern","inn","alehouse"],"terrain":["interior"]}),
  "inn_night":       ("Inn at Night","settlement","inn_quiet_bed",
                       ["floor_creak","ember_pop","distant_snore"], "hearth_crackle",
                       "tavern_theme", {"poi_types":["inn"],"tags":["interior","night"]}),
  "marketplace":     ("Marketplace","settlement","market_crowd_bed",
                       ["vendor_call","cart_wheel","crate_thud","haggle_murmur"], None,
                       "town_theme", {"poi_types":["market","bazaar"],"tags":["settlement"]}),
  "city":            ("City Streets","settlement","city_bed",
                       ["bell_toll","footsteps_pass","door_close","dog_bark"], None,
                       "town_theme", {"poi_types":["city","town","district"]}),
  "harbor":          ("Harbor","settlement","harbor_bed",
                       ["gull_cry","ship_bell","rope_creak","crate_thud"], "wind_sea",
                       "coast_theme", {"poi_types":["harbor","dock","port"]}),
  "campfire":        ("Campfire","settlement","camp_night_bed",
                       ["fire_pop","cricket_swell","gear_shift"], "hearth_crackle",
                       "rest_theme", {"poi_types":["camp","rest"],"tags":["rest"]}),
  # ── dungeon / interior ───────────────────────────────────────
  "dungeon":         ("Dungeon","dungeon","dungeon_bed",
                       ["chain_rattle","stone_grind","distant_moan","water_drip"], "dungeon_air",
                       "dungeon_theme", {"terrain":["dungeon","stone"],"poi_types":["dungeon","ruin"]}),
  "crypt":           ("Crypt","dungeon","crypt_bed",
                       ["bone_shift","whisper_swell","dust_fall","coffin_creak"], "dungeon_air",
                       "dungeon_theme", {"poi_types":["crypt","tomb","catacomb"],"tags":["undead"]}),
  "temple":          ("Temple","dungeon","temple_bed",
                       ["choir_swell","incense_chime","stone_step"], "temple_air",
                       "temple_theme", {"poi_types":["temple","shrine","sanctum"]}),
  "castle_hall":     ("Castle Hall","dungeon","castle_hall_bed",
                       ["armor_clank","banner_flap","distant_court"], "hall_air",
                       "court_theme", {"poi_types":["castle","keep","hall","throne"]}),
  # ── weather (overlay-friendly) ───────────────────────────────
  "storm":           ("Storm","weather","storm_bed",
                       ["thunder_far","thunder_near","gust_swell"], "rain_texture",
                       None, {"tags":["weather","storm"]}),
  "rain":            ("Rain","weather","rain_bed", ["drip_irregular","gutter_run"], None,
                       None, {"tags":["weather","rain"]}),
  "heavy_rain":      ("Heavy Rain","weather","heavy_rain_bed", ["thunder_far","splash_heavy"], None,
                       None, {"tags":["weather","rain","heavy"]}),
  "blizzard":        ("Blizzard","weather","blizzard_bed", ["ice_crack","gust_high"], "wind_high",
                       None, {"tags":["weather","snow"],"terrain":["snow"]}),
  "wind":            ("Wind","weather","wind_bed", ["gust_swell","whistle_thin"], None,
                       None, {"tags":["weather","wind"]}),
  # ── tension / combat (also see combat_tiers) ─────────────────
  "tension":         ("Tension","combat","tension_bed", ["heartbeat_low","string_swell"], None,
                       "tension_theme", {"tags":["tension","stealth"]}),
  "battle":          ("Battle","combat","battle_bed", ["sword_ring","shield_hit"], None,
                       "battle_theme", {"tags":["combat"]}),
  "boss_battle":     ("Boss Battle","combat","boss_bed", ["drum_hit","horn_blast"], None,
                       "boss_theme", {"tags":["combat","boss"]}),
  # ── auto sentinel (engine picks via scene_match) ─────────────
  "auto":            ("Auto (scene-driven)","system", None, [], None, None, {}),
}

def build_track(key, t):
    label, family, bed_name, det, texname, mus, match = t
    track = {"label": label, "family": family, "fallback": f"procedural_{family}",
             "asset_probe": "enabled", "scene_match": match, "layers": {}}
    if bed_name: track["layers"]["bed"] = bed(bed_name)
    if det:      track["layers"]["detail"] = detail(det)
    if texname:  track["layers"]["texture"] = tex(texname)
    if mus:      track["music"] = music(mus)
    # legacy single-file field kept for backward-compat with current _startTrack
    primary = bed_name or (mus if mus else None)
    track["files"] = [f"{BASE}/beds/{bed_name}.ogg"] if bed_name else ([f"{BASE}/music/{mus}.ogg"] if mus else [])
    return track

manifest = {
    "version": VER,
    "schema": 2,
    "loudness_target_lufs": -16,          # normalize every asset to this
    "crossfade_ms_default": 2500,         # equal-power overlap (engine upgrade)
    "auto_scene_music": True,             # follow map_context unless DM overrides
    "tracks": {k: build_track(k, v) for k, v in SCENES.items()},

    # combat intensity tiers — server swaps these on initiative/HP thresholds
    "combat_tiers": {
        "battle":          {"track": "battle", "trigger": "encounter_start"},
        "battle_bloodied": {"track": "battle", "music": f"{BASE}/music/battle_intense.ogg", "trigger": "party_or_boss_bloodied"},
        "boss_battle":     {"track": "boss_battle", "trigger": "boss_tag"},
    },

    # event stingers — short, duck ambient under them, then restore
    "stingers": {
        "quest_complete": {"file": f"{BASE}/stingers/quest_complete.ogg", "gain": 0.9, "duck_ambient_ms": 1800},
        "quest_accept":   {"file": f"{BASE}/stingers/quest_accept.ogg",   "gain": 0.7, "duck_ambient_ms": 1000},
        "level_up":       {"file": f"{BASE}/stingers/level_up.ogg",       "gain": 0.9, "duck_ambient_ms": 1800},
        "treasure":       {"file": f"{BASE}/stingers/treasure.ogg",       "gain": 0.8, "duck_ambient_ms": 1200},
        "crit_hit":       {"file": f"{BASE}/stingers/crit.ogg",           "gain": 0.8, "duck_ambient_ms": 600},
        "victory":        {"file": f"{BASE}/stingers/victory.ogg",        "gain": 0.9, "duck_ambient_ms": 2200},
        "player_down":    {"file": f"{BASE}/stingers/player_down.ogg",    "gain": 0.85,"duck_ambient_ms": 1500},
    },

    # discrete SFX (decoded buffers; map to sound_play_sfx ids)
    "sfx": {
        "dice_roll":  {"files": ["/static/sounds/clack1.ogg","/static/sounds/clack2.ogg","/static/sounds/clack3.ogg"], "gain": 1.0},
        "page_turn":  {"file": f"{BASE}/sfx/page_turn.ogg", "gain": 0.8},
        "coin":       {"file": f"{BASE}/sfx/coin.ogg", "gain": 0.9},
        "door_open":  {"file": f"{BASE}/sfx/door_open.ogg", "gain": 0.9},
        "ui_select":  {"file": f"{BASE}/sfx/ui_select.ogg", "gain": 0.6},
    },
}

out = pathlib.Path("manifest.upgraded.json")
out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

# self-check
assert set(SCENES) >= {"forest","tavern","dungeon","battle","boss_battle","storm"}, "scene keys drifted"
distinct_beds = {v[2] for v in SCENES.values() if v[2]}
print(f"OK — {len(manifest['tracks'])} scenes, {len(distinct_beds)} distinct beds, "
      f"{len(manifest['stingers'])} stingers, {len(manifest['sfx'])} sfx groups")
print(f"Wrote {out}")
