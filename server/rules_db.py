from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List

from server.db import get_conn
from server.rules_content import OPEN_5E_SPELLS
from server.rules_engine import normalize_name


def _json_dumps(value: Any) -> str:
    return json.dumps(value or {}, separators=(",", ":"))


def _json_loads(value: str, default):
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def init_rules_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS rules_spells (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                source TEXT,
                source_page TEXT,
                rules_version TEXT,
                spell_level INTEGER NOT NULL DEFAULT 0,
                school TEXT,
                casting_time TEXT,
                range_text TEXT,
                components TEXT,
                material_component_text TEXT,
                duration TEXT,
                concentration INTEGER NOT NULL DEFAULT 0,
                ritual INTEGER NOT NULL DEFAULT 0,
                attack_type TEXT,
                save_ability TEXT,
                damage_type TEXT,
                healing_type TEXT,
                base_effect_text TEXT,
                base_damage_formula TEXT,
                higher_level_text TEXT,
                scaling_type TEXT,
                scaling_data TEXT NOT NULL DEFAULT '{}',
                targeting_data TEXT NOT NULL DEFAULT '{}',
                area_data TEXT NOT NULL DEFAULT '{}',
                tags TEXT NOT NULL DEFAULT '[]',
                class_lists TEXT NOT NULL DEFAULT '[]',
                subclass_lists TEXT NOT NULL DEFAULT '[]',
                granted_by_feat TEXT NOT NULL DEFAULT '[]',
                granted_by_species TEXT NOT NULL DEFAULT '[]',
                granted_by_item TEXT NOT NULL DEFAULT '[]',
                is_homebrew INTEGER NOT NULL DEFAULT 0,
                created_by_dm INTEGER NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS rules_custom_spells (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                source TEXT,
                source_page TEXT,
                rules_version TEXT,
                spell_level INTEGER NOT NULL DEFAULT 0,
                school TEXT,
                casting_time TEXT,
                range_text TEXT,
                components TEXT,
                material_component_text TEXT,
                duration TEXT,
                concentration INTEGER NOT NULL DEFAULT 0,
                ritual INTEGER NOT NULL DEFAULT 0,
                attack_type TEXT,
                save_ability TEXT,
                damage_type TEXT,
                healing_type TEXT,
                base_effect_text TEXT,
                base_damage_formula TEXT,
                higher_level_text TEXT,
                scaling_type TEXT,
                scaling_data TEXT NOT NULL DEFAULT '{}',
                targeting_data TEXT NOT NULL DEFAULT '{}',
                area_data TEXT NOT NULL DEFAULT '{}',
                tags TEXT NOT NULL DEFAULT '[]',
                class_lists TEXT NOT NULL DEFAULT '[]',
                subclass_lists TEXT NOT NULL DEFAULT '[]',
                granted_by_feat TEXT NOT NULL DEFAULT '[]',
                granted_by_species TEXT NOT NULL DEFAULT '[]',
                granted_by_item TEXT NOT NULL DEFAULT '[]',
                is_homebrew INTEGER NOT NULL DEFAULT 1,
                created_by_dm INTEGER NOT NULL DEFAULT 1,
                created_by TEXT,
                created_at REAL NOT NULL DEFAULT 0,
                updated_by TEXT,
                updated_at REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS player_granted_spells (
                id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                recipient_user_id TEXT NOT NULL,
                spell_id TEXT NOT NULL,
                spell_source TEXT NOT NULL DEFAULT 'srd',
                granted_by_user_id TEXT NOT NULL,
                granted_at REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS rules_match_review (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT,
                character_name TEXT,
                content_type TEXT NOT NULL DEFAULT 'spell',
                original_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                status TEXT NOT NULL,
                match_score REAL NOT NULL DEFAULT 0,
                suggested_rule_id TEXT,
                suggested_name TEXT,
                source_tag TEXT,
                imported_payload TEXT NOT NULL DEFAULT '{}',
                reviewed INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL DEFAULT 0
            );
            """
        )
        conn.commit()
    seed_rules_spells()


ALL_COLUMNS = [
    "id", "name", "normalized_name", "source", "source_page", "rules_version", "spell_level", "school",
    "casting_time", "range", "components", "material_component_text", "duration", "concentration", "ritual",
    "attack_type", "save_ability", "damage_type", "healing_type", "base_effect_text", "base_damage_formula",
    "higher_level_text", "scaling_type", "scaling_data", "targeting_data", "area_data", "tags", "class_lists",
    "subclass_lists", "granted_by_feat", "granted_by_species", "granted_by_item", "is_homebrew", "created_by_dm", "updated_at",
]


def _serialize_spell(rule: Dict[str, Any]) -> Dict[str, Any]:
    record = dict(rule or {})
    record["normalized_name"] = normalize_name(record.get("name"))
    record["concentration"] = 1 if record.get("concentration") else 0
    record["ritual"] = 1 if record.get("ritual") else 0
    record["is_homebrew"] = 1 if record.get("is_homebrew") else 0
    record["created_by_dm"] = 1 if record.get("created_by_dm") else 0
    for key in ["scaling_data", "targeting_data", "area_data", "tags", "class_lists", "subclass_lists", "granted_by_feat", "granted_by_species", "granted_by_item"]:
        record[key] = _json_dumps(record.get(key, {} if key.endswith("_data") else []))
    record["range_text"] = record.pop("range", record.get("range_text") or "")
    record.setdefault("updated_at", time.time())
    return record


def _deserialize_spell(row) -> Dict[str, Any]:
    d = dict(row)
    d["range"] = d.pop("range_text", "")
    d["concentration"] = bool(d.get("concentration"))
    d["ritual"] = bool(d.get("ritual"))
    d["is_homebrew"] = bool(d.get("is_homebrew"))
    d["created_by_dm"] = bool(d.get("created_by_dm"))
    for key in ["scaling_data", "targeting_data", "area_data"]:
        d[key] = _json_loads(d.get(key), {})
    for key in ["tags", "class_lists", "subclass_lists", "granted_by_feat", "granted_by_species", "granted_by_item"]:
        d[key] = _json_loads(d.get(key), [])
    return d


def seed_rules_spells() -> None:
    with get_conn() as conn:
        for spell in OPEN_5E_SPELLS:
            rec = _serialize_spell(spell)
            conn.execute(
                """
                INSERT INTO rules_spells (
                    id,name,normalized_name,source,source_page,rules_version,spell_level,school,
                    casting_time,range_text,components,material_component_text,duration,concentration,ritual,
                    attack_type,save_ability,damage_type,healing_type,base_effect_text,base_damage_formula,
                    higher_level_text,scaling_type,scaling_data,targeting_data,area_data,tags,class_lists,
                    subclass_lists,granted_by_feat,granted_by_species,granted_by_item,is_homebrew,created_by_dm,updated_at
                ) VALUES (
                    :id,:name,:normalized_name,:source,:source_page,:rules_version,:spell_level,:school,
                    :casting_time,:range_text,:components,:material_component_text,:duration,:concentration,:ritual,
                    :attack_type,:save_ability,:damage_type,:healing_type,:base_effect_text,:base_damage_formula,
                    :higher_level_text,:scaling_type,:scaling_data,:targeting_data,:area_data,:tags,:class_lists,
                    :subclass_lists,:granted_by_feat,:granted_by_species,:granted_by_item,:is_homebrew,:created_by_dm,:updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    normalized_name=excluded.normalized_name,
                    source=excluded.source,
                    source_page=excluded.source_page,
                    rules_version=excluded.rules_version,
                    spell_level=excluded.spell_level,
                    school=excluded.school,
                    casting_time=excluded.casting_time,
                    range_text=excluded.range_text,
                    components=excluded.components,
                    material_component_text=excluded.material_component_text,
                    duration=excluded.duration,
                    concentration=excluded.concentration,
                    ritual=excluded.ritual,
                    attack_type=excluded.attack_type,
                    save_ability=excluded.save_ability,
                    damage_type=excluded.damage_type,
                    healing_type=excluded.healing_type,
                    base_effect_text=excluded.base_effect_text,
                    base_damage_formula=excluded.base_damage_formula,
                    higher_level_text=excluded.higher_level_text,
                    scaling_type=excluded.scaling_type,
                    scaling_data=excluded.scaling_data,
                    targeting_data=excluded.targeting_data,
                    area_data=excluded.area_data,
                    tags=excluded.tags,
                    class_lists=excluded.class_lists,
                    subclass_lists=excluded.subclass_lists,
                    granted_by_feat=excluded.granted_by_feat,
                    granted_by_species=excluded.granted_by_species,
                    granted_by_item=excluded.granted_by_item,
                    updated_at=excluded.updated_at
                """,
                rec,
            )
        conn.commit()


def get_official_spells() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM rules_spells ORDER BY spell_level, name").fetchall()
    return [_deserialize_spell(row) for row in rows]


def get_custom_spells(session_id: str) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM rules_custom_spells WHERE session_id=? ORDER BY spell_level, name", (session_id,)).fetchall()
    return [_deserialize_spell(row) for row in rows]


def upsert_custom_spell(session_id: str, user_id: str, spell: Dict[str, Any]) -> Dict[str, Any]:
    rec = _serialize_spell(spell)
    now = time.time()
    rec["id"] = rec.get("id") or f"custom_spell_{uuid.uuid4().hex[:12]}"
    rec["session_id"] = session_id
    rec["created_by"] = str(user_id)
    rec["created_at"] = now
    rec["updated_by"] = str(user_id)
    rec["updated_at"] = now
    with get_conn() as conn:
        existing = conn.execute("SELECT id, created_by, created_at FROM rules_custom_spells WHERE id=? AND session_id=?", (rec["id"], session_id)).fetchone()
        if existing:
            rec["created_by"] = existing["created_by"]
            rec["created_at"] = existing["created_at"]
        conn.execute(
            """
            INSERT INTO rules_custom_spells (
                id,session_id,name,normalized_name,source,source_page,rules_version,spell_level,school,
                casting_time,range_text,components,material_component_text,duration,concentration,ritual,
                attack_type,save_ability,damage_type,healing_type,base_effect_text,base_damage_formula,
                higher_level_text,scaling_type,scaling_data,targeting_data,area_data,tags,class_lists,
                subclass_lists,granted_by_feat,granted_by_species,granted_by_item,is_homebrew,created_by_dm,
                created_by,created_at,updated_by,updated_at
            ) VALUES (
                :id,:session_id,:name,:normalized_name,:source,:source_page,:rules_version,:spell_level,:school,
                :casting_time,:range_text,:components,:material_component_text,:duration,:concentration,:ritual,
                :attack_type,:save_ability,:damage_type,:healing_type,:base_effect_text,:base_damage_formula,
                :higher_level_text,:scaling_type,:scaling_data,:targeting_data,:area_data,:tags,:class_lists,
                :subclass_lists,:granted_by_feat,:granted_by_species,:granted_by_item,:is_homebrew,:created_by_dm,
                :created_by,:created_at,:updated_by,:updated_at
            )
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                normalized_name=excluded.normalized_name,
                source=excluded.source,
                source_page=excluded.source_page,
                rules_version=excluded.rules_version,
                spell_level=excluded.spell_level,
                school=excluded.school,
                casting_time=excluded.casting_time,
                range_text=excluded.range_text,
                components=excluded.components,
                material_component_text=excluded.material_component_text,
                duration=excluded.duration,
                concentration=excluded.concentration,
                ritual=excluded.ritual,
                attack_type=excluded.attack_type,
                save_ability=excluded.save_ability,
                damage_type=excluded.damage_type,
                healing_type=excluded.healing_type,
                base_effect_text=excluded.base_effect_text,
                base_damage_formula=excluded.base_damage_formula,
                higher_level_text=excluded.higher_level_text,
                scaling_type=excluded.scaling_type,
                scaling_data=excluded.scaling_data,
                targeting_data=excluded.targeting_data,
                area_data=excluded.area_data,
                tags=excluded.tags,
                class_lists=excluded.class_lists,
                subclass_lists=excluded.subclass_lists,
                granted_by_feat=excluded.granted_by_feat,
                granted_by_species=excluded.granted_by_species,
                granted_by_item=excluded.granted_by_item,
                updated_by=excluded.updated_by,
                updated_at=excluded.updated_at
            """,
            rec,
        )
        conn.commit()
    return get_custom_spell(session_id, rec["id"])


def get_custom_spell(session_id: str, spell_id: str) -> Dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM rules_custom_spells WHERE session_id=? AND id=?", (session_id, spell_id)).fetchone()
    return _deserialize_spell(row) if row else None


def delete_custom_spell(session_id: str, spell_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM rules_custom_spells WHERE session_id=? AND id=?", (session_id, spell_id))
        conn.commit()


def upsert_review_queue(session_id: str, user_id: str, character_name: str, review_items: List[Dict[str, Any]]) -> None:
    now = time.time()
    with get_conn() as conn:
        for item in review_items or []:
            review_id = f"review_{session_id}_{normalize_name(item.get('name'))}"
            conn.execute(
                """
                INSERT INTO rules_match_review (
                    id,session_id,user_id,character_name,content_type,original_name,normalized_name,status,match_score,
                    suggested_rule_id,suggested_name,source_tag,imported_payload,reviewed,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    user_id=excluded.user_id,
                    character_name=excluded.character_name,
                    status=excluded.status,
                    match_score=excluded.match_score,
                    suggested_rule_id=excluded.suggested_rule_id,
                    suggested_name=excluded.suggested_name,
                    source_tag=excluded.source_tag,
                    imported_payload=excluded.imported_payload,
                    updated_at=excluded.updated_at
                """,
                (
                    review_id, session_id, user_id, character_name, "spell", item.get("name"), normalize_name(item.get("name")),
                    item.get("status") or "unmatched", float(item.get("match_score") or 0), item.get("suggested_rule_id") or "",
                    item.get("suggested_name") or "", item.get("source_tag") or "imported", _json_dumps(item), 0, now, now,
                ),
            )
        conn.commit()


def list_review_queue(session_id: str) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM rules_match_review WHERE session_id=? ORDER BY updated_at DESC, original_name", (session_id,)).fetchall()
    return [dict(row) | {"imported_payload": _json_loads(row["imported_payload"], {})} for row in rows]


# ─────────────────────────────────────────────
# SPELL LIBRARY
# ─────────────────────────────────────────────

def get_spell_library(session_id: str) -> List[Dict[str, Any]]:
    """Return all SRD spells merged with campaign custom spells."""
    official = get_official_spells()
    for s in official:
        s["spell_source"] = "srd"
    custom = get_custom_spells(session_id)
    for s in custom:
        s["spell_source"] = "custom"
    return official + custom


def get_spell_by_id(spell_id: str) -> Dict[str, Any] | None:
    """Fetch a single SRD spell by id."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM rules_spells WHERE id=?", (spell_id,)).fetchone()
    if row:
        d = _deserialize_spell(row)
        d["spell_source"] = "srd"
        return d
    return None


def lookup_spell_id_by_normalized_name(normalized_name: str) -> str | None:
    """Return the canonical spell id whose normalized_name matches, or None.

    Used as a fallback during spell ID reconciliation when an exact id lookup
    fails (e.g. the stored id is a human-readable name rather than a slug).
    """
    if not normalized_name:
        return None
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM rules_spells WHERE normalized_name = ? LIMIT 1",
            (normalized_name,),
        ).fetchone()
    if row:
        return str(row["id"])
    return None


# ─────────────────────────────────────────────
# PLAYER GRANTED SPELLS
# ─────────────────────────────────────────────

def grant_spell(session_id: str, recipient_user_id: str, spell_id: str,
                spell_source: str, granter_user_id: str) -> Dict[str, Any]:
    """Grant a spell to a player. Returns the grant record."""
    grant_id = f"grant_{uuid.uuid4().hex[:12]}"
    now = time.time()
    spell_source = spell_source if spell_source in ("srd", "custom") else "srd"
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO player_granted_spells
                (id, campaign_id, recipient_user_id, spell_id, spell_source, granted_by_user_id, granted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (grant_id, session_id, recipient_user_id, spell_id, spell_source, granter_user_id, now),
        )
        conn.commit()
    return {
        "id": grant_id,
        "campaign_id": session_id,
        "recipient_user_id": recipient_user_id,
        "spell_id": spell_id,
        "spell_source": spell_source,
        "granted_by_user_id": granter_user_id,
        "granted_at": now,
    }


def get_granted_spells_for_user(session_id: str, user_id: str) -> List[Dict[str, Any]]:
    """Return grant records for a specific player in this session."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM player_granted_spells WHERE campaign_id=? AND recipient_user_id=? ORDER BY granted_at",
            (session_id, user_id),
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_granted_spells(session_id: str) -> List[Dict[str, Any]]:
    """Return all grant records for the session (DM view)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM player_granted_spells WHERE campaign_id=? ORDER BY granted_at",
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_granted_spell_library_for_user(session_id: str, user_id: str) -> List[Dict[str, Any]]:
    """Return only the full spell records granted to a specific player."""
    grants = get_granted_spells_for_user(session_id, user_id)
    spells: List[Dict[str, Any]] = []
    for grant in grants:
        source = str(grant.get("spell_source") or "srd").strip().lower()
        spell_id = str(grant.get("spell_id") or "").strip()
        if not spell_id:
            continue
        spell = get_custom_spell(session_id, spell_id) if source == "custom" else get_spell_by_id(spell_id)
        if not spell:
            continue
        spell = dict(spell)
        spell["spell_source"] = source
        spell["grant_id"] = grant.get("id")
        spell["granted_by_user_id"] = grant.get("granted_by_user_id")
        spell["granted_at"] = grant.get("granted_at")
        spells.append(spell)
    return spells


def revoke_granted_spell(grant_id: str, session_id: str) -> str | None:
    """Delete a grant and return the recipient_user_id, or None if not found."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT recipient_user_id FROM player_granted_spells WHERE id=? AND campaign_id=?",
            (grant_id, session_id),
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM player_granted_spells WHERE id=? AND campaign_id=?", (grant_id, session_id))
        conn.commit()
    return row["recipient_user_id"]


# ─── Loot / Treasure tables ────────────────────────────────────────────────────

def init_loot_db() -> None:
    """Create loot-related tables and seed them on first run."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS magic_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                rarity TEXT NOT NULL DEFAULT 'common',
                item_type TEXT NOT NULL DEFAULT 'wondrous',
                attunement_required INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT '',
                effect TEXT NOT NULL DEFAULT '',
                unidentified_description TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS treasure_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cr_range_min INTEGER NOT NULL,
                cr_range_max INTEGER NOT NULL,
                roll_d100_min INTEGER NOT NULL,
                roll_d100_max INTEGER NOT NULL,
                table_type TEXT NOT NULL DEFAULT 'individual',
                item_type TEXT NOT NULL DEFAULT 'coin',
                item_id TEXT,
                quantity_dice INTEGER NOT NULL DEFAULT 1,
                quantity_sides INTEGER NOT NULL DEFAULT 6,
                quantity_modifier INTEGER NOT NULL DEFAULT 0,
                coin_type TEXT NOT NULL DEFAULT 'gp'
            );

            CREATE TABLE IF NOT EXISTS party_treasury (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL UNIQUE,
                gold INTEGER NOT NULL DEFAULT 0,
                silver INTEGER NOT NULL DEFAULT 0,
                copper INTEGER NOT NULL DEFAULT 0,
                gems TEXT NOT NULL DEFAULT '[]',
                art_objects TEXT NOT NULL DEFAULT '[]',
                updated_at REAL NOT NULL DEFAULT 0
            );
            """
        )
        conn.commit()
    seed_magic_items()
    seed_treasure_tables()
    init_srd_items_table()


# ── SRD magic items (common / uncommon) ────────────────────────────────────────
_SRD_MAGIC_ITEMS: List[Dict[str, Any]] = [
    # Potions
    {"id": "mi_potion_healing",       "name": "Potion of Healing",        "rarity": "common",   "item_type": "potion",   "attunement_required": 0, "description": "A vial of red liquid that glimmers when agitated.", "effect": "Regain 2d4+2 hit points when you drink this potion.", "unidentified_description": "A small vial of red liquid that seems to shimmer with an inner warmth."},
    {"id": "mi_potion_greater_heal",  "name": "Potion of Greater Healing", "rarity": "uncommon","item_type": "potion",   "attunement_required": 0, "description": "A vial of red liquid, more vibrant than a standard healing potion.", "effect": "Regain 4d4+4 hit points when you drink this potion.", "unidentified_description": "A vial of deep crimson liquid that pulses faintly with life."},
    {"id": "mi_potion_superior_heal", "name": "Potion of Superior Healing","rarity": "rare",    "item_type": "potion",   "attunement_required": 0, "description": "A vial of brilliant red liquid.", "effect": "Regain 8d4+8 hit points when you drink this potion.", "unidentified_description": "A dazzling ruby-red vial that hums softly when held."},
    {"id": "mi_potion_climbing",      "name": "Potion of Climbing",        "rarity": "common",  "item_type": "potion",   "attunement_required": 0, "description": "A yellowish-brown liquid with flecks of mica.", "effect": "Gain a climbing speed equal to your walking speed for 1 hour.", "unidentified_description": "A murky yellowish liquid with tiny metallic flakes floating within."},
    {"id": "mi_potion_water_breath",  "name": "Potion of Water Breathing", "rarity": "uncommon","item_type": "potion",   "attunement_required": 0, "description": "A murky blue-green liquid.", "effect": "Breathe underwater for 1 hour after drinking.", "unidentified_description": "A swirling blue-green liquid with tiny bubbles that never quite reach the surface."},
    {"id": "mi_potion_fire_resistance","name":"Potion of Fire Resistance", "rarity": "uncommon","item_type": "potion",   "attunement_required": 0, "description": "A red-orange vial of potion.", "effect": "Resistance to fire damage for 1 hour.", "unidentified_description": "A vial of swirling orange liquid that feels warm to the touch."},
    {"id": "mi_potion_invisibility",  "name": "Potion of Invisibility",    "rarity": "very rare","item_type": "potion",  "attunement_required": 0, "description": "A clear liquid that looks like water.", "effect": "Become invisible for 1 hour or until you attack or cast a spell.", "unidentified_description": "A perfectly clear liquid that seems to distort light strangely."},
    {"id": "mi_potion_speed",         "name": "Potion of Speed",           "rarity": "very rare","item_type": "potion",  "attunement_required": 0, "description": "A bright yellow liquid with a faint sweet smell.", "effect": "Haste effect for 1 minute.", "unidentified_description": "A yellow liquid that almost seems to vibrate in its vial."},
    {"id": "mi_potion_mind_reading",  "name": "Potion of Mind Reading",    "rarity": "rare",    "item_type": "potion",   "attunement_required": 0, "description": "A pale lavender liquid with ghostly wisps.", "effect": "Cast detect thoughts (save DC 13) for 1 minute.", "unidentified_description": "A misty purple liquid with faint ghostly shapes swirling inside."},
    # Scrolls
    {"id": "mi_scroll_protection",    "name": "Scroll of Protection",      "rarity": "rare",    "item_type": "scroll",   "attunement_required": 0, "description": "A roll of parchment with a protective ward inscribed.", "effect": "As an action, read to create a 5-foot radius barrier against one creature type for 5 minutes.", "unidentified_description": "A rolled parchment covered in dense, glowing script that fades if you stare too long."},
    {"id": "mi_spell_scroll_1",       "name": "Spell Scroll (1st Level)",  "rarity": "common",  "item_type": "scroll",   "attunement_required": 0, "description": "A scroll containing a 1st-level spell.", "effect": "Cast the inscribed 1st-level spell without spending a spell slot.", "unidentified_description": "A parchment roll faintly glowing with magical ink."},
    {"id": "mi_spell_scroll_2",       "name": "Spell Scroll (2nd Level)",  "rarity": "uncommon","item_type": "scroll",   "attunement_required": 0, "description": "A scroll containing a 2nd-level spell.", "effect": "Cast the inscribed 2nd-level spell without spending a spell slot.", "unidentified_description": "A more ornate scroll roll, the ink shifting slightly in dim light."},
    {"id": "mi_spell_scroll_3",       "name": "Spell Scroll (3rd Level)",  "rarity": "uncommon","item_type": "scroll",   "attunement_required": 0, "description": "A scroll containing a 3rd-level spell.", "effect": "Cast the inscribed 3rd-level spell without spending a spell slot.", "unidentified_description": "A finely made scroll; tiny symbols dance along its edges."},
    {"id": "mi_spell_scroll_4",       "name": "Spell Scroll (4th Level)",  "rarity": "rare",    "item_type": "scroll",   "attunement_required": 0, "description": "A scroll containing a 4th-level spell.", "effect": "Cast the inscribed 4th-level spell without spending a spell slot.", "unidentified_description": "A silver-threaded scroll with a steady magical pulse."},
    {"id": "mi_spell_scroll_5",       "name": "Spell Scroll (5th Level)",  "rarity": "rare",    "item_type": "scroll",   "attunement_required": 0, "description": "A scroll containing a 5th-level spell.", "effect": "Cast the inscribed 5th-level spell without spending a spell slot.", "unidentified_description": "Dense glyphs crawl slowly across this heavy vellum scroll."},
    {"id": "mi_spell_scroll_6",       "name": "Spell Scroll (6th Level)",  "rarity": "very rare","item_type": "scroll", "attunement_required": 0, "description": "A scroll containing a 6th-level spell.", "effect": "Cast the inscribed 6th-level spell without spending a spell slot.", "unidentified_description": "Arcane script burns faintly blue at the edges."},
    {"id": "mi_spell_scroll_7",       "name": "Spell Scroll (7th Level)",  "rarity": "very rare","item_type": "scroll", "attunement_required": 0, "description": "A scroll containing a 7th-level spell.", "effect": "Cast the inscribed 7th-level spell without spending a spell slot.", "unidentified_description": "A solemn black scroll sealed with starlit wax."},
    {"id": "mi_spell_scroll_8",       "name": "Spell Scroll (8th Level)",  "rarity": "very rare","item_type": "scroll", "attunement_required": 0, "description": "A scroll containing an 8th-level spell.", "effect": "Cast the inscribed 8th-level spell without spending a spell slot.", "unidentified_description": "The parchment crackles with restrained power when unrolled."},
    {"id": "mi_spell_scroll_9",       "name": "Spell Scroll (9th Level)",  "rarity": "legendary","item_type": "scroll", "attunement_required": 0, "description": "A scroll containing a 9th-level spell.", "effect": "Cast the inscribed 9th-level spell without spending a spell slot.", "unidentified_description": "A legendary script whose runes seem to look back at you."},
    {"id": "mi_scroll_warding_tides", "name": "Scroll of Warding Tides",   "rarity": "uncommon","item_type": "scroll",   "attunement_required": 0, "description": "A sea-salt treated scroll used by mariners in monster waters.", "effect": "As an action, gain resistance to cold and lightning damage for 10 minutes.", "unidentified_description": "A damp-proof scroll braided with blue twine and shell dust."},
    {"id": "mi_scroll_safe_harbor",   "name": "Scroll of Safe Harbor",     "rarity": "rare",    "item_type": "scroll",   "attunement_required": 0, "description": "A navigator's ward script copied from old lighthouse vaults.", "effect": "As an action, conjure a calm 20-foot weather bubble centered on you for 10 minutes.", "unidentified_description": "This chart-like scroll carries tiny compass roses and ward glyphs."},
    {"id": "mi_scroll_warding_circle","name": "Scroll of Warding Circle",  "rarity": "rare",    "item_type": "scroll",   "attunement_required": 0, "description": "A ritual scroll for field sanctums and camp defense.", "effect": "As an action, inscribe a 10-foot circle that grants advantage on saves vs fear for 10 minutes.", "unidentified_description": "A precise ritual sheet with concentric sigils and anchor marks."},
    {"id": "mi_scroll_far_path",      "name": "Scroll of the Far Path",    "rarity": "very rare","item_type": "scroll",  "attunement_required": 0, "description": "A travel rite favored by scouts, outriders, and horizon mages.", "effect": "As an action, teleport up to 300 feet to an unoccupied space you can see.", "unidentified_description": "The ink on this long strip bends like a road over hills."},
    {"id": "mi_scroll_voltaic_malfunction", "name": "Scroll of Voltaic Malfunction", "rarity": "rare", "item_type": "scroll", "attunement_required": 0, "description": "A risky artificer schematic wrapped around brittle copper foil.", "effect": "As an action, unleash a 20-foot lightning line (6d6, Dex DC 14 half). On a natural 1, take 2d6 lightning damage.", "unidentified_description": "Copper-veined parchment that emits faint static when touched."},
    {"id": "mi_scroll_blackwake_last_order", "name": "Blackwake Admiral's Last Order", "rarity": "legendary", "item_type": "scroll", "attunement_required": 0, "description": "A named command scroll sealed by a drowned admiral's signet.", "effect": "As an action, summon spectral corsairs for 1 minute; once before fading, they unleash a devastating broadside in a 30-foot cone.", "unidentified_description": "Salt-stained vellum carrying a seal shaped like a broken compass."},
    # Rings
    {"id": "mi_ring_protection",      "name": "Ring of Protection",        "rarity": "uncommon","item_type": "ring",     "attunement_required": 1, "description": "A plain silver ring engraved with small protective runes.", "effect": "+1 bonus to AC and saving throws while attuned.", "unidentified_description": "A plain silver ring etched with tiny, almost invisible symbols."},
    {"id": "mi_ring_swimming",        "name": "Ring of Swimming",          "rarity": "uncommon","item_type": "ring",     "attunement_required": 0, "description": "A ring shaped like a fish swallowing its tail.", "effect": "Gain a swimming speed of 40 feet while wearing this ring.", "unidentified_description": "A ring carved to resemble a serpentine fish biting its own tail."},
    {"id": "mi_ring_feather_falling", "name": "Ring of Feather Falling",   "rarity": "uncommon","item_type": "ring",     "attunement_required": 1, "description": "A silver ring with a small feather motif.", "effect": "When you fall while wearing this ring, you descend 60 feet per round and take no fall damage.", "unidentified_description": "A delicate silver ring with what appears to be a tiny feather etched into it."},
    {"id": "mi_ring_warmth",          "name": "Ring of Warmth",            "rarity": "uncommon","item_type": "ring",     "attunement_required": 1, "description": "A warm copper ring with a sun motif.", "effect": "Resistance to cold damage; comfortable in temperatures as low as −50°F.", "unidentified_description": "A copper-hued ring that always feels warm to the touch regardless of temperature."},
    {"id": "mi_ring_jumping",         "name": "Ring of Jumping",           "rarity": "uncommon","item_type": "ring",     "attunement_required": 1, "description": "A worn iron ring with tiny spring-like etchings.", "effect": "Triple your jumping distance while attuned.", "unidentified_description": "A plain iron ring with faint coil-like markings."},
    # Wands
    {"id": "mi_wand_magic_missiles",  "name": "Wand of Magic Missiles",    "rarity": "uncommon","item_type": "wand",     "attunement_required": 0, "description": "A plain wooden wand tipped with a silver point.", "effect": "Has 7 charges. Expend 1–3 charges to cast magic missile at 1st–3rd level. Regains 1d6+1 charges at dawn.", "unidentified_description": "A slim wooden wand with a silver tip that faintly crackles when waved."},
    {"id": "mi_wand_web",             "name": "Wand of Web",               "rarity": "uncommon","item_type": "wand",     "attunement_required": 1, "description": "A gnarled wooden wand with filaments carved along its length.", "effect": "7 charges; cast web (save DC 15) by expending 1 charge. Regains 1d6+1 charges at dawn.", "unidentified_description": "A gnarled wand with strange thread-like carvings spiraling around it."},
    {"id": "mi_wand_secrets",         "name": "Wand of Secrets",           "rarity": "uncommon","item_type": "wand",     "attunement_required": 0, "description": "A plain wand that pulses when near hidden doors or traps.", "effect": "3 charges; detect secret doors and traps within 30 feet. Regains 1d3 charges at dawn.", "unidentified_description": "A featureless wand that occasionally seems to twitch of its own accord."},
    {"id": "mi_wand_enemy_detection", "name": "Wand of Enemy Detection",   "rarity": "rare",    "item_type": "wand",     "attunement_required": 1, "description": "A blood-red wand with a pointed tip.", "effect": "7 charges; detect creatures hostile to you within 60 feet. Regains 1d6+1 charges at dawn.", "unidentified_description": "A deep crimson wand that feels oddly warm when you feel threatened."},
    {"id": "mi_wand_fireballs",       "name": "Wand of Fireballs",         "rarity": "rare",    "item_type": "wand",     "attunement_required": 1, "description": "A carved bone wand tipped with a red gem.", "effect": "7 charges; cast fireball (save DC 15) by expending 1–3 charges. Regains 1d6+1 charges at dawn.", "unidentified_description": "A pale wand topped with a deep red gemstone that faintly radiates warmth."},
    {"id": "mi_wand_lightning_bolt",  "name": "Wand of Lightning Bolts",   "rarity": "rare",    "item_type": "wand",     "attunement_required": 1, "description": "A carved crystal wand that crackles faintly.", "effect": "7 charges; cast lightning bolt (save DC 15) by expending 1–3 charges. Regains 1d6+1 charges at dawn.", "unidentified_description": "A crystalline wand that leaves a tingle in your fingertips when gripped."},
    # Armour & Shields
    {"id": "mi_armor_1",              "name": "+1 Armor",                  "rarity": "uncommon","item_type": "armor",    "attunement_required": 0, "description": "A suit of armor with minor magical enhancement.", "effect": "+1 bonus to AC in addition to the armor's normal bonus.", "unidentified_description": "A suit of armor that catches the light oddly, as if slightly more solid than normal."},
    {"id": "mi_armor_2",              "name": "+2 Armor",                  "rarity": "rare",    "item_type": "armor",    "attunement_required": 0, "description": "A well-crafted suit of armor humming with protective magic.", "effect": "+2 bonus to AC in addition to the armor's normal bonus.", "unidentified_description": "A finely made suit of armor that seems to repel dust and minor dents."},
    {"id": "mi_shield_1",             "name": "+1 Shield",                 "rarity": "uncommon","item_type": "armor",    "attunement_required": 0, "description": "A shield with a faint rune etched inside.", "effect": "+1 bonus to AC in addition to the shield's normal bonus.", "unidentified_description": "A shield with a barely visible marking inside the grip."},
    {"id": "mi_shield_2",             "name": "+2 Shield",                 "rarity": "rare",    "item_type": "armor",    "attunement_required": 0, "description": "A shield that deflects blows more readily than mundane ones.", "effect": "+2 bonus to AC in addition to the shield's normal bonus.", "unidentified_description": "A shield that feels strangely light yet sturdy."},
    # Weapons
    {"id": "mi_weapon_1",             "name": "+1 Weapon",                 "rarity": "uncommon","item_type": "weapon",   "attunement_required": 0, "description": "A weapon with a slight magical edge.", "effect": "+1 bonus to attack and damage rolls made with this weapon.", "unidentified_description": "A weapon that seems slightly sharper and better balanced than a mundane version."},
    {"id": "mi_weapon_2",             "name": "+2 Weapon",                 "rarity": "rare",    "item_type": "weapon",   "attunement_required": 0, "description": "A weapon crackling with subtle enchantment.", "effect": "+2 bonus to attack and damage rolls made with this weapon.", "unidentified_description": "A weapon that hums faintly when swung in the air."},
    {"id": "mi_weapon_3",             "name": "+3 Weapon",                 "rarity": "very rare","item_type": "weapon",  "attunement_required": 0, "description": "A weapon blazing with obvious magical power.", "effect": "+3 bonus to attack and damage rolls made with this weapon.", "unidentified_description": "A weapon surrounded by a barely-visible shimmer even in daylight."},
    {"id": "mi_flametongue",          "name": "Flame Tongue",              "rarity": "rare",    "item_type": "weapon",   "attunement_required": 1, "description": "A sword that bursts into flame when commanded.", "effect": "Speak the command word as a bonus action to ignite; deals an extra 2d6 fire damage on a hit.", "unidentified_description": "A sword with runes near the hilt that feel warm to the touch."},
    {"id": "mi_frost_brand",          "name": "Frost Brand",               "rarity": "very rare","item_type": "weapon",  "attunement_required": 1, "description": "A sword sheathed in a thin layer of frost.", "effect": "Extra 1d6 cold damage on a hit; resistance to fire; extinguishes nonmagical flames within 30 ft when drawn.", "unidentified_description": "A blade that leaves a faint trace of frost wherever it passes."},
    {"id": "mi_sun_blade",            "name": "Sun Blade",                 "rarity": "rare",    "item_type": "weapon",   "attunement_required": 1, "description": "A hilt that conjures a blade of sunlight.", "effect": "+2 to attacks and damage; deals radiant damage; acts as sunlight within 15 feet.", "unidentified_description": "A hilt with no blade, inscribed with a stylised sun on the pommel."},
    {"id": "mi_vorpal_sword",         "name": "Vorpal Sword",              "rarity": "legendary","item_type": "weapon",  "attunement_required": 1, "description": "A keenly honed sword of supernatural sharpness.", "effect": "+3 to attacks and damage; on a natural 20 severs the target's head (if it has one).", "unidentified_description": "An impossibly sharp blade that seems to cut the very air it passes through."},
    # Wondrous items
    {"id": "mi_bag_of_holding",       "name": "Bag of Holding",            "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A cloth bag that is bigger on the inside than the outside.", "effect": "Holds up to 500 lbs / 64 cubic feet. Weighs 15 lbs regardless of contents.", "unidentified_description": "A plain-looking bag that feels oddly light even when full."},
    {"id": "mi_boots_speed",          "name": "Boots of Speed",            "rarity": "rare",    "item_type": "wondrous", "attunement_required": 1, "description": "Supple leather boots with small wings on the ankle.", "effect": "Bonus action to activate; double walking speed and opportunity attacks have disadvantage against you for 10 minutes.", "unidentified_description": "Finely crafted boots with tiny decorative wings on each ankle."},
    {"id": "mi_boots_elvenkind",      "name": "Boots of Elvenkind",        "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "Soft green boots that muffle footsteps.", "effect": "Your steps make no sound; advantage on Dexterity (Stealth) checks involving moving quietly.", "unidentified_description": "Supple green leather boots that feel unnaturally light."},
    {"id": "mi_boots_striding",       "name": "Boots of Striding and Springing","rarity":"uncommon","item_type":"wondrous","attunement_required":1,"description":"Sturdy boots with spring-steel soles.","effect":"Walking speed of at least 30 ft; jump three times the normal distance.","unidentified_description":"Heavy boots with an odd springiness to the soles."},
    {"id": "mi_cloak_protection",     "name": "Cloak of Protection",       "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "A plain dark cloak stitched with golden thread.", "effect": "+1 bonus to AC and saving throws while attuned.", "unidentified_description": "A dark, finely woven cloak that feels subtly reassuring when worn."},
    {"id": "mi_cloak_elvenkind",      "name": "Cloak of Elvenkind",        "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "A mottled grey-green cloak that seems to shift colour.", "effect": "Advantage on Dexterity (Stealth) checks; disadvantage on Perception checks that rely on sight against you.", "unidentified_description": "A strange mottled cloak that makes colours seem to blur around the wearer."},
    {"id": "mi_cloak_displacement",   "name": "Cloak of Displacement",     "rarity": "rare",    "item_type": "wondrous", "attunement_required": 1, "description": "A cloak that projects a displaced illusory image of the wearer.", "effect": "Attackers have disadvantage on attack rolls against you; effect ends after an attack hits.", "unidentified_description": "A shimmer seems to surround whoever wears this heavy travelling cloak."},
    {"id": "mi_gauntlets_ogre",       "name": "Gauntlets of Ogre Power",   "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "Iron gauntlets that grant great strength.", "effect": "Strength score becomes 19 while wearing these gauntlets.", "unidentified_description": "Heavy iron gauntlets that feel strangely comfortable despite their bulk."},
    {"id": "mi_headband_intellect",   "name": "Headband of Intellect",     "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "A plain headband that sharpens the mind.", "effect": "Intelligence score becomes 19 while wearing this headband.", "unidentified_description": "A plain metal headband with a smooth gemstone at the centre."},
    {"id": "mi_amulet_hp",            "name": "Amulet of Health",          "rarity": "rare",    "item_type": "wondrous", "attunement_required": 1, "description": "A polished red amulet.", "effect": "Constitution score becomes 19 while attuned.", "unidentified_description": "A smooth red amulet that pulses faintly, almost like a heartbeat."},
    {"id": "mi_hat_disguise",         "name": "Hat of Disguise",           "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "A wide-brimmed hat with illusion magic woven in.", "effect": "Cast disguise self at will while wearing and attuned to this hat.", "unidentified_description": "An ordinary-looking hat with a faint shimmer visible only from the corner of the eye."},
    {"id": "mi_helm_telepathy",       "name": "Helm of Telepathy",         "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "A plain iron helm engraved with a stylised eye.", "effect": "Cast detect thoughts (save DC 13) at will while wearing this helm.", "unidentified_description": "A simple helm with an eye-like symbol that seems to watch you."},
    {"id": "mi_rope_entanglement",    "name": "Rope of Entanglement",      "rarity": "rare",    "item_type": "wondrous", "attunement_required": 0, "description": "A coil of silken rope that moves on command.", "effect": "Command as a bonus action; the rope attempts to restrain a creature within 20 ft (Str/Dex DC 15).", "unidentified_description": "A coil of unnaturally smooth rope that occasionally seems to flex on its own."},
    {"id": "mi_necklace_fireballs",   "name": "Necklace of Fireballs",     "rarity": "rare",    "item_type": "wondrous", "attunement_required": 0, "description": "A string of beads, each bead a fireball.", "effect": "Throw beads as actions; each creates a 3d6 fireball (Dex DC 15). More powerful beads do more damage.", "unidentified_description": "A necklace strung with small, oddly warm glass beads."},
    {"id": "mi_pearl_power",          "name": "Pearl of Power",            "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "A lustrous pearl with a faint aura.", "effect": "As an action, regain one expended spell slot of 3rd level or lower.", "unidentified_description": "A perfectly smooth pearl with an inner glow visible only in darkness."},
    {"id": "mi_periapt_wound_closure","name": "Periapt of Wound Closure",  "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "A golden disc pendant with healing runes.", "effect": "Stabilise automatically when dying; double the dice healing when spending hit dice.", "unidentified_description": "A golden disc pendant engraved with interlocking circular patterns."},
    {"id": "mi_stone_good_luck",      "name": "Stone of Good Luck",        "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "A smooth agate inscribed with a rune of fortune.", "effect": "+1 to ability checks and saving throws while attuned.", "unidentified_description": "A smooth, warm agate stone with a barely visible etching."},
    {"id": "mi_winged_boots",         "name": "Winged Boots",              "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "Leather boots with small wings that unfold.", "effect": "Flying speed equal to walking speed for up to 4 hours (split into increments).", "unidentified_description": "Boots with tiny folded wing motifs that seem to flutter in a breeze."},
    {"id": "mi_gloves_missile_snare", "name": "Gloves of Missile Snaring","rarity": "uncommon","item_type": "wondrous",  "attunement_required": 1, "description": "Leather gloves stitched with catching runes.", "effect": "Reaction to reduce ranged weapon attack by 1d10 + Dexterity modifier.", "unidentified_description": "Supple leather gloves with faint stitched symbols on the palms."},
    {"id": "mi_eyes_minute_seeing",   "name": "Eyes of Minute Seeing",     "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "Crystal lenses that clip onto the eyes.", "effect": "Advantage on Investigation checks involving something within 1 foot; see objects as small as 1 mm.", "unidentified_description": "Oddly thick crystal lenses on a fine wire frame."},
    {"id": "mi_goggles_night",        "name": "Goggles of Night",          "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "Dark lens goggles infused with shadow magic.", "effect": "Darkvision out to 60 feet; if you already have darkvision, it extends by 60 feet.", "unidentified_description": "Dark tinted goggles that make everything appear strangely clear in dim light."},
    {"id": "mi_brooch_shielding",     "name": "Brooch of Shielding",       "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "A decorative brooch that deflects magic missiles.", "effect": "Immunity to damage from the magic missile spell.", "unidentified_description": "A decorative brooch that occasionally seems to emit a barely audible hum."},
    {"id": "mi_decanter_water",       "name": "Decanter of Endless Water", "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "An ornate flask with a sealed stopper.", "effect": "Produces fresh water in three modes: stream (1 gal), fountain (5 gal), geyser (30 gal, 5 ft wide).", "unidentified_description": "A sealed ornate flask that sloshes with liquid even when apparently empty."},
    {"id": "mi_immovable_rod",        "name": "Immovable Rod",             "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A flat iron rod with a toggle button.", "effect": "Press the button; the rod becomes fixed in space, bearing up to 8,000 lbs.", "unidentified_description": "A plain flat iron rod with a small toggle on one end."},
    {"id": "mi_folding_boat",         "name": "Folding Boat",              "rarity": "rare",    "item_type": "wondrous", "attunement_required": 0, "description": "A small wooden box that unfolds into a boat.", "effect": "Speak one of three command words to transform into a rowboat, sailboat, or back to a box.", "unidentified_description": "A polished wooden box with intricate dove-tailed joints and a tiny inlaid anchor."},
    {"id": "mi_sending_stones",       "name": "Sending Stones",            "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A matched pair of polished stones.", "effect": "Use as an action to cast sending to the holder of the paired stone (once per day each).", "unidentified_description": "Two smooth grey stones that always feel faintly warm to the touch."},
    {"id": "mi_lantern_revealing",    "name": "Lantern of Revealing",      "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A brass lantern with blue-tinted flame.", "effect": "Illuminates invisible creatures; reveals creatures and objects in a 30-foot cone.", "unidentified_description": "A brass lantern whose flame burns an unusual pale blue."},
    {"id": "mi_alchemy_jug",          "name": "Alchemy Jug",               "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A ceramic jug that produces various liquids.", "effect": "Each day the jug can produce one of several liquids (water, beer, acid, oil, honey, wine, etc.).", "unidentified_description": "A plain ceramic jug that sloshes with liquid you didn't pour in."},
    {"id": "mi_bag_tricks_grey",      "name": "Bag of Tricks (Grey)",      "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A grey pouch with a star pattern sewn inside.", "effect": "Pull a fluffy object; throw it up to 20 ft and it transforms into a random beast (weasel–brown bear).", "unidentified_description": "A small grey pouch that contains what feels like a ball of fluff."},
    {"id": "mi_bag_tricks_rust",      "name": "Bag of Tricks (Rust)",      "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A rust-coloured pouch with animal prints sewn inside.", "effect": "Pull a fluffy object; throw it up to 20 ft and it transforms into a random beast (rat–giant elk).", "unidentified_description": "A rust-coloured pouch that makes faint shuffling noises when jostled."},
    {"id": "mi_broom_flying",         "name": "Broom of Flying",           "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A mundane-looking broom that flies.", "effect": "Speak the command word to hover; fly at 50 ft speed carrying up to 400 lbs.", "unidentified_description": "An old-fashioned straw broom that leaves no debris on a clean floor."},
    {"id": "mi_carpet_flying",        "name": "Carpet of Flying",          "rarity": "very rare","item_type": "wondrous","attunement_required": 0, "description": "A large, ornately patterned carpet.", "effect": "Speak the command word; flies at 80 ft, carrying up to 800 lbs.", "unidentified_description": "A beautifully patterned carpet that always seems free of wrinkles no matter how it's folded."},
    {"id": "mi_chime_opening",        "name": "Chime of Opening",          "rarity": "rare",    "item_type": "wondrous", "attunement_required": 0, "description": "A hollow mithril tube that opens locks.", "effect": "Strike and point at a door, chest, or similar object within 120 ft; the object opens (10 uses).", "unidentified_description": "A small hollow metallic tube that makes a clear tone when tapped."},
    {"id": "mi_cube_force",           "name": "Cube of Force",             "rarity": "rare",    "item_type": "wondrous", "attunement_required": 1, "description": "A small cube with different symbols on each face.", "effect": "Activate a face to create a 15-foot force cube barrier with different properties.", "unidentified_description": "A perfectly symmetrical small cube with a different symbol carved into each face."},
    {"id": "mi_eversmoking_bottle",   "name": "Eversmoking Bottle",        "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A brass bottle stoppered with lead.", "effect": "Pull the stopper; produces a cloud of smoke that heavily obscures a 60-foot radius.", "unidentified_description": "A heavy brass bottle with a lead stopper that seems to vibrate slightly."},
    {"id": "mi_eyes_charming",        "name": "Eyes of Charming",          "rarity": "uncommon","item_type": "wondrous", "attunement_required": 1, "description": "Crystal lenses tinted with pink magic.", "effect": "3 charges; cast charm person (Wis DC 13). Regains 1d3 charges at dawn.", "unidentified_description": "Rosy-tinted crystal lenses on an elegant wire frame."},
    {"id": "mi_figurine_golden_lions","name": "Figurine of Wondrous Power (Golden Lions)", "rarity": "rare", "item_type": "wondrous", "attunement_required": 0, "description": "Two tiny gold lions figurines.", "effect": "Speak the command word to transform each into a lion for up to 1 hour. Recharges after 7 days.", "unidentified_description": "Two beautifully detailed miniature golden lion figurines."},
    {"id": "mi_gem_brightness",       "name": "Gem of Brightness",         "rarity": "uncommon","item_type": "wondrous", "attunement_required": 0, "description": "A clear prism holding 50 charges of light.", "effect": "Expend charges to shed bright light in radii of 30, 60, or 300 feet (blinding creatures).", "unidentified_description": "A perfectly cut clear prism that refracts light in unusual patterns."},
    {"id": "mi_horseshoes_speed",     "name": "Horseshoes of Speed",       "rarity": "rare",    "item_type": "wondrous", "attunement_required": 0, "description": "Iron horseshoes with rune engravings.", "effect": "Horse wearing all four gains +30 ft to walking speed.", "unidentified_description": "Iron horseshoes with faint etched runes that glow faintly when trotted on stone."},
    {"id": "mi_instrument_bard",      "name": "Instrument of the Bards (Doss Lute)", "rarity": "uncommon", "item_type": "wondrous", "attunement_required": 1, "description": "A finely crafted lute that hums with power.", "effect": "Cast fly, invisibility, levitate, or protection from evil and good once each per dawn.", "unidentified_description": "A beautifully crafted lute whose strings never seem to go out of tune."},
    {"id": "mi_ioun_stone_reserve",   "name": "Ioun Stone (Reserve)",      "rarity": "rare",    "item_type": "wondrous", "attunement_required": 1, "description": "A vibrant purple prism that orbits your head.", "effect": "Store a spell of up to 3rd level; the stone casts the spell when you have no spell slots remaining.", "unidentified_description": "A faceted purple stone that floats with an almost imperceptible movement."},
    {"id": "mi_manual_golems",        "name": "Manual of Golems",          "rarity": "very rare","item_type": "wondrous","attunement_required": 0, "description": "A tome with instructions for creating a golem.", "effect": "Contains detailed instructions and formulae for constructing one type of golem.", "unidentified_description": "A dense tome written in a cramped, nearly illegible hand with strange diagrams."},
    {"id": "mi_mirror_life_trapping", "name": "Mirror of Life Trapping",   "rarity": "very rare","item_type": "wondrous","attunement_required": 0, "description": "A full-length silver-framed mirror.", "effect": "Creatures that look into its surface while within 5 ft may be trapped in one of 12 extradimensional cells.", "unidentified_description": "An elegant framed mirror with an oddly deep reflection."},
    # ── New Potions ─────────────────────────────────────────────────────────────
    {"id": "mi_potion_supreme_heal",        "name": "Potion of Supreme Healing",        "rarity": "very rare", "item_type": "potion", "attunement_required": 0, "description": "A radiant crimson liquid brimming with vitality.", "effect": "Drink to regain 10d4+20 HP. Takes an action.", "unidentified_description": "A vial of intensely glowing red liquid."},
    {"id": "mi_potion_animal_friendship",   "name": "Potion of Animal Friendship",      "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "A murky liquid with bits of fur floating inside.", "effect": "Drink to cast Animal Friendship (DC 13) for 1 hour.", "unidentified_description": "A murky green-brown liquid with tiny floating specks."},
    {"id": "mi_potion_flying",              "name": "Potion of Flying",                 "rarity": "very rare", "item_type": "potion", "attunement_required": 0, "description": "A clear liquid with wisps of cloud swirling within.", "effect": "Drink to gain a flying speed of 60 ft for 1 hour.", "unidentified_description": "A clear potion with misty white swirls inside."},
    {"id": "mi_potion_heroism",             "name": "Potion of Heroism",                "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "A sparkling golden liquid.", "effect": "Drink to gain 10 temporary HP and the Blessed condition for 1 hour.", "unidentified_description": "A bright gold liquid that sparkles in any light."},
    {"id": "mi_potion_poison",              "name": "Potion of Poison",                 "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "Appears identical to a healing potion.", "effect": "Appears as a healing potion. On drink: 3d6 poison damage, DC 13 Con or poisoned 24 hrs.", "unidentified_description": "A vial of red liquid that looks exactly like a healing potion."},
    {"id": "mi_potion_giant_hill",          "name": "Potion of Giant Strength (Hill)",  "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "A thick brown liquid with a musky smell.", "effect": "Str becomes 21 for 1 hour.", "unidentified_description": "A thick brown liquid that smells of earth and sweat."},
    {"id": "mi_potion_giant_stone",         "name": "Potion of Giant Strength (Stone)", "rarity": "rare",      "item_type": "potion", "attunement_required": 0, "description": "A grey, gritty liquid that tastes of slate.", "effect": "Str becomes 23 for 1 hour.", "unidentified_description": "A grey liquid with fine sediment swirling within."},
    {"id": "mi_potion_giant_frost",         "name": "Potion of Giant Strength (Frost)", "rarity": "rare",      "item_type": "potion", "attunement_required": 0, "description": "A pale blue liquid that is cold to the touch.", "effect": "Str becomes 23 for 1 hour.", "unidentified_description": "A pale blue liquid that frosts its vial."},
    {"id": "mi_potion_giant_fire",          "name": "Potion of Giant Strength (Fire)",  "rarity": "rare",      "item_type": "potion", "attunement_required": 0, "description": "An orange liquid that radiates heat.", "effect": "Str becomes 25 for 1 hour.", "unidentified_description": "A warm orange liquid that feels hot through the glass."},
    {"id": "mi_potion_giant_cloud",         "name": "Potion of Giant Strength (Cloud)", "rarity": "very rare", "item_type": "potion", "attunement_required": 0, "description": "A swirling white liquid that seems lighter than air.", "effect": "Str becomes 27 for 1 hour.", "unidentified_description": "A milky white liquid with faint wisps of vapour."},
    {"id": "mi_potion_giant_storm",         "name": "Potion of Giant Strength (Storm)", "rarity": "legendary", "item_type": "potion", "attunement_required": 0, "description": "A crackling violet liquid with tiny sparks.", "effect": "Str becomes 29 for 1 hour.", "unidentified_description": "A dark violet liquid that sparks when the vial is shaken."},
    {"id": "mi_potion_resist_fire",         "name": "Potion of Resistance (Fire)",      "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "A warm red liquid that flickers faintly.", "effect": "Gain resistance to fire damage for 1 hour.", "unidentified_description": "A red liquid that feels warm to the touch."},
    {"id": "mi_potion_resist_cold",         "name": "Potion of Resistance (Cold)",      "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "A pale blue liquid that chills the vial.", "effect": "Gain resistance to cold damage for 1 hour.", "unidentified_description": "A pale blue liquid that frosts the outside of its container."},
    {"id": "mi_potion_resist_lightning",    "name": "Potion of Resistance (Lightning)", "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "A crackling yellow liquid.", "effect": "Gain resistance to lightning damage for 1 hour.", "unidentified_description": "A yellow liquid with tiny sparks inside."},
    {"id": "mi_potion_resist_acid",         "name": "Potion of Resistance (Acid)",      "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "A bubbling green liquid.", "effect": "Gain resistance to acid damage for 1 hour.", "unidentified_description": "A green liquid that fizzes gently."},
    {"id": "mi_potion_resist_poison",       "name": "Potion of Resistance (Poison)",    "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "A sickly purple liquid.", "effect": "Gain resistance to poison damage for 1 hour.", "unidentified_description": "A deep purple liquid with a faint bitter smell."},
    {"id": "mi_potion_resist_necrotic",     "name": "Potion of Resistance (Necrotic)",  "rarity": "uncommon",  "item_type": "potion", "attunement_required": 0, "description": "A dark liquid that seems to absorb light.", "effect": "Gain resistance to necrotic damage for 1 hour.", "unidentified_description": "A shadowy black liquid that dims nearby light."},
    # ── New Magic Weapons ───────────────────────────────────────────────────────
    {"id": "mi_weapon_1_dagger",      "name": "+1 Dagger",        "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A finely honed dagger with a magical edge.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A dagger that gleams unnaturally."},
    {"id": "mi_weapon_1_shortsword",  "name": "+1 Shortsword",    "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A shortsword with a subtle magical enhancement.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A shortsword that hums faintly when drawn."},
    {"id": "mi_weapon_1_longsword",   "name": "+1 Longsword",     "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A longsword with a faint magical glow.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A longsword that feels perfectly balanced."},
    {"id": "mi_weapon_1_greatsword",  "name": "+1 Greatsword",    "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A greatsword crackling with minor enchantment.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A large sword that seems lighter than it should be."},
    {"id": "mi_weapon_1_handaxe",     "name": "+1 Handaxe",       "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A handaxe with a keen magical edge.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A handaxe that never seems to dull."},
    {"id": "mi_weapon_1_battleaxe",   "name": "+1 Battleaxe",     "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A battleaxe enhanced with subtle magic.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A battleaxe with faint runes along the blade."},
    {"id": "mi_weapon_1_warhammer",   "name": "+1 Warhammer",     "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A warhammer with a magically reinforced head.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A warhammer that lands with unusual force."},
    {"id": "mi_weapon_1_rapier",      "name": "+1 Rapier",        "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A rapier with an enchanted blade.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A rapier with a blade that catches the light strangely."},
    {"id": "mi_weapon_1_shortbow",    "name": "+1 Shortbow",      "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A shortbow strung with a faintly glowing string.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A shortbow whose string hums softly."},
    {"id": "mi_weapon_1_longbow",     "name": "+1 Longbow",       "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A longbow carved from enchanted wood.", "effect": "+1 to attack and damage rolls.", "unidentified_description": "A longbow that feels warm to the touch."},
    {"id": "mi_weapon_2_longsword",   "name": "+2 Longsword",     "rarity": "rare",      "item_type": "weapon", "attunement_required": 0, "description": "A longsword humming with potent magic.", "effect": "+2 to attack and damage rolls.", "unidentified_description": "A longsword that hums with visible energy."},
    {"id": "mi_weapon_2_greatsword",  "name": "+2 Greatsword",    "rarity": "rare",      "item_type": "weapon", "attunement_required": 0, "description": "A greatsword radiating powerful enchantment.", "effect": "+2 to attack and damage rolls.", "unidentified_description": "A greatsword that seems to pull toward targets."},
    {"id": "mi_weapon_2_longbow",     "name": "+2 Longbow",       "rarity": "rare",      "item_type": "weapon", "attunement_required": 0, "description": "A longbow of masterful enchantment.", "effect": "+2 to attack and damage rolls.", "unidentified_description": "A longbow with glowing runes along the limbs."},
    {"id": "mi_weapon_3_longsword",   "name": "+3 Longsword",     "rarity": "very rare", "item_type": "weapon", "attunement_required": 0, "description": "A longsword blazing with powerful magic.", "effect": "+3 to attack and damage rolls.", "unidentified_description": "A longsword surrounded by a visible shimmer."},
    {"id": "mi_javelin_lightning",    "name": "Javelin of Lightning",    "rarity": "uncommon",  "item_type": "weapon", "attunement_required": 0, "description": "A javelin that transforms into a lightning bolt when hurled.", "effect": "Hurl to become a lightning bolt: 4d6 lightning in a 5x120 ft line, DC 13 Dex half. Once per dawn.", "unidentified_description": "A javelin with faint blue veins running through its shaft."},
    {"id": "mi_sword_life_stealing",  "name": "Sword of Life Stealing",  "rarity": "rare",      "item_type": "weapon", "attunement_required": 1, "description": "A dark blade that feeds on life force.", "effect": "On a natural 20: deal +10 necrotic and gain 10 temp HP.", "unidentified_description": "A blade with a dark, oily sheen."},
    {"id": "mi_dagger_venom",         "name": "Dagger of Venom",         "rarity": "rare",      "item_type": "weapon", "attunement_required": 0, "description": "A +1 dagger with a hidden venom reservoir.", "effect": "+1 dagger. Action to poison blade: DC 15 Con or 2d10 poison + poisoned 1 min. Once per dawn.", "unidentified_description": "A dagger with a hollow groove along the blade."},
    {"id": "mi_mace_disruption",      "name": "Mace of Disruption",      "rarity": "rare",      "item_type": "weapon", "attunement_required": 1, "description": "A mace blazing with divine light.", "effect": "+2d6 radiant vs fiends/undead. DC 15 Wis or destroyed if target at 25 HP or fewer.", "unidentified_description": "A mace that glows faintly with a warm light."},
    {"id": "mi_sunblade",             "name": "Sunblade",                 "rarity": "very rare", "item_type": "weapon", "attunement_required": 1, "description": "A hilt that projects a blade of pure sunlight.", "effect": "+2 finesse longsword. Bonus action to emit sunlight. +1d8 radiant vs undead.", "unidentified_description": "A golden hilt with no visible blade."},
    {"id": "mi_oathbow",              "name": "Oathbow",                  "rarity": "very rare", "item_type": "weapon", "attunement_required": 1, "description": "A longbow that binds you to slay a sworn enemy.", "effect": "Name a sworn enemy: advantage vs them, ignore cover. Disadvantage vs all others while they live.", "unidentified_description": "A black longbow inscribed with oaths in Elvish."},
    {"id": "mi_holy_avenger",         "name": "Holy Avenger",             "rarity": "legendary", "item_type": "weapon", "attunement_required": 1, "description": "A holy longsword reserved for paladins.", "effect": "+3 longsword, paladin only. +2d10 radiant vs fiends/undead. Allies within 10 ft have advantage on magic saves.", "unidentified_description": "A radiant longsword with a hilt shaped like holy wings."},
    {"id": "mi_luck_blade",           "name": "Luck Blade",               "rarity": "legendary", "item_type": "weapon", "attunement_required": 1, "description": "A blade blessed with extraordinary fortune.", "effect": "+1 sword. Once/day reroll any d20. Contains 1d4-1 Wish charges.", "unidentified_description": "A sword that seems to gleam with good fortune."},
    {"id": "mi_defender",             "name": "Defender",                  "rarity": "legendary", "item_type": "weapon", "attunement_required": 1, "description": "A +3 sword that can bolster your defense.", "effect": "+3 sword. Transfer up to +3 from attack bonus to AC each turn as a free action.", "unidentified_description": "A sword that shifts between offense and defense on its own."},
    # ── New Magic Armor ─────────────────────────────────────────────────────────
    {"id": "mi_armor_1_leather",      "name": "+1 Leather Armor",              "rarity": "uncommon",  "item_type": "armor", "attunement_required": 0, "description": "Leather armor enhanced with minor protective magic.", "effect": "+1 bonus to AC.", "unidentified_description": "Leather armor that feels tougher than it looks."},
    {"id": "mi_armor_1_chain_mail",   "name": "+1 Chain Mail",                 "rarity": "uncommon",  "item_type": "armor", "attunement_required": 0, "description": "Chain mail reinforced with magical links.", "effect": "+1 bonus to AC.", "unidentified_description": "Chain mail that rings softly with each step."},
    {"id": "mi_armor_1_breastplate",  "name": "+1 Breastplate",                "rarity": "uncommon",  "item_type": "armor", "attunement_required": 0, "description": "A breastplate with a faint protective aura.", "effect": "+1 bonus to AC.", "unidentified_description": "A breastplate that deflects minor blows on its own."},
    {"id": "mi_armor_1_half_plate",   "name": "+1 Half Plate",                 "rarity": "uncommon",  "item_type": "armor", "attunement_required": 0, "description": "Half plate with subtle magical reinforcement.", "effect": "+1 bonus to AC.", "unidentified_description": "Half plate armor with faintly glowing seams."},
    {"id": "mi_armor_1_plate",        "name": "+1 Plate Armor",                "rarity": "uncommon",  "item_type": "armor", "attunement_required": 0, "description": "Plate armor with a minor magical enhancement.", "effect": "+1 bonus to AC.", "unidentified_description": "Plate armor that shrugs off scratches."},
    {"id": "mi_armor_2_breastplate",  "name": "+2 Breastplate",                "rarity": "rare",      "item_type": "armor", "attunement_required": 0, "description": "A breastplate humming with strong protective magic.", "effect": "+2 bonus to AC.", "unidentified_description": "A breastplate with a visible shimmer."},
    {"id": "mi_armor_2_half_plate",   "name": "+2 Half Plate",                 "rarity": "rare",      "item_type": "armor", "attunement_required": 0, "description": "Half plate radiating potent enchantment.", "effect": "+2 bonus to AC.", "unidentified_description": "Half plate armor that hums with energy."},
    {"id": "mi_armor_2_plate",        "name": "+2 Plate Armor",                "rarity": "rare",      "item_type": "armor", "attunement_required": 0, "description": "Plate armor glowing with strong protective wards.", "effect": "+2 bonus to AC.", "unidentified_description": "Plate armor with glowing rune markings."},
    {"id": "mi_armor_3_plate",        "name": "+3 Plate Armor",                "rarity": "very rare", "item_type": "armor", "attunement_required": 0, "description": "Plate armor blazing with powerful enchantment.", "effect": "+3 bonus to AC.", "unidentified_description": "Plate armor surrounded by a visible aura."},
    {"id": "mi_shield_3",             "name": "+3 Shield",                     "rarity": "very rare", "item_type": "armor", "attunement_required": 0, "description": "A shield blazing with powerful protective magic.", "effect": "+3 bonus to AC in addition to the shield's normal +2.", "unidentified_description": "A shield that seems to deflect blows before they land."},
    {"id": "mi_adamantine_chain",     "name": "Adamantine Armor (Chain Mail)", "rarity": "uncommon",  "item_type": "armor", "attunement_required": 0, "description": "Chain mail forged from adamantine.", "effect": "Critical hits against you become normal hits.", "unidentified_description": "Dull grey chain mail that feels unusually dense."},
    {"id": "mi_adamantine_plate",     "name": "Adamantine Armor (Plate)",      "rarity": "uncommon",  "item_type": "armor", "attunement_required": 0, "description": "Plate armor forged from adamantine.", "effect": "Critical hits against you become normal hits.", "unidentified_description": "Dark grey plate armor of extraordinary density."},
    {"id": "mi_mithral_chain",        "name": "Mithral Armor (Chain Mail)",    "rarity": "uncommon",  "item_type": "armor", "attunement_required": 0, "description": "Chain mail forged from mithral.", "effect": "No Strength requirement and no Stealth disadvantage.", "unidentified_description": "Silvery chain mail that weighs almost nothing."},
    {"id": "mi_mithral_plate",        "name": "Mithral Armor (Plate)",         "rarity": "uncommon",  "item_type": "armor", "attunement_required": 0, "description": "Plate armor forged from mithral.", "effect": "No Strength requirement and no Stealth disadvantage.", "unidentified_description": "Gleaming silver plate armor that is surprisingly light."},
    {"id": "mi_elven_chain",          "name": "Elven Chain",                   "rarity": "rare",      "item_type": "armor", "attunement_required": 0, "description": "A +1 chain shirt of elven make.", "effect": "+1 chain shirt. No proficiency required to wear it.", "unidentified_description": "An incredibly fine chain shirt of silvery links."},
    {"id": "mi_glamoured_studded",    "name": "Glamoured Studded Leather",     "rarity": "rare",      "item_type": "armor", "attunement_required": 0, "description": "Enchanted studded leather that changes appearance.", "effect": "+1 studded leather. Bonus action to change its appearance to any armor or clothing.", "unidentified_description": "Studded leather that seems to shift in the light."},
    {"id": "mi_dwarven_plate",        "name": "Dwarven Plate",                 "rarity": "very rare", "item_type": "armor", "attunement_required": 0, "description": "Masterwork dwarven plate with magical heft.", "effect": "+2 plate. Reduce any involuntary movement by up to 10 ft.", "unidentified_description": "Heavy plate armor adorned with dwarven runes."},
    {"id": "mi_efreeti_chain",        "name": "Efreeti Chain",                 "rarity": "very rare", "item_type": "armor", "attunement_required": 1, "description": "Chain mail forged in the fires of the Plane of Fire.", "effect": "+3 chain mail. Immunity to fire damage. Requires attunement.", "unidentified_description": "Red-tinged chain mail that radiates heat."},
    {"id": "mi_spellguard_shield",    "name": "Spellguard Shield",             "rarity": "very rare", "item_type": "armor", "attunement_required": 1, "description": "A shield inscribed with anti-magic wards.", "effect": "Advantage on saves vs spells. Spell attacks against you have disadvantage. Requires attunement.", "unidentified_description": "A shield covered in glowing arcane sigils."},
    {"id": "mi_plate_etherealness",   "name": "Plate of Etherealness",         "rarity": "legendary", "item_type": "armor", "attunement_required": 1, "description": "Shimmering plate armor that straddles two planes.", "effect": "Action to become ethereal for up to 10 minutes. Once per dawn. Requires attunement.", "unidentified_description": "Plate armor that appears slightly translucent."},
    # ── New Wondrous Items ──────────────────────────────────────────────────────
    {"id": "mi_bracers_archery",            "name": "Bracers of Archery",              "rarity": "uncommon",  "item_type": "wondrous", "attunement_required": 1, "description": "Leather bracers embossed with arrow motifs.", "effect": "+2 damage with longbows and shortbows. Requires attunement.", "unidentified_description": "Leather bracers with tiny arrow etchings."},
    {"id": "mi_rope_climbing",              "name": "Rope of Climbing",                "rarity": "uncommon",  "item_type": "wondrous", "attunement_required": 0, "description": "A 60-ft rope that moves on command.", "effect": "60-ft rope. Command it to animate, tie knots, or hold up to 3000 lb.", "unidentified_description": "A coil of rope that coils itself neatly when dropped."},
    {"id": "mi_portable_hole",              "name": "Portable Hole",                   "rarity": "rare",      "item_type": "wondrous", "attunement_required": 0, "description": "A 6-ft diameter circle of black cloth.", "effect": "6-ft diameter extradimensional hole. Do not place inside a Bag of Holding.", "unidentified_description": "A circle of dark cloth that seems to absorb anything placed on it."},
    {"id": "mi_gem_seeing",                 "name": "Gem of Seeing",                   "rarity": "rare",      "item_type": "wondrous", "attunement_required": 1, "description": "A clear gem that reveals all truths.", "effect": "3 charges. Truesight 30 ft for 10 min. Regains 1d3 charges at dawn. Requires attunement.", "unidentified_description": "A perfectly clear gemstone that distorts vision when held up."},
    {"id": "mi_mantle_spell_resist",        "name": "Mantle of Spell Resistance",      "rarity": "rare",      "item_type": "wondrous", "attunement_required": 1, "description": "A cloak woven with anti-magic threads.", "effect": "Advantage on all saving throws against spells. Requires attunement.", "unidentified_description": "A heavy cloak that seems to repel sparks and embers."},
    {"id": "mi_periapt_poison",             "name": "Periapt of Proof Against Poison", "rarity": "rare",      "item_type": "wondrous", "attunement_required": 0, "description": "A pendant that neutralizes all poisons.", "effect": "Immunity to poison damage and the poisoned condition.", "unidentified_description": "A green pendant that seems to purify anything it touches."},
    {"id": "mi_hewards_haversack",          "name": "Heward's Handy Haversack",        "rarity": "rare",      "item_type": "wondrous", "attunement_required": 0, "description": "A backpack with extradimensional compartments.", "effect": "Like a Bag of Holding. The item you want is always on top.", "unidentified_description": "A worn backpack that always seems to have what you need."},
    {"id": "mi_ring_spell_storing",         "name": "Ring of Spell Storing",           "rarity": "rare",      "item_type": "ring",     "attunement_required": 1, "description": "A ring that stores spells for later use.", "effect": "Store up to 5 levels of spells. Release them using your spell save DC. Requires attunement.", "unidentified_description": "A ring with faintly glowing inlaid gems."},
    {"id": "mi_crystal_ball",               "name": "Crystal Ball",                    "rarity": "very rare", "item_type": "wondrous", "attunement_required": 1, "description": "A flawless crystal sphere for scrying.", "effect": "Cast Scrying DC 17 for up to 1 hour. Requires attunement.", "unidentified_description": "A large crystal sphere that occasionally shows faint images."},
    {"id": "mi_ring_regeneration",          "name": "Ring of Regeneration",            "rarity": "very rare", "item_type": "ring",     "attunement_required": 1, "description": "A ring that knits wounds and regrows limbs.", "effect": "Regain 1d6 HP every 10 minutes. Regrow lost limbs in 1d6+1 days. Requires attunement.", "unidentified_description": "A green-tinged ring that feels warm against the skin."},
    {"id": "mi_ring_shooting_stars",        "name": "Ring of Shooting Stars",          "rarity": "very rare", "item_type": "ring",     "attunement_required": 1, "description": "A ring that channels starlight into destructive magic.", "effect": "6 charges. Cast Faerie Fire, Ball Lightning, or Shooting Stars. Requires attunement outdoors at night.", "unidentified_description": "A dark ring with tiny star-like sparkles."},
    {"id": "mi_staff_power",                "name": "Staff of Power",                  "rarity": "very rare", "item_type": "staff",    "attunement_required": 1, "description": "A mighty staff brimming with arcane power.", "effect": "+2 attack/spell/saves/AC. 20 charges, various spells. Regains 2d8+4 at dawn. Requires attunement (sorc/war/wiz).", "unidentified_description": "A staff that crackles with visible energy."},
    {"id": "mi_robe_archmagi",              "name": "Robe of the Archmagi",            "rarity": "legendary", "item_type": "wondrous", "attunement_required": 1, "description": "Robes of supreme arcane power.", "effect": "+2 AC, advantage on magic saves, +2 spell DC and spell attack rolls. Requires attunement (sorc/war/wiz).", "unidentified_description": "Shimmering robes covered in moving arcane symbols."},
    {"id": "mi_ring_three_wishes",          "name": "Ring of Three Wishes",            "rarity": "legendary", "item_type": "ring",     "attunement_required": 1, "description": "A ring containing the ultimate magic.", "effect": "3 charges of Wish. Becomes nonmagical when last charge is used. Requires attunement.", "unidentified_description": "A plain golden ring that feels heavier than it looks."},
    {"id": "mi_scarab_protection",          "name": "Scarab of Protection",            "rarity": "legendary", "item_type": "wondrous", "attunement_required": 1, "description": "A scarab-shaped brooch with divine wards.", "effect": "+1 to saving throws. 12 charges to negate death effects or destroy undead on touch. Requires attunement.", "unidentified_description": "A beetle-shaped brooch that glows faintly."},
    {"id": "mi_staff_magi",                 "name": "Staff of the Magi",               "rarity": "legendary", "item_type": "staff",    "attunement_required": 1, "description": "The pinnacle of magical staves.", "effect": "50 charges. Cast many spells, absorb spells targeting you. Retributive Strike: 16d6 force. Requires attunement (sorc/war/wiz).", "unidentified_description": "A staff of ancient wood covered in powerful runes."},
    # ── Tinker / pirate chase additions ───────────────────────────────────────
    {"id":"mi_goggles_true_measure","name":"Goggles of True Measure","rarity":"uncommon","item_type":"wondrous","attunement_required":1,"description":"Calibrated brass goggles built by guild tinkerers.","effect":"While attuned, gain advantage on Investigation checks involving mechanisms, traps, and hidden seams.","unidentified_description":"Stacked brass lenses click softly as if auto-focusing."},
    {"id":"mi_field_repair_gauntlet","name":"Field Repair Gauntlet","rarity":"rare","item_type":"wondrous","attunement_required":1,"description":"A reinforced artificer gauntlet with integrated rivet punch and arc welder.","effect":"Has 5 charges. Expend 1 charge to cast mending as an action; expend 2 to grant +1 AC to one armor piece for 1 hour. Regains 1d4+1 charges at dawn.","unidentified_description":"A heavy plated glove etched with tiny service markings."},
    {"id":"mi_blackwake_compass","name":"Blackwake Compass","rarity":"rare","item_type":"wondrous","attunement_required":1,"description":"A named corsair compass that always needles toward advantage.","effect":"While attuned, you cannot become lost at sea and gain advantage on checks to navigate storms or reefs.","unidentified_description":"A tarnished brass compass that spins once before settling with intent."},
    {"id":"mi_tidecaller_cutlass","name":"Tidecaller's Cutlass","rarity":"very rare","item_type":"weapon","attunement_required":1,"description":"A wave-etched blade carried by the first tidewardens.","effect":"+2 weapon. On hit, deal an extra 1d6 cold damage; once per short rest, a struck target must pass Str DC 15 or be pushed 10 feet.","unidentified_description":"A salt-blue curved blade with coral inlay and a sea-silk grip."},
    {"id":"mi_clockwork_scout","name":"Clockwork Scout","rarity":"rare","item_type":"wondrous","attunement_required":0,"description":"A palm-sized brass beetle that records what it sees.","effect":"As an action, deploy the scout for 10 minutes of silent reconnaissance within 300 feet; it returns and replays simple visual cues.","unidentified_description":"A folded brass insect with tiny crystal eyes."},
    # ── EXPANSION: Scrolls — utility, protection, ward, named, cursed ────────
    {"id":"mi_scroll_mending_field","name":"Scroll of Mending Field","rarity":"common","item_type":"scroll","attunement_required":0,"description":"A field-repair scroll etched in copperplate ink.","effect":"As an action, cast Mending on any object within 10 feet; may target up to three minor breaks on the same object.","unidentified_description":"A short parchment strip with tool-marks and neat copperplate glyphs."},
    {"id":"mi_scroll_farspeech","name":"Scroll of Farspeech","rarity":"uncommon","item_type":"scroll","attunement_required":0,"description":"An arcanist's correspondence scroll sealed with twin sigils.","effect":"As an action, send a spoken message of 25 words or fewer to one creature you know within 5 miles. They hear it clearly, once.","unidentified_description":"Twin ink-stamped rings flank the text on this compact scroll."},
    {"id":"mi_scroll_iron_ward","name":"Scroll of Iron Ward","rarity":"uncommon","item_type":"scroll","attunement_required":0,"description":"A defensive ward parchment reinforced with iron-salt ink.","effect":"As an action, grant one creature you touch a +2 bonus to AC for 1 minute. The ward collapses after the target is struck three times.","unidentified_description":"Stiff parchment with jagged angular runes that press slightly into the skin."},
    {"id":"mi_scroll_fog_bank","name":"Scroll of Fog Bank","rarity":"uncommon","item_type":"scroll","attunement_required":0,"description":"A sea-spray scroll used by pirates to cover escapes in harbor mist.","effect":"As an action, create a 30-foot radius fog cloud centered on a point within 120 feet for 10 minutes. Heavily obscures all within.","unidentified_description":"A damp scroll that smells faintly of brine and low-tide mist."},
    {"id":"mi_scroll_swift_step","name":"Scroll of Swift Step","rarity":"uncommon","item_type":"scroll","attunement_required":0,"description":"A courier ward used by outriders and messengers in urgent transit.","effect":"As a bonus action, double your movement speed until the end of your next turn.","unidentified_description":"Small glyphs crowd this narrow scroll as if written in tremendous haste."},
    {"id":"mi_scroll_ritual_ward_fire","name":"Scroll of Ritual Fire Ward","rarity":"uncommon","item_type":"scroll","attunement_required":0,"description":"A forgemaster's protection rite for prolonged heat work.","effect":"As an action, a willing creature you touch gains resistance to fire damage for 10 minutes.","unidentified_description":"Orange-tinted parchment with heat-formed seal marks at both ends."},
    {"id":"mi_scroll_calm_waters","name":"Scroll of Calm Waters","rarity":"uncommon","item_type":"scroll","attunement_required":0,"description":"A navigator's ward used to ease rough crossings for small vessels.","effect":"As an action, calm winds and waves in a 60-foot radius for 10 minutes. Difficult terrain from water is negated within the zone.","unidentified_description":"A softened scroll laminated with sea-grass and a pressed shell at one corner."},
    {"id":"mi_scroll_stone_ward","name":"Scroll of Stone Ward","rarity":"rare","item_type":"scroll","attunement_required":0,"description":"A defensive rite adapted from druid bark-ward traditions.","effect":"As an action, grant yourself or one touched creature resistance to bludgeoning, piercing, and slashing damage for 1 minute.","unidentified_description":"Grey-inked glyphs on rough parchment that feels almost like bark."},
    {"id":"mi_scroll_shadow_step","name":"Scroll of Shadow Step","rarity":"rare","item_type":"scroll","attunement_required":0,"description":"A nightwarden's escape scroll that bends space through shadow.","effect":"As an action, teleport from any area of dim light or darkness to another such area within 60 feet. You arrive without sound.","unidentified_description":"The ink on this scroll seems to shift into darker patches when you look away."},
    {"id":"mi_scroll_tidal_force","name":"Scroll of Tidal Force","rarity":"rare","item_type":"scroll","attunement_required":0,"description":"A naval battle-scroll amplifying wave-force against a hull or ranked foes.","effect":"As an action, a crashing force wave (30-ft line, 5-ft wide) strikes all in its path: 6d8 bludgeoning damage (DC 15 Str halves), and those who fail are knocked prone.","unidentified_description":"Blue-green ink forms a jagged wave-crest across this stiff vellum scroll."},
    {"id":"mi_scroll_circuit_interrupt","name":"Scroll of Circuit Interrupt","rarity":"rare","item_type":"scroll","attunement_required":0,"description":"A tinker-devised schematic that disrupts conductive systems via arc discharge.","effect":"As an action, unleash an arc pulse in a 15-foot radius: 5d6 lightning damage (Dex DC 14 half) and one non-magical mechanism within the area is disabled for 1 minute.","unidentified_description":"Copper-threaded parchment with circuit-like rune traces along both margins."},
    {"id":"mi_scroll_speak_with_dead","name":"Scroll of Speaking with the Dead","rarity":"rare","item_type":"scroll","attunement_required":0,"description":"A ritual scroll long used by war-priests and field investigators.","effect":"As an action, cast Speak with Dead on a nearby corpse. The effect lasts 10 minutes and requires no material components.","unidentified_description":"Dense funerary script in grey-brown ink on aged vellum."},
    {"id":"mi_scroll_veil_of_storms","name":"Scroll of the Veil of Storms","rarity":"very rare","item_type":"scroll","attunement_required":0,"description":"A named tempest ward recovered from a legendary corsair's chart room.","effect":"As an action, summon a 60-foot storm veil for 1 minute. Creatures entering or starting their turn inside take 4d8 lightning + 4d8 thunder damage and are deafened (DC 15 Con half).","unidentified_description":"A heavy sealed scroll with coral-pressed edges and a salt-crystal disc seal."},
    {"id":"mi_scroll_cursed_recall","name":"Scroll of Cursed Recall","rarity":"rare","item_type":"scroll","attunement_required":0,"description":"A black-market scroll of uncertain origin. Reading it is as dangerous as useful.","effect":"As an action, you return to the last location where you took a long rest. However, roll a d6: on a 1, one random item in your pack is teleported away instead.","unidentified_description":"Smudged text on black-stained parchment; the final line appears to have been rewritten."},
    {"id":"mi_scroll_unwritten_command","name":"Scroll of the Unwritten Command","rarity":"legendary","item_type":"scroll","attunement_required":0,"description":"A scroll that appears blank until read aloud, when it writes the reader's intent in a single devastating order.","effect":"As an action, name a creature within 60 feet: they must succeed on a Wis DC 19 save or follow a single-sentence spoken command for 1 minute, as Dominate Person.","unidentified_description":"A scroll that appears entirely blank until you begin reading it aloud."},
    # ── EXPANSION: Chase items — named pirate + tinker wondrous ───────────────
    {"id":"mi_ring_trickster","name":"Ring of the Trickster","rarity":"uncommon","item_type":"ring","attunement_required":1,"description":"A named ring once worn by a notorious confidence artist.","effect":"While attuned, you may cast Disguise Self at will as a bonus action, and gain advantage on Deception checks against anyone who has not seen through your disguise.","unidentified_description":"A plain brass ring worth almost nothing at first glance."},
    {"id":"mi_voltaic_bracer","name":"Voltaic Bracer","rarity":"uncommon","item_type":"wondrous","attunement_required":1,"description":"A tinker-built arm bracer with an integrated charge capacitor.","effect":"Has 4 charges. As a bonus action, expend 1 charge to add 1d8 lightning damage to your next melee hit this turn. Regains 1d4 charges at dawn.","unidentified_description":"A plated bracer with a small dial and a crystal inset on the inside wrist."},
    {"id":"mi_amulet_deep_sea","name":"Amulet of the Deep Sea","rarity":"uncommon","item_type":"wondrous","attunement_required":1,"description":"A corsair amulet carved from deep-sea oyster shell.","effect":"While attuned, you can breathe underwater and have a swimming speed of 30 feet.","unidentified_description":"A dark shell amulet on a braided sea-twine cord."},
    {"id":"mi_corsair_coat","name":"Corsair's Charmed Coat","rarity":"rare","item_type":"wondrous","attunement_required":1,"description":"A well-traveled captain's coat layered with subtle deflection wards.","effect":"While attuned: +1 AC, advantage on Charisma checks with sailors and pirates, and resistance to cold damage.","unidentified_description":"A salt-faded long coat with unusual heft in its lining."},
    {"id":"mi_artificers_monocle","name":"Artificer's Monocle","rarity":"rare","item_type":"wondrous","attunement_required":1,"description":"A single enchanted lens on a brass frame built for deep mechanical analysis.","effect":"While attuned: identify any mechanical object's function with 1 minute of study; advantage on checks vs traps and mechanisms; once per day cast Detect Magic as a free action.","unidentified_description":"A single thick lens on a hinged brass arm."},
    # ── EXPANSION: Potions and magic consumables ──────────────────────────────
    {"id":"mi_potion_resist_thunder","name":"Potion of Resistance (Thunder)","rarity":"uncommon","item_type":"potion","attunement_required":0,"description":"A vibrating amber liquid that hums when the cork is removed.","effect":"Gain resistance to thunder damage for 1 hour.","unidentified_description":"An amber liquid that faintly vibrates inside its sealed vial."},
    {"id":"mi_potion_resist_psychic","name":"Potion of Resistance (Psychic)","rarity":"uncommon","item_type":"potion","attunement_required":0,"description":"A pale lavender liquid with a curiously still, deep quality.","effect":"Gain resistance to psychic damage for 1 hour.","unidentified_description":"A pale liquid that makes the holder feel oddly calm."},
    {"id":"mi_oil_slipperiness","name":"Oil of Slipperiness","rarity":"uncommon","item_type":"potion","attunement_required":0,"description":"A gel-like liquid that renders coated surfaces frictionless.","effect":"Apply to yourself or an object. Lasts 8 hours. While coated, you are immune to the restrained condition and can move through tight spaces as if one size smaller.","unidentified_description":"A clear viscous gel that makes fingers slip off the vial."},
    {"id":"mi_oil_sharpness","name":"Oil of Sharpness","rarity":"rare","item_type":"potion","attunement_required":0,"description":"A bright metallic fluid that hones any blade to supernatural keenness.","effect":"Apply to a slashing or piercing weapon. For 1 hour, that weapon has a +3 bonus to attack and damage rolls (does not stack with other magical bonuses).","unidentified_description":"A thin metallic oil with a mirror-like surface."},
    {"id":"mi_philter_love","name":"Philter of Love","rarity":"uncommon","item_type":"potion","attunement_required":0,"description":"A rosy liquid with a faint floral sweetness.","effect":"The drinker becomes charmed by the first creature they see after drinking. Lasts 1 hour (Wis DC 12 to end early each minute).","unidentified_description":"A rosy liquid that smells of flowers and something subtle and sweet."},
]


def seed_magic_items() -> None:
    """Insert SRD magic items using INSERT OR IGNORE and deduplicate by name."""
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO magic_items (id, name, rarity, item_type, attunement_required, description, effect, unidentified_description) VALUES (:id,:name,:rarity,:item_type,:attunement_required,:description,:effect,:unidentified_description)",
            _SRD_MAGIC_ITEMS,
        )
        # Deduplicate by name (case-insensitive), keeping lowest rowid
        conn.execute(
            "DELETE FROM magic_items WHERE rowid NOT IN (SELECT MIN(rowid) FROM magic_items GROUP BY LOWER(name))"
        )
        conn.commit()


# Individual Treasure tables (SRD 5e): keyed by CR range.
# Format: (cr_min, cr_max, d100_min, d100_max, coin_type, qty_dice, qty_sides, qty_mod)
_INDIVIDUAL_TREASURE: List[tuple] = [
    # CR 0–4
    (0, 4, 1,  30,  "cp", 5, 6,  0),
    (0, 4, 31, 60,  "sp", 4, 6,  0),
    (0, 4, 61, 70,  "ep", 3, 6,  0),
    (0, 4, 71, 95,  "gp", 3, 6,  0),
    (0, 4, 96, 100, "pp", 1, 6,  0),
    # CR 5–10
    (5, 10, 1,  30,  "cp", 4, 6,  0),   # ×100
    (5, 10, 31, 60,  "sp", 6, 6,  0),   # ×10
    (5, 10, 61, 70,  "ep", 3, 6,  0),   # ×10
    (5, 10, 71, 95,  "gp", 4, 6,  0),   # ×10
    (5, 10, 96, 100, "pp", 2, 6,  0),
    # CR 11–16
    (11, 16, 1,  20,  "sp", 4, 6,  0),  # ×100
    (11, 16, 21, 35,  "ep", 1, 6,  0),  # ×100
    (11, 16, 36, 75,  "gp", 2, 6,  0),  # ×100
    (11, 16, 76, 100, "pp", 2, 6,  0),  # ×10
    # CR 17+
    (17, 30, 1,  15,  "ep", 2, 6,  0),  # ×1000
    (17, 30, 16, 55,  "gp", 2, 6,  0),  # ×1000
    (17, 30, 56, 100, "pp", 3, 6,  0),  # ×100
]

# Hoard tables: (cr_min, cr_max, coin_type, qty_dice, qty_sides, qty_multiplier)
_HOARD_COINS: List[tuple] = [
    (0, 4,   "cp", 6, 6, 100),
    (0, 4,   "sp", 3, 6, 100),
    (0, 4,   "gp", 2, 6, 10),
    (5, 10,  "cp", 2, 6, 100),
    (5, 10,  "sp", 2, 6, 1000),
    (5, 10,  "gp", 6, 6, 100),
    (5, 10,  "pp", 3, 6, 10),
    (11, 16, "sp", 4, 6, 1000),
    (11, 16, "gp", 1, 6, 10000),
    (11, 16, "pp", 1, 6, 1000),
    (17, 30, "gp", 2, 6, 10000),
    (17, 30, "pp", 8, 6, 1000),
]


def seed_treasure_tables() -> None:
    """Seed treasure_tables if empty."""
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM treasure_tables").fetchone()[0]
        if count > 0:
            return
        rows = []
        for (cr_min, cr_max, d100_min, d100_max, coin_type, qty_dice, qty_sides, qty_mod) in _INDIVIDUAL_TREASURE:
            rows.append((cr_min, cr_max, d100_min, d100_max, "individual", "coin", None, qty_dice, qty_sides, qty_mod, coin_type))
        for (cr_min, cr_max, coin_type, qty_dice, qty_sides, _mult) in _HOARD_COINS:
            rows.append((cr_min, cr_max, 1, 100, "hoard", "coin", None, qty_dice, qty_sides, 0, coin_type))
        conn.executemany(
            "INSERT INTO treasure_tables (cr_range_min, cr_range_max, roll_d100_min, roll_d100_max, table_type, item_type, item_id, quantity_dice, quantity_sides, quantity_modifier, coin_type) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()


# ── Party treasury helpers ──────────────────────────────────────────────────────

def get_party_treasury(campaign_id: str) -> Dict[str, Any]:
    """Return the party treasury row for a campaign, creating it if absent."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM party_treasury WHERE campaign_id=?", (campaign_id,)).fetchone()
        if row:
            d = dict(row)
            d["gems"] = _json_loads(d.get("gems"), [])
            d["art_objects"] = _json_loads(d.get("art_objects"), [])
            return d
        now = time.time()
        conn.execute(
            "INSERT INTO party_treasury (campaign_id, gold, silver, copper, gems, art_objects, updated_at) VALUES (?,0,0,0,'[]','[]',?)",
            (campaign_id, now),
        )
        conn.commit()
        return {"campaign_id": campaign_id, "gold": 0, "silver": 0, "copper": 0, "gems": [], "art_objects": [], "updated_at": now}


def update_party_treasury(campaign_id: str, gold: int = 0, silver: int = 0, copper: int = 0,
                           gems: list | None = None, art_objects: list | None = None) -> Dict[str, Any]:
    """Add to the party treasury (delta values). Returns updated treasury."""
    current = get_party_treasury(campaign_id)
    # Auto-convert: every 10cp becomes 1sp, every 10sp becomes 1gp.
    carry_sp, actual_copper = divmod(max(0, int(current["copper"]) + int(copper)), 10)
    actual_silver = int(current["silver"]) + int(silver) + carry_sp
    carry_gp, actual_silver = divmod(actual_silver, 10)
    actual_gold = max(0, int(current["gold"]) + int(gold) + carry_gp)

    new_gems = list(current["gems"]) + list(gems or [])
    new_art  = list(current["art_objects"]) + list(art_objects or [])
    now = time.time()
    with get_conn() as conn:
        conn.execute(
            "UPDATE party_treasury SET gold=?, silver=?, copper=?, gems=?, art_objects=?, updated_at=? WHERE campaign_id=?",
            (actual_gold, actual_silver, actual_copper, json.dumps(new_gems), json.dumps(new_art), now, campaign_id),
        )
        conn.commit()
    return {"campaign_id": campaign_id, "gold": actual_gold, "silver": actual_silver, "copper": actual_copper, "gems": new_gems, "art_objects": new_art, "updated_at": now}


def set_party_treasury(campaign_id: str, gold: int, silver: int, copper: int,
                        gems: list | None = None, art_objects: list | None = None) -> Dict[str, Any]:
    """Set absolute treasury values (for DM manual adjustments)."""
    # Normalise carry
    carry_sp, copper = divmod(max(0, int(copper)), 10)
    carry_gp, silver = divmod(max(0, int(silver)) + carry_sp, 10)
    gold = max(0, int(gold)) + carry_gp
    existing = get_party_treasury(campaign_id)
    new_gems = list(gems) if gems is not None else list(existing.get("gems", []))
    new_art  = list(art_objects) if art_objects is not None else list(existing.get("art_objects", []))
    now = time.time()
    with get_conn() as conn:
        conn.execute(
            "UPDATE party_treasury SET gold=?, silver=?, copper=?, gems=?, art_objects=?, updated_at=? WHERE campaign_id=?",
            (gold, silver, copper, json.dumps(new_gems), json.dumps(new_art), now, campaign_id),
        )
        conn.commit()
    return {"campaign_id": campaign_id, "gold": gold, "silver": silver, "copper": copper, "gems": new_gems, "art_objects": new_art, "updated_at": now}


def get_magic_item(item_id: str) -> Dict[str, Any] | None:
    """Return a magic item row by id."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM magic_items WHERE id=?", (item_id,)).fetchone()
    return dict(row) if row else None


def get_all_magic_items() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM magic_items ORDER BY rarity, name").fetchall()
    return [dict(r) for r in rows]


# ─── SRD Items (bulk-imported from dnd5eapi.co) ────────────────────────────────

def init_srd_items_table() -> None:
    """Create the srd_items table if it doesn't exist and auto-seed if empty."""
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS srd_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Gear',
                rarity TEXT NOT NULL DEFAULT 'Common',
                weight REAL NOT NULL DEFAULT 0,
                default_price TEXT NOT NULL DEFAULT '',
                default_qty INTEGER NOT NULL DEFAULT 1,
                description TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                stack_limit INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        # Migrate existing tables that predate the stack_limit column.
        try:
            conn.execute("ALTER TABLE srd_items ADD COLUMN stack_limit INTEGER NOT NULL DEFAULT 1")
        except Exception:
            pass  # Column already exists
        conn.commit()
    _seed_srd_items_from_magic_items()
    _seed_srd_mundane_equipment()


def _seed_srd_items_from_magic_items() -> None:
    """Seed srd_items from the existing magic_items table (INSERT OR IGNORE)."""
    _rarity_title = {
        "common": "Common", "uncommon": "Uncommon", "rare": "Rare",
        "very rare": "Very Rare", "legendary": "Legendary",
    }
    _type_to_cat = {
        "potion": "Potion", "scroll": "Scroll", "ring": "Ring",
        "wand": "Wondrous Item", "armor": "Armor", "weapon": "Weapon",
        "wondrous": "Wondrous Item", "rod": "Wondrous Item", "staff": "Wondrous Item",
    }
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM magic_items").fetchall()
        for row in rows:
            r = dict(row)
            rarity = _rarity_title.get(str(r.get("rarity") or "").lower(), "Common")
            category = _type_to_cat.get(str(r.get("item_type") or "").lower(), "Wondrous Item")
            desc = str(r.get("description") or "")
            if r.get("effect"):
                desc = (desc + "\n" + str(r["effect"])).strip()
            conn.execute(
                "INSERT OR IGNORE INTO srd_items (id, name, category, rarity, weight, default_price, default_qty, description, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"srd_mi_{r['id']}", r["name"], category, rarity, 0.0, "", 1, desc[:2000], str(r.get("item_type") or ""))
            )
        conn.commit()


# Built-in D&D 5e SRD mundane equipment for offline seeding
_SRD_MUNDANE: List[Dict[str, Any]] = [
    # Weapons
    {"id":"seq_club","name":"Club","category":"Weapon","rarity":"Common","weight":2,"default_price":"1 sp","description":"Simple melee weapon. Damage: 1d4 bludgeoning.\nProperties: Light, Monk"},
    {"id":"seq_dagger","name":"Dagger","category":"Weapon","rarity":"Common","weight":1,"default_price":"2 gp","description":"Simple melee/ranged weapon. Damage: 1d4 piercing.\nProperties: Finesse, Light, Thrown (20/60)"},
    {"id":"seq_greatclub","name":"Greatclub","category":"Weapon","rarity":"Common","weight":10,"default_price":"2 sp","description":"Simple melee weapon. Damage: 1d8 bludgeoning.\nProperties: Two-Handed"},
    {"id":"seq_handaxe","name":"Handaxe","category":"Weapon","rarity":"Common","weight":2,"default_price":"5 gp","description":"Simple melee weapon. Damage: 1d6 slashing.\nProperties: Light, Thrown (20/60)"},
    {"id":"seq_javelin","name":"Javelin","category":"Weapon","rarity":"Common","weight":2,"default_price":"5 sp","description":"Simple melee weapon. Damage: 1d6 piercing.\nProperties: Thrown (30/120)"},
    {"id":"seq_lighthammer","name":"Light Hammer","category":"Weapon","rarity":"Common","weight":2,"default_price":"2 gp","description":"Simple melee weapon. Damage: 1d4 bludgeoning.\nProperties: Light, Thrown (20/60)"},
    {"id":"seq_mace","name":"Mace","category":"Weapon","rarity":"Common","weight":4,"default_price":"5 gp","description":"Simple melee weapon. Damage: 1d6 bludgeoning."},
    {"id":"seq_quarterstaff","name":"Quarterstaff","category":"Weapon","rarity":"Common","weight":4,"default_price":"2 sp","description":"Simple melee weapon. Damage: 1d6 bludgeoning.\nProperties: Versatile (1d8)"},
    {"id":"seq_shortsword","name":"Shortsword","category":"Weapon","rarity":"Common","weight":2,"default_price":"10 gp","description":"Martial melee weapon. Damage: 1d6 piercing.\nProperties: Finesse, Light"},
    {"id":"seq_longsword","name":"Longsword","category":"Weapon","rarity":"Common","weight":3,"default_price":"15 gp","description":"Martial melee weapon. Damage: 1d8 slashing.\nProperties: Versatile (1d10)"},
    {"id":"seq_rapier","name":"Rapier","category":"Weapon","rarity":"Common","weight":2,"default_price":"25 gp","description":"Martial melee weapon. Damage: 1d8 piercing.\nProperties: Finesse"},
    {"id":"seq_greataxe","name":"Greataxe","category":"Weapon","rarity":"Common","weight":7,"default_price":"30 gp","description":"Martial melee weapon. Damage: 1d12 slashing.\nProperties: Heavy, Two-Handed"},
    {"id":"seq_greatsword","name":"Greatsword","category":"Weapon","rarity":"Common","weight":6,"default_price":"50 gp","description":"Martial melee weapon. Damage: 2d6 slashing.\nProperties: Heavy, Two-Handed"},
    {"id":"seq_maul","name":"Maul","category":"Weapon","rarity":"Common","weight":10,"default_price":"10 gp","description":"Martial melee weapon. Damage: 2d6 bludgeoning.\nProperties: Heavy, Two-Handed"},
    {"id":"seq_warhammer","name":"Warhammer","category":"Weapon","rarity":"Common","weight":2,"default_price":"15 gp","description":"Martial melee weapon. Damage: 1d8 bludgeoning.\nProperties: Versatile (1d10)"},
    {"id":"seq_battleaxe","name":"Battleaxe","category":"Weapon","rarity":"Common","weight":4,"default_price":"10 gp","description":"Martial melee weapon. Damage: 1d8 slashing.\nProperties: Versatile (1d10)"},
    {"id":"seq_flail","name":"Flail","category":"Weapon","rarity":"Common","weight":2,"default_price":"10 gp","description":"Martial melee weapon. Damage: 1d8 bludgeoning."},
    {"id":"seq_halberd","name":"Halberd","category":"Weapon","rarity":"Common","weight":6,"default_price":"20 gp","description":"Martial melee weapon. Damage: 1d10 slashing.\nProperties: Heavy, Reach, Two-Handed"},
    {"id":"seq_lance","name":"Lance","category":"Weapon","rarity":"Common","weight":6,"default_price":"10 gp","description":"Martial melee weapon. Damage: 1d12 piercing.\nProperties: Reach, Special"},
    {"id":"seq_pike","name":"Pike","category":"Weapon","rarity":"Common","weight":18,"default_price":"5 gp","description":"Martial melee weapon. Damage: 1d10 piercing.\nProperties: Heavy, Reach, Two-Handed"},
    {"id":"seq_shortbow","name":"Shortbow","category":"Weapon","rarity":"Common","weight":2,"default_price":"25 gp","description":"Simple ranged weapon. Damage: 1d6 piercing.\nRange: 80/320 ft. Properties: Ammunition, Two-Handed"},
    {"id":"seq_longbow","name":"Longbow","category":"Weapon","rarity":"Common","weight":2,"default_price":"50 gp","description":"Martial ranged weapon. Damage: 1d8 piercing.\nRange: 150/600 ft. Properties: Ammunition, Heavy, Two-Handed"},
    {"id":"seq_crossbow_light","name":"Crossbow, Light","category":"Weapon","rarity":"Common","weight":5,"default_price":"25 gp","description":"Simple ranged weapon. Damage: 1d8 piercing.\nRange: 80/320 ft. Properties: Ammunition, Loading, Two-Handed"},
    {"id":"seq_crossbow_heavy","name":"Crossbow, Heavy","category":"Weapon","rarity":"Common","weight":18,"default_price":"50 gp","description":"Martial ranged weapon. Damage: 1d10 piercing.\nRange: 100/400 ft. Properties: Ammunition, Heavy, Loading, Two-Handed"},
    {"id":"seq_hand_crossbow","name":"Hand Crossbow","category":"Weapon","rarity":"Common","weight":3,"default_price":"75 gp","description":"Martial ranged weapon. Damage: 1d6 piercing.\nRange: 30/120 ft. Properties: Ammunition, Light, Loading"},
    # Armor
    {"id":"seq_leather","name":"Leather Armor","category":"Armor","rarity":"Common","weight":10,"default_price":"10 gp","description":"Light armor. AC: 11 + Dex modifier."},
    {"id":"seq_padded","name":"Padded Armor","category":"Armor","rarity":"Common","weight":8,"default_price":"5 gp","description":"Light armor. AC: 11 + Dex modifier. Properties: Disadvantage on Stealth"},
    {"id":"seq_studded_leather","name":"Studded Leather","category":"Armor","rarity":"Common","weight":13,"default_price":"45 gp","description":"Light armor. AC: 12 + Dex modifier."},
    {"id":"seq_hide","name":"Hide Armor","category":"Armor","rarity":"Common","weight":12,"default_price":"10 gp","description":"Medium armor. AC: 12 + Dex modifier (max +2)."},
    {"id":"seq_chain_shirt","name":"Chain Shirt","category":"Armor","rarity":"Common","weight":20,"default_price":"50 gp","description":"Medium armor. AC: 13 + Dex modifier (max +2)."},
    {"id":"seq_scale_mail","name":"Scale Mail","category":"Armor","rarity":"Common","weight":45,"default_price":"50 gp","description":"Medium armor. AC: 14 + Dex modifier (max +2). Properties: Disadvantage on Stealth"},
    {"id":"seq_breastplate","name":"Breastplate","category":"Armor","rarity":"Common","weight":20,"default_price":"400 gp","description":"Medium armor. AC: 14 + Dex modifier (max +2)."},
    {"id":"seq_half_plate","name":"Half Plate","category":"Armor","rarity":"Common","weight":40,"default_price":"750 gp","description":"Medium armor. AC: 15 + Dex modifier (max +2). Properties: Disadvantage on Stealth"},
    {"id":"seq_ring_mail","name":"Ring Mail","category":"Armor","rarity":"Common","weight":40,"default_price":"30 gp","description":"Heavy armor. AC: 14. Properties: Disadvantage on Stealth"},
    {"id":"seq_chain_mail","name":"Chain Mail","category":"Armor","rarity":"Common","weight":55,"default_price":"75 gp","description":"Heavy armor. AC: 16. Requires Str 13. Properties: Disadvantage on Stealth"},
    {"id":"seq_splint","name":"Splint Armor","category":"Armor","rarity":"Common","weight":60,"default_price":"200 gp","description":"Heavy armor. AC: 17. Requires Str 15. Properties: Disadvantage on Stealth"},
    {"id":"seq_plate","name":"Plate Armor","category":"Armor","rarity":"Common","weight":65,"default_price":"1500 gp","description":"Heavy armor. AC: 18. Requires Str 15. Properties: Disadvantage on Stealth"},
    {"id":"seq_shield","name":"Shield","category":"Armor","rarity":"Common","weight":6,"default_price":"10 gp","description":"+2 bonus to AC. Cannot be used with two-handed weapons."},
    # Adventuring Gear
    {"id":"seq_abacus","name":"Abacus","category":"Gear","rarity":"Common","weight":2,"default_price":"2 gp","description":"A counting frame for arithmetic calculations."},
    {"id":"seq_acid_vial","name":"Acid (vial)","category":"Gear","rarity":"Common","weight":1,"default_price":"25 gp","description":"As an action, splash the contents at a creature or object. Target takes 2d6 acid damage (Dex DC 13 halves)."},
    {"id":"seq_alchemist_fire","name":"Alchemist's Fire","category":"Gear","rarity":"Common","weight":1,"default_price":"50 gp","description":"Sticky, adhesive fluid. Creature hit takes 1d4 fire damage at start of each turn until action used to extinguish."},
    {"id":"seq_arrows","name":"Arrows (20)","category":"Gear","rarity":"Common","weight":1,"default_price":"1 gp","description":"Ammunition for shortbows and longbows."},
    {"id":"seq_blowgun_needles","name":"Blowgun Needles (50)","category":"Gear","rarity":"Common","weight":1,"default_price":"1 gp","description":"Ammunition for blowguns."},
    {"id":"seq_crossbow_bolts","name":"Crossbow Bolts (20)","category":"Gear","rarity":"Common","weight":1.5,"default_price":"1 gp","description":"Ammunition for crossbows."},
    {"id":"seq_sling_bullets","name":"Sling Bullets (20)","category":"Gear","rarity":"Common","weight":1.5,"default_price":"4 cp","description":"Ammunition for slings."},
    {"id":"seq_antitoxin","name":"Antitoxin (vial)","category":"Gear","rarity":"Common","weight":0,"default_price":"50 gp","description":"Drinking grants advantage on Constitution saving throws against poison for 1 hour. Not magical."},
    {"id":"seq_backpack","name":"Backpack","category":"Gear","rarity":"Common","weight":5,"default_price":"2 gp","description":"Holds up to 30 pounds / 1 cubic foot."},
    {"id":"seq_ball_bearings","name":"Ball Bearings (bag of 1,000)","category":"Gear","rarity":"Common","weight":2,"default_price":"1 gp","description":"Scatter as action; DC 10 Dex save to avoid falling prone when crossing area."},
    {"id":"seq_barrel","name":"Barrel","category":"Gear","rarity":"Common","weight":70,"default_price":"2 gp","description":"Holds 40 gallons of liquid or 4 cubic feet of solid material."},
    {"id":"seq_bedroll","name":"Bedroll","category":"Gear","rarity":"Common","weight":7,"default_price":"1 gp","description":"Provides comfortable sleeping arrangement during long rests outdoors."},
    {"id":"seq_bell","name":"Bell","category":"Gear","rarity":"Common","weight":0,"default_price":"1 gp","description":"A small brass bell."},
    {"id":"seq_blanket","name":"Blanket","category":"Gear","rarity":"Common","weight":3,"default_price":"5 sp","description":"A warm woolen blanket."},
    {"id":"seq_block_and_tackle","name":"Block and Tackle","category":"Gear","rarity":"Common","weight":5,"default_price":"1 gp","description":"Set of pulleys; allows halving effective weight of objects being lifted."},
    {"id":"seq_book","name":"Book","category":"Gear","rarity":"Common","weight":5,"default_price":"25 gp","description":"A book with 400 pages of blank or written content."},
    {"id":"seq_caltrops","name":"Caltrops (bag of 20)","category":"Gear","rarity":"Common","weight":2,"default_price":"1 gp","description":"Scatter as action; DC 15 Dex or speed reduced by 10 ft and 1 piercing damage."},
    {"id":"seq_candle","name":"Candle","category":"Gear","rarity":"Common","weight":0,"default_price":"1 cp","description":"Illuminates a bright 5-foot radius and dim light 5 feet beyond for 1 hour."},
    {"id":"seq_chain","name":"Chain (10 feet)","category":"Gear","rarity":"Common","weight":10,"default_price":"5 gp","description":"Has 10 hit points. Can be burst with DC 20 Strength check."},
    {"id":"seq_chalk","name":"Chalk (1 piece)","category":"Gear","rarity":"Common","weight":0,"default_price":"1 cp","description":"White chalk for writing or marking surfaces."},
    {"id":"seq_climbers_kit","name":"Climber's Kit","category":"Gear","rarity":"Common","weight":12,"default_price":"25 gp","description":"Includes special pitons, boot tips, gloves, and a harness. Advantage on Athletics to climb."},
    {"id":"seq_clothes_common","name":"Clothes, Common","category":"Gear","rarity":"Common","weight":3,"default_price":"5 sp","description":"Everyday working clothes."},
    {"id":"seq_clothes_fine","name":"Clothes, Fine","category":"Gear","rarity":"Common","weight":6,"default_price":"15 gp","description":"Elegant clothing suitable for nobles and wealthy merchants."},
    {"id":"seq_crowbar","name":"Crowbar","category":"Gear","rarity":"Common","weight":5,"default_price":"2 gp","description":"Advantage on Strength checks where leverage could be applied."},
    {"id":"seq_flask","name":"Flask or Tankard","category":"Gear","rarity":"Common","weight":1,"default_price":"2 cp","description":"Holds 1 pint of liquid."},
    {"id":"seq_grappling_hook","name":"Grappling Hook","category":"Gear","rarity":"Common","weight":4,"default_price":"2 gp","description":"Iron hook attached to a rope for climbing and securing."},
    {"id":"seq_hammer","name":"Hammer","category":"Gear","rarity":"Common","weight":3,"default_price":"1 gp","description":"Iron hammer used for construction or breaking."},
    {"id":"seq_healer_kit","name":"Healer's Kit","category":"Gear","rarity":"Common","weight":3,"default_price":"5 gp","description":"10 uses. Stabilize a creature without a Wisdom (Medicine) check."},
    {"id":"seq_holy_water","name":"Holy Water (flask)","category":"Gear","rarity":"Common","weight":1,"default_price":"25 gp","description":"Deals 2d6 radiant damage to undead and fiends; 20-foot splash."},
    {"id":"seq_ink_bottle","name":"Ink (1 ounce bottle)","category":"Gear","rarity":"Common","weight":0,"default_price":"10 gp","description":"Black ink in a sealed bottle."},
    {"id":"seq_lantern_bullseye","name":"Lantern, Bullseye","category":"Gear","rarity":"Common","weight":2,"default_price":"10 gp","description":"Burns 6 hours per flask; 60-foot cone of bright light, 60 more dim."},
    {"id":"seq_lantern_hooded","name":"Lantern, Hooded","category":"Gear","rarity":"Common","weight":2,"default_price":"5 gp","description":"Burns 6 hours per flask; 30-foot radius bright, 30 more dim. Hood dims to 5-foot."},
    {"id":"seq_lock","name":"Lock","category":"Gear","rarity":"Common","weight":1,"default_price":"10 gp","description":"DC 15 Thieves' Tools to pick."},
    {"id":"seq_magnifying_glass","name":"Magnifying Glass","category":"Gear","rarity":"Common","weight":0,"default_price":"100 gp","description":"Advantage on Appraisal checks for small objects. Used as fire-starter in sunlight."},
    {"id":"seq_manacles","name":"Manacles","category":"Gear","rarity":"Common","weight":6,"default_price":"2 gp","description":"AC 19; 15 hit points; Escape DC 20. Can bind a Medium or Small creature."},
    {"id":"seq_mirror","name":"Mirror, Steel","category":"Gear","rarity":"Common","weight":0.5,"default_price":"5 gp","description":"A polished steel mirror for signalling or personal use."},
    {"id":"seq_oil_flask","name":"Oil (flask)","category":"Gear","rarity":"Common","weight":1,"default_price":"1 sp","description":"Pour to create slick (DC 10 Dex or fall prone) or splash for 5 fire damage on ignition."},
    {"id":"seq_paper","name":"Paper (one sheet)","category":"Gear","rarity":"Common","weight":0,"default_price":"2 sp","description":"A single sheet of paper."},
    {"id":"seq_perfume","name":"Perfume (vial)","category":"Gear","rarity":"Common","weight":0,"default_price":"5 gp","description":"A small vial of fragrant perfume."},
    {"id":"seq_pickaxe","name":"Miner's Pick","category":"Gear","rarity":"Common","weight":10,"default_price":"2 gp","description":"A heavy iron pick used for mining."},
    {"id":"seq_piton","name":"Piton","category":"Gear","rarity":"Common","weight":0.25,"default_price":"5 cp","description":"Iron spike driven into rock for climbing."},
    {"id":"seq_poison_basic","name":"Poison, Basic (vial)","category":"Gear","rarity":"Common","weight":0,"default_price":"100 gp","description":"Apply to weapon or ammo. On hit, DC 10 Con save or 1d4 poison damage."},
    {"id":"seq_pole","name":"Pole (10-foot)","category":"Gear","rarity":"Common","weight":7,"default_price":"5 cp","description":"A 10-foot wooden pole."},
    {"id":"seq_rope_hempen","name":"Rope, Hempen (50 feet)","category":"Gear","rarity":"Common","weight":10,"default_price":"1 gp","description":"2 hit points; DC 17 Strength to break."},
    {"id":"seq_rope_silk","name":"Rope, Silk (50 feet)","category":"Gear","rarity":"Common","weight":5,"default_price":"10 gp","description":"2 hit points; DC 17 Strength to break. Lighter than hempen."},
    {"id":"seq_sack","name":"Sack","category":"Gear","rarity":"Common","weight":0.5,"default_price":"1 cp","description":"Holds up to 30 pounds / 1 cubic foot."},
    {"id":"seq_sealing_wax","name":"Sealing Wax","category":"Gear","rarity":"Common","weight":0,"default_price":"5 sp","description":"Used to seal letters and documents."},
    {"id":"seq_shovel","name":"Shovel","category":"Gear","rarity":"Common","weight":5,"default_price":"2 gp","description":"An iron shovel for digging."},
    {"id":"seq_signal_whistle","name":"Signal Whistle","category":"Gear","rarity":"Common","weight":0,"default_price":"5 cp","description":"A small metal whistle for signalling."},
    {"id":"seq_spyglass","name":"Spyglass","category":"Gear","rarity":"Common","weight":1,"default_price":"1000 gp","description":"Objects appear 2× closer when viewed through the lens."},
    {"id":"seq_tent","name":"Tent, Two-Person","category":"Gear","rarity":"Common","weight":20,"default_price":"2 gp","description":"A simple tent sheltering up to two people."},
    {"id":"seq_tinderbox","name":"Tinderbox","category":"Gear","rarity":"Common","weight":1,"default_price":"5 sp","description":"Contains flint, fire steel, and tinder. Light a torch in 1 action; other fires in 1 minute."},
    {"id":"seq_torch","name":"Torch","category":"Gear","rarity":"Common","weight":1,"default_price":"1 cp","description":"Burns 1 hour; bright 20-foot radius, dim 20 more. Melee: 1 fire damage."},
    {"id":"seq_waterskin","name":"Waterskin","category":"Gear","rarity":"Common","weight":5,"default_price":"2 sp","description":"Holds 4 pints of liquid (water, wine, etc.)."},
    {"id":"seq_whetstone","name":"Whetstone","category":"Gear","rarity":"Common","weight":1,"default_price":"1 cp","description":"Used to sharpen bladed weapons."},
    # Tools
    {"id":"seq_thieves_tools","name":"Thieves' Tools","category":"Tool","rarity":"Common","weight":1,"default_price":"25 gp","description":"Includes small file, set of lock picks, mirror on handle, narrow-bladed scissors, pliers."},
    {"id":"seq_herbalism_kit","name":"Herbalism Kit","category":"Tool","rarity":"Common","weight":3,"default_price":"5 gp","description":"For identifying, harvesting, and preparing herbs; craft antitoxin and healing potions."},
    {"id":"seq_alchemist_supplies","name":"Alchemist's Supplies","category":"Tool","rarity":"Common","weight":8,"default_price":"50 gp","description":"For producing alchemical items. Includes two glass beakers, metal frame, stirring rod, small mortar and pestle, pouch of common alchemical ingredients."},
    {"id":"seq_disguise_kit","name":"Disguise Kit","category":"Tool","rarity":"Common","weight":3,"default_price":"25 gp","description":"Includes cosmetics, hair dye, small props, and a few changes of clothing."},
    {"id":"seq_forgery_kit","name":"Forgery Kit","category":"Tool","rarity":"Common","weight":5,"default_price":"15 gp","description":"Includes several types of ink, parchment, quills, seals, and gold and silver leaf."},
    {"id":"seq_navigators_tools","name":"Navigator's Tools","category":"Tool","rarity":"Common","weight":2,"default_price":"25 gp","description":"Includes sextant, compass, calipers, ruler, parchment, ink, and quill."},
    {"id":"seq_poisoner_kit","name":"Poisoner's Kit","category":"Tool","rarity":"Common","weight":2,"default_price":"50 gp","description":"Includes glass vials, mortar and pestle, chemicals, and a glass stirring rod."},
    # Potions (mundane)
    {"id":"seq_ration","name":"Rations (1 day)","category":"Gear","rarity":"Common","weight":2,"default_price":"5 sp","description":"Compact dry foods suitable for extended travel (jerky, dried fruit, hardtack, nuts)."},
    {"id":"seq_canteen","name":"Canteen","category":"Gear","rarity":"Common","weight":0.5,"default_price":"1 sp","description":"Metal water container holding 1 pint."},
    {"id":"seq_soap","name":"Soap","category":"Gear","rarity":"Common","weight":0,"default_price":"2 cp","description":"A small bar of soap."},
    {"id":"seq_firewood","name":"Firewood (per day)","category":"Gear","rarity":"Common","weight":20,"default_price":"1 cp","description":"Enough wood for a campfire for one day."},
    {"id":"seq_lamp","name":"Lamp","category":"Gear","rarity":"Common","weight":1,"default_price":"5 sp","description":"Burns for 6 hours per flask; bright 15-foot radius, dim 30 more."},
    {"id":"seq_riding_horse","name":"Riding Horse","category":"Mount & Vehicle","rarity":"Common","weight":0,"default_price":"75 gp","description":"Mount-capable inventory container in-app. 5e carry profile: up to 480 lb of gear/passengers."},
    {"id":"seq_draft_horse","name":"Draft Horse","category":"Mount & Vehicle","rarity":"Common","weight":0,"default_price":"50 gp","description":"Hauling-capable inventory container in-app. 5e carry profile: up to 540 lb of cargo."},
    {"id":"seq_cart","name":"Cart","category":"Mount & Vehicle","rarity":"Common","weight":0,"default_price":"15 gp","description":"Vehicle inventory container in-app. 5e cargo profile: up to 300 lb before over-capacity warnings."},
    # Crafted gear, materials, and profession-linked economy additions
    {"id":"seq_batwing_travel_cloak","name":"Batwing Travel Cloak","category":"Gear","rarity":"Uncommon","weight":2,"default_price":"28 gp","description":"A dark leather traveling cloak cut like folded wings. Favored by scouts, night couriers, and cave delvers.","tags":"cloak,utility,craftable,profession:tailor,recipe:batwing_travel_cloak,shop:tailor"},
    {"id":"seq_stormwax_cloak","name":"Stormwax Cloak","category":"Gear","rarity":"Uncommon","weight":3,"default_price":"40 gp","description":"A waxed cloak that sheds rain and sea spray, granting comfort on long wet marches.","tags":"cloak,travel,craftable,profession:tailor,recipe:stormwax_cloak,shop:tailor"},
    {"id":"seq_marshstrider_boots","name":"Marshstrider Boots","category":"Gear","rarity":"Uncommon","weight":3,"default_price":"35 gp","description":"Bog-leather boots with wide soles for marsh work. Hunters swear by their footing.","tags":"boots,utility,craftable,profession:leatherworker,recipe:marshstrider_boots,shop:leatherworker"},
    {"id":"seq_forgehand_gloves","name":"Forgehand Gloves","category":"Gear","rarity":"Common","weight":1,"default_price":"12 gp","description":"Heat-resistant gloves used by smiths and glassworkers when handling hot tools.","tags":"gloves,profession_tool,craftable,profession:blacksmith,shop:blacksmith"},
    {"id":"seq_watcher_signet","name":"Watcher Signet","category":"Ring","rarity":"Uncommon","weight":0,"default_price":"55 gp","description":"A silver ring set with a smoky quartz eye. Often worn by wardens and caravan guards.","tags":"ring,utility,crafted,profession:jeweler,shop:jeweler"},
    {"id":"seq_moonthread_amulet","name":"Moonthread Amulet","category":"Wondrous Item","rarity":"Uncommon","weight":0,"default_price":"90 gp","description":"An amulet wrapped in pale silver thread that never tangles. Keeps a traveler calmly focused at night.","tags":"amulet,utility,crafted,profession:jeweler,shop:magic"},
    {"id":"seq_wayfinder_talisman","name":"Wayfinder Talisman","category":"Wondrous Item","rarity":"Common","weight":0,"default_price":"18 gp","description":"A carved driftwood charm that subtly tugs toward familiar roads and landmarks.","tags":"talisman,travel,craftable,profession:woodworker,shop:general"},
    {"id":"seq_glowmoss_lantern","name":"Glowmoss Lantern","category":"Gear","rarity":"Uncommon","weight":2,"default_price":"20 gp","description":"A hooded lantern packed with cultivated glowmoss. Dimmer than oil flame, but never smokes.","tags":"lantern,utility,craftable,profession:tinker,recipe:glowmoss_lantern,shop:general"},
    {"id":"seq_folding_cookset","name":"Folding Cookset","category":"Gear","rarity":"Common","weight":4,"default_price":"9 gp","description":"A nested iron cookset with pan, pot, and hook for campfire use.","tags":"travel,utility,craftable,profession:blacksmith,shop:general"},
    {"id":"seq_field_repair_kit","name":"Field Repair Kit","category":"Tool","rarity":"Common","weight":5,"default_price":"15 gp","description":"Needle, awl, rivets, wax cord, and buckle parts for mending armor and tack in camp.","tags":"tool,craftable,profession:leatherworker,recipe:field_repair_kit,shop:general"},
    {"id":"seq_hunter_snares","name":"Hunter's Snares (3)","category":"Gear","rarity":"Common","weight":2,"default_price":"3 gp","description":"Trip loops and spring-wire snares for securing small game or warning perimeters.","tags":"field_gear,craftable,profession:trapper,shop:general"},
    {"id":"seq_portable_mortar","name":"Portable Mortar and Pestle","category":"Tool","rarity":"Common","weight":2,"default_price":"6 gp","description":"A compact stone grinder for battlefield salves and trail alchemy.","tags":"tool,alchemy,craftable,profession:alchemist,shop:alchemist"},
    {"id":"seq_treated_bandage","name":"Treated Bandage Roll","category":"Consumable","rarity":"Common","weight":0.5,"default_price":"1 gp","description":"Clean linen infused with herb resin. A practical medic supply in cities and war camps.","tags":"consumable,crafted,profession:herbalist,recipe:treated_bandage"},
    {"id":"seq_stitchleaf_salve","name":"Stitchleaf Salve","category":"Consumable","rarity":"Common","weight":0.5,"default_price":"8 gp","description":"A thick green salve brewed from stitchleaf and pine resin. Stops bleeding and eases soreness.","tags":"consumable,craftable,profession:herbalist,recipe:stitchleaf_salve,shop:alchemist"},
    {"id":"seq_minor_vigor_tonic","name":"Minor Vigor Tonic","category":"Potion","rarity":"Common","weight":0.5,"default_price":"18 gp","description":"A bitter tonic used by mercenary medics to restore stamina after hard marching.","tags":"potion,craftable,profession:alchemist,recipe:minor_vigor_tonic,shop:alchemist"},
    {"id":"seq_smoke_capsule","name":"Smoke Capsule","category":"Consumable","rarity":"Common","weight":0.25,"default_price":"6 gp","description":"A sealed clay capsule that bursts into thick smoke when thrown.","tags":"consumable,utility,craftable,profession:alchemist,shop:black_market"},
    {"id":"seq_bone_reinforced_buckler","name":"Bone-Reinforced Buckler","category":"Armor","rarity":"Common","weight":5,"default_price":"20 gp","description":"A compact shield reinforced with monster bone ribs. Counts as a standard shield for AC bonuses.","tags":"shield,craftable,profession:leatherworker,recipe:bone_reinforced_buckler"},
    {"id":"seq_ashwood_hunting_bow","name":"Ashwood Hunting Bow","category":"Weapon","rarity":"Common","weight":2,"default_price":"30 gp","description":"A resilient ashwood bow favored by foresters. Damage profile matches a shortbow.","tags":"weapon,bow,craftable,profession:bowyer,recipe:ashwood_hunting_bow"},
    {"id":"seq_ironbark_arrow_bundle","name":"Ironbark Arrows (20)","category":"Gear","rarity":"Common","weight":1,"default_price":"2 gp","description":"Hardwood shaft arrows fletched for damp climates and long storage.","tags":"ammunition,craftable,profession:fletcher,recipe:ironbark_arrow_bundle"},
    {"id":"seq_skinning_knife","name":"Skinning Knife","category":"Weapon","rarity":"Common","weight":1,"default_price":"5 gp","description":"A narrow curved blade for field dressing game and carving useful hides.","tags":"weapon,tool,craftable,profession:leatherworker,shop:general"},
    {"id":"seq_amberglass_vial","name":"Amberglass Vial","category":"Material","rarity":"Common","weight":0.1,"default_price":"3 sp","description":"A durable amber vial used to store volatile reagents and tinctures.","tags":"material,crafting,alchemy,shop:alchemist"},
    {"id":"seq_cured_hide_bundle","name":"Cured Hide Bundle","category":"Material","rarity":"Common","weight":3,"default_price":"4 gp","description":"Tanned hide strips sized for belts, straps, and light armor patches.","tags":"material,crafting,profession:leatherworker,source:harvest"},
    {"id":"seq_leather_scraps","name":"Leather Scraps","category":"Material","rarity":"Common","weight":1,"default_price":"8 sp","description":"Mixed scrap leather suitable for mending, wraps, and satchel reinforcement.","tags":"material,crafting,profession:leatherworker,source:harvest"},
    {"id":"seq_bone_shards","name":"Bone Shards","category":"Material","rarity":"Common","weight":1,"default_price":"1 gp","description":"Cleaned shards used for glue, carving, and composite grips.","tags":"material,crafting,profession:boneworker,source:harvest"},
    {"id":"seq_fang_cluster","name":"Fang Cluster","category":"Material","rarity":"Common","weight":0.5,"default_price":"2 gp","description":"Sorted fangs prized by trappers, shamans, and charm-makers.","tags":"material,crafting,profession:trapper,source:harvest"},
    {"id":"seq_venom_sac","name":"Venom Sac","category":"Material","rarity":"Uncommon","weight":0.5,"default_price":"12 gp","description":"A carefully tied gland pouch used in poison and antidote brewing.","tags":"material,crafting,alchemy,profession:alchemist,source:monster"},
    {"id":"seq_chitin_plate","name":"Chitin Plate","category":"Material","rarity":"Common","weight":2,"default_price":"5 gp","description":"Segmented shell plates harvested from giant insects and polished for reinforcement.","tags":"material,crafting,profession:armorer,source:monster"},
    {"id":"seq_scaled_scraps","name":"Scaled Scraps","category":"Material","rarity":"Uncommon","weight":1,"default_price":"9 gp","description":"Flexible scale offcuts used in cloaks, armor lining, and heatproof wraps.","tags":"material,crafting,profession:leatherworker,source:monster"},
    {"id":"seq_mythril_ore_fragment","name":"Mythril Ore Fragment","category":"Material","rarity":"Uncommon","weight":1,"default_price":"20 gp","description":"A raw silvery ore chip that smiths alloy into lightweight gear.","tags":"material,crafting,profession:blacksmith,source:mining"},
    {"id":"seq_bloomsteel_ingot","name":"Bloomsteel Ingot","category":"Material","rarity":"Common","weight":5,"default_price":"15 gp","description":"A clean smelted ingot stamped by local guild for dependable smithing work.","tags":"material,crafting,profession:blacksmith,shop:blacksmith"},
    {"id":"seq_hardwood_plank_bundle","name":"Hardwood Plank Bundle","category":"Material","rarity":"Common","weight":8,"default_price":"6 gp","description":"Seasoned planks favored by fletchers and wainwrights.","tags":"material,crafting,profession:woodworker,shop:general"},
    {"id":"seq_frostcap_mushroom","name":"Frostcap Mushroom","category":"Material","rarity":"Common","weight":0.2,"default_price":"1 gp","description":"A pale cave mushroom used for cooling tonics and smoke stabilizers.","tags":"material,crafting,alchemy,profession:herbalist,source:foraging"},
    {"id":"seq_sunleaf_bunch","name":"Sunleaf Bunch","category":"Material","rarity":"Common","weight":0.2,"default_price":"9 sp","description":"Bright gold-green leaves dried for salves and travel teas.","tags":"material,crafting,alchemy,profession:herbalist,source:foraging"},
    {"id":"seq_spider_silk_spool","name":"Spider Silk Spool","category":"Material","rarity":"Uncommon","weight":0.5,"default_price":"10 gp","description":"Strong, thin silk thread used in cloaks, bowstrings, and surgical stitching.","tags":"material,crafting,profession:tailor,source:monster"},
    {"id":"seq_aether_dust","name":"Aether Dust","category":"Material","rarity":"Rare","weight":0.1,"default_price":"45 gp","description":"A glittering residue collected from shattered spell foci and leyline stones.","tags":"material,crafting,arcane,profession:enchanter,source:salvage"},
    {"id":"seq_crystal_shard_cluster","name":"Crystal Shard Cluster","category":"Material","rarity":"Uncommon","weight":1,"default_price":"14 gp","description":"Clear resonance crystals prized in foci, lenses, and talismans.","tags":"material,crafting,arcane,profession:jeweler,source:mining"},
    {"id":"seq_recipe_bone_reinforced_buckler","name":"Recipe: Bone-Reinforced Buckler","category":"Recipe","rarity":"Common","weight":0,"default_price":"9 gp","description":"Pattern sheet detailing hide lamination over shaped bone ribs.","tags":"recipe,profession:leatherworker,crafts:bone_reinforced_buckler"},
    {"id":"seq_recipe_ashwood_hunting_bow","name":"Recipe: Ashwood Hunting Bow","category":"Recipe","rarity":"Common","weight":0,"default_price":"8 gp","description":"Bowyer notes covering ash curing, tiller balancing, and string tension.","tags":"recipe,profession:bowyer,crafts:ashwood_hunting_bow"},
    {"id":"seq_recipe_stitchleaf_salve","name":"Recipe: Stitchleaf Salve","category":"Recipe","rarity":"Common","weight":0,"default_price":"6 gp","description":"Herbalist formula for a battlefield salve using stitchleaf, wax, and ash.","tags":"recipe,profession:herbalist,crafts:stitchleaf_salve"},
    {"id":"seq_recipe_minor_vigor_tonic","name":"Recipe: Minor Vigor Tonic","category":"Recipe","rarity":"Uncommon","weight":0,"default_price":"14 gp","description":"An alchemical tonic protocol with measured bloomsteel trace and sunleaf reduction.","tags":"recipe,profession:alchemist,crafts:minor_vigor_tonic"},
    # Item-family expansion: pirate + tinker + deeper adventuring utility
    {"id":"seq_cutlass","name":"Cutlass","category":"Weapon","rarity":"Common","weight":3,"default_price":"18 gp","description":"A naval-curved saber favored in close-quarters deck fighting. Treat as a scimitar profile.","tags":"weapon,pirate,shop:black_market"},
    {"id":"seq_cutlass_serrated","name":"Serrated Boarding Cutlass","category":"Weapon","rarity":"Uncommon","weight":3,"default_price":"35 gp","description":"A heavier hooked cutlass designed to catch rigging and shield rims during boarding actions.","tags":"weapon,pirate,craftable,profession:blacksmith"},
    {"id":"seq_boarding_axe","name":"Boarding Axe","category":"Weapon","rarity":"Common","weight":4,"default_price":"14 gp","description":"A compact axe with a reinforced haft hook for pulling lines and climbing rails.","tags":"weapon,pirate,shop:blacksmith"},
    {"id":"seq_belaying_pin","name":"Belaying Pin","category":"Weapon","rarity":"Common","weight":2,"default_price":"4 sp","description":"A hardened hardwood pin that doubles as an improvised club on ship decks.","tags":"weapon,pirate,shop:general"},
    {"id":"seq_grappling_bundle","name":"Boarding Grapple Bundle","category":"Gear","rarity":"Common","weight":8,"default_price":"7 gp","description":"A weighted triple-hook, 30-foot line, and quick-release knots for ship and rooftop approach.","tags":"pirate,travel,utility,shop:black_market"},
    {"id":"seq_sea_cloak","name":"Sea Cloak","category":"Gear","rarity":"Common","weight":3,"default_price":"12 gp","description":"Waxed and saltproofed travel cloak that resists spray and wind-chill on open water.","tags":"pirate,travel,profession:tailoring,shop:general"},
    {"id":"seq_stormshore_cloak","name":"Stormshore Cloak","category":"Gear","rarity":"Rare","weight":3,"default_price":"85 gp","description":"A rune-stitched sea cloak that dries quickly and sheds lightning-static in squalls.","tags":"pirate,magic,craftable,profession:tailoring,profession:alchemy"},
    {"id":"seq_weatherproof_boots","name":"Weatherproof Deck Boots","category":"Gear","rarity":"Common","weight":2,"default_price":"10 gp","description":"Grooved soles and tar-sealed seams keep footing stable on wet planks and slick rocks.","tags":"pirate,travel,boots,profession:leatherworking"},
    {"id":"seq_captains_spyglass","name":"Captain's Spyglass","category":"Gear","rarity":"Uncommon","weight":1,"default_price":"180 gp","description":"A brass extendable glass with storm-mark calibration rings and distance etchings.","tags":"pirate,navigation,profession:tinkering,shop:magic"},
    {"id":"seq_chart_case","name":"Waterproof Chart Case","category":"Gear","rarity":"Common","weight":1,"default_price":"4 gp","description":"Pitch-sealed tube with wax flap for preserving maps, manifests, and coded routes.","tags":"pirate,navigation,utility,shop:general"},
    {"id":"seq_smugglers_satchel","name":"Smuggler's Satchel","category":"Gear","rarity":"Uncommon","weight":2,"default_price":"24 gp","description":"Layered satchel with hidden pocketing and scent-masking oilcloth lining.","tags":"pirate,container,utility,profession:leatherworking,shop:black_market"},
    {"id":"seq_powder_horn","name":"Powder Horn","category":"Gear","rarity":"Common","weight":1,"default_price":"3 gp","description":"A tight-stop horn for keeping flash powder and alchemical charges dry at sea.","tags":"pirate,consumable_support,shop:black_market"},
    {"id":"seq_signal_flags","name":"Signal Flag Set","category":"Gear","rarity":"Common","weight":2,"default_price":"6 gp","description":"Color-coded pennants used for coded naval signaling and coordinated maneuvers.","tags":"pirate,navigation,utility,shop:general"},
    {"id":"seq_tidecharm","name":"Tide Charm","category":"Trinket","rarity":"Uncommon","weight":0.1,"default_price":"35 gp","description":"A carved coral charm said to steady hands during rough seas and moon tides.","tags":"pirate,trinket,magic,shop:magic"},
    {"id":"seq_tinkers_multitool","name":"Tinker's Multi-Tool","category":"Tool","rarity":"Common","weight":2,"default_price":"20 gp","description":"Fold-out pliers, micro-file, lens clip, tension key, and spark striker in one brass frame.","tags":"tinker,tool,profession:tinkering,shop:blacksmith"},
    {"id":"seq_grapnel_spool","name":"Grapnel Spool Launcher","category":"Gear","rarity":"Uncommon","weight":4,"default_price":"48 gp","description":"Spring spool with retractable line and claw for vertical access and quick pulls.","tags":"tinker,utility,traversal,profession:tinkering"},
    {"id":"seq_signal_beetle","name":"Signal Beetle","category":"Gear","rarity":"Uncommon","weight":0.2,"default_price":"26 gp","description":"A clockwork beetle that blinks coded light pulses to paired receivers.","tags":"tinker,utility,communication,profession:tinkering"},
    {"id":"seq_flash_device","name":"Flash Prism Capsule","category":"Consumable","rarity":"Common","weight":0.1,"default_price":"9 gp","description":"Throw to emit a blinding arc burst; ideal for escapes and ambush breaks.","tags":"consumable,tinker,utility,profession:alchemy"},
    {"id":"seq_shock_probe","name":"Shock Probe","category":"Gear","rarity":"Uncommon","weight":1,"default_price":"22 gp","description":"A charge-tip test rod used to stun mechanisms and jolt stubborn latches.","tags":"tinker,utility,profession:tinkering,shop:blacksmith"},
    {"id":"seq_calibrated_lens","name":"Calibrated Lens Goggles","category":"Gear","rarity":"Uncommon","weight":1,"default_price":"30 gp","description":"Stacked flip lenses for circuit work, trap sighting, and distant readouts.","tags":"tinker,tool,profession:tinkering,shop:magic"},
    {"id":"seq_wrist_spring_blade","name":"Wrist Spring-Blade","category":"Weapon","rarity":"Uncommon","weight":1,"default_price":"32 gp","description":"A hidden forearm blade deployed by a spring latch for emergency close combat.","tags":"tinker,weapon,profession:tinkering,shop:black_market"},
    {"id":"seq_stabilizer_kit","name":"Portable Stabilizer Kit","category":"Tool","rarity":"Common","weight":3,"default_price":"16 gp","description":"Clamp feet, balancing wedges, and arc-braces for field repairs on unstable terrain.","tags":"tinker,tool,repair,profession:tinkering"},
    {"id":"seq_brewers_bandage","name":"Brine-Sterile Bandage","category":"Consumable","rarity":"Common","weight":0.2,"default_price":"2 gp","description":"Sea-salt sterilized wrap for treating cuts, rope burn, and deck splinter wounds.","tags":"consumable,field_medicine,profession:herbalist"},
    {"id":"seq_battlefield_salve","name":"Battlefield Resin Salve","category":"Consumable","rarity":"Common","weight":0.2,"default_price":"7 gp","description":"Resin-and-herb salve that dulls pain and seals shallow wounds after a skirmish.","tags":"consumable,field_medicine,profession:alchemy"},
    {"id":"seq_vigor_draught","name":"Vigor Draught","category":"Potion","rarity":"Uncommon","weight":0.5,"default_price":"24 gp","description":"A sharp tonic used by couriers and marines to push through fatigue.","tags":"potion,consumable,alchemy,shop:alchemist"},
    {"id":"seq_resistance_tonic_cold","name":"Coldguard Tonic","category":"Potion","rarity":"Uncommon","weight":0.5,"default_price":"28 gp","description":"A mint-bitter tonic that grants brief resistance to cold and numbing winds.","tags":"potion,resistance,alchemy,shop:alchemist"},
    {"id":"seq_resistance_tonic_lightning","name":"Stormguard Tonic","category":"Potion","rarity":"Uncommon","weight":0.5,"default_price":"30 gp","description":"An ozone-scented tonic that tempers lightning shock for a short duration.","tags":"potion,resistance,alchemy,pirate,shop:alchemist"},
    {"id":"seq_smoke_injector_charge","name":"Smoke Injector Charge","category":"Consumable","rarity":"Common","weight":0.1,"default_price":"5 gp","description":"Pressurized cartridge used in tinker launchers to create instant concealment.","tags":"consumable,tinker,alchemy,shop:black_market"},
    {"id":"seq_arc_battery","name":"Arc Battery Cell","category":"Material","rarity":"Uncommon","weight":0.5,"default_price":"16 gp","description":"A crystal-cored battery storing controlled static charge for field devices.","tags":"material,tinker,crafting,profession:tinkering"},
    {"id":"seq_clockwork_spring_set","name":"Clockwork Spring Set","category":"Material","rarity":"Common","weight":0.4,"default_price":"5 gp","description":"Precision-cut tempered springs for trigger housing, launchers, and scouts.","tags":"material,tinker,crafting,profession:tinkering"},
    {"id":"seq_precision_gear_pack","name":"Precision Gear Pack","category":"Material","rarity":"Common","weight":0.6,"default_price":"6 gp","description":"Assorted micro-gears and pins used in watches, rangefinders, and signaling rigs.","tags":"material,tinker,crafting,profession:tinkering"},
    {"id":"seq_salvaged_brass","name":"Salvaged Brass Bundle","category":"Material","rarity":"Common","weight":2,"default_price":"4 gp","description":"Recovered brass strips and plates suited for durable casings and fittings.","tags":"material,tinker,crafting,profession:blacksmith"},
    {"id":"seq_coral_inlay","name":"Coral Inlay Shards","category":"Material","rarity":"Uncommon","weight":0.4,"default_price":"8 gp","description":"Sea-cured coral fragments used in charms, blades, and tide-ward engravings.","tags":"material,pirate,crafting,profession:jeweler"},
    {"id":"seq_tarred_rope_bundle","name":"Tarred Rope Bundle","category":"Material","rarity":"Common","weight":4,"default_price":"3 gp","description":"Waterproof rope coils used for rigging repairs and boarding kits.","tags":"material,pirate,crafting,profession:shipwright"},
    {"id":"seq_driftwood_plank_bundle","name":"Driftwood Plank Bundle","category":"Material","rarity":"Common","weight":6,"default_price":"4 gp","description":"Seasoned sea-planks used for quick hull patching and deck braces.","tags":"material,pirate,crafting,profession:woodworking"},
    {"id":"seq_lantern_oil_sealed","name":"Sealed Lantern Oil","category":"Gear","rarity":"Common","weight":1,"default_price":"4 sp","description":"Storm-sealed oil flask that burns clean in wet and windy conditions.","tags":"travel,light,pirate,shop:general"},
    {"id":"seq_hooked_climbing_line","name":"Hooked Climbing Line","category":"Gear","rarity":"Common","weight":5,"default_price":"5 gp","description":"A knotted traversal line with integrated hook and quick-release knots.","tags":"travel,traversal,utility,shop:general"},
    {"id":"seq_lantern_blueglass","name":"Blueglass Beacon Lantern","category":"Gear","rarity":"Uncommon","weight":2,"default_price":"18 gp","description":"A shutter lantern with blueglass panes, preferred for long-range night signaling.","tags":"light,navigation,pirate,profession:tinkering"},
    {"id":"seq_surveyors_compass","name":"Surveyor's Compass","category":"Tool","rarity":"Common","weight":1,"default_price":"9 gp","description":"A rugged compass with notch marks for overland and shoreline triangulation.","tags":"navigation,survival,tool,shop:general"},
    {"id":"seq_field_suture_kit","name":"Field Suture Kit","category":"Tool","rarity":"Common","weight":1,"default_price":"8 gp","description":"Needles, thread, clamps, and alcohol for emergency wound closure.","tags":"field_medicine,tool,profession:herbalist"},
    {"id":"seq_capsule_case","name":"Capsule Bandolier","category":"Gear","rarity":"Common","weight":1,"default_price":"6 gp","description":"A padded chest bandolier made for secure carry of glass vials and smoke capsules.","tags":"container,alchemy,utility,shop:alchemist"},
    {"id":"seq_recipe_flash_prism_capsule","name":"Recipe: Flash Prism Capsule","category":"Recipe","rarity":"Common","weight":0,"default_price":"9 gp","description":"Tinker-alchemy instructions for a compact flash-burst capsule.","tags":"recipe,profession:tinkering,profession:alchemy,crafts:flash_prism_capsule"},
    {"id":"seq_recipe_stormshore_cloak","name":"Recipe: Stormshore Cloak","category":"Recipe","rarity":"Rare","weight":0,"default_price":"20 gp","description":"Tailor's stormproof pattern using wax layering and arc-treated thread.","tags":"recipe,profession:tailoring,crafts:stormshore_cloak"},
    {"id":"seq_recipe_grapnel_spool_launcher","name":"Recipe: Grapnel Spool Launcher","category":"Recipe","rarity":"Uncommon","weight":0,"default_price":"14 gp","description":"Workshop schematic for a spring-driven grapnel spool with safety latch.","tags":"recipe,profession:tinkering,crafts:grapnel_spool_launcher"},
    {"id":"seq_recipe_smugglers_satchel","name":"Recipe: Smuggler's Satchel","category":"Recipe","rarity":"Uncommon","weight":0,"default_price":"11 gp","description":"Leatherworker's guide to hidden seams and moisture-proof lining.","tags":"recipe,profession:leatherworking,crafts:smugglers_satchel"},
    # Stage 2 starter materials ─ canonical IDs used by tests and future systems
    {"id":"mat_iron_ingot","name":"Iron Ingot","category":"Material","rarity":"Common","weight":1.0,"default_price":"1 gp","default_qty":1,"stack_limit":20,"description":"A smelted bar of wrought iron. Standard smithing stock for tools, fittings, and weapons.","tags":"material,metal,crafting,profession:blacksmith,shop:blacksmith"},
    {"id":"mat_cured_hide","name":"Cured Hide","category":"Material","rarity":"Common","weight":2.0,"default_price":"2 gp","default_qty":1,"stack_limit":10,"description":"A single tanned animal hide, softened and treated for use in armor, bags, and straps.","tags":"material,leather,crafting,profession:leatherworker,source:harvest"},
    {"id":"mat_bat_wing_membrane","name":"Bat Wing Membrane","category":"Material","rarity":"Uncommon","weight":0.25,"default_price":"5 gp","default_qty":1,"stack_limit":10,"description":"Thin, flexible membrane harvested from giant bats. Used in cloaks, gliders, and shadow-ward charms.","tags":"material,beast,occult,crafting,source:monster"},
    {"id":"mat_shadow_resin","name":"Shadow Resin","category":"Material","rarity":"Rare","weight":0.5,"default_price":"30 gp","default_qty":1,"stack_limit":5,"description":"A thick, smoke-dark resin that solidifies when exposed to dim light. Prized in enchanting and shadow-binding.","tags":"material,occult,alchemy,crafting,source:salvage"},
    {"id":"mat_glass_vial","name":"Glass Vial","category":"Material","rarity":"Common","weight":0.1,"default_price":"1 sp","default_qty":1,"stack_limit":50,"description":"A small, stoppered glass vial suitable for potions, reagents, and samples.","tags":"material,alchemy,crafting,shop:alchemist"},
    # ── EXPANSION: Additional materials ──────────────────────────────────────
    {"id":"mat_silver_ingot","name":"Silver Ingot","category":"Material","rarity":"Common","weight":1.0,"default_price":"5 gp","default_qty":1,"stack_limit":20,"description":"A smelted silver bar used in jewelry, runed weapons, and holy gear. Softer than iron; requires a delicate hand.","tags":"material,metal,crafting,profession:blacksmith,profession:jeweler,shop:blacksmith"},
    {"id":"mat_adamantine_shard","name":"Adamantine Shard","category":"Material","rarity":"Rare","weight":1.0,"default_price":"50 gp","default_qty":1,"stack_limit":5,"description":"A fragment of adamantine ore, nearly unworkable without a master smith's tools. Used in elite armor reinforcement and special weapons.","tags":"material,metal,crafting,profession:blacksmith,source:mining"},
    {"id":"mat_darkwood_plank","name":"Darkwood Plank","category":"Material","rarity":"Uncommon","weight":2.0,"default_price":"8 gp","default_qty":1,"stack_limit":10,"description":"Dense black-grained timber from deep forest trees. Lightweight yet strong; favored for bows, staves, and wand housings.","tags":"material,wood,crafting,profession:woodworker,source:forest"},
    {"id":"mat_deepmoss_herb","name":"Deepmoss Herb","category":"Material","rarity":"Common","weight":0.1,"default_price":"4 sp","default_qty":1,"stack_limit":20,"description":"A spongy cave moss with subtle cooling properties, used in recovery tonics and skin salves.","tags":"material,herb,crafting,profession:herbalist,source:foraging"},
    {"id":"mat_brimstone_crystal","name":"Brimstone Crystal","category":"Material","rarity":"Uncommon","weight":0.5,"default_price":"12 gp","default_qty":1,"stack_limit":10,"description":"A yellow-green mineral used in fire tonics, alchemical charges, and signal powder. Crackles when struck.","tags":"material,crystal,alchemy,crafting,profession:alchemist,source:mining"},
    {"id":"mat_copper_wire_spool","name":"Copper Wire Spool","category":"Material","rarity":"Common","weight":0.3,"default_price":"2 gp","default_qty":1,"stack_limit":20,"description":"Fine copper wire on a small reel; used in tinker circuits, trap springs, and signal relays.","tags":"material,metal,tinker,crafting,profession:tinkering"},
    {"id":"mat_sea_oak_plank","name":"Sea-Oak Plank","category":"Material","rarity":"Common","weight":5.0,"default_price":"3 gp","default_qty":1,"stack_limit":10,"description":"Waterlogged-resistant oak plank used in ship repairs, dock frames, and weatherproof field furniture.","tags":"material,wood,pirate,crafting,profession:shipwright,source:forest"},
    {"id":"mat_saltpetre_pouch","name":"Saltpetre Pouch","category":"Material","rarity":"Common","weight":0.5,"default_price":"6 sp","default_qty":1,"stack_limit":20,"description":"Dried saltpetre crystals used in alchemical charges, flash powder, and preservative brines.","tags":"material,alchemy,crafting,profession:alchemist,shop:alchemist"},
    {"id":"mat_wyvern_scale","name":"Wyvern Scale","category":"Material","rarity":"Rare","weight":1.0,"default_price":"25 gp","default_qty":1,"stack_limit":5,"description":"A tough, heat-resistant scale stripped from a wyvern. Prized for armor linings and fire-ward charms.","tags":"material,beast,crafting,profession:leatherworker,source:monster"},
    {"id":"mat_leyline_dust","name":"Leyline Dust","category":"Material","rarity":"Rare","weight":0.1,"default_price":"40 gp","default_qty":1,"stack_limit":5,"description":"Crystallized energy siphoned from leyline convergences. Essential in scroll-making and high-tier enchanting.","tags":"material,arcane,crafting,profession:enchanter,source:leyline"},
    # ── EXPANSION: Mundane adventuring gear ──────────────────────────────────
    {"id":"seq_everlit_torch","name":"Everlit Torch","category":"Gear","rarity":"Uncommon","weight":1,"default_price":"5 gp","description":"A chemically treated torch that burns 4 hours without guttering in wind or rain. Bright 20-foot radius; dim 20 more.","tags":"light,utility,travel,shop:general"},
    {"id":"seq_glowstone","name":"Glowstone","category":"Gear","rarity":"Common","weight":0.2,"default_price":"4 sp","description":"A palm-sized stone coated with bioluminescent paste. Sheds dim light in a 10-foot radius for 8 hours before needing recoating.","tags":"light,utility,travel,shop:general"},
    {"id":"seq_camouflage_netting","name":"Camouflage Netting","category":"Gear","rarity":"Common","weight":5,"default_price":"2 gp","description":"Woven burlap and leaf-strip netting sized to cover a prone figure or a small camp position. Advantage on Stealth checks while hidden beneath it.","tags":"utility,stealth,travel,shop:general"},
    {"id":"seq_tripwire_set","name":"Tripwire Alert Set","category":"Gear","rarity":"Common","weight":1,"default_price":"1 gp","description":"Thin wire, stakes, and a small bell for a 20-foot perimeter alarm. Takes 5 minutes to set. Triggers on contact or pull.","tags":"trap,utility,field_gear,shop:general"},
    {"id":"seq_campfire_kit","name":"Campfire Kit","category":"Gear","rarity":"Common","weight":3,"default_price":"3 gp","description":"Flint, fire steel, oiled tinder, and folding grate for quick camp fires. Includes fuel tabs for wet-weather ignition.","tags":"travel,utility,camp,shop:general"},
    {"id":"seq_navigation_journal","name":"Navigation Journal","category":"Gear","rarity":"Common","weight":1,"default_price":"3 gp","description":"A gridded blank-page journal with compass rose prints and scale rulers pressed into the cover boards.","tags":"navigation,writing,utility,shop:general"},
    {"id":"seq_waterproof_satchel","name":"Waterproof Oilcloth Satchel","category":"Gear","rarity":"Common","weight":1,"default_price":"4 gp","description":"An oilcloth bag with wax-sealed flap. Keeps contents dry in rain, splashes, and brief submersion.","tags":"container,pirate,travel,shop:general"},
    {"id":"seq_medical_splint","name":"Field Splint","category":"Gear","rarity":"Common","weight":0.5,"default_price":"5 sp","description":"Paired hardwood staves with binding cloth for immobilizing a broken limb. Standard medic supply.","tags":"field_medicine,tool,shop:general"},
    {"id":"seq_listening_cone","name":"Listening Cone","category":"Tool","rarity":"Common","weight":0.3,"default_price":"2 gp","description":"A copper ear trumpet that amplifies quiet sounds through walls and doors. Advantage on Perception checks involving sound through barriers.","tags":"tool,utility,profession:tinkering"},
    {"id":"seq_parchment_roll","name":"Parchment Roll (5 sheets)","category":"Gear","rarity":"Common","weight":0.2,"default_price":"1 sp","description":"A rolled set of five blank parchment sheets for maps, notes, and field correspondence.","tags":"writing,utility,shop:general"},
    {"id":"seq_chalk_bundle","name":"Colored Chalk Bundle","category":"Gear","rarity":"Common","weight":0.1,"default_price":"2 sp","description":"Six sticks of chalk in red, white, and blue for map marking, trail blazing, and coded field signals.","tags":"writing,utility,navigation,shop:general"},
    {"id":"seq_grapple_line_kit","name":"Grapple and Line Kit","category":"Gear","rarity":"Common","weight":4,"default_price":"6 gp","description":"A compact steel grapple with 40-foot silkweave line and belt clip. More reliable than a bare grappling hook for quick work.","tags":"traversal,utility,climb,shop:general"},
    {"id":"seq_repair_cement","name":"Iron Repair Cement","category":"Consumable","rarity":"Common","weight":0.3,"default_price":"2 gp","description":"A fast-setting mineral paste for sealing cracks in armor, masonry, and hulls. Sets hard in 10 minutes.","tags":"consumable,repair,utility,shop:general"},
    # ── EXPANSION: Consumables — field medicine, utility ─────────────────────
    {"id":"seq_antitoxin_salve","name":"Antitoxin Salve","category":"Consumable","rarity":"Common","weight":0.2,"default_price":"15 gp","description":"A topical paste that slows poison absorption when applied to a fresh wound. Advantage on Con saves vs contact or ingested poisons for 30 minutes.","tags":"consumable,field_medicine,profession:herbalist,shop:alchemist"},
    {"id":"seq_fever_break_draught","name":"Fever-Break Draught","category":"Consumable","rarity":"Common","weight":0.5,"default_price":"6 gp","description":"A sharp herbal brew used to clear fever and restore focus. Removes the Poisoned condition caused by disease effects (DM discretion).","tags":"consumable,field_medicine,craftable,profession:herbalist,shop:alchemist"},
    {"id":"seq_numbing_poultice","name":"Numbing Poultice","category":"Consumable","rarity":"Common","weight":0.2,"default_price":"4 gp","description":"A damp clay-and-herb wrap that dulls sharp pain and slows bleeding from shallow cuts.","tags":"consumable,field_medicine,craftable,profession:herbalist,shop:alchemist"},
    {"id":"seq_quick_flare","name":"Quick-Burn Flare","category":"Consumable","rarity":"Common","weight":0.3,"default_price":"3 sp","description":"A chemical flare that burns brilliant white for 10 minutes and can be seen for a mile at night.","tags":"consumable,light,signal,pirate,shop:general"},
    {"id":"seq_healing_salve_minor","name":"Minor Healing Salve","category":"Consumable","rarity":"Common","weight":0.3,"default_price":"4 gp","description":"A waxy herb salve for minor wounds. Stabilizes a dying creature when applied; grants 1 HP of healing.","tags":"consumable,field_medicine,craftable,profession:herbalist,shop:alchemist"},
    {"id":"seq_ashguard_oil","name":"Ashguard Oil","category":"Consumable","rarity":"Uncommon","weight":0.3,"default_price":"18 gp","description":"A gritty mineral oil applied to skin or cloth. Advantage on saves vs fire exposure for 1 hour.","tags":"consumable,resistance,alchemy,profession:alchemist,shop:alchemist"},
    {"id":"seq_cold_salt_pack","name":"Cold Salt Pack","category":"Consumable","rarity":"Common","weight":0.4,"default_price":"2 gp","description":"A cloth sack filled with salt and brine crystals. Reduces swelling and numbs injury sites; practical medic gear.","tags":"consumable,field_medicine,shop:general"},
    {"id":"seq_smelling_salts","name":"Smelling Salts","category":"Consumable","rarity":"Common","weight":0.1,"default_price":"5 sp","description":"Ammonia-laced crystals that revive unconscious creatures. Use as an action to wake one unconscious creature within reach.","tags":"consumable,field_medicine,shop:general,shop:alchemist"},
    # ── EXPANSION: Pirate gear ─────────────────────────────────────────────────
    {"id":"seq_corsair_vest","name":"Corsair's Boiled-Leather Vest","category":"Armor","rarity":"Uncommon","weight":8,"default_price":"38 gp","description":"Boiled and lacquered leather vest worn over a shirt. AC 12 + Dex modifier (light armor). A staple for corsairs who want mobility without full armor.","tags":"armor,pirate,light,craftable,profession:leatherworker"},
    {"id":"seq_nav_chart","name":"Navigation Chart","category":"Gear","rarity":"Common","weight":0.3,"default_price":"8 gp","description":"An accurate coastal or sea chart with depth soundings, reef marks, and trade route overlays.","tags":"pirate,navigation,utility,shop:general"},
    {"id":"seq_anchor_spike","name":"Anchor Spike","category":"Weapon","rarity":"Common","weight":6,"default_price":"8 gp","description":"A sharpened iron anchor-stake that doubles as a brutal bludgeoning weapon in dock fights. Treat as a warhammer for damage.","tags":"weapon,pirate,shop:blacksmith"},
    {"id":"seq_pirates_medallion","name":"Corsair's Medallion","category":"Trinket","rarity":"Common","weight":0.1,"default_price":"1 gp","description":"A worn iron disc bearing a crossed-anchor crest. Marks the wearer as sailing crew in port cultures.","tags":"trinket,pirate,shop:general"},
    {"id":"seq_rum_flask","name":"Rum Flask","category":"Consumable","rarity":"Common","weight":1,"default_price":"5 cp","description":"A dented tin flask of naval rum. Drinking grants advantage on Persuasion with sailors for 1 hour, but disadvantage on Perception.","tags":"consumable,pirate,morale,shop:general"},
    {"id":"seq_tide_lantern","name":"Tide Lantern","category":"Gear","rarity":"Uncommon","weight":2,"default_price":"22 gp","description":"A sealed brass lantern filled with bioluminescent sea-oil that burns even in rain or spray. Bright 20-foot radius; dim 20 more. Lasts 8 hours per fill.","tags":"light,pirate,navigation,profession:tinkering"},
    {"id":"seq_boarding_shield","name":"Boarding Shield","category":"Armor","rarity":"Uncommon","weight":7,"default_price":"30 gp","description":"A compact circular iron-studded shield. Provides the standard +2 AC bonus and can be used to shove opponents in tight corridors.","tags":"armor,shield,pirate,craftable,profession:blacksmith"},
    {"id":"seq_captains_log","name":"Captain's Log Book","category":"Gear","rarity":"Common","weight":1,"default_price":"2 gp","description":"A hardbound logbook for recording voyages, cargo manifests, and crew notes.","tags":"pirate,writing,navigation,shop:general"},
    {"id":"seq_tidewatch_compass","name":"Tidewatch Compass","category":"Tool","rarity":"Common","weight":0.5,"default_price":"12 gp","description":"A sea-grade compass with moon-phase and tidal indicator dials for coastal navigation.","tags":"pirate,navigation,tool,shop:general"},
    # ── EXPANSION: Tinker gear ────────────────────────────────────────────────
    {"id":"seq_mechanical_notebook","name":"Tinker's Schematic Notebook","category":"Gear","rarity":"Common","weight":1,"default_price":"4 gp","description":"Graph-ruled pages bound in riveted boards. Used for technical drawings, mechanism diagrams, and field notes.","tags":"tinker,writing,tool,profession:tinkering"},
    {"id":"seq_lens_array","name":"Tinker Lens Array","category":"Tool","rarity":"Uncommon","weight":1,"default_price":"28 gp","description":"A fold-out arm with three magnifying lenses and a reticle for micro-work, circuit inspection, and detail carving.","tags":"tinker,tool,profession:tinkering,shop:magic"},
    {"id":"seq_spark_coil","name":"Spark Coil","category":"Gear","rarity":"Uncommon","weight":1,"default_price":"20 gp","description":"A hand-wound coil that generates a controlled static charge. Used to test circuits, stun small mechanisms, and slow-recharge arc batteries.","tags":"tinker,utility,profession:tinkering,shop:blacksmith"},
    {"id":"seq_clockwork_key","name":"Clockwork Skeleton Key","category":"Tool","rarity":"Uncommon","weight":0.3,"default_price":"35 gp","description":"A multi-bit adjustable key that reshapes to common clockwork pin configurations. Advantage on checks to open mechanical locks.","tags":"tinker,tool,profession:tinkering,shop:black_market"},
    {"id":"seq_field_forge_kit","name":"Field Forge Kit","category":"Tool","rarity":"Common","weight":8,"default_price":"18 gp","description":"Compact anvil block, bellows, tongs, and punch set for emergency metalwork and hardpoint repairs in the field.","tags":"tinker,tool,profession:blacksmith,shop:blacksmith"},
    {"id":"seq_tinker_goggles_basic","name":"Work Goggles","category":"Gear","rarity":"Common","weight":0.3,"default_price":"4 gp","description":"Clear-lensed eye protection for sparks, smoke, and bright flash. Prevents blindness from flash capsules and open forge work.","tags":"tinker,tool,protection,profession:tinkering,shop:blacksmith"},
    {"id":"seq_circuit_paste","name":"Conductive Circuit Paste","category":"Material","rarity":"Common","weight":0.2,"default_price":"3 gp","description":"A metallic adhesive paste used to bond wire junctions and complete arc circuits in tinker devices.","tags":"material,tinker,crafting,profession:tinkering,shop:blacksmith"},
    {"id":"seq_portable_press","name":"Portable Stamping Press","category":"Tool","rarity":"Common","weight":4,"default_price":"10 gp","description":"A compact hand-press for stamping wax seals, sigil marks, and rivet heads in field work.","tags":"tinker,tool,utility,profession:tinkering"},
    # ── EXPANSION: Recipe items for new craftables ────────────────────────────
    {"id":"seq_recipe_iron_buckler","name":"Recipe: Iron Buckler","category":"Recipe","rarity":"Common","weight":0,"default_price":"7 gp","description":"Smithing notes for a compact iron buckler with a hide-wrapped grip.","tags":"recipe,profession:blacksmith,crafts:iron_buckler"},
    {"id":"seq_recipe_scaled_vest","name":"Recipe: Scaled Leather Vest","category":"Recipe","rarity":"Common","weight":0,"default_price":"8 gp","description":"Pattern for a scale-reinforced leather vest with buckled side straps.","tags":"recipe,profession:leatherworker,crafts:scaled_vest"},
    {"id":"seq_recipe_fever_break_draught","name":"Recipe: Fever-Break Draught","category":"Recipe","rarity":"Common","weight":0,"default_price":"5 gp","description":"Herbalist notes for a fast fever-break tonic using sunleaf and deepmoss herb.","tags":"recipe,profession:herbalist,crafts:fever_break_draught"},
    {"id":"seq_recipe_numbing_poultice","name":"Recipe: Numbing Poultice","category":"Recipe","rarity":"Common","weight":0,"default_price":"4 gp","description":"Simple field formula for a frostcap-and-sunleaf poultice that dulls sharp pain.","tags":"recipe,profession:herbalist,crafts:numbing_poultice"},
    {"id":"seq_recipe_recurve_bow","name":"Recipe: Recurve Hunting Bow","category":"Recipe","rarity":"Common","weight":0,"default_price":"10 gp","description":"Bowyer pattern for a recurve bow using darkwood and spider-silk string.","tags":"recipe,profession:woodworker,profession:bowyer,crafts:recurve_bow"},
    {"id":"seq_recipe_arc_lantern","name":"Recipe: Arc Lantern","category":"Recipe","rarity":"Uncommon","weight":0,"default_price":"15 gp","description":"Tinker schematics for a battery-powered arc lantern that runs without oil.","tags":"recipe,profession:tinkering,crafts:arc_lantern"},
    {"id":"seq_recipe_seafarers_amulet","name":"Recipe: Seafarer's Amulet","category":"Recipe","rarity":"Uncommon","weight":0,"default_price":"12 gp","description":"Jeweler's mounting notes for a coral-set tide charm amulet.","tags":"recipe,profession:jeweler,crafts:seafarers_amulet"},
    {"id":"seq_recipe_corsair_vest","name":"Recipe: Corsair's Boiled-Leather Vest","category":"Recipe","rarity":"Common","weight":0,"default_price":"9 gp","description":"Leatherworker's pattern for a boiled-leather corsair vest with lacquer finish.","tags":"recipe,profession:leatherworker,crafts:corsair_vest"},
    {"id":"seq_recipe_tar_caulk_kit","name":"Recipe: Tar Caulk Kit","category":"Recipe","rarity":"Common","weight":0,"default_price":"4 gp","description":"Shipwright notes for mixing a field-grade tar caulk for hull and deck repairs.","tags":"recipe,profession:shipwright,crafts:tar_caulk_kit"},
    {"id":"seq_recipe_winter_wrap","name":"Recipe: Winter Travel Wrap","category":"Recipe","rarity":"Common","weight":0,"default_price":"6 gp","description":"Tailor's pattern for a layered cold-weather cloak using scaled scraps as inner lining.","tags":"recipe,profession:tailor,crafts:winter_wrap"},
    {"id":"seq_recipe_clockwork_sentry","name":"Recipe: Clockwork Sentry","category":"Recipe","rarity":"Rare","weight":0,"default_price":"25 gp","description":"Advanced tinker schematics for a wound-spring perimeter sentry with integrated alert mechanism.","tags":"recipe,profession:tinkering,crafts:clockwork_sentry"},
    {"id":"seq_recipe_padded_surcoat","name":"Recipe: Padded Surcoat","category":"Recipe","rarity":"Common","weight":0,"default_price":"7 gp","description":"Tailor's pattern for a padded surcoat stitched over a leather base for light protection.","tags":"recipe,profession:tailor,crafts:padded_surcoat"},
]


def _seed_srd_mundane_equipment() -> None:
    """Seed srd_items with built-in mundane equipment list (INSERT OR IGNORE)."""
    with get_conn() as conn:
        for item in _SRD_MUNDANE:
            conn.execute(
                "INSERT OR IGNORE INTO srd_items (id, name, category, rarity, weight, default_price, default_qty, description, tags, stack_limit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item["id"], item["name"], item.get("category","Gear"), item.get("rarity","Common"),
                 float(item.get("weight",0)), item.get("default_price",""), int(item.get("default_qty",1)),
                 item.get("description","")[:2000], item.get("tags",""), int(item.get("stack_limit",1)))
            )
        conn.commit()


def get_srd_item_count() -> int:
    """Return the number of SRD items in the database."""
    try:
        with get_conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM srd_items").fetchone()[0]
    except Exception:
        return 0


def get_all_srd_items() -> List[Dict[str, Any]]:
    """Return all SRD items ordered by category and name."""
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM srd_items ORDER BY category, name").fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_srd_items_by_rarity(rarity: str) -> List[Dict[str, Any]]:
    """Return all SRD items with the given rarity (case-insensitive)."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM srd_items WHERE LOWER(rarity)=LOWER(?) ORDER BY name",
                (rarity,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def insert_srd_items_batch(items: List[Dict[str, Any]]) -> tuple[int, int]:
    """Bulk-insert SRD items using INSERT OR IGNORE. Returns (inserted, skipped) counts."""
    if not items:
        return 0, 0
    init_srd_items_table()
    inserted = 0
    skipped = 0
    with get_conn() as conn:
        for item in items:
            try:
                result = conn.execute(
                    """INSERT OR IGNORE INTO srd_items
                       (id, name, category, rarity, weight, default_price, default_qty, description, tags, stack_limit)
                       VALUES (:id, :name, :category, :rarity, :weight, :default_price, :default_qty, :description, :tags, :stack_limit)""",
                    {
                        "id": str(item.get("id", ""))[:80],
                        "name": str(item.get("name", ""))[:80],
                        "category": str(item.get("category", "Gear"))[:40],
                        "rarity": str(item.get("rarity", "Common"))[:32],
                        "weight": float(item.get("weight", 0) or 0),
                        "default_price": str(item.get("default_price", ""))[:32],
                        "default_qty": int(item.get("default_qty", 1) or 1),
                        "description": str(item.get("description", ""))[:2000],
                        "tags": str(item.get("tags", ""))[:200],
                        "stack_limit": int(item.get("stack_limit", 1) or 1),
                    },
                )
                if result.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1
        conn.commit()
    return inserted, skipped
