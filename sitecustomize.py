"""Runtime hotfixes loaded by Python's site startup.

This file intentionally keeps the patch narrow: viewer power grant messages from
DM UI surfaces can arrive with a viewer profile key rather than the exact
``viewer_user_id`` expected by ``server.handlers.viewer_powers``.  The wrapper
normalizes that target before the existing handler runs and sends explicit
status feedback so the DM/viewer are not left with a silent no-op.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
from types import ModuleType
from typing import Any

_TARGET_MODULE = "server.handlers.viewer_powers"
_PATCH_FLAG = "_viewer_power_grant_delivery_hotfix_applied"


def _clean(value: Any) -> str:
    return str(value or "").strip()[:128]


def _viewer_identifier_candidates(module: ModuleType, user: Any) -> set[str]:
    candidates: set[str] = set()
    for raw in (
        getattr(user, "id", ""),
        getattr(user, "player_key", ""),
        getattr(user, "name", ""),
    ):
        cleaned = _clean(raw)
        if cleaned:
            candidates.add(cleaned)
            candidates.add(cleaned.lower())
    try:
        viewer_key = _clean(module._viewer_key_for_user(user))
        if viewer_key:
            candidates.add(viewer_key)
            candidates.add(viewer_key.lower())
    except Exception:
        pass
    try:
        for alias in module._viewer_key_aliases(user):
            alias = _clean(alias)
            if alias:
                candidates.add(alias)
                candidates.add(alias.lower())
    except Exception:
        pass
    return candidates


def _payload_viewer_candidates(payload: dict[str, Any]) -> set[str]:
    candidates: set[str] = set()
    for key in (
        "viewer_user_id",
        "user_id",
        "viewer_id",
        "viewer_key",
        "profile_key",
        "target_viewer_id",
        "target_viewer_key",
        "viewer",
        "name",
    ):
        cleaned = _clean(payload.get(key))
        if cleaned:
            candidates.add(cleaned)
            candidates.add(cleaned.lower())
    return candidates


def _resolve_viewer_from_payload(module: ModuleType, session: Any, payload: dict[str, Any]) -> Any | None:
    candidates = _payload_viewer_candidates(payload)
    if not candidates:
        return None

    users = getattr(session, "users", {}) or {}
    direct_ids = [c for c in candidates if c in users]
    for uid in direct_ids:
        user = users.get(uid)
        if user and module._role(user) == "viewer":
            return user

    profiles = module._get_viewer_profiles(session)
    for user in users.values():
        if module._role(user) != "viewer":
            continue
        user_candidates = _viewer_identifier_candidates(module, user)
        try:
            profile_key = module._viewer_key_for_user(user)
            profile = dict(profiles.get(profile_key) or {})
            for raw in (
                profile_key,
                profile.get("viewer_key"),
                profile.get("user_id"),
                profile.get("name"),
            ):
                cleaned = _clean(raw)
                if cleaned:
                    user_candidates.add(cleaned)
                    user_candidates.add(cleaned.lower())
        except Exception:
            pass
        if candidates & user_candidates:
            return user
    return None


def _power_ids_for_viewer(module: ModuleType, session: Any, viewer: Any) -> set[str]:
    try:
        profiles = module._get_viewer_profiles(session)
        key = module._viewer_key_for_user(viewer)
        profile = dict(profiles.get(key) or {})
        return {str(pid) for pid in (profile.get("powers") or {}).keys()}
    except Exception:
        return set()


async def _send_status(module: ModuleType, session: Any, user_id: str, kind: str, message: str) -> None:
    if not user_id:
        return
    await module.manager.send_to(
        session.id,
        user_id,
        {"type": "viewer_power_status", "payload": {"kind": kind, "message": message}},
    )


def _apply_patch(module: ModuleType) -> ModuleType:
    if getattr(module, _PATCH_FLAG, False):
        return module

    original_grant = module.handle_viewer_power_grant
    original_grant_preset = module.handle_viewer_power_grant_preset

    async def handle_viewer_power_grant(payload: dict, session: Any, user: Any):
        if module._role(user) != "dm":
            return await original_grant(payload, session, user)
        normalized = dict(payload or {})
        viewer = _resolve_viewer_from_payload(module, session, normalized)
        if viewer:
            normalized["viewer_user_id"] = getattr(viewer, "id", "")
        power_id = _clean(normalized.get("power_id"))
        before = _power_ids_for_viewer(module, session, viewer) if viewer else set()
        await original_grant(normalized, session, user)
        after = _power_ids_for_viewer(module, session, viewer) if viewer else set()
        defs = module._viewer_power_defs(session)
        power_name = str((defs.get(power_id) or {}).get("name") or power_id or "viewer power")
        dm_id = _clean(getattr(user, "id", ""))
        if viewer and power_id and power_id in after:
            viewer_id = _clean(getattr(viewer, "id", ""))
            verb = "granted" if power_id not in before else "refreshed"
            await _send_status(module, session, viewer_id, "granted", f"The DM {verb} you {power_name}.")
            await _send_status(module, session, dm_id, "granted", f"{power_name} sent to {getattr(viewer, 'name', 'viewer')}.")
        else:
            await _send_status(module, session, dm_id, "grant_failed", "Viewer power was not sent. Check the viewer is connected and the power is valid.")

    async def handle_viewer_power_grant_preset(payload: dict, session: Any, user: Any):
        if module._role(user) != "dm":
            return await original_grant_preset(payload, session, user)
        normalized = dict(payload or {})
        viewer = _resolve_viewer_from_payload(module, session, normalized)
        if viewer:
            normalized["viewer_user_id"] = getattr(viewer, "id", "")
        preset_id = _clean(normalized.get("preset_id"))
        before = _power_ids_for_viewer(module, session, viewer) if viewer else set()
        await original_grant_preset(normalized, session, user)
        after = _power_ids_for_viewer(module, session, viewer) if viewer else set()
        added = sorted(after - before)
        preset_name = str((module.VIEWER_POWER_PRESETS.get(preset_id) or {}).get("name") or preset_id or "viewer power pack")
        dm_id = _clean(getattr(user, "id", ""))
        if viewer and (added or after != before):
            viewer_id = _clean(getattr(viewer, "id", ""))
            await _send_status(module, session, viewer_id, "granted", f"The DM granted you {preset_name}.")
            await _send_status(module, session, dm_id, "granted", f"{preset_name} sent to {getattr(viewer, 'name', 'viewer')}.")
        else:
            await _send_status(module, session, dm_id, "grant_failed", "Viewer power pack was not sent. Check the viewer is connected and the preset is valid.")

    module.handle_viewer_power_grant = handle_viewer_power_grant
    module.handle_viewer_power_grant_preset = handle_viewer_power_grant_preset
    setattr(module, _PATCH_FLAG, True)
    return module


class _ViewerPowerPatchLoader(importlib.abc.Loader):
    def __init__(self, wrapped: importlib.abc.Loader):
        self._wrapped = wrapped

    def create_module(self, spec):  # pragma: no cover - passthrough to default loader
        create_module = getattr(self._wrapped, "create_module", None)
        if create_module:
            return create_module(spec)
        return None

    def exec_module(self, module: ModuleType) -> None:
        self._wrapped.exec_module(module)
        _apply_patch(module)


class _ViewerPowerPatchFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path: Any = None, target: Any = None):
        if fullname != _TARGET_MODULE:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if not spec or not spec.loader or isinstance(spec.loader, _ViewerPowerPatchLoader):
            return spec
        spec.loader = _ViewerPowerPatchLoader(spec.loader)
        return spec


def patch_viewer_power_delivery_now() -> bool:
    """Patch the viewer powers module immediately if it is already importable."""
    module = sys.modules.get(_TARGET_MODULE)
    if module is None:
        module = importlib.import_module(_TARGET_MODULE)
    _apply_patch(module)
    return bool(getattr(module, _PATCH_FLAG, False))


if not any(isinstance(finder, _ViewerPowerPatchFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _ViewerPowerPatchFinder())

if _TARGET_MODULE in sys.modules:
    _apply_patch(sys.modules[_TARGET_MODULE])
