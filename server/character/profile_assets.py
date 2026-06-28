"""Persistent character-profile asset and size guards.

PDF imports can embed portraits or token art as huge ``data:image/...;base64``
strings. Those strings are real persisted fields, not runtime caches, so the
runtime-stripper alone cannot remove them. This module relocates large inline
images into the existing ``/static/user_uploads`` asset directory and keeps the
profile document bounded without touching canonical character data such as
ability scores, inventory, spell selections, class features, HP, or conditions.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import re
import sys
from copy import deepcopy
from typing import Any

from server.asset_pipeline import sha256_hex
from server.paths import ASSETS_DIR, ensure_data_dirs

logger = logging.getLogger(__name__)

DATA_IMAGE_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.*)$", re.S)

PROFILE_SYNC_STRING_MAX_BYTES = 4096
PROFILE_SYNC_MAX_BYTES = 256 * 1024
PROFILE_THUMB_MAX_BYTES = 128 * 1024
PROFILE_THUMB_MAX_DIM = 256
DATA_PDF_RE = re.compile(r"^data:application/pdf;base64,", re.I | re.S)
_IMAGE_FIELD_NAMES = frozenset({
    "avatarUrl", "portraitUrl", "tokenImageUrl", "imageUrl", "image_url", "portrait_url", "thumb_url", "thumbnailUrl",
})


def _looks_like_data_asset(value: str) -> bool:
    return bool(DATA_IMAGE_RE.match(value) or DATA_PDF_RE.match(value) or (value.startswith("data:") and ";base64," in value[:120]))


def _thumb_filename_for_url(url: str) -> str | None:
    if not isinstance(url, str) or not url.startswith(USER_UPLOADS_URL_PREFIX + "/"):
        return None
    name = url.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0]
    return f"{stem}_thumb.jpg"


def ensure_profile_portrait_thumbnail(url: str, *, max_bytes: int = PROFILE_THUMB_MAX_BYTES) -> str:
    """Return a small static thumbnail URL for a relocated profile portrait.

    Only local ``/static/user_uploads`` images are transformed. Remote URLs and
    non-image files are returned unchanged so clients can still lazy-load them
    without embedding bytes in WebSocket frames.
    """
    thumb_name = _thumb_filename_for_url(str(url or ""))
    if not thumb_name:
        return str(url or "")
    source = USER_UPLOADS_DIR / str(url).rsplit("/", 1)[-1]
    dest = USER_UPLOADS_DIR / thumb_name
    if dest.exists() and dest.stat().st_size <= max_bytes:
        return f"{USER_UPLOADS_URL_PREFIX}/{thumb_name}"
    if not source.exists() or source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return str(url or "")
    try:
        from PIL import Image
        with Image.open(source) as img:
            img = img.convert("RGB")
            img.thumbnail((PROFILE_THUMB_MAX_DIM, PROFILE_THUMB_MAX_DIM), Image.LANCZOS)
            quality = 82
            while True:
                while quality >= 45:
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=quality, optimize=True)
                    raw = buf.getvalue()
                    if len(raw) <= max_bytes:
                        ensure_data_dirs()
                        USER_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(raw)
                        return f"{USER_UPLOADS_URL_PREFIX}/{thumb_name}"
                    quality -= 8
                width, height = img.size
                if max(width, height) <= 64:
                    break
                scale = 0.75
                img = img.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.LANCZOS)
                quality = 70
    except Exception as exc:
        logger.warning("[char_profile_assets] thumbnail generation failed url=%s error=%s", url, exc)
    return str(url or "")


def _profile_asset_metadata(url: str, *, original_bytes: int = 0, mime: str = "") -> dict[str, Any]:
    return {
        "available": bool(url),
        "asset_url": url,
        "url": url,
        "mime": mime,
        "bytes": int(original_bytes or 0),
        "lazy": True,
        "embedded": False,
    }


def sanitize_profile_for_websocket(profile: Any) -> Any:
    """Deep-copy a profile and strip inline/base64 asset blobs for WS sync.

    Character rules data is preserved; only large string blobs (inline images,
    PDFs, and oversized arbitrary strings) are replaced by lightweight lazy-load
    metadata. Portrait-like fields are normalized to ``portrait_url`` and
    ``thumb_url`` so clients can show a small image without receiving base64.
    """
    if not isinstance(profile, dict):
        return profile
    out = deepcopy(profile)
    portrait_url = ""
    thumb_url = ""
    seen: set[int] = set()

    def note_portrait(url: str) -> None:
        nonlocal portrait_url, thumb_url
        if url and not _looks_like_data_asset(url):
            portrait_url = portrait_url or url
            thumb_url = thumb_url or ensure_profile_portrait_thumbnail(url)

    def walk(node: Any, path: str = "") -> Any:
        if isinstance(node, dict):
            ident = id(node)
            if ident in seen:
                return node
            seen.add(ident)
            for key in list(node.keys()):
                child = node.get(key)
                key_s = str(key)
                if isinstance(child, str):
                    size = len(child.encode("utf-8", errors="ignore"))
                    if key_s in _IMAGE_FIELD_NAMES and child and not _looks_like_data_asset(child):
                        note_portrait(child)
                    if _looks_like_data_asset(child):
                        decoded = _decode_data_image(child)
                        url = None
                        mime = "application/pdf" if DATA_PDF_RE.match(child) else ""
                        if decoded:
                            mime = decoded[0]
                            url = _write_profile_image_asset(child, key_path=_path_join(path, key_s), profile_label=str(out.get("id") or out.get("name") or "?"))
                            if url and key_s in _IMAGE_FIELD_NAMES:
                                note_portrait(url)
                        node[key] = _profile_asset_metadata(url or "", original_bytes=size, mime=mime)
                    elif size > PROFILE_SYNC_STRING_MAX_BYTES:
                        node[key] = {"truncated": True, "bytes": size, "lazy": True, "embedded": False}
                    continue
                node[key] = walk(child, _path_join(path, key_s))
            return node
        if isinstance(node, list):
            ident = id(node)
            if ident in seen:
                return node
            seen.add(ident)
            for idx, child in enumerate(list(node)):
                node[idx] = walk(child, _path_join(path, idx))
        return node

    walk(out)
    # Canonical lightweight portrait metadata for clients.
    for source in (
        (((out.get("nativeCharacter") or {}).get("identity") or {}).get("portraitUrl") if isinstance(out.get("nativeCharacter"), dict) else ""),
        ((out.get("charSheet") or {}).get("avatarUrl") if isinstance(out.get("charSheet"), dict) else ""),
        ((out.get("charBook") or {}).get("avatarUrl") if isinstance(out.get("charBook"), dict) else ""),
        out.get("avatarUrl"), out.get("portraitUrl"), out.get("tokenImageUrl"),
    ):
        if isinstance(source, str):
            note_portrait(source)
    out["portrait_url"] = portrait_url
    out["thumb_url"] = thumb_url or portrait_url
    out["asset_sync"] = {"embedded_assets": False, "lazy_assets": True}
    sync_size = json_size(out)
    if sync_size > PROFILE_SYNC_MAX_BYTES:
        # Last-resort safety: keep common summary/canonical roots but drop large import/raw documents.
        for key in ("sourceDocument", "rawDocument", "pdf", "pdfData", "importRaw", "rawText"):
            if key in out:
                out[key] = {"omitted_from_sync": True, "lazy": True}
        profile_label = str(out.get("id") or out.get("name") or "?")
        final_size = json_size(out)
        logger.warning(
            "[char_profile_assets] large_profile_sync profile=%s bytes=%s cap=%s bytes_after_strip=%s",
            profile_label, sync_size, PROFILE_SYNC_MAX_BYTES, final_size,
        )
    return out


def sanitize_profiles_for_websocket(profiles: Any) -> Any:
    if isinstance(profiles, dict):
        return {k: sanitize_profiles_for_websocket(v) for k, v in profiles.items()}
    if isinstance(profiles, list):
        return [sanitize_profile_for_websocket(v) for v in profiles]
    return profiles
DATA_IMAGE_INLINE_THRESHOLD_BYTES = 4 * 1024
DATA_IMAGE_DIAGNOSTIC_THRESHOLD_BYTES = 4 * 1024
PROFILE_STRING_FIELD_MAX_BYTES = 64 * 1024
PROFILE_WARN_MAX_BYTES = 256 * 1024
USER_UPLOADS_DIR = ASSETS_DIR / "user_uploads"
USER_UPLOADS_URL_PREFIX = "/static/user_uploads"

_EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}


def json_size(value: Any) -> int:
    try:
        return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    except Exception:
        try:
            return len(str(value).encode("utf-8"))
        except Exception:
            return 0


def _path_join(parent: str, key: str | int) -> str:
    if isinstance(key, int):
        return f"{parent}[{key}]" if parent else f"[{key}]"
    return f"{parent}.{key}" if parent else str(key)


def _is_large_data_image(value: str, *, threshold: int = DATA_IMAGE_INLINE_THRESHOLD_BYTES) -> bool:
    if len(value.encode("utf-8", errors="ignore")) <= threshold:
        return False
    return bool(DATA_IMAGE_RE.match(value))


def _decode_data_image(value: str) -> tuple[str, bytes] | None:
    match = DATA_IMAGE_RE.match(value)
    if not match:
        return None
    mime = match.group(1).lower()
    try:
        raw = base64.b64decode(match.group(2).strip(), validate=True)
    except Exception:
        return None
    if not raw:
        return None
    return mime, raw


def _write_profile_image_asset(value: str, *, key_path: str, profile_label: str = "") -> str | None:
    decoded = _decode_data_image(value)
    if not decoded:
        return None
    mime, raw = decoded
    ext = _EXT_BY_MIME.get(mime, ".bin")
    digest = sha256_hex(raw)
    filename = f"char_profile_{digest[:24]}{ext}"
    try:
        ensure_data_dirs()
        USER_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        dest = USER_UPLOADS_DIR / filename
        if not dest.exists():
            dest.write_bytes(raw)
        url = f"{USER_UPLOADS_URL_PREFIX}/{filename}"
        logger.info(
            "[char_profile_assets] relocated data image profile=%s path=%s bytes=%s file=%s",
            profile_label or "?", key_path, len(raw), url,
        )
        return url
    except Exception as exc:
        logger.warning(
            "[char_profile_assets] failed to relocate data image profile=%s path=%s error=%s",
            profile_label or "?", key_path, exc,
        )
        return None


def relocate_large_inline_images(value: Any, *, profile_label: str = "", threshold: int = DATA_IMAGE_INLINE_THRESHOLD_BYTES) -> list[dict[str, Any]]:
    """Replace large ``data:image`` strings with static user-upload URLs.

    Mutates ``value`` in place and returns relocation metadata. Small inline data
    URLs are intentionally left unchanged for tiny icons.
    """
    relocated: list[dict[str, Any]] = []
    seen: set[int] = set()

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            ident = id(node)
            if ident in seen:
                return
            seen.add(ident)
            for key in list(node.keys()):
                child_path = _path_join(path, str(key))
                child = node.get(key)
                if isinstance(child, str) and _is_large_data_image(child, threshold=threshold):
                    url = _write_profile_image_asset(child, key_path=child_path, profile_label=profile_label)
                    if url:
                        old_len = len(child.encode("utf-8", errors="ignore"))
                        node[key] = url
                        relocated.append({"path": child_path, "bytes": old_len, "url": url})
                    continue
                walk(child, child_path)
        elif isinstance(node, list):
            ident = id(node)
            if ident in seen:
                return
            seen.add(ident)
            for idx, child in enumerate(node):
                child_path = _path_join(path, idx)
                if isinstance(child, str) and _is_large_data_image(child, threshold=threshold):
                    url = _write_profile_image_asset(child, key_path=child_path, profile_label=profile_label)
                    if url:
                        old_len = len(child.encode("utf-8", errors="ignore"))
                        node[idx] = url
                        relocated.append({"path": child_path, "bytes": old_len, "url": url})
                    continue
                walk(child, child_path)

    walk(value, "")
    return relocated


def _truncate_utf8(text: str, max_bytes: int) -> str:
    raw = text.encode("utf-8", errors="ignore")
    if len(raw) <= max_bytes:
        return text
    return raw[:max_bytes].decode("utf-8", errors="ignore")


def enforce_profile_size_caps(profile: Any, *, profile_label: str = "", string_cap: int = PROFILE_STRING_FIELD_MAX_BYTES, profile_cap: int = PROFILE_WARN_MAX_BYTES) -> list[dict[str, Any]]:
    """Truncate clearly oversized strings and warn on still-large profiles."""
    warnings: list[dict[str, Any]] = []
    seen: set[int] = set()

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            ident = id(node)
            if ident in seen:
                return
            seen.add(ident)
            for key in list(node.keys()):
                child_path = _path_join(path, str(key))
                child = node.get(key)
                if isinstance(child, str):
                    size = len(child.encode("utf-8", errors="ignore"))
                    if size > string_cap:
                        node[key] = _truncate_utf8(child, string_cap)
                        new_size = len(node[key].encode("utf-8", errors="ignore"))
                        warnings.append({"path": child_path, "old_bytes": size, "new_bytes": new_size})
                        logger.warning(
                            "[char_profile_assets] truncated oversized string profile=%s path=%s old_bytes=%s cap=%s",
                            profile_label or "?", child_path, size, string_cap,
                        )
                    continue
                walk(child, child_path)
        elif isinstance(node, list):
            ident = id(node)
            if ident in seen:
                return
            seen.add(ident)
            for idx, child in enumerate(node):
                child_path = _path_join(path, idx)
                if isinstance(child, str):
                    size = len(child.encode("utf-8", errors="ignore"))
                    if size > string_cap:
                        node[idx] = _truncate_utf8(child, string_cap)
                        new_size = len(node[idx].encode("utf-8", errors="ignore"))
                        warnings.append({"path": child_path, "old_bytes": size, "new_bytes": new_size})
                        logger.warning(
                            "[char_profile_assets] truncated oversized string profile=%s path=%s old_bytes=%s cap=%s",
                            profile_label or "?", child_path, size, string_cap,
                        )
                    continue
                walk(child, child_path)

    walk(profile, "")
    total = json_size(profile)
    if total > profile_cap:
        warnings.append({"path": "$profile", "bytes": total, "cap": profile_cap})
        logger.warning(
            "[char_profile_assets] large_profile profile=%s bytes=%s cap=%s",
            profile_label or "?", total, profile_cap,
        )
    return warnings


def sanitize_profile_persistence(profile: Any, *, profile_label: str = "") -> dict[str, Any]:
    """Relocate large inline images and apply persistence-size guardrails."""
    install_db_large_field_diagnostics()
    relocated = relocate_large_inline_images(profile, profile_label=profile_label)
    warnings = enforce_profile_size_caps(profile, profile_label=profile_label)
    return {"relocated": relocated, "warnings": warnings, "bytes": json_size(profile)}


def _top_child_sizes(value: Any, *, limit: int = 10) -> list[tuple[str, int]]:
    sizes: list[tuple[str, int]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            sizes.append((str(key), json_size(child)))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            sizes.append((f"[{idx}]", json_size(child)))
    sizes.sort(key=lambda kv: kv[1], reverse=True)
    return sizes[:limit]


def find_large_data_images(value: Any, *, threshold: int = DATA_IMAGE_DIAGNOSTIC_THRESHOLD_BYTES) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    seen: set[int] = set()

    def walk(node: Any, path: str) -> None:
        if isinstance(node, str):
            size = len(node.encode("utf-8", errors="ignore"))
            if size > threshold and node.startswith("data:"):
                found.append((path or "$", size))
            return
        if isinstance(node, dict):
            ident = id(node)
            if ident in seen:
                return
            seen.add(ident)
            for key, child in node.items():
                walk(child, _path_join(path, str(key)))
        elif isinstance(node, list):
            ident = id(node)
            if ident in seen:
                return
            seen.add(ident)
            for idx, child in enumerate(node):
                walk(child, _path_join(path, idx))

    walk(value, "")
    found.sort(key=lambda kv: kv[1], reverse=True)
    return found


def char_profiles_bloat_diagnostics_from_serialized(serialized: str) -> str:
    """Return compact diagnostics for the single largest stored profile."""
    try:
        data = json.loads(serialized)
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""
    largest_label = ""
    largest_profile: dict[str, Any] | None = None
    largest_size = 0
    for owner_key, profiles in data.items():
        entries = profiles if isinstance(profiles, list) else [profiles]
        for profile in entries:
            if not isinstance(profile, dict):
                continue
            size = json_size(profile)
            if size > largest_size:
                largest_size = size
                largest_profile = profile
                largest_label = f"{owner_key}/{profile.get('id') or profile.get('name') or '?'}"
    if not largest_profile:
        return ""
    parts = [f"largest_profile={largest_label}", f"profile_bytes={largest_size}"]
    for key in ("charSheet", "nativeRuntime"):
        top = _top_child_sizes(largest_profile.get(key), limit=10)
        if top:
            parts.append(f"{key}_subkeys[" + " ".join(f"{name}={size}" for name, size in top) + "]")
    data_urls = find_large_data_images(largest_profile, threshold=DATA_IMAGE_DIAGNOSTIC_THRESHOLD_BYTES)[:10]
    if data_urls:
        parts.append("data_urls[" + " ".join(f"{path}={size}" for path, size in data_urls) + "]")
    return " ".join(parts)


def install_db_large_field_diagnostics() -> bool:
    """Extend server.db char_profiles large-field diagnostics when db is loaded.

    This avoids rewriting the large persistence module while still making the
    existing ``large_field`` warning include largest-profile, charSheet,
    nativeRuntime, and data-URL path diagnostics before the next save warning.
    """
    db_mod = sys.modules.get("server.db")
    if db_mod is None:
        return False
    old = getattr(db_mod, "_char_profiles_size_breakdown", None)
    if not callable(old):
        return False
    # Detect the patch via a tag on the live function rather than a module-level
    # flag: reloading server.db resets _char_profiles_size_breakdown back to the
    # original (un-patched) implementation while leaving any module attribute we
    # set behind, so a flag check would wrongly skip re-installing the patch.
    if getattr(old, "_char_profile_bloat_diag_patched", False):
        return True

    def _patched_char_profiles_size_breakdown(value: str, limit: int = 8) -> str:
        base = old(value, limit=limit)
        detail = char_profiles_bloat_diagnostics_from_serialized(value)
        return " ".join(part for part in (base, detail) if part)

    _patched_char_profiles_size_breakdown._char_profile_bloat_diag_patched = True
    setattr(db_mod, "_char_profiles_size_breakdown", _patched_char_profiles_size_breakdown)
    setattr(db_mod, "_char_profile_bloat_diag_installed", True)
    return True


install_db_large_field_diagnostics()
