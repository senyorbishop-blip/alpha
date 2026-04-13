/**
 * dnd_assets.js
 * Procedural DnD tactical map asset library.
 * Exports `terrain`, `props`, and `assetManifest`.
 *
 * Terrain functions return a 96×96 OffscreenCanvas (or regular Canvas).
 * Prop functions return a canvas whose size varies by prop type.
 * All variation is baked at draw time — callers must NOT apply random
 * rotation or UV offsets; tiling is UV-anchored by the renderer.
 */
(function () {
  'use strict';

  // ─── PNG image cache for prop overrides ──────────────────────────────────
  // Prop PNG overrides can come from:
  //  - /vtt_single_props/<filename>.png (preferred runtime pack)
  //  - /static/assets/props/<key>.png (legacy fallback)
  // If the file exists, the PNG is drawn onto the canvas instead of the
  // procedural fallback. The canvas is mutated in-place when the image loads
  // so the asset cache automatically picks up the update on the next render.
  const _imgCache = {};
  const PROP_IMAGE_VERSION = '20260401';
  const PROP_IMAGE_REV = 'h';
  function _versionedPropPath(path) {
    const raw = String(path || '').trim();
    if (!raw) return '';
    return `${raw}${raw.includes('?') ? '&' : '?'}v=${PROP_IMAGE_VERSION}${PROP_IMAGE_REV}`;
  }
  const _propImageOverrides = Object.freeze({
    chest: '/static/assets/props/chest_closed.png',
    mimic: '/static/assets/props/mimic_revealed.png',
    guild_board: '/static/assets/props/guild_board.png',
    guildboard: '/vtt_single_props/guild_board.png',
    quest_board: '/vtt_single_props/guild_board.png',
    shop: '/static/assets/props/shop_stall.png',
    merchant: '/vtt_single_props/shop_stall.png',
    market_stall: '/vtt_single_props/shop_stall.png',
    shop_front: '/vtt_single_props/shop_stall.png',
    store: '/vtt_single_props/shop_stall.png',
    barrel: '/static/assets/props/barrel.png',
    door: '/static/assets/props/door.png',
    table: '/static/assets/props/table.png',
    torch: '/static/assets/props/torch.png',
    campfire: '/static/assets/props/campfire.png',
    crate: '/static/assets/props/crate_topdown.png',
    bookshelf: '/static/assets/props/bookshelf.png',
    bookcase: '/vtt_single_props/bookshelf.png',
  });
  function _getPropImg(key) {
    if (!_imgCache[key]) {
      const img = new Image();
      img.decoding = 'async';
      img.loading = 'eager';
      img.src = _versionedPropPath(_propImageOverrides[key] || ('/vtt_single_props/' + key + '.png'));
      _imgCache[key] = img;
    }
    return _imgCache[key];
  }
  /** Draw img into canvas g (size×size), or run fallbackFn if not yet loaded. */
  function _drawOrFallback(c, g, size, key, fallbackFn) {
    const img = _getPropImg(key);
    if (img.complete && img.naturalWidth > 0) {
      g.drawImage(img, 0, 0, size, size);
    } else {
      fallbackFn();
      if (!img._listenerAdded) {
        img._listenerAdded = true;
        img.onload = function () {
          g.clearRect(0, 0, size, size);
          g.drawImage(img, 0, 0, size, size);
          // Invalidate asset cache so the next map render picks up the image.
          if (window.DndAssetCache) window.DndAssetCache[key] = c;
          window.dispatchEvent(new CustomEvent('dnd-prop-image-loaded', { detail: { id: key } }));
        };
        img.onerror = function () {};
      }
    }
  }

  // ─── Tiny Perlin noise ────────────────────────────────────────────────────
  /**
   * Returns a seeded deterministic noise value in [–1, 1] for (x, y).
   * Based on a classic hash-gradient approach (no lookup table needed).
   * @param {number} x
   * @param {number} y
   * @param {number} [seed=0]
   * @returns {number}
   */
  function noise2(x, y, seed = 0) {
    const fx = Math.floor(x), fy = Math.floor(y);
    const rx = x - fx, ry = y - fy;
    const fade = t => t * t * t * (t * (t * 6 - 15) + 10);
    const ux = fade(rx), uy = fade(ry);
    function grad(ix, iy) {
      let h = (ix * 1619 + iy * 31337 + seed * 1013) | 0;
      h ^= h << 13; h ^= h >> 17; h ^= h << 5;
      const gx = ((h & 1) ? 1 : -1) * (1 + (h & 7));
      const gy = ((h & 2) ? 1 : -1) * (1 + ((h >> 3) & 7));
      const len = Math.sqrt(gx * gx + gy * gy);
      return (gx / len) * (x - ix) + (gy / len) * (y - iy);
    }
    const n00 = grad(fx,     fy);
    const n10 = grad(fx + 1, fy);
    const n01 = grad(fx,     fy + 1);
    const n11 = grad(fx + 1, fy + 1);
    const lerp = (a, b, t) => a + t * (b - a);
    return lerp(lerp(n00, n10, ux), lerp(n01, n11, ux), uy);
  }

  /** Fractional Brownian Motion — sum of noise octaves. */
  function fbm(x, y, octaves = 4, seed = 0) {
    let v = 0, amp = 1, freq = 1, max = 0;
    for (let i = 0; i < octaves; i++) {
      v += noise2(x * freq, y * freq, seed + i * 997) * amp;
      max += amp;
      amp *= 0.5;
      freq *= 2;
    }
    return v / max; // normalised to [–1, 1]
  }

  /** Make an OffscreenCanvas if available, else fall back to regular canvas. */
  function makeCanvas(w, h) {
    if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
    const c = document.createElement('canvas');
    c.width = w; c.height = h;
    return c;
  }

  const TILE = 96;

  // ─── Terrain functions ────────────────────────────────────────────────────

  /**
   * Stone/dungeon floor tile.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function stone() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 18, py / 18, 4, 1);
        const v = Math.floor(60 + n * 28);
        g.fillStyle = `rgb(${v + 4},${v},${v + 8})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // mortar lines
    g.strokeStyle = 'rgba(20,18,26,0.55)';
    g.lineWidth = 1;
    const bw = 24, bh = 16;
    for (let row = 0; row * bh < TILE + bh; row++) {
      const offX = (row % 2) * (bw / 2);
      for (let col = -1; col * bw < TILE + bw; col++) {
        const bx = col * bw + offX, by = row * bh;
        g.strokeRect(bx + 0.5, by + 0.5, bw - 1, bh - 1);
      }
    }
    return c;
  }

  /**
   * Dirt / road tile.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function dirt() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 14, py / 14, 3, 2);
        const r = Math.floor(130 + n * 22);
        const gr = Math.floor(96 + n * 16);
        const b  = Math.floor(60 + n * 12);
        g.fillStyle = `rgb(${r},${gr},${b})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // small pebble marks
    g.fillStyle = 'rgba(80,62,42,0.35)';
    for (let i = 0; i < 14; i++) {
      const nx = noise2(i * 3.7, 0.5, 99) * 0.5 + 0.5;
      const ny = noise2(0.5, i * 3.7, 199) * 0.5 + 0.5;
      const pr = 1.5 + Math.abs(noise2(i, i, 42)) * 2;
      g.beginPath();
      g.arc(nx * TILE, ny * TILE, pr, 0, Math.PI * 2);
      g.fill();
    }
    return c;
  }

  /**
   * Grass tile.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function grass() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 16, py / 16, 4, 3);
        const r = Math.floor(52 + n * 14);
        const gr = Math.floor(110 + n * 30);
        const b  = Math.floor(44 + n * 10);
        g.fillStyle = `rgb(${r},${gr},${b})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // blade tufts
    g.strokeStyle = 'rgba(68,148,56,0.52)';
    g.lineWidth = 1;
    for (let i = 0; i < 20; i++) {
      const bx = (noise2(i, 0, 55) * 0.5 + 0.5) * TILE;
      const by = (noise2(0, i, 66) * 0.5 + 0.5) * TILE;
      g.beginPath(); g.moveTo(bx, by + 4); g.lineTo(bx - 2, by); g.stroke();
      g.beginPath(); g.moveTo(bx, by + 4); g.lineTo(bx + 2, by - 2); g.stroke();
    }
    return c;
  }

  /**
   * Water tile.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function water() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 12, py / 10, 3, 4);
        const r = Math.floor(28 + n * 12);
        const gr = Math.floor(88 + n * 28);
        const b  = Math.floor(180 + n * 40);
        g.fillStyle = `rgb(${r},${gr},${b})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // wave highlights
    g.strokeStyle = 'rgba(180,240,255,0.28)';
    g.lineWidth = 1;
    for (let row = 0; row < 6; row++) {
      const wy = 8 + row * 14;
      g.beginPath();
      for (let px = 0; px <= TILE; px += 4) {
        const dy = noise2(px / 10, row, 77) * 3;
        if (px === 0) g.moveTo(px, wy + dy);
        else g.lineTo(px, wy + dy);
      }
      g.stroke();
    }
    return c;
  }

  /**
   * Forest ground tile.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function forestGround() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 14, py / 14, 4, 5);
        const r = Math.floor(38 + n * 16);
        const gr = Math.floor(78 + n * 28);
        const b  = Math.floor(32 + n * 10);
        g.fillStyle = `rgb(${r},${gr},${b})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // leaf litter
    g.fillStyle = 'rgba(42,96,34,0.5)';
    for (let i = 0; i < 18; i++) {
      const lx = (noise2(i * 2.1, 0.3, 88) * 0.5 + 0.5) * TILE;
      const ly = (noise2(0.3, i * 2.1, 99) * 0.5 + 0.5) * TILE;
      g.beginPath(); g.ellipse(lx, ly, 4, 2.5, noise2(i, i, 7) * Math.PI, 0, Math.PI * 2); g.fill();
    }
    return c;
  }

  /**
   * Cave stone tile.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function caveStone() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 16, py / 16, 5, 6);
        const v = Math.floor(46 + n * 22);
        g.fillStyle = `rgb(${v},${v},${v + 6})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // crack lines
    g.strokeStyle = 'rgba(10,8,14,0.48)';
    g.lineWidth = 1;
    for (let i = 0; i < 5; i++) {
      const sx = (noise2(i, 0, 11) * 0.5 + 0.5) * TILE;
      const sy = (noise2(0, i, 22) * 0.5 + 0.5) * TILE;
      g.beginPath(); g.moveTo(sx, sy);
      for (let s = 1; s < 6; s++) {
        g.lineTo(
          sx + noise2(s, i, 33) * 18,
          sy + s * 10 + noise2(s, i, 44) * 8
        );
      }
      g.stroke();
    }
    return c;
  }

  /**
   * Desert sand tile.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function sand() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 20, py / 20, 3, 7);
        const r = Math.floor(210 + n * 20);
        const gr = Math.floor(178 + n * 18);
        const b  = Math.floor(120 + n * 14);
        g.fillStyle = `rgb(${r},${gr},${b})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // ripple marks
    g.strokeStyle = 'rgba(230,200,130,0.28)';
    g.lineWidth = 1;
    for (let row = 0; row < 5; row++) {
      const ry = 10 + row * 18;
      g.beginPath();
      for (let px = 0; px <= TILE; px += 3) {
        const dy = noise2(px / 14, row * 2, 55) * 4;
        if (px === 0) g.moveTo(px, ry + dy);
        else g.lineTo(px, ry + dy);
      }
      g.stroke();
    }
    return c;
  }

  /**
   * Lava tile.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function lava() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 10, py / 10, 4, 8);
        const t = (n + 1) / 2; // 0..1
        const r = Math.floor(180 + t * 70);
        const gr = Math.floor(40 + t * 60);
        const b  = Math.floor(10 + t * 10);
        g.fillStyle = `rgb(${r},${gr},${b})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // bright flow cores
    g.fillStyle = 'rgba(255,200,60,0.28)';
    for (let i = 0; i < 8; i++) {
      const bx = (noise2(i, 0.1, 33) * 0.5 + 0.5) * TILE;
      const by = (noise2(0.1, i, 44) * 0.5 + 0.5) * TILE;
      const rad = 6 + Math.abs(noise2(i, i, 55)) * 10;
      g.beginPath();
      g.arc(bx, by, rad, 0, Math.PI * 2);
      g.fill();
    }
    return c;
  }

  /**
   * Hills terrain tile — rolling green with ridge contours and warm highlights.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function hills() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    // Base: warm green with yellowish ridge peaks
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 22, py / 22, 5, 12);
        const peak = fbm(px / 10, py / 10, 3, 99);
        const t = (n + 1) / 2;
        const r = Math.floor(58 + t * 36 + peak * 18);
        const gr = Math.floor(104 + t * 44 + peak * 20);
        const b  = Math.floor(30 + t * 16 + peak * 6);
        g.fillStyle = `rgb(${Math.min(255,r)},${Math.min(255,gr)},${Math.min(255,b)})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // Contour lines suggesting elevation bands
    g.strokeStyle = 'rgba(80,110,40,0.32)';
    g.lineWidth = 1;
    for (let band = 0; band < 4; band++) {
      g.beginPath();
      let first = true;
      for (let px = 0; px <= TILE; px += 2) {
        const ny = (band * 22) + noise2(px / 14, band, 77) * 9 + noise2(px / 6, band * 2, 43) * 5;
        if (first) { g.moveTo(px, ny); first = false; } else g.lineTo(px, ny);
      }
      g.stroke();
    }
    // Sparse grass tufts
    g.strokeStyle = 'rgba(100,160,50,0.42)';
    g.lineWidth = 1;
    for (let i = 0; i < 12; i++) {
      const bx = (noise2(i * 3.1, 0.5, 33) * 0.5 + 0.5) * TILE;
      const by = (noise2(0.5, i * 3.1, 44) * 0.5 + 0.5) * TILE;
      g.beginPath(); g.moveTo(bx, by + 5); g.lineTo(bx - 3, by); g.stroke();
      g.beginPath(); g.moveTo(bx, by + 5); g.lineTo(bx + 3, by - 1); g.stroke();
    }
    return c;
  }

  /**
   * Mountains terrain tile — jagged grey rock with snow-cap highlights.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function mountains() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    // Rocky base — cool grey with subtle warm undertone
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 12, py / 12, 6, 17);
        const n2 = fbm(px / 5, py / 5, 3, 99);
        const v = Math.floor(78 + n * 38 + n2 * 14);
        g.fillStyle = `rgb(${Math.min(255,v+6)},${Math.min(255,v+2)},${Math.min(255,v+14)})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // Angular crack lines
    g.strokeStyle = 'rgba(20,18,28,0.42)';
    g.lineWidth = 1;
    for (let i = 0; i < 8; i++) {
      const sx = (noise2(i, 0.1, 55) * 0.5 + 0.5) * TILE;
      const sy = (noise2(0.1, i, 66) * 0.5 + 0.5) * TILE;
      g.beginPath(); g.moveTo(sx, sy);
      for (let s = 1; s <= 5; s++) {
        g.lineTo(sx + noise2(s, i, 33) * 14, sy + s * 8 + noise2(s, i, 44) * 6);
      }
      g.stroke();
    }
    // Snow-cap highlights on upper faces
    g.fillStyle = 'rgba(230,238,255,0.22)';
    for (let i = 0; i < 7; i++) {
      const cx = (noise2(i * 2, 0, 11) * 0.5 + 0.5) * TILE;
      const cy = (noise2(0, i * 2, 22) * 0.5 + 0.5) * (TILE * 0.55);
      const rx = 6 + Math.abs(noise2(i, i, 5)) * 8;
      const ry = 3 + Math.abs(noise2(i, i, 6)) * 4;
      g.beginPath(); g.ellipse(cx, cy, rx, ry, noise2(i, i, 7) * 0.8, 0, Math.PI * 2); g.fill();
    }
    return c;
  }

  /**
   * Swamp terrain tile — murky dark green-brown with algae pools.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function swamp() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    // Murky mud base
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 16, py / 16, 4, 21);
        const wet = fbm(px / 8, py / 8, 3, 77);
        const r = Math.floor(44 + n * 20 + wet * 8);
        const gr = Math.floor(62 + n * 24 + wet * 14);
        const b  = Math.floor(28 + n * 10 + wet * 6);
        g.fillStyle = `rgb(${Math.min(255,r)},${Math.min(255,gr)},${Math.min(255,b)})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // Dark algae-covered water pools
    g.fillStyle = 'rgba(30,58,26,0.52)';
    for (let i = 0; i < 5; i++) {
      const px = (noise2(i * 2.3, 0, 55) * 0.5 + 0.5) * TILE;
      const py = (noise2(0, i * 2.3, 66) * 0.5 + 0.5) * TILE;
      const rx = 8 + Math.abs(noise2(i, i, 7)) * 10;
      const ry = 5 + Math.abs(noise2(i, i, 8)) * 7;
      g.beginPath(); g.ellipse(px, py, rx, ry, noise2(i, i, 9) * Math.PI, 0, Math.PI * 2); g.fill();
    }
    // Bright green algae specks
    g.fillStyle = 'rgba(58,120,40,0.42)';
    for (let i = 0; i < 14; i++) {
      const ax = (noise2(i, 0.7, 33) * 0.5 + 0.5) * TILE;
      const ay = (noise2(0.7, i, 44) * 0.5 + 0.5) * TILE;
      g.beginPath(); g.ellipse(ax, ay, 2.5, 1.5, noise2(i, i, 1) * Math.PI, 0, Math.PI * 2); g.fill();
    }
    // Murky ripple lines
    g.strokeStyle = 'rgba(90,130,60,0.22)';
    g.lineWidth = 1;
    for (let row = 0; row < 4; row++) {
      const wy = 10 + row * 20;
      g.beginPath();
      for (let px = 0; px <= TILE; px += 4) {
        const dy = noise2(px / 10, row, 88) * 3;
        if (px === 0) g.moveTo(px, wy + dy); else g.lineTo(px, wy + dy);
      }
      g.stroke();
    }
    return c;
  }

  /**
   * Snow / Ice terrain tile — crystalline white-blue with ice crack patterns.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function snow() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    // Bright icy base
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 20, py / 20, 4, 29);
        const shine = fbm(px / 8, py / 8, 2, 111);
        const r = Math.floor(210 + n * 22 + shine * 18);
        const gr = Math.floor(220 + n * 18 + shine * 14);
        const b  = Math.floor(235 + n * 14 + shine * 12);
        g.fillStyle = `rgb(${Math.min(255,r)},${Math.min(255,gr)},${Math.min(255,b)})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // Ice crack lines
    g.strokeStyle = 'rgba(140,180,220,0.45)';
    g.lineWidth = 0.8;
    for (let i = 0; i < 6; i++) {
      const sx = (noise2(i, 0.2, 11) * 0.5 + 0.5) * TILE;
      const sy = (noise2(0.2, i, 22) * 0.5 + 0.5) * TILE;
      g.beginPath(); g.moveTo(sx, sy);
      for (let s = 1; s <= 4; s++) {
        g.lineTo(sx + noise2(s, i, 33) * 16, sy + s * 10 + noise2(s, i, 44) * 8);
      }
      g.stroke();
    }
    // Sparkle highlights
    g.fillStyle = 'rgba(255,255,255,0.72)';
    for (let i = 0; i < 18; i++) {
      const sx = (noise2(i * 2.7, 0.3, 55) * 0.5 + 0.5) * TILE;
      const sy = (noise2(0.3, i * 2.7, 66) * 0.5 + 0.5) * TILE;
      const r = 0.8 + Math.abs(noise2(i, i, 77)) * 1.4;
      g.beginPath(); g.arc(sx, sy, r, 0, Math.PI * 2); g.fill();
    }
    // Blue-shadow tint in hollows
    g.fillStyle = 'rgba(180,210,240,0.14)';
    for (let i = 0; i < 6; i++) {
      const hx = (noise2(i * 3, 0, 88) * 0.5 + 0.5) * TILE;
      const hy = (noise2(0, i * 3, 99) * 0.5 + 0.5) * TILE;
      const hr = 8 + Math.abs(noise2(i, i, 5)) * 10;
      g.beginPath(); g.arc(hx, hy, hr, 0, Math.PI * 2); g.fill();
    }
    return c;
  }

  /**
   * Shallows terrain tile — translucent turquoise over sandy bottom with ripples.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function shallows() {
    const c = makeCanvas(TILE, TILE);
    const g = c.getContext('2d');
    // Sandy bottom base
    for (let py = 0; py < TILE; py++) {
      for (let px = 0; px < TILE; px++) {
        const n = fbm(px / 18, py / 18, 3, 37);
        const r = Math.floor(175 + n * 22);
        const gr = Math.floor(195 + n * 18);
        const b  = Math.floor(160 + n * 14);
        g.fillStyle = `rgb(${Math.min(255,r)},${Math.min(255,gr)},${Math.min(255,b)})`;
        g.fillRect(px, py, 1, 1);
      }
    }
    // Turquoise water overlay
    const waterGrad = g.createLinearGradient(0, 0, 0, TILE);
    waterGrad.addColorStop(0, 'rgba(60,190,200,0.46)');
    waterGrad.addColorStop(1, 'rgba(30,155,180,0.40)');
    g.fillStyle = waterGrad;
    g.fillRect(0, 0, TILE, TILE);
    // Gentle wave ripples
    g.strokeStyle = 'rgba(220,255,255,0.38)';
    g.lineWidth = 1;
    for (let row = 0; row < 5; row++) {
      const wy = 6 + row * 17;
      g.beginPath();
      for (let px = 0; px <= TILE; px += 3) {
        const dy = noise2(px / 12, row, 55) * 2.5;
        if (px === 0) g.moveTo(px, wy + dy); else g.lineTo(px, wy + dy);
      }
      g.stroke();
    }
    // Sandy patches visible through clear water
    g.fillStyle = 'rgba(210,210,160,0.20)';
    for (let i = 0; i < 6; i++) {
      const sx = (noise2(i * 2.5, 0.4, 33) * 0.5 + 0.5) * TILE;
      const sy = (noise2(0.4, i * 2.5, 44) * 0.5 + 0.5) * TILE;
      const rx = 6 + Math.abs(noise2(i, i, 7)) * 9;
      const ry = 4 + Math.abs(noise2(i, i, 8)) * 6;
      g.beginPath(); g.ellipse(sx, sy, rx, ry, noise2(i, i, 9) * Math.PI, 0, Math.PI * 2); g.fill();
    }
    return c;
  }

  // ─── Prop functions ───────────────────────────────────────────────────────

  function makeSquare(px) {
    const c = makeCanvas(px, px);
    return { c, g: c.getContext('2d') };
  }

  /**
   * Stone wall segment.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function wallStone() {
    const { c, g } = makeSquare(50);
    g.fillStyle = 'rgb(70,72,84)';
    g.fillRect(0, 0, 50, 50);
    g.strokeStyle = 'rgba(20,18,28,0.72)';
    g.lineWidth = 1.5;
    const bw = 16, bh = 12;
    for (let row = 0; row * bh < 52; row++) {
      const ox = (row % 2) * (bw / 2);
      for (let col = -1; col * bw < 52; col++) {
        g.strokeRect(col * bw + ox + 0.5, row * bh + 0.5, bw - 1, bh - 1);
      }
    }
    g.strokeStyle = 'rgba(200,205,220,0.16)';
    g.lineWidth = 1;
    g.strokeRect(1, 1, 48, 48);
    return c;
  }

  /**
   * Wood wall segment.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function wallWood() {
    const { c, g } = makeSquare(50);
    const planks = 5, pw = 50 / planks;
    for (let i = 0; i < planks; i++) {
      const n = noise2(i, 0.5, 22);
      const r = Math.floor(100 + n * 20);
      const gr = Math.floor(66 + n * 14);
      const b  = Math.floor(38 + n * 8);
      g.fillStyle = `rgb(${r},${gr},${b})`;
      g.fillRect(i * pw, 0, pw, 50);
      g.strokeStyle = 'rgba(30,18,10,0.55)';
      g.lineWidth = 1;
      g.strokeRect(i * pw + 0.5, 0.5, pw - 1, 49);
    }
    // grain lines
    g.strokeStyle = 'rgba(80,52,28,0.28)';
    g.lineWidth = 0.5;
    for (let i = 0; i < 6; i++) {
      const gy = 8 + i * 7;
      g.beginPath(); g.moveTo(2, gy); g.lineTo(48, gy + noise2(i, 1, 9) * 4); g.stroke();
    }
    return c;
  }

  /**
   * Door prop.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function door() {
    const size = 50;
    const c = makeCanvas(size, size);
    const g = c.getContext('2d');
    _drawOrFallback(c, g, size, 'door', function () {
      g.fillStyle = 'rgb(115,70,32)';
      g.fillRect(6, 2, 38, 46);
      g.strokeStyle = 'rgba(220,180,100,0.85)';
      g.lineWidth = 2;
      g.strokeRect(6.5, 2.5, 37, 45);
      g.strokeStyle = 'rgba(220,180,100,0.55)';
      g.lineWidth = 1;
      g.strokeRect(10, 6, 14, 18);
      g.strokeRect(26, 6, 14, 18);
      g.strokeRect(10, 28, 14, 16);
      g.strokeRect(26, 28, 14, 16);
      g.fillStyle = 'rgba(240,200,80,0.9)';
      g.beginPath(); g.arc(35, 25, 3, 0, Math.PI * 2); g.fill();
    });
    return c;
  }

  /**
   * Chest prop. Uses chest.png when available, procedural fallback otherwise.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function chest() {
    const size = 50;
    const c = makeCanvas(size, size);
    const g = c.getContext('2d');
    _drawOrFallback(c, g, size, 'chest', function () {
      g.fillStyle = 'rgb(118,76,38)';
      g.fillRect(5, 12, 40, 28);
      g.fillStyle = 'rgb(98,56,22)';
      g.fillRect(5, 12, 40, 10);
      g.strokeStyle = 'rgba(230,195,100,0.85)';
      g.lineWidth = 2;
      g.strokeRect(5.5, 12.5, 39, 27);
      g.strokeRect(5.5, 12.5, 39, 10);
      // bands
      g.strokeStyle = 'rgba(180,130,40,0.7)';
      g.lineWidth = 2;
      g.beginPath(); g.moveTo(22, 12); g.lineTo(22, 40); g.stroke();
      g.beginPath(); g.moveTo(28, 12); g.lineTo(28, 40); g.stroke();
      // lock
      g.fillStyle = 'rgba(240,210,70,0.92)';
      g.fillRect(22, 23, 6, 5);
    });
    return c;
  }

  /**
   * Table prop.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function table() {
    const size = 100;
    const c = makeCanvas(size, size);
    const g = c.getContext('2d');
    _drawOrFallback(c, g, size, 'table', function () {
      g.fillStyle = 'rgb(102,64,32)';
      g.fillRect(8, 16, 84, 60);
      g.strokeStyle = 'rgba(220,190,130,0.8)';
      g.lineWidth = 2;
      g.strokeRect(8.5, 16.5, 83, 59);
      g.fillStyle = 'rgb(80,50,22)';
      [[10,72],[82,72],[10,22],[82,22]].forEach(([lx,ly]) => g.fillRect(lx, ly, 8, 12));
    });
    return c;
  }

  /**
   * Barrel prop.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function barrel() {
    const size = 50;
    const c = makeCanvas(size, size);
    const g = c.getContext('2d');
    _drawOrFallback(c, g, size, 'barrel', function () {
      g.fillStyle = 'rgb(118,72,36)';
      g.fillRect(14, 6, 22, 38);
      g.strokeStyle = 'rgba(220,190,110,0.8)';
      g.lineWidth = 2;
      g.strokeRect(14.5, 6.5, 21, 37);
      g.strokeStyle = 'rgba(180,130,42,0.72)';
      g.lineWidth = 2;
      [14, 24, 34].forEach(y => {
        g.beginPath(); g.moveTo(14, y); g.lineTo(36, y); g.stroke();
      });
    });
    return c;
  }

  /**
   * Crate prop.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function crate() {
    const size = 50;
    const c = makeCanvas(size, size);
    const g = c.getContext('2d');
    _drawOrFallback(c, g, size, 'crate', function () {
      g.fillStyle = 'rgb(130,88,44)';
      g.fillRect(5, 5, 40, 40);
      g.strokeStyle = 'rgba(220,195,130,0.75)';
      g.lineWidth = 2;
      g.strokeRect(5.5, 5.5, 39, 39);
      g.beginPath(); g.moveTo(5, 5); g.lineTo(45, 45); g.moveTo(45, 5); g.lineTo(5, 45); g.stroke();
    });
    return c;
  }

  /**
   * Torch wall sconce.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function torch() {
    const { c, g } = makeSquare(50);
    // bracket
    g.fillStyle = 'rgb(80,64,48)';
    g.fillRect(21, 28, 8, 16);
    // flame
    const grad = g.createRadialGradient(25, 22, 2, 25, 28, 12);
    grad.addColorStop(0, 'rgba(255,230,100,0.95)');
    grad.addColorStop(0.5, 'rgba(255,130,30,0.72)');
    grad.addColorStop(1, 'rgba(200,50,10,0)');
    g.fillStyle = grad;
    g.beginPath();
    g.moveTo(25, 10); g.bezierCurveTo(32, 16, 34, 24, 25, 28);
    g.bezierCurveTo(16, 24, 18, 16, 25, 10);
    g.closePath(); g.fill();
    return c;
  }

  /**
   * Bookshelf / bookcase prop.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function bookshelf() {
    const size = 100;
    const c = makeCanvas(size, size);
    const g = c.getContext('2d');
    _drawOrFallback(c, g, size, 'bookshelf', function () {
      g.fillStyle = 'rgb(90,56,24)';
      g.fillRect(4, 4, 92, 92);
      g.strokeStyle = 'rgba(200,170,100,0.8)';
      g.lineWidth = 2;
      g.strokeRect(4.5, 4.5, 91, 91);
      const cols = ['#c44','#4a8','#48c','#a84','#884','#c84','#68c','#ca4'];
      let bx = 8;
      for (let i = 0; i < 12; i++) {
        const bh = 18 + (i % 3) * 6;
        const by = 8 + (i < 6 ? 0 : 46);
        g.fillStyle = cols[i % cols.length];
        g.fillRect(bx, by, 6, bh);
        bx += 7;
        if (bx > 88) bx = 8;
      }
      g.strokeStyle = 'rgba(180,140,70,0.6)';
      g.lineWidth = 2;
      g.beginPath(); g.moveTo(4, 50); g.lineTo(96, 50); g.stroke();
    });
    return c;
  }

  /**
   * Altar / pedestal prop.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function altar() {
    const { c, g } = makeSquare(100);
    // base
    g.fillStyle = 'rgb(100,95,110)';
    g.fillRect(8, 60, 84, 32);
    g.strokeStyle = 'rgba(220,210,240,0.6)';
    g.lineWidth = 2;
    g.strokeRect(8.5, 60.5, 83, 31);
    // top surface
    g.fillStyle = 'rgb(130,124,148)';
    g.fillRect(14, 20, 72, 42);
    g.strokeStyle = 'rgba(220,210,240,0.55)';
    g.strokeRect(14.5, 20.5, 71, 41);
    // rune symbol
    g.strokeStyle = 'rgba(160,100,255,0.75)';
    g.lineWidth = 2;
    g.beginPath();
    g.moveTo(50, 30); g.lineTo(50, 56);
    g.moveTo(38, 43); g.lineTo(62, 43);
    g.moveTo(42, 33); g.lineTo(58, 53);
    g.moveTo(58, 33); g.lineTo(42, 53);
    g.stroke();
    return c;
  }

  /**
   * Shop stall prop with awning.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function shop() {
    const size = 150;
    const c = makeCanvas(size, size);
    const g = c.getContext('2d');
    _drawOrFallback(c, g, size, 'shop', function () {
      g.fillStyle = 'rgb(110,68,32)';
      g.fillRect(10, 70, 130, 60);
      g.strokeStyle = 'rgba(220,190,120,0.8)';
      g.lineWidth = 2;
      g.strokeRect(10.5, 70.5, 129, 59);
      const aw = g.createLinearGradient(10, 18, 140, 18);
      aw.addColorStop(0, 'rgba(180,40,40,0.92)');
      aw.addColorStop(0.5, 'rgba(220,60,40,0.92)');
      aw.addColorStop(1, 'rgba(180,40,40,0.92)');
      g.fillStyle = aw;
      g.beginPath();
      g.moveTo(10, 18); g.lineTo(140, 18); g.lineTo(130, 50); g.lineTo(20, 50);
      g.closePath(); g.fill();
      g.strokeStyle = 'rgba(255,230,160,0.45)';
      g.lineWidth = 2;
      for (let sx = 20; sx < 140; sx += 12) {
        g.beginPath(); g.moveTo(sx, 18); g.lineTo(sx - 6, 50); g.stroke();
      }
      g.fillStyle = 'rgba(240,220,160,0.92)';
      g.fillRect(46, 52, 58, 14);
      g.fillStyle = 'rgba(80,40,10,0.88)';
      g.font = 'bold 10px sans-serif';
      g.textAlign = 'center';
      g.fillText('SHOP', 75, 63);
    });
    return c;
  }

  /**
   * Well prop.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function well() {
    const { c, g } = makeSquare(100);
    // wall ring
    g.fillStyle = 'rgb(96,90,84)';
    g.beginPath(); g.arc(50, 52, 38, 0, Math.PI * 2); g.fill();
    g.fillStyle = 'rgb(22,20,28)';
    g.beginPath(); g.arc(50, 52, 24, 0, Math.PI * 2); g.fill();
    g.strokeStyle = 'rgba(200,195,185,0.65)';
    g.lineWidth = 2;
    g.beginPath(); g.arc(50, 52, 38, 0, Math.PI * 2); g.stroke();
    // roof posts
    g.fillStyle = 'rgb(88,54,24)';
    g.fillRect(12, 16, 8, 38); g.fillRect(80, 16, 8, 38);
    g.fillRect(12, 14, 76, 8);
    // rope
    g.strokeStyle = 'rgba(200,180,130,0.8)';
    g.lineWidth = 2;
    g.beginPath(); g.moveTo(50, 22); g.lineTo(50, 46); g.stroke();
    return c;
  }

  /**
   * Campfire prop.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function campfire() {
    const { c, g } = makeSquare(50);
    // stones
    g.fillStyle = 'rgb(96,94,100)';
    [[12,30],[38,30],[25,36],[16,38],[34,38]].forEach(([lx,ly]) => {
      g.beginPath(); g.ellipse(lx, ly, 5, 3.5, 0, 0, Math.PI*2); g.fill();
    });
    // logs
    g.strokeStyle = 'rgb(88,50,18)';
    g.lineWidth = 4;
    g.beginPath(); g.moveTo(12, 36); g.lineTo(38, 22); g.stroke();
    g.beginPath(); g.moveTo(38, 36); g.lineTo(12, 22); g.stroke();
    // flames
    const fl = g.createRadialGradient(25, 20, 2, 25, 28, 14);
    fl.addColorStop(0, 'rgba(255,230,90,0.98)');
    fl.addColorStop(0.45, 'rgba(255,110,20,0.8)');
    fl.addColorStop(1, 'rgba(180,30,0,0)');
    g.fillStyle = fl;
    g.beginPath();
    g.moveTo(25, 8); g.bezierCurveTo(33, 14, 36, 26, 25, 32);
    g.bezierCurveTo(14, 26, 17, 14, 25, 8);
    g.closePath(); g.fill();
    return c;
  }

  /**
   * Pillar / column prop.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function pillar() {
    const { c, g } = makeSquare(50);
    g.fillStyle = 'rgb(150,148,156)';
    g.fillRect(16, 6, 18, 38);
    g.fillStyle = 'rgb(130,128,138)';
    g.fillRect(14, 4, 22, 6);
    g.fillRect(14, 40, 22, 6);
    g.strokeStyle = 'rgba(220,218,230,0.55)';
    g.lineWidth = 1;
    g.strokeRect(16.5, 6.5, 17, 37);
    // fluting
    for (let i = 0; i < 3; i++) {
      g.beginPath();
      g.moveTo(20 + i * 3, 10); g.lineTo(20 + i * 3, 40);
      g.stroke();
    }
    return c;
  }

  /**
   * Guild board / quest board prop. Uses guild_board.png when available.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function guildBoard() {
    const size = 100;
    const c = makeCanvas(size, size);
    const g = c.getContext('2d');
    _drawOrFallback(c, g, size, 'guild_board', function () {
      // shadow
      g.fillStyle = 'rgba(0,0,0,0.18)';
      g.beginPath();
      g.ellipse(50, 90, 30, 7, 0, 0, Math.PI * 2);
      g.fill();
      // center post
      g.fillStyle = 'rgb(95,66,43)';
      g.fillRect(45, 30, 10, 60);
      g.fillStyle = 'rgba(55,36,22,0.45)';
      g.fillRect(48, 31, 2, 57);
      // board frame + backing
      g.fillStyle = 'rgb(122,87,58)';
      g.fillRect(18, 14, 64, 50);
      g.fillStyle = 'rgb(205,181,136)';
      g.fillRect(22, 18, 56, 42);
      // cross beams
      g.strokeStyle = 'rgba(96,68,44,0.55)';
      g.lineWidth = 2;
      g.beginPath();
      g.moveTo(24, 30); g.lineTo(76, 30);
      g.moveTo(24, 46); g.lineTo(76, 46);
      g.stroke();
      // pinned notes
      const notes = [
        { x: 27, y: 21, w: 14, h: 12 },
        { x: 43, y: 23, w: 16, h: 13 },
        { x: 61, y: 22, w: 13, h: 11 },
        { x: 30, y: 38, w: 17, h: 14 },
        { x: 50, y: 39, w: 19, h: 12 },
      ];
      notes.forEach((note, idx) => {
        g.fillStyle = idx % 2 ? 'rgba(247,239,218,0.96)' : 'rgba(240,230,200,0.96)';
        g.fillRect(note.x, note.y, note.w, note.h);
        g.fillStyle = 'rgba(116,92,56,0.28)';
        g.fillRect(note.x + 2, note.y + 3, Math.max(4, note.w - 4), 1);
        g.fillRect(note.x + 2, note.y + 6, Math.max(3, note.w - 6), 1);
        g.fillStyle = idx === 2 ? 'rgb(38,122,92)' : 'rgb(176,46,38)';
        g.beginPath();
        g.arc(note.x + Math.max(2, Math.floor(note.w * 0.5)), note.y + 2, 1.8, 0, Math.PI * 2);
        g.fill();
      });
      // top title plank
      g.fillStyle = 'rgb(86,54,34)';
      g.fillRect(24, 7, 52, 10);
      g.fillStyle = 'rgba(230,200,130,0.96)';
      g.font = '700 6.5px system-ui';
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      g.fillText('QUESTS', 50, 12);
    });
    return c;
  }

  /**
   * Mimic prop — a chest-like monster in disguise.
   * Uses mimic.png when available, procedural fallback otherwise.
   * @returns {HTMLCanvasElement|OffscreenCanvas}
   */
  function mimic() {
    const size = 50;
    const c = makeCanvas(size, size);
    const g = c.getContext('2d');
    _drawOrFallback(c, g, size, 'mimic', function () {
      // Body — darker, gnarlier chest
      g.fillStyle = 'rgb(72,44,22)';
      g.fillRect(4, 14, 42, 28);
      g.fillStyle = 'rgb(52,28,10)';
      g.fillRect(4, 14, 42, 10);
      g.strokeStyle = 'rgba(160,80,20,0.9)';
      g.lineWidth = 2;
      g.strokeRect(4.5, 14.5, 41, 27);
      g.strokeRect(4.5, 14.5, 41, 10);
      // Metal bands (corroded)
      g.strokeStyle = 'rgba(100,60,10,0.8)';
      g.lineWidth = 2;
      g.beginPath(); g.moveTo(20, 14); g.lineTo(20, 42); g.stroke();
      g.beginPath(); g.moveTo(30, 14); g.lineTo(30, 42); g.stroke();
      // Glowing eyes
      g.fillStyle = 'rgba(255,160,0,0.95)';
      g.beginPath(); g.ellipse(18, 20, 3, 2.5, 0, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.ellipse(32, 20, 3, 2.5, 0, 0, Math.PI * 2); g.fill();
      g.fillStyle = 'rgba(255,220,0,0.7)';
      g.beginPath(); g.ellipse(18, 20, 1.5, 1.2, 0, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.ellipse(32, 20, 1.5, 1.2, 0, 0, Math.PI * 2); g.fill();
      // Teeth along the lid gap
      g.fillStyle = 'rgb(230,220,190)';
      const toothX = [7, 11, 15, 19, 24, 29, 33, 37, 41];
      toothX.forEach(tx => {
        g.beginPath();
        g.moveTo(tx, 24); g.lineTo(tx + 2, 24); g.lineTo(tx + 1, 28); g.closePath(); g.fill();
      });
      // Tongue hint
      g.fillStyle = 'rgba(180,30,30,0.85)';
      g.beginPath();
      g.ellipse(25, 38, 8, 4, 0, 0, Math.PI * 2);
      g.fill();
    });
    return c;
  }

  // ─── Asset Manifest ───────────────────────────────────────────────────────

  const terrain = { stone, dirt, grass, water, forestGround, caveStone, sand, lava, hills, mountains, swamp, snow, shallows };
  const props = {
    wallStone, wallWood, door, chest, table, barrel, crate,
    torch, bookshelf, altar, shop, well, campfire, pillar, guild_board: guildBoard, mimic,
  };

  const assetManifest = Object.freeze({
    terrain: [
      { id: 'stone',       label: 'Stone',        fn: stone,       tags: ['dungeon','hardscape'],  size: 96, tileable: true },
      { id: 'dirt',        label: 'Dirt / Road',  fn: dirt,        tags: ['path','ground'],        size: 96, tileable: true },
      { id: 'grass',       label: 'Grass',        fn: grass,       tags: ['biome','outdoor'],      size: 96, tileable: true },
      { id: 'water',       label: 'Water',        fn: water,       tags: ['water','hazard'],       size: 96, tileable: true },
      { id: 'forestGround',label: 'Forest',       fn: forestGround,tags: ['biome','outdoor'],      size: 96, tileable: true },
      { id: 'caveStone',   label: 'Cave Stone',   fn: caveStone,   tags: ['cave','dungeon'],       size: 96, tileable: true },
      { id: 'sand',        label: 'Desert Sand',  fn: sand,        tags: ['biome','desert'],       size: 96, tileable: true },
      { id: 'lava',        label: 'Lava',         fn: lava,        tags: ['hazard','fire'],        size: 96, tileable: true },
      { id: 'hills',       label: 'Hills',        fn: hills,       tags: ['biome','outdoor'],      size: 96, tileable: true },
      { id: 'mountains',   label: 'Mountains',    fn: mountains,   tags: ['biome','outdoor'],      size: 96, tileable: true },
      { id: 'swamp',       label: 'Swamp',        fn: swamp,       tags: ['biome','outdoor'],      size: 96, tileable: true },
      { id: 'snow',        label: 'Snow / Ice',   fn: snow,        tags: ['biome','cold'],         size: 96, tileable: true },
      { id: 'shallows',    label: 'Shallows',     fn: shallows,    tags: ['water','biome'],        size: 96, tileable: true },
    ],
    props: [
      { id: 'wallStone',   label: 'Stone Wall',   fn: wallStone,   tags: ['walls'],              size: 50,  footprint: 1 },
      { id: 'wallWood',    label: 'Wood Wall',    fn: wallWood,    tags: ['walls'],              size: 50,  footprint: 1 },
      { id: 'door',        label: 'Door',         fn: door,        tags: ['doors'],              size: 50,  footprint: 1 },
      { id: 'chest',       label: 'Chest',        fn: chest,       tags: ['furniture','chest'],  size: 50,  footprint: 1 },
      { id: 'table',       label: 'Table',        fn: table,       tags: ['furniture'],          size: 100, footprint: 2 },
      { id: 'barrel',      label: 'Barrel',       fn: barrel,      tags: ['furniture'],          size: 50,  footprint: 1 },
      { id: 'crate',       label: 'Crate',        fn: crate,       tags: ['furniture','crate'],  size: 50,  footprint: 1 },
      { id: 'torch',       label: 'Torch',        fn: torch,       tags: ['lighting'],           size: 50,  footprint: 1 },
      { id: 'bookshelf',   label: 'Bookshelf',    fn: bookshelf,   tags: ['furniture','bookshelf','bookcase'], size: 100, footprint: 2 },
      { id: 'altar',       label: 'Altar',        fn: altar,       tags: ['furniture'],          size: 100, footprint: 2 },
      { id: 'shop',        label: 'Shop Stall',   fn: shop,        tags: ['store','shop','stall','merchant'], size: 150, footprint: 3 },
      { id: 'guild_board', label: 'Guild Board',  fn: guildBoard,  tags: ['quest','board'],      size: 100, footprint: 2 },
      { id: 'mimic',       label: 'Mimic',        fn: mimic,       tags: ['monster','chest','revealed'], size: 50,  footprint: 1 },
      { id: 'well',        label: 'Well',         fn: well,        tags: ['furniture'],          size: 100, footprint: 2 },
      { id: 'campfire',    label: 'Campfire',     fn: campfire,    tags: ['lighting'],           size: 50,  footprint: 1 },
      { id: 'pillar',      label: 'Pillar',       fn: pillar,      tags: ['walls'],              size: 50,  footprint: 1 },
    ],
  });

  window.DndAssets = Object.freeze({ terrain, props, assetManifest });
})();
