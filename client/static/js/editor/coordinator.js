(function(){
  const AppEditorCoordinator = {
    handlePointerDown(env, wx, wy){
      if (!env) return false;
      const layer = String(env.editorActiveLayer || 'terrain');
      if (layer === 'walls') { env.handleEditorWallClick(wx, wy); return true; }
      if (layer === 'props') { env.handleEditorPropMouseDown(wx, wy); return true; }
      if (layer === 'paths') { env.handleEditorPathClick(wx, wy); return true; }
      if (layer === 'markers') { env.handleEditorMarkerClick(wx, wy); return true; }
      env.editorPainting = true;
      env.editorMousePrevWorld = null;
      env.applyEditorBrush(wx, wy);
      return true;
    },
    handlePointerMove(env, wx, wy){
      if (!env) return false;
      const layer = String(env.editorActiveLayer || 'terrain');
      if (env.editorPainting) {
        env.applyEditorBrush(wx, wy);
        return true;
      }
      if (layer === 'markers' && env.editorMarkerDrag && env.updateEditorMarkerDrag(wx, wy)) return true;
      if (layer === 'markers' && env.editorLabelDrag && env.updateEditorLabelDrag(wx, wy)) return true;
      if (layer === 'props' && env.editorPropDragId && env.updateEditorPropDrag(wx, wy)) return true;
      if (layer === 'walls') env.updateEditorWallHover(wx, wy);
      if (layer === 'props') env.updateEditorPropHover(wx, wy);
      return false;
    },
    handlePointerUp(env){
      if (!env) return { handled:false };
      if (env.editorMarkerDrag) {
        const wasMoved = !!env.editorMarkerDrag.moved;
        const markerId = String(env.editorMarkerDrag.id || '');
        env.finishEditorMarkerDrag();
        if (!wasMoved) {
          env.ensureEditorMarkersLoaded();
          const item = (env.currentMarkerItems() || []).find(m => String(m.id || '') === markerId);
          if (item) env.openEditorMarkerModal('edit', item, null);
        }
        return { handled:true };
      }
      if (env.editorLabelDrag) {
        const wasMoved = !!env.editorLabelDrag.moved;
        const labelId = String(env.editorLabelDrag.id || '');
        env.finishEditorLabelDrag();
        if (!wasMoved) {
          env.ensureEditorLabelsLoaded();
          const item = (env.currentLabelItems() || []).find(m => String(m.id || '') === labelId);
          if (item) env.openEditorLabelModal('edit', item, null);
        }
        return { handled:true };
      }
      return { handled:false };
    },
    finalizePointerCommit(env){
      if (!env) return false;
      let handled = false;
      if (env.editorMarkerDrag) {
        env.finishEditorMarkerDrag();
        handled = true;
      }
      if (env.editorLabelDrag) {
        env.finishEditorLabelDrag();
        handled = true;
      }
      if (env.editorPropDragId) {
        env.finishEditorPropDrag();
        handled = true;
      }
      if (env.editorPainting) {
        env.editorPainting = false;
        env.editorMousePrevWorld = null;
        env.saveEditorLayer(true);
        handled = true;
      }
      return handled;
    },
  };
  window.AppEditorCoordinator = AppEditorCoordinator;
})();
