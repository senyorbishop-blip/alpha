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
- **`inventory_revision`:** monotonic inventory/item revision used by clients to ignore stale `player_inventory_sync` payloads.
- **`map_nav_version`:** monotonic map navigation version used to avoid stale world/local map navigation winning during reconnect.
- **Fog map `revision`:** per-map manual fog revision included in `fog_maps`, `fog_state`, and `fog_update` payloads.

## 4. Missing revisions

These are known gaps and should be introduced in later hardening PRs, not in this foundation PR:

- **Per-token revision:** token snapshots do not yet carry per-token monotonic revisions.
- **Wall/door revision:** wall and door topology does not yet have a dedicated authoritative revision for LOS/fog calculations.
- **Active profile/runtime revision:** active profile selection and hydrated character runtime do not yet share a dedicated revision.
- **Spell manifest revision:** spell/action source manifests do not yet expose a shared monotonic revision.
- **Quick Actions hydration revision:** Quick Actions derivation does not yet have a server/client hydration revision or explicit readiness contract.

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

## 6. Target future reconnect snapshot shape

A future reconnect snapshot should make every live gameplay stream explicit and versioned in one contract. A target shape is:

```json
{
  "type": "state_sync_v2",
  "payload": {
    "session": { "id": "...", "map_context": "world", "map_mode": "world", "map_nav_version": 0 },
    "authority": { "user_id": "...", "role": "player", "resolved_role": "player", "active_profile_id": "...", "active_profile_revision": 0 },
    "tokens": { "revision": 0, "entries": {}, "hidden_filtered": 0, "fog_hidden_filtered": 0 },
    "combat": { "active": false, "revision": 0, "state": {} },
    "inventory": { "revision": 0, "state": {} },
    "fog": { "context": "world", "revision": 0, "state": {} },
    "walls_doors": { "revision": 0, "state": {} },
    "spells": { "manifest_revision": 0 },
    "quick_actions": { "hydration_revision": 0, "status": "unknown" }
  }
}
```

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
4. **PR 4 token/map revision hardening:** add per-token/map-context revision checks.
5. **PR 5 active profile + Quick Actions hardening:** add active profile/runtime/Quick Actions hydration revisions.
6. **PR 6 fog visibility revision hardening:** formalize fog revision handling and server/client visibility coupling.
7. **PR 7 wall/door LOS:** introduce authoritative wall/door LOS inputs after the revision contract exists.
8. **PR 8 hidden NPC enforcement tests:** expand tests proving hidden/fog-hidden NPC details never leak.
9. **PR 9 e2e/manual QA coverage:** add browser/manual automation coverage for reconnect and multiplayer drift.
