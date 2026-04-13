# Claude Code — Character Builder UI Implementation
## Drop this entire file into Claude Code. Run from repo root: `DnD-Beta-master/`

---

## CONTEXT — READ FIRST

You are implementing a premium character builder UI for a D&D virtual tabletop called **Tavern Tabletop**. The repo is at `DnD-Beta-master/`. You have a fully working HTML preview of the target design at `character-builder-preview.html` — read it first to understand every visual detail, every component, and every interaction before touching any app file.

**Start by reading these files in this exact order:**

```
1. character-builder-preview.html          ← The complete UI reference. Every pixel, every interaction.
2. client/static/js/character/builder/builder_shell.js
3. client/static/js/character/builder/builder_router.js
4. client/static/js/character/builder/builder_state.js
5. client/static/js/character/builder/builder_api.js
6. client/static/js/character/builder/builder_validators.js
7. client/static/js/character/builder/steps/step_species.js
8. client/static/js/character/builder/steps/step_class.js
9. client/static/js/character/builder/steps/step_abilities.js
10. client/static/js/character/builder/steps/step_origins.js
11. client/static/js/character/builder/steps/step_identity.js
12. client/static/js/character/builder/steps/step_review.js
13. client/static/js/character/builder/steps/step_progression.js
14. client/static/js/character/builder/steps/step_spells.js
15. client/static/js/character/builder/steps/step_equipment.js
16. client/static/css/session-theme.css                         ← Existing CSS variables and theme
17. server/data/rules/5e2024/species/human.json                 ← Sample species data
18. server/data/rules/5e2024/classes/fighter.json               ← Sample class data
19. server/character/rules_catalog.py                           ← Catalog loader
20. server/rules/routes.py                                      ← API routes
```

**Do not modify any backend Python files yet** — this task is frontend-only. Do not touch WebSocket handlers, session management, or auth.

---

## TASK OVERVIEW

Implement the premium UI from `character-builder-preview.html` into the live app. The implementation splits into 6 sub-tasks below. Work through them in order. Each one is a complete, self-contained change.

---

## SUB-TASK 1 — CSS Design System
### File: `client/static/css/character-builder.css` (CREATE NEW)

Extract the complete CSS design system from `character-builder-preview.html` into a standalone stylesheet. This file will be imported by all builder step modules.

The CSS must include every rule from the preview, organized into these sections:

```css
/* ── 1. CSS VARIABLES ── */
/* Copy :root block from preview exactly */

/* ── 2. SPECIES CARD GRID ── */
/* .species-grid, .species-card, .sc-icon, .sc-name, .sc-badges, .sc-badge,
   .sc-flavor, .sc-traits, .sc-trait, .sc-selected-check */

/* ── 3. SPECIES DETAIL PANEL ── */
/* .species-detail, .sd-header, .sd-name, .sd-meta, .sd-traits-grid,
   .sd-trait, .sd-trait-name, .sd-trait-desc, .sd-trait-mech */

/* ── 4. CLASS CARD GRID ── */
/* .class-grid, .class-card, .cc-header, .cc-name, .cc-die, .cc-role,
   .cc-tags, .cc-tag, .cc-features, .cc-feature, .cc-spellcaster */

/* ── 5. CLASS DETAIL PANEL ── */
/* .class-detail, .cd-header, .cd-stats, .cd-stat, .cd-desc */

/* ── 6. PROGRESSION TABLE ── */
/* .prog-table, .prog-level-badge, .feature-tag, .asi-row, .subclass-row */

/* ── 7. ABILITIES ── */
/* .ability-method-tabs, .method-tab, .ability-layout, .ability-grid-6,
   .ability-block, .ability-label, .ability-mod, .ability-score-box,
   .ability-btn, .ability-cost-indicator, .point-buy-budget, .pb-points,
   .pb-label, .pb-bar, .pb-bar-fill, .class-tip */

/* ── 8. STAT BLOCK REVIEW ── */
/* .statblock, .sb-banner, .sb-portrait, .sb-identity, .sb-char-name,
   .sb-char-sub, .sb-combat-bar, .sb-stat, .sb-body, .sb-section,
   .ability-row-sb, .save-row, .save-dot, .feature-list-sb,
   .sb-spell-bar, .spell-slot-bar, .ss-slot, .sb-validation */

/* ── 9. BUILDER CHROME ── */
/* .screen-header, .screen-title, .screen-subtitle, .screen-divider,
   .roadmap-toggle, .roadmap-content, .roadmap-row, .builder-tooltip-btn,
   .step-progress, .step-track, .step-dot, .step-connector, .step-label */

/* ── 10. SHARED COMPONENTS ── */
/* .search-input, .btn-nav, .help-btn, .preview-banner, .toast */

/* ── 11. ANIMATIONS ── */
/* @keyframes screenIn, @keyframes toastIn */
```

**Critical rule:** The CSS variables in this file must co-exist with `session-theme.css`. Do NOT override any existing `--color-*` variables that session-theme.css already defines. Add new variables using the `--cb-` prefix if there is any collision risk (e.g. `--cb-gold`, `--cb-obsidian`). Use the preview's `:root` block as the source of truth for all builder-specific variables.

After creating the file, verify it contains every class used in the preview HTML. Run a grep to confirm:
```bash
grep -o 'class="[^"]*"' character-builder-preview.html | tr ' ' '\n' | sort -u
```

---

## SUB-TASK 2 — Species Step
### File: `client/static/js/character/builder/steps/step_species.js` (REWRITE)

Rewrite the entire `render` function and add supporting functions. The existing module structure (`registerStep`, `escHtml`, `ensureCatalogLoaded`) must be preserved — only change what renders.

**The render function must return HTML that matches the species screen from the preview exactly.** Here is the complete spec:

### 2a. Inject CSS on first render

Add `ensureBuilderStyles()` at the top of the IIFE. It adds a `<link>` to `character-builder.css` if not already present:

```javascript
function ensureBuilderStyles() {
  if (document.getElementById('character-builder-css')) return;
  const link = document.createElement('link');
  link.id = 'character-builder-css';
  link.rel = 'stylesheet';
  link.href = '/static/css/character-builder.css';
  document.head.appendChild(link);
}
```

### 2b. Card grid render

The `render` function returns a grid of species cards. Each card must:

- Use `data-species-id="${entry.id}"` attribute
- Display: icon (from `entry.icon` or a fallback emoji map), name, speed badge, darkvision badge (only if `senses.darkvision > 0`), size badge, up to 3 trait names as pills, first 2 lines of `flavorText` (truncated with CSS)
- Have a `✓` check element (hidden by default, shown when `selected` class is present)
- Have a `data-builder-path="species.id"` hidden input that the existing state system reads — keep this or the state won't save

**Emoji icon fallback map** (for species that don't have an icon field in the JSON yet):
```javascript
const SPECIES_ICONS = {
  human: '👤', elf: '🌙', dwarf: '⛏', halfling: '🍀',
  dragonborn: '🐉', tiefling: '😈', gnome: '🔬', 'half-elf': '🌙',
  'half-orc': '💪', 'wood-elf': '🌲', aasimar: '✨', goliath: '⛰️', orc: '💚'
};
```

**Species color map** (for the colored icon background and card accent):
```javascript
const SPECIES_COLORS = {
  human: '#C9A84C', elf: '#7FB3D3', 'wood-elf': '#58D68D', dwarf: '#A0826D',
  halfling: '#82E0AA', dragonborn: '#E74C3C', tiefling: '#C0392B',
  gnome: '#48C9B0', 'half-elf': '#85C1E9', 'half-orc': '#27AE60',
  aasimar: '#F7DC6F', goliath: '#AAB7B8', orc: '#58D68D'
};
```

### 2c. Detail panel

After the card grid, render a `<div class="species-detail" id="builder-species-detail">` that starts hidden. When a card is clicked, populate this panel with:
- Species name (colored with the species color)
- Badges row (speed, darkvision, size)
- Flavor text in italic
- All traits in a 2-column grid. Each trait shows: name, full `description`, and if the trait has a `mechanics` object, render a teal-highlighted mechanic line showing actionType + usesPerRest + any damage formula

### 2d. Wire interactions in the `bind` function

The step has a `bind(root, context)` function called after render. Wire these in `bind`:

```javascript
bind: function bindSpeciesStep(root, context) {
  // 1. Card click handler
  root.querySelectorAll('.species-card').forEach(function(card) {
    card.addEventListener('click', function() {
      const id = card.dataset.speciesId;
      // Update hidden input
      const hiddenInput = root.querySelector('[data-builder-path="species.id"]');
      if (hiddenInput) hiddenInput.value = id;
      // Update state
      if (context && typeof context.onSetField === 'function') {
        context.onSetField(['species', 'id'], id);
      }
      // Visual selection
      root.querySelectorAll('.species-card').forEach(function(c) {
        c.classList.remove('selected');
      });
      card.classList.add('selected');
      // Show detail panel
      showSpeciesDetailPanel(root, id);
    });
  });

  // 2. Auto-show detail for already-selected species
  const draft = context && context.draft || {};
  const currentId = draft.species && draft.species.id;
  if (currentId) {
    showSpeciesDetailPanel(root, currentId);
  }
}
```

`showSpeciesDetailPanel(root, speciesId)` must:
1. Find the species data from `CharacterBuilderAPI.getCachedCatalog().species`
2. Populate `#builder-species-detail` with the full detail HTML
3. Add the `visible` CSS class to show it
4. Scroll the panel into view smoothly

### 2e. Roadmap toggle

Add the roadmap button and collapsible div at the top of the render output. Wire the toggle in `bind`. The roadmap content is populated from the currently selected class in the draft (read `draft.class.id`, look up the class in the catalog's `progressionTable`, show first 5 levels).

---

## SUB-TASK 3 — Class Step
### File: `client/static/js/character/builder/steps/step_class.js` (REWRITE)

Same approach as Species. Preserve the module structure, rewrite render and bind.

### 3a. Card grid

Each class card must show:
- Class name with color from `CLASS_COLORS` map (define this in the module)
- Hit die badge
- Caster type badge (full/half/pact) — only if `spellcastingType !== 'none'` and `spellcastingType` exists
- Role identity line (`classDescription` truncated to 80 chars, or use a `roleIdentity` field if present)
- Save proficiencies as pills
- Armor proficiencies as a single pill (first 2 armor types)
- First 4 features from `levelUnlockIds["1"]` mapped through `featureDefinitions` to their `displayName`
- Bottom accent bar colored with the class color (CSS `::after` pseudo-element using `--class-color` custom property set inline)
- A `data-class-id="${classId}"` attribute
- A hidden `<input data-builder-path="class.id" />` — must keep this for state

**Class color map:**
```javascript
const CLASS_COLORS = {
  fighter: '#C0392B', wizard: '#2471A3', rogue: '#7F8C8D',
  barbarian: '#884EA0', paladin: '#F0B27A', bard: '#1ABC9C',
  cleric: '#F4D03F', monk: '#A9CCE3', warlock: '#8E44AD',
  druid: '#58D68D', sorcerer: '#E74C3C', ranger: '#27AE60'
};
```

### 3b. Class detail panel

Show below the grid when a class is selected:
- Class name, hit die, primary abilities, saving throws, caster type — as stat blocks
- Class description text (italic, left-bordered)
- Full 20-level progression table from `progressionTable` array
  - Rows with `asiOrFeat: true` get class `asi-row` (gold text)
  - Rows where features contain subclass keywords get `subclass-row` (purple text)
  - Feature names are rendered as `<span class="feature-tag">` pills
  - ASI features get `<span class="feature-tag asi">` pills
  - Subclass features get `<span class="feature-tag subclass">` pills

### 3c. Bind

```javascript
bind: function bindClassStep(root, context) {
  root.querySelectorAll('.class-card').forEach(function(card) {
    card.addEventListener('click', function() {
      const id = card.dataset.classId;
      const hiddenInput = root.querySelector('[data-builder-path="class.id"]');
      if (hiddenInput) hiddenInput.value = id;
      if (context && typeof context.onSetField === 'function') {
        context.onSetField(['class', 'id'], id);
      }
      root.querySelectorAll('.class-card').forEach(function(c) { c.classList.remove('selected'); });
      card.classList.add('selected');
      showClassDetailPanel(root, id);
    });
  });
  // Auto-show for already-selected class
  const draft = context && context.draft || {};
  const currentId = draft.class && draft.class.id;
  if (currentId) showClassDetailPanel(root, currentId);
}
```

---

## SUB-TASK 4 — Abilities Step
### File: `client/static/js/character/builder/steps/step_abilities.js` (REWRITE)

Preserve all existing logic (point buy cost table, standard array, roll function, `wireButtons`). Add the new visual layer on top.

### 4a. Render changes

Replace the current plain `<div class="builder-ability-grid">` with the new 6-card grid:

```javascript
// For each ability key, render an ability-block card:
function renderAbilityCard(key, value, mode, pointBuyRemaining) {
  const mod = abilityModifier(value);
  const cost = pointBuyCost(value);
  const modStr = mod >= 0 ? '+' + mod : String(mod);
  const modClass = mod > 0 ? 'pos' : mod < 0 ? 'neg' : '';
  const canIncrease = mode === 'point_buy'
    ? value < 15 && pointBuyRemaining >= (pointBuyCost(value + 1) - cost)
    : value < 20;
  const canDecrease = mode === 'point_buy' ? value > 8 : value > 3;

  return [
    '<div class="ability-block' + (value >= 14 ? ' boosted' : '') + '">',
    '<div class="ability-label">' + key.toUpperCase() + '</div>',
    '<div class="ability-mod ' + modClass + '">' + escHtml(modStr) + '</div>',
    '<div class="ability-score-box">',
    '<button class="ability-btn" data-ability-key="' + key + '" data-ability-delta="-1"' + (!canDecrease ? ' disabled' : '') + '>−</button>',
    '<span class="ability-score-val">' + escHtml(value) + '</span>',
    '<button class="ability-btn" data-ability-key="' + key + '" data-ability-delta="1"' + (!canIncrease ? ' disabled' : '') + '>+</button>',
    '</div>',
    mode === 'point_buy' ? '<div class="ability-cost-indicator">' + cost + 'pt</div>' : '',
    '</div>',
  ].join('');
}
```

The 6 cards go inside `<div class="ability-grid-6">` inside `<div class="ability-layout">`.

### 4b. Point Buy Budget sidebar

Add a budget panel to the right side of `ability-layout`:

```javascript
function renderPointBuyBudget(remaining) {
  const pct = Math.max(0, (remaining / 27) * 100);
  const barColor = pct > 50 ? 'var(--cb-teal)' : pct > 20 ? 'var(--cb-gold)' : '#E74C3C';
  return [
    '<div class="point-buy-budget" id="builder-pb-budget"',
    (remaining <= 0 ? ' style="border-color:rgba(231,76,60,0.4)"' : ''),
    '>',
    '<div class="pb-points">' + remaining + '<span> pts</span></div>',
    '<div class="pb-label">Points Remaining</div>',
    '<div class="pb-bar"><div class="pb-bar-fill" style="width:' + pct + '%;background:' + barColor + '"></div></div>',
    '</div>',
  ].join('');
}
```

### 4c. Class tip panel

Add `renderClassTip(classId)` that reads the selected class from the draft and shows build tips. Use this data object inside the module:

```javascript
const CLASS_BUILD_TIPS = {
  fighter:   { p: 'Strength',     pr: 'weapon attacks & Athletics',      s: 'Constitution', sr: 'HP and Concentration saves',          d: 'Intelligence',  dr: 'Rarely used by Fighters'          },
  wizard:    { p: 'Intelligence', pr: 'spell save DC & attack bonus',    s: 'Constitution', sr: 'Concentration saving throws',         d: 'Strength',      dr: 'Wizards avoid melee entirely'     },
  rogue:     { p: 'Dexterity',    pr: 'attacks, stealth, and AC',        s: 'Constitution', sr: 'HP for survivability',                d: 'Strength',      dr: 'DEX rogues ignore STR entirely'   },
  barbarian: { p: 'Strength',     pr: 'weapon attacks and grappling',    s: 'Constitution', sr: 'HP, Rage defense, Concentration',     d: 'Intelligence',  dr: 'Barbarians are primal, not clever'},
  paladin:   { p: 'Strength',     pr: 'weapon attacks and Athletics',    s: 'Charisma',     sr: 'Aura of Protection + spells',         d: 'Intelligence',  dr: 'Safe to keep at 10 or below'     },
  bard:      { p: 'Charisma',     pr: 'Bardic Inspiration, spells, social', s: 'Dexterity', sr: 'AC, initiative, and DEX saves',      d: 'Strength',      dr: 'Bards rarely pick up weapons'     },
  cleric:    { p: 'Wisdom',       pr: 'spell save DC, Channel Divinity', s: 'Constitution', sr: 'Concentration spells and HP',         d: 'Strength',      dr: 'Unless you took Protector Order'  },
  monk:      { p: 'Dexterity',    pr: 'AC, attacks, and initiative',     s: 'Wisdom',       sr: 'Unarmored Defense AC + saves',        d: 'Strength',      dr: 'Monks use DEX for everything STR' },
  warlock:   { p: 'Charisma',     pr: 'Eldritch Blast, spells',          s: 'Constitution', sr: 'Concentration and HP',                d: 'Strength',      dr: 'You have Eldritch Blast at range'  },
  druid:     { p: 'Wisdom',       pr: 'spell save DC, attack, Wild Shape',s: 'Constitution',sr: 'Concentration spells',                d: 'Strength',      dr: 'You can Wild Shape for physical tasks'},
  sorcerer:  { p: 'Charisma',     pr: 'spell save DC and attack bonus',  s: 'Constitution', sr: 'Concentration — critical for Metamagic', d: 'Strength',   dr: 'Never need to be near an enemy'   },
  ranger:    { p: 'Dexterity',    pr: 'attacks, AC, and stealth',        s: 'Wisdom',       sr: 'spell save DC and Nature/Survival',   d: 'Intelligence',  dr: 'Rarely used in Ranger gameplay'   },
};
```

### 4d. Method tab bar

Replace the `<select data-builder-path="abilityGenerationMode">` with styled tabs:

```javascript
function renderMethodTabs(mode) {
  return [
    '<div class="ability-method-tabs">',
    ['standard_array', 'Standard Array', 'point_buy', 'Point Buy', 'roll', 'Roll (4d6)', 'manual', 'Manual Entry']
      .reduce(function(arr, _, i, src) {
        if (i % 2 === 0) arr.push([src[i], src[i+1]]);
        return arr;
      }, [])
      .map(function(pair) {
        return '<button class="method-tab' + (mode === pair[0] ? ' active' : '') + '" data-method="' + pair[0] + '">' + pair[1] + '</button>';
      }).join(''),
    '</div>',
    // Keep the hidden select for state compatibility:
    '<select data-builder-path="abilityGenerationMode" style="display:none">',
    ['manual','standard_array','point_buy','roll'].map(function(m) {
      return '<option value="' + m + '"' + (mode === m ? ' selected' : '') + '>' + m + '</option>';
    }).join(''),
    '</select>',
  ].join('');
}
```

Wire the tab buttons in `bind` to update both the hidden select (for state) and re-render the ability cards.

---

## SUB-TASK 5 — Origins Step
### File: `client/static/js/character/builder/steps/step_origins.js` (REWRITE)

Replace the existing free-text background input with a card grid. The backgrounds data comes from `/api/rules/backgrounds` if it exists — gracefully fall back to a hardcoded list if the endpoint isn't available yet.

**Hardcoded fallback data inside the module:**

```javascript
const BACKGROUND_FALLBACK = [
  { id: 'soldier',    name: 'Soldier',    icon: '🪖', skills: ['Athletics', 'Intimidation'],      tool: "Gaming Set",                feat: 'Savage Attacker', gold: 50  },
  { id: 'criminal',   name: 'Criminal',   icon: '🗝️', skills: ['Sleight of Hand', 'Stealth'],      tool: "Thieves' Tools",            feat: 'Alert',           gold: 50  },
  { id: 'sage',       name: 'Sage',       icon: '📚', skills: ['Arcana', 'History'],              tool: "Calligrapher's Supplies",   feat: 'Magic Initiate',  gold: 50  },
  { id: 'acolyte',    name: 'Acolyte',    icon: '⛪', skills: ['Insight', 'Religion'],            tool: "Calligrapher's Supplies",   feat: 'Magic Initiate (Divine)', gold: 50 },
  { id: 'noble',      name: 'Noble',      icon: '👑', skills: ['History', 'Persuasion'],          tool: 'Musical Instrument',        feat: 'Skilled',         gold: 150 },
  { id: 'hermit',     name: 'Hermit',     icon: '🏔️', skills: ['Medicine', 'Religion'],           tool: 'Herbalism Kit',             feat: 'Magic Initiate (Primal)', gold: 25 },
  { id: 'entertainer',name: 'Entertainer',icon: '🎭', skills: ['Acrobatics', 'Performance'],      tool: 'Musical Instrument',        feat: 'Tavern Brawler',  gold: 50  },
  { id: 'farmer',     name: 'Farmer',     icon: '🌾', skills: ['Animal Handling', 'Nature'],      tool: "Carpenter's Tools",         feat: 'Tough',           gold: 30  },
  { id: 'guard',      name: 'Guard',      icon: '🛡️', skills: ['Athletics', 'Perception'],        tool: 'Musical Instrument',        feat: 'Alert',           gold: 50  },
  { id: 'sailor',     name: 'Sailor',     icon: '⚓', skills: ['Acrobatics', 'Perception'],       tool: "Navigator's Tools",         feat: 'Tavern Brawler',  gold: 50  },
  { id: 'merchant',   name: 'Merchant',   icon: '💰', skills: ['Animal Handling', 'Persuasion'],  tool: "Navigator's Tools",         feat: 'Lucky',           gold: 100 },
  { id: 'wayfarer',   name: 'Wayfarer',   icon: '🎒', skills: ['Insight', 'Stealth'],             tool: "Thieves' Tools",            feat: 'Lucky',           gold: 16  },
  { id: 'artisan',    name: 'Artisan',    icon: '🔨', skills: ['Investigation', 'Persuasion'],    tool: "Artisan's Tools",           feat: 'Crafter',         gold: 50  },
  { id: 'charlatan',  name: 'Charlatan',  icon: '🎪', skills: ['Deception', 'Sleight of Hand'],   tool: 'Forgery Kit',               feat: 'Skilled',         gold: 50  },
  { id: 'scribe',     name: 'Scribe',     icon: '📜', skills: ['Investigation', 'Perception'],    tool: "Calligrapher's Supplies",   feat: 'Skilled',         gold: 40  },
  { id: 'guide',      name: 'Guide',      icon: '🗺️', skills: ['Stealth', 'Survival'],            tool: "Cartographer's Tools",      feat: 'Magic Initiate (Primal)', gold: 50 },
];
```

Render each background as a species-card styled card (reuse the same CSS classes):

```javascript
function renderBackgroundCard(bg, selectedId) {
  const isSelected = bg.id === selectedId;
  return [
    '<div class="species-card' + (isSelected ? ' selected' : '') + '" data-background-id="' + bg.id + '">',
    '<div class="sc-selected-check">✓</div>',
    '<div class="sc-icon" style="font-size:1.4rem;background:rgba(201,168,76,0.06);border-color:rgba(201,168,76,0.15)">' + bg.icon + '</div>',
    '<div class="sc-name">' + escHtml(bg.name) + '</div>',
    '<div class="sc-badges">',
    '<span class="sc-badge" style="background:rgba(201,168,76,0.08);border-color:rgba(201,168,76,0.2);color:var(--cb-gold-dim)">⭐ ' + escHtml(bg.feat) + '</span>',
    '</div>',
    '<div class="sc-traits">',
    bg.skills.map(function(s) { return '<div class="sc-trait">' + escHtml(s) + '</div>'; }).join(''),
    '<div class="sc-trait" style="color:var(--cb-text-dim)">' + escHtml(bg.tool) + '</div>',
    '<div class="sc-trait" style="color:var(--cb-gold-dim)">' + bg.gold + ' GP</div>',
    '</div>',
    '</div>',
  ].join('');
}
```

In `bind`, wire card clicks to call `context.onSetField(['origins', 'backgroundId'], id)` and also auto-fill skill proficiencies: `context.onSetField(['origins', 'skillProficiencies'], bg.skills)`.

Also keep the existing language/lineage text inputs below the card grid — don't remove them.

---

## SUB-TASK 6 — Review Step
### File: `client/static/js/character/builder/steps/step_review.js` (REWRITE)

Replace the existing plain-text grid with a complete computed stat block matching the preview's `#statblock` section.

### 6a. Stat computation functions (pure JS, no external deps)

Add these helper functions inside the IIFE:

```javascript
function abilityMod(score) {
  return Math.floor((safeInt(score, 10) - 10) / 2);
}

function profBonus(level) {
  return 2 + Math.floor((Math.max(1, safeInt(level, 1)) - 1) / 4);
}

function fmtMod(mod) {
  return mod >= 0 ? '+' + mod : String(mod);
}

function getClassRow(classId) {
  var api = global.CharacterBuilderAPI;
  if (!api || typeof api.getCachedCatalog !== 'function') return null;
  var catalog = api.getCachedCatalog();
  var classes = Array.isArray(catalog && catalog.classes) ? catalog.classes : [];
  return classes.find(function(c) { return c.id === classId; }) || null;
}

function getSpeciesRow(speciesId) {
  var api = global.CharacterBuilderAPI;
  if (!api || typeof api.getCachedCatalog !== 'function') return null;
  var catalog = api.getCachedCatalog();
  var species = Array.isArray(catalog && catalog.species) ? catalog.species : [];
  return species.find(function(s) { return s.id === speciesId; }) || null;
}

function computeStats(draft) {
  var abilities = (draft.abilities && typeof draft.abilities === 'object') ? draft.abilities : {};
  var classData = (draft.class && typeof draft.class === 'object') ? draft.class : {};
  var progression = (draft.progression && typeof draft.progression === 'object') ? draft.progression : {};
  var speciesData = (draft.species && typeof draft.species === 'object') ? draft.species : {};

  var classId = String(classData.id || '').trim().toLowerCase();
  var speciesId = String(speciesData.id || '').trim().toLowerCase();
  var level = safeInt(progression.level, 1);
  var prof = profBonus(level);

  var classRow = getClassRow(classId);
  var speciesRow = getSpeciesRow(speciesId);

  var hitDie = (classRow && classRow.hitDie) ? safeInt(classRow.hitDie, 8) : 8;
  var conMod = abilityMod(abilities.con);
  var dexMod = abilityMod(abilities.dex);
  var wisMod = abilityMod(abilities.wis);

  // AC calculation with special class rules
  var ac = 10 + dexMod;
  if (classId === 'barbarian') ac = 10 + dexMod + abilityMod(abilities.con);
  if (classId === 'monk') ac = 10 + dexMod + wisMod;

  // HP: max at level 1, average for subsequent levels
  var maxHp = hitDie + conMod + (Math.max(0, level - 1) * (Math.floor(hitDie / 2) + 1 + conMod));

  // Speed from species
  var speed = speciesRow && speciesRow.movement ? safeInt(speciesRow.movement.walk, 30) : 30;

  // Darkvision
  var darkvision = speciesRow && speciesRow.senses ? safeInt(speciesRow.senses.darkvision, 0) : 0;

  // Saving throws
  var classThrows = classRow && Array.isArray(classRow.savingThrows) ? classRow.savingThrows : [];
  var saves = {};
  ['str', 'dex', 'con', 'int', 'wis', 'cha'].forEach(function(k) {
    var mod = abilityMod(abilities[k]);
    saves[k] = classThrows.includes(k) ? mod + prof : mod;
  });

  // Spellcasting
  var spellAbility = classRow ? classRow.spellcastingAbility : null;
  var spellMod = spellAbility ? abilityMod(abilities[spellAbility]) : 0;
  var spellDC = spellAbility ? (8 + prof + spellMod) : null;
  var spellAtk = spellAbility ? (prof + spellMod) : null;

  // Spell slots at current level
  var spellSlots = {};
  if (classRow && classRow.spellSlots && classRow.spellSlots[String(level)]) {
    spellSlots = classRow.spellSlots[String(level)];
  }

  // Passive perception
  var passivePerc = 10 + wisMod + prof; // assume perception proficiency

  // Initiative
  var initiative = dexMod;

  return {
    level: level, prof: prof, ac: ac, maxHp: maxHp, speed: speed,
    initiative: initiative, passivePerc: passivePerc,
    saves: saves, classThrows: classThrows,
    spellAbility: spellAbility, spellDC: spellDC, spellAtk: spellAtk, spellSlots: spellSlots,
    darkvision: darkvision, hitDie: hitDie,
    classId: classId, speciesId: speciesId,
    classRow: classRow, speciesRow: speciesRow
  };
}
```

### 6b. Render the stat block

The render function uses `computeStats(draft)` to build the HTML. Structure:

```
1. Banner (portrait, name, subtitle: "Species Class · Level N · Background")
2. Spell bar (only if spellDC is not null) — Spell Save DC | Spell Attack | Casting Ability
3. Combat bar — 6 stats: AC | HP | Initiative | Speed | Passive Perc. | Proficiency
4. Body — 3 columns:
   Left:   6 ability score blocks (label, modifier large, raw score small)
   Center: 6 saving throws with proficiency dots
   Right:  Level 1 class features list
5. Spell slot tracker (only if spellSlots has any entries)
6. Validation panel (green "Ready to Save" or list of issues)
```

Refer to the preview HTML for the exact class names. The stat block must look identical to the preview's Screen 6.

---

## SUB-TASK 7 — Builder Shell Progress Bar
### File: `client/static/js/character/builder/builder_shell.js` (PARTIAL EDIT)

Find the section that renders step pills / navigation. Replace the existing step pill rendering with the new progress track from the preview.

**Find this block** (approximate — read the file first):
```javascript
// Something like:
'<div class="builder-steps">' + steps.map(...).join('') + '</div>'
```

**Replace with:**
```javascript
function renderStepProgress(steps, currentStepId) {
  const currentIndex = steps.findIndex(function(s) { return s.id === currentStepId; });
  return [
    '<div class="step-track">',
    steps.map(function(step, i) {
      const isDone = i < currentIndex;
      const isActive = i === currentIndex;
      const dotClass = 'step-dot' + (isDone ? ' done' : isActive ? ' active' : '');
      return [
        '<div class="step-item">',
        '<button class="' + dotClass + '" data-step-id="' + escHtml(step.id) + '">',
        isDone ? '' : String(i + 1),
        '<span class="step-label">' + escHtml(step.label || step.id) + '</span>',
        '</button>',
        i < steps.length - 1 ? '<div class="step-connector' + (isDone ? ' done' : '') + '"></div>' : '',
        '</div>',
      ].join('');
    }).join(''),
    '</div>',
    '<div class="step-progress-bar" style="width:' + (currentIndex / Math.max(1, steps.length - 1) * 100) + '%"></div>',
  ].join('');
}
```

Wire the step dot buttons to navigate to that step when clicked (use the existing router's navigation method).

---

## SUB-TASK 8 — Tooltips Module
### File: `client/static/js/character/builder/builder_tooltips.js` (CREATE NEW)

Create this file and load it in `client/templates/play.html` (add a `<script src="/static/js/character/builder/builder_tooltips.js">` tag near the other builder script tags).

```javascript
(function initBuilderTooltips(global) {
  'use strict';

  var TOOLTIPS = {
    'species': {
      title: 'What is a Species?',
      body: 'Your species (called "race" in older editions) determines your character\'s ancestry. It grants permanent traits, affects your speed and senses, and shapes your innate abilities. Species traits don\'t change as you level up.'
    },
    'class': {
      title: 'What is a Class?',
      body: 'Your class is your character\'s profession and primary power source. A Fighter masters weapons; a Wizard commands arcane magic; a Rogue excels at stealth and precision. Your class determines which abilities you gain as you level up, your hit points, and whether you can cast spells.'
    },
    'abilities': {
      title: 'What are Ability Scores?',
      body: 'Six scores — Strength, Dexterity, Constitution, Intelligence, Wisdom, and Charisma — measure your natural aptitudes. Each score generates a modifier: (score − 10) ÷ 2, rounded down. STR 15 = +2 modifier. Modifiers are what actually affect your dice rolls.'
    },
    'standard-array': {
      title: 'Standard Array',
      body: 'The standard array is 15, 14, 13, 12, 10, 8 — assign these six values to your six abilities in any order you choose. Recommended for new players because it creates a fair, balanced character without luck.'
    },
    'point-buy': {
      title: 'Point Buy',
      body: 'You have 27 points to spend. Every ability starts at 8 and costs points to raise. Maximum score before species bonuses is 15. Scores of 14 and 15 cost extra: 14 costs 7 total, 15 costs 9 total. Great for precise character optimization.'
    },
    'hit-die': {
      title: 'Hit Die',
      body: 'Your hit die determines hit points per level. At 1st level you get the maximum value. At later levels you roll it (or take the average) and add your Constitution modifier. Barbarians have d12 (most HP), Wizards have d6 (fewest HP).'
    },
    'saving-throws': {
      title: 'Saving Throws',
      body: 'Saving throws represent your ability to resist effects like fireballs, charm spells, and pit traps. Each class is proficient in two saving throw types, adding their proficiency bonus to those rolls. Fighters save with Strength and Constitution; Wizards with Intelligence and Wisdom.'
    },
    'subclass': {
      title: 'What is a Subclass?',
      body: 'At 3rd level (or 1st for Warlocks), you choose a subclass — a specialization within your class. A Fighter chooses between Battlemaster (tactical maneuvers), Champion (raw power), and Eldritch Knight (fighter + wizard spells). Subclasses dramatically shape your playstyle.'
    },
    'asi': {
      title: 'Ability Score Improvement',
      body: 'At certain levels (4, 8, 12, 16, 19 for most classes), you can raise one ability score by 2, raise two different scores by 1 each, or take a Feat instead. Feats are powerful special abilities that can define your combat style.'
    },
    'feat': {
      title: 'What is a Feat?',
      body: 'Feats are optional special abilities taken instead of an Ability Score Improvement. Lucky gives you 3 rerolls per day. Great Weapon Master lets you trade −5 to hit for +10 damage. Sentinel stops fleeing enemies. Feats are powerful choices that define your style.'
    },
    'proficiency-bonus': {
      title: 'Proficiency Bonus',
      body: 'Starts at +2 at level 1 and increases to +6 at level 17. Added to: attack rolls with weapons you\'re proficient with, spell attack rolls, saving throws your class is proficient in, and ability checks using skills or tools you\'re proficient with.'
    },
    'spellcasting': {
      title: 'How does Spellcasting work?',
      body: 'Spell casters use a spellcasting ability (INT for Wizards, WIS for Druids/Clerics, CHA for Bards/Sorcerers/Warlocks/Paladins). Spell Save DC = 8 + proficiency + casting modifier. Spell Attack Bonus = proficiency + casting modifier. Higher ability scores make your spells harder to resist.'
    },
    'background': {
      title: 'What is a Background?',
      body: 'Your background defines who your character was before becoming an adventurer. Each background grants two skill proficiencies, one tool proficiency, a starting language, an Origin feat, and starting equipment and gold. The Origin feat is one of the most powerful benefits — choose a background that grants a feat that fits your build.'
    },
    'rage': {
      title: 'What is Rage?',
      body: 'Rage is the Barbarian\'s signature feature. As a Bonus Action, you enter a Rage that lasts 1 minute: +2 to STR damage rolls (scales to +4 at 16), resistance to bludgeoning/piercing/slashing damage, and you can\'t cast or concentrate on spells. Number of uses scales from 2 at level 1 to unlimited at level 20.'
    },
    'sneak-attack': {
      title: 'What is Sneak Attack?',
      body: 'The Rogue\'s signature burst damage. Once per turn, if you hit a creature with a finesse or ranged weapon and you either have Advantage on the roll OR an ally is adjacent to the target, you deal extra damage. Starts at 1d6 at level 1 and scales to 10d6 at level 19. This is why Rogues are terrifying.'
    },
    'bardic-inspiration': {
      title: 'What is Bardic Inspiration?',
      body: 'As a Bonus Action, grant a creature within 60 ft a Bardic Inspiration die. They can add it to any ability check, attack roll, or saving throw in the next 10 minutes. Starts as a d6 at level 1, scales to a d12 at level 15. Uses per long rest = your CHA modifier. At level 5, you recover uses on short rests too.'
    },
  };

  function showTooltip(key) {
    var tip = TOOLTIPS[key];
    if (!tip) return;
    closeTooltip();
    var overlay = document.createElement('div');
    overlay.id = 'builder-tooltip-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center';
    overlay.onclick = closeTooltip;
    var panel = document.createElement('div');
    panel.style.cssText = 'background:#1a2028;border:1px solid rgba(201,168,76,0.4);border-radius:16px;padding:24px;max-width:400px;margin:20px;position:relative';
    panel.onclick = function(e) { e.stopPropagation(); };
    panel.innerHTML = '<div style="font-family:\'Cinzel\',serif;font-size:1rem;color:#E8C97A;margin-bottom:10px;padding-right:24px">' + escHtml(tip.title) + '</div>'
      + '<div style="font-size:0.82rem;color:#a89f8e;line-height:1.75">' + escHtml(tip.body) + '</div>'
      + '<button onclick="window.BuilderTooltips.close()" style="position:absolute;top:12px;right:14px;background:none;border:none;color:#6b6258;font-size:1.3rem;cursor:pointer;line-height:1">×</button>';
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
  }

  function closeTooltip() {
    var el = document.getElementById('builder-tooltip-overlay');
    if (el) el.remove();
  }

  function escHtml(v) {
    return String(v || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  global.BuilderTooltips = { show: showTooltip, close: closeTooltip, TOOLTIPS: TOOLTIPS };
})(window);
```

In each step module, add tooltip buttons next to section labels:
```javascript
// Pattern to use in any step render function:
'<label>Species <button class="help-btn" onclick="window.BuilderTooltips && window.BuilderTooltips.show(\'species\')">?</button></label>'
```

---

## SUB-TASK 9 — Load CSS in HTML template
### File: `client/templates/play.html` (EDIT)

Find where CSS is loaded (look for `<link rel="stylesheet"` tags). Add the new stylesheet:

```html
<link rel="stylesheet" href="/static/css/character-builder.css">
```

Also find where the character builder JS files are loaded and add the tooltips module:

```html
<script src="/static/js/character/builder/builder_tooltips.js"></script>
```

---

## TESTING CHECKLIST

After completing all sub-tasks, verify these manually in a browser:

**CSS**
- [ ] `character-builder.css` loads without 404
- [ ] No CSS variables conflict with `session-theme.css` (check DevTools for overridden variables)
- [ ] Dark background renders correctly (check both themes if applicable)

**Species Step**
- [ ] 9+ species cards render in a responsive grid
- [ ] Clicking a card selects it (gold border, ✓ check)
- [ ] Species detail panel appears below with all traits
- [ ] Darkvision badge only appears on species that have it
- [ ] Roadmap toggle works

**Class Step**
- [ ] 12 class cards render
- [ ] Each class has the correct color accent
- [ ] Spellcaster badges show correctly (Full/Half/Pact/nothing)
- [ ] Clicking a class shows the 20-level progression table
- [ ] ASI rows are gold, subclass rows are purple

**Abilities Step**
- [ ] 4 method tabs render and are clickable
- [ ] Point Buy: + and − buttons work, budget tracker updates
- [ ] Standard Array button fills in 15,14,13,12,10,8
- [ ] Roll button generates random scores
- [ ] Class tip panel shows for the currently selected class

**Origins Step**
- [ ] 12+ background cards render
- [ ] Clicking a card selects it and fills backgroundId in state

**Review Step**
- [ ] Stat block renders with AC, HP, initiative computed from actual choices
- [ ] Spell section only shows for spellcasting classes
- [ ] Darkvision appears in saves section when species has it
- [ ] "Ready to Save" shows when required fields are filled

**Run existing tests:**
```bash
python -m pytest tests/test_species_system_ui.py tests/test_class_feature_system_ui.py tests/test_character_native_foundation.py -v
```
All should still pass. The frontend changes don't touch Python, but run tests to confirm nothing was accidentally modified.

---

## NOTES FOR CLAUDE CODE

- **Work file by file.** Don't try to do all 9 sub-tasks in one pass.
- **Read before writing.** Every file has existing logic that must be preserved (especially state management and `data-builder-path` attributes).
- **The hidden inputs are load-bearing.** `data-builder-path="species.id"` and `data-builder-path="class.id"` are how the existing state system reads values. Never remove them — just hide them with `style="display:none"` if needed.
- **CSS variables:** Prefix all new variables `--cb-` to avoid any collision with existing theme variables.
- **The preview file is your ground truth.** If in doubt about any visual detail, look at `character-builder-preview.html`. Every class name, every color, every animation is already designed and working there.
- **Don't touch server Python files** in this task. That's a separate stage.
