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
import json
import logging
import re
from typing import Any

from server.asset_pipeline import sha256_hex
from server.paths import ASSETS_DIR, ensure_data_dirs

logger = logging.getLogger(__name__)

DATA_IMAGE_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.*)$", re.S)
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
