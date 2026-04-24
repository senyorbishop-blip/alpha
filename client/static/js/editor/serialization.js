/**
 * editor/serialization.js — authoritative editor map document serializer.
 *
 * Stage 4 note:
 * - `window.EditorMapDocument` is the live source of truth for normalizing and
 *   building serialized map documents.
 * - It intentionally reads from the live editor globals still owned by
 *   `client/templates/play.html` (`_editorLayersAll`, `_editorWallsAll`, etc.).
 * - Treat editor runtime/state modules as non-authoritative until the page
 *   explicitly migrates editor ownership to them.
 */
(function(){
  const VERSION = 1;
  const clone = (value) => {
    if (value == null) return value;
    try { return JSON.parse(JSON.stringify(value)); } catch (_) { return value; }
  };
  const safeCtx = (value) => String(value || 'world').trim().slice(0, 80) || 'world';

  function normalizeMapDocument(raw, mapContext){
    const src = raw && typeof raw === 'object' ? raw : {};
    const layers = src.layers && typeof src.layers === 'object' ? src.layers : {};
    const terrain = layers.terrain && typeof layers.terrain === 'object' ? layers.terrain : {};
    return {
      version: VERSION,
      map_context: safeCtx(src.map_context || mapContext),
      map_type: String(src.map_type || src.type || ((src.settings || {}).editor_mode || 'tactical')).toLowerCase() === 'world' ? 'world' : 'tactical',
      grid: clone(src.grid && typeof src.grid === 'object' ? src.grid : { tile_size_px: 64, feet_per_tile: 5, snap: true }),
      assets: clone(src.assets && typeof src.assets === 'object' ? src.assets : {}),
      settings: clone(src.settings && typeof src.settings === 'object' ? src.settings : {}),
      meta: clone(src.meta && typeof src.meta === 'object' ? src.meta : {}),
      layers: {
        terrain: { cells: clone(terrain.cells && typeof terrain.cells === 'object' ? terrain.cells : {}) },
        walls: Array.isArray(layers.walls) ? clone(layers.walls) : [],
        props: Array.isArray(layers.props) ? clone(layers.props) : [],
        paths: Array.isArray(layers.paths) ? clone(layers.paths) : [],
        labels: Array.isArray(layers.labels) ? clone(layers.labels) : [],
        markers: Array.isArray(layers.markers) ? clone(layers.markers) : [],
        lights: Array.isArray(layers.lights) ? clone(layers.lights) : [],
        hazards: Array.isArray(layers.hazards) ? clone(layers.hazards) : [],
      }
    };
  }

  function buildMapDocument(mapContext, runtime){
    const rt = runtime || window;
    const ctx = safeCtx(mapContext);
    const settingsAll = rt._mapSettingsAll || {};
    const settings = clone(settingsAll[ctx] || {});
    const gridSizePx = Math.max(16, Math.min(256, Number((settings.grid || {}).size_px || 64))) || 64;
    const mapType = String(settings.editor_mode || 'tactical').toLowerCase() === 'world' ? 'world' : 'tactical';
    let backgroundUrl = null;
    if (ctx === 'world') {
      backgroundUrl = rt._worldMapImageUrl || rt.mapImageUrl || null;
    } else {
      const poi = (rt.pois || {})[ctx] || null;
      backgroundUrl = poi && poi.local_map_url ? poi.local_map_url : null;
    }
    const hazards = Object.values(rt.hazardZones || {}).filter(z => z && String(z.map_context || 'world') === ctx);
    return normalizeMapDocument({
      map_context: ctx,
      map_type: mapType,
      grid: { tile_size_px: gridSizePx, feet_per_tile: 5, snap: true },
      assets: { background_url: backgroundUrl },
      settings,
      meta: { schema: 'casual-dnd.map-document', generated_on_client: true },
      layers: {
        terrain: { cells: clone((rt._editorLayersAll || {})[ctx] || {}) },
        walls: clone((rt._editorWallsAll || {})[ctx] || []),
        props: clone((rt._editorPropsAll || {})[ctx] || []),
        paths: clone((rt._editorPathsAll || {})[ctx] || []),
        labels: clone((rt._editorLabelsAll || {})[ctx] || []),
        markers: clone((rt._editorMarkersAll || {})[ctx] || []),
        lights: clone((rt._editorLightsAll || {})[ctx] || []),
        hazards: clone(hazards),
      }
    }, ctx);
  }

  function collectMapDocuments(runtime){
    const rt = runtime || window;
    const contexts = new Set(['world']);
    ['_editorLayersAll','_editorWallsAll','_editorPropsAll','_editorPathsAll','_editorLabelsAll','_editorMarkersAll','_editorLightsAll','_mapSettingsAll'].forEach((key) => {
      const value = rt[key] || {};
      Object.keys(value || {}).forEach((ctx) => contexts.add(safeCtx(ctx)));
    });
    Object.values(rt.hazardZones || {}).forEach((zone) => contexts.add(safeCtx(zone && zone.map_context)));
    Object.values(rt.pois || {}).forEach((poi) => { if (poi && poi.local_map_url && poi.id) contexts.add(safeCtx(poi.id)); });
    const docs = {};
    Array.from(contexts).sort((a,b)=> (a==='world'?-1:b==='world'?1:a.localeCompare(b))).forEach((ctx) => {
      docs[ctx] = buildMapDocument(ctx, rt);
    });
    return docs;
  }

  window.EditorMapDocument = {
    VERSION,
    normalizeMapDocument,
    buildMapDocument,
    collectMapDocuments,
  };
})();
