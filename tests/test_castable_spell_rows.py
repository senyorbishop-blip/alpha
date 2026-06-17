import json
import subprocess


def _node(script: str):
    code = "const rt=require('./client/static/js/character/spell_runtime.js');\n" + script
    out = subprocess.check_output(['node', '-e', code], text=True)
    return json.loads(out)


def test_bishop_sorcerer_19_generates_castable_rows_through_9th():
    data = _node(r'''
const character={level:19,totalLevel:19,spellSaveDc:18,spellAttack:'+10',spellSlots:[0,4,3,3,3,3,2,1,1,1]};
const known=[
 {spellId:'fireball',name:'Fireball',baseLevel:3,source:'Sorcerer',sourceType:'class',sourceVariantId:'sorcerer',usesSpellSlot:true},
 {spellId:'scorching-ray',name:'Scorching Ray',baseLevel:2,source:'Sorcerer',sourceType:'class',sourceVariantId:'sorcerer',usesSpellSlot:true},
 {spellId:'meteor-swarm',name:'Meteor Swarm',baseLevel:9,source:'Sorcerer',sourceType:'class',sourceVariantId:'sorcerer',usesSpellSlot:true},
 {spellId:'power-word-stun',name:'Power Word Stun',baseLevel:8,source:'Sorcerer',sourceType:'class',sourceVariantId:'sorcerer',usesSpellSlot:true},
 {spellId:'finger-of-death',name:'Finger of Death',baseLevel:7,source:'Sorcerer',sourceType:'class',sourceVariantId:'sorcerer',usesSpellSlot:true},
 {spellId:'chain-lightning',name:'Chain Lightning',baseLevel:6,source:'Sorcerer',sourceType:'class',sourceVariantId:'sorcerer',usesSpellSlot:true},
 {spellId:'chain-lightning',name:'Chain Lightning',baseLevel:6,source:'Thunder Mage Quarterstaff',sourceType:'item',sourceVariantId:'thunder-mage-quarterstaff',usesSpellSlot:false,usesCharges:true},
];
const built=rt.buildCastableSpellRows(character, known, []);
function rows(name){return built.rows.filter(r=>r.name===name).map(r=>({castLevel:r.castLevel,damagePreview:r.damagePreview,effectPreview:r.effectPreview,source:r.source,sourceType:r.sourceType,castResourceType:r.castResourceType,sourceVariantId:r.sourceVariantId}));}
console.log(JSON.stringify({rows:built.rows.length, fireball:rows('Fireball'), scorching:rows('Scorching Ray'), meteor:rows('Meteor Swarm'), pws:rows('Power Word Stun'), fod:rows('Finger of Death'), chain:rows('Chain Lightning')}));
''')
    assert [r['castLevel'] for r in data['fireball']] == [3,4,5,6,7,8,9]
    assert data['fireball'][0]['damagePreview'] == '8d6'
    assert data['fireball'][1]['damagePreview'] == '9d6'
    assert data['fireball'][5]['damagePreview'] == '13d6'
    assert data['fireball'][6]['damagePreview'] == '14d6'
    assert [r['castLevel'] for r in data['scorching']] == [2,3,4,5,6,7,8,9]
    assert data['scorching'][-1]['damagePreview'] == '10 rays × 2d6'
    assert data['meteor'][0]['castLevel'] == 9
    assert data['pws'][0]['castLevel'] == 8
    assert data['fod'][0]['castLevel'] == 7
    assert any(r['source'] == 'Sorcerer' and r['castResourceType'] == 'spell-slot' for r in data['chain'])
    assert any(r['source'] == 'Thunder Mage Quarterstaff' and r['castResourceType'] == 'charges' for r in data['chain'])


def test_virtual_row_cast_level_controls_shared_resolver_preview():
    data = _node(r'''
const character={level:19,spellSlots:[0,4,3,3,3,3,2,1,1,1]};
const built=rt.buildCastableSpellRows(character,[{spellId:'fireball',name:'Fireball',baseLevel:3,source:'Sorcerer',sourceType:'class',usesSpellSlot:true}],[]);
const row8=built.rows.find(r=>r.name==='Fireball'&&r.castLevel===8);
const row9=built.rows.find(r=>r.name==='Fireball'&&r.castLevel===9);
const cast8=rt.resolveSpellCast(row8.card, character, {castLevel:row8.castLevel,slotLevel:row8.slotLevel});
const cast9=rt.resolveSpellCast(row9.card, character, {castLevel:row9.castLevel,slotLevel:row9.slotLevel});
console.log(JSON.stringify({row8:row8.damagePreview,cast8:cast8.castLevel,formula8:cast8.formulaUsed,row9:row9.damagePreview,cast9:cast9.castLevel,formula9:cast9.formulaUsed}));
''')
    assert data == {'row8':'13d6','cast8':8,'formula8':'13d6','row9':'14d6','cast9':9,'formula9':'14d6'}


def test_universal_higher_level_scaling_audit_categories():
    data = _node(r'''
const character={level:19,totalLevel:19,spellcastingModifier:4,spellSaveDc:18,spellAttack:'+10',spellSlots:[0,4,3,3,3,3,2,1,1,1]};
const known=[
 {spellId:'fireball',name:'Fireball',baseLevel:3,source:'Wizard',sourceType:'class',usesSpellSlot:true},
 {spellId:'lightning-bolt',name:'Lightning Bolt',baseLevel:3,source:'Wizard',sourceType:'class',usesSpellSlot:true},
 {spellId:'scorching-ray',name:'Scorching Ray',baseLevel:2,source:'Sorcerer',sourceType:'class',usesSpellSlot:true},
 {spellId:'cure-wounds',name:'Cure Wounds',baseLevel:1,source:'Cleric',sourceType:'class',usesSpellSlot:true},
 {spellId:'counterspell',name:'Counterspell',baseLevel:3,source:'Wizard',sourceType:'class',usesSpellSlot:true},
 {spellId:'chain-lightning',name:'Chain Lightning',baseLevel:6,source:'Sorcerer',sourceType:'class',usesSpellSlot:true},
 {spellId:'shield',name:'Shield',baseLevel:1,source:'Wizard',sourceType:'class',usesSpellSlot:true},
 {spellId:'fireball',name:'Fireball',baseLevel:3,source:'Wand of Fireballs',sourceType:'item',sourceVariantId:'wand-of-fireballs',usesSpellSlot:false,usesCharges:true},
 {spellId:'misty-step',name:'Misty Step',baseLevel:2,source:'Fey Step',sourceType:'species',sourceVariantId:'eladrin',usesSpellSlot:false,limitedUse:{max:1,period:'long_rest'}},
 {spellId:'mystery-upcast',name:'Mystery Upcast',baseLevel:2,source:'Import',sourceType:'class',usesSpellSlot:true}
];
const library=[{id:'mystery-upcast',name:'Mystery Upcast',level:2,higher_level_text:'At Higher Levels. Something improves, but structured metadata is absent.'}];
const built=rt.buildCastableSpellRows(character, known, library);
function row(name,lvl,source){ return built.rows.find(r=>r.name===name&&r.castLevel===lvl&&(!source||r.source===source)); }
console.log(JSON.stringify({
 fireball4:row('Fireball',4).damagePreview,
 lightning5:row('Lightning Bolt',5).damagePreview,
 ray4:row('Scorching Ray',4).damagePreview,
 cure3:row('Cure Wounds',3).healingPreview,
 counter5:row('Counterspell',5).effectPreview,
 chain7:row('Chain Lightning',7).effectPreview,
 shield2:row('Shield',2).effectPreview,
 item:row('Fireball',9,'Wand of Fireballs').castResourceType,
 limited:row('Misty Step',9,'Fey Step').castResourceType,
 missing:row('Mystery Upcast',3).effectPreview,
 missingMeta:row('Mystery Upcast',3).higherLevelMetadata,
 audit:built.diagnostics
}));
''')
    assert data['fireball4'] == '9d6'
    assert data['lightning5'] == '10d6'
    assert data['ray4'] == '5 rays × 2d6'
    assert data['cure3'] == '3d8 +4'
    assert 'level 5 or lower' in data['counter5']
    assert '+1 target' in data['chain7']
    assert data['shield2'] == 'No additional higher-level effect'
    assert data['item'] == 'charges'
    assert data['limited'] == 'limited-use'
    assert data['missing'] == 'Scaling data missing'
    assert data['missingMeta']['scalingDataMissing'] is True
    assert 'Fireball' in data['audit']['damageScaling']
    assert 'Cure Wounds' in data['audit']['healingScaling']
    assert 'Chain Lightning' in data['audit']['targetScaling']
    assert 'Counterspell' in data['audit']['specialScaling']
    assert any(x.startswith('Shield L2') for x in data['audit']['noHigherLevelEffect'])
    assert 'Mystery Upcast' in data['audit']['missingScalingData']
    assert data['audit']['generatedRowsPerSpell']['Fireball'] >= 7
