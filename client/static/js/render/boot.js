(function (global) {
  'use strict';

  // Stage 4 render bootstrap owner:
  // - owns canvas resize wiring, fog-canvas creation, one-time pointer binding,
  //   one-time global render finalizers, and starting the animation loop
  // - deliberately does NOT own drawLoop()/drawFrame() or gameplay interaction
  //   logic, which still live in play.html via the compatibility env callbacks

  function getWrap(env) {
    return env && env.wrap ? env.wrap : null;
  }

  function getCanvas(env) {
    return env && env.canvas ? env.canvas : null;
  }

  function resizeCanvas(env) {
    const wrap = getWrap(env);
    const canvas = getCanvas(env);
    if (!wrap || !canvas) return false;
    const drawFrame = env.drawFrame;
    const dpr = global.devicePixelRatio || 1;
    canvas.width = Math.floor(wrap.clientWidth * dpr);
    canvas.height = Math.floor(wrap.clientHeight * dpr);
    canvas.style.width = wrap.clientWidth + 'px';
    canvas.style.height = wrap.clientHeight + 'px';
    const weatherCanvas = typeof env.getWeatherCanvas === 'function' ? env.getWeatherCanvas() : null;
    if (weatherCanvas) {
      weatherCanvas.width = canvas.width;
      weatherCanvas.height = canvas.height;
    }
    if (typeof drawFrame === 'function') drawFrame();
    return true;
  }

  function ensureFogCanvas(env) {
    const existing = typeof env.getFogCanvas === 'function' ? env.getFogCanvas() : null;
    if (existing) {
      return { fogCanvas: existing, fogCtx: typeof env.getFogCtx === 'function' ? env.getFogCtx() : null };
    }
    if (!env || !env.document) return { fogCanvas: null, fogCtx: null };
    const fogCanvas = env.document.createElement('canvas');
    const fogCtx = fogCanvas.getContext('2d');
    if (typeof env.setFogCanvas === 'function') env.setFogCanvas(fogCanvas);
    if (typeof env.setFogCtx === 'function') env.setFogCtx(fogCtx);
    const canvas = getCanvas(env);
    if (canvas) {
      fogCanvas.width = canvas.width;
      fogCanvas.height = canvas.height;
    }
    return { fogCanvas, fogCtx };
  }

  function bindCanvasEvents(env) {
    const wrap = getWrap(env);
    if (!wrap || wrap.dataset.renderBootBound === '1') return false;
    wrap.dataset.renderBootBound = '1';
    wrap.addEventListener('mousedown', env.onMouseDown);
    wrap.addEventListener('mousemove', env.onMouseMove);
    wrap.addEventListener('mouseup', env.onMouseUp);
    wrap.addEventListener('contextmenu', env.onRightClick);
    wrap.addEventListener('wheel', env.onWheel, { passive: false });
    wrap.addEventListener('dblclick', (e) => {
      e.preventDefault();
      if (typeof env.onDoubleClick === 'function') env.onDoubleClick(e);
    });
    return true;
  }

  function bindGlobalRenderEvents(env) {
    const doc = env && env.document ? env.document : null;
    if (doc && doc.body && doc.body.dataset.renderBootFinalizersBound !== '1') {
      doc.body.dataset.renderBootFinalizersBound = '1';
      if (typeof env.onDocumentMouseUp === 'function') doc.addEventListener('mouseup', env.onDocumentMouseUp);
      if (typeof env.onBlur === 'function') global.addEventListener('blur', env.onBlur);
    }
    return true;
  }

  function bindResize(env) {
    if (global.__appRenderBootResizeBound) return false;
    global.__appRenderBootResizeBound = true;
    global.addEventListener('resize', () => resizeCanvas(env));
    return true;
  }

  function startRenderLoop(drawLoop) {
    if (typeof drawLoop !== 'function') return null;
    return global.requestAnimationFrame(drawLoop);
  }

  function ensureLoopStarted(env) {
    if (!env) return false;
    if (typeof env.isLoopStarted === 'function' && env.isLoopStarted()) return false;
    if (typeof env.setLoopStarted === 'function') env.setLoopStarted(true);
    startRenderLoop(env.drawLoop);
    return true;
  }

  function initCanvas(env) {
    resizeCanvas(env);
    ensureFogCanvas(env);
    bindCanvasEvents(env);
    bindGlobalRenderEvents(env);
    bindResize(env);
    ensureLoopStarted(env);
  }

  global.AppRenderBoot = {
    initCanvas,
    resizeCanvas,
    ensureFogCanvas,
    bindCanvasEvents,
    bindGlobalRenderEvents,
    bindResize,
    ensureLoopStarted,
    startRenderLoop,
  };
})(window);
