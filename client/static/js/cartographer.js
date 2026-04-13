(function () {
  'use strict';

  const DISCOVER_SCOPE_MAP = {
    interior: 'interior',
    battlemap: 'battlemap',
    location: 'location',
    region: 'region',
  };

  const GENERATE_SCOPE_MAP = {
    interior: 'interior',
    battlemap: 'local_area',
    location: 'settlement',
    region: 'region',
  };

  const STYLE_LABELS = {
    painterly: 'Painterly', fantasy_atlas: 'Atlas / Parchment', dark_gritty: 'Dark & Gritty', hand_drawn: 'Hand Drawn', clean_tactical: 'Clean Tactical',
    atlas: 'Atlas / Parchment', inkwash: 'Ink Wash', tactical: 'Tactical', realistic: 'Realistic', dark: 'Dark / Gritty', ancient: 'Ancient', vibrant: 'Vibrant'
  };
  const SOURCE_LABELS = { builtin: 'Built-in', built_in: 'Built-in', generated: 'Generated', imported: 'Imported', uploaded: 'Uploaded', duplicated: 'Duplicated', edited: 'Edited' };

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function humanizeLabel(value, fallback = 'Unknown') {
    const raw = String(value || '').trim();
    if (!raw) return fallback;
    return raw
      .replace(/[_-]+/g, ' ')
      .replace(/\btts\b/gi, 'TTS')
      .replace(/\bai\b/gi, 'AI')
      .replace(/\b\w/g, (m) => m.toUpperCase());
  }

  function formatMapSource(item) {
    const source = item?.source || {};
    if (source.is_premium_manual_import) return 'Premium Import';
    if (source.is_open_content) return 'Open / Free';
    if (item?.source_type === 'generated') return 'Generated';
    return SOURCE_LABELS[item?.source_type] || humanizeLabel(item?.source_type, 'Saved');
  }

  function sourceBadges(item) {
    const badges = [];
    const source = item?.source || {};
    const origin = item?.content_origin || {};
    if (origin.label) badges.push({ label: origin.label, tone: 'neutral' });
    if (source.is_open_content) badges.push({ label: 'Open', tone: 'success' });
    if (source.is_premium_manual_import) badges.push({ label: 'Premium Import', tone: 'warn' });
    if (item?.source_type === 'generated') badges.push({ label: 'Generated', tone: 'info' });
    if (item?.pack_name) badges.push({ label: item.pack_name, tone: 'neutral' });
    if (item?.asset_status && item.asset_status !== 'ready') badges.push({ label: humanizeLabel(item.asset_status), tone: 'error' });
    return badges.slice(0, 3);
  }

  function badgeHtml(label, tone = 'neutral') {
    const palette = {
      success: 'background:rgba(74,140,92,0.18);border:1px solid rgba(110,231,183,0.22);color:#cfeeda;',
      warn: 'background:rgba(139,105,20,0.18);border:1px solid rgba(247,198,106,0.28);color:#f6df9b;',
      info: 'background:rgba(36,78,110,0.18);border:1px solid rgba(116,185,255,0.25);color:#cfe8ff;',
      error: 'background:rgba(139,40,40,0.18);border:1px solid rgba(255,150,150,0.28);color:#ffd0d0;',
      neutral: 'background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);color:var(--parchment-dim);',
    };
    return `<span style="padding:0.12rem 0.38rem;border-radius:999px;font-size:0.54rem;letter-spacing:0.03em;${palette[tone] || palette.neutral}">${esc(label)}</span>`;
  }

  function metadataLine(item) {
    return [
      item?.source_creator ? `By ${item.source_creator}` : '',
      item?.license_label || '',
      item?.attribution?.pack_name || item?.pack_name || '',
    ].filter(Boolean).join(' · ');
  }

  function mapMetaSummary(item) {
    return [
      formatMapSource(item),
      item?.width_cells && item?.height_cells ? `${item.width_cells}×${item.height_cells}` : '',
      item?.grid_type ? humanizeLabel(item.grid_type) : '',
      item?.scale_label || '',
      STYLE_LABELS[item?.image_style] || humanizeLabel(item?.image_style, ''),
    ].filter(Boolean).join(' · ');
  }


  async function safeJsonFetch(url, options) {
    const response = await fetch(url, options);
    const contentType = response.headers.get('content-type') || '';
    const rawText = await response.text();
    let payload = null;
    try {
      payload = rawText ? JSON.parse(rawText) : {};
    } catch (error) {
      console.error('[MapLibrary] non-JSON response', { url, status: response.status, contentType, bodySnippet: rawText.slice(0, 240) });
      throw new Error(response.ok ? 'Server returned an unreadable response.' : `Server error ${response.status}: ${rawText.slice(0, 120) || 'empty response'}`);
    }
    if (!response.ok || payload?.ok === false) {
      console.error('[MapLibrary] request failed', { url, status: response.status, contentType, bodySnippet: rawText.slice(0, 240), payload });
    }
    return { response, payload, contentType, rawText };
  }

  class CartographerController {
    constructor() {
      this.state = {
        activeTab: 'discover',
        discover: { q: '', map_scope: 'interior', terrain: '', image_style: 'painterly', grid_type: 'square', scale_label: '5 ft', sort: 'best_match' },
        library: { q: '', sort: 'newest', source_type: '', favorites_only: false },
        results: [],
        libraryItems: [],
        selected: null,
        generated: null,
        loading: false,
        uploadFile: null,
      };
      this.init();
    }

    async init() {
      this.renderShell();
      this.bindEvents();
      await this.loadIntegrationStatus();
      await this.importMapLibrary(false);
      await this.searchDiscover();
      await this.loadLibrary();
    }

    renderShell() {
      const host = document.getElementById('map-cartographer');
      if (!host) return;
      host.innerHTML = `
        <div class="sidebar-label" style="display:flex;align-items:center;gap:0.45rem;"><span>🗺</span> Map Studio</div>
        <div class="cart-stage-intro">Find a ready map fast, spin up a new battleground when prep runs long, or stash polished uploads in your library for later.</div>
        <div class="cart-stage-card cart-stage-card-summary">
          <div class="cart-stage-chip-row">
            <span class="cart-stage-chip">Discover built-ins</span>
            <span class="cart-stage-chip">Generate on demand</span>
            <span class="cart-stage-chip">Manage your library</span>
          </div>
        </div>
        <div id="cart-integration-status" style="display:none;padding:0.45rem 0.55rem;margin-bottom:0.7rem;background:rgba(0,0,0,0.18);border:1px solid rgba(139,105,20,0.22);border-radius:5px;font-size:0.6rem;color:var(--parchment-dim);line-height:1.45;"></div>
        <div class="cart-tab-toolbar">
          <button class="mini-btn active" data-cart-tab="discover">Discover</button>
          <button class="mini-btn" data-cart-tab="generate">Generate</button>
          <button class="mini-btn" data-cart-tab="library">Library</button>
        </div>
        <div id="cart-shared-feedback" style="display:none;margin-bottom:0.6rem;padding:0.45rem 0.55rem;border-radius:6px;font-size:0.62rem;"></div>
        <section data-cart-pane="discover"></section>
        <section data-cart-pane="generate" style="display:none"></section>
        <section data-cart-pane="library" style="display:none"></section>
        <div id="cart-preview-modal" style="display:none;position:fixed;inset:0;background:rgba(8,10,12,0.82);z-index:1200;align-items:center;justify-content:center;padding:1rem;">
          <div style="width:min(960px,94vw);max-height:88vh;overflow:auto;background:#111511;border:1px solid rgba(212,175,55,0.35);border-radius:14px;box-shadow:0 24px 80px rgba(0,0,0,0.4);padding:1rem;">
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:start;margin-bottom:0.75rem;">
              <div><div id="cart-preview-title" style="font-family:'Cinzel',serif;color:var(--gold);font-size:1rem;"></div><div id="cart-preview-meta" style="font-size:0.65rem;color:var(--parchment-dim);margin-top:0.25rem;"></div></div>
              <button class="mini-btn" id="cart-preview-close">Close</button>
            </div>
            <div style="display:grid;grid-template-columns:minmax(0,1.5fr) minmax(260px,0.9fr);gap:0.9rem;align-items:start;">
              <div style="background:rgba(0,0,0,0.22);border:1px solid rgba(212,175,55,0.15);border-radius:12px;padding:0.65rem;"><img id="cart-preview-image" alt="Map preview" style="width:100%;display:block;border-radius:8px;background:#1a1f19;"></div>
              <div>
                <div id="cart-preview-description" style="font-size:0.68rem;color:var(--parchment);line-height:1.55;margin-bottom:0.7rem;"></div>
                <div id="cart-preview-tags" style="display:flex;flex-wrap:wrap;gap:0.3rem;margin-bottom:0.7rem;"></div>
                <div id="cart-preview-actions" style="display:flex;flex-direction:column;gap:0.4rem;"></div>
              </div>
            </div>
          </div>
        </div>`;
      this.renderDiscoverPane();
      this.renderGeneratePane();
      this.renderLibraryPane();
    }

    renderDiscoverPane() {
      const pane = document.querySelector('[data-cart-pane="discover"]');
      if (!pane) return;
      pane.innerHTML = `
        <div class="cart-stage-card">
          <div class="cart-stage-card-title">Find the fastest good fit</div>
          <div class="cart-stage-card-note">Start with a short scene prompt and map scope. Expand advanced filters only when you need to narrow the search.</div>
          <div class="cart-row"><div class="cart-label">Search maps</div><input id="carto-query" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="ruined keep, tavern, forest ambush"></div>
          <div class="cart-two-col">
            <div class="cart-row"><div class="cart-label">Map Scope</div><select id="carto-scope" class="cart-select"><option value="interior">Interior / Dungeon</option><option value="battlemap">Battlemap</option><option value="location">Location / Area</option><option value="region">Region / World</option></select></div>
            <div class="cart-row"><div class="cart-label">Terrain</div><select id="carto-terrain" class="cart-select"><option value="">Any</option><option value="forest">Forest</option><option value="mountain">Mountain</option><option value="cave">Cave</option><option value="castle">Castle</option><option value="crypt">Crypt</option><option value="temple">Temple</option><option value="road">Road</option><option value="harbor">Harbor</option><option value="ruins">Ruins</option><option value="coastal">Coastal</option></select></div>
          </div>
          <details class="cart-stage-card cart-stage-card-nested">
            <summary class="cart-stage-summary">Advanced filters<span>Style, build, source, and refinement</span></summary>
            <div class="cart-stage-body">
              <div class="cart-two-col">
                <div class="cart-row"><div class="cart-label">Style</div><select id="carto-style" class="cart-select"><option value="">Any</option><option value="painterly">Painterly</option><option value="atlas">Atlas / Parchment</option><option value="dark">Dark / Gritty</option><option value="tactical">Tactical</option></select></div>
                <div class="cart-row"><div class="cart-label">Grid</div><select id="carto-grid" class="cart-select"><option value="">Any</option><option value="square">Square</option><option value="hex">Hex</option><option value="none">None</option></select></div>
              </div>
              <div class="cart-two-col">
                <div class="cart-row"><div class="cart-label">Build Type</div><input id="carto-build" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="road, ruins, shrine"></div>
                <div class="cart-row"><div class="cart-label">Interior Type</div><input id="carto-interior" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="tavern, crypt, tower"></div>
              </div>
              <div class="cart-two-col">
                <div class="cart-row"><div class="cart-label">Scale</div><input id="carto-scale-label" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="5 ft, 10 ft, 1 mile"></div>
                <div class="cart-row"><div class="cart-label">Tags</div><input id="carto-tags" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="forest, ambush, swamp"></div>
              </div>
              <div class="cart-two-col">
                <div class="cart-row"><div class="cart-label">Source</div><select id="carto-source-focus" class="cart-select"><option value="">Any</option><option value="open">Open / Free</option><option value="generated">Generated</option></select></div>
                <div class="cart-row"><div class="cart-label">Pack Name</div><input id="carto-pack-query" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="Starter Forest Pack"></div>
              </div>
            </div>
          </details>
          <div style="display:flex;gap:0.45rem;margin:0.45rem 0 0;"><button id="carto-search-btn" class="cart-result-btn primary" style="flex:1;">Find Map</button><button id="carto-library-shortcut" class="cart-result-btn secondary" style="flex:1;">Open Library</button></div>
        </div>
        <div class="results-header"><span class="results-label">BEST MATCHES</span><span id="results-count" class="results-count"></span></div>
        <div id="carto-results-list" style="display:flex;flex-direction:column;gap:0.5rem;"></div>`;
    }

    renderGeneratePane() {
      const pane = document.querySelector('[data-cart-pane="generate"]');
      if (!pane) return;
      pane.innerHTML = `
        <div class="cart-stage-card">
          <div class="cart-stage-card-title">Generate a fresh battle map</div>
          <div class="cart-stage-card-note">Keep the opening fields short and high-signal. Expand the advanced controls only if the first pass needs more steering.</div>
          <div class="cart-row"><div class="cart-label">Title</div><input id="cart-gen-title" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="Abandoned Dwarven Throne Hall"></div>
          <div class="cart-row"><div class="cart-label">Detailed description</div><textarea id="cart-description" class="cart-textarea" placeholder="Describe important rooms, combat spaces, traversal loops, secrets, mood, and visual beats."></textarea></div>
          <div class="cart-two-col">
            <div class="cart-row"><div class="cart-label">Map Scope</div><select id="cart-gen-scope" class="cart-select"><option value="interior">Interior / Dungeon</option><option value="battlemap">Battlemap</option><option value="location">Location / Area</option><option value="region">Region / World</option></select></div>
            <div class="cart-row"><div class="cart-label">Output Mode</div><select id="cart-output-mode" class="cart-select"><option value="illustrated_overview">Illustrated</option><option value="tactical_grid">Tactical Grid</option><option value="hybrid">Hybrid</option></select></div>
          </div>
          <div class="cart-two-col">
            <div class="cart-row"><div class="cart-label">Terrain</div><select id="cart-terrain" class="cart-select"><option value="">Any</option><option value="mountain_realm">Mountain Realm</option><option value="deep_forest_frontier">Deep Forest</option><option value="coastal_kingdom">Coastal Kingdom</option><option value="riverlands">Riverlands</option><option value="volcanic_wasteland">Volcanic</option><option value="swamp_marches">Swamp</option><option value="high_desert">Desert</option><option value="frozen_north">Frozen</option><option value="underdark">Underdark</option></select></div>
            <div class="cart-row"><div class="cart-label">Build</div><select id="cart-build" class="cart-select"><option value="">Any</option><option value="ancient_castle">Ancient Castle</option><option value="trade_road">Trade Road</option><option value="frontier_villages">Frontier Villages</option><option value="tavern_crossroads">Tavern Crossroads</option><option value="ruined_empire">Ruined Empire</option><option value="war_torn">War-Torn</option><option value="pirate_coast">Pirate Coast</option></select></div>
          </div>
          <details class="cart-stage-card cart-stage-card-nested">
            <summary class="cart-stage-summary">Advanced generation controls<span>Interior type, grid, density, tags, and seed</span></summary>
            <div class="cart-stage-body">
              <div class="cart-two-col">
                <div class="cart-row"><div class="cart-label">Interior Type</div><select id="cart-interior" class="cart-select"><option value="">— None —</option><option value="dungeon">Dungeon</option><option value="tavern">Tavern / Inn</option><option value="castle_keep">Castle / Keep</option><option value="crypt">Crypt / Tomb</option><option value="cave">Cave</option><option value="temple">Temple</option><option value="sewer">Sewer</option><option value="tower">Tower</option><option value="manor">Mansion</option><option value="mine">Mine</option><option value="camp">Camp</option><option value="prison">Prison</option></select></div>
                <div class="cart-row"><div class="cart-label">Image Style</div><select id="cart-style" class="cart-select"><option value="atlas">Atlas / Parchment</option><option value="painterly">Painterly</option><option value="inkwash">Ink Wash</option><option value="tactical">Tactical</option><option value="dark">Dark / Gritty</option><option value="ancient">Ancient</option><option value="vibrant">Vibrant</option></select></div>
              </div>
              <div class="cart-two-col">
                <div class="cart-row"><div class="cart-label">Grid</div><select id="cart-grid-type" class="cart-select"><option value="square">Square</option><option value="hex">Hex</option><option value="none">None</option></select></div>
                <div class="cart-row"><div class="cart-label">Scale</div><select id="cart-grid-scale" class="cart-select"><option value="5ft">5 ft</option><option value="10ft">10 ft</option><option value="25ft">25 ft</option><option value="1 mile">1 mile</option></select></div>
              </div>
              <div class="cart-two-col"><div class="cart-row"><div class="cart-label">Width (cells)</div><input id="cart-grid-w" type="number" min="8" max="180" value="36" class="cart-select" style="padding:0.35rem 0.45rem;"></div><div class="cart-row"><div class="cart-label">Height (cells)</div><input id="cart-grid-h" type="number" min="8" max="180" value="36" class="cart-select" style="padding:0.35rem 0.45rem;"></div></div>
              <div class="cart-two-col"><div class="cart-row"><div class="cart-label">Level of detail</div><select id="cart-detail-density" class="cart-select"><option value="medium">Standard</option><option value="high">High</option><option value="low">Fast</option></select></div><div class="cart-row"><div class="cart-label">Encounter density</div><select id="cart-encounter-density" class="cart-select"><option value="medium">Balanced</option><option value="high">Dense</option><option value="low">Sparse</option></select></div></div>
              <div class="cart-two-col"><div class="cart-row"><div class="cart-label">Room density</div><select id="cart-room-density" class="cart-select"><option value="medium">Balanced</option><option value="high">Dense interior</option><option value="low">Spacious</option></select></div><div class="cart-row"><div class="cart-label">Landmark density</div><select id="cart-landmark-density" class="cart-select"><option value="medium">Balanced</option><option value="high">Dense landmarks</option><option value="low">Minimal</option></select></div></div>
              <div class="cart-two-col"><div class="cart-row"><div class="cart-label">Theme tags</div><input id="cart-theme-tags" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="dwarven, ruined, forge"></div><div class="cart-row"><div class="cart-label">Atmosphere tags</div><input id="cart-atmosphere-tags" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="haunted, smoky, moonlit"></div></div>
              <div class="cart-two-col"><div class="cart-row"><div class="cart-label">Seed</div><input id="cart-seed" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="Optional seed"></div><div class="cart-row"><div class="cart-label">Save to Library</div><label style="display:flex;align-items:center;gap:0.4rem;height:36px;padding:0 0.45rem;border:1px solid var(--border);border-radius:6px;"><input id="cart-save-to-library" type="checkbox" checked> Save generated result</label></div></div>
            </div>
          </details>
          <div style="display:flex;gap:0.45rem;margin-top:0.55rem;"><button id="cart-generate-btn" class="cart-result-btn primary" style="flex:1;">Generate Map</button><button id="cart-duplicate-settings" class="cart-result-btn secondary" style="flex:1;">Copy Filters to Discover</button></div>
        </div>
        <div id="cart-loading" style="display:none;align-items:center;gap:0.6rem;padding:0.8rem 0;font-size:0.63rem;color:var(--parchment-dim);"><div class="loading-spinner"></div><span id="cart-loading-text">Generating map…</span></div>
        <div id="cart-result"></div>`;
    }

    renderLibraryPane() {
      const pane = document.querySelector('[data-cart-pane="library"]');
      if (!pane) return;
      pane.innerHTML = `
        <details class="cart-stage-card" open>
          <summary class="cart-stage-summary">Upload a map to your library<span>Secondary setup for imported JPG / PNG / WebP maps</span></summary>
          <div class="cart-stage-body">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:0.6rem;margin-bottom:0.55rem;">
              <div>
                <div class="cart-label" style="margin-bottom:0.2rem;">Upload to Library</div>
                <div style="font-size:0.58rem;color:var(--parchment-dim);line-height:1.45;">Drop in an existing JPG, PNG, or WebP map and save it directly into Map Studio.</div>
              </div>
              <button id="cart-library-pick-upload" class="cart-result-btn secondary" type="button">Choose File</button>
            </div>
            <input id="cart-library-upload-file" type="file" accept="image/png,image/jpeg,image/webp" style="display:none;">
            <div id="cart-library-upload-name" style="font-size:0.6rem;color:var(--gold-dim);margin-bottom:0.55rem;">No file selected.</div>
            <div class="cart-row"><div class="cart-label">Title</div><input id="cart-library-upload-title" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="Sunken Temple Ambush"></div>
            <div class="cart-row"><div class="cart-label">Description</div><textarea id="cart-library-upload-description" class="cart-textarea" placeholder="Short note for search, reuse, and party prep."></textarea></div>
            <div class="cart-two-col">
              <div class="cart-row"><div class="cart-label">Map Scope</div><select id="cart-library-upload-scope" class="cart-select"><option value="interior">Interior / Dungeon</option><option value="battlemap">Battlemap</option><option value="location">Location / Area</option><option value="region">Region / World</option></select></div>
              <div class="cart-row"><div class="cart-label">Grid</div><select id="cart-library-upload-grid" class="cart-select"><option value="square">Square</option><option value="hex">Hex</option><option value="none">None</option></select></div>
            </div>
            <div class="cart-two-col">
              <div class="cart-row"><div class="cart-label">Width (cells)</div><input id="cart-library-upload-width" type="number" min="1" max="500" value="30" class="cart-select" style="padding:0.35rem 0.45rem;"></div>
              <div class="cart-row"><div class="cart-label">Height (cells)</div><input id="cart-library-upload-height" type="number" min="1" max="500" value="20" class="cart-select" style="padding:0.35rem 0.45rem;"></div>
            </div>
            <div class="cart-two-col">
              <div class="cart-row"><div class="cart-label">Style</div><select id="cart-library-upload-style" class="cart-select"><option value="painterly">Painterly</option><option value="atlas">Atlas / Parchment</option><option value="dark">Dark / Gritty</option><option value="tactical">Tactical</option><option value="hand_drawn">Hand Drawn</option></select></div>
              <div class="cart-row"><div class="cart-label">Scale</div><input id="cart-library-upload-scale" class="cart-select" style="padding:0.35rem 0.45rem;" value="5 ft" placeholder="5 ft"></div>
            </div>
            <div class="cart-row"><div class="cart-label">Tags</div><input id="cart-library-upload-tags" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="ruins, ambush, sewer"></div>
            <div style="display:flex;gap:0.45rem;margin-top:0.55rem;">
              <button id="cart-library-upload-btn" class="cart-result-btn primary" type="button" style="flex:1;">Upload Map</button>
              <button id="cart-library-upload-clear" class="cart-result-btn secondary" type="button">Clear</button>
            </div>
          </div>
        </details>
        <div class="cart-stage-card">
          <div class="cart-stage-card-title">Search saved and built-in maps</div>
          <div class="cart-stage-card-note">Use the library for repeatable prep. Keep upload collapsed unless you are actively bringing in a new map.</div>
          <div class="cart-row"><div class="cart-label">Library search</div><input id="cart-library-query" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="Search saved + built-in maps"></div>
          <div class="cart-two-col"><div class="cart-row"><div class="cart-label">Source</div><select id="cart-library-source" class="cart-select"><option value="">All</option><option value="builtin">Built-in</option><option value="generated">Generated</option><option value="edited">Edited</option><option value="imported">Imported</option></select></div><div class="cart-row"><div class="cart-label">Sort</div><select id="cart-library-sort" class="cart-select"><option value="newest">Newest</option><option value="recently_used">Recently used</option><option value="favorites">Favorites</option><option value="alphabetical">Alphabetical</option><option value="most_used">Most used</option></select></div></div>
          <div class="cart-two-col"><div class="cart-row"><div class="cart-label">Pack</div><input id="cart-library-pack" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="Vault of Dungeons"></div><div class="cart-row"><div class="cart-label">Creator</div><input id="cart-library-creator" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="Creator name"></div></div>
          <div class="cart-two-col"><div class="cart-row"><div class="cart-label">License</div><input id="cart-library-license" class="cart-select" style="padding:0.35rem 0.45rem;" placeholder="CC-BY 4.0, Licensed purchase"></div><div class="cart-row"><div class="cart-label">Import Type</div><select id="cart-library-asset-type" class="cart-select"><option value="">Any</option><option value="open">Open / Free</option><option value="manual_import">Manually Imported</option><option value="generated">Generated</option></select></div></div>
          <div class="cart-row"><div class="cart-label">Content Origin</div><select id="cart-library-origin" class="cart-select"><option value="">Any</option><option value="bundled">Bundled starter content</option><option value="licensed_attributed">Licensed / Attributed</option><option value="imported">Imported</option><option value="user_custom">User custom</option><option value="generated">Generated</option></select></div>
        </div>
        <div style="display:flex;gap:0.45rem;align-items:center;flex-wrap:wrap;margin:0.35rem 0 0.75rem;"><label style="display:flex;align-items:center;gap:0.35rem;font-size:0.62rem;color:var(--parchment-dim);"><input id="cart-library-favorites" type="checkbox"> Favorites only</label><label style="display:flex;align-items:center;gap:0.35rem;font-size:0.62rem;color:var(--parchment-dim);"><input id="cart-library-open" type="checkbox"> Open / free only</label><button id="cart-library-refresh" class="cart-result-btn secondary" style="margin-left:auto;">Refresh</button></div>
        <div id="cart-library-results" style="display:flex;flex-direction:column;gap:0.5rem;"></div>`;
    }

    bindEvents() {
      document.querySelectorAll('[data-cart-tab]').forEach((btn) => btn.addEventListener('click', () => this.switchTab(btn.dataset.cartTab)));
      document.getElementById('carto-search-btn')?.addEventListener('click', () => this.searchDiscover());
      document.getElementById('carto-library-shortcut')?.addEventListener('click', () => this.switchTab('library'));
      document.getElementById('cart-generate-btn')?.addEventListener('click', () => this.generateMap());
      document.getElementById('cart-duplicate-settings')?.addEventListener('click', () => this.copyGeneratorSettingsToDiscover());
      document.getElementById('cart-library-refresh')?.addEventListener('click', async () => { await this.importMapLibrary(); await this.loadLibrary(); });
      document.getElementById('cart-library-pick-upload')?.addEventListener('click', () => document.getElementById('cart-library-upload-file')?.click());
      document.getElementById('cart-library-upload-file')?.addEventListener('change', (e) => this.onUploadFileSelected(e));
      document.getElementById('cart-library-upload-btn')?.addEventListener('click', () => this.uploadLibraryMap());
      document.getElementById('cart-library-upload-clear')?.addEventListener('click', () => this.resetUploadForm());
      document.getElementById('cart-preview-close')?.addEventListener('click', () => this.closePreview());
      document.getElementById('cart-preview-modal')?.addEventListener('click', (e) => {
        if (e.target && e.target.id === 'cart-preview-modal') this.closePreview();
      });
      ['carto-query','cart-library-query'].forEach((id) => {
        document.getElementById(id)?.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            id === 'carto-query' ? this.searchDiscover() : this.loadLibrary();
          }
        });
      });
      ['carto-scope','carto-terrain','carto-style','carto-grid','carto-source-focus'].forEach((id) => document.getElementById(id)?.addEventListener('change', () => this.searchDiscover()));
      ['carto-build','carto-interior','carto-scale-label','carto-tags','carto-pack-query'].forEach((id) => document.getElementById(id)?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.searchDiscover();
        }
      }));
      ['cart-library-source','cart-library-sort','cart-library-favorites','cart-library-open','cart-library-asset-type','cart-library-origin'].forEach((id) => document.getElementById(id)?.addEventListener('change', () => this.loadLibrary()));
      ['cart-library-pack','cart-library-creator','cart-library-license'].forEach((id) => document.getElementById(id)?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.loadLibrary();
        }
      }));
    }

    onUploadFileSelected(event) {
      const file = event?.target?.files?.[0] || null;
      this.state.uploadFile = file;
      const nameEl = document.getElementById('cart-library-upload-name');
      const titleEl = document.getElementById('cart-library-upload-title');
      if (nameEl) {
        nameEl.textContent = file
          ? `${file.name} · ${Math.max(1, Math.round(file.size / 1024))} KB · ready to upload`
          : 'No file selected.';
      }
      if (file && titleEl && !titleEl.value.trim()) {
        titleEl.value = file.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim();
      }
      if (file) this.showFeedback(`Selected “${file.name}”. Add optional metadata, then upload it into your library.`, 'info');
    }

    resetUploadForm() {
      this.state.uploadFile = null;
      ['cart-library-upload-title','cart-library-upload-description','cart-library-upload-tags'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      [['cart-library-upload-width', '30'], ['cart-library-upload-height', '20'], ['cart-library-upload-scale', '5 ft']].forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.value = value;
      });
      [['cart-library-upload-scope', 'interior'], ['cart-library-upload-grid', 'square'], ['cart-library-upload-style', 'painterly']].forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.value = value;
      });
      const fileEl = document.getElementById('cart-library-upload-file');
      if (fileEl) fileEl.value = '';
      const nameEl = document.getElementById('cart-library-upload-name');
      if (nameEl) nameEl.textContent = 'No file selected.';
    }

    async uploadLibraryMap() {
      const file = this.state.uploadFile;
      if (!file) {
        this.showFeedback('Choose a map image before uploading.', 'error');
        return;
      }
      const form = new FormData();
      form.append('file', file);
      form.append('title', document.getElementById('cart-library-upload-title')?.value || '');
      form.append('description', document.getElementById('cart-library-upload-description')?.value || '');
      form.append('map_scope', document.getElementById('cart-library-upload-scope')?.value || 'interior');
      form.append('grid_type', document.getElementById('cart-library-upload-grid')?.value || 'square');
      form.append('image_style', document.getElementById('cart-library-upload-style')?.value || 'painterly');
      form.append('scale_label', document.getElementById('cart-library-upload-scale')?.value || '5 ft');
      form.append('width_cells', document.getElementById('cart-library-upload-width')?.value || '30');
      form.append('height_cells', document.getElementById('cart-library-upload-height')?.value || '20');
      form.append('tags', document.getElementById('cart-library-upload-tags')?.value || '');
      const button = document.getElementById('cart-library-upload-btn');
      const originalLabel = button?.textContent || 'Upload Map';
      if (button) {
        button.disabled = true;
        button.textContent = 'Uploading…';
      }
      try {
        this.showFeedback(`Uploading “${file.name}” into your library…`, 'info');
        console.info('[MapLibrary] upload request started', { name: file.name, size: file.size, type: file.type });
        const { response, payload } = await safeJsonFetch('/api/maps/library/upload', { method: 'POST', body: form });
        if (!response.ok || payload?.ok === false) throw new Error(payload?.error || payload?.detail || 'Map upload failed');
        const uploadedMap = payload.map || payload;
        console.info('[MapLibrary] upload success', uploadedMap);
        this.showFeedback(`Uploaded “${uploadedMap.title || 'Map'}” into your library. It is ready in the Library tab for preview, edit, or scene placement.`, 'success');
        this.resetUploadForm();
        this.switchTab('library');
        await this.loadLibrary();
      } catch (error) {
        this.showFeedback(error.message || 'Map upload failed.', 'error');
      } finally {
        if (button) {
          button.disabled = false;
          button.textContent = originalLabel;
        }
      }
    }

    switchTab(tab) {
      this.state.activeTab = tab;
      document.querySelectorAll('[data-cart-tab]').forEach((btn) => btn.classList.toggle('active', btn.dataset.cartTab === tab));
      document.querySelectorAll('[data-cart-pane]').forEach((pane) => { pane.style.display = pane.dataset.cartPane === tab ? 'block' : 'none'; });
      if (tab === 'library') this.loadLibrary();
    }

    async loadIntegrationStatus() {
      try {
        const response = await fetch('/api/assistant/status');
        if (!response.ok) return;
        const payload = await response.json();
        const assistant = payload.assistant || {};
        const cartographer = assistant.providers?.cartographer || {};
        const el = document.getElementById('cart-integration-status');
        if (!el) return;
        el.style.display = 'block';
        const provider = humanizeLabel(cartographer.image_provider, 'Stub');
        const providerSummary = cartographer.image_provider && cartographer.image_provider !== 'stub'
          ? `Map Studio is routed through ${provider}.`
          : 'Map Studio is currently in stub mode until a real image provider is configured.';
        el.textContent = `${providerSummary} Use DM Assistant for detailed provider readiness, fallback notes, and tool availability.`;
      } catch (_) {}
    }

    discoverFilters() {
      const sourceFocus = document.getElementById('carto-source-focus')?.value || '';
      return {
        q: document.getElementById('carto-query')?.value || '',
        map_scope: DISCOVER_SCOPE_MAP[document.getElementById('carto-scope')?.value || 'interior'] || 'interior',
        terrain: document.getElementById('carto-terrain')?.value || '',
        build_type: document.getElementById('carto-build')?.value || '',
        interior_type: document.getElementById('carto-interior')?.value || '',
        image_style: document.getElementById('carto-style')?.value || '',
        grid_type: document.getElementById('carto-grid')?.value || '',
        scale_label: document.getElementById('carto-scale-label')?.value || '',
        tags: document.getElementById('carto-tags')?.value || '',
        include_collections: 'true',
        open_content_only: sourceFocus === 'open' ? 'true' : '',
        premium_only: sourceFocus === 'premium' ? 'true' : '',
        source_type: sourceFocus === 'generated' ? 'generated' : '',
        pack_name: document.getElementById('carto-pack-query')?.value || '',
        sort: 'best_match',
        page_size: 8,
      };
    }


    async importMapLibrary(showFeedback = true) {
      try {
        const { response, payload } = await safeJsonFetch('/api/maps/library/import', { method: 'POST' });
        if (!response.ok) throw new Error(payload?.detail || payload?.error || 'Map import failed');
        if (showFeedback) {
          const count = Number(payload.imported || 0);
          const broken = Number(payload.broken || 0);
          const duplicates = Number(payload.duplicates || 0);
          const issues = Array.isArray(payload.issues) ? payload.issues : [];
          const firstIssue = issues.length ? issues[0] : null;
          const summary = `Map import scan complete: ${count} ready, ${broken} broken, ${duplicates} duplicate${duplicates === 1 ? '' : 's'} skipped.`;
          const detail = firstIssue ? ` First issue: ${firstIssue.message}` : '';
          this.showFeedback(`${summary}${detail}`, broken || duplicates ? 'warn' : 'success');
        }
        return payload;
      } catch (error) {
        if (showFeedback) this.showFeedback(error.message || 'Map import failed.', 'error');
        return null;
      }
    }
    async searchDiscover() {
      const params = new URLSearchParams(this.discoverFilters());
      this.setCount('Searching…');
      try {
        const { payload } = await safeJsonFetch(`/api/maps/library?${params.toString()}`);
        this.state.results = payload.items || [];
        this.state.discoverCollections = payload.collections || {};
        this.setCount(`${payload.total || 0} maps`);
        this.renderMapList('carto-results-list', this.state.results, { empty: 'No maps matched. Try generating one with richer detail.', collections: this.state.discoverCollections });
      } catch (error) {
        this.renderMapList('carto-results-list', [], { empty: `Search failed: ${error.message}` });
      }
    }

    async loadLibrary() {
      const params = new URLSearchParams();
      const query = (document.getElementById('cart-library-query')?.value || '').trim();
      const sourceType = document.getElementById('cart-library-source')?.value || '';
      const favoritesOnly = document.getElementById('cart-library-favorites')?.checked;
      const openOnly = document.getElementById('cart-library-open')?.checked;
      const sort = document.getElementById('cart-library-sort')?.value || 'newest';
      const packName = (document.getElementById('cart-library-pack')?.value || '').trim();
      const creator = (document.getElementById('cart-library-creator')?.value || '').trim();
      const license = (document.getElementById('cart-library-license')?.value || '').trim();
      const assetType = document.getElementById('cart-library-asset-type')?.value || '';
      const originCategory = document.getElementById('cart-library-origin')?.value || '';

      if (query) params.set('q', query);
      if (sourceType) params.set('source_type', sourceType);
      if (typeof favoritesOnly === 'boolean' && favoritesOnly) params.set('favorites_only', 'true');
      if (typeof openOnly === 'boolean' && openOnly) params.set('open_content_only', 'true');
      if (packName) params.set('pack_name', packName);
      if (creator) params.set('source_creator', creator);
      if (license) params.set('license_label', license);
      if (assetType) params.set('asset_source_type', assetType);
      if (originCategory) params.set('content_origin_category', originCategory);
      if (sort) params.set('sort', sort);
      params.set('include_collections', 'true');
      params.set('page_size', '30');

      try {
        const { payload } = await safeJsonFetch(`/api/maps/library?${params.toString()}`);
        this.state.libraryItems = payload.items || [];
        const summary = this.state.libraryItems.length
          ? `Library ready — showing ${this.state.libraryItems.length} map${this.state.libraryItems.length === 1 ? '' : 's'}.`
          : 'Library ready — no maps matched the current filters.';
        this.showFeedback(summary, this.state.libraryItems.length ? 'info' : 'warn');
        this.renderMapList('cart-library-results', this.state.libraryItems, {
          empty: 'No maps match this filter yet. Try clearing filters or click Refresh to ingest bundled starter maps from import/.',
          libraryMode: true,
          collections: payload.collections || {},
        });
      } catch (error) {
        this.renderMapList('cart-library-results', [], { empty: `Library failed to load: ${error.message}`, libraryMode: true });
        this.showFeedback(`Library failed to load: ${error.message}`, 'error');
      }
    }

    renderMapList(targetId, items, options) {
      const target = document.getElementById(targetId);
      if (!target) return;
      if (!items || !items.length) {
        target.innerHTML = `<div style="font-size:0.67rem;color:var(--parchment-dim);padding:0.8rem;border:1px dashed rgba(212,175,55,0.18);border-radius:10px;">${esc(options.empty)}</div>`;
        return;
      }
      const featured = Array.isArray(options.collections?.featured) && options.collections.featured.length
        ? `<div style="display:flex;flex-wrap:wrap;gap:0.35rem;margin-bottom:0.35rem;">${options.collections.featured.slice(0, 4).map((item) => badgeHtml(`Featured: ${item.title}`, 'info')).join('')}</div>`
        : '';
      const quickstart = Array.isArray(options.collections?.quickstart) && options.collections.quickstart.length
        ? `<div style="display:flex;flex-wrap:wrap;gap:0.35rem;margin-bottom:0.55rem;">${options.collections.quickstart.slice(0, 4).map((item) => badgeHtml(`Quick Start: ${item.title}`, 'success')).join('')}</div>`
        : '';
      target.innerHTML = `${quickstart}${featured}${items.map((item) => this.mapCardHtml(item, options.libraryMode)).join('')}`;
      target.querySelectorAll('[data-map-action="preview"]').forEach((btn) => btn.addEventListener('click', () => this.previewMap(btn.dataset.mapId)));
      target.querySelectorAll('[data-map-action="use"]').forEach((btn) => btn.addEventListener('click', () => this.useMap(btn.dataset.mapId)));
      target.querySelectorAll('[data-map-action="favorite"]').forEach((btn) => btn.addEventListener('click', () => this.toggleFavorite(btn.dataset.mapId)));
      target.querySelectorAll('[data-map-action="edit"]').forEach((btn) => btn.addEventListener('click', () => this.editMap(btn.dataset.mapId)));
      target.querySelectorAll('[data-map-action="duplicate"]').forEach((btn) => btn.addEventListener('click', () => this.duplicateMap(btn.dataset.mapId)));
      target.querySelectorAll('[data-map-action="archive"]').forEach((btn) => btn.addEventListener('click', () => this.archiveMap(btn.dataset.mapId)));
      target.querySelectorAll('[data-map-thumb]').forEach((img) => img.addEventListener('error', () => {
        const fallbackUrl = img.getAttribute('src');
        console.warn('[MapLibrary] thumbnail failed:', fallbackUrl);
        img.replaceWith(Object.assign(document.createElement('div'), {
          textContent: 'Map preview unavailable',
          style: 'width:84px;height:84px;display:flex;align-items:center;justify-content:center;text-align:center;padding:0.35rem;border-radius:10px;border:1px dashed rgba(220,120,120,0.35);background:#151815;color:#ffb3b3;font-size:0.56rem;line-height:1.3;'
        }));
      }));
    }

    mapCardHtml(item, libraryMode) {
      const tags = (item.tags || []).slice(0, 4).map((tag) => `<span style="padding:0.12rem 0.35rem;border-radius:999px;background:rgba(212,175,55,0.08);border:1px solid rgba(212,175,55,0.18);font-size:0.56rem;color:var(--parchment-dim);">${esc(tag)}</span>`).join('');
      const badges = sourceBadges(item).map((badge) => badgeHtml(badge.label, badge.tone)).join('');
      const attribution = metadataLine(item);
      const availability = item.asset_status && item.asset_status !== 'ready'
        ? `<div style="font-size:0.56rem;color:#ffcccc;">Availability: ${esc(humanizeLabel(item.asset_status))}</div>`
        : '';
      return `
        <article style="display:grid;grid-template-columns:84px minmax(0,1fr);gap:0.65rem;padding:0.55rem;border:1px solid rgba(212,175,55,0.18);border-radius:12px;background:linear-gradient(180deg,rgba(32,28,17,0.9),rgba(18,20,14,0.96));box-shadow:inset 0 1px 0 rgba(255,255,255,0.02);">
          <button data-map-action="preview" data-map-id="${esc(item.id)}" style="padding:0;border:none;background:none;cursor:pointer;">
            <img src="${esc(item.thumbnail_url || item.preview_url || item.full_map_url || '')}" alt="${esc(item.title)}" data-map-thumb="${esc(item.id)}" style="width:84px;height:84px;object-fit:cover;border-radius:10px;border:1px solid rgba(212,175,55,0.16);background:#151815;">
          </button>
          <div style="min-width:0;display:flex;flex-direction:column;gap:0.35rem;">
            <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:start;"><div><div style="font-size:0.72rem;color:var(--parchment);font-weight:700;">${esc(item.title || 'Untitled')}</div><div style="font-size:0.58rem;color:var(--gold-dim);margin-top:0.15rem;">${esc(mapMetaSummary(item))}</div></div><span style="font-size:0.54rem;padding:0.12rem 0.35rem;border-radius:999px;border:1px solid rgba(212,175,55,0.24);color:var(--gold);">${esc(STYLE_LABELS[item.image_style] || item.image_style || 'Style')}</span></div>
            <div style="display:flex;flex-wrap:wrap;gap:0.28rem;">${badges || badgeHtml(formatMapSource(item), 'neutral')}</div>
            <div style="font-size:0.6rem;color:var(--parchment-dim);line-height:1.45;">${esc((item.description || 'No description yet.').slice(0, 150))}</div>
            ${attribution ? `<div style="font-size:0.57rem;color:var(--parchment-dim);line-height:1.4;">${esc(attribution)}</div>` : ''}
            ${availability}
            <div style="display:flex;flex-wrap:wrap;gap:0.28rem;">${tags || '<span style="font-size:0.56rem;color:var(--parchment-dim);">No tags yet</span>'}</div>
            <div style="display:flex;gap:0.35rem;flex-wrap:wrap;margin-top:0.15rem;">
              <button class="cart-result-btn primary" data-map-action="use" data-map-id="${esc(item.id)}">Use This Map</button>
              <button class="cart-result-btn secondary" data-map-action="favorite" data-map-id="${esc(item.id)}">${item.is_favorite ? '★ Favorited' : '☆ Favorite'}</button>
              <button class="cart-result-btn secondary" data-map-action="${item.editable ? 'edit' : 'duplicate'}" data-map-id="${esc(item.id)}">${item.editable ? 'Edit Map' : 'Edit as Copy'}</button>
              ${libraryMode && item.editable ? `<button class="cart-result-btn secondary" data-map-action="archive" data-map-id="${esc(item.id)}">Archive</button>` : ''}
            </div>
          </div>
        </article>`;
    }

    buildGenerationPayload() {
      const mapScopeKey = document.getElementById('cart-gen-scope')?.value || 'interior';
      const description = (document.getElementById('cart-description')?.value || '').trim();
      const title = (document.getElementById('cart-gen-title')?.value || '').trim();
      const terrain = document.getElementById('cart-terrain')?.value || '';
      const build = document.getElementById('cart-build')?.value || '';
      const interior = document.getElementById('cart-interior')?.value || '';
      const width = Math.max(8, Number(document.getElementById('cart-grid-w')?.value || 36));
      const height = Math.max(8, Number(document.getElementById('cart-grid-h')?.value || 36));
      const detail = document.getElementById('cart-detail-density')?.value || 'high';
      const encounter = document.getElementById('cart-encounter-density')?.value || 'medium';
      const roomDensity = document.getElementById('cart-room-density')?.value || 'medium';
      const landmarkDensity = document.getElementById('cart-landmark-density')?.value || 'medium';
      const themeTags = this.parseTagInput(document.getElementById('cart-theme-tags')?.value || '');
      const atmosphereTags = this.parseTagInput(document.getElementById('cart-atmosphere-tags')?.value || '');
      const richDescription = this.composeRichDescription({ title, description, terrain, build, interior, detail, encounter, roomDensity, landmarkDensity, themeTags, atmosphereTags, mapScopeKey });
      return {
        title: title || this.deriveTitle({ terrain, build, interior, mapScopeKey }),
        description: richDescription,
        map_scope: GENERATE_SCOPE_MAP[mapScopeKey] || 'interior',
        map_size: `${width}x${height}`,
        width_cells: width,
        height_cells: height,
        grid_width: width,
        grid_height: height,
        grid_type: document.getElementById('cart-grid-type')?.value || 'square',
        scale_label: document.getElementById('cart-grid-scale')?.value || '5ft',
        grid_scale: document.getElementById('cart-grid-scale')?.value || '5ft',
        output_mode: document.getElementById('cart-output-mode')?.value || 'hybrid',
        terrain: terrain,
        terrain_preset: terrain,
        build_type: build,
        build_preset: build,
        interior_type: interior,
        interior_preset: interior,
        image_style: document.getElementById('cart-style')?.value || 'atlas',
        level_of_detail: detail,
        detail_density: detail,
        encounter_density: encounter,
        room_density: roomDensity,
        landmark_density: landmarkDensity,
        poi_density: encounter,
        theme_tags: themeTags,
        atmosphere_tags: atmosphereTags,
        seed: document.getElementById('cart-seed')?.value || '',
        save_to_library: !!document.getElementById('cart-save-to-library')?.checked,
        session_id: window.SESSION_ID || '',
      };
    }

    composeRichDescription(input) {
      const scopeFlavor = {
        interior: 'Create a D&D-usable interior map with clear room logic, loops, choke points, door placement, and combat staging space.',
        battlemap: 'Create a tactical battlemap with line-of-sight blockers, approach lanes, terrain hazards, and encounter-ready geometry.',
        location: 'Create a local area map with multiple landmarks, traversal routes, encounter nodes, and settlement or wilderness context.',
        region: 'Create a regional/world style map with strong landmarks, travel routes, factions, and campaign-facing points of interest.'
      }[input.mapScopeKey] || '';
      const archetype = [input.terrain, input.build, input.interior].filter(Boolean).join(', ');
      const density = `Detail level ${input.detail}; encounter density ${input.encounter}; room density ${input.roomDensity}; landmark density ${input.landmarkDensity}.`;
      const tags = [input.themeTags.length ? `Theme tags: ${input.themeTags.join(', ')}.` : '', input.atmosphereTags.length ? `Atmosphere tags: ${input.atmosphereTags.join(', ')}.` : ''].filter(Boolean).join(' ');
      const user = input.description || 'Bias toward believable D&D play spaces, secrets, tactical flanking lanes, landmark readability, and strong visual storytelling.';
      return [scopeFlavor, archetype ? `Map archetype: ${archetype}.` : '', density, tags, user].filter(Boolean).join(' ');
    }

    deriveTitle(input) {
      return [input.terrain, input.build, input.interior, input.mapScopeKey].filter(Boolean).map((part) => part.replace(/[_-]+/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase())).join(' ') || 'Generated Map';
    }

    parseTagInput(value) {
      return String(value || '').split(',').map((tag) => tag.trim()).filter(Boolean).slice(0, 12);
    }

    async generateMap() {
      const payload = this.buildGenerationPayload();
      const loading = document.getElementById('cart-loading');
      const loadingText = document.getElementById('cart-loading-text');
      if (loading) loading.style.display = 'flex';
      if (loadingText) loadingText.textContent = 'Generating detailed map and saving metadata…';
      try {
        const response = await fetch('/api/ai/generate-map', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || result.error || 'Map generation failed');
        this.state.generated = result;
        this.renderGeneratedResult(result);
        this.showFeedback(result.library_entry ? `Saved “${result.library_entry.title}” to your library.` : 'Map generated successfully.', 'success');
        await this.searchDiscover();
        await this.loadLibrary();
      } catch (error) {
        this.showFeedback(error.message || 'Map generation failed.', 'error');
      } finally {
        if (loading) loading.style.display = 'none';
      }
    }

    renderGeneratedResult(result) {
      const target = document.getElementById('cart-result');
      if (!target) return;
      const entry = result.library_entry || {};
      const imageUrl = (result.image && result.image.url) || entry.preview_url || entry.full_map_url || '';
      const summary = (result.plan && result.plan.summary) || entry.description || 'Detailed map generated.';
      const title = (entry.title || (result.plan && result.plan.title) || 'Generated Map');
      const tags = (entry.tags || []).map((tag) => `<span style="padding:0.12rem 0.35rem;border-radius:999px;background:rgba(212,175,55,0.08);border:1px solid rgba(212,175,55,0.18);font-size:0.56rem;color:var(--parchment-dim);">${esc(tag)}</span>`).join('');
      target.innerHTML = `
        <div class="cart-section-divider"></div>
        <div style="display:grid;gap:0.6rem;">
          <img src="${esc(imageUrl)}" alt="${esc(title)}" style="width:100%;border-radius:12px;border:1px solid rgba(212,175,55,0.18);background:#171b16;${imageUrl ? '' : 'display:none;'}">
          <div class="cart-result-title-text">${esc(title)}</div>
          <div class="cart-result-summary-text">${esc(summary)}</div>
          <div style="display:flex;flex-wrap:wrap;gap:0.28rem;">${tags}</div>
          <div class="cart-result-meta-text">${esc((entry.width_cells || result.editor_import?.grid_width || '?'))}×${esc((entry.height_cells || result.editor_import?.grid_height || '?'))} · ${esc(result.editor_import?.grid_type || entry.grid_type || 'square')} · ${esc(STYLE_LABELS[entry.image_style] || entry.image_style || 'Generated')}</div>
          <div style="display:flex;gap:0.4rem;flex-wrap:wrap;">
            <button class="cart-result-btn primary" id="cart-generated-use">Use on Current Scene</button>
            <button class="cart-result-btn secondary" id="cart-generated-preview">Preview</button>
            <button class="cart-result-btn secondary" id="cart-generated-regenerate">Regenerate</button>
          </div>
        </div>`;
      document.getElementById('cart-generated-use')?.addEventListener('click', () => {
        if (entry.id) this.useMap(entry.id);
        else if (imageUrl) this.applyMap({ id: result.result_id || 'generated-preview', title, full_map_url: imageUrl, map_data_json: result.editor_import || {} });
      });
      document.getElementById('cart-generated-preview')?.addEventListener('click', () => this.previewMap(entry.id, result));
      document.getElementById('cart-generated-regenerate')?.addEventListener('click', () => this.generateMap());
    }

    copyGeneratorSettingsToDiscover() {
      const scope = document.getElementById('cart-gen-scope')?.value || 'interior';
      document.getElementById('carto-scope').value = scope;
      document.getElementById('carto-query').value = document.getElementById('cart-gen-title')?.value || document.getElementById('cart-description')?.value || '';
      const terrain = document.getElementById('cart-terrain')?.value || '';
      if (document.getElementById('carto-terrain')) document.getElementById('carto-terrain').value = terrain.includes('forest') ? 'forest' : terrain.includes('mountain') ? 'mountain' : '';
      this.switchTab('discover');
      this.searchDiscover();
    }

    async previewMap(mapId, overrideData) {
      let item = overrideData && overrideData.library_entry ? overrideData.library_entry : null;
      if (!item && mapId) {
        const { response, payload } = await safeJsonFetch(`/api/maps/library/${encodeURIComponent(mapId)}`);
        item = payload.map || payload;
        if (!response.ok) throw new Error(payload.error || payload.detail || 'Map preview failed');
      }
      if (!item) return;
      document.getElementById('cart-preview-modal').style.display = 'flex';
      document.getElementById('cart-preview-title').textContent = item.title || 'Map Preview';
      document.getElementById('cart-preview-meta').textContent = mapMetaSummary(item);
      document.getElementById('cart-preview-image').src = item.preview_url || item.thumbnail_url || item.full_map_url || '';
      const previewDetails = [
        item.description || 'No description saved.',
        metadataLine(item),
        item.attribution?.text || '',
        item.asset_status && item.asset_status !== 'ready' ? `Availability: ${humanizeLabel(item.asset_status)}` : '',
        item.quality?.is_stub ? 'This entry is marked as a stub/draft result.' : '',
      ].filter(Boolean);
      document.getElementById('cart-preview-description').textContent = previewDetails.join('\n\n');
      document.getElementById('cart-preview-tags').innerHTML = [
        ...sourceBadges(item).map((badge) => badgeHtml(badge.label, badge.tone)),
        ...(item.tags || []).map((tag) => `<span style="padding:0.14rem 0.4rem;border-radius:999px;background:rgba(212,175,55,0.08);border:1px solid rgba(212,175,55,0.18);font-size:0.58rem;color:var(--parchment-dim);">${esc(tag)}</span>`),
      ].join('');
      const actions = document.getElementById('cart-preview-actions');
      actions.innerHTML = `
        <div style="font-size:0.6rem;color:var(--parchment-dim);line-height:1.55;padding:0.55rem 0.65rem;border-radius:10px;border:1px solid rgba(212,175,55,0.14);background:rgba(255,255,255,0.03);">Using this map will apply it to the current scene context. ${item.source?.is_premium_manual_import ? 'The source stays local to this installation.' : 'Open/free attribution remains visible in the library metadata.'}</div>
        <button class="cart-result-btn primary" id="cart-preview-use">Use This Map</button>
        <button class="cart-result-btn secondary" id="cart-preview-favorite">${item.is_favorite ? '★ Favorited' : '☆ Favorite'}</button>
        <button class="cart-result-btn secondary" id="cart-preview-edit">${item.editable ? 'Edit Map' : 'Edit as Copy'}</button>
        <button class="cart-result-btn secondary" id="cart-preview-close-2">Close</button>`;
      document.getElementById('cart-preview-use')?.addEventListener('click', () => this.useMap(item.id));
      document.getElementById('cart-preview-favorite')?.addEventListener('click', async () => { await this.toggleFavorite(item.id); this.closePreview(); });
      document.getElementById('cart-preview-edit')?.addEventListener('click', async () => { this.closePreview(); if (item.editable) await this.editMap(item.id); else await this.duplicateMap(item.id, true); });
      document.getElementById('cart-preview-close-2')?.addEventListener('click', () => this.closePreview());
    }

    closePreview() {
      const modal = document.getElementById('cart-preview-modal');
      if (modal) modal.style.display = 'none';
    }

    async useMap(mapId) {
      console.info('[MapLibrary] activation requested', { mapId });
      const { response, payload } = await safeJsonFetch(`/api/maps/library/${encodeURIComponent(mapId)}`);
      const item = payload.map || payload;
      if (!response.ok) return this.showFeedback(payload.error || payload.detail || 'Map could not be loaded.', 'error');
      await safeJsonFetch(`/api/maps/library/${encodeURIComponent(mapId)}/use`, { method: 'POST' }).catch(() => null);
      if (window.SESSION_ID && window.USER_ID) {
        const { response: activation, payload: activationData } = await safeJsonFetch(`/api/session/${encodeURIComponent(window.SESSION_ID)}/map/library/${encodeURIComponent(mapId)}?user_id=${encodeURIComponent(window.USER_ID)}`, { method: 'POST' });
        console.info('[MapLibrary] activation response', activationData);
        if (!activation.ok || !activationData.ok) {
          console.error('[MapLibrary] activation failed:', activationData, item);
          this.showFeedback(activationData.error || 'Map could not be activated on the scene.', 'error');
          return;
        }
        if (Array.isArray(activationData.warnings) && activationData.warnings.length) {
          this.showFeedback(activationData.warnings[0], 'error');
        } else {
          this.showFeedback(`Loaded “${item.title}” into the current scene.`, 'success');
        }
      } else {
        this.applyMap(item);
        this.showFeedback(`Loaded “${item.title}” into the current scene.`, 'success');
      }
      this.closePreview();
      this.loadLibrary();
      this.searchDiscover();
    }

    applyMap(item) {
      const mapUrl = item.full_map_url || item.preview_url || item.thumbnail_url || item.map_data_json?.background_url;
      const editorImport = item.map_data_json || {};
      if (typeof window.openCartPlacementModal === 'function') {
        window.openCartPlacementModal({
          editor_import: {
            title: item.title || 'Library Map',
            background_url: mapUrl,
            grid_type: editorImport.grid_type || item.grid_type,
            grid_scale: editorImport.grid_scale || item.scale_label,
            grid_width: editorImport.grid_width || item.width_cells,
            grid_height: editorImport.grid_height || item.height_cells,
            metadata: editorImport.metadata || {},
          },
          image: { url: mapUrl },
          plan: { summary: item.description || '' },
        });
      } else if (typeof window.loadMapIntoTabletop === 'function') {
        window.loadMapIntoTabletop(mapUrl, item);
      }
    }



    async duplicateMap(mapId, editAfter) {
      try {
        console.info('[MapLibrary] duplicate requested', { mapId });
        const { payload } = await safeJsonFetch(`/api/maps/${encodeURIComponent(mapId)}/duplicate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
        const map = payload.map || payload;
        this.showFeedback(`Created editable copy of “${map.title || 'map'}”.`, 'success');
        await this.loadLibrary();
        await this.searchDiscover();
        if (editAfter && map?.id) await this.editMap(map.id);
      } catch (error) {
        console.error('[MapLibrary] duplicate failed', error);
        this.showFeedback(error.message || 'Map duplication failed.', 'error');
      }
    }

    async editMap(mapId) {
      try {
        const { payload } = await safeJsonFetch(`/api/maps/library/${encodeURIComponent(mapId)}`);
        const map = payload.map || payload;
        if (!map.editable) return this.duplicateMap(mapId, true);
        const title = window.prompt('Map title', map.title || '');
        if (title == null) return;
        const description = window.prompt('Description', map.description || '');
        if (description == null) return;
        const tags = window.prompt('Tags (comma separated)', (map.tags || []).join(', '));
        if (tags == null) return;
        const width = window.prompt('Width in grid cells', String(map.width_cells || map.placement?.width_cells || 30));
        if (width == null) return;
        const height = window.prompt('Height in grid cells', String(map.height_cells || map.placement?.height_cells || 20));
        if (height == null) return;
        const scale = window.prompt('Scale multiplier', String(map.scale || 1));
        if (scale == null) return;
        const offsetX = window.prompt('X offset (pixels)', String(map.placement?.transform?.offset_x || 0));
        if (offsetX == null) return;
        const offsetY = window.prompt('Y offset (pixels)', String(map.placement?.transform?.offset_y || 0));
        if (offsetY == null) return;
        const gridType = window.prompt('Grid type (square, hex, none)', String(map.grid_type || 'square')) || map.grid_type || 'square';
        const mapScope = window.prompt('Map scope (interior, battlemap, location, region)', String(map.map_scope || 'interior')) || map.map_scope || 'interior';
        console.info('[MapLibrary] edit save started', { mapId });
        const { payload: savePayload } = await safeJsonFetch(`/api/maps/${encodeURIComponent(mapId)}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title,
            description,
            tags,
            width_cells: Number(width),
            height_cells: Number(height),
            scale: Number(scale),
            grid_type: gridType,
            map_scope: mapScope,
            transform: { offset_x: Number(offsetX), offset_y: Number(offsetY), snap_to_grid: true, origin_x: 0.5, origin_y: 0.5, rotation: 0 },
          }),
        });
        if (savePayload?.ok === false) throw new Error(savePayload.error || 'Map save failed');
        console.info('[MapLibrary] edit save success', savePayload);
        if (window.confirm('Replace the source image for this map now?')) {
          await new Promise((resolve) => {
            const picker = document.createElement('input');
            picker.type = 'file';
            picker.accept = 'image/png,image/jpeg,image/webp';
            picker.addEventListener('change', async () => {
              const file = picker.files && picker.files[0];
              if (!file) return resolve();
              try {
                const form = new FormData();
                form.append('file', file);
                const { payload: replacePayload } = await safeJsonFetch(`/api/maps/${encodeURIComponent(mapId)}/replace-image`, { method: 'POST', body: form });
                if (replacePayload?.ok === false) throw new Error(replacePayload.error || 'Image replacement failed');
                console.info('[MapLibrary] image replacement success', replacePayload);
              } catch (replaceError) {
                console.error('[MapLibrary] image replacement failed', replaceError);
                this.showFeedback(replaceError.message || 'Image replacement failed.', 'error');
              }
              resolve();
            }, { once: true });
            picker.click();
          });
        }
        this.showFeedback('Map updated successfully.', 'success');
        await this.loadLibrary();
        await this.searchDiscover();
      } catch (error) {
        console.error('[MapLibrary] edit save failure', error);
        this.showFeedback(error.message || 'Map save failed.', 'error');
      }
    }

    async toggleFavorite(mapId) {
      const { payload: existingPayload } = await safeJsonFetch(`/api/maps/library/${encodeURIComponent(mapId)}`);
      const item = existingPayload.map || existingPayload;
      const { payload } = await safeJsonFetch(`/api/maps/library/${encodeURIComponent(mapId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_favorite: !item.is_favorite }),
      });
      if (payload?.ok === false) throw new Error(payload.error || 'Favorite update failed');
      this.showFeedback(`${item.title} ${item.is_favorite ? 'removed from' : 'added to'} favorites.`, 'success');
      this.loadLibrary();
      this.searchDiscover();
    }

    async archiveMap(mapId) {
      const { payload } = await safeJsonFetch(`/api/maps/library/${encodeURIComponent(mapId)}`, { method: 'DELETE' });
      if (payload?.ok === false) throw new Error(payload.error || 'Archive failed');
      this.showFeedback('Map archived from your active library view.', 'success');
      this.loadLibrary();
      this.searchDiscover();
    }

    setCount(text) {
      const el = document.getElementById('results-count');
      if (el) el.textContent = text;
    }

    showFeedback(message, type) {
      const el = document.getElementById('cart-shared-feedback');
      if (!el) return;
      el.style.display = 'block';
      el.textContent = message;
      const palette = type === 'error'
        ? { background: 'rgba(139,26,26,0.12)', border: 'rgba(220,80,80,0.35)', color: '#ffb3b3', timeout: 5200 }
        : type === 'warn'
          ? { background: 'rgba(130,95,20,0.18)', border: 'rgba(247,198,106,0.35)', color: '#f7d794', timeout: 4800 }
          : type === 'info'
            ? { background: 'rgba(34,66,88,0.18)', border: 'rgba(116,185,255,0.28)', color: '#cfe8ff', timeout: 3200 }
            : { background: 'rgba(70,120,70,0.14)', border: 'rgba(110,231,183,0.28)', color: '#caefd8', timeout: 4200 };
      el.style.background = palette.background;
      el.style.border = `1px solid ${palette.border}`;
      el.style.color = palette.color;
      clearTimeout(this.feedbackTimer);
      this.feedbackTimer = setTimeout(() => { el.style.display = 'none'; }, palette.timeout);
    }
  }

  window.cartographer = null;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { window.cartographer = new CartographerController(); });
  } else {
    window.cartographer = new CartographerController();
  }
})();
