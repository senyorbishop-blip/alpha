# Architecture Review — DnD-Beta

**Reviewed:** 2026-04-07  
**Reviewer:** Staff-Level Architecture Pass  
**Scope:** Full backend + frontend codebase

---

## 1. Structure — Folder Layout and Scalability

### Current state

The backend is organized as a flat-ish `server/` package with sub-packages for
domain areas (`server/users/`, `server/campaigns/`, `server/handlers/`, …) and a
handful of top-level module files that carry cross-cutting logic.  The frontend
lives in `client/templates/` (one large Jinja template) and `client/static/js/`
(mixed live and dormant module files).

### What works

* `server/handlers/` separates WebSocket message handling from the HTTP/session
  layer.  Clear module boundaries exist for `tokens`, `combat`, `sound`,
  `narration`, and `map_editor`.
* `server/encumbrance.py`, `server/map_logic.py`, and `server/map_document.py`
  are already extracted as single-concern service modules.
* Tests live in a flat `tests/` directory which keeps discovery simple.

### What will break first at 10× scale

| Risk | Root cause | Impact |
|------|-----------|--------|
| **`server/handlers/inventory.py` (4,455 lines)** | Single file owns equipment, shops, loot, bags, encumbrance side-effects, and gold | Every feature touching an item requires editing/reviewing this file; merge conflicts guaranteed |
| **`server/handlers/content.py` (3,078 lines)** | Journal, quests, profiles, dice rolling, and chat share one module | Unrelated features break each other during refactors |
| **`client/templates/play.html` (~42,000 lines, ~32,000 of inline JS)** | All play-page UI logic lives in one non-cacheable template | Browser load time, no code splitting, and zero reuse across pages |
| **`main.py` (951 lines)** | App startup, middleware, page routes, API routes, and WebSocket endpoint in one file | Difficult to test individual routes in isolation; startup ordering bugs are hard to trace |

### Recommended folder additions (not immediate — sprint 2+)

```
server/
  handlers/
    equipment.py       # extracted from inventory.py
    shop.py            # extracted from inventory.py
    loot.py            # extracted from inventory.py
    bags.py            # extracted from inventory.py
    journal.py         # extracted from content.py
    quests.py          # extracted from content.py
    chat.py            # extracted from content.py
  api/
    loot_routes.py     # API routes currently inline in main.py
    map_routes.py      # map API helper functions currently in main.py
  middleware/
    upload.py          # LargeUploadMiddleware currently in main.py
```

---

## 2. Separation of Concerns

### Backend

**Healthy separations that already exist**

* `server/encumbrance.py` — pure weight/state calculations, no I/O.
* `server/map_logic.py` — pathfinding/blocker logic, no session mutation.
* `server/quest_progress.py` — objective tracking, no WebSocket calls.
* `server/handlers/common.py` — shared helpers imported by all handlers.

**Mixed responsibilities to address**

| File | Mixed concern | Ideal location |
|------|--------------|----------------|
| `main.py:785-940` | Loot generation logic | `server/handlers/inventory.py` or `server/api/loot_routes.py` |
| `main.py:324-380` | Map API helper functions (`_map_api_response`, `_map_request_user_id`, `_sanitize_map_update_payload`) | `server/handlers/cartographer.py` |
| `server/handlers/inventory.py:53-99` | Class/armor proficiency table (`_CLASS_DEFAULT_TRAINING`) | `server/constants.py` or `server/rules/equipment.py` |
| `server/handlers/combat.py:18` | `ENC_HEAVY = "heavily_encumbered"` redefined here | **Fixed** — now imported from `server.encumbrance` |

### Frontend

`client/templates/play.html` remains the live runtime owner for:
* Global state variables
* WebSocket send/receive glue
* Panel show/hide logic
* Token render updates

These are not yet broken out into dedicated modules because the migration is
staged (see `docs/frontend-modularization.md`).  Do **not** move logic out of
`play.html` until the corresponding module is confirmed to be loaded and
exercised in the same code path.

**Canonical pattern for new UI logic:** add it as a loaded `.js` module in
`client/static/js/` and reference it from `play.html` via a `<script>` tag —
never add new inline JS blocks to `play.html`.

---

## 3. Tech Debt — Three Highest-Risk Areas

### Risk 1 — Inconsistent handler permission guards

**Current state:** handlers use three distinct patterns to enforce access control:

```python
# Pattern A — silent return (client gets no feedback, appears frozen)
if user.role != "dm":
    return

# Pattern B — typed error message (client can show feedback)
await manager.send_to(session.id, user.id, {"type": "error", "payload": {"message": "…"}})
return

# Pattern C — module-local helper (inconsistent message type per module)
await _send_inventory_action_result(session, user.id, "Only the DM can do this.")
return
```

Pattern A is the most common and is a UX regression: players submit an action
and nothing happens.  It also makes security audits harder because "did the
guard fire?" requires reading every return path.

**Fix (implemented in this review):** `server/handlers/common.py` now exposes
`require_dm(session, user)` and `require_role(session, user, *roles)` — both
return `bool` and send a typed `"error"` message on denial.  Migrate existing
handlers gradually (start with new code; backfill during next feature touches).

```python
# Canonical pattern — use in all new handler code
async def handle_foo(payload: dict, session: Session, user: User):
    if not await require_dm(session, user):
        return
    # ... DM-only logic ...
```

### Risk 2 — Magic constants scattered across handler files

**Current state:** domain-level constants are defined at the top of whichever
handler first needed them, creating undiscoverable duplicates:

| Constant | Defined in | Also used in |
|----------|-----------|-------------|
| `ENC_HEAVY = "heavily_encumbered"` | `server/handlers/combat.py` *(was)* | `server/encumbrance.py` (canonical) |
| `_VALID_TRACKS = {"silence", "tavern", …}` | `server/handlers/sound.py` | referenced in `combat.py` string literal |
| `_EQUIPMENT_KINDS = {"armor", "shield", …}` | `server/handlers/inventory.py` | compared against in `content.py` |
| `PX_PER_GRID = 50.0` | `server/handlers/common.py` | also hard-coded in `play.html` JS as `const PX_PER_GRID = 50` |

**Fix (implemented):** `server/constants.py` now contains canonical definitions
for `PX_PER_GRID`, `FT_PER_GRID`, role strings, ambient tracks, equipment slot
enumerations, commerce TTLs, and loot mechanics.  Handler files continue to keep
their existing private `_` aliases until a future cleanup pass; new code should
import from `server.constants`.

### Risk 3 — `inventory.py` and `content.py` monolith handlers

**Current state:** `inventory.py` (4,455 lines) and `content.py` (3,078 lines)
each own unrelated features.  Both files are touched by almost every feature
sprint, which:

* Increases merge-conflict frequency (≥3 people touch them per sprint)
* Makes PR reviews hard (thousands of lines of context unrelated to the change)
* Prevents targeted test runs (a failing import breaks all dependent tests)
* Risks accidental coupling between unrelated systems (shop logic accidentally
  reading encumbrance state; quest handlers accidentally mutating item library)

**Recommended split for `inventory.py`** (sprint 2):

| New file | Lines to extract |
|----------|-----------------|
| `equipment.py` | `_equip_item`, `_unequip_item`, `_recompute_equipment_effects`, `_CLASS_DEFAULT_TRAINING` |
| `shop.py` | shop open/close/haggle/buy/sell handlers + pricing helpers |
| `loot.py` | `handle_generate_loot`, `handle_distribute_loot`, loot-roll state |
| `bags.py` | `handle_bag_add_item`, `handle_bag_remove_item`, `handle_bag_destroy` |

**Recommended split for `content.py`** (sprint 3):

| New file | Lines to extract |
|----------|-----------------|
| `journal.py` | `handle_journal_upsert`, `handle_journal_delete`, broadcast helper |
| `quests.py` | All quest/objective/progression handlers |
| `chat.py` | `handle_dice_roll`, `handle_chat_message`, `handle_dice_special_fx` |

---

## 4. Patterns — Canonical Definitions

### A. Handler permission check

**Do this** (new canonical — `server/handlers/common.py`):

```python
# DM-only guard
async def handle_foo(payload: dict, session: Session, user: User):
    if not await require_dm(session, user):
        return

# Allow DM + player, block viewer
async def handle_bar(payload: dict, session: Session, user: User):
    if not await require_role(session, user, "dm", "player"):
        return
```

**Do not do this** (existing anti-patterns to migrate away from):

```python
# ❌ Silent return — client gets no feedback
if user.role != "dm":
    return

# ❌ Ad-hoc inline error — duplicates the wire format
await manager.send_to(session.id, user.id, {"type": "error", "payload": {"message": "…"}})
return
```

### B. Sending a typed feedback message to one user

```python
# ✅ New canonical
await send_error(session, user.id, "Descriptive error text.")

# ✅ Also acceptable for non-error confirmation (module-specific helpers are fine
#    when they carry domain-specific payload shape — e.g. inventory_action_result)
await _send_inventory_action_result(session, user.id, "Item equipped.")
```

### C. Referencing shared constants

```python
# ✅ Import from server.constants
from server.constants import VALID_AMBIENT_TRACKS, EQUIPMENT_KINDS

# ❌ Redefine locally — only acceptable for private module-level tuning values
_VALID_TRACKS = {"silence", "tavern", "dungeon", "forest", "battle"}
```

### D. Handler signature

All WebSocket handlers must follow this signature (already enforced by the
dispatch table in `server/handlers/__init__.py`):

```python
async def handle_<message_type>(payload: dict, session: Session, user: User):
    ...
```

### E. Saving state

Always use `save_campaign_async(session)` (not the sync variant) inside
handlers so the WebSocket event loop is never blocked:

```python
await save_campaign_async(session)  # ✅
save_campaign(session)              # ❌ blocks the event loop
```

---

## 5. Dependencies

### Current `requirements.txt` analysis

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| `fastapi` | 0.111.0 | Slightly behind (0.115.x current) | Safe; no critical CVEs in 0.111 |
| `uvicorn[standard]` | 0.30.1 | Behind (0.34.x current) | Consider upgrading for HTTP/2 fixes |
| `websockets` | 12.0 | Current | ✅ |
| `python-multipart` | 0.0.9 | Current | ✅ |
| `jinja2` | 3.1.4 | Current | ✅ |
| `httpx` | 0.27.0 | Behind (0.28.x current) | Low risk |
| `pypdf` | 5.9.0 | Current | ✅ |
| `Pillow` | ≥10.0.0 | Acceptable floor | Pin to a specific minor for reproducibility |
| `PyJWT` | ≥2.8.0 | Acceptable floor | ✅ |
| `bcrypt` | ≥4.0.0 | Acceptable floor | ✅ |
| `cffi` | ≥1.15.0 | Transitive | Could be dropped if bcrypt drops it |
| `requests` | ≥2.31.0 | Acceptable floor | Used for ElevenLabs HTTP; consider replacing with `httpx` (already in deps) to avoid two HTTP clients |
| `python-dotenv` | ≥1.0.0 | Acceptable floor | ✅ |

### Redundant packages

* **`requests`** and **`httpx`** both exist.  `httpx` is already present for
  async HTTP; the `requests` usage (ElevenLabs REST calls in `narration.py`)
  should be migrated to `httpx` to remove a second sync HTTP client dependency.
  This is a sprint 2 candidate — do not rush it.

### Missing from `requirements.txt`

* `pytest` is not listed but is required for the test suite.  Add
  `pytest>=8.0.0` (or `pytest>=7.4.0` for broader compatibility) to keep CI
  reproducible.

### No risky / malicious packages found

The dependency surface is small and well-chosen.  No packages with known
high-severity CVEs at the pinned versions.

---

## Prioritized Refactor Roadmap

### This sprint (highest leverage, lowest risk)

1. **[Done] Add `send_error`, `require_dm`, `require_role` to `server/handlers/common.py`**  
   Canonical pattern is now defined and tested.  Use it for all new handler code
   immediately.

2. **[Done] Expand `server/constants.py`**  
   Grid, role, ambient track, equipment slot, commerce TTL, and loot constants
   are now centralized.  Import from `server.constants` in new code.

3. **[Done] Remove duplicate `ENC_HEAVY` definition in `combat.py`**  
   Now imported from `server.encumbrance` (the authoritative definition).

4. **Add `pytest` to `requirements.txt`**  
   One-line change; prevents "why do tests not run on a fresh checkout" reports.

5. **Audit and migrate top-5 silent-return guards**  
   Pick the five highest-traffic DM-only handlers (combat update, journal upsert,
   item library ops) and apply `require_dm` so players get feedback.  Each
   change is 2 lines; each should have a test.

### Next sprint

6. **Replace `requests` with `httpx` in `narration.py`**  
   Drop the second HTTP client.  Narration tests already cover the affected paths.

7. **Extract `server/handlers/equipment.py` from `inventory.py`**  
   Move equip/unequip handlers and `_CLASS_DEFAULT_TRAINING` into a new file.
   Update `__init__.py` dispatch table imports.  No behavior change.

8. **Extract `server/handlers/journal.py` from `content.py`**  
   Journal is self-contained (3 functions + 1 broadcast helper).  Easiest split
   in `content.py`.

9. **Move map API helpers out of `main.py`**  
   `_map_api_response`, `_map_request_user_id`, `_map_is_editable`,
   `_sanitize_map_update_payload` should live in `server/handlers/cartographer.py`
   or a new `server/api/map_routes.py`.

### This quarter

10. **Complete `inventory.py` split** into equipment, shop, loot, bags modules.

11. **Complete `content.py` split** into journal, quests, chat modules.

12. **Frontend: migrate new UI logic to loaded `.js` modules** — no new inline
    JS in `play.html`; every new feature gets a `client/static/js/` module and a
    `<script src="…">` tag.

13. **Pin all `requirements.txt` ranges to exact versions** for reproducible CI
    builds.  Use a `requirements-dev.txt` for test tooling.

14. **Apply `require_dm` / `require_role` to all remaining silent-return guards**
    across all handler files as a global cleanup pass.
