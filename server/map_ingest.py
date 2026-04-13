from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any

from server.paths import (
    MAPS_BUILTIN_DIR,
    MAPS_GENERATED_DIR,
    MAPS_IMPORT_DIR,
    MAPS_MANIFESTS_DIR,
    MAPS_PREVIEWS_DIR,
    MAPS_THUMBNAILS_DIR,
)

SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp'}
SUPPORTED_ARCHIVE_EXTENSIONS = {'.zip'}
MANIFEST_FILENAMES = ('pack.json', 'manifest.json', 'map_pack.json')
MAP_SOURCE_TYPES = {'open', 'licensed', 'manual_import'}
SCHEMA_VERSION = 1
_PLACEHOLDER_HINTS = {'placeholder', 'stub', 'sample', 'mock'}
MAX_IMPORT_DIAGNOSTICS = 200


class ImporterError(RuntimeError):
    def __init__(self, message: str, *, code: str = 'import_error', path: str = '', asset_id: str = ''):
        super().__init__(message)
        self.code = code
        self.path = path
        self.asset_id = asset_id


def ensure_map_dirs() -> None:
    for path in (
        MAPS_IMPORT_DIR,
        MAPS_BUILTIN_DIR,
        MAPS_THUMBNAILS_DIR,
        MAPS_PREVIEWS_DIR,
        MAPS_GENERATED_DIR,
        MAPS_MANIFESTS_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def sync_map_imports(*, save_map, get_conn, slugify=None) -> dict[str, Any]:
    ensure_map_dirs()
    _ensure_starter_pack()
    diagnostics: list[dict[str, Any]] = []
    extracted = _extract_archives(diagnostics=diagnostics)
    pack_defs = _discover_pack_definitions(extracted, diagnostics=diagnostics)
    results = {
        'imported': 0,
        'duplicates': 0,
        'broken': 0,
        'hidden_legacy_placeholders': 0,
        'packs': [],
        'issues': diagnostics,
    }

    results['hidden_legacy_placeholders'] = _archive_legacy_placeholder_rows(get_conn)

    seen_checksums: set[str] = set()
    seen_targets: set[str] = set()
    pack_ids: set[str] = set()

    for pack in pack_defs:
        pack_id = pack['pack_id']
        pack_ids.add(pack_id)
        pack_result = {
            'pack_id': pack_id,
            'pack_name': pack.get('pack_name') or pack_id,
            'source_type': pack.get('source_type') or 'manual_import',
            'manifest_path': str(pack.get('pack_manifest_path') or ''),
            'maps': 0,
            'duplicates': 0,
            'broken': 0,
            'issues': [],
        }
        for asset in pack['assets']:
            try:
                manifest = _ingest_asset(pack, asset, seen_checksums=seen_checksums, seen_targets=seen_targets)
            except DuplicateAsset as exc:
                pack_result['duplicates'] += 1
                results['duplicates'] += 1
                issue = _diagnostic_entry(
                    level='warning',
                    code=exc.code,
                    message=str(exc),
                    pack=pack,
                    asset=asset,
                    path=exc.path or str(asset.get('resolved_file_path') or ''),
                    asset_id=exc.asset_id or str(asset.get('id') or ''),
                )
                _append_diagnostic(results['issues'], issue)
                _append_diagnostic(pack_result['issues'], issue)
                continue
            except BrokenAsset as exc:
                pack_result['broken'] += 1
                results['broken'] += 1
                issue = _diagnostic_entry(
                    level='error',
                    code=exc.code,
                    message=str(exc),
                    pack=pack,
                    asset=asset,
                    path=exc.path or str(asset.get('resolved_file_path') or ''),
                    asset_id=exc.asset_id or str(asset.get('id') or ''),
                )
                _append_diagnostic(results['issues'], issue)
                _append_diagnostic(pack_result['issues'], issue)
                continue
            save_map(_build_library_entry(manifest))
            pack_result['maps'] += 1
            results['imported'] += 1
        results['packs'].append(pack_result)

    _mark_missing_assets(get_conn)
    _archive_missing_manifests(get_conn, pack_ids)
    return results


class DuplicateAsset(Exception):
    def __init__(self, message: str, *, code: str = 'duplicate_asset', path: str = '', asset_id: str = ''):
        super().__init__(message)
        self.code = code
        self.path = path
        self.asset_id = asset_id


class BrokenAsset(Exception):
    def __init__(self, message: str, *, code: str = 'broken_asset', path: str = '', asset_id: str = ''):
        super().__init__(message)
        self.code = code
        self.path = path
        self.asset_id = asset_id


def _coerce_int(value: Any, default: int = 0, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        result = int(value)
    except Exception:
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _coerce_bool(value: Any, default: bool = True) -> bool:
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


def _normalize_source_type(value: Any) -> str:
    source_type = str(value or 'manual_import').strip().lower()
    if source_type not in MAP_SOURCE_TYPES:
        return 'manual_import'
    return source_type


def _append_diagnostic(target: list[dict[str, Any]], issue: dict[str, Any]) -> None:
    if len(target) >= MAX_IMPORT_DIAGNOSTICS:
        return
    target.append(issue)


def _diagnostic_entry(*, level: str, code: str, message: str, pack: dict[str, Any] | None = None, asset: dict[str, Any] | None = None, path: str = '', asset_id: str = '') -> dict[str, Any]:
    entry = {
        'level': level,
        'code': code,
        'message': message,
        'path': path,
        'asset_id': asset_id or str((asset or {}).get('id') or ''),
        'pack_id': str((pack or {}).get('pack_id') or ''),
        'pack_name': str((pack or {}).get('pack_name') or ''),
    }
    if asset:
        entry['asset_title'] = str(asset.get('title') or '')
    return entry


def _archive_legacy_placeholder_rows(get_conn) -> int:
    now = time.time()
    changed = 0
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, metadata_json FROM map_library WHERE source_type='builtin' AND (full_map_url LIKE '/static/maps/full/%' OR thumbnail_url LIKE '/static/maps/full/%')"
        ).fetchall()
        for row in rows:
            metadata = _loads(row['metadata_json'], {})
            metadata['availability'] = 'legacy_placeholder_hidden'
            metadata['legacy_seed_hidden_at'] = now
            conn.execute(
                'UPDATE map_library SET archived=1, updated_at=?, metadata_json=? WHERE id=?',
                (now, json.dumps(metadata), row['id']),
            )
            changed += 1
        conn.commit()
    return changed


def _extract_archives(*, diagnostics: list[dict[str, Any]] | None = None) -> list[Path]:
    extracted: list[Path] = []
    for archive in MAPS_IMPORT_DIR.rglob('*'):
        if archive.suffix.lower() not in SUPPORTED_ARCHIVE_EXTENSIONS or not archive.is_file():
            continue
        archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()[:12]
        dest = MAPS_GENERATED_DIR / 'extracted' / f'{archive.stem}-{archive_hash}'
        marker = dest / '.done'
        if marker.exists():
            extracted.append(dest)
            continue
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    name = Path(member.filename)
                    if name.name.startswith('.'):
                        continue
                    if name.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS | {'.json', '.txt'}:
                        continue
                    target = dest / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target, 'wb') as out:
                        shutil.copyfileobj(src, out)
        except zipfile.BadZipFile:
            if diagnostics is not None:
                _append_diagnostic(diagnostics, {
                    'level': 'error',
                    'code': 'bad_archive',
                    'message': f'Archive could not be read: {archive.name}',
                    'path': str(archive),
                    'asset_id': '',
                    'pack_id': '',
                    'pack_name': archive.stem,
                })
            if dest.exists():
                shutil.rmtree(dest)
            continue
        marker.write_text(str(time.time()), encoding='utf-8')
        extracted.append(dest)
    return extracted


def _discover_pack_definitions(extracted_roots: list[Path], *, diagnostics: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    roots = [MAPS_IMPORT_DIR, *extracted_roots]
    packs: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        manifest_paths = []
        for filename in MANIFEST_FILENAMES:
            manifest_paths.extend(root.rglob(filename))
        used_dirs: set[Path] = set()
        for manifest_path in sorted(set(manifest_paths)):
            pack = _load_pack_manifest(manifest_path)
            if pack:
                packs.append(pack)
                used_dirs.add(manifest_path.parent.resolve())
            elif diagnostics is not None:
                _append_diagnostic(diagnostics, {
                    'level': 'error',
                    'code': 'invalid_manifest',
                    'message': f'Manifest could not be parsed or had no valid assets: {manifest_path.name}',
                    'path': str(manifest_path),
                    'asset_id': '',
                    'pack_id': '',
                    'pack_name': manifest_path.parent.name,
                })
        for directory in [root, *[p for p in root.rglob('*') if p.is_dir()]]:
            resolved = directory.resolve()
            if any(resolved == used or used in resolved.parents for used in used_dirs):
                continue
            images = sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS)
            if not images:
                continue
            packs.append(_build_inferred_pack(directory, images))
            used_dirs.add(resolved)
    deduped: dict[str, dict[str, Any]] = {}
    for pack in packs:
        deduped[pack['pack_id']] = pack
    return list(deduped.values())


def _load_pack_manifest(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    maps = raw.get('maps') or raw.get('assets') or []
    if not isinstance(maps, list):
        return None
    pack_name = str(raw.get('pack_name') or raw.get('title') or path.parent.name).strip() or path.parent.name
    source_type = _normalize_source_type(raw.get('source_type'))
    pack_id = _safe_id(str(raw.get('id') or slug_filename(pack_name)))
    assets = []
    for item in maps:
        if not isinstance(item, dict):
            continue
        file_ref = Path(str(item.get('file_path') or item.get('file') or '')).expanduser()
        file_path = file_ref if file_ref.is_absolute() else (path.parent / file_ref)
        asset = dict(item)
        asset['resolved_file_path'] = file_path
        assets.append(asset)
    if not assets:
        return None
    return {
        'pack_id': pack_id,
        'pack_name': pack_name,
        'pack_manifest_path': path,
        'source_type': source_type,
        'source_creator': str(raw.get('source_creator') or raw.get('creator') or '').strip(),
        'license_label': str(raw.get('license_label') or raw.get('license') or '').strip(),
        'attribution_text': str(raw.get('attribution_text') or '').strip(),
        'active': _coerce_bool(raw.get('active', True), True),
        'assets': assets,
    }


def _build_inferred_pack(directory: Path, images: list[Path]) -> dict[str, Any]:
    sidecar = next((p for p in directory.iterdir() if p.is_file() and p.name.lower() in {'pack.txt', 'source.txt'}), None)
    source_text = sidecar.read_text(encoding='utf-8').strip() if sidecar and sidecar.exists() else ''
    source_type = 'manual_import'
    creator = ''
    license_label = ''
    attribution_text = ''
    if source_text:
        for line in source_text.splitlines():
            if ':' not in line:
                continue
            key, value = [part.strip() for part in line.split(':', 1)]
            key = key.lower()
            if key == 'source_type':
                source_type = _normalize_source_type(value)
            elif key in {'creator', 'source_creator'}:
                creator = value
            elif key in {'license', 'license_label'}:
                license_label = value
            elif key == 'attribution_text':
                attribution_text = value
    return {
        'pack_id': _safe_id(slug_filename(directory.name)),
        'pack_name': directory.name,
        'pack_manifest_path': None,
        'source_type': source_type,
        'source_creator': creator,
        'license_label': license_label,
        'attribution_text': attribution_text,
        'active': True,
        'assets': [{'resolved_file_path': path} for path in images],
    }


def _ingest_asset(pack: dict[str, Any], asset: dict[str, Any], *, seen_checksums: set[str], seen_targets: set[str]) -> dict[str, Any]:
    source_path = Path(asset.get('resolved_file_path') or '')
    manifest_id = str(asset.get('id') or '')
    if not source_path.exists() or not source_path.is_file() or source_path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise BrokenAsset(f'Missing map asset: {source_path}', code='missing_asset', path=str(source_path), asset_id=manifest_id)
    raw = source_path.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    manifest_id = manifest_id or f"{pack['pack_id']}-{checksum[:12]}"
    if _looks_like_placeholder(source_path):
        raise BrokenAsset(f'Placeholder asset ignored: {source_path.name}', code='placeholder_asset', path=str(source_path), asset_id=manifest_id)
    dest_name = f'{manifest_id}{source_path.suffix.lower()}'
    final_path = MAPS_BUILTIN_DIR / dest_name
    if checksum in seen_checksums or str(final_path) in seen_targets:
        raise DuplicateAsset(f'Duplicate asset skipped: {source_path.name}', code='duplicate_asset', path=str(source_path), asset_id=manifest_id)
    seen_checksums.add(checksum)
    seen_targets.add(str(final_path))
    image_meta = _copy_and_render_derivatives(raw, source_path.suffix.lower(), final_path, manifest_id)
    inferred = infer_metadata(source_path)
    title = str(asset.get('title') or inferred['title'] or source_path.stem.replace('_', ' ').title()).strip()
    tags = _unique_strings([*(asset.get('tags') or []), *inferred['tags']])
    source_type = _normalize_source_type(asset.get('source_type') or pack.get('source_type') or 'manual_import')
    manifest = {
        'schema_version': SCHEMA_VERSION,
        'id': manifest_id,
        'title': title,
        'source_creator': str(asset.get('source_creator') or pack.get('source_creator') or '').strip(),
        'source_type': source_type,
        'license_label': str(asset.get('license_label') or pack.get('license_label') or '').strip(),
        'map_scope': str(asset.get('map_scope') or inferred['map_scope'] or 'battlemap'),
        'terrain': str(asset.get('terrain') or inferred['terrain'] or ''),
        'build_type': str(asset.get('build_type') or inferred['build_type'] or ''),
        'interior_type': str(asset.get('interior_type') or inferred['interior_type'] or ''),
        'image_style': str(asset.get('image_style') or inferred['image_style'] or 'tactical'),
        'grid_type': str(asset.get('grid_type') or inferred['grid_type'] or 'square'),
        'scale_label': str(asset.get('scale_label') or inferred['scale_label'] or '5 ft'),
        'width_cells': _coerce_int(asset.get('width_cells') or inferred['width_cells'] or 0, 0, minimum=0, maximum=10000),
        'height_cells': _coerce_int(asset.get('height_cells') or inferred['height_cells'] or 0, 0, minimum=0, maximum=10000),
        'tags': tags,
        'file_path': _api_map_url(final_path),
        'thumbnail_path': _api_map_url(image_meta['thumbnail_path']),
        'preview_path': _api_map_url(image_meta['preview_path']),
        'attribution_text': str(asset.get('attribution_text') or pack.get('attribution_text') or '').strip(),
        'pack_name': str(asset.get('pack_name') or pack.get('pack_name') or '').strip(),
        'imported_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'checksum': checksum,
        'active': _coerce_bool(asset.get('active', pack.get('active', True)), True),
        'manifest_path': str(MAPS_MANIFESTS_DIR / f'{manifest_id}.json'),
        'source_file_path': str(source_path),
        'width_px': image_meta['width_px'],
        'height_px': image_meta['height_px'],
    }
    (MAPS_MANIFESTS_DIR / f'{manifest_id}.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def infer_metadata(path: Path) -> dict[str, Any]:
    stem = path.stem.lower().replace('-', '_')
    tokens = [token for token in stem.split('_') if token]
    terrain_tokens = {'forest', 'cave', 'coastal', 'mountain', 'swamp', 'desert', 'river', 'volcanic', 'urban', 'harbor', 'road', 'ruins', 'temple', 'castle', 'crypt', 'tundra', 'jungle', 'town', 'village'}
    build_tokens = {'keep', 'tower', 'courtyard', 'tomb', 'temple', 'fortress', 'village', 'district', 'harbor', 'camp', 'road', 'crossroads', 'inn', 'castle', 'throne', 'market', 'dock', 'shrine'}
    style_tokens = {'painterly', 'atlas', 'inkwash', 'tactical', 'realistic', 'dark', 'ancient', 'vibrant'}
    terrain = next((token for token in tokens if token in terrain_tokens), '')
    build = next((token for token in tokens if token in build_tokens), '')
    image_style = next((token for token in tokens if token in style_tokens), 'tactical')
    size_map = {'tiny': 16, 'small': 24, 'medium': 32, 'large': 48, 'huge': 72}
    base = next((size_map[token] for token in tokens if token in size_map), 32)
    scope = 'region' if 'region' in tokens or 'world' in tokens else 'battlemap'
    if any(token in tokens for token in {'dungeon', 'crypt', 'tavern', 'tower', 'manor', 'mine', 'temple', 'keep'}):
        scope = 'interior'
    if any(token in tokens for token in {'town', 'village', 'settlement', 'hamlet'}):
        scope = 'location'
    return {
        'title': ' '.join(token.capitalize() for token in tokens if not token.isdigit()) or path.stem.replace('_', ' ').title(),
        'map_scope': scope,
        'terrain': terrain or ('urban' if 'town' in tokens else ''),
        'build_type': build,
        'interior_type': build if scope == 'interior' else '',
        'image_style': image_style,
        'grid_type': 'square',
        'scale_label': '5 ft' if scope in {'battlemap', 'interior'} else '1 mile',
        'width_cells': base,
        'height_cells': base if scope != 'region' else max(20, base // 2),
        'tags': [token for token in tokens if len(token) > 2 and not token.isdigit() and token not in size_map],
    }


def _copy_and_render_derivatives(raw: bytes, ext: str, final_path: Path, manifest_id: str) -> dict[str, Any]:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    thumb_path = MAPS_THUMBNAILS_DIR / f'{manifest_id}.webp'
    preview_path = MAPS_PREVIEWS_DIR / f'{manifest_id}.webp'
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(raw))
        img.load()
        width_px, height_px = img.width, img.height
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        img.save(final_path, quality=95)
        thumb = img.copy()
        thumb.thumbnail((256, 256), Image.LANCZOS)
        thumb.save(thumb_path, 'WEBP', quality=82, method=5)
        preview = img.copy()
        preview.thumbnail((1024, 1024), Image.LANCZOS)
        preview.save(preview_path, 'WEBP', quality=88, method=5)
        return {'thumbnail_path': thumb_path, 'preview_path': preview_path, 'width_px': width_px, 'height_px': height_px}
    except Exception:
        final_path.write_bytes(raw)
        shutil.copy2(final_path, thumb_path)
        shutil.copy2(final_path, preview_path)
        return {'thumbnail_path': thumb_path, 'preview_path': preview_path, 'width_px': 0, 'height_px': 0}


def _build_library_entry(manifest: dict[str, Any]) -> dict[str, Any]:
    db_source_type = 'imported' if manifest['source_type'] == 'manual_import' else 'builtin'
    title = manifest['title']
    description_bits = [manifest.get('pack_name') or '', manifest.get('attribution_text') or '']
    description = ' · '.join(bit for bit in description_bits if bit).strip(' ·')
    return {
        'id': manifest['id'],
        'title': title,
        'slug': slug_filename(title),
        'description': description,
        'source_type': db_source_type,
        'map_scope': manifest['map_scope'],
        'terrain': manifest['terrain'],
        'build_type': manifest['build_type'],
        'interior_type': manifest['interior_type'],
        'output_mode': 'illustrated_overview' if manifest['map_scope'] == 'region' else 'tactical_grid',
        'image_style': manifest['image_style'],
        'grid_type': manifest['grid_type'],
        'scale_label': manifest['scale_label'],
        'width_cells': manifest['width_cells'] or None,
        'height_cells': manifest['height_cells'] or None,
        'width_px': manifest.get('width_px') or None,
        'height_px': manifest.get('height_px') or None,
        'thumbnail_url': manifest['thumbnail_path'],
        'full_map_url': manifest['file_path'],
        'preview_url': manifest['preview_path'],
        'map_data_json': {
            'background_url': manifest['file_path'],
            'grid_type': manifest['grid_type'],
            'grid_scale': manifest['scale_label'],
            'grid_width': manifest['width_cells'],
            'grid_height': manifest['height_cells'],
            'metadata': {'pack_name': manifest['pack_name'], 'source_creator': manifest['source_creator']},
        },
        'tags': manifest['tags'],
        'is_public': True,
        'is_pinned': manifest['source_type'] in {'open', 'licensed'},
        'metadata_json': {
            'asset_manifest_path': manifest['manifest_path'],
            'asset_source_type': manifest['source_type'],
            'license_label': manifest['license_label'],
            'source_creator': manifest['source_creator'],
            'pack_name': manifest['pack_name'],
            'attribution_text': manifest['attribution_text'],
            'checksum': manifest['checksum'],
            'availability': 'ready' if manifest['active'] else 'inactive',
            'file_path': manifest['file_path'],
            'thumbnail_path': manifest['thumbnail_path'],
            'preview_path': manifest['preview_path'],
            'source_file_path': manifest['source_file_path'],
        },
        'archived': not bool(manifest['active']),
    }


def _mark_missing_assets(get_conn) -> None:
    now = time.time()
    with get_conn() as conn:
        rows = conn.execute("SELECT id, full_map_url, thumbnail_url, preview_url, metadata_json FROM map_library WHERE archived=0").fetchall()
        for row in rows:
            metadata = _loads(row['metadata_json'], {})
            for key in ('full_map_url', 'thumbnail_url', 'preview_url'):
                url = row[key]
                if not url or not _map_url_exists(url):
                    metadata['availability'] = 'missing_asset'
                    conn.execute('UPDATE map_library SET archived=1, updated_at=?, metadata_json=? WHERE id=?', (now, json.dumps(metadata), row['id']))
                    break
        conn.commit()


def _archive_missing_manifests(get_conn, active_pack_ids: set[str]) -> None:
    if not active_pack_ids:
        return
    now = time.time()
    with get_conn() as conn:
        rows = conn.execute("SELECT id, metadata_json FROM map_library WHERE source_type IN ('builtin','imported')").fetchall()
        for row in rows:
            metadata = _loads(row['metadata_json'], {})
            manifest_path = metadata.get('asset_manifest_path')
            if manifest_path and not Path(manifest_path).exists():
                metadata['availability'] = 'missing_manifest'
                conn.execute('UPDATE map_library SET archived=1, updated_at=?, metadata_json=? WHERE id=?', (now, json.dumps(metadata), row['id']))
        conn.commit()


def _map_url_exists(url: str) -> bool:
    if not url.startswith('/api/maps/assets/'):
        return True
    rel = url.split('/api/maps/assets/', 1)[1]
    return (MAPS_IMPORT_DIR.parent / rel).exists()


def _api_map_url(path: Path) -> str:
    maps_root = MAPS_IMPORT_DIR.parent
    return f"/api/maps/assets/{path.relative_to(maps_root).as_posix()}"


def _looks_like_placeholder(path: Path) -> bool:
    lowered = path.name.lower()
    return any(hint in lowered for hint in _PLACEHOLDER_HINTS)


def _loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def _unique_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(text[:64])
    return result[:16]


def slug_filename(value: str) -> str:
    return _safe_id(re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-') or 'map')


def _safe_id(value: str) -> str:
    return re.sub(r'[^a-z0-9_-]+', '-', value.lower()).strip('-_')[:80] or 'map'


def _ensure_starter_pack() -> None:
    starter_dir = MAPS_IMPORT_DIR / 'open-starter-pack'
    manifest_path = starter_dir / 'pack.json'
    if manifest_path.exists():
        return
    starter_dir.mkdir(parents=True, exist_ok=True)
    maps = [
        {
            'id': 'starter-crossroads-ambush',
            'title': 'Crossroads Ambush',
            'file_path': 'crossroads_ambush.png',
            'map_scope': 'battlemap',
            'terrain': 'road',
            'build_type': 'crossroads',
            'image_style': 'tactical',
            'grid_type': 'square',
            'scale_label': '5 ft',
            'width_cells': 24,
            'height_cells': 18,
            'tags': ['road', 'forest', 'ambush', 'starter'],
            'attribution_text': 'Original OpenAI starter battlemap authored for this project.'
        },
        {
            'id': 'starter-ruined-shrine',
            'title': 'Ruined Shrine Courtyard',
            'file_path': 'ruined_shrine_courtyard.png',
            'map_scope': 'battlemap',
            'terrain': 'ruins',
            'build_type': 'shrine',
            'image_style': 'tactical',
            'grid_type': 'square',
            'scale_label': '5 ft',
            'width_cells': 22,
            'height_cells': 16,
            'tags': ['ruins', 'shrine', 'courtyard', 'starter'],
            'attribution_text': 'Original OpenAI starter battlemap authored for this project.'
        },
    ]
    pack = {
        'id': 'open-starter-pack',
        'pack_name': 'Open Starter Pack',
        'source_creator': 'OpenAI / Casual DnD starter content',
        'source_type': 'open',
        'license_label': 'Open starter content bundled with the app',
        'attribution_text': 'Original starter battlemaps included for lawful demo/library seeding.',
        'maps': maps,
    }
    manifest_path.write_text(json.dumps(pack, indent=2), encoding='utf-8')
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return
    _render_crossroads_map(starter_dir / 'crossroads_ambush.png', Image, ImageDraw)
    _render_shrine_map(starter_dir / 'ruined_shrine_courtyard.png', Image, ImageDraw)


def _render_crossroads_map(path: Path, Image, ImageDraw) -> None:
    cell = 64
    w, h = 24 * cell, 18 * cell
    img = Image.new('RGB', (w, h), '#31452c')
    draw = ImageDraw.Draw(img)
    for x in range(0, w, cell):
        draw.line((x, 0, x, h), fill=(82, 96, 68), width=1)
    for y in range(0, h, cell):
        draw.line((0, y, w, y), fill=(82, 96, 68), width=1)
    draw.rectangle((0, 7 * cell, w, 11 * cell), fill='#826a48')
    draw.rectangle((10 * cell, 0, 14 * cell, h), fill='#826a48')
    draw.rectangle((2 * cell, 2 * cell, 6 * cell, 6 * cell), fill='#455b3a')
    draw.rectangle((17 * cell, 12 * cell, 22 * cell, 16 * cell), fill='#455b3a')
    draw.ellipse((9 * cell, 7 * cell, 15 * cell, 13 * cell), outline='#4a3421', width=10)
    draw.rectangle((3 * cell, 12 * cell, 8 * cell, 15 * cell), fill='#4f3d2f')
    draw.rectangle((16 * cell, 2 * cell, 21 * cell, 5 * cell), fill='#4f3d2f')
    for cx, cy in [(4, 4), (18, 14), (6, 13), (19, 3), (12, 9)]:
        draw.ellipse(((cx * cell) - 14, (cy * cell) - 14, (cx * cell) + 14, (cy * cell) + 14), fill='#23311d')
    img.save(path)


def _render_shrine_map(path: Path, Image, ImageDraw) -> None:
    cell = 64
    w, h = 22 * cell, 16 * cell
    img = Image.new('RGB', (w, h), '#58614a')
    draw = ImageDraw.Draw(img)
    for x in range(0, w, cell):
        draw.line((x, 0, x, h), fill=(104, 114, 92), width=1)
    for y in range(0, h, cell):
        draw.line((0, y, w, y), fill=(104, 114, 92), width=1)
    draw.rectangle((3 * cell, 2 * cell, 19 * cell, 14 * cell), fill='#8d8b7a')
    draw.rectangle((5 * cell, 4 * cell, 17 * cell, 12 * cell), fill='#69735e')
    draw.rectangle((8 * cell, 5 * cell, 14 * cell, 11 * cell), fill='#a79d85')
    draw.rectangle((10 * cell, 0, 12 * cell, 5 * cell), fill='#8d8b7a')
    draw.rectangle((10 * cell, 11 * cell, 12 * cell, h), fill='#8d8b7a')
    for cx, cy in [(6, 5), (16, 5), (6, 11), (16, 11)]:
        draw.rectangle(((cx * cell) - 18, (cy * cell) - 18, (cx * cell) + 18, (cy * cell) + 18), fill='#4e4f4a')
    draw.ellipse((9 * cell, 6 * cell, 13 * cell, 10 * cell), outline='#3d3024', width=8)
    img.save(path)
