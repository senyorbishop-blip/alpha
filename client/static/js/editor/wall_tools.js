(function(){
  const AppEditorWalls = {
    normalizeEditorWallSegment(seg){
      if (!seg || typeof seg !== 'object') return null;
      const x1 = Math.round(Number(seg.x1));
      const y1 = Math.round(Number(seg.y1));
      const x2 = Math.round(Number(seg.x2));
      const y2 = Math.round(Number(seg.y2));
      if (![x1, y1, x2, y2].every(Number.isFinite)) return null;
      if (x1 === x2 && y1 === y2) return null;
      return { x1, y1, x2, y2 };
    },
    editorWallSegmentSignature(seg){
      if (!seg) return '';
      const a = `${seg.x1}:${seg.y1}`;
      const b = `${seg.x2}:${seg.y2}`;
      return a <= b ? `${a}|${b}` : `${b}|${a}`;
    },
    mergeEditorWallSegments(segments){
      const horizontal = new Map();
      const vertical = new Map();
      const others = [];
      (Array.isArray(segments) ? segments : []).forEach(raw => {
        const seg = this.normalizeEditorWallSegment(raw);
        if (!seg) return;
        if (seg.y1 === seg.y2) {
          const y = seg.y1; const start = Math.min(seg.x1, seg.x2); const end = Math.max(seg.x1, seg.x2);
          if (start === end) return; if (!horizontal.has(y)) horizontal.set(y, []); horizontal.get(y).push([start, end]); return;
        }
        if (seg.x1 === seg.x2) {
          const x = seg.x1; const start = Math.min(seg.y1, seg.y2); const end = Math.max(seg.y1, seg.y2);
          if (start === end) return; if (!vertical.has(x)) vertical.set(x, []); vertical.get(x).push([start, end]); return;
        }
        others.push(seg);
      });
      const merged = [];
      const mergeRanges = (items, build) => {
        items.sort((a, b) => (a[0] - b[0]) || (a[1] - b[1]));
        let current = null;
        items.forEach(([start, end]) => {
          if (!current) { current = [start, end]; return; }
          if (start <= current[1]) current[1] = Math.max(current[1], end);
          else { const built = build(current[0], current[1]); if (built) merged.push(built); current = [start, end]; }
        });
        if (current) { const built = build(current[0], current[1]); if (built) merged.push(built); }
      };
      horizontal.forEach((items, y) => mergeRanges(items, (start, end) => this.normalizeEditorWallSegment({ x1: start, y1: Number(y), x2: end, y2: Number(y) })));
      vertical.forEach((items, x) => mergeRanges(items, (start, end) => this.normalizeEditorWallSegment({ x1: Number(x), y1: start, x2: Number(x), y2: end })));
      const seen = new Set(); const result = [];
      [...merged, ...others].forEach(seg => { const sig = this.editorWallSegmentSignature(seg); if (!sig || seen.has(sig)) return; seen.add(sig); result.push(seg); });
      return result;
    },
    buildEditorRoomWallSegments(a, b){
      const x1 = Math.min(a.x, b.x), y1 = Math.min(a.y, b.y), x2 = Math.max(a.x, b.x), y2 = Math.max(a.y, b.y);
      if (x1 === x2 || y1 === y2) return [];
      return [
        { x1, y1, x2, y2: y1 }, { x1: x2, y1, x2, y2 }, { x1: x2, y1: y2, x2: x1, y2 }, { x1, y1: y2, x2: x1, y2: y1 },
      ].map(seg => this.normalizeEditorWallSegment(seg)).filter(Boolean);
    },
    snapEditorWallPoint(wx, wy){ return { x: Math.round(wx / 50) * 50, y: Math.round(wy / 50) * 50 }; },
    constrainEditorWallPoint(env, start, pt){
      if (!env.editorWallStraightAssist || !start || !pt) return pt;
      const dx = Math.abs(pt.x - start.x), dy = Math.abs(pt.y - start.y);
      return dx >= dy ? { x: pt.x, y: start.y } : { x: start.x, y: pt.y };
    },
    editorPointLineDistance(px, py, x1, y1, x2, y2){
      const dx = x2 - x1, dy = y2 - y1;
      if (!dx && !dy) return Math.hypot(px - x1, py - y1);
      let t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy);
      t = Math.max(0, Math.min(1, t));
      const cx = x1 + t * dx, cy = y1 + t * dy;
      return Math.hypot(px - cx, py - cy);
    },
    findEditorWallIndexAt(env, wx, wy){
      env.ensureEditorWallsLoaded();
      const threshold = 12 / Math.max(0.2, env.camZoom || 1);
      for (let i = (env.editorWallSegments() || []).length - 1; i >= 0; i--) {
        const seg = env.editorWallSegments()[i];
        if (this.editorPointLineDistance(wx, wy, seg.x1, seg.y1, seg.x2, seg.y2) <= threshold) return i;
      }
      return -1;
    },
    updateEditorWallHover(env, wx, wy){
      const next = (env.isEditorOpen() && env.editorActiveLayer === 'walls') ? this.findEditorWallIndexAt(env, wx, wy) : -1;
      if (next !== env.editorWallHoverIndex()) {
        env.setEditorWallHoverIndex(next);
        env.drawFrame();
      }
    },
    getEditorDoorGapFromSegment(seg, wx, wy){
      const normalized = this.normalizeEditorWallSegment(seg); if (!normalized) return null;
      if (normalized.y1 === normalized.y2) {
        const start = Math.min(normalized.x1, normalized.x2), end = Math.max(normalized.x1, normalized.x2);
        if ((end - start) < 50) return null;
        let gapStart = Math.floor(wx / 50) * 50;
        gapStart = Math.max(start, Math.min(gapStart, end - 50));
        const gapEnd = gapStart + 50;
        return { orientation: 'h', gapStart, gapEnd, anchorX: gapStart, anchorY: normalized.y1 };
      }
      if (normalized.x1 === normalized.x2) {
        const start = Math.min(normalized.y1, normalized.y2), end = Math.max(normalized.y1, normalized.y2);
        if ((end - start) < 50) return null;
        let gapStart = Math.floor(wy / 50) * 50;
        gapStart = Math.max(start, Math.min(gapStart, end - 50));
        const gapEnd = gapStart + 50;
        return { orientation: 'v', gapStart, gapEnd, anchorX: normalized.x1, anchorY: gapStart };
      }
      return null;
    },
    splitEditorWallSegmentForDoor(seg, wx, wy){
      const normalized = this.normalizeEditorWallSegment(seg); if (!normalized) return null;
      const gap = this.getEditorDoorGapFromSegment(normalized, wx, wy); if (!gap) return null;
      const pieces = [];
      if (gap.orientation === 'h') {
        const start = Math.min(normalized.x1, normalized.x2), end = Math.max(normalized.x1, normalized.x2);
        if (gap.gapStart > start) pieces.push(this.normalizeEditorWallSegment({ x1: start, y1: normalized.y1, x2: gap.gapStart, y2: normalized.y1 }));
        if (gap.gapEnd < end) pieces.push(this.normalizeEditorWallSegment({ x1: gap.gapEnd, y1: normalized.y1, x2: end, y2: normalized.y1 }));
      } else {
        const start = Math.min(normalized.y1, normalized.y2), end = Math.max(normalized.y1, normalized.y2);
        if (gap.gapStart > start) pieces.push(this.normalizeEditorWallSegment({ x1: normalized.x1, y1: start, x2: normalized.x1, y2: gap.gapStart }));
        if (gap.gapEnd < end) pieces.push(this.normalizeEditorWallSegment({ x1: normalized.x1, y1: gap.gapEnd, x2: normalized.x1, y2: end }));
      }
      return { gap, pieces: pieces.filter(Boolean) };
    },
  };
  window.AppEditorWalls = AppEditorWalls;
})();
