"""Behavioural tests for the Customize Top 5 Quick Actions picker filter.

These exercise the real JS via node (mirrors the pattern used by
test_quick_action_spell_upcast_and_bar.py / test_castable_spell_rows.py)
rather than only asserting on source text, since the bug was a runtime
data-leak (garbage entries reaching the picker), not a missing string.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_node(script: str):
    return json.loads(subprocess.check_output(["node", "-e", script], cwd=ROOT, text=True, timeout=30))


# Shared fixture: a fake ActionsTab model + fake spell source that reproduces
# every garbage pattern reported in the bug (headings, passives, duplicate
# spell rows, raw imported text, plus the real playable actions that must
# still appear).
FIXTURE = r"""
global.window = global;
require('./client/static/js/character/tabs/actions_tab.js');
const sel = require('./client/static/js/character/combat_quick_selectors.js');

window.ActionsTab = {
  buildQuickActionModel: function () {
    return {
      primaryActions: [],
      bonusActions: [],
      reactions: [],
      passives: [],
      resources: [],
      _allActions: [
        { id: 'thunder-mage-quarterstaff', name: 'Thunder Mage Quarterstaff', source: 'weapon', quickBarKind: 'attack', quickBarLane: 'action' },
        { id: 'spellcasting', name: 'Spellcasting', source: 'feature-fallback', quickBarKind: 'use', quickBarLane: 'action' },
        { id: 'metamagic', name: 'Metamagic', source: 'feature-fallback', quickBarKind: 'use', quickBarLane: 'action' },
        { id: 'subclass-feature', name: 'Subclass Feature', source: 'feature-fallback', quickBarKind: 'use', quickBarLane: 'action' },
        { id: 'darkvision', name: 'Darkvision', source: 'native_action', quickBarKind: 'passive', quickBarLane: 'action' },
        { id: 'imported-text', name: 'Imported Note', source: 'feature-fallback', quickBarKind: 'use', quickBarLane: 'action' },
        { id: 'font-of-magic', name: 'Font of Magic: Convert Sorcery Points', source: 'native_action', quickBarKind: 'use', quickBarLane: 'action', quickBarResourceState: { remaining: 2, max: 5 } },
        { id: 'second-wind', name: 'Second Wind', source: 'native_action', quickBarKind: 'use', quickBarLane: 'bonus', quickBarResourceState: { remaining: 1, max: 1 } },
      ],
    };
  },
};
global._getCombatQuickSpells = function () {
  return [
    { id: 'fire-bolt', name: 'Fire Bolt', level: 0, source: 'class' },
    { id: 'scorching-ray-1', name: 'Scorching Ray', level: 3, source: 'class' },
    { id: 'scorching-ray-2', name: 'Scorching Ray', level: 3, source: 'class' },
    { id: '5th-level-spells', name: '5th-Level Spells', source: 'class' },
    { id: '7th-level-spells', name: '7th-Level Spells', source: 'class' },
    { id: 'chain-lightning-class', name: 'Chain Lightning', level: 6, source: 'class', sourceType: 'class' },
    { id: 'chain-lightning-item', name: 'Chain Lightning', level: 6, source: 'item', sourceType: 'item', itemName: 'Thunder Mage Quarterstaff' },
  ];
};
global.getCombatQuickBarRuntime = function () { return { charSheet: {}, combat: { active: false } }; };
"""


def test_customize_top_5_excludes_headings_passives_and_imported_text_blocks():
    rows = _run_node(FIXTURE + """
const candidates = sel.buildQuickActionCandidates();
console.log(JSON.stringify(candidates.map(c => c.name)));
""")
    forbidden = [
        'Spellcasting', 'Metamagic', 'Subclass Feature', 'Darkvision',
        'Imported Note', '5th-Level Spells', '7th-Level Spells',
    ]
    for name in forbidden:
        assert name not in rows, f"{name!r} must never be selectable in Customize Top 5"


def test_customize_top_5_includes_real_playable_actions():
    rows = _run_node(FIXTURE + """
const candidates = sel.buildQuickActionCandidates();
console.log(JSON.stringify(candidates.map(c => c.name)));
""")
    for name in ['Thunder Mage Quarterstaff', 'Fire Bolt', 'Scorching Ray', 'Font of Magic: Convert Sorcery Points']:
        assert name in rows, f"{name!r} should be a valid Quick Action candidate"


def test_customize_top_5_dedupes_duplicate_scorching_ray_rows():
    rows = _run_node(FIXTURE + """
const candidates = sel.buildQuickActionCandidates();
const scorching = candidates.filter(c => c.name === 'Scorching Ray');
console.log(JSON.stringify(scorching.length));
""")
    assert rows == 1


def test_customize_top_5_preserves_source_variants_that_behave_differently():
    rows = _run_node(FIXTURE + """
const candidates = sel.buildQuickActionCandidates();
const chain = candidates.filter(c => c.name === 'Chain Lightning').map(c => c.sourceType);
console.log(JSON.stringify(chain.sort()));
""")
    assert sorted(rows) == ['class', 'item']


def test_is_playable_quick_action_rejects_known_garbage_shapes():
    rows = _run_node("""
global.window = global;
const sel = require('./client/static/js/character/combat_quick_selectors.js');
const cases = [
  { id: 'a', name: '5th-Level Spells', quickBarType: 'spell' },
  { id: 'b', name: 'Spellcasting', quickBarKind: 'use' },
  { id: 'c', name: 'Metamagic', quickBarKind: 'use' },
  { id: 'd', name: 'Subclass Feature', quickBarKind: 'use' },
  { id: 'e', name: 'Some Passive', quickBarKind: 'passive' },
  { id: 'f', name: 'Imported text', quickBarKind: 'use', source: 'feature-fallback' },
  { id: '', name: '' },
];
console.log(JSON.stringify(cases.map(c => sel.isPlayableQuickAction(c))));
""")
    assert rows == [False] * 7


def test_is_playable_quick_action_accepts_real_actions():
    rows = _run_node("""
global.window = global;
const sel = require('./client/static/js/character/combat_quick_selectors.js');
const cases = [
  { id: 'fire-bolt', name: 'Fire Bolt', quickBarType: 'spell' },
  { id: 'thunder-mage-quarterstaff', name: 'Thunder Mage Quarterstaff', quickBarKind: 'attack', source: 'weapon' },
  { id: 'font-of-magic', name: 'Font of Magic: Convert Sorcery Points', quickBarKind: 'use', source: 'native_action' },
];
console.log(JSON.stringify(cases.map(c => sel.isPlayableQuickAction(c))));
""")
    assert rows == [True, True, True]


def test_toggle_quick_pick_cannot_exceed_five_but_allows_unselecting():
    rows = _run_node("""
global.window = global;
global.localStorage = (function () {
  const store = {};
  return {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; },
  };
})();
global.getCombatQuickBarRuntime = function () { return { charSheet: {}, combat: { active: false } }; };
const sel = require('./client/static/js/character/combat_quick_selectors.js');
['a', 'b', 'c', 'd', 'e'].forEach(id => sel.toggleQuickPick('action', { id }));
let picks = sel.readQuickPicks();
const afterFive = picks.length;
sel.toggleQuickPick('action', { id: 'f' });
picks = sel.readQuickPicks();
const afterSixthAttempt = picks.length;
const sixthRejected = !picks.some(p => p.endsWith(':f'));
sel.toggleQuickPick('action', { id: 'a' });
picks = sel.readQuickPicks();
const afterUnselect = picks.length;
console.log(JSON.stringify({ afterFive, afterSixthAttempt, sixthRejected, afterUnselect }));
""")
    assert rows['afterFive'] == 5
    assert rows['afterSixthAttempt'] == 5
    assert rows['sixthRejected'] is True
    assert rows['afterUnselect'] == 4


def test_invalid_saved_pick_is_preserved_and_warned_not_thrown():
    rows = _run_node("""
global.window = global;
window.ActionsTab = {
  buildQuickActionModel: function () {
    return { primaryActions: [], bonusActions: [], reactions: [], passives: [], resources: [], _allActions: [
      { id: 'real-attack', name: 'Real Attack', source: 'weapon', quickBarKind: 'attack', quickBarLane: 'action' },
    ] };
  },
};
global._getCombatQuickSpells = function () { return []; };
global.localStorage = (function () {
  const store = {};
  return {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; },
  };
})();
global.getCombatQuickBarRuntime = function () { return { charSheet: {}, combat: { active: false } }; };
const sel = require('./client/static/js/character/combat_quick_selectors.js');
sel.writeQuickPicks(['action:real-attack', 'action:deleted-old-feature']);
let warned = false;
const origWarn = console.warn;
console.warn = function () { warned = true; };
const model = sel.selectQuickActions({});
console.warn = origWarn;
console.log(JSON.stringify({
  warned,
  picksAfter: sel.readQuickPicks(),
  primaryNames: model.primaryActions.map(a => a.name),
  disabledNames: model.primaryActions.filter(a => a.quickBarCanUse === false).map(a => a.name),
}));
""")
    assert rows['warned'] is True
    assert rows['picksAfter'] == ['action:real-attack', 'action:deleted-old-feature']
    assert 'Real Attack' in rows['primaryNames']
    assert 'deleted old feature' in rows['disabledNames']


def test_customize_picker_deduplicates_virtual_cast_rows_and_uses_stable_spell_pick_key():
    rows = _run_node("""
global.window = global;
window.ActionsTab = { buildQuickActionModel: () => ({ primaryActions: [], bonusActions: [], reactions: [], resources: [], _allActions: [] }) };
global._getCombatQuickSpells = function () { return [
  { id: 'fireball::cast-3', name: 'Fireball', baseSpellId: 'fireball', baseLevel: 3, castLevel: 3, source: 'class' },
  { id: 'fireball::cast-4', name: 'Fireball', baseSpellId: 'fireball', baseLevel: 3, castLevel: 4, source: 'class' },
  { id: 'fireball::cast-5', name: 'Fireball', baseSpellId: 'fireball', baseLevel: 3, castLevel: 5, source: 'class' },
]; };
global.getCombatQuickBarRuntime = () => ({ charSheet: {}, combat: { active: false }, spellSlots: {3: 2, 4: 1, 5: 1}, spellSlotState: {} });
const sel = require('./client/static/js/character/combat_quick_selectors.js');
const candidates = sel.buildQuickActionCandidates();
console.log(JSON.stringify({ names: candidates.map(c => c.name), keys: candidates.map(c => c.quickBarPickKey), castLevels: candidates.map(c => c.castLevel) }));
""")
    assert rows['names'] == ['Fireball']
    assert rows['keys'] == ['spell:fireball']
    assert rows['castLevels'] == [None]


def test_quick_bar_top_spells_deduplicates_virtual_rows_and_keeps_higher_slot_available():
    rows = _run_node("""
global.window = global;
global.localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
window.ActionsTab = { buildQuickActionModel: () => ({ primaryActions: [], bonusActions: [], reactions: [], resources: [], _allActions: [] }) };
global._getCombatQuickSpells = function () { return [
  { id: 'scorching-ray::cast-2', name: 'Scorching Ray', baseSpellId: 'scorching-ray', baseLevel: 2, castLevel: 2, source: 'class' },
  { id: 'scorching-ray::cast-3', name: 'Scorching Ray', baseSpellId: 'scorching-ray', baseLevel: 2, castLevel: 3, source: 'class' },
  { id: 'scorching-ray::cast-4', name: 'Scorching Ray', baseSpellId: 'scorching-ray', baseLevel: 2, castLevel: 4, source: 'class' },
  { id: 'scorching-ray::cast-5', name: 'Scorching Ray', baseSpellId: 'scorching-ray', baseLevel: 2, castLevel: 5, source: 'class' },
]; };
global.getCombatQuickBarRuntime = () => ({ charSheet: {}, combat: { active: false }, spellSlots: {2: 3, 3: 2}, spellSlotState: {2: 3, 3: 1} });
const sel = require('./client/static/js/character/combat_quick_selectors.js');
const model = sel.selectQuickActions({});
console.log(JSON.stringify(model.topSpells.map(s => ({ name: s.name, key: s.quickBarPickKey, canUse: s.quickBarCanUse, levels: s.availableCastLevels, summary: s.quickBarSlotSummary }))));
""")
    assert len(rows) == 1
    assert rows[0]['name'] == 'Scorching Ray'
    assert rows[0]['key'] == 'spell:scorching-ray'
    assert rows[0]['canUse'] is True
    assert rows[0]['levels'] == [3]
    assert 'L2 0/3' in rows[0]['summary'] and 'L3 1/2' in rows[0]['summary']


def test_quick_spell_no_slots_is_unavailable_and_reports_no_slots():
    rows = _run_node("""
global.window = global;
global._getCombatQuickSpells = () => [];
global.getCombatQuickBarRuntime = () => ({ spellSlots: {2: 3, 3: 2}, spellSlotState: {2: 3, 3: 2} });
const sel = require('./client/static/js/character/combat_quick_selectors.js');
const spell = { id: 'scorching-ray::cast-2', name: 'Scorching Ray', baseSpellId: 'scorching-ray', baseLevel: 2, castLevel: 2, quickBarType: 'spell' };
const runtime = global.getCombatQuickBarRuntime();
console.log(JSON.stringify({ available: sel._spellAvailable(spell, runtime), summary: sel._spellSlotSummary(spell, runtime), candidate: sel._canonicalSpellDisplayCandidate(spell, runtime) }));
""")
    assert rows['available'] is False
    assert rows['summary'] == 'No slots'
    assert rows['candidate']['availableCastLevels'] == []


def test_quick_action_sources_include_rest_and_modal_slot_sync_hooks():
    bar = (ROOT / 'client/static/js/character/combat_quick_bar.js').read_text(encoding='utf-8')
    actions = (ROOT / 'client/static/js/character/combat_quick_actions.js').read_text(encoding='utf-8')
    for event in ['character:spell-state-updated', 'character:runtime-updated', 'character:resources-updated', 'character:rest-completed', 'spellSlots:updated']:
        assert event in bar
        assert event in actions
    assert 'global.refreshCombatQuickActions = refreshCombatQuickActions;' in bar
    assert 'refreshSpellModalSlots' in actions

def test_quick_pick_spell_fireball_survives_done_and_appears_in_top_spells():
    rows = _run_node("""
global.window = global;
global.localStorage = (function () { const store = {}; return { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } }; })();
window.ActionsTab = { buildQuickActionModel: () => ({ primaryActions: [], bonusActions: [], reactions: [], resources: [], _allActions: [] }) };
global._getCombatQuickSpells = () => [{ id: 'fireball', name: 'Fireball', level: 3, baseLevel: 3, source: 'class' }];
global.getCombatQuickBarRuntime = () => ({ charSheet: {}, combat: { active: false }, spellSlots: {3: 1}, spellSlotState: {} });
const sel = require('./client/static/js/character/combat_quick_selectors.js');
sel.toggleQuickPickKey('spell:fireball');
const model = sel.selectQuickActions({});
console.log(JSON.stringify({ picks: sel.readQuickPicks(), topSpells: model.topSpells.map(s => s.name) }));
""")
    assert rows['picks'] == ['spell:fireball']
    assert rows['topSpells'] == ['Fireball']


def test_old_quick_pick_fireball_cast_key_migrates_to_canonical_spell_key():
    rows = _run_node("""
global.window = global;
global.localStorage = (function () { const store = {}; return { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } }; })();
window.ActionsTab = { buildQuickActionModel: () => ({ primaryActions: [], bonusActions: [], reactions: [], resources: [], _allActions: [] }) };
global._getCombatQuickSpells = () => [{ id: 'fireball::cast-5', baseSpellId: 'fireball', name: 'Fireball', level: 3, baseLevel: 3, source: 'class' }];
global.getCombatQuickBarRuntime = () => ({ charSheet: {}, combat: { active: false }, spellSlots: {3: 1}, spellSlotState: {} });
const sel = require('./client/static/js/character/combat_quick_selectors.js');
sel.writeQuickPicks(['spell:fireball::cast-5']);
// Canonicalization of stored picks is a one-time migration that runs on
// character/combat load — NOT inside the render-time selector (which must be
// side-effect free). The selector still exposes canonical keys in-memory.
sel.migrateQuickPicks();
const model = sel.selectQuickActions({});
console.log(JSON.stringify({ picks: sel.readQuickPicks(), topSpells: model.topSpells.map(s => s.quickBarPickKey) }));
""")
    assert rows['picks'] == ['spell:fireball']
    assert rows['topSpells'] == ['spell:fireball']


def test_out_of_slot_selected_spell_remains_visible_but_disabled():
    rows = _run_node("""
global.window = global;
global.localStorage = (function () { const store = {}; return { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } }; })();
window.ActionsTab = { buildQuickActionModel: () => ({ primaryActions: [], bonusActions: [], reactions: [], resources: [], _allActions: [] }) };
global._getCombatQuickSpells = () => [{ id: 'fireball', name: 'Fireball', level: 3, baseLevel: 3, source: 'class' }];
global.getCombatQuickBarRuntime = () => ({ charSheet: {}, combat: { active: false }, spellSlots: {3: 1}, spellSlotState: {3: 1} });
const sel = require('./client/static/js/character/combat_quick_selectors.js');
sel.writeQuickPicks(['spell:fireball']);
const model = sel.selectQuickActions({});
console.log(JSON.stringify(model.topSpells.map(s => ({ name: s.name, canUse: s.quickBarCanUse, reason: s.quickBarDisabledReason }))));
""")
    assert rows == [{'name': 'Fireball', 'canUse': False, 'reason': 'No spell slots available'}]
