"""
server/users/assets.py — User token / power-icon upload and retrieval endpoints.
"""
import io
import secrets
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image

from server.auth.jwt_utils import verify_token
from server.auth.models import get_user_by_id, add_user_asset, list_user_assets
from server.paths import ASSETS_DIR, ensure_data_dirs

router = APIRouter()

_COOKIE_NAME = "dnd_session"
_MAX_ASSET_BYTES = 8 * 1024 * 1024  # 8 MB
_ALLOWED_MIME = {"image/png", "image/webp", "image/jpeg", "image/gif"}

USER_ASSETS_DIR = ASSETS_DIR / "user_uploads"


def _get_auth_user(request: Request):
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/api/users/me/assets/upload")
async def upload_user_asset(
    request: Request,
    file: UploadFile = File(...),
    asset_type: str = Form("token"),
):
    user = _get_auth_user(request)

    if asset_type not in ("token", "power_icon"):
        raise HTTPException(status_code=400, detail="asset_type must be 'token' or 'power_icon'")

    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {content_type}")

    data = await file.read()
    if len(data) > _MAX_ASSET_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 2 MB limit")

    # Validate image bytes with Pillow
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")

    ensure_data_dirs()
    USER_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "asset.png").suffix.lower() or ".png"
    filename = f"{user['id']}_{secrets.token_hex(8)}{ext}"
    dest = USER_ASSETS_DIR / filename
    dest.write_bytes(data)

    url = f"/static/user_uploads/{filename}"
    asset = add_user_asset(user["id"], filename, url, asset_type)
    return JSONResponse({"ok": True, **asset})


@router.get("/api/users/me/assets")
async def get_user_assets(request: Request):
    user = _get_auth_user(request)
    return JSONResponse({"ok": True, "assets": list_user_assets(user["id"])})
