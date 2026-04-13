/**
 * ResultOverlay — DOM overlay that floats above character sheet panels.
 * Z-index: 9999 (above map canvas at 200, above character sheet panels).
 *
 * Positioning strategy:
 * - Default: above the centroid of settled dice in screen space
 * - With resultAnchor: above the triggering character sheet element
 */

let _overlayEl = null;

/**
 * Show the result overlay after all dice settle.
 *
 * @param {Array<{type, value}>}  results      Per-die results
 * @param {Object}                [opts]
 * @param {THREE.Camera}          [opts.camera]
 * @param {THREE.WebGLRenderer}   [opts.renderer]
 * @param {THREE.Vector3}         [opts.worldCentroid]
 * @param {HTMLElement}           [opts.resultAnchor]  Character sheet element
 * @param {string}                [opts.rollLabel]
 */
export function showResultOverlay(results, opts = {}) {
  removeResultOverlay();

  const total = results.reduce((sum, r) => sum + (typeof r.value === 'number' ? r.value : 0), 0);

  const el = document.createElement('div');
  el.id = 'dice-result-overlay';
  el.innerHTML = `
    <div class="dro-inner">
      <div class="dro-breakdown">
        ${results.map((r, i) => `
          <span class="dro-chip dro-${r.type}" style="animation-delay:${i * 80}ms">
            ${r.value ?? '?'}
          </span>
          ${i < results.length - 1 ? '<span class="dro-plus">+</span>' : ''}
        `).join('')}
      </div>
      ${results.length > 1 ? `<div class="dro-total">${total}</div>` : ''}
      ${opts.rollLabel ? `<div class="dro-label">${opts.rollLabel}</div>` : ''}
    </div>
  `;

  // ── Position ────────────────────────────────────────────────────
  if (opts.resultAnchor) {
    const rect = opts.resultAnchor.getBoundingClientRect();
    el.style.left = `${rect.left + rect.width / 2}px`;
    el.style.top  = `${rect.top - 20}px`;
  } else if (opts.worldCentroid && opts.camera && opts.renderer) {
    const screen = worldToScreen(opts.worldCentroid, opts.camera, opts.renderer);
    el.style.left = `${screen.x}px`;
    el.style.top  = `${Math.max(screen.y - 100, 80)}px`;
  } else {
    // Fallback: top-centre of viewport
    el.style.left = '50%';
    el.style.top  = '18%';
  }

  document.body.appendChild(el);
  _overlayEl = el;

  // Animate in on next frame
  requestAnimationFrame(() => el.classList.add('dro-visible'));

  // Auto-dismiss after 4.5 s
  const dismiss = () => {
    el.classList.add('dro-exit');
    el.addEventListener('transitionend', () => { el.remove(); if (_overlayEl === el) _overlayEl = null; }, { once: true });
  };
  const timer = setTimeout(dismiss, 4500);
  el.addEventListener('click', () => { clearTimeout(timer); dismiss(); });
}

export function removeResultOverlay() {
  if (_overlayEl) {
    _overlayEl.remove();
    _overlayEl = null;
  }
  document.getElementById('dice-result-overlay')?.remove();
}

function worldToScreen(worldPos, camera, renderer) {
  const v = worldPos.clone().project(camera);
  const w = renderer.domElement.clientWidth;
  const h = renderer.domElement.clientHeight;
  return { x: (v.x + 1) / 2 * w, y: (-v.y + 1) / 2 * h };
}

/**
 * Inject result overlay CSS into document head (idempotent).
 * Called once by DiceWorld.js on init.
 */
export function injectResultOverlayCSS() {
  if (document.getElementById('dice-result-overlay-css')) return;
  const style = document.createElement('style');
  style.id = 'dice-result-overlay-css';
  style.textContent = `
    #dice-result-overlay {
      position: fixed;
      z-index: 9999;
      transform: translate(-50%, -50%) scale(0.85);
      opacity: 0;
      pointer-events: auto;
      cursor: pointer;
      transition:
        opacity  0.28s ease,
        transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    #dice-result-overlay.dro-visible {
      opacity: 1;
      transform: translate(-50%, -50%) scale(1);
    }
    #dice-result-overlay.dro-exit {
      opacity: 0;
      transform: translate(-50%, -58%) scale(0.9);
      transition: opacity 0.2s ease, transform 0.2s ease;
    }
    .dro-inner {
      background: linear-gradient(135deg, rgba(12,22,32,0.96), rgba(20,42,36,0.96));
      border: 1px solid rgba(58,158,126,0.55);
      border-radius: 14px;
      padding: 14px 24px;
      backdrop-filter: blur(14px);
      box-shadow:
        0 0 0 1px rgba(58,158,126,0.18),
        0 10px 40px rgba(0,0,0,0.65),
        0 0 50px rgba(58,158,126,0.12);
      text-align: center;
      min-width: 80px;
    }
    .dro-breakdown {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      flex-wrap: wrap;
      font-family: 'Crimson Text', 'Palatino Linotype', serif;
      color: rgba(200,240,220,0.75);
      font-size: 16px;
      margin-bottom: 6px;
    }
    .dro-chip {
      background: rgba(58,158,126,0.18);
      border: 1px solid rgba(58,158,126,0.38);
      border-radius: 7px;
      padding: 3px 10px;
      font-size: 15px;
      animation: droPopIn 0.32s cubic-bezier(0.34,1.56,0.64,1) both;
    }
    .dro-plus { opacity: 0.5; }
    .dro-total {
      font-family: 'Crimson Text', serif;
      font-size: 52px;
      font-weight: 700;
      color: #c8f0e0;
      line-height: 1;
      text-shadow:
        0 0 24px rgba(58,158,126,0.85),
        0 2px 6px rgba(0,0,0,0.85);
    }
    .dro-label {
      font-family: 'Crimson Text', serif;
      font-size: 12px;
      color: rgba(200,240,220,0.5);
      margin-top: 4px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    @keyframes droPopIn {
      from { transform: scale(0.4); opacity: 0; }
      to   { transform: scale(1);   opacity: 1; }
    }
  `;
  document.head.appendChild(style);
}
