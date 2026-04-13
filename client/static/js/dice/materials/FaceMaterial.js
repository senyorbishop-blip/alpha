import * as THREE from 'three';

const FACE_TEXTURE_CACHE = new Map();

/**
 * FaceMaterial — 4-layer engraved number factory.
 * Creates CanvasTexture with:
 *   1. Radial gradient base (ambient occlusion feel)
 *   2. Grain overlay (resin texture)
 *   3. 4-layer engraved numeral (deep pit → shadow → highlight → main fill)
 *   4. Edge vignette
 *
 * @param {string|number} label    Face number or label (e.g. '00', 6, 20)
 * @param {Object}        opts
 * @param {number}        [opts.size=256]
 * @param {string}        [opts.faceColor='#2e8b6e']
 * @param {string}        [opts.numeralColor='#d4f5e9']
 * @param {string}        [opts.dieType='d6']
 * @param {boolean}       [opts.showUnderlineDot=false]  — for 6 and 9
 * @param {boolean}       [opts.showUnderlineBar=false]  — for d10 '0' and d100 '00'
 */
export function createFaceTexture(label, opts = {}) {
  const {
    size            = 256,
    faceColor       = '#2e8b6e',
    numeralColor    = '#d4f5e9',
    showUnderlineDot = false,
    showUnderlineBar = false,
    dieType         = 'd6',
    repeatAroundFace = false,
  } = opts;

  const texSize = (dieType === 'd20' || dieType === 'd4') ? Math.max(size, 512) : Math.max(size, 192);
  const cacheKey = JSON.stringify({ label: Array.isArray(label) ? label.map(String) : String(label), texSize, faceColor, numeralColor, showUnderlineDot, showUnderlineBar, dieType, repeatAroundFace });
  const cached = FACE_TEXTURE_CACHE.get(cacheKey);
  if (cached) return cached;

  const labelParts = Array.isArray(label) ? label.map(v => String(v)) : [String(label)];
  const labelStr = labelParts.join(' ');
  const canvas   = document.createElement('canvas');
  canvas.width   = canvas.height = texSize;
  const ctx      = canvas.getContext('2d');

  // ── 1. Base radial gradient — center bright, edges dark (AO) ──────
  const radial = ctx.createRadialGradient(
    texSize * 0.5, texSize * 0.42, texSize * 0.04,
    texSize * 0.5, texSize * 0.50, texSize * 0.64
  );
  radial.addColorStop(0,   adjustBrightness(faceColor,  0.15));
  radial.addColorStop(0.7, faceColor);
  radial.addColorStop(1,   adjustBrightness(faceColor, -0.28));
  ctx.fillStyle = radial;
  ctx.fillRect(0, 0, texSize, texSize);

  // ── 2. Grain overlay — resin texture ──────────────────────────────
  applyGrain(ctx, texSize, 0.045);

  // ── 3. Engraved numeral — multi-layer depth effect ─────────────────
  // Scale font relative to texSize to maintain sharpness at larger resolution
  const fontSize = repeatAroundFace
    ? Math.floor(texSize * (Array.isArray(label) ? 0.19 : 0.26))
    : (dieType === 'd10' || dieType === 'd100')
      ? (labelStr.length >= 2 ? Math.floor(texSize * 0.28) : Math.floor(texSize * 0.34))
      : labelStr.length >= 3
        ? Math.floor(texSize * 0.35)
        : labelStr.length >= 2
          ? Math.floor(texSize * 0.42)
          : Math.floor(texSize * 0.52);
  const font = `bold ${fontSize}px "Crimson Text", "Palatino Linotype", serif`;
  ctx.font = font;
  ctx.textAlign    = 'center';
  ctx.textBaseline = 'middle';
  const cx = texSize / 2;
  const cy = texSize / 2;

  // Enhanced engraving depth for d20/d4 (and good baseline for all dice)
  const isD20 = dieType === 'd20';
  const isD4 = dieType === 'd4';
  const depthScale = isD20 ? 1.7 : (isD4 ? 1.45 : 1.18);
  const strokeColor = chooseReadableStrokeColor(faceColor, numeralColor);
  const primaryFill = adjustBrightness(numeralColor, isD4 ? -0.02 : 0.01);
  const glowColor = chooseReadableGlowColor(faceColor, numeralColor);
  const highlightAlpha = isD20 ? 0.34 : (isD4 ? 0.36 : 0.28);
  const shadowAlpha = isD20 ? 0.70 : (isD4 ? 0.68 : 0.62);
  const offsets = repeatAroundFace
    ? [
        { x: 0, y: -texSize * 0.23 },
        { x: -texSize * 0.19, y: texSize * 0.11 },
        { x: texSize * 0.19, y: texSize * 0.11 },
      ]
    : [{ x: 0, y: 0 }];

  const textItems = repeatAroundFace && Array.isArray(label)
    ? offsets.map(({ x, y }, index) => ({ x, y, text: String(label[index] ?? label[0] ?? '') }))
    : offsets.map(({ x, y }) => ({ x, y, text: labelStr }));

  textItems.forEach(({ x, y, text }) => {
    const tx = cx + x;
    const ty = cy + y;

    if (isD20 || isD4) {
      ctx.fillStyle = 'rgba(0,0,0,0.35)';
      ctx.fillText(text, tx + 3.5 * depthScale, ty + 5.0 * depthScale);
    }

    ctx.fillStyle = `rgba(0,0,0,${shadowAlpha})`;
    ctx.fillText(text, tx + 2.8 * depthScale, ty + 3.8 * depthScale);

    ctx.fillStyle = `rgba(0,0,0,${isD20 ? 0.42 : 0.38})`;
    ctx.fillText(text, tx + 1.4 * depthScale, ty + 2.1 * depthScale);

    ctx.save();
    ctx.shadowColor = glowColor;
    ctx.shadowBlur = Math.max(repeatAroundFace ? 8 : 12, texSize * (repeatAroundFace ? 0.025 : 0.035));
    ctx.fillStyle = `rgba(255,255,255,${isD20 ? 0.10 : 0.07})`;
    ctx.fillText(text, tx, ty);
    ctx.restore();

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = Math.max(repeatAroundFace ? 3 : 6, texSize * (repeatAroundFace ? 0.018 : 0.032));
    ctx.lineJoin = 'round';
    ctx.miterLimit = 2;
    ctx.strokeText(text, tx, ty);

    ctx.fillStyle = `rgba(255,255,255,${isD20 ? 0.16 : 0.12})`;
    ctx.fillText(text, tx - 0.9 * depthScale, ty - 1.6 * depthScale);

    ctx.fillStyle = primaryFill;
    ctx.fillText(text, tx, ty);

    ctx.fillStyle = `rgba(255,255,255,${highlightAlpha})`;
    ctx.fillText(text, tx, ty - depthScale);
  });

  // ── 4. Underline dot for 6 and 9 ──────────────────────────────────
  if (showUnderlineDot) {
    ctx.beginPath();
    ctx.arc(cx + texSize * 0.22, cy + texSize * 0.27, texSize * 0.018, 0, Math.PI * 2);
    ctx.fillStyle = adjustBrightness(numeralColor, -0.12);
    ctx.fill();
  }

  // ── 5. Underline bar for d10 '0' and d100 '00'/'tens' labels ──────
  if (showUnderlineBar) {
    const barW = texSize * 0.30;
    ctx.strokeStyle = adjustBrightness(numeralColor, -0.12);
    ctx.lineWidth   = texSize * 0.013;
    ctx.beginPath();
    ctx.moveTo(cx - barW / 2, cy + texSize * 0.28);
    ctx.lineTo(cx + barW / 2, cy + texSize * 0.28);
    ctx.stroke();
  }

  // ── 6. Edge vignette — polygon face feels slightly rounded ─────────
  const vignette = ctx.createRadialGradient(
    texSize / 2, texSize / 2, texSize * 0.35,
    texSize / 2, texSize / 2, texSize * 0.72
  );
  vignette.addColorStop(0, 'rgba(0,0,0,0)');
  vignette.addColorStop(1, 'rgba(0,0,0,0.24)');
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, texSize, texSize);

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 2;
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.userData = { ...(tex.userData || {}), sharedFaceTexture: true, faceTextureCacheKey: cacheKey };
  FACE_TEXTURE_CACHE.set(cacheKey, tex);
  return tex;
}

/**
 * Create all face textures for a die type.
 * @param {string[]} labels      Face labels in face order
 * @param {string}   faceColor
 * @param {string}   [numeralColor='#d4f5e9']
 * @param {string}   [dieType='d6']
 * @returns {THREE.CanvasTexture[]}
 */
export function createAllFaceTextures(labels, faceColor, numeralColor = '#d4f5e9', dieType = 'd6') {
  return labels.map(label => {
    const labelStrings = Array.isArray(label) ? label.map(v => String(v)) : [String(label)];
    return createFaceTexture(label, {
      faceColor,
      numeralColor,
      dieType,
      showUnderlineDot: labelStrings.some(l => l === '6' || l === '9') && (dieType === 'd6' || dieType === 'd10'),
      showUnderlineBar: labelStrings.some(l => l === '0' || l === '00'),
      repeatAroundFace: dieType === 'd4',
    });
  });
}

// ── Internal helpers ─────────────────────────────────────────────────

function adjustBrightness(hex, amount) {
  try {
    const c = new THREE.Color(hex);
    const hsl = {};
    c.getHSL(hsl);
    hsl.l = Math.max(0, Math.min(1, hsl.l + amount));
    c.setHSL(hsl.h, hsl.s, hsl.l);
    return `#${c.getHexString()}`;
  } catch {
    return hex;
  }
}

function chooseReadableStrokeColor(faceColor, numeralColor) {
  try {
    const face = new THREE.Color(faceColor);
    const num = new THREE.Color(numeralColor);
    const faceLum = 0.2126 * face.r + 0.7152 * face.g + 0.0722 * face.b;
    const numLum = 0.2126 * num.r + 0.7152 * num.g + 0.0722 * num.b;
    if (Math.abs(faceLum - numLum) < 0.24) {
      return faceLum > 0.55 ? 'rgba(12,16,22,0.94)' : 'rgba(255,247,236,0.94)';
    }
    return numLum > faceLum ? 'rgba(14,18,26,0.92)' : 'rgba(255,247,236,0.92)';
  } catch {
    return 'rgba(255,248,235,0.92)';
  }
}

function applyGrain(ctx, size, strength) {
  const imageData = ctx.getImageData(0, 0, size, size);
  for (let i = 0; i < imageData.data.length; i += 4) {
    const noise = (Math.random() - 0.5) * strength * 255;
    imageData.data[i]     = Math.max(0, Math.min(255, imageData.data[i]     + noise));
    imageData.data[i + 1] = Math.max(0, Math.min(255, imageData.data[i + 1] + noise));
    imageData.data[i + 2] = Math.max(0, Math.min(255, imageData.data[i + 2] + noise));
  }
  ctx.putImageData(imageData, 0, 0);
}


function chooseReadableGlowColor(faceColor, numeralColor) {
  try {
    const face = new THREE.Color(faceColor);
    const num = new THREE.Color(numeralColor);
    const mixed = face.clone().lerp(num, 0.78);
    const faceLum = 0.2126 * face.r + 0.7152 * face.g + 0.0722 * face.b;
    const mixedLum = 0.2126 * mixed.r + 0.7152 * mixed.g + 0.0722 * mixed.b;
    if (Math.abs(faceLum - mixedLum) < 0.12) {
      return faceLum > 0.55 ? 'rgba(20,28,36,0.52)' : 'rgba(255,246,230,0.46)';
    }
    return `rgba(${Math.round(mixed.r * 255)}, ${Math.round(mixed.g * 255)}, ${Math.round(mixed.b * 255)}, 0.48)`;
  } catch {
    return 'rgba(255,246,230,0.46)';
  }
}
