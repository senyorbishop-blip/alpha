"""Owned-animal pet shop catalog.

Pets are ordinary owned animals (dog/cat/bird/monkey) that a player can buy with
character currency. Ownership is recorded by adding the pet's summon template id
to the character's ``summons.unlockedTemplates`` list, after which the pet rides
the shared summon runtime (summon/move/re-summon/dismiss/command in combat).

This module only carries the *shop* concerns (price, display blurb, ordering).
The combat/runtime stat blocks live in ``server.character.summon_runtime`` and the
summon template definitions live in ``server.character.summon_catalog``.
"""
from __future__ import annotations

import copy
from typing import Any

from server.character.summon_catalog import get_summon_template

# Pet ownership is recorded against this synthetic feature id so it can be
# distinguished from class-granted summon unlocks during reconciliation.
PET_SOURCE_FEATURE_ID = "pet-ownership"
PET_SOURCE_CLASS_ID = "pet"


# Ordered shop catalog. Each entry references a pet summon template id and carries
# the price (in gold pieces) plus presentation metadata for the buy panel.
PET_SHOP_CATALOG: dict[str, dict[str, Any]] = {
    "pet-dog": {
        "templateId": "pet-dog",
        "name": "Dog",
        "emoji": "\U0001F415",  # 🐕
        "priceGp": 25,
        "order": 1,
        "blurb": "A loyal hound. Keen smell, fast on its feet, and happy to harry your foes.",
    },
    "pet-cat": {
        "templateId": "pet-cat",
        "name": "Cat",
        "emoji": "\U0001F408",  # 🐈
        "priceGp": 10,
        "order": 2,
        "blurb": "An aloof but agile companion. Climbs well and slips through tight spaces.",
    },
    "pet-bird": {
        "templateId": "pet-bird",
        "name": "Bird",
        "emoji": "\U0001F985",  # 🦅
        "priceGp": 35,
        "order": 3,
        "blurb": "A trained bird of prey. Scouts from the air and dives on exposed targets.",
    },
    "pet-monkey": {
        "templateId": "pet-monkey",
        "name": "Monkey",
        "emoji": "\U0001F412",  # 🐒
        "priceGp": 50,
        "order": 4,
        "blurb": "A clever, nimble primate. Grabs objects, climbs anything, and escapes danger.",
    },
}


def is_pet_template(template_id: Any) -> bool:
    """Return True if the given summon template id is an ownable pet."""
    return str(template_id or "").strip().lower() in PET_SHOP_CATALOG


def get_pet_shop_entry(template_id: Any) -> dict[str, Any] | None:
    """Return a copy of the shop entry for a pet template id, or None."""
    key = str(template_id or "").strip().lower()
    row = PET_SHOP_CATALOG.get(key)
    return copy.deepcopy(row) if isinstance(row, dict) else None


def get_pet_price_gp(template_id: Any) -> int | None:
    """Return the gold-piece price for a pet template id, or None if unknown."""
    entry = PET_SHOP_CATALOG.get(str(template_id or "").strip().lower())
    if not isinstance(entry, dict):
        return None
    try:
        return max(0, int(entry.get("priceGp") or 0))
    except Exception:
        return 0


def list_pet_shop_entries() -> list[dict[str, Any]]:
    """Return the ordered list of purchasable pets enriched with template data."""
    out: list[dict[str, Any]] = []
    for entry in sorted(PET_SHOP_CATALOG.values(), key=lambda row: int(row.get("order") or 0)):
        template = get_summon_template(entry.get("templateId"))
        if not isinstance(template, dict):
            # Defensive: a shop entry without a backing template is unusable.
            continue
        merged = copy.deepcopy(entry)
        merged["summonGroupId"] = str(template.get("variantGroup") or "").strip().lower()
        merged["size"] = str(template.get("size") or "")
        merged["movement"] = copy.deepcopy(template.get("movement") or {})
        out.append(merged)
    return out
