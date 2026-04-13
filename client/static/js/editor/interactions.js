(function(){
  function setDisplayById(doc, id, value) { const el = doc && typeof doc.getElementById === "function" ? doc.getElementById(id) : null; if (el && el.style) el.style.display = value; return el; }
  const AppEditorInteractions = {
    closeEditorMarkerModal(env){
      if (!env) return;
      env.closeEditorMarkerModal();
    },
    openEditorMarkerModal(env, mode, marker, snapped){
      if (!env || env.ROLE !== 'dm') return;
      const modal = document.getElementById('editor-marker-modal');
      if (!modal) return;
      const isEdit = mode === 'edit' && marker;
      env.editorMarkerModalState = {
        mode: isEdit ? 'edit' : 'create',
        markerId: isEdit ? String(marker.id || '') : '',
        x: isEdit ? Number(marker.x || 0) : Number(snapped?.x || 0),
        y: isEdit ? Number(marker.y || 0) : Number(snapped?.y || 0),
      };
      document.getElementById('editor-marker-modal-title').textContent = isEdit ? 'Edit Marker' : 'Place Marker';
      document.getElementById('editor-marker-modal-save').textContent = isEdit ? 'Save Changes' : 'Save Marker';
      setDisplayById(document, 'editor-marker-modal-delete', isEdit ? '' : 'none');
      env.fillEditorMarkerModalKinds(isEdit ? marker.kind : env.editorMarkerKind);
      env.fillEditorMarkerModalPois(isEdit ? String(marker.linked_poi_id || '') : '');
      const emNEl = document.getElementById('editor-marker-modal-name');
      const emSzEl = document.getElementById('editor-marker-modal-size');
      const emStEl = document.getElementById('editor-marker-modal-style');
      const emAsEl = document.getElementById('editor-marker-modal-asset-scale');
      const emAaEl = document.getElementById('editor-marker-modal-asset-anchor');
      const emAfEl = document.getElementById('editor-marker-modal-asset-footprint');
      if (emNEl)  emNEl.value  = isEdit ? String(marker.name || '') : ((env.editorMarkerKind || 'marker').charAt(0).toUpperCase() + (env.editorMarkerKind || 'marker').slice(1));
      if (emSzEl) emSzEl.value = isEdit ? String(marker.size || 'medium') : 'medium';
      if (emStEl) emStEl.value = isEdit ? String(marker.style || 'round') : 'round';
      if (emAsEl) emAsEl.value = String(Math.max(0.25, Number((isEdit ? marker?.asset_scale : env.getSelectedEditorMarkerAsset?.()?.scale) || 1) || 1));
      if (emAaEl) emAaEl.value = String((isEdit ? marker?.asset_anchor : env.getSelectedEditorMarkerAsset?.()?.anchor) || 'center').toLowerCase() === 'bottom' ? 'bottom' : 'center';
      if (emAfEl) emAfEl.value = String(Math.max(0.5, Number((isEdit ? marker?.asset_footprint : env.getSelectedEditorMarkerAsset?.()?.footprint) || 1) || 1));
      if (typeof window.refreshEditorMarkerCustomFields === 'function') window.refreshEditorMarkerCustomFields();
      modal.classList.add('open');
      setTimeout(() => document.getElementById('editor-marker-modal-name')?.focus(), 20);
    },
    saveEditorMarkerModal(env){
      if (!env || !env.editorMarkerModalState) return;
      env.ensureEditorMarkersLoaded();
      const kind = String(document.getElementById('editor-marker-modal-kind')?.value || env.editorMarkerKind || 'city').toLowerCase();
      const name = String(document.getElementById('editor-marker-modal-name')?.value || '').trim() || (kind.charAt(0).toUpperCase() + kind.slice(1));
      const poiId = String(document.getElementById('editor-marker-modal-poi')?.value || '');
      const size = String(document.getElementById('editor-marker-modal-size')?.value || 'medium').toLowerCase();
      const style = String(document.getElementById('editor-marker-modal-style')?.value || 'round').toLowerCase();
      const assetScale = Math.max(0.25, Math.min(4, Number(document.getElementById('editor-marker-modal-asset-scale')?.value || 1) || 1));
      const assetAnchor = String(document.getElementById('editor-marker-modal-asset-anchor')?.value || 'center').toLowerCase() === 'bottom' ? 'bottom' : 'center';
      const assetFootprint = Math.max(0.5, Math.min(4, Number(document.getElementById('editor-marker-modal-asset-footprint')?.value || 1) || 1));
      const poi = poiId ? (env.pois[poiId] || null) : null;
      const items = Array.isArray(env.currentMarkerItems()) ? env.currentMarkerItems().slice() : [];
      const selectedMarkerAsset = kind === 'custom_asset' && typeof env.getSelectedEditorMarkerAsset === 'function' ? (env.getSelectedEditorMarkerAsset() || null) : null;
      if (env.editorMarkerModalState.mode === 'edit') {
        const idx = items.findIndex(item => String(item.id || '') === String(env.editorMarkerModalState.markerId || ''));
        if (idx < 0) {
          env.closeEditorMarkerModal();
          return;
        }
        items[idx] = { ...items[idx], kind, name, size, style, linked_poi_id: poiId, linked_map_url: poi?.local_map_url || '', asset_id: selectedMarkerAsset?.id || items[idx]?.asset_id || '', asset_file: selectedMarkerAsset?.file || items[idx]?.asset_file || '', asset_thumbnail: selectedMarkerAsset?.thumbnail || selectedMarkerAsset?.file || items[idx]?.asset_thumbnail || '', asset_scale: kind === 'custom_asset' ? assetScale : 1, asset_anchor: kind === 'custom_asset' ? assetAnchor : 'center', asset_footprint: kind === 'custom_asset' ? assetFootprint : 1 };
      } else {
        items.push({ id: `marker_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,6)}`, kind, x: env.editorMarkerModalState.x, y: env.editorMarkerModalState.y, name, size, style, linked_poi_id: poiId, linked_map_url: poi?.local_map_url || '', asset_id: selectedMarkerAsset?.id || '', asset_file: selectedMarkerAsset?.file || '', asset_thumbnail: selectedMarkerAsset?.thumbnail || selectedMarkerAsset?.file || '', asset_scale: kind === 'custom_asset' ? assetScale : 1, asset_anchor: kind === 'custom_asset' ? assetAnchor : 'center', asset_footprint: kind === 'custom_asset' ? assetFootprint : 1 });
      }
      env.setCurrentMarkerItems(items);
      env.editorMarkerKind = kind;
      env.setEditorMarkerKind(kind);
      env.saveEditorMarkers(true);
      env.closeEditorMarkerModal();
      env.drawFrame();
    },
    deleteEditorMarkerModalItem(env){
      if (!env || !env.editorMarkerModalState || env.editorMarkerModalState.mode !== 'edit') return;
      env.ensureEditorMarkersLoaded();
      const items = Array.isArray(env.currentMarkerItems()) ? env.currentMarkerItems().slice() : [];
      const idx = items.findIndex(item => String(item.id || '') === String(env.editorMarkerModalState.markerId || ''));
      if (idx >= 0) items.splice(idx, 1);
      env.setCurrentMarkerItems(items);
      env.saveEditorMarkers(true);
      env.closeEditorMarkerModal();
      env.drawFrame();
    },
    applyEditorWallCut(env, kind, wx, wy){
      env.ensureEditorWallsLoaded();
      const idx = env.findEditorWallIndexAt(wx, wy);
      env.editorWallHoverIndex = idx;
      if (idx < 0) return false;
      const segmentsBefore = Array.isArray(env.editorWallSegments()) ? env.editorWallSegments().slice() : [];
      const target = segmentsBefore[idx];
      const cut = env.splitEditorWallSegmentForDoor(target, wx, wy);
      if (!cut) return false;
      const segmentsAfter = segmentsBefore.slice();
      segmentsAfter.splice(idx, 1, ...cut.pieces);
      const merged = env.mergeEditorWallSegments(segmentsAfter);
      env.setEditorWallSegments(merged);
      // Push undo for wall cut + door placement
      if (typeof env.pushEditorUndo === 'function') {
        env.pushEditorUndo({ type: 'wall_cut', before: segmentsBefore.slice(), after: merged.slice(), kind, gap: cut.gap });
      }
      const placed = env.upsertEditorDoorProp(kind, cut.gap);
      env.markEditorLayerDirty('walls', 120);
      env.saveEditorWalls(true);
      if (placed) {
        env.markEditorLayerDirty('props', 120);
        env.saveEditorProps(true);
      }
      return true;
    },
    handleEditorWallClick(env, wx, wy){
      env.ensureEditorWallsLoaded();
      if (env.editorPaintMode === 'erase') {
        const idx = env.findEditorWallIndexAt(wx, wy);
        env.editorWallHoverIndex = idx;
        if (idx >= 0) {
          const segments = Array.isArray(env.editorWallSegments()) ? env.editorWallSegments().slice() : [];
          const removed  = segments[idx];
          segments.splice(idx, 1);
          env.setEditorWallSegments(segments);
          // Push undo for wall erase
          if (typeof env.pushEditorUndo === 'function') {
            env.pushEditorUndo({ type: 'wall_erase', segment: removed });
          }
          env.editorWallDraftStart = null;
          env.editorWallHoverIndex = -1;
          env.markEditorLayerDirty('walls', 120);
          env.saveEditorWalls(true);
          env.drawFrame();
        }
        return;
      }
      if (env.editorWallTool === 'door' || env.editorWallTool === 'opening') {
        const ok = this.applyEditorWallCut(env, env.editorWallTool, wx, wy);
        if (!ok) env.showToast('Click a straight wall segment to cut a doorway/opening');
        env.drawFrame();
        return;
      }
      const snapped = env.snapEditorWallPoint(wx, wy);
      if (!env.editorWallDraftStart) {
        env.editorWallDraftStart = snapped;
        env.drawFrame();
        return;
      }
      if (env.editorWallTool === 'room') {
        const roomSegments = env.buildEditorRoomWallSegments(env.editorWallDraftStart, snapped);
        env.editorWallDraftStart = null;
        const addedSegs = [];
        roomSegments.forEach(seg => { if (env.addEditorWallSegment(seg)) addedSegs.push(seg); });
        if (addedSegs.length) {
          if (typeof env.pushEditorUndo === 'function') {
            env.pushEditorUndo({ type: 'wall_add', segments: addedSegs });
          }
          env.markEditorLayerDirty('walls', 120);
          env.saveEditorWalls(true);
        }
        env.drawFrame();
        return;
      }
      const pt = env.constrainEditorWallPoint(env.editorWallDraftStart, snapped);
      const seg = env.normalizeEditorWallSegment({ x1: env.editorWallDraftStart.x, y1: env.editorWallDraftStart.y, x2: pt.x, y2: pt.y });
      env.editorWallDraftStart = null;
      if (!seg) {
        env.drawFrame();
        return;
      }
      if (env.addEditorWallSegment(seg)) {
        if (typeof env.pushEditorUndo === 'function') {
          env.pushEditorUndo({ type: 'wall_add', segments: [seg] });
        }
        env.markEditorLayerDirty('walls', 120);
        env.saveEditorWalls(true);
      }
      env.drawFrame();
    },
    handleEditorPropMouseDown(env, wx, wy){
      env.ensureEditorPropsLoaded();
      if (env.editorPaintMode === 'erase') {
        const idx = env.findEditorPropIndexAt(wx, wy);
        env.editorPropHoverIndex = idx;
        if (idx >= 0) {
          const items = Array.isArray(env.editorPropItems()) ? env.editorPropItems().slice() : [];
          const removed = items[idx];
          items.splice(idx, 1);
          env.setEditorPropItems(items);
          // Push undo for prop erasure
          if (removed && typeof env.pushEditorUndo === 'function') {
            env.pushEditorUndo({ type: 'prop_erase', items: [removed] });
          }
          if (env.openPropPopupId && removed && removed.id === env.openPropPopupId) env.propPopupClose();
          env.editorPropHoverIndex = -1;
          env.markEditorLayerDirty('props', 140);
          env.drawFrame();
        }
        return;
      }
      const idx = env.findEditorPropIndexAt(wx, wy);
      const items = Array.isArray(env.editorPropItems()) ? env.editorPropItems() : [];
      if (idx >= 0) {
        const hitItem = items[idx];
        env.editorPropHoverIndex = idx;
        env.editorPropDragId = hitItem.id;
        env.drawFrame();
        return;
      }
      if (env.editorPropKind === 'settlement_cluster') {
        if (env.placeSettlementClusterAt(wx, wy)) env.saveEditorProps(true);
        return;
      }
      if (env.editorPropKind === 'market_district' || env.editorPropKind === 'temple_district' || env.editorPropKind === 'farm_block') {
        if (env.placeDistrictClusterAt(env.editorPropKind, wx, wy)) env.saveEditorProps(true);
        return;
      }
      if (env.editorPropKind === 'town_generator' || env.editorPropKind === 'city_generator') {
        if (env.placeGeneratedSettlementAt(env.editorPropKind, wx, wy)) env.saveEditorProps(true);
        return;
      }
      if (env.editorPropKind === 'harbor_generator') {
        if (env.placeHarborLayoutAt(wx, wy)) env.saveEditorProps(true);
        return;
      }
      if (env.editorPropKind === 'crossing_generator') {
        if (env.placeCrossingLayoutAt(wx, wy)) env.saveEditorProps(true);
        return;
      }
      if (env.editorPropKind === 'town_wall_ring') {
        if (env.placeTownWallRingAt(wx, wy)) env.saveEditorProps(true);
        return;
      }
      const snapped = env.editorPathSnapPoint(wx, wy);
      const item = env.buildEditorPropItem(env.editorPropKind, snapped.x, snapped.y, env.editorPropSize);
      if (!item) return;
      const dupe = items.some(existing => env.editorPropSignature(existing) === env.editorPropSignature(item));
      if (dupe) return;
      env.setEditorPropItems(items.concat([item]));
      env.editorPropDragId = item.id;
      env.editorPropHoverIndex = env.findEditorPropIndexById(item.id);
      env.markEditorLayerDirty('props', 260);
      env.drawFrame();
    },
    updateEditorPropDrag(env, wx, wy){
      if (!env.editorPropDragId) return false;
      env.ensureEditorPropsLoaded();
      const idx = env.findEditorPropIndexById(env.editorPropDragId);
      if (idx < 0) return false;
      const items = Array.isArray(env.editorPropItems()) ? env.editorPropItems().slice() : [];
      const item = items[idx];
      const snapped = env.editorPathSnapPoint(wx, wy);
      item.x = snapped.x;
      item.y = snapped.y;
      env.setEditorPropItems(items);
      env.editorPropHoverIndex = idx;
      env.markEditorLayerDirty('props', 260);
      env.drawFrame();
      return true;
    },
    finishEditorPropDrag(env){
      if (!env.editorPropDragId) return false;
      env.editorPropDragId = null;
      env.setEditorPropItems(env.dedupeEditorProps(env.editorPropItems()));
      env.markEditorLayerDirty('props', 80);
      env.saveEditorProps(true);
      env.drawFrame();
      return true;
    },
    applyEditorBrushStamp(env, wx, wy, touchedOut){
      env.ensureEditorLayerLoaded();
      const gx = Math.floor(wx / 50);
      const gy = Math.floor(wy / 50);
      const radius = Math.max(0, env.editorBrush - 1);
      const touched = [];
      const cells = env.editorLayerCells() || {};
      for (let dx = -radius; dx <= radius; dx++) {
        for (let dy = -radius; dy <= radius; dy++) {
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > radius + 0.35) continue;
          const falloff = radius <= 0 ? 1 : Math.max(0, 1 - dist / (radius + 0.15));
          const edgeNoise = env.terrainHash01(gx + dx, gy + dy, env.editorTerrain * 131 + env.editorBrush * 17);
          if (radius > 0 && falloff < 0.28 && edgeNoise > falloff * 2.6) continue;
          const tx = gx + dx;
          const ty = gy + dy;
          const key = `${tx}:${ty}`;
          touched.push([tx, ty]);
          if (Array.isArray(touchedOut)) touchedOut.push([tx, ty]);
          if (env.editorPaintMode === 'erase') {
            delete cells[key];
            continue;
          }
          if (env.editorPaintMode === 'blend') {
            cells[key] = env.smartBlendTerrainAt(tx, ty);
            continue;
          }
          if (env.editorPaintMode === 'forest' || env.editorPaintMode === 'mountain' || env.editorPaintMode === 'coastline') continue;
          cells[key] = env.editorTerrain;
        }
      }
      env.setEditorLayerCells(cells);
      if (env.editorPaintMode === 'forest') {
        env.paintForestRegion(touched, gx, gy, radius);
        env.smoothTerrainAroundCells(touched, 5, 2);
        env.smoothTerrainAroundCells(touched, 3, 1);
      } else if (env.editorPaintMode === 'mountain') {
        env.paintMountainRange(touched, gx, gy, radius);
        env.smoothTerrainAroundCells(touched, 9, 2);
        env.smoothTerrainAroundCells(touched, 8, 1);
      } else if (env.editorPaintMode === 'coastline') {
        env.paintCoastlineRegion(touched, gx, gy, radius);
      } else {
        if (env.editorPaintMode === 'paint' && env.editorTerrain === 4 && touched.length) {
          const coastalNeighbors = [[1,0],[-1,0],[0,1],[0,-1],[1,1],[1,-1],[-1,1],[-1,-1]];
          touched.forEach(([cx, cy]) => {
            coastalNeighbors.forEach(([dx, dy]) => {
              const nx = cx + dx;
              const ny = cy + dy;
              const k = `${nx}:${ny}`;
              const existing = Number(cells[k] || 0);
              if (existing === 4 || existing === 7) return;
              if (existing && existing !== 3 && existing !== 2 && existing !== 10 && existing !== 11) return;
              if (env.terrainHash01(nx, ny, 4701) > 0.78) return;
              cells[k] = 7;
              if (Array.isArray(touchedOut)) touchedOut.push([nx, ny]);
            });
          });
        }
        if (env.editorPaintMode === 'paint') env.smoothTerrainAroundCells(touched, env.editorTerrain, 2);
        else if (env.editorPaintMode === 'blend') {
          env.smoothTerrainAroundCells(touched, env.editorTerrain, 3);
          if (env.editorTerrain === 4 || env.editorTerrain === 11) env.smoothTerrainAroundCells(touched, 7, 2);
          else if (env.editorTerrain === 9 || env.editorTerrain === 8) env.smoothTerrainAroundCells(touched, 8, 2);
          else if (env.editorTerrain === 5) env.smoothTerrainAroundCells(touched, 3, 1);
        }
      }
    },
    applyEditorBrush(env, wx, wy){
      env.ensureEditorLayerLoaded();
      const allTouched = [];
      const prev = env.editorMousePrevWorld && Number.isFinite(env.editorMousePrevWorld.x) && Number.isFinite(env.editorMousePrevWorld.y) ? env.editorMousePrevWorld : null;
      if (prev) {
        const dist = Math.hypot(wx - prev.x, wy - prev.y);
        const step = Math.max(12, 18 + (env.editorBrush - 1) * 9);
        const steps = Math.max(1, Math.ceil(dist / step));
        for (let i = 1; i <= steps; i++) {
          const t = i / steps;
          this.applyEditorBrushStamp(env, prev.x + (wx - prev.x) * t, prev.y + (wy - prev.y) * t, allTouched);
        }
      } else {
        this.applyEditorBrushStamp(env, wx, wy, allTouched);
      }
      env.editorMousePrevWorld = { x: wx, y: wy };
      env.markEditorLayerDirty('terrain', 260);
      env.drawFrame();
    },
  };
  window.AppEditorInteractions = AppEditorInteractions;
})();
