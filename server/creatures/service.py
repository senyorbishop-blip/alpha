import logging
import time
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse

from server.db import (
    create_creature,
    create_creature_variant,
    delete_creature,
    get_creature,
    get_creature_any,
    get_creatures,
    is_creature_owned_by_user,
    save_creature_edits,
    seed_srd_for_user,
    seed_srd_npcs_for_user,
    update_creature,
)
from server.http.auth import get_request_user
from server.http.session_access import (
    can_user_place_creatures,
    get_or_restore_session,
    request_has_dm_access,
)

logger = logging.getLogger(__name__)


def _require_dm_request(request: Request, *, session_id: str = "", fallback_user_id: str = "") -> JSONResponse | None:
    auth_user = get_request_user(request) or {}
    auth_role = str(auth_user.get("role") or "").strip().lower()
    session_id = str(session_id or "").strip().upper()
    if session_id:
        session = get_or_restore_session(session_id)
        if not session:
            return JSONResponse({"error": "Session not found."}, status_code=404)
        if not request_has_dm_access(request, session, fallback_user_id=fallback_user_id):
            return JSONResponse({"error": "DM only."}, status_code=403)
        return None
    if auth_role != "dm":
        return JSONResponse({"error": "DM only."}, status_code=403)
    return None


def parse_speed_ft(speed_str) -> int | None:
    if not speed_str:
        return None
    import re

    match = re.search(r"(\d+)", str(speed_str))
    return int(match.group(1)) if match else None


def resolve_library_owner(request: Request, query_owner_id: str = "") -> str:
    auth_user = get_request_user(request)
    if auth_user:
        return str(auth_user["id"])
    if query_owner_id:
        return str(query_owner_id).strip()[:100]
    return "anonymous"


def _map_grid_size_px(session, map_ctx: str, requested_grid_size_px=None) -> int:
    """Return the active grid size for a map context, matching play.html defaults."""
    try:
        requested = int(round(float(requested_grid_size_px)))
    except Exception:
        requested = 0
    if 16 <= requested <= 256:
        return requested
    try:
        settings = (getattr(session, "map_settings", {}) or {}).get(str(map_ctx or "world") or "world") or {}
        grid = (settings.get("grid") or {}) if isinstance(settings, dict) else {}
        size = int(round(float(grid.get("size_px") or 64)))
    except Exception:
        size = 64
    return max(16, min(256, size))


def _creature_token_squares(creature: dict) -> int:
    try:
        return max(1, min(4, int(creature.get("token_size", 1) or 1)))
    except Exception:
        return 1


def _creature_token_px(creature: dict, grid_size_px: int) -> int:
    return int(max(1, _creature_token_squares(creature)) * max(16, min(256, int(grid_size_px or 64))))


async def spawn_creature_from_library_entry(
    *,
    session,
    creature_id: str,
    dm_user_id: str,
    request_source: str = "",
    request_entity_type: str = "",
    x: float = 0.0,
    y: float = 0.0,
    map_ctx: str = "world",
    session_user=None,
    grid_size_px=None,
):
    creature = get_creature_any(str(creature_id or "").strip())
    if not creature:
        return None

    resolved_source = str(creature.get("source_type") or creature.get("source") or "").lower()
    if request_source and request_source != resolved_source:
        return None
    resolved_entity_type = str(creature.get("entry_type") or creature.get("creature_type") or "").lower()
    if request_entity_type and request_entity_type != resolved_entity_type:
        return None

    owner_user_id = str(creature.get("owner_user_id") or "").strip()
    is_owned = is_creature_owned_by_user(creature, dm_user_id)
    is_shared_source = resolved_source in {"srd", "builtin", "shared", "system"}
    if not is_owned and not is_shared_source:
        logger.warning(
            "[CreatureSpawn] denied creature_id=%s auth_user_id=%s owner_user_id=%s",
            creature_id, dm_user_id, owner_user_id
        )
        return None

    from server.session import create_token, build_token_runtime_payload
    from server.connections import manager
    from server.handlers.common import _broadcast_token_event

    active_grid_size_px = _map_grid_size_px(session, map_ctx, grid_size_px)
    token_px = _creature_token_px(creature, active_grid_size_px)
    token = create_token(
        session=session,
        dm_id=dm_user_id,
        name=creature["name"],
        x=float(x),
        y=float(y),
        color="#e74c3c",
        shape="circle",
        width=token_px,
        height=token_px,
        owner_id=None,
        hp=creature.get("hp"),
        max_hp=creature.get("hp"),
        ac=creature.get("ac"),
        speed=parse_speed_ft(creature.get("speed")),
        token_type="monster" if creature.get("creature_type") == "monster" else "npc",
        notes=creature.get("backstory", ""),
        map_context=map_ctx,
        image_url=creature.get("portrait_url"),
        creature_id=str(creature.get("id") or creature_id or "")[:120],
        creature_type=str(creature.get("creature_type") or creature.get("entry_type") or "monster")[:40],
        monster_type=str(creature.get("monster_type") or "")[:60],
        cr=str(creature.get("cr") or "")[:16],
    )
    if is_owned:
        update_creature(creature_id, dm_user_id, {
            "last_used_at": time.time(),
            "use_count": int(creature.get("use_count", 0) or 0) + 1,
        })
    log_entry = session.add_log(f"{getattr(session_user, 'name', 'DM')} spawned '{creature['name']}' from bestiary.", "system")
    # Only deliver the full token payload to clients who can actually see this
    # token (hidden/staged/fog/wall-LOS rules) — never broadcast unconditionally,
    # since a spawned creature can be a hidden ambush monster.
    await _broadcast_token_event(manager, session, "token_created", {
        "token": build_token_runtime_payload(session, token),
        "log": log_entry,
        "from_bestiary": True,
        "creature_id": str(creature_id),
        "source": resolved_source,
    }, token)
    return token


async def seed_library_for_owner(owner_user_id: str) -> None:
    import asyncio as _asyncio

    loop = _asyncio.get_running_loop()
    await loop.run_in_executor(None, seed_srd_for_user, owner_user_id)
    await loop.run_in_executor(None, seed_srd_npcs_for_user, owner_user_id)


async def list_creatures_response(request: Request, **filters):
    session_id = str(filters.pop("session_id", "") or "").strip().upper()
    owner_id = str(filters.pop("owner_id", "") or "").strip()
    denied = _require_dm_request(request, session_id=session_id, fallback_user_id=owner_id)
    if denied:
        return denied
    owner_user_id = resolve_library_owner(request, owner_id)
    await seed_library_for_owner(owner_user_id)
    creatures = get_creatures(owner_user_id=owner_user_id, **filters)
    return JSONResponse({"creatures": creatures, "total": len(creatures)})


async def portrait_upload_response(file, asset_id_builder):
    import io
    from pathlib import Path as _Path

    raw = await file.read()
    if len(raw) > 8 * 1024 * 1024:
        return JSONResponse({"ok": False, "error": "File too large (max 8 MB)."}, status_code=400)

    orig_ext = _Path(file.filename or "").suffix.lower()
    content_type = (file.content_type or "").lower()
    is_svg = orig_ext == ".svg" or content_type == "image/svg+xml"
    if not is_svg:
        try:
            from PIL import Image

            probe = Image.open(io.BytesIO(raw))
            probe.verify()
        except Exception:
            return JSONResponse({"ok": False, "error": "File is not a valid image."}, status_code=400)

    asset_id = asset_id_builder(file.filename or "portrait")
    loop = __import__("asyncio").get_running_loop()

    def _do_save():
        uploads_dir = Path("client/static/assets/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        ext = orig_ext if orig_ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg") else ".png"
        dest = uploads_dir / f"{asset_id}{ext}"
        dest.write_bytes(raw)
        return f"/static/assets/uploads/{asset_id}{ext}"

    try:
        url = await loop.run_in_executor(None, _do_save)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
    return JSONResponse({"ok": True, "url": url})


def create_creature_response(owner_user_id: str, data: dict):
    if not str(data.get("name", "")).strip():
        return JSONResponse({"error": "name is required"}, status_code=400)
    creature = create_creature(owner_user_id, data)
    if not creature:
        return JSONResponse({"error": "Failed to create creature"}, status_code=500)
    return JSONResponse({"creature": creature}, status_code=201)


def update_creature_response(creature_id: str, owner_user_id: str, data: dict):
    saved, mode = save_creature_edits(creature_id, owner_user_id, data)
    if not saved:
        original = get_creature_any(creature_id)
        if original:
            return JSONResponse({"error": "This creature is read-only; create a custom copy to edit."}, status_code=403)
        return JSONResponse({"error": "Creature not found."}, status_code=404)
    return JSONResponse({"creature": saved, "save_mode": mode})


def variant_creature_response(creature_id: str, owner_user_id: str, body: dict):
    original = get_creature_any(creature_id)
    if not original:
        return JSONResponse({"error": "Creature not found."}, status_code=404)
    variant_name = str(body.get("name", "") or "").strip() or f"{original['name']} (Variant)"
    new_creature = create_creature_variant(owner_user_id, original, body, variant_name=variant_name)
    if not new_creature:
        return JSONResponse({"error": "Failed to create variant"}, status_code=500)
    return JSONResponse({"creature": new_creature}, status_code=201)


def delete_creature_response(creature_id: str, owner_user_id: str):
    existing = get_creature(creature_id, owner_user_id)
    if not existing:
        return JSONResponse({"error": "Creature not found or not owned by you"}, status_code=404)
    ok = delete_creature(creature_id, owner_user_id)
    if not ok:
        return JSONResponse({"error": "Delete failed"}, status_code=500)
    return JSONResponse({"ok": True})


async def spawn_creature_response(creature_id: str, request: Request, body: dict):
    auth_user = get_request_user(request)
    auth_user_id = str((auth_user or {}).get("id") or "").strip()
    payload_creature_id = str(body.get("creature_id", "") or "").strip()
    canonical_creature_id = payload_creature_id or str(creature_id or "").strip()
    source = str(body.get("source", "") or "").strip().lower()
    entity_type = str(body.get("entity_type", "") or "").strip().lower()
    session_id = str(body.get("session_id", "")).strip().upper()
    request_user_id = str(body.get("user_id", "")).strip()
    map_ctx = str(body.get("map_context", "world") or "world")

    def error_response(status_code: int, code: str, message: str, *, details: dict | None = None):
        payload = {"code": code, "message": message, "details": details or {}}
        logger.warning("[CreatureSpawn] rejected status=%s code=%s details=%s", status_code, code, payload["details"])
        return JSONResponse(payload, status_code=status_code)

    logger.info(
        "[CreatureSpawn] incoming payload creature_id=%s path_creature_id=%s source=%s entity_type=%s "
        "session_id=%s auth_user_id=%s body_user_id=%s map_context=%s raw=%s",
        canonical_creature_id,
        creature_id,
        source or "<missing>",
        entity_type or "<missing>",
        session_id or "<missing>",
        auth_user_id or "<unauthenticated>",
        request_user_id or "<missing>",
        map_ctx,
        body,
    )

    if not auth_user_id:
        return error_response(401, "unauthenticated", "You must be signed in to place creatures.", details={"session_id": session_id})
    if not session_id:
        return error_response(400, "invalid_payload", "session_id is required.", details={"field": "session_id"})
    if not canonical_creature_id:
        return error_response(400, "invalid_payload", "creature_id is required.", details={"field": "creature_id"})
    if payload_creature_id and payload_creature_id != str(creature_id or ""):
        return error_response(
            409,
            "creature_id_mismatch",
            "The request creature_id does not match the route creature identifier.",
            details={"route_creature_id": str(creature_id or ""), "payload_creature_id": payload_creature_id},
        )
    if source and source not in {"custom", "variant", "imported", "shared", "srd", "builtin"}:
        return error_response(400, "invalid_payload", "Unsupported creature source.", details={"field": "source", "value": source})
    if entity_type and entity_type not in {"monster", "npc"}:
        return error_response(400, "invalid_payload", "Unsupported entity_type.", details={"field": "entity_type", "value": entity_type})

    session = get_or_restore_session(session_id)
    if not session:
        return error_response(404, "session_not_found", "Session not found.", details={"session_id": session_id})

    session_user = session.users.get(auth_user_id) or session.users.get(request_user_id)
    session_role = getattr(session_user, "role", None)
    permission = can_user_place_creatures(
        session,
        user=session_user,
        connection={"user_id": request_user_id},
        mode=str(body.get("mode") or body.get("ui_mode") or body.get("view_mode") or ""),
        request=request,
        fallback_user_id=request_user_id,
    )
    logger.info(
        "[CreatureSpawn] permission session_id=%s auth_user_id=%s request_user_id=%s session_role=%s session_dm_id=%s frontend_mode=%s allowed=%s reason=%s authority=%s",
        session_id,
        auth_user_id,
        request_user_id or "<missing>",
        session_role or "<missing>",
        str(getattr(session, "dm_id", "") or ""),
        permission.get("ui_mode") or "<unspecified>",
        permission.get("allowed"),
        permission.get("reason"),
        permission.get("authority"),
    )
    if not permission.get("allowed"):
        return error_response(
            403,
            "spawn_not_allowed",
            "Only the session DM can place creatures on the map.",
            details={
                "session_id": session_id,
                "auth_user_id": auth_user_id,
                "request_user_id": request_user_id or None,
                "session_role": session_role,
                "session_dm_id": getattr(session, "dm_id", None),
                "permission_reason": permission.get("reason"),
                "authority": permission.get("authority"),
            },
        )

    creature = get_creature_any(canonical_creature_id)
    if not creature:
        logger.warning(
            "[CreatureSpawn] lookup result missing creature_id=%s source=%s auth_user_id=%s session_id=%s",
            canonical_creature_id, source or "<unknown>", auth_user_id, session_id
        )
        return error_response(
            404,
            "creature_not_found",
            "Creature not found.",
            details={"creature_id": canonical_creature_id, "source": source or None},
        )

    resolved_source = str(creature.get("source_type") or creature.get("source") or "").lower()
    owner_user_id = str(creature.get("owner_user_id") or "").strip()
    is_owned = is_creature_owned_by_user(creature, auth_user_id)
    is_shared_source = resolved_source in {"srd", "builtin", "shared", "system"}
    lookup_result = {
        "resolved_source": resolved_source,
        "owner_user_id": owner_user_id,
        "is_owned": is_owned,
        "is_shared_source": is_shared_source,
        "session_role": session_role,
    }
    logger.info("[CreatureSpawn] lookup result creature_id=%s result=%s", canonical_creature_id, lookup_result)
    if source and source != resolved_source:
        return error_response(
            409,
            "creature_source_mismatch",
            "Creature source does not match the requested source.",
            details={"creature_id": canonical_creature_id, "requested_source": source, "resolved_source": resolved_source},
        )
    if entity_type and entity_type != str(creature.get("entry_type") or creature.get("creature_type") or "").lower():
        return error_response(
            409,
            "entity_type_mismatch",
            "Creature entity type does not match the requested entity_type.",
            details={"creature_id": canonical_creature_id, "requested_entity_type": entity_type, "resolved_entity_type": creature.get("entry_type")},
        )
    if not is_owned and not is_shared_source:
        return error_response(
            403,
            "creature_not_owned",
            "You do not own this custom creature.",
            details={"creature_id": canonical_creature_id, "owner_user_id": owner_user_id, "auth_user_id": auth_user_id},
        )

    try:
        x = float(body.get("x", 0) or 0)
        y = float(body.get("y", 0) or 0)
    except Exception:
        return error_response(400, "invalid_payload", "x and y must be numeric.", details={"x": body.get("x"), "y": body.get("y")})

    from server.db import save_campaign_async
    token = await spawn_creature_from_library_entry(
        session=session,
        creature_id=canonical_creature_id,
        dm_user_id=auth_user_id,
        request_source=source,
        request_entity_type=entity_type,
        x=x,
        y=y,
        map_ctx=map_ctx,
        session_user=session_user,
        grid_size_px=body.get("grid_size_px") or body.get("gridSizePx"),
    )
    if not token:
        return error_response(
            400,
            "spawn_failed",
            "Creature could not be spawned with the requested parameters.",
            details={"creature_id": canonical_creature_id, "source": source or None, "entity_type": entity_type or None},
        )
    logger.info(
        "[CreatureSpawn] success creature_id=%s session_id=%s auth_user_id=%s token_id=%s token_type=%s map_context=%s",
        canonical_creature_id, session_id, auth_user_id, token.id, token.token_type, map_ctx
    )
    await save_campaign_async(session)
    return JSONResponse({
        "ok": True,
        "token_id": token.id,
        "token": token.to_dict(),
        "creature": {
            "id": canonical_creature_id,
            "source": resolved_source,
            "entity_type": creature.get("entry_type") or creature.get("creature_type"),
        },
    })
