# Sound Design Plan — toward RuneScape-tier audio

Goal: keep the existing `SoundEngine` (it's good) and get the table from
synthesized pink-noise to layered, area-aware, combat-reactive atmosphere with
iconic stingers. ~70% sourcing a curated, license-clear library; ~30% engine
polish. Ships with `manifest.upgraded.json` (drop-in) + `generate_audio_manifest.py`.

---

## Where it stands

**Engine (keep):** WebAudio with master/ambient/SFX buses, crossfade (`setAmbient`),
ducking (`setAmbientDucking`), per-player personal volume, manifest resolution,
buffer cache, DM→table broadcast (`sound_set_ambient`/`sound_play_sfx`/`sound_stop_all`).
Combat already auto-swaps to a `battle` track on initiative and stores the prior
track to restore. Track selection can already read map context (`_getCurrentMapContext`).

**Gaps (fix):**
- **No real assets.** Only 3 dice `.ogg`s are committed; the audio folder is just
  a README + manifest. The engine therefore runs on its procedural fallback
  (`mkNoise('pink')` + oscillators) — the "synthetic" sound the engine header admits.
- **Placeholder manifest.** 25 scene keys exist but several biomes point at one
  reused loop that isn't even present.
- **Layers are fake.** Manifest declares `bed/detail/texture`, but the engine
  renders them as synthesized noise, not recorded stems.
- **Crossfade is linear + sequential** (slight dip between tracks), not equal-power overlap.
- **Auto area-music is partial** and there are no event stingers.

---

## What `manifest.upgraded.json` changes

- Keeps all **25 scene keys** the engine already knows; gives each a **distinct**
  layered definition: `bed` (looping ambience) + `detail` (randomized one-shots
  with min/max gap) + `texture` (quiet continuous layer) + optional streamed `music`.
- Adds `scene_match` per track (`poi_types` / `terrain` / `tags`) so music can
  **auto-follow the map** with DM override — the RuneScape "new area, new music".
- Adds `combat_tiers` (battle → bloodied → boss) and 7 `stingers`
  (quest_complete, level_up, treasure, victory, crit, quest_accept, player_down).
- Adds a `sfx` table (keeps your 3 dice clacks as the `dice_roll` group).
- Global `loudness_target_lufs: -16` and `crossfade_ms_default: 2500`.
- Keeps a legacy `files: []` per track so the current `_startTrack` still works
  during migration.

---

## Engine upgrades (independent PRs)

1. **Equal-power overlapping crossfade.** Replace the linear fade-out-then-in in
   `setAmbient` with two overlapping gain ramps using an equal-power curve
   (`cos`/`sin`), so transitions don't dip. Honor `crossfade_ms_default`.
2. **Real layered playback.** New `_startLayeredTrack(track)` that plays `bed`
   (looped buffer, seamless loop points), schedules `detail` one-shots at random
   gaps in `[min_gap_s,max_gap_s]`, loops `texture`, and (if present) starts
   streamed `music` on its own gain. Each layer on its own sub-gain under
   `ambientGain`. Procedural stays only as the logged fallback.
3. **Manifest-driven SFX + stingers.** `playSfx(id)` resolves `manifest.sfx[id]`
   (random pick for groups); add `playStinger(id)` that ducks `ambientGain` for
   `duck_ambient_ms` then restores. Both decode-and-cache buffers.
4. **Auto area-music.** On map/scene change, pick the track whose `scene_match`
   best fits the current `map_context`/POI/terrain; crossfade unless the DM has
   set a manual override. Server stays authoritative via `sound_set_ambient`.
5. **Combat intensity tiers.** Extend the existing initiative hook: `battle` on
   start, swap to `battle_bloodied` music when a boss/PC is bloodied, `boss_battle`
   on a boss tag, and fire the `victory` stinger + restore `pre_combat_track` on
   `clear_encounter`.
6. **Streaming for music.** Beds/SFX stay decoded buffers; long `music` files use
   a streamed `HTMLAudioElement` source so they don't block on full decode. Drop
   the runtime `*_loop_*.wav` generation once real assets exist (also de-bloats
   the working tree).

---

## Event hooks (where sound meets the rest of the app)

| Trigger | Source | Action |
|---|---|---|
| Encounter start | `combat.py` initiative (exists) | crossfade to `battle` tier |
| Boss/PC bloodied | combat HP thresholds | swap to `battle_bloodied` |
| `clear_encounter` | combat (exists) | `victory` stinger → restore prior track |
| Quest turn-in | Codex / `quest_premium_progression` | `quest_complete` stinger |
| Quest accepted | `handle_session_quest_accept` | `quest_accept` stinger |
| Level up | character level-up | `level_up` stinger |
| Treasure / loot opened | inventory / chest | `treasure` stinger |
| Party enters new map/region | map context change | auto area-music crossfade |
| Player drops to 0 HP | combat death save | `player_down` stinger |

These reuse the existing `sound_set_ambient`/`sound_play_sfx` broadcast and the
Codex work — quest turn-in firing a victory jingle closes that loop.

---

## Asset production targets

Per scene: 1 bed (60–120 s seamless loop), 3–5 detail one-shots, 0–1 texture,
0–1 music loop (90–180 s). Plus 7 stingers (2–5 s) and the SFX set.

- **Format:** `.ogg` (Vorbis ~q5) for web; keep masters in WAV.
- **Loudness:** normalize beds/music to **-16 LUFS**, stingers a touch hotter
  (~-14), so ducking + narration (your TTS) sit cleanly on top.
- **Looping:** trim to zero-crossings / equal-power loop points; test for seams.
- **Curate, don't hoard:** a small, memorable, well-looped set beats a huge messy
  one — that's exactly how RuneScape's audio reads as cohesive.

---

## License-safe sourcing (verify terms at integration time)

You **cannot** use RuneScape's own music (Jagex-owned) — match the *feel*, not the
files. Reputable sources, by typical license (licenses change — confirm each asset
before a commercial ship):

- **Sonniss "GDC Game Audio Bundle"** — royalty-free, commercial-OK; huge SFX/ambience. Best first stop for beds/detail/SFX.
- **OpenGameArt.org (filter CC0)** — loops, SFX, some music; CC0 = no attribution.
- **Freesound.org (filter CC0; CC-BY available)** — vast ambience/one-shots; track attribution for CC-BY.
- **Pixabay Audio** — Pixabay license (royalty-free, commercial, no attribution) — good modern music/ambience.
- **Kevin MacLeod / incompetech.com** — CC-BY (attribution required); lots of fantasy/ambient cues good for area music.
- **Tabletop Audio** — purpose-built TTRPG ambiences; **check its commercial terms** before embedding in a paid product.
- **Music**: for distinctive themes, commission a composer (itch.io/Fiverr asset packs with explicit commercial license), or use Pixabay/CC0.

**Vetting checklist per asset:** ☐ license permits commercial use ☐ permits
modification/looping ☐ attribution captured (if CC-BY) ☐ no AI-training or
no-derivatives clause that blocks use ☐ source URL + license saved to an
`ATTRIBUTIONS.md` in `assets/audio/`.

---

## Build order

1. Drop in `manifest.upgraded.json` (rename to `manifest.json`, bump `?v=`).
2. Engine PRs 1–3 (crossfade, layered playback, SFX/stingers) — sounds better
   immediately even with a starter asset set.
3. Source the curated library against the manifest filenames; commit under
   `assets/audio/{beds,detail,texture,music,stingers,sfx}/` (via Git LFS — see the
   hygiene pack's `.gitattributes`).
4. Engine PRs 4–6 (auto area-music, combat tiers, streaming) + the event hooks.

## Agent prompt

> Read `AGENTS.md`. Implement the six SoundEngine upgrades in
> `client/static/js/ui/sound_engine.js` per the Sound Design Plan, driven by
> `manifest.upgraded.json` (install as `manifest.json`). Keep procedural synthesis
> only as the logged fallback. Reuse the existing `sound_set_ambient` /
> `sound_play_sfx` broadcast and the combat initiative hook in
> `server/handlers/combat.py`; add the combat tiers + `victory`/quest/level
> stingers via those channels. Do not break `test_audio_broadcast.py`; run
> `python -m pytest tests/test_audio_broadcast.py -v` plus `tests/ -v`. Commit
> real assets via Git LFS and an `assets/audio/ATTRIBUTIONS.md`. Acceptance:
> distinct layered ambience per scene, equal-power crossfades, auto area-music
> following `map_context` with DM override, combat tiers, and stingers firing on
> quest turn-in / level-up / encounter clear.
