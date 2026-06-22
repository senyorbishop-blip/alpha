# Realtime Sync Engine v1 — Audit & Patch Plan

Scope note on the requested file list: the task referenced `server/handlers/init.py`.
That file does not exist; the actual message-dispatch hub is
`server/handlers/__init__.py` (`handle_message()`), and that is what this audit
covers.

This document does **not** propose a redesign. It keeps FastAPI, keeps
WebSockets, keeps `play.html` as the gameplay-state-application layer, and does
not introduce a separate game engine or external infra (no Redis). It is a map
of what the current live-sync system already does well, where it can still
desync, and what to fix next, in the smallest possible steps.

## 1. Current live-sync architecture

- Single WebSocket per `(session_id, user_id)`, served by the FastAPI endpoint
  in `main.py:websocket_endpoint`. The registry/broadcaster is the
  `ConnectionManager` singleton in `server/connections.py`.
- On connect, `ConnectionManager.connect()` detects whether a different socket
  object already owns that `user_id` and, if so, closes the old one with code
  `1001` ("Replaced by a newer connection") and replaces the registry entry.
  This is the single-owner-per-user invariant the reconnect-storm fix relies
  on; it is paired with client-side logic (`ws.js`) that recognizes its own
  socket was replaced and does **not** schedule a reconnect for it.
- The receive loop (`main.py`) updates a per-connection `last_pong["t"]`
  timestamp on **every** inbound frame (not just `pong`), then special-cases
  `pong`, then applies role-based message filtering (`_VIEWER_ALLOWED`,
  `_PLAYER_DENIED`, `_ASSISTANT_DM_DENIED`), then dispatches via
  `handle_message()`.
- `handle_message()` in `server/handlers/__init__.py` is a single dict-based
  dispatch table (~150+ message types) mapping `msg_type -> handler`. Each
  handler lives in a `server/handlers/*.py` module organized by subsystem
  (tokens, combat, map_editor/fog, inventory, hazards, conditions, etc.).
- Outbound delivery has three shapes, all built on `ConnectionManager`:
  - `send_to(session_id, user_id, message)` — single recipient.
  - `broadcast(session_id, message, exclude_user=None)` — everyone.
  - Per-user filtered loops in `server/handlers/common.py`
    (`_broadcast_token_event`, `_broadcast_token_visibility`,
    `_broadcast_combat`, `_combat_state_payload_for_user`,
    `_visible_tokens_payload_for_user`) that compute a different payload (or
    no payload) per recipient based on role/visibility/fog, then call
    `send_to` per user. This is the mechanism that keeps hidden tokens, fogged
    NPCs, and DM-only combat data out of player/viewer payloads.
- Client-side, every inbound frame travels `ws.js` (`AppWS`, the single socket
  owner + heartbeat/reconnect/outbound-queue layer) →
  `message_dispatch.js` (`AppMessageDispatch`, thin recursion-guarded relay) →
  `runtime_bridge.js` (`AppRuntimeBridge`, env-adapter that also owns the
  "request full state once per real reconnect" logic) → the legacy
  `handleLegacyMessage` switch statement inside `play.html`, which is still
  the place where most gameplay state is actually applied to in-memory
  objects (`tokens`, `_combat`, `fogMaps`, etc.) and redrawn.
- Three independent revision counters already exist and are already wired
  into broadcasts:
  - `session.visibility_revision` (int, `server/session.py`) — bumped by
    `bump_visibility_revision()` in `server/handlers/common.py` whenever fog,
    hidden state, or (after this patch) token position changes. Carried on
    `tokens_sync` payloads as `visibility_revision`.
  - `session.combat["revision"]` — bumped by `_bump_combat_revision()` in
    `server/handlers/combat.py`, carried on `combat_state` payloads.
  - `session.fog_maps[map_ctx]["revision"]` — bumped per-map-context inside
    `handle_fog_toggle` / `handle_fog_paint` in `server/handlers/map_editor.py`,
    carried on `fog_state` / `fog_update` payloads.
- Client-side, `play.html` already tracks per-stream "last applied revision"
  in `_lastVisibilityRevisionByStream` (keyed by stream name, e.g. `'tokens'`,
  `'combat'`), guarded by `_isStaleVisibilityPayload(payload, stream)`. This
  exists specifically because an earlier shared single counter caused
  cross-stream false-positive staleness drops between `tokens_sync` and
  `combat_state` — the per-stream design is deliberate and should be reused,
  not replaced, by any new revision work.

## 2. What is already good

- **Single-socket-owner reconnect handling.** The server closes the old
  socket explicitly with a distinguishable close code, and the client
  recognizes "I was replaced" vs. "I was disconnected" and only reconnects in
  the latter case. This is the right shape for preventing reconnect storms and
  is covered by `tests/test_ws_single_owner_reconnect_storm.py`,
  `tests/test_ws_lifecycle_hardening.py`, and
  `tests/test_connection_manager_socket_identity.py`.
- **Heartbeat liveness that doesn't false-positive during busy gameplay.**
  `last_pong["t"]` is refreshed on *any* valid frame, not only `pong`, and the
  client replies to `ping` at the transport layer (`ws.js`) before gameplay
  dispatch even sees it. This avoids the documented failure mode where a
  player mid-combat (sending lots of frames, but not literally `pong`) got
  force-disconnected by a heartbeat timeout. Covered by
  `tests/test_ws_heartbeat_server.py` and `tests/test_ws_heartbeat_pong_client.py`.
- **Per-stream stale-payload rejection, not a shared global counter.**
  `_isStaleVisibilityPayload` keys its "last seen" state by stream name. This
  was clearly hard-won (the in-code comment explains the bug it fixes) and is
  exactly the right primitive to extend rather than replace. Covered by
  `tests/test_runtime_invariants_guard.py::test_visibility_gate_is_per_stream_not_a_shared_scalar`.
- **Combat already does preview/commit with server-side re-validation.**
  `_handle_combat_move_plan` in `server/handlers/combat.py` accepts a
  client-computed `expected_cost_ft` for a movement preview, but recomputes
  the real cost server-side and rejects the commit ("Movement cost changed on
  the server; preview again.") if the client's number doesn't match within
  tolerance. This is the target pattern for every other "client previews,
  server reconciles" surface (drag preview, ruler, etc.) and should be held up
  as the example when extending other systems.
- **Combat revision reconciliation favors correctness over strict
  ordering.** `combatApplyState` / `handleCombatStateLive` in `play.html`
  don't just compare `incomingRevision > localRevision`; they also compute a
  signature over initiative order and apply the update if the signature
  changed even on an equal/lower revision. This avoids a narrow class of bugs
  where a legitimately new combat state arrives with a revision that didn't
  monotonically increase from the client's point of view (e.g. due to a
  reconnect re-fetch), at the cost of being slightly more permissive than a
  strict revision gate. That tradeoff is reasonable for a low-frequency,
  high-importance stream like combat order.
- **Reconnect already triggers an explicit full-state pull for the streams
  that need it.** `runtime_bridge.js`'s `onOpen` handler sends `request_state`
  (reason `'reconnect'`), `treasury_get`, and conditionally
  `combat_state_request` if combat is active/unknown — all funneled through
  `AppWS.requestInitialStateOnce` so they fire exactly once per real socket
  open, not once per dispatched message. `handle_combat_state_request` in
  `server/handlers/combat.py` is the matching server-side explicit resync
  endpoint.
- **Outbound resilience across brief disconnects.** `ws.js` queues messages
  while disconnected (capped at 200) and flushes them on reconnect, with
  type-based de-duplication for high-frequency/idempotent message types
  (`local_map_enter`/`local_map_exit`, editor saves) so a flush doesn't replay
  a stack of redundant nav/save events.

## 3. Where desync can still happen

- **`token_moved` had no staleness protection at all** (fixed by the tiny
  patch in this PR — see §11). It is the highest-frequency message in the
  system (every drag-release, every step of server-driven movement) and,
  before this patch, carried no revision field and had no ordering guard on
  the client. A reordered/delayed `token_moved` (plausible on a flaky mobile
  connection, where TCP-level reordering across reconnects or queued/flushed
  messages can put two `token_moved` packets out of send order relative to
  each other) could snap a token back to a stale position with no way for the
  client to know it was looking at old data.
- **Per-handler revision discipline is inconsistent within combat itself.**
  `_bump_combat_revision()` is called from `handle_combat_add_token`,
  `handle_combat_remove_combatant`, `handle_combat_update`, `handle_combat_next`,
  `handle_combat_prev`, and `handle_combat_roll_initiative`, but **not** from
  `handle_combat_dash`, `handle_combat_toggle_difficult_terrain`,
  `handle_combat_toggle_disengage`, `handle_combat_reset_movement`,
  `handle_combat_death_save`, `handle_combat_select_target`, or the
  move-preview/commit flow. Any of those mutate `session.combat` state that
  matters to other clients (e.g. disengage/difficult-terrain flags affect
  movement legality for everyone), but a client that missed the broadcast (or
  applied an older one out of order) has no revision signal telling it the
  data is stale.
- **Inventory has zero revision/sequence infrastructure** (`grep -c revision
  server/handlers/inventory.py` is 0). Item charges, shop/crafting/loot state,
  and corpse harvesting all broadcast plain "current state" messages with no
  way for a client to detect it applied an out-of-order update.
- **Fog deltas (`fog_update`) carry a revision but nothing rejects a stale
  one.** `client/static/js/render/fog.js`'s `fogApplyUpdate` stores
  `state.lastFogUpdateRevision` from the incoming payload, but never compares
  it against the previous value before applying — it always applies. A
  reordered `fog_update` (sparse cell delta) can flip cells back to a stale
  bitstring with no rejection.
- **`token_moved` is excluded from the mover's own connection, and the mover
  applies its own move optimistically with no equivalent reconciliation
  point.** This is fine in the common case, but if the server-side move was
  actually rejected or clamped (e.g. `find_movement_blocker`, or the
  budget-validated combat move path) the mover relies on a separate
  `token_move_denied` message to roll back. That path exists and works, but it
  means there are now two different "this is the truth" messages
  (`token_moved` for everyone else, `token_move_denied` for the mover on
  rejection) with different payload shapes and, before this patch, neither
  carried a revision.
- **DM-side fog paint is optimistic-local with a server round trip on a
  timer, not per-stroke.** `fogPaintAt`/`fogFlushBatch` batch and debounce
  (80ms) local paint before sending `fog_paint`. This is a reasonable UX
  tradeoff (smooth painting), but it does mean a DM's local fog state and the
  server's authoritative fog state can diverge for up to one debounce window,
  and if the DM's client disconnects mid-batch, that local-only paint is lost
  silently (no "are you sure"/queued-send guarantee beyond the existing
  message queue cap).

## 4. Which messages are currently server-authoritative

- Token position (`token_moved`, `token_move_denied`) — server validates
  movement blockers and (in combat) movement budget before committing
  `token.x`/`token.y`, then broadcasts.
- Token HP / temp HP / hidden state — `_apply_damage`/`_apply_heal` and the
  hidden-state handlers mutate the `Token` object server-side first, then
  broadcast via `_broadcast_token_event`/`_broadcast_token_visibility`.
- Fog visibility (cell grid) — `handle_fog_toggle`/`handle_fog_paint` mutate
  `session.fog_maps[ctx]` server-side, then broadcast `fog_state`/`fog_update`.
- Combat order / active turn / initiative — `session.combat` dict is the
  single source of truth, mutated by the combat handlers, then broadcast via
  `_broadcast_combat`.
- Map context / DM navigation — `session.dm_map_context`,
  `map_nav_version`, `dm_nav_intent` are server-tracked monotonic fields used
  to resolve races between DM map navigation and stale client-side nav state.
- Viewer permissions / role-based filtering — enforced both at the message-
  filtering layer in `main.py` (`_VIEWER_ALLOWED` etc.) and again inside the
  per-user payload builders in `common.py` (`_visible_tokens_payload_for_user`,
  `_combat_state_payload_for_user`), i.e. defense in depth rather than a
  single client-trust point.

## 5. Which messages rely too much on client-side optimistic state

- **`token_moved` (pre-patch)** — broadcast with no revision, and the
  receiving client had no way to detect or reject an out-of-order delivery.
  Partially addressed by this PR's tiny patch (§11); full risk-closure still
  needs the same treatment applied consistently to `token_move_denied` and to
  any other position-affecting broadcast.
- **Inventory state broadcasts** — no revision at all, so a client that
  receives two inventory updates out of order (e.g. across a brief
  disconnect/reconnect + queued-message flush) has no signal that the second
  one it received is actually the older one.
- **Fog deltas (`fog_update`)** — revision is stored but never checked before
  applying.
- **Several combat sub-actions** (dash, disengage, difficult terrain toggle,
  death saves, target selection) don't bump `combat["revision"]` even though
  they mutate shared combat state, so a client can't use the revision gate to
  detect it's behind on those specific fields.

## 6. Which state streams need revisions/sequence numbers

In priority order (highest desync risk × highest message frequency first):

1. **Token position (`token_moved`)** — done in this PR (§11); reuses
   `session.visibility_revision`, the same counter `tokens_sync` already
   stamps, so the two streams stay comparable on the client.
2. **Inventory** (item charges, shop/crafting/loot, corpse harvesting) — needs
   its own counter (e.g. `inventory_revision`), analogous to
   `visibility_revision`, stamped on every inventory-affecting broadcast.
3. **The combat sub-actions that don't currently call
   `_bump_combat_revision()`** — no new counter needed, just consistent use of
   the one that already exists.
4. **Fog deltas** — revision already present in the payload; this is really a
   client-side rejection gap (see §9), not a missing-counter gap.

## 7. Which systems need smooth visual interpolation

- **Token movement is the only strong candidate**, and only once its sync
  stream is provably safe (see the explicit ordering constraint in the task:
  interpolation is Option D and should only be applied "if that stream is
  already safe"). Before this PR, `token_moved` had no staleness gate, so
  interpolating toward a value that might be stale would visually mask the
  desync rather than fix it — worse, not better. After this PR's revision
  gate lands and proves stable, token movement is well-suited to
  interpolation: positions already arrive as discrete `(x, y)` snapshots with
  no physics/velocity payload, so a simple lerp-toward-latest-authoritative-
  position over a short fixed window (e.g. 80-120ms) would remove the
  "teleport" feel for everyone *except* the mover (who already sees their own
  drag locally) without changing any wire format.
- No other stream is a good interpolation candidate: HP changes are discrete
  and expected to feel discrete (damage numbers, not a tween), fog is a
  binary cell grid, combat order is inherently a list reorder, and
  inventory/charges are also discrete counters.

## 8. Which systems need full snapshot recovery after reconnect

- **Already have it:** combat (`combat_state_request` /
  `handle_combat_state_request`), treasury (`treasury_get`), and general
  player state (`request_state`) — all funneled through
  `AppWS.requestInitialStateOnce` in `runtime_bridge.js`'s `onOpen` handler.
- **Implicit, not explicit:** tokens and fog currently rely on the
  *connect-time* `state_sync`/`tokens_sync` payload that the server sends as
  part of the initial WebSocket accept flow in `main.py`, not on a
  client-initiated post-reconnect pull analogous to `combat_state_request`.
  In practice this means a reconnect already gets a fresh token/fog snapshot
  (good), but there's no equivalent of `handle_combat_state_request` for
  tokens/fog if something more targeted is ever needed (e.g. "I think I'm
  behind on tokens specifically, without re-running the entire connect
  handshake"). Not an active bug today — `state_sync` already covers it — but
  worth noting as the reconnect-recovery story is least explicit for these two
  streams.
- **Inventory has no explicit reconnect recovery path** beyond whatever is
  included in the general `state_sync`/`request_state` payload; this should
  be verified against the same template as combat once `inventory_revision`
  exists, so a client that detects an inventory revision gap can request a
  fresh inventory snapshot the same way combat does.

## 9. Which systems need delta updates

- **Already delta-based:** fog (`fog_update` sends sparse cell indices, not
  the whole grid), token position (`token_moved` is a single token's `x`/`y`,
  not a full token re-send), combat (`combat_state` is a full combat-object
  resend today — see below).
- **Could become delta-based but isn't a priority:** `combat_state` resends
  the entire `session.combat` payload (including the full combatants list) on
  every change. For typical D&D party sizes (a handful of combatants) this is
  not a meaningful bandwidth or performance concern, so converting it to a
  delta format is **not recommended** — it would add complexity (diffing,
  merge logic) for a stream that's already small and already has solid
  revision+signature reconciliation. Leave as full-resend.
- **Inventory** would benefit from per-item delta messages (e.g. "item X now
  has N charges") rather than resending an entire inventory/shop state blob,
  once it has a revision counter to make ordering of those deltas safe.

## 10. Which systems should stay event-based

- Dice rolls, chat messages, narration hooks, scene/hazard triggers,
  emotes — these are inherently one-shot events, not state to reconcile. They
  should NOT get a revision/snapshot-recovery treatment; a missed chat message
  during a brief disconnect is expected/acceptable lost history, not a
  desync.
- UI-only state (modals, hover, ruler/path preview, dice animation) is
  explicitly client-local per the task's design direction and was confirmed
  not to be server-broadcast for any of the files audited — correctly so.

## 11. What tiny patches should be done first

Recommended order (each is independently shippable, smallest blast-radius
first):

1. **(this PR) Add revision/sequence handling + stale-packet rejection to
   `token_moved`.** Done — see "Tiny patch implemented" below.
2. **Apply `_bump_combat_revision()` consistently** to the combat handlers
   that currently skip it (dash, disengage toggle, difficult-terrain toggle,
   reset-movement, death-save, select-target). Pure consistency fix, no new
   infrastructure, very low risk.
3. **Add stale-packet rejection for `fog_update`** using the revision value
   it already carries but doesn't check — mirror the `_isStaleVisibilityPayload`
   pattern with its own stream key (e.g. `'fog:' + map_ctx`, since fog
   revisions are per-map-context, not global).
4. **Add an `inventory_revision` counter** analogous to
   `visibility_revision`, stamped on inventory-affecting broadcasts, plus a
   matching `inventory_state_request` reconnect-recovery handler modeled
   directly on `handle_combat_state_request`. This is the largest of the four
   (inventory.py is the biggest handler file), so it should be its own
   dedicated PR, broken down further if needed (e.g. revision-stamping first,
   reconnect-recovery second).
5. **Only after #1-#3 are stable in production:** add client-side
   interpolation for non-local-mover token positions, per §7.

---

## Tiny patch implemented in this PR

**Chosen option: (A) add missing revision/sequence handling to one stream —
token position (`token_moved`).** (Per the task's explicit instruction, only
one option was implemented; the others above are recommended next steps, not
done here.)

### What changed

- `server/handlers/tokens.py` (`handle_token_move`): after committing the new
  `token.x`/`token.y`, calls `bump_visibility_revision(session)` (the same
  counter `tokens_sync` already stamps) and includes the resulting
  `visibility_revision` in the `token_moved` broadcast payload.
- `client/templates/play.html` (`case 'token_moved':`): added
  `if (_isStaleVisibilityPayload(p)) break;` as the first line of the case,
  reusing the existing per-stream staleness gate (default stream `'tokens'`,
  the same stream `tokens_sync` uses) so an out-of-order/delayed `token_moved`
  is dropped instead of snapping a token to a stale position. A payload
  without a `visibility_revision` field (e.g. from any code path not yet
  updated) is treated as not-stale, preserving backward compatibility.

### Why this stream, and why this option

`token_moved` is the highest-frequency, most visually-jarring message in the
system, and was the only token-related broadcast with literally zero
ordering protection. It's also the smallest possible change that closes a
real, confirmed gap: it reuses an existing counter and an existing client-side
gate function rather than inventing new infrastructure, and it touches one
handler and one switch-case. Per the task's explicit rule, token movement
*interpolation* (Option D) was not implemented, because interpolating before
the stream had a staleness gate would have hidden the symptom rather than
fixed the cause; the next tiny patch (§11.5) revisits interpolation once this
gate has had time to prove itself.

### Files changed

- `server/handlers/tokens.py`
- `client/templates/play.html`
- `tests/test_token_move_revision_guard.py` (new)

### Tests added

`tests/test_token_move_revision_guard.py`:

- `test_token_moved_broadcast_carries_increasing_revision` — two successive
  moves produce strictly increasing `visibility_revision` values, and
  `session.visibility_revision` keeps pace.
- `test_token_moved_omits_revision_only_if_counter_never_bumped` — the first
  move on a fresh session produces revision `1` (post-increment), not `0`.
- `test_play_html_token_moved_case_checks_stale_visibility_payload` —
  asserts the `token_moved` case in `play.html` actually contains the new
  guard (textual/shape assertion, matching the existing style used by
  `tests/test_combat_fog_sync_client.py`).
- `test_stale_token_moved_payload_is_dropped_by_client` — runs the real
  `token_moved` case body (extracted from `play.html`, executed under Node)
  against a sequence of payloads where the second one is out-of-order/stale;
  confirms the stale one is dropped and the token's position is unaffected.
- `test_token_moved_payload_without_revision_still_applies` — confirms
  backward compatibility: a payload without `visibility_revision` still
  applies normally.

### Tests run

```
python -m pytest tests/test_ws_heartbeat_server.py tests/test_ws_heartbeat_pong_client.py tests/test_ws_lifecycle_hardening.py tests/test_ws_single_owner_reconnect_storm.py -v --tb=short
→ 28 passed

python -m pytest tests/test_runtime_invariants_guard.py tests/test_player_boot_regression.py -v --tb=short
→ 21 passed

python -m pytest tests/test_token_move_revision_guard.py -v --tb=short
→ 5 passed (new tests for this patch)

python -m pytest tests/test_tokens_sync_payload.py tests/test_owner_identity_compat.py tests/test_session_authority_and_scene_maps.py tests/test_fog_interleave_e2e.py tests/test_connection_manager_socket_identity.py -v --tb=short
→ 28 passed

python -m pytest tests/ -k "combat or token" -q --tb=short
→ 423 passed
```

All passed; no regressions found.

### Risks remaining

- The revision is shared with `tokens_sync` by design (so the two streams
  stay comparable), which means *any* visibility-affecting change anywhere in
  the session (a fog edit, a different token's hide/reveal) will also advance
  the counter that gates `token_moved`. This is intentional and matches the
  existing `visibility_revision` contract, but it does mean the gate is
  "global monotonic clock," not "per-token sequence" — two rapid moves of
  *different* tokens are still ordered correctly relative to each other, but
  a client that's only interested in one token can't distinguish "stale for
  this token" from "stale because something else advanced the clock." In
  practice this doesn't cause incorrect behavior (the existing per-stream gate
  was designed for exactly this global-counter shape, see §1), but a future
  patch could consider a true per-token sequence if finer-grained reasoning is
  ever needed.
- `token_move_denied` (the rejection path back to the mover) still does not
  carry a revision. This is lower risk because it's only ever sent to the
  single user who just attempted the move, not broadcast, so there's no
  multi-client ordering question — but it's worth revisiting if a future
  audit finds a concrete desync there.

### Next tiny patch (recommended, not implemented here)

Per the task's instruction to recommend but not implement the next patch:
**apply `_bump_combat_revision()` consistently across the combat handlers
that currently skip it** (`handle_combat_dash`,
`handle_combat_toggle_difficult_terrain`, `handle_combat_toggle_disengage`,
`handle_combat_reset_movement`, `handle_combat_death_save`,
`handle_combat_select_target`). This is a pure consistency fix — no new
counters, no new client logic, just calling an existing function from a few
more places — and it closes the gap identified in §3/§5 where those specific
combat sub-actions mutate shared state without giving clients any revision
signal that they're now behind.
