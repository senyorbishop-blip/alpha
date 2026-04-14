"""
server/handlers/map_editor.py — Map editor helpers and handlers.
"""
import logging
import posixpath
import secrets
import time

logger = logging.getLogger(__name__)
from server.session import normalize_interactable, assistant_dm_has_scope
from server.quest_progress import apply_objective_event, normalize_quest_payload_shape
from server.living_world_events import emit_world_event, consume_world_event
from server.session import filter_editor_props_for_role
from server.handlers.common import (
    Session, User, manager,
    save_campaign_async,
    normalize_map_settings,
    _refresh_map_documents,
)


def _get_editor_prop(session: Session, map_ctx: str, prop_id: str):
    props_all = dict(getattr(session, "editor_props", {}) or {})
    items = list(props_all.get(map_ctx) or [])
    for idx, item in enumerate(items):
        if str(item.get("id") or "") == prop_id:
            return props_all, items, idx, dict(item)
    return props_all, items, -1, None


async def _send_prop_action_error(session: Session, user: User, message: str):
    await manager.send_to(session.id, user.id, {"type": "error", "payload": {"message": message}})


async def _broadcast_prop_action_log(session: Session, message: str):
    log_entry = session.add_log(message, "system", "System")
    await manager.broadcast(session.id, {
        "type": "chat_message",
        "payload": {
            "user_name": "System",
            "role": "system",
            "message": message,
            "log": log_entry,
        }
    })


async def _send_prop_action_result(session: Session, user_id: str, message: str):
    await manager.send_to(session.id, user_id, {
        "type": "prop_action_result",
        "payload": {"message": message}
    })


async def _send_interactable_action_result(session: Session, user_id: str, payload: dict):
    await manager.send_to(session.id, user_id, {
        "type": "interactable_action_result",
        "payload": payload,
    })


async def _broadcast_editor_state(session: Session):
    payload = {"layers": dict(getattr(session, "editor_layers", {}) or {})}
    await manager.broadcast(session.id, {"type": "editor_layers_sync", "payload": payload})


async def _broadcast_editor_walls_state(session: Session):
    payload = {"walls": dict(getattr(session, "editor_walls", {}) or {})}
    await manager.broadcast(session.id, {"type": "editor_walls_sync", "payload": payload})


async def _broadcast_editor_props_state(session: Session):
    props_all = dict(getattr(session, "editor_props", {}) or {})
    for uid, u in session.users.items():
        payload = {"props": filter_editor_props_for_role(props_all, getattr(u, "role", "viewer"))}
        await manager.send_to(session.id, uid, {"type": "editor_props_sync", "payload": payload})


async def _broadcast_editor_world_state(session: Session):
    payload = {
        "paths": dict(getattr(session, "editor_paths", {}) or {}),
        "labels": dict(getattr(session, "editor_labels", {}) or {}),
        "markers": dict(getattr(session, "editor_markers", {}) or {}),
        "lights": dict(getattr(session, "editor_lights", {}) or {}),
    }
    await manager.broadcast(session.id, {"type": "editor_world_sync", "payload": payload})


def _merge_wall_segments(segments: list[dict]) -> list[dict]:
    horizontal: dict[int, list[tuple[int, int]]] = {}
    vertical: dict[int, list[tuple[int, int]]] = {}
    others: list[dict] = []
    for seg in segments or []:
        try:
            x1 = int(seg.get("x1"))
            y1 = int(seg.get("y1"))
            x2 = int(seg.get("x2"))
            y2 = int(seg.get("y2"))
        except Exception:
            continue
        if x1 == x2 and y1 == y2:
            continue
        if y1 == y2:
            horizontal.setdefault(y1, []).append((min(x1, x2), max(x1, x2)))
        elif x1 == x2:
            vertical.setdefault(x1, []).append((min(y1, y2), max(y1, y2)))
        else:
            others.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2})

    merged: list[dict] = []

    def _merge_ranges(values: list[tuple[int, int]], build):
        values.sort(key=lambda item: (item[0], item[1]))
        cur_start = None
        cur_end = None
        for start, end in values:
            if cur_start is None:
                cur_start, cur_end = start, end
                continue
            if start <= cur_end:
                cur_end = max(cur_end, end)
            else:
                item = build(cur_start, cur_end)
                if item:
                    merged.append(item)
                cur_start, cur_end = start, end
        if cur_start is not None:
            item = build(cur_start, cur_end)
            if item:
                merged.append(item)

    for y, values in horizontal.items():
        _merge_ranges(values, lambda start, end, y=y: {"x1": start, "y1": y, "x2": end, "y2": y} if start != end else None)
    for x, values in vertical.items():
        _merge_ranges(values, lambda start, end, x=x: {"x1": x, "y1": start, "x2": x, "y2": end} if start != end else None)

    unique: list[dict] = []
    seen: set[tuple[int, int, int, int]] = set()
    for seg in [*merged, *others]:
        try:
            a = (int(seg["x1"]), int(seg["y1"]))
            b = (int(seg["x2"]), int(seg["y2"]))
        except Exception:
            continue
        key = (*a, *b) if a <= b else (*b, *a)
        if key in seen:
            continue
        seen.add(key)
        unique.append({"x1": a[0], "y1": a[1], "x2": b[0], "y2": b[1]} if a <= b else {"x1": b[0], "y1": b[1], "x2": a[0], "y2": a[1]})
    return unique


def _get_poi(session: Session, poi_id: str):
    poi = (getattr(session, "pois", {}) or {}).get(poi_id)
    return poi if poi else None


def _normalize_dm_map_context(session: Session, value) -> str:
    ctx = str(value or "world").strip()[:80] or "world"
    if ctx == "world":
        return "world"
    pois = dict(getattr(session, "pois", {}) or {})
    if ctx in pois:
        return ctx
    docs = dict(getattr(session, "map_documents", {}) or {})
    if ctx in docs:
        return ctx
    return "world"


def _resolve_fog_map_context(session: Session, payload: dict) -> str:
    data = payload if isinstance(payload, dict) else {}
    requested = (
        data.get("map_ctx")
        or data.get("map_context")
        or data.get("dm_map_context")
        or getattr(session, "dm_map_context", "world")
        or "world"
    )
    return _normalize_dm_map_context(session, requested)


async def _broadcast_fog_to_visible_users(session: Session, message: dict, map_ctx: str):
    """Deliver fog updates only to users whose visible map contexts include map_ctx."""
    users = dict(getattr(session, "users", {}) or {})
    for uid, participant in users.items():
        role = str(getattr(participant, "role", "") or "").strip().lower()
        if role == "dm":
            await manager.send_to(session.id, uid, message)
            continue
        try:
            visible = session.visible_map_contexts_for_user(uid)
        except Exception:
            visible = {"world"}
        if str(map_ctx or "world") in {str(ctx or "world") for ctx in (visible or {"world"})}:
            await manager.send_to(session.id, uid, message)


def _resolve_local_map_url(session: Session, map_ctx: str, fallback=None) -> str | None:
    if map_ctx == "world":
        return None
    poi = (getattr(session, "pois", {}) or {}).get(map_ctx)
    poi_url = str(getattr(poi, "local_map_url", "") or "").strip()
    if poi_url:
        return poi_url
    docs = dict(getattr(session, "map_documents", {}) or {})
    doc = docs.get(map_ctx) if isinstance(docs.get(map_ctx), dict) else {}
    assets = doc.get("assets") if isinstance(doc.get("assets"), dict) else {}
    doc_url = str(assets.get("background_url") or "").strip()
    if doc_url:
        return doc_url
    fallback_url = str(fallback or "").strip()
    return fallback_url or None


def _user_has_map_presence(session: Session, user: User, map_ctx: str) -> bool:
    if user.role == "dm":
        return True
    for token in (getattr(session, "tokens", {}) or {}).values():
        if not token or str(getattr(token, "owner_id", "") or "") != str(user.id):
            continue
        if str(getattr(token, "map_context", "world") or "world") == str(map_ctx or "world"):
            return True
    return False


def _interactable_target_payload(kind: str, map_ctx: str, item) -> dict:
    if kind == "poi":
        return {
            "target_kind": "poi",
            "target_id": str(getattr(item, "id", "") or ""),
            "target_name": str(getattr(item, "name", "Location") or "Location")[:120],
            "map_context": str(getattr(item, "map_context", map_ctx) or map_ctx or "world")[:80],
        }
    return {
        "target_kind": "prop",
        "target_id": str(item.get("id") or ""),
        "target_name": str(item.get("name") or "Object")[:120],
        "map_context": str(map_ctx or "world")[:80],
    }


def _resolve_interactable_state(interactable: dict) -> tuple[str, dict]:
    states = interactable.get("states") if isinstance(interactable.get("states"), dict) else {}
    state_id = str(interactable.get("current_state") or "").strip().lower()[:32]
    if state_id and isinstance(states.get(state_id), dict):
        return state_id, dict(states.get(state_id) or {})
    if isinstance(states.get("closed"), dict):
        return "closed", dict(states.get("closed") or {})
    for key, value in states.items():
        if isinstance(value, dict):
            return str(key), dict(value or {})
    return "", {}


def _state_actions(interactable: dict, state_cfg: dict) -> list[dict]:
    entries = state_cfg.get("available_actions") if isinstance(state_cfg.get("available_actions"), list) else interactable.get("actions")
    out = []
    seen = set()
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        action_id = str(entry.get("id") or "").strip().lower()
        if not action_id or action_id in seen:
            continue
        seen.add(action_id)
        out.append(dict(entry))
    return out


async def handle_interactable_action(payload: dict, session: Session, user: User):
    if user.role not in {"dm", "player", "viewer"}:
        return
    target_kind = str(payload.get("target_kind") or payload.get("object_type") or "prop").strip().lower()
    action_id = str(payload.get("action") or "").strip().lower()[:40]
    map_ctx = str(payload.get("map_context") or "world").strip()[:80] or "world"
    actor_note = str(payload.get("note") or payload.get("message") or "").strip()[:240]
    requested_skill = str(payload.get("skill") or "").strip().lower()[:40]

    if target_kind not in {"prop", "poi"} or not action_id:
        return await _send_prop_action_error(session, user, "Choose an interactive object and action.")

    interactable = None
    target = None
    if target_kind == "poi":
        poi_id = str(payload.get("poi_id") or payload.get("target_id") or "").strip()[:48]
        poi = _get_poi(session, poi_id)
        if not poi:
            return await _send_prop_action_error(session, user, "That point of interest is no longer available.")
        target = poi
        map_ctx = str(getattr(poi, "map_context", map_ctx) or map_ctx or "world")[:80] or "world"
        interactable = normalize_interactable(getattr(poi, "interactable", None))
    else:
        prop_id = str(payload.get("prop_id") or payload.get("target_id") or "").strip()[:48]
        _, _, _, prop = _get_editor_prop(session, map_ctx, prop_id)
        if not prop:
            return await _send_prop_action_error(session, user, "That world object is no longer available.")
        kind = str(prop.get("kind") or "").strip().lower()
        hidden = bool(prop.get("hidden")) if kind in {"chest", "merchant", "store", "tavern", "blacksmith", "market_stall", "inn", "shop"} else False
        if user.role != "dm" and hidden:
            return await _send_prop_action_error(session, user, "That world object is not visible to you.")
        target = prop
        interactable = normalize_interactable(prop.get("interactable"))

    if not interactable or not interactable.get("enabled"):
        return await _send_prop_action_error(session, user, "That world object has no interaction prompt yet.")

    state_id, state_cfg = _resolve_interactable_state(interactable)
    actions = _state_actions(interactable, state_cfg)
    action = next((entry for entry in actions if str(entry.get("id") or "") == action_id), None)
    if not action:
        return await _send_prop_action_error(session, user, "That interaction is not enabled for this object.")

    permissions = interactable.get("permissions") if isinstance(interactable.get("permissions"), dict) else {}
    if user.role != "dm" and bool(permissions.get("dm_only")):
        return await _send_prop_action_error(session, user, "Only the DM can use that interaction.")
    if user.role == "player" and not bool(permissions.get("allow_players", True)):
        return await _send_prop_action_error(session, user, "Players cannot use that interaction.")
    if user.role == "viewer" and not bool(permissions.get("allow_viewers", False)):
        return await _send_prop_action_error(session, user, "Viewers cannot use that interaction.")
    if user.role != "dm" and bool(permissions.get("requires_token")) and not _user_has_map_presence(session, user, map_ctx):
        return await _send_prop_action_error(session, user, "Move one of your tokens onto this map before interacting.")

    target_payload = _interactable_target_payload(target_kind, map_ctx, target)
    prompt = str(interactable.get("prompt") or "").strip()
    result_payload = {
        **target_payload,
        "action": action_id,
        "action_label": str(action.get("label") or action_id.replace("_", " ").title())[:80],
        "interactable_kind": str(interactable.get("kind") or "")[:40],
        "prompt": prompt,
        "discovery_hook": str(interactable.get("discovery_hook") or "")[:80],
        "discovery_visibility": str(((interactable.get("visibility") or {}).get("discovery_visibility")) or "")[:32],
        "actor_user_id": str(user.id),
        "actor_name": str(user.name)[:120],
        "note": actor_note,
    }
    if state_id:
        result_payload["interactable_state"] = state_id
    if state_cfg.get("label_override"):
        result_payload["state_label_override"] = str(state_cfg.get("label_override"))[:120]
    if state_cfg.get("asset_key_override"):
        result_payload["state_asset_key_override"] = str(state_cfg.get("asset_key_override"))[:120]
    if requested_skill:
        result_payload["skill"] = requested_skill

    target_name = target_payload["target_name"] or ("Location" if target_kind == "poi" else "Object")
    action_label = result_payload["action_label"]
    actor_message = f"{action_label} recorded for {target_name}."
    if prompt and action_id in {"inspect", "interact"}:
        actor_message = prompt
    elif action_id == "attempt_skill_action":
        skill_name = requested_skill or str(action.get("skill") or "skill check").strip().lower()
        actor_message = f"You attempt {skill_name} on {target_name}."
    elif action_id == "mark_for_party":
        actor_message = f"Marked {target_name} for the party."
    elif action_id == "ask_party":
        actor_message = f"Asked the party about {target_name}."
    result_payload["message"] = actor_message

    if action_id in {"mark_for_party", "ask_party"}:
        party_message = actor_note or (
            f"{user.name} marked {target_name} for the party."
            if action_id == "mark_for_party"
            else f"{user.name} asked the party about {target_name}."
        )
        log_entry = session.add_log(party_message, "system", "System")
        event_payload = {
            **result_payload,
            "message": party_message,
            "log": log_entry,
        }
        for uid, target_user in session.users.items():
            if target_user.role in {"dm", "player"}:
                await manager.send_to(session.id, uid, {"type": "interactable_action_event", "payload": event_payload})
        await save_campaign_async(session)
        return await _send_interactable_action_result(session, user.id, result_payload)

    if action_id == "attempt_skill_action" and user.role == "player":
        dm_targets = [uid for uid, target_user in session.users.items() if target_user.role == "dm"]
        for uid in dm_targets:
            await manager.send_to(session.id, uid, {
                "type": "interactable_action_event",
                "payload": {
                    **result_payload,
                    "message": f"{user.name} attempts {result_payload.get('skill') or 'a skill check'} on {target_name}.",
                    "audience": "dm",
                },
            })

    states = interactable.get("states") if isinstance(interactable.get("states"), dict) else {}
    next_state = ""
    state_next_by_action = state_cfg.get("next_state_by_action") if isinstance(state_cfg.get("next_state_by_action"), dict) else {}
    candidate = str(state_next_by_action.get(action_id) or state_cfg.get("next_state") or "").strip().lower()
    if candidate and isinstance(states.get(candidate), dict):
        next_state = candidate
    prop_state_changed = False
    if next_state:
        interactable["current_state"] = next_state
        prop_state_changed = True
        result_payload["interactable_next_state"] = next_state
        next_cfg = dict(states.get(next_state) or {})
        if next_cfg.get("label_override"):
            result_payload["next_state_label_override"] = str(next_cfg.get("label_override"))[:120]
        if next_cfg.get("asset_key_override"):
            result_payload["next_state_asset_key_override"] = str(next_cfg.get("asset_key_override"))[:120]

    world_state = dict(getattr(session, "world_state", {}) or {})
    current_flags = dict(world_state.get("world_state_flags") or {})
    one_time_flags = [str(v).strip()[:80] for v in list(state_cfg.get("one_time_flags") or []) if str(v).strip()]
    used_flags = set(str(v).strip()[:80] for v in list(interactable.get("used_one_time_flags") or []) if str(v).strip())
    for flag in one_time_flags:
        if flag in used_flags:
            continue
        current_flags[flag] = True
        used_flags.add(flag)
        prop_state_changed = True
    for key, value in dict(state_cfg.get("world_state_flags") or {}).items():
        current_flags[str(key)[:80]] = value
        prop_state_changed = True
    if current_flags:
        world_state["world_state_flags"] = current_flags
    if used_flags:
        interactable["used_one_time_flags"] = sorted(used_flags)
    if world_state:
        session.world_state = world_state
        result_payload["world_state_flags_written"] = sorted(str(k) for k in dict(state_cfg.get("world_state_flags") or {}).keys())

    state_discovery_hook = str(state_cfg.get("discovery_hook") or "").strip()[:80]
    if state_discovery_hook:
        result_payload["discovery_hook"] = state_discovery_hook
    state_discovery_visibility = str(state_cfg.get("discovery_visibility") or "").strip().lower()[:32]
    if state_discovery_visibility:
        result_payload["discovery_visibility"] = state_discovery_visibility
    handout_unlock_ids = [str(v).strip()[:80] for v in list(state_cfg.get("handout_unlock_ids") or []) if str(v).strip()]
    if handout_unlock_ids:
        result_payload["handout_unlock_ids"] = handout_unlock_ids

    if target_kind == "prop":
        props_all, items, idx, prop = _get_editor_prop(session, map_ctx, str(target_payload.get("target_id") or ""))
        if idx >= 0 and prop:
            prop["interactable"] = interactable
            items[idx] = prop
            props_all[map_ctx] = items
            session.editor_props = props_all
    else:
        if target:
            target.interactable = interactable

    world_event = emit_world_event(session, "interactable_used", {
        "source": "interactable_action",
        "actor_user_id": str(user.id),
        "summary": f"{user.name} used {action_label} on {target_name}.",
        "meta": {
            "target_kind": target_kind,
            "target_id": str(target_payload.get("target_id") or ""),
            "map_context": str(target_payload.get("map_context") or "world"),
            "action": action_id,
            "state": state_id,
            "next_state": next_state,
        },
    })
    result_payload["living_world_event_id"] = str(world_event.get("id") or "")
    if handout_unlock_ids or dict(state_cfg.get("world_state_flags") or {}) or one_time_flags:
        consume_world_event(session, world_event, {
            "unlock_handout_ids": handout_unlock_ids,
            "set_world_state_flags": dict(state_cfg.get("world_state_flags") or {}),
        })

    event_type = ""
    if action_id in {"talk", "speak", "conversation", "hail", "ask"}:
        event_type = "talk_npc"
    elif target_kind == "poi" and action_id in {"inspect", "interact"}:
        event_type = "discover_location"
    if event_type:
        event = {
            "event_type": event_type,
            "target_id": str(target_payload.get("target_id") or ""),
            "target_map_context": str(target_payload.get("map_context") or ""),
        }
        quests = list(getattr(session, "session_quests", []) or [])
        for idx, quest in enumerate(quests):
            entry = normalize_quest_payload_shape(dict(quest or {}))
            if apply_objective_event(entry, event):
                quests[idx] = entry
        session.session_quests = quests

    if target_kind == "prop" and prop_state_changed:
        await _broadcast_editor_props_state(session)
    await save_campaign_async(session)
    await _send_interactable_action_result(session, user.id, result_payload)


async def handle_editor_layer_save(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    cells = payload.get("cells") or {}
    if not isinstance(cells, dict):
        cells = {}
    clean = {}
    for k, v in list(cells.items())[:20000]:
        if not isinstance(k, str) or (":" not in k and "," not in k):
            continue
        try:
            sep = ":" if ":" in k else ","
            xv, yv = k.split(sep, 1)
            int(xv); int(yv)
            vv = int(v)
            k = f"{int(xv)}:{int(yv)}"
        except Exception:
            continue
        if 1 <= vv <= 9999:
            clean[k] = vv
    layers = dict(getattr(session, "editor_layers", {}) or {})
    layers[map_ctx] = clean
    session.editor_layers = layers
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_state(session)
    await save_campaign_async(session)


async def handle_editor_layer_clear(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    layers = dict(getattr(session, "editor_layers", {}) or {})
    layers[map_ctx] = {}
    session.editor_layers = layers
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_state(session)
    await save_campaign_async(session)


async def handle_editor_walls_save(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    walls = payload.get("walls") or []
    if not isinstance(walls, list):
        walls = []
    clean = []
    for seg in walls[:5000]:
        if not isinstance(seg, dict):
            continue
        try:
            x1 = int(seg.get("x1"))
            y1 = int(seg.get("y1"))
            x2 = int(seg.get("x2"))
            y2 = int(seg.get("y2"))
        except Exception:
            continue
        if x1 == x2 and y1 == y2:
            continue
        clean_seg = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        if "kind" in seg:
            clean_seg["kind"] = str(seg.get("kind") or "wall")[:40]
        clean_seg["blocks_movement"] = bool(seg.get("blocks_movement", True))
        clean_seg["blocks_vision"] = bool(seg.get("blocks_vision", True))
        clean.append(clean_seg)
    walls_all = dict(getattr(session, "editor_walls", {}) or {})
    walls_all[map_ctx] = _merge_wall_segments(clean)
    session.editor_walls = walls_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_walls_state(session)
    await save_campaign_async(session)


async def handle_editor_walls_clear(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    walls_all = dict(getattr(session, "editor_walls", {}) or {})
    walls_all[map_ctx] = []
    session.editor_walls = walls_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_walls_state(session)
    await save_campaign_async(session)


def _sanitize_prop_asset_fields(item: dict) -> dict:
    asset_id = str(item.get("asset_id") or "").strip()[:80]
    asset_file = str(item.get("asset_file") or "").strip()[:300]

    if asset_file:
        try:
            normalized = posixpath.normpath(asset_file)
        except Exception:
            normalized = ""
        if normalized.startswith("/api/assets/file/") or normalized.startswith("/static/") or normalized.startswith("/vtt_single_props/"):
            asset_file = normalized
        else:
            asset_file = ""

    asset_anchor = str(item.get("asset_anchor") or "center").strip().lower()
    if asset_anchor not in ("center", "bottom", "top-left"):
        asset_anchor = "center"

    try:
        asset_scale = max(0.1, min(10.0, float(item.get("asset_scale") or 1.0)))
    except Exception:
        asset_scale = 1.0

    asset_name = str(item.get("asset_name") or "").strip()[:80]

    out = {}
    if asset_id:
        out["asset_id"] = asset_id
    if asset_file:
        out["asset_file"] = asset_file
    if asset_name:
        out["asset_name"] = asset_name
    out["asset_anchor"] = asset_anchor
    out["asset_scale"] = asset_scale
    return out


async def handle_editor_props_save(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    props = payload.get("props") or []
    if not isinstance(props, list):
        props = []
    clean = []
    seen = set()
    allowed = {"crate", "table", "tree", "pine", "forest_cluster", "rock", "hill", "mountain", "barrel", "stairs", "chest", "merchant", "store", "shop", "house", "tavern", "blacksmith", "castle", "inn", "temple", "watchtower", "market_stall", "barracks", "dock", "windmill", "manor", "townhall", "guildhall", "stable", "warehouse", "gatehouse", "longhouse", "shop_row", "chapel", "guard_post", "keep", "fountain", "wall_tower", "palisade", "bridge", "settlement_cluster", "market_district", "temple_district", "farm_block", "town_generator", "city_generator", "harbor_generator", "crossing_generator", "town_wall_ring", "door", "opening", "custom_asset"}
    default_slots = {"chest": 12, "merchant": 18, "store": 24, "shop": 24, "tavern": 24, "blacksmith": 24, "market_stall": 18, "inn": 12}
    default_names = {"crate": "Crate", "table": "Table", "tree": "Tree", "pine": "Pine Tree", "forest_cluster": "Forest Cluster", "rock": "Rock", "hill": "Hill", "mountain": "Mountain", "barrel": "Barrel", "stairs": "Stairs", "chest": "Chest", "merchant": "Merchant", "store": "Store Stall", "shop": "Shop", "house": "House", "tavern": "Tavern", "blacksmith": "Blacksmith", "castle": "Castle", "inn": "Inn", "temple": "Temple", "watchtower": "Watchtower", "market_stall": "Market Stall", "barracks": "Barracks", "dock": "Dock", "windmill": "Windmill", "manor": "Manor", "townhall": "Town Hall", "guildhall": "Guild Hall", "stable": "Stable", "warehouse": "Warehouse", "gatehouse": "Gatehouse", "longhouse": "Longhouse", "shop_row": "Shop Row", "chapel": "Chapel", "guard_post": "Guard Post", "keep": "Keep", "fountain": "Fountain", "wall_tower": "Wall Tower", "palisade": "Palisade", "bridge": "Bridge", "settlement_cluster": "Town Cluster", "market_district": "Market District", "temple_district": "Temple District", "farm_block": "Farm Block", "town_generator": "Town Layout", "city_generator": "City Layout", "harbor_generator": "Harbor Layout", "crossing_generator": "Crossing", "town_wall_ring": "Town Wall Ring", "door": "Door", "opening": "Opening"}
    for item in props[:5000]:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "crate").strip().lower()
        if kind not in allowed:
            kind = "crate"
        try:
            x = int(round(float(item.get("x", 0)) / 50.0) * 50)
            y = int(round(float(item.get("y", 0)) / 50.0) * 50)
            w = max(1, min(6, int(item.get("w", 1))))
            h = max(1, min(6, int(item.get("h", 1))))
            default_slot_count = default_slots.get(kind, 0)
            slot_count = int(item.get("slot_count", default_slot_count))
            if kind in {"chest", "merchant", "store", "shop", "tavern", "blacksmith", "market_stall", "inn"}:
                slot_count = max(1, min(60, slot_count or default_slot_count or 1))
            else:
                slot_count = max(0, min(60, slot_count))
        except Exception:
            continue
        item_id = str(item.get("id") or secrets.token_hex(6))[:48]
        name = str(item.get("name") or default_names.get(kind, "Prop")).strip()[:60] or default_names.get(kind, "Prop")
        _can_be_hidden = {"chest", "merchant", "store", "tavern", "blacksmith", "market_stall", "inn", "shop"}
        hidden = bool(item.get("hidden")) if kind in _can_be_hidden else False
        rotation = int(round(float(item.get("rotation", 0) or 0) / 90.0) * 90) % 360
        facing = "v" if str(item.get("facing") or item.get("orientation") or "h").strip().lower().startswith("v") else "h"
        inventory = []
        raw_inventory = item.get("inventory") or []
        if isinstance(raw_inventory, list):
            is_shop = kind in {"merchant", "store", "shop", "tavern", "blacksmith", "market_stall", "inn"}
            for entry in raw_inventory[: slot_count or 60]:
                if isinstance(entry, dict):
                    entry_name = str(entry.get("name") or "").strip()[:80]
                    if not entry_name:
                        continue
                    try:
                        qty = max(1, min(999, int(entry.get("qty", 1))))
                    except Exception:
                        qty = 1
                    clean_entry = {"name": entry_name, "qty": qty}
                    notes = str(entry.get("notes") or entry.get("note") or "").strip()[:160]
                    if notes:
                        clean_entry["notes"] = notes
                    if is_shop:
                        price = str(entry.get("price") or "").strip()[:32]
                        if price:
                            clean_entry["price"] = price
                        clean_entry["infinite"] = bool(entry.get("infinite") or entry.get("unlimited"))
                    inventory.append(clean_entry)
                else:
                    entry_name = str(entry or "").strip()[:80]
                    if entry_name:
                        inventory.append({"name": entry_name, "qty": 1})
        sig = (kind, x, y, w, h, facing if kind in {"door", "opening"} else "", rotation if kind not in {"door", "opening"} else 0)
        if sig in seen:
            continue
        seen.add(sig)
        clean_item = {
            "id": item_id, "kind": kind, "x": x, "y": y, "w": w, "h": h,
            "hidden": hidden, "rotation": rotation, "facing": facing if kind in {"door", "opening"} else None, "name": name, "slot_count": slot_count, "inventory": inventory,
        }
        if kind in {"door", "opening"}:
            clean_item["state"] = "open" if kind == "opening" else ("open" if str(item.get("state") or "closed").strip().lower() == "open" else "closed")
            clean_item["locked"] = bool(item.get("locked", False)) if kind == "door" else False
            clean_item["blocks_movement"] = bool(item.get("blocks_movement", True)) if kind == "door" else False
            clean_item["blocks_vision"] = bool(item.get("blocks_vision", True)) if kind == "door" else False
        if kind == "custom_asset":
            clean_item.update(_sanitize_prop_asset_fields(item))
        interactable = normalize_interactable(item.get("interactable"))
        if interactable:
            clean_item["interactable"] = interactable
        clean.append(clean_item)
    props_all = dict(getattr(session, "editor_props", {}) or {})
    props_all[map_ctx] = clean
    session.editor_props = props_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_props_state(session)
    await save_campaign_async(session)


async def handle_editor_props_clear(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    props_all = dict(getattr(session, "editor_props", {}) or {})
    props_all[map_ctx] = []
    session.editor_props = props_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_props_state(session)
    await save_campaign_async(session)


async def handle_editor_paths_save(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    items = payload.get("paths") or []
    if not isinstance(items, list):
        items = []
    clean = []
    for raw in items[:1000]:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "road").strip().lower()
        if kind not in {"road", "river"}:
            kind = "road"
        style = str(raw.get("style") or ("water" if kind == "river" else "dirt")).strip().lower()[:24]
        try:
            width = max(0.5, min(6.0, float(raw.get("width", 1.0))))
        except Exception:
            width = 1.0
        points = []
        for pt in list(raw.get("points") or [])[:300]:
            if not isinstance(pt, dict):
                continue
            try:
                x = int(round(float(pt.get("x", 0))))
                y = int(round(float(pt.get("y", 0))))
            except Exception:
                continue
            points.append({"x": x, "y": y})
        if len(points) < 2:
            continue
        clean.append({
            "id": str(raw.get("id") or secrets.token_hex(6))[:48],
            "kind": kind,
            "style": style,
            "width": width,
            "points": points,
        })
    paths_all = dict(getattr(session, "editor_paths", {}) or {})
    paths_all[map_ctx] = clean
    session.editor_paths = paths_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_world_state(session)
    await save_campaign_async(session)


async def handle_editor_paths_clear(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    paths_all = dict(getattr(session, "editor_paths", {}) or {})
    paths_all[map_ctx] = []
    session.editor_paths = paths_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_world_state(session)
    await save_campaign_async(session)


async def handle_editor_labels_save(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    items = payload.get("labels") or []
    if not isinstance(items, list):
        items = []
    clean = []
    for raw in items[:1000]:
        if not isinstance(raw, dict):
            continue
        text_value = str(raw.get("text") or "").strip()[:80]
        if not text_value:
            continue
        size = str(raw.get("size") or "medium").strip().lower()
        if size not in {"small", "medium", "large"}:
            size = "medium"
        try:
            x = int(round(float(raw.get("x", 0))))
            y = int(round(float(raw.get("y", 0))))
            curve = max(-1.0, min(1.0, float(raw.get("curve", 0.0))))
        except Exception:
            continue
        clean.append({
            "id": str(raw.get("id") or secrets.token_hex(6))[:48],
            "x": x,
            "y": y,
            "text": text_value,
            "size": size,
            "curve": curve,
        })
    labels_all = dict(getattr(session, "editor_labels", {}) or {})
    labels_all[map_ctx] = clean
    session.editor_labels = labels_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_world_state(session)
    await save_campaign_async(session)


async def handle_editor_labels_clear(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    labels_all = dict(getattr(session, "editor_labels", {}) or {})
    labels_all[map_ctx] = []
    session.editor_labels = labels_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_world_state(session)
    await save_campaign_async(session)


async def handle_editor_markers_save(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    items = payload.get("markers") or []
    if not isinstance(items, list):
        items = []
    clean = []
    allowed = {"city", "town", "settlement", "ruin", "shop", "tavern", "camp", "landmark", "blacksmith", "market", "castle", "harbor", "forest", "mountain"}
    for raw in items[:1000]:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind") or "landmark").strip().lower()
        if kind not in allowed:
            kind = "landmark"
        try:
            x = int(round(float(raw.get("x", 0))))
            y = int(round(float(raw.get("y", 0))))
        except Exception:
            continue
        clean.append({
            "id": str(raw.get("id") or secrets.token_hex(6))[:48],
            "kind": kind,
            "x": x,
            "y": y,
            "name": str(raw.get("name") or raw.get("text") or kind.title()).strip()[:80],
            "linked_map_url": str(raw.get("linked_map_url") or "")[:400],
            "linked_poi_id": str(raw.get("linked_poi_id") or "")[:80],
        })
    markers_all = dict(getattr(session, "editor_markers", {}) or {})
    markers_all[map_ctx] = clean
    session.editor_markers = markers_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_world_state(session)
    await save_campaign_async(session)


async def handle_editor_markers_clear(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    markers_all = dict(getattr(session, "editor_markers", {}) or {})
    markers_all[map_ctx] = []
    session.editor_markers = markers_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_world_state(session)
    await save_campaign_async(session)


async def handle_map_settings_save(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    settings = normalize_map_settings(payload.get("settings") or {})
    all_settings = dict(getattr(session, "map_settings", {}) or {})
    all_settings[map_ctx] = settings
    session.map_settings = all_settings
    _refresh_map_documents(session, map_ctx)
    await manager.broadcast(session.id, {
        "type": "map_settings_sync",
        "payload": {"map_settings": dict(session.map_settings or {})}
    })
    await save_campaign_async(session)


async def handle_door_toggle(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    prop_id = str(payload.get("prop_id") or "").strip()[:48]
    if not prop_id:
        return
    props_all = dict(getattr(session, "editor_props", {}) or {})
    items = list(props_all.get(map_ctx) or [])
    changed = False
    for item in items:
        if str(item.get("id") or "") != prop_id or str(item.get("kind") or "") != "door":
            continue
        if bool(item.get("locked", False)) and str(item.get("state") or "closed").strip().lower() != "open":
            item["state"] = "closed"
        else:
            item["state"] = "open" if str(item.get("state") or "closed").strip().lower() != "open" else "closed"
        changed = True
        break
    if not changed:
        return
    props_all[map_ctx] = items
    session.editor_props = props_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_props_state(session)
    await save_campaign_async(session)


async def handle_door_lock_set(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    map_ctx = str(payload.get("map_context") or "world")[:80]
    prop_id = str(payload.get("prop_id") or "").strip()[:48]
    if not prop_id:
        return
    locked = bool(payload.get("locked"))
    props_all = dict(getattr(session, "editor_props", {}) or {})
    items = list(props_all.get(map_ctx) or [])
    changed = False
    for item in items:
        if str(item.get("id") or "") != prop_id or str(item.get("kind") or "") != "door":
            continue
        item["locked"] = locked
        if locked:
            item["state"] = "closed"
        changed = True
        break
    if not changed:
        return
    props_all[map_ctx] = items
    session.editor_props = props_all
    _refresh_map_documents(session, map_ctx)
    await _broadcast_editor_props_state(session)
    await save_campaign_async(session)


async def handle_fog_toggle(payload: dict, session: Session, user: User):
    """DM toggles fog on/off for the current map only."""
    map_ctx = _resolve_fog_map_context(session, payload)
    if user.role != 'dm' and not assistant_dm_has_scope(session, user, "maps.fog", map_ctx=map_ctx):
        return
    if session.fog_maps is None:
        session.fog_maps = {}
    entry = session.fog_maps.get(map_ctx, {'enabled': False, 'cols': 64, 'rows': 64, 'cells': ''})
    if 'enabled' in payload:
        entry['enabled'] = bool(payload['enabled'])
    else:
        entry['enabled'] = not entry.get('enabled', False)
    total = entry['cols'] * entry['rows']
    if entry['enabled'] and len(entry.get('cells', '')) != total:
        entry['cells'] = '0' * total
    session.fog_maps[map_ctx] = entry
    await _broadcast_fog_to_visible_users(session, {
        'type': 'fog_state',
        'payload': {
            'map_ctx': map_ctx,
            'fog_enabled': entry['enabled'],
            'fog_cols': entry['cols'],
            'fog_rows': entry['rows'],
            'fog_cells': entry['cells'],
        }
    }, map_ctx)
    await save_campaign_async(session)


async def handle_fog_paint(payload: dict, session: Session, user: User):
    """DM paints reveal/hide cells on fog grid."""
    reveal = bool(payload.get('reveal', True))
    map_ctx = _resolve_fog_map_context(session, payload)
    if user.role != 'dm' and not assistant_dm_has_scope(session, user, "maps.fog", map_ctx=map_ctx):
        return
    cells = payload.get('cells', [])
    if session.fog_maps is None:
        session.fog_maps = {}
    if map_ctx not in session.fog_maps:
        session.fog_maps[map_ctx] = {'enabled': True, 'cols': 64, 'rows': 64, 'cells': '0' * 64 * 64}
    entry = session.fog_maps[map_ctx]
    if not entry.get('enabled', False):
        return
    total = entry['cols'] * entry['rows']
    if len(entry['cells']) != total:
        entry['cells'] = '0' * total
    arr = list(entry['cells'])
    for idx in cells:
        if 0 <= idx < total:
            arr[idx] = '1' if reveal else '0'
    entry['cells'] = ''.join(arr)
    await _broadcast_fog_to_visible_users(session, {
        'type': 'fog_update',
        'payload': {
            'map_ctx': map_ctx,
            'reveal': reveal,
            'cells': cells,
        }
    }, map_ctx)
    await save_campaign_async(session)


async def handle_spell_marker_relay(payload: dict, session: Session, user: User):
    """Relay spell markers to all other clients."""
    msg_type = payload.pop('_msg_type', 'spell_marker_add')
    await manager.broadcast(session.id, {
        'type': msg_type,
        'payload': payload,
    }, exclude_user=user.id)


async def handle_ruler_broadcast(payload: dict, session: Session, user: User):
    """DM can broadcast a ruler measurement to all players."""
    if user.role not in ("dm", "player"):
        return

    await manager.broadcast(session.id, {
        "type": "ruler_shown",
        "payload": {
            "user_name": user.name,
            "x1": payload.get("x1"),
            "y1": payload.get("y1"),
            "x2": payload.get("x2"),
            "y2": payload.get("y2"),
            "distance_px": payload.get("distance_px"),
            "distance_ft": payload.get("distance_ft"),
        }
    }, exclude_user=user.id)


async def handle_ping_map(payload: dict, session: Session, user: User):
    if user.role == "viewer":
        return
    try:
        x = float(payload.get("x"))
        y = float(payload.get("y"))
    except Exception:
        return
    if not (-100000.0 <= x <= 100000.0 and -100000.0 <= y <= 100000.0):
        return
    map_ctx = str(payload.get("map_context") or session.dm_map_context or "world").strip()[:80] or "world"
    if user.role == "player":
        settings_all = dict(getattr(session, "map_settings", {}) or {})
        map_settings = settings_all.get(map_ctx) if isinstance(settings_all.get(map_ctx), dict) else {}
        world_settings = map_settings.get("world") if isinstance(map_settings.get("world"), dict) else {}
        if bool(world_settings.get("allow_player_ping", True)) is False:
            return
    mode = str(payload.get("mode") or "ping").strip().lower()
    if mode not in {"ping", "point"}:
        mode = "ping"
    now_ms = int(time.time() * 1000)
    throttle = dict(getattr(session, "_ping_throttle", {}) or {})
    user_key = f"{user.id}:{mode}"
    min_gap = 80 if mode == "point" else 260
    if now_ms - int(throttle.get(user_key, 0) or 0) < min_gap:
        return
    throttle[user_key] = now_ms
    session._ping_throttle = throttle
    color = str(payload.get("color") or "#f1c40f").strip()[:16] or "#f1c40f"
    await manager.broadcast(session.id, {
        "type": "map_ping",
        "payload": {
            "x": x,
            "y": y,
            "user_name": user.name,
            "color": color,
            "mode": mode,
            "user_role": user.role,
            "map_context": map_ctx,
        }
    }, exclude_user=user.id)


async def handle_poi_create(payload: dict, session: Session, user: User):
    from server.session import POI
    import secrets as _secrets
    if user.role != "dm":
        await manager.send_to(session.id, user.id, {"type": "error", "payload": {"message": "Only DM can place POIs."}})
        return
    poi = POI(
        id=_secrets.token_hex(6),
        x=payload.get("x", 0), y=payload.get("y", 0),
        name=payload.get("name", "Location"),
        description=payload.get("description", ""),
        dm_notes=payload.get("dm_notes", ""),
        poi_type=payload.get("poi_type", "city"),
        map_context=payload.get("map_context", "world"),
        revealed_to_players=bool(payload.get("revealed_to_players", True)),
        interactable=normalize_interactable(payload.get("interactable")),
    )
    session.pois[poi.id] = poi
    await manager.broadcast(session.id, {
        "type": "poi_created",
        "payload": {"poi": poi.to_dict(include_dm_notes=False), "poi_dm": poi.to_dict(include_dm_notes=True)}
    })
    await save_campaign_async(session)


async def handle_poi_update(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    poi = session.pois.get(payload.get("poi_id"))
    if not poi:
        return
    if "name"                in payload: poi.name                = payload["name"]
    if "description"         in payload: poi.description         = payload["description"]
    if "dm_notes"            in payload: poi.dm_notes            = payload["dm_notes"]
    if "poi_type"            in payload: poi.poi_type            = payload["poi_type"]
    if "revealed_to_players" in payload: poi.revealed_to_players = bool(payload["revealed_to_players"])
    if "interactable"        in payload: poi.interactable        = normalize_interactable(payload.get("interactable"))
    # Allow DM to link a pre-saved local map URL (must be a /static/ path for security)
    if "local_map_url" in payload:
        url = str(payload["local_map_url"] or "").strip()
        if url.startswith("/static/"):
            poi.local_map_url = url
        elif url == "":
            poi.local_map_url = None
    await manager.broadcast(session.id, {
        "type": "poi_updated",
        "payload": {"poi": poi.to_dict(include_dm_notes=False), "poi_dm": poi.to_dict(include_dm_notes=True)}
    })
    await save_campaign_async(session)


async def handle_poi_delete(payload: dict, session: Session, user: User):
    if user.role != "dm":
        return
    poi_id = payload.get("poi_id")
    if poi_id in session.pois:
        del session.pois[poi_id]
    await manager.broadcast(session.id, {
        "type": "poi_deleted",
        "payload": {"poi_id": poi_id}
    })
    await save_campaign_async(session)


async def handle_bring_all_to_map(payload: dict, session: Session, user: User):
    """DM brings all connected players into a local map."""
    if user.role != "dm":
        return
    await manager.broadcast(session.id, {
        "type": "bring_all_to_map",
        "payload": payload,
    })


async def handle_local_map_nav(payload: dict, session: Session, user: User):
    """Track DM map context server-side and relay to all clients."""
    payload = dict(payload or {}) if isinstance(payload, dict) else {}
    try:
        if not user or getattr(user, "role", None) != "dm":
            return

        try:
            incoming_intent = int(payload.get("client_nav_intent") or 0)
        except Exception:
            incoming_intent = 0
        try:
            current_intent = int(getattr(session, "dm_nav_intent", 0) or 0)
        except Exception:
            current_intent = 0

        if incoming_intent and current_intent and incoming_intent < current_intent:
            return
        if incoming_intent >= current_intent:
            session.dm_nav_intent = incoming_intent

        requested_ctx = str(payload.get("dm_map_context") or "").strip()
        if not requested_ctx:
            requested_ctx = str(payload.get("poi_id") or payload.get("map_context") or "").strip()
        target_ctx = _normalize_dm_map_context(
            session,
            requested_ctx or ("world" if not payload.get("map_url") else getattr(session, "dm_map_context", "world")),
        )

        is_enter = target_ctx != "world"
        if is_enter:
            resolved_map_url = _resolve_local_map_url(session, target_ctx, fallback=payload.get("map_url"))
            session.dm_map_context = target_ctx
            session.dm_current_map_url = resolved_map_url
        else:
            session.dm_map_context = "world"
            session.dm_current_map_url = None

        try:
            session.map_nav_version = int(getattr(session, "map_nav_version", 0) or 0) + 1
        except Exception:
            session.map_nav_version = 1

        nav_payload = dict(payload)
        nav_payload["dm_map_context"] = str(getattr(session, "dm_map_context", "world") or "world")
        nav_payload["dm_current_map_url"] = getattr(session, "dm_current_map_url", None)
        nav_payload["nav_version"] = int(getattr(session, "map_nav_version", 0) or 0)
        nav_payload["client_nav_intent"] = int(getattr(session, "dm_nav_intent", 0) or 0)

        msg_type = "local_map_enter" if is_enter else "local_map_exit"
        msg = {"type": msg_type, "payload": nav_payload}

        try:
            await manager.broadcast(session.id, msg, exclude_user=getattr(user, "id", None))
        except Exception as broadcast_err:
            logger.error("[WS] local_map_nav broadcast error: %s; payload=%r", broadcast_err, payload)

        try:
            await manager.send_to(session.id, user.id, msg)
        except Exception as echo_err:
            logger.error("[WS] local_map_nav echo error: %s; payload=%r", echo_err, payload)

        if not payload.get("resync"):
            try:
                await save_campaign_async(session)
            except Exception as save_err:
                logger.error("[WS] local_map_nav save error: %s; payload=%r", save_err, payload)
    except Exception as e:
        logger.error("[WS] local_map_nav internal error: %s; payload=%r", e, payload)
        return


async def handle_weather_set(payload: dict, session: Session, user: User):
    """DM-only. Saves weather to map_settings and broadcasts weather_sync."""
    if getattr(user, 'role', None) != 'dm':
        return {"type": "error", "payload": {"message": "DM only."}}

    map_ctx    = payload.get("map_context", getattr(session, "current_map", "default"))
    w_type     = payload.get("weather_type", "none")
    intensity  = max(0.0, min(1.0, float(payload.get("intensity", 0.5))))
    wind_angle = max(0.0, min(360.0, float(payload.get("wind_angle", 0.0))))
    wind_speed = max(0.0, min(1.0,   float(payload.get("wind_speed", 0.3))))

    weather_cfg = {
        "weather_type": w_type,
        "intensity":    intensity,
        "wind_angle":   wind_angle,
        "wind_speed":   wind_speed,
    }

    if not hasattr(session, "map_settings") or session.map_settings is None:
        session.map_settings = {}
    session.map_settings.setdefault(map_ctx, {})["weather"] = weather_cfg

    # Save to session-level weather_state for join-sync
    session.weather_state = {**weather_cfg, "map_context": map_ctx}
    await save_campaign_async(session)

    await manager.broadcast(session.id, {
        "type": "weather_sync",
        "payload": {**weather_cfg, "map_context": map_ctx},
    })
    return None


async def handle_map_set_url(payload: dict, session: Session, user: User):
    """DM-only. Assign an existing map URL to the active world or POI scene."""
    if getattr(user, 'role', None) != 'dm':
        return {"type": "error", "payload": {"message": "DM only."}}

    url = str(payload.get("map_image_url") or "").strip()
    map_ctx = str(payload.get("map_context") or payload.get("scene_id") or payload.get("poi_id") or 'world').strip() or 'world'
    if not url:
        return {"type": "error", "payload": {"message": "No map URL provided."}}

    if not url.startswith("/static/"):
        return {"type": "error", "payload": {"message": "Invalid map URL."}}

    before_world = str(getattr(session, 'map_image_url', '') or '') or None
    before_poi = None
    if map_ctx != 'world':
        poi = session.pois.get(map_ctx)
        if not poi:
            return {"type": "error", "payload": {"message": "Target POI not found.", "map_context": map_ctx}}
        before_poi = str(getattr(poi, 'local_map_url', '') or '') or None
        poi.local_map_url = url
    else:
        session.map_image_url = url

    _refresh_map_documents(session, map_ctx)
    logger.info("[SceneMapAssign] session_id=%s map_context=%s world_before=%r poi_before=%r assigned_url=%r world_after=%r poi_after=%r", session.id, map_ctx, before_world, before_poi, url, getattr(session, 'map_image_url', None), getattr(session.pois.get(map_ctx), 'local_map_url', None) if map_ctx != 'world' else None)
    await save_campaign_async(session)

    payload_out = {"map_image_url": url, "map_context": map_ctx}
    await manager.broadcast(session.id, {"type": "map_changed", "payload": payload_out})
    if map_ctx != 'world':
        poi = session.pois.get(map_ctx)
        await manager.broadcast(session.id, {
            "type": "poi_updated",
            "payload": {"poi": poi.to_dict(include_dm_notes=False), "poi_dm": poi.to_dict(include_dm_notes=True)}
        })
    return None
