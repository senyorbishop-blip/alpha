from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from server.rules_content import OPEN_5E_SPELLS
from server.character.spell_authored_data import STAGE4B_AUTHORED_OVERRIDES, STAGE4C_AUTHORED_OVERRIDES, STAGE4D_AUTHORED_OVERRIDES, STAGE4E_AUTHORED_OVERRIDES


_ABILITY_LABELS = {
    'STR': 'Strength',
    'DEX': 'Dexterity',
    'CON': 'Constitution',
    'INT': 'Intelligence',
    'WIS': 'Wisdom',
    'CHA': 'Charisma',
}

_DAMAGE_KEYWORDS = {
    'fire': 'fire',
    'flame': 'fire',
    'burn': 'fire',
    'frost': 'cold',
    'ice': 'cold',
    'cold': 'cold',
    'lightning': 'lightning',
    'thunder': 'thunder',
    'poison': 'poison',
    'acid': 'acid',
    'necrot': 'necrotic',
    'radiance': 'radiant',
    'radiant': 'radiant',
    'psych': 'psychic',
    'mind': 'psychic',
    'force': 'force',
    'shadow': 'necrotic',
}

_KEYWORD_TAGS = [
    ('summon', 'summon'),
    ('conjure', 'summon'),
    ('illusion', 'illusion'),
    ('charm', 'charm'),
    ('fear', 'fear'),
    ('teleport', 'teleport'),
    ('misty', 'teleport'),
    ('heal', 'healing'),
    ('cure', 'healing'),
    ('raise', 'healing'),
    ('reviv', 'revival'),
    ('dead', 'necromancy'),
    ('wall', 'barrier'),
    ('shield', 'defense'),
    ('ward', 'defense'),
    ('counter', 'counter'),
    ('detect', 'utility'),
    ('locate', 'utility'),
    ('scry', 'utility'),
    ('polymorph', 'transformation'),
    ('shape', 'transformation'),
    ('dominate', 'control'),
    ('hold', 'control'),
    ('suggest', 'control'),
    ('command', 'control'),
]

_MANUAL_OVERRIDES: dict[str, dict[str, Any]] = {
    'booming-blade': {
        'attackType': 'Melee Spell Attack / weapon strike',
        'damageType': 'thunder',
        'damageFormula': 'Weapon hit + 1d8 thunder rider',
        'scalingNote': 'At character levels 5, 11, and 17 the on-hit burst and the movement burst each grow by 1d8.',
        'description': (
            'Brand your melee strike with unstable thunder. As part of the cast, make a melee attack with the weapon used for the spell. '
            'On a hit, resolve the weapon damage normally and wrap the target in resonant energy.\n\n'
            'If the target willingly moves before your next turn begins, the stored energy detonates and deals thunder damage. '
            'Use this cantrip when you want to punish disengaging enemies, chokepoint runners, or creatures trying to kite a front-line fighter.'
        ),
    },
    'green-flame-blade': {
        'attackType': 'Melee Spell Attack / weapon strike',
        'damageType': 'fire',
        'damageFormula': 'Weapon hit + 1d8 fire splash',
        'scalingNote': 'At character levels 5, 11, and 17 both the primary fire rider and the leap damage improve by 1d8.',
        'description': (
            'Channel green fire through a melee weapon swing. As part of the cast, make a melee attack with the weapon used for the spell. '
            'On a hit, the main target takes the weapon damage and an extra burst of fire.\n\n'
            'A second creature close to the first target can also be scorched by the jumping flame. '
            'This is a pressure cantrip for clustered targets and rewards aggressive front-line casters.'
        ),
    },
    'eldritch-blast': {
        'attackType': 'Ranged Spell Attack',
        'damageType': 'force',
        'damageFormula': '1d10',
        'scalingNote': 'At character levels 5, 11, and 17 you fire an additional beam. Each beam makes its own attack roll and can hit the same or different targets.',
        'description': (
            'Fire a beam of crackling force at a creature you can see in range. Make a ranged spell attack for each beam produced by the cantrip. '
            'Each successful beam deals force damage and resolves separately for effects that trigger on a hit.\n\n'
            'This is a reliable ranged pressure tool and scales through extra beams rather than a single larger damage roll.'
        ),
    },
    'fireball': {
        'savingThrow': 'DEX',
        'damageType': 'fire',
        'damageFormula': '8d6',
        'scalingNote': 'When cast with a slot above 3rd, add 1d6 fire damage for each slot level above 3rd.',
        'description': (
            'Choose a point within range and erupt it into a roaring sphere of flame. Creatures in the blast make a Dexterity save. '
            'A failed save takes full fire damage; a successful save takes half.\n\n'
            'Use this spell to clear clusters, punish enemies hiding behind cover edges, or force concentration checks across a wide area. '
            'Objects and scenery that should burn can be affected at the DM’s discretion.'
        ),
    },
    'magic-missile': {
        'damageType': 'force',
        'damageFormula': '3 × (1d4+1)',
        'scalingNote': 'Each slot level above 1st adds one extra dart.',
        'description': (
            'Create three force darts that strike automatically. You can send them all at one creature or divide them among visible targets. '
            'Each dart deals its damage separately, which makes the spell good for finishing weakened enemies or forcing several concentration checks.\n\n'
            'Because the darts do not require an attack roll, this is one of the most dependable direct-damage spells in the library.'
        ),
    },
    'shield': {
        'description': (
            'Flash a ward into place as a reaction when danger is about to land. Until the start of your next turn, your Armor Class rises sharply, '
            'often turning a hit into a miss.\n\n'
            'Use Shield to survive burst windows, protect concentration, or shut down a volley that would otherwise connect. '
            'It is strongest when you cast it only after you know an attack is threatening you.'
        ),
        'effect': '+5 AC reaction ward',
    },
    'mage-armor': {
        'description': (
            'Wrap an unarmored creature in a persistent arcane shell. The target’s base Armor Class becomes 13 + its Dexterity modifier for the spell’s duration.\n\n'
            'This is an all-day defensive spell for casters and lightly equipped characters. It is usually cast before danger begins, not during the fight.'
        ),
        'effect': 'AC becomes 13 + DEX',
    },
    'cure-wounds': {
        'healingFormula': '1d8 + spellcasting modifier',
        'scalingNote': 'Each slot level above 1st adds 1d8 healing.',
        'description': (
            'Touch a creature and restore hit points through direct restorative magic. This is your stronger single-target healing option when you can afford to be in touch range.\n\n'
            'Use it to pull an ally back from danger, stabilize a front-liner between enemy turns, or refill hit points after the fight.'
        ),
    },
    'healing-word': {
        'healingFormula': '1d4 + spellcasting modifier',
        'scalingNote': 'Each slot level above 1st adds 1d4 healing.',
        'description': (
            'Speak a quick burst of healing at range and restore hit points to a creature you can see. Because it uses a bonus action, '
            'it is excellent for getting an ally back into the fight while keeping your main action free.\n\n'
            'The raw healing is modest, but the action economy is extremely strong.'
        ),
    },
    'guidance': {
        'description': (
            'Touch a willing creature and lace its next important moment with divine or primal help. Before the spell ends, the target can add 1d4 to one ability check.\n\n'
            'Use it before scouting, social scenes, lockpicking, tracking, or any other check where a small bonus can turn failure into success.'
        ),
        'effect': '+1d4 to one ability check',
    },
    'bless': {
        'scalingNote': 'Each slot above 1st lets you affect one additional creature.',
        'description': (
            'Bolster up to three allies with battle-ready fortune while you maintain concentration. Blessed creatures add 1d4 to attack rolls and saving throws.\n\n'
            'Bless is one of the strongest low-level support spells because it improves accuracy and survival at the same time. '
            'Cast it early in hard fights or before enemies force dangerous saves.'
        ),
        'effect': 'Up to 3 allies gain +1d4 to attacks and saves',
    },
    'bane': {
        'savingThrow': 'CHA',
        'scalingNote': 'Each slot above 1st lets you affect one additional creature.',
        'description': (
            'Curse up to three enemies with fraying confidence while you maintain concentration. Affected creatures subtract 1d4 from attack rolls and saving throws.\n\n'
            'Bane is the mirror image of Bless: use it to weaken accurate enemies, blunt elite attackers, or set up later save-based spells.'
        ),
        'effect': 'Up to 3 enemies take -1d4 to attacks and saves',
    },
    'hunter-s-mark': {
        'damageType': 'force',
        'damageFormula': '1d6 on each weapon hit',
        'description': (
            'Mark one creature as your quarry while maintaining concentration. Your weapon hits against that target deal extra damage, '
            'and you can usually move the mark to a new target after the first drops.\n\n'
            'This is the ranger’s bread-and-butter damage spell and rewards focus fire across multiple turns.'
        ),
    },
    'hex': {
        'damageType': 'necrotic',
        'damageFormula': '1d6 on each hit',
        'description': (
            'Lay a malignant mark on a creature while maintaining concentration. Each time you hit it with an attack, the target takes extra damage. '
            'The curse also hampers one ability score’s checks, making it useful inside and outside combat.\n\n'
            'Hex shines on characters who make many attacks or repeatable beams.'
        ),
    },
    'spiritual-weapon': {
        'attackType': 'Melee Spell Attack',
        'damageType': 'force',
        'damageFormula': '1d8 + spellcasting modifier',
        'scalingNote': 'When cast with a higher slot, the summoned weapon’s hit grows every two slot levels.',
        'description': (
            'Summon a floating weapon within range and strike immediately. The weapon uses your bonus action on later turns to keep attacking without concentration.\n\n'
            'This spell is premium action-economy pressure for divine casters because it lets you keep attacking while spending your action on something else.'
        ),
    },
    'spirit-guardians': {
        'savingThrow': 'WIS',
        'damageType': 'radiant or necrotic',
        'damageFormula': '3d8',
        'scalingNote': 'Each slot above 3rd adds 1d8 damage.',
        'description': (
            'Call swirling spirits to orbit you in a damaging aura while you maintain concentration. Enemies inside the field are slowed, '
            'and the first time they enter it on a turn or start there, they make a Wisdom save against the spell’s damage.\n\n'
            'This spell dominates close-quarters fights, protects choke points, and punishes enemies that try to rush the party.'
        ),
    },
    'counterspell': {
        'description': (
            'Snap a hostile spell apart as a reaction when you see it being cast. Lesser spells can be broken outright; '
            'stronger magic may demand a spellcasting ability check to shut it down cleanly.\n\n'
            'Use this to protect the party from enemy control, burst damage, teleport escapes, or resurrection denial.'
        ),
        'effect': 'Reaction to interrupt a spell',
    },
    'dispel-magic': {
        'description': (
            'Unravel one magical effect, ward, or ongoing spell on a creature, object, or area. Stronger effects can require a spellcasting ability check.\n\n'
            'Dispel Magic is the universal answer to enemy buffs, traps, curses, magical locks, and long-running battlefield effects.'
        ),
        'effect': 'Ends one magical effect',
    },
    'misty-step': {
        'description': (
            'Blink through a ripple of magic and reappear at a point you can see. Because it uses a bonus action, it is ideal for escaping grapples, '
            'clearing hazards, or taking high-value positions before you spend your action.\n\n'
            'This is a pure mobility spell: short range, instant payoff, and no concentration burden.'
        ),
        'effect': 'Short bonus-action teleport',
    },
    'revivify': {
        'description': (
            'Reach for a creature that has only just died and pull it back before the moment is lost. The spell returns the target to life with a small amount of vitality.\n\n'
            'Revivify is emergency resurrection magic. It is strongest when the group is ready with diamonds, positioning, and enough safety to cast it immediately.'
        ),
        'effect': 'Return a recently slain creature to life',
    },
    'dimension-door': {
        'description': (
            'Fold space and step through it to a distant point, carrying yourself and, if the table allows, a nearby companion or light burden.\n\n'
            'Use this spell to bypass terrain, escape captures, reach rooftops, cross chasms, or rescue an ally from a collapsing fight. '
            'It is a tactical reposition tool first and a combat spell second.'
        ),
        'effect': 'Long-range teleport reposition',
    },
    'polymorph': {
        'savingThrow': 'WIS',
        'description': (
            'Transform a creature into a beast form. Unwilling targets resist with a Wisdom save, while willing allies can accept the change.\n\n'
            'Use Polymorph as control or rescue: turn an enemy into a harmless animal, or turn an ally into a large bag of temporary hit points and new movement options. '
            'The spell ends when concentration breaks or the new form is reduced to 0 hit points.'
        ),
    },
    'wall-of-force': {
        'description': (
            'Shape an invisible barrier of pure force that seals off movement and many attacks. The wall does not rely on hit points; it simply exists until the spell ends or a rare countermeasure removes it.\n\n'
            'Use it to split encounters, trap monsters away from the party, protect a retreat, or buy time in a fight you cannot win head-on.'
        ),
        'effect': 'Create a near-impenetrable barrier',
    },
    'chain-lightning': {
        'savingThrow': 'DEX',
        'damageType': 'lightning',
        'damageFormula': '10d8',
        'description': (
            'Launch a main lightning strike that forks into secondary arcs. The primary target and each jumped target make a Dexterity save for the spell’s damage.\n\n'
            'This spell is excellent against scattered elites because it reaches multiple creatures without needing them to stand inside the same area.'
        ),
    },
    'meteor-swarm': {
        'savingThrow': 'DEX',
        'damageType': 'fire and bludgeoning',
        'damageFormula': '40d6 total',
        'description': (
            'Call down apocalyptic impacts across a massive area. Creatures caught in the devastation make a Dexterity save. '
            'On a failure they take the full combination of fire and concussive damage; on a success they take half.\n\n'
            'Meteor Swarm is an encounter-ending spell built for huge battlefields, sieges, and legendary set pieces.'
        ),
    },
    'wish': {
        'description': (
            'Bend the highest tier of magic to duplicate almost any lower spell or attempt a reality-altering effect beyond normal limits.\n\n'
            'At the table, Wish should be treated with care: it can solve impossible problems, but it can also reshape the story and impose serious consequences when used recklessly.'
        ),
        'effect': 'Reality-warping apex magic',
    },
}

_MANUAL_OVERRIDES.update(STAGE4B_AUTHORED_OVERRIDES)
_MANUAL_OVERRIDES.update(STAGE4C_AUTHORED_OVERRIDES)
_MANUAL_OVERRIDES.update(STAGE4D_AUTHORED_OVERRIDES)
_MANUAL_OVERRIDES.update(STAGE4E_AUTHORED_OVERRIDES)
if 'hunter-s-mark' in _MANUAL_OVERRIDES and 'hunters-mark' not in _MANUAL_OVERRIDES:
    _MANUAL_OVERRIDES['hunters-mark'] = dict(_MANUAL_OVERRIDES['hunter-s-mark'])
if 'hunters-mark' in _MANUAL_OVERRIDES:
    _MANUAL_OVERRIDES['hunters-mark']['damageType'] = ''


def _slug(value: Any) -> str:
    return re.sub(r'[^a-z0-9]+', '-', str(value or '').strip().lower()).strip('-')


@lru_cache(maxsize=1)
def _open5e_index() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in OPEN_5E_SPELLS:
        cloned = dict(row)
        for candidate in [
            row.get('name'),
            row.get('id'),
            str(row.get('id') or '').removeprefix('spell_'),
            str(row.get('id') or '').removeprefix('spell-'),
        ]:
            key = _slug(candidate)
            if key:
                out[key] = cloned
    return out


def _save_label(save: str) -> str:
    save = str(save or '').strip().upper()
    if not save:
        return ''
    return f"{_ABILITY_LABELS.get(save, save.title())} save"


def _clean(text: Any) -> str:
    return str(text or '').strip()


def _is_placeholder_catalog_text(text: Any) -> bool:
    value = _clean(text).lower()
    return 'spell data entry for the 5e2024 rules catalog' in value and 'baseline casting metadata' in value


def _pick_preferred_text(*values: Any) -> str:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return ''


def _merge_components(base_components: Any, material_text: Any) -> str:
    components = _clean(base_components)
    material = _clean(material_text)
    if not components:
        return ''
    if 'M' in components and material and material.lower() not in components.lower():
        return f'{components} ({material})'
    return components


def _guess_damage_type(name: str, existing: str, school: str) -> str:
    if existing:
        return existing
    lname = name.lower()
    for key, dmg in _DAMAGE_KEYWORDS.items():
        if key in lname:
            return dmg
    if school.lower() == 'necromancy' and any(k in lname for k in ['touch', 'dead', 'blight', 'death']):
        return 'necrotic'
    return ''


def _guess_attack_or_save(name: str, level: int, school: str, damage_type: str, tags: list[str] | None = None, effect_text: str = '') -> tuple[str, str]:
    lname = name.lower()
    tag_set = {str(t).strip().lower() for t in (tags or []) if str(t).strip()}
    combined = f"{lname} {str(effect_text or '').lower()}"
    if tag_set & {'utility', 'ritual', 'buff', 'healing', 'summon', 'teleport'} and not (tag_set & {'damage', 'attack', 'save'}):
        return '', ''
    if any(k in combined for k in ['spell attack', 'make a ranged spell attack', 'make a melee spell attack']):
        return ('Melee Spell Attack' if 'melee spell attack' in combined or 'touch' in combined or 'grasp' in lname or 'whip' in lname else 'Ranged Spell Attack'), ''
    if any(k in lname for k in ['bolt', 'ray', 'blast', 'grasp', 'whip', 'knife', 'orb', 'arrow']) or 'attack' in tag_set:
        return 'Ranged Spell Attack' if any(k in lname for k in ['bolt', 'ray', 'blast', 'knife', 'orb', 'arrow']) else 'Melee Spell Attack', ''
    if any(k in lname for k in ['charm', 'fear', 'mock', 'suggest', 'hold', 'dominate', 'command', 'sleep', 'pattern', 'confusion', 'phantasmal', 'feeblemind']):
        return '', 'WIS'
    if any(k in lname for k in ['poison', 'blight', 'sicken', 'death', 'wilt', 'disease', 'contagion']):
        return '', 'CON'
    if any(k in lname for k in ['lightning', 'fireball', 'thunderwave', 'eruption', 'storm', 'ice storm', 'shatter', 'quake', 'swarm']):
        return '', 'DEX'
    if any(k in lname for k in ['telekinesis', 'earth tremor', 'thorns', 'entangle', 'web', 'whirlwind']):
        return '', 'STR'
    if 'save' in tag_set:
        if school.lower() in ('enchantment', 'illusion'):
            return '', 'WIS'
        if damage_type in ('fire', 'cold', 'lightning', 'acid', 'thunder', 'radiant'):
            return '', 'DEX'
        if damage_type in ('poison', 'necrotic'):
            return '', 'CON'
    return '', ''


def _guess_formula(level: int, attack_type: str, save: str, name: str, damage_type: str, tags: list[str] | None = None) -> str:
    lname = name.lower()
    tag_set = {str(t).strip().lower() for t in (tags or []) if str(t).strip()}
    iconic_damage_names = {'fireball', 'lightning bolt', 'meteor swarm', 'toll the dead', 'vicious mockery'}
    if not attack_type and not save and 'damage' not in tag_set:
        return ''
    if not damage_type and 'damage' not in tag_set and not any(k in lname for k in iconic_damage_names):
        return ''
    if any(k in lname for k in ['fireball']):
        return '8d6'
    if any(k in lname for k in ['lightning bolt']):
        return '8d6'
    if any(k in lname for k in ['meteor swarm']):
        return '40d6 total'
    if level == 0:
        if 'eldritch blast' in lname:
            return '1d10'
        if 'toll the dead' in lname:
            return '1d8 or 1d12 vs wounded target'
        if 'vicious mockery' in lname:
            return '1d6'
        if 'word of radiance' in lname or 'thunderclap' in lname or 'sword burst' in lname:
            return '1d6'
        if attack_type:
            return '1d10' if damage_type in ('fire', 'force') else '1d8'
        if save:
            return '1d8'
        return ''
    base = {1: '2d8', 2: '3d8', 3: '5d8', 4: '6d8', 5: '8d8', 6: '10d8', 7: '12d8', 8: '14d8', 9: '16d8'}
    if any(k in lname for k in ['wall of fire', 'spirit guardians', 'flame strike']):
        return {4: '5d8', 3: '3d8', 5: '4d6 + 4d6'}.get(level, base.get(level, ''))
    if any(k in lname for k in ['heal', 'cure', 'healing word', 'mass cure', 'mass heal', 'prayer of healing', 'regenerate']):
        return ''
    if attack_type:
        return base.get(level, '10d8')
    if save:
        return {1: '3d6', 2: '4d6', 3: '8d6', 4: '8d8', 5: '10d8', 6: '10d10', 7: '12d10', 8: '14d10', 9: '16d10'}.get(level, base.get(level, ''))
    return ''


def _ordinal(value: int) -> str:
    value = int(value)
    if 10 <= (value % 100) <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(value % 10, 'th')
    return f'{value}{suffix}'


def _cantrip_scaling(formula: str) -> str:
    if not formula:
        return 'This cantrip improves at character levels 5, 11, and 17.'
    match = re.match(r'\s*(\d+)d(\d+)', formula)
    if not match:
        return 'This cantrip improves at character levels 5, 11, and 17.'
    count, sides = int(match.group(1)), int(match.group(2))
    return f'At character levels 5, 11, and 17, increase the main damage roll to {count + 1}d{sides}, {count + 2}d{sides}, and {count + 3}d{sides}.'


def _generic_scaling(name: str, level: int, formula: str, healing_formula: str) -> str:
    lname = name.lower()
    if level == 0:
        return _cantrip_scaling(formula)
    if healing_formula:
        match = re.match(r'\s*(\d+)d(\d+)', healing_formula)
        if match:
            return f'When cast with a slot above {_ordinal(level)}, add 1d{match.group(2)} healing for each slot level above the spell’s base level.'
        return ''
    if any(k in lname for k in ['summon', 'conjure', 'animate', 'awaken', 'clone', 'find familiar']):
        return 'Higher slots usually improve the summoned creature, the number of created objects, or the duration at your table’s chosen tuning.'
    if formula:
        match = re.match(r'\s*(\d+)d(\d+)', formula)
        if match:
            return f'When cast with a slot above {_ordinal(level)}, add 1d{match.group(2)} to the main damage roll for each slot level above the spell’s base level unless a more specific spell rule says otherwise.'
    return ''




def _themed_effect_text(name: str, school: str, range_text: str, duration: str) -> str:
    lname = name.lower()
    if 'alarm' in lname:
        return 'Ward a point, object, doorway, or campsite so the spell alerts you when a creature enters the protected space.'
    if 'detect' in lname:
        return 'Sense the presence, source, or nearest trace of the category named by the spell while you study the area.'
    if 'locate' in lname:
        return 'Point yourself toward the creature, object, or destination named by the spell as long as it remains within the spell’s limits.'
    if 'identify' in lname or 'legend lore' in lname or 'comprehend languages' in lname or 'tongues' in lname:
        return 'Reveal hidden information, translation, or magical properties that would otherwise require investigation or downtime.'
    if 'find familiar' in lname:
        return 'Call a bound magical companion that scouts, delivers touch spells, and performs simple support tasks.'
    if 'unseen servant' in lname or 'floating disk' in lname:
        return 'Create a simple magical helper that carries, lifts, or manipulates objects within clear task limits.'
    if 'speak with' in lname or 'true seeing' in lname or 'clairvoyance' in lname or 'scry' in lname:
        return 'Open an information channel that lets you observe, communicate, or perceive beyond normal mortal limits.'
    if 'teleport' in lname or 'plane shift' in lname or 'gate' in lname or 'arcane gate' in lname or 'word of recall' in lname:
        return 'Move creatures across long distances or between planes through an instant magical transit effect.'
    if 'raise dead' in lname or 'true resurrection' in lname or 'resurrection' in lname:
        return 'Return a dead creature to life when the body, time limit, and material requirements are all satisfied.'
    if 'wall' in lname or 'sphere' in lname or 'forcecage' in lname:
        return 'Create a battlefield barrier that blocks movement, line paths, or safe access to a space.'
    if 'cloud' in lname or 'storm' in lname or 'plague' in lname or 'whirlwind' in lname or 'tsunami' in lname:
        return 'Fill an area with hazardous magical terrain that damages, obscures, or displaces creatures over time.'
    if 'invisibility' in lname or 'seeming' in lname or 'disguise' in lname or 'mislead' in lname:
        return 'Conceal or alter appearances so creatures lose track of your real position or identity.'
    if 'haste' in lname or 'heroism' in lname or 'longstrider' in lname or 'freedom of movement' in lname:
        return 'Enhance speed, resilience, or action economy for the target while the spell remains active.'
    if 'hold' in lname or 'web' in lname or 'entangle' in lname or 'snare' in lname or 'compulsion' in lname:
        return 'Control movement by restraining, redirecting, or locking creatures in place.'
    if 'polymorph' in lname or 'shapechange' in lname or 'alter self' in lname or 'enlarge/reduce' in lname:
        return 'Reshape the target’s body, size, or form to create a tactical advantage.'
    if 'animate' in lname or 'conjure' in lname or 'summon' in lname or 'create undead' in lname or 'planar ally' in lname or 'bigby' in lname:
        return 'Bring forth a magical creature, object, or animated force that acts as a temporary ally or hazard.'
    if 'restoration' in lname or 'purify' in lname or 'remove curse' in lname or 'heal' in lname:
        return 'Restore the target by removing damage, conditions, curses, or lingering magical harm.'
    if 'bless' in lname or 'bane' in lname or 'sanctuary' in lname or 'shield of faith' in lname:
        return 'Apply a broad combat modifier that improves defenses or weakens the enemy side of the fight.'
    if 'illusion' in lname or school.lower() == 'illusion':
        return 'Create deceptive sensory details that distract, misdirect, or hide the truth of a scene.'
    if 'counterspell' in lname or 'dispel' in lname or 'antimagic' in lname or 'invulnerability' in lname:
        return 'Directly interfere with magical energy by interrupting, suppressing, or negating it.'
    return ''

def _tactical_hint_from_tags(name: str, tags: list[str], concentration: bool) -> str:
    tag_set = {str(t).strip().lower() for t in (tags or []) if str(t).strip()}
    lname = name.lower()
    if 'healing' in tag_set:
        return 'Keep it for recovery windows, emergency pickups, or to steady a front-liner who cannot afford to fall.'
    if 'buff' in tag_set:
        return 'Cast it before the enemy’s most dangerous swing lands so the party gets the full value from the buff.'
    if 'control' in tag_set or any(k in lname for k in ['hold', 'web', 'entangle', 'suggest', 'command']):
        return 'This spell is strongest when it steals actions, movement, or positioning from a target that matters.'
    if 'teleport' in tag_set or 'misty' in lname:
        return 'Use it to rewrite positioning: escape danger, bypass terrain, or take a better line without spending a full turn doing it.'
    if 'utility' in tag_set or 'ritual' in tag_set:
        return 'Treat it as a problem-solving tool first. It shines when the party asks the world a question instead of trying to damage it.'
    if 'damage' in tag_set and 'aoe' in tag_set:
        return 'Aim for clustered enemies, chokepoints, or turns where forcing multiple saves matters more than focusing one target.'
    if 'damage' in tag_set:
        return 'Use it when you need efficient pressure without overcommitting bigger resources.'
    if concentration:
        return 'Plan your concentration around this spell; the value comes from keeping it active long enough to matter.'
    return ''


def _build_description(name: str, level: int, school: str, cast_time: str, range_text: str, duration: str, concentration: bool,
                      attack_type: str, save: str, damage_formula: str, damage_type: str, healing_formula: str, effect: str,
                      scaling_note: str, area_text: str, tags: list[str]) -> str:
    school_text = school or 'magic'
    target_text = area_text or range_text or 'range'
    opener = f'{name} is a {"cantrip" if level == 0 else f"level {level}"} {school_text.lower()} spell cast with {cast_time.lower() if cast_time else "an action"} at {target_text.lower()}.'
    effect_text = _clean(effect).rstrip('.')
    if healing_formula:
        body = f'It restores {healing_formula} to its target or targets. {effect_text + "." if effect_text else ""}'.strip()
    elif attack_type:
        body = f'Resolve it with a {attack_type.lower()}. On a hit, it applies {damage_formula or "the listed"} {damage_type + " " if damage_type else ""}damage{(" and " + effect_text.lower()) if effect_text else ""}.'
    elif save:
        body = f'Creatures affected by the spell make a {_save_label(save).lower()}. On a failed save, apply {damage_formula or effect_text or "the spell’s main effect"}; on a success, reduce or avoid the effect as the spell indicates.'
    else:
        themed = _themed_effect_text(name, school_text, range_text, duration)
        body = effect_text or themed or f'It creates a {school_text.lower()} effect focused on utility, positioning, support, or control rather than direct damage.'
    timing_bits = []
    if concentration:
        timing_bits.append('It requires concentration, so starting another concentration spell will end it.')
    if duration and duration.lower() not in ('instantaneous', 'instant'):
        timing_bits.append(f'Its effect can persist for {duration.lower()}.')
    tactical = _tactical_hint_from_tags(name, tags, concentration)
    if tactical:
        timing_bits.append(tactical)
    extra = _clean(scaling_note)
    return '\n\n'.join([part for part in [f'{opener} {body}'.strip(), ' '.join(timing_bits).strip(), extra] if part])


def enrich_spell_row(raw: dict[str, Any]) -> dict[str, Any]:
    row = dict(raw or {})
    spell_id = _slug(row.get('id') or row.get('displayName') or row.get('name') or 'spell')
    open_row = _open5e_index().get(spell_id, {})
    override = _MANUAL_OVERRIDES.get(spell_id, {})
    placeholder_local = _is_placeholder_catalog_text(row.get('description'))

    name = _pick_preferred_text(override.get('displayName'), row.get('displayName'), row.get('name'), open_row.get('name'), spell_id.replace('-', ' ').title())
    level = int(override.get('level') or row.get('level') or row.get('spell_level') or open_row.get('spell_level') or 0)
    school = _pick_preferred_text(override.get('school'), open_row.get('school'), row.get('school'))
    cast_time = _pick_preferred_text(override.get('castingTime'), open_row.get('casting_time'), row.get('castingTime'), row.get('casting_time'), '1 action')
    range_text = _pick_preferred_text(override.get('range'), open_row.get('range'), row.get('range'))
    components = _merge_components(override.get('components') or open_row.get('components') or row.get('components'), open_row.get('material_component_text'))
    duration = _pick_preferred_text(override.get('duration'), open_row.get('duration'), row.get('duration'), 'Instantaneous')
    concentration = bool(override.get('concentration') if override.get('concentration') is not None else open_row.get('concentration') if open_row else row.get('concentration'))
    ritual = bool(override.get('ritual') if override.get('ritual') is not None else open_row.get('ritual') if open_row else row.get('ritual'))

    classes_source = override.get('classes') or open_row.get('class_lists') or row.get('classes') or []
    classes = [str(v).strip() for v in classes_source if str(v).strip()]

    area = open_row.get('area_data') if isinstance(open_row.get('area_data'), dict) else {}
    area_shape = _clean(area.get('shape'))
    area_size = _clean(area.get('size'))
    area_text = ' '.join([v for v in [area_size, area_shape] if v]).strip()

    tags = [str(v).strip().lower() for v in (override.get('tags') or open_row.get('tags') or row.get('tags') or []) if str(v).strip()]
    if concentration and 'concentration' not in tags:
        tags.append('concentration')
    if ritual and 'ritual' not in tags:
        tags.append('ritual')
    for needle, tag in _KEYWORD_TAGS:
        if needle in name.lower() and tag not in tags:
            tags.append(tag)

    if 'damageType' in override:
        damage_type = _clean(override.get('damageType'))
    else:
        damage_type = _pick_preferred_text(open_row.get('damage_type'), row.get('damageType'))
    damage_type = _guess_damage_type(name, damage_type, school)

    healing_formula = _pick_preferred_text(override.get('healingFormula'), row.get('healingFormula'))
    if not healing_formula and open_row.get('healing_type'):
        healing_formula = 'See spell text'

    attack_type = _pick_preferred_text(override.get('attackType'), open_row.get('attack_type'), row.get('attackType')).replace('_', ' ').title()
    saving_throw = _pick_preferred_text(override.get('savingThrow'), open_row.get('save_ability'), row.get('savingThrow')).upper()

    base_effect = _pick_preferred_text(override.get('effect'), open_row.get('base_effect_text'), row.get('effect'))
    if placeholder_local and not base_effect:
        base_effect = _clean(open_row.get('base_effect_text'))

    if not attack_type and not saving_throw:
        attack_type, saving_throw = _guess_attack_or_save(name, level, school, damage_type, tags, base_effect)

    damage_formula = _pick_preferred_text(override.get('damageFormula'), open_row.get('base_damage_formula'), row.get('damageFormula'))
    if not damage_formula and not healing_formula:
        damage_formula = _guess_formula(level, attack_type, saving_throw, name, damage_type, tags)

    scaling_note = _pick_preferred_text(override.get('scalingNote'), open_row.get('higher_level_text'), row.get('scalingNote'), row.get('higher_levels'), row.get('atHigherLevels'))
    if not scaling_note:
        scaling_note = _generic_scaling(name, level, damage_formula, healing_formula)

    if damage_formula and 'damage' not in tags and not healing_formula:
        tags.append('damage')
    if healing_formula and 'healing' not in tags:
        tags.append('healing')
    if attack_type and 'attack' not in tags:
        tags.append('attack')
    if saving_throw and 'save' not in tags:
        tags.append('save')

    description = _clean(override.get('description'))
    if not description:
        description = _build_description(
            name=name,
            level=level,
            school=school,
            cast_time=cast_time,
            range_text=range_text,
            duration=duration,
            concentration=concentration,
            attack_type=attack_type,
            save=saving_throw,
            damage_formula=damage_formula,
            damage_type=damage_type,
            healing_formula=healing_formula,
            effect=base_effect,
            scaling_note=scaling_note,
            area_text=area_text,
            tags=tags,
        )

    summary_effect = base_effect or (f'{damage_formula} {damage_type}'.strip() if damage_formula or damage_type else '') or (healing_formula if healing_formula else '')
    short_summary_parts = [
        'Cantrip' if level == 0 else f'Level {level}',
        school,
        summary_effect,
    ]
    short_summary = ' • '.join([p for p in short_summary_parts if p])

    row.update({
        'id': spell_id,
        'displayName': name,
        'name': name,
        'level': level,
        'school': school,
        'castingTime': cast_time,
        'range': range_text,
        'components': components,
        'duration': duration,
        'classes': classes,
        'description': description,
        'damageType': damage_type or row.get('damageType'),
        'damageFormula': damage_formula or row.get('damageFormula'),
        'healingFormula': healing_formula or row.get('healingFormula'),
        'attackType': attack_type or row.get('attackType'),
        'savingThrow': saving_throw or row.get('savingThrow'),
        'scalingNote': scaling_note,
        'effect': base_effect or row.get('effect') or '',
        'tags': list(dict.fromkeys([t for t in tags if t])),
        'shortPlayerSummary': short_summary,
        'fullPlayerDetailText': description,
        'playerFacingEffectSummary': summary_effect or short_summary,
        'higherLevel': scaling_note,
        'concentration': concentration,
        'ritual': ritual,
        'areaText': area_text,
    })
    return row
