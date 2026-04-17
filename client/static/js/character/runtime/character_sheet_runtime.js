(function (global) {
  'use strict';

const KNOWN_RENDER_CHAR_SHEET_CALLERS = new Set([
  'openMyTokenStats',
  'placeCharacter',
  'syncCharacterBookInputs',
  'openCharacterBook',
  'autoFillCharacterBookFromPaste',
  'loadCharacterFromJson',
  'importCharacterBookFromUpload',
  'adjustHp',
  'toggleSpellSlot',
  'updateMyChar',
  'applyCharProfileRecord',
  'legacy-renderCharSheet-shim',
]);

function requestCharacterBookOverviewRender(source = 'unknown') {
  renderCharacterBookOverviewContent();
}


function _prettySheetLabel(raw) {
  return String(raw || '')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b([a-z])/g, function (_, ch) { return ch.toUpperCase(); });
}

function _formatGoldUnits(units) {
  const totalCp = Math.max(0, Math.round(Number(units || 0)));
  const gp = Math.floor(totalCp / 100);
  const sp = Math.floor((totalCp % 100) / 10);
  const cp = totalCp % 10;
  if (gp > 0) return `${gp} gp${sp > 0 ? ` ${sp} sp` : ''}${cp > 0 ? ` ${cp} cp` : ''}`;
  if (sp > 0) return `${sp} sp${cp > 0 ? ` ${cp} cp` : ''}`;
  return `${cp} cp`;
}

function renderCharSheet() {
  requestCharacterBookOverviewRender('legacy-renderCharSheet-shim');
}

function renderCharacterBookOverviewContent() {
  const c = ensureCharSheetRuntimeDefaults(_charSheet);
  if (!c) return;

  document.getElementById('sheet-char-name').textContent = c.name || 'Adventurer';
  const speciesLine = _prettySheetLabel(c.species || c.race || '');
  const backgroundLine = _prettySheetLabel(c.background || c.book?.background || '');
  document.getElementById('sheet-char-sub').textContent = [speciesLine, backgroundLine].filter(Boolean).join(' · ') || 'Character details';

  const body = document.getElementById('sheet-body');
  if (!body) return;
  body.innerHTML = '';
  const book = (c && typeof c.book === 'object' && c.book) ? c.book : {};
  const levelValue = parseInt(c.totalLevel || c.level || book.level, 10) || 1;
  const heroClass = ((Array.isArray(c.classes) ? c.classes : []).map(cl => cl?.name).filter(Boolean).join(' / ') || book.className || 'Adventurer');
  const heroSubclass = ((Array.isArray(c.classes) ? c.classes : []).map(cl => cl?.subclass).filter(Boolean).join(' / ') || book.subclass || '');
  const heroRace = c.species || c.race || book.species || book.race || '';
  const heroBackground = c.background || book.background || '';
  const heroSize = c.size || c.speciesGameplay?.size || 'Medium';
  const heroSenses = String(c.senses || book.senses || (Array.isArray(c.speciesGameplay?.senses) ? c.speciesGameplay.senses.join(', ') : '') || '').trim();
  const heroResistances = String(c.resistances || book.resistances || (Array.isArray(c.speciesGameplay?.resistances) ? c.speciesGameplay.resistances.join(', ') : '') || '').trim();
  const heroDarkvision = parseInt(c.darkvisionRadius ?? c.speciesGameplay?.darkvision_radius ?? 0, 10) || 0;
  const heroPortrait = c.avatarUrl || book.avatarUrl || '';
  const passivePerception = parseInt(c.passivePerception ?? book.passivePerception, 10);
  const profBonus = parseInt(c.profBonus ?? book.profBonus, 10);
  const speedValue = parseInt(c.speed, 10) || 0;
  const spellSaveDc = String(c.spellSaveDc ?? book.spellSaveDc ?? '').trim();
  const spellAttack = String(c.spellAttack ?? book.spellAttack ?? '').trim();
  const inspiration = String(c.inspiration ?? book.inspiration ?? '').trim();
  const accentColor = _coerceHexColor(c.accentColor || document.getElementById('char-accent-color')?.value || '#00e5cc', '#00e5cc');
  const tagline = String(c.tagline || document.getElementById('char-tagline')?.value || '').trim();
  const portraitFrame = String(c.portraitFrame || document.getElementById('char-portrait-frame')?.value || 'classic').trim() || 'classic';
  const frameStyle = PLAYER_PORTRAIT_FRAMES[portraitFrame] || PLAYER_PORTRAIT_FRAMES.classic;
  applyCharacterSheetTheme(c);

  // ── HP Section ──
  const combatSnapshot = _getSheetCombatSnapshot(c);
  const safeMaxHp = combatSnapshot.maxHp;
  const safeCurrentHp = combatSnapshot.currentHp;
  const safeTempHp = combatSnapshot.tempHp;
  const hpPct = safeMaxHp > 0 ? Math.max(0, Math.min(100, (safeCurrentHp / safeMaxHp) * 100)) : 0;
  const hpColor = hpPct > 50 ? '#2ecc71' : hpPct > 25 ? '#e67e22' : '#e74c3c';
  const trackedFeatures = _getStructuredClassFeatures().filter(f => f.trackUses);
  const classFeature = _getSheetPrimaryClassResource(trackedFeatures);
  const classState = classFeature ? _getClassFeatureResourceState(classFeature) : null;
  const classFeatureRows = trackedFeatures.map((feature) => {
    const state = _getClassFeatureResourceState(feature);
    return state ? { feature, state } : null;
  }).filter(Boolean);
  const secondaryResourceRows = classFeatureRows
    .filter(row => row && row.feature?.key !== classFeature?.key)
    .slice(0, 3);
  const inventoryRows = _sheetInventorySummaryRows(c);
  const actionSections = _getPlayerActionsSections();
  const spotlightAttacks = (actionSections.Attacks || []).slice(0, 4);
  const spotlightBonus = (actionSections['Bonus Actions'] || []).slice(0, 3);
  const spotlightReactions = (actionSections.Reactions || []).slice(0, 3);
  const rawSpellSpotlightCards = (typeof _getStructuredRulesSpellbookCards === 'function' ? _getStructuredRulesSpellbookCards() : []);
  const spellUsage = (_charSheet && typeof _charSheet.spellUsageCounts === 'object' && _charSheet.spellUsageCounts) ? _charSheet.spellUsageCounts : {};
  const prettySpellName = function (raw) { return String(raw || '').replace(/^spell[_-]+/i, '').replace(/[_-]+/g, ' ').replace(/\b([a-z])/g, function (_, ch) { return ch.toUpperCase(); }).trim(); };
  const selectedSpellNames = (typeof _currentSpellSelectionNames === 'function') ? _currentSpellSelectionNames(c) : [];
  const readySpellCards = (typeof _getCombatQuickSpells === 'function' ? _getCombatQuickSpells() : []).map(function (entry, idx) {
    const card = entry && entry.card ? entry.card : {};
    const prettyName = prettySpellName(entry && (entry.name || entry.id) || card.name || 'Spell');
    const level = Number(entry && entry.level != null ? entry.level : (card.spell_level != null ? card.spell_level : (card.level != null ? card.level : 0))) || 0;
    return Object.assign({
      id: String(entry && (entry.id || prettyName || ('quick-spell-' + idx)) || ('quick-spell-' + idx)),
      name: prettyName,
      displayName: prettyName,
      spell_level: level,
      level: level,
      concentration: !!(card.concentration || card.is_concentration),
      is_concentration: !!(card.concentration || card.is_concentration),
      base_effect_text: card.base_effect_text || card.effect || card.current?.effect || '',
      current: card.current || { effect: card.base_effect_text || card.effect || '', formula: card.damage_dice || card.damage || card.damage_formula || card.base_damage_formula || '' },
      level_school: card.level_school || card.school || (level === 0 ? 'Cantrip' : ''),
      range: entry && entry.range || card.range || '',
      source: entry && entry.source || 'spell',
      card: card
    }, card || {});
  });
  const spellSpotlightSource = readySpellCards.length ? readySpellCards : rawSpellSpotlightCards;
  const spellSpotlightCards = spellSpotlightSource.slice().sort(function (a, b) {
    const aCount = parseInt(spellUsage[String(a && (a.id || a.name) || '').toLowerCase()] || 0, 10) || 0;
    const bCount = parseInt(spellUsage[String(b && (b.id || b.name) || '').toLowerCase()] || 0, 10) || 0;
    if (bCount !== aCount) return bCount - aCount;
    return (parseInt(a && (a.spell_level || a.level || 0), 10) || 0) - (parseInt(b && (b.spell_level || b.level || 0), 10) || 0);
  }).slice(0, 4);
  const liveCurrency = (typeof _getLivePlayerGoldValue === 'function' && _getLivePlayerGoldValue() > 0) ? _getLivePlayerGoldValue() : null;
  const inventoryHost = document.getElementById('sheet-inventory-summary');
  if (inventoryHost) {
    inventoryHost.innerHTML = inventoryRows.length
      ? inventoryRows.map(row => `<div class="sheet-inventory-row"><span>${escapeHtml(row.name)} ×${row.qty}</span><span style="color:var(--parchment-dim);">${escapeHtml(row.note || '—')}</span></div>`).join('')
      : '<div class="sheet-note">No synced inventory entries yet.</div>';
  }

  const quickAttackCards = (typeof _getUnifiedQuickAttackCards === 'function') ? _getUnifiedQuickAttackCards() : [];
  const rulesSpellCards = readySpellCards.length ? readySpellCards : ((typeof _getStructuredRulesSpellbookCards === 'function') ? _getStructuredRulesSpellbookCards() : []);
  const syncedSpellCount = Math.max(rulesSpellCards.length, selectedSpellNames.length);
  const nativeActionGroups = (typeof _getNativeCharacterBookActionCards === 'function') ? _getNativeCharacterBookActionCards() : { actions: [], bonusActions: [], reactions: [] };
  const nativeActionCards = []
    .concat(Array.isArray(nativeActionGroups?.actions) ? nativeActionGroups.actions : [])
    .concat(Array.isArray(nativeActionGroups?.bonusActions) ? nativeActionGroups.bonusActions : [])
    .concat(Array.isArray(nativeActionGroups?.reactions) ? nativeActionGroups.reactions : []);
  const nativeResourceCards = (typeof _getNativeCharacterBookResources === 'function') ? _getNativeCharacterBookResources() : [];
  const nativeFeatureCards = (typeof _getNativeCharacterBookFeatures === 'function') ? _getNativeCharacterBookFeatures() : [];
  const selectedTarget = (typeof _nativeActionSelectedTarget === 'function') ? _nativeActionSelectedTarget() : null;
  const activeConcentration = (typeof _getActiveConcentrationSpellName === 'function') ? _getActiveConcentrationSpellName() : '';
  body.innerHTML += `
    <div class="sheet-combat-strip">
      <div class="sheet-hp-hero">
        <div class="sheet-inline-title">Play State</div>
        <div class="hp-bar-wrap"><div class="hp-bar-fill" style="width:${Math.round(hpPct)}%;background:${hpColor};"></div></div>
        <div class="hp-numbers"><span class="hp-current">${safeCurrentHp}</span><span class="hp-sep">/</span><span class="hp-max">${safeMaxHp}</span><span class="sheet-combat-chip"><strong>Temp ${safeTempHp}</strong></span></div>
        <div class="sheet-combat-chip-row">
          <span class="sheet-combat-chip"><strong>AC ${combatSnapshot.ac}</strong></span>
          <span class="sheet-combat-chip"><strong>SPD ${combatSnapshot.speed || '—'} ft</strong></span>
          <span class="sheet-combat-chip"><strong>Init ${Number.isFinite(combatSnapshot.initiative) ? formatSignedSummaryValue(combatSnapshot.initiative) : '—'}</strong></span>
          ${spellSaveDc ? `<span class="sheet-combat-chip"><strong>DC ${escapeHtml(spellSaveDc)}</strong></span>` : ''}
          ${spellAttack ? `<span class="sheet-combat-chip"><strong>Atk ${escapeHtml(spellAttack)}</strong></span>` : ''}
          <span class="sheet-combat-chip"><strong>PB ${Number.isFinite(combatSnapshot.profBonus) ? formatSignedSummaryValue(combatSnapshot.profBonus) : '—'}</strong></span>
          <span class="sheet-combat-chip"><strong>Passive ${Number.isFinite(combatSnapshot.passivePerception) ? combatSnapshot.passivePerception : '—'}</strong></span>
          ${combatSnapshot.isCombatActive ? `<span class="sheet-combat-chip"><strong>${combatSnapshot.isMyTurn ? 'Your Turn' : 'Combat Active'}</strong></span>` : ''}
          ${combatSnapshot.concentration ? `<span class="sheet-combat-chip"><strong>⟳ Concentrating</strong></span>` : ''}
          ${combatSnapshot.conditionList.filter(id => String(id).toLowerCase() !== 'concentrating').slice(0, 4).map(id => `<span class="sheet-combat-chip">${escapeHtml(CONDITIONS_MAP[id]?.name || id)}</span>`).join('')}
        </div>
      </div>
      <div class="sheet-class-resource-hero">
        <div class="sheet-class-resource-title">Class Resource</div>
        <div class="sheet-class-resource-main">${escapeHtml(classFeature?.name || 'Class Feature')}</div>
        <div class="sheet-note" style="margin-top:0.2rem;">${classState ? `Uses ${escapeHtml(classState.summary)}` : 'No tracked uses found in current book text.'}</div>
        ${secondaryResourceRows.length ? `<div class="sheet-combat-chip-row">${secondaryResourceRows.map(row => `<span class="sheet-combat-chip"><strong>${escapeHtml(row.feature.name || 'Feature')}</strong> ${escapeHtml(row.state.summary)}</span>`).join('')}</div>` : ''}
        <div class="sheet-combat-chip-row">
          ${classFeature?.key ? `<button class="sheet-quick-btn" type="button" onclick="adjustClassFeatureUse('${escapeHtml(classFeature.key)}', 1)">Use</button><button class="sheet-quick-btn" type="button" onclick="adjustClassFeatureUse('${escapeHtml(classFeature.key)}', -1)">Restore</button>` : '<span class="sheet-note">Add usage text like “Wild Shape 1/2”.</span>'}
        </div>
      </div>
    </div>
    <div class="sheet-quick-actions">
      <div class="sheet-inline-title">Quick Actions</div>
      <input id="sheet-hp-delta" class="sheet-book-input mono" type="number" min="1" max="999" value="5" style="max-width:92px;margin-bottom:0.35rem;" />
      <div class="sheet-quick-actions-grid">
        <button class="sheet-quick-btn primary" type="button" onclick="runSheetQuickAction('initiative')">Roll Initiative</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('class')">Class Action</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('cast')">Cast Spell</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('damage')">Damage</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('heal')">Heal</button>
        <button class="sheet-quick-btn" type="button" onclick="runSheetQuickAction('rest')">Rest</button>
      </div>
    </div>
    <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
      <div class="sheet-inline-title">Attack Spotlight</div>
      <div class="sheet-inline-list">
        ${spotlightAttacks.map(action => `<div class="sheet-inline-row"><div class="sheet-inline-row-top"><strong>${escapeHtml(action.name || 'Attack')}</strong><div class="sheet-inline-tags">${(action.badges || []).slice(0,2).map(tag => `<span class="sheet-inline-tag">${escapeHtml(String(tag))}</span>`).join('')}</div></div><div class="sheet-note">${escapeHtml(action.desc || action.resource || 'Attack roll')}</div><div class="sheet-combat-chip-row" style="margin-top:0.35rem;"><button class="sheet-quick-btn" type="button" onclick="playerUseAction('${escapeHtml(action.source || 'weapon')}', '${escapeHtml(action.id || '')}')">Roll</button><button class="sheet-quick-btn" type="button" onclick="playerInspectAction('${escapeHtml(action.source || 'weapon')}', '${escapeHtml(action.id || '')}')">Info</button></div></div>`).join('') || '<div class="sheet-note">Equip a weapon or add an attack entry to populate this section.</div>'}
      </div>
    </div>
    <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
      <div class="sheet-inline-title">Bonus Actions & Reactions</div>
      <div class="sheet-inline-list">
        ${spotlightBonus.concat(spotlightReactions).map(action => `<div class="sheet-inline-row"><div class="sheet-inline-row-top"><strong>${escapeHtml(action.name || 'Action')}</strong><div class="sheet-inline-tags">${(action.badges || []).slice(0,2).map(tag => `<span class="sheet-inline-tag">${escapeHtml(String(tag))}</span>`).join('')}</div></div><div class="sheet-note">${escapeHtml(action.resource || action.desc || 'Quick-turn option')}</div><div class="sheet-combat-chip-row" style="margin-top:0.35rem;"><button class="sheet-quick-btn" type="button" onclick="playerUseAction('${escapeHtml(action.source || 'native_action')}', '${escapeHtml(action.id || '')}')">Use</button><button class="sheet-quick-btn" type="button" onclick="playerInspectAction('${escapeHtml(action.source || 'native_action')}', '${escapeHtml(action.id || '')}')">Info</button></div></div>`).join('') || '<div class="sheet-note">Native bonus actions and reactions will appear here once the class runtime is mapped.</div>'}
      </div>
    </div>
    <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
      <div class="sheet-inline-title">Spell Spotlight</div>
      <div class="sheet-inline-list">
        ${spellSpotlightCards.map(card => `<div class="sheet-inline-row"><div class="sheet-inline-row-top"><strong>${escapeHtml(prettySpellName(card.name || card.displayName || 'Spell'))}</strong><div class="sheet-inline-tags"><span class="sheet-inline-tag">${escapeHtml((card.spell_level || card.level || 0) === 0 ? 'Cantrip' : `Lv ${(card.spell_level || card.level || 0)}`)}</span>${card.concentration || card.is_concentration ? '<span class="sheet-inline-tag">Concentration</span>' : ''}</div></div><div class="sheet-note">${escapeHtml(card.base_effect_text || card.current?.effect || card.level_school || 'Quick cast-ready spell card.')}</div><div class="sheet-combat-chip-row" style="margin-top:0.35rem;"><button class="sheet-quick-btn" type="button" onclick="castRulesSpell('${escapeHtml(card.id || card.name || '')}')">Cast</button><button class="sheet-quick-btn" type="button" onclick="playerInspectSpell('${escapeHtml(card.id || card.name || '')}')">Info</button></div></div>`).join('') || '<div class="sheet-note">Link spell cards or learn spells in the Magic tab to surface quick-cast spell cards here.</div>'}
      </div>
    </div>
    <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
      <div class="sheet-inline-title">Loadout Snapshot</div>
      <div class="sheet-note" style="margin-bottom:0.4rem;">${liveCurrency != null ? `Gold on hand: ${escapeHtml(_formatGoldUnits(liveCurrency))}` : 'Open Inventory for the full bag. This strip shows the live synced loadout first.'}</div>
      <div class="sheet-inline-list">
        ${inventoryRows.slice(0, 6).map(row => `<div class="sheet-inline-row"><div class="sheet-inline-row-top"><strong>${escapeHtml(row.name || 'Item')}</strong><div class="sheet-inline-tags"><span class="sheet-inline-tag">×${escapeHtml(String(row.qty || 1))}</span></div></div><div class="sheet-note">${escapeHtml(row.note || 'Loadout item')}</div></div>`).join('') || '<div class="sheet-note">No synced inventory items yet.</div>'}
      </div>
    </div>
    <div class="sheet-overview-hero">
      <div class="sheet-overview-portrait" style="border:${escapeHtml(frameStyle.border)};border-radius:${escapeHtml(frameStyle.radius)};box-shadow:${escapeHtml(frameStyle.shadow)};">${heroPortrait ? `<img src="${escapeHtml(heroPortrait)}" alt="Portrait of ${escapeHtml(c.name || 'Adventurer')}" loading="lazy">` : `<span>${escapeHtml(String(c.name || 'A').slice(0, 1).toUpperCase())}</span>`}</div>
      <div class="sheet-overview-meta">
        <div class="sheet-overview-name">${escapeHtml(c.name || 'Adventurer')}</div>
        <div class="sheet-overview-subline">${escapeHtml(_prettySheetLabel(heroClass))}${heroSubclass ? ` · ${escapeHtml(_prettySheetLabel(heroSubclass))}` : ''}</div>
        ${tagline ? `<div class="sheet-overview-subline" style="font-style:italic;color:var(--sheet-accent, var(--gold));">“${escapeHtml(tagline)}”</div>` : ''}
        <div class="sheet-overview-tags">
          <span class="sheet-overview-tag">Level ${levelValue}</span>
          ${heroRace ? `<span class="sheet-overview-tag">${escapeHtml(heroRace)}</span>` : ''}
          ${heroSize ? `<span class="sheet-overview-tag">${escapeHtml(heroSize)}</span>` : ''}
          ${heroBackground ? `<span class="sheet-overview-tag">${escapeHtml(heroBackground)}</span>` : ''}
        </div>
      </div>
    </div>`;
  body.innerHTML += `
    <div class="sheet-glance-grid">
      <div class="sheet-glance-tile primary"><div class="sheet-glance-label">Armor Class</div><div class="sheet-glance-value">${parseInt(c.ac, 10) || 0}</div><div class="sheet-glance-sub">Defense</div></div>
      <div class="sheet-glance-tile primary"><div class="sheet-glance-label">Current HP</div><div class="sheet-glance-value">${safeCurrentHp}</div><div class="sheet-glance-sub">of ${safeMaxHp}</div></div>
      <div class="sheet-glance-tile"><div class="sheet-glance-label">Temp HP</div><div class="sheet-glance-value">${safeTempHp}</div><div class="sheet-glance-sub">buffer</div></div>
      <div class="sheet-glance-tile"><div class="sheet-glance-label">Speed</div><div class="sheet-glance-value">${speedValue || '—'}</div><div class="sheet-glance-sub">${speedValue ? 'ft' : 'not set'}</div></div>
    </div>`;
  body.innerHTML += `
    <div class="sheet-resource-grid">
      <div class="sheet-resource-item"><label>Proficiency</label><strong>${Number.isFinite(profBonus) ? formatSignedSummaryValue(profBonus) : '—'}</strong></div>
      <div class="sheet-resource-item"><label>Passive Perception</label><strong>${Number.isFinite(passivePerception) && passivePerception > 0 ? passivePerception : '—'}</strong></div>
      ${heroDarkvision > 0 ? `<div class="sheet-resource-item"><label>Darkvision</label><strong>${heroDarkvision} ft</strong></div>` : ''}
      ${spellSaveDc ? `<div class="sheet-resource-item"><label>Spell Save DC</label><strong>${escapeHtml(spellSaveDc)}</strong></div>` : ''}
      ${spellAttack ? `<div class="sheet-resource-item"><label>Spell Attack</label><strong>${escapeHtml(spellAttack)}</strong></div>` : ''}
      ${inspiration ? `<div class="sheet-resource-item"><label>Inspiration</label><strong>${escapeHtml(inspiration)}</strong></div>` : ''}
    </div>`;
  body.innerHTML += `
    <div class="sheet-resource-grid">
      <div class="sheet-resource-item"><label>Senses</label><strong>${escapeHtml(heroSenses || '—')}</strong></div>
      <div class="sheet-resource-item"><label>Resistances</label><strong>${escapeHtml(heroResistances || '—')}</strong></div>
    </div>`;

  // ── Class Features List ──
  const allClassFeatures = typeof _getStructuredClassFeatures === 'function' ? _getStructuredClassFeatures() : [];
  if (allClassFeatures.length) {
    const featuresBySection = {};
    allClassFeatures.forEach(f => {
      const sec = f.section || 'Class Features';
      if (!featuresBySection[sec]) featuresBySection[sec] = [];
      featuresBySection[sec].push(f);
    });
    const sectionOrder = ['Class Features', 'Actions', 'Bonus Actions', 'Reactions'];
    const otherSections = Object.keys(featuresBySection).filter(s => !sectionOrder.includes(s));
    const allSections = [...sectionOrder, ...otherSections].filter(s => featuresBySection[s]);
    const featureHtml = allSections.map(sec => {
      const items = featuresBySection[sec];
      return `<div style="margin-bottom:0.6rem;">
        <div class="sheet-inline-title" style="margin-bottom:0.3rem;">${escapeHtml(sec)}</div>
        <div style="display:flex;flex-wrap:wrap;gap:0.3rem;">
          ${items.map(f => {
            const tagParts = [];
            if (f.className) tagParts.push(f.className);
            if (f.subclass) tagParts.push(`(${f.subclass})`);
            if (f.minLevel > 1) tagParts.push(`Lv.${f.minLevel}`);
            const tags = tagParts.join(' ');
            return `<span class="sheet-combat-chip" style="cursor:default;" title="${escapeHtml(tags)}">${escapeHtml(f.name)}</span>`;
          }).join('')}
        </div>
      </div>`;
    }).join('');
    body.innerHTML += `
      <div class="sheet-inline-section" style="margin-bottom:0.7rem;">
        <div class="sheet-inline-title">Class Abilities at Level ${levelValue}</div>
        <div style="font-size:0.68rem;color:var(--parchment-dim);margin-bottom:0.55rem;">Features unlocked for your class and subclass up to your current level.</div>
        ${featureHtml}
      </div>`;
  }
}


  global.AppCharacterSheetRuntime = {
    requestCharacterBookOverviewRender,
    renderCharSheet,
    renderCharacterBookOverviewContent,
  };
})(window);
