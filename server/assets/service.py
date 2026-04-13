import asyncio
import io
import json
import re
import secrets
import zipfile
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse

from server import paths

ASSET_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}
ASSET_ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
ASSET_MAX_BYTES = 40 * 1024 * 1024
ASSET_MAX_DIM = 4096
ASSET_THUMB_DIM = 256
STATIC_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "client" / "static" / "assets" / "manifest.json"


def load_user_manifest() -> dict:
    try:
        with open(paths.USER_MANIFEST_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            data = {}
        if not isinstance(data.get("assets"), list):
            data["assets"] = []
        if not isinstance(data.get("packs"), list):
            data["packs"] = []
        return data
    except FileNotFoundError:
        return {"version": 1, "packs": [], "assets": []}
    except Exception:
        return {"version": 1, "packs": [], "assets": []}


def save_user_manifest(data: dict) -> None:
    paths.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = paths.USER_MANIFEST_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp.replace(paths.USER_MANIFEST_PATH)


def safe_parse_float(s: str, default: float, minimum: float, maximum: float) -> float:
    try:
        return max(minimum, min(maximum, float(s)))
    except (ValueError, TypeError):
        return default


def safe_parse_int(s: str, default: int) -> int:
    try:
        return int(s)
    except (ValueError, TypeError):
        return default


def coerce_manifest_version(value, default: float = 1) -> float:
    """Return a numeric manifest version without throwing on dotted strings.

    Static manifests may use cache-busting versions like "20260401.8".
    Keep those numeric so `/api/assets/manifest` never 500s while still
    producing a stable value for client-side asset versioning.
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if numeric > 0 else default
    raw = str(value or '').strip()
    if not raw:
        return default
    for parser in (int, float):
        try:
            numeric = float(parser(raw))
            return numeric if numeric > 0 else default
        except (ValueError, TypeError):
            pass
    parts = re.findall(r'\d+', raw)
    if not parts:
        return default
    try:
        numeric = float('.'.join([parts[0], ''.join(parts[1:])]) if len(parts) > 1 else parts[0])
        return numeric if numeric > 0 else default
    except (ValueError, TypeError):
        return default


def make_asset_id(filename: str) -> str:
    stem = Path(filename).stem
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in stem).strip("_")[:40] or "import"
    return f"user_{safe}_{secrets.token_hex(4)}"


def merged_manifest() -> dict:
    static_data: dict = {"version": 1, "packs": [], "assets": []}
    try:
        with open(STATIC_MANIFEST_PATH, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            static_data = raw
    except Exception:
        pass
    user_data = load_user_manifest()
    needs_save = False
    for asset in user_data.get("assets", []):
        if asset.get("category", "").lower() == "terrain" and "terrain_id" not in asset:
            asset["terrain_id"] = get_next_terrain_id(user_data)
            needs_save = True
    if needs_save:
        save_user_manifest(user_data)
    static_ids = {a["id"] for a in static_data.get("assets", []) if a.get("id")}
    merged_assets = list(static_data.get("assets", []))
    for ua in user_data.get("assets", []):
        if ua.get("id") and ua["id"] not in static_ids:
            merged_assets.append(ua)
    static_pack_ids = {p["id"] for p in static_data.get("packs", []) if p.get("id")}
    merged_packs = list(static_data.get("packs", []))
    for up in user_data.get("packs", []):
        if up.get("id") and up["id"] not in static_pack_ids:
            merged_packs.append(up)
    return {
        "version": max(coerce_manifest_version(static_data.get("version", 1)), coerce_manifest_version(user_data.get("version", 1))),
        "packs": merged_packs,
        "assets": merged_assets,
    }


def get_next_terrain_id(user_manifest: dict | None = None) -> int:
    if user_manifest is None:
        merged = merged_manifest()
        assets = merged.get("assets", [])
    else:
        # Keep user upload terrain-id sequencing deterministic and monotonic within
        # the user manifest stream, regardless of static manifest ordering/content.
        assets = user_manifest.get("assets", [])
    terrain_ids = [
        int(a.get("terrain_id", 0))
        for a in assets
        if a.get("terrain_id") is not None and a.get("category", "").lower() == "terrain"
    ]
    return max(terrain_ids, default=0) + 1


def save_asset_file(raw: bytes, asset_id: str, orig_ext: str) -> tuple[str, str, int, int]:
    paths.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    ext = orig_ext.lower() if orig_ext in ASSET_ALLOWED_EXTS else ".png"
    fname = f"{asset_id}{ext}"
    fpath = paths.ASSETS_DIR / fname
    img_w = 0
    img_h = 0
    if ext == ".svg":
        fpath.write_bytes(raw)
        return f"/api/assets/file/{fname}", f"/api/assets/file/{fname}", img_w, img_h
    thumb_fname = f"{asset_id}_thumb.webp"
    tpath = paths.ASSETS_DIR / thumb_fname
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        img.load()
        img_w, img_h = img.width, img.height
        if img.width > ASSET_MAX_DIM or img.height > ASSET_MAX_DIM:
            img.thumbnail((ASSET_MAX_DIM, ASSET_MAX_DIM), Image.LANCZOS)
            img_w, img_h = img.width, img.height
        img.save(fpath, quality=92)
        thumb = img.copy()
        thumb.thumbnail((ASSET_THUMB_DIM, ASSET_THUMB_DIM), Image.LANCZOS)
        thumb.save(tpath, "WEBP", quality=80, method=4)
    except Exception:
        fpath.write_bytes(raw)
        tpath = fpath
        thumb_fname = fname
    return f"/api/assets/file/{fname}", f"/api/assets/file/{thumb_fname}", img_w, img_h


def asset_manifest_response():
    return JSONResponse(merged_manifest())


def asset_file_response(filename: str):
    if re.search(r"[^A-Za-z0-9._\-]", filename):
        raise HTTPException(400, "Invalid filename")
    fpath = paths.ASSETS_DIR / filename
    if not fpath.exists() or not fpath.is_file():
        raise HTTPException(404, "Asset not found")
    return FileResponse(str(fpath), headers={"Cache-Control": "public, max-age=86400"})


async def upload_asset_response(file, category: str, subtype: str, style_pack: str, name: str, tags: str, tileable: str, scale: str, anchor: str, duration_ms: str, footprint: str):
    content_type = (file.content_type or "").lower().split(";")[0].strip()
    orig_ext = (Path(file.filename or "").suffix.lower() if file.filename else "")
    if content_type not in ASSET_ALLOWED_TYPES and orig_ext not in ASSET_ALLOWED_EXTS:
        return JSONResponse({"ok": False, "error": "Only PNG, JPEG, WEBP, and SVG files are supported."}, status_code=400)
    raw = await file.read()
    if len(raw) > ASSET_MAX_BYTES:
        return JSONResponse({"ok": False, "error": f"File too large (max {ASSET_MAX_BYTES // (1024*1024)} MB)."}, status_code=400)
    if not raw:
        return JSONResponse({"ok": False, "error": "Empty file."}, status_code=400)
    is_svg = orig_ext == ".svg" or content_type == "image/svg+xml"
    if not is_svg:
        try:
            from PIL import Image
            probe = Image.open(io.BytesIO(raw))
            probe.verify()
        except Exception:
            return JSONResponse({"ok": False, "error": "File is not a valid image."}, status_code=400)
    asset_id = make_asset_id(file.filename or "import")
    import hashlib
    file_hash = hashlib.sha256(raw).hexdigest()
    user_manifest = load_user_manifest()
    for existing in user_manifest.get("assets", []):
        if existing.get("file_hash") == file_hash:
            return JSONResponse({"ok": True, "duplicate": True, "skipped": True, "asset": existing})
    loop = asyncio.get_running_loop()
    file_url, thumb_url, img_w, img_h = await loop.run_in_executor(None, lambda: save_asset_file(raw, asset_id, orig_ext or ".png"))
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    asset_category = category.strip().lower() or "terrain"
    asset_entry = {
        "id": asset_id,
        "name": (name.strip() or Path(file.filename or "").stem or "Imported Asset")[:80],
        "category": asset_category,
        "subtype": subtype.strip() or "custom",
        "style_pack": style_pack.strip() or "custom_imports",
        "tags": tag_list,
        "file": file_url,
        "thumbnail": thumb_url,
        "license": "user_imported",
        "animated": False,
        "tileable": tileable.lower() not in ("false", "0", "no"),
        "scale": max(0.1, min(10.0, safe_parse_float(scale, 1.0, 0.1, 10.0))),
        "anchor": anchor.strip() or "center",
        "duration_ms": safe_parse_int(duration_ms, 8000),
        "footprint": max(0.5, min(4.0, safe_parse_float(footprint, 1.0, 0.5, 4.0))),
        "file_hash": file_hash,
        "img_w": img_w,
        "img_h": img_h,
    }
    if asset_category == "terrain":
        asset_entry["terrain_id"] = get_next_terrain_id(user_manifest)
    user_manifest["assets"].append(asset_entry)
    pack_ids = {p["id"] for p in user_manifest.get("packs", [])}
    if "custom_imports" not in pack_ids:
        user_manifest.setdefault("packs", []).append({"id": "custom_imports", "name": "Custom Imports", "description": "User-imported local assets."})
    save_user_manifest(user_manifest)
    return JSONResponse({"ok": True, "asset": asset_entry})


async def upload_asset_batch_response(file, category: str, subtype: str, style_pack: str, tags: str, tileable: str, scale: str, anchor: str, duration_ms: str, footprint: str):
    fname = (file.filename or "").lower()
    if not fname.endswith(".zip"):
        return JSONResponse({"ok": False, "error": "Only .zip archives are supported for batch import."}, status_code=400)
    raw_zip = await file.read()
    if len(raw_zip) > 200 * 1024 * 1024:
        return JSONResponse({"ok": False, "error": "Zip too large (max 200 MB)."}, status_code=400)
    if not raw_zip:
        return JSONResponse({"ok": False, "error": "Empty file."}, status_code=400)
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_zip))
    except zipfile.BadZipFile:
        return JSONResponse({"ok": False, "error": "Invalid zip file."}, status_code=400)
    import hashlib
    user_manifest = load_user_manifest()
    existing_hashes = {a.get("file_hash") for a in user_manifest.get("assets", []) if a.get("file_hash")}
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    def _process_batch():
        results = {"imported": [], "duplicates": [], "skipped": []}
        for zi in zf.infolist():
            if zi.is_dir():
                continue
            entry_name = zi.filename
            entry_ext = Path(entry_name).suffix.lower()
            if entry_ext not in ASSET_ALLOWED_EXTS:
                results["skipped"].append(entry_name)
                continue
            try:
                img_bytes = zf.read(zi)
            except Exception:
                results["skipped"].append(entry_name)
                continue
            if len(img_bytes) > ASSET_MAX_BYTES:
                results["skipped"].append(entry_name)
                continue
            file_hash = hashlib.sha256(img_bytes).hexdigest()
            if file_hash in existing_hashes:
                results["duplicates"].append(entry_name)
                continue
            if entry_ext != ".svg":
                try:
                    from PIL import Image
                    probe = Image.open(io.BytesIO(img_bytes))
                    probe.verify()
                except Exception:
                    results["skipped"].append(entry_name)
                    continue
            aid = make_asset_id(Path(entry_name).name)
            f_url, t_url, i_w, i_h = save_asset_file(img_bytes, aid, entry_ext)
            asset_category = category.strip().lower() or "terrain"
            asset_entry = {
                "id": aid,
                "name": Path(entry_name).stem[:80],
                "category": asset_category,
                "subtype": subtype.strip() or "custom",
                "style_pack": style_pack.strip() or "custom_imports",
                "tags": tag_list,
                "file": f_url,
                "thumbnail": t_url,
                "license": "user_imported",
                "animated": False,
                "tileable": tileable.lower() not in ("false", "0", "no"),
                "scale": max(0.1, min(10.0, safe_parse_float(scale, 1.0, 0.1, 10.0))),
                "anchor": anchor.strip() or "center",
                "duration_ms": safe_parse_int(duration_ms, 8000),
                "footprint": max(0.5, min(4.0, safe_parse_float(footprint, 1.0, 0.5, 4.0))),
                "file_hash": file_hash,
                "img_w": i_w,
                "img_h": i_h,
            }
            if asset_category == "terrain":
                temp_manifest = {"assets": user_manifest.get("assets", []) + results["imported"]}
                asset_entry["terrain_id"] = get_next_terrain_id(temp_manifest)
            existing_hashes.add(file_hash)
            results["imported"].append(asset_entry)
        return results
    loop = asyncio.get_running_loop()
    batch_result = await loop.run_in_executor(None, _process_batch)
    for entry in batch_result["imported"]:
        user_manifest["assets"].append(entry)
    pack_ids = {p["id"] for p in user_manifest.get("packs", [])}
    if "custom_imports" not in pack_ids:
        user_manifest.setdefault("packs", []).append({"id": "custom_imports", "name": "Custom Imports", "description": "User-imported local assets."})
    save_user_manifest(user_manifest)
    return JSONResponse({
        "ok": True,
        "count": len(batch_result["imported"]),
        "assets": batch_result["imported"],
        "duplicates": batch_result["duplicates"],
        "skipped": batch_result["skipped"],
    })


def update_asset_metadata_response(asset_id: str, name: str, category: str, subtype: str, style_pack: str, tags: str, tileable: str, scale: str, anchor: str, duration_ms: str, footprint: str, token_fit: str, token_zoom: str, token_offset_x: str, token_offset_y: str):
    if not asset_id:
        return JSONResponse({"ok": False, "error": "asset_id required."}, status_code=400)
    user_manifest = load_user_manifest()
    asset = next((a for a in user_manifest.get("assets", []) if a.get("id") == asset_id), None)
    if not asset:
        return JSONResponse({"ok": False, "error": "Asset not found in user library."}, status_code=404)
    if name.strip():
        asset["name"] = name.strip()[:80]
    if category.strip():
        asset["category"] = category.strip().lower()
    if subtype.strip():
        asset["subtype"] = subtype.strip()
    if style_pack.strip():
        asset["style_pack"] = style_pack.strip()
    if tags.strip():
        asset["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    asset["tileable"] = tileable.lower() not in ("false", "0", "no")
    try:
        asset["scale"] = max(0.1, min(10.0, float(scale)))
    except (ValueError, TypeError):
        pass
    asset["anchor"] = anchor.strip() or asset.get("anchor", "center")
    try:
        asset["duration_ms"] = int(duration_ms)
    except (ValueError, TypeError):
        pass
    try:
        asset["footprint"] = max(0.5, min(4.0, float(footprint)))
    except (ValueError, TypeError):
        pass
    asset["token_fit"] = token_fit.strip() or "cover"
    try:
        asset["token_zoom"] = float(token_zoom)
    except (ValueError, TypeError):
        pass
    try:
        asset["token_offset_x"] = float(token_offset_x)
        asset["token_offset_y"] = float(token_offset_y)
    except (ValueError, TypeError):
        pass
    if asset.get("category", "").lower() == "terrain" and "terrain_id" not in asset:
        asset["terrain_id"] = get_next_terrain_id(user_manifest)
    save_user_manifest(user_manifest)
    return JSONResponse({"ok": True, "asset": asset})


def delete_asset_response(asset_id: str):
    user_manifest = load_user_manifest()
    asset = next((a for a in user_manifest.get("assets", []) if a.get("id") == asset_id), None)
    if not asset:
        return JSONResponse({"ok": False, "error": "Asset not found."}, status_code=404)
    for url_key in ("file", "thumbnail"):
        url = asset.get(url_key, "")
        if url.startswith("/api/assets/file/"):
            fname = url.split("/api/assets/file/", 1)[1].split("?")[0]
            if not re.search(r"[^A-Za-z0-9._\-]", fname):
                fpath = paths.ASSETS_DIR / fname
                try:
                    if fpath.exists():
                        fpath.unlink()
                except Exception:
                    pass
    user_manifest["assets"] = [a for a in user_manifest["assets"] if a.get("id") != asset_id]
    save_user_manifest(user_manifest)
    return JSONResponse({"ok": True})
