(function (global) {
  'use strict';

  function updateSharedPointerWorld(env, evt, options) {
    const world = env.getMouseWorld(evt);
    const opts = options || {};
    if (opts.updateFog && env.setFogMouseWorld) env.setFogMouseWorld(world);
    if (opts.updateSpell && env.setSpellMouseWorld) env.setSpellMouseWorld(world);
    if (opts.updateEditor && env.setEditorMouseWorld) env.setEditorMouseWorld(world);
    return world;
  }

  function beginPan(env, evt) {
    env.pan.active = true;
    env.pan.lastX = evt.clientX;
    env.pan.lastY = evt.clientY;
    if (env.wrap && env.wrap.classList) env.wrap.classList.add('panning');
    return true;
  }

  function beginMiddlePan(env, evt) {
    return beginPan(env, evt);
  }

  function beginSelectPan(env, evt) {
    return beginPan(env, evt);
  }

  function updatePan(env, evt) {
    if (!env.pan.active) return false;
    const dx = evt.clientX - env.pan.lastX;
    const dy = evt.clientY - env.pan.lastY;
    env.cam.x += dx / env.cam.zoom;
    env.cam.y += dy / env.cam.zoom;
    env.pan.lastX = evt.clientX;
    env.pan.lastY = evt.clientY;
    return true;
  }

  function endPan(env) {
    env.pan.active = false;
    if (env.wrap && env.wrap.classList) env.wrap.classList.remove('panning');
    return true;
  }

  function handleWheelZoom(env, evt) {
    evt.preventDefault();
    const factor = evt.deltaY < 0 ? 1.1 : 0.9;
    const point = env.getCanvasEventPoint(evt);
    global.AppCamera.zoomAtScreenPoint({
      cam: env.cam,
      canvas: env.canvas,
      sx: point.x,
      sy: point.y,
      factor: factor,
      minZoom: 0.1,
      maxZoom: 8,
    });
    if (env.clampCamera) env.clampCamera();
    return true;
  }

  global.AppPointerOrchestrator = {
    updateSharedPointerWorld: updateSharedPointerWorld,
    beginMiddlePan: beginMiddlePan,
    beginSelectPan: beginSelectPan,
    updatePan: updatePan,
    endPan: endPan,
    handleWheelZoom: handleWheelZoom,
  };
})(window);
