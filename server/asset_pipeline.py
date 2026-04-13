"""
server/asset_pipeline.py
========================
Back-end asset processing utilities shared between the upload endpoints and any
future offline pipeline tooling.

Responsibilities
----------------
* Validate and normalise uploaded image data (format, dimensions, content)
* Generate consistent, capped thumbnails (WebP, 256 px square)
* Produce editor-ready metadata (dimensions, anchor, scale hints)
* Provide helper functions for building manifest entries

This module does **not** own any database or manifest state; it only processes
bytes and returns results.  All persistence is handled by the caller (upload
endpoints in main.py or the offline generator in tools/).
"""

from __future__ import annotations

import hashlib
import io
import secrets
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants — kept in sync with main.py values
# ---------------------------------------------------------------------------

ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({"image/png", "image/jpeg", "image/webp", "image/svg+xml"})
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".webp", ".svg"})

MAX_UPLOAD_BYTES: int = 40 * 1024 * 1024   # 40 MB
MAX_DIMENSION: int    = 4096               # pixel cap for full-size assets
THUMB_DIMENSION: int  = 256                # thumbnail square edge

# Clamp ranges for numeric metadata
SCALE_MIN:     float = 0.1
SCALE_MAX:     float = 10.0
FOOTPRINT_MIN: float = 0.5
FOOTPRINT_MAX: float = 4.0


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def make_asset_id(filename: str) -> str:
    """Return a collision-resistant asset id derived from *filename*."""
    stem = Path(filename).stem
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in stem).strip("_")[:40] or "import"
    return f"user_{safe}_{secrets.token_hex(4)}"


def sha256_hex(data: bytes) -> str:
    """Return the hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def validate_image_bytes(raw: bytes) -> tuple[bool, str]:
    """
    Verify that *raw* is a decodable image (PNG/JPEG/WebP).

    Returns ``(True, "")`` on success or ``(False, error_message)`` on failure.
    SVG files are considered valid without PIL verification.
    """
    if not raw:
        return False, "Empty file."
    # SVGs are XML text — skip PIL verification
    if raw.lstrip()[:4] in (b"<svg", b"<?xm"):
        return True, ""
    try:
        from PIL import Image
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
        return True, ""
    except Exception as exc:
        return False, f"File is not a valid image: {exc}"


def process_image(raw: bytes, dest_path: Path, thumb_path: Path) -> tuple[str, str, int, int]:
    """
    Save the full-size image to *dest_path* (capping at :data:`MAX_DIMENSION`)
    and a thumbnail WebP to *thumb_path*.

    Returns ``(file_url_path, thumb_url_path, width, height)`` where the URL
    paths are relative to the static root (starting with ``/api/assets/file/``).

    Falls back to a raw file copy if PIL is unavailable.
    """
    orig_ext = dest_path.suffix.lower()
    img_w = img_h = 0

    # SVGs — save as-is; no PIL needed
    if orig_ext == ".svg":
        dest_path.write_bytes(raw)
        thumb_path = dest_path  # reuse same file as thumbnail
        return (
            f"/api/assets/file/{dest_path.name}",
            f"/api/assets/file/{dest_path.name}",
            img_w,
            img_h,
        )

    try:
        from PIL import Image as _PILImage

        img = _PILImage.open(io.BytesIO(raw))
        img.load()
        img_w, img_h = img.width, img.height

        # Downscale if needed
        if img_w > MAX_DIMENSION or img_h > MAX_DIMENSION:
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), _PILImage.LANCZOS)
            img_w, img_h = img.width, img.height

        img.save(dest_path, quality=92)

        # Thumbnail
        thumb = img.copy()
        thumb.thumbnail((THUMB_DIMENSION, THUMB_DIMENSION), _PILImage.LANCZOS)
        thumb.save(thumb_path, "WEBP", quality=80, method=4)
    except ImportError:
        # PIL not installed – raw copy
        dest_path.write_bytes(raw)
        thumb_path = dest_path
    except Exception:
        dest_path.write_bytes(raw)
        thumb_path = dest_path

    return (
        f"/api/assets/file/{dest_path.name}",
        f"/api/assets/file/{thumb_path.name}",
        img_w,
        img_h,
    )


def build_asset_entry(
    *,
    asset_id: str,
    name: str,
    category: str,
    subtype: str,
    style_pack: str,
    tags: list[str],
    file_url: str,
    thumb_url: str,
    tileable: bool,
    scale: float,
    anchor: str,
    duration_ms: int,
    footprint: float,
    file_hash: str,
    img_w: int,
    img_h: int,
    terrain_id: Optional[int] = None,
    animated: bool = False,
) -> dict:
    """Return a fully-populated asset manifest entry dict."""
    entry: dict = {
        "id": asset_id,
        "name": name[:80],
        "category": category,
        "subtype": subtype,
        "style_pack": style_pack,
        "tags": tags,
        "file": file_url,
        "thumbnail": thumb_url,
        "license": "user_imported",
        "animated": animated,
        "tileable": tileable,
        "scale": _clamp(scale, SCALE_MIN, SCALE_MAX),
        "anchor": anchor or "center",
        "duration_ms": duration_ms,
        "footprint": _clamp(footprint, FOOTPRINT_MIN, FOOTPRINT_MAX),
        "file_hash": file_hash,
        "img_w": img_w,
        "img_h": img_h,
    }
    if terrain_id is not None:
        entry["terrain_id"] = terrain_id
    return entry


def derive_grid_size(img_w: int, img_h: int, cell_px: int = 100) -> tuple[int, int]:
    """
    Estimate the grid footprint (columns × rows) for an asset given its pixel
    dimensions and the map cell size in pixels.

    The result uses the same simple integer rounding the client-side JS uses
    when inferring a ``WxH`` size tag.
    """
    cols = max(1, round(img_w / cell_px))
    rows = max(1, round(img_h / cell_px))
    return cols, rows


def categories_for_filename(filename: str) -> tuple[str, str]:
    """
    Heuristically guess the asset category and subtype from a file name.

    Returns ``(category, subtype)``.  Defaults to ``("props", "custom")``.

    Examples::

        >>> categories_for_filename("barrel_oak.png")
        ('props', 'container')
        >>> categories_for_filename("stone_floor_tile.jpg")
        ('terrain', 'hardscape')
    """
    stem = Path(filename).stem.lower().replace("-", "_")
    tokens = stem.split("_")

    terrain_words  = {"floor", "ground", "stone", "grass", "dirt", "road", "path",
                      "water", "lava", "sand", "snow", "ice", "swamp", "marsh",
                      "cave", "tile", "texture", "terrain", "hills", "forest"}
    prop_furniture = {"table", "chair", "bookshelf", "shelf", "desk", "throne", "bench"}
    prop_container = {"barrel", "crate", "chest", "sack", "bag", "lockbox", "box",
                      "pot", "urn", "vase"}
    prop_lighting  = {"torch", "brazier", "lantern", "campfire", "fire", "candle"}
    prop_hazard    = {"trap", "spike", "pressure", "poison", "vent", "hazard"}
    prop_clutter   = {"bones", "skull", "rubble", "debris", "rock", "stone", "pile"}
    prop_camp      = {"tent", "bedroll", "campfire", "camp", "cooking", "bedroll"}
    marker_words   = {"city", "town", "village", "castle", "ruin", "forest", "mountain",
                      "harbor", "tavern", "shop", "blacksmith", "camp", "landmark",
                      "shrine", "marker", "poi", "settlement"}

    word_set = set(tokens)

    if word_set & terrain_words:
        return "terrain", "custom"
    if word_set & prop_furniture:
        return "props", "furniture"
    if word_set & prop_container:
        return "props", "container"
    if word_set & prop_lighting:
        return "props", "lighting"
    if word_set & prop_hazard:
        return "props", "hazard"
    if word_set & prop_clutter:
        return "props", "clutter"
    if word_set & prop_camp:
        return "props", "camp"
    if word_set & marker_words:
        return "markers", "custom"
    return "props", "custom"


def tags_for_filename(filename: str) -> list[str]:
    """
    Extract candidate tags from a filename by splitting on underscores / hyphens.

    Short common words (``a``, ``the``, ``of`` …) and numbers are excluded.
    """
    _STOP = frozenset({"a", "an", "the", "of", "in", "at", "to", "and", "or", "for",
                       "with", "new", "old", "big", "small", "v1", "v2", "v3", "final",
                       "export", "clean", "web", "icon", "img", "image", "file"})
    stem = Path(filename).stem.lower().replace("-", "_")
    parts = [p.strip("0123456789") for p in stem.split("_")]
    return [p for p in parts if len(p) > 1 and p not in _STOP]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return lo
