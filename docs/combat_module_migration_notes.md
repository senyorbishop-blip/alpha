# Combat module migration notes (`gameplay/combat.js`)

Status: **groundwork only — module loaded, env complete, NO routing wired.**

## Summary

The goal was to make `client/static/js/gameplay/combat.js`
(`window.AppGameplayCombat`) the live path for combat UI / actions / rendering,
replacing the inline copies in `client/templates/play.html`, with exactly one
shared `combatApplyState` / `renderCombat` used by both the UI side and the
message side (`combat_messages.js`).

Investigation found the module is a **stale fork**, not an equivalent
extraction (its own header calls it "dormant… not loaded by play.html today").
Most exported functions have diverged from the live inline versions. Migrating
to the module as-is would regress combat behavior and **break role gating** —
both forbidden by the task's behavior-identical invariant. The decisive detail:
the message side already routes through the inline `window.*` globals
(`combat_messages.js` → `callIfPresent` → `getFn` falls back to `global[name]`),
so there is **already one live implementation — the inline one** — and the
module copies are dead code. Routing play.html through the module would not
*converge* the two sides; it would *replace* the good shared implementation with
the stale fork on both sides.

## What was done (safe, additive, reversible)

- `core/env_builders_gameplay.js`: completed `getCombatEnv` with the 3 missing
  members (`addLogEntry`, `getStore`, `getUserName`) so it now covers the full
  22-member surface the module expects.
- `play.html`: load `env_builders_gameplay.js` + `gameplay/combat.js` (after the
  message-handler scripts, before `render/boot.js`).
- `play.html`: added `buildCombatEnv()` — builds the full env-injected surface,
  every member pointing at the live inline functions/state (`getCombat`/
  `setCombat` read & write the same `_combat` object both sides share;
  `USER_ID` = `getEffectiveUserId()` to match inline gating semantics).
- `play.html`: one-time boot sanity check logging that the module + env builder
  loaded and `buildCombatEnv()` exposes all 22 members. **Nothing routes combat
  actions through the module.** Every inline function remains authoritative.

## Per-function divergence (inline = live/`main` vs. module)

Identical (thin `sendWS` wrappers — safe to shim if ever wanted): `combatNext`,
`combatPrev`, `combatClear`, `combatDash`, `combatToggleDifficultTerrain`,
`combatResetMovement`, `combatToggleDisengage`, `combatEndTurn`,
`combatRollDeathSave`, `combatResolvePending`, `combatEditInit`,
`sortCombatants`, `pushCombat`, `combatArmTarget`.

Diverged (must NOT be migrated without reconciliation):

| Function | Inline (live) | Module (stale) |
|---|---|---|
| `combatApplyState` | ~170 lines: revision conflict guards, accidental-empty reconnect guard, suspended/fog/hidden combatants, action-economy runtime, inspect reset, move-plan voiding, active-turn pulse, tab attention | ~15 lines: naive overwrite + badge |
| `renderCombat` | ~270 lines: dice-physics debounce, deferred-mount retry, authoritative-active guard, turn summary, off-turn tray, mark row, spell/weapon trays, roster normalization, suspended section, party panel, hostile suggestions | ~40 lines: basic list + move row |
| role gating (`isMyToken` / `canRollInitiative` / `canActCurrentTurn`) | `getEffectiveUserId()` + `_combatantOwnedByMe()` — resolves ownership even when token is unsynced/off-map | raw `env.USER_ID` / `t.owner_id` — breaks gating for unsynced tokens & multi-character |
| `combatStart` | filters `!t.staged`, richer init-mod resolution, sets `encounter_id` + action-economy runtime, `refreshRightPanelContextUI()` | none of that |
| `combatRollInitiative` | settle-based dice (`_rollLocalDiceAfterSettle`), popup-id correlation, optimistic update, pending flag | stale immediate `Math.random()` send |
| `combatRemove` | sends `combat_remove_combatant` to server (authoritative) | splices array locally |
| `combatSelectTarget` / `combatAttackSelected` | monster-quick flow, spell-slot picker, encumbrance disadvantage, `client_action_id` | basic versions |

## Recommended next step (separate effort)

Invert the migration: refresh `combat.js`'s diverged functions to match the live
inline code (kept env-injected), verify equivalence function-by-function, then
repoint play.html via shims and delete the inline bodies. Only then is "one
shared `combatApplyState` / `renderCombat`" achievable without regression.
`buildCombatEnv()` is already in place to support that work.
