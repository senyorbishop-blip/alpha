import json
from pathlib import Path

from server.character.service import resolve_runtime
from server.character.rules_catalog import load_rules_catalog


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPECIES_ROOT = PROJECT_ROOT / 'server' / 'data' / 'rules' / '5e2024' / 'species'


def _species_traits(species_file: str):
    return json.loads((SPECIES_ROOT / species_file).read_text(encoding='utf-8')).get('traits', [])


def test_runtime_includes_subclass_feature_entries_with_real_text_and_action_lanes():
    result = resolve_runtime(
        {
            'identity': {'name': 'Gorim'},
            'classes': [{'classId': 'barbarian', 'level': 10, 'subclassId': 'berserker'}],
            'abilities': {'scores': {'str': 16, 'dex': 14, 'con': 14, 'cha': 12}},
        }
    )

    runtime = result['runtime']
    class_features = runtime.get('classFeatures') or []
    actions = runtime.get('actions') or []
    bonus_actions = runtime.get('bonusActions') or []

    frenzy = next((row for row in class_features if row.get('name') == 'Frenzy'), None)
    intimidating = next((row for row in class_features if row.get('name') == 'Intimidating Presence'), None)

    assert frenzy is not None
    assert frenzy.get('isSubclass') is True
    assert 'extra unarmed strike' in str(frenzy.get('description') or '').lower()
    assert any(row.get('name') == 'Frenzy' for row in bonus_actions)

    assert intimidating is not None
    assert intimidating.get('isSubclass') is True
    assert 'wisdom save' in str(intimidating.get('description') or '').lower()
    assert any(row.get('name') == 'Intimidating Presence' for row in actions)


def test_runtime_origin_background_and_feat_surfaces_are_enriched_for_features_tab():
    result = resolve_runtime(
        {
            'identity': {'name': 'Kael'},
            'species': {'id': 'dragonborn', 'name': 'Dragonborn', 'traits': _species_traits('dragonborn.json')},
            'background': {'id': 'acolyte', 'name': 'Acolyte'},
            'classes': [{'classId': 'fighter', 'level': 2}],
            'abilities': {'scores': {'str': 16, 'dex': 12, 'con': 14}},
            'feats': ['alert', 'tough'],
        }
    )

    runtime = result['runtime']
    origin_traits = runtime.get('originTraits') or []
    background_features = runtime.get('backgroundFeatures') or []
    feat_features = runtime.get('featFeatures') or []

    breath_weapon = next((row for row in origin_traits if row.get('name') == 'Breath Weapon'), None)
    shelter = next((row for row in background_features if row.get('name') == 'Shelter of the Faithful'), None)
    alert = next((row for row in feat_features if row.get('name') == 'Alert'), None)

    assert breath_weapon is not None
    assert breath_weapon.get('type') in {'action', 'bonus action', 'reaction', 'passive'}
    assert breath_weapon.get('usage')
    assert 'character level' in str(breath_weapon.get('description') or '').lower()

    assert shelter is not None
    assert 'free healing and care' in str(shelter.get('description') or '').lower()

    assert alert is not None
    assert 'initiative +5' in str(alert.get('description') or '').lower()
    assert alert.get('section') == 'Feats'


def test_core_class_features_are_authored_not_placeholder_labels():
    result = resolve_runtime(
        {
            'identity': {'name': 'Sera'},
            'classes': [{'classId': 'paladin', 'level': 6}],
            'abilities': {'scores': {'str': 16, 'dex': 10, 'con': 14, 'cha': 16}},
        }
    )

    runtime = result['runtime']
    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}

    lay_on_hands = features.get('Lay on Hands')
    aura = features.get('Aura of Protection (10 ft)')

    assert lay_on_hands is not None
    assert 'limited pool' in str(lay_on_hands.get('description') or '').lower() or 'healing' in str(lay_on_hands.get('description') or '').lower()
    assert lay_on_hands.get('resourceName') == 'Lay on Hands'

    assert aura is not None
    assert 'saving throw' in str(aura.get('summary') or '').lower() or 'team-defense' in str(aura.get('description') or '').lower()



def test_stage5b_champion_subclass_features_are_real_runtime_entries():
    result = resolve_runtime(
        {
            'identity': {'name': 'Boros'},
            'classes': [{'classId': 'fighter', 'level': 15, 'subclassId': 'champion'}],
            'abilities': {'scores': {'str': 18, 'dex': 12, 'con': 16}},
        }
    )

    runtime = result['runtime']
    features = {row.get('name'): row for row in (runtime.get('classFeatures') or [])}

    improved = features.get('Improved Critical')
    survivor = features.get('Survivor')

    assert improved is not None
    assert improved.get('isSubclass') is True
    assert improved.get('type') == 'passive'
    assert 'threaten decisive hits' in str(improved.get('description') or '').lower() or 'crit' in str(improved.get('description') or '').lower()

    assert survivor is not None
    assert survivor.get('isSubclass') is True
    assert 'attrition' in str(survivor.get('description') or '').lower() or 'recover' in str(survivor.get('description') or '').lower()



def test_stage5b_paladin_rogue_and_warlock_subclass_actions_gain_authored_depth():
    paladin = resolve_runtime(
        {
            'identity': {'name': 'Astra'},
            'classes': [{'classId': 'paladin', 'level': 20, 'subclassId': 'oath-of-devotion'}],
            'abilities': {'scores': {'str': 18, 'cha': 18, 'con': 16}},
        }
    )['runtime']
    rogue = resolve_runtime(
        {
            'identity': {'name': 'Shade'},
            'classes': [{'classId': 'rogue', 'level': 17, 'subclassId': 'thief'}],
            'abilities': {'scores': {'dex': 18, 'int': 14}},
        }
    )['runtime']
    warlock = resolve_runtime(
        {
            'identity': {'name': 'Morrow'},
            'classes': [{'classId': 'warlock', 'level': 14, 'subclassId': 'fiend-patron'}],
            'abilities': {'scores': {'cha': 18, 'con': 14, 'dex': 14}},
        }
    )['runtime']

    paladin_features = {row.get('name'): row for row in (paladin.get('classFeatures') or [])}
    rogue_features = {row.get('name'): row for row in (rogue.get('classFeatures') or [])}
    warlock_features = {row.get('name'): row for row in (warlock.get('classFeatures') or [])}

    sacred_weapon = paladin_features.get('Channel Divinity: Sacred Weapon')
    holy_nimbus = paladin_features.get('Holy Nimbus')
    fast_hands = rogue_features.get('Fast Hands')
    hurl = warlock_features.get('Hurl Through Hell')

    assert sacred_weapon is not None
    assert sacred_weapon.get('type') == 'action'
    assert sacred_weapon.get('resourceName') == 'Channel Divinity'
    assert 'accuracy' in str(sacred_weapon.get('description') or '').lower() or 'attack' in str(sacred_weapon.get('description') or '').lower()

    assert holy_nimbus is not None
    assert holy_nimbus.get('type') == 'action'
    assert any(row.get('name') == 'Holy Nimbus' for row in (paladin.get('actions') or []))

    assert fast_hands is not None
    assert fast_hands.get('type') == 'bonus action'
    assert any(row.get('name') == 'Fast Hands' for row in (rogue.get('bonusActions') or []))

    assert hurl is not None
    assert 'nightmare' in str(hurl.get('description') or '').lower() or 'dimension' in str(hurl.get('description') or '').lower()
    assert '10d10' in str(hurl.get('description') or '').lower() or str(hurl.get('effect') or '').lower() or str(hurl.get('dice') or '').lower()



def test_stage5b_monk_long_tail_features_are_no_longer_generic_level_labels():
    result = resolve_runtime(
        {
            'identity': {'name': 'Tarin'},
            'classes': [{'classId': 'monk', 'level': 17}],
            'abilities': {'scores': {'dex': 18, 'wis': 16, 'con': 14}},
        }
    )

    features = {row.get('name'): row for row in (result['runtime'].get('classFeatures') or [])}

    empowered = features.get('Empowered Strikes')
    perfect_focus = features.get('Perfect Focus')
    superior_defense = features.get('Superior Defense')

    assert empowered is not None
    assert 'resistant' in str(empowered.get('description') or '').lower() or 'magical' in str(empowered.get('description') or '').lower()

    assert perfect_focus is not None
    assert 'focus' in str(perfect_focus.get('summary') or '').lower()
    assert 'resource' in ' '.join(perfect_focus.get('tags') or []) or 'focus' in str(perfect_focus.get('description') or '').lower()

    assert superior_defense is not None
    assert 'survival' in str(superior_defense.get('description') or '').lower() or 'magical pressure' in str(superior_defense.get('description') or '').lower()



def test_stage5c_rules_catalog_now_exposes_monk_subclasses():
    catalog = load_rules_catalog()
    monk_rows = catalog.get('subclassesByClass', {}).get('monk') or []
    monk_ids = {row.get('id') for row in monk_rows}

    assert monk_ids == {'way-of-shadow', 'way-of-the-open-hand', 'way-of-the-four-elements'}



def test_stage5c_monk_subclasses_have_real_runtime_features_and_action_lanes():
    shadow_runtime = resolve_runtime(
        {
            'identity': {'name': 'Nyx'},
            'classes': [{'classId': 'monk', 'level': 17, 'subclassId': 'way-of-shadow'}],
            'abilities': {'scores': {'dex': 18, 'wis': 16, 'con': 14}},
        }
    )['runtime']
    open_hand_runtime = resolve_runtime(
        {
            'identity': {'name': 'Aren'},
            'classes': [{'classId': 'monk', 'level': 17, 'subclassId': 'way-of-the-open-hand'}],
            'abilities': {'scores': {'dex': 18, 'wis': 16, 'con': 14}},
        }
    )['runtime']

    shadow_features = {row.get('name'): row for row in (shadow_runtime.get('classFeatures') or [])}
    open_hand_features = {row.get('name'): row for row in (open_hand_runtime.get('classFeatures') or [])}

    shadow_step = shadow_features.get('Shadow Step')
    opportunist = shadow_features.get('Opportunist')
    wholeness = open_hand_features.get('Wholeness of Body')
    quivering = open_hand_features.get('Quivering Palm')

    assert shadow_step is not None
    assert shadow_step.get('type') == 'bonus action'
    assert 'teleport' in str(shadow_step.get('description') or '').lower() or 'dim light' in str(shadow_step.get('description') or '').lower()
    assert any(row.get('name') == 'Shadow Step' for row in (shadow_runtime.get('bonusActions') or []))

    assert opportunist is not None
    assert opportunist.get('type') == 'reaction'
    assert any(row.get('name') == 'Opportunist' for row in (shadow_runtime.get('reactions') or []))

    assert wholeness is not None
    assert wholeness.get('type') == 'action'
    assert wholeness.get('resourceName') == 'Wholeness of Body'
    assert any(row.get('name') == 'Wholeness of Body' for row in (open_hand_runtime.get('actions') or []))

    assert quivering is not None
    assert quivering.get('type') == 'action'
    assert 'vibration' in str(quivering.get('description') or '').lower() or 'finisher' in str(quivering.get('description') or '').lower()



def test_stage5c_remaining_subclass_long_tail_now_has_authored_depth():
    bard = resolve_runtime(
        {
            'identity': {'name': 'Liora'},
            'classes': [{'classId': 'bard', 'level': 14, 'subclassId': 'college-of-glamour'}],
            'abilities': {'scores': {'cha': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']
    cleric = resolve_runtime(
        {
            'identity': {'name': 'Vey'},
            'classes': [{'classId': 'cleric', 'level': 17, 'subclassId': 'light-domain'}],
            'abilities': {'scores': {'wis': 18, 'con': 14, 'dex': 12}},
        }
    )['runtime']
    druid = resolve_runtime(
        {
            'identity': {'name': 'Thorn'},
            'classes': [{'classId': 'druid', 'level': 10, 'subclassId': 'circle-of-the-land'}],
            'abilities': {'scores': {'wis': 18, 'con': 14, 'dex': 14}},
        }
    )['runtime']
    ranger = resolve_runtime(
        {
            'identity': {'name': 'Kest'},
            'classes': [{'classId': 'ranger', 'level': 15, 'subclassId': 'gloom-stalker'}],
            'abilities': {'scores': {'dex': 18, 'wis': 16, 'con': 14}},
        }
    )['runtime']
    sorcerer = resolve_runtime(
        {
            'identity': {'name': 'Mira'},
            'classes': [{'classId': 'sorcerer', 'level': 14, 'subclassId': 'wild-magic'}],
            'abilities': {'scores': {'cha': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']
    wizard = resolve_runtime(
        {
            'identity': {'name': 'Iven'},
            'classes': [{'classId': 'wizard', 'level': 14, 'subclassId': 'diviner'}],
            'abilities': {'scores': {'int': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']
    warlock = resolve_runtime(
        {
            'identity': {'name': 'Faelan'},
            'classes': [{'classId': 'warlock', 'level': 14, 'subclassId': 'archfey-patron'}],
            'abilities': {'scores': {'cha': 18, 'dex': 14, 'con': 14}},
        }
    )['runtime']

    bard_features = {row.get('name'): row for row in (bard.get('classFeatures') or [])}
    cleric_features = {row.get('name'): row for row in (cleric.get('classFeatures') or [])}
    druid_features = {row.get('name'): row for row in (druid.get('classFeatures') or [])}
    ranger_features = {row.get('name'): row for row in (ranger.get('classFeatures') or [])}
    sorcerer_features = {row.get('name'): row for row in (sorcerer.get('classFeatures') or [])}
    wizard_features = {row.get('name'): row for row in (wizard.get('classFeatures') or [])}
    warlock_features = {row.get('name'): row for row in (warlock.get('classFeatures') or [])}

    assert bard_features['Mantle of Inspiration'].get('type') == 'bonus action'
    assert bard_features['Mantle of Inspiration'].get('resourceName') == 'Bardic Inspiration'
    assert any(row.get('name') == 'Mantle of Inspiration' for row in (bard.get('bonusActions') or []))

    assert cleric_features['Radiance of the Dawn'].get('resourceName') == 'Channel Divinity'
    assert any(row.get('name') == 'Radiance of the Dawn' for row in (cleric.get('actions') or []))

    assert druid_features['Natural Recovery'].get('trackUses') is True
    assert 'slot economy' in str(druid_features['Natural Recovery'].get('description') or '').lower()

    assert 'opening heartbeat' in str(ranger_features['Dread Ambusher'].get('description') or '').lower() or 'first-round' in str(ranger_features['Dread Ambusher'].get('description') or '').lower()

    assert sorcerer_features['Bend Luck'].get('type') == 'reaction'
    assert sorcerer_features['Bend Luck'].get('resourceName') == 'Sorcery Points'

    assert wizard_features['Portent'].get('resourceName') == 'Portent'
    assert 'stored rolls' in str(wizard_features['Portent'].get('description') or '').lower() or 'future d20' in str(wizard_features['Portent'].get('description') or '').lower()

    assert warlock_features['Misty Escape'].get('type') == 'reaction'
    assert any(row.get('name') == 'Misty Escape' for row in (warlock.get('reactions') or []))


def test_stage5d_remaining_core_class_long_tail_features_now_have_authored_depth():
    sorcerer = resolve_runtime(
        {
            'identity': {'name': 'Bishop'},
            'classes': [{'classId': 'sorcerer', 'level': 19, 'subclassId': 'wild-magic'}],
            'abilities': {'scores': {'cha': 20, 'con': 13, 'dex': 10, 'int': 16, 'wis': 15}},
        }
    )['runtime']
    wizard = resolve_runtime(
        {
            'identity': {'name': 'Quill'},
            'classes': [{'classId': 'wizard', 'level': 18}],
            'abilities': {'scores': {'int': 20, 'con': 14, 'dex': 14}},
        }
    )['runtime']
    ranger = resolve_runtime(
        {
            'identity': {'name': 'Ash'},
            'classes': [{'classId': 'ranger', 'level': 18}],
            'abilities': {'scores': {'dex': 18, 'wis': 16, 'con': 14}},
        }
    )['runtime']
    druid = resolve_runtime(
        {
            'identity': {'name': 'Moss'},
            'classes': [{'classId': 'druid', 'level': 18}],
            'abilities': {'scores': {'wis': 20, 'con': 14, 'dex': 14}},
        }
    )['runtime']

    sorcerer_features = {row.get('name'): row for row in (sorcerer.get('classFeatures') or [])}
    wizard_features = {row.get('name'): row for row in (wizard.get('classFeatures') or [])}
    ranger_features = {row.get('name'): row for row in (ranger.get('classFeatures') or [])}
    druid_features = {row.get('name'): row for row in (druid.get('classFeatures') or [])}

    assert 'heightened casting state' in str(sorcerer_features['Innate Sorcery'].get('description') or '').lower() or 'heightened' in str(sorcerer_features['Innate Sorcery'].get('summary') or '').lower()
    assert 'trade between' in str(sorcerer_features['Flexible Casting'].get('description') or '').lower() or 'resource' in ' '.join(sorcerer_features['Flexible Casting'].get('tags') or []).lower()

    assert 'learned specialist' in str(wizard_features['Scholar'].get('description') or '').lower() or 'knowledge' in ' '.join(wizard_features['Scholar'].get('tags') or []).lower()
    assert 'cantrips are used constantly' in str(wizard_features['Cantrip Formulas'].get('description') or '').lower() or 'flexibility' in str(wizard_features['Cantrip Formulas'].get('summary') or '').lower()

    conjure_barrage = ranger_features['Conjure Barrage (1/LR)']
    assert conjure_barrage.get('type') == 'action'
    assert conjure_barrage.get('resourceName') == 'Conjure Barrage'
    assert 'crowd-hit' in str(conjure_barrage.get('description') or '').lower() or 'clustered enemies' in str(conjure_barrage.get('description') or '').lower()

    assert 'older, steadier' in str(druid_features['Timeless Body'].get('description') or '').lower() or 'identity spike' in str(druid_features['Timeless Body'].get('description') or '').lower()


def test_stage5e_remaining_core_long_tail_features_are_no_longer_generic_placeholders():
    ranger_runtime = resolve_runtime(
        {
            'identity': {'name': 'Vale'},
            'classes': [{'classId': 'ranger', 'level': 20}],
            'abilities': {'scores': {'dex': 18, 'wis': 16, 'con': 14}},
        }
    )['runtime']
    barbarian_runtime = resolve_runtime(
        {
            'identity': {'name': 'Hruk'},
            'classes': [{'classId': 'barbarian', 'level': 20}],
            'abilities': {'scores': {'str': 20, 'con': 18, 'dex': 14}},
        }
    )['runtime']

    ranger_features = {row.get('name'): row for row in (ranger_runtime.get('classFeatures') or [])}
    barbarian_features = {row.get('name'): row for row in (barbarian_runtime.get('classFeatures') or [])}

    foe_slayer = ranger_features.get('Foe Slayer')
    tireless = ranger_features.get('Tireless')
    brutal = barbarian_features.get('Brutal Strike (1d10 + effect)')
    indomitable_might = barbarian_features.get('Indomitable Might')

    assert foe_slayer is not None
    assert 'hunter payoff' in str(foe_slayer.get('description') or '').lower() or 'precise and deadly' in str(foe_slayer.get('description') or '').lower()

    assert tireless is not None
    assert 'self-sufficient' in str(tireless.get('description') or '').lower() or 'attrition' in str(tireless.get('description') or '').lower()

    assert brutal is not None
    assert 'shift the fight' in str(brutal.get('description') or '').lower() or 'extra brutality' in str(brutal.get('effect') or '').lower()

    assert indomitable_might is not None
    assert 'brute-force' in str(indomitable_might.get('description') or '').lower() or 'physical strength' in str(indomitable_might.get('summary') or '').lower()
