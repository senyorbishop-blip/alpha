(function(){
  const AppEditorPanels = {
    syncPanelSections(env){
      const activeLayer = String(env.getActiveLayer() || 'terrain');
      const terrainSection = env.document.getElementById('editor-terrain-section');
      const brushSection = env.document.getElementById('editor-brush-section');
      const wallHelp = env.document.getElementById('editor-wall-help');
      const propSection = env.document.getElementById('editor-prop-section');
      const pathSection = env.document.getElementById('editor-path-section');
      const markerSection = env.document.getElementById('editor-marker-section');
      if (terrainSection) terrainSection.style.display = activeLayer === 'terrain' ? '' : 'none';
      if (brushSection) brushSection.style.display = activeLayer === 'terrain' ? '' : 'none';
      if (wallHelp) wallHelp.style.display = activeLayer === 'walls' ? 'block' : 'none';
      if (propSection) propSection.style.display = activeLayer === 'props' ? 'block' : 'none';
      if (pathSection) pathSection.style.display = 'none';
      if (markerSection) markerSection.style.display = 'none';
    },
    refreshPanelControls(env, forceToast){
      env.handlers.refreshMapStyleControls();
      env.handlers.refreshWeatherControls(forceToast);
      this.syncPanelSections(env);
    },
    applyPanelDefaults(env){
      env.handlers.setMode('paint');
      env.handlers.setTerrain(1);
      env.handlers.setLayerMode('terrain');
      env.handlers.setWallTool('segment');
      env.handlers.setWallStraightAssist(true);
      env.handlers.setPropKind('crate');
      env.handlers.setPropRotation(0);
      env.handlers.setPropSize(1);
      env.handlers.setPathKind('road');
      env.handlers.setPathWidth(1.2);
      env.handlers.setMarkerKind('city');
      env.handlers.refreshMapStyleControls();
      this.syncPanelSections(env);
    },
  };
  window.AppEditorPanels = AppEditorPanels;
})();
