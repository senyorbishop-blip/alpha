(function () {
  function getGridDelta(env, dx, dy) {
    return { sx: Math.abs(dx) / env.PX_PER_GRID, sy: Math.abs(dy) / env.PX_PER_GRID };
  }
  function getSquaresFromDelta(env, dx, dy) {
    const { sx, sy } = getGridDelta(env, dx, dy);
    if (env.getRulerUnit() !== 'ft' || env.getRulerDiagonalRule() === 'straight') return Math.hypot(sx, sy);
    const diag = Math.min(sx, sy);
    const straight = Math.max(sx, sy) - diag;
    return straight + (diag > 0 ? diag * 2 - 1 : 0);
  }
  function formatUnits(env, val) {
    if (env.getRulerUnit() === 'miles') return val >= 100 ? `${Math.round(val)} mi` : `${val.toFixed(1)} mi`;
    return val >= 100 ? `${Math.round(val)} ft` : `${val.toFixed(1)} ft`;
  }
  function getDistance(env, dx, dy) { return formatUnits(env, getSquaresFromDelta(env, dx, dy) * env.getRulerScale()); }
  function getSquares(env, dx, dy) { return getSquaresFromDelta(env, dx, dy); }
  function getActiveSpeed(env) {
    if (env.ROLE === 'dm' && env.getActiveTokenEditorId() && env.tokens[env.getActiveTokenEditorId()]) {
      const speed = parseInt(env.tokens[env.getActiveTokenEditorId()].speed ?? '', 10);
      return Number.isFinite(speed) ? speed : null;
    }
    if (env.ROLE === 'player') {
      const myToken = Object.values(env.tokens).find(t => t.owner_id === env.USER_ID);
      const speed = parseInt(myToken?.speed ?? env.getCharSheet()?.speed ?? '', 10);
      return Number.isFinite(speed) ? speed : null;
    }
    return null;
  }
  function getDisplay(env, dx, dy) {
    const squares = getSquares(env, dx, dy);
    const base = formatUnits(env, squares * env.getRulerScale());
    const squareText = squares >= 10 ? `${Math.round(squares)} sq` : `${squares.toFixed(1)} sq`;
    const speed = getActiveSpeed(env);
    if (speed == null || env.getRulerUnit() !== 'ft') return `${base} • ${squareText}`;
    const diff = (squares * env.getRulerScale()) - speed;
    if (diff <= 0.01) return `${base} • ${squareText} • within ${speed} ft`;
    return `${base} • ${squareText} • +${Math.round(diff)} ft over`;
  }
  function draw(env, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1;
    const label = getDisplay(env, dx, dy);
    const { ctx, cam } = env;
    ctx.save();
    ctx.setLineDash([8 / cam.zoom, 5 / cam.zoom]);
    ctx.strokeStyle = '#00d4d4';
    ctx.lineWidth = 2 / cam.zoom;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.setLineDash([]);
    [{ x: x1, y: y1 }, { x: x2, y: y2 }].forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 5 / cam.zoom, 0, Math.PI * 2);
      ctx.fillStyle = '#00d4d4';
      ctx.fill();
    });
    const midX = (x1 + x2) / 2, midY = (y1 + y2) / 2;
    const angle = Math.atan2(dy, dx);
    ctx.save();
    ctx.translate(midX, midY);
    const textAngle = angle > Math.PI / 2 || angle < -Math.PI / 2 ? angle + Math.PI : angle;
    ctx.rotate(textAngle);
    const fs = Math.max(12, 14 / cam.zoom);
    ctx.font = `600 ${fs}px Cinzel, serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'bottom';
    const tw = ctx.measureText(label).width + 12 / cam.zoom;
    const th = fs * 1.3;
    ctx.fillStyle = 'rgba(18,16,14,0.82)';
    ctx.beginPath();
    const rx = -tw / 2, ry = -th - 2 / cam.zoom;
    const rr = 4 / cam.zoom;
    ctx.roundRect(rx, ry, tw, th, rr);
    ctx.fill();
    ctx.strokeStyle = 'rgba(0,212,212,0.5)';
    ctx.lineWidth = 1 / cam.zoom;
    ctx.stroke();
    ctx.fillStyle = '#00d4d4';
    ctx.fillText(label, 0, -4 / cam.zoom);
    ctx.restore();
    ctx.restore();
  }
  window.AppRenderRuler = { getGridDelta, getSquaresFromDelta, formatUnits, getDistance, getSquares, getActiveSpeed, getDisplay, draw };
})();
