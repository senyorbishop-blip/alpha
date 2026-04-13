/**
 * editor/state.js — dormant env-injected editor state module.
 *
 * Stage 4 note:
 * - `client/templates/play.html` still owns the live editor runtime state and
 *   save/apply flow used at runtime.
 * - `client/static/js/editor/serialization.js` remains the authoritative map
 *   document serializer.
 * - This module is preserved from the modularization effort but is not loaded by
 *   `play.html` today.
 */
(function(){
  const AppEditorState = {
    editorMapContextKey(env){
      const poi = env && env.currentPoi;
      return (poi && poi.id) ? poi.id : 'world';
    },
    normalizeEditorBool(v){
      if (typeof v === 'boolean') return v;
      if (typeof v === 'number') return v !== 0;
      const s = String(v || '').trim().toLowerCase();
      return s === '1' || s === 'true' || s === 'yes' || s === 'on';
    },
    setEditorMode(env, mode){
      const allowed = new Set(['paint','erase']);
      env.editorPaintMode.value = allowed.has(mode) ? mode : 'paint';
      document.getElementById('editor-tool-paint')?.classList.toggle('active', env.editorPaintMode.value === 'paint');
      document.getElementById('editor-tool-erase')?.classList.toggle('active', env.editorPaintMode.value === 'erase');
      const help = document.getElementById('editor-brush-help');
      const blendWrap = document.getElementById('editor-blend-strength-wrap');
      const forestWrap = document.getElementById('editor-forest-density-wrap');
      const mountainWrap = document.getElementById('editor-mountain-direction-wrap');
      if (blendWrap) blendWrap.style.display = 'none';
      if (forestWrap) forestWrap.style.display = 'none';
      if (mountainWrap) mountainWrap.style.display = 'none';
      if (help) help.textContent = env.editorPaintMode.value === 'erase'
        ? 'Erase clears tactical terrain cells from the current POI map.'
        : 'Draw paints the selected tactical terrain onto the current POI map.';
    },
    setEditorLayerMode(env, layer){
      const allowed = new Set(['terrain','walls','props']);
      env.editorActiveLayer.value = allowed.has(layer) ? layer : 'terrain';
      document.getElementById('editor-layer-terrain')?.classList.toggle('active', env.editorActiveLayer.value === 'terrain');
      document.getElementById('editor-layer-walls')?.classList.toggle('active', env.editorActiveLayer.value === 'walls');
      document.getElementById('editor-layer-props')?.classList.toggle('active', env.editorActiveLayer.value === 'props');
      const terrainSection = document.getElementById('editor-terrain-section');
      const brushSection = document.getElementById('editor-brush-section');
      const wallHelp = document.getElementById('editor-wall-help');
      const propSection = document.getElementById('editor-prop-section');
      const pathSection = document.getElementById('editor-path-section');
      const markerSection = document.getElementById('editor-marker-section');
      if (terrainSection) terrainSection.style.display = env.editorActiveLayer.value === 'terrain' ? '' : 'none';
      if (brushSection) brushSection.style.display = env.editorActiveLayer.value === 'terrain' ? '' : 'none';
      if (wallHelp) wallHelp.style.display = env.editorActiveLayer.value === 'walls' ? 'block' : 'none';
      if (propSection) propSection.style.display = env.editorActiveLayer.value === 'props' ? 'block' : 'none';
      if (pathSection) pathSection.style.display = 'none';
      if (markerSection) markerSection.style.display = 'none';
      env.editorWallDraftStart.value = null;
      env.editorWallHoverIndex.value = -1;
      env.editorPropHoverIndex.value = -1;
      env.editorPropDragId.value = null;
      if (env.editorActiveLayer.value !== 'props') env.handlers.propPopupClose();
      try {
        env.handlers.refreshEditorWeatherControls();
        env.handlers.refreshEditorMapStyleControls();
      } catch (err) {
        console.warn('Skipping weather/style control refresh during early init.', err);
      }
    },
    setEditorWallTool(env, tool){
      env.editorWallTool.value = (tool === 'room' || tool === 'door' || tool === 'opening') ? tool : 'segment';
      document.getElementById('editor-wall-tool-segment')?.classList.toggle('active', env.editorWallTool.value === 'segment');
      document.getElementById('editor-wall-tool-room')?.classList.toggle('active', env.editorWallTool.value === 'room');
      document.getElementById('editor-wall-tool-door')?.classList.toggle('active', env.editorWallTool.value === 'door');
      document.getElementById('editor-wall-tool-opening')?.classList.toggle('active', env.editorWallTool.value === 'opening');
      const note = document.getElementById('editor-wall-mode-note');
      if (note) {
        note.textContent = env.editorWallTool.value === 'room'
          ? 'Room mode: click the first corner, then click the opposite corner to place a snapped 4-wall room.'
          : (env.editorWallTool.value === 'door'
            ? 'Door mode: click a hovered horizontal or vertical wall to cut a one-square gap and place a saved door marker.'
            : (env.editorWallTool.value === 'opening'
              ? 'Opening mode: click a hovered horizontal or vertical wall to cut a one-square gap and place a saved opening marker.'
              : 'Segment mode: click once to start a wall, then click again to finish. Straight Assist locks new segments to horizontal or vertical.'));
      }
      env.editorWallDraftStart.value = null;
      env.editorWallHoverIndex.value = -1;
    },
    setEditorWallStraightAssist(env, enabled){ env.editorWallStraightAssist.value = !!enabled; },
    setEditorPropRotation(env, v){
      const normalized = Number.isFinite(Number(v)) ? Number(v) : 0;
      env.editorPropRotation.value = ((normalized % 360) + 360) % 360;
      const label = document.getElementById('editor-prop-rotation-val');
      if (label) label.textContent = `${env.editorPropRotation.value}°`;
    },
    rotateEditorPropSelection(env, delta){
      const next = ((Number(env.editorPropRotation.value) || 0) + (Number(delta) || 0)) % 360;
      return this.setEditorPropRotation(env, next);
    },
    setEditorPropKind(env, kind){
      const normalized = String(kind || '').toLowerCase();
      env.editorPropKind.value = env.editorBuildPaletteKinds.has(normalized) ? normalized : 'barrel';
      const suggested = Math.max(1, Math.min(4, Number(env.editorPropRecommendedSize[env.editorPropKind.value]) || env.editorPropSize.value || 1));
      if (env.editorPropSize.value !== suggested) this.setEditorPropSize(env, suggested);
      document.querySelectorAll('.editor-prop-btn').forEach(btn => {
        btn.classList.toggle('active', String(btn.dataset.prop || '') === env.editorPropKind.value);
      });
    },
    setEditorPropSize(env, v){
      env.editorPropSize.value = Math.max(1, Math.min(4, Number(v) || 1));
      const label = document.getElementById('editor-prop-size-val');
      if (label) label.textContent = String(env.editorPropSize.value);
    },
    setEditorChestHidden(env, v){ env.editorChestHidden.value = !!v; },
    setEditorTerrain(env, terrain){
      const selected = Number(terrain) || 1;
      env.editorTerrain.value = env.editorAllowedTerrainPalette.has(selected) ? selected : 1;
      document.querySelectorAll('.editor-terrain-btn').forEach(btn => {
        btn.classList.toggle('active', Number(btn.dataset.terrain) === env.editorTerrain.value);
      });
    },
    setEditorBrush(env, v){
      const maxBrush = 12;
      env.editorBrush.value = Math.max(1, Math.min(maxBrush, Number(v) || 1));
      const label = document.getElementById('editor-brush-val');
      if (label) label.textContent = String(env.editorBrush.value);
    },
    setEditorBlendStrength(env, v){
      env.editorBlendStrength.value = Math.max(0.25, Math.min(1, (Number(v) || 65) / 100));
      const label = document.getElementById('editor-blend-strength-val');
      if (label) label.textContent = String(Math.round(env.editorBlendStrength.value * 100));
    },
    setEditorForestDensity(env, v){
      env.editorForestDensity.value = Math.max(0.2, Math.min(1, (Number(v) || 70) / 100));
      const label = document.getElementById('editor-forest-density-val');
      if (label) label.textContent = String(Math.round(env.editorForestDensity.value * 100));
    },
    setEditorMountainDirection(env, dir){
      env.editorMountainDirection.value = ['auto','ew','ns','nesw','nwse'].includes(String(dir || '')) ? String(dir) : 'auto';
      document.querySelectorAll('.editor-mountain-dir-btn').forEach(btn => btn.classList.toggle('active', String(btn.dataset.dir || '') === env.editorMountainDirection.value));
    },
    setEditorPathKind(env, kind){
      env.editorPathKind.value = kind === 'river' ? 'river' : 'road';
      document.querySelectorAll('.editor-path-kind-btn').forEach(btn => btn.classList.toggle('active', String(btn.dataset.pathKind || '') === env.editorPathKind.value));
    },
    setEditorPathWidth(env, v){
      env.editorPathWidth.value = Math.max(0.5, Math.min(3, Number(v) || 1.2));
      const label = document.getElementById('editor-path-width-val');
      if (label) label.textContent = env.editorPathWidth.value.toFixed(1);
    },
    setEditorMarkerKind(env, kind){
      const allowed = new Set(['city','town','settlement','ruin','shop','tavern','camp','landmark','blacksmith','market','castle','harbor','forest','mountain']);
      env.editorMarkerKind.value = allowed.has(String(kind || '').toLowerCase()) ? String(kind).toLowerCase() : 'city';
      document.querySelectorAll('.editor-marker-kind-btn').forEach(btn => btn.classList.toggle('active', String(btn.dataset.markerKind || '') === env.editorMarkerKind.value));
    },
  };
  window.AppEditorState = AppEditorState;
})();
