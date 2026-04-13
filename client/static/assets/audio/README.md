# Ambient Audio Assets

Place seamless-loop ambient audio files in this directory.
The sound engine will automatically detect and use them in preference to the
procedural synthesis fallback.

## Required Files

| Filename         | Description                                    |
|------------------|------------------------------------------------|
| `forest.ogg`     | Natural forest ambience — birds, wind, leaves  |
| `tavern.ogg`     | Warm tavern ambience — crowd, fire, music      |
| `dungeon.ogg`    | Underground ambience — drips, rumble, air      |
| `battle.ogg`     | Battle/combat tension — drums, tension strings |

MP3 or WebM alternatives also work (engine probes in order: ogg → mp3 → webm).

## Notes

- Files should be seamlessly loopable (loop point without audible click)
- Recommend: 44.1 kHz, stereo, -14 LUFS normalised for consistent volume
- File size: target 2–8 MB per track for reasonable load time
- Free sources: freesound.org, OpenGameArt.org, Kenney.nl sound packs

## Without Audio Files

When no asset files are present the engine falls back to procedural Web Audio
synthesis. This sounds synthetic but is functional without any external files.
