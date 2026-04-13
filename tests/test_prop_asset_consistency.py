import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PROP_PATHS = {
    'barrel': '/static/assets/props/barrel.png',
    'campfire': '/static/assets/props/campfire.png',
    'door': '/static/assets/props/door.png',
    'table': '/static/assets/props/table.png',
    'torch': '/static/assets/props/torch.png',
    'bookshelf': '/static/assets/props/bookshelf.png',
    'chest': '/static/assets/props/chest_closed.png',
    'crate': '/static/assets/props/crate_topdown.png',
    'guild_board': '/static/assets/props/guild_board.png',
    'mimic': '/static/assets/props/mimic_revealed.png',
    'shop': '/static/assets/props/shop_stall.png',
}

MANIFEST_IDS = {
    'barrel': 'prop_barrel',
    'campfire': 'prop_campfire',
    'door': 'prop_door',
    'table': 'prop_table',
    'torch': 'prop_torch',
    'bookshelf': 'prop_bookshelf',
    'chest': 'prop_chest',
    'crate': 'prop_crate',
    'guild_board': 'guild_board',
    'mimic': 'mimic',
    'shop': 'prop_shop_front',
}


def _extract_js_object_entries(text: str, marker: str) -> dict[str, str]:
    start = text.index(marker)
    brace_start = text.index('{', start)
    depth = 0
    end = brace_start
    for idx in range(brace_start, len(text)):
        char = text[idx]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                end = idx
                break
    block = text[brace_start + 1:end]
    return dict(re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*'([^']+)'", block))


def test_vtt_single_props_are_lowercase_only_for_replaced_files():
    props_dir = ROOT / 'vtt_single_props'
    files = [path.name for path in props_dir.iterdir() if path.is_file()]
    lowered = {}
    for name in files:
        key = name.lower()
        assert key not in lowered, f'Case-colliding prop files found: {lowered[key]!r} and {name!r}'
        lowered[key] = name
    for name in ['barrel.png', 'campfire.png', 'door.png', 'table.png', 'torch.png']:
        assert (props_dir / name).is_file(), f'Missing canonical runtime prop file: {name}'


def test_prop_paths_match_manifest_runtime_and_editor():
    manifest = json.loads((ROOT / 'client/static/assets/manifest.json').read_text(encoding='utf-8'))
    manifest_assets = {asset['id']: asset for asset in manifest['assets'] if asset.get('id')}

    runtime_map = _extract_js_object_entries(
        (ROOT / 'client/static/js/assets/dnd_assets.js').read_text(encoding='utf-8'),
        'const _propImageOverrides = Object.freeze('
    )
    editor_map = _extract_js_object_entries(
        (ROOT / 'client/templates/play.html').read_text(encoding='utf-8'),
        'function getNativeEditorPropAssetFile(kind) {'
    )

    for kind, expected_path in EXPECTED_PROP_PATHS.items():
        manifest_id = MANIFEST_IDS[kind]
        asset = manifest_assets[manifest_id]
        assert asset['file'] == expected_path, f'{manifest_id} file drifted from expected prop path'
        assert asset['thumbnail'] == expected_path, f'{manifest_id} thumbnail drifted from expected prop path'
        assert runtime_map[kind] == expected_path, f'runtime prop map drifted for {kind}'
        assert editor_map[kind] == expected_path, f'editor prop map drifted for {kind}'
