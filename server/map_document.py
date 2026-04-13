"""Helpers for building and hydrating versioned map documents."""
from __future__ import annotations

import copy
import time
from typing import Any

from server.editor_schema import normalize_map_settings
from server.map_migrations import MAP_DOCUMENT_VERSION, migrate_map_document


EDITOR_GRID_SIZE = 50
FT_PER_GRID = 5


def _clone(value: Any):
    return copy.deepcopy(value)


def _safe_ctx(value: Any) -> str:
    text = str(value or "world").strip()[:80]
    return text or "world"


def _map_name_for_context(session, map_context: str) -> str:
    if map_context == "world":
        return "World Map"
    poi = (getattr(session, "pois", {}) or {}).get(map_context)
    if poi and getattr(poi, "name", None):
        return str(poi.name)[:120]
    return f"Local Map {map_context}"


def _background_url_for_context(session, map_context: str) -> str | None:
    if map_context == "world":
        url = getattr(session, "map_image_url", None)
        return str(url)[:400] if url else None
    poi = (getattr(session, "pois", {}) or {}).get(map_context)
    if poi and getattr(poi, "local_map_url", None):
        return str(poi.local_map_url)[:400]
    return None


def _context_hazards(session, map_context: str) -> list:
    items = []
    for zone in list((getattr(session, "hazard_zones", {}) or {}).values()):
        if not isinstance(zone, dict):
            continue
        zone_ctx = _safe_ctx(zone.get("map_context") or "world")
        if zone_ctx != map_context:
            continue
        items.append(_clone(zone))
    return items


def _known_contexts(session) -> list[str]:
    contexts = {"world"}
    for attr in (
        "editor_layers", "editor_walls", "editor_props", "map_settings",
        "editor_paths", "editor_labels", "editor_markers", "editor_lights",
    ):
        value = getattr(session, attr, None) or {}
        if isinstance(value, dict):
            for key in value.keys():
                contexts.add(_safe_ctx(key))
    for poi in (getattr(session, "pois", {}) or {}).values():
        if getattr(poi, "local_map_url", None):
            contexts.add(_safe_ctx(getattr(poi, "id", "world")))
    for zone in (getattr(session, "hazard_zones", {}) or {}).values():
        if isinstance(zone, dict):
            contexts.add(_safe_ctx(zone.get("map_context") or "world"))
    return sorted(contexts, key=lambda item: (item != "world", item))


def build_map_document(session, map_context: str) -> dict:
    ctx = _safe_ctx(map_context)
    settings_all = dict(getattr(session, "map_settings", {}) or {})
    existing_docs = dict(getattr(session, "map_documents", {}) or {})
    existing_doc = migrate_map_document(existing_docs.get(ctx), map_context=ctx)
    existing_assets = dict(existing_doc.get("assets") or {})
    existing_meta = dict(existing_doc.get("meta") or {})
    settings = normalize_map_settings(settings_all.get(ctx) or {})
    map_type = str(settings.get("editor_mode") or "tactical").strip().lower()
    if map_type not in {"world", "tactical"}:
        map_type = "tactical"

    doc = {
        "version": MAP_DOCUMENT_VERSION,
        "map_context": ctx,
        "map_type": map_type,
        "grid": {
            "tile_size_px": EDITOR_GRID_SIZE,
            "feet_per_tile": FT_PER_GRID,
            "snap": True,
        },
        "assets": {
            "background_url": _background_url_for_context(session, ctx),
            "background_layers": list(existing_assets.get("background_layers") or []),
        },
        "settings": settings,
        "meta": {
            "schema": "casual-dnd.map-document",
            "name": str(existing_meta.get("name") or _map_name_for_context(session, ctx))[:120],
            "generated_from_legacy": True,
            "updated_at": time.time(),
        },
        "layers": {
            "terrain": {"cells": dict((getattr(session, "editor_layers", {}) or {}).get(ctx) or {})},
            "walls": list((getattr(session, "editor_walls", {}) or {}).get(ctx) or []),
            "props": list((getattr(session, "editor_props", {}) or {}).get(ctx) or []),
            "paths": list((getattr(session, "editor_paths", {}) or {}).get(ctx) or []),
            "labels": list((getattr(session, "editor_labels", {}) or {}).get(ctx) or []),
            "markers": list((getattr(session, "editor_markers", {}) or {}).get(ctx) or []),
            "lights": list((getattr(session, "editor_lights", {}) or {}).get(ctx) or []),
            "hazards": _context_hazards(session, ctx),
        },
    }
    return migrate_map_document(doc, map_context=ctx)


def build_map_documents_from_session(session) -> dict:
    return {ctx: build_map_document(session, ctx) for ctx in _known_contexts(session)}


def refresh_session_map_documents(session, map_context: str | None = None) -> dict:
    docs = dict(getattr(session, "map_documents", {}) or {})
    if map_context:
        ctx = _safe_ctx(map_context)
        docs[ctx] = build_map_document(session, ctx)
    else:
        docs = build_map_documents_from_session(session)
    session.map_documents = docs
    return docs


def normalize_map_documents(raw: Any) -> dict:
    src = raw if isinstance(raw, dict) else {}
    docs = {}
    for ctx, value in src.items():
        safe_ctx = _safe_ctx(ctx)
        docs[safe_ctx] = migrate_map_document(value, map_context=safe_ctx)
    return docs


def extract_legacy_editor_state(map_documents: Any) -> dict:
    docs = normalize_map_documents(map_documents)
    editor_layers = {}
    editor_walls = {}
    editor_props = {}
    map_settings = {}
    editor_paths = {}
    editor_labels = {}
    editor_markers = {}
    editor_lights = {}
    hazard_zones = {}

    for ctx, doc in docs.items():
        layers = doc.get("layers") if isinstance(doc.get("layers"), dict) else {}
        terrain = layers.get("terrain") if isinstance(layers.get("terrain"), dict) else {}
        editor_layers[ctx] = dict(terrain.get("cells") or {})
        editor_walls[ctx] = list(layers.get("walls") or [])
        editor_props[ctx] = list(layers.get("props") or [])
        editor_paths[ctx] = list(layers.get("paths") or [])
        editor_labels[ctx] = list(layers.get("labels") or [])
        editor_markers[ctx] = list(layers.get("markers") or [])
        editor_lights[ctx] = list(layers.get("lights") or [])
        map_settings[ctx] = normalize_map_settings(doc.get("settings") or {})
        for hazard in list(layers.get("hazards") or []):
            if not isinstance(hazard, dict):
                continue
            hz = _clone(hazard)
            hz["map_context"] = ctx
            hazard_id = str(hz.get("id") or f"{ctx}:{len(hazard_zones)+1}")[:64]
            hz["id"] = hazard_id
            hazard_zones[hazard_id] = hz

    return {
        "editor_layers": editor_layers,
        "editor_walls": editor_walls,
        "editor_props": editor_props,
        "map_settings": map_settings,
        "editor_paths": editor_paths,
        "editor_labels": editor_labels,
        "editor_markers": editor_markers,
        "editor_lights": editor_lights,
        "hazard_zones": hazard_zones,
    }


def hydrate_session_from_map_documents(session, map_documents: Any) -> dict:
    docs = normalize_map_documents(map_documents)
    legacy = extract_legacy_editor_state(docs)
    session.map_documents = docs
    session.editor_layers = legacy["editor_layers"]
    session.editor_walls = legacy["editor_walls"]
    session.editor_props = legacy["editor_props"]
    session.map_settings = legacy["map_settings"]
    session.editor_paths = legacy["editor_paths"]
    session.editor_labels = legacy["editor_labels"]
    session.editor_markers = legacy["editor_markers"]
    session.editor_lights = legacy["editor_lights"]
    existing_hazards = dict(getattr(session, "hazard_zones", {}) or {})
    existing_hazards.update(legacy["hazard_zones"])
    session.hazard_zones = existing_hazards
    return docs
