from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from server.assets.service import make_asset_id
from server.http.auth import get_request_user
from server.creatures.service import (
    create_creature_response,
    delete_creature_response,
    list_creatures_response,
    portrait_upload_response,
    resolve_library_owner,
    spawn_creature_response,
    update_creature_response,
    variant_creature_response,
)

router = APIRouter()


@router.get("/api/library/creatures")
async def api_list_creatures(
    request: Request,
    owner_id: str = "",
    type: str = "",
    cr_min: str = "",
    cr_max: str = "",
    search: str = "",
    source: str = "",
    monster_type: str = "",
    environment: str = "",
    role_tag: str = "",
    favorites_only: int = 0,
    recent_only: int = 0,
    custom_mode: str = "",
    sort: str = "",
    archived: int = 0,
    session_id: str = "",
):
    return await list_creatures_response(
        request,
        owner_id=owner_id,
        session_id=session_id or None,
        creature_type=type or None,
        cr_min=cr_min or None,
        cr_max=cr_max or None,
        search=search or None,
        source=source or None,
        monster_type=monster_type or None,
        environment=environment or None,
        role_tag=role_tag or None,
        favorites_only=bool(favorites_only),
        recent_only=bool(recent_only),
        custom_mode=custom_mode or None,
        sort=sort or None,
        archived=bool(archived),
    )


@router.post("/api/library/creatures/portrait-upload")
async def api_bestiary_portrait_upload(request: Request, file: UploadFile = File(...)):
    return await portrait_upload_response(file, make_asset_id)


@router.post("/api/library/creatures")
async def api_create_creature(request: Request):
    owner_user_id = resolve_library_owner(request)
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    auth_user = get_request_user(request) or {}
    if str(auth_user.get("role") or "").lower() != "dm":
        return JSONResponse({"error": "DM only"}, status_code=403)
    return create_creature_response(owner_user_id, data)


@router.put("/api/library/creatures/{creature_id}")
async def api_update_creature(creature_id: str, request: Request):
    owner_user_id = resolve_library_owner(request)
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    auth_user = get_request_user(request) or {}
    if str(auth_user.get("role") or "").lower() != "dm":
        return JSONResponse({"error": "DM only"}, status_code=403)
    return update_creature_response(creature_id, owner_user_id, data)


@router.post("/api/library/creatures/{creature_id}/variant")
async def api_creature_variant(creature_id: str, request: Request, owner_id: str = ""):
    try:
        body = await request.json()
    except Exception:
        body = {}
    auth_user = get_request_user(request) or {}
    auth_role = str(auth_user.get("role") or "").lower()
    explicit_owner_id = owner_id or str(body.get("owner_id", "") or "")
    # Backward-compatible contract: allow unauthenticated variant creation when
    # owner_id is explicitly supplied. Authenticated non-DM callers remain DM-only.
    if auth_user and auth_role != "dm":
        return JSONResponse({"error": "DM only"}, status_code=403)
    owner_user_id = resolve_library_owner(request, explicit_owner_id)
    return variant_creature_response(creature_id, owner_user_id, body)


@router.delete("/api/library/creatures/{creature_id}")
async def api_delete_creature(creature_id: str, request: Request):
    owner_user_id = resolve_library_owner(request)
    auth_user = get_request_user(request) or {}
    if str(auth_user.get("role") or "").lower() != "dm":
        return JSONResponse({"error": "DM only"}, status_code=403)
    return delete_creature_response(creature_id, owner_user_id)


@router.post("/api/library/creatures/{creature_id}/spawn")
async def api_spawn_creature(creature_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    return await spawn_creature_response(creature_id, request, body)
