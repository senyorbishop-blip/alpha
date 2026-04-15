"""Live summon runtime handlers (Pass C Beast Master vertical slice)."""
from __future__ import annotations

import copy
import time

from server.character.resolver import resolve_character_runtime
from server.character.summon_runtime import build_summon_runtime_payload, register_active_summon
from server.handlers.common import Session, User, manager, save_campaign_async, _broadcast_token_state_sync
from server.handlers.content import _send_char_profiles
from server.session import create_token


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

    # Replace prior beast companion token for same owner to avoid duplicate spam.
    removed_token_ids: list[str] = []
    for tok in list((session.tokens or {}).values()):
        if not tok:
            continue
        if str(getattr(tok, "owner_id", "") or "") != str(user.id):
            continue
        if str(getattr(tok, "token_type", "") or "").strip().lower() != "companion":
            continue
        notes = str(getattr(tok, "notes", "") or "").lower()
        if "beast master companion" not in notes:
            continue
        removed_token_ids.append(str(getattr(tok, "id", "") or ""))
        session.tokens.pop(str(getattr(tok, "id", "") or ""), None)

    token = create_token(
        session=session,
        dm_id=user.id,
        name=str(token_payload.get("name") or "🐾 Primal Beast"),
        x=float(token_payload.get("x", 120.0) or 120.0),
        y=float(token_payload.get("y", 120.0) or 120.0),
        color="#7ad67a",
        shape="circle",
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
        monster_type="beast-companion",
        cr="",
    )

    active_entry = {
        "id": str(actor.get("id") or ""),
        "templateId": str((actor.get("templateId") or "").strip().lower()),
        "variantId": selected_variant,
        "summonGroupId": str(((actor.get("source") or {}).get("variantGroup") or "").strip().lower()),
        "tokenId": str(token.id),
        "ownerUserId": str(user.id),
        "ownerProfileId": profile_id,
        "source": copy.deepcopy(actor.get("source") or {}),
        "spawnedAt": time.time(),
        "actor": actor,
    }

    profiles = dict(getattr(session, "char_profiles", {}) or {})
    owner_key = str(resolved.get("owner_key") or "")
    profile_index = int(resolved.get("profile_index", -1) or -1)
    bucket = list(profiles.get(owner_key) or []) if isinstance(profiles.get(owner_key), list) else []
    if 0 <= profile_index < len(bucket):
        row = bucket[profile_index] if isinstance(bucket[profile_index], dict) else {}
        native_doc = row.get("nativeCharacter") if isinstance(row.get("nativeCharacter"), dict) else {}
        register_active_summon(native_doc, active_entry)
        resolved_runtime = resolve_character_runtime(native_doc)
        row["nativeCharacter"] = resolved_runtime.get("document") if isinstance(resolved_runtime.get("document"), dict) else native_doc
        row["nativeRuntime"] = resolved_runtime.get("runtime") if isinstance(resolved_runtime.get("runtime"), dict) else row.get("nativeRuntime", {})
        bucket[profile_index] = row
        profiles[owner_key] = bucket
        session.char_profiles = profiles

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
