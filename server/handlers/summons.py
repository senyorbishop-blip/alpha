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
)
from server.handlers.common import Session, User, manager, save_campaign_async, _broadcast_token_state_sync, _sync_combatant_token_state
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
        creature_type="summon",
        monster_type=str(token_payload.get("monster_type") or (actor.get("summonCategory") or "") or "summon"),
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
        "tokenId": str(token.id),
        "ownerUserId": str(user.id),
        "ownerProfileId": profile_id,
        "mapContext": str(token_payload.get("map_context") or "world"),
        "sceneId": str(token_payload.get("map_context") or "world"),
        "source": copy.deepcopy(actor.get("source") or {}),
        "createdAt": time.time(),
        "updatedAt": time.time(),
        "status": "active",
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


def _iter_user_native_documents(session: Session, user: User):
    profiles = dict(getattr(session, "char_profiles", {}) or {})
    for owner_key, rows in profiles.items():
        if not isinstance(rows, list):
            continue
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            native = row.get("nativeCharacter") if isinstance(row.get("nativeCharacter"), dict) else {}
            if not native:
                continue
            owner_profile_id = str(row.get("id") or "").strip()
            if user.role == "dm":
                yield owner_key, idx, row, native, owner_profile_id
            elif owner_key == _char_profile_bucket_key(session, user):
                yield owner_key, idx, row, native, owner_profile_id


async def handle_summon_action_use(payload: dict, session: Session, user: User):
    if user.role not in {"player", "dm"}:
        return
    token_id = str(payload.get("token_id") or payload.get("tokenId") or "").strip()
    action_id = str(payload.get("action_id") or payload.get("actionId") or "").strip().lower()
    target_id = str(payload.get("target_id") or payload.get("targetId") or "").strip()
    if not token_id or not action_id:
        return
    token = (session.tokens or {}).get(token_id)
    if not token:
        return
    if user.role != "dm" and str(getattr(token, "owner_id", "") or "") != str(user.id):
        return

    found = None
    for owner_key, idx, row, native, owner_profile_id in _iter_user_native_documents(session, user):
        active_rows = ((native.get("summons") or {}).get("activeSummons") or [])
        for active in active_rows:
            if not isinstance(active, dict):
                continue
            if str(active.get("tokenId") or "").strip() != token_id:
                continue
            actor = active.get("actor") if isinstance(active.get("actor"), dict) else {}
            actions = actor.get("actions") if isinstance(actor.get("actions"), list) else []
            action = next((a for a in actions if isinstance(a, dict) and str(a.get("id") or "").strip().lower() == action_id), None)
            if action:
                found = (owner_key, idx, row, native, active, actor, action, owner_profile_id)
                break
        if found:
            break
    if not found:
        await manager.send_to(session.id, user.id, {"type": "summon_action_result", "payload": {"ok": False, "error": "action_not_found"}})
        return

    _, idx, _, native, active, actor, action, owner_profile_id = found
    command_model = str(action.get("commandModel") or actor.get("commandModel") or "").strip().lower()
    if (session.combat or {}).get("active") and command_model in {"bonus_action_command", "action_command"}:
        round_no = int((session.combat or {}).get("round", 1) or 1)
        usage = session.combat.get("summon_command_usage") if isinstance(session.combat.get("summon_command_usage"), dict) else {}
        owner_usage = usage.get(owner_profile_id) if isinstance(usage.get(owner_profile_id), dict) else {}
        if int(owner_usage.get("round", 0) or 0) == round_no and owner_usage.get("used"):
            await manager.send_to(session.id, user.id, {"type": "summon_action_result", "payload": {"ok": False, "error": "command_already_used_this_round"}})
            return
        usage[owner_profile_id] = {"round": round_no, "used": True, "model": command_model}
        session.combat["summon_command_usage"] = usage

    damage_formula = str(((action.get("damage") or {}).get("formula") or "")).replace(" ", "")
    damage_type = str(((action.get("damage") or {}).get("type") or ""))
    target = (session.tokens or {}).get(target_id) if target_id else None
    applied_damage = None
    if target and damage_formula:
        import re, random

        m = re.match(r"(\d+)d(\d+)([+\-]\d+)?$", damage_formula)
        if m:
            qty = max(1, int(m.group(1)))
            die = max(2, int(m.group(2)))
            mod = int(m.group(3) or 0)
            total = sum(random.randint(1, die) for _ in range(qty)) + mod
            target.hp = max(0, int(getattr(target, "hp", 0) or 0) - max(0, total))
            _sync_combatant_token_state(session, target, previous_hp=None)
            applied_damage = max(0, total)
            await manager.broadcast(
                session.id,
                {"type": "token_hp_updated", "payload": {"token_id": target.id, "hp": target.hp, "maxHp": target.max_hp, "hidden_hp": target.hidden_hp, "log": None}},
            )

    log_msg = f"🧿 {actor.get('name', 'Summon')} used {action.get('displayName', action_id)}"
    if target:
        log_msg += f" on {getattr(target, 'name', 'target')}"
    if applied_damage is not None:
        log_msg += f" for {applied_damage} {damage_type}".strip()
    log_entry = session.add_log(log_msg, "combat", user.name)
    await manager.broadcast(session.id, {"type": "log_entry", "payload": {"log": log_entry}})
    await manager.send_to(
        session.id,
        user.id,
        {"type": "summon_action_result", "payload": {"ok": True, "token_id": token_id, "action_id": action_id, "target_id": target_id, "applied_damage": applied_damage}},
    )
    # keep runtime summon state hp in sync when target is itself
    synchronize_active_summon_state(
        native,
        token_id=token_id,
        hp_current=int(getattr(token, "hp", 0) or 0),
        hp_max=int(getattr(token, "max_hp", 1) or 1),
    )
    await _send_char_profiles(session, user.id)
    await save_campaign_async(session)
