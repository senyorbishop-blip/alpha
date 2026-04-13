from __future__ import annotations

import json
import logging
import re
import secrets
import sqlite3
import time
from typing import Any

from server.db import get_conn
from server.map_ingest import sync_map_imports
from server.paths import DATA_DIR

MAP_LIBRARY_DIR = DATA_DIR / 'maps'
MAP_LIBRARY_META_DIR = MAP_LIBRARY_DIR / 'library_meta'

SOURCE_TYPES = {'builtin', 'built_in', 'generated', 'imported', 'uploaded', 'duplicated', 'edited'}
READ_ONLY_SOURCE_TYPES = {'builtin', 'built_in'}
DEFAULT_TRANSFORM = {
    'offset_x': 0,
    'offset_y': 0,
    'origin_x': 0.5,
    'origin_y': 0.5,
    'snap_to_grid': True,
    'rotation': 0,
}

logger = logging.getLogger(__name__)

_MAP_LIBRARY_DB_READY = False
_MAP_LIBRARY_DB_INITIALIZING = False


def _content_origin_category(*, source_type: str, asset_source_type: str) -> str:
    normalized_source = str(source_type or '').strip().lower()
    normalized_asset_source = str(asset_source_type or '').strip().lower()
    if normalized_source in READ_ONLY_SOURCE_TYPES and normalized_asset_source == 'open':
        return 'bundled'
    if normalized_source in {'uploaded', 'edited', 'duplicated'}:
        return 'user_custom'
    if normalized_source == 'imported' and normalized_asset_source in {'manual_import', 'licensed'}:
        return 'licensed_attributed'
    if normalized_source == 'imported' or normalized_asset_source in {'manual_import', 'licensed'}:
        return 'imported'
    if normalized_source == 'generated':
        return 'generated'
    return 'custom'


def _content_origin_label(category: str) -> str:
    labels = {
        'bundled': 'Bundled',
        'imported': 'Imported',
        'user_custom': 'User Custom',
        'licensed_attributed': 'Licensed / Attributed',
        'generated': 'Generated',
        'custom': 'Custom',
    }
    return labels.get(str(category or '').strip().lower(), 'Custom')


def init_map_library_db() -> None:
    global _MAP_LIBRARY_DB_READY, _MAP_LIBRARY_DB_INITIALIZING

    if _MAP_LIBRARY_DB_READY:
        return
    if _MAP_LIBRARY_DB_INITIALIZING:
        logger.debug('Map library DB init re-entry skipped while initialization is already in progress.')
        return

    _MAP_LIBRARY_DB_INITIALIZING = True
    logger.info('Map library DB initialization started.')
    try:
        MAP_LIBRARY_META_DIR.mkdir(parents=True, exist_ok=True)
        with get_conn() as conn:
            conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS map_library (
                id TEXT PRIMARY KEY,
                owner_user_id TEXT,
                parent_map_id TEXT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'generated',
                map_scope TEXT NOT NULL DEFAULT 'interior',
                terrain TEXT NOT NULL DEFAULT '',
                build_type TEXT NOT NULL DEFAULT '',
                interior_type TEXT NOT NULL DEFAULT '',
                output_mode TEXT NOT NULL DEFAULT '',
                image_style TEXT NOT NULL DEFAULT '',
                grid_type TEXT NOT NULL DEFAULT 'square',
                scale_label TEXT NOT NULL DEFAULT '5 ft',
                width_cells INTEGER,
                height_cells INTEGER,
                width_px INTEGER,
                height_px INTEGER,
                thumbnail_url TEXT,
                full_map_url TEXT,
                preview_url TEXT,
                generation_prompt_text TEXT NOT NULL DEFAULT '',
                generation_payload_json TEXT NOT NULL DEFAULT '{}',
                map_data_json TEXT NOT NULL DEFAULT '{}',
                tags_json TEXT NOT NULL DEFAULT '[]',
                theme_tags_json TEXT NOT NULL DEFAULT '[]',
                atmosphere_tags_json TEXT NOT NULL DEFAULT '[]',
                normalized_spec_json TEXT NOT NULL DEFAULT '{}',
                is_favorite INTEGER NOT NULL DEFAULT 0,
                is_pinned INTEGER NOT NULL DEFAULT 0,
                is_public INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_used_at REAL,
                use_count INTEGER NOT NULL DEFAULT 0,
                rating REAL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
            '''
        )
            conn.commit()
        sync_map_imports(save_map=_save_map_no_init, get_conn=get_conn, slugify=slugify)
        _MAP_LIBRARY_DB_READY = True
        logger.info('Map library DB initialization completed.')
    except Exception:
        logger.exception('Map library DB initialization failed.')
        raise
    finally:
        _MAP_LIBRARY_DB_INITIALIZING = False


def slugify(value: str) -> str:
    cleaned = re.sub(r'[^a-z0-9]+', '-', (value or '').lower()).strip('-')
    return cleaned or f'map-{secrets.token_hex(3)}'


def _json_loads(value: str | None, default: Any):
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def _normalize_source_type(value: Any) -> str:
    source = str(value or 'generated').strip().lower()
    if source == 'builtin':
        return 'built_in'
    if source not in SOURCE_TYPES:
        return 'generated'
    return source


def _normalize_url(raw_url: Any) -> str:
    url = str(raw_url or '').strip().replace('\\', '/')
    if not url:
        return ''
    if url.startswith('/static/'):
        return url
    if url.startswith('static/'):
        return '/' + url
    return url


def _normalize_tags(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [part.strip() for part in value.split(',') if part.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = [str(part).strip() for part in value if str(part).strip()]
    else:
        items = []
    deduped: list[str] = []
    seen: set[str] = set()
    for tag in items[:24]:
        lowered = tag.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(tag[:48])
    return deduped


def _normalize_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {'1', 'true', 'yes', 'on'}:
        return True
    if text in {'0', 'false', 'no', 'off'}:
        return False
    return default


def _coerce_int(value: Any, default: int | None = None, minimum: int | None = None, maximum: int | None = None) -> int | None:
    try:
        result = int(value)
    except Exception:
        return default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _coerce_float(value: Any, default: float | None = None, minimum: float | None = None, maximum: float | None = None) -> float | None:
    try:
        result = float(value)
    except Exception:
        return default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _normalise_transform(value: Any) -> dict[str, Any]:
    data = dict(value or {})
    transform = dict(DEFAULT_TRANSFORM)
    transform['offset_x'] = _coerce_float(data.get('offset_x'), 0.0) or 0.0
    transform['offset_y'] = _coerce_float(data.get('offset_y'), 0.0) or 0.0
    transform['origin_x'] = _coerce_float(data.get('origin_x'), 0.5, 0.0, 1.0) or 0.5
    transform['origin_y'] = _coerce_float(data.get('origin_y'), 0.5, 0.0, 1.0) or 0.5
    transform['rotation'] = _coerce_float(data.get('rotation'), 0.0, -360.0, 360.0) or 0.0
    transform['snap_to_grid'] = bool(data.get('snap_to_grid', True))
    return transform


def _row_to_map(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    for key in ('tags_json', 'theme_tags_json', 'atmosphere_tags_json', 'generation_payload_json', 'map_data_json', 'normalized_spec_json', 'metadata_json'):
        item[key] = _json_loads(item.get(key), [] if key.endswith('_json') and 'tags' in key else {})
    item['tags'] = _normalize_tags(item.pop('tags_json', []))
    item['theme_tags'] = _normalize_tags(item.pop('theme_tags_json', []))
    item['atmosphere_tags'] = _normalize_tags(item.pop('atmosphere_tags_json', []))
    item['generation_payload_json'] = item.get('generation_payload_json', {})
    item['map_data_json'] = item.get('map_data_json', {})
    item['normalized_spec_json'] = item.get('normalized_spec_json', {})
    item['metadata_json'] = item.get('metadata_json', {})
    item['is_favorite'] = bool(item.get('is_favorite'))
    item['is_pinned'] = bool(item.get('is_pinned'))
    item['is_public'] = bool(item.get('is_public'))
    item['archived'] = bool(item.get('archived'))
    item['source_type'] = _normalize_source_type(item.get('source_type'))
    image_url = _normalize_url(item.get('full_map_url') or item.get('preview_url') or item.get('thumbnail_url') or item.get('metadata_json', {}).get('image_url'))
    thumb_url = _normalize_url(item.get('thumbnail_url') or image_url)
    preview_url = _normalize_url(item.get('preview_url') or image_url)
    transform = _normalise_transform(item.get('map_data_json', {}).get('transform') or item.get('metadata_json', {}).get('transform') or {})
    scale = _coerce_float(item.get('map_data_json', {}).get('scale') or item.get('metadata_json', {}).get('scale'), 1.0, 0.05, 20.0) or 1.0
    item['image_url'] = image_url
    item['full_map_url'] = image_url
    item['thumbnail_url'] = thumb_url
    item['preview_url'] = preview_url
    item['thumbnail_override_url'] = _normalize_url(item.get('metadata_json', {}).get('thumbnail_override_url'))
    item['scale'] = scale
    asset_source_type = str(item.get('metadata_json', {}).get('asset_source_type') or item.get('metadata_json', {}).get('source_type') or '').strip().lower()
    availability = str(item.get('metadata_json', {}).get('availability') or 'ready').strip().lower() or 'ready'
    source_creator = str(item.get('metadata_json', {}).get('source_creator') or '').strip()
    license_label = str(item.get('metadata_json', {}).get('license_label') or '').strip()
    attribution_text = str(item.get('metadata_json', {}).get('attribution_text') or '').strip()
    pack_name = str(item.get('metadata_json', {}).get('pack_name') or '').strip()
    is_stub = _normalize_bool(item.get('metadata_json', {}).get('stub'), False)
    source_label = 'Built-in' if item['source_type'] in READ_ONLY_SOURCE_TYPES else ('Custom' if item['source_type'] in {'uploaded', 'duplicated', 'edited', 'imported'} else item['source_type'].replace('_', ' ').title())
    if item['source_type'] == 'imported' and asset_source_type == 'manual_import':
        source_label = 'Imported'
    elif item['source_type'] in READ_ONLY_SOURCE_TYPES and asset_source_type == 'open':
        source_label = 'Built-in'
    item['source_label'] = source_label
    origin_category = _content_origin_category(source_type=item['source_type'], asset_source_type=asset_source_type)
    origin_label = _content_origin_label(origin_category)
    item['editable'] = item['source_type'] not in READ_ONLY_SOURCE_TYPES
    item['image_pixel_width'] = _coerce_int(item.get('width_px'), 0, 0) or 0
    item['image_pixel_height'] = _coerce_int(item.get('height_px'), 0, 0) or 0
    item['placement'] = {
        'width_cells': _coerce_int(item.get('width_cells') or item.get('map_data_json', {}).get('grid_width'), 1, 1, 500) or 1,
        'height_cells': _coerce_int(item.get('height_cells') or item.get('map_data_json', {}).get('grid_height'), 1, 1, 500) or 1,
        'grid_type': str(item.get('grid_type') or item.get('map_data_json', {}).get('grid_type') or 'square'),
        'scale': scale,
        'transform': transform,
    }
    item['source_creator'] = source_creator
    item['license_label'] = license_label
    item['attribution_text'] = attribution_text
    item['pack_name'] = pack_name
    item['asset_source_type'] = asset_source_type
    item['asset_status'] = availability
    item['is_stub'] = is_stub
    item['quality'] = {
        'has_full_asset': bool(image_url),
        'has_thumbnail': bool(thumb_url),
        'has_preview': bool(preview_url),
        'has_manifest': bool(item.get('metadata_json', {}).get('asset_manifest_path')),
        'metadata_complete': bool(source_creator or license_label or attribution_text or pack_name),
        'is_stub': is_stub,
    }
    item['source'] = {
        'type': item['source_type'],
        'asset_type': asset_source_type,
        'label': source_label,
        'origin_category': origin_category,
        'origin_label': origin_label,
        'is_built_in': item['source_type'] in READ_ONLY_SOURCE_TYPES,
        'is_generated': item['source_type'] == 'generated',
        'is_imported': item['source_type'] == 'imported',
        'is_open_content': asset_source_type == 'open',
        'is_manual_import': asset_source_type == 'manual_import' or item['source_type'] == 'imported',
        'is_premium_manual_import': item['source_type'] == 'imported' and asset_source_type == 'manual_import',
    }
    item['content_origin'] = {
        'category': origin_category,
        'label': origin_label,
        'is_bundled': origin_category == 'bundled',
        'is_user_custom': origin_category == 'user_custom',
        'is_licensed': origin_category == 'licensed_attributed',
    }
    item['attribution'] = {
        'creator': source_creator,
        'license_label': license_label,
        'text': attribution_text,
        'pack_name': pack_name,
        'required': bool(source_creator or license_label or attribution_text),
    }
    item['available'] = availability == 'ready' and bool(image_url)
    return item


def _get_map_no_init(map_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM map_library WHERE id=? AND archived=0', (map_id,)).fetchone()
    return _row_to_map(row) if row else None


def _save_map_no_init(entry: dict[str, Any]) -> dict[str, Any]:
    now = time.time()
    existing = _get_map_no_init(str(entry.get('id') or '')) if entry.get('id') else None
    map_id = str(entry.get('id') or secrets.token_hex(12))
    title = str(entry.get('title') or (existing or {}).get('title') or 'Untitled Map').strip()[:160]
    source_type = _normalize_source_type(entry.get('source_type') or (existing or {}).get('source_type') or 'generated')
    map_data = dict((existing or {}).get('map_data_json') or {})
    map_data.update(dict(entry.get('map_data_json') or {}))
    metadata = dict((existing or {}).get('metadata_json') or {})
    metadata.update(dict(entry.get('metadata_json') or {}))
    transform = _normalise_transform(entry.get('transform') or map_data.get('transform') or metadata.get('transform') or {})
    map_data['transform'] = transform
    metadata['transform'] = transform
    image_url = _normalize_url(entry.get('image_url') or entry.get('full_map_url') or (existing or {}).get('image_url') or (existing or {}).get('full_map_url'))
    if image_url:
        metadata['image_url'] = image_url
    scale = _coerce_float(entry.get('scale') or map_data.get('scale') or metadata.get('scale'), 1.0, 0.05, 20.0) or 1.0
    map_data['scale'] = scale
    metadata['scale'] = scale
    width_cells = _coerce_int(entry.get('width_cells') or map_data.get('grid_width') or (existing or {}).get('width_cells'), 30, 1, 500)
    height_cells = _coerce_int(entry.get('height_cells') or map_data.get('grid_height') or (existing or {}).get('height_cells'), 20, 1, 500)
    map_data['grid_width'] = width_cells
    map_data['grid_height'] = height_cells
    map_data['grid_type'] = str(entry.get('grid_type') or map_data.get('grid_type') or (existing or {}).get('grid_type') or 'square')[:32]
    map_data['grid_scale'] = str(entry.get('scale_label') or map_data.get('grid_scale') or (existing or {}).get('scale_label') or '5 ft')[:32]
    map_data['background_url'] = image_url or map_data.get('background_url') or ''
    direct_metadata = {
        'source_creator': str(entry.get('source_creator') if entry.get('source_creator') is not None else metadata.get('source_creator') or '').strip(),
        'license_label': str(entry.get('license_label') if entry.get('license_label') is not None else metadata.get('license_label') or '').strip(),
        'attribution_text': str(entry.get('attribution_text') if entry.get('attribution_text') is not None else metadata.get('attribution_text') or '').strip(),
        'pack_name': str(entry.get('pack_name') if entry.get('pack_name') is not None else metadata.get('pack_name') or '').strip(),
        'asset_source_type': str(entry.get('asset_source_type') if entry.get('asset_source_type') is not None else metadata.get('asset_source_type') or '').strip().lower(),
    }
    metadata.update({key: value for key, value in direct_metadata.items() if value})
    metadata['availability'] = str(entry.get('asset_status') if entry.get('asset_status') is not None else metadata.get('availability') or 'ready').strip().lower() or 'ready'
    metadata['stub'] = _normalize_bool(entry.get('is_stub') if entry.get('is_stub') is not None else metadata.get('stub'), False)
    payload = {
        'id': map_id,
        'owner_user_id': entry.get('owner_user_id') if entry.get('owner_user_id') is not None else (existing or {}).get('owner_user_id'),
        'parent_map_id': entry.get('parent_map_id') if entry.get('parent_map_id') is not None else (existing or {}).get('parent_map_id'),
        'title': title,
        'slug': slugify(str(entry.get('slug') or (existing or {}).get('slug') or title)),
        'description': str(entry.get('description') if entry.get('description') is not None else (existing or {}).get('description') or '')[:4000],
        'source_type': source_type,
        'map_scope': str(entry.get('map_scope') or (existing or {}).get('map_scope') or 'interior')[:32],
        'terrain': str(entry.get('terrain') if entry.get('terrain') is not None else (existing or {}).get('terrain') or '')[:80],
        'build_type': str(entry.get('build_type') if entry.get('build_type') is not None else (existing or {}).get('build_type') or '')[:80],
        'interior_type': str(entry.get('interior_type') if entry.get('interior_type') is not None else (existing or {}).get('interior_type') or '')[:80],
        'output_mode': str(entry.get('output_mode') if entry.get('output_mode') is not None else (existing or {}).get('output_mode') or '')[:80],
        'image_style': str(entry.get('image_style') if entry.get('image_style') is not None else (existing or {}).get('image_style') or '')[:80],
        'grid_type': map_data['grid_type'],
        'scale_label': map_data['grid_scale'],
        'width_cells': width_cells,
        'height_cells': height_cells,
        'width_px': _coerce_int(entry.get('width_px') if entry.get('width_px') is not None else (existing or {}).get('width_px'), None, 1, 50000),
        'height_px': _coerce_int(entry.get('height_px') if entry.get('height_px') is not None else (existing or {}).get('height_px'), None, 1, 50000),
        'thumbnail_url': _normalize_url(entry.get('thumbnail_url') or metadata.get('thumbnail_override_url') or image_url),
        'full_map_url': image_url,
        'preview_url': _normalize_url(entry.get('preview_url') or image_url),
        'generation_prompt_text': str(entry.get('generation_prompt_text') if entry.get('generation_prompt_text') is not None else (existing or {}).get('generation_prompt_text') or '')[:8000],
        'generation_payload_json': json.dumps(entry.get('generation_payload_json') if entry.get('generation_payload_json') is not None else (existing or {}).get('generation_payload_json') or {}),
        'map_data_json': json.dumps(map_data),
        'tags_json': json.dumps(_normalize_tags(entry.get('tags') if entry.get('tags') is not None else (existing or {}).get('tags') or [])),
        'theme_tags_json': json.dumps(_normalize_tags(entry.get('theme_tags') if entry.get('theme_tags') is not None else (existing or {}).get('theme_tags') or [])),
        'atmosphere_tags_json': json.dumps(_normalize_tags(entry.get('atmosphere_tags') if entry.get('atmosphere_tags') is not None else (existing or {}).get('atmosphere_tags') or [])),
        'normalized_spec_json': json.dumps(entry.get('normalized_spec_json') if entry.get('normalized_spec_json') is not None else (existing or {}).get('normalized_spec_json') or {}),
        'is_favorite': 1 if (entry.get('is_favorite') if entry.get('is_favorite') is not None else (existing or {}).get('is_favorite')) else 0,
        'is_pinned': 1 if (entry.get('is_pinned') if entry.get('is_pinned') is not None else (existing or {}).get('is_pinned')) else 0,
        'is_public': 1 if (entry.get('is_public') if entry.get('is_public') is not None else (existing or {}).get('is_public')) else 0,
        'archived': 1 if (entry.get('archived') if entry.get('archived') is not None else (existing or {}).get('archived')) else 0,
        'created_at': float((existing or {}).get('created_at') or entry.get('created_at') or now),
        'updated_at': now,
        'last_used_at': entry.get('last_used_at') if entry.get('last_used_at') is not None else (existing or {}).get('last_used_at'),
        'use_count': int(entry.get('use_count') if entry.get('use_count') is not None else (existing or {}).get('use_count') or 0),
        'rating': entry.get('rating') if entry.get('rating') is not None else (existing or {}).get('rating'),
        'metadata_json': json.dumps(metadata),
    }
    columns = ', '.join(payload.keys())
    placeholders = ', '.join(['?'] * len(payload))
    updates = ', '.join([f"{key}=excluded.{key}" for key in payload.keys() if key not in {'id', 'created_at'}])
    with get_conn() as conn:
        conn.execute(f'INSERT INTO map_library ({columns}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}', tuple(payload.values()))
        conn.commit()
        row = conn.execute('SELECT * FROM map_library WHERE id=?', (map_id,)).fetchone()
    saved = _row_to_map(row)
    _write_metadata_file(saved)
    return saved


def save_map(entry: dict[str, Any]) -> dict[str, Any]:
    init_map_library_db()
    return _save_map_no_init(entry)

def duplicate_map(map_id: str, *, owner_user_id: str | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any] | None:
    original = get_map(map_id)
    if not original:
        return None
    clone = dict(original)
    clone.update(dict(overrides or {}))
    clone['id'] = secrets.token_hex(12)
    clone['parent_map_id'] = original.get('id')
    clone['owner_user_id'] = owner_user_id if owner_user_id is not None else original.get('owner_user_id')
    clone['source_type'] = 'duplicated'
    clone['is_favorite'] = False
    clone['is_pinned'] = False
    clone['use_count'] = 0
    clone['last_used_at'] = None
    clone['archived'] = False
    if not overrides or 'title' not in overrides:
        clone['title'] = f"{original.get('title') or 'Map'} (Copy)"
    return save_map(clone)


def _write_metadata_file(entry: dict[str, Any]) -> None:
    MAP_LIBRARY_META_DIR.mkdir(parents=True, exist_ok=True)
    path = MAP_LIBRARY_META_DIR / f"{entry['id']}.json"
    path.write_text(json.dumps(entry, indent=2), encoding='utf-8')


def get_map(map_id: str) -> dict[str, Any] | None:
    init_map_library_db()
    return _get_map_no_init(map_id)


def record_use(map_id: str) -> dict[str, Any] | None:
    init_map_library_db()
    now = time.time()
    with get_conn() as conn:
        conn.execute('UPDATE map_library SET use_count = use_count + 1, last_used_at=?, updated_at=? WHERE id=? AND archived=0', (now, now, map_id))
        conn.commit()
    return get_map(map_id)


def archive_map(map_id: str) -> None:
    init_map_library_db()
    with get_conn() as conn:
        conn.execute('UPDATE map_library SET archived=1, updated_at=? WHERE id=?', (time.time(), map_id))
        conn.commit()


def _matches_filter_text(actual: Any, expected: Any) -> bool:
    wanted = str(expected or '').strip().lower()
    if not wanted:
        return True
    return str(actual or '').strip().lower() == wanted


def _filter_metadata_item(item: dict[str, Any], filters: dict[str, Any]) -> bool:
    if not filters.get('include_stub') and item.get('is_stub'):
        return False
    if filters.get('premium_only') and not item.get('source', {}).get('is_premium_manual_import'):
        return False
    if filters.get('open_content_only') and not item.get('source', {}).get('is_open_content'):
        return False
    if not _matches_filter_text(item.get('source_creator'), filters.get('source_creator')):
        return False
    if not _matches_filter_text(item.get('license_label'), filters.get('license_label')):
        return False
    if not _matches_filter_text(item.get('pack_name'), filters.get('pack_name')):
        return False
    if not _matches_filter_text(item.get('asset_source_type'), filters.get('asset_source_type')):
        return False
    if not _matches_filter_text(item.get('content_origin', {}).get('category'), filters.get('content_origin_category')):
        return False
    return True


def _build_collections(items: list[dict[str, Any]], filters: dict[str, Any]) -> dict[str, Any]:
    featured = sorted(
        items,
        key=lambda item: (
            item.get('is_pinned'),
            item.get('quality', {}).get('metadata_complete'),
            item.get('source', {}).get('is_open_content'),
            item.get('use_count') or 0,
            item.get('rank_score') or 0,
        ),
        reverse=True,
    )[:6]
    wanted_scope = str(filters.get('map_scope') or '').strip().lower()
    recommended = sorted(
        items,
        key=lambda item: (
            str(item.get('map_scope') or '').strip().lower() == wanted_scope if wanted_scope else False,
            item.get('rank_score') or 0,
            item.get('quality', {}).get('metadata_complete'),
        ),
        reverse=True,
    )[:6]
    quickstart = sorted(
        items,
        key=lambda item: (
            item.get('content_origin', {}).get('is_bundled'),
            'starter' in {str(tag).strip().lower() for tag in (item.get('tags') or [])},
            item.get('source', {}).get('is_open_content'),
            item.get('quality', {}).get('metadata_complete'),
            item.get('is_pinned'),
            item.get('rank_score') or 0,
        ),
        reverse=True,
    )[:4]
    return {'featured': featured, 'recommended': recommended, 'quickstart': quickstart}


def search_maps(filters: dict[str, Any]) -> dict[str, Any]:
    init_map_library_db()
    clauses = ['archived = 0', 'full_map_url IS NOT NULL', "full_map_url <> ''"]
    params: list[Any] = []

    def add_exact(column: str, key: str):
        value = str(filters.get(key) or '').strip()
        if value:
            if column == 'source_type' and value == 'built_in':
                clauses.append("source_type IN ('builtin','built_in')")
            else:
                clauses.append(f'{column} = ?')
                params.append('builtin' if column == 'source_type' and value == 'builtin' else value)

    for col in ('source_type', 'map_scope', 'terrain', 'build_type', 'interior_type', 'image_style', 'grid_type', 'scale_label'):
        add_exact(col, col)
    if filters.get('favorites_only'):
        clauses.append('is_favorite = 1')
    q = str(filters.get('q') or '').strip().lower()
    if q:
        like = f'%{q}%'
        clauses.append('(LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(tags_json) LIKE ? OR LOWER(generation_prompt_text) LIKE ?)')
        params.extend([like, like, like, like])
    tags = filters.get('tags') or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',') if t.strip()]
    for tag in tags:
        clauses.append('LOWER(tags_json) LIKE ?')
        params.append(f'%{tag.lower()}%')
    where = ' AND '.join(clauses)
    with get_conn() as conn:
        rows = conn.execute(f'SELECT * FROM map_library WHERE {where}', tuple(params)).fetchall()
    items = [_row_to_map(r) for r in rows]
    items = [item for item in items if _filter_metadata_item(item, filters)]
    items = [item for item in items if item.get('available')]
    for item in items:
        item['rank_score'] = _score(item, filters)
    sort_key = str(filters.get('sort') or 'best_match')
    if sort_key == 'alphabetical':
        items.sort(key=lambda m: (m.get('title') or '').lower())
    elif sort_key == 'newest':
        items.sort(key=lambda m: m.get('created_at') or 0, reverse=True)
    elif sort_key == 'recently_used':
        items.sort(key=lambda m: (m.get('last_used_at') or 0, m.get('created_at') or 0), reverse=True)
    elif sort_key == 'favorites':
        items.sort(key=lambda m: (m.get('is_favorite'), m.get('is_pinned'), m.get('created_at') or 0), reverse=True)
    elif sort_key == 'most_used':
        items.sort(key=lambda m: (m.get('use_count') or 0, m.get('last_used_at') or 0), reverse=True)
    else:
        items.sort(key=lambda m: (m.get('rank_score') or 0, m.get('is_pinned'), m.get('is_favorite'), m.get('last_used_at') or 0), reverse=True)
    page = max(1, int(filters.get('page') or 1))
    page_size = max(1, min(100, int(filters.get('page_size') or 24)))
    start = (page - 1) * page_size
    payload = {'items': items[start:start + page_size], 'total': len(items), 'page': page, 'page_size': page_size}
    if filters.get('include_collections'):
        payload['collections'] = _build_collections(items, filters)
    return payload


def _score(item: dict[str, Any], filters: dict[str, Any]) -> float:
    score = 0.0
    scope = str(filters.get('map_scope') or '').strip()
    if scope and item.get('map_scope') == scope:
        score += 40
    for key, weight in [('terrain', 18), ('build_type', 12), ('interior_type', 10), ('grid_type', 8), ('image_style', 8), ('scale_label', 4)]:
        wanted = str(filters.get(key) or '').strip().lower()
        current = str(item.get(key) or '').strip().lower()
        if wanted and wanted == current:
            score += weight
    try:
        wc = int(filters.get('width_cells') or 0)
        hc = int(filters.get('height_cells') or 0)
        if wc and item.get('width_cells'):
            score += max(0, 8 - min(8, abs(int(item['width_cells']) - wc) / 4))
        if hc and item.get('height_cells'):
            score += max(0, 8 - min(8, abs(int(item['height_cells']) - hc) / 4))
    except Exception:
        pass
    q = str(filters.get('q') or '').strip().lower()
    hay = ' '.join([
        str(item.get('title') or ''),
        str(item.get('description') or ''),
        ' '.join(item.get('tags') or []),
        str(item.get('source_creator') or ''),
        str(item.get('pack_name') or ''),
    ]).lower()
    if q:
        title = str(item.get('title') or '').strip().lower()
        tags = [str(tag).strip().lower() for tag in (item.get('tags') or [])]
        if q == title:
            score += 28
        elif title.startswith(q):
            score += 22
        elif q in title:
            score += 18
        elif q in hay:
            score += 16
        else:
            overlap = sum(1 for token in q.split() if token and token in hay)
            score += overlap * 4
        score += sum(3 for tag in tags if tag == q)
    score += min(10, (item.get('use_count') or 0) * 0.4)
    if item.get('is_favorite'):
        score += 6
    if item.get('is_pinned'):
        score += 8
    if item.get('quality', {}).get('metadata_complete'):
        score += 5
    if item.get('source', {}).get('is_open_content'):
        score += 4
    if item.get('source', {}).get('is_premium_manual_import'):
        score += 3
    if item.get('source_type') == 'generated':
        score += 2
    if item.get('source_type') in {'builtin', 'built_in'}:
        score += 1
    if item.get('is_stub'):
        score -= 10
    return round(score, 2)
