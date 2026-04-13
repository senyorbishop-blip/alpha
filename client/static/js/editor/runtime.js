/**
 * editor/runtime.js — dormant env-injected editor runtime module.
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
  const AppEditorRuntime = {
    updateEditorMapStyleReadout(env){
      const val = Number(env.document.getElementById('editor-world-opacity')?.value || 82);
      const label = env.document.getElementById('editor-world-opacity-val');
      if (label) label.textContent = String(Math.round(val));
    },
    refreshEditorMapStyleControls(env){
      const note = env.document.getElementById('editor-focus-note');
      if (note) {
        note.textContent = env.editorMapContextKey() === 'world'
          ? 'World-map editing is stripped right back for now. The main world map stays visible while tactical POI building is the current focus.'
          : 'Tactical POI building is the current focus. Use terrain, walls, and the small prop set to build local encounters.';
      }
      const brush = env.document.getElementById('editor-brush-size');
      if (brush) brush.max = '12';
      if (env.state && env.state.editorTerrainCache) env.state.editorTerrainCache.dirty = true;
    },
    saveEditorMapStyleSettings(env, debounceOnly){
      if (env.role !== 'dm') return;
      const doSave = () => {
        const settings = JSON.parse(JSON.stringify(env.currentMapSettings() || {}));
        settings.editor_mode = 'tactical';
        settings.world = { ...(settings.world || {}), show_grid: false, terrain_opacity: 1 };
        env.sendWS({ type: 'map_settings_save', payload: { map_context: env.editorMapContextKey(), settings } });
        if (env.state && env.state.editorTerrainCache) env.state.editorTerrainCache.dirty = true;
        env.drawFrame();
      };
      if (debounceOnly) {
        clearTimeout(env.state.editorMapStyleSaveTimer);
        env.setEditorMapStyleSaveTimer(setTimeout(doSave, 180));
      } else {
        doSave();
      }
    },
    setEditorMapMode(env, mode){
      if (env.role !== 'dm') return;
      const settings = JSON.parse(JSON.stringify(env.currentMapSettings() || {}));
      settings.editor_mode = 'tactical';
      settings.world = { ...(settings.world || {}), show_grid: false, terrain_opacity: 1 };
      env.applyMapSettingsAll({ ...(env.state.mapSettingsAll || {}), [env.editorMapContextKey()]: settings });
      this.refreshEditorMapStyleControls(env);
      this.saveEditorMapStyleSettings(env);
      env.drawFrame();
    },
    updateEditorWeatherReadout(env){
      const intensity = Number(env.document.getElementById('editor-weather-intensity')?.value || 0.5);
      const wind = Number(env.document.getElementById('editor-weather-wind')?.value || 0.2);
      const iLabel = env.document.getElementById('editor-weather-intensity-val');
      const wLabel = env.document.getElementById('editor-weather-wind-val');
      if (iLabel) iLabel.textContent = intensity.toFixed(2);
      if (wLabel) wLabel.textContent = wind.toFixed(2);
    },
    refreshEditorWeatherControls(env, forceToast){
      const settings = env.currentMapSettings();
      const weather = settings.weather || {};
      const enabledEl = env.document.getElementById('editor-weather-enabled');
      const typeEl = env.document.getElementById('editor-weather-type');
      const intensityEl = env.document.getElementById('editor-weather-intensity');
      const windEl = env.document.getElementById('editor-weather-wind');
      if (enabledEl) enabledEl.checked = !!weather.enabled;
      if (typeEl) typeEl.value = String(weather.type || 'none');
      if (intensityEl) intensityEl.value = Number(weather.intensity ?? 0.5).toFixed(2);
      if (windEl) windEl.value = Number(weather.wind ?? 0.2).toFixed(2);
      this.updateEditorWeatherReadout(env);
      if (forceToast) env.showToast("Loaded this map's saved weather settings.");
    },
    saveEditorWeatherSettings(env, debounceOnly){
      if (env.role !== 'dm') return;
      if (env.state.weatherSettingsSaveTimer) clearTimeout(env.state.weatherSettingsSaveTimer);
      const doSave = () => {
        const settings = JSON.parse(JSON.stringify(env.currentMapSettings() || {}));
        settings.weather = {
          enabled: !!env.document.getElementById('editor-weather-enabled')?.checked,
          type: String(env.document.getElementById('editor-weather-type')?.value || 'none'),
          intensity: Number(env.document.getElementById('editor-weather-intensity')?.value || 0.5),
          wind: Number(env.document.getElementById('editor-weather-wind')?.value || 0.2),
        };
        env.sendWS({ type: 'map_settings_save', payload: { map_context: env.editorMapContextKey(), settings } });
      };
      if (debounceOnly) env.setWeatherSettingsSaveTimer(setTimeout(doSave, 180));
      else doSave();
    },
    saveEditorActiveLayer(env, silent){
      if (env.activeLayer === 'walls') env.saveEditorWalls(silent);
      else if (env.activeLayer === 'props') env.saveEditorProps(silent);
      else if (env.activeLayer === 'paths') env.saveEditorPaths(silent);
      else if (env.activeLayer === 'markers') { env.saveEditorMarkers(silent); env.saveEditorLabels(true); }
      else env.saveEditorLayer(silent);
    },
    clearEditorActiveLayer(env){
      if (env.activeLayer === 'walls') env.clearEditorWalls();
      else if (env.activeLayer === 'props') env.clearEditorProps();
      else if (env.activeLayer === 'paths') env.clearEditorPaths();
      else if (env.activeLayer === 'markers') env.clearEditorMarkers();
      else env.clearEditorLayer();
    },
  };
  window.AppEditorRuntime = AppEditorRuntime;
})();
