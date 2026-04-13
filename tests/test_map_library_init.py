import sqlite3

from server import map_library


def test_init_map_library_db_uses_no_init_save_helper_during_sync(tmp_path, monkeypatch):
    db_path = tmp_path / 'maps.db'
    meta_dir = tmp_path / 'library_meta'

    def temp_get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    sync_calls: list[str] = []

    def fake_sync_map_imports(*, save_map, get_conn, slugify=None):
        assert save_map is map_library._save_map_no_init
        assert get_conn is temp_get_conn
        assert map_library._MAP_LIBRARY_DB_INITIALIZING is True
        sync_calls.append('called')

        created = save_map(
            {
                'id': 'starter-map',
                'title': 'Starter Map',
                'source_type': 'imported',
                'full_map_url': '/api/maps/assets/builtin/starter.png',
                'thumbnail_url': '/api/maps/assets/builtin/starter-thumb.png',
                'preview_url': '/api/maps/assets/builtin/starter-preview.png',
            }
        )
        assert created['title'] == 'Starter Map'

        updated = save_map(
            {
                'id': 'starter-map',
                'title': 'Starter Map Updated',
                'source_type': 'imported',
                'full_map_url': '/api/maps/assets/builtin/starter.png',
            }
        )
        assert updated['title'] == 'Starter Map Updated'
        return {'imported': 1, 'duplicates': 0, 'broken': 0, 'packs': []}

    monkeypatch.setattr(map_library, 'get_conn', temp_get_conn)
    monkeypatch.setattr(map_library, 'MAP_LIBRARY_META_DIR', meta_dir)
    monkeypatch.setattr(map_library, 'sync_map_imports', fake_sync_map_imports)
    monkeypatch.setattr(map_library, '_MAP_LIBRARY_DB_READY', False)
    monkeypatch.setattr(map_library, '_MAP_LIBRARY_DB_INITIALIZING', False)

    map_library.init_map_library_db()
    map_library.init_map_library_db()

    assert sync_calls == ['called']
    assert map_library._MAP_LIBRARY_DB_READY is True
    assert map_library._MAP_LIBRARY_DB_INITIALIZING is False

    loaded = map_library.get_map('starter-map')
    assert loaded is not None
    assert loaded['title'] == 'Starter Map Updated'
    assert (meta_dir / 'starter-map.json').exists()


def test_get_map_exposes_canonical_metadata_contract(tmp_path, monkeypatch):
    db_path = tmp_path / 'maps.db'
    meta_dir = tmp_path / 'library_meta'

    def temp_get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(map_library, 'get_conn', temp_get_conn)
    monkeypatch.setattr(map_library, 'MAP_LIBRARY_META_DIR', meta_dir)
    monkeypatch.setattr(map_library, 'sync_map_imports', lambda **kwargs: {'imported': 0, 'duplicates': 0, 'broken': 0, 'packs': []})
    monkeypatch.setattr(map_library, '_MAP_LIBRARY_DB_READY', False)
    monkeypatch.setattr(map_library, '_MAP_LIBRARY_DB_INITIALIZING', False)

    saved = map_library.save_map({
        'id': 'premium-pack-map',
        'title': 'Premium Pack Map',
        'description': 'Imported from a licensed pack.',
        'source_type': 'imported',
        'asset_source_type': 'manual_import',
        'source_creator': 'Cartographer Guild',
        'license_label': 'Licensed purchase',
        'attribution_text': 'Imported by the DM from a lawfully purchased pack.',
        'pack_name': 'Vault of Dungeons',
        'full_map_url': '/api/maps/assets/builtin/premium-pack-map.png',
        'thumbnail_url': '/api/maps/assets/builtin/premium-pack-map-thumb.webp',
        'preview_url': '/api/maps/assets/builtin/premium-pack-map-preview.webp',
        'tags': ['dungeon', 'premium', 'vault'],
        'metadata_json': {
            'availability': 'ready',
            'stub': False,
        },
    })

    assert saved['source_creator'] == 'Cartographer Guild'
    assert saved['license_label'] == 'Licensed purchase'
    assert saved['pack_name'] == 'Vault of Dungeons'
    assert saved['asset_source_type'] == 'manual_import'
    assert saved['asset_status'] == 'ready'
    assert saved['source']['is_imported'] is True
    assert saved['source']['is_manual_import'] is True
    assert saved['source']['is_premium_manual_import'] is True
    assert saved['source']['origin_category'] == 'licensed_attributed'
    assert saved['content_origin']['label'] == 'Licensed / Attributed'
    assert saved['attribution']['creator'] == 'Cartographer Guild'
    assert saved['attribution']['license_label'] == 'Licensed purchase'
    assert saved['quality']['has_full_asset'] is True
    assert saved['quality']['has_preview'] is True
    assert saved['quality']['has_thumbnail'] is True
    assert saved['is_stub'] is False


def test_search_maps_supports_metadata_filters_and_collection_ranking(tmp_path, monkeypatch):
    db_path = tmp_path / 'maps.db'
    meta_dir = tmp_path / 'library_meta'

    def temp_get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(map_library, 'get_conn', temp_get_conn)
    monkeypatch.setattr(map_library, 'MAP_LIBRARY_META_DIR', meta_dir)
    monkeypatch.setattr(map_library, 'sync_map_imports', lambda **kwargs: {'imported': 0, 'duplicates': 0, 'broken': 0, 'packs': []})
    monkeypatch.setattr(map_library, '_MAP_LIBRARY_DB_READY', False)
    monkeypatch.setattr(map_library, '_MAP_LIBRARY_DB_INITIALIZING', False)

    map_library.save_map({
        'id': 'open-featured-forest',
        'title': 'Forest Road Ambush',
        'description': 'Curated open-content forest battlemap.',
        'source_type': 'built_in',
        'asset_source_type': 'open',
        'source_creator': 'Open Mapper',
        'license_label': 'CC-BY 4.0',
        'pack_name': 'Starter Forest Pack',
        'terrain': 'forest',
        'build_type': 'road',
        'grid_type': 'square',
        'scale_label': '5 ft',
        'is_pinned': True,
        'full_map_url': '/api/maps/assets/builtin/forest-road.png',
        'thumbnail_url': '/api/maps/assets/builtin/forest-road-thumb.webp',
        'preview_url': '/api/maps/assets/builtin/forest-road-preview.webp',
        'tags': ['forest', 'road', 'ambush'],
    })
    map_library.save_map({
        'id': 'custom-uploaded-wharf',
        'title': 'Harbor Wharf Custom',
        'description': 'User-custom upload for session prep.',
        'source_type': 'uploaded',
        'asset_source_type': 'manual_import',
        'terrain': 'coastal',
        'full_map_url': '/static/user_uploads/maps/wharf.png',
        'thumbnail_url': '/static/user_uploads/maps/wharf.png',
        'preview_url': '/static/user_uploads/maps/wharf.png',
        'tags': ['harbor', 'custom'],
    })
    map_library.save_map({
        'id': 'premium-forest-vault',
        'title': 'Forest Vault Assault',
        'description': 'Premium imported forest map.',
        'source_type': 'imported',
        'asset_source_type': 'manual_import',
        'source_creator': 'Cartographer Guild',
        'license_label': 'Licensed purchase',
        'pack_name': 'Vault of Dungeons',
        'terrain': 'forest',
        'build_type': 'ruins',
        'grid_type': 'square',
        'scale_label': '5 ft',
        'full_map_url': '/api/maps/assets/builtin/forest-vault.png',
        'thumbnail_url': '/api/maps/assets/builtin/forest-vault-thumb.webp',
        'preview_url': '/api/maps/assets/builtin/forest-vault-preview.webp',
        'tags': ['forest', 'vault'],
    })
    map_library.save_map({
        'id': 'stub-forest-draft',
        'title': 'Forest Draft Stub',
        'description': 'Stub draft map that should stay hidden by default.',
        'source_type': 'generated',
        'asset_source_type': 'generated',
        'terrain': 'forest',
        'full_map_url': '/api/maps/assets/builtin/forest-draft.png',
        'thumbnail_url': '/api/maps/assets/builtin/forest-draft-thumb.webp',
        'preview_url': '/api/maps/assets/builtin/forest-draft-preview.webp',
        'metadata_json': {'availability': 'ready', 'stub': True},
        'tags': ['forest', 'draft'],
    })

    premium = map_library.search_maps({'pack_name': 'Vault of Dungeons', 'asset_source_type': 'manual_import'})
    assert premium['total'] == 1
    assert premium['items'][0]['id'] == 'premium-forest-vault'

    open_only = map_library.search_maps({'open_content_only': True})
    assert open_only['total'] == 1
    assert open_only['items'][0]['id'] == 'open-featured-forest'

    default_results = map_library.search_maps({'q': 'forest', 'include_collections': True})
    ids = [item['id'] for item in default_results['items']]
    assert 'stub-forest-draft' not in ids
    assert default_results['items'][0]['id'] == 'open-featured-forest'
    assert default_results['collections']['featured'][0]['id'] == 'open-featured-forest'
    assert any(item['id'] == 'open-featured-forest' for item in default_results['collections']['quickstart'])

    custom_only = map_library.search_maps({'content_origin_category': 'user_custom'})
    assert custom_only['total'] == 1
    assert custom_only['items'][0]['id'] == 'custom-uploaded-wharf'
