import logging
import secrets
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from server.connections import manager
from server.db import save_campaign_async
from server.http.session_access import get_or_restore_session
from server.handlers.common import _refresh_map_documents
from server.maps.service import (
    apply_library_map_to_session_response,
    clear_session_world_map,
    create_blank_local_map,
    create_library_map_response,
    delete_library_map_response,
    get_library_map_response,
    get_session_world_map_layers,
    import_maps_response,
    map_asset_response,
    record_library_map_use_response,
    save_uploaded_poi_map,
    save_uploaded_world_map,
    search_maps_response,
    set_session_world_map_layers,
    update_library_map_response,
    upload_library_map_response,
)

router = APIRouter()


def _parse_bool_query(value) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"", "0", "false", "no", "off"}:
        return False
    return False


@router.post("/api/session/{session_id}/map")
async def upload_map(session_id: str, user_id: str, file: UploadFile = File(...), world_x: float = Form(0), world_y: float = Form(0)):
    session = get_or_restore_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    user = session.users.get(user_id)
    if not user or user.role != "dm":
        return JSONResponse({"error": "Only DM can set map"}, status_code=403)
    if not (file.content_type or "").startswith("image/"):
        return JSONResponse({"error": "File must be an image"}, status_code=400)

    url, dest = await save_uploaded_world_map(session_id, file)
    layer = {
        "id": f"upload-{session_id}-{secrets.token_hex(4)}",
        "url": url,
        "x": float(world_x or 0),
        "y": float(world_y or 0),
        "width": 0,
        "height": 0,
        "locked": True,
        "name": Path(file.filename or 'Uploaded Map').stem[:160] or 'Uploaded Map',
    }
    world_layers = get_session_world_map_layers(session)
    world_layers.append(layer)
    set_session_world_map_layers(session, world_layers)
    logger.info("[MAP] uploaded world map filename=%r disk=%s public_url=%s exists=%s pos=(%s,%s)", file.filename, dest, url, dest.exists(), world_x, world_y)
    await save_campaign_async(session)
    await manager.broadcast(session_id, {
        "type": "map_changed",
        "payload": {"map_image_url": url, "world_map_layers": world_layers}
    })
    return JSONResponse({"ok": True, "url": url, "world_map_layers": world_layers})


@router.delete("/api/session/{session_id}/map")
async def clear_map(session_id: str, request: Request):
    body = await request.json()
    session = get_or_restore_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    user = session.users.get(body.get("user_id", ""))
    if not user or user.role != "dm":
        return JSONResponse({"error": "Only DM can clear map"}, status_code=403)
    await clear_session_world_map(session)
    await manager.broadcast(session_id, {
        "type": "map_changed",
        "payload": {"map_image_url": None, "world_map_layers": []}
    })
    return JSONResponse({"ok": True})


@router.post("/api/session/{session_id}/poi/{poi_id}/map")
async def upload_poi_map(session_id: str, poi_id: str, user_id: str, file: UploadFile = File(...)):
    session = get_or_restore_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    user = session.users.get(user_id)
    if not user or user.role != "dm":
        return JSONResponse({"error": "Only DM can upload POI maps"}, status_code=403)
    if not (file.content_type or "").startswith("image/"):
        return JSONResponse({"error": "File must be an image"}, status_code=400)
    url = await save_uploaded_poi_map(session_id, poi_id, file)
    if poi_id in session.pois:
        session.pois[poi_id].local_map_url = url
        _refresh_map_documents(session, poi_id)
        logger.info("[PoiMapUpload] session_id=%s poi_id=%s assigned_url=%r", session_id, poi_id, url)
        await save_campaign_async(session)
        poi = session.pois[poi_id]
        await manager.broadcast(session_id, {
            "type": "poi_updated",
            "payload": {"poi": poi.to_dict(include_dm_notes=False), "poi_dm": poi.to_dict(include_dm_notes=True)}
        })
    return JSONResponse({"ok": True, "url": url})


@router.post("/api/session/{session_id}/poi/{poi_id}/blank_map")
async def create_blank_poi_map(session_id: str, poi_id: str, request: Request, user_id: str):
    session = get_or_restore_session(session_id)
    if not session:
        return JSONResponse({"ok": False, "error": "Session not found"}, status_code=404)
    user = session.users.get(user_id)
    if not user or user.role != "dm":
        return JSONResponse({"ok": False, "error": "Only DM can create local maps"}, status_code=403)
    poi = session.pois.get(poi_id)
    if not poi:
        return JSONResponse({"ok": False, "error": "POI not found"}, status_code=404)
    try:
        body = await request.json()
    except Exception:
        body = {}
    cols = max(8, min(120, int(body.get("cols", 30) or 30)))
    rows = max(8, min(120, int(body.get("rows", 20) or 20)))
    poi.local_map_url = create_blank_local_map(cols, rows)
    _refresh_map_documents(session, poi_id)
    logger.info("[PoiBlankMap] session_id=%s poi_id=%s assigned_url=%r cols=%d rows=%d", session_id, poi_id, poi.local_map_url, cols, rows)
    await save_campaign_async(session)
    await manager.broadcast(session.id, {
        "type": "poi_updated",
        "payload": {"poi": poi.to_dict(include_dm_notes=False), "poi_dm": poi.to_dict(include_dm_notes=True)}
    })
    return JSONResponse({"ok": True, "url": poi.local_map_url, "cols": cols, "rows": rows})


@router.get("/api/maps/assets/{asset_path:path}")
async def api_map_asset(asset_path: str):
    return map_asset_response(asset_path)


@router.post("/api/maps/library/import")
async def api_maps_import():
    return import_maps_response()


@router.get("/api/maps/library")
async def api_maps_library(
    q: str = "",
    source_type: str = "",
    asset_source_type: str = "",
    content_origin_category: str = "",
    map_scope: str = "",
    terrain: str = "",
    build_type: str = "",
    interior_type: str = "",
    image_style: str = "",
    grid_type: str = "",
    scale_label: str = "",
    source_creator: str = "",
    license_label: str = "",
    pack_name: str = "",
    width_cells: int = 0,
    height_cells: int = 0,
    tags: str = "",
    favorites_only: str = "",
    premium_only: str = "",
    open_content_only: str = "",
    include_stub: str = "",
    include_collections: str = "",
    page: int = 1,
    page_size: int = 24,
    sort: str = "best_match",
):
    return search_maps_response({
        "q": q, "source_type": source_type, "asset_source_type": asset_source_type, "content_origin_category": content_origin_category, "map_scope": map_scope, "terrain": terrain,
        "build_type": build_type, "interior_type": interior_type, "image_style": image_style,
        "grid_type": grid_type, "scale_label": scale_label, "source_creator": source_creator,
        "license_label": license_label, "pack_name": pack_name, "width_cells": width_cells,
        "height_cells": height_cells, "tags": tags, "favorites_only": _parse_bool_query(favorites_only),
        "premium_only": _parse_bool_query(premium_only), "open_content_only": _parse_bool_query(open_content_only),
        "include_stub": _parse_bool_query(include_stub), "include_collections": _parse_bool_query(include_collections),
        "page": page, "page_size": page_size, "sort": sort,
    })


@router.post("/api/maps/search")
async def api_maps_search(request: Request):
    body = await request.json()
    return search_maps_response(body if isinstance(body, dict) else {})


@router.get("/api/maps/library/{map_id}")
async def api_maps_get(map_id: str):
    return get_library_map_response(map_id)


@router.post("/api/maps/library")
async def api_maps_create(request: Request):
    return create_library_map_response(await request.json())


@router.post("/api/maps/library/upload")
async def api_maps_upload(
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    map_scope: str = Form("interior"),
    grid_type: str = Form("square"),
    image_style: str = Form("painterly"),
    scale_label: str = Form("5 ft"),
    width_cells: int = Form(30),
    height_cells: int = Form(20),
    tags: str = Form(""),
):
    return await upload_library_map_response(file, title, description, map_scope, grid_type, image_style, scale_label, width_cells, height_cells, tags)


@router.post("/api/session/{session_id}/map/library/{map_id}")
async def api_apply_library_map_to_session(session_id: str, map_id: str, user_id: str):
    return await apply_library_map_to_session_response(session_id, map_id, user_id)


@router.put("/api/maps/library/{map_id}")
async def api_maps_update(map_id: str, request: Request):
    return update_library_map_response(map_id, await request.json())


@router.delete("/api/maps/library/{map_id}")
async def api_maps_delete(map_id: str):
    return delete_library_map_response(map_id)


@router.post("/api/maps/library/{map_id}/use")
async def api_maps_use(map_id: str):
    return record_library_map_use_response(map_id)
