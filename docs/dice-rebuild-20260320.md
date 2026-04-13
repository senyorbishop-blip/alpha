# Premium Dice Rebuild — March 20, 2026

## Audit Summary

### Conflicts found
- The prior `client/static/js/dice/dice3d.js` implementation was not physics-authentic. It animated dice along scripted paths, stored `resultValue` separately, and `detectUpFace()` returned the assigned result instead of reading the final mesh orientation.
- `client/templates/play.html` was already wired to a 3D-only overlay, but the result pipeline still treated the visible dice as presentation while authoritative values arrived separately via websocket and were injected after the throw.
- `server/handlers/content.py` resolved `d100` as a single `1..100` random integer instead of percentile tens/ones logic.
- Theme persistence existed only as a loose local color set; there was no formal theme catalog or preset selection.

### Refactor strategy
- Keep the app's live websocket and overlay hooks in `play.html`, but replace the dice engine behind `window.DicePhysics3D`.
- Convert the renderer to a tray-focused Three.js presentation with a real physics world driven by `cannon-es`.
- Replace fake result assignment with explicit face metadata and quaternion-based top-face detection.
- Preserve the current public API shape so existing UI code continues to work while the internals become authoritative and orientation-based.

## Implementation Notes

### Rendering / tray
- The rebuilt renderer creates a framed tray with a felt floor, raised walls, cinematic lighting, fog, and auto-fit camera tuning for larger dice pools.
- Dice are now rendered as 3D meshes with per-face labels attached to actual face centers instead of overlay cards pretending to be dice.

### Physics
- Dice now use rigid bodies in `cannon-es`.
- The tray has a floor and four walls as static colliders.
- Dice types use per-shape mass and settle thresholds so d4/d6/d20-class dice do not all behave identically.
- Continuous collision detection and tuned damping are enabled to reduce tunneling, endless bounce, and post-settle jitter.

### Result detection
- Every die definition carries explicit face metadata with local face center, local outward normal, and mapped value.
- On settle, the engine rotates each local normal into world space using the die quaternion, computes the dot product against world up, and selects the face with the highest score.
- The result is accepted only when velocity is low for a sustained window and the winning face is not ambiguous.

### Percentile / d100
- `d100` now rolls as two dice visually and logically: one percentile die (`00`–`90`) plus one units die (`0`–`9`).
- Server payloads include `percentile_pairs` so authoritative logic can remain inspectable and consistent.

### Themes / persistence
- Added formal preset themes: `obsidian-gold`, `emerald-ivory`, `arcane-glass`, and `bone-crimson`.
- Player preferences still persist client-side for now through local storage; no database schema change was required for this pass.
- The UI now exposes a preset selector while preserving custom color overrides.

## Integration Hooks
- `rollDice()` remains the entry point for the dice flyout.
- `showDiceAnimation()` still owns overlay/tray presentation.
- `fillDiceResult()` remains the websocket ingestion point for authoritative results.
- `handle_dice_roll()` remains the server entry point and now includes seed/mode/theme metadata plus percentile pair details for `d100`.

## Future Upgrades
- Broadcast spectator tray replays for remote players so all clients watch the same landing.
- Add audio material sets, magical impact FX, and unlockable dice packs.
- Move theme preference persistence to a player profile schema when account-backed cosmetics are ready.
- Add browser automation coverage for repeat-roll stress tests and cocked-die handling.
