# Live Sync Validation Check — 2026-03-27

## Scope
This validation run focused on automated sync and role-behavior guardrails for DM, player, and viewer paths.

## Runtime source-of-truth files consulted
- `main.py`
- `server/handlers/__init__.py`
- `client/templates/play.html`
- `docs/repo-map.md`
- `docs/system-audit-20260320.md`

## Commands run

1. `python -m pytest tests/test_session_authority_and_scene_maps.py -v --tb=short`
   - Result: **pass** (3 passed)

2. `python -m pytest tests/test_player_permissions.py -v --tb=short`
   - Result: **pass** (11 passed)

3. `python -m pytest tests/test_refactor.py -v --tb=short`
   - Result: **pass** (177 passed)

4. `python -m pytest tests/test_campaign_roundtrip.py -v --tb=short`
   - Result: **pass** (3 passed)

5. `python -m pytest tests/ -v --tb=short`
   - Result: **fail** (354 passed, 2 failed)
   - Failing tests:
     - `tests/test_refactor.py::test_asset_upload_single_png`
       - Expected asset name `Test Floor`, got `Test Terrain`.
     - `tests/test_refactor.py::test_terrain_upload_assigns_terrain_id`
       - Expected second upload to have larger `terrain_id`; observed `2 > 3` assertion failure.

## Interpretation
- Core DM/player/viewer sync and authority checks passed in targeted suites.
- The full-suite run exposed two asset-upload-related failures, indicating cross-suite state coupling (or shared upload state behavior) when running all tests together.
- A clean “all green” full validation for live sync readiness is **not** achieved until those full-suite failures are resolved.
