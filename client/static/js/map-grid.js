// map-grid.js
// Tavern Tabletop — Canvas Grid Overlay Renderer
// Draws grid lines exactly aligned to map's grid_px metadata

(function() {
  'use strict';

  class MapGridRenderer {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.currentMap = null;
      this.visible = true;
      this.color = 'rgba(0, 0, 0, 0.25)';
      this.lineWidth = 0.5;
    }

    // Load a map — sets canvas size to match image display size
    setMap(mapMeta, displayWidth, displayHeight) {
      this.currentMap = mapMeta;
      this.canvas.width = displayWidth;
      this.canvas.height = displayHeight;
      this.render();
    }

    // Calculate scale factor from source grid_px to display size
    getScale(displayWidth) {
      if (!this.currentMap) return 1;
      var sourceWidth = this.currentMap.width_cells * this.currentMap.grid_px;
      return displayWidth / sourceWidth;
    }

    render() {
      if (!this.currentMap || !this.visible) return;
      var ctx = this.ctx;
      var canvas = this.canvas;

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      var scale = this.getScale(canvas.width);
      var cellPx = this.currentMap.grid_px * scale;

      ctx.strokeStyle = this.color;
      ctx.lineWidth = this.lineWidth;
      ctx.beginPath();

      // Vertical lines
      for (var x = 0; x <= this.currentMap.width_cells; x++) {
        var px = Math.round(x * cellPx) + 0.5;
        ctx.moveTo(px, 0);
        ctx.lineTo(px, canvas.height);
      }

      // Horizontal lines
      for (var y = 0; y <= this.currentMap.height_cells; y++) {
        var py = Math.round(y * cellPx) + 0.5;
        ctx.moveTo(0, py);
        ctx.lineTo(canvas.width, py);
      }

      ctx.stroke();
    }

    setVisible(visible) {
      this.visible = visible;
      this.render();
    }

    setColor(color) {
      this.color = color;
      this.render();
    }

    // Convert pixel position to cell coordinate
    pixelToCell(px, py) {
      if (!this.currentMap) return null;
      var scale = this.getScale(this.canvas.width);
      var cellPx = this.currentMap.grid_px * scale;
      return {
        col: Math.floor(px / cellPx),
        row: Math.floor(py / cellPx)
      };
    }

    // Convert cell coordinate to pixel position (top-left of cell)
    cellToPixel(col, row) {
      if (!this.currentMap) return null;
      var scale = this.getScale(this.canvas.width);
      var cellPx = this.currentMap.grid_px * scale;
      return {
        x: col * cellPx,
        y: row * cellPx
      };
    }
  }

  window.MapGridRenderer = MapGridRenderer;
})();
