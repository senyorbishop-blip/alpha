"""Versioned map document migrations for the editor rebuild."""
from __future__ import annotations

import copy
import time
from typing import Any

from server.editor_schema import (
    normalize_grid,
    normalize_hazard,
    normalize_label,
    normalize_light,
    normalize_map_asset_bundle,
    normalize_map_settings,
    normalize_marker,
    normalize_path,
    normalize_prop,
    normalize_terrain_cells,
    normalize_wall,
)

MAP_DOCUMENT_VERSION = 1


_LAYER_DEFAULTS = {
    "terrain": {"cells": {}},
    "walls": [],
    "props": [],
    "paths": [],
    "labels": [],
    "markers": [],
    "lights": [],
    "hazards": [],
}



def _clone(value: Any):
    return copy.deepcopy(value)



def _default_layers() -> dict:
    return {
        "terrain": {"cells": {}},
        "walls": [],
        "props": [],
        "paths": [],
        "labels": [],
        "markers": [],
        "lights": [],
        "hazards": [],
    }



def _safe_ctx(value: Any, fallback: str) -> str:
    text = str(value or fallback or "world").strip()[:80]
    return text or "world"



def _normalize_layer_items(values: Any, normalizer, *, map_context: str) -> list:
    items = []
    for index, value in enumerate(values if isinstance(values, list) else []):
        item = normalizer(value, index=index, map_context=map_context)
        if item is not None:
            items.append(item)
    return items



def migrate_map_document(raw: Any, *, map_context: str = "world") -> dict:
    """Normalize any stored map document into the current schema version.

    This migration is intentionally conservative in Phase 2: it preserves as much
    existing data as possible while ensuring a predictable editor document shape.
    """
    src = raw if isinstance(raw, dict) else {}
    resolved_context = _safe_ctx(src.get("map_context"), map_context)
    layers_src = src.get("layers") if isinstance(src.get("layers"), dict) else {}
    meta_src = src.get("meta") if isinstance(src.get("meta"), dict) else {}
    doc = {
        "version": MAP_DOCUMENT_VERSION,
        "map_context": resolved_context,
        "map_type": str(src.get("map_type") or src.get("type") or "tactical").strip().lower(),
        "grid": normalize_grid(src.get("grid")),
        "assets": normalize_map_asset_bundle(src.get("assets")),
        "settings": normalize_map_settings(src.get("settings") if isinstance(src.get("settings"), dict) else {}),
        "meta": {
            "schema": str(meta_src.get("schema") or "casual-dnd.map-document")[:80],
            "name": str(meta_src.get("name") or ("World Map" if resolved_context == "world" else f"Local Map {resolved_context}"))[:120],
            "generated_from_legacy": bool(meta_src.get("generated_from_legacy", False)),
            "migrated_to": MAP_DOCUMENT_VERSION,
            "updated_at": float(meta_src.get("updated_at") or time.time()),
        },
        "layers": _default_layers(),
    }
    if doc["map_type"] not in {"world", "tactical"}:
        doc["map_type"] = "tactical"

    terrain_src = layers_src.get("terrain") if isinstance(layers_src.get("terrain"), dict) else {}
    doc["layers"]["terrain"] = {"cells": normalize_terrain_cells(terrain_src.get("cells"))}
    doc["layers"]["walls"] = _normalize_layer_items(layers_src.get("walls"), normalize_wall, map_context=resolved_context)
    doc["layers"]["props"] = _normalize_layer_items(layers_src.get("props"), normalize_prop, map_context=resolved_context)
    doc["layers"]["paths"] = _normalize_layer_items(layers_src.get("paths"), normalize_path, map_context=resolved_context)
    doc["layers"]["labels"] = _normalize_layer_items(layers_src.get("labels"), normalize_label, map_context=resolved_context)
    doc["layers"]["markers"] = _normalize_layer_items(layers_src.get("markers"), normalize_marker, map_context=resolved_context)
    doc["layers"]["lights"] = _normalize_layer_items(layers_src.get("lights"), normalize_light, map_context=resolved_context)
    doc["layers"]["hazards"] = _normalize_layer_items(layers_src.get("hazards"), normalize_hazard, map_context=resolved_context)
    return doc
