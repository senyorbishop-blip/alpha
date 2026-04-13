import asyncio
import io
import logging
import re
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi.responses import JSONResponse

from server.db import get_conn, save_campaign_async
from server.http.session_access import get_or_restore_session
from server.map_ingest import sync_map_imports
from server.map_library import (
    archive_map as archive_library_map,
    get_map as get_library_map,
    record_use as record_library_use,
    save_map as save_library_map,
    search_maps,
)
from server.paths import MAPS_DIR
from server.users.assets import USER_ASSETS_DIR


def normalize_map_asset_url(raw_url: str) -> str:
    url = str(raw_url or '').strip().replace('\\', '/')
    if not url:
        return ''
    if url.startswith('/static/'):
        return url
    if url.startswith('static/'):
        return '/' + url
    return url



def compute_world_map_layer(entry: dict) -> tuple[dict, list[str]]:
    width_cells = max(1, int(entry.get('width_cells') or entry.get('map_data_json', {}).get('grid_width') or 1))
    height_cells = max(1, int(entry.get('height_cells') or entry.get('map_data_json', {}).get('grid_height') or 1))
    width_px = max(1, int(entry.get('width_px') or 0) or 1)
    height_px = max(1, int(entry.get('height_px') or 0) or 1)
    tile_px = 50
    target_width = width_cells * tile_px
    target_height = height_cells * tile_px
    warnings = []
    requested_ratio = width_cells / max(height_cells, 1)
    image_ratio = width_px / max(height_px, 1)
    if abs(requested_ratio - image_ratio) > 0.05:
        warnings.append(f'Image aspect ratio ({width_px}×{height_px}) does not match requested grid footprint ({width_cells}×{height_cells}).')
    layer = {
        'id': str(entry.get('id') or secrets.token_hex(8)),
        'url': normalize_map_asset_url(entry.get('full_map_url') or entry.get('preview_url') or entry.get('thumbnail_url') or entry.get('image_url')),
        'x': target_width / 2,
        'y': target_height / 2,
        'width': target_width,
        'height': target_height,
        'locked': True,
        'name': str(entry.get('title') or 'World Map')[:160],
        'grid_type': str(entry.get('grid_type') or 'square'),
        'width_cells': width_cells,
        'height_cells': height_cells,
        'width_px': width_px,
        'height_px': height_px,
        'scale_x': target_width / max(width_px, 1),
        'scale_y': target_height / max(height_px, 1),
    }
    logger.debug("[MAP] computed layer id=%s url=%s tex=%dx%d cells=%dx%d scale=(%.4f,%.4f) pos=(%s,%s)", layer['id'], layer['url'], width_px, height_px, width_cells, height_cells, layer['scale_x'], layer['scale_y'], layer['x'], layer['y'])
    return layer, warnings



def set_session_world_map_layers(session, layers: list[dict]) -> list[dict]:
    normalized = [dict(layer) for layer in (layers or []) if layer and layer.get('url')]
    docs = dict(getattr(session, 'map_documents', {}) or {})
    world_doc = dict(docs.get('world') or {})
    world_assets = dict(world_doc.get('assets') or {})
    world_assets['background_layers'] = normalized
    if normalized:
        world_assets['background_url'] = normalized[-1]['url']
    else:
        world_assets['background_url'] = None
    world_doc['assets'] = world_assets
    docs['world'] = world_doc
    session.map_documents = docs
    session.map_image_url = normalized[-1]['url'] if normalized else None
    return normalized



def get_session_world_map_layers(session) -> list[dict]:
    docs = dict(getattr(session, 'map_documents', {}) or {})
    world_doc = dict(docs.get('world') or {})
    assets = dict(world_doc.get('assets') or {})
    layers = assets.get('background_layers') or []
    return [dict(layer) for layer in layers if isinstance(layer, dict) and layer.get('url')]


async def save_uploaded_world_map(session_id: str, file) -> tuple[str, Path]:
    maps_dir = MAPS_DIR
    maps_dir.mkdir(parents=True, exist_ok=True)
    orig_ext = (Path(file.filename).suffix.lower() if file.filename else '') or '.jpg'
    if orig_ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        orig_ext = '.jpg'
    for old_f in maps_dir.glob(f"{session_id}_map.*"):
        try:
            old_f.unlink()
        except OSError:
            pass

    raw = await file.read()
    filename_holder = {"name": f"{session_id}_map{orig_ext}"}

    def _process_map():
        dest = maps_dir / filename_holder["name"]
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(raw))
            if img.width > 4096 or img.height > 4096:
                img.thumbnail((4096, 4096), Image.LANCZOS)

            save_ext = orig_ext
            if orig_ext == '.png':
                fmt = 'PNG'
            elif orig_ext == '.webp':
                fmt = 'WEBP'
            else:
                fmt = 'JPEG'
                save_ext = '.jpg'
                img = img.convert('RGB')

            filename_holder["name"] = f"{session_id}_map{save_ext}"
            dest = maps_dir / filename_holder["name"]

            if fmt == 'PNG':
                img.save(dest, 'PNG', optimize=True)
            elif fmt == 'WEBP':
                img.save(dest, 'WEBP', lossless=True, quality=100, method=6)
            else:
                img.save(dest, 'JPEG', quality=90, subsampling=0)
        except Exception:
            dest = maps_dir / filename_holder["name"]
            with open(dest, 'wb') as fh:
                fh.write(raw)
        logger.debug("[MAP] Saved %dKB", dest.stat().st_size // 1024)
        return dest

    loop = asyncio.get_running_loop()
    dest = await loop.run_in_executor(None, _process_map)
    return f"/static/maps/{filename_holder['name']}", dest


async def save_uploaded_poi_map(session_id: str, poi_id: str, file) -> str:
    maps_dir = MAPS_DIR
    maps_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{session_id}_poi_{poi_id}.jpg"
    dest = maps_dir / filename
    raw_poi = await file.read()

    def _save_poi_map():
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(raw_poi)).convert("RGB")
            if img.width > 2048 or img.height > 2048:
                img.thumbnail((2048, 2048), Image.LANCZOS)
            img.save(dest, "JPEG", quality=85, optimize=True)
            logger.debug("[POI MAP] %dKB saved", dest.stat().st_size // 1024)
        except Exception as exc:
            logger.warning("[POI MAP] compress failed (%s), raw save", exc)
            with open(dest, 'wb') as fh:
                fh.write(raw_poi)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _save_poi_map)
    return f"/static/maps/{filename}"


async def clear_session_world_map(session) -> None:
    if session.map_image_url:
        try:
            filename = Path(session.map_image_url).name
            (MAPS_DIR / filename).unlink(missing_ok=True)
        except Exception:
            pass
    set_session_world_map_layers(session, [])
    await save_campaign_async(session)


def create_blank_local_map(cols: int, rows: int) -> str:
    safe_cols = max(8, min(120, int(cols or 30)))
    safe_rows = max(8, min(120, int(rows or 20)))
    return f"__blank__:{safe_cols}x{safe_rows}"


def map_asset_response(asset_path: str):
    target = (MAPS_DIR / asset_path).resolve()
    try:
        target.relative_to(MAPS_DIR.resolve())
    except ValueError:
        return JSONResponse({"detail": "Invalid asset path"}, status_code=400)
    if not target.exists() or not target.is_file():
        return JSONResponse({"detail": "Map asset not found"}, status_code=404)
    from fastapi.responses import FileResponse

    return FileResponse(str(target), headers={"Cache-Control": "public, max-age=86400"})


def import_maps_response():
    return JSONResponse(sync_map_imports(save_map=save_library_map, get_conn=get_conn, slugify=lambda value: value))


def search_maps_response(filters: dict):
    return JSONResponse(search_maps(filters))


def get_library_map_response(map_id: str):
    match = get_library_map(map_id)
    if not match:
        return JSONResponse(content={"detail": "Map not found"}, status_code=404)
    return JSONResponse(content=match)


def create_library_map_response(body: dict):
    return JSONResponse(save_library_map(body if isinstance(body, dict) else {}))


async def upload_library_map_response(file, title: str, description: str, map_scope: str, grid_type: str, image_style: str, scale_label: str, width_cells: int, height_cells: int, tags: str):
    content_type = (file.content_type or "").lower()
    allowed_types = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    if content_type not in allowed_types:
        return JSONResponse({"error": "Only PNG, JPG, and WebP maps can be uploaded."}, status_code=400)
    raw = await file.read()
    if not raw:
        return JSONResponse({"error": "Uploaded file was empty."}, status_code=400)
    try:
        from PIL import Image

        probe = Image.open(io.BytesIO(raw))
        probe.load()
        width_px, height_px = probe.size
    except Exception:
        return JSONResponse({"error": "Uploaded file is not a valid image."}, status_code=400)

    subdir = USER_ASSETS_DIR / "maps"
    subdir.mkdir(parents=True, exist_ok=True)
    ext = allowed_types[content_type]
    original_name = Path(file.filename or 'uploaded-map').stem
    safe_name = re.sub(r'[^a-zA-Z0-9._-]+', '-', original_name).strip('-._')[:80] or 'uploaded-map'
    map_id = secrets.token_hex(12)
    filename = f"{safe_name}-{map_id}{ext}"
    dest = subdir / filename
    dest.write_bytes(raw)
    public_url = f"/static/user_uploads/maps/{filename}".replace('\\', '/')
    logger.info("[MAP_UPLOAD] filename=%r saved=%s public_url=%s exists=%s size=%d", file.filename, dest, public_url, dest.exists(), len(raw))
    cleaned_tags = [tag.strip() for tag in str(tags or "").split(",") if tag.strip()][:16]
    normalized_grid = grid_type if grid_type in {"square", "hex", "none"} else "square"
    normalized_scope = map_scope if map_scope in {"interior", "battlemap", "location", "region"} else "interior"
    saved = save_library_map({
        "id": map_id,
        "title": str(title or file.filename or "Uploaded Map").strip()[:160] or "Uploaded Map",
        "description": str(description or "")[:4000],
        "source_type": "imported",
        "asset_source_type": "manual_import",
        "map_scope": normalized_scope,
        "grid_type": normalized_grid,
        "image_style": str(image_style or "painterly")[:80],
        "scale_label": str(scale_label or "5 ft")[:32],
        "width_cells": max(1, min(500, int(width_cells or 30))),
        "height_cells": max(1, min(500, int(height_cells or 20))),
        "width_px": width_px,
        "height_px": height_px,
        "thumbnail_url": public_url,
        "preview_url": public_url,
        "full_map_url": public_url,
        "tags": cleaned_tags,
        "map_data_json": {
            "background_url": public_url,
            "grid_type": normalized_grid,
            "grid_scale": str(scale_label or "5 ft")[:32],
            "grid_width": max(1, min(500, int(width_cells or 30))),
            "grid_height": max(1, min(500, int(height_cells or 20))),
        },
        "metadata_json": {
            "uploaded_filename": file.filename,
            "saved_disk_path": str(dest),
            "content_type": content_type,
            "availability": "ready",
            "asset_source_type": "manual_import",
            "image_url": public_url,
            "thumbnail_url": public_url,
            "grid_type": normalized_grid,
            "width_cells": max(1, min(500, int(width_cells or 30))),
            "height_cells": max(1, min(500, int(height_cells or 20))),
            "width_px": width_px,
            "height_px": height_px,
        },
    })
    return JSONResponse(saved)


async def apply_library_map_to_session_response(session_id: str, map_id: str, user_id: str):
    session = get_or_restore_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    user = session.users.get(user_id)
    if not user or user.role != "dm":
        return JSONResponse({"error": "Only DM can set map"}, status_code=403)
    item = get_library_map(map_id)
    if not item:
        return JSONResponse({"error": "Map not found"}, status_code=404)
    layer, warnings = compute_world_map_layer(item)
    if not layer.get('url'):
        return JSONResponse({"error": "Map asset URL is missing."}, status_code=400)
    asset_path = USER_ASSETS_DIR / Path(layer['url']).name if '/static/user_uploads/' in layer['url'] else None
    if asset_path is not None:
        logger.debug("[MAP] activate library map id=%s url=%s asset_exists=%s asset=%s", map_id, layer['url'], asset_path.exists(), asset_path)
    world_layers = [layer]
    set_session_world_map_layers(session, world_layers)
    await save_campaign_async(session)
    from server.connections import manager

    await manager.broadcast(session_id, {
        "type": "map_changed",
        "payload": {"map_image_url": layer['url'], "world_map_layers": world_layers}
    })
    return JSONResponse({"ok": True, "map": item, "world_map_layers": world_layers, "warnings": warnings})


def update_library_map_response(map_id: str, body: dict):
    payload = dict(body if isinstance(body, dict) else {})
    payload["id"] = map_id
    existing = get_library_map(map_id)
    if not existing:
        return JSONResponse({"detail": "Map not found"}, status_code=404)
    return JSONResponse(save_library_map({**existing, **payload}))


def delete_library_map_response(map_id: str):
    if not get_library_map(map_id):
        return JSONResponse({"detail": "Map not found"}, status_code=404)
    archive_library_map(map_id)
    return JSONResponse({"ok": True, "archived": True, "map_id": map_id})


def record_library_map_use_response(map_id: str):
    updated = record_library_use(map_id)
    if not updated:
        return JSONResponse({"detail": "Map not found"}, status_code=404)
    return JSONResponse(updated)
