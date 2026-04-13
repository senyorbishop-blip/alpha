import * as THREE from 'three';

/**
 * DiceTheme — teal palette + theme management.
 * Maintains compatibility with original THEME_LIBRARY.
 */

const MIN_DICE_OPACITY = 0.15;

export const THEME_LIBRARY = {
  'obsidian-silver': {
    id: 'obsidian-silver',
    label: 'Obsidian Silver',
    baseColor:    '#0c0f16',
    numeralColor: '#e8e0d0',
    edgeColor:    '#5a5f70',
    roughness:    0.22,
    metalness:    0.44,
    emissive:     '#07090e',
    opacity:      1,
  },
  'obsidian-gold': {
    id: 'obsidian-gold',
    label: 'Obsidian Gold',
    baseColor:    '#0e1118',
    numeralColor: '#f2de96',
    edgeColor:    '#7a6038',
    roughness:    0.26,
    metalness:    0.46,
    emissive:     '#0e0b04',
    opacity:      1,
  },
  'emerald-ivory': {
    id: 'emerald-ivory',
    label: 'Emerald Ivory',
    baseColor:    '#12604e',
    numeralColor: '#f5f2e2',
    edgeColor:    '#7ed6b8',
    roughness:    0.32,
    metalness:    0.18,
    emissive:     '#061d18',
    opacity:      1,
  },
  'arcane-glass': {
    id: 'arcane-glass',
    label: 'Arcane Glass',
    baseColor:    '#6e58e8',
    numeralColor: '#f4f0ff',
    edgeColor:    '#b8aeff',
    roughness:    0.06,
    metalness:    0.06,
    emissive:     '#221540',
    opacity:      0.70,
    transmission: 0.38,
  },
  'bone-crimson': {
    id: 'bone-crimson',
    label: 'Bone Crimson',
    baseColor:    '#d6c8b4',
    numeralColor: '#6a1820',
    edgeColor:    '#eeddce',
    roughness:    0.65,
    metalness:    0.03,
    emissive:     '#100506',
    opacity:      1,
  },
  'blood-resin': {
    id: 'blood-resin',
    label: 'Blood Resin',
    baseColor:    '#1a0608',
    numeralColor: '#f0d0c8',
    edgeColor:    '#8a2020',
    roughness:    0.20,
    metalness:    0.42,
    emissive:     '#140204',
    opacity:      1,
  },
  'dragonforge-royal': {
    id: 'dragonforge-royal',
    label: 'Dragonforge Royal',
    baseColor:    '#24103f',
    numeralColor: '#f6d79f',
    edgeColor:    '#a77cff',
    roughness:    0.16,
    metalness:    0.62,
    emissive:     '#190a33',
    opacity:      1,
    premium:      true,
  },
  'moonsteel-oath': {
    id: 'moonsteel-oath',
    label: 'Moonsteel Oath',
    baseColor:    '#0f1f2e',
    numeralColor: '#e8f7ff',
    edgeColor:    '#8fd5ff',
    roughness:    0.12,
    metalness:    0.72,
    emissive:     '#071722',
    opacity:      1,
    premium:      true,
  },
  'voidfire-sigil': {
    id: 'voidfire-sigil',
    label: 'Voidfire Sigil',
    baseColor:    '#13060f',
    numeralColor: '#ffd5f3',
    edgeColor:    '#ff5ca8',
    roughness:    0.10,
    metalness:    0.48,
    emissive:     '#2a0521',
    opacity:      0.92,
    transmission: 0.14,
    premium:      true,
  },
};

export const DEFAULT_THEME_ID = 'obsidian-silver';
const STORAGE_PREFIX = 'dnd_dice_theme:';
const CUSTOM_STYLES_PREFIX = 'dnd_dice_custom:';

function normalizeColor(hex, fallback) {
  if (typeof hex !== 'string' || !/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(hex)) return fallback;
  return hex;
}

export function ensureReadableTheme(input = {}) {
  const defaultTheme = THEME_LIBRARY[DEFAULT_THEME_ID];
  const baseColor    = normalizeColor(input.baseColor    || input.faceColor,  defaultTheme.baseColor);
  const numeralColor = normalizeColor(input.numeralColor || input.pipColor,   defaultTheme.numeralColor);
  const edgeColor    = normalizeColor(input.edgeColor,                         defaultTheme.edgeColor);

  const theme = {
    id:           input.id       || 'custom',
    themeId:      input.themeId  || input.id || 'custom',
    label:        input.label    || 'Custom Dice',
    baseColor,
    numeralColor,
    edgeColor,
    roughness:    Math.max(0.02, Math.min(1,    Number(input.roughness   ?? 0.35))),
    metalness:    Math.max(0,    Math.min(1,    Number(input.metalness   ?? 0.2))),
    emissive:     normalizeColor(input.emissive, '#090909'),
    opacity:      Math.max(MIN_DICE_OPACITY, Math.min(1, Number(input.opacity ?? 1))),
    transmission: Math.max(0, Math.min(0.92, Number(input.transmission ?? 0))),
  };

  // Keep the user's numeral hue whenever possible. Instead of replacing
  // custom colours with white/black, only nudge the lightness if the face and
  // numeral are genuinely too close together.
  const base     = new THREE.Color(theme.baseColor);
  const text     = new THREE.Color(theme.numeralColor);
  const baseHsl = {}; base.getHSL(baseHsl);
  const textHsl = {}; text.getHSL(textHsl);
  const contrast = Math.abs(baseHsl.l - textHsl.l);
  if (contrast < 0.18) {
    const adjusted = text.clone();
    const nextLightness = baseHsl.l > 0.52
      ? Math.max(0.08, Math.min(0.42, baseHsl.l - 0.34))
      : Math.min(0.92, Math.max(0.58, baseHsl.l + 0.34));
    adjusted.setHSL(textHsl.h, Math.max(textHsl.s, 0.6), nextLightness);
    theme.numeralColor = `#${adjusted.getHexString()}`;
  }
  return theme;
}

export function buildTheme(themeId, overrides) {
  const base = THEME_LIBRARY[themeId] || THEME_LIBRARY[DEFAULT_THEME_ID];
  return ensureReadableTheme({ ...base, ...(overrides || {}) });
}

export function getPlayerPrefs(userId) {
  try {
    const saved = JSON.parse(localStorage.getItem(`${STORAGE_PREFIX}${userId}`) || 'null') || {};
    const base  = saved.themeId && THEME_LIBRARY[saved.themeId]
      ? THEME_LIBRARY[saved.themeId]
      : THEME_LIBRARY[DEFAULT_THEME_ID];
    const prefs = ensureReadableTheme({ ...base, ...saved, faceColor: saved.faceColor, pipColor: saved.pipColor });
    prefs.opacity = Math.max(MIN_DICE_OPACITY, Math.min(1, prefs.opacity ?? 1));
    return prefs;
  } catch {
    return ensureReadableTheme(THEME_LIBRARY[DEFAULT_THEME_ID]);
  }
}

export function setPlayerPrefs(userId, prefs) {
  const theme = ensureReadableTheme({ ...THEME_LIBRARY[DEFAULT_THEME_ID], ...(prefs || {}) });
  const payload = {
    themeId:      prefs?.themeId || 'custom',
    faceColor:    theme.baseColor,
    pipColor:     theme.numeralColor,
    edgeColor:    theme.edgeColor,
    baseColor:    theme.baseColor,
    numeralColor: theme.numeralColor,
    roughness:    theme.roughness,
    metalness:    theme.metalness,
    emissive:     theme.emissive,
    opacity:      Math.max(MIN_DICE_OPACITY, Math.min(1, theme.opacity)),
    transmission: theme.transmission,
  };
  localStorage.setItem(`${STORAGE_PREFIX}${userId}`, JSON.stringify(payload));
  return payload;
}

export function getThemes() {
  return Object.values(THEME_LIBRARY).map(t => ({ ...t }));
}

export function getCustomStyles(userId) {
  try {
    const data = JSON.parse(localStorage.getItem(`${CUSTOM_STYLES_PREFIX}${userId}`) || '[]');
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

export function saveCustomStyle(userId, name, styleObj) {
  const trimmed = String(name || '').trim();
  if (!trimmed) return null;
  const styles = getCustomStyles(userId);
  // Preserve existing id if a style with the same label already exists
  const existingIdx = styles.findIndex(s => s.label === trimmed);
  const id = existingIdx >= 0
    ? styles[existingIdx].id
    : 'custom_' + trimmed.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '') + '_' + Date.now();
  const style = ensureReadableTheme({ ...styleObj, id, label: trimmed, custom: true });
  if (existingIdx >= 0) {
    styles[existingIdx] = style;
  } else {
    styles.push(style);
  }
  localStorage.setItem(`${CUSTOM_STYLES_PREFIX}${userId}`, JSON.stringify(styles));
  return style;
}

export function deleteCustomStyle(userId, styleId) {
  const styles = getCustomStyles(userId).filter(s => s.id !== styleId);
  localStorage.setItem(`${CUSTOM_STYLES_PREFIX}${userId}`, JSON.stringify(styles));
}
