(function () {
  'use strict';

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function humanize(value, fallback = 'Unknown') {
    const raw = String(value || '').trim();
    if (!raw) return fallback;
    return raw.replace(/[_-]+/g, ' ').replace(/\btts\b/gi, 'TTS').replace(/\b\w/g, (m) => m.toUpperCase());
  }

  const ACTIONS = {
    generate_map: {
      label: 'Generate map',
      intro: 'Create a first-pass battleground through the assistant while keeping full Map Studio access intact.',
      fields: [
        { key: 'title', label: 'Title', type: 'text', placeholder: 'Collapsed Temple Approach' },
        { key: 'description', label: 'Prompt', type: 'textarea', placeholder: 'Describe rooms, chokepoints, mood, traversal loops, and encounter beats.' },
        { key: 'map_scope', label: 'Scope', type: 'select', options: [['interior', 'Interior'], ['local_area', 'Battlemap'], ['settlement', 'Location'], ['region', 'Region']] },
        { key: 'output_mode', label: 'Output', type: 'select', options: [['illustrated_overview', 'Illustrated'], ['tactical_grid', 'Tactical'], ['hybrid', 'Hybrid']] },
      ],
    },
    describe_scene: {
      label: 'Describe scene',
      intro: 'Draft a concise scene beat you can review before using the existing narration controls.',
      fields: [
        { key: 'terrain_type', label: 'Terrain', type: 'text', placeholder: 'dungeon, forest, crypt' },
        { key: 'revealed_props', label: 'Notable details', type: 'text', placeholder: 'altar, broken statues, torch sconces' },
        { key: 'campaign_tone', label: 'Tone', type: 'select', options: [['heroic', 'Heroic'], ['grimdark', 'Grimdark'], ['mysterious', 'Mysterious'], ['comedic', 'Comedic']] },
      ],
    },
    suggest_ambience: {
      label: 'Suggest ambience',
      intro: 'Get a recommended ambient loop and a few SFX ideas without changing your current direct audio workflow.',
      fields: [
        { key: 'terrain_type', label: 'Terrain', type: 'text', placeholder: 'forest, tavern, crypt' },
        { key: 'scene', label: 'Scene', type: 'text', placeholder: 'exploration, combat, social scene' },
        { key: 'weather', label: 'Weather', type: 'select', options: [['', 'None'], ['rain', 'Rain'], ['stormy', 'Stormy'], ['fog', 'Fog'], ['snow', 'Snow']] },
        { key: 'current_track', label: 'Current track', type: 'select', options: [['silence', 'Silence'], ['tavern', 'Tavern'], ['dungeon', 'Dungeon'], ['forest', 'Forest'], ['battle', 'Battle']] },
      ],
    },
    ask_rules: {
      label: 'Ask rules',
      intro: 'Ask for a quick ruling from the assistant while preserving the existing chat shortcut flow.',
      fields: [
        { key: 'question', label: 'Question', type: 'textarea', placeholder: 'What triggers an opportunity attack?' },
      ],
    },
    draft_npc_line: {
      label: 'Draft NPC line',
      intro: 'Draft a short NPC response you can review before using the existing NPC speech flow.',
      fields: [
        { key: 'token_name', label: 'NPC name', type: 'text', placeholder: 'Captain Merrow' },
        { key: 'token_notes', label: 'Notes', type: 'textarea', placeholder: 'Rigid city watch captain, tired, distrustful of adventurers.' },
        { key: 'player_message', label: 'Prompt', type: 'textarea', placeholder: 'Why should we trust you?' },
        { key: 'campaign_tone', label: 'Tone', type: 'select', options: [['heroic', 'Heroic'], ['grimdark', 'Grimdark'], ['mysterious', 'Mysterious'], ['comedic', 'Comedic']] },
      ],
    },
    suggest_encounter: {
      label: 'Suggest encounter',
      intro: 'Get a quick encounter seed you can adapt into the existing encounter template workflow.',
      fields: [
        { key: 'terrain_type', label: 'Terrain', type: 'text', placeholder: 'forest, crypt, dungeon' },
        { key: 'party_level', label: 'Party level', type: 'text', placeholder: '5' },
        { key: 'party_size', label: 'Party size', type: 'text', placeholder: '4' },
        { key: 'difficulty', label: 'Difficulty', type: 'select', options: [['easy', 'Easy'], ['medium', 'Medium'], ['hard', 'Hard'], ['deadly', 'Deadly']] },
        { key: 'objective', label: 'Objective', type: 'text', placeholder: 'hold the bridge, escape the crypt, defend civilians' },
      ],
    },
    suggest_loot: {
      label: 'Suggest loot',
      intro: 'Pull a loot preview from the existing level-aware loot tables before you commit it in play.',
      fields: [
        { key: 'dungeon_level', label: 'Dungeon level', type: 'text', placeholder: '5' },
      ],
    },
    draft_session_recap: {
      label: 'Draft session recap',
      intro: 'Turn raw session notes into a recap draft while keeping your existing journal workflow in place.',
      fields: [
        { key: 'notes', label: 'Session notes', type: 'textarea', placeholder: 'Party entered the flooded crypt, bargained with the ferryman ghost, and found the crown fragment.' },
        { key: 'style', label: 'Style', type: 'select', options: [['dramatic', 'Dramatic'], ['neutral', 'Neutral'], ['heroic', 'Heroic']] },
      ],
    },
  };

  class DMAssistantController {
    constructor() {
      this.host = null;
      this.state = {
        role: 'viewer',
        selectedAction: 'generate_map',
        loading: false,
        status: null,
        result: null,
        error: '',
        history: [],
      };
    }

    mount() {
      this.host = document.getElementById('dm-assistant-host');
      if (!this.host) return;
      this.render();
      this.bind();
      this.refreshStatus();
    }

    setRole(role) {
      this.state.role = String(role || 'viewer').toLowerCase();
      const railBtn = document.getElementById('rail-assistant-btn');
      if (railBtn) railBtn.style.display = this.state.role === 'dm' ? 'flex' : 'none';
      this.render();
    }

    async refreshStatus() {
      try {
        const resp = await fetch('/api/assistant/status');
        if (!resp.ok) throw new Error(`status ${resp.status}`);
        const payload = await resp.json();
        this.state.status = payload.assistant || null;
        window.__assistantStatus = this.state.status;
        document.dispatchEvent(new CustomEvent('dm-assistant-status', { detail: this.state.status }));
        this.render();
      } catch (err) {
        console.warn('[DMAssistant] status fetch failed', err);
      }
    }

    bind() {
      this.host.addEventListener('click', (event) => {
        const tabBtn = event.target.closest('[data-assistant-action]');
        if (tabBtn) {
          this.state.selectedAction = tabBtn.dataset.assistantAction;
          this.state.result = null;
          this.state.error = '';
          this.render();
          return;
        }
        const submitBtn = event.target.closest('[data-assistant-submit]');
        if (submitBtn) {
          this.runSelectedAction();
          return;
        }
        const utilBtn = event.target.closest('[data-assistant-util]');
        if (utilBtn) {
          this.handleUtility(utilBtn.dataset.assistantUtil);
        }
      });
    }

    currentConfig() {
      return ACTIONS[this.state.selectedAction] || ACTIONS.generate_map;
    }

    readForm() {
      const action = this.state.selectedAction;
      const config = this.currentConfig();
      const body = { action };
      (config.fields || []).forEach((field) => {
        const el = this.host.querySelector(`[data-assistant-field="${field.key}"]`);
        if (!el) return;
        body[field.key] = el.value;
      });
      if (action === 'describe_scene') {
        body.revealed_props = String(body.revealed_props || '')
          .split(',')
          .map((part) => part.trim())
          .filter(Boolean);
      }
      return body;
    }

    async runSelectedAction() {
      const body = this.readForm();
      this.state.loading = true;
      this.state.error = '';
      this.render();
      try {
        const resp = await fetch('/api/assistant/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (!resp.ok || data.ok === false) {
          throw new Error(data.error || `Assistant request failed (${resp.status})`);
        }
        this.state.result = data;
        this.state.history = [{
          action: data.action,
          title: data.title || this.currentConfig().label,
          summary: data.summary || '',
          provider: data.provider || null,
          at: new Date().toISOString(),
        }, ...this.state.history].slice(0, 6);
      } catch (err) {
        this.state.result = null;
        this.state.error = err.message || 'Assistant request failed.';
      } finally {
        this.state.loading = false;
        this.render();
      }
    }

    handleUtility(kind) {
      const result = this.state.result || {};
      const content = result.content || {};
      if (kind === 'open_map_studio' && typeof window.toggleFlyout === 'function') {
        window.toggleFlyout('flyout-cart');
        return;
      }
      if (kind === 'copy_text') {
        const text = content.text || result.summary || '';
        if (text && navigator.clipboard?.writeText) navigator.clipboard.writeText(text);
        if (typeof window.showToast === 'function') window.showToast('Assistant text copied.');
        return;
      }
      if (kind === 'send_to_narration') {
        const text = content.text || result.summary || '';
        const input = document.getElementById('narration-text-input');
        if (input) input.value = text;
        if (typeof window.toggleFlyout === 'function') window.toggleFlyout('flyout-sound');
        if (typeof window.showToast === 'function') window.showToast('Narration draft moved into the live narration controls.');
        return;
      }
      if (kind === 'apply_track') {
        const track = content.recommended_track;
        if (track && typeof window.dmSoundSetTrack === 'function') {
          window.dmSoundSetTrack(track);
          if (typeof window.showToast === 'function') window.showToast(`Ambient track set to ${humanize(track)}.`);
        }
      }
    }

    renderField(field) {
      const id = `assistant-${field.key}`;
      const baseLabel = `<label style="display:grid;gap:0.24rem;font-size:0.62rem;color:var(--gold-dim);text-transform:uppercase;letter-spacing:0.06em;">${esc(field.label)}`;
      if (field.type === 'textarea') {
        return `${baseLabel}<textarea id="${id}" data-assistant-field="${field.key}" style="min-height:80px;border-radius:10px;border:1px solid rgba(0,229,204,0.18);background:rgba(0,0,0,0.26);color:var(--parchment);padding:0.55rem 0.6rem;font-size:0.72rem;resize:vertical;" placeholder="${esc(field.placeholder || '')}"></textarea></label>`;
      }
      if (field.type === 'select') {
        return `${baseLabel}<select id="${id}" data-assistant-field="${field.key}" style="border-radius:10px;border:1px solid rgba(0,229,204,0.18);background:rgba(0,0,0,0.26);color:var(--parchment);padding:0.55rem 0.6rem;font-size:0.72rem;">${(field.options || []).map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join('')}</select></label>`;
      }
      return `${baseLabel}<input id="${id}" data-assistant-field="${field.key}" type="text" style="border-radius:10px;border:1px solid rgba(0,229,204,0.18);background:rgba(0,0,0,0.26);color:var(--parchment);padding:0.55rem 0.6rem;font-size:0.72rem;" placeholder="${esc(field.placeholder || '')}" /></label>`;
    }

    renderResult() {
      if (this.state.error) {
        return `<div style="padding:0.7rem 0.8rem;border-radius:12px;border:1px solid rgba(188,72,72,0.45);background:rgba(139,26,26,0.12);color:#ffcccc;font-size:0.7rem;line-height:1.5;">${esc(this.state.error)}</div>`;
      }
      const result = this.state.result;
      if (!result) {
        return '<div style="padding:0.8rem;border-radius:12px;border:1px dashed rgba(201,162,39,0.18);background:rgba(255,255,255,0.02);color:var(--parchment-dim);font-size:0.68rem;line-height:1.5;">Pick a tool, provide a short prompt, and run it here. Direct feature access remains available in the rest of the UI.</div>';
      }
      const provider = result.provider || {};
      const actions = [];
      if (result.action === 'generate_map') actions.push('<button class="mini-btn" type="button" data-assistant-util="open_map_studio">Open Map Studio</button>');
      if (result.action === 'describe_scene') actions.push('<button class="mini-btn" type="button" data-assistant-util="send_to_narration">Send to Narration</button>');
      if (result.action === 'draft_npc_line') actions.push('<button class="mini-btn" type="button" data-assistant-util="copy_text">Copy Line</button>');
      if (result.action === 'ask_rules') actions.push('<button class="mini-btn" type="button" data-assistant-util="copy_text">Copy Answer</button>');
      if (result.action === 'suggest_ambience') actions.push('<button class="mini-btn" type="button" data-assistant-util="apply_track">Apply Track</button>');
      if (result.action === 'suggest_encounter') actions.push('<button class="mini-btn" type="button" data-assistant-util="copy_text">Copy Seed</button>');
      if (result.action === 'suggest_loot') actions.push('<button class="mini-btn" type="button" data-assistant-util="copy_text">Copy Loot</button>');
      if (result.action === 'draft_session_recap') actions.push('<button class="mini-btn" type="button" data-assistant-util="copy_text">Copy Recap</button>');
      const textBlock = result.content?.text ? `<div style="white-space:pre-wrap;line-height:1.55;color:var(--parchment);font-size:0.74rem;">${esc(result.content.text)}</div>` : '';
      const mapImage = result.content?.image?.url ? `<img src="${esc(result.content.image.url)}" alt="Assistant generated map preview" style="width:100%;display:block;margin-top:0.6rem;border-radius:10px;border:1px solid rgba(201,162,39,0.16);background:rgba(0,0,0,0.18);" />` : '';
      const ambienceBits = result.action === 'suggest_ambience' ? `<div style="margin-top:0.45rem;font-size:0.68rem;color:var(--parchment-dim);">SFX ideas: ${esc((result.content?.suggested_sfx || []).join(', ') || 'None')}<br>Why: ${esc((result.content?.reasoning || []).join('; '))}</div>` : '';
      const encounterBits = result.action === 'suggest_encounter' ? `<div style="margin-top:0.45rem;font-size:0.68rem;color:var(--parchment-dim);line-height:1.5;">Enemy groups: ${esc((result.content?.enemy_groups || []).join(', '))}<br>Pacing: ${esc(result.content?.pacing || '')}<br>Set piece: ${esc(result.content?.set_piece || '')}</div>` : '';
      const lootBits = result.action === 'suggest_loot' ? `<div style="margin-top:0.45rem;font-size:0.68rem;color:var(--parchment-dim);line-height:1.5;">Gold: ${esc(String(result.content?.gold || 0))} gp<br>Items: ${esc((result.content?.items || []).map((item) => item.name || item.id).join(', ') || 'None')}</div>` : '';
      return `
        <div style="padding:0.8rem;border-radius:12px;border:1px solid rgba(0,229,204,0.18);background:rgba(255,255,255,0.03);display:grid;gap:0.55rem;">
          <div style="display:flex;justify-content:space-between;gap:0.75rem;align-items:flex-start;">
            <div>
              <div style="font-family:'Cinzel',serif;color:var(--gold);font-size:0.88rem;">${esc(result.title || this.currentConfig().label)}</div>
              <div style="margin-top:0.18rem;font-size:0.66rem;color:var(--parchment-dim);line-height:1.45;">${esc(result.summary || '')}</div>
            </div>
            <div style="text-align:right;font-size:0.58rem;color:var(--parchment-dim);line-height:1.4;">
              <div>Provider: ${esc(humanize(provider.primary || provider.provider || 'Unknown'))}</div>
              <div>${provider.fallback_reason ? `Fallback: ${esc(humanize(provider.fallback_reason))}` : 'Fallback: none'}</div>
            </div>
          </div>
          ${textBlock}
          ${ambienceBits}
          ${encounterBits}
          ${lootBits}
          ${mapImage}
          <div style="display:flex;gap:0.45rem;flex-wrap:wrap;">${actions.join('')}</div>
        </div>`;
    }

    renderHistory() {
      if (!this.state.history.length) {
        return '<div style="font-size:0.64rem;color:var(--parchment-dim);">No recent assistant actions yet.</div>';
      }
      return this.state.history.map((entry) => `
        <div style="padding:0.45rem 0.55rem;border-radius:10px;border:1px solid rgba(201,162,39,0.12);background:rgba(255,255,255,0.02);display:grid;gap:0.18rem;">
          <div style="display:flex;justify-content:space-between;gap:0.4rem;">
            <strong style="font-size:0.66rem;color:var(--gold);font-weight:700;">${esc(humanize(entry.action))}</strong>
            <span style="font-size:0.55rem;color:var(--parchment-dim);">${esc(new Date(entry.at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }))}</span>
          </div>
          <div style="font-size:0.62rem;color:var(--parchment-dim);line-height:1.45;">${esc(entry.summary || entry.title || '')}</div>
        </div>`).join('');
    }

    render() {
      if (!this.host) return;
      if (this.state.role !== 'dm') {
        this.host.innerHTML = '<div style="font-size:0.68rem;color:var(--parchment-dim);line-height:1.5;">DM Assistant is only available to the DM.</div>';
        return;
      }
      const config = this.currentConfig();
      const tools = (this.state.status && Array.isArray(this.state.status.tools)) ? this.state.status.tools : [];
      const toolTabs = Object.entries(ACTIONS).map(([key, meta]) => {
        const tool = tools.find((entry) => entry.key === key) || {};
        const disabled = tool.available === false;
        return `<button type="button" data-assistant-action="${key}" class="mini-btn${this.state.selectedAction === key ? ' active' : ''}" style="${disabled ? 'opacity:0.58;' : ''}">${esc(meta.label)}</button>`;
      }).join('');
      const statusText = this.state.status
        ? `Tools are routed through the Stage 1 assistant layer. Narration: ${esc(humanize(this.state.status.providers?.narration?.effective_provider || 'browser_fallback'))}. Cartographer: ${esc(humanize(this.state.status.providers?.cartographer?.image_provider || 'stub'))}.`
        : 'Loading assistant provider status…';
      this.host.innerHTML = `
        <div class="sidebar-label" style="display:flex;align-items:center;gap:0.45rem;"><span>🧙</span> DM Assistant</div>
        <div style="font-size:0.64rem;color:var(--parchment-dim);line-height:1.5;margin-bottom:0.7rem;">One entry point for your AI-adjacent DM tools. Direct Map Studio, narration, chat, and NPC workflows remain available while this layer matures.</div>
        <div style="margin-bottom:0.7rem;padding:0.45rem 0.55rem;border-radius:10px;border:1px solid rgba(0,229,204,0.16);background:rgba(0,0,0,0.18);font-size:0.6rem;color:var(--parchment-dim);line-height:1.45;">${statusText}</div>
        <div style="display:flex;flex-wrap:wrap;gap:0.38rem;margin-bottom:0.7rem;">${toolTabs}</div>
        <div style="padding:0.8rem;border-radius:12px;border:1px solid rgba(201,162,39,0.14);background:rgba(255,255,255,0.02);display:grid;gap:0.6rem;">
          <div style="font-family:'Cinzel',serif;color:var(--gold);font-size:0.82rem;">${esc(config.label)}</div>
          <div style="font-size:0.65rem;color:var(--parchment-dim);line-height:1.5;">${esc(config.intro)}</div>
          ${(config.fields || []).map((field) => this.renderField(field)).join('')}
          <div style="display:flex;gap:0.45rem;align-items:center;flex-wrap:wrap;">
            <button class="mini-btn" type="button" data-assistant-submit="1" ${this.state.loading ? 'disabled' : ''}>${this.state.loading ? 'Working…' : 'Run Assistant Action'}</button>
            <button class="mini-btn" type="button" data-assistant-util="open_map_studio" ${this.state.selectedAction !== 'generate_map' ? 'style="display:none;"' : ''}>Open direct tool</button>
          </div>
        </div>
        <div style="margin-top:0.8rem;display:grid;gap:0.45rem;">
          <div style="font-family:'Cinzel',serif;color:var(--gold);font-size:0.76rem;">Result</div>
          ${this.renderResult()}
        </div>
        <div style="margin-top:0.8rem;display:grid;gap:0.45rem;">
          <div style="display:flex;justify-content:space-between;gap:0.5rem;align-items:center;">
            <div style="font-family:'Cinzel',serif;color:var(--gold);font-size:0.76rem;">Recent actions</div>
            <button class="mini-btn" type="button" data-assistant-util="refresh_status">Refresh status</button>
          </div>
          <div style="display:grid;gap:0.35rem;">${this.renderHistory()}</div>
        </div>`;
      const refreshBtn = this.host.querySelector('[data-assistant-util="refresh_status"]');
      if (refreshBtn) refreshBtn.onclick = () => this.refreshStatus();
    }
  }

  const controller = new DMAssistantController();
  window.DMAssistant = controller;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => controller.mount());
  } else {
    controller.mount();
  }
})();
