"""Pet shop handlers: buy/own animals as controllable companion tokens.

Pets ride the shared summon runtime. Ownership is recorded by adding the pet's
summon template id to the active character profile's ``summons.unlockedTemplates``
list. Once owned, the pet automatically surfaces in the player's Summon Manager,
where it can be summoned, moved, re-summoned, dismissed, and commanded in combat
just like a class companion.
"""
from __future__ import annotations

import logging

from server.character.pet_catalog import (
    get_pet_price_gp,
    get_pet_shop_entry,
    is_pet_template,
)
from server.character.resolver import resolve_character_runtime
from server.character.summon_runtime import remove_active_summon
from server.character.summon_state import normalize_summon_state
from server.handlers.common import Session, User, manager, save_campaign_async, _broadcast_token_state_sync
from server.handlers.content import _send_char_profiles, _char_profile_bucket_key

logger = logging.getLogger(__name__)

_CURRENCY_IN_COPPER = {"pp": 1000, "gp": 100, "ep": 50, "sp": 10, "cp": 1}


def _find_owner_profile(session: Session, user: User, requested_profile_id: str):
    """Locate the active (or requested) character profile bucket for a user.

    Returns ``(owner_key, profile_index, profile_row)`` or ``("", -1, None)``.
    """
    owner_key = _char_profile_bucket_key(session, user)
    profiles = dict(getattr(session, "char_profiles", {}) or {})
    bucket = list(profiles.get(owner_key) or []) if isinstance(profiles.get(owner_key), list) else []
    target_id = str(requested_profile_id or "").strip()
    if not target_id:
        target_id = str((getattr(session, "active_char_profiles", {}) or {}).get(user.id) or "").strip()
    if target_id:
        for idx, row in enumerate(bucket):
            if isinstance(row, dict) and str(row.get("id") or "").strip() == target_id:
                return owner_key, idx, row
    for idx, row in enumerate(bucket):
        if isinstance(row, dict):
            return owner_key, idx, row
    return owner_key, -1, None


def _currency_block(native: dict) -> dict:
    equipment = native.get("equipment") if isinstance(native.get("equipment"), dict) else {}
    currency = equipment.get("currency") if isinstance(equipment.get("currency"), dict) else {}
    return currency


def _wallet_copper(currency: dict) -> int:
    total = 0
    for coin, rate in _CURRENCY_IN_COPPER.items():
        try:
            total += max(0, int(currency.get(coin) or 0)) * rate
        except Exception:
            continue
    return total


def _deduct_currency(native: dict, price_gp: int) -> bool:
    """Deduct ``price_gp`` gold worth of coins from the character wallet.

    Spends from the highest denominations first and makes change. Returns False
    (without mutating) if the wallet cannot cover the cost.
    """
    equipment = native.get("equipment") if isinstance(native.get("equipment"), dict) else {}
    if not isinstance(native.get("equipment"), dict):
        native["equipment"] = equipment
    currency = equipment.get("currency") if isinstance(equipment.get("currency"), dict) else {}
    if not isinstance(equipment.get("currency"), dict):
        equipment["currency"] = currency
    for coin in _CURRENCY_IN_COPPER:
        try:
            currency[coin] = max(0, int(currency.get(coin) or 0))
        except Exception:
            currency[coin] = 0

    cost_copper = max(0, int(price_gp)) * _CURRENCY_IN_COPPER["gp"]
    if _wallet_copper(currency) < cost_copper:
        return False

    remaining = cost_copper
    # Spend from highest to lowest denomination.
    for coin, rate in sorted(_CURRENCY_IN_COPPER.items(), key=lambda kv: -kv[1]):
        if remaining <= 0:
            break
        use = min(currency[coin], remaining // rate)
        currency[coin] -= use
        remaining -= use * rate
    # Make change from a higher coin if exact denominations didn't cover it.
    if remaining > 0:
        wallet_copper = _wallet_copper(currency)
        if wallet_copper < remaining:
            return False
        # Convert everything to copper, subtract, then re-mint into coins.
        wallet_copper -= remaining
        for coin, rate in sorted(_CURRENCY_IN_COPPER.items(), key=lambda kv: -kv[1]):
            currency[coin] = wallet_copper // rate
            wallet_copper -= currency[coin] * rate
    return True


def _persist_profile(session: Session, owner_key: str, profile_index: int, native: dict) -> None:
    profiles = dict(getattr(session, "char_profiles", {}) or {})
    bucket = list(profiles.get(owner_key) or []) if isinstance(profiles.get(owner_key), list) else []
    if not (0 <= profile_index < len(bucket)):
        return
    row = bucket[profile_index] if isinstance(bucket[profile_index], dict) else {}
    resolved = resolve_character_runtime(native)
    row["nativeCharacter"] = resolved.get("document") if isinstance(resolved.get("document"), dict) else native
    row["nativeRuntime"] = resolved.get("runtime") if isinstance(resolved.get("runtime"), dict) else row.get("nativeRuntime", {})
    bucket[profile_index] = row
    profiles[owner_key] = bucket
    session.char_profiles = profiles


async def handle_pet_acquire(payload: dict, session: Session, user: User):
    """Buy a pet: deduct character currency and record ownership."""
    if user.role not in {"player", "dm"}:
        await manager.send_to(session.id, user.id, {"type": "pet_acquire_result", "payload": {"ok": False, "error": "role_not_allowed"}})
        return

    template_id = str(payload.get("template_id") or payload.get("templateId") or "").strip().lower()
    requested_profile_id = str(payload.get("profile_id") or payload.get("profileId") or "").strip()
    if not is_pet_template(template_id):
        await manager.send_to(session.id, user.id, {"type": "pet_acquire_result", "payload": {"ok": False, "error": "unknown_pet"}})
        return

    owner_key, profile_index, profile = _find_owner_profile(session, user, requested_profile_id)
    if profile_index < 0 or not isinstance(profile, dict):
        await manager.send_to(session.id, user.id, {"type": "pet_acquire_result", "payload": {"ok": False, "error": "profile_not_found"}})
        return

    native = profile.get("nativeCharacter") if isinstance(profile.get("nativeCharacter"), dict) else {}
    if not native:
        await manager.send_to(session.id, user.id, {"type": "pet_acquire_result", "payload": {"ok": False, "error": "missing_native_character"}})
        return

    summons = normalize_summon_state(native.get("summons"))
    unlocked = list(summons.get("unlockedTemplates") or [])
    if template_id in {str(t or "").strip().lower() for t in unlocked}:
        await manager.send_to(session.id, user.id, {"type": "pet_acquire_result", "payload": {"ok": False, "error": "already_owned"}})
        return

    price_gp = get_pet_price_gp(template_id) or 0
    # DMs may grant pets for free; players must pay.
    if user.role != "dm" and price_gp > 0:
        if not _deduct_currency(native, price_gp):
            await manager.send_to(session.id, user.id, {"type": "pet_acquire_result", "payload": {"ok": False, "error": "insufficient_funds", "price_gp": price_gp}})
            return

    unlocked.append(template_id)
    summons["unlockedTemplates"] = unlocked
    native["summons"] = summons
    _persist_profile(session, owner_key, profile_index, native)

    shop_entry = get_pet_shop_entry(template_id) or {}
    session.add_log(f"{user.name} acquired a pet {shop_entry.get('name', template_id)}", "system")
    await _send_char_profiles(session, user.id)
    await manager.send_to(session.id, user.id, {
        "type": "pet_acquire_result",
        "payload": {"ok": True, "template_id": template_id, "price_gp": price_gp, "pet": shop_entry},
    })
    await save_campaign_async(session)


async def handle_pet_release(payload: dict, session: Session, user: User):
    """Release an owned pet: drop ownership and remove any active token."""
    if user.role not in {"player", "dm"}:
        await manager.send_to(session.id, user.id, {"type": "pet_release_result", "payload": {"ok": False, "error": "role_not_allowed"}})
        return

    template_id = str(payload.get("template_id") or payload.get("templateId") or "").strip().lower()
    requested_profile_id = str(payload.get("profile_id") or payload.get("profileId") or "").strip()
    if not is_pet_template(template_id):
        await manager.send_to(session.id, user.id, {"type": "pet_release_result", "payload": {"ok": False, "error": "unknown_pet"}})
        return

    owner_key, profile_index, profile = _find_owner_profile(session, user, requested_profile_id)
    if profile_index < 0 or not isinstance(profile, dict):
        await manager.send_to(session.id, user.id, {"type": "pet_release_result", "payload": {"ok": False, "error": "profile_not_found"}})
        return

    native = profile.get("nativeCharacter") if isinstance(profile.get("nativeCharacter"), dict) else {}
    if not native:
        await manager.send_to(session.id, user.id, {"type": "pet_release_result", "payload": {"ok": False, "error": "missing_native_character"}})
        return

    summons = normalize_summon_state(native.get("summons"))
    unlocked = [str(t or "").strip().lower() for t in (summons.get("unlockedTemplates") or [])]
    if template_id not in unlocked:
        await manager.send_to(session.id, user.id, {"type": "pet_release_result", "payload": {"ok": False, "error": "not_owned"}})
        return

    # Remove any active deployment for this pet and delete its token.
    removed_rows = remove_active_summon(native, summon_group_id=template_id, owner_profile_id=str(profile.get("id") or ""))
    removed_token_ids: list[str] = []
    for row in removed_rows:
        tok_id = str(row.get("tokenId") or "").strip()
        tok = (session.tokens or {}).get(tok_id)
        if tok and str(getattr(tok, "owner_id", "") or "") == str(user.id):
            session.tokens.pop(tok_id, None)
            removed_token_ids.append(tok_id)
            await manager.broadcast(session.id, {"type": "token_deleted", "payload": {"token_id": tok_id}})

    summons = normalize_summon_state(native.get("summons"))
    summons["unlockedTemplates"] = [t for t in unlocked if t != template_id]
    native["summons"] = summons
    _persist_profile(session, owner_key, profile_index, native)

    if removed_token_ids:
        await _broadcast_token_state_sync(session)
    await _send_char_profiles(session, user.id)
    await manager.send_to(session.id, user.id, {
        "type": "pet_release_result",
        "payload": {"ok": True, "template_id": template_id, "removed_token_ids": removed_token_ids},
    })
    await save_campaign_async(session)
