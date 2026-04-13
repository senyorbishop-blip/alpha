# Dice System Audit — March 2026

## Overview

This document records the full audit of the dice system in this repository, including all
dice-related files, the identified architecture, clashes found, fixes applied, and the
single production-ready pipeline that remains after cleanup.

---

## All Dice-Related Files Found

| File | Status | Role |
|---|---|---|
| `client/static/js/dice/dice3d.js` | **Active** | 3-D physics dice system (ES module, primary path) |
| `client/templates/play.html` (lines 232–247, 560, 850–929) | **Active** | Dice CSS: overlay, canvas, result popup, 3-D wrap |
| `client/templates/play.html` (lines 2199–2215) | **Active** | Dice Tray flyout HTML (`#flyout-dice`) |
| `client/templates/play.html` (lines 2945–2954) | **Active** | Dice overlay HTML (`#dice-overlay`, `#dice-3d-wrap`) |
| `client/templates/play.html` (lines 11506–12078) | **Active** | All dice JS: `selectDice`, `rollDice`, 2-D animation, `showDiceAnimation`, `fillDiceResult`, `closeDiceOverlay` |
| `client/templates/play.html` (line 14395–14404) | **Active** | `dice_result` WebSocket handler (inline switch-case) |
| `server/handlers/content.py` (`handle_dice_roll`) | **Active** | Server-side roll resolution + broadcast |
| `server/handlers/__init__.py` (line 125) | **Active** | Dispatch table: `"dice_roll": handle_dice_roll` |
| `client/static/js/core/message_handlers.js` (`handleDiceResult`) | **Unloaded (dead)** | Duplicate WS handler — NOT loaded by play.html |
| `client/static/js/core/env_builders_gameplay.js` | **Unloaded (dead)** | Passes `showDiceAnimation`/`fillDiceResult` into combat env — module not loaded |
| `client/static/js/gameplay/combat.js` | **Unloaded (dead)** | Uses `env.showDiceAnimation` / `env.fillDiceResult` — not loaded |

---

## Architecture of the Active Dice Pipeline

```
User clicks Roll (or code triggers a roll)
        │
        ▼
rollDice() / showDiceAnimation(type, qty, null)   [play.html]
        │
        ├─── DicePhysics3D.isReady? ──YES──► DicePhysics3D.throw(configs, onSettle)
        │                                          │ dice-3d-wrap shown
        │                                          │ dice-canvas-wrap hidden (use-3d)
        │                                          │ dice-overlay-bg fade in
        │                                          ▼
        │                                     Physics loop (dice3d.js)
        │
        └─── NO ──► 2-D canvas animation (play.html animateDice loop)
                         dice-canvas-wrap shown
                         dice-overlay open
                         animation runs 1600 ms
        │
        ▼  (simultaneously, or shortly after for WS rolls)
sendWS({ type: 'dice_roll', ... })   [play.html]
        │
        ▼  (server)
handle_dice_roll(payload)            [server/handlers/content.py]
  random.randint(1, dice_type) × qty
  broadcast 'dice_result' to all users in session
        │
        ▼  (client WS switch)
case 'dice_result':                  [play.html line 14395]
  addLogEntry(..., type: 'dice')
  if (p.user_id === USER_ID):
    fillDiceResult(rolls, total, ...)
  flash roll button
        │
        ▼
fillDiceResult(rolls, total, ...)    [play.html]
        │
        ├─── DicePhysics3D.isReady? ──YES──► DicePhysics3D.setResult(rolls)
        │                                          │ dice settle and snap to result
        │                                          │ onSettle fires
        │                                          ▼
        │                                    _showDice3DResultPopup(meta)
        │                                    #dice-result-popup shown
        │                                    nat-20 / nat-1 FX if applicable
        │
        └─── NO ──► _diceResult = rolls
                    if already settled → revealDiceResultPopup()
                    else → waits for animateDice to finish
        │
        ▼  (user clicks overlay or auto-timeout)
closeDiceOverlay()                   [play.html]
  - removes all .open / .active / .visible classes
  - cancels rAF and timeouts
  - clears canvas
  - DicePhysics3D.close() if 3-D path was used
```

---

## Clashes and Issues Found

### Issue 1 — Dead `@dimforge/rapier3d-compat` entry in importmap (FIXED)

**Location:** `client/templates/play.html`, lines 11–19 (importmap)

**Problem:** The importmap declared `@dimforge/rapier3d-compat` pointing to a CDN URL for a
Rapier physics WASM library. However, `dice3d.js` uses its own custom physics simulation and
does **not** import Rapier. No JS file in the repository imports `@dimforge/rapier3d-compat`.
The entry was dead code: misleading to developers, and would trigger an unnecessary network
request if any file ever accidentally imported it.

**Fix applied:** Removed the `@dimforge/rapier3d-compat` entry from the importmap. The importmap
now correctly declares only the two dependencies actually used by `dice3d.js`:
- `"three"` → Three.js ES module (CDN)
- `"three/addons/"` → Three.js addons (CDN)

---

### Issue 2 — `env.flashRollButton()` called in unloaded `message_handlers.js` (FIXED)

**Location:** `client/static/js/core/message_handlers.js`, line 508

**Problem:** The `handleDiceResult` function in `message_handlers.js` called `env.flashRollButton()`.
This function is:
1. Not defined anywhere in `play.html`
2. Not wired up in `env_builders_gameplay.js`
3. Not present in any loaded module

`message_handlers.js` is an **unloaded** module (see repo-map.md — it belongs to the unconnected
env-injection refactoring). It does not run in production. However, if this module were ever
connected to `play.html`, calling `env.flashRollButton()` would throw a runtime error (`TypeError:
env.flashRollButton is not a function`), silently swallowing subsequent code.

The actual roll-button flash behaviour is implemented inline in play.html's `dice_result` WS
handler (lines 14402–14403):
```javascript
const rb = document.querySelector('.roll-btn');
if (rb) { rb.style.boxShadow = '0 0 20px rgba(139,26,26,0.9)'; setTimeout(() => rb.style.boxShadow = '', 600); }
```

**Fix applied:** Removed the `env.flashRollButton()` call from `message_handlers.js`.
If `message_handlers.js` is ever connected to `play.html`, the inline flash in play.html's
`dice_result` handler already covers this behaviour; no separate `flashRollButton` env method
is needed.

---

### Issue 3 — Stale "bridge logic" comment at end of play.html (FIXED)

**Location:** `client/templates/play.html`, former line 19531

**Problem:** A stale comment `// (3-D dice bridge logic is now inline in showDiceAnimation / fillDiceResult / closeDiceOverlay above)` implied a prior architecture where the 3-D bridge was a separate section that had been migrated. The comment added no information and could confuse future developers.

**Fix applied:** Comment removed.

---

## No-Action Findings

The following potential clashes were investigated and found to be **non-issues**:

### `message_handlers.js` handleDiceResult vs inline `dice_result` handler
Both exist but `message_handlers.js` is NOT loaded by play.html. Only the inline handler at
line 14395 runs. No double-handling occurs at runtime.

### `combat.js` uses `env.showDiceAnimation` / `env.fillDiceResult`
`combat.js` (and its env builder) is an unloaded module. Initiative rolls in play.html are
handled directly at line 19318–19319 inline. No clash.

### 3-D and 2-D dice paths co-existing in `showDiceAnimation`
This is intentional: `showDiceAnimation` checks `window.DicePhysics3D && window.DicePhysics3D.isReady`
and takes the 3-D path if available, falling back to the 2-D canvas animation otherwise. The
2-D fallback is not dead code—it ensures dice work even if Three.js fails to load (network
error, CSP issue, etc.).

### `#dice-result-popup` z-index with 3-D canvas
Both `#dice-overlay` (containing the popup) and `#dice-3d-wrap` (containing the THREE.js canvas)
have `z-index: 10061`. Since `#dice-3d-wrap` comes later in DOM order it is painted on top.
However, the THREE.js renderer uses `alpha: true` with `setClearColor(0x000000, 0)`, producing
a transparent canvas. The browser composites transparent WebGL pixels with what was painted
before them at lower stacking order, which includes `#dice-overlay`. Result: the popup is
visible through transparent canvas regions. The `_labelCanvas` from `dice3d.js` is at
`z-index: 10062`, above everything, to show per-die result labels. This design is correct.

---

## Final State: Single Dice Pipeline

After this audit and cleanup, the dice system has **one clear pipeline**:

| Concern | Owner |
|---|---|
| Entry point | `rollDice()` in play.html; or direct `showDiceAnimation()` + `fillDiceResult()` call |
| Animation (primary) | `dice3d.js` via `window.DicePhysics3D.throw()` |
| Animation (fallback) | 2-D canvas in play.html (`animateDice` rAF loop) |
| Roll resolution | Server: `handle_dice_roll` in `content.py` → broadcast `dice_result` |
| Result ingestion | `fillDiceResult()` in play.html → `DicePhysics3D.setResult()` or `_diceResult` var |
| Cleanup | `closeDiceOverlay()` in play.html → also calls `DicePhysics3D.close()` |
| WS handler | Inline `dice_result` switch-case in play.html (line 14395) |
| State model | `_diceAnimType`, `_diceResult`, `_dice3dRollMeta` etc. — all in play.html |
| CSS | Inline `<style>` in play.html — no external CSS for dice |

No legacy code paths remain attached. No duplicate handlers fire. No old imports referenced.

---

## Remaining Risks / Follow-up Suggestions

1. **`message_handlers.js` drift** — As an unloaded module, `handleDiceResult` in
   `message_handlers.js` may continue to drift from the actual behaviour in play.html. If the
   env-injection refactoring is ever completed, `handleDiceResult` will need to be re-audited
   and `flashRollButton` equivalent wiring reviewed. See repo-map.md for full guidance on the
   unloaded module situation.

2. **No server-side modifier validation** — `handle_dice_roll` in `content.py` applies the
   modifier passed by the client without range clamping. A malicious client could pass an
   extreme modifier. Consider adding `modifier = max(-999, min(999, modifier))` or similar.

3. **2-D fallback coverage** — The 2-D canvas animation is a complete fallback but is only
   lightly maintained. If the Three.js CDN is blocked, the fallback activates. The fallback
   does not support Nat-20/Nat-1 FX for the 3-D visuals but still triggers `showNat20FX()`
   and `showNat1FX()` via `revealDiceResultPopup()`. This is acceptable.

4. **No automated browser tests for dice** — The existing test suite only covers server-side
   Python. The dice render path (both 3-D and 2-D) has no automated test coverage. Manual
   verification is required after any changes to `dice3d.js` or the `showDiceAnimation` /
   `fillDiceResult` functions.

---

## Stage 3 trust/readability polish (2026-03-30)

- Kept the server `dice_result` payload as the authoritative source for displayed totals/rolls.
- Preserved landed-face inspection by comparing settled physics faces against authoritative
  rolls and flagging mismatches in the dice UI copy/logging.
- Tightened multi-die throw containment in `physics/BodyFactory.js` by reducing spawn spread and
  lateral velocity, improving in-frame readability for repeated pool rolls.
- Adjusted reveal timing to scale with dice count (shorter for single-die, slightly longer for pools)
  so players can read landings without delaying routine rolls.
