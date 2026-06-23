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

- **Wall/door revision:** wall and door topology does not yet have a dedicated authoritative revision for LOS/fog calculations.
- **Active profile/runtime revision:** active profile selection and hydrated character runtime do not yet share a dedicated revision.
- **Spell manifest revision:** spell/action source manifests do not yet expose a shared monotonic revision.
- **Quick Actions hydration revision:** Quick Actions derivation does not yet have a server/client hydration revision or explicit readiness contract.

(Per-token revision and map-context revision were the PR 4 gaps; see section 9 below — they are now implemented.)

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
      "summary": {}
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
  and fog dimensions summarize the role-visible fog entry for the active map.

### Placeholder/future fields

- `snapshot_revision` is `0` until this envelope itself has a version bump.
- `map.map_document_revision`, `map.wall_revision`, and `map.door_revision` are
  placeholders for future map document and LOS hardening.
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
6. **PR 6 fog visibility revision hardening:** formalize fog revision handling and server/client visibility coupling.
7. **PR 7 wall/door LOS:** introduce authoritative wall/door LOS inputs after the revision contract exists.
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
