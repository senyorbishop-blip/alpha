# Tavern Tabletop — Sound Effects

All files should be `.ogg` format (Ogg Vorbis), placed in this directory
(`client/static/sounds/`).

The `AudioManager` class (`client/static/js/ui/sound_engine.js`) loads files
from here at runtime. If a file is missing the engine falls back to procedural
Web Audio API synthesis — **zero console errors** for absent files.

---

## UI Sounds

These short click sounds play when buttons are clicked throughout the UI
(tactile feedback). Loaded by both `AudioManager` and
`client/static/js/dice/utils/audio.js` (dice collision sounds).

| File | Purpose |
|---|---|
| `clack1.ogg` | Button click / dice collision variant 1 (50–200 ms) |
| `clack2.ogg` | Button click / dice collision variant 2 (50–200 ms) |
| `clack3.ogg` | Button click / dice collision variant 3 (50–200 ms) |

Source: [freesound.org](https://freesound.org) — search **"wood click short"** CC0
licence. Convert to OGG Vorbis 44 100 Hz mono.

> **Status:** `clack1.ogg`, `clack2.ogg`, `clack3.ogg` are present.

---

## Sound Effects (DM Panel)

Triggered by the DM panel "Sound Effects" buttons. Each plays once
(one-shot). The AudioManager tries the `.ogg` file first; if absent it
synthesises an equivalent using the Web Audio API.

| File | Button label | Description | Suggested source |
|---|---|---|---|
| `clash.ogg`    | Clash    | Sword / metal clash      | freesound: **"sword clash metal"** |
| `fireball.ogg` | Fireball | Fire whoosh / burst      | freesound: **"fire whoosh burst"** |
| `heal.ogg`     | Heal     | Magic heal chime         | freesound: **"magic heal chime"** |
| `door.ogg`     | Door     | Heavy door creak         | freesound: **"heavy door creak"** |
| `thunder.ogg`  | Thunder  | Thunder crack            | freesound: **"thunder crack close"** |
| `trap.ogg`     | Trap     | Bear trap / snap         | freesound: **"bear trap snap"** |
| `gasp.ogg`     | Gasp     | Shocked breath           | freesound: **"gasp breath shock"** |

All CC0 (Creative Commons Zero) files are acceptable. Target: mono or stereo,
44 100 Hz, 1–3 seconds, OGG Vorbis quality 4–6.

---

## Ambient Loops

Long looping background tracks for each scene type. Must be **seamlessly
loopable** (loop point at zero-crossing, no click at loop boundary).

The AudioManager looks for these files first; if absent the `SoundEngine`
tries the asset manifest (`/static/assets/audio/manifest.json`) and finally
falls back to real-time procedural synthesis.

| File | Ambient scene | Description | Suggested source |
|---|---|---|---|
| `ambient_tavern.ogg`  | Tavern  | Crowd murmur, fire crackle  | opengameart: **"RPG Sound Pack"** by artisticdude |
| `ambient_dungeon.ogg` | Dungeon | Dripping water, stone echo  | opengameart: **"RPG Sound Pack"** by artisticdude |
| `ambient_forest.ogg`  | Forest  | Birds, wind through leaves  | opengameart: **"RPG Sound Pack"** by artisticdude |
| `ambient_battle.ogg`  | Battle  | War drums, tension drone    | opengameart: **"RPG Sound Pack"** by artisticdude |

Target: stereo, 44 100 Hz, 30–120 seconds, OGG Vorbis quality 5–7.
Ensure the loop start/end points are identical in amplitude and phase.

---

## Generating Silent Placeholder Files (stops 404 log noise)

```bash
python scripts/generate_placeholder_sounds.py
```

This creates zero-length OGG files for any key listed in the script so the
server never logs 404s, without adding real audio data.

---

## Key → File Mapping (AudioManager)

```
SFX buttons  : clash → clash.ogg
               fireball → fireball.ogg
               door → door.ogg
               thunder → thunder.ogg
               heal → heal.ogg
               trap → trap.ogg
               gasp → gasp.ogg
               clack1..3 → clack1.ogg .. clack3.ogg

Ambient btns : tavern  → ambient_tavern.ogg
               dungeon → ambient_dungeon.ogg
               forest  → ambient_forest.ogg
               battle  → ambient_battle.ogg
```
