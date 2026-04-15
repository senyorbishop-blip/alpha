"""
server/encumbrance.py — D&D 5e encumbrance calculation engine.

Provides weight lookup, carry-capacity thresholds, extradimensional container
support, and speed-penalty computation.  All functions are pure (no I/O) so
they can be called freely from handlers or tests.
"""
from __future__ import annotations
from typing import Any
import math
import re

# ─── Item weight tables ───────────────────────────────────────────────────────

# Exact-name lookup (lowercase stripped).
ITEM_WEIGHT_BY_NAME: dict[str, float] = {
    # Weapons
    "dagger": 1.0,
    "dart": 0.25,
    "handaxe": 2.0,
    "light hammer": 2.0,
    "sickle": 2.0,
    "club": 2.0,
    "greatclub": 10.0,
    "javelin": 2.0,
    "quarterstaff": 4.0,
    "spear": 3.0,
    "shortsword": 2.0,
    "short sword": 2.0,
    "scimitar": 3.0,
    "rapier": 2.0,
    "longsword": 3.0,
    "long sword": 3.0,
    "battleaxe": 4.0,
    "flail": 2.0,
    "morningstar": 4.0,
    "trident": 4.0,
    "war pick": 2.0,
    "warhammer": 2.0,
    "whip": 3.0,
    "greatsword": 6.0,
    "great sword": 6.0,
    "greataxe": 7.0,
    "glaive": 6.0,
    "halberd": 6.0,
    "lance": 6.0,
    "maul": 10.0,
    "pike": 18.0,
    "heavy crossbow": 18.0,
    "light crossbow": 5.0,
    "hand crossbow": 3.0,
    "shortbow": 2.0,
    "short bow": 2.0,
    "longbow": 2.0,
    "long bow": 2.0,
    "sling": 0.0,
    "blowgun": 1.0,
    "net": 3.0,
    "shield": 6.0,
    "buckler": 3.0,
    # Ammunition
    "arrow": 0.05,
    "arrows (20)": 1.0,
    "bolt": 0.075,
    "bolts (20)": 1.5,
    "sling bullet": 0.075,
    # Armour
    "padded armour": 8.0, "padded armor": 8.0,
    "leather armour": 10.0, "leather armor": 10.0,
    "studded leather armour": 13.0, "studded leather armor": 13.0,
    "hide armour": 12.0, "hide armor": 12.0,
    "chain shirt": 20.0,
    "scale mail": 45.0,
    "breastplate": 20.0,
    "half plate armour": 40.0, "half plate armor": 40.0,
    "ring mail": 40.0,
    "chain mail": 55.0,
    "splint armour": 60.0, "splint armor": 60.0,
    "plate armour": 65.0, "plate armor": 65.0,
    # Common gear
    "backpack": 5.0,
    "bedroll": 7.0,
    "blanket": 3.0,
    "book": 5.0,
    "candle": 0.0,
    "chain (10 ft)": 10.0,
    "crowbar": 5.0,
    "grappling hook": 4.0,
    "hammer": 3.0,
    "ink": 0.0,
    "ladder (10 ft)": 25.0,
    "lantern": 1.0,
    "hooded lantern": 2.0,
    "bullseye lantern": 2.0,
    "lock": 1.0,
    "magnifying glass": 0.0,
    "mirror": 0.5,
    "steel mirror": 0.5,
    "oil (flask)": 1.0,
    "paper": 0.0,
    "parchment": 0.0,
    "pick (miner's)": 10.0,
    "piton": 0.25,
    "pole (10 ft)": 7.0,
    "potion": 0.5,
    "potion of healing": 0.5,
    "pouch": 1.0,
    "quiver": 1.0,
    "rations": 2.0,
    "ration": 2.0,
    "iron rations": 2.0,
    "rope": 10.0,
    "rope (50 ft)": 10.0,
    "rope (50ft)": 10.0,
    "hempen rope": 10.0,
    "silk rope": 5.0,
    "sack": 0.5,
    "sealing wax": 0.0,
    "shovel": 5.0,
    "signal whistle": 0.0,
    "signet ring": 0.0,
    "soap": 0.0,
    "spellbook": 3.0,
    "spike (iron)": 0.5,
    "tent": 20.0,
    "tinderbox": 1.0,
    "torch": 1.0,
    "vial": 0.0,
    "waterskin": 5.0,
    "whetstone": 1.0,
    # Containers
    "chest": 25.0,
    "barrel": 70.0,
    "basket": 2.0,
    "bucket": 2.0,
    "case (crossbow bolt)": 1.0,
    "flask": 1.0,
    "jug": 4.0,
    "pot (iron)": 10.0,
    "vial": 0.0,
}

# Substring / keyword fallback weights (checked after exact match).
# Format: (keyword, weight).  First match wins.
_KEYWORD_WEIGHTS: list[tuple[str, float]] = [
    ("plate",         65.0),
    ("splint",        60.0),
    ("chain mail",    55.0),
    ("chain shirt",   20.0),
    ("scale mail",    45.0),
    ("ring mail",     40.0),
    ("half plate",    40.0),
    ("breastplate",   20.0),
    ("hide",          12.0),
    ("studded",       13.0),
    ("leather",       10.0),
    ("padded",         8.0),
    # armour / armor keyword with no other match → medium guess
    ("armour",        30.0),
    ("armor",         30.0),
    ("potion",         0.5),
    ("ration",         2.0),
    ("arrows",         0.05),
    ("arrow",          0.05),
    ("bolts",          0.075),
    ("bolt",           0.075),
    ("rope",          10.0),
    ("shield",         6.0),
    ("staff",          4.0),
    ("sword",          3.0),
    ("axe",            4.0),
    ("bow",            2.0),
    ("crossbow",       5.0),
    ("torch",          1.0),
    ("book",           5.0),
    ("pack",           5.0),
]

# Weight by item category key (lower-cased).
ITEM_WEIGHT_BY_CATEGORY: dict[str, float] = {
    "light armor": 13.0, "light armour": 13.0,
    "medium armor": 30.0, "medium armour": 30.0,
    "heavy armor": 60.0, "heavy armour": 60.0,
    "shield": 6.0,
    "weapon": 3.0,
    "melee weapon": 3.0,
    "ranged weapon": 2.0,
    "ammunition": 0.05,
    "potion": 0.5,
    "scroll": 0.0,
    "wand": 1.0,
    "staff": 4.0,
    "rod": 2.0,
    "ring": 0.0,
    "amulet": 0.0,
    "trinket": 0.0,
    "gem": 0.0,
    "tool": 2.0,
    "gear": 1.0,
    "adventuring gear": 1.0,
    "consumable": 0.5,
    "food": 1.0,
    "treasure": 0.0,
    "misc": 0.5,
    "material": 0.5,
}

# Weight by item_type field (lower-cased).
ITEM_WEIGHT_BY_TYPE: dict[str, float] = {
    "light_armor": 13.0, "light_armour": 13.0,
    "medium_armor": 30.0, "medium_armour": 30.0,
    "heavy_armor": 60.0, "heavy_armour": 60.0,
    "shield": 6.0,
    "melee_weapon": 3.0,
    "ranged_weapon": 2.0,
    "weapon": 3.0,
    "potion": 0.5,
    "scroll": 0.0,
    "wand": 1.0,
    "staff": 4.0,
    "rod": 2.0,
    "ring": 0.0,
    "amulet": 0.0,
    "trinket": 0.0,
    "ammunition": 0.05,
    "consumable": 0.5,
    "misc": 0.5,
}

DEFAULT_ITEM_WEIGHT: float = 0.5  # fallback for unknown items

_WEIGHT_TEXT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lb|lbs|pound|pounds)\b", re.IGNORECASE)

# ─── Extradimensional containers ─────────────────────────────────────────────

# Keyed by lowercase name fragment.  On a match the entry dict is merged into
# the inventory item.
EXTRADIMENSIONAL_CONTAINERS: dict[str, dict[str, Any]] = {
    "bag of holding": {
        "extradimensional": True,
        "own_weight_lbs": 15.0,
        "capacity_lbs": 500.0,
        "volume_ft3": 64.0,
        "is_devouring": False,
    },
    "handy haversack": {
        "extradimensional": True,
        "own_weight_lbs": 5.0,
        "capacity_lbs": 120.0,
        "volume_ft3": None,
        "is_devouring": False,
    },
    "portable hole": {
        "extradimensional": True,
        "own_weight_lbs": 0.0,
        "capacity_lbs": 1000.0,
        "volume_ft3": 282.0,
        "is_devouring": False,
    },
    "bag of devouring": {
        "extradimensional": True,
        "own_weight_lbs": 5.0,
        "capacity_lbs": 0.0,
        "volume_ft3": None,
        "is_devouring": True,
    },
}

# Mundane inventory containers/mount-hauling profiles (5e-inspired defaults).
# These are not extradimensional; contents still count toward carried weight.
MUNDANE_CONTAINERS: dict[str, dict[str, Any]] = {
    "riding horse": {
        "is_container": True,
        "own_weight_lbs": 0.0,
        "capacity_lbs": 480.0,
        "volume_ft3": None,
        "is_devouring": False,
    },
    "draft horse": {
        "is_container": True,
        "own_weight_lbs": 0.0,
        "capacity_lbs": 540.0,
        "volume_ft3": None,
        "is_devouring": False,
    },
    "cart": {
        "is_container": True,
        "own_weight_lbs": 0.0,
        "capacity_lbs": 300.0,
        "volume_ft3": None,
        "is_devouring": False,
    },
}

# ─── Size capacity multipliers ───────────────────────────────────────────────

SIZE_MULTIPLIERS: dict[str, float] = {
    "tiny":        0.25,
    "small":       0.5,
    "medium":      1.0,
    "large":       2.0,
    "huge":        4.0,
    "gargantuan":  8.0,
}

# ─── Encumbrance state labels ────────────────────────────────────────────────

ENC_NONE   = "unencumbered"
ENC_LIGHT  = "encumbered"
ENC_HEAVY  = "heavily_encumbered"
ENC_OVER   = "over_capacity"

# Two-handed / heavy weapon names that Tiny characters cannot equip
_TINY_BLOCKED_WEAPON_KEYWORDS = {
    "greatsword", "great sword", "greataxe", "great axe",
    "maul", "pike", "halberd", "glaive", "heavy crossbow",
    "longbow", "long bow", "lance", "greatclub",
}
# Heavy armor types that Small characters cannot equip (without DM override)
_SMALL_BLOCKED_ARMOR_TYPES = {"heavy_armor", "heavy_armour"}
_SMALL_BLOCKED_ARMOR_CATEGORIES = {"heavy armor", "heavy armour"}


# ─── Public helpers ───────────────────────────────────────────────────────────

def get_item_weight(item: dict) -> float:
    """Return per-unit weight in lbs for one inventory item dict."""
    # 1. Explicit override stored on the item
    explicit = item.get("weight_lbs")
    if explicit is not None:
        try:
            return max(0.0, float(explicit))
        except Exception:
            pass

    # 1.5 Weight hints embedded in imported text fields (e.g. "1 lb.")
    for field in ("weight", "notes", "effect", "unidentified_description"):
        raw = item.get(field)
        if raw is None:
            continue
        match = _WEIGHT_TEXT_RE.search(str(raw))
        if not match:
            continue
        try:
            return max(0.0, float(match.group(1)))
        except Exception:
            continue

    name_lower = str(item.get("name") or "").strip().lower()

    # 2. Exact name lookup
    if name_lower in ITEM_WEIGHT_BY_NAME:
        return ITEM_WEIGHT_BY_NAME[name_lower]

    # 3. Keyword substring lookup
    for kw, w in _KEYWORD_WEIGHTS:
        if kw in name_lower:
            return w

    # 4. Category lookup
    cat = str(item.get("category") or "").strip().lower()
    if cat in ITEM_WEIGHT_BY_CATEGORY:
        return ITEM_WEIGHT_BY_CATEGORY[cat]

    # 5. item_type lookup
    itype = str(item.get("item_type") or "").strip().lower()
    if itype in ITEM_WEIGHT_BY_TYPE:
        return ITEM_WEIGHT_BY_TYPE[itype]

    return DEFAULT_ITEM_WEIGHT


def get_size_multiplier(size: str) -> float:
    return SIZE_MULTIPLIERS.get(str(size or "medium").strip().lower(), 1.0)


def _get_carry_capacity_scalar(strength: int, size: str = "medium") -> float:
    str_val = max(1, min(30, int(strength or 10)))
    base_capacity = math.floor((str_val * 15.0) * 1.5) + 20
    return base_capacity * get_size_multiplier(size)


def get_carry_capacity(strength_or_character: Any, size: str = "medium") -> Any:
    """Carry capacity helper.

    Backwards compatibility:
    - get_carry_capacity(strength, size) -> float
    New character-native mode:
    - get_carry_capacity(character_document: dict) -> dict payload
    """
    if isinstance(strength_or_character, dict):
        character_document = strength_or_character
        abilities = character_document.get("abilities", {})
        ability_scores = abilities.get("scores", {}) if isinstance(abilities, dict) else {}
        str_score = int(ability_scores.get("str", abilities.get("str", 10)) or 10) if isinstance(abilities, dict) else 10
        carry_capacity = math.floor((str_score * 15) * 1.5) + 20
        push_drag_lift = str_score * 30
        encumbered_threshold = carry_capacity / 3
        heavily_encumbered = (carry_capacity * 2) / 3
        return {
            "carryCapacity": carry_capacity,
            "pushDragLift": push_drag_lift,
            "encumberedThreshold": encumbered_threshold,
            "heavilyEncumberedThreshold": heavily_encumbered,
        }
    return _get_carry_capacity_scalar(int(strength_or_character or 10), size)


def get_encumbrance_thresholds(strength: int, size: str = "medium") -> dict:
    capacity = _get_carry_capacity_scalar(strength, size)
    return {
        ENC_LIGHT:  capacity / 3.0,
        ENC_HEAVY:  (capacity * 2.0) / 3.0,
        ENC_OVER:   capacity,
    }


def get_total_carried_weight(inventory: list, gold_units: int = 0) -> float:
    """
    Total weight the character physically carries.

    Items inside an extradimensional container count only as the container's
    own_weight_lbs (its contents are weightless from the carrier's perspective).
    Coins: 50 gp = 1 lb  →  1 unit (= 0.01 gp) = 1/5000 lb.
    """
    total = 0.0
    for item in inventory or []:
        if not isinstance(item, dict):
            continue
        if item.get("extradimensional"):
            # Only the bag itself is counted, not its contents
            total += float(item.get("own_weight_lbs") or 0.0)
        elif is_inventory_container(item):
            own_weight = item.get("own_weight_lbs")
            if own_weight is None:
                own_weight = get_item_weight(item)
            total += max(0.0, float(own_weight or 0.0))
            total += get_bag_contents_weight(item)
        else:
            qty = max(1, int(item.get("qty") or 1))
            total += get_item_weight(item) * qty
    # 50 gp = 5000 units = 1 lb
    total += max(0.0, float(gold_units or 0)) / 5000.0
    return round(total, 2)


def get_encumbrance_state(strength: int, size: str, total_weight: float) -> str:
    t = get_encumbrance_thresholds(strength, size)
    if total_weight > t[ENC_OVER]:
        return ENC_OVER
    if total_weight > t[ENC_HEAVY]:
        return ENC_HEAVY
    if total_weight > t[ENC_LIGHT]:
        return ENC_LIGHT
    return ENC_NONE


def get_speed_penalty(state: str) -> int:
    return {ENC_LIGHT: -10, ENC_HEAVY: -20, ENC_OVER: -9999}.get(state, 0)


def get_effective_speed(base_speed: int, strength: int, size: str, total_weight: float) -> int:
    state = get_encumbrance_state(strength, size, total_weight)
    if state == ENC_OVER:
        return 0
    return max(0, int(base_speed or 0) + get_speed_penalty(state))


def auto_tag_extradimensional(entry: dict) -> dict:
    """
    If the item name matches a known container profile, return a copy with
    relevant fields set. Includes both extradimensional and mundane containers.
    """
    name_lower = str(entry.get("name") or "").strip().lower()
    for key, props in EXTRADIMENSIONAL_CONTAINERS.items():
        if key in name_lower:
            updated = dict(entry)
            # Only set if not already explicitly set by the item record
            for k, v in props.items():
                if updated.get(k) is None:
                    updated[k] = v
            if "bag_contents" not in updated:
                updated["bag_contents"] = []
            return updated
    for key, props in MUNDANE_CONTAINERS.items():
        if key in name_lower:
            updated = dict(entry)
            for k, v in props.items():
                if updated.get(k) is None:
                    updated[k] = v
            if "bag_contents" not in updated:
                updated["bag_contents"] = []
            return updated
    return entry


def get_bag_contents_weight(bag: dict) -> float:
    """Total weight of items stored inside a container."""
    return round(get_total_carried_weight(list(bag.get("bag_contents") or []), 0), 2)


def is_inventory_container(item: dict) -> bool:
    """True when an item can hold other inventory items."""
    if not isinstance(item, dict):
        return False
    if item.get("extradimensional") or item.get("is_container"):
        return True
    try:
        return float(item.get("capacity_lbs") or 0.0) > 0.0
    except Exception:
        return False


def check_extradimensional_conflict(outer: dict, inner: dict) -> bool:
    """Returns True if placing inner inside outer would create a rift."""
    return bool(outer.get("extradimensional")) and bool(inner.get("extradimensional"))


def is_oversized_for_size(item: dict, character_size: str) -> tuple[bool, str]:
    """
    Returns (blocked: bool, reason: str).
    Tiny: cannot equip two-handed weapons, medium/heavy armour, shields.
    Small: cannot equip heavy armour.
    """
    size = str(character_size or "medium").strip().lower()
    name_lower = str(item.get("name") or "").strip().lower()
    item_type = str(item.get("item_type") or "").strip().lower()
    category = str(item.get("category") or "").strip().lower()

    if size == "tiny":
        # Two-handed / heavy weapons
        for kw in _TINY_BLOCKED_WEAPON_KEYWORDS:
            if kw in name_lower:
                return True, f"A {item.get('name','item')} is far too large for a Tiny creature to wield or carry."
        # Medium / heavy armour
        if item_type in {"medium_armor", "medium_armour", "heavy_armor", "heavy_armour"} or \
           category in {"medium armor", "medium armour", "heavy armor", "heavy armour", "shield"}:
            return True, f"A Tiny creature cannot wear {item.get('name','this armour')}."

    if size == "small":
        if item_type in _SMALL_BLOCKED_ARMOR_TYPES or category in _SMALL_BLOCKED_ARMOR_CATEGORIES:
            return True, f"Small creatures cannot normally wear {item.get('name','heavy armour')} (DM override available)."

    return False, ""


def extract_str_size_from_profile(profile: dict) -> tuple[int, str]:
    """
    Extract (strength, size) from a stored char-profile dict.
    Returns (10, 'medium') as defaults.
    """
    char_book = profile.get("charBook") or {}
    ability_scores = char_book.get("abilityScores") or {}
    try:
        strength = int(ability_scores.get("strength") or ability_scores.get("str") or 10)
    except Exception:
        strength = 10
    strength = max(1, min(30, strength))

    # Size: check charBook identity section or top-level
    identity = char_book.get("identity") or {}
    size = (
        identity.get("size")
        or char_book.get("size")
        or profile.get("size")
        or "medium"
    )
    return strength, str(size or "medium").strip().lower() or "medium"


def get_str_size_for_user(session: Any, user_id: str) -> tuple[int, str]:
    """
    Best-effort extraction of (strength, size) for a given user_id by looking
    up their char profiles stored on the session.
    Returns (10, 'medium') if nothing found.
    DM-set overrides (enc_str_overrides) take priority over char profiles.
    """
    # DM override takes priority
    str_overrides = dict(getattr(session, "enc_str_overrides", {}) or {})
    override = str_overrides.get(user_id)
    if override and isinstance(override, dict):
        try:
            strength = max(1, min(30, int(override.get("strength") or 10)))
            size = str(override.get("size") or "medium").strip().lower() or "medium"
            return strength, size
        except Exception:
            pass

    from server.session import normalize_profile_owner_key
    user = (getattr(session, "users", {}) or {}).get(user_id)
    if not user:
        return 10, "medium"

    profiles_all = dict(getattr(session, "char_profiles", {}) or {})
    name_key = normalize_profile_owner_key(getattr(user, "name", ""))
    mine = list(profiles_all.get(name_key) or profiles_all.get(user_id) or [])
    if not mine:
        return 10, "medium"

    # Use most-recently-updated profile
    best = max(mine, key=lambda p: float(p.get("updated_at") or 0.0), default=None)
    if not best:
        return 10, "medium"
    return extract_str_size_from_profile(best)


def build_encumbrance_payload(
    inventory: list,
    gold_units: int,
    strength: int,
    size: str,
    encumbrance_settings: dict,
) -> dict:
    """
    Build the full encumbrance summary sent to the client via
    player_inventory_sync.
    """
    settings = encumbrance_settings or {}
    if not settings.get("use_encumbrance", True):
        return {
            "enabled": False,
            "total_weight": 0.0,
            "capacity": 0.0,
            "state": ENC_NONE,
            "speed_penalty": 0,
            "thresholds": {},
            "bags": [],
        }

    total = get_total_carried_weight(inventory, gold_units)
    capacity = _get_carry_capacity_scalar(strength, size)
    thresholds = get_encumbrance_thresholds(strength, size)
    state = get_encumbrance_state(strength, size, total)
    coin_weight = round(max(0.0, float(gold_units or 0)) / 5000.0, 2)

    bags = []
    for item in inventory or []:
        if not isinstance(item, dict) or not is_inventory_container(item):
            continue
        contents = list(item.get("bag_contents") or [])
        contents_weight = get_bag_contents_weight(item)
        cap = float(item.get("capacity_lbs") or 500.0)
        bags.append({
            "id": str(item.get("id") or ""),
            "name": str(item.get("name") or "Container"),
            "own_weight": float(item.get("own_weight_lbs") or 0.0),
            "contents_weight": contents_weight,
            "capacity": cap,
            "fill_pct": round(min(1.0, contents_weight / max(0.001, cap)) * 100, 1),
            "contents": contents,
        })

    return {
        "enabled": True,
        "total_weight": total,
        "capacity": capacity,
        "state": state,
        "speed_penalty": get_speed_penalty(state),
        "thresholds": thresholds,
        "bags": bags,
        "coin_weight": coin_weight,
        "strength": strength,
        "size": size,
    }
