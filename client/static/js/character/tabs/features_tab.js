/*
 * client/static/js/character/tabs/features_tab.js
 * Features & Traits Tab — Player-facing readable feature cards and notes.
 *
 * Exposes: window.FeaturesTab
 *   .initFeaturesTab(container, charData)
 */

(function initFeaturesTabModule(global) {
  'use strict';

  function _esc(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch])
    );
  }

  function _safeArray(value) {
    return Array.isArray(value) ? value.filter(Boolean) : [];
  }

  function _firstText() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = arguments[i];
      if (value == null) continue;
      const text = String(value).trim();
      if (text) return text;
    }
    return '';
  }

  function _descHtml(text) {
    if (!text) return '<em>No description available.</em>';
    return String(text)
      .split(/\n{2,}/)
      .map(p => `<p>${_esc(p.trim()).replace(/\n/g, '<br>')}</p>`)
      .join('');
  }

  function _previewText(text, limit = 180) {
    const raw = String(text || '').replace(/\s+/g, ' ').trim();
    if (!raw) return '';
    return raw.length > limit ? raw.slice(0, limit - 3) + '…' : raw;
  }

  function _cleanPlayerFacingText(text) {
    const raw = String(text || '').replace(/\r/g, '').trim();
    if (!raw) return '';
    const blocked = [
      /the sheet should/i,
      /usually watch/i,
      /start here/i,
      /best time to use it/i,
      /important thing is/i,
      /hidden unlock/i,
      /this should make/i,
      /it matters because/i,
      /treat this like/i,
      /the player should/i,
      /practical effect/i,
      /this shines most when/i,
      /in-app job/i,
      /feature should feel/i,
      /the subclass should/i,
      /the class should/i,
      /the sheet should make/i,
      /the sheet should/i,
    ];
    const paragraphs = raw.split(/\n{2,}/).map(function (part) { return String(part || '').trim(); }).filter(Boolean);
    const kept = paragraphs.filter(function (part) {
      return !blocked.some(function (pattern) { return pattern.test(part); });
    });
    return (kept.length ? kept : paragraphs.slice(0, 1)).join('\n\n').replace(/\s+([.,;:!?])/g, '$1').trim();
  }

  function _trimRepeatedLead(summary, description) {
    const cleanSummary = String(summary || '').replace(/\s+/g, ' ').trim();
    const cleanDescription = String(description || '').trim();
    if (!cleanSummary || !cleanDescription) return cleanDescription;
    const loweredSummary = cleanSummary.toLowerCase();
    const loweredDescription = cleanDescription.replace(/\s+/g, ' ').trim().toLowerCase();
    if (loweredDescription === loweredSummary) return '';
    if (loweredDescription.startsWith(loweredSummary)) {
      return cleanDescription.slice(cleanSummary.length).replace(/^\s*[.\-–—:]?\s*/, '').trim();
    }
    return cleanDescription;
  }

  function _firstSentence(text) {
    const raw = String(text || '').replace(/\s+/g, ' ').trim();
    if (!raw) return '';
    const match = raw.match(/^[^.!?]+[.!?]?/);
    return (match ? match[0] : raw).trim();
  }

  function _cleanFeatureSummary(feature) {
    const base = _firstText(
      _cleanPlayerFacingText(feature && feature.summary),
      _cleanPlayerFacingText(feature && feature.effect),
      _firstSentence(_cleanPlayerFacingText(feature && feature.description)),
      _previewText(_cleanPlayerFacingText(feature && feature.description), 180)
    );
    return base || 'Open to read the full feature details.';
  }

  function _featureTagPills(feature) {
    const tags = [];
    if (feature && feature.actionType) tags.push(feature.actionType);
    if (feature && feature.resourceName) tags.push(feature.resourceName);
    if (feature && feature.usage) tags.push(feature.usage);
    else if (feature && feature.recovery) tags.push(feature.recovery);
    if (feature && feature.isSubclass) tags.push('Subclass');
    return tags.slice(0, 3);
  }

  function _featureSourceLine(feature) {
    return [feature && (feature.source || feature.className), feature && feature.level ? 'Level ' + feature.level : ''].filter(Boolean).join(' • ');
  }

  function _featureTypeKey(feature) {
    const kind = String(feature && feature.kind || '').toLowerCase();
    if (kind === 'native') return 'native';
    if (kind === 'class') return 'class';
    if (kind === 'trait' || kind === 'origin') return 'traits';
    if (kind === 'feat') return 'feats';
    return 'all';
  }

  function _coerceFeature(entry, defaults = {}) {
    if (!entry) return null;
    if (typeof entry === 'string') {
      return {
        name: entry,
        description: defaults.description || '',
        level: defaults.level || 0,
        source: defaults.source || '',
        kind: defaults.kind || '',
        isSubclass: !!defaults.isSubclass,
      };
    }
    const obj = typeof entry === 'object' ? entry : { name: String(entry) };
    const mechanics = obj.mechanics && typeof obj.mechanics === 'object' ? obj.mechanics : {};
    return {
      name: _firstText(obj.name, obj.title, obj.label, defaults.name, 'Feature'),
      summary: _cleanPlayerFacingText(_firstText(obj.summary, obj.effect, obj.note, defaults.summary)),
      description: _cleanPlayerFacingText(_firstText(obj.description, obj.desc, obj.text, obj.summary, obj.note, defaults.description)),
      level: obj.level || obj.minLevel || defaults.level || 0,
      source: _firstText(obj.source, obj.className, obj.origin, defaults.source),
      section: _firstText(obj.section, defaults.section),
      kind: _firstText(obj.kind, obj.type, defaults.kind),
      resourceName: _firstText(obj.resourceName, obj.resource, defaults.resourceName),
      actionType: _firstText(obj.type, obj.actionType, mechanics.actionType, defaults.actionType),
      range: _firstText(obj.range, mechanics.range, defaults.range),
      duration: _firstText(obj.duration, defaults.duration),
      save: _firstText(obj.save, mechanics.saveDC, defaults.save),
      trigger: _firstText(obj.trigger, defaults.trigger),
      usage: _firstText(obj.usage, mechanics.usesPerRest, defaults.usage),
      recovery: _firstText(obj.recovery, defaults.recovery),
      effect: _firstText(obj.effect, mechanics.damageFormula, defaults.effect),
      className: _firstText(obj.className, defaults.className),
      subclassName: _firstText(obj.subclassName, defaults.subclassName),
      isSubclass: !!(obj.isSubclass || defaults.isSubclass),
      tags: _safeArray(obj.tags || defaults.tags),
      raw: obj,
    };
  }

  function _dedupeFeatures(items) {
    const seen = new Set();
    return _safeArray(items).filter(function (item) {
      if (!item || !item.name) return false;
      const key = [String(item.name).toLowerCase(), item.level || 0, String(item.source || '').toLowerCase()].join('::');
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function _summaryCard(label, value, note) {
    return `<div class="cs-traits-summary-card">
      <div class="cs-traits-summary-label">${_esc(label)}</div>
      <div class="cs-traits-summary-value">${_esc(String(value))}</div>
      <div class="cs-traits-summary-note">${_esc(note || '')}</div>
    </div>`;
  }




  const CUSTOM_CLASS_GUIDES = {
    tinker: {
      title: 'Tinker Surface Guide',
      summary: 'Tinker should read like an engineer with a live field kit: gadgets, prepared formulae, rig upgrades, and fast battlefield problem-solving.',
      pillars: ['Prototype Rig', 'Gadget Charges', 'Specialty Spells', 'Deployables / countermeasures'],
      loop: 'Check Gadget Charges first, then any rig or deployment features, then confirm your prepared formulae and subclass devices line up with what you expect to use on the map.',
      next: ['Open Features & Traits for rig and infusion details', 'Open Actions for deployment / countermeasure cards', 'Open Spells to confirm specialty formulae and subclass grants'],
    },
    pirate: {
      title: 'Pirate Surface Guide',
      summary: 'Pirate should read like a mobile duelist-controller: swagger resources, dirty tricks, pressure, and momentum on the battlefield.',
      pillars: ['Swagger Dice', 'Dirty Fighting', 'Boarding pressure', 'Marked target play'],
      loop: 'Check Swagger Dice first, then your bonus-action pressure tools, then make sure your attack cards and subclass tricks are all visible from the combat surface.',
      next: ['Open Features & Traits for trick wording and subclass identity', 'Open Actions for swagger-fueled tricks and movement tools', 'Use equipped attacks and watch how your target pressure features connect'],
    },
  };

  const CLASS_PLAYBOOKS = {
    barbarian: {
      role: 'Front-line bruiser',
      loop: 'Open with Rage, pressure targets with weapon attacks, and verify that resistances and reckless choices feel worth the trade-off.',
      testOrder: ['Rage spend / recovery', 'Attack accuracy and damage', 'Reckless / defense trade-off'],
      verify: ['Rage uses', 'Rest recovery', 'Attack cards', 'Target damage'],
    },
    bard: {
      role: 'Support caster',
      loop: 'Use Bardic Inspiration and support spells first, then check that spell cards, save DCs, and resource spend all match the sheet.',
      testOrder: ['Bardic Inspiration spend', 'Spell cast / slot spend', 'Concentration swaps'],
      verify: ['Bardic Inspiration', 'Spell slots', 'Spell details', 'Action economy'],
    },
    cleric: {
      role: 'Divine caster',
      loop: 'Pressure the spell layer first, then validate Channel Divinity and any domain-flavored actions or passives the sheet is surfacing.',
      testOrder: ['Spell save DC', 'Channel Divinity', 'Prepared spell list'],
      verify: ['Channel Divinity', 'Spell slots', 'Save cards', 'Healing / damage output'],
    },
    druid: {
      role: 'Adaptive controller',
      loop: 'Test druid as a cast-vs-shift loop: verify prepared Wisdom casting, Wild Shape resource flow, and circle identity tools without losing track of either lane.',
      testOrder: ['Prepared spells and cantrip/slot progression', 'Wild Shape uses + form CR limits + Wild Companion option', 'Circle lane checks (Moon combat shifting or Land recovery/circle spells)'],
      verify: ['Wild Shape', 'Prepared formula', 'Spell slots', 'Circle feature actions'],
    },
    fighter: {
      role: 'Weapon specialist',
      loop: 'Work through equipped attacks first, then confirm Action Surge, mastery notes, and any once-per-rest combat buttons.',
      testOrder: ['Equipped attacks', 'Action Surge', 'Second Wind'],
      verify: ['Attack cards', 'Action Surge', 'Second Wind', 'Weapon rules'],
    },
    monk: {
      role: 'Mobile striker',
      loop: 'Validate Focus Point spend, martial attacks, and movement/action economy together so the Monk core loop remains clear in play.',
      testOrder: ['Focus resource', 'Attack / damage buttons', 'Bonus action techniques'],
      verify: ['Focus Points', 'Martial Arts', 'Bonus actions', 'Target application'],
    },
    paladin: {
      role: 'Burst defender',
      loop: 'Start with weapon attacks, then confirm Divine Smite timing, Lay on Hands, Channel Divinity options, and aura positioning cues.',
      testOrder: ['Attack cards + smite hook', 'Lay on Hands + Channel Divinity', 'Spell slot / aura surface'],
      verify: ['Lay on Hands', 'Channel Divinity', 'Spell slots', 'Aura-facing notes'],
    },
    ranger: {
      role: 'Hunter / skirmisher',
      loop: 'Audit ranger as a blended loop: martial attack cadence, Hunter’s Mark pressure, half-caster slots/known spells, and mobility/scouting identity should all connect.',
      testOrder: ['Equipped attacks + Extra Attack cadence', "Hunter\'s Mark + slot/concentration lane", 'Subclass tactics / companion or opener flow'],
      verify: ['Half-caster slot and known-spell clarity', 'Weapon mastery + fighting style visibility', 'Mobility/scout features', 'Subclass timing tools'],
    },
    rogue: {
      role: 'Precision striker',
      loop: 'Attack flow matters most here: make sure Sneak Attack-facing cards, bonus actions, and target application all feel connected.',
      testOrder: ['Attack cards', 'Sneak Attack conditions', 'Bonus action mobility'],
      verify: ['Sneak Attack', 'Cunning Action', 'Targeting', 'Damage spikes'],
    },
    sorcerer: {
      role: 'Flexible caster',
      loop: 'Audit sorcerer as a known-spell + Sorcery Point loop: spells known and slot tiers first, then Flexible Casting and Metamagic spenders, then origin-specific tools.',
      testOrder: ['Known/cantrip limits', 'Sorcery Point spend and recovery', 'Metamagic + origin feature actions'],
      verify: ['Sorcery Points', 'Flexible Casting', 'Metamagic options', 'Origin features'],
    },
    warlock: {
      role: 'Pact caster',
      loop: 'Audit the pact magic surface carefully: the sheet should make limited slots and invocation flavor obvious, not hide them in notes.',
      testOrder: ['Pact spell cards', 'Short-rest slot logic', 'Invocation-facing features'],
      verify: ['Pact slots', 'Spell cards', 'Short rest logic', 'Class feature detail'],
    },
    wizard: {
      role: 'Prepared arcane caster',
      loop: 'Work down the magic tab carefully: spell attack/save math, prepared lists, and slot spend all need to line up before the sheet is trustworthy.',
      testOrder: ['Spell library / prepared surface', 'Slot spend', 'Save / attack roll output'],
      verify: ['Prepared spells', 'Spell slots', 'Spell details', 'Arcane recovery notes'],
    },
    tinker: {
      role: 'Engineer controller',
      loop: 'Audit Tinker as a kit loop: gadget charges first, then rig/deploy actions, then specialty spell support and subclass device identity.',
      testOrder: ['Gadget resource and recharge cadence', 'Deploy / countermeasure action cards', 'Specialty spell and subclass rig tools'],
      verify: ['Gadget Charges', 'Rig actions', 'Deployables', 'Specialty spell lane'],
    },
    pirate: {
      role: 'Tempo duelist',
      loop: 'Audit Pirate as a pressure loop: swagger resource, dirty tricks, movement tempo, and target-control riders should all read as one fighting style.',
      testOrder: ['Swagger spend and recovery', 'Dirty trick action cards', 'Movement / pressure subclass tools'],
      verify: ['Swagger Dice', 'Dirty tricks', 'Bonus-action pressure', 'Subclass identity'],
    },
  };

  function _classKey(charData) {
    const raw = _firstText(charData && charData.className, charData && charData.class, charData && charData.name).toLowerCase();
    return raw.split(/[^a-z]+/).find(Boolean) || '';
  }

  function _playbookForClass(charData) {
    const key = _classKey(charData);
    return CLASS_PLAYBOOKS[key] || null;
  }

  function _featureKeywordHaystack(feature) {
    return [feature && feature.name, feature && feature.description, feature && feature.kind, feature && feature.resourceName, feature && feature.source]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
  }

  function _featureConnectedSystems(feature) {
    const text = _featureKeywordHaystack(feature);
    const systems = new Set();
    if (!text) return ['Feature text'];
    if (/(spell|cantrip|ritual|slot|concentration|metamagic|arcane|pact|divine|smite|hunter's mark)/.test(text)) {
      systems.add('Spell cards');
      systems.add('Slot / concentration rules');
    }
    if (/(rage|focus|ki|bardic inspiration|channel divinity|wild shape|action surge|second wind|lay on hands|sorcery points)/.test(text)) {
      systems.add('Tracked resources');
      systems.add('Rest recovery');
    }
    if (/(attack|martial arts|extra attack|weapon mastery|fighting style|sneak attack|unarmed|damage|reckless)/.test(text)) {
      systems.add('Attack / damage flow');
      systems.add('Target application');
    }
    if (/(reaction|uncanny dodge|deflect|shield|counter)/.test(text)) {
      systems.add('Reaction timing');
    }
    if (/(speed|step of the wind|dash|disengage|movement|push|topple)/.test(text)) {
      systems.add('Movement / positioning');
    }
    if (!systems.size) systems.add('Feature text');
    return Array.from(systems);
  }

  function _featureTestingGuidance(feature, charData) {
    const text = _featureKeywordHaystack(feature);
    const className = _firstText(charData && charData.className, 'this class');
    if (/(rage)/.test(text)) return 'Use this feature, then short/long rest and make sure spend + recovery counts stay synchronized.';
    if (/(focus|ki|discipline points|patient defense|flurry|step of the wind|stunning strike)/.test(text)) return 'Use this from the Combat tab and confirm Focus spend, timing lane, and target/result output all match the feature text.';
    if (/(bardic inspiration|channel divinity|wild shape|lay on hands|action surge|second wind|sorcery points)/.test(text)) return 'Spend the linked resource, then confirm remaining uses and recovery hints update correctly.';
    if (/(spell|metamagic|arcane|pact|ritual)/.test(text)) return 'Open the Magic tab and confirm the related spell, slot, and concentration behavior matches this description.';
    if (/(sneak attack|extra attack|weapon mastery|fighting style|martial arts|reckless attack|divine smite)/.test(text)) return 'Use related attack cards from Combat and confirm this feature changes attack or damage flow as described.';
    return `Use this ${className} feature and verify text clarity, unlock level, and linked combat/spell/resource surfaces.`;
  }



  function _featureRulesBreakdown(feature) {
    const rows = [];
    rows.push({ label: 'Unlock lane', value: feature.level ? `Level ${feature.level}` : 'Passive / always-on' });
    rows.push({ label: 'Feature type', value: feature.kind || feature.actionType || 'Feature' });
    rows.push({ label: 'Section', value: feature.section || 'Feature list' });
    rows.push({ label: 'Subclass path', value: feature.isSubclass ? 'Subclass-specific surface' : 'Core class / build surface' });
    rows.push({ label: 'Range', value: feature.range || '—' });
    rows.push({ label: 'Duration', value: feature.duration || '—' });
    rows.push({ label: 'Save / Trigger', value: feature.save || feature.trigger || '—' });
    rows.push({ label: 'Uses', value: feature.usage || '—' });
    rows.push({ label: 'Recovery', value: feature.recovery || '—' });
    rows.push({ label: 'Resource link', value: feature.resourceName || 'No linked resource detected' });
    return rows;
  }

  function _featureAutomationCoverage(feature) {
    return [
      { label: 'Inspector depth', value: 'Ready' },
      { label: 'Runtime link', value: feature.kind === 'native' || feature.kind === 'class' ? 'Structured / runtime-facing' : 'Mostly descriptive' },
      { label: 'Resource link', value: feature.resourceName ? 'Linked resource surfaced' : 'No linked pool detected' },
      { label: 'Cross-system impact', value: _featureConnectedSystems(feature).length > 1 ? 'Multi-system feature' : 'Local sheet / text impact' },
    ];
  }

  function _featureCommonBlockers(feature) {
    const blockers = [];
    if (!feature.description) blockers.push({ label: 'Rules text', value: 'This entry still needs richer descriptive text to feel complete.' });
    if (feature.resourceName) blockers.push({ label: 'Spend / recovery', value: 'Verify the linked resource changes on use and after rest recovery.' });
    if (feature.isSubclass) blockers.push({ label: 'Unlock source', value: 'Confirm the subclass feature appears at the correct level and in the class feature list.' });
    if (!blockers.length) blockers.push({ label: 'Coverage', value: 'No obvious blockers detected from the current feature metadata.' });
    return blockers;
  }
  function _renderPlaybook(charData, sections) {
    const playbook = _playbookForClass(charData);
    const classLabel = _firstText(charData && charData.className, 'Current class');
    const resources = _safeArray(sections.nativeFeatures)
      .concat(_safeArray(sections.classFeatures))
      .map(function (item) { return _firstText(item && item.resourceName, item && item.name); })
      .filter(Boolean);
    const uniqueResources = Array.from(new Set(resources)).slice(0, 6);
    if (!playbook && !uniqueResources.length) {
      return `<section class="cs-overview-section">
        <div class="cs-overview-section-title">Class Guide</div>
        <div class="cs-overview-copy">Use this area for quick class context and key resources.</div>
        <div class="cs-empty-state compact"><span>Class-specific guidance is not available for this build yet.</span></div>
      </section>`;
    }
    const checklist = (playbook && Array.isArray(playbook.verify) ? playbook.verify : ['Feature text', 'Combat / magic surface']).map(function (item) {
      return `<span class="cs-playbook-chip">${_esc(item)}</span>`;
    }).join('');
    const order = (playbook && Array.isArray(playbook.testOrder) ? playbook.testOrder : ['Feature text', 'Connected systems']).map(function (item) {
      return `<li>${_esc(item)}</li>`;
    }).join('');
    const resourceHtml = uniqueResources.length
      ? `<div class="cs-playbook-chip-row">${uniqueResources.map(function (item) { return `<span class="cs-playbook-chip muted">${_esc(item)}</span>`; }).join('')}</div>`
      : '<div class="cs-empty-state compact"><span>No tracked resource hooks surfaced for this class yet.</span></div>';
    return `<section class="cs-overview-section">
      <div class="cs-overview-section-title">Class Guide</div>
      <div class="cs-overview-copy">Quick reference for how ${_esc(classLabel || 'this build')} plays in live turns.</div>
      <div class="cs-playbook-grid">
        <div class="cs-playbook-card highlight">
          <div class="cs-playbook-eyebrow">Core role</div>
          <div class="cs-playbook-title">${_esc(classLabel || 'Current class')}</div>
          <div class="cs-playbook-copy">${_esc((playbook && playbook.role ? playbook.role + ' — ' : '') + (playbook && playbook.loop ? playbook.loop : 'Use features, actions, and spells together during your turn.'))}</div>
        </div>
        <div class="cs-playbook-card">
          <div class="cs-playbook-eyebrow">Key checks</div>
          <div class="cs-playbook-chip-row">${checklist}</div>
        </div>
        <div class="cs-playbook-card">
          <div class="cs-playbook-eyebrow">First steps</div>
          <ol class="cs-playbook-list">${order}</ol>
        </div>
        <div class="cs-playbook-card">
          <div class="cs-playbook-eyebrow">Tracked resources</div>
          ${resourceHtml}
        </div>
      </div>
    </section>`;
  }



  function _resourceHintsFromSections(sections) {
    const source = []
      .concat(_safeArray(sections && sections.nativeFeatures))
      .concat(_safeArray(sections && sections.classFeatures));
    const seen = new Set();
    return source.map(function (feature) {
      const name = _firstText(feature && feature.resourceName, '');
      if (!name) return null;
      const key = name.toLowerCase();
      if (seen.has(key)) return null;
      seen.add(key);
      const summary = _firstText(feature && feature.usage, feature && feature.recovery, feature && feature.summary, 'Tracked feature resource');
      return { name, summary };
    }).filter(Boolean);
  }

  function _renderCustomClassGuide(charData, sections) {
    const key = _classKey(charData);
    const guide = CUSTOM_CLASS_GUIDES[key];
    if (!guide) return '';
    const resources = _resourceHintsFromSections(sections);
    const resourceHtml = resources.length
      ? resources.map(function (item) { return `<span class="cs-playbook-chip muted">${_esc(item.name)}</span>`; }).join('')
      : '<span class="cs-playbook-chip muted">No structured resource surface detected yet</span>';
    return `<section class="cs-overview-section">
      <div class="cs-overview-section-title">${_esc(guide.title)}</div>
      <div class="cs-overview-copy">${_esc(guide.summary)}</div>
      <div class="cs-playbook-grid">
        <div class="cs-playbook-card highlight">
          <div class="cs-playbook-eyebrow">Core gameplay loop</div>
          <div class="cs-playbook-title">${_esc(_firstText(charData && charData.className, 'Custom class'))}</div>
          <div class="cs-playbook-copy">${_esc(guide.loop)}</div>
        </div>
        <div class="cs-playbook-card">
          <div class="cs-playbook-eyebrow">Signature pillars</div>
          <div class="cs-playbook-chip-row">${guide.pillars.map(function (item) { return `<span class="cs-playbook-chip">${_esc(item)}</span>`; }).join('')}</div>
        </div>
        <div class="cs-playbook-card">
          <div class="cs-playbook-eyebrow">Tracked resources</div>
          <div class="cs-playbook-chip-row">${resourceHtml}</div>
        </div>
        <div class="cs-playbook-card">
          <div class="cs-playbook-eyebrow">Best next surfaces</div>
          <ol class="cs-playbook-list">${guide.next.map(function (item) { return `<li>${_esc(item)}</li>`; }).join('')}</ol>
        </div>
      </div>
    </section>`;
  }
  function _renderSummaryStrip(data) {
    const native = _safeArray(data.nativeFeatures);
    const classFeatures = _safeArray(data.classFeatures);
    const traits = _safeArray(data.traits);
    const feats = _safeArray(data.feats);
    const subclassCount = classFeatures.filter(function (item) { return !!item.isSubclass; }).length;
    return `<div class="cs-traits-summary-grid">
      ${_summaryCard('Features', native.length + classFeatures.length, 'class and subclass entries')}
      ${_summaryCard('Traits', traits.length, 'species and origin rules')}
      ${_summaryCard('Feats', feats.length, 'extra build options')}
      ${_summaryCard('Subclass', subclassCount, subclassCount ? 'subclass features found' : 'no subclass entries yet')}
    </div>`;
  }

  function _renderCharacterNotes(charData) {
    const noteGroups = [
      { label: 'Notes', value: _firstText(charData && charData.notes, charData && charData.identity && charData.identity.notes) },
      { label: 'Backstory', value: _firstText(charData && charData.backstory, charData && charData.identity && charData.identity.backstory) },
      { label: 'Roleplay', value: [_firstText(charData && charData.personalityTraits), _firstText(charData && charData.ideals), _firstText(charData && charData.bonds), _firstText(charData && charData.flaws)].filter(Boolean).join(' • ') },
    ].filter(function (entry) { return entry.value; });
    if (!noteGroups.length) return '';
    return `<section class="cs-overview-section cs-feature-notes-section">
      <div class="cs-overview-section-title">Character Notes</div>
      <div class="cs-overview-copy">A simple place for player reminders and roleplay notes.</div>
      <div class="cs-build-note-grid">${noteGroups.map(function (note) {
        return `<div class="cs-build-note-card"><div class="cs-build-note-label">${_esc(note.label)}</div><div class="cs-build-note-value">${_esc(note.value)}</div></div>`;
      }).join('')}</div>
    </section>`;
  }

  function _renderFeatureControls() {
    return `<section class="cs-overview-section cs-feature-controls-section">
      <div class="cs-overview-section-title">Features & Traits</div>
      <div class="cs-overview-copy">Each row starts with a short rules summary. Open any feature card to view full details.</div>
      <div class="cs-feature-toolbar">
        <input type="search" class="cs-feature-search" data-feature-search placeholder="Search features, traits, feats, resources…" aria-label="Search features" />
        <div class="cs-feature-filter-row" role="tablist" aria-label="Feature filters">
          <button type="button" class="cs-feature-filter-chip active" data-feature-filter="all">All</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="class">Class Features</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="traits">Traits</button>
          <button type="button" class="cs-feature-filter-chip" data-feature-filter="feats">Feats</button>
        </div>
      </div>
    </section>`;
  }

  function _featurePlayerFacts(feature) {
    return [
      feature.actionType ? { label: 'Action', value: feature.actionType } : null,
      feature.resourceName ? { label: 'Resource', value: feature.resourceName } : null,
      feature.range ? { label: 'Range', value: feature.range } : null,
      feature.duration ? { label: 'Duration', value: feature.duration } : null,
      (feature.save || feature.trigger) ? { label: feature.save ? 'Save' : 'Trigger', value: feature.save || feature.trigger } : null,
      feature.effect ? { label: 'Effect', value: feature.effect } : null,
      feature.usage ? { label: 'Uses', value: feature.usage } : null,
      feature.recovery ? { label: 'Recovery', value: feature.recovery } : null,
    ].filter(Boolean);
  }

  function _featureWhenItMatters(feature) {
    const text = _featureKeywordHaystack(feature);
    if (!text) return 'Use this when the moment matches the feature’s summary and rules text.';
    if (/(bonus action|reaction|action|trigger)/.test(text)) return 'Look for the turn where this changes your options or timing, then use it there instead of saving it forever.';
    if (/(resource|rest|uses|sorcery|focus|ki|bardic inspiration|channel divinity|lay on hands|wild shape)/.test(text)) return 'Check the resource cost first, then spend it when the payoff clearly matters.';
    if (/(aura|passive|always|defense|resistance|advantage on saving throw|saving throw)/.test(text)) return 'This is mostly passive—make sure its benefit is visible when the right roll, attack, or condition comes up.';
    if (/(spell|magic|cantrip|slot|concentration|invocation)/.test(text)) return 'Treat this like part of your spell package and check that the magic tab or related action shows the same idea clearly.';
    return 'Use this when the rules text lines up with what is happening in the scene, especially if it changes attacks, movement, defense, or resources.';
  }


  function _featureGeneratedGuidance(feature) {
    const text = _featureKeywordHaystack(feature);
    const notes = [];
    if (!text) return '';
    if (/once on each of your turns/.test(text) && /weapon attack/.test(text)) notes.push('This is a passive rider, not a separate action. Apply it to one successful weapon attack on your turn.');
    if (/channel divinity/.test(text)) notes.push('This feature uses Channel Divinity, so it shares that resource with your other Channel Divinity options.');
    if (/bonus action/.test(text)) notes.push('This uses your bonus action on the turn you activate it.');
    if (/reaction/.test(text)) notes.push('This uses your reaction, so you only get one until your next turn starts.');
    if (/become invisible/.test(text)) notes.push('The invisibility ends when the listed duration runs out or another rule breaks it.');
    if (/(deal extra|extra .* damage)/.test(text) && /weapon attack/.test(text)) notes.push('Extra damage riders apply after the hit lands; they do not create a second attack roll.');
    if (/(long rest|short rest)/.test(text) && !/recovery/.test(text)) notes.push('Check the rest cadence in the text so you know when the feature becomes available again.');
    return notes.join(' ');
  }

  function _renderFeatureBody(feature) {
    const summary = _cleanFeatureSummary(feature);
    const facts = _featurePlayerFacts(feature);
    const description = _trimRepeatedLead(summary, _firstText(feature && feature.description, ''));
    const generatedGuidance = _featureGeneratedGuidance(feature);
    const whenItMatters = _featureWhenItMatters(feature);

    const factsHtml = facts.length ? `<div class="cs-feature-facts">${facts.map(function (fact) {
      return `<div class="cs-feature-fact"><span class="cs-feature-fact-label">${_esc(fact.label)}</span><span class="cs-feature-fact-value">${_esc(fact.value)}</span></div>`;
    }).join('')}</div>` : '';

    if (!description) {
      const fallbackLines = [];
      if (facts.length) {
        fallbackLines.push(facts.map(function (fact) { return `${fact.label}: ${fact.value}`; }).join(' • '));
      }
      if (generatedGuidance) fallbackLines.push(generatedGuidance);
      fallbackLines.push(whenItMatters);
      const fallbackCopy = fallbackLines.filter(Boolean).join('\n\n');
      return `
        <div class="cs-feature-body-summary"><strong>${_esc(summary)}</strong></div>
        ${factsHtml}
        <div class="cs-feature-body-rules">${_descHtml(fallbackCopy || 'No additional detail is available for this feature yet.')}</div>
      `;
    }

    const rulesHtml = `<div class="cs-feature-body-rules">${_descHtml(description)}</div>`;
    const guidanceHtml = generatedGuidance
      ? `<div class="cs-feature-use-note"><span class="cs-feature-note-label">Rules note — </span>${_esc(generatedGuidance)}</div>`
      : '';
    const whenHtml = `<div class="cs-feature-use-note"><span class="cs-feature-note-label">When to use — </span>${_esc(whenItMatters)}</div>`;

    return `
      <div class="cs-feature-body-summary"><strong>${_esc(summary)}</strong></div>
      ${factsHtml}
      ${rulesHtml}
      ${guidanceHtml}
      ${whenHtml}
    `;
  }

  function _renderFeatureItem(feature, idx, { showLevel = false, showSubclass = false, sectionKey = 'all' } = {}) {
    const levelText = showLevel && feature.level ? `Level ${_esc(String(feature.level))}` : '';
    const sourceLine = _featureSourceLine(feature);
    const summary = _cleanFeatureSummary(feature);
    const tags = _featureTagPills(feature);
    const searchBlob = [feature.name, feature.summary, feature.description, feature.source, feature.kind, feature.resourceName, feature.actionType, _safeArray(feature.tags).join(' ')].filter(Boolean).join(' ').toLowerCase();

    return `
      <div class="cs-feature-item" data-feature-index="${_esc(String(idx))}" data-feature-type="${_esc(_featureTypeKey(feature) || sectionKey)}" data-feature-level="${_esc(String(feature.level || 0))}" data-feature-search="${_esc(searchBlob)}">
        <div class="cs-feature-header" role="button" tabindex="0" aria-expanded="false" aria-label="${_esc(feature.name || 'Feature')}">
          <div class="cs-feature-maincopy">
            <div class="cs-feature-title-row">
              <span class="cs-feature-name">${_esc(feature.name || '—')}</span>
            </div>
            ${sourceLine || levelText ? `<div class="cs-feature-inline-meta">${_esc([sourceLine, !sourceLine ? levelText : ''].filter(Boolean).join(' • '))}</div>` : ''}
            <div class="cs-feature-preview"><strong>${_esc(summary)}</strong></div>
          </div>
          <span class="cs-feature-meta">
            ${tags.map(function (tag) { return `<span class="cs-feature-kind-badge">${_esc(tag)}</span>`; }).join('')}
            <span class="cs-feature-chevron" aria-hidden="true">&#9658;</span>
          </span>
        </div>
        <div class="cs-feature-body">${_renderFeatureBody(feature)}</div>
      </div>`;
  }


  function _renderSection(title, items, opts = {}) {
    if (!items || !items.length) {
      return `<div class="cs-feature-section" data-feature-section="${_esc(opts.sectionKey || 'all')}">
        <div class="cs-feature-section-title">${_esc(title)}</div>
        ${opts.copy ? `<div class="cs-feature-section-copy">${_esc(opts.copy)}</div>` : ''}
        <div class="cs-feature-list">
          <div class="cs-empty-state">
            <span class="cs-empty-state-icon">📜</span>
            <span>${_esc(opts.emptyLabel || 'None recorded')}</span>
          </div>
        </div>
      </div>`;
    }

    const rows = items.map(function (item, idx) {
      return _renderFeatureItem(item, opts.offset ? opts.offset + idx : idx, opts);
    }).join('');
    return `<div class="cs-feature-section" data-feature-section="${_esc(opts.sectionKey || 'all')}">
      <div class="cs-feature-section-title">${_esc(title)}</div>
      ${opts.copy ? `<div class="cs-feature-section-copy">${_esc(opts.copy)}</div>` : ''}
      <div class="cs-feature-list">${rows}</div>
    </div>`;
  }

  function _fetchSheetFeatures(charData, cb) {
    const charId = charData && (charData.id || charData.charId || charData.characterId);
    if (!charId) { cb(null, null); return; }
    const params = new URLSearchParams();
    if (charData.sessionId) params.set('session_id', charData.sessionId);
    const qs = params.toString();

    fetch(`/api/character/${encodeURIComponent(charId)}/sheet${qs ? '?' + qs : ''}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        if (!data || !data.character) { cb(null, null); return; }
        const character = data.character;
        const result = {};
        const rawFeatures = character.classFeatures;
        if (rawFeatures && typeof rawFeatures === 'object' && !Array.isArray(rawFeatures)) {
          const flat = [];
          Object.entries(rawFeatures).forEach(([lvl, items]) => {
            if (Array.isArray(items)) {
              items.forEach(item => flat.push(_coerceFeature(item, { level: parseInt(lvl, 10) || 0, source: 'API sheet' })));
            }
          });
          if (flat.length) result.features = flat.filter(Boolean);
        } else if (Array.isArray(rawFeatures) && rawFeatures.length) {
          result.features = rawFeatures.map(f => _coerceFeature(f, { source: 'API sheet' })).filter(Boolean);
        }
        if (Array.isArray(character.speciesTraits) && character.speciesTraits.length) {
          result.traits = character.speciesTraits.map(t => _coerceFeature(t, { source: 'Species trait', kind: 'Trait' })).filter(Boolean);
        }
        cb(null, result);
      })
      .catch(err => cb(err, null));
  }

  function _isHiddenProgressionFeature(feature) {
    if (!feature) return false;
    const rawName = _firstText(feature.name, '');
    const name = rawName.toLowerCase();
    const cleanName = rawName.replace(/\[[^\]]+\]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
    const summary = _firstText(feature.summary, feature.description, '').toLowerCase();
    const source = _firstText(feature.source, feature.section, '').toLowerCase();
    const haystack = [name, cleanName, summary, source, _firstText(feature.kind, ''), _firstText(feature.className, ''), _firstText(feature.subclassName, '')].join(' ');
    if (/^ability score improvement$/i.test(cleanName)) return true;
    if (/^epic boon/i.test(cleanName)) return true;
    if (/^cantrips known\b/i.test(cleanName)) return true;
    if (/^spells known\b/i.test(cleanName)) return true;
    if (/^cantrips known\s*:?\s*\d+/i.test(cleanName)) return true;
    if (/^spells known\s*:?\s*\d+/i.test(cleanName)) return true;
    if (/^subclass feature$/i.test(cleanName) && /progression|unlock/.test(haystack)) return true;
    if (/\bsubclass feature\b/.test(cleanName) && /progression|unlock/.test(haystack)) return true;
    if (/\b\d+(st|nd|rd|th)-level spells?\b/.test(cleanName)) return true;
    if (/\b\d+(st|nd|rd|th)-level spell slots?\b/.test(cleanName)) return true;
    if (/native spellcasting progression/.test(source)) return true;
    if (/spellcasting progression/.test(haystack)) return true;
    if (/\bability score improvement\b/.test(haystack) && /choose|feat|ability|progression|unlock/.test(haystack)) return true;
    if (/\bcantrips known\b/.test(summary) || /\bspells known\b/.test(summary)) return true;
    if (/\b\d+(st|nd|rd|th)-level spells?\b/.test(summary) || /\b\d+(st|nd|rd|th)-level spell slots?\b/.test(summary)) return true;
    if (/\bspell slots?\b/.test(cleanName) && /native|progression|automatic|unlock/.test(haystack)) return true;
    if (/\b(cantrip|spell) (progression|unlock|slots?)\b/.test(haystack)) return true;
    return false;
  }


  function _extractSections(charData, sheetData) {
    const merged = Object.assign({}, charData || {}, sheetData || {});
    const nativeFeatures = _safeArray(charData && charData.nativeFeatures)
      .map(item => _coerceFeature(item, { source: 'Structured', kind: 'Native' }))
      .filter(Boolean)
      .filter(function (item) { return !_isHiddenProgressionFeature(item); });
    const classFeatures = _dedupeFeatures(
      _safeArray(merged.features).map(item => _coerceFeature(item, { source: 'Class feature', kind: 'Class' }))
        .concat(_safeArray(charData && charData.nativeClassFeatures).map(item => _coerceFeature(item, { source: 'Class progression', kind: 'Class' })))
        .filter(Boolean)
        .filter(function (item) { return !_isHiddenProgressionFeature(item); })
    );
    const traits = _dedupeFeatures(
      _safeArray(merged.traits).map(item => _coerceFeature(item, { source: 'Species trait', kind: 'Trait' }))
    );
    if (charData && (charData.species || charData.race)) {
      traits.unshift(_coerceFeature({
        name: `${_firstText(charData.species, charData.race)} profile`,
        description: _firstText(charData.senses, charData.languages, charData.size ? `Size ${charData.size}` : ''),
        source: 'Origin summary',
        kind: 'Origin',
      }));
    }
    const feats = _dedupeFeatures(
      _safeArray(merged.feats).map(item => _coerceFeature(item, { source: 'Feat', kind: 'Feat' }))
    );
    return { nativeFeatures, classFeatures, traits, feats };
  }

  function _groupFeaturesByLevel(items) {
    const map = new Map();
    _safeArray(items).forEach(function (feature) {
      const lvl = parseInt(feature && feature.level, 10);
      if (!Number.isFinite(lvl) || lvl <= 0) return;
      if (!map.has(lvl)) map.set(lvl, []);
      map.get(lvl).push(feature);
    });
    return Array.from(map.entries())
      .sort(function (a, b) { return a[0] - b[0]; })
      .map(function (entry) {
        return { level: entry[0], items: entry[1] };
      });
  }

  function _roadmapCard(entry, currentLevel) {
    const preview = entry.items.slice(0, 3).map(function (item) { return _esc(item.name || 'Feature'); }).join(' • ');
    const levelState = entry.level === currentLevel ? 'current' : (entry.level > currentLevel ? 'upcoming' : 'past');
    const levelSearch = entry.items.map(function (item) {
      return [item.name, item.description, item.kind, item.source].filter(Boolean).join(' ');
    }).join(' ').toLowerCase();
    return `<button type="button" class="cs-roadmap-card ${_esc(levelState)}" data-roadmap-level="${_esc(String(entry.level))}" data-feature-type="class" data-feature-search="${_esc(levelSearch)}">
      <div class="cs-roadmap-level">Level ${_esc(String(entry.level))}</div>
      <div class="cs-roadmap-count">${_esc(String(entry.items.length))} unlock${entry.items.length === 1 ? '' : 's'}</div>
      <div class="cs-roadmap-preview">${preview || 'Open to inspect'}</div>
      <div class="cs-roadmap-hint">${levelState === 'current' ? 'Current level surface' : (levelState === 'upcoming' ? 'Upcoming unlocks' : 'Already gained')}</div>
    </button>`;
  }

  function _renderRoadmap(sections, currentLevel) {
    const roadmap = _groupFeaturesByLevel([].concat(_safeArray(sections.nativeFeatures), _safeArray(sections.classFeatures)));
    if (!roadmap.length) {
      return `<section class="cs-overview-section">
        <div class="cs-overview-section-title">Level Roadmap</div>
        <div class="cs-overview-copy">This roadmap shows what the character gains by level so progression is easier to read at a glance.</div>
        <div class="cs-empty-state compact"><span>No level-tagged class features are available yet.</span></div>
      </section>`;
    }
    return `<section class="cs-overview-section">
      <div class="cs-overview-section-title">Level Roadmap</div>
      <div class="cs-overview-copy">This ladder shows what you already have and what is coming next, so leveling is easier to follow.</div>
      <div class="cs-roadmap-grid">${roadmap.map(function (entry) { return _roadmapCard(entry, currentLevel); }).join('')}</div>
    </section>`;
  }

  function _renderLevelSpotlight(sections, currentLevel) {
    const classRoadmap = _groupFeaturesByLevel([].concat(_safeArray(sections.nativeFeatures), _safeArray(sections.classFeatures)));
    const currentEntry = classRoadmap.find(function (entry) { return entry.level === currentLevel; }) || null;
    const nextEntry = classRoadmap.find(function (entry) { return entry.level > currentLevel; }) || null;
    const currentList = currentEntry && currentEntry.items.length
      ? currentEntry.items.map(function (item) {
          return `<button type="button" class="cs-spotlight-link" data-feature-inspect-name="${_esc(item.name || '')}">${_esc(item.name || 'Feature')}</button>`;
        }).join('')
      : '<div class="cs-empty-state compact"><span>No current level feature rows were tagged with this level yet.</span></div>';
    const nextList = nextEntry && nextEntry.items.length
      ? nextEntry.items.slice(0, 5).map(function (item) {
          return `<button type="button" class="cs-spotlight-link" data-feature-inspect-name="${_esc(item.name || '')}">${_esc(item.name || 'Feature')}</button>`;
        }).join('')
      : '<div class="cs-empty-state compact"><span>No future unlock rows are surfaced yet.</span></div>';
    return `<section class="cs-overview-section">
      <div class="cs-overview-section-title">Current & Next Unlocks</div>
      <div class="cs-overview-copy">This block highlights the features you should already have and the next unlock waiting for you.</div>
      <div class="cs-spotlight-grid">
        <div class="cs-spotlight-card current">
          <div class="cs-spotlight-eyebrow">Current level</div>
          <div class="cs-spotlight-title">Level ${_esc(String(currentLevel || 0))}</div>
          <div class="cs-spotlight-list">${currentList}</div>
        </div>
        <div class="cs-spotlight-card upcoming">
          <div class="cs-spotlight-eyebrow">Next unlock</div>
          <div class="cs-spotlight-title">${nextEntry ? `Level ${_esc(String(nextEntry.level))}` : 'No higher unlock loaded'}</div>
          <div class="cs-spotlight-list">${nextList}</div>
        </div>
      </div>
    </section>`;
  }

  function _openFeatureDetails(feature, context = {}) {
    if (!feature || !global.CSContainer || typeof global.CSContainer.openDetailDrawer !== 'function') return;
    const quickFacts = _featurePlayerFacts(feature);
    global.CSContainer.openDetailDrawer({
      kicker: 'Feature',
      title: feature.name || 'Feature',
      subtitle: [feature.isSubclass ? 'Subclass feature' : '', feature.level ? `Level ${feature.level}` : '', feature.source || feature.className || 'Character feature'].filter(Boolean).join(' • ') || 'Character feature',
      chips: [feature.actionType || '', feature.resourceName || '', feature.level ? `Level ${feature.level}` : ''].filter(Boolean),
      sections: [
        { title: 'Summary', body: feature.summary || feature.effect || _previewText(feature.description || '', 240) || 'No quick summary loaded yet.' },
        { title: 'Feature Data', items: quickFacts.length ? quickFacts : [{ label: 'Type', value: feature.actionType || 'Passive' }] },
        { title: 'Key Rules', body: feature.description || feature.desc || 'No detailed feature text is loaded for this entry yet.' },
        { title: 'Source', items: [
          { label: 'Level', value: feature.level ? String(feature.level) : 'Always on' },
          { label: 'From', value: feature.source || feature.className || 'Character feature' },
          { label: 'Subclass', value: feature.subclassName || (feature.isSubclass ? 'Yes' : 'No') },
        ] },
      ],
    });
  }

  function _applyFeatureFilters(container) {
    if (!container) return;
    const query = String(container.__csFeatureQuery || '').trim().toLowerCase();
    const filter = String(container.__csFeatureFilter || 'all');
    const items = Array.from(container.querySelectorAll('.cs-feature-item'));
    items.forEach(function (item) {
      const type = String(item.getAttribute('data-feature-type') || 'all');
      const search = String(item.getAttribute('data-feature-search') || '').toLowerCase();
      const matchesFilter = filter === 'all' || type === filter;
      const matchesQuery = !query || search.indexOf(query) !== -1;
      item.hidden = !(matchesFilter && matchesQuery);
    });
    Array.from(container.querySelectorAll('.cs-feature-section')).forEach(function (section) {
      const rows = Array.from(section.querySelectorAll('.cs-feature-item'));
      if (!rows.length) return;
      section.hidden = rows.every(function (row) { return row.hidden; });
    });
    Array.from(container.querySelectorAll('.cs-roadmap-card')).forEach(function (card) {
      const type = String(card.getAttribute('data-feature-type') || 'class');
      const search = String(card.getAttribute('data-feature-search') || '').toLowerCase();
      const matchesFilter = filter === 'all' || filter === 'class' || type === filter;
      const matchesQuery = !query || search.indexOf(query) !== -1;
      card.hidden = !(matchesFilter && matchesQuery);
    });
    Array.from(container.querySelectorAll('.cs-feature-filter-chip')).forEach(function (btn) {
      btn.classList.toggle('active', String(btn.getAttribute('data-feature-filter')) === filter);
    });
  }

  function _bindExpand(container) {
    if (!container || container.__csFeaturesBound) return;
    container.__csFeaturesBound = true;
    container.addEventListener('click', function (e) {
      const inspectBtn = e.target.closest('[data-feature-inspect]');
      if (inspectBtn) {
        e.preventDefault();
        e.stopPropagation();
        const idx = parseInt(inspectBtn.getAttribute('data-feature-inspect'), 10);
        const features = container.__csFeaturesCache || [];
        if (Number.isFinite(idx) && features[idx]) _openFeatureDetails(features[idx], { sectionTitle: 'Feature list', charData: container.__csCharData || {} });
        return;
      }
      const spotlightBtn = e.target.closest('[data-feature-inspect-name]');
      if (spotlightBtn) {
        e.preventDefault();
        const targetName = String(spotlightBtn.getAttribute('data-feature-inspect-name') || '').toLowerCase();
        const features = container.__csFeaturesCache || [];
        const feature = features.find(function (entry) { return String(entry && entry.name || '').toLowerCase() === targetName; });
        if (feature) _openFeatureDetails(feature, { sectionTitle: 'Current & Next Unlocks', charData: container.__csCharData || {} });
        return;
      }
      const roadmapCard = e.target.closest('[data-roadmap-level]');
      if (roadmapCard) {
        e.preventDefault();
        const level = parseInt(roadmapCard.getAttribute('data-roadmap-level'), 10);
        const features = (container.__csFeaturesCache || []).filter(function (entry) { return parseInt(entry && entry.level, 10) === level; });
        if (features.length) {
          _openFeatureDetails(features[0], {
            sectionTitle: `Level Roadmap • Level ${level}`,
            charData: container.__csCharData || {}
          });
        }
        return;
      }
      const filterBtn = e.target.closest('[data-feature-filter]');
      if (filterBtn) {
        e.preventDefault();
        container.__csFeatureFilter = String(filterBtn.getAttribute('data-feature-filter') || 'all');
        _applyFeatureFilters(container);
        return;
      }
      const mapJump = e.target.closest('[data-map-panel-open]');
      if (mapJump) {
        e.preventDefault();
        e.stopPropagation();
        if (global.CSContainer && typeof global.CSContainer.openMapPanelFromSheet === 'function') {
          global.CSContainer.openMapPanelFromSheet(String(mapJump.getAttribute('data-map-panel-open') || ''));
        }
        return;
      }
      const header = e.target.closest('.cs-feature-header');
      if (!header) return;
      const item = header.closest('.cs-feature-item');
      if (!item) return;
      const section = item.closest('.cs-feature-section');
      Array.from((section || container).querySelectorAll('.cs-feature-item.open')).forEach(function (openItem) {
        if (openItem === item) return;
        openItem.classList.remove('open');
        const openHeader = openItem.querySelector('.cs-feature-header');
        if (openHeader) openHeader.setAttribute('aria-expanded', 'false');
      });
      const isOpen = item.classList.toggle('open');
      header.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
    container.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        const header = e.target.closest('.cs-feature-header');
        if (header) {
          e.preventDefault();
          header.click();
        }
      }
    });
    container.addEventListener('input', function (e) {
      const search = e.target.closest('[data-feature-search]');
      if (!search) return;
      container.__csFeatureQuery = search.value || '';
      _applyFeatureFilters(container);
    });
  }

  function _render(container, charData, sheetData) {
    const sections = _extractSections(charData, sheetData);
    const allFeatures = []
      .concat(sections.nativeFeatures || [])
      .concat(sections.classFeatures || [])
      .concat(sections.traits || [])
      .concat(sections.feats || []);
    const currentLevel = parseInt(charData && (charData.totalLevel || charData.level), 10) || 0;

    let offset = 0;
    const playerClassFeatures = _dedupeFeatures([].concat(_safeArray(sections.nativeFeatures), _safeArray(sections.classFeatures)));
    const classMarkup = _renderSection('Class & Subclass Features', playerClassFeatures, {
      showLevel: true,
      showSubclass: true,
      offset,
      sectionKey: 'class',
      copy: 'Core class and subclass features, with the quick rules summary first and the full text directly underneath when opened.',
      emptyLabel: 'No class features were found for this character.',
    });
    offset += _safeArray(playerClassFeatures).length;
    const traitsMarkup = _renderSection('Species Traits', sections.traits, {
      offset,
      sectionKey: 'traits',
      copy: 'Species, ancestry, and origin-facing rules live here.',
      emptyLabel: 'No species traits are loaded yet.',
    });
    offset += _safeArray(sections.traits).length;
    const featsMarkup = _renderSection('Feats', sections.feats, {
      offset,
      sectionKey: 'feats',
      copy: 'Feats live here with plain-language reminders of what they change.',
      emptyLabel: 'No feats are recorded on this sheet yet.',
    });

    container.innerHTML = `
      <div class="cs-traits-shell cs-traits-shell-readable">
        ${_renderFeatureControls()}
        ${classMarkup}
        ${traitsMarkup}
        ${featsMarkup}
        </div>
    `;

    container.__csFeaturesCache = allFeatures;
    container.__csCharData = charData || {};
    container.__csFeatureFilter = container.__csFeatureFilter || 'all';
    _bindExpand(container);
    _applyFeatureFilters(container);
  }

  function initFeaturesTab(container, charData) {
    if (!container) return;
    _render(container, charData, null);
    _fetchSheetFeatures(charData, (err, sheetData) => {
      if (!err && sheetData) {
        _render(container, charData, sheetData);
      }
    });
  }

  global.FeaturesTab = { initFeaturesTab };

}(window));
