import base64
import json
import sqlite3
import zipfile

from server import map_ingest


_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0XQAAAAASUVORK5CYII="
)
_TINY_JPG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEBUQEBAVFhUVFRUVFRUVFRUVFRUWFhUVFRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMsNygtLisBCgoKDg0OGxAQGysmICYrLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAAEAAgMBIgACEQEDEQH/xAAXAAADAQAAAAAAAAAAAAAAAAAAAQID/8QAFhEBAQEAAAAAAAAAAAAAAAAAAQAC/9oADAMBAAIQAxAAAAHfR//EABcQAQADAAAAAAAAAAAAAAAAAAEAEUH/2gAIAQEAAT8AeCf/xAAVEQEBAAAAAAAAAAAAAAAAAAABAP/aAAgBAgEBPwB//8QAFhEBAQEAAAAAAAAAAAAAAAAAAAER/9oACAEDAQE/AR//2Q=="
)


def test_sync_map_imports_reports_diagnostics_without_breaking_valid_imports(tmp_path, monkeypatch):
    import_dir = tmp_path / 'import'
    builtin_dir = tmp_path / 'builtin'
    thumbs_dir = builtin_dir / 'thumbnails'
    previews_dir = builtin_dir / 'previews'
    generated_dir = tmp_path / 'generated'
    manifests_dir = tmp_path / 'manifests'
    for path in (import_dir, builtin_dir, thumbs_dir, previews_dir, generated_dir, manifests_dir):
        path.mkdir(parents=True, exist_ok=True)

    db_path = tmp_path / 'maps.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        '''
        CREATE TABLE map_library (
            id TEXT PRIMARY KEY,
            source_type TEXT,
            full_map_url TEXT,
            thumbnail_url TEXT,
            preview_url TEXT,
            metadata_json TEXT,
            archived INTEGER DEFAULT 0,
            updated_at REAL DEFAULT 0
        )
        '''
    )
    conn.commit()
    conn.close()

    def get_conn():
        handle = sqlite3.connect(db_path)
        handle.row_factory = sqlite3.Row
        return handle

    saved_entries = []

    def save_map(entry):
        saved_entries.append(entry)
        return entry

    valid_image = import_dir / 'valid_map.png'
    valid_image.write_bytes(_TINY_PNG)
    placeholder_image = import_dir / 'sample_placeholder.png'
    placeholder_image.write_bytes(_TINY_PNG)

    manifest = {
        'id': 'diagnostic-pack',
        'pack_name': 'Diagnostic Pack',
        'source_type': 'manual_import',
        'maps': [
            {'id': 'valid-map', 'title': 'Valid Map', 'file_path': 'valid_map.png'},
            {'id': 'missing-map', 'title': 'Missing Map', 'file_path': 'missing_map.png'},
            {'id': 'duplicate-map', 'title': 'Duplicate Map', 'file_path': 'valid_map.png'},
            {'id': 'placeholder-map', 'title': 'Placeholder Map', 'file_path': 'sample_placeholder.png'},
        ],
    }
    (import_dir / 'pack.json').write_text(json.dumps(manifest), encoding='utf-8')

    monkeypatch.setattr(map_ingest, 'MAPS_IMPORT_DIR', import_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_BUILTIN_DIR', builtin_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_THUMBNAILS_DIR', thumbs_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_PREVIEWS_DIR', previews_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_GENERATED_DIR', generated_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_MANIFESTS_DIR', manifests_dir)
    monkeypatch.setattr(map_ingest, '_ensure_starter_pack', lambda: None)

    result = map_ingest.sync_map_imports(save_map=save_map, get_conn=get_conn)

    assert result['imported'] == 1
    assert result['duplicates'] == 1
    assert result['broken'] == 2
    assert len(saved_entries) == 1
    assert result['packs'][0]['maps'] == 1
    assert result['packs'][0]['duplicates'] == 1
    assert result['packs'][0]['broken'] == 2

    codes = {issue['code'] for issue in result['issues']}
    assert 'missing_asset' in codes
    assert 'duplicate_asset' in codes
    assert 'placeholder_asset' in codes
    assert result['packs'][0]['issues'], 'Pack diagnostics should expose per-pack issue details'


def test_sync_map_imports_normalizes_manifest_metadata_for_zip_and_sidecar_packs(tmp_path, monkeypatch):
    import_dir = tmp_path / 'import'
    builtin_dir = tmp_path / 'builtin'
    thumbs_dir = builtin_dir / 'thumbnails'
    previews_dir = builtin_dir / 'previews'
    generated_dir = tmp_path / 'generated'
    manifests_dir = tmp_path / 'manifests'
    for path in (import_dir, builtin_dir, thumbs_dir, previews_dir, generated_dir, manifests_dir):
        path.mkdir(parents=True, exist_ok=True)

    db_path = tmp_path / 'maps.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        '''
        CREATE TABLE map_library (
            id TEXT PRIMARY KEY,
            source_type TEXT,
            full_map_url TEXT,
            thumbnail_url TEXT,
            preview_url TEXT,
            metadata_json TEXT,
            archived INTEGER DEFAULT 0,
            updated_at REAL DEFAULT 0
        )
        '''
    )
    conn.commit()
    conn.close()

    def get_conn():
        handle = sqlite3.connect(db_path)
        handle.row_factory = sqlite3.Row
        return handle

    saved_entries = []

    def save_map(entry):
        saved_entries.append(entry)
        return entry

    # Bundled zip pack with intentionally mixed-type manifest fields.
    archive = import_dir / 'bundle.zip'
    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr('maps/zip_map.png', _TINY_PNG)
        zf.writestr(
            'maps/pack.json',
            json.dumps(
                {
                    'id': 'zip-pack',
                    'pack_name': 'Zip Pack',
                    'source_type': 'MANUAL_IMPORT',
                    'source_creator': 'Zip Creator',
                    'license_label': 'Zip License',
                    'attribution_text': 'Zip Attribution',
                    'active': 'false',
                    'maps': [
                        {
                            'id': 'zip-map',
                            'title': 'Zip Map',
                            'file_path': 'zip_map.png',
                            'width_cells': 'bad-value',
                            'height_cells': '42',
                            'active': 'true',
                        }
                    ],
                }
            ),
        )

    # Loose image folder with source sidecar metadata.
    loose_dir = import_dir / 'loose-pack'
    loose_dir.mkdir(parents=True, exist_ok=True)
    (loose_dir / 'loose_map.jpg').write_bytes(_TINY_JPG)
    (loose_dir / 'source.txt').write_text(
        '\n'.join(
            [
                'source_type: licensed',
                'creator: Sidecar Creator',
                'license: Sidecar License',
                'attribution_text: Sidecar Attribution',
            ]
        ),
        encoding='utf-8',
    )

    monkeypatch.setattr(map_ingest, 'MAPS_IMPORT_DIR', import_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_BUILTIN_DIR', builtin_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_THUMBNAILS_DIR', thumbs_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_PREVIEWS_DIR', previews_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_GENERATED_DIR', generated_dir)
    monkeypatch.setattr(map_ingest, 'MAPS_MANIFESTS_DIR', manifests_dir)
    monkeypatch.setattr(map_ingest, '_ensure_starter_pack', lambda: None)

    result = map_ingest.sync_map_imports(save_map=save_map, get_conn=get_conn)

    assert result['imported'] == 2
    assert result['broken'] == 0
    assert result['duplicates'] == 0

    zip_entry = next(entry for entry in saved_entries if entry['id'] == 'zip-map')
    assert zip_entry['source_type'] == 'imported'
    assert zip_entry['metadata_json']['asset_source_type'] == 'manual_import'
    assert zip_entry['metadata_json']['source_creator'] == 'Zip Creator'
    assert zip_entry['metadata_json']['license_label'] == 'Zip License'
    assert zip_entry['metadata_json']['attribution_text'] == 'Zip Attribution'
    assert zip_entry['width_cells'] is None
    assert zip_entry['height_cells'] == 42

    loose_entry = next(entry for entry in saved_entries if entry['id'] != 'zip-map')
    assert loose_entry['source_type'] == 'builtin'
    assert loose_entry['metadata_json']['asset_source_type'] == 'licensed'
    assert loose_entry['metadata_json']['source_creator'] == 'Sidecar Creator'
    assert loose_entry['metadata_json']['license_label'] == 'Sidecar License'
    assert loose_entry['metadata_json']['attribution_text'] == 'Sidecar Attribution'
