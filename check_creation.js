
    const STEPS = [
      { key: 'hero', title: 'Hero Identity', copy: 'Start with the core identity of the hero entering this realm.' },
      { key: 'species', title: 'Species & Look', copy: 'Pick the ancestry and visual type. The preview updates immediately.' },
      { key: 'class', title: 'Class & Style', copy: 'Choose a class. Starter gold, weapons, and style all update from this choice.' },
      { key: 'background', title: 'Background', copy: 'Give the hero a place in the world and a role in the story.' },
      { key: 'abilities', title: 'Abilities', copy: 'Assign your stats using the curated array so the hero is ready for play.' },
      { key: 'equipment', title: 'Equipment', copy: 'Review the automatic 50 GP and class-based starter gear for this hero.' },
      { key: 'backstory', title: 'Backstory', copy: 'Add the personal details that make the hero feel lived in.' },
      { key: 'confirm', title: 'Confirm & Enter', copy: 'Review the finished hero, save them to Dice, then enter the realm.' }
    ];
    const GENDERS = [
      { id: 'male', label: 'Male', pronouns: 'He / Him' },
      { id: 'female', label: 'Female', pronouns: 'She / Her' },
      { id: 'nonbinary', label: 'Non-binary', pronouns: 'They / Them' },
    ];
    const STAT_ARRAY = [15, 14, 13, 12, 10, 8];
    const STATS = [
      ['strength', 'STR'], ['dexterity', 'DEX'], ['constitution', 'CON'],
      ['intelligence', 'INT'], ['wisdom', 'WIS'], ['charisma', 'CHA']
    ];
    const FALLBACK_SPECIES = [
      { id: 'human', name: 'Human', description: 'Versatile and ambitious, ready to thrive in any realm.', speed: 30, size: 'Medium', gameplayBenefits: ['Adaptable', 'Extra feat-ready'], summary: 'Balanced and flexible adventurers.' },
      { id: 'elf', name: 'Elf', description: 'Graceful, sharp-sensed wanderers with refined magic and motion.', speed: 30, size: 'Medium', gameplayBenefits: ['Darkvision', 'Fey grace'], summary: 'Agile and perceptive.' },
      { id: 'dwarf', name: 'Dwarf', description: 'Stone-hewn survivors built for endurance and grim resolve.', speed: 25, size: 'Medium', gameplayBenefits: ['Resilience', 'Craft lore'], summary: 'Hardy and steadfast.' },
      { id: 'halfling', name: 'Halfling', description: 'Small, lucky heroes who punch well above their weight.', speed: 25, size: 'Small', gameplayBenefits: ['Lucky', 'Brave'], summary: 'Quick and deceptively dangerous.' },
      { id: 'tiefling', name: 'Tiefling', description: 'Infernal-blooded wanderers with horns, mystery, and presence.', speed: 30, size: 'Medium', gameplayBenefits: ['Darkvision', 'Infernal legacy'], summary: 'Bold and arcane-touched.' },
      { id: 'dragonborn', name: 'Dragonborn', description: 'Scaled descendants of ancient drakes with a breath of power.', speed: 30, size: 'Medium', gameplayBenefits: ['Breath weapon', 'Scaled hide'], summary: 'Proud draconic warriors.' },
      { id: 'warforged', name: 'Warforged', description: 'Forged bodies with living souls, steel in frame and purpose in heart.', speed: 30, size: 'Medium', gameplayBenefits: ['Construct resilience', 'Integrated armor'], summary: 'Mechanical and resolute.' },
      { id: 'tabaxi', name: 'Tabaxi', description: 'Feline explorers with speed, curiosity, and a hunter’s edge.', speed: 30, size: 'Medium', gameplayBenefits: ['Cat agility', 'Claws'], summary: 'Fast and nimble.' }
    ];
    const FALLBACK_CLASSES = [
      { id: 'barbarian', displayName: 'Barbarian', summary: 'A brutal front-liner fueled by fury.', hitDie: 12, primaryAbility: 'Strength', spellcaster: 'none', startingEquipment: ['Greataxe', 'Handaxe (×2)', 'Explorer\'s Pack'], accentColor: '#d06a3f' },
      { id: 'bard', displayName: 'Bard', summary: 'A performer whose words and music shape fate.', hitDie: 8, primaryAbility: 'Charisma', spellcaster: 'full', startingEquipment: ['Rapier', 'Lute', 'Leather Armor', 'Diplomat\'s Pack'], accentColor: '#9b6de3' },
      { id: 'cleric', displayName: 'Cleric', summary: 'A divine champion with healing, radiance, and steel.', hitDie: 8, primaryAbility: 'Wisdom', spellcaster: 'full', startingEquipment: ['Mace', 'Scale Mail', 'Shield', 'Holy Symbol'], accentColor: '#d8b34a' },
      { id: 'druid', displayName: 'Druid', summary: 'A primal caster tied to nature, beast, and season.', hitDie: 8, primaryAbility: 'Wisdom', spellcaster: 'full', startingEquipment: ['Wooden Staff', 'Leather Armor', 'Explorer\'s Pack'], accentColor: '#4fa56a' },
      { id: 'fighter', displayName: 'Fighter', summary: 'A martial specialist with reliable weapons and armor.', hitDie: 10, primaryAbility: 'Strength', spellcaster: 'none', startingEquipment: ['Chain Mail', 'Longsword', 'Shield', 'Dungeoneer\'s Pack'], accentColor: '#4a73d8' },
      { id: 'monk', displayName: 'Monk', summary: 'A disciplined combatant built on speed and technique.', hitDie: 8, primaryAbility: 'Dexterity', spellcaster: 'none', startingEquipment: ['Shortsword', 'Quarterstaff', 'Explorer\'s Pack'], accentColor: '#bb8753' },
      { id: 'paladin', displayName: 'Paladin', summary: 'A sacred knight whose oath carries holy power.', hitDie: 10, primaryAbility: 'Strength', spellcaster: 'half', startingEquipment: ['Chain Mail', 'Longsword', 'Shield', 'Holy Symbol'], accentColor: '#e0c85f' },
      { id: 'ranger', displayName: 'Ranger', summary: 'A hunter between wilderness craft and martial skill.', hitDie: 10, primaryAbility: 'Dexterity', spellcaster: 'half', startingEquipment: ['Longbow', 'Quiver (20 arrows)', 'Shortsword (×2)', 'Leather Armor'], accentColor: '#6c9c44' },
      { id: 'rogue', displayName: 'Rogue', summary: 'A stealthy skirmisher built on finesse and precision.', hitDie: 8, primaryAbility: 'Dexterity', spellcaster: 'none', startingEquipment: ['Rapier', 'Shortbow', 'Leather Armor', 'Thieves\' Tools'], accentColor: '#6551b6' },
      { id: 'sorcerer', displayName: 'Sorcerer', summary: 'An innate caster whose power erupts from within.', hitDie: 6, primaryAbility: 'Charisma', spellcaster: 'full', startingEquipment: ['Light Crossbow', 'Arcane Focus', 'Dungeoneer\'s Pack'], accentColor: '#d25dd9' },
      { id: 'warlock', displayName: 'Warlock', summary: 'A pact-bound caster wielding strange, forbidden gifts.', hitDie: 8, primaryAbility: 'Charisma', spellcaster: 'pact', startingEquipment: ['Light Crossbow', 'Arcane Focus', 'Scholar\'s Pack'], accentColor: '#6d3ebb' },
      { id: 'wizard', displayName: 'Wizard', summary: 'A scholar of spellcraft, precision, and learned magic.', hitDie: 6, primaryAbility: 'Intelligence', spellcaster: 'full', startingEquipment: ['Quarterstaff', 'Spellbook', 'Scholar\'s Pack', 'Arcane Focus'], accentColor: '#5a7fdd' },
      { id: 'tinker', displayName: 'Tinker', summary: 'A homebrew inventor blending gadgets, alchemy, and grit.', hitDie: 8, primaryAbility: 'Intelligence', spellcaster: 'half', startingEquipment: ['Tinker\'s Tools', 'Leather Armor', 'Hand Crossbow', 'Mechanical Companion'], accentColor: '#cf9b47' },
      { id: 'pirate', displayName: 'Pirate', summary: 'A homebrew swashbuckler of pistols, blades, and swagger.', hitDie: 10, primaryAbility: 'Dexterity', spellcaster: 'none', startingEquipment: ['Cutlass', 'Flintlock Pistol', 'Navigator\'s Tools', 'Leather Armor'], accentColor: '#a65d37' }
    ];
    const FALLBACK_BACKGROUNDS = [
      { id: 'acolyte', name: 'Acolyte', summary: 'Raised in faith and ritual.' },
      { id: 'criminal', name: 'Criminal', summary: 'A life of secrets, fences, and close calls.' },
      { id: 'folk-hero', name: 'Folk Hero', summary: 'A local savior with a name worth repeating.' },
      { id: 'noble', name: 'Noble', summary: 'Power, title, and expectation.' },
      { id: 'outlander', name: 'Outlander', summary: 'A survivalist from beyond the city walls.' },
      { id: 'sage', name: 'Sage', summary: 'Driven by knowledge, lore, and old ruins.' },
      { id: 'soldier', name: 'Soldier', summary: 'Disciplined by war and command.' },
      { id: 'urchin', name: 'Urchin', summary: 'Streetwise, scrappy, and impossible to pin down.' },
    ];

    const params = new URLSearchParams(location.search);
    const SESSION_ID = String(params.get('session') || '').trim().toUpperCase();
    const INVITE = String(params.get('code') || '').trim();
    const ROLE = String(params.get('role') || 'player').trim().toLowerCase();

    const state = {
      authUser: null,
      campaignName: 'Unknown realm',
      step: 0,
      species: [],
      classes: [],
      backgrounds: FALLBACK_BACKGROUNDS,
      hero: {
        name: '', gender: 'male', pronouns: 'He / Him', deity: '', homeland: '',
        speciesId: '', classId: '', backgroundId: '', alignment: '',
        personalityTraits: '', ideals: '', bonds: '', flaws: '', backstory: '',
        stats: { strength: 10, dexterity: 10, constitution: 10, intelligence: 10, wisdom: 10, charisma: 10 },
        assigned: { strength: null, dexterity: null, constitution: null, intelligence: null, wisdom: null, charisma: null },
        remaining: [...STAT_ARRAY],
      }
    };

    const els = {
      steps: document.getElementById('steps'),
      stepTitle: document.getElementById('step-title'),
      stepCopy: document.getElementById('step-copy'),
      feedback: document.getElementById('feedback'),
      stepView: document.getElementById('step-view'),
      next: document.getElementById('next-step'),
      back: document.getElementById('back-step'),
      cancel: document.getElementById('cancel-btn'),
      avatar: document.getElementById('avatar-preview'),
      heroTitle: document.getElementById('hero-title'),
      heroSubtitle: document.getElementById('hero-subtitle'),
      heroCampaign: document.getElementById('hero-campaign'),
      backLink: document.getElementById('back-link'),
      badgeGold: document.getElementById('badge-gold'),
      badgeClass: document.getElementById('badge-class'),
      badgeSpecies: document.getElementById('badge-species'),
    };

    function setFeedback(message, type) {
      els.feedback.textContent = message || '';
      els.feedback.className = 'feedback' + (type ? (' ' + type) : '');
    }
    function getCsrfToken() {
      const match = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/);
      return match ? decodeURIComponent(match[1]) : '';
    }
    async function fetchJson(url, options = {}) {
      const opts = Object.assign({ credentials: 'same-origin' }, options || {});
      opts.headers = Object.assign({}, opts.headers || {});
      const needsCsrf = /^(POST|PUT|PATCH|DELETE)$/i.test(String(opts.method || 'GET'));
      if (needsCsrf) {
        const csrf = getCsrfToken();
        if (csrf && !opts.headers['X-CSRF-Token']) opts.headers['X-CSRF-Token'] = csrf;
      }
      const res = await fetch(url, opts);
      let data = null;
      try { data = await res.json(); } catch (_) { data = null; }
      if (!res.ok) throw new Error((data && (data.detail || data.error)) || 'Request failed');
      return data;
    }
    function redirectToLogin() {
      const next = encodeURIComponent(location.pathname + location.search);
      location.href = '/player?next=' + next;
    }
    function getRosterUrl(createdId = '') {
      const q = new URLSearchParams({ session: SESSION_ID, code: INVITE, role: ROLE });
      if (createdId) q.set('created', createdId);
      return '/join?' + q.toString();
    }
    function getPlayerKey() { return state.authUser && state.authUser.id ? ('auth_' + state.authUser.id) : ''; }
    function selectedSpecies() { return state.species.find(s => s.id === state.hero.speciesId) || state.species[0] || null; }
    function selectedClass() { return state.classes.find(c => c.id === state.hero.classId) || state.classes[0] || null; }
    function selectedBackground() { return state.backgrounds.find(b => b.id === state.hero.backgroundId) || state.backgrounds[0] || null; }
    function modStr(score) { const m = Math.floor((Number(score || 10) - 10) / 2); return m >= 0 ? ('+' + m) : String(m); }
    function scoreSum() { return Object.values(state.hero.stats).reduce((n,v)=>n+Number(v||0),0); }
    function classPrimaryAbilityLabel(item) {
      return item.primaryAbility || item.primary_ability || item.spellcastingAbility || 'Primary stat';
    }
    function classDisplayName(item) { return item.displayName || item.name || item.id || 'Class'; }
    function speciesDisplayName(item) { return item.displayName || item.name || item.id || 'Species'; }
    function backgroundDisplayName(item) { return item.displayName || item.name || item.id || 'Background'; }
    function equipmentForClass(item) {
      const raw = item && (item.startingEquipment || item.starting_equipment || item.starting_items || item.equipmentPicks || item.equipment_picks || []);
      if (Array.isArray(raw) && raw.length) return raw.map(v => typeof v === 'string' ? v : (v.name || v.id || '')).filter(Boolean);
      return ['Traveler clothes', 'Starter pack'];
    }
    function classAccent(item) { return item.accentColor || item.accent_color || '#d0a65f'; }
    function normalizeCatalogClasses(items) {
      return (Array.isArray(items) ? items : []).map(item => ({
        id: String(item.id || item.classId || item.name || '').trim().toLowerCase().replace(/\s+/g, '-'),
        displayName: item.displayName || item.name || item.id || 'Class',
        summary: item.summary || item.description || 'A character class ready for adventure.',
        hitDie: item.hitDie || item.hit_die || item.hitPointsPerLevel || 8,
        primaryAbility: item.primaryAbility || item.primary_ability || item.spellcastingAbility || 'Primary stat',
        spellcaster: item.spellcaster || item.casterType || 'none',
        startingEquipment: equipmentForClass(item),
        accentColor: classAccent(item),
      })).filter(item => item.id);
    }
    function normalizeCatalogSpecies(items) {
      return (Array.isArray(items) ? items : []).map(item => ({
        id: String(item.id || item.name || '').trim().toLowerCase().replace(/\s+/g, '-'),
        name: item.displayName || item.name || item.id || 'Species',
        description: item.summary || item.description || 'A playable ancestry.',
        speed: Number(item.speed || 30),
        size: item.size || 'Medium',
        gameplayBenefits: Array.isArray(item.gameplayBenefits) ? item.gameplayBenefits : (Array.isArray(item.traits) ? item.traits.slice(0,2) : []),
        summary: item.summary || item.description || '',
      })).filter(item => item.id);
    }
    function renderSteps() {
      els.steps.innerHTML = STEPS.map((step, idx) => {
        const cls = idx === state.step ? 'step-pill active' : (idx < state.step ? 'step-pill done' : 'step-pill');
        const num = idx < state.step ? '✓' : String(idx + 1);
        return `<div class="${cls}"><span class="step-num">${num}</span><span>${step.title}</span></div>`;
      }).join('');
    }
    function renderAvatarSVG(size = 250) {
      const species = selectedSpecies() || { id: 'human', name: 'Human' };
      const klass = selectedClass() || { id: 'fighter', displayName: 'Fighter', accentColor: '#d0a65f' };
      const accent = classAccent(klass);
      const gender = state.hero.gender;
      const skinMap = { male: '#d4a27f', female: '#e2b996', nonbinary: '#c89673' };
      const skin = skinMap[gender] || '#d4a27f';
      const horn = species.id.includes('tiefling');
      const scales = species.id.includes('dragon');
      const ears = species.id.includes('elf') || species.id.includes('halfling');
      const metal = species.id.includes('warforged');
      const feline = species.id.includes('tabaxi');
      const beard = species.id.includes('dwarf');
      const color = accent;
      return `
      <svg width="${size}" height="${size}" viewBox="0 0 260 320" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="${species.name} ${classDisplayName(klass)} preview">
        <defs>
          <radialGradient id="aura" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(130 115) rotate(90) scale(120 92)">
            <stop stop-color="${color}" stop-opacity="0.35"/>
            <stop offset="1" stop-color="${color}" stop-opacity="0"/>
          </radialGradient>
          <linearGradient id="body" x1="130" y1="85" x2="130" y2="260" gradientUnits="userSpaceOnUse">
            <stop stop-color="${color}" stop-opacity="0.85"/>
            <stop offset="1" stop-color="#24150f"/>
          </linearGradient>
        </defs>
        <ellipse cx="130" cy="120" rx="96" ry="76" fill="url(#aura)" />
        <ellipse cx="130" cy="290" rx="42" ry="10" fill="rgba(0,0,0,0.38)"/>
        <path d="M98 118C98 98 111 84 130 84C149 84 162 98 162 118V152C162 174 149 188 130 188C111 188 98 174 98 152V118Z" fill="${metal ? '#b8b0aa' : skin}" stroke="rgba(0,0,0,0.18)" stroke-width="2"/>
        ${ears ? '<path d="M92 126L78 118L84 140L98 134Z" fill="'+(metal ? '#b8b0aa':skin)+'" opacity="0.95"/><path d="M168 126L182 118L176 140L162 134Z" fill="'+(metal ? '#b8b0aa':skin)+'" opacity="0.95"/>' : ''}
        ${horn ? '<path d="M110 84C106 58 92 40 82 32C86 54 90 72 98 90Z" fill="#7c5a4b"/><path d="M150 84C154 58 168 40 178 32C174 54 170 72 162 90Z" fill="#7c5a4b"/>' : ''}
        ${feline ? '<path d="M102 90L92 68L114 82Z" fill="'+skin+'"/><path d="M158 90L168 68L146 82Z" fill="'+skin+'"/>' : ''}
        <path d="M92 208C104 190 118 182 130 182C142 182 156 190 168 208L182 278H78L92 208Z" fill="url(#body)" stroke="rgba(255,255,255,0.08)"/>
        <path d="M116 202H144L152 278H108L116 202Z" fill="rgba(255,255,255,0.06)"/>
        <circle cx="116" cy="132" r="4" fill="#1a120d"/>
        <circle cx="144" cy="132" r="4" fill="#1a120d"/>
        <path d="M121 156C126 160 134 160 139 156" stroke="#8a4f40" stroke-width="2.8" stroke-linecap="round"/>
        <path d="M115 114C120 110 126 109 131 110" stroke="rgba(0,0,0,0.22)" stroke-width="3" stroke-linecap="round"/>
        <path d="M145 114C140 110 134 109 129 110" stroke="rgba(0,0,0,0.22)" stroke-width="3" stroke-linecap="round"/>
        ${beard ? '<path d="M102 162C112 188 148 188 158 162C150 192 110 194 102 162Z" fill="#5f3619"/>' : ''}
        ${scales ? '<path d="M104 98C120 90 140 90 156 98C148 108 112 108 104 98Z" fill="#8bb1d5" opacity="0.5"/>' : ''}
        <path d="M98 206C90 224 86 244 84 278" stroke="${color}" stroke-opacity="0.55" stroke-width="10" stroke-linecap="round"/>
        <path d="M162 206C170 224 174 244 176 278" stroke="${color}" stroke-opacity="0.55" stroke-width="10" stroke-linecap="round"/>
        <path d="M114 278C112 242 111 226 108 214" stroke="#2c1b15" stroke-width="12" stroke-linecap="round"/>
        <path d="M146 278C148 242 149 226 152 214" stroke="#2c1b15" stroke-width="12" stroke-linecap="round"/>
        ${klass.id.includes('wizard') || klass.id.includes('sorcerer') || klass.id.includes('warlock') || klass.id.includes('druid') || klass.id.includes('bard') ? '<path d="M188 120L196 214" stroke="'+color+'" stroke-width="8" stroke-linecap="round"/><circle cx="186" cy="114" r="12" fill="'+color+'" fill-opacity="0.35" stroke="'+color+'"/>' : ''}
        ${klass.id.includes('fighter') || klass.id.includes('paladin') || klass.id.includes('cleric') ? '<path d="M72 130L72 222" stroke="#b4aca4" stroke-width="8" stroke-linecap="round"/><path d="M58 138H86L80 178H64Z" fill="rgba(255,255,255,0.18)" stroke="#d2c1af"/>' : ''}
        ${klass.id.includes('rogue') || klass.id.includes('ranger') || klass.id.includes('pirate') ? '<path d="M182 134L206 166" stroke="#c8b19b" stroke-width="6" stroke-linecap="round"/><path d="M206 166L198 194" stroke="#c8b19b" stroke-width="6" stroke-linecap="round"/>' : ''}
      </svg>`;
    }
    function renderPreview() {
      els.avatar.innerHTML = renderAvatarSVG(window.innerWidth < 760 ? 220 : 250);
      const sp = selectedSpecies();
      const cls = selectedClass();
      const bg = selectedBackground();
      els.heroTitle.textContent = state.hero.name.trim() || 'Unnamed Hero';
      els.heroSubtitle.textContent = `${sp ? speciesDisplayName(sp) : 'Unset species'} · ${cls ? classDisplayName(cls) : 'Unset class'} · ${bg ? backgroundDisplayName(bg) : 'Unset background'}`;
      els.heroCampaign.textContent = 'Realm: ' + (state.campaignName || 'Unknown campaign');
      els.badgeClass.textContent = 'Class · ' + (cls ? classDisplayName(cls) : 'Unset');
      els.badgeSpecies.textContent = 'Species · ' + (sp ? speciesDisplayName(sp) : 'Unset');
      els.badgeGold.textContent = 'Starting Gold · 50 GP';
    }
    function renderStepView() {
      const step = STEPS[state.step];
      els.stepTitle.textContent = step.title;
      els.stepCopy.textContent = step.copy;
      els.back.textContent = state.step === 0 ? 'Back to roster' : 'Previous step';
      els.next.textContent = state.step === STEPS.length - 1 ? 'Save & Enter Realm' : 'Next step';
      els.stepView.innerHTML = renderStepMarkup();
      bindStepMarkup();
      renderPreview();
      renderSteps();
    }
    function renderOptionCard(item, type, selectedId) {
      const id = item.id;
      const selected = id === selectedId ? ' selected' : '';
      const title = type === 'class' ? classDisplayName(item) : (type === 'species' ? speciesDisplayName(item) : backgroundDisplayName(item));
      const desc = item.summary || item.description || 'Ready for the realm.';
      const accent = type === 'class' ? classAccent(item) : '#a7c5ff';
      let tags = '';
      if (type === 'class') {
        tags = `<span class="tag">d${item.hitDie || 8} hit die</span><span class="tag">${classPrimaryAbilityLabel(item)}</span>${item.spellcaster && item.spellcaster !== 'none' ? `<span class="tag">${String(item.spellcaster).toUpperCase()} caster</span>` : '<span class="tag">Martial</span>'}`;
      } else if (type === 'species') {
        tags = `<span class="tag">${item.size || 'Medium'}</span><span class="tag">${item.speed || 30} ft</span>${(item.gameplayBenefits || []).slice(0,1).map(v => `<span class="tag">${v}</span>`).join('')}`;
      } else {
        tags = `<span class="tag">Background</span>`;
      }
      return `<button type="button" class="option-card${selected}" data-option-type="${type}" data-option-id="${escapeHtml(id)}">
        <div class="mini-portrait">${renderMiniGlyph(type, item, accent)}</div>
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(desc)}</p>
        </div>
        <div class="card-tags">${tags}</div>
      </button>`;
    }
    function renderMiniGlyph(type, item, accent) {
      if (type === 'species') {
        return `<svg width="86" height="86" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" fill="none"><circle cx="60" cy="60" r="56" fill="${accent}" fill-opacity="0.12"/><circle cx="60" cy="42" r="22" fill="#d9b08b"/>${String(item.id||'').includes('elf') ? '<path d="M31 42L18 36L24 54L36 49Z" fill="#d9b08b"/><path d="M89 42L102 36L96 54L84 49Z" fill="#d9b08b"/>' : ''}${String(item.id||'').includes('tiefling') ? '<path d="M44 28C40 14 34 8 28 3C31 16 35 24 41 33Z" fill="#78574a"/><path d="M76 28C80 14 86 8 92 3C89 16 85 24 79 33Z" fill="#78574a"/>' : ''}<path d="M34 72C40 58 50 52 60 52C70 52 80 58 86 72L91 102H29L34 72Z" fill="#2e2017" opacity="0.85"/></svg>`;
      }
      if (type === 'class') {
        return `<svg width="92" height="92" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" fill="none"><circle cx="60" cy="60" r="56" fill="${accent}" fill-opacity="0.14"/><path d="M42 42C42 32 50 24 60 24C70 24 78 32 78 42V58C78 68 70 76 60 76C50 76 42 68 42 58V42Z" fill="#d9b08b"/><path d="M38 82C45 72 52 68 60 68C68 68 75 72 82 82L88 104H32L38 82Z" fill="${accent}" fill-opacity="0.9"/>${String(item.id||'').includes('wizard') || String(item.id||'').includes('warlock') || String(item.id||'').includes('sorcerer') ? '<circle cx="90" cy="36" r="10" fill="'+accent+'" fill-opacity="0.36" stroke="'+accent+'"/><path d="M92 46L86 88" stroke="'+accent+'" stroke-width="6" stroke-linecap="round"/>' : ''}${String(item.id||'').includes('fighter') || String(item.id||'').includes('paladin') || String(item.id||'').includes('cleric') ? '<path d="M28 46V96" stroke="#d7c7b8" stroke-width="7" stroke-linecap="round"/><path d="M18 54H38L34 74H22Z" fill="rgba(255,255,255,0.22)" stroke="#d7c7b8"/>' : ''}</svg>`;
      }
      return `<svg width="92" height="92" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" fill="none"><circle cx="60" cy="60" r="56" fill="${accent}" fill-opacity="0.10"/><path d="M30 78C41 52 79 52 90 78" stroke="${accent}" stroke-width="8" stroke-linecap="round"/><path d="M38 90C48 84 72 84 82 90" stroke="#f1ddbc" stroke-width="8" stroke-linecap="round"/></svg>`;
    }
    function renderStepMarkup() {
      const step = STEPS[state.step].key;
      const hero = state.hero;
      if (step === 'hero') {
        return `
          <div class="form-grid">
            <div class="field"><label>Hero Name</label><input class="input" id="hero-name" value="${escapeHtml(hero.name)}" placeholder="Name your adventurer" /></div>
            <div class="field"><label>Pronouns</label><select class="select" id="hero-pronouns">${GENDERS.map(g => `<option value="${g.pronouns}" ${hero.pronouns === g.pronouns ? 'selected' : ''}>${g.pronouns}</option>`).join('')}</select></div>
            <div class="field full"><label>Identity Style</label><div class="card-grid">${GENDERS.map(g => `<button type="button" class="option-card${hero.gender===g.id ? ' selected' : ''}" data-gender="${g.id}"><div class="mini-portrait">${renderMiniGlyph('background',{id:g.id}, '#a787de')}</div><div><h3>${g.label}</h3><p>${g.pronouns}</p></div><div class="card-tags"><span class="tag">Preview style</span><span class="tag">Hero card art</span></div></button>`).join('')}</div></div>
            <div class="field"><label>Homeland</label><input class="input" id="hero-homeland" value="${escapeHtml(hero.homeland)}" placeholder="Where are they from?" /></div>
            <div class="field"><label>Patron / Deity</label><input class="input" id="hero-deity" value="${escapeHtml(hero.deity)}" placeholder="Optional faith or patron" /></div>
          </div>`;
      }
      if (step === 'species') {
        return `<div class="card-grid">${state.species.map(item => renderOptionCard(item, 'species', hero.speciesId)).join('')}</div>`;
      }
      if (step === 'class') {
        return `<div class="card-grid">${state.classes.map(item => renderOptionCard(item, 'class', hero.classId)).join('')}</div>`;
      }
      if (step === 'background') {
        return `<div class="card-grid">${state.backgrounds.map(item => renderOptionCard(item, 'background', hero.backgroundId)).join('')}</div>`;
      }
      if (step === 'abilities') {
        return `<div class="ability-grid">${STATS.map(([key,label]) => {
          const score = hero.stats[key];
          return `<div class="ability-card"><div class="ability-head"><strong>${label}</strong><span class="ability-score">${score} (${modStr(score)})</span></div><div class="stat-choices">${STAT_ARRAY.map(v => {
            const used = hero.assigned[key] !== v && !hero.remaining.includes(v);
            const active = hero.assigned[key] === v;
            return `<button type="button" class="stat-choice${used ? ' used' : ''}" data-stat="${key}" data-value="${v}" ${used ? 'disabled' : ''} style="${active ? 'background:rgba(156,224,219,0.18); color:#c9fff8; border:1px solid rgba(156,224,219,0.38);' : ''}">${v}</button>`;
          }).join('')}</div></div>`;
        }).join('')}</div>`;
      }
      if (step === 'equipment') {
        const cls = selectedClass() || { startingEquipment: [] };
        const equipment = equipmentForClass(cls);
        return `<div class="equipment-list">
          <div class="equipment-item"><strong>Starting Gold</strong><span>50 GP</span></div>
          ${equipment.map(item => `<div class="equipment-item"><strong>${escapeHtml(item)}</strong><span>Class starter gear</span></div>`).join('')}
        </div>`;
      }
      if (step === 'backstory') {
        return `<div class="form-grid">
          <div class="field"><label>Alignment</label><input class="input" id="hero-alignment" value="${escapeHtml(hero.alignment)}" placeholder="Neutral Good, Chaotic Neutral, etc." /></div>
          <div class="field"><label>Personality Traits</label><input class="input" id="hero-traits" value="${escapeHtml(hero.personalityTraits)}" placeholder="Short personality notes" /></div>
          <div class="field"><label>Ideals</label><input class="input" id="hero-ideals" value="${escapeHtml(hero.ideals)}" placeholder="What drives them?" /></div>
          <div class="field"><label>Bonds</label><input class="input" id="hero-bonds" value="${escapeHtml(hero.bonds)}" placeholder="What ties them down?" /></div>
          <div class="field full"><label>Flaws</label><input class="input" id="hero-flaws" value="${escapeHtml(hero.flaws)}" placeholder="Weaknesses, fears, habits" /></div>
          <div class="field full"><label>Backstory</label><textarea class="textarea" id="hero-backstory" placeholder="Write the opening chapter of this hero.">${escapeHtml(hero.backstory)}</textarea></div>
        </div>`;
      }
      const cls = selectedClass();
      const sp = selectedSpecies();
      const bg = selectedBackground();
      const equipment = equipmentForClass(cls || {});
      return `<div class="review-list">
        <div class="review-item"><strong>Name</strong><span>${escapeHtml(hero.name || 'Unnamed Hero')}</span></div>
        <div class="review-item"><strong>Species</strong><span>${escapeHtml(sp ? speciesDisplayName(sp) : 'Unset')}</span></div>
        <div class="review-item"><strong>Class</strong><span>${escapeHtml(cls ? classDisplayName(cls) : 'Unset')}</span></div>
        <div class="review-item"><strong>Background</strong><span>${escapeHtml(bg ? backgroundDisplayName(bg) : 'Unset')}</span></div>
        <div class="review-item"><strong>Ability Total</strong><span>${scoreSum()} across the six core stats</span></div>
        <div class="review-item"><strong>Starting Gold</strong><span>50 GP</span></div>
        <div class="review-item"><strong>Starter Gear</strong><span>${escapeHtml(equipment.join(', '))}</span></div>
        <div class="review-item"><strong>Backstory</strong><span>${escapeHtml(hero.backstory || 'No backstory yet')}</span></div>
      </div>`;
    }
    function bindStepMarkup() {
      const step = STEPS[state.step].key;
      if (step === 'hero') {
        document.getElementById('hero-name')?.addEventListener('input', e => { state.hero.name = e.target.value; renderPreview(); });
        document.getElementById('hero-pronouns')?.addEventListener('change', e => { state.hero.pronouns = e.target.value; });
        document.getElementById('hero-homeland')?.addEventListener('input', e => { state.hero.homeland = e.target.value; });
        document.getElementById('hero-deity')?.addEventListener('input', e => { state.hero.deity = e.target.value; });
        document.querySelectorAll('[data-gender]').forEach(btn => btn.addEventListener('click', () => { state.hero.gender = btn.getAttribute('data-gender'); renderStepView(); }));
      } else if (step === 'species' || step === 'class' || step === 'background') {
        document.querySelectorAll('[data-option-id]').forEach(btn => btn.addEventListener('click', () => {
          const id = btn.getAttribute('data-option-id');
          if (step === 'species') state.hero.speciesId = id;
          if (step === 'class') state.hero.classId = id;
          if (step === 'background') state.hero.backgroundId = id;
          renderStepView();
        }));
      } else if (step === 'abilities') {
        document.querySelectorAll('[data-stat][data-value]').forEach(btn => btn.addEventListener('click', () => {
          const stat = btn.getAttribute('data-stat');
          const value = Number(btn.getAttribute('data-value'));
          const current = state.hero.assigned[stat];
          let remaining = [...state.hero.remaining];
          if (current !== null && current !== undefined) remaining.push(current);
          const idx = remaining.indexOf(value);
          if (idx === -1) return;
          remaining.splice(idx, 1);
          remaining.sort((a,b)=>b-a);
          state.hero.assigned[stat] = value;
          state.hero.remaining = remaining;
          state.hero.stats[stat] = value;
          renderStepView();
        }));
      } else if (step === 'backstory') {
        document.getElementById('hero-alignment')?.addEventListener('input', e => { state.hero.alignment = e.target.value; });
        document.getElementById('hero-traits')?.addEventListener('input', e => { state.hero.personalityTraits = e.target.value; });
        document.getElementById('hero-ideals')?.addEventListener('input', e => { state.hero.ideals = e.target.value; });
        document.getElementById('hero-bonds')?.addEventListener('input', e => { state.hero.bonds = e.target.value; });
        document.getElementById('hero-flaws')?.addEventListener('input', e => { state.hero.flaws = e.target.value; });
        document.getElementById('hero-backstory')?.addEventListener('input', e => { state.hero.backstory = e.target.value; });
      }
    }
    function canProceed() {
      const step = STEPS[state.step].key;
      if (step === 'hero') return !!state.hero.name.trim();
      if (step === 'species') return !!state.hero.speciesId;
      if (step === 'class') return !!state.hero.classId;
      if (step === 'background') return !!state.hero.backgroundId;
      if (step === 'abilities') return state.hero.remaining.length === 0;
      return true;
    }
    function buildDraftDocument() {
      const sp = selectedSpecies() || { id: 'human', name: 'Human', speed: 30, size: 'Medium' };
      const cls = selectedClass() || { id: 'fighter', displayName: 'Fighter', startingEquipment: ['Longsword'] };
      const bg = selectedBackground() || { id: 'folk-hero', name: 'Folk Hero' };
      const equipment = equipmentForClass(cls);
      return {
        schemaVersion: 1,
        rulesMode: 'casual',
        ruleset: 'casual-dnd-5e-compatible',
        sourceMode: 'native',
        identity: {
          name: state.hero.name.trim(),
          displayName: state.hero.name.trim(),
          pronouns: state.hero.pronouns,
          alignment: state.hero.alignment,
          deity: state.hero.deity,
          homeland: state.hero.homeland,
          backstory: state.hero.backstory,
          personalityTraits: state.hero.personalityTraits,
          ideals: state.hero.ideals,
          bonds: state.hero.bonds,
          flaws: state.hero.flaws,
        },
        presentation: {
          portraitFrame: 'importer-premium',
          tokenDisplay: {
            scale: 1,
            cropMode: 'cover',
            ringStyle: 'classic',
            accentColor: classAccent(cls),
            labelFormat: 'class_name',
          },
        },
        species: {
          id: sp.id,
          name: speciesDisplayName(sp),
          size: String(sp.size || 'Medium').toLowerCase(),
          speed: Number(sp.speed || 30),
          traits: Array.isArray(sp.gameplayBenefits) ? sp.gameplayBenefits : [],
          senses: [],
          resistances: [],
          gameplayBenefits: Array.isArray(sp.gameplayBenefits) ? sp.gameplayBenefits : [],
          summary: sp.summary || sp.description || '',
        },
        background: {
          id: bg.id,
          name: backgroundDisplayName(bg),
          traits: [],
          proficiencies: [],
          tools: [],
          languages: [],
          equipmentPicks: [],
          featureSummary: bg.summary || '',
        },
        abilities: {
          generationMode: 'standard_array',
          scores: {
            str: Number(state.hero.stats.strength || 10),
            dex: Number(state.hero.stats.dexterity || 10),
            con: Number(state.hero.stats.constitution || 10),
            int: Number(state.hero.stats.intelligence || 10),
            wis: Number(state.hero.stats.wisdom || 10),
            cha: Number(state.hero.stats.charisma || 10),
          },
        },
        classes: [{
          name: classDisplayName(cls),
          classId: cls.id,
          level: 1,
        }],
        progression: { level: 1 },
        equipment: {
          currency: { cp: 0, sp: 0, ep: 0, gp: 50, pp: 0 },
          choices: equipment,
        },
        spellbook: {
          castingMode: cls.spellcaster && cls.spellcaster !== 'none' ? String(cls.spellcaster) : 'none',
          spellcastingAbility: String(classPrimaryAbilityLabel(cls) || '').toLowerCase(),
          known: [], prepared: [], rituals: [], entries: [],
        },
      };
    }
    function rememberSelectedProfile(sessionData, profileId) {
      if (!profileId || !sessionData || !sessionData.session_id) return;
      const identitySeed = String(sessionData.user_id || sessionData.name || (state.authUser && state.authUser.username) || 'player').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_');
      const identity = identitySeed || 'player';
      const key = `tavern_char_profile_${String(sessionData.session_id).trim().toUpperCase()}_${identity}`;
      try { localStorage.setItem(key, profileId); } catch (_) {}
    }
    function saveAndEnter(sessionData) {
      localStorage.setItem('tavern_last_session', JSON.stringify({
        session_id: sessionData.session_id,
        invite_code: INVITE,
        name: sessionData.name,
        role: sessionData.role,
      }));
      const search = new URLSearchParams({
        session_id: sessionData.session_id,
        user_id: sessionData.user_id,
        role: sessionData.role,
        name: sessionData.name,
        returning: sessionData.returning ? '1' : '0',
      });
      location.href = '/play?' + search.toString();
    }
    async function handleFinish() {
      if (!canProceed()) {
        setFeedback('Finish the required choices before entering the realm.', 'error');
        return;
      }
      try {
        setFeedback('Forging hero profile…');
        const saveData = await fetchJson('/api/character/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: SESSION_ID, character_document: buildDraftDocument() }),
        });
        const profileId = String(saveData.profile_id || (saveData.profile && saveData.profile.id) || '').trim();
        setFeedback('Hero forged. Binding them to the realm…');
        const sessionData = await fetchJson('/api/session/join', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: SESSION_ID, invite_code: INVITE, claim_token: null }),
        });
        rememberSelectedProfile(sessionData, profileId);
        saveAndEnter(sessionData);
      } catch (err) {
        setFeedback(err.message || 'The forging ritual failed.', 'error');
      }
    }
    function goBack() { location.href = getRosterUrl(); }
    function renderAll() { renderSteps(); renderStepView(); }
    async function loadSessionInfo() {
      const qs = new URLSearchParams({ role: ROLE, player_key: getPlayerKey(), user_name: state.authUser ? (state.authUser.character_name || state.authUser.username || '') : '' });
      const data = await fetchJson(`/api/session/${encodeURIComponent(SESSION_ID)}/lobby?${qs.toString()}`);
      state.campaignName = data.campaign_name || 'Unknown campaign';
      els.heroCampaign.textContent = 'Realm: ' + state.campaignName;
    }
    async function loadCatalog() {
      try {
        const data = await fetchJson('/api/character/content/catalog?rules_mode=casual');
        const classes = normalizeCatalogClasses(data && data.classes);
        const species = normalizeCatalogSpecies(data && data.species);
        state.classes = classes.length ? classes : normalizeCatalogClasses(FALLBACK_CLASSES);
        state.species = species.length ? species : normalizeCatalogSpecies(FALLBACK_SPECIES);
        if (!state.hero.classId && state.classes[0]) state.hero.classId = state.classes[0].id;
        if (!state.hero.speciesId && state.species[0]) state.hero.speciesId = state.species[0].id;
        if (!state.hero.backgroundId && state.backgrounds[0]) state.hero.backgroundId = state.backgrounds[0].id;
      } catch (_) {
        state.classes = normalizeCatalogClasses(FALLBACK_CLASSES);
        state.species = normalizeCatalogSpecies(FALLBACK_SPECIES);
        if (!state.hero.classId && state.classes[0]) state.hero.classId = state.classes[0].id;
        if (!state.hero.speciesId && state.species[0]) state.hero.speciesId = state.species[0].id;
        if (!state.hero.backgroundId && state.backgrounds[0]) state.hero.backgroundId = state.backgrounds[0].id;
      }
    }
    function escapeHtml(value) {
      return String(value || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    async function init() {
      if (!SESSION_ID || !INVITE) {
        setFeedback('This creation route needs a valid player invite. Open it from a fresh realm link.', 'error');
        els.next.disabled = true;
        return;
      }
      try {
        const me = await fetch('/api/auth/me', { credentials: 'same-origin' });
        if (!me.ok) { redirectToLogin(); return; }
        const auth = await me.json();
        state.authUser = auth && auth.user ? auth.user : null;
        if (!state.authUser) { redirectToLogin(); return; }
        els.backLink.href = getRosterUrl();
        await Promise.all([loadCatalog(), loadSessionInfo()]);
        renderAll();
        setFeedback('Importer-style hero forge ready. This version uses the new visual species and class flow before entering play.', 'success');
      } catch (err) {
        setFeedback(err.message || 'Could not prepare the hero forge.', 'error');
      }
    }
    els.cancel.addEventListener('click', goBack);
    els.back.addEventListener('click', () => { if (state.step === 0) goBack(); else { state.step = Math.max(0, state.step - 1); renderAll(); } });
    els.next.addEventListener('click', () => {
      if (state.step === STEPS.length - 1) { handleFinish(); return; }
      if (!canProceed()) { setFeedback('Complete this step before moving on.', 'error'); return; }
      state.step = Math.min(STEPS.length - 1, state.step + 1);
      renderAll();
    });
    init();
  