# Map Library Import Pipeline

## Storage layout

The runtime map library now uses persistent data directories under `DATA_DIR/maps/`:

- `import/` — drop legal open/free packs, loose image folders, or ZIP files here.
- `builtin/` — normalized full-resolution imported map files.
- `builtin/thumbnails/` — generated small WebP thumbnails.
- `builtin/previews/` — generated medium WebP previews.
- `generated/` — archive extraction/cache workspace.
- `manifests/` — one manifest JSON per imported map.
- `library_meta/` — serialized DB/library metadata snapshots.

## Pack manifest schema

Place `pack.json` (or `manifest.json`) next to a supplied pack. Supported fields:

```json
{
  "id": "open-starter-pack",
  "pack_name": "Open Starter Pack",
  "source_creator": "Creator name",
  "source_type": "open",
  "license_label": "CC-BY 4.0",
  "attribution_text": "Attribution shown in UI/metadata",
  "maps": [
    {
      "id": "forest-road-01",
      "title": "Forest Road Ambush",
      "file_path": "forest_road_ambush.png",
      "map_scope": "battlemap",
      "terrain": "forest",
      "build_type": "road",
      "interior_type": "",
      "image_style": "tactical",
      "grid_type": "square",
      "scale_label": "5 ft",
      "width_cells": 24,
      "height_cells": 18,
      "tags": ["forest", "road", "ambush"],
      "active": true
    }
  ]
}
```

Each imported map is normalized into a per-map manifest in `DATA_DIR/maps/manifests/<id>.json` with these fields:

- `id`
- `title`
- `source_creator`
- `source_type` (`open` | `licensed` | `manual_import`)
- `license_label`
- `map_scope`
- `terrain`
- `build_type`
- `interior_type`
- `image_style`
- `grid_type`
- `scale_label`
- `width_cells`
- `height_cells`
- `tags`
- `file_path`
- `thumbnail_path`
- `preview_path`
- `attribution_text`
- `pack_name`
- `imported_at`
- `checksum`
- `active`

The runtime library API (`/api/maps/library`) now also returns a computed content-origin slice per item:

- `content_origin.category` (`bundled` | `imported` | `user_custom` | `licensed_attributed` | `generated` | `custom`)
- `content_origin.label` (human readable label shown in Map Studio)
- `source.origin_category` / `source.origin_label` mirrors for compatibility with existing clients.

## Open / free pack flow

1. Put the pack folder or ZIP into `DATA_DIR/maps/import/`.
2. Include `pack.json` when possible so creator/license metadata stay explicit.
3. Click **Refresh** in the Library tab, or call `POST /api/maps/library/import`.
4. The importer copies the images into the normalized builtin store, generates thumbnails/previews, writes manifests, and registers only valid entries.

### First-run starter pack behavior

On first run, the importer ensures a minimal `open-starter-pack` exists under `DATA_DIR/maps/import/open-starter-pack/` with attribution metadata so the library does not feel empty in a fresh checkout. Use **Refresh** in Map Studio to force a rescan if needed.

## Manual premium import flow

1. Download the premium pack yourself from the licensed creator.
2. Drop the downloaded folder, ZIP, or loose image files into `DATA_DIR/maps/import/`.
3. Optionally add a `pack.json`, `manifest.json`, `pack.txt`, or `source.txt` file describing creator/license/source type.
4. Refresh/import. These maps are stored as `source_type = imported` in the library, while preserving manifest `source_type = manual_import` metadata.

## Quality control rules

- Legacy `/static/maps/full/*` placeholder seeds are hidden automatically.
- Broken records are archived if the full map, preview, or thumbnail is missing.
- Placeholder/sample/stub-named imports are skipped.
- Duplicate files are skipped using checksum and destination-path checks.
- Discover/Library only show entries with ready assets behind them.
