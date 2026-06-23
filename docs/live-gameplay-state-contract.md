# Live Gameplay State Contract and Reconnect Diagnostics

This document describes the current live gameplay state contract for reconnect/state-sync hardening and the target contract for follow-up PRs. PR 1 adds visibility into the current behavior without changing gameplay authority, fog LOS, combat rules, token visibility rules, or spell rules.

## 1. Server is authoritative for

- **Session membership:** the server owns the session user list and whether a connecting `user_id` belongs to the session.
- **Role/authority:** the server resolves the effective `dm`, `player`, `viewer`, or assistant role from session membership and uses it when building snapshots.
- **Tokens:** the server owns authoritative token records, token positions, token hidden flags, token ownership, and token map context.
- **Hidden token filtering:** non-DM snapshots must not include hidden token payloads.
- **Combat:** the server owns combat active/inactive state, combatants, turn, round, selected target, pending attack, suspended combatants, and `combat.revision`.
- **Inventory:** the server owns player inventory, party loot/stash state, item actions derived from inventory, encumbrance payloads, and `inventory_revision`.
- **Active profile:** the server stores the active character profile id per user in `active_char_profiles`.
- **Manual fog state:** the server owns manual fog maps, enabled state, grid dimensions, fog cells, map context, and fog map `revision`.

## 2. Client is currently responsible for

- **Rendering:** the client renders maps, tokens, overlays, panels, chat/log UI, combat surfaces, and right-side tabs from server snapshots.
- **Quick Actions derivation:** the movable Quick Actions bar derives available actions from hydrated character sheet/runtime data on the client.
- **Spell modal UI:** spell action presentation, modal controls, and slot UI hydration are client-side presentation responsibilities.
- **Fog rendering:** the client renders fog overlays and applies full `fog_state` and sparse `fog_update` messages to local render buffers.
- **Some character runtime hydration:** the client hydrates parts of active character sheet/runtime state for UI, Quick Actions, and local presentation.

## 3. Existing revisions

- **`combat.revision`:** monotonic combat payload revision used by clients to detect stale combat state.
- **`visibility_revision`:** monotonic visibility/token/fog-related revision used by token and combat streams to guard against stale visibility snapshots.
- **`token_state_revision`:** monotonic session-wide token mutation revision (PR 4). Bumped on every authoritative token mutation — create, move, delete, hide/unhide, hp/ac/status update, ownership/profile-link change, staged/map-context change — and stamped onto `token.revision` for the specific token that changed. Tracked separately from `visibility_revision` so a non-visibility token edit (e.g. HP) does not also have to inflate the visibility counter; both are included on every token payload so clients can use whichever guard fits the event.
- **`inventory_revision`:** monotonic inventory/item revision used by clients to ignore stale `player_inventory_sync` payloads.
- **`map_nav_version`:** monotonic map navigation version used to avoid stale world/local map navigation winning during reconnect. Also exposed as `map_context_revision` (PR 4) — the same counter, aliased for clarity in map-context-focused payloads rather than introducing a second independent counter.
- **Fog map `revision`:** per-map manual fog revision included in `fog_maps`, `fog_state`, and `fog_update` payloads.

## 4. Missing revisions

These are known gaps and should be introduced in later hardening PRs, not in this foundation PR:

- **Active profile/runtime revision:** active profile selection and hydrated character runtime do not yet share a dedicated revision.
- **Spell manifest revision:** spell/action source manifests do not yet expose a shared monotonic revision.
- **Quick Actions hydration revision:** Quick Actions derivation does not yet have a server/client hydration revision or explicit readiness contract.

(Per-token revision and map-context revision were the PR 4 gaps; see section 9 below — they are now implemented. Wall/door revision was the PR 7 gap; see section 11 below — it is now implemented.)

## 5. Reconnect flow today

1. The browser opens or reopens the WebSocket for a session/user.
2. The server validates optional JWT identity and session membership.
3. If the session is not in memory, the server attempts DB restore before accepting the socket.
4. The server resolves the user role from session membership.
5. The server sends an initial `state_sync` built by `Session.to_state_dict_for_role(role, user_id)`.
6. The client boot/runtime bridge also sends `request_state` once per real socket open as reconnect recovery.
7. The server responds to `request_state` with another role-filtered `state_sync`.
8. For DM/player clients, the client may request `combat_state` after open when combat state is active or unknown.
9. Token, combat, fog, inventory, active profile, and Quick Actions surfaces apply or ignore payloads based on existing revision gates and local hydration state.

## 6. Reconnect Snapshot v2

PR 2 introduces a server-built reconnect snapshot message named
`authoritative_snapshot`. It is sent after the legacy `state_sync` on WebSocket
connect and after `request_state`, so current clients keep booting through the
old path while the new contract can be logged, inspected, and hardened.

The snapshot is generated by
`Session.to_authoritative_snapshot_for_role(role, user_id, source)` and starts
from the existing `Session.to_state_dict_for_role(...)` payload. That means the
new envelope inherits current role filtering instead of creating a second token
or combat visibility implementation.

Current shape:

```json
{
  "type": "authoritative_snapshot",
  "payload": {
    "snapshot_revision": 0,
    "session": {
      "id": "...",
      "resolved_role": "dm|player|viewer|assistant_dm",
      "user_id": "...",
      "authority": {
        "role": "dm|player|viewer",
        "is_dm": false,
        "is_player": true,
        "is_viewer": false,
        "matched_via": "server_session_user",
        "can_control_tokens": true,
        "can_see_hidden": false
      }
    },
    "map": {
      "context": "world",
      "mode": "world",
      "current_map_id": "",
      "current_map_url": "",
      "map_nav_version": 0,
      "map_context_revision": 0,
      "dm_nav_intent": 0,
      "token_state_revision": 0,
      "visibility_revision": 0,
      "map_document_revision": 0,
      "wall_revision": 0,
      "door_revision": 0
    },
    "tokens": {
      "revision": 0,
      "token_state_revision": 0,
      "visibility_revision": 0,
      "items": {},
      "count": 0,
      "filter_summary": {
        "hidden_filtered": 0,
        "fog_hidden_filtered": 0
      }
    },
    "combat": { "active": false, "revision": 0, "state": {} },
    "character": {
      "active_profile_id": "",
      "runtime_revision": 0,
      "hydration_status": "unknown|ok|missing|error",
      "summary": {}
    },
    "spells": {
      "manifest_revision": 0,
      "hydration_status": "unknown|ok|missing|error",
      "summary": {}
    },
    "inventory": {
      "revision": 0,
      "hydration_status": "unknown|ok|missing|error",
      "summary": {}
    },
    "fog": {
      "map_context": "world",
      "revision": 0,
      "visibility_revision": 0,
      "enabled": false,
      "source": "reconnect|authoritative_snapshot",
      "summary": { "cols": 0, "rows": 0 },
      "explored": { "revealed_cells": 0, "total_cells": 0 },
      "currently_visible": null,
      "unseen": null,
      "visibility_source": "manual_fog",
      "wall_revision": 0,
      "door_revision": 0
    },
    "debug": {
      "created_at": "2026-06-23T00:00:00Z",
      "source": "ws_connect|request_state|manual",
      "legacy_state_sync_also_sent": true
    }
  }
}
```

### Currently authoritative in `authoritative_snapshot`

- `session.id`, `session.resolved_role`, `session.user_id`, and
  `session.authority` are server resolved from session membership.
- `map.context`, `map.mode`, `map.current_map_url`, `map.map_nav_version`, and
  `map.dm_nav_intent` mirror the current server map navigation state.
- `tokens.items`, `tokens.count`, and `tokens.visibility_revision` are the
  existing role-filtered token reconnect payload.
- `tokens.filter_summary` exposes counts only for hidden/fog-filtered tokens.
  It does not include hidden token names, ids, notes, stats, or payload data.
- `combat.active`, `combat.revision`, and `combat.state` use the existing
  filtered combat payload rules inherited from `state_sync`.
- `character.active_profile_id` is the server active profile id for the
  reconnecting user when available.
- `inventory.revision` is the existing session `inventory_revision`.
- `fog.map_context`, `fog.revision`, `fog.visibility_revision`, `fog.enabled`,
  `fog.source`, and fog dimensions summarize the role-visible fog entry for
  the active map (never a different map's fog — see PR 6, section 10).
- `map.wall_revision`, `map.door_revision`, `map.doors` (role-safe door
  summary), and `fog.currently_visible.cell_count` /
  `fog.visibility_source` are now live — see PR 7, section 11.

### Placeholder/future fields

- `snapshot_revision` is `0` until this envelope itself has a version bump.
- `map.map_document_revision` is a placeholder for future map document
  hardening.
- `character.runtime_revision`, `spells.manifest_revision`, and detailed
  hydration summaries are placeholders until character/spell/Quick Actions
  hydration gets a shared revision contract.

### What legacy `state_sync` still handles

The client still applies the legacy `state_sync` path as the runtime source of
truth for gameplay state application. `authoritative_snapshot` is currently
received, shape-checked, stored at `window.__lastAuthoritativeSnapshot`, and
logged through `liveDebugLog` when `window.__LIVE_DEBUG__` is enabled. It does
not yet replace the old token, fog, combat, inventory, character, or map apply
paths.

### Migration plan

1. Keep sending legacy `state_sync` and `authoritative_snapshot` together.
2. Expand tests around DM/player/viewer snapshot safety and revision coverage.
3. Move one stream at a time to read from `authoritative_snapshot` after its
   revision semantics are hardened.
4. Only remove or reduce legacy `state_sync` once every live client stream has
   an equivalent v2 apply path and backward-compatibility coverage.

### Security rule

Hidden token/NPC payloads must never be included in non-DM
`authoritative_snapshot` payloads. Player/viewer snapshots may include only
filter counts (`hidden_filtered`, `fog_hidden_filtered`) for omitted private
tokens, never the omitted token ids, names, notes, stat blocks, positions, or
other payload details.

## 7. Known drift risks

- A stale token snapshot can race with combat or fog updates unless revisions are consistently compared per stream.
- Hidden/fog-hidden NPC filtering can be difficult to debug because correct payloads intentionally omit private token details.
- Map context drift can stage tokens on the wrong client view after reconnect if world/local navigation and token sync race.
- Combat can appear inactive or stale on the client if combat state is not re-requested after reconnect.
- Active profile state can be known on the server while Quick Actions is still waiting on client-side character runtime hydration.
- Fog rendering can have a newer or older client buffer than the latest server fog map revision if a client misses a sparse update.

## 8. Recommended PR order

1. **PR 1 debug/contract:** add safe structured diagnostics and this state contract document.
2. **PR 2 reconnect snapshot v2:** introduce an explicit reconnect snapshot shape with complete stream summaries.
3. **PR 3 combat revision hardening:** tighten combat revision application/ignore rules and tests.
4. **PR 4 token/map revision hardening (done):** added per-token/map-context revision checks — see section 9.
5. **PR 5 active profile + Quick Actions hardening:** add active profile/runtime/Quick Actions hydration revisions.
6. **PR 6 fog visibility revision hardening (done):** formalized fog revision handling and server/client visibility coupling — see section 10.
7. **PR 7 wall/door vision blocking hardening (done):** server-authoritative wall/door LOS engine, `wall_revision`/`door_revision`, secret-door filtering, LOS fog reveal, and token/combat visibility gating — see section 11.
8. **PR 8 hidden NPC enforcement tests:** expand tests proving hidden/fog-hidden NPC details never leak.
9. **PR 9 e2e/manual QA coverage:** add browser/manual automation coverage for reconnect and multiplayer drift.

## 9. PR 4 — Token and map revision hardening

### Token revision model

- `Session.token_state_revision` (int) is a session-wide monotonic counter,
  separate from `visibility_revision`. It is bumped exactly once per
  authoritative token mutation via `bump_token_state_revision(session)` /
  `_stamp_token_revision(session, token)` in `server/handlers/common.py`.
- `_stamp_token_revision` also stamps the new revision onto `token.revision`
  (added to the `Token` dataclass and `Token.to_dict()` in `server/session.py`),
  so every token payload that includes the full token dict carries a per-token
  revision in addition to the session-wide counter.
- Every token mutation path bumps it: `_broadcast_token_event` (covers
  `token_moved`, `token_created`, `token_hp_updated`, `token_updated`,
  `token_condition_changed`) and `_broadcast_token_visibility` (covers
  `token_hidden_changed` / `token_removed_hidden`) both call
  `_stamp_token_revision` centrally. `handle_token_delete`,
  `handle_token_placed`, and `handle_token_send_to_staging` in
  `server/handlers/tokens.py` call it directly because they broadcast through
  `manager.broadcast(...)` instead of the shared helpers.
- `token_state_revision` (plus `visibility_revision`, `token_id`, and
  `map_context`) is included on: `tokens_sync`, `token_moved`, `token_created`,
  `token_updated`, `token_hp_updated`, `token_hidden_changed`,
  `token_removed_hidden`, `token_placed`, `token_sent_to_staging`,
  `token_deleted`, the `state_sync` top level, and the `authoritative_snapshot`
  `tokens` block.
- Strict server-side hidden/fog/map-context filtering in
  `_is_token_visible_to_user` / `_visible_tokens_payload_for_user` is
  unchanged by this PR — token revision tracking is additive, not a new
  filtering mechanism.

### Map revision model

- `map_nav_version` remains the single authoritative map navigation counter.
  `map_context_revision` is the same value, exposed as an alias in the
  `authoritative_snapshot` `map` block and in `local_map_nav` payloads, rather
  than introducing a second independent counter that would need to be kept in
  sync with the first.
- `session.to_state_dict()` and `to_authoritative_snapshot_for_role(...)` both
  now include `map_mode` (`"world"` or `"local"`), `token_state_revision`, and
  `visibility_revision` alongside the existing `map_nav_version` /
  `dm_nav_intent` fields.
- `handle_local_map_nav` (`server/handlers/map_editor.py`) now also calls
  `_broadcast_token_state_sync(session)` after applying a map-context change,
  so non-DM clients' visible token set is proactively refreshed when the DM
  changes map context, instead of waiting for an unrelated later token event
  to trigger a resync.

### Client apply/ignore rules

- `applyAuthoritativeTokenSnapshot(payload, source)` (client/templates/play.html)
  is the single entry point for full token snapshots (`tokens_sync`, the
  `state_sync` token block, the `authoritative_snapshot` `tokens.items` block,
  and local map enter/exit token payloads if present). It drops the snapshot
  if `token_state_revision` is older than the last one applied, otherwise
  delegates to the existing `applyAuthoritativeTokenSync` projection logic and
  rebuilds the hidden-token suppression set from the snapshot's contents.
- `applyAuthoritativeTokenEvent(eventType, payload, applyFn, source)` is the
  single entry point for single-token events (`token_moved`, `token_created`,
  `token_placed`, `token_updated`, `token_hp_updated`, `token_hidden_changed`,
  `token_sent_to_staging`, `token_removed_hidden`, `token_deleted`). It checks
  the hidden-suppression guard and the `token_state_revision` stale-guard
  before invoking the event's existing apply logic via `applyFn`.
- `applyAuthoritativeMapContext(payload, source)` is the single entry point for
  map-context-bearing messages (`local_map_enter`, `local_map_exit`,
  `state_sync`, `authoritative_snapshot`). It reuses the existing
  `_shouldIgnoreStaleNav` / `_acceptNavVersion` gate keyed on `nav_version`, so
  a stale/delayed local-map payload cannot overwrite a newer world-map payload
  (or vice versa) just because it arrived later on the wire.
- `token_moved` additionally keeps the pre-existing `visibility_revision`
  stream guard (`_isStaleVisibilityPayload`) for its very high message
  frequency, in addition to the new `token_state_revision` guard.

### Hidden token stale-event protection

- `_suppressedHiddenTokenIds` (client) tracks ids the client currently
  believes are hidden/removed. It is populated whenever a token snapshot
  includes a hidden token, or a `token_hidden_changed` / `token_removed_hidden`
  event removes one, and cleared when a `token_hidden_changed` event reports
  `hidden: false`, a `token_created`/`token_placed` event reintroduces the id,
  or a newer full snapshot is applied (which rebuilds the set from scratch).
- `applyAuthoritativeTokenEvent` checks this set before applying any event
  type other than `token_hidden_changed`/`token_removed_hidden` themselves, so
  a stale, out-of-order `token_moved` (or any other single-token event) that
  was in flight when the token went hidden cannot resurrect it client-side —
  even if that stale event's own `token_state_revision` check is inconclusive
  (e.g. an older client message shape with no revision at all).

### Current limitations

- Staged-token filtering (excluding off-map/staged tokens from non-DM
  `tokens` payloads) is unchanged in this PR. The existing client-side
  staging tray (`_stagingTokens`) depends on staged/cross-map-context tokens
  still being delivered to their owning player, and changing that
  server-side filtering risks breaking the staging UX. This is a deliberate
  scope decision, not an oversight.
- `local_map_enter` / `local_map_exit` payloads do not embed a full token
  block today; the token resync for a map-context change is delivered via
  the separate `tokens_sync` message the server now sends right after the
  nav broadcast (see "Map revision model" above). `applyAuthoritativeTokenSnapshot`
  on the nav payload itself is wired in defensively for forward compatibility,
  but is a no-op until/unless `tokens`/`token_state_revision` fields are added
  to those payloads directly.
- This PR does not implement fog/wall/door LOS revision coupling (future PR
  per section 8, item 6/7) — manual fog behavior and revisions are
  unchanged.

## 10. PR 6 — Fog visibility revision hardening

This PR formalizes the manual fog revision/source contract and consolidates
client fog application behind one entry point. It does **not** add wall/door
LOS, does not rebuild the map renderer, and does not change manual fog tools
(paint/reveal/hide/toggle) themselves — those are unchanged and remain
DM-only.

### Fog revision model

- Each map context's fog entry in `session.fog_maps[ctx]` keeps its own
  monotonic `revision`, bumped by exactly 1 on every toggle (`handle_fog_toggle`)
  or paint (`handle_fog_paint`) for that context only. Other contexts'
  revisions/cells are untouched (see "World/local separation" below).
- Every fog payload (`fog_state`, `fog_update`, the `local_map_enter` /
  `local_map_exit` fog snapshot, and the `authoritative_snapshot` fog block)
  now also carries `visibility_revision` (the session-wide counter) and
  `map_mode` (`"world"` or `"local"`) alongside the per-context `revision`, so
  a client can tell at a glance whether a fog change is expected to also
  affect token/combat visibility.
- A new `source` field is stamped on every fog payload, using the enum
  `state_sync | authoritative_snapshot | fog_state | fog_update |
  local_map_enter | local_map_exit | reconnect`. The reconnect snapshot
  (`source="ws_connect"` passed into `to_authoritative_snapshot_for_role`)
  reports `fog.source = "reconnect"`; any other snapshot source (e.g.
  `request_state`, `"manual"`) reports `"authoritative_snapshot"`.
- `session.visibility_revision` is bumped whenever a fog change can affect
  token/combat visibility. This was already wired before this PR:
  `handle_fog_toggle`/`handle_fog_paint` call `_broadcast_token_state_sync`,
  which calls `bump_visibility_revision(session)` internally — this PR makes
  the before/after value visible in `[live_state]` debug logs and exposes the
  current value on every fog payload.

### Snapshot fog block (`authoritative_snapshot.payload.fog`)

In addition to the pre-existing `map_context`, `revision`,
`visibility_revision`, `enabled`, and `summary.{cols,rows}` fields, the fog
block now reports:

- `source` — `"reconnect"` or `"authoritative_snapshot"` (see above).
- `explored.revealed_cells` / `explored.total_cells` — a manual-fog reveal
  count/summary, safe to send to any role (counts only, never raw cell data).
- `currently_visible.cell_count` — count of fog cells currently inside LOS of
  a player vision source (PR 7, section 11); `unseen` remains an explicit
  `null` placeholder (no client use case yet).
- `visibility_source: "manual_fog_plus_wall_door_los"` — names the visibility
  model that produced this block, now that wall/door LOS gating exists
  alongside manual fog paint (PR 7).
- `wall_revision` / `door_revision` — live session counters (PR 7, section 11).

The fog block is always resolved from the snapshot's own map context (the
viewing user's current world/local context), so it can never report a
different map's fog as "current" — this was already true before this PR
(`fog_entry = fog_maps.get(map_ctx) or fog_maps.get("world")`) and is covered
by `test_authoritative_snapshot_fog_block_matches_current_map_context_not_other_map`.

Note: the snapshot's fog block carries no cell data (`fog_cells`) — it is a
compact summary only. Full fog cell data still arrives via the legacy
`state_sync` (`fog_maps`) sent immediately before the snapshot on connect, or
via `fog_state`/`fog_update`/`local_map_enter`/`local_map_exit` afterward.
`debug.legacy_state_sync_also_sent: true` on the snapshot signals this.

### World/local fog separation

`session.fog_maps` is, and remains, a dict keyed by normalized map context —
each context's `enabled`/`cols`/`rows`/`cells`/`revision` lives independently.
This PR adds a regression test
(`test_fog_toggle_bumps_only_target_context_revision`) proving that toggling
the local map's fog does not touch the world map's revision or cells, and
vice versa. Non-DM `to_state_dict_for_role` snapshots already filter
`fog_maps` down to `visible_map_contexts_for_user(user_id)`, so a player never
receives another subgroup's local fog at all.

### Client: single fog apply path

`window.AppFog.applyAuthoritativeFogState(state, env, payload, source)`
(`client/static/js/render/fog.js`) is now the one entry point for every fog
payload shape:

- Full state (`fog_maps` dict, or a single-context `fog_cells` string) is
  delegated to the existing `fogApplyState`.
- Sparse updates (`cells` array + `reveal`) are delegated to the existing
  `fogApplyUpdate`.
- Compact summary-only payloads (the `authoritative_snapshot` fog block, which
  has no cell data) only advance per-context revision/visibility_revision
  bookkeeping in `state.fogRevisionByContext[ctx]` — they never touch
  `fogMaps`/render state.

All payloads route through a per-context revision guard before being applied:
a fog or snapshot payload whose `revision` is lower than the last one recorded
for that map context is logged and ignored (`fog ignored stale ... revision`);
same-revision payloads are idempotent; missing/zero revision is treated as a
legacy payload and applied without the stale check (with a debug warning).
This guard is keyed per map context, so a stale local-map fog payload cannot
roll back a newer world-map fog state, and vice versa.

`client/templates/play.html` exposes a thin global wrapper,
`applyAuthoritativeFogState(p, source)`, used by every call site: the
`state_sync`, `fog_state`, `fog_update`, `local_map_enter`, and
`local_map_exit` message handlers, and (new in this PR)
`handleAuthoritativeSnapshot()`, which previously parsed the snapshot's fog
block only for a debug log and never applied it.

Debug logs (gated by `window.__LIVE_DEBUG__`/`liveDebugLog`) for every fog
apply/ignore decision include: `source`, incoming/local fog `revision`,
incoming/local `visibility_revision`, `map_ctx`, and whether the payload was
applied or ignored and why (`stale_snapshot_revision`, `bookkeeping_only`,
`sparse_update`, `full_state`, or `legacy_fallback`).

### Hidden/fog-hidden token safety

Unchanged by this PR, and covered by existing tests
(`test_hidden_npc_excluded_from_player_reconnect_snapshot`,
`test_npc_touching_unrevealed_fog_excluded_from_player_reconnect_snapshot`,
PR 4's `_suppressedHiddenTokenIds` stale-event guard): hidden/fog-hidden NPCs
are excluded from non-DM snapshots and stay excluded across stale token
events. This PR adds
`test_fog_toggle_hiding_npc_bumps_visibility_revision`, proving a fog paint
that hides a previously-visible NPC bumps `session.visibility_revision` so
the token/combat resync this triggers (`_broadcast_token_state_sync` +
`run_combat_fog_sync`, both already called from `handle_fog_toggle`/
`handle_fog_paint`) is provably wired end-to-end, not just structurally
present.

### Tests added

- `tests/test_fog_visibility_revision_hardening.py` — fog payload `source`/
  `visibility_revision`/`map_mode` fields, world/local revision isolation,
  snapshot fog-block map-context correctness, snapshot `source` derivation,
  LOS placeholder shape, and the visibility_revision-bump-on-hide check.
- Updated `tests/test_fog_sync.py`, `tests/test_fog_ui_sticky.py`, and
  `tests/test_ws_reconnect_regression.py` literal-string regression checks to
  match the new `applyAuthoritativeFogState(...)` call sites (the underlying
  behavior they guard — stale-entry promotion, map-context-keyed apply,
  fog-before-combat ordering — is unchanged; only the function name calling
  into it changed).

### Remaining risks / out of scope

- Wall/door LOS and `currently_visible` computation landed in PR 7 (see
  section 11); this section's history is kept as-is for context.
- The client revision guard is bookkeeping-only for snapshot-sourced payloads;
  it cannot detect a stale snapshot whose `revision` matches the local one but
  whose `enabled` flag disagrees (extremely unlikely in practice, since both
  values are bumped together server-side, but worth knowing if a future PR adds a
  second visibility source that could disagree with manual fog independently).

## 11. PR 7 — Wall and door vision blocking hardening

### Server LOS engine (`server/visibility.py`)

A new module, not a rewrite of any renderer, is the single source of truth
for "what can a token see" once walls/doors are involved:

- `vision_blockers(session, map_ctx)` reuses `server/map_logic.py`'s existing
  `collect_map_blockers()` (already merges walls + door props into one
  `Blocker` list with movement-blocking already resolved), filtered to
  `.blocks_vision`. Movement-blocking logic is untouched and not duplicated.
- `has_los(x1, y1, x2, y2, blockers)` is a straight segment-intersection test
  against every vision-blocking segment — the same algorithm
  `client/static/js/render/vision.js` already uses for its preview, so
  DM/player preview and server truth agree whenever nothing is stale.
- A closed door (secret or not) blocks LOS exactly like a wall; an open door
  is transparent. This falls out of `door_blocker()` already returning `None`
  for open doors — no new branch was needed.
- `player_vision_sources(session, map_ctx)` collects player-owned,
  non-hidden, non-staged tokens with a positive usable vision radius (same
  `max(vision_radius, bright_radius, darkvision_radius if has_darkvision)`
  formula the client vision preview already uses) as `{x, y, radius_px,
  token_id}`.
- `token_blocked_by_los(session, token, map_context=None)` **fails open**: it
  returns `False` ("not blocked") whenever there is no vision-blocking
  geometry on the map or no player vision source positioned on it, so any
  campaign/map without walls/doors or without vision-enabled tokens behaves
  exactly as it did before this PR.
- `compute_visible_cell_indices(session, map_ctx, cols, rows)` /
  `apply_los_fog_reveal(session, map_ctx)` drive fog reveal (below).

### Wall blocking

Unchanged data model — `session.editor_walls[ctx]` segments, already
normalized by `normalize_wall()`. Saving/clearing walls now also bumps
`wall_revision` and `visibility_revision`, triggers a token resync, an LOS
fog reveal pass, and a combat visibility resync (`handle_editor_walls_save`/
`handle_editor_walls_clear` in `server/handlers/map_editor.py`).

### Door blocking

Door props (`kind == "door"`) already carried `state`/`locked`/
`blocks_vision`; `door_blocker()` already excluded open doors from the
blocker list. `handle_door_toggle` and `handle_door_lock_set` now bump
`door_revision` + `visibility_revision` and trigger the same
resync/fog-reveal/combat-resync chain as wall edits. `handle_editor_props_save`
/`handle_editor_props_clear` bump the same revisions whenever the affected
map context has (or had) any door prop.

### Secret/hidden doors

Two new door fields, `secret` and `revealed` (DM-only, persisted alongside
the existing door prop fields), gate door *metadata* visibility:

- `server/session.py::filter_editor_props_for_role()` — the existing single
  choke point for prop payload filtering (already used per-user by
  `_broadcast_editor_props_state`) — drops a door entirely from non-DM
  payloads while `secret` is true and `revealed` is false, and always strips
  the `secret`/`revealed` fields themselves from non-DM payloads (even once
  revealed, players see geometry/state, never the secret/revealed bookkeeping).
- `server/handlers/map_editor.py::filter_door_summary_for_role()` is the
  equivalent choke point for the new `map.doors` snapshot summary.
- The LOS engine itself always reads raw, unfiltered `session.editor_props`,
  so an undiscovered secret door still functionally blocks sight server-side
  — players are never told it exists, but it behaves like a wall to them.

### Revision model

- `Session.wall_revision` / `Session.door_revision` (new `int` fields,
  default `0`) — monotonic counters bumped by
  `server/handlers/common.py::bump_wall_revision()` /
  `bump_door_revision()` on every wall/door create/update/toggle/lock/delete.
- `Session.visibility_revision` (pre-existing, from PR 6) is also bumped on
  every wall/door mutation, since wall/door state can change what's visible.
- Every wall/door mutation handler now also calls `_broadcast_token_state_sync`
  and `run_combat_fog_sync` so a wall/door change resyncs which tokens and
  combatants are visible in the same turn it lands, not just on the next
  unrelated update.

### Snapshot v2 additions (`authoritative_snapshot`)

- `map.wall_revision`, `map.door_revision` — live counters (previously `0`
  placeholders from PR 6).
- `map.doors` — role-safe door summary (`id`, `x`, `y`, `facing`, `state`,
  `locked`, `blocks_vision`, plus `secret`/`revealed` for DM only) via
  `filter_door_summary_for_role()`.
- `fog.currently_visible.cell_count` — count of fog cells currently inside
  LOS of a player vision source, via `compute_visible_cell_indices()`.
- `fog.visibility_source` — `"manual_fog_plus_wall_door_los"`, replacing the
  PR 6 placeholder string `"manual_fog"`.

### Fog reveal via LOS

`apply_los_fog_reveal(session, map_ctx)` is purely additive on top of the
existing manual-paint fog bitstring (`fog_maps[ctx]["cells"]`): it only ever
flips a cell from `"0"` to `"1"` inside LOS of a player vision source, never
the reverse, so it never competes with or overwrites the DM's manual fog
tools. `server/handlers/map_editor.py::_apply_los_fog_reveal_and_broadcast()`
wraps this with the existing fog revision bump + `fog_state` broadcast path
(`_broadcast_fog_to_visible_users`), and is called from:

- `handle_token_move` (`server/handlers/tokens.py`) — a moving player vision
  source can newly reveal cells.
- Every wall/door mutation handler — walls/doors changing can also change
  what's in LOS of an already-stationary vision source.

### Token and combat visibility through LOS

- `server/handlers/common.py::_can_user_see_token()` now also excludes an
  NPC/monster token blocked by LOS from a non-DM viewer's token payload
  (alongside the pre-existing `hidden`/fog-hidden checks).
- `server/handlers/common.py::_combat_state_payload_for_user()` applies the
  same LOS check when filtering the per-user combat payload.
- `server/handlers/combat.py::is_token_visible_to_party()` and
  `_suspend_reasons()` both gain a `"los"` reason, parallel to the existing
  `"fog"`/`"hidden"`/`"staged"` reasons. `sync_combat_visibility()`'s
  suspend/restore loop now also suspends/restores on `"los"` (previously
  only `{"fog", "hidden", "staged"}` were filtered into the active suspend
  set). LOS-suspended combatants land in the generic `suspended_combatants`
  list (no dedicated `los_suspended_combatants` bucket was added — not
  required by the spec, and `fog_suspended_combatants`/
  `hidden_suspended_combatants` remain the only dedicated buckets).

### Client tracking

- `client/templates/play.html`: `editor_walls_sync` / `editor_props_sync`
  handlers now track `window._wallRevision` / `window._doorRevision` /
  `window._visibilityRevision` (monotonic, never regresses) and log via
  `liveDebugLog`/`window.__LIVE_DEBUG__`. `buildClientLiveStateSummary()`
  gained `wall_revision`/`door_revision` fields so every debug log that uses
  it reports them consistently. `handleAuthoritativeSnapshot()` also seeds
  `window._wallRevision`/`window._doorRevision` from `map.wall_revision`/
  `map.door_revision` on reconnect.
- Door/wall state changes don't need an explicit "force redraw" call: the
  existing `requestAnimationFrame` render loop reads `_editorWallsAll`/
  `_editorPropsAll` every frame, so updating that data is sufficient for the
  map/vision-preview canvas to reflect the new state on the next frame.
- Fog cell data and its revision/visibility_revision guard were already
  fully centralized in `window.AppFog.applyAuthoritativeFogState` (PR 6); PR 7
  reuses that path unchanged for LOS-driven fog reveal broadcasts — no
  competing fog apply path was introduced.

### Tests added

`tests/test_wall_door_vision_blocking.py` — wall LOS blocking/non-blocking,
closed/open door LOS, secret-door LOS blocking + payload exclusion (and
exclusion of the `secret`/`revealed` metadata itself even once revealed),
fails-open behavior with no blockers/sources, player-vision-source
hidden/staged exclusion, LOS fog reveal additive/non-regressing/wall-blocked
behavior, fog-disabled no-op, combat suspend/restore on wall LOS, and
wall/door mutation handlers bumping `wall_revision`/`door_revision`/
`visibility_revision` and producing the correct snapshot v2 fields (including
secret-door exclusion from a player-role snapshot).

`tests/test_fog_visibility_revision_hardening.py`'s PR 6 placeholder test
(`test_authoritative_snapshot_fog_block_has_los_placeholders`) was updated/
renamed (`test_authoritative_snapshot_fog_block_has_wall_door_los_fields`) to
assert the now-implemented `currently_visible`/`visibility_source` values
instead of the old `null`/`"manual_fog"` placeholders.

### Remaining risks / out of scope

- `compute_visible_cell_indices()` is a per-source bounding-box + per-cell LOS
  raycast — correct but O(sources × cells-in-radius), not spatially indexed.
  Acceptable for v1 per the task's explicit "correctness over perfect
  performance" guidance; worth revisiting if maps grow very large or fog
  grids get much finer-grained.
- LOS-suspended combatants share the generic `suspended_combatants` bucket
  with no dedicated UI list (see "Token and combat visibility" above) — if a
  future UI wants to visually distinguish "suspended by wall" from
  "suspended by fog", it will need a new bucket, not just a new reason string.
- Manual QA (DM/player two-client wall/door placement, secret door
  reveal/discovery, fog reveal-through-LOS, hidden NPC behind closed door,
  combat suspend/restore) has not been run in this sandboxed environment —
  the server-side test suite above is the verification path actually
  exercised here.
