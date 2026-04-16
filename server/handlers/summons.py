"""Live summon runtime handlers (Pass D summon families)."""
from __future__ import annotations

import copy
import time

from server.character.resolver import resolve_character_runtime
from server.character.summon_runtime import (
    build_summon_runtime_payload,
    register_active_summon,
    remove_active_summon,
    reconcile_native_summons,
    plan_active_summon_mutations,
    synchronize_active_summon_state,
    prune_expired_temporary_summons,
)
from server.handlers.common import Session, User, manager, save_campaign_async, _broadcast_token_state_sync
from server.character.summon_state import normalize_summon_state
from server.handlers.content import _send_char_profiles, _char_profile_bucket_key
from server.session import create_token


def _upsert_profile_runtime(session: Session, *, owner_key: str, profile_index: int, native_doc: dict):
    profiles = dict(getattr(session, "char_profiles", {}) or {})
    bucket = list(profiles.get(owner_key) or []) if isinstance(profiles.get(owner_key), list) else []
    if not (0 <= profile_index < len(bucket)):
        return
    row = bucket[profile_index] if isinstance(bucket[profile_index], dict) else {}
    resolved_runtime = resolve_character_runtime(native_doc)
    row["nativeCharacter"] = resolved_runtime.get("document") if isinstance(resolved_runtime.get("document"), dict) else native_doc
    row["nativeRuntime"] = resolved_runtime.get("runtime") if isinstance(resolved_runtime.get("runtime"), dict) else row.get("nativeRuntime", {})
    bucket[profile_index] = row
    profiles[owner_key] = bucket
    session.char_profiles = profiles


async def handle_summon_runtime_request(payload: dict, session: Session, user: User):
    if user.role not in {"player", "dm"}:
        await manager.send_to(
            session.id,
            user.id,
            {"type": "summon_runtime_result", "payload": {"ok": False, "error": "role_not_allowed"}},
        )
        return

    resolved = build_summon_runtime_payload(session=session, user=user, payload=payload or {})
    if not bool(resolved.get("ok")):
        await manager.send_to(
            session.id,
            user.id,
            {"type": "summon_runtime_result", "payload": {"ok": False, "error": str(resolved.get("error") or "summon_failed")}},
        )
        return

    actor = copy.deepcopy(resolved.get("actor") or {})
    token_payload = resolved.get("token_payload") if isinstance(resolved.get("token_payload"), dict) else {}
    selected_variant = str(resolved.get("selected_variant") or "")
    profile_id = str(resolved.get("profile_id") or "")

    summon_group_id = str(resolved.get("summon_group_id") or "")
    removed_token_ids: list[str] = []
    native_document = resolved.get("native_document") if isinstance(resolved.get("native_document"), dict) else {}
    expired_rows = prune_expired_temporary_summons(native_document)
    for expired in expired_rows:
        expired_token_id = str(expired.get("tokenId") or "").strip()
        if expired_token_id and expired_token_id in (session.tokens or {}):
            session.tokens.pop(expired_token_id, None)
            removed_token_ids.append(expired_token_id)
            await manager.broadcast(session.id, {"type": "token_deleted", "payload": {"token_id": expired_token_id}})
    valid_map_contexts = {"world"}
    valid_map_contexts.update(str(k or "").strip() for k in (getattr(session, "pois", {}) or {}).keys())
    valid_map_contexts.update(str(k or "").strip() for k in (getattr(session, "map_documents", {}) or {}).keys())
    reconcile_native_summons(
        native_document,
        existing_token_ids={str(k) for k in (session.tokens or {}).keys()},
        valid_map_contexts=valid_map_contexts,
    )
    mutation_plan = plan_active_summon_mutations(
        native_document,
        active_entry={
            "summonGroupId": summon_group_id,
            "templateId": str((resolved.get("template") or {}).get("id") or ""),
            "ownerProfileId": profile_id,
            "source": copy.deepcopy(actor.get("source") or {}),
        },
        template=(resolved.get("template") if isinstance(resolved.get("template"), dict) else {}),
    )
    for row in (mutation_plan.get("remove_entries") or []):
        if not isinstance(row, dict):
            continue
        removed = remove_active_summon(
            native_document,
            active_id=str(row.get("id") or ""),
            token_id=str(row.get("tokenId") or ""),
            owner_profile_id=profile_id,
        )
        for gone in removed:
            token_id = str(gone.get("tokenId") or "").strip()
            if not token_id:
                continue
            tok = (session.tokens or {}).get(token_id)
            if tok and str(getattr(tok, "owner_id", "") or "") == str(user.id):
                removed_token_ids.append(token_id)
                session.tokens.pop(token_id, None)

    token = create_token(
        session=session,
        dm_id=user.id,
        name=str(token_payload.get("name") or "🐾 Primal Beast"),
        x=float(token_payload.get("x", 120.0) or 120.0),
        y=float(token_payload.get("y", 120.0) or 120.0),
        color=str(((actor.get("tokenVisual") or {}).get("color") or "#7ad67a")),
        shape=str(((actor.get("tokenVisual") or {}).get("shape") or "circle")),
        width=float(token_payload.get("width", 40.0) or 40.0),
        height=float(token_payload.get("height", 40.0) or 40.0),
        owner_id=user.id,
        hp=int(token_payload.get("hp", 1) or 1),
        max_hp=int(token_payload.get("max_hp", token_payload.get("hp", 1)) or 1),
        temp_hp=0,
        map_context=str(token_payload.get("map_context") or "world"),
        hidden_hp=False,
        hidden=False,
        initiative_mod=0,
        ac=int(token_payload.get("ac", 10) or 10),
        speed=int(token_payload.get("speed", 0) or 0),
        token_type="companion",
        notes=str(token_payload.get("notes") or "")[:2000],
        level=int(((actor.get("levelSource") or {}).get("classLevel") or 1)),
        faction=str(token_payload.get("faction") or "allies"),
        passive_perception=None,
        staged=False,
        image_url=token_payload.get("image_url"),
        creature_id=str(actor.get("id") or "")[:120],
        creature_type=("summon" if bool(actor.get("isCreature", True)) else "deployed_effect"),
        monster_type=str(token_payload.get("monster_type") or (actor.get("entityKind") or actor.get("summonCategory") or "") or "summon"),
        cr="",
    )

    active_entry = {
        "id": str(actor.get("id") or ""),
        "templateId": str((actor.get("templateId") or "").strip().lower()),
        "summonTemplateId": str((actor.get("templateId") or "").strip().lower()),
        "variantId": selected_variant,
        "variant": selected_variant,
        "summonGroupId": str(((actor.get("source") or {}).get("variantGroup") or "").strip().lower()),
        "sourceClassId": str(((actor.get("source") or {}).get("classId") or "").strip().lower()),
        "sourceSubclassId": str(((actor.get("source") or {}).get("subclassId") or "").strip().lower()),
        "sourceFeatureId": str(((actor.get("source") or {}).get("featureId") or "").strip().lower()),
        "summonOrigin": str((resolved.get("template") or {}).get("summonOrigin") or ((actor.get("source") or {}).get("summonOrigin") or "feature")).strip().lower(),
        "spellId": str((resolved.get("template") or {}).get("spellId") or ((actor.get("source") or {}).get("spellId") or "")).strip().lower(),
        "tokenId": str(token.id),
        "ownerUserId": str(user.id),
        "ownerProfileId": profile_id,
        "mapContext": str(token_payload.get("map_context") or "world"),
        "sceneId": str(token_payload.get("map_context") or "world"),
        "source": copy.deepcopy(actor.get("source") or {}),
        "createdAt": time.time(),
        "updatedAt": time.time(),
        "status": "active",
        "entityKind": str(actor.get("entityKind") or (resolved.get("template") or {}).get("entityKind") or "creature").strip().lower(),
        "isCreature": bool(actor.get("isCreature", (resolved.get("template") or {}).get("isCreature", True))),
        "actionSurfaceType": str(actor.get("actionSurfaceType") or (resolved.get("template") or {}).get("actionSurfaceType") or "").strip().lower(),
        "placementRules": copy.deepcopy(actor.get("placementRules") or (resolved.get("template") or {}).get("placementRules") or {}),
        "interactionModel": copy.deepcopy(actor.get("interactionModel") or {}),
        "cleanupPolicy": copy.deepcopy(actor.get("cleanupPolicy") or (resolved.get("template") or {}).get("cleanupPolicy") or {}),
        "replaceOnResummon": bool((resolved.get("template") or {}).get("replaceOnResummon")),
        "maxActive": int((resolved.get("template") or {}).get("maxActive") or 1),
        "spawnedAt": time.time(),
        "actor": actor,
    }

    owner_key = str(resolved.get("owner_key") or "")
    profile_index = int(resolved.get("profile_index", -1) or -1)
    register_active_summon(native_document, active_entry)
    _upsert_profile_runtime(session, owner_key=owner_key, profile_index=profile_index, native_doc=native_document)

    await manager.broadcast(
        session.id,
        {
            "type": "token_created",
            "payload": {
                "token": token.to_dict(),
                "log": session.add_log(f"{user.name} summoned {actor.get('name', 'Primal Beast')}", "system"),
            },
        },
    )
    if removed_token_ids:
        for token_id in removed_token_ids:
            await manager.broadcast(session.id, {"type": "token_deleted", "payload": {"token_id": token_id}})

    await _broadcast_token_state_sync(session)
    await _send_char_profiles(session, user.id)
    await manager.send_to(
        session.id,
        user.id,
        {
            "type": "summon_runtime_result",
            "payload": {
                "ok": True,
                "profile_id": profile_id,
                "summon": active_entry,
                "token": token.to_dict(),
                "removed_token_ids": removed_token_ids,
            },
        },
    )
    await save_campaign_async(session)


async def handle_summon_runtime_dismiss(payload: dict, session: Session, user: User):
    if user.role not in {"player", "dm"}:
        await manager.send_to(session.id, user.id, {"type": "summon_runtime_dismiss_result", "payload": {"ok": False, "error": "role_not_allowed"}})
        return
    requested_profile_id = str(payload.get("profile_id") or payload.get("profileId") or "").strip()
    owner_key = _char_profile_bucket_key(session, user)
    profiles = dict(getattr(session, "char_profiles", {}) or {})
    bucket = list(profiles.get(owner_key) or []) if isinstance(profiles.get(owner_key), list) else []
    if not requested_profile_id:
        requested_profile_id = str((getattr(session, "active_char_profiles", {}) or {}).get(user.id) or "").strip()
    profile_index = -1
    native_document: dict = {}
    for idx, row in enumerate(bucket):
        if not isinstance(row, dict):
            continue
        if requested_profile_id and str(row.get("id") or "").strip() != requested_profile_id:
            continue
        native_document = row.get("nativeCharacter") if isinstance(row.get("nativeCharacter"), dict) else {}
        profile_index = idx
        requested_profile_id = str(row.get("id") or requested_profile_id or "")
        break
    if profile_index < 0 or not native_document:
        await manager.send_to(session.id, user.id, {"type": "summon_runtime_dismiss_result", "payload": {"ok": False, "error": "profile_not_found"}})
        return
    profile_id = requested_profile_id
    active_id = str(payload.get("active_id") or payload.get("activeId") or "").strip()
    token_id = str(payload.get("token_id") or payload.get("tokenId") or "").strip()
    summon_group_id = str(payload.get("summon_group_id") or payload.get("summonGroupId") or "").strip().lower()
    source_feature_id = str(payload.get("source_feature_id") or payload.get("sourceFeatureId") or "").strip().lower()

    removed_rows = remove_active_summon(
        native_document,
        active_id=active_id,
        token_id=token_id,
        summon_group_id=summon_group_id,
        source_feature_id=source_feature_id,
        owner_profile_id=profile_id,
    )
    if not removed_rows:
        await manager.send_to(session.id, user.id, {"type": "summon_runtime_dismiss_result", "payload": {"ok": True, "removed": [], "removed_token_ids": []}})
        return

    removed_token_ids: list[str] = []
    for row in removed_rows:
        tok_id = str(row.get("tokenId") or "").strip()
        tok = (session.tokens or {}).get(tok_id)
        if tok and str(getattr(tok, "owner_id", "") or "") == str(user.id):
            session.tokens.pop(tok_id, None)
            removed_token_ids.append(tok_id)
            await manager.broadcast(session.id, {"type": "token_deleted", "payload": {"token_id": tok_id}})

    _upsert_profile_runtime(
        session,
        owner_key=owner_key,
        profile_index=profile_index,
        native_doc=native_document,
    )
    await _broadcast_token_state_sync(session)
    await _send_char_profiles(session, user.id)
    await manager.send_to(
        session.id,
        user.id,
        {"type": "summon_runtime_dismiss_result", "payload": {"ok": True, "removed": removed_rows, "removed_token_ids": removed_token_ids}},
    )
    await save_campaign_async(session)


def _iter_active_summons(session: Session):
    profiles = dict(getattr(session, "char_profiles", {}) or {})
    users = dict(getattr(session, "users", {}) or {})
    for owner_key, bucket in profiles.items():
        rows = list(bucket) if isinstance(bucket, list) else []
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            profile_id = str(row.get("id") or "").strip()
            native = row.get("nativeCharacter") if isinstance(row.get("nativeCharacter"), dict) else {}
            summons = normalize_summon_state(native.get("summons"))
            for active in (summons.get("activeSummons") or []):
                if not isinstance(active, dict):
                    continue
                token_id = str(active.get("tokenId") or "").strip()
                token = (session.tokens or {}).get(token_id)
                owner_user_id = str(active.get("ownerUserId") or "").strip()
                owner_name = ""
                if owner_user_id and owner_user_id in users:
                    owner_name = str(getattr(users[owner_user_id], "name", "") or "")
                if not owner_name:
                    owner_name = str(((active.get("actor") or {}).get("owner") or {}).get("userName") or "")
                if not owner_name:
                    owner_name = str(owner_key or "")
                enriched = copy.deepcopy(active)
                enriched["ownerBucketKey"] = str(owner_key)
                enriched["profileIndex"] = idx
                enriched["profileId"] = profile_id
                enriched["ownerName"] = owner_name
                enriched["tokenPresent"] = bool(token)
                enriched["tokenName"] = str(getattr(token, "name", "") or (enriched.get("actor") or {}).get("name") or "")
                enriched["tokenMapContext"] = str(getattr(token, "map_context", "") or enriched.get("mapContext") or enriched.get("sceneId") or "")
                yield owner_key, idx, row, native, enriched


async def handle_summon_runtime_admin(payload: dict, session: Session, user: User):
    if user.role != "dm":
        await manager.send_to(session.id, user.id, {"type": "summon_runtime_admin_result", "payload": {"ok": False, "error": "role_not_allowed"}})
        return

    action = str(payload.get("action") or "list").strip().lower()
    active_id = str(payload.get("active_id") or payload.get("activeId") or "").strip()
    token_id = str(payload.get("token_id") or payload.get("tokenId") or "").strip()

    rows = list(_iter_active_summons(session))
    if action in {"list", "refresh", "cleanup_stale"}:
        touched_profiles: set[tuple[str, int]] = set()
        removed_token_ids: list[str] = []
        for owner_key, profile_index, _, native, _ in rows:
            expired_rows = prune_expired_temporary_summons(native)
            if not expired_rows:
                continue
            touched_profiles.add((owner_key, profile_index))
            for expired in expired_rows:
                expired_token_id = str(expired.get("tokenId") or "").strip()
                if expired_token_id and expired_token_id in (session.tokens or {}):
                    session.tokens.pop(expired_token_id, None)
                    removed_token_ids.append(expired_token_id)
                    await manager.broadcast(session.id, {"type": "token_deleted", "payload": {"token_id": expired_token_id}})
        if touched_profiles:
            profiles = dict(getattr(session, "char_profiles", {}) or {})
            for owner_key, profile_index in touched_profiles:
                bucket = list(profiles.get(owner_key) or []) if isinstance(profiles.get(owner_key), list) else []
                if not (0 <= profile_index < len(bucket)):
                    continue
                slot = bucket[profile_index] if isinstance(bucket[profile_index], dict) else {}
                native_doc = slot.get("nativeCharacter") if isinstance(slot.get("nativeCharacter"), dict) else {}
                resolved_runtime = resolve_character_runtime(native_doc)
                slot["nativeCharacter"] = resolved_runtime.get("document") if isinstance(resolved_runtime.get("document"), dict) else native_doc
                slot["nativeRuntime"] = resolved_runtime.get("runtime") if isinstance(resolved_runtime.get("runtime"), dict) else slot.get("nativeRuntime", {})
                bucket[profile_index] = slot
                profiles[owner_key] = bucket
            session.char_profiles = profiles
            await _broadcast_token_state_sync(session)
            await save_campaign_async(session)
        rows = list(_iter_active_summons(session))
    if action in {"list", "refresh"}:
        data = [entry for (_, _, _, _, entry) in rows]
        await manager.send_to(session.id, user.id, {"type": "summon_runtime_admin_result", "payload": {"ok": True, "action": "list", "summons": data}})
        return

    if action == "inspect":
        selected = None
        for _, _, _, _, entry in rows:
            if active_id and str(entry.get("id") or "") == active_id:
                selected = entry
                break
            if token_id and str(entry.get("tokenId") or "") == token_id:
                selected = entry
                break
        await manager.send_to(session.id, user.id, {"type": "summon_runtime_admin_result", "payload": {"ok": True, "action": "inspect", "summon": selected}})
        return

    if action in {"dismiss", "cleanup_stale"}:
        removed: list[dict] = []
        removed_token_ids: list[str] = []
        touched: set[tuple[str, int]] = set()
        for owner_key, profile_index, row, native, entry in rows:
            row_active_id = str(entry.get("id") or "")
            row_token_id = str(entry.get("tokenId") or "")
            if action == "cleanup_stale" and row_token_id and row_token_id in (session.tokens or {}):
                continue
            if action == "dismiss" and active_id and row_active_id != active_id:
                continue
            if action == "dismiss" and token_id and row_token_id != token_id:
                continue
            if action == "dismiss" and not active_id and not token_id:
                continue
            gone = remove_active_summon(native, active_id=row_active_id, token_id=row_token_id, owner_profile_id=str(entry.get("ownerProfileId") or ""))
            if not gone:
                continue
            removed.extend(gone)
            touched.add((owner_key, profile_index))
            if row_token_id and row_token_id in (session.tokens or {}):
                session.tokens.pop(row_token_id, None)
                removed_token_ids.append(row_token_id)
                await manager.broadcast(session.id, {"type": "token_deleted", "payload": {"token_id": row_token_id}})

        if touched:
            profiles = dict(getattr(session, "char_profiles", {}) or {})
            for owner_key, profile_index in touched:
                bucket = list(profiles.get(owner_key) or []) if isinstance(profiles.get(owner_key), list) else []
                if not (0 <= profile_index < len(bucket)):
                    continue
                slot = bucket[profile_index] if isinstance(bucket[profile_index], dict) else {}
                native_doc = slot.get("nativeCharacter") if isinstance(slot.get("nativeCharacter"), dict) else {}
                resolved_runtime = resolve_character_runtime(native_doc)
                slot["nativeCharacter"] = resolved_runtime.get("document") if isinstance(resolved_runtime.get("document"), dict) else native_doc
                slot["nativeRuntime"] = resolved_runtime.get("runtime") if isinstance(resolved_runtime.get("runtime"), dict) else slot.get("nativeRuntime", {})
                bucket[profile_index] = slot
                profiles[owner_key] = bucket
            session.char_profiles = profiles
            await _broadcast_token_state_sync(session)
            for uid in (session.users or {}).keys():
                await _send_char_profiles(session, uid)
            await save_campaign_async(session)

        await manager.send_to(session.id, user.id, {
            "type": "summon_runtime_admin_result",
            "payload": {"ok": True, "action": action, "removed": removed, "removed_token_ids": removed_token_ids},
        })
        return

    await manager.send_to(session.id, user.id, {"type": "summon_runtime_admin_result", "payload": {"ok": False, "error": "unknown_action"}})
