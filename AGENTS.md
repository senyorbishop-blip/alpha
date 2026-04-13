# AGENTS.md — Tavern Tabletop / D&D repo operating guide

This file applies to the entire repository.

The main goal of this guide is to keep future Codex work aligned with the **actual runtime architecture** of this repo, especially the historically sensitive `client/templates/play.html` play page.

---

## 1. Read this first before changing code

Before major work, inspect these files first:

1. `docs/repo-map.md`
2. `docs/system-audit-20260320.md`
3. `main.py`
4. `client/templates/play.html`
5. `server/handlers/__init__.py`
6. relevant `server/handlers/*.py`
7. relevant tests in `tests/`

If the task touches maps or map import/library behavior, also inspect:

- `docs/map-library-imports.md`

If the task touches CI/test expectations, inspect:

- `.github/workflows/test.yml`
- `TESTING_CHECKLIST.md`

---

## 2. Repo layout at a practical level

### Runtime/backend

- `main.py`
  - FastAPI app entrypoint.
  - Owns app startup/lifespan, static mounts, page router setup, API router registration, and the live WebSocket endpoint.
- `server/handlers/__init__.py`
  - Live WebSocket message dispatch table.
  - If a WS message type changes, this file is usually part of the change.
- `server/handlers/`
  - Domain-specific live backend behavior.
  - Important files include:
    - `tokens.py`
    - `combat.py`
    - `map_editor.py`
    - `inventory.py`
    - `hazards.py`
    - `viewer_powers.py`
    - `conditions.py`
    - `content.py`
    - `narration.py`
    - `sound.py`
    - `common.py`

### Runtime/frontend

- `client/templates/play.html`
  - Main live tabletop page.
  - Historically central and still sensitive.
  - Still contains a large amount of runtime authority, glue code, and global state.
- `client/static/js/editor/`
  - Mix of loaded editor modules and dormant migration targets.
- `client/static/js/core/`
  - Mix of live compatibility shell code and dormant env-injection refactor files.
- `client/static/js/render/`
  - Some files are loaded by `play.html`, others are not.
- `client/static/js/gameplay/`
  - Present in repo, but do not assume live usage.
- `client/static/js/state/`
  - `state/store.js` is live as a shell store; the folder is not generally the full state authority.
- `client/static/js/ui/`
  - Contains both live UI modules and dormant modules.

### Documentation and tests

- `docs/repo-map.md`
  - Primary architecture map. Consult before major client refactors.
- `docs/system-audit-20260320.md`
  - Important runtime ownership notes for audio/narration and cleanup history.
- `docs/map-library-imports.md`
  - Runtime map library import/storage expectations.
- `tests/`
  - Architecture guardrails and regression coverage.

---

## 3. Current runtime sources of truth

In every final response after code changes, explicitly state which files you treated as the runtime source of truth.

### Backend source of truth

Treat these as authoritative unless your inspection proves a narrower owner for the specific feature:

- `main.py`
- `server/handlers/__init__.py`
- relevant `server/handlers/*.py`
- relevant persistence/schema files if the change touches save/restore behavior

### Frontend source of truth

#### Highest-priority live authority

- `client/templates/play.html`

For most play-page behavior, start by assuming `play.html` is still the live owner until you verify otherwise.

#### Slice-specific live authorities already used at runtime

- `client/static/js/editor/serialization.js`
  - authoritative map document serializer/normalizer
  - but still reads editor globals owned by `play.html`
- `client/static/js/ui/sound_engine.js`
  - live audio authority
- `client/static/js/ui/narration.js`
  - live narration authority
- `client/static/js/core/runtime_bridge.js`
  - live compatibility bridge into legacy `play.html` globals
- `client/static/js/core/boot_shell.js`
  - live boot shell, still delegating into `play.html`
- `client/static/js/core/ws.js`
  - live WS wrapper
- `client/static/js/core/message_dispatch.js`
  - live first-hop dispatch, not the final message application authority
- `client/static/js/state/store.js`
  - live shell/session/user/socket store
- `client/static/js/render/boot.js`
- `client/static/js/render/fog.js`
- `client/static/js/render/vision.js`
- `client/static/js/ui/tabs.js`
- `client/static/js/ui/chat.js`
- `client/static/js/ui/chat_log.js`
- loaded editor/render helper modules referenced by `play.html`

### Source-of-truth warning

Do **not** upgrade a dormant refactor file into the "real" implementation merely because it looks cleaner. If `play.html` still owns the live runtime path, changing only the dormant file is not a real fix.

---

## 4. What is loaded by `play.html` right now

These are the current important live browser modules loaded by `client/templates/play.html`:

### Loaded editor/runtime helpers

- `client/static/js/editor/serialization.js`
- `client/static/js/editor/terrain_manifest.js`
- `client/static/js/assets/dnd_assets.js`
- `client/static/js/editor/asset_initializer.js`
- `client/static/js/editor/asset_renderer.js`
- `client/static/js/editor/terrain_renderer.js`
- `client/static/js/editor/placement_controller.js`
- `client/static/js/editor/shop_panel.js`
- `client/static/js/editor/shop_view.js`
- `client/static/js/editor/assets.js`
- `client/static/js/ui/asset_library.js`
- `client/static/js/ui/editor_panel.js`
- `client/static/js/render/combat_fx.js`

### Loaded audio / compatibility helpers

- `client/static/js/ui/sound_engine.js`
- `client/static/js/ui/narration.js`
- `client/static/ambient_engine.js`
- `client/static/sfx_engine.js`
- `client/static/tts_client.js`

Treat `ambient_engine.js` and `sfx_engine.js` as compatibility/fallback support while they are still loaded.

### Loaded shell/bridge/render/ui files

- `client/static/js/state/store.js`
- `client/static/js/core/runtime_bridge.js`
- `client/static/js/core/boot_shell.js`
- `client/static/js/core/ws.js`
- `client/static/js/core/message_dispatch.js`
- `client/static/js/render/boot.js`
- `client/static/js/render/fog.js`
- `client/static/js/render/vision.js`
- `client/static/js/ui/tabs.js`
- `client/static/js/ui/chat.js`
- `client/static/js/ui/chat_log.js`
- `client/static/js/dice/dice3d.js`

### Also loaded on the page outside the core folders

- `client/static/js/map-library.js`
- `client/static/js/map-grid.js`
- `client/static/js/cartographer.js`

---

## 5. What is present but should not be assumed live

The repo contains an incomplete migration toward more modular/env-driven code.

Do **not** assume these folders/files are live unless you confirm they are script-tagged by a page and actually used in the runtime path:

- many files in `client/static/js/gameplay/`
- `client/static/js/core/message_handlers.js`
- `client/static/js/core/api.js`
- `client/static/js/core/env_builders.js`
- `client/static/js/core/env_builders_gameplay.js`
- `client/static/js/core/errors.js`
- non-loaded files in `client/static/js/render/`
- non-loaded files in `client/static/js/ui/`
- several non-loaded files in `client/static/js/editor/`

Rule: before editing one of these, verify in `play.html` whether it is actually loaded.

---

## 6. `play.html` rules

`client/templates/play.html` is sensitive and historically central.

### Do

- treat it as a primary live runtime surface
- preserve script load order unless the task explicitly requires changing it
- preserve compatibility when moving logic out of it
- trace indirect callers before removing globals
- assume DM/player/viewer behavior on this page is a live contract

### Do not

- casually split large sections out without verifying the live load path
- remove old glue code while the new module still depends on it indirectly
- edit a dormant module and assume the live page changed
- create a second active implementation beside the existing play-page one
- reorder script tags casually

### Special warning about indirect usage

Some loaded modules call back into `play.html` globals indirectly. If a function looks unused in local search, that is **not** proof it is safe to remove.

---

## 7. Preferred staged refactor order

Keep refactors staged and practical.

1. **Clarify runtime ownership first**
   - identify what is live, compatibility-only, fallback-only, and dormant
2. **Identify exact source-of-truth files for this task**
3. **Change the current live path first**
4. **Add/update tests for the behavior you changed**
5. **Validate multiplayer sync and play-page stability**
6. **Only later remove legacy code in a follow-up**

### For logic moving out of `play.html`

Use this order:

1. preserve current behavior in `play.html`
2. extract one vertical slice to a loaded module
3. keep compatibility shims while the page still depends on them
4. validate DM/player/viewer behavior
5. remove old path only after proving it is no longer called

### Avoid this anti-pattern

Do not make parallel edits that leave both:

- an old live implementation in `play.html`, and
- a second new live implementation in a module

One responsibility should have one live implementation.

---

## 8. Multiplayer sync and stability guardrails

When a task touches live gameplay behavior, assume multiplayer sync can regress even from "small" UI changes.

### Inspect all three layers when WS/gameplay behavior changes

1. client send/apply path
2. `main.py` websocket/runtime path
3. `server/handlers/__init__.py` dispatch + the relevant handler module

### Always preserve role behavior

Validate DM/player/viewer behavior for any change affecting:

- chat
- combat
- tokens
- fog/vision
- editor/map state
- narration/audio
- viewer powers
- session join/rejoin/state sync

### Special map-context warning

If a task touches local maps / POIs / scene maps / world map switching:

- verify POI or scene-map changes do not overwrite world-map state
- verify persistence still roundtrips correctly

---

## 9. Build / run / test commands

### Setup / run

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Alternative startup path used by some existing docs/checklists:

```bash
python main.py
```

### Main automated test command

Use the same baseline command CI uses:

```bash
python -m pytest tests/ -v --tb=short
```

---

## 10. How to validate frontend changes

For any perceptible frontend/play-page change:

### Minimum automated validation

Run relevant targeted tests first, then the full suite when feasible.

Common targeted choices:

```bash
python -m pytest tests/test_audio_broadcast.py -v --tb=short
python -m pytest tests/test_refactor.py -v --tb=short
python -m pytest tests/test_campaign_roundtrip.py -v --tb=short
python -m pytest tests/test_session_authority_and_scene_maps.py -v --tb=short
python -m pytest tests/ -v --tb=short
```

### Minimum manual validation

Use multiple browser windows/tabs where relevant:

1. DM creates/enters session
2. player joins
3. viewer joins if the feature touches broadcast/visibility/audio/chat
4. validate the changed feature
5. smoke-test:
   - page boot
   - WS connect/reconnect
   - token sync
   - side panels/chat/log
   - DM/player/viewer permissions

### If audio / narration changed

Also validate:

- ambient track switching
- narration preview
- narration broadcast to player(s)
- narration stop
- player audio unlock flow
- fallback path when premium voice/audio asset paths are unavailable

### Screenshots

If you make a perceptible front-end change and the environment allows it, take a screenshot.

---

## 11. How to validate backend changes

### Minimum automated validation

```bash
python -m pytest tests/test_refactor.py -v --tb=short
python -m pytest tests/test_campaign_roundtrip.py -v --tb=short
python -m pytest tests/test_persistence_schema.py -v --tb=short
python -m pytest tests/test_session_authority_and_scene_maps.py -v --tb=short
python -m pytest tests/test_player_permissions.py -v --tb=short
python -m pytest tests/ -v --tb=short
```

### Manual backend validation

If handlers/routes/session persistence changed, verify:

- expected WS message still reaches the intended handler
- reconnect/state sync still works
- multiplayer sync still works across roles
- save/restore still preserves the relevant state
- scene-map behavior still isolates world-map state correctly

---

## 12. Important task-specific hotspots

### If changing editor/map behavior

Inspect first:

- `client/templates/play.html`
- `client/static/js/editor/serialization.js`
- relevant `server/handlers/map_editor.py`
- related persistence/restore tests
- `docs/map-library-imports.md` if imports/library behavior are involved

### If changing audio/narration

Inspect first:

- `client/templates/play.html`
- `client/static/js/ui/sound_engine.js`
- `client/static/js/ui/narration.js`
- `server/handlers/sound.py`
- `server/handlers/narration.py`
- `docs/system-audit-20260320.md`
- `tests/test_audio_broadcast.py`

### If changing sync/combat/token behavior

Inspect first:

- `main.py`
- `server/handlers/__init__.py`
- relevant handler modules in `server/handlers/`
- `client/templates/play.html`
- sync/persistence tests in `tests/`

---

## 13. Final output requirements for future agents

In the final response after making changes:

- explicitly state which files were treated as source of truth
- include validation notes
- list exact commands run for checks/tests
- call out warnings/limitations honestly

If frontend runtime behavior changed, also include:

- what manual validation was performed
- whether DM/player/viewer behavior was checked
- whether a screenshot was taken

