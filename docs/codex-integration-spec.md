# The Codex — Integration & Communication Spec

How the unified Codex (Quests · Session Log · Notes · Lore) wires into the
**existing** Tavern Tabletop runtime. The guiding rule: **reuse the engines you
already have** (quest progression, rewards, per-role broadcast, persistence) and
add one unifying surface + a real link graph on top. Nothing here forks an
existing authority — which is the AGENTS.md anti-pattern.

---

## 0. What already exists (so we build on it, not beside it)

| Concern | Today | Symbol |
|---|---|---|
| Journals | session-level list, DM-authored, `shared` flag | `journal_entries`, `handle_journal_upsert`, `_broadcast_journal_state` → `journal_sync` |
| Notes | a single session string + scattered POI/token/char notes | `session.notes`, `_normalize_character_notes` |
| Quests | full engine: objectives, progression, rewards, board | `session_quests`, `apply_objective_event`, `resolve_session_quest_progression`, `_broadcast_session_quests` → `session_quests_sync`, `quest_premium_progression` |
| Quest links | **already present** | `linked_handout_ids`, `linked_map_ids`, `linked_poi_ids`, `linked_npc_ids`, `board_ids`, `quest_board_bindings` |
| Handouts | targeted delivery w/ recipients & subgroups | `handout_*`, `_handout_targets_user` |
| POIs / map | first-class entities | `poi_create/update/delete`, `map_context` |
| Live → quest | combat already advances objectives | `clear_encounter` → `handle_session_quest_objective_event` |
| Rewards | gold/xp/items/reputation/flags | `_normalize_reward_bundle`, `quest_premium_progression` |
| Initial load | role-filtered snapshot | `handle_request_state` → `to_authoritative_snapshot_for_role` |
| Persistence | campaign blob + schema/restore | `save_campaign_async`, `persistence_schema`, `restore` |

**Takeaway:** quests are mature; journals/notes are thin; the link graph is
half-built (quest→entity, but not entity→quest, and journals/notes don't link).
The Codex unifies storage + UI + visibility + linking, and **projects quests in
read-only** rather than reimplementing them.

---

## 1. Data model

One entry store + one link table. Quests keep their engine and are *projected*
into the Codex; journals and notes migrate fully.

```
codex_entries
  id            text pk
  type          'quest' | 'log' | 'note' | 'lore' | 'handout'
  title         text
  body_md       text                      # markdown (reuse journal content_md cap 12000)
  author_id     text                      # who wrote it  (NEW: enables player entries)
  author_role   'dm'|'player'|'viewer'
  visibility    'private'|'party'|'dm'     # see §3
  subgroup_id   text|null                  # party-tier scoping for split party
  tags          json[]
  pinned        bool
  source_ref    json|null                  # for projections: {kind:'session_quest', id:'q1'}
  created_at, updated_at  real

codex_links                                # the bidirectional graph
  entry_id      text fk codex_entries
  target_kind   'npc'|'token'|'poi'|'map'|'item'|'handout'|'encounter'|'entry'
  target_id     text                       # token id / poi_id / item id / entry id …
  label         text                       # cached display name
  (index on target_kind,target_id  -> backlinks are a single query)
```

**Migration (one-time, in `restore`/a schema bump):**
- `journal_entries[]` → `codex_entries` with `type='log'` (or `'note'` when
  `category` says so); `shared==true` → `visibility='party'`, else `'dm'`;
  `author_role='dm'`. Carry `poi_id` → a `codex_links` row.
- `session.notes` (the blob) → one `codex_entries` row `type='note'
  visibility='dm' author_role='dm'`. Then retire the blob.
- `session_quests[]` stay as-is in the engine; a **projection** builds a
  read-only `type='quest'` Codex view per render (source_ref points back). The
  quest's existing `linked_*_ids` become `codex_links` rows so quests light up in
  the graph immediately.

Keep `item_schema_version`-style versioning: add `codex_schema_version: 1`.

---

## 2. Message protocol (mirror the patterns you already use)

Add a small, consistent set — modeled exactly on `journal_sync` /
`session_quests_sync` so the client and broadcast code feel familiar.

| Direction | Type | Notes |
|---|---|---|
| client→server | `codex_upsert` | create/update a `log`/`note`/`lore` entry. **Players may author** `note`/`log`; `lore` is DM/assistant-DM. |
| client→server | `codex_delete` | author or DM only |
| client→server | `codex_link_set` | set links for an entry (the `@mention` result) |
| client→server | `codex_link_query` | "what's linked to this token/poi/item?" → returns entries (powers token/POI click) |
| server→client | `codex_sync` | per-user, **role+visibility-filtered** list (see §3). Mirrors `_broadcast_journal_state`. |
| server→client | `codex_entry_result` | ack for upsert/delete |

**Initial hydration:** fold a `codex` block into
`to_authoritative_snapshot_for_role(role, user_id)` so a connecting client gets
its visible entries in the same role-filtered snapshot that already powers
`request_state`. No separate fetch.

**Quests are not duplicated on the wire:** keep emitting `session_quests_sync`
from the engine; the client merges the quest projection into the Codex view. The
Codex never writes quest state — quest edits still go through the existing quest
handlers.

---

## 3. Visibility & broadcast (extend, don't replace)

Today `_broadcast_journal_state` does: `dm → all`, `player → shared only`.
Generalize that exact loop for three tiers:

```python
async def _broadcast_codex(session):
    entries = session.codex_entries
    for uid, u in session.users.items():
        visible = [e for e in entries if _codex_visible(e, u, session)]
        await manager.send_to(session.id, uid, {"type":"codex_sync",
                              "payload":{"entries": visible}})

def _codex_visible(e, u, session) -> bool:
    if u.role == "dm": return True                       # DM sees all
    if e["visibility"] == "dm": return False             # DM-only hidden
    if e["visibility"] == "private":
        return e["author_id"] == u.id                    # only the author
    # party: respect split-party subgroups (reuse _session_user_subgroup)
    if e.get("subgroup_id"):
        return session.get_user_subgroup_id(u.id) == e["subgroup_id"]
    return True
```

This is the same shape as the quest path's `_visible_session_quests_for_role`,
so the two read models stay consistent. Quest projections inherit quest
visibility from the engine unchanged.

---

## 4. What it communicates with (the cross-system surface)

This is the part that makes the Codex more than a notes panel. Each hook reuses
an existing channel.

**A. Combat / encounters → quest objectives (already live).**
`clear_encounter` and other events flow through
`handle_session_quest_objective_event` → `apply_objective_event` →
`resolve_session_quest_progression` → `session_quests_sync`. The Codex quest
projection re-renders automatically. *Extend* by emitting the same event from
more places (e.g. token death of a linked NPC → `defeat_npc` event) so the
objective tracker in the prototype ticks itself during play.

**B. Tokens / NPCs → Codex (new, cheap).**
Tokens already have ids. Add an "Open in Codex" entry to the token context menu
that sends `codex_link_query{target_kind:'token'|'npc', target_id}`. Because
`codex_links` is indexed by `(target_kind,target_id)`, backlinks are one query.
Now clicking the Red Knife Captain's token shows its lore, the bounty quest, and
any player suspicions — the prototype's "appears in N entries", wired to the map.

**C. Map / POIs → Codex.**
Journals already carry `poi_id`; promote that to a `codex_links` row. On
`poi_create/update`, offer "link a Codex entry". Clicking a POI surfaces linked
entries; a quest's `linked_poi_ids` already populate the graph.

**D. Handouts → Codex entry type.**
Handouts become `type='handout'` Codex entries that reuse the existing
`_handout_targets_user` recipient/subgroup logic for `visibility`. This folds the
"Journal & Handouts" panel into one place and gives handouts tags/links/search
for free.

**E. Quest completion → rewards → inventory/economy (already exists).**
On turn-in, the engine's `quest_premium_progression` resolves `reward_bundle`
(gold/xp/items/reputation/flags). The Codex shows the reward preview (prototype
already does) and a DM "grant rewards" action that calls the **existing** reward
path — items land in inventory, gold in currency. No new economy code.

**F. Quest board (in-world surface).**
`quest_board_bindings` + `_broadcast_quest_board_notice` already bind quests to
physical boards with `linked_handout_ids`/`linked_map_ids`/`linked_poi_ids`. The
Codex quest entry shows these bindings and can deep-link to the board token.

---

## 5. Authorization (fold in the earlier finding)

Route every new `codex_*` type through a **default-deny capability table**
checked in `handle_message` before dispatch, using the `require_role` helper that
already exists but is barely used:

```
codex_upsert(note|log)  → dm, player            (author owns the row)
codex_upsert(lore)      → dm, assistant_dm:lore.write
codex_upsert(handout)   → dm
codex_delete            → author OR dm
codex_link_query        → any connected role
quest_* (unchanged)     → existing guards (accept = player; objective clear = dm)
```

Players authoring notes/log is the unlock; ownership (`author_id`) is the guard
for edit/delete. Assistant-DM `lore.write` reuses `assistant_dm_has_scope`.

---

## 6. Frontend integration

- The Codex drawer (the prototype) **replaces** the `rail-journal-btn` panel and
  absorbs the scattered notes surfaces. It subscribes to `codex_sync` and merges
  the quest projection from `session_quests_sync`.
- Token + POI context menus gain **"Open in Codex"** → `codex_link_query`.
- `@`-mention autocomplete resolves against live session entities (tokens, POIs,
  items, other entries) and writes `codex_links` via `codex_link_set`.
- Quick-capture defaults to `visibility:'private'`, `author_id = me` — works for
  every role, fixing the player-journal gap.
- Keep the existing quest authoring handlers; just present them through the
  prototype's progressive wizard instead of the 35-field wall.

---

## 7. Phased build plan (independent PRs)

1. **PR1 — Codex store + migration.** Add `codex_entries`/`codex_links`,
   migrate `journal_entries` + `session.notes` blob, `codex_sync`/`upsert`/
   `delete`, three-tier visibility, capability table. Journals/notes now flow
   through the Codex; quests untouched. *Acceptance:* old journal data visible in
   Codex; players can author private/party notes; DM-only hidden from players;
   `pytest` green incl. `test_persistence_schema`, `test_campaign_roundtrip`.
2. **PR2 — Link graph + entity hooks.** `codex_links`, `codex_link_query`,
   token/POI "Open in Codex", project quest `linked_*_ids` into links, backlinks.
   *Acceptance:* clicking a token/POI returns linked entries; quest↔entry
   backlinks resolve both directions.
3. **PR3 — Quest projection + reward wiring + handouts-as-entries.** Read-only
   quest projection in the Codex, objective tracker bound to live
   `session_quests_sync`, reward-grant via existing engine, handouts become a
   Codex type. *Acceptance:* `clear_encounter` ticks the Codex tracker; turn-in
   grants via `quest_premium_progression`; handout recipients unchanged.
4. **PR4 — Frontend Codex drawer.** Replace the journal panel; subscribe to
   `codex_sync`; wizardize quest authoring. *Acceptance:* journal/quest/notes
   reachable only through the Codex; no orphaned panels (respect the
   "don't leave two authorities" rule).

---

## 8. Agent prompt (paste into Claude Code)

> Read `AGENTS.md` and this spec. Implement the Codex in the four PRs in §7 on
> `claude/*` branches. **Do not reimplement the quest progression or reward
> engine** — project `session_quests` into a read-only Codex `type='quest'` view
> and keep all quest writes on the existing handlers. Reuse the per-user
> role-filtered broadcast pattern from `_broadcast_journal_state` /
> `_broadcast_session_quests`; fold initial hydration into
> `to_authoritative_snapshot_for_role`. Migrate `journal_entries` and the
> `session.notes` blob into `codex_entries`; retire the blob. Gate every `codex_*`
> message through a default-deny capability table in `handle_message` using the
> existing `require_role`/`assistant_dm_has_scope`. Players must be able to author
> `note`/`log` entries (ownership via `author_id`). Per PR, run
> `python -m pytest tests/ -v --tb=short` plus
> `tests/test_persistence_schema.py`, `tests/test_campaign_roundtrip.py`,
> `tests/test_session_authority_and_scene_maps.py`, and commit a short report.
> **Constraints:** no forked authorities, no quest-engine rewrite, idempotent
> migration, all JSON valid, keep `journal_sync`/`session_quests_sync` emitting
> until PR4 cuts the client over. **Acceptance:** the per-PR criteria in §7.
