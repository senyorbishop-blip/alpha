from fastapi import APIRouter, File, Form, UploadFile

from server.assets.service import (
    asset_file_response,
    asset_manifest_response,
    delete_asset_response,
    update_asset_metadata_response,
    upload_asset_batch_response,
    upload_asset_response,
)

router = APIRouter()


@router.get("/api/assets/manifest")
async def get_asset_manifest():
    return asset_manifest_response()


@router.get("/api/assets/file/{filename}")
async def serve_asset_file(filename: str):
    return asset_file_response(filename)


@router.post("/api/assets/upload")
async def upload_asset(
    file: UploadFile = File(...),
    category: str = Form("terrain"),
    subtype: str = Form("custom"),
    style_pack: str = Form("custom_imports"),
    name: str = Form(""),
    tags: str = Form(""),
    tileable: str = Form("true"),
    scale: str = Form("1"),
    anchor: str = Form("center"),
    duration_ms: str = Form("8000"),
    footprint: str = Form("1"),
):
    return await upload_asset_response(file, category, subtype, style_pack, name, tags, tileable, scale, anchor, duration_ms, footprint)


@router.post("/api/assets/upload-batch")
async def upload_asset_batch(
    file: UploadFile = File(...),
    category: str = Form("terrain"),
    subtype: str = Form("custom"),
    style_pack: str = Form("custom_imports"),
    tags: str = Form(""),
    tileable: str = Form("true"),
    scale: str = Form("1"),
    anchor: str = Form("center"),
    duration_ms: str = Form("8000"),
    footprint: str = Form("1"),
):
    return await upload_asset_batch_response(file, category, subtype, style_pack, tags, tileable, scale, anchor, duration_ms, footprint)


@router.post("/api/assets/update")
async def update_asset_metadata(
    asset_id: str = Form(""),
    name: str = Form(""),
    category: str = Form(""),
    subtype: str = Form(""),
    style_pack: str = Form(""),
    tags: str = Form(""),
    tileable: str = Form("true"),
    scale: str = Form("1"),
    anchor: str = Form("center"),
    duration_ms: str = Form("8000"),
    footprint: str = Form("1"),
    token_fit: str = Form("cover"),
    token_zoom: str = Form("1"),
    token_offset_x: str = Form("0"),
    token_offset_y: str = Form("0"),
):
    return update_asset_metadata_response(asset_id, name, category, subtype, style_pack, tags, tileable, scale, anchor, duration_ms, footprint, token_fit, token_zoom, token_offset_x, token_offset_y)


@router.delete("/api/assets/{asset_id}")
async def delete_asset(asset_id: str):
    return delete_asset_response(asset_id)
