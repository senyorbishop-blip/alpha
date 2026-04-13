"""Built-in DM prep-pack library helpers.

Prep packs are reusable import bundles that map onto existing session content
systems (quests, handouts, POIs, encounter templates, references).
"""
from __future__ import annotations

import json
import secrets
import time
from copy import deepcopy
from pathlib import Path

_DEFAULT_LIBRARY_PATH = Path(__file__).resolve().parent / "data" / "prep_packs_builtin.json"


def _as_text(value, limit: int, default: str = "") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    return text[:limit]


def _as_list(value, *, limit: int = 24, item_limit: int = 120) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for entry in value:
        text = str(entry or "").strip()
        if text and text not in out:
            out.append(text[:item_limit])
    return out[:limit]


def _as_id(value, fallback: str) -> str:
    candidate = str(value or "").strip()[:64]
    return candidate or fallback


def _normalize_quest_entry(raw: dict, idx: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    title = _as_text(raw.get("title"), 120)
    if not title:
        return None
    objectives = _as_list(raw.get("objective_list") or raw.get("objectives"), limit=16)
    return {
        "id": _as_id(raw.get("id"), f"pack-quest-{idx + 1}"),
        "title": title,
        "summary": _as_text(raw.get("summary"), 300),
        "description": _as_text(raw.get("description"), 4000),
        "category": _as_text(raw.get("category"), 60, "general"),
        "difficulty_tier": _as_text(raw.get("difficulty_tier"), 40, "Tier 1"),
        "status": _as_text(raw.get("status"), 24, "available").lower(),
        "objective_list": objectives,
        "linked_poi_ids": _as_list(raw.get("linked_poi_ids"), limit=16, item_limit=80),
        "linked_map_ids": _as_list(raw.get("linked_map_ids"), limit=16, item_limit=80),
        "linked_handout_ids": _as_list(raw.get("linked_handout_ids"), limit=16, item_limit=80),
        "linked_npc_ids": _as_list(raw.get("linked_npc_ids"), limit=16, item_limit=80),
        "linked_encounter_template_ids": _as_list(raw.get("linked_encounter_template_ids"), limit=16, item_limit=80),
        "reward_bundle": {
            "gold": max(0, int((raw.get("reward_bundle") or {}).get("gold", 0) or 0)),
            "xp": max(0, int((raw.get("reward_bundle") or {}).get("xp", 0) or 0)),
            "items": _as_list((raw.get("reward_bundle") or {}).get("items"), limit=16, item_limit=80),
        },
    }


def _normalize_handout_entry(raw: dict, idx: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    title = _as_text(raw.get("title"), 120)
    if not title:
        return None
    return {
        "id": _as_id(raw.get("id"), f"pack-handout-{idx + 1}"),
        "title": title,
        "public_text": _as_text(raw.get("public_text") or raw.get("content"), 12000),
        "dm_secret_text": _as_text(raw.get("dm_secret_text"), 12000),
        "recipients": "all",
    }


def _normalize_poi_entry(raw: dict, idx: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = _as_text(raw.get("name"), 80)
    if not name:
        return None
    return {
        "id": _as_id(raw.get("id"), f"pack-poi-{idx + 1}"),
        "name": name,
        "description": _as_text(raw.get("description"), 2000),
        "dm_notes": _as_text(raw.get("dm_notes"), 2000),
        "poi_type": _as_text(raw.get("poi_type"), 40, "city"),
        "map_context": _as_text(raw.get("map_context"), 80, "world") or "world",
        "local_map_url": _as_text(raw.get("local_map_url"), 400),
        "x": float(raw.get("x", 0) or 0),
        "y": float(raw.get("y", 0) or 0),
        "revealed_to_players": bool(raw.get("revealed_to_players", True)),
    }


def _normalize_encounter_entry(raw: dict, idx: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = _as_text(raw.get("name"), 120)
    entries_raw = raw.get("entries") if isinstance(raw.get("entries"), list) else []
    if not name or not entries_raw:
        return None
    entries = []
    for entry in entries_raw[:40]:
        if not isinstance(entry, dict):
            continue
        creature_id = _as_text(entry.get("creature_id") or entry.get("canonical_creature_id"), 80)
        if not creature_id:
            continue
        entries.append({
            "creature_id": creature_id,
            "canonical_creature_id": creature_id,
            "name": _as_text(entry.get("name"), 120, "Creature"),
            "qty": max(1, min(20, int(entry.get("qty", 1) or 1))),
            "source": _as_text(entry.get("source"), 32, "library").lower(),
            "source_type": _as_text(entry.get("source_type") or entry.get("source"), 32, "library").lower(),
            "entry_type": _as_text(entry.get("entry_type") or entry.get("creature_type"), 24, "monster").lower(),
            "creature_type": _as_text(entry.get("creature_type") or entry.get("entry_type"), 24, "monster").lower(),
            "monster_type": _as_text(entry.get("monster_type"), 40).lower(),
            "cr": _as_text(entry.get("cr"), 16),
        })
    if not entries:
        return None
    return {
        "id": _as_id(raw.get("id"), f"pack-encounter-{idx + 1}"),
        "name": name,
        "notes": _as_text(raw.get("notes"), 400),
        "map_context": _as_text(raw.get("map_context"), 80, "world") or "world",
        "entries": entries,
    }


def _normalize_pack(raw: dict, idx: int) -> dict | None:
    if not isinstance(raw, dict):
        return None
    name = _as_text(raw.get("name") or raw.get("title"), 120)
    if not name:
        return None
    pack_id = _as_id(raw.get("pack_id") or raw.get("id"), f"prep-pack-{idx + 1:02d}")
    quests = []
    for i, raw_entry in enumerate(raw.get("quests") or []):
        entry = _normalize_quest_entry(raw_entry, i)
        if entry:
            quests.append(entry)
    handouts = []
    for i, raw_entry in enumerate(raw.get("handouts") or []):
        entry = _normalize_handout_entry(raw_entry, i)
        if entry:
            handouts.append(entry)
    pois = []
    for i, raw_entry in enumerate(raw.get("pois") or []):
        entry = _normalize_poi_entry(raw_entry, i)
        if entry:
            pois.append(entry)
    encounters = []
    for i, raw_entry in enumerate(raw.get("encounters") or []):
        entry = _normalize_encounter_entry(raw_entry, i)
        if entry:
            encounters.append(entry)
    return {
        "pack_id": pack_id,
        "name": name,
        "summary": _as_text(raw.get("summary"), 300),
        "description": _as_text(raw.get("description"), 1600),
        "category": _as_text(raw.get("category"), 60, "general"),
        "tags": _as_list(raw.get("tags"), limit=12, item_limit=40),
        "map_references": _as_list(raw.get("map_references"), limit=16, item_limit=80),
        "npc_references": _as_list(raw.get("npc_references"), limit=24, item_limit=80),
        "source_marker": _as_text(raw.get("source_marker"), 40, "built_in"),
        "quests": quests,
        "handouts": handouts,
        "pois": pois,
        "encounters": encounters,
    }


def load_builtin_prep_packs(path: Path | None = None) -> list[dict]:
    library_path = path or _DEFAULT_LIBRARY_PATH
    try:
        parsed = json.loads(library_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    out: list[dict] = []
    for idx, raw in enumerate(parsed):
        normalized = _normalize_pack(raw, idx)
        if normalized:
            out.append(normalized)
    return out


def get_prep_pack(pack_id: str, *, path: Path | None = None) -> dict | None:
    target = _as_text(pack_id, 64)
    if not target:
        return None
    for pack in load_builtin_prep_packs(path):
        if str(pack.get("pack_id") or "") == target:
            return deepcopy(pack)
    return None


def prep_pack_catalog_view(pack: dict) -> dict:
    payload = dict(pack or {})
    payload.pop("quests", None)
    payload.pop("handouts", None)
    payload.pop("pois", None)
    payload.pop("encounters", None)
    payload["counts"] = {
        "quests": len((pack or {}).get("quests") or []),
        "handouts": len((pack or {}).get("handouts") or []),
        "pois": len((pack or {}).get("pois") or []),
        "encounters": len((pack or {}).get("encounters") or []),
    }
    return payload


def build_import_instance_id(pack_id: str) -> str:
    return f"{_as_text(pack_id, 40, 'prep-pack')}-{secrets.token_hex(4)}"


def import_timestamp() -> float:
    return time.time()
