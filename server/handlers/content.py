"""
server/handlers/content.py — Journal, library, character profiles, chat, and state handlers.
"""
import asyncio
import time
import secrets
import logging

logger = logging.getLogger(__name__)
from server.session import Session, User, normalize_profile_owner_key, set_assistant_dm_permissions, assistant_dm_has_scope, grant_temp_permission, ACTIVE_PROFILE_ID_KEY_LIMIT, set_player_gold_for_user, _inventory_owner_key, bump_character_hydration_revisions, build_quick_actions_sync_payload
from server.character.profile_sanitize import strip_runtime_fields
from server.character.profile_assets import sanitize_profile_persistence
from server.quest_library import (
    build_session_quest_from_template,
    get_quest_template,
    load_builtin_quest_templates,
)
from server.prep_pack_library import (
    get_prep_pack,
    load_builtin_prep_packs,
    prep_pack_catalog_view,
    build_import_instance_id,
    import_timestamp,
)
from server.quest_progress import (
    apply_dm_override,
    apply_objective_event,
    normalize_objective_list,
    normalize_quest_payload_shape,
    normalize_quest_status,
    rebuild_progress,
)
from server.quest_progression import (
    normalize_quest_progression_fields,
    resolve_session_quest_progression,
)
from server.quest_premium_progression import build_premium_progression_snapshot
from server.faction_reputation import apply_reputation_changes_to_session
from server.living_world_events import emit_world_event, consume_world_event
from server.handlers.common import (
    manager,
    save_campaign_async,
    _safe_int,
    _broadcast_token_state_sync,
    build_live_state_debug_summary,
)
from server.handlers.inventory import (
    _update_encumbrance_cache,
    _broadcast_inventory_state,
    _recompute_equipment_effects,
)


def _normalize_item_library_entry(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()[:80]
    if not name:
        return None
    category = str(raw.get("category") or "Gear").strip()[:40] or "Gear"
    rarity = str(raw.get("rarity") or "Common").strip()[:32] or "Common"
    notes = str(raw.get("notes") or "").strip()[:240]
    price = str(raw.get("price") or "").strip()[:32]
    default_qty = _safe_int(raw.get("default_qty"), 1, minimum=1, maximum=999)
    entry_id = str(raw.get("id") or secrets.token_hex(6)).strip()[:48] or secrets.token_hex(6)
    updated_at = float(raw.get("updated_at") or time.time())
    out = {
        "id": entry_id,
        "name": name,
        "category": category,
        "rarity": rarity,
        "notes": notes,
        "price": price,
        "default_qty": default_qty,
        "updated_at": updated_at,
    }
    return out


# NOTE: The rest of this file is intentionally unchanged below this import section.
