/**
 * D100 — Percentile (Two D10s)
 *
 * D100 = tens die + units die. Physical convention:
 * - Tens die: slightly different color (blue-tinted)
 * - Units die: standard teal color
 * Special case: 00 + 0 = 100
 */

export const D100_SPAWN_OFFSET = 1.2;  // X offset between the two d10s

/**
 * Compute the d100 result from individual tens/units rolls.
 * @param {number} tensResult  0,10,20,...,90 (raw tens die face value)
 * @param {number} unitsResult 0,1,...,9
 * @returns {number} 1-100
 */
export function computeD100Result(tensResult, unitsResult) {
  if (tensResult === 0 && unitsResult === 0) return 100;
  return tensResult + unitsResult;
}

/**
 * Color for the tens die (blue-tinted to distinguish from units die).
 * Follows physical d100 convention.
 */
export const D100_TENS_COLOR  = '#2a6e8a';

/**
 * Color for the units die (standard teal).
 */
export const D100_UNITS_COLOR = '#3a9e7e';
