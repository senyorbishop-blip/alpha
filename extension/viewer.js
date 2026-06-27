/* extension/viewer.js — viewer-facing panel/component for the Twitch Extension.
 *
 * Flow:
 *   1. onAuthorized -> capture the Helper JWT, channelId, userId.
 *   2. requestIdShare once so the EBS receives the real Twitch user id (needed
 *      to match the linked local account). Power buttons are gated behind it.
 *   3. Load the purchasable catalog from the EBS and render one button per power.
 *   4. On click -> useBits(sku); on transaction complete -> POST the signed
 *      receipt to the EBS, which verifies it and grants the named power.
 *
 * Compliance: Bits always buy a single KNOWN power the viewer selected. There is
 * no "spend Bits -> random power" path. UI copy uses "use Bits to trigger".
 */

// ── EBS endpoint ───────────────────────────────────────────────────────────────
// Set this to your EBS (this app's) HTTPS domain. It must also be listed in the
// Extension's allowlist / CSP in the Twitch Developer Console.
const EBS_BASE = 'https://YOUR-EBS-DOMAIN';

const twitch = window.Twitch ? window.Twitch.ext : null;

const state = {
  token: '',
  channelId: '',
  userId: '',          // opaque (U...) until identity is shared, then real id
  identityShared: false,
  bitsEnabled: false,
  products: {},        // sku -> {cost, displayName}
  catalog: [],         // [{power_id, sku, name, cooldown_sec, requires_approval}]
  subPowers: [],
  pendingSku: null,
};

const $ = (id) => document.getElementById(id);

function setStatus(msg) {
  const el = $('status');
  if (el) el.textContent = msg;
}

async function ebs(path, { method = 'GET', body } = {}) {
  const resp = await fetch(`${EBS_BASE}${path}`, {
    method,
    headers: {
      'Authorization': `Bearer ${state.token}`,
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await resp.json(); } catch (_) { /* non-JSON */ }
  return { ok: resp.ok, status: resp.status, data };
}

// ── Auth ─────────────────────────────────────────────────────────────────────
if (twitch) {
  twitch.onAuthorized((auth) => {
    state.token = auth.token;
    state.channelId = auth.channelId;
    state.userId = auth.userId; // may be opaque until identity is shared
    state.identityShared = !!auth.userId && !String(auth.userId).startsWith('U');
    setStatus('Ready.');
    refresh();
  });

  // Bits availability + product prices.
  if (twitch.features && typeof twitch.features.onChanged === 'function') {
    twitch.features.onChanged(() => {
      state.bitsEnabled = !!(twitch.features && twitch.features.isBitsEnabled);
      renderBitsAvailability();
    });
  }

  // Bits transaction outcomes.
  if (twitch.bits) {
    twitch.bits.onTransactionComplete((tx) => onTransactionComplete(tx));
    twitch.bits.onTransactionCancelled(() => onTransactionCancelled());
  }
} else {
  setStatus('Twitch Extension Helper not loaded.');
}

// ── Identity gate ──────────────────────────────────────────────────────────────
function renderIdentityGate() {
  const gate = $('identity-gate');
  if (state.identityShared) {
    gate.hidden = true;
  } else {
    gate.hidden = false;
  }
}

$('share-identity').addEventListener('click', () => {
  if (twitch && twitch.actions && typeof twitch.actions.requestIdShare === 'function') {
    twitch.actions.requestIdShare();
  }
});

// Request identity share once automatically on load too.
function autoRequestIdShare() {
  if (!state.identityShared && twitch && twitch.actions && typeof twitch.actions.requestIdShare === 'function') {
    twitch.actions.requestIdShare();
  }
}

// ── Refresh ────────────────────────────────────────────────────────────────────
async function refresh() {
  renderIdentityGate();
  autoRequestIdShare();
  await loadProducts();
  await loadCatalog();
  renderBitsAvailability();
  renderPowers();
  renderSubSection();
}

async function loadProducts() {
  if (!twitch || !twitch.bits || typeof twitch.bits.getProducts !== 'function') return;
  try {
    const products = await twitch.bits.getProducts();
    state.products = {};
    (products || []).forEach((p) => { state.products[p.sku] = p; });
  } catch (_) {
    state.products = {};
  }
}

async function loadCatalog() {
  if (!state.token) return;
  const { ok, data } = await ebs(`/catalog?channel=${encodeURIComponent(state.channelId)}`);
  if (ok && data && data.ok) {
    state.catalog = Array.isArray(data.powers) ? data.powers : [];
    state.subPowers = Array.isArray(data.sub_powers) ? data.sub_powers : [];
    if (!data.bound) setStatus('The streamer has not linked a live game yet.');
  } else if (data && data.error === 'extension_not_configured') {
    setStatus('Extension backend is not configured.');
  }
}

// ── Render ─────────────────────────────────────────────────────────────────────
function renderBitsAvailability() {
  const note = $('bits-disabled');
  const powers = $('powers');
  if (!state.bitsEnabled) {
    note.hidden = false;
    powers.hidden = true;
  } else {
    note.hidden = true;
  }
}

function renderPowers() {
  const wrap = $('powers');
  const list = $('power-list');
  list.innerHTML = '';
  if (!state.identityShared || !state.bitsEnabled || !state.catalog.length) {
    wrap.hidden = true;
    return;
  }
  wrap.hidden = false;
  state.catalog.forEach((power) => {
    const product = state.products[power.sku];
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'power-btn';
    btn.disabled = !product; // SKU must exist live in Twitch
    const cost = product ? `${product.cost.amount} Bits` : 'unavailable';
    btn.innerHTML = `
      <span class="power-btn__name">${escapeHtml(power.name)}</span>
      <span class="power-btn__cost">${escapeHtml(cost)}</span>
      ${power.requires_approval ? '<span class="power-btn__tag">needs DM approval</span>' : ''}
      ${power.cooldown_sec ? `<span class="power-btn__tag">${power.cooldown_sec}s cooldown</span>` : ''}
    `;
    btn.addEventListener('click', () => useBitsForPower(power.sku));
    list.appendChild(btn);
  });
}

function renderSubSection() {
  const section = $('sub-section');
  const list = $('sub-list');
  list.innerHTML = '';
  const subAvailable = !!(twitch && twitch.features && twitch.features.isSubscriptionStatusAvailable);
  const status = twitch && twitch.viewer ? twitch.viewer.subscriptionStatus : null;
  const isSubscribed = !!status; // server re-verifies; this only controls the prompt
  if (!state.identityShared || !subAvailable || !isSubscribed || !state.subPowers.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  state.subPowers.forEach((power) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'power-btn power-btn--sub';
    btn.innerHTML = `
      <span class="power-btn__name">${escapeHtml(power.name)}</span>
      <span class="power-btn__cost">Claim free</span>
      ${power.requires_approval ? '<span class="power-btn__tag">needs DM approval</span>' : ''}
    `;
    btn.addEventListener('click', () => claimSubPower(power.power_id, btn));
    list.appendChild(btn);
  });
}

// ── Bits flow ──────────────────────────────────────────────────────────────────
function useBitsForPower(sku) {
  if (!twitch || !twitch.bits || !state.products[sku]) return;
  state.pendingSku = sku;
  setStatus('Confirm in the Bits dialog…');
  twitch.bits.useBits(sku);
}

async function onTransactionComplete(tx) {
  setStatus('Triggering your power…');
  const receipt = tx && (tx.transactionReceipt || tx.transaction_receipt);
  const { ok, data } = await ebs('/transaction', {
    method: 'POST',
    body: { transactionReceipt: receipt },
  });
  if (ok && data && data.ok) {
    const grant = data.grant || {};
    if (data.duplicate) {
      setStatus('Already counted.');
    } else if (grant.requires_approval) {
      setStatus(`${grant.power_name} sent — waiting for DM approval.`);
    } else {
      setStatus(`${grant.power_name} is ready in your game profile!`);
    }
  } else {
    setStatus((data && data.message) || 'Could not apply that power.');
  }
  state.pendingSku = null;
}

function onTransactionCancelled() {
  state.pendingSku = null;
  setStatus('Cancelled.');
}

// ── Sub claim flow ───────────────────────────────────────────────────────────
async function claimSubPower(powerId, btn) {
  if (btn) btn.disabled = true;
  setStatus('Claiming your sub power…');
  const { ok, data } = await ebs('/sub-claim', { method: 'POST', body: { power_id: powerId } });
  if (ok && data && data.ok) {
    const grant = data.grant || {};
    setStatus(grant.requires_approval
      ? `${grant.power_name} sent — waiting for DM approval.`
      : `${grant.power_name} is ready in your game profile!`);
  } else {
    setStatus((data && data.message) || 'Could not claim that power.');
    if (btn) btn.disabled = false;
  }
}

// ── utils ──────────────────────────────────────────────────────────────────────
function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
