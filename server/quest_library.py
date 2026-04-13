"""Built-in premade quest template library helpers."""
from __future__ import annotations

import json
import secrets
import time
from copy import deepcopy
from pathlib import Path

_DEFAULT_LIBRARY_PATH = Path(__file__).resolve().parent / "data" / "quest_templates_builtin.json"


def _as_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for entry in value:
        text = str(entry or "").strip()
        if text:
            out.append(text[:120])
    return out[:12]


def _as_id_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for entry in value:
        text = str(entry or "").strip()[:64]
        if not text or text in out:
            continue
        out.append(text)
    return out[:24]


def _normalize_template(raw: dict, idx: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()[:120]
    if not title:
        return None
    template_id = str(raw.get("template_id") or raw.get("id") or f"builtin-quest-{idx + 1:02d}").strip()[:64]
    if not template_id:
        return None
    summary = str(raw.get("summary") or raw.get("short_summary") or "").strip()[:300]
    description = str(raw.get("description") or raw.get("long_description") or "").strip()[:4000]
    category = str(raw.get("category") or raw.get("type") or "general").strip()[:60] or "general"
    tier = str(raw.get("difficulty_tier") or raw.get("tier") or "Tier 1").strip()[:40] or "Tier 1"
    return {
        "template_id": template_id,
        "title": title,
        "summary": summary,
        "description": description,
        "category": category,
        "difficulty_tier": tier,
        "objective_structure": _as_list(raw.get("objective_structure")),
        "reward_bundle": {
            "gold": max(0, int(raw.get("reward_bundle", {}).get("gold", 0) or 0)),
            "xp": max(0, int(raw.get("reward_bundle", {}).get("xp", 0) or 0)),
            "items": _as_list((raw.get("reward_bundle") or {}).get("items")),
        },
        "suggested_map_poi_type": str(raw.get("suggested_map_poi_type") or "").strip()[:80],
        "enemy_npc_faction_tags": _as_list(raw.get("enemy_npc_faction_tags")),
        "required_faction_tags": _as_list(raw.get("required_faction_tags")),
        "required_guild_rank_id": str(raw.get("required_guild_rank_id") or "").strip()[:40].lower(),
        "required_guild_rank_points": max(0, int(raw.get("required_guild_rank_points") or 0)),
        "prerequisite_quest_ids": _as_id_list(raw.get("prerequisite_quest_ids")),
        "unlocks_quest_ids": _as_id_list(raw.get("unlocks_quest_ids")),
        "guild_tags": _as_list(raw.get("guild_tags")),
        "follow_up_hooks": _as_list(raw.get("follow_up_hooks")),
        "board_faction_label": str(raw.get("board_faction_label") or "").strip()[:80],
        "source_marker": str(raw.get("source_marker") or "built_in").strip()[:40] or "built_in",
    }


def load_builtin_quest_templates(path: Path | None = None) -> list[dict]:
    library_path = path or _DEFAULT_LIBRARY_PATH
    try:
        parsed = json.loads(library_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    out: list[dict] = []
    for idx, raw in enumerate(parsed):
        normalized = _normalize_template(raw, idx)
        if normalized:
            out.append(normalized)
    return out


def get_quest_template(template_id: str, *, path: Path | None = None) -> dict | None:
    target = str(template_id or "").strip()
    if not target:
        return None
    for template in load_builtin_quest_templates(path):
        if str(template.get("template_id") or "") == target:
            return deepcopy(template)
    return None


def build_session_quest_from_template(template: dict, *, imported_by: str = "dm") -> dict:
    now = time.time()
    objective_structure = _as_list(template.get("objective_structure"))
    objective_list = [
        {
            "id": f"obj-{idx + 1}",
            "title": text,
            "status": "active" if idx == 0 else "pending",
        }
        for idx, text in enumerate(objective_structure)
    ]
    reward_bundle = dict(template.get("reward_bundle") or {})
    reward_bundle["items"] = _as_list(reward_bundle.get("items"))
    reward_bundle["gold"] = max(0, int(reward_bundle.get("gold", 0) or 0))
    reward_bundle["xp"] = max(0, int(reward_bundle.get("xp", 0) or 0))

    return {
        "id": f"sq-{secrets.token_hex(6)}",
        "template_id": str(template.get("template_id") or ""),
        "title": str(template.get("title") or "Untitled quest"),
        "summary": str(template.get("summary") or ""),
        "description": str(template.get("description") or ""),
        "status": "available",
        "category": str(template.get("category") or "general"),
        "difficulty_tier": str(template.get("difficulty_tier") or "Tier 1"),
        "objective_list": objective_list,
        "reward_bundle": reward_bundle,
        "visibility": {"mode": "party_public", "roles": ["player", "viewer"], "player_ids": [], "hidden_objective_ids": []},
        "linked_handout_ids": [],
        "linked_poi_ids": [],
        "linked_map_ids": [],
        "faction_tags": _as_list(template.get("enemy_npc_faction_tags")),
        "required_faction_tags": _as_list(template.get("required_faction_tags")),
        "required_guild_rank_id": str(template.get("required_guild_rank_id") or "").strip()[:40].lower(),
        "required_guild_rank_points": max(0, int(template.get("required_guild_rank_points") or 0)),
        "prerequisite_quest_ids": _as_id_list(template.get("prerequisite_quest_ids")),
        "unlocks_quest_ids": _as_id_list(template.get("unlocks_quest_ids")),
        "guild_tags": _as_list(template.get("guild_tags")),
        "hidden_until_unlocked": False,
        "lock_visibility": "listed",
        "source_type": "template_import",
        "source_marker": str(template.get("source_marker") or "built_in"),
        "created_at": now,
        "updated_at": now,
        "meta": {
            "board_label": str(template.get("board_faction_label") or ""),
            "suggested_map_poi_type": str(template.get("suggested_map_poi_type") or ""),
            "follow_up_hooks": _as_list(template.get("follow_up_hooks")),
            "imported_by": str(imported_by or "dm")[:64],
            "template_title": str(template.get("title") or ""),
        },
    }
