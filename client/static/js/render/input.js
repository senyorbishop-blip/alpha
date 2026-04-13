(function (global) {
  'use strict';

  function getCanvasClientPoint(evt, canvas) {
    const rect = canvas.getBoundingClientRect();
    return {
      rect,
      x: evt.clientX - rect.left,
      y: evt.clientY - rect.top,
    };
  }

  function getCanvasPixelPoint(evt, canvas) {
    const point = getCanvasClientPoint(evt, canvas);
    const rect = point.rect;
    const safeWidth = rect.width || canvas.clientWidth || canvas.width || 1;
    const safeHeight = rect.height || canvas.clientHeight || canvas.height || 1;
    const scaleX = (canvas.width || 1) / safeWidth;
    const scaleY = (canvas.height || 1) / safeHeight;
    return {
      x: point.x * scaleX,
      y: point.y * scaleY,
    };
  }

  function screenToWorldFromEvent(evt, canvas, cam) {
    const point = getCanvasPixelPoint(evt, canvas);
    return {
      x: (point.x - canvas.width / 2) / cam.zoom + cam.x,
      y: (point.y - canvas.height / 2) / cam.zoom + cam.y,
    };
  }

  global.AppRenderInput = {
    getCanvasClientPoint,
    getCanvasPixelPoint,
    getMouseWorldFromEvent: screenToWorldFromEvent,
  };
})(window);
