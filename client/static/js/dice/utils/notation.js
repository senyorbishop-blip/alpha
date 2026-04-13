/**
 * Dice notation parser.
 * Supports: d20, 2d6, 2d6+3, 4d6dl1, 2d20kh1, 1d100
 */
const TOKEN = /(\d*)d(\d+)([+-]\d+)?(kh\d+|kl\d+|dl\d+|dh\d+)?/gi;

/**
 * Parse a dice notation string into an array of roll groups.
 * @param {string} notation
 * @returns {Array<{count, sides, mod, keepDrop, dieType}>}
 */
export function parseNotation(notation) {
  const groups = [];
  TOKEN.lastIndex = 0;
  let match;
  while ((match = TOKEN.exec(notation)) !== null) {
    const [, countStr, sidesStr, modStr, keepDropStr] = match;
    const count    = parseInt(countStr || '1');
    const sides    = parseInt(sidesStr);
    const mod      = modStr ? parseInt(modStr) : 0;
    const keepDrop = keepDropStr ?? null;
    groups.push({ count, sides, mod, keepDrop, dieType: `d${sides}` });
  }
  return groups;
}

/**
 * Apply keep/drop logic to an array of roll values.
 * @param {number[]} rolls
 * @param {string|null} keepDropStr  e.g. 'kh1', 'kl1', 'dl1', 'dh1'
 * @returns {{ kept: number[], dropped: number[] }}
 */
export function applyKeepDrop(rolls, keepDropStr) {
  if (!keepDropStr) return { kept: rolls, dropped: [] };
  const type   = keepDropStr.slice(0, 2);  // kh / kl / dl / dh
  const n      = parseInt(keepDropStr.slice(2));
  const sorted = [...rolls].sort((a, b) => a - b);

  let kept, dropped;
  if (type === 'kh') { kept = sorted.slice(-n);     dropped = sorted.slice(0, -n); }
  if (type === 'kl') { kept = sorted.slice(0, n);   dropped = sorted.slice(n);     }
  if (type === 'dh') { kept = sorted.slice(0, -n);  dropped = sorted.slice(-n);    }
  if (type === 'dl') { kept = sorted.slice(n);      dropped = sorted.slice(0, n);  }

  return { kept: kept ?? rolls, dropped: dropped ?? [] };
}

/**
 * Compute the total for a parsed group with keep/drop applied.
 * @param {number[]} rolls
 * @param {Object} group  Result from parseNotation()
 * @returns {{ kept, dropped, total }}
 */
export function computeGroupTotal(rolls, group) {
  const { kept, dropped } = applyKeepDrop(rolls, group.keepDrop);
  const total = kept.reduce((sum, v) => sum + v, 0) + group.mod;
  return { kept, dropped, total };
}
