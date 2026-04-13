# Testing Checklist — Tavern TTS GPU Narration System

Step-by-step verification for all features.
Run each section in order.

---

## 1. Pre-flight: GPU verification

```bash
nvidia-smi
# Verify: RTX 5070 Ti listed, driver ≥ 560, 16GB VRAM

python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# Expected: True  NVIDIA GeForce RTX 5070 Ti
```

---

## 2. Server startup sequence

Start the server:
```bash
python main.py
```

Watch the log. You should see ALL of the following lines within 60–120 seconds:

```
[TTS] CUDA device: NVIDIA GeForce RTX 5070 Ti  VRAM: 16384 MB
[Chatterbox] loading model → CUDA (this may take 30-60 s) …
[Chatterbox] ready  sr=24000  VRAM_delta=XXXXmb  load_ms=XXXX
[Chatterbox] warmup complete  ms=XXX
[Dia] loading Dia-1.6B → CUDA (this may take 30-90 s) …
[Dia] ready  sr=44100  VRAM_delta=XXXXmb  load_ms=XXXX
[Dia] warmup complete  ms=XXX
[Kokoro] loading ONNX model → CPU …
[Kokoro] ready  CPU  load_ms=XXX
[Kokoro] warmup complete  ms=XXX
✓ Tavern TTS ready
  ├─ Chatterbox  [GPU ✓]  VRAM: XXXXmb   warmup: XXXms
  ├─ Dia         [GPU ✓]  VRAM: XXXXmb   warmup: XXXms
  └─ Kokoro      [CPU ✓]               warmup: XXXms
  └─ RAM cache: 20 phrases pre-rendered
```

**Fail criteria:** any `[GPU ✗]` line or missing `✓ Tavern TTS ready`.

### Verify GPU memory with nvidia-smi
```bash
nvidia-smi
# Both Chatterbox (~3-4GB) and Dia (~3-4GB) should show GPU memory usage
# Total should be ~6-8 GB, leaving >8 GB free on 16 GB card
```

---

## 3. TTS API endpoints

### 3a. Status endpoint
```bash
curl http://localhost:8000/api/tts/status
```
Expected response:
```json
{
  "chatterbox": { "ready": true, "vram_mb": XXXX, "queue": 0 },
  "dia":        { "ready": true, "vram_mb": XXXX, "queue": 0 },
  "kokoro":     { "ready": true, "queue": 0, "device": "cpu" },
  "cache_hits": 0,
  "cache_size": 20,
  "startup_ok": true
}
```

### 3b. Voices endpoint
```bash
curl http://localhost:8000/api/tts/voices | python -m json.tool
```
Expected: 12 presets, grouped as chatterbox (4), dia (8), kokoro (1).

### 3c. Warmup phrases endpoint
```bash
curl http://localhost:8000/api/tts/warmup-phrases
```
Expected: 20 phrases listed.

### 3d. Speak endpoint — Chatterbox
```bash
curl -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Roll for initiative.","voice_preset":"grand_narrator"}' \
  --output /tmp/test_chatterbox.wav
# Check headers:
curl -I -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Roll for initiative.","voice_preset":"grand_narrator"}'
```
Expected headers: `X-TTS-Engine: chatterbox`, `X-TTS-Cache: miss` (first call),
`X-TTS-Cache: hit` (second call), `X-TTS-Latency-Ms: XXX`.

### 3e. Speak endpoint — Dia NPC
```bash
curl -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Welcome to my tavern!","voice_preset":"tavern_keeper","emotion":"warm"}' \
  --output /tmp/test_dia.wav
```
Expected: WAV file, `X-TTS-Engine: dia`.

### 3f. Speak endpoint — Kokoro fallback
```bash
curl -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"System ready.","voice_preset":"system_voice"}' \
  --output /tmp/test_kokoro.wav
```
Expected: WAV file, `X-TTS-Engine: kokoro`, latency < 300ms.

### 3g. Cache hit test
```bash
# Run the grand_narrator request twice; second should be a cache hit
curl -I -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Roll for initiative.","voice_preset":"grand_narrator"}'
# Expected on 2nd call: X-TTS-Cache: hit, X-TTS-Latency-Ms near 0
```

### 3h. NPC conversation endpoint
```bash
curl -X POST http://localhost:8000/api/tts/speak-npc-conversation \
  -H "Content-Type: application/json" \
  -d '{"lines":[{"speaker":"S1","text":"What do you want?","voice_preset":"tavern_keeper"},{"speaker":"S2","text":"A room for the night.","voice_preset":"grand_narrator"}]}' \
  --output /tmp/test_conversation.wav
```
Expected: WAV file with two voices.

---

## 4. Nonverbal tag injection

Test Dia nonverbal injection logic:

```bash
# tavern_keeper + "!" → should inject [laughs]
curl -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Welcome back, brave adventurer!","voice_preset":"tavern_keeper","emotion":"warm"}' \
  -o /tmp/test_tavern_laugh.wav
# Play /tmp/test_tavern_laugh.wav — should hear a laugh

# shadow_villain + dramatic → should inject [sighs]
curl -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"You think you can stop me...","voice_preset":"shadow_villain","emotion":"dramatic"}' \
  -o /tmp/test_villain.wav
```

---

## 5. Frontend: voice dropdown

1. Open http://localhost:8000/play as DM
2. Open the sound flyout panel
3. Scroll to the [NARRATION] section
4. Verify the voice dropdown shows 3 groups:
   - `── NARRATORS (Chatterbox GPU) ──` with 4 options
   - `── NPC VOICES (Dia GPU) ──` with 8 options
   - `── SYSTEM (Kokoro CPU) ──` with 1 option

---

## 6. Frontend: TTS status row

After page load, the narration-integration-status div should show:
```
✓ GPU narration ready  •  Chatterbox + Dia + Kokoro
```

If only Kokoro loaded:
```
⚡ Partial: Kokoro ready
```

---

## 7. Frontend: warmup phrase chips

Below the narration textarea, you should see clickable phrase chips:
- "Roll for initiative."
- "Make a perception check."
- etc. (20 total)

Click one → it inserts into the textarea. ✓

---

## 8. Frontend: Preview button

1. Type "A figure emerges from the shadows." in narration textarea
2. Select "The Grand Narrator" from dropdown
3. Click [Preview]
4. Verify:
   - Status shows: "Generated in XXXms (CHATTERBOX)"
   - Audio plays locally in your browser
   - Panel header shows a golden glow animation while playing
   - narration-scroll-overlay appears with word-by-word text reveal
   - Players do NOT hear this (preview is local only)

---

## 9. Frontend: Broadcast button

1. Open a second browser tab as a player
2. Click the audio unlock overlay on the player tab ("Click to enable tavern audio")
3. Verify the DM panel shows: `🔊 PlayerName (audio ready)`
4. Type text in DM narration textarea
5. Click [Broadcast]
6. Verify on player tab: audio plays and narration scroll-overlay appears

---

## 10. Frontend: Stop button

1. Start a long narration playing on all clients
2. Click [Stop] on DM panel
3. Verify all connected clients stop audio immediately (<100ms)

---

## 11. Frontend: Audio unlock overlay

1. Open a NEW browser tab at http://localhost:8000/play (player URL)
2. Verify: A dark overlay appears with a pulsing rune icon (᛭) and text "Click to enable tavern audio"
3. Click anywhere on the page
4. Verify: Overlay disappears, DM panel updates to show `🔊 PlayerName`

---

## 12. Procedural ambient engine

1. On the DM panel, click [Tavern] ambient button
2. Verify: Tavern ambient sounds start playing (crowd murmur, fireplace warmth)
   with a 3-second crossfade
3. Click [Dungeon] — crossfades to drips + stone rumble
4. Click [Forest] — crossfades to wind/leaves + birds
5. Click [Battle] — crossfades to war drums + metallic shimmer
6. Click [Silence] — fades to silence over 500ms (no clicks/pops)
7. Click [Auto] — auto-detects ambient from current map terrain

---

## 13. Procedural SFX engine

Click each SFX button and verify distinct sounds:

| Button   | Expected sound                                  |
|----------|-------------------------------------------------|
| ⚔ Clash  | Short sharp metallic burst + reverb tail        |
| 🔥 Fireball | Noise swell with sub thump, fades ~600ms    |
| 🚪 Door  | Creaking FM + heavy thud                        |
| ⚡ Thunder | Multiple layered rumbles, stereo spread      |
| ✨ Heal  | Ascending C→G→C arpeggio with reverb halo       |
| 🪤 Trap  | Mechanical click + snap/slide down              |
| 😱 Gasp  | Breathy bandpass noise with wobble              |
| ⏹ Stop  | All SFX immediately silenced                    |

---

## 14. window.tavernTTS global API

Open browser DevTools console on the play page:

```javascript
// Test basic speak
await window.tavernTTS.speak("Hello adventurers!", "grand_narrator", "dramatic");

// Test NPC conversation
await window.tavernTTS.speakNPC([
  { speaker: "S1", text: "What manner of creature are you?", voice_preset: "tavern_keeper" },
  { speaker: "S2", text: "A friend... perhaps.", voice_preset: "shadow_villain" }
]);

// Test preload
window.tavernTTS.preload(["Roll for initiative.", "Make a perception check."]);

// Test stop
window.tavernTTS.stop();

// Test ambient
window.tavernAmbient.setScene("tavern");
window.tavernAmbient.setIntensity(0.8);
window.tavernAmbient.crossfadeTo("battle", 3.0);

// Test SFX
window.tavernSFX.play("clash");
window.tavernSFX.play("fireball");
window.tavernSFX.play("heal");
```

---

## 15. WebSocket relay verification

1. Open DevTools Network tab → WS filter
2. Click [Broadcast] as DM
3. Verify outgoing WS frame: `{"type":"tts_narration","payload":{"audio_b64":"...","voice_preset":"...","duration_ms":...}}`
4. Verify all player clients receive and play the audio

---

## 16. Generation speed benchmarks (RTX 5070 Ti)

Run after all engines are warmed up:

```bash
# Benchmark Chatterbox
time curl -s -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"The ancient tome whispers its secrets to those who dare to listen.","voice_preset":"grand_narrator"}' \
  -o /dev/null

# Expected: < 500ms for ~10 word sentence (50-80x realtime = 4s audio in ~60ms GPU time)

# Benchmark Dia
time curl -s -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Welcome to the Rusty Flagon, stranger.","voice_preset":"tavern_keeper"}' \
  -o /dev/null

# Benchmark Kokoro (CPU)
time curl -s -X POST http://localhost:8000/api/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"System ready.","voice_preset":"system_voice"}' \
  -o /dev/null
# Expected: < 200ms on Ryzen 9800X3D
```

---

## 17. Cache verification

```bash
curl http://localhost:8000/api/tts/status | python -m json.tool
```

After warmup and some requests:
- `cache_size` should be ≥ 20 (warmup phrases)
- `cache_hits` > 0 after repeated requests
- `cache_size_mb` should be growing but staying under 500MB

---

## Pass criteria summary

| Test | Criteria |
|------|----------|
| GPU startup | Both Chatterbox + Dia show `[GPU ✓]` in log |
| VRAM | nvidia-smi shows both models loaded, total < 12GB |
| API /status | `startup_ok: true`, all 3 engines `ready: true` |
| API /voices | 12 presets in 3 groups |
| Chatterbox speed | < 2s for 20-word sentence |
| Dia speed | < 3s for 20-word sentence |
| Kokoro speed | < 200ms always |
| Cache | Hit on 2nd identical request, latency ≈ 0ms |
| Frontend dropdown | 12 voices in 3 grouped optgroups |
| Phrase chips | 20 chips, clicking inserts text |
| Preview | Local audio only, no WebSocket broadcast |
| Broadcast | All connected players hear audio |
| Audio unlock | Overlay appears, dismisses on click, DM panel updates |
| Ambient | All 5 scenes, smooth 3s crossfade, no clicks/pops |
| SFX | All 8 sounds distinctly different |
| Stop | Immediate silence on all clients |
