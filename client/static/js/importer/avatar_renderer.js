(function () {
  const cache = new Map();

  function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }
  function hashString(input) {
    const text = String(input || 'hero');
    let h = 2166136261;
    for (let i = 0; i < text.length; i += 1) {
      h ^= text.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }
  function pick(arr, seed, offset) {
    if (!Array.isArray(arr) || !arr.length) return null;
    return arr[(Math.abs(seed) + (offset || 0)) % arr.length];
  }
  function rgba(hex, alpha) {
    const raw = String(hex || '#ffffff').replace('#', '');
    const clean = raw.length === 3 ? raw.split('').map((c) => c + c).join('') : raw.padEnd(6, '0').slice(0, 6);
    const n = parseInt(clean, 16);
    const r = (n >> 16) & 255;
    const g = (n >> 8) & 255;
    const b = n & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  function hexToRgb(hex) {
    const raw = String(hex || '#ffffff').replace('#', '');
    const clean = raw.length === 3 ? raw.split('').map((c) => c + c).join('') : raw.padEnd(6, '0').slice(0, 6);
    const n = parseInt(clean, 16);
    return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
  }
  function mix(hexA, hexB, weight) {
    const a = hexToRgb(hexA); const b = hexToRgb(hexB); const w = clamp(weight, 0, 1);
    const r = Math.round(a.r * (1 - w) + b.r * w);
    const g = Math.round(a.g * (1 - w) + b.g * w);
    const b2 = Math.round(a.b * (1 - w) + b.b * w);
    return `rgb(${r}, ${g}, ${b2})`;
  }
  function lighten(hex, amount) { return mix(hex, '#ffffff', amount); }
  function darken(hex, amount) { return mix(hex, '#000000', amount); }
  function roundedRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function speciesKey(v) { return String(v || '').trim().toLowerCase(); }
  function classKey(v) { return String(v || '').trim().toLowerCase(); }

  function inferClassRole(value) {
    const key = classKey(value);
    if (/wizard|sorcerer|warlock/.test(key)) return 'arcane';
    if (/cleric|paladin/.test(key)) return 'divine';
    if (/fighter|barbarian/.test(key)) return 'martial';
    if (/rogue|ranger|monk/.test(key)) return 'agile';
    if (/bard/.test(key)) return 'bard';
    if (/druid/.test(key)) return 'nature';
    return 'adventurer';
  }
  function inferItemType(value) {
    const key = classKey(value);
    if (/wizard|sorcerer|warlock|druid/.test(key)) return 'staff';
    if (/cleric|paladin/.test(key)) return 'mace';
    if (/fighter|barbarian/.test(key)) return 'sword';
    if (/ranger/.test(key)) return 'bow';
    if (/rogue|bard|monk/.test(key)) return 'dagger';
    return 'book';
  }
  function accentForClass(value, fallback) {
    const key = classKey(value);
    if (/barbarian/.test(key)) return '#c46039';
    if (/bard/.test(key)) return '#b865e8';
    if (/cleric/.test(key)) return '#d9c27c';
    if (/druid/.test(key)) return '#5b925c';
    if (/fighter/.test(key)) return '#96a3b4';
    if (/monk/.test(key)) return '#d58a43';
    if (/paladin/.test(key)) return '#d5b67d';
    if (/ranger/.test(key)) return '#6d925a';
    if (/rogue/.test(key)) return '#657998';
    if (/sorcerer/.test(key)) return '#cf67b6';
    if (/warlock/.test(key)) return '#8b61d9';
    if (/wizard/.test(key)) return '#5f8dd9';
    return fallback || '#b88c53';
  }

  function basePalette(options) {
    const sp = speciesKey(options.species || options.speciesId || 'human');
    const klass = classKey(options.className || options.classId || 'adventurer');
    const accent = accentForClass(klass, options.accentColor);
    const defaults = {
      skin: '#ddb08f',
      skin2: '#f0cfb0',
      hair: '#2b211d',
      hair2: '#4c382d',
      cloth: darken(accent, 0.32),
      cloth2: darken(accent, 0.1),
      trim: lighten(accent, 0.28),
      metal: '#cfc6b8',
      glow: accent,
      cape: darken(accent, 0.46),
      gem: lighten(accent, 0.35)
    };
    if (/elf/.test(sp)) return Object.assign(defaults, { skin: '#e8c8ac', skin2: '#f2dcc2', hair: '#d0c09b', hair2: '#8c765c' });
    if (/dwarf/.test(sp)) return Object.assign(defaults, { skin: '#d39f79', skin2: '#eab48c', hair: '#5d3d2a', hair2: '#936749' });
    if (/halfling/.test(sp)) return Object.assign(defaults, { skin: '#e6b891', skin2: '#f2cda8', hair: '#6d482c', hair2: '#a57b53' });
    if (/tiefling/.test(sp)) return Object.assign(defaults, { skin: '#b87b86', skin2: '#d8a0aa', hair: '#2a1a23', hair2: '#5a3340', glow: '#c2677f', gem: '#f291ad' });
    if (/dragon/.test(sp)) return Object.assign(defaults, { skin: '#8d87cf', skin2: '#b7b1ef', hair: '#564da8', hair2: '#9f95ee', glow: '#8f7cff' });
    if (/warforged/.test(sp)) return Object.assign(defaults, { skin: '#b0a79f', skin2: '#d9d3ca', hair: '#6e737d', hair2: '#969ca6', metal: '#ddd7cc', glow: '#8fd7d1' });
    if (/tabaxi/.test(sp)) return Object.assign(defaults, { skin: '#b98f69', skin2: '#dfb992', hair: '#503223', hair2: '#caa06f', glow: '#f1c37f' });
    if (/goliath/.test(sp)) return Object.assign(defaults, { skin: '#b68f77', skin2: '#d0a893', hair: '#3c2d28', hair2: '#6b564c', glow: '#c8a88e' });
    if (/aasimar/.test(sp)) return Object.assign(defaults, { skin: '#efceab', skin2: '#f7e4c4', hair: '#f6e7c0', hair2: '#d2bb79', glow: '#f4d896', gem: '#f7efc6' });
    return defaults;
  }

  function makeOptions(input) {
    const opts = Object.assign({}, input || {});
    const seed = hashString([opts.name, opts.species, opts.speciesId, opts.className, opts.classId, opts.gender, opts.variant].join('|'));
    return Object.assign(opts, {
      seed,
      speciesId: speciesKey(opts.speciesId || opts.species || 'human'),
      classId: classKey(opts.classId || opts.className || 'adventurer'),
      gender: String(opts.gender || 'neutral').toLowerCase(),
      palette: basePalette(opts),
      role: inferClassRole(opts.className || opts.classId),
      itemType: inferItemType(opts.className || opts.classId),
      level: Number(opts.level || opts.startingLevel || 1) || 1,
    });
  }

  function paintBackground(ctx, w, h, opts, variant) {
    const p = opts.palette;
    const r = variant === 'token' ? Math.round(w * 0.24) : Math.round(w * 0.1);
    const bg = ctx.createLinearGradient(0, 0, 0, h);
    bg.addColorStop(0, rgba(lighten(p.glow, 0.08), 0.18));
    bg.addColorStop(0.25, 'rgba(32,16,11,0.14)');
    bg.addColorStop(1, 'rgba(8,3,2,0.38)');
    ctx.fillStyle = bg;
    roundedRect(ctx, 0, 0, w, h, r);
    ctx.fill();

    const lantern = ctx.createRadialGradient(w * 0.5, h * 0.18, 4, w * 0.5, h * 0.22, w * 0.34);
    lantern.addColorStop(0, rgba(p.glow, 0.42));
    lantern.addColorStop(1, rgba(p.glow, 0));
    ctx.fillStyle = lantern;
    ctx.fillRect(0, 0, w, h);

    const side = ctx.createLinearGradient(0, 0, w, 0);
    side.addColorStop(0, 'rgba(255,255,255,0.04)');
    side.addColorStop(0.2, 'rgba(255,255,255,0)');
    side.addColorStop(0.8, 'rgba(255,255,255,0)');
    side.addColorStop(1, 'rgba(255,255,255,0.03)');
    ctx.fillStyle = side;
    roundedRect(ctx, 0, 0, w, h, r);
    ctx.fill();

    ctx.strokeStyle = rgba('#f4dfb8', 0.18);
    ctx.lineWidth = variant === 'token' ? 2 : 3;
    roundedRect(ctx, 1.5, 1.5, w - 3, h - 3, r);
    ctx.stroke();

    roundedRect(ctx, 10, 10, w - 20, h - 20, Math.max(14, r - 10));
    ctx.strokeStyle = rgba(p.glow, 0.13);
    ctx.lineWidth = 1.4;
    ctx.stroke();

    const floor = ctx.createRadialGradient(w * 0.5, h * 0.86, 8, w * 0.5, h * 0.92, w * 0.28);
    floor.addColorStop(0, 'rgba(0,0,0,0.26)');
    floor.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = floor;
    ctx.fillRect(0, h * 0.7, w, h * 0.3);
  }

  function drawHalo(ctx, x, y, scale, opts) {
    const p = opts.palette;
    const halo = ctx.createRadialGradient(x, y - 24 * scale, 4, x, y - 24 * scale, 52 * scale);
    halo.addColorStop(0, rgba(lighten(p.glow, 0.32), 0.38));
    halo.addColorStop(0.55, rgba(p.glow, 0.16));
    halo.addColorStop(1, rgba(p.glow, 0));
    ctx.fillStyle = halo;
    ctx.beginPath();
    ctx.arc(x, y - 24 * scale, 58 * scale, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawSpeciesExtras(ctx, x, y, scale, opts) {
    const sp = opts.speciesId;
    const p = opts.palette;
    if (/elf/.test(sp)) {
      ctx.fillStyle = p.skin;
      ctx.beginPath(); ctx.moveTo(x - 28 * scale, y + 4 * scale); ctx.lineTo(x - 52 * scale, y - 6 * scale); ctx.lineTo(x - 32 * scale, y + 22 * scale); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x + 28 * scale, y + 4 * scale); ctx.lineTo(x + 52 * scale, y - 6 * scale); ctx.lineTo(x + 32 * scale, y + 22 * scale); ctx.closePath(); ctx.fill();
    }
    if (/tiefling/.test(sp)) {
      ctx.fillStyle = darken(p.hair, 0.12);
      ctx.beginPath();
      ctx.moveTo(x - 26 * scale, y - 24 * scale);
      ctx.bezierCurveTo(x - 52 * scale, y - 74 * scale, x - 44 * scale, y - 94 * scale, x - 18 * scale, y - 82 * scale);
      ctx.bezierCurveTo(x - 8 * scale, y - 62 * scale, x - 6 * scale, y - 44 * scale, x - 8 * scale, y - 26 * scale);
      ctx.closePath(); ctx.fill();
      ctx.beginPath();
      ctx.moveTo(x + 26 * scale, y - 24 * scale);
      ctx.bezierCurveTo(x + 52 * scale, y - 74 * scale, x + 44 * scale, y - 94 * scale, x + 18 * scale, y - 82 * scale);
      ctx.bezierCurveTo(x + 8 * scale, y - 62 * scale, x + 6 * scale, y - 44 * scale, x + 8 * scale, y - 26 * scale);
      ctx.closePath(); ctx.fill();
    }
    if (/dragon/.test(sp)) {
      ctx.fillStyle = lighten(p.hair2, 0.08);
      ctx.beginPath(); ctx.moveTo(x - 12 * scale, y - 34 * scale); ctx.lineTo(x - 2 * scale, y - 64 * scale); ctx.lineTo(x + 6 * scale, y - 34 * scale); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x + 12 * scale, y - 34 * scale); ctx.lineTo(x + 2 * scale, y - 64 * scale); ctx.lineTo(x - 6 * scale, y - 34 * scale); ctx.closePath(); ctx.fill();
    }
    if (/tabaxi/.test(sp)) {
      ctx.fillStyle = p.hair;
      ctx.beginPath(); ctx.moveTo(x - 26 * scale, y - 18 * scale); ctx.lineTo(x - 42 * scale, y - 44 * scale); ctx.lineTo(x - 12 * scale, y - 30 * scale); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x + 26 * scale, y - 18 * scale); ctx.lineTo(x + 42 * scale, y - 44 * scale); ctx.lineTo(x + 12 * scale, y - 30 * scale); ctx.closePath(); ctx.fill();
    }
    if (/aasimar/.test(sp)) {
      ctx.strokeStyle = rgba('#f7e6ad', 0.72);
      ctx.lineWidth = 4 * scale;
      ctx.beginPath(); ctx.ellipse(x, y - 54 * scale, 28 * scale, 9 * scale, 0, 0, Math.PI * 2); ctx.stroke();
    }
  }

  function drawHair(ctx, x, y, scale, opts) {
    const p = opts.palette;
    const style = opts.seed % 10;
    const grad = ctx.createLinearGradient(0, y - 64 * scale, 0, y + 42 * scale);
    grad.addColorStop(0, p.hair2); grad.addColorStop(1, p.hair);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(x - 38 * scale, y - 6 * scale);
    ctx.bezierCurveTo(x - 42 * scale, y - 48 * scale, x - 20 * scale, y - 62 * scale, x, y - 64 * scale);
    ctx.bezierCurveTo(x + 24 * scale, y - 62 * scale, x + 42 * scale, y - 42 * scale, x + 38 * scale, y - 6 * scale);
    ctx.quadraticCurveTo(x + 22 * scale, y - 20 * scale, x, y - 18 * scale);
    ctx.quadraticCurveTo(x - 24 * scale, y - 20 * scale, x - 38 * scale, y - 6 * scale);
    ctx.closePath();
    ctx.fill();

    if (style === 0 || style === 6) {
      ctx.beginPath(); ctx.moveTo(x - 10 * scale, y - 36 * scale); ctx.lineTo(x - 18 * scale, y + 8 * scale); ctx.lineTo(x + 10 * scale, y + 4 * scale); ctx.lineTo(x + 4 * scale, y - 36 * scale); ctx.closePath(); ctx.fill();
    } else if (style === 1 || style === 7) {
      ctx.beginPath(); ctx.moveTo(x + 26 * scale, y - 8 * scale); ctx.quadraticCurveTo(x - 6 * scale, y - 42 * scale, x - 22 * scale, y + 8 * scale); ctx.lineTo(x + 10 * scale, y + 8 * scale); ctx.closePath(); ctx.fill();
    } else if (style === 2 || style === 8) {
      ctx.beginPath(); ctx.moveTo(x - 24 * scale, y - 4 * scale); ctx.quadraticCurveTo(x, y - 34 * scale, x + 22 * scale, y - 2 * scale); ctx.lineTo(x + 12 * scale, y + 10 * scale); ctx.lineTo(x - 16 * scale, y + 10 * scale); ctx.closePath(); ctx.fill();
    } else {
      ctx.beginPath(); ctx.moveTo(x - 24 * scale, y - 2 * scale); ctx.quadraticCurveTo(x - 8 * scale, y - 26 * scale, x + 6 * scale, y - 20 * scale); ctx.quadraticCurveTo(x + 20 * scale, y - 18 * scale, x + 20 * scale, y + 6 * scale); ctx.lineTo(x - 8 * scale, y + 12 * scale); ctx.closePath(); ctx.fill();
    }

    if (style >= 3 || /female/.test(opts.gender)) {
      ctx.beginPath(); ctx.moveTo(x - 30 * scale, y + 10 * scale); ctx.quadraticCurveTo(x - 48 * scale, y + 46 * scale, x - 30 * scale, y + 92 * scale); ctx.lineTo(x - 4 * scale, y + 48 * scale); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(x + 30 * scale, y + 10 * scale); ctx.quadraticCurveTo(x + 48 * scale, y + 46 * scale, x + 30 * scale, y + 92 * scale); ctx.lineTo(x + 4 * scale, y + 48 * scale); ctx.closePath(); ctx.fill();
    }
    if (style === 5 || style === 9) {
      ctx.fillStyle = rgba(p.trim, 0.92);
      ctx.beginPath(); ctx.arc(x + 30 * scale, y + 24 * scale, 6 * scale, 0, Math.PI * 2); ctx.fill();
    }
  }

  function drawFace(ctx, x, y, scale, opts) {
    const p = opts.palette;
    const headGrad = ctx.createLinearGradient(0, y - 54 * scale, 0, y + 42 * scale);
    headGrad.addColorStop(0, p.skin2); headGrad.addColorStop(1, darken(p.skin, 0.08));
    ctx.fillStyle = headGrad;
    ctx.beginPath(); ctx.ellipse(x, y, 34 * scale, 38 * scale, 0, 0, Math.PI * 2); ctx.fill();

    drawHair(ctx, x, y - 4 * scale, scale, opts);

    const eyeY = y + 2 * scale;
    const eyeDx = 13 * scale;
    ctx.fillStyle = '#22120f';
    ctx.beginPath(); ctx.ellipse(x - eyeDx, eyeY, 5.5 * scale, 4.7 * scale, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(x + eyeDx, eyeY, 5.5 * scale, 4.7 * scale, 0, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,0.8)';
    ctx.beginPath(); ctx.arc(x - eyeDx + 1.4 * scale, eyeY - 1.3 * scale, 1.3 * scale, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(x + eyeDx + 1.4 * scale, eyeY - 1.3 * scale, 1.3 * scale, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = rgba('#59362a', 0.72); ctx.lineWidth = 2.2 * scale; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(x - 18 * scale, y - 12 * scale); ctx.quadraticCurveTo(x - 10 * scale, y - 16 * scale, x - 3 * scale, y - 11 * scale); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + 3 * scale, y - 11 * scale); ctx.quadraticCurveTo(x + 10 * scale, y - 16 * scale, x + 18 * scale, y - 12 * scale); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x, y + 8 * scale); ctx.lineTo(x, y + 15 * scale); ctx.strokeStyle = rgba('#9c6454', 0.54); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - 10 * scale, y + 22 * scale); ctx.quadraticCurveTo(x, y + 30 * scale, x + 10 * scale, y + 22 * scale); ctx.strokeStyle = rgba('#6a3428', 0.75); ctx.stroke();

    if (/warforged/.test(opts.speciesId)) {
      ctx.strokeStyle = rgba('#f1ece2', 0.5); ctx.lineWidth = 2 * scale;
      ctx.strokeRect(x - 20 * scale, y - 20 * scale, 40 * scale, 42 * scale);
      ctx.beginPath(); ctx.moveTo(x, y - 20 * scale); ctx.lineTo(x, y + 22 * scale); ctx.stroke();
    }
    if (/dwarf/.test(opts.speciesId)) {
      ctx.fillStyle = p.hair;
      ctx.beginPath(); ctx.moveTo(x - 18 * scale, y + 24 * scale); ctx.quadraticCurveTo(x, y + 56 * scale, x + 18 * scale, y + 24 * scale); ctx.quadraticCurveTo(x + 22 * scale, y + 54 * scale, x, y + 76 * scale); ctx.quadraticCurveTo(x - 22 * scale, y + 54 * scale, x - 18 * scale, y + 24 * scale); ctx.fill();
    }
    if (/tabaxi/.test(opts.speciesId)) {
      ctx.strokeStyle = rgba('#f2ddc0', 0.5); ctx.lineWidth = 1.8 * scale;
      [['-1',-1],['1',1]].forEach((_,i) => {
        const sign = i===0 ? -1 : 1;
        ctx.beginPath(); ctx.moveTo(x + sign * 32 * scale, y + 8 * scale); ctx.lineTo(x + sign * 50 * scale, y + 4 * scale); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x + sign * 32 * scale, y + 16 * scale); ctx.lineTo(x + sign * 52 * scale, y + 18 * scale); ctx.stroke();
      });
    }
    if (/goliath/.test(opts.speciesId)) {
      ctx.strokeStyle = rgba('#91d7d0', 0.42); ctx.lineWidth = 2.2 * scale;
      ctx.beginPath(); ctx.moveTo(x - 16 * scale, y - 4 * scale); ctx.quadraticCurveTo(x - 4 * scale, y + 8 * scale, x - 12 * scale, y + 22 * scale); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x + 10 * scale, y - 14 * scale); ctx.quadraticCurveTo(x + 22 * scale, y - 4 * scale, x + 18 * scale, y + 16 * scale); ctx.stroke();
    }
  }

  function drawShoulders(ctx, x, y, scale, opts) {
    const p = opts.palette;
    ctx.fillStyle = rgba('#000000', 0.18);
    ctx.beginPath(); ctx.ellipse(x, y + 90 * scale, 72 * scale, 18 * scale, 0, 0, Math.PI * 2); ctx.fill();

    ctx.fillStyle = p.cape;
    ctx.beginPath();
    ctx.moveTo(x - 54 * scale, y + 16 * scale);
    ctx.quadraticCurveTo(x - 74 * scale, y + 64 * scale, x - 54 * scale, y + 124 * scale);
    ctx.lineTo(x - 12 * scale, y + 96 * scale);
    ctx.lineTo(x - 4 * scale, y + 34 * scale);
    ctx.closePath();
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(x + 54 * scale, y + 16 * scale);
    ctx.quadraticCurveTo(x + 74 * scale, y + 64 * scale, x + 54 * scale, y + 124 * scale);
    ctx.lineTo(x + 12 * scale, y + 96 * scale);
    ctx.lineTo(x + 4 * scale, y + 34 * scale);
    ctx.closePath();
    ctx.fill();

    const torso = ctx.createLinearGradient(0, y + 4 * scale, 0, y + 124 * scale);
    torso.addColorStop(0, p.cloth2); torso.addColorStop(1, darken(p.cloth, 0.22));
    ctx.fillStyle = torso;
    ctx.beginPath();
    ctx.moveTo(x - 48 * scale, y + 18 * scale);
    ctx.quadraticCurveTo(x - 24 * scale, y + 2 * scale, x, y + 6 * scale);
    ctx.quadraticCurveTo(x + 24 * scale, y + 2 * scale, x + 48 * scale, y + 18 * scale);
    ctx.lineTo(x + 62 * scale, y + 90 * scale);
    ctx.quadraticCurveTo(x, y + 126 * scale, x - 62 * scale, y + 90 * scale);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = rgba(p.trim, 0.85);
    ctx.beginPath(); ctx.moveTo(x - 18 * scale, y + 10 * scale); ctx.lineTo(x + 18 * scale, y + 10 * scale); ctx.lineTo(x + 8 * scale, y + 28 * scale); ctx.lineTo(x - 8 * scale, y + 28 * scale); ctx.closePath(); ctx.fill();
    ctx.fillStyle = rgba('#0f0908', 0.26);
    ctx.beginPath(); ctx.arc(x, y + 18 * scale, 8 * scale, 0, Math.PI * 2); ctx.fill();
  }

  function drawRoleOverlays(ctx, x, y, scale, opts) {
    const p = opts.palette;
    const role = opts.role;
    if (role === 'martial') {
      ctx.fillStyle = rgba(p.metal, 0.32);
      roundedRect(ctx, x - 56 * scale, y + 18 * scale, 20 * scale, 26 * scale, 8 * scale); ctx.fill();
      roundedRect(ctx, x + 36 * scale, y + 18 * scale, 20 * scale, 26 * scale, 8 * scale); ctx.fill();
      ctx.strokeStyle = rgba('#e8e1d4', 0.24); ctx.lineWidth = 2 * scale; ctx.beginPath(); ctx.moveTo(x, y + 28 * scale); ctx.lineTo(x, y + 88 * scale); ctx.stroke();
    } else if (role === 'divine') {
      ctx.strokeStyle = rgba('#f0dfaf', 0.56); ctx.lineWidth = 2.8 * scale;
      ctx.beginPath(); ctx.moveTo(x, y + 22 * scale); ctx.lineTo(x, y + 56 * scale); ctx.moveTo(x - 10 * scale, y + 38 * scale); ctx.lineTo(x + 10 * scale, y + 38 * scale); ctx.stroke();
      ctx.fillStyle = rgba('#f7efcf', 0.16); ctx.beginPath(); ctx.arc(x, y + 24 * scale, 9 * scale, 0, Math.PI * 2); ctx.fill();
    } else if (role === 'arcane') {
      ctx.fillStyle = rgba(p.glow, 0.22);
      ctx.beginPath(); ctx.arc(x - 46 * scale, y + 58 * scale, 10 * scale, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(x + 46 * scale, y + 46 * scale, 7 * scale, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = rgba(lighten(p.glow, 0.3), 0.72); ctx.lineWidth = 1.8 * scale; ctx.beginPath(); ctx.arc(x, y + 56 * scale, 20 * scale, 0, Math.PI * 2); ctx.stroke();
    } else if (role === 'nature') {
      ctx.strokeStyle = rgba('#b6d59a', 0.48); ctx.lineWidth = 2 * scale;
      ctx.beginPath(); ctx.moveTo(x - 22 * scale, y + 54 * scale); ctx.quadraticCurveTo(x - 4 * scale, y + 34 * scale, x + 10 * scale, y + 54 * scale); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x + 8 * scale, y + 54 * scale); ctx.quadraticCurveTo(x + 26 * scale, y + 34 * scale, x + 32 * scale, y + 58 * scale); ctx.stroke();
    } else if (role === 'bard') {
      ctx.strokeStyle = rgba('#f4d7a2', 0.56); ctx.lineWidth = 2.2 * scale;
      ctx.beginPath(); ctx.arc(x - 20 * scale, y + 56 * scale, 8 * scale, 0, Math.PI * 2); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x - 12 * scale, y + 56 * scale); ctx.lineTo(x + 18 * scale, y + 36 * scale); ctx.stroke();
    } else if (role === 'agile') {
      ctx.strokeStyle = rgba('#cfd8ef', 0.42); ctx.lineWidth = 2.2 * scale;
      ctx.beginPath(); ctx.moveTo(x - 12 * scale, y + 26 * scale); ctx.lineTo(x + 12 * scale, y + 26 * scale); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x - 6 * scale, y + 16 * scale); ctx.lineTo(x + 6 * scale, y + 36 * scale); ctx.stroke();
    }
  }

  function drawItem(ctx, x, y, scale, opts) {
    const item = opts.itemType;
    const p = opts.palette;
    if (item === 'staff') {
      ctx.strokeStyle = rgba('#c8a06b', 0.95); ctx.lineWidth = 5 * scale;
      ctx.beginPath(); ctx.moveTo(x + 58 * scale, y + 24 * scale); ctx.lineTo(x + 72 * scale, y + 134 * scale); ctx.stroke();
      ctx.fillStyle = rgba(p.glow, 0.24); ctx.beginPath(); ctx.arc(x + 56 * scale, y + 18 * scale, 12 * scale, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = rgba(lighten(p.glow, 0.32), 0.86); ctx.lineWidth = 2 * scale; ctx.beginPath(); ctx.arc(x + 56 * scale, y + 18 * scale, 12 * scale, 0, Math.PI * 2); ctx.stroke();
    } else if (item === 'bow') {
      ctx.strokeStyle = rgba('#ccb292', 0.94); ctx.lineWidth = 5 * scale; ctx.beginPath(); ctx.moveTo(x - 60 * scale, y + 24 * scale); ctx.quadraticCurveTo(x - 78 * scale, y + 78 * scale, x - 60 * scale, y + 134 * scale); ctx.stroke();
      ctx.strokeStyle = rgba('#f0d9b1', 0.72); ctx.lineWidth = 1.6 * scale; ctx.beginPath(); ctx.moveTo(x - 60 * scale, y + 26 * scale); ctx.lineTo(x - 60 * scale, y + 132 * scale); ctx.stroke();
    } else if (item === 'sword' || item === 'mace') {
      ctx.strokeStyle = rgba('#d8d2c6', 0.94); ctx.lineWidth = 5 * scale; ctx.beginPath(); ctx.moveTo(x + 58 * scale, y + 36 * scale); ctx.lineTo(x + 82 * scale, y + 126 * scale); ctx.stroke();
      ctx.strokeStyle = rgba('#a87b42', 0.9); ctx.lineWidth = 4 * scale; ctx.beginPath(); ctx.moveTo(x + 50 * scale, y + 52 * scale); ctx.lineTo(x + 72 * scale, y + 44 * scale); ctx.stroke();
    } else if (item === 'dagger') {
      ctx.strokeStyle = rgba('#d8d2c6', 0.94); ctx.lineWidth = 4 * scale; ctx.beginPath(); ctx.moveTo(x + 52 * scale, y + 56 * scale); ctx.lineTo(x + 72 * scale, y + 98 * scale); ctx.stroke();
      ctx.strokeStyle = rgba('#a87b42', 0.9); ctx.lineWidth = 3 * scale; ctx.beginPath(); ctx.moveTo(x + 46 * scale, y + 66 * scale); ctx.lineTo(x + 60 * scale, y + 58 * scale); ctx.stroke();
    } else {
      ctx.fillStyle = rgba('#5b3b2a', 0.95); roundedRect(ctx, x + 48 * scale, y + 62 * scale, 24 * scale, 32 * scale, 4 * scale); ctx.fill();
      ctx.strokeStyle = rgba('#d0a65b', 0.7); ctx.lineWidth = 2 * scale; ctx.strokeRect(x + 52 * scale, y + 66 * scale, 16 * scale, 24 * scale);
    }
  }

  function addNoise(ctx, w, h, seed) {
    const count = Math.max(18, Math.round((w * h) / 2400));
    for (let i = 0; i < count; i += 1) {
      const x = ((seed * (i + 3) * 17) % 1000) / 1000 * w;
      const y = ((seed * (i + 11) * 29) % 1000) / 1000 * h;
      const a = 0.02 + (((seed >> (i % 12)) & 7) / 300);
      ctx.fillStyle = `rgba(255,255,255,${a})`;
      ctx.fillRect(x, y, 1, 1);
    }
  }

  function drawAvatar(ctx, w, h, opts, variant) {
    const scale = Math.min(w, h) / 270;
    paintBackground(ctx, w, h, opts, variant);
    const cx = w * 0.5;
    const headY = h * (variant === 'mini' ? 0.34 : 0.31);
    drawHalo(ctx, cx, headY, scale, opts);
    drawSpeciesExtras(ctx, cx, headY - 8 * scale, scale, opts);
    drawShoulders(ctx, cx, headY + 44 * scale, scale, opts);
    drawRoleOverlays(ctx, cx, headY + 44 * scale, scale, opts);
    drawFace(ctx, cx, headY, scale, opts);
    drawItem(ctx, cx, headY + 44 * scale, scale, opts);
    addNoise(ctx, w, h, opts.seed);
  }

  function renderDataUrl(options, size, variant) {
    const opts = makeOptions(options);
    const kind = variant || 'portrait';
    const dims = kind === 'token' ? { w: size || 96, h: size || 96 } : kind === 'mini' ? { w: size || 110, h: Math.round((size || 110) * 1.1) } : { w: size || 320, h: Math.round((size || 320) * 1.18) };
    const key = JSON.stringify([opts.seed, opts.speciesId, opts.classId, opts.gender, opts.level, dims.w, dims.h, kind, opts.accentColor || '']);
    if (cache.has(key)) return cache.get(key);
    const canvas = document.createElement('canvas');
    canvas.width = dims.w; canvas.height = dims.h;
    const ctx = canvas.getContext('2d');
    drawAvatar(ctx, dims.w, dims.h, opts, kind);
    const url = canvas.toDataURL('image/png');
    cache.set(key, url);
    return url;
  }

  function renderImgMarkup(options, size, variant, className) {
    const src = renderDataUrl(options, size, variant);
    const cls = ['avatar-render', className || '', variant || 'portrait'].filter(Boolean).join(' ');
    const label = String(options && (options.name || options.className || options.species || 'Hero avatar')).replace(/"/g, '&quot;');
    return `<img class="${cls}" alt="${label}" src="${src}">`;
  }

  window.CasualDnDAvatarRenderer = { renderDataUrl, renderImgMarkup, renderOptions: makeOptions };
}());
