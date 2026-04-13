(function(){
  // Stage 5 vision shell owner:
  // - owns preview/fallback interpretation, visibility helpers, preview UI,
  //   and player-vision overlay logic through env/state compatibility wrappers
  // - deliberately does NOT own tokens, walls, props, or the surrounding draw loop,
  //   which still remain inline in play.html for now
  function getVisionController(env) {
    const role = env.ROLE;
    const previewState = env.previewState || { enabled:false, tokenId:'', ownerId:'' };
    if (role === 'player') return { mode: 'player', userId: String(env.USER_ID || ''), tokenId: '' };
    if (role === 'dm' && previewState.enabled) {
      return {
        mode: 'preview',
        userId: String(previewState.ownerId || ''),
        tokenId: String(previewState.tokenId || ''),
      };
    }
    return { mode: role || 'viewer', userId: String(env.USER_ID || ''), tokenId: '' };
  }

  function getFogMode(env) {
    const mode = String((env && typeof env.getFogSystemMode === 'function' ? env.getFogSystemMode() : '') || '').toLowerCase();
    if (mode === 'off' || mode === 'manual' || mode === 'vision' || mode === 'hybrid') return mode;
    return env.fogEnabled ? 'manual' : 'off';
  }

  function isVisionLimitedMode(env) {
    const mode = getVisionController(env).mode;
    if (mode === 'preview') return true;
    if (mode !== 'player') return false;
    const fogMode = getFogMode(env);
    return fogMode === 'vision' || fogMode === 'hybrid';
  }

  function getVisionFallbackReason(env) {
    if (!isVisionLimitedMode(env)) return '';
    const controller = getVisionController(env);
    const drawCtx = env.getCurrentMapContext();
    const tokenMap = env.tokens || {};
    const pool = Object.values(tokenMap);
    if (controller.mode === 'preview') {
      const tok = controller.tokenId ? (tokenMap[controller.tokenId] || (env.stagingTokens || {})[controller.tokenId]) : null;
      if (!tok) return 'Vision preview fallback: preview token could not be found.';
      if ((tok.map_context || 'world') !== drawCtx) return 'Vision preview fallback: preview token is not on this map.';
      if (tok.hidden) return 'Vision preview fallback: preview token is hidden.';
      if (!(tok.visionEnabled ?? tok.vision_enabled)) return 'Vision preview fallback: preview token vision is disabled.';
      const radiusFt = Math.max(
        Number(tok.dimRadius ?? tok.dim_radius ?? tok.visionRadius ?? tok.vision_radius ?? 0) || 0,
        Number(tok.brightRadius ?? tok.bright_radius ?? 0) || 0,
        !!(tok.hasDarkvision ?? tok.has_darkvision) ? (Number(tok.darkvisionRadius ?? tok.darkvision_radius ?? 0) || 0) : 0,
        0
      );
      if (radiusFt <= 0) return 'Vision preview fallback: preview token has no usable vision radius.';
      return '';
    }
    const owned = pool.filter(t => t && String(t.owner_id || '') === String(controller.userId || ''));
    if (!owned.length) return 'Vision fallback active: no token is currently assigned to this player.';
    const onMap = owned.filter(t => (t.map_context || 'world') === drawCtx);
    if (!onMap.length) return 'Vision fallback active: your token is not on this map yet.';
    const visible = onMap.filter(t => !t.hidden);
    if (!visible.length) return 'Vision fallback active: your token is hidden.';
    const enabled = visible.filter(t => !!(t.visionEnabled ?? t.vision_enabled));
    if (!enabled.length) return 'Vision fallback active: your token vision is disabled.';
    const usable = enabled.filter(t => {
      const radiusFt = Math.max(
        Number(t.dimRadius ?? t.dim_radius ?? t.visionRadius ?? t.vision_radius ?? 0) || 0,
        Number(t.brightRadius ?? t.bright_radius ?? 0) || 0,
        !!(t.hasDarkvision ?? t.has_darkvision) ? (Number(t.darkvisionRadius ?? t.darkvision_radius ?? 0) || 0) : 0,
        0
      );
      return radiusFt > 0;
    });
    if (!usable.length) return 'Vision fallback active: your token has no usable vision radius.';
    return '';
  }

  function hasUsableVisionSources(env) { return !getVisionFallbackReason(env); }
  function isVisionMaskActive(env) { return isVisionLimitedMode(env) && hasUsableVisionSources(env); }
  function isVisionPreviewActiveForToken(env, tokenId) {
    const previewState = env.previewState || {};
    return env.ROLE === 'dm' && previewState.enabled && String(previewState.tokenId || '') === String(tokenId || '');
  }

  function refreshVisionPreviewUi(env) {
    const previewState = env.previewState || {};
    const doc = env.document || document;
    const banner = doc.getElementById('vision-preview-banner');
    const bannerText = doc.getElementById('vision-preview-banner-text');
    const btn = doc.getElementById('te-preview-vision-btn');
    const stopBtn = doc.getElementById('te-stop-preview-vision-btn');
    const fallbackBanner = doc.getElementById('vision-fallback-banner');
    const fallbackText = doc.getElementById('vision-fallback-banner-text');
    const tok = String(previewState.tokenId || '') ? ((env.tokens || {})[previewState.tokenId] || (env.stagingTokens || {})[previewState.tokenId]) : null;
    const active = env.ROLE === 'dm' && !!previewState.enabled && !!tok;
    if (bannerText) {
      const name = tok?.name || 'Selected Token';
      bannerText.textContent = active ? `Previewing ${name} vision` : 'Previewing player vision';
    }
    if (banner) banner.style.display = active ? 'block' : 'none';
    if (btn) btn.textContent = active ? '👁 Previewing Vision' : '👁 Preview Vision';
    if (btn) btn.style.boxShadow = active ? '0 0 0 1px rgba(167,255,244,0.18) inset' : 'none';
    if (stopBtn) stopBtn.style.display = active ? 'block' : 'none';
    const fallbackReason = getVisionFallbackReason(env);
    if (fallbackText) fallbackText.textContent = fallbackReason || 'Vision fallback active.';
    const shouldShowFallback = fallbackReason && (env.ROLE === 'dm' || !!env.showFallbackBanner);
    if (fallbackBanner) fallbackBanner.style.display = shouldShowFallback ? 'block' : 'none';
  }

  function startTokenVisionPreview(env, tokenId) {
    if (env.ROLE !== 'dm') return false;
    const tok = tokenId ? ((env.tokens || {})[tokenId] || (env.stagingTokens || {})[tokenId]) : null;
    if (!tok) { env.showToast('Pick a player token first.'); return false; }
    if (tok.hidden) { env.showToast('Hidden tokens cannot be used for vision preview.'); return false; }
    if (!String(tok.owner_id || '').trim()) { env.showToast('Assign this token to a player first.'); return false; }
    if (!(tok.visionEnabled ?? tok.vision_enabled)) { env.showToast('Enable vision on this token first.'); return false; }
    env.setPreviewState({ enabled: true, tokenId: String(tok.id), ownerId: String(tok.owner_id || '') });
    refreshVisionPreviewUi(env);
    env.drawFrame();
    return true;
  }

  function stopVisionPreview(env) {
    const previewState = env.previewState || {};
    if (!previewState.enabled) return;
    env.setPreviewState({ enabled: false, tokenId: '', ownerId: '' });
    refreshVisionPreviewUi(env);
    env.drawFrame();
  }

  function toggleTokenVisionPreview(env) {
    const tokenId = env.getSelectedTokenId();
    if (isVisionPreviewActiveForToken(env, tokenId)) stopVisionPreview(env);
    else startTokenVisionPreview(env, tokenId);
  }

  function getCurrentMapVisionSources(env) {
    const controller = getVisionController(env);
    if (!isVisionLimitedMode(env)) return [];
    const drawCtx = env.getCurrentMapContext();
    return Object.values(env.tokens || {}).filter(t => {
      if (!t || (t.map_context || 'world') !== drawCtx) return false;
      if (t.hidden) return false;
      const ownerId = String(t.owner_id || '');
      if (controller.mode === 'preview') {
        if (controller.tokenId) {
          if (String(t.id || '') !== String(controller.tokenId || '')) return false;
        } else if (!(ownerId && ownerId === controller.userId)) {
          return false;
        }
        return !!(t.visionEnabled ?? t.vision_enabled);
      }
      if (ownerId !== controller.userId) return false;
      return !!(t.visionEnabled ?? t.vision_enabled);
    }).map(t => {
      const baseFt = Number(t.dimRadius ?? t.dim_radius ?? t.visionRadius ?? t.vision_radius ?? 0) || 0;
      const brightFt = Number(t.brightRadius ?? t.bright_radius ?? 0) || 0;
      const darkFt = !!(t.hasDarkvision ?? t.has_darkvision) ? (Number(t.darkvisionRadius ?? t.darkvision_radius ?? 0) || 0) : 0;
      const radiusFt = Math.max(baseFt, brightFt, darkFt, 0);
      return {
        id: t.id,
        tokenId: t.id,
        ownerId: String(t.owner_id || ''),
        x: Number(t.x || 0) + Number(t.width || 0) / 2,
        y: Number(t.y || 0) + Number(t.height || 0) / 2,
        radiusPx: (radiusFt / 5) * 50,
      };
    }).filter(src => src.radiusPx > 0);
  }

  function collectCurrentMapVisionBlockers(env) {
    const drawCtx = env.getCurrentMapContext();
    const blockers = [];
    const walls = env.editorWallsAll?.[drawCtx] || [];
    walls.forEach(seg => {
      if (!seg) return;
      const x1 = Number(seg.x1), y1 = Number(seg.y1), x2 = Number(seg.x2), y2 = Number(seg.y2);
      if (![x1, y1, x2, y2].every(Number.isFinite)) return;
      if (x1 === x2 && y1 === y2) return;
      blockers.push({ x1, y1, x2, y2 });
    });
    const props = env.editorPropsAll?.[drawCtx] || [];
    const solidKinds = new Set(['barrel', 'table', 'tree', 'rock', 'crate']);
    props.forEach(item => {
      if (!item) return;
      const kind = String(item.kind || '').toLowerCase();
      if (kind === 'door') {
        if (String(item.state || 'closed').toLowerCase() === 'open') return;
        if (item.blocks_vision === false) return;
        const x = Number(item.x || 0), y = Number(item.y || 0);
        const facing = String(item.facing || 'h').toLowerCase().startsWith('v') ? 'v' : 'h';
        if (facing === 'v') blockers.push({ x1: x, y1: y, x2: x, y2: y + 50 });
        else blockers.push({ x1: x, y1: y, x2: x + 50, y2: y });
        return;
      }
      if (!solidKinds.has(kind)) return;
      const x = Number(item.x || 0), y = Number(item.y || 0);
      const w = Math.max(1, Number(item.w || 1)) * 50;
      const h = Math.max(1, Number(item.h || 1)) * 50;
      blockers.push({ x1: x, y1: y, x2: x + w, y2: y });
      blockers.push({ x1: x + w, y1: y, x2: x + w, y2: y + h });
      blockers.push({ x1: x + w, y1: y + h, x2: x, y2: y + h });
      blockers.push({ x1: x, y1: y + h, x2: x, y2: y });
    });
    return blockers;
  }

  function orient(ax, ay, bx, by, cx, cy) { return (by - ay) * (cx - bx) - (bx - ax) * (cy - by); }
  function onSegment(ax, ay, bx, by, cx, cy) {
    return cx <= Math.max(ax, bx) + 0.0001 && cx + 0.0001 >= Math.min(ax, bx) && cy <= Math.max(ay, by) + 0.0001 && cy + 0.0001 >= Math.min(ay, by);
  }
  function segmentsIntersect(a1x, a1y, a2x, a2y, b1x, b1y, b2x, b2y) {
    const o1 = orient(a1x, a1y, a2x, a2y, b1x, b1y);
    const o2 = orient(a1x, a1y, a2x, a2y, b2x, b2y);
    const o3 = orient(b1x, b1y, b2x, b2y, a1x, a1y);
    const o4 = orient(b1x, b1y, b2x, b2y, a2x, a2y);
    if ((o1 > 0) !== (o2 > 0) && (o3 > 0) !== (o4 > 0)) return true;
    if (Math.abs(o1) < 0.0001 && onSegment(a1x, a1y, a2x, a2y, b1x, b1y)) return true;
    if (Math.abs(o2) < 0.0001 && onSegment(a1x, a1y, a2x, a2y, b2x, b2y)) return true;
    if (Math.abs(o3) < 0.0001 && onSegment(b1x, b1y, b2x, b2y, a1x, a1y)) return true;
    if (Math.abs(o4) < 0.0001 && onSegment(b1x, b1y, b2x, b2y, a2x, a2y)) return true;
    return false;
  }

  function isPointVisibleToPlayer(env, wx, wy, paddingPx = 0) {
    if (!isVisionMaskActive(env)) return true;
    const sources = getCurrentMapVisionSources(env);
    if (!sources.length) return true;
    const blockers = collectCurrentMapVisionBlockers(env);
    for (const src of sources) {
      const dx = wx - src.x;
      const dy = wy - src.y;
      const reach = src.radiusPx + Math.max(0, Number(paddingPx || 0));
      if ((dx * dx) + (dy * dy) > (reach * reach)) continue;
      let blocked = false;
      for (const seg of blockers) {
        if (segmentsIntersect(src.x, src.y, wx, wy, seg.x1, seg.y1, seg.x2, seg.y2)) { blocked = true; break; }
      }
      if (!blocked) return true;
    }
    return false;
  }
  function isPointVisibleToPlayerWithinRange(env, wx, wy, maxRangePx, paddingPx = 0) {
    if (!isVisionMaskActive(env)) return true;
    const sources = getCurrentMapVisionSources(env);
    if (!sources.length) return true;
    const blockers = collectCurrentMapVisionBlockers(env);
    const rangePx = Math.max(0, Number(maxRangePx || 0));
    for (const src of sources) {
      const dx = wx - src.x, dy = wy - src.y;
      const reach = Math.min(src.radiusPx, rangePx || src.radiusPx) + Math.max(0, Number(paddingPx || 0));
      if ((dx * dx) + (dy * dy) > (reach * reach)) continue;
      let blocked = false;
      for (const seg of blockers) {
        if (segmentsIntersect(src.x, src.y, wx, wy, seg.x1, seg.y1, seg.x2, seg.y2)) { blocked = true; break; }
      }
      if (!blocked) return true;
    }
    return false;
  }
  function isRectVisibleToPlayerWithinRange(env, x, y, w, h, maxRangePx, paddingPx = 0) {
    if (!isVisionMaskActive(env)) return true;
    const pad = Math.max(0, Number(paddingPx || 0));
    const extraReach = Math.max(w, h) * 0.18;
    const points = [[x + w / 2, y + h / 2],[x + pad, y + pad],[x + w - pad, y + pad],[x + pad, y + h - pad],[x + w - pad, y + h - pad]];
    return points.some(([px, py]) => isPointVisibleToPlayerWithinRange(env, px, py, maxRangePx, extraReach));
  }
  function isRectVisibleToPlayer(env, x, y, w, h, paddingPx = 0) {
    if (!isVisionMaskActive(env)) return true;
    const pad = Math.max(0, Number(paddingPx || 0));
    const points = [[x + w / 2, y + h / 2],[x + pad, y + pad],[x + w - pad, y + pad],[x + pad, y + h - pad],[x + w - pad, y + h - pad]];
    return points.some(([px, py]) => isPointVisibleToPlayer(env, px, py, Math.max(w, h) * 0.18));
  }
  function isTokenVisibleToPlayer(env, t) {
    if (!isVisionMaskActive(env)) return true;
    if (!t) return false;
    const controller = getVisionController(env);
    if (controller.mode === 'player' && String(t.owner_id || '') === String(controller.userId || '')) return true;
    if (controller.mode === 'preview' && String(t.id || '') === String(controller.tokenId || '')) return true;
    const cx = Number(t.x || 0) + Number(t.width || 0) / 2;
    const cy = Number(t.y || 0) + Number(t.height || 0) / 2;
    const pad = Math.max(Number(t.width || 0), Number(t.height || 0)) * 0.35;
    return isPointVisibleToPlayer(env, cx, cy, pad);
  }
  function isHazardVisibleToPlayer(env, zone) {
    if (!isVisionMaskActive(env)) return true;
    if (!zone) return false;
    const radiusPx = (Number(zone.radius_ft || 15) / 5) * 50;
    return isPointVisibleToPlayer(env, Number(zone.x || 0), Number(zone.y || 0), radiusPx * 0.75);
  }
  function isPoiVisibleToPlayer(env, poi) {
    if (!poi) return false;
    if (env && env.getRole && env.getRole() !== 'dm' && poi.revealed_to_players === false) return false;
    if (!isVisionMaskActive(env)) return true;
    const zoom = Math.max(env.cam.zoom || 1, 0.0001);
    return isPointVisibleToPlayer(env, Number(poi.x || 0), Number(poi.y || 0) - 22 / zoom, 24 / zoom);
  }
  function drawPlayerVisionOverlay(env, W, H) {
    if (!isVisionMaskActive(env)) return;
    const sources = getCurrentMapVisionSources(env);
    if (!sources.length) return;
    const topLeft = env.screenToWorld(0, 0);
    const bottomRight = env.screenToWorld(W, H);
    const step = 25;
    const startX = Math.floor(Math.min(topLeft.x, bottomRight.x) / step) * step;
    const endX = Math.ceil(Math.max(topLeft.x, bottomRight.x) / step) * step;
    const startY = Math.floor(Math.min(topLeft.y, bottomRight.y) / step) * step;
    const endY = Math.ceil(Math.max(topLeft.y, bottomRight.y) / step) * step;
    const ctx = env.ctx;
    const cam = env.cam;
    ctx.save();
    ctx.translate(W / 2, H / 2);
    ctx.scale(cam.zoom, cam.zoom);
    ctx.translate(cam.x, cam.y);
    const fogMode = getFogMode(env);
    const overlayAlpha = fogMode === 'hybrid' ? 0.72 : 0.88;
    ctx.fillStyle = `rgba(0,0,0,${overlayAlpha})`;
    for (let x = startX; x < endX; x += step) {
      for (let y = startY; y < endY; y += step) {
        if (isPointVisibleToPlayer(env, x + (step / 2), y + (step / 2), step * 0.45)) continue;
        ctx.fillRect(x, y, step, step);
      }
    }
    ctx.restore();
  }

  window.AppVision = {
    getVisionController,
    getFogMode,
    isVisionLimitedMode,
    getVisionFallbackReason,
    hasUsableVisionSources,
    isVisionMaskActive,
    isVisionPreviewActiveForToken,
    refreshVisionPreviewUi,
    startTokenVisionPreview,
    stopVisionPreview,
    toggleTokenVisionPreview,
    getCurrentMapVisionSources,
    collectCurrentMapVisionBlockers,
    isPointVisibleToPlayer,
    isPointVisibleToPlayerWithinRange,
    isRectVisibleToPlayerWithinRange,
    isRectVisibleToPlayer,
    isTokenVisibleToPlayer,
    isHazardVisibleToPlayer,
    isPoiVisibleToPlayer,
    drawPlayerVisionOverlay,
  };
})();
