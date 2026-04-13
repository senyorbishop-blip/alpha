(function(){
  const MARKER_KINDS = ['city','town','settlement','ruin','shop','tavern','camp','blacksmith','market','castle','harbor','forest','mountain','landmark','custom_asset'];
  const AppEditorPoi = {
    editorLinkablePoisForContext(env){
      const currentContext = env.currentPoi ? (env.currentPoi.id || '__local__') : 'world';
      return Object.values(env.pois || {}).filter(p => p && (p.map_context || 'world') === currentContext && p.local_map_url).sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
    },
    editorMarkerModalKinds(){ return MARKER_KINDS.slice(); },
    fillEditorMarkerModalKinds(env, selected){
      const sel = document.getElementById('editor-marker-modal-kind');
      if (!sel) return;
      const current = String(selected || env.editorMarkerKind || 'city').toLowerCase();
      sel.replaceChildren(...this.editorMarkerModalKinds().map(kind => {
        const label = kind.replace(/_/g,' ').split(' ').map(part => part ? (part.charAt(0).toUpperCase() + part.slice(1)) : '').join(' ');
        const opt = document.createElement('option');
        opt.value = kind;
        opt.textContent = label;
        return opt;
      }));
      sel.value = current;
    },
    fillEditorMarkerModalPois(env, selectedPoiId){
      const sel = document.getElementById('editor-marker-modal-poi');
      if (!sel) return;
      const linkable = this.editorLinkablePoisForContext(env);
      const noneOpt = document.createElement('option');
      noneOpt.value = '';
      noneOpt.textContent = 'No linked local map';
      const poiOpts = linkable.map(poi => {
        const opt = document.createElement('option');
        opt.value = poi.id;
        opt.textContent = poi.name || 'POI';
        return opt;
      });
      sel.replaceChildren(noneOpt, ...poiOpts);
      sel.value = selectedPoiId || '';
    },
    showEditorMarkerLinkHelp(env){
      const linkable = this.editorLinkablePoisForContext(env);
      if (!linkable.length) {
        env.showToast('No local-map POIs on this map yet. Create a POI with a local map first, then place a marker and link it.');
        return;
      }
      env.showToast(`Linkable POIs on this map: ${linkable.map(p => p.name).slice(0, 4).join(', ')}${linkable.length > 4 ? '…' : ''}`);
    },
  };
  window.AppEditorPoi = AppEditorPoi;
})();
