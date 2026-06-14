from __future__ import annotations

from typing import Any


STAGE4B_AUTHORED_OVERRIDES: dict[str, dict[str, Any]] = {
    'fireball': {
        'savingThrow': 'DEX',
        'damageType': 'fire',
        'damageFormula': '8d6',
        'school': 'Evocation',
        'castingTime': '1 action',
        'range': '150 feet',
        'duration': 'Instantaneous',
        'areaText': '20-foot radius sphere',
        'effect': 'Explosive sphere of fire; Dexterity save for half',
        'scalingNote': 'Each slot level above 3rd adds 1d6 fire damage.',
        'scaling_type': 'slot_damage',
        'scaling_data': {'base_slot': 3, 'base_formula': '8d6', 'per_slot_formula': '1d6'},
        'description': (
            'Choose a point within range and erupt it into a roaring sphere of flame. '
            'Creatures in the blast make a Dexterity save. A failure takes full fire damage; '
            'a success takes half.\n\n'
            'Use this spell to clear clusters, punish enemies hiding behind cover edges, or '
            'force concentration checks across a wide area.'
        ),
        'tags': ['damage', 'save', 'aoe', 'fire'],
    },
    'absorb-elements': {
        'damageType': 'elemental',
        'damageFormula': '1d6',
        'castingTime': '1 reaction',
        'effect': 'Halve incoming elemental damage and add it to your next melee strike',
        'scalingNote': 'Each slot level above 1st adds 1d6 elemental damage to the melee strike.',
        'scaling_type': 'slot_damage',
        'scaling_data': {'base_slot': 1, 'base_formula': '1d6', 'per_slot_formula': '1d6'},
        'description': (
            'Use your reaction when you take acid, cold, fire, lightning, or thunder damage. '
            'You have resistance to the triggering damage type and the spell stores the energy in you until your next turn. '
            'Your first melee attack on your next turn deals an extra 1d6 of that damage type per slot level used.\n\n'
            'Absorb Elements is outstanding value: it halves a big hit AND delivers a revenge strike.'
        ),
        'tags': ['reaction', 'defense', 'elemental', 'damage'],
    },
    'fire-bolt': {
        'attackType': 'Ranged Spell Attack',
        'damageType': 'fire',
        'damageFormula': '1d10',
        'scalingNote': 'At character levels 5, 11, and 17 the fire damage increases to 2d10, 3d10, and 4d10.',
        'effect': 'Single-target fire blast',
        'description': (
            'Hurl a mote of fire at a creature or unattended flammable object you can see. Make a ranged spell attack; on a hit, the target takes fire damage. '
            'Loose combustible objects can ignite if the table agrees they should burn.\n\n'
            'This is a bread-and-butter ranged cantrip for blaster casters. Use it when you want clean single-target pressure without spending a slot.'
        ),
    },
    'ray-of-frost': {
        'attackType': 'Ranged Spell Attack',
        'damageType': 'cold',
        'damageFormula': '1d8',
        'effect': 'Cold hit and speed reduced by 10 feet',
        'scalingNote': 'At character levels 5, 11, and 17 the damage increases to 2d8, 3d8, and 4d8.',
        'description': (
            'Launch a frigid beam at a creature in range. On a hit, it takes cold damage and its speed drops by 10 feet until the start of your next turn.\n\n'
            'Ray of Frost trades a little raw damage for control. It is excellent for peeling melee threats, slowing runners, and buying space for the party.'
        ),
    },
    'sacred-flame': {
        'savingThrow': 'DEX',
        'damageType': 'radiant',
        'damageFormula': '1d8',
        'effect': 'Radiant save cantrip that ignores cover better than most attack cantrips',
        'scalingNote': 'At character levels 5, 11, and 17 the radiant damage increases to 2d8, 3d8, and 4d8.',
        'description': (
            'Call down radiant fire on a creature you can see. The target makes a Dexterity save; on a failure it takes radiant damage.\n\n'
            'Sacred Flame is a reliable divine cantrip when attack rolls are awkward or cover is getting in the way. It is strong against foes who depend on Armor Class instead of saves.'
        ),
    },
    'toll-the-dead': {
        'savingThrow': 'WIS',
        'damageType': 'necrotic',
        'damageFormula': '1d8 or 1d12 against a wounded target',
        'effect': 'Necrotic save cantrip that hits harder after the target is injured',
        'scalingNote': 'At character levels 5, 11, and 17 the damage scales to 2 dice, 3 dice, and 4 dice of the appropriate size.',
        'description': (
            'Sound a grim bell at a creature you can see. The target makes a Wisdom save. On a failure it takes necrotic damage, and the die size increases if the target is already missing hit points.\n\n'
            'This is one of the best cantrips for finishing hurt enemies. Let the front line wound the target first, then ring the bell for the larger die.'
        ),
    },
    'mage-hand': {
        'effect': 'Create a floating spectral hand for simple object interaction',
        'description': (
            'Create a hovering magical hand that can manipulate light objects, open simple containers, move unattended gear, or perform other basic interactions at a distance.\n\n'
            'Mage Hand is a pure utility cantrip. Use it for traps, awkward ledges, suspicious objects, or any moment where keeping your body out of danger matters.'
        ),
    },
    'minor-illusion': {
        'effect': 'Create a small sound or image to distract, hide, or misdirect',
        'description': (
            'Create a brief sensory deception such as a sound or a compact image within range. The illusion stays within the spell’s limits until dismissed, disturbed, or closely inspected.\n\n'
            'Minor Illusion rewards clever play. It is best for distraction, bait, hiding sight lines, fake cover, or pulling guards into a bad position rather than raw damage.'
        ),
    },
    'prestidigitation': {
        'effect': 'Tiny magical tricks for cleaning, marking, flavoring, or harmless stagecraft',
        'description': (
            'Perform a pocket-sized magical trick: clean or soil objects, create fleeting sensory effects, mark surfaces, light or snuff small flames, or produce other harmless bits of magical flair.\n\n'
            'Prestidigitation is a roleplay and utility cantrip. It shines in infiltration, social scenes, flavor, and problem solving where small details matter.'
        ),
    },
    'shillelagh': {
        'damageType': 'force',
        'damageFormula': 'Weapon damage using your spellcasting ability',
        'effect': 'Empower a club or staff for magical melee attacks',
        'description': (
            'Imbue a club or quarterstaff with primal power so it counts as magical and attacks through your spellcasting ability instead of raw Strength.\n\n'
            'Shillelagh is a bridge spell for nature casters who want to fight in melee without splitting their stats too thin.'
        ),
    },
    'shocking-grasp': {
        'attackType': 'Melee Spell Attack',
        'damageType': 'lightning',
        'damageFormula': '1d8',
        'effect': 'Lightning melee hit that disrupts reactions',
        'scalingNote': 'At character levels 5, 11, and 17 the lightning damage increases to 2d8, 3d8, and 4d8.',
        'description': (
            'Deliver a crackling electric touch. Make a melee spell attack; on a hit, the target takes lightning damage and has trouble using reactions before your next turn.\n\n'
            'This cantrip is excellent for slipping away from a dangerous melee enemy after the hit lands.'
        ),
    },
    'vicious-mockery': {
        'savingThrow': 'WIS',
        'damageType': 'psychic',
        'damageFormula': '1d6',
        'effect': 'Psychic insult that weakens the target’s next attack',
        'scalingNote': 'At character levels 5, 11, and 17 the psychic damage increases to 2d6, 3d6, and 4d6.',
        'description': (
            'Loose a cutting insult laced with magic at a creature that can hear you. It makes a Wisdom save; on a failure it takes psychic damage and suffers disadvantage on its next attack before your next turn.\n\n'
            'Use Vicious Mockery to chip at targets while also softening incoming pressure on the party.'
        ),
    },
    'thorn-whip': {
        'attackType': 'Melee Spell Attack',
        'damageType': 'piercing',
        'damageFormula': '1d6',
        'effect': 'Pull a target closer with a magical thorn lash',
        'scalingNote': 'At character levels 5, 11, and 17 the damage increases to 2d6, 3d6, and 4d6.',
        'description': (
            'Snap out a vine-like lash at a creature in range. On a hit it takes piercing damage and is yanked closer to you.\n\n'
            'Thorn Whip is a positioning cantrip. Pull enemies off ledges, into hazards, through choke points, or into your fighter’s threatened space.'
        ),
    },
    'spare-the-dying': {
        'effect': 'Stabilize a dying creature without spending a slot',
        'description': (
            'Touch a dying creature and stabilize it so it stops making death saves and stops bleeding toward death.\n\n'
            'Spare the Dying is an emergency tool, not a true heal. It keeps someone alive long enough for real recovery or battlefield extraction.'
        ),
    },
    'poison-spray': {
        'savingThrow': 'CON',
        'damageType': 'poison',
        'damageFormula': '1d12',
        'effect': 'Short-range poison burst against a single target',
        'scalingNote': 'At character levels 5, 11, and 17 the poison damage increases to 2d12, 3d12, and 4d12.',
        'description': (
            'Blast a nearby creature with toxic vapor. The target makes a Constitution save; on a failure it takes poison damage.\n\n'
            'Poison Spray hits hard for a cantrip, but the range is short and many monsters resist poison. Use it when you are already close and the target is vulnerable.'
        ),
    },
    'produce-flame': {
        'attackType': 'Ranged Spell Attack',
        'damageType': 'fire',
        'damageFormula': '1d8',
        'effect': 'Conjure flame for light now or a thrown fire attack later',
        'scalingNote': 'At character levels 5, 11, and 17 the fire damage increases to 2d8, 3d8, and 4d8.',
        'description': (
            'Call a flame into your hand. It can shed light while held, or you can hurl it at a creature as a ranged spell attack that deals fire damage on a hit.\n\n'
            'Produce Flame is flexible because it doubles as both a light source and an attack cantrip.'
        ),
    },
    'thunderwave': {
        'savingThrow': 'CON',
        'damageType': 'thunder',
        'damageFormula': '2d8',
        'effect': 'Close-range thunder blast that pushes creatures away',
        'scalingNote': 'Each slot level above 1st adds 1d8 thunder damage.',
        'description': (
            'Release a violent wave of thunderous force from yourself. Creatures in the area make a Constitution save; on a failure they take thunder damage and are pushed away from you, while a success reduces the damage.\n\n'
            'Thunderwave is part damage spell and part panic button. Use it when enemies have collapsed onto your position or when you want to blast creatures off edges and out of formation.'
        ),
    },
    'burning-hands': {
        'savingThrow': 'DEX',
        'damageType': 'fire',
        'damageFormula': '3d6',
        'effect': 'Short cone of fire that hits clustered targets',
        'scalingNote': 'Each slot level above 1st adds 1d6 fire damage.',
        'description': (
            'Fan both hands into a sweeping cone of fire. Creatures in the area make a Dexterity save; on a failure they take full fire damage, and on a success they take half.\n\n'
            'Burning Hands is ideal in cramped spaces, doorways, tunnels, or any fight where several enemies rush the same square of the map.'
        ),
    },
    'charm-person': {
        'savingThrow': 'WIS',
        'effect': 'Charm a humanoid who fails the save',
        'scalingNote': 'Each slot level above 1st lets you target one additional humanoid.',
        'description': (
            'Work subtle magic on a humanoid you can see. It makes a Wisdom save; on a failure it is charmed by you for the spell’s duration within the spell’s usual limits.\n\n'
            'Charm Person is strongest in social scenes, guards, negotiations, and escape plays. It is not a mind-control nuke, but it can change a scene before combat starts.'
        ),
    },
    'detect-magic': {
        'effect': 'Sense nearby magic and study its aura',
        'description': (
            'Extend your senses for nearby magic. While the spell lasts, you can detect magical presence nearby and spend actions focusing to identify faint auras and magical schools on what you sense.\n\n'
            'Detect Magic is a scouting and investigation staple. Cast it before opening suspicious treasure, crossing wards, or handling unknown relics.'
        ),
    },
    'fog-cloud': {
        'effect': 'Create a heavily obscured area of fog',
        'scalingNote': 'Higher slots expand the size of the fog bank.',
        'description': (
            'Fill an area with thick magical fog that blocks sight through the cloud.\n\n'
            'Fog Cloud is for control, retreat, ambushes, and breaking enemy targeting. It can help the party escape or make ranged attackers miserable, but it also blinds your side if placed carelessly.'
        ),
    },
    'guiding-bolt': {
        'attackType': 'Ranged Spell Attack',
        'damageType': 'radiant',
        'damageFormula': '4d6',
        'effect': 'Radiant bolt that lights up the target for the next attacker',
        'scalingNote': 'Each slot level above 1st adds 1d6 radiant damage.',
        'description': (
            'Throw a streak of divine radiance at a creature. Make a ranged spell attack; on a hit the target takes radiant damage and is outlined by light, setting up the next attack against it.\n\n'
            'Guiding Bolt is fantastic opening pressure because it combines strong damage with team support.'
        ),
    },
    'sanctuary': {
        'savingThrow': 'WIS',
        'effect': 'Ward a creature so attackers must fight through holy hesitation',
        'description': (
            'Wrap a creature in protective magic. Creatures trying to directly attack or harm the warded target must push through the spell’s saving throw gate first.\n\n'
            'Sanctuary buys time. Use it to protect a dying ally, a fragile caster, or an NPC who needs to survive the round.'
        ),
    },
    'sleep': {
        'effect': 'Drop creatures into magical slumber based on the pool rolled',
        'description': (
            'Roll the spell’s sleep pool and compare it against creatures in the chosen area, starting with the lowest current hit points. Creatures covered by the pool fall unconscious until the spell ends or they are disturbed.\n\n'
            'Sleep is strongest early, against weak groups, or for silent takedowns. It falls off against tougher enemies once their hit point totals climb.'
        ),
    },
    'heroism': {
        'effect': 'Grant courage and recurring temporary hit points',
        'description': (
            'Bolster a willing creature with supernatural bravery. While concentration lasts, the target resists fear and gains a fresh layer of temporary hit points at the spell’s recurring interval.\n\n'
            'Heroism is a clean pre-fight buff when you expect fear pressure or repeated chip damage.'
        ),
    },
    'inflict-wounds': {
        'attackType': 'Melee Spell Attack',
        'damageType': 'necrotic',
        'damageFormula': '3d10',
        'effect': 'Heavy melee necrotic hit',
        'scalingNote': 'Each slot level above 1st adds 1d10 necrotic damage.',
        'description': (
            'Channel ruin through a touch attack. Make a melee spell attack; on a hit the target takes a heavy burst of necrotic damage.\n\n'
            'Inflict Wounds is one of the nastiest single-target hits at low level, but it demands that you get dangerously close.'
        ),
    },
    'command': {
        'savingThrow': 'WIS',
        'effect': 'Force a creature to obey a brief one-word order',
        'scalingNote': 'Each slot level above 1st lets you affect one additional creature.',
        'description': (
            'Speak a sharp magical command to a creature that can understand you. It makes a Wisdom save; on a failure it follows the brief order on its next turn as long as the command fits the spell’s limits.\n\n'
            'Command is flexible control. It can force movement, drop items, waste turns, or open space for the party without dealing direct damage.'
        ),
    },
    'goodberry': {
        'healingFormula': 'Up to 10 berries that each restore 1 hit point',
        'effect': 'Create restorative berries that also count as emergency food',
        'description': (
            'Create a bundle of magical berries. Each berry can be eaten later to restore a small amount of health, and the spell also covers basic nourishment for the day within its usual limits.\n\n'
            'Goodberry is quiet, efficient healing and excellent travel prep. It is especially valuable before rest, exploration, or attrition-heavy adventures.'
        ),
    },
    'armor-of-agathys': {
        'damageType': 'cold',
        'effect': 'Temporary hit points with retaliatory cold damage',
        'scalingNote': 'Higher slots increase both the temporary hit points and the cold damage returned to attackers.',
        'description': (
            'Coat yourself in punishing frost. The spell grants temporary hit points, and creatures that hit you in melee are blasted by cold while the ward holds.\n\n'
            'Armor of Agathys is best on characters who expect to be hit repeatedly and want every incoming swing to hurt the attacker back.'
        ),
    },
    'hellish-rebuke': {
        'savingThrow': 'DEX',
        'damageType': 'fire',
        'damageFormula': '2d10',
        'effect': 'Reaction fire retaliation when a creature hurts you',
        'scalingNote': 'Each slot level above 1st adds 1d10 fire damage.',
        'description': (
            'Answer pain with infernal flame as a reaction. The creature that triggered the spell makes a Dexterity save; on a failure it takes full fire damage, and on a success it takes half.\n\n'
            'Hellish Rebuke is pure punishment. Save it for enemies who thought hitting you was free.'
        ),
    },
    'faerie-fire': {
        'savingThrow': 'DEX',
        'effect': 'Outline creatures in light so attacks find them more easily',
        'description': (
            'Dust creatures in the area with visible magical light. Targets that fail the Dexterity save glow for the duration, making them easier to track and hit while the spell lasts.\n\n'
            'Faerie Fire is a team spell. It turns hard-to-hit enemies into focus-fire targets and helps the party against darkness, invisibility tricks, and slippery skirmishers.'
        ),
    },
    'entangle': {
        'savingThrow': 'STR',
        'effect': 'Area control that restrains creatures in grasping growth',
        'description': (
            'Burst a patch of ground into twisting plants. Creatures in the area make a Strength save; on a failure they are restrained until they break free or the spell ends.\n\n'
            'Entangle is early battlefield control at its simplest: pin the front line, split the fight, and make the enemy spend actions escaping.'
        ),
    },
    'blindness-deafness': {
        'savingThrow': 'CON',
        'effect': 'Blind or deafen a creature on a failed save; it can repeat the save at the end of its turns',
        'description': (
            'Assault a creature\'s senses with crippling magic. It makes a Constitution save; on a failure you choose whether it becomes blinded or deafened for the duration, with repeated saves available at the end of its turns.\n\n'
            'Blindness/Deafness is a clean shutdown spell against dangerous attackers, archers, and casters who need line of sight or awareness to function properly.'
        ),
    },
    'hold-person': {
        'savingThrow': 'WIS',
        'effect': 'Paralyze a humanoid while concentration lasts',
        'scalingNote': 'Each slot level above 2nd lets you target one additional humanoid.',
        'description': (
            'Lock a humanoid in place with paralyzing magic. The target makes a Wisdom save; on a failure it is paralyzed for the duration while you keep concentration.\n\n'
            'Hold Person is lethal when your melee allies can reach the target. Use it on dangerous humanoid bosses, duelists, and casters you need to shut down now.'
        ),
    },
    'detect-thoughts': {
        'savingThrow': 'WIS',
        'effect': 'Read surface thoughts and probe deeper with pressure',
        'description': (
            'Open your mind to nearby thinking creatures. You can skim surface thoughts, then push deeper on a chosen mind if the spell’s save gate is failed.\n\n'
            'Detect Thoughts is an investigation and social pressure spell. It can expose lies, hidden motives, and ambushes, but obvious use may also escalate a scene.'
        ),
    },
    'misty-step': {
        'effect': 'Bonus-action short teleport',
        'description': (
            'Blink through space and reappear at a nearby point you can reach with the spell.\n\n'
            'Misty Step is one of the best mobility spells in the game. Use it to escape grapples, hop ledges, leave melee, cross gaps, or steal a winning position without spending your action.'
        ),
    },
    'scorching-ray': {
        'attackType': 'Ranged Spell Attack',
        'damageType': 'fire',
        'damageFormula': '3 × 2d6',
        'effect': 'Multiple fire rays that can focus or split targets',
        'scalingNote': 'Each slot level above 2nd adds one extra ray.',
        'description': (
            'Create several rays of fire and hurl them at creatures you can see. Each ray makes its own ranged spell attack and deals fire damage on a hit.\n\n'
            'Scorching Ray is flexible burst damage. Focus all rays on one target for a spike turn or spread them around to finish several wounded enemies.'
        ),
    },
    'shatter': {
        'savingThrow': 'CON',
        'damageType': 'thunder',
        'damageFormula': '3d8',
        'effect': 'Thunder burst that punishes creatures and fragile objects in an area',
        'scalingNote': 'Each slot level above 2nd adds 1d8 thunder damage.',
        'description': (
            'Detonate a painfully loud pulse in a compact area. Creatures make a Constitution save for half; on a failure they take full thunder damage. Unsecured, nonmagical objects in the area can also be wrecked.\n\n'
            'Shatter is a dependable compact AoE for tight rooms, clustered enemies, and scenes where breaking objects is part of the plan.'
        ),
    },
    'suggestion': {
        'savingThrow': 'WIS',
        'effect': 'Plant a compelling course of action in the target’s mind',
        'description': (
            'Speak a magically persuasive idea to a creature that can hear and understand you. It makes a Wisdom save; on a failure it follows the suggested course of action within the spell’s limits for the duration.\n\n'
            'Suggestion is subtle, powerful control. It wins scenes before swords come out if you frame the command cleverly and believably.'
        ),
    },
    'invisibility': {
        'effect': 'Turn a creature unseen until the spell ends or its cover is broken',
        'scalingNote': 'Higher slots can extend the spell to additional targets when supported by the final tuning.',
        'description': (
            'Render a creature unseen for the spell’s duration until the usual breaking conditions are met.\n\n'
            'Invisibility is for scouting, theft, escape, and repositioning. It is strongest before initiative or when someone absolutely must cross a dangerous space unseen.'
        ),
    },
    'web': {
        'savingThrow': 'DEX',
        'effect': 'Fill an area with sticky restraint and difficult terrain',
        'description': (
            'Spread dense magical webbing through an area, turning it into a movement problem and trapping creatures that fail the save.\n\n'
            'Web is premium battlefield control. It blocks corridors, burns actions, and sets up the rest of the party to safely destroy pinned enemies.'
        ),
    },
    'darkness': {
        'effect': 'Create a zone of magical darkness that blocks normal sight',
        'description': (
            'Create a sphere of magical darkness that ordinary vision cannot see through.\n\n'
            'Darkness is a positioning spell. It can shut down ranged lines, protect retreats, and create chaos, but your own team also has to function inside the blackout.'
        ),
    },
    'pass-without-trace': {
        'effect': 'Boost the whole group’s stealth and cover their tracks',
        'description': (
            'Wrap your group in muting shadows and drifting natural cover. Affected creatures gain a strong bonus to stealth and leave far less trace behind.\n\n'
            'Pass without Trace is the spell for infiltration nights, scouting parties, and bypassing fights you never wanted to take.'
        ),
    },
    'lesser-restoration': {
        'effect': 'End a common harmful condition on a creature you touch',
        'description': (
            'Touch a creature and purge one of the common lingering afflictions the spell is designed to end.\n\n'
            'Lesser Restoration is a toolkit spell. Keep it ready when poison, paralysis, disease, or similar status effects are likely to derail the party.'
        ),
    },
    'aid': {
        'healingFormula': '+5 current and maximum hit points to up to 3 creatures',
        'effect': 'Raise current and maximum hit points for multiple allies',
        'scalingNote': 'Each slot level above 2nd adds 5 more hit points to the grant.',
        'description': (
            'Bolster up to three creatures with durable magical vigor. Each target’s current hit points and maximum hit points both increase for the duration.\n\n'
            'Aid is outstanding before a hard fight because it stacks more staying power onto several allies at once.'
        ),
    },
    'prayer-of-healing': {
        'healingFormula': 'Party healing after a longer cast',
        'effect': 'Slow-cast group healing outside immediate danger',
        'scalingNote': 'Higher slots improve the healing delivered to each affected creature.',
        'description': (
            'Lead a longer restorative prayer that heals multiple creatures after the casting completes.\n\n'
            'Prayer of Healing is not for the middle of a frantic round. It is for regrouping after the fight, preserving other resources, and patching up several allies at once.'
        ),
    },
    'locate-object': {
        'effect': 'Point yourself toward a known object within the spell’s search limit',
        'description': (
            'Tune your senses toward a specific object or the nearest instance of a known kind of object. The spell points you in its direction while it remains within the search boundary.\n\n'
            'Locate Object is a problem-solver for investigations, theft recovery, dungeon keys, missing gear, and quietly tracking a target item.'
        ),
    },
    'magic-weapon': {
        'effect': 'Temporarily enhance a weapon’s accuracy and damage as magical',
        'description': (
            'Imbue a nonmagical weapon with arcane force so it becomes magical and hits harder for the duration.\n\n'
            'Magic Weapon matters when the party lacks enchanted gear or needs to punch through resistance with the front line.'
        ),
    },
    'moonbeam': {
        'savingThrow': 'CON',
        'damageType': 'radiant',
        'damageFormula': '2d10',
        'effect': 'Concentration beam that burns creatures entering or starting in it',
        'scalingNote': 'Each slot level above 2nd adds 1d10 radiant damage.',
        'description': (
            'Call down a cylinder of pale radiance. Creatures caught in the beam make a Constitution save and take radiant damage on a failure, and the beam continues threatening the area while concentration lasts.\n\n'
            'Moonbeam is a zone-control damage spell. Park it where enemies want to stand, or drag it across a battlefield that keeps shifting.'
        ),
    },
    'silence': {
        'effect': 'Create a sphere where sound cannot pass and verbal casting is shut down',
        'description': (
            'Smother a region in magical quiet so sound cannot pass into or out of it.\n\n'
            'Silence is a tactical scalpel. Drop it on enemy casters, alarms, sentries, or any scene where sound is the real threat.'
        ),
    },
    'spider-climb': {
        'effect': 'Let a creature move across walls and ceilings',
        'description': (
            'Grant a creature the ability to move along walls and ceilings as easily as along the floor for the duration.\n\n'
            'Spider Climb rewrites positioning. It wins vertical encounters, bypasses traps, and opens routes the map was not expecting players to use.'
        ),
    },
    'flaming-sphere': {
        'savingThrow': 'DEX',
        'damageType': 'fire',
        'damageFormula': '2d6',
        'effect': 'Rolling fire sphere that occupies space and keeps pressuring targets',
        'scalingNote': 'Each slot level above 2nd adds 1d6 fire damage.',
        'description': (
            'Summon a roiling globe of fire that can be rammed into creatures and left threatening a patch of the battlefield while concentration lasts.\n\n'
            'Flaming Sphere is steady action-economy pressure. It keeps dealing meaningful damage while your action goes elsewhere.'
        ),
    },
}



STAGE4C_AUTHORED_OVERRIDES: dict[str, dict[str, Any]] = {'animate-dead': {'school': 'Necromancy',
                  'castingTime': '1 minute',
                  'range': '10 feet',
                  'components': 'V, S, M',
                  'duration': 'Instantaneous',
                  'classes': ['Cleric', 'Wizard'],
                  'effect': 'Raise a corpse or skeleton as an undead servant you must reassert control over each day',
                  'scalingNote': 'When you cast this spell with a slot above 3rd, you can animate or reassert control '
                                 'over two additional undead for each slot level above 3rd.',
                  'description': 'Imbue bones or a corpse with necromantic force and raise it as an undead servant. '
                                 'The creature follows your spoken commands for a limited time, but you must spend '
                                 'magic again to keep control after that window ends.\n'
                                 '\n'
                                 'Animate Dead is long-form resource magic. It is strongest between fights, during '
                                 'downtime, or in campaigns where preparation and disposable bodies matter more than '
                                 'one-turn burst damage.',
                  'tags': ['summon', 'necromancy', 'utility']},
 'bestow-curse': {'school': 'Necromancy',
                  'castingTime': '1 action',
                  'range': 'Touch',
                  'components': 'V, S',
                  'duration': 'Up to 1 minute',
                  'concentration': True,
                  'classes': ['Bard', 'Cleric', 'Warlock', 'Wizard'],
                  'savingThrow': 'WIS',
                  'effect': 'Lay a curse on a creature that weakens checks, attacks, or other parts of its game plan',
                  'scalingNote': 'At higher cast levels the curse can last longer, and at very high slot tiers some '
                                 'tables may no longer require concentration.',
                  'description': 'Touch a creature and attempt to bind it with hostile magic. The target resists with '
                                 'a Wisdom save, and on a failure it suffers a curse chosen from the spell’s available '
                                 'modes or your table’s approved variant.\n'
                                 '\n'
                                 'Bestow Curse is a boss-fight control tool. Use it to ruin a dangerous attacker, shut '
                                 'down a key ability score, or build a longer tactical advantage around one high-value '
                                 'target.',
                  'tags': ['control', 'save', 'concentration']},
 'blink': {'school': 'Transmutation',
           'castingTime': '1 action',
           'range': 'Self',
           'components': 'V, S',
           'duration': '1 minute',
           'classes': ['Sorcerer', 'Wizard'],
           'effect': 'Phase in and out of the battlefield, making it harder for enemies to pin you down',
           'description': 'Wrap yourself in unstable planar motion for the next minute. At the end of your turns, the '
                          'spell can flick you out of the battlefield until the start of your next turn, causing '
                          'attacks and many effects to lose their chance to hit you.\n'
                          '\n'
                          'Blink is selfish but powerful survival magic. It shines when you need to keep concentration '
                          'alive, soak enemy focus without staying exposed, or cast from risky positions.',
           'tags': ['defense', 'mobility']},
 'call-lightning': {'school': 'Conjuration',
                    'castingTime': '1 action',
                    'range': '120 feet',
                    'components': 'V, S',
                    'duration': 'Up to 10 minutes',
                    'concentration': True,
                    'classes': ['Druid'],
                    'savingThrow': 'DEX',
                    'damageType': 'lightning',
                    'damageFormula': '3d10',
                    'effect': 'Conjure a storm cloud and call down repeatable lightning strikes while concentration '
                              'lasts',
                    'scalingNote': 'Each slot level above 3rd adds 1d10 lightning damage to each strike.',
                    'description': 'Summon a storm cloud overhead and call a bolt of lightning onto a point you can '
                                   'see below it. Creatures near the strike make a Dexterity save, taking full '
                                   'lightning damage on a failure and reduced damage on a success.\n'
                                   '\n'
                                   'Call Lightning is sustained battlefield pressure, not a one-and-done blast. It is '
                                   'best outdoors or in encounters where repeated rounds of area damage will outvalue '
                                   'an instant nuke.',
                    'areaText': '5-foot radius strike under the storm cloud',
                    'tags': ['damage', 'save', 'aoe', 'concentration']},
 'clairvoyance': {'school': 'Divination',
                  'castingTime': '10 minutes',
                  'range': '1 mile',
                  'components': 'V, S, M',
                  'duration': '10 minutes',
                  'classes': ['Bard', 'Cleric', 'Sorcerer', 'Wizard'],
                  'effect': 'Create a distant sensor that lets you see or hear from a chosen location',
                  'description': 'Open a magical sensor at a location you know or can describe. You choose whether the '
                                 'sensor relays sight or sound, and you perceive through it while the spell lasts.\n'
                                 '\n'
                                 'Clairvoyance is surveillance magic. Use it to check ambush routes, confirm a room '
                                 'before entry, spy on rituals, or gather information without physically committing '
                                 'the party.',
                  'tags': ['utility', 'divination']},
 'daylight': {'school': 'Evocation',
              'castingTime': '1 action',
              'range': '60 feet',
              'components': 'V, S',
              'duration': '1 hour',
              'classes': ['Cleric', 'Druid', 'Paladin', 'Ranger', 'Sorcerer'],
              'effect': 'Flood an area or object with powerful bright light and suppress lesser magical darkness',
              'description': 'Create a large sphere of bright light centered on a point or object. The light reaches '
                             'far, follows the chosen object if needed, and can overwhelm weaker magical darkness in '
                             'the affected area.\n'
                             '\n'
                             'Daylight is encounter-shaping utility. It is excellent in caves, undead scenes, stealth '
                             'denial, and any map where darkness was supposed to be the enemy’s advantage.',
              'tags': ['utility', 'light']},
 'fear': {'school': 'Illusion',
          'castingTime': '1 action',
          'range': 'Self',
          'components': 'V, S, M',
          'duration': 'Up to 1 minute',
          'concentration': True,
          'classes': ['Bard', 'Sorcerer', 'Warlock', 'Wizard'],
          'savingThrow': 'WIS',
          'effect': 'Project a terror wave that forces enemies to drop into panic and retreat',
          'description': 'Unleash a horrifying vision in a cone from yourself. Creatures in the area make a Wisdom '
                         'save, and those who fail become overwhelmed by fear and try to flee while the effect holds.\n'
                         '\n'
                         'Fear is battlefield breakup magic. Use it to shatter front lines, peel melee threats off the '
                         'party, or force enemies to waste turns escaping instead of fighting.',
          'areaText': '30-foot cone',
          'tags': ['control', 'fear', 'save', 'concentration', 'aoe']},
 'fly': {'school': 'Transmutation',
         'castingTime': '1 action',
         'range': 'Touch',
         'components': 'V, S, M',
         'duration': 'Up to 10 minutes',
         'concentration': True,
         'classes': ['Sorcerer', 'Warlock', 'Wizard'],
         'effect': 'Grant a target true aerial movement for the duration',
         'scalingNote': 'When cast with a slot above 3rd, you can target one additional creature for each slot level '
                        'above 3rd.',
         'description': 'Touch a creature and grant it a flying speed for the spell’s duration. The target can '
                        'maneuver freely through the air as long as concentration holds.\n'
                        '\n'
                        'Fly rewrites map geometry. Use it to take vertical control, bypass hazards, rescue trapped '
                        'allies, or give a ranged striker the best angle on the battlefield.',
         'tags': ['buff', 'mobility', 'concentration']},
 'gaseous-form': {'school': 'Transmutation',
                  'castingTime': '1 action',
                  'range': 'Touch',
                  'components': 'V, S, M',
                  'duration': 'Up to 1 hour',
                  'concentration': True,
                  'classes': ['Sorcerer', 'Warlock', 'Wizard'],
                  'effect': 'Turn a willing creature into drifting mist that can slip through tight spaces',
                  'description': 'Transform a willing creature into a cloud-like form. In this state it can float, '
                                 'seep through openings, and ignore many ordinary movement problems, but its offensive '
                                 'options become extremely limited.\n'
                                 '\n'
                                 'Gaseous Form is infiltration and escape magic. It wins bars, vents, prisons, cliff '
                                 'routes, and scenes where survival matters more than attacking right now.',
                  'tags': ['utility', 'mobility', 'concentration', 'transformation']},
 'glyph-of-warding': {'school': 'Abjuration',
                      'castingTime': '1 hour',
                      'range': 'Touch',
                      'components': 'V, S, M',
                      'duration': 'Until dispelled or triggered',
                      'classes': ['Bard', 'Cleric', 'Wizard'],
                      'effect': 'Store a harmful trigger or held spell inside a magical trap glyph',
                      'description': 'Inscribe a hidden magical glyph on a surface or inside an object. When the '
                                     'trigger conditions are met, the glyph erupts with a chosen warding effect or '
                                     'releases a stored spell according to your setup.\n'
                                     '\n'
                                     'Glyph of Warding is preparation magic. It is best in strongholds, ambushes, '
                                     'treasure rooms, fallback points, and any plan where you control the ground '
                                     'before the fight begins.',
                      'tags': ['utility', 'trap', 'defense']},
 'haste': {'school': 'Transmutation',
           'castingTime': '1 action',
           'range': '30 feet',
           'components': 'V, S, M',
           'duration': 'Up to 1 minute',
           'concentration': True,
           'classes': ['Sorcerer', 'Wizard'],
           'effect': 'Supercharge one target with speed, defense, and an extra slice of action economy',
           'description': 'Choose a creature in range and flood it with accelerated magic. While concentration lasts, '
                          'the target moves faster, becomes harder to hit, and gains an extra burst of action economy '
                          'each round inside the spell’s limits.\n'
                          '\n'
                          'Haste is one of the best payoff buffs in the game, but it comes with risk. Put it on a '
                          'creature that can convert every round of extra tempo into real pressure before '
                          'concentration breaks.',
           'tags': ['buff', 'concentration']},
 'hypnotic-pattern': {'school': 'Illusion',
                      'castingTime': '1 action',
                      'range': '120 feet',
                      'components': 'S, M',
                      'duration': 'Up to 1 minute',
                      'concentration': True,
                      'classes': ['Bard', 'Sorcerer', 'Warlock', 'Wizard'],
                      'savingThrow': 'WIS',
                      'effect': 'Fill an area with mesmerizing light that incapacitates creatures who fail the save',
                      'description': 'Shape twisting magical colors into a large cube within range. Creatures that see '
                                     'the pattern make a Wisdom save, and those who fail are left charmed, '
                                     'incapacitated, and effectively removed from the fight until something breaks the '
                                     'effect.\n'
                                     '\n'
                                     'Hypnotic Pattern is elite encounter control. It is strongest when you can catch '
                                     'several enemies at once and then focus the few who are still acting.',
                      'areaText': '30-foot cube',
                      'tags': ['control', 'save', 'concentration', 'aoe']},
 'leomunds-tiny-hut': {'displayName': "Leomund's Tiny Hut",
                       'school': 'Evocation',
                       'castingTime': '1 minute',
                       'range': 'Self',
                       'components': 'V, S, M',
                       'duration': '8 hours',
                       'ritual': True,
                       'classes': ['Bard', 'Wizard'],
                       'effect': 'Create a fixed protective dome that shelters the group during rest or watch',
                       'description': 'Create a stationary dome of force-like magical shelter around yourself and '
                                      'nearby allies. Those inside stay comfortable and protected from many outside '
                                      'environmental problems while the hut lasts.\n'
                                      '\n'
                                      'Tiny Hut is travel insurance. Use it to secure rests in hostile territory, hold '
                                      'a position during wilderness play, or buy the party breathing room in uncertain '
                                      'zones.',
                       'tags': ['ritual', 'defense', 'utility']},
 'lightning-bolt': {'school': 'Evocation',
                    'castingTime': '1 action',
                    'range': 'Self',
                    'components': 'V, S, M',
                    'duration': 'Instantaneous',
                    'classes': ['Sorcerer', 'Wizard'],
                    'savingThrow': 'DEX',
                    'damageType': 'lightning',
                    'damageFormula': '8d6',
                    'effect': 'Rip a straight line of lightning through everything caught in its path',
                    'scalingNote': 'When cast with a slot above 3rd, add 1d6 lightning damage for each slot level '
                                   'above 3rd.',
                    'description': 'Fire a crackling line of lightning in front of you. Creatures in the line make a '
                                   'Dexterity save, taking full lightning damage on a failure and reduced damage on a '
                                   'success.\n'
                                   '\n'
                                   'Lightning Bolt rewards positioning more than Fireball does. Use it through '
                                   'hallways, bridges, ranks, and chokepoints where enemies line up for punishment.',
                    'areaText': '100-foot line, 5 feet wide',
                    'tags': ['damage', 'save', 'aoe']},
 'major-image': {'school': 'Illusion',
                 'castingTime': '1 action',
                 'range': '120 feet',
                 'components': 'V, S, M',
                 'duration': 'Up to 10 minutes',
                 'concentration': True,
                 'classes': ['Bard', 'Sorcerer', 'Warlock', 'Wizard'],
                 'effect': 'Create a large multisensory illusion that can fool creatures and reshape a scene',
                 'description': 'Create a substantial illusion that can include image, sound, smell, and temperature '
                                'cues within the spell’s limits. The illusion persists while concentration lasts and '
                                'can be used to bait movement, hide truth, or dominate a scene.\n'
                                '\n'
                                'Major Image is not raw damage, but it can win encounters through deception. Treat it '
                                'like a battlefield prop director rather than a direct attack.',
                 'tags': ['illusion', 'utility', 'concentration']},
 'mass-healing-word': {'school': 'Evocation',
                       'castingTime': '1 bonus action',
                       'range': '60 feet',
                       'components': 'V',
                       'duration': 'Instantaneous',
                       'classes': ['Cleric'],
                       'healingFormula': '1d4 + spellcasting modifier',
                       'effect': 'Restore hit points to several allies you can see with a bonus action cast',
                       'scalingNote': 'When cast with a slot above 3rd, add 1d4 healing for each slot level above 3rd.',
                       'description': 'Release a burst of spoken healing that reaches multiple creatures you can see. '
                                      'Each chosen ally regains a modest amount of hit points, making the spell ideal '
                                      'for spreading recovery instead of topping off one person.\n'
                                      '\n'
                                      'Mass Healing Word is a tempo spell. It is best when several allies need to get '
                                      'back on their feet at once and you still want to keep your action free.',
                       'tags': ['healing', 'support']},
 'nondetection': {'school': 'Abjuration',
                  'castingTime': '1 action',
                  'range': 'Touch',
                  'components': 'V, S, M',
                  'duration': '8 hours',
                  'classes': ['Bard', 'Ranger', 'Wizard'],
                  'effect': 'Hide a creature, object, or place from divination magic and magical tracking',
                  'description': 'Ward a target so many forms of magical surveillance and divination fail to read it '
                                 'cleanly. The protection lasts for hours and is ideal when the enemy has access to '
                                 'scrying, magical search tools, or supernatural hunters.\n'
                                 '\n'
                                 'Nondetection matters most in plot-heavy campaigns. It is how you keep secrets, hide '
                                 'artifacts, and move under magical scrutiny without broadcasting your location.',
                  'tags': ['utility', 'defense']},
 'plant-growth': {'school': 'Transmutation',
                  'castingTime': '1 action',
                  'range': '150 feet',
                  'components': 'V, S',
                  'duration': 'Instantaneous',
                  'classes': ['Bard', 'Druid', 'Ranger'],
                  'effect': 'Explode natural plant life into thick terrain that slows movement or enriches land over '
                            'time',
                  'description': 'Supercharge existing plant life in a wide area. In combat, the ground can become '
                                 'brutally difficult to cross; outside combat, the spell can instead enrich fertile '
                                 'land for longer-term value.\n'
                                 '\n'
                                 'Plant Growth is one of the nastiest non-damage area control spells in natural '
                                 'terrain. Use it to break charges, protect retreats, or control where the fight is '
                                 'allowed to happen.',
                  'areaText': '100-foot radius',
                  'tags': ['control', 'utility', 'terrain']},
 'protection-from-energy': {'school': 'Abjuration',
                            'castingTime': '1 action',
                            'range': 'Touch',
                            'components': 'V, S',
                            'duration': 'Up to 1 hour',
                            'concentration': True,
                            'classes': ['Artificer', 'Cleric', 'Druid', 'Ranger', 'Sorcerer', 'Wizard'],
                            'effect': 'Give one creature resistance against a chosen elemental damage type',
                            'description': 'Touch a creature and shield it against one elemental damage type of your '
                                           'choice. For the duration, that target resists that form of damage while '
                                           'concentration holds.\n'
                                           '\n'
                                           'Protection from Energy is pre-emptive defense. Cast it when you know the '
                                           'dragon, mage, trap, or environment is about to lean hard on one element.',
                            'tags': ['buff', 'defense', 'concentration']},
 'remove-curse': {'school': 'Abjuration',
                  'castingTime': '1 action',
                  'range': 'Touch',
                  'components': 'V, S',
                  'duration': 'Instantaneous',
                  'classes': ['Cleric', 'Paladin', 'Warlock', 'Wizard'],
                  'effect': 'Break a curse on a creature or object and sever cursed attunement when applicable',
                  'description': 'Touch a creature or object and unravel a curse affecting it. Against a cursed item, '
                                 'the magic may remain in the item itself, but the bond to the current victim can '
                                 'still be broken.\n'
                                 '\n'
                                 'Remove Curse is story-progression magic. It keeps weird loot, hostile hexes, and '
                                 'cursed set pieces from trapping the party in a dead end.',
                  'tags': ['utility', 'restoration']},
 'sleet-storm': {'school': 'Conjuration',
                 'castingTime': '1 action',
                 'range': '150 feet',
                 'components': 'V, S, M',
                 'duration': 'Up to 1 minute',
                 'concentration': True,
                 'classes': ['Druid', 'Sorcerer', 'Wizard'],
                 'effect': 'Fill a large area with freezing rain that obscures sight and wrecks movement',
                 'description': 'Conjure a wide storm of sleet and ice that heavily obscures the area and turns the '
                                'ground treacherous. Creatures inside struggle with movement, footing, and maintaining '
                                'concentration.\n'
                                '\n'
                                'Sleet Storm is disruption magic. It breaks ranged plans, wrecks enemy concentration, '
                                'and buys time without needing to directly kill anything.',
                 'areaText': '40-foot radius, 20-foot high cylinder',
                 'tags': ['control', 'concentration', 'aoe', 'terrain']},
 'slow': {'school': 'Transmutation',
          'castingTime': '1 action',
          'range': '120 feet',
          'components': 'V, S, M',
          'duration': 'Up to 1 minute',
          'concentration': True,
          'classes': ['Bard', 'Sorcerer', 'Wizard'],
          'savingThrow': 'WIS',
          'effect': 'Sap several creatures with magical sluggishness, cutting speed, defense, and action quality',
          'description': 'Choose creatures in a wide area and drag them under a wave of temporal or physical '
                         'sluggishness. Targets that fail the save become dramatically worse at moving, reacting, and '
                         'converting turns into value while concentration lasts.\n'
                         '\n'
                         'Slow is precision control against elite enemies. It does not fully remove creatures like '
                         'some spells do, but it makes almost everything they do worse.',
          'areaText': 'Up to 6 creatures in a 40-foot cube',
          'tags': ['control', 'save', 'concentration']},
 'speak-with-dead': {'school': 'Necromancy',
                     'castingTime': '1 action',
                     'range': '10 feet',
                     'components': 'V, S, M',
                     'duration': '10 minutes',
                     'classes': ['Bard', 'Cleric'],
                     'effect': 'Question a corpse and receive limited answers from its lingering spirit-echo',
                     'description': 'Briefly awaken the dead enough to ask questions of a corpse that still has a '
                                    'mouth or equivalent means to answer. The dead do not become truly alive, but they '
                                    'can provide fragments of knowledge from when they lived.\n'
                                    '\n'
                                    'Speak with Dead is investigation magic. It shines in murder mysteries, dungeon '
                                    'histories, political intrigue, and any moment where the body still knows more '
                                    'than the living do.',
                     'tags': ['utility', 'divination', 'necromancy']},
 'stinking-cloud': {'school': 'Conjuration',
                    'castingTime': '1 action',
                    'range': '90 feet',
                    'components': 'V, S, M',
                    'duration': 'Up to 1 minute',
                    'concentration': True,
                    'classes': ['Bard', 'Sorcerer', 'Wizard'],
                    'savingThrow': 'CON',
                    'effect': 'Create a nauseating cloud that obscures the area and can rob creatures of actions',
                    'description': 'Fill a wide zone with a choking yellow cloud. Creatures inside deal with heavy '
                                   'obscurity, and those who fail the save can be left retching instead of acting '
                                   'effectively.\n'
                                   '\n'
                                   'Stinking Cloud is space denial. Drop it on archers, hallways, clustered back '
                                   'lines, or any fight where breaking enemy actions matters more than dealing direct '
                                   'damage.',
                    'areaText': '20-foot radius sphere',
                    'tags': ['control', 'save', 'concentration', 'aoe']},
 'tongues': {'school': 'Divination',
             'castingTime': '1 action',
             'range': 'Touch',
             'components': 'V, M',
             'duration': '1 hour',
             'classes': ['Bard', 'Cleric', 'Sorcerer', 'Warlock', 'Wizard'],
             'effect': 'Let a creature understand spoken languages and be understood in return',
             'description': 'Touch a creature and expand its ability to understand speech across language barriers. '
                            'For the spell’s duration, conversation becomes possible even when the participants do not '
                            'share a normal tongue.\n'
                            '\n'
                            'Tongues is social and exploration utility. It prevents language from halting diplomacy, '
                            'interrogation, lore scenes, or strange planar encounters.',
             'tags': ['utility', 'divination']},
 'water-breathing': {'school': 'Transmutation',
                     'castingTime': '1 action',
                     'range': '30 feet',
                     'components': 'V, S, M',
                     'duration': '24 hours',
                     'ritual': True,
                     'classes': ['Druid', 'Ranger', 'Wizard'],
                     'effect': 'Grant several willing creatures the ability to breathe underwater for a full day',
                     'description': 'Choose willing creatures in range and adapt them for underwater survival. For the '
                                    'duration, they can breathe beneath the surface and operate in aquatic scenes '
                                    'without drowning pressure.\n'
                                    '\n'
                                    'Water Breathing is expedition magic. Cast it before shipwreck dives, flooded '
                                    'ruins, lake monsters, or any session where the map continues below the surface.',
                     'tags': ['utility', 'ritual']},
 'water-walk': {'school': 'Transmutation',
                'castingTime': '1 action',
                'range': '30 feet',
                'components': 'V, S, M',
                'duration': '1 hour',
                'ritual': True,
                'classes': ['Cleric', 'Druid', 'Ranger', 'Sorcerer'],
                'effect': 'Let several creatures move across water and similar liquids as though on solid ground',
                'description': 'Choose willing creatures in range and buoy them on the surface of water or comparable '
                               'liquids as though they were walking on solid ground. They can cross rivers, marshes, and '
                               'hazards that would normally swallow or slow the group.\n'
                               '\n'
                               'Water Walk turns terrain into a non-issue. Use it for travel, pursuits, and encounters '
                               'where the environment was meant to divide the party.',
                'tags': ['utility', 'ritual', 'mobility']}}



STAGE4D_AUTHORED_OVERRIDES: dict[str, dict[str, Any]] = {'arcane-eye': {'school': 'Divination',
                'castingTime': '1 action',
                'range': '30 feet',
                'components': 'V, S, M',
                'duration': 'Up to 1 hour',
                'concentration': True,
                'classes': ['Wizard'],
                'effect': 'Create an invisible scouting eye that can travel ahead and feed you visual information',
                'description': 'Create an invisible magical eye at a point in range and guide it through the '
                               'environment while you maintain concentration. The eye can slip ahead of the party, '
                               'round corners, and check rooms before anyone commits their body to the danger.\n'
                               '\n'
                               'Arcane Eye is premium scouting magic. Use it to map a dungeon branch, watch a ritual '
                               'chamber, or inspect a trapped corridor when opening the wrong door would start a '
                               'fight.',
                'tags': ['utility', 'divination', 'concentration', 'scout']},
 'banishment': {'school': 'Abjuration',
                'castingTime': '1 action',
                'range': '60 feet',
                'components': 'V, S, M',
                'duration': 'Up to 1 minute',
                'concentration': True,
                'classes': ['Cleric', 'Paladin', 'Sorcerer', 'Warlock', 'Wizard'],
                'savingThrow': 'CHA',
                'effect': 'Attempt to remove a creature from the battlefield outright for the duration',
                'description': 'Aim a severing word at a creature you can see and force it to fight the pull of exile. '
                               'On a failed Charisma save, the target vanishes from the current battlefield for as '
                               'long as you keep concentration.\n'
                               '\n'
                               'Banishment is one of the cleanest ways to swing a hard encounter. Use it to erase the '
                               'scariest piece on the board, split a boss from its bodyguards, or send an extraplanar '
                               'threat back where it came from.',
                'scalingNote': 'When cast with a slot above 4th, you can target one additional creature for each slot '
                               'level above 4th.',
                'tags': ['control', 'save', 'concentration', 'teleport']},
 'blight': {'school': 'Necromancy',
            'castingTime': '1 action',
            'range': '30 feet',
            'components': 'V, S',
            'duration': 'Instantaneous',
            'classes': ['Druid', 'Sorcerer', 'Warlock', 'Wizard'],
            'savingThrow': 'CON',
            'damageType': 'necrotic',
            'damageFormula': '8d8',
            'effect': 'Wither one creature with a burst of draining necrotic magic',
            'description': 'Focus a pulse of magical decay into one creature in range. On a failed Constitution save, '
                           'the target takes a heavy burst of necrotic damage; a success cuts the damage down. Plant '
                           'creatures and mundane vegetation fare especially badly against the effect.\n'
                           '\n'
                           'Blight is a brutal single-target nuke when you need to punish a tough enemy instead of '
                           'spreading damage around a crowd.',
            'scalingNote': 'When cast with a slot above 4th, add 1d8 necrotic damage for each slot level above 4th.',
            'tags': ['damage', 'save', 'necromancy']},
 'compulsion': {'school': 'Enchantment',
                'castingTime': '1 action',
                'range': '30 feet',
                'components': 'V, S',
                'duration': 'Up to 1 minute',
                'concentration': True,
                'classes': ['Bard'],
                'savingThrow': 'WIS',
                'areaText': 'Creatures of your choice in a 30-foot radius',
                'effect': 'Drive nearby creatures to move where you want instead of holding their ground',
                'description': 'Project an irresistible pressure that tugs creatures away from their current choices. '
                               'Creatures of your choice that fail the Wisdom save are pushed into forced movement '
                               'patterns on your turn and struggle to stay where they would rather be.\n'
                               '\n'
                               'Compulsion is battlefield herding. Use it to peel enemies off the back line, drag '
                               'guards out of cover, or make a congested melee line unravel in the direction you '
                               'choose.',
                'tags': ['control', 'save', 'concentration', 'aoe']},
 'confusion': {'school': 'Enchantment',
               'castingTime': '1 action',
               'range': '90 feet',
               'components': 'V, S, M',
               'duration': 'Up to 1 minute',
               'concentration': True,
               'classes': ['Bard', 'Druid', 'Sorcerer', 'Wizard'],
               'savingThrow': 'WIS',
               'areaText': '10-foot radius sphere',
               'effect': 'Scramble the minds of a cluster of creatures so their turns become unreliable',
               'description': 'Flood a zone with mind-bending static and force creatures inside it to make Wisdom '
                              'saves. Failing creatures behave erratically, wasting turns, wandering, or lashing out '
                              'without discipline.\n'
                              '\n'
                              'Confusion is strongest against groups that depend on coordination. Cast it into the '
                              'middle of enemy lines when stealing actions is worth more than dealing direct damage.',
               'tags': ['control', 'save', 'concentration', 'aoe']},
 'conjure-minor-elementals': {'school': 'Conjuration',
                              'castingTime': '1 minute',
                              'range': '90 feet',
                              'components': 'V, S, M',
                              'duration': 'Up to 1 hour',
                              'concentration': True,
                              'classes': ['Druid', 'Wizard'],
                              'effect': 'Summon a group of lesser elemental allies to swarm, screen, or harass the '
                                        'field',
                              'description': 'Call a small host of elemental spirits into physical form and direct '
                                             'them as temporary allies while you maintain concentration. The exact '
                                             'bodies and numbers depend on how your table packages elemental stat '
                                             'blocks for summoning.\n'
                                             '\n'
                                             'This spell trades one action now for a pile of board presence later. Use '
                                             'it when extra bodies, extra attacks, and blocked movement lanes will '
                                             'matter for several rounds.',
                              'scalingNote': 'Higher slots should improve the strength, quantity, or durability of the '
                                             'summoned elementals based on the summoning rules your table is using.',
                              'tags': ['summon', 'concentration', 'utility']},
 'control-water': {'school': 'Transmutation',
                   'castingTime': '1 action',
                   'range': '300 feet',
                   'components': 'V, S, M',
                   'duration': 'Up to 10 minutes',
                   'concentration': True,
                   'classes': ['Cleric', 'Druid', 'Wizard'],
                   'areaText': '100-foot cube of water',
                   'effect': 'Raise, part, redirect, or whirl a huge body of water',
                   'description': 'Seize command of a massive volume of water and reshape its behavior while you '
                                  'maintain concentration. You can part it, redirect it, raise it, or turn it violent '
                                  'enough to disrupt creatures caught inside the chosen area.\n'
                                  '\n'
                                  'Control Water is encounter-warping terrain magic. It can open a path through a '
                                  'flood, swamp ships, expose what is hiding below the surface, or make a water map '
                                  'itself become the hazard.',
                   'tags': ['control', 'utility', 'concentration', 'aoe']},
 'death-ward': {'school': 'Abjuration',
                'castingTime': '1 action',
                'range': 'Touch',
                'components': 'V, S',
                'duration': '8 hours',
                'classes': ['Cleric', 'Paladin'],
                'effect': 'Place a one-time shield against a killing blow or death effect',
                'description': 'Lay a protective ward on a creature that waits quietly until disaster strikes. The '
                               'next time the target would be dropped outright or destroyed by a lethal magical '
                               'effect, the ward intervenes and leaves them standing instead of dead.\n'
                               '\n'
                               'Death Ward is a pre-fight insurance spell. Put it on the person most likely to eat the '
                               'boss burst, the healer who cannot afford to fall first, or the ally carrying a '
                               'critical objective.',
                'tags': ['buff', 'defense']},
 'dimension-door': {'school': 'Conjuration',
                    'castingTime': '1 action',
                    'range': '500 feet',
                    'components': 'V',
                    'duration': 'Instantaneous',
                    'classes': ['Bard', 'Sorcerer', 'Warlock', 'Wizard'],
                    'effect': 'Teleport yourself, and often one companion, a long distance in a single jump',
                    'description': 'Fold space around yourself and vanish to a point you can describe or visualize '
                                   'within range. The spell is built for decisive repositioning and can often carry '
                                   'one nearby ally or a manageable burden with you.\n'
                                   '\n'
                                   'Dimension Door solves distance all at once. Use it to break out of cells, bypass '
                                   'vertical maps, rescue an ally from a doomed corner, or instantly relocate the '
                                   'party’s most important piece.',
                    'tags': ['utility', 'teleport', 'mobility']},
 'dominate-beast': {'school': 'Enchantment',
                    'castingTime': '1 action',
                    'range': '60 feet',
                    'components': 'V, S',
                    'duration': 'Up to 1 minute',
                    'concentration': True,
                    'classes': ['Druid', 'Sorcerer'],
                    'savingThrow': 'WIS',
                    'effect': 'Take command of a beast and steer its movement and actions',
                    'description': 'Lock your will onto a beast you can see and force it to contest your control with '
                                   'a Wisdom save. On a failed save, the creature comes under your direction while you '
                                   'maintain concentration.\n'
                                   '\n'
                                   'Dominate Beast is strongest when the battlefield already contains an impressive '
                                   'animal. Steal the enemy rider’s mount, turn a summoned beast around, or convert '
                                   'local wildlife into a temporary asset.',
                    'tags': ['control', 'save', 'concentration']},
 'evards-black-tentacles': {'school': 'Conjuration',
                            'castingTime': '1 action',
                            'range': '90 feet',
                            'components': 'V, S, M',
                            'duration': 'Up to 1 minute',
                            'concentration': True,
                            'classes': ['Wizard'],
                            'savingThrow': 'DEX',
                            'damageType': 'bludgeoning',
                            'damageFormula': '3d6',
                            'areaText': '20-foot square',
                            'effect': 'Fill an area with grasping tentacles that restrain and crush creatures',
                            'description': 'Spread a carpet of rubbery black tentacles across the ground at a point in '
                                           'range. Creatures caught in the area are battered, entangled, and forced to '
                                           'fight their way out while the spell remains active.\n'
                                           '\n'
                                           'This spell is brutal area denial. Drop it on a choke point, doorway, '
                                           'bridge, or enemy clump and make them choose between staying trapped or '
                                           'wasting turns escaping.',
                            'tags': ['control', 'damage', 'save', 'concentration', 'aoe']},
 'fabricate': {'school': 'Transmutation',
               'castingTime': '10 minutes',
               'range': '120 feet',
               'components': 'V, S',
               'duration': 'Instantaneous',
               'classes': ['Wizard'],
               'effect': 'Turn raw materials into a finished object, structure, or batch of goods',
               'description': 'Convert a quantity of raw material into a crafted product that could normally be made '
                              'from it, subject to your knowledge and the spell’s limits. The magic handles the '
                              'time-consuming physical labor in a single casting.\n'
                              '\n'
                              'Fabricate is downtime power disguised as a spell. It can produce tools, barricades, '
                              'bridges, trade goods, or mission gear when the party has materials but not hours to '
                              'spare.',
               'tags': ['utility', 'crafting']},
 'fire-shield': {'school': 'Evocation',
                 'castingTime': '1 action',
                 'range': 'Self',
                 'components': 'V, S, M',
                 'duration': '10 minutes',
                 'classes': ['Sorcerer', 'Warlock', 'Wizard'],
                 'damageType': 'fire or cold',
                 'damageFormula': '2d8',
                 'effect': 'Wrap yourself in protective elemental energy that punishes melee attackers',
                 'description': 'Cloak yourself in either chilling frost or searing flame. The spell grants resistance '
                                'to the opposite element and lashes back at creatures that hit you in melee with a '
                                'burst of matching retaliatory damage.\n'
                                '\n'
                                'Fire Shield is a self-buff for casters who expect to get pressured. It turns every '
                                'melee hit against you into a costly trade and can make a front line think twice about '
                                'staying adjacent.',
                 'tags': ['buff', 'defense', 'damage']},
 'freedom-of-movement': {'school': 'Abjuration',
                         'castingTime': '1 action',
                         'range': 'Touch',
                         'components': 'V, S, M',
                         'duration': '1 hour',
                         'classes': ['Artificer', 'Bard', 'Cleric', 'Druid', 'Ranger'],
                         'effect': 'Let a creature ignore many restraints, slows, and movement impediments',
                         'description': 'Touch a creature and untangle its movement from many of the world’s usual '
                                        'restrictions. The target can push through restraints, difficult movement '
                                        'conditions, and many forms of magical hindrance that would normally pin them '
                                        'in place.\n'
                                        '\n'
                                        'Freedom of Movement is a surgical answer to control-heavy encounters. Cast it '
                                        'on the ally who must keep moving no matter what the dungeon or enemy lineup '
                                        'throws at them.',
                         'tags': ['buff', 'mobility']},
 'greater-invisibility': {'school': 'Illusion',
                          'castingTime': '1 action',
                          'range': 'Touch',
                          'components': 'V, S',
                          'duration': 'Up to 1 minute',
                          'concentration': True,
                          'classes': ['Bard', 'Sorcerer', 'Wizard'],
                          'effect': 'Make a creature invisible without dropping the spell when it attacks or casts',
                          'description': 'Touch a creature and veil it completely while you maintain concentration. '
                                         'Unlike weaker invisibility magic, the target can keep fighting, casting, and '
                                         'moving aggressively without breaking the concealment.\n'
                                         '\n'
                                         'Greater Invisibility is elite offense and defense at once. It protects a '
                                         'fragile striker, boosts a rogue’s pressure, and makes repeated attacks much '
                                         'harder for enemies to answer.',
                          'tags': ['buff', 'illusion', 'concentration', 'stealth']},
 'guardian-of-faith': {'school': 'Conjuration',
                       'castingTime': '1 action',
                       'range': '30 feet',
                       'components': 'V',
                       'duration': '8 hours',
                       'classes': ['Cleric', 'Paladin'],
                       'damageType': 'radiant',
                       'damageFormula': '20',
                       'effect': 'Station a radiant sentinel that punishes enemies who pass too close',
                       'description': 'Conjure a spectral guardian at a point in range and leave it standing watch. '
                                      'Hostile creatures that move through its threat zone take radiant punishment '
                                      'until the guardian has spent its full reserve or the spell ends.\n'
                                      '\n'
                                      'Guardian of Faith is a defensive anchor. Plant it on a doorway, altar, bridge, '
                                      'or objective and force enemies to bleed for every step they take through that '
                                      'space.',
                       'tags': ['damage', 'defense', 'summon']},
 'hallucinatory-terrain': {'school': 'Illusion',
                           'castingTime': '10 minutes',
                           'range': '300 feet',
                           'components': 'V, S, M',
                           'duration': '24 hours',
                           'classes': ['Bard', 'Druid', 'Warlock', 'Wizard'],
                           'areaText': '150-foot cube',
                           'effect': 'Alter the apparent look of a broad landscape without changing its actual '
                                     'physical shape',
                           'description': 'Paint a large stretch of terrain with convincing false appearance so it '
                                          'looks like a different environment to ordinary senses. Paths can seem '
                                          'flooded, empty ground can appear broken, and an obvious camp can look like '
                                          'harmless wilderness.\n'
                                          '\n'
                                          'Hallucinatory Terrain is ambush and deception magic on a map scale. Use it '
                                          'to hide a base, bait enemies down the wrong route, or turn open ground into '
                                          'an illusion of safety.',
                           'tags': ['utility', 'illusion', 'aoe']},
 'ice-storm': {'school': 'Evocation',
               'castingTime': '1 action',
               'range': '300 feet',
               'components': 'V, S, M',
               'duration': 'Instantaneous',
               'classes': ['Druid', 'Sorcerer', 'Wizard'],
               'savingThrow': 'DEX',
               'damageType': 'bludgeoning and cold',
               'damageFormula': '2d8 bludgeoning + 4d6 cold',
               'areaText': '20-foot radius, 40-foot high cylinder',
               'effect': 'Hammer an area with freezing hail that damages and roughens the ground',
               'description': 'Call down a crushing barrage of hail and ice over a wide cylinder. Creatures inside the '
                              'strike zone take a mix of impact and cold damage, and the battered ground becomes '
                              'harder to move through afterward.\n'
                              '\n'
                              'Ice Storm is both burst damage and map control. It softens clustered enemies while '
                              'leaving behind messy terrain that slows reinforcements and retreats.',
               'scalingNote': 'When cast with a slot above 4th, add 1d8 bludgeoning damage for each slot level above '
                              '4th.',
               'tags': ['damage', 'save', 'aoe', 'control']},
 'locate-creature': {'school': 'Divination',
                     'castingTime': '1 action',
                     'range': 'Self',
                     'components': 'V, S, M',
                     'duration': 'Up to 1 hour',
                     'concentration': True,
                     'classes': ['Bard', 'Cleric', 'Druid', 'Paladin', 'Ranger', 'Wizard'],
                     'effect': 'Sense the direction of a known creature as long as it remains within the spell’s limit',
                     'description': 'Tune your senses toward a creature you know and track its direction while you '
                                    'maintain concentration. The spell does not provide a full map, but it keeps you '
                                    'oriented toward the target as long as nothing blocks the magic outright.\n'
                                    '\n'
                                    'Locate Creature is pursuit magic. Use it to follow an escaping villain, find a '
                                    'missing ally in a complex dungeon, or confirm which branch of a map the quarry '
                                    'actually took.',
                     'tags': ['utility', 'divination', 'concentration']},
 'otilukes-resilient-sphere': {'school': 'Evocation',
                               'castingTime': '1 action',
                               'range': '30 feet',
                               'components': 'V, S, M',
                               'duration': 'Up to 1 minute',
                               'concentration': True,
                               'classes': ['Wizard'],
                               'savingThrow': 'DEX',
                               'effect': 'Seal a creature inside a hard force bubble that isolates it from the fight',
                               'description': 'Snap a globe of force around a creature in range. An unwilling target '
                                              'gets a Dexterity save to avoid the enclosure; on a failure it is '
                                              'trapped inside a near-impervious sphere for as long as your '
                                              'concentration holds.\n'
                                              '\n'
                                              'This spell is precision removal. Bubble a dangerous enemy, buy time for '
                                              'the healer, or protect a fragile ally by cutting them off from the rest '
                                              'of the battlefield.',
                               'tags': ['control', 'save', 'concentration', 'barrier']},
 'phantasmal-killer': {'school': 'Illusion',
                       'castingTime': '1 action',
                       'range': '120 feet',
                       'components': 'V, S',
                       'duration': 'Up to 1 minute',
                       'concentration': True,
                       'classes': ['Bard', 'Wizard'],
                       'savingThrow': 'WIS',
                       'damageType': 'psychic',
                       'damageFormula': '4d10',
                       'effect': 'Manifest a nightmare only one target can perceive, then let the fear tear at it',
                       'description': 'Plant a private horror in a creature’s mind and force it to face the illusion '
                                      'as though it were real. Failing the initial Wisdom save leaves the target '
                                      'frightened, and the nightmare continues to rip into it with psychic pain on '
                                      'later turns.\n'
                                      '\n'
                                      'Phantasmal Killer is a pressure spell for breaking one important enemy. It '
                                      'combines fear, damage, and concentration tax against creatures that cannot '
                                      'afford to lose composure.',
                       'tags': ['damage', 'control', 'save', 'concentration']},
 'polymorph': {'school': 'Transmutation',
               'castingTime': '1 action',
               'range': '60 feet',
               'components': 'V, S, M',
               'duration': 'Up to 1 hour',
               'concentration': True,
               'classes': ['Bard', 'Druid', 'Sorcerer', 'Wizard'],
               'savingThrow': 'WIS',
               'effect': 'Transform a creature into a beast form for rescue, control, or a temporary power spike',
               'description': 'Rewrite a creature into a beast shape of your choosing within the spell’s limits. '
                              'Willing allies can accept the transformation for mobility or temporary hit point '
                              'padding, while unwilling targets get a Wisdom save to resist being turned into '
                              'something far less dangerous.\n'
                              '\n'
                              'Polymorph is one of the most flexible spells at this tier. Save an ally by turning them '
                              'into a giant sack of hit points, or neutralize an enemy by reducing it to a harmless '
                              'form.',
               'tags': ['control', 'utility', 'concentration', 'transformation', 'save']},
 'stone-shape': {'school': 'Transmutation',
                 'castingTime': '1 action',
                 'range': 'Touch',
                 'components': 'V, S, M',
                 'duration': 'Instantaneous',
                 'classes': ['Druid', 'Wizard'],
                 'effect': 'Sculpt stone into openings, barriers, simple forms, or rough engineering fixes',
                 'description': 'Touch a section of stone and force it into a new shape that remains after the spell '
                                'ends. You can carve an opening, seal a passage, make crude stone fittings, or alter '
                                'the battlefield in ways mundane masonry would take hours to manage.\n'
                                '\n'
                                'Stone Shape is a dungeon breaker. It opens locked routes, creates cover, seals '
                                'pursuit lanes, and solves problems when the obstacle is literally made of rock.',
                 'tags': ['utility', 'control', 'transformation']},
 'stoneskin': {'school': 'Abjuration',
               'castingTime': '1 action',
               'range': 'Touch',
               'components': 'V, S, M',
               'duration': 'Up to 1 hour',
               'concentration': True,
               'classes': ['Artificer', 'Druid', 'Ranger', 'Sorcerer', 'Wizard'],
               'effect': 'Harden a creature against many mundane weapon hits',
               'description': 'Touch a creature and turn its flesh as resilient as worked stone for the duration. '
                              'While you maintain concentration, many ordinary weapon blows become dramatically less '
                              'effective against the target.\n'
                              '\n'
                              'Stoneskin is a boss-fight prep spell. Put it on the ally who must stand in front of the '
                              'nastiest weapon user on the map and keep them there.',
               'tags': ['buff', 'defense', 'concentration']},
 'wall-of-fire': {'school': 'Evocation',
                  'castingTime': '1 action',
                  'range': '120 feet',
                  'components': 'V, S, M',
                  'duration': 'Up to 1 minute',
                  'concentration': True,
                  'classes': ['Druid', 'Sorcerer', 'Wizard'],
                  'savingThrow': 'DEX',
                  'damageType': 'fire',
                  'damageFormula': '5d8',
                  'effect': 'Raise a blazing barrier that burns creatures when it appears and when they stay near the '
                            'hot side',
                  'description': 'Draw a long wall or ring of fire at a point in range and choose the side that throws '
                                 'the harshest heat. Creatures caught by the initial appearance take a burst of fire '
                                 'damage, and remaining in the danger zone continues to punish bad positioning.\n'
                                 '\n'
                                 'Wall of Fire is both offense and zoning. Split an encounter in half, protect the '
                                 'back line, or force enemies to choose between taking damage and surrendering space.',
                  'scalingNote': 'When cast with a slot above 4th, add 1d8 fire damage for each slot level above 4th.',
                  'areaText': 'Up to 60-foot wall or 20-foot radius ring',
                  'tags': ['damage', 'save', 'concentration', 'aoe', 'barrier']},
 'animate-objects': {'school': 'Transmutation',
                     'castingTime': '1 action',
                     'range': '120 feet',
                     'components': 'V, S',
                     'duration': 'Up to 1 minute',
                     'concentration': True,
                     'classes': ['Bard', 'Sorcerer', 'Wizard'],
                     'effect': 'Turn unattended objects into a temporary swarm of attackers under your command',
                     'description': 'Wake nearby objects with violent motion and direct them as a squad of floating '
                                    'weapons, tools, or debris while you maintain concentration. The exact attack '
                                    'profiles depend on object size and how your table packages animated-object '
                                    'stats.\n'
                                    '\n'
                                    'Animate Objects is a damage engine with incredible action economy. It is best '
                                    'when there are plenty of valid objects nearby and the fight will last long enough '
                                    'for multiple rounds of attacks.',
                     'scalingNote': 'Higher slots should improve the number or size of objects you can animate based '
                                    'on your table’s chosen stat packaging.',
                     'tags': ['summon', 'damage', 'concentration']},
 'awaken': {'school': 'Transmutation',
            'castingTime': '8 hours',
            'range': 'Touch',
            'components': 'V, S, M',
            'duration': 'Instantaneous',
            'classes': ['Bard', 'Druid'],
            'effect': 'Grant a beast or plant true awareness, language, and a lasting bond',
            'description': 'Pour a full ritual of life-shaping magic into a beast or plant and raise it into genuine '
                           'awakened intelligence. The target gains greater awareness, language, and personality, and '
                           'it usually begins the story with a friendly stance toward you.\n'
                           '\n'
                           'Awaken is world-building magic more than combat tech. Use it to create allies, guardians, '
                           'witnesses, or strange recurring NPCs that only this kind of spell can produce.',
            'tags': ['utility', 'ritual-like', 'transformation']},
 'bigbys-hand': {'school': 'Evocation',
                 'castingTime': '1 action',
                 'range': '120 feet',
                 'components': 'V, S, M',
                 'duration': 'Up to 1 minute',
                 'concentration': True,
                 'classes': ['Wizard'],
                 'damageType': 'force',
                 'damageFormula': 'Varies by hand mode',
                 'effect': 'Conjure a giant spectral hand that can strike, shove, grasp, or shield',
                 'description': 'Manifest an enormous magical hand and command it each round while you maintain '
                                'concentration. The hand can punch, shove creatures around, pin them, or intercept '
                                'damage depending on which mode you choose in the moment.\n'
                                '\n'
                                'Bigby’s Hand is one of the best flexible control spells at this level because it can '
                                'swap between offense, defense, and movement denial without changing spells.',
                 'tags': ['control', 'damage', 'concentration', 'summon']},
 'cloudkill': {'school': 'Conjuration',
               'castingTime': '1 action',
               'range': '120 feet',
               'components': 'V, S',
               'duration': 'Up to 10 minutes',
               'concentration': True,
               'classes': ['Sorcerer', 'Wizard'],
               'savingThrow': 'CON',
               'damageType': 'poison',
               'damageFormula': '5d8',
               'areaText': '20-foot radius sphere',
               'effect': 'Roll a deadly poison cloud across the battlefield and force creatures to flee or choke '
                         'inside it',
               'description': 'Create a heavy bank of toxic gas that drifts across the battlefield while you maintain '
                              'concentration. Creatures caught in the cloud make Constitution saves against poison '
                              'damage, and the obscuring vapor can keep threatening fresh spaces as it moves.\n'
                              '\n'
                              'Cloudkill is attrition magic. Use it to sweep corridors, flush enemies out of cover, or '
                              'lock down a route the opposition needs to cross.',
               'scalingNote': 'When cast with a slot above 5th, add 1d8 poison damage for each slot level above 5th.',
               'tags': ['damage', 'save', 'concentration', 'aoe', 'control']},
 'cone-of-cold': {'school': 'Evocation',
                  'castingTime': '1 action',
                  'range': 'Self (60-foot cone)',
                  'components': 'V, S, M',
                  'duration': 'Instantaneous',
                  'classes': ['Sorcerer', 'Wizard'],
                  'savingThrow': 'CON',
                  'damageType': 'cold',
                  'damageFormula': '8d8',
                  'areaText': '60-foot cone',
                  'effect': 'Blast a wide cone with killing cold',
                  'description': 'Unleash a roaring fan of winter from your outstretched hands. Creatures in the cone '
                                 'make Constitution saves; failures take the full crushing cold, while successful '
                                 'creatures endure only part of it.\n'
                                 '\n'
                                 'Cone of Cold is a classic room-clearer when you can step into the correct angle. It '
                                 'rewards good positioning and punishes clustered enemies over a huge wedge of space.',
                  'scalingNote': 'When cast with a slot above 5th, add 1d8 cold damage for each slot level above 5th.',
                  'tags': ['damage', 'save', 'aoe']},
 'conjure-elemental': {'school': 'Conjuration',
                       'castingTime': '1 minute',
                       'range': '90 feet',
                       'components': 'V, S, M',
                       'duration': 'Up to 1 hour',
                       'concentration': True,
                       'classes': ['Druid', 'Wizard'],
                       'effect': 'Call a true elemental ally into service for the duration',
                       'description': 'Summon an elemental creature into a prepared space and keep it bound to your '
                                      'command while you maintain concentration. The exact stat block and temperament '
                                      'depend on the type of elemental chosen and the summoning package your table is '
                                      'using.\n'
                                      '\n'
                                      'Conjure Elemental trades one slot for a powerful extra body that can tank '
                                      'space, carry utility, and multiply the party’s action economy in a long fight.',
                       'scalingNote': 'Higher slots should improve the elemental’s power package according to the '
                                      'summoning rules your table has chosen.',
                       'tags': ['summon', 'concentration', 'utility']},
 'contagion': {'school': 'Necromancy',
               'castingTime': '1 action',
               'range': 'Touch',
               'components': 'V, S',
               'duration': 'Special',
               'classes': ['Cleric', 'Druid'],
               'savingThrow': 'CON',
               'effect': 'Infect a creature with a magical disease that can cripple it over time',
               'description': 'Lay a diseased touch on a creature and force it to start fighting off a supernatural '
                              'sickness. The exact progression and symptoms depend on the rule package you are using '
                              'for the spell, but the outcome is severe for targets that cannot shake it quickly.\n'
                              '\n'
                              'Contagion is not a burst-damage spell. It is pressure, debilitation, and long-tail '
                              'punishment aimed at enemies who expect to win the war of attrition.',
               'tags': ['control', 'save', 'necromancy']},
 'creation': {'school': 'Illusion',
              'castingTime': '1 minute',
              'range': '30 feet',
              'components': 'V, S, M',
              'duration': 'Special',
              'classes': ['Sorcerer', 'Wizard'],
              'effect': 'Make a nonliving object out of shadow-stuff for a limited time',
              'description': 'Pull an object into being from magical substance and hold it together long enough to '
                             'matter. The object must stay within the spell’s size and material limits, and more '
                             'delicate or exotic creations usually last for less time than simple ones.\n'
                             '\n'
                             'Creation is open-ended utility. It is perfect for the player who keeps seeing one '
                             'missing tool, one missing bridge, or one missing decoy object that would solve the whole '
                             'scene.',
              'tags': ['utility', 'illusion', 'crafting']},
 'dispel-evil-and-good': {'school': 'Abjuration',
                          'castingTime': '1 action',
                          'range': 'Self',
                          'components': 'V, S',
                          'duration': 'Up to 1 minute',
                          'concentration': True,
                          'classes': ['Cleric', 'Paladin'],
                          'effect': 'Protect yourself against major outsider creature types and potentially drive them '
                                    'away',
                          'description': 'Wrap yourself in a protective ward keyed against creatures such as '
                                         'celestials, elementals, fey, fiends, and undead. While the spell lasts you '
                                         'gain valuable protection against their influence and may be able to break '
                                         'possession or send a hostile outsider away.\n'
                                         '\n'
                                         'Dispel Evil and Good is specialist tech, but when the campaign type matches '
                                         'the target list it becomes a fight-winning answer.',
                          'tags': ['buff', 'defense', 'concentration', 'counter']},
 'dominate-person': {'school': 'Enchantment',
                     'castingTime': '1 action',
                     'range': '60 feet',
                     'components': 'V, S',
                     'duration': 'Up to 1 minute',
                     'concentration': True,
                     'classes': ['Bard', 'Sorcerer', 'Wizard'],
                     'savingThrow': 'WIS',
                     'effect': 'Seize direct control of a humanoid target',
                     'description': 'Crash your will into a humanoid mind and force it to contest your control with a '
                                    'Wisdom save. On a failed save, the target falls under your command while your '
                                    'concentration lasts, letting you redirect a dangerous enemy into a temporary '
                                    'asset.\n'
                                    '\n'
                                    'Dominate Person is devastating against elite humanoids. Turn a knight on their '
                                    'own line, hijack a mage’s movement, or strip an enemy commander of agency at the '
                                    'worst possible moment.',
                     'scalingNote': 'Higher-level castings can extend the duration according to the spell’s long-form '
                                    'rule package.',
                     'tags': ['control', 'save', 'concentration']},
 'dream': {'school': 'Illusion',
           'castingTime': '1 minute',
           'range': 'Special',
           'components': 'V, S, M',
           'duration': '8 hours',
           'classes': ['Bard', 'Warlock', 'Wizard'],
           'effect': 'Send a message into a sleeping mind or turn the visit into a psychic nightmare',
           'description': 'Reach across any distance to a sleeping creature and enter its dreams as messenger, '
                          'observer, or tormentor. The spell can carry an intimate private conversation or twist the '
                          'rest into a harrowing nightmare when subtlety is no longer the goal.\n'
                          '\n'
                          'Dream is story magic with teeth. It handles diplomacy, threats, espionage, and '
                          'long-distance pressure without needing the party to stand in the same room as the target.',
           'tags': ['utility', 'illusion', 'communication']},
 'flame-strike': {'school': 'Evocation',
                  'castingTime': '1 action',
                  'range': '60 feet',
                  'components': 'V, S, M',
                  'duration': 'Instantaneous',
                  'classes': ['Cleric'],
                  'savingThrow': 'DEX',
                  'damageType': 'fire and radiant',
                  'damageFormula': '4d6 fire + 4d6 radiant',
                  'areaText': '10-foot radius, 40-foot high cylinder',
                  'effect': 'Drop a column of sacred fire that blends holy and elemental damage',
                  'description': 'Call a vertical pillar of divine flame down on a point you can see. Creatures in the '
                                 'cylinder make Dexterity saves against a mixed blast of fire and radiant damage that '
                                 'is hard to mitigate with one resistance alone.\n'
                                 '\n'
                                 'Flame Strike is a divine artillery spell. Use it when you need area damage that '
                                 'still feels like holy judgment instead of plain battlefield wizardry.',
                  'scalingNote': 'When cast with a slot above 5th, add 1d6 fire and 1d6 radiant damage for each slot '
                                 'level above 5th.',
                  'tags': ['damage', 'save', 'aoe']},
 'geas': {'school': 'Enchantment',
          'castingTime': '1 minute',
          'range': '60 feet',
          'components': 'V',
          'duration': '30 days',
          'classes': ['Bard', 'Cleric', 'Druid', 'Paladin', 'Wizard'],
          'savingThrow': 'WIS',
          'damageType': 'psychic',
          'damageFormula': '5d10',
          'effect': 'Bind a creature to a command under threat of painful magical punishment',
          'description': 'Lay a long-form command on a creature that fails its Wisdom save and force it to live under '
                         'that obligation for the spell’s duration. Disobeying the command brings a sharp wave of '
                         'psychic punishment, even though the spell does not grant minute-by-minute puppet control.\n'
                         '\n'
                         'Geas is campaign leverage more than battle tempo. It shines in intrigue, bargains, prisoner '
                         'handling, and situations where one lasting order matters more than immediate violence.',
          'tags': ['control', 'save', 'utility']},
 'greater-restoration': {'school': 'Abjuration',
                         'castingTime': '1 action',
                         'range': 'Touch',
                         'components': 'V, S, M',
                         'duration': 'Instantaneous',
                         'classes': ['Bard', 'Cleric', 'Druid'],
                         'effect': 'Remove one severe condition, curse, or crippling magical affliction',
                         'description': 'Touch a creature and purge one major lingering harm from it, whether that '
                                        'harm is physical, spiritual, or magical in origin. This is the party’s answer '
                                        'to the kinds of effects that lesser healing magic cannot solve cleanly.\n'
                                        '\n'
                                        'Greater Restoration is premium support utility. Save it for petrification, '
                                        'ability drain, curses, or story-grade afflictions that would otherwise take a '
                                        'character out of play.',
                         'tags': ['healing', 'utility', 'counter']},
 'hold-monster': {'school': 'Enchantment',
                  'castingTime': '1 action',
                  'range': '90 feet',
                  'components': 'V, S, M',
                  'duration': 'Up to 1 minute',
                  'concentration': True,
                  'classes': ['Bard', 'Sorcerer', 'Warlock', 'Wizard'],
                  'savingThrow': 'WIS',
                  'effect': 'Paralyze a creature and open it up to devastating follow-up attacks',
                  'description': 'Fix a creature in place with a paralyzing enchantment if it fails the Wisdom save. '
                                 'While you maintain concentration, the target loses agency and becomes dramatically '
                                 'easier for the party to destroy at close range.\n'
                                 '\n'
                                 'Hold Monster is one of the nastiest setup spells in the game when it lands. Save it '
                                 'for the enemy whose turn matters most, then let the rest of the party cash in.',
                  'scalingNote': 'When cast with a slot above 5th, you can target one additional creature for each '
                                 'slot level above 5th.',
                  'tags': ['control', 'save', 'concentration']},
 'insect-plague': {'school': 'Conjuration',
                   'castingTime': '1 action',
                   'range': '300 feet',
                   'components': 'V, S, M',
                   'duration': 'Up to 10 minutes',
                   'concentration': True,
                   'classes': ['Cleric', 'Druid'],
                   'savingThrow': 'CON',
                   'damageType': 'piercing',
                   'damageFormula': '4d10',
                   'areaText': '20-foot radius sphere',
                   'effect': 'Fill a large area with biting insects that obscure sight and grind creatures down',
                   'description': 'Summon a roiling cloud of locusts or similar vermin into a point in range and keep '
                                  'it active with concentration. Creatures caught inside take repeated damage and '
                                  'fight in a heavily obscured zone that is miserable to cross.\n'
                                  '\n'
                                  'Insect Plague is sustained area control. It locks down space, taxes concentration '
                                  'on enemy casters, and punishes anyone who insists on standing in the bad area.',
                   'tags': ['damage', 'save', 'concentration', 'aoe', 'control']},
 'legend-lore': {'school': 'Divination',
                 'castingTime': '10 minutes',
                 'range': 'Self',
                 'components': 'V, S, M',
                 'duration': 'Instantaneous',
                 'classes': ['Bard', 'Cleric', 'Wizard'],
                 'effect': 'Receive a curated burst of hidden history about a person, place, or thing of legend',
                 'description': 'Ask the world for the story behind a legendary subject and receive lore, fragments, '
                                'and symbolic truth in return. The clearer the target and the stronger its mythic '
                                'footprint, the richer the answer tends to be.\n'
                                '\n'
                                'Legend Lore is investigation at mythic scale. Use it when normal research has stopped '
                                'being enough and the campaign needs the deeper history behind the clue.',
                 'tags': ['utility', 'divination']},
 'mass-cure-wounds': {'school': 'Evocation',
                      'castingTime': '1 action',
                      'range': '60 feet',
                      'components': 'V, S',
                      'duration': 'Instantaneous',
                      'classes': ['Bard', 'Cleric', 'Druid'],
                      'healingFormula': '3d8 + spellcasting modifier',
                      'areaText': 'Up to 6 creatures in a 30-foot radius',
                      'effect': 'Restore a solid burst of hit points to several allies at once',
                      'description': 'Release a broad wave of healing over multiple creatures you can see in range and '
                                     'restore a meaningful chunk of hit points to each of them. It is the practical '
                                     'answer when the whole party is bleeding instead of only one person being down.\n'
                                     '\n'
                                     'Mass Cure Wounds is best after a big enemy area attack or between fight phases '
                                     'where several allies need to stand back up at once.',
                      'scalingNote': 'When cast with a slot above 5th, add 1d8 healing for each slot level above 5th.',
                      'tags': ['healing', 'aoe']},
 'mislead': {'school': 'Illusion',
             'castingTime': '1 action',
             'range': 'Self',
             'components': 'S',
             'duration': 'Up to 1 hour',
             'concentration': True,
             'classes': ['Bard', 'Wizard'],
             'effect': 'Turn yourself invisible while projecting a visible illusory double elsewhere',
             'description': 'Slip into invisibility and leave behind a convincing duplicate that can move and draw '
                            'attention while you maintain concentration. Your real body stays hidden, while the decoy '
                            'becomes the face the enemies think they are chasing.\n'
                            '\n'
                            'Mislead is premium deception for infiltration, escapes, and social manipulation. It lets '
                            'you be in the conversation without truly being in the danger.',
             'tags': ['illusion', 'utility', 'concentration', 'stealth']},
 'planar-binding': {'school': 'Abjuration',
                    'castingTime': '1 hour',
                    'range': '60 feet',
                    'components': 'V, S, M',
                    'duration': '24 hours',
                    'classes': ['Cleric', 'Druid', 'Warlock', 'Wizard'],
                    'savingThrow': 'WIS',
                    'effect': 'Lock an outsider into service after it has already been contained or summoned',
                    'description': 'Extend a controlling seal over a celestial, elemental, fey, or fiend that is '
                                   'already trapped or present and force it to resist with a Wisdom save. On a failed '
                                   'save, the creature remains bound to your service for the spell’s duration.\n'
                                   '\n'
                                   'Planar Binding is advanced setup magic. It is not for casual combat turns; it is '
                                   'for summoners, preparation-heavy casters, and stories where bargains with '
                                   'outsiders become concrete assets.',
                    'scalingNote': 'Higher-level slots should extend the binding duration according to the spell’s '
                                   'long-form rule package.',
                    'tags': ['control', 'save', 'summon', 'utility']},
 'raise-dead': {'school': 'Necromancy',
                'castingTime': '1 hour',
                'range': 'Touch',
                'components': 'V, S, M',
                'duration': 'Instantaneous',
                'classes': ['Bard', 'Cleric', 'Druid', 'Paladin'],
                'effect': 'Return a creature that has been dead for a limited time back to life',
                'description': 'Call a soul back to its body if the death is recent enough and the remains are in '
                               'workable condition. The creature returns weakened but alive, giving the party a true '
                               'second chance after a loss that would otherwise end the story for that character.\n'
                               '\n'
                               'Raise Dead is long-form recovery magic. It carries cost, time, and emotional weight, '
                               'so it lands best when resurrection is a major moment rather than a casual reset '
                               'button.',
                'tags': ['healing', 'revival', 'utility']},
 'reincarnate': {'school': 'Transmutation',
                 'castingTime': '1 hour',
                 'range': 'Touch',
                 'components': 'V, S, M',
                 'duration': 'Instantaneous',
                 'classes': ['Druid'],
                 'effect': 'Return a dead creature to life in a newly grown adult body',
                 'description': 'Weave primal life back around a dead creature’s soul and grow it a new body to '
                                'inhabit. The creature returns alive, but not necessarily in the same ancestry or '
                                'physical form it had before death.\n'
                                '\n'
                                'Reincarnate is resurrection with story consequences. It is perfect for tables that '
                                'want death to matter without forcing the character out of the campaign completely.',
                 'tags': ['healing', 'revival', 'transformation', 'utility']},
 'scrying': {'school': 'Divination',
             'castingTime': '10 minutes',
             'range': 'Self',
             'components': 'V, S, M',
             'duration': 'Up to 10 minutes',
             'concentration': True,
             'classes': ['Bard', 'Cleric', 'Druid', 'Warlock', 'Wizard'],
             'savingThrow': 'WIS',
             'effect': 'Create a remote sensor to watch a creature or place from afar',
             'description': 'Focus on a known creature or location and open a magical sensor at that distant point if '
                            'the target fails to resist. The result is a window into a place you are not standing, '
                            'letting the party gather information before acting.\n'
                            '\n'
                            'Scrying is strategic intelligence. Use it to check defenses, verify a villain’s location, '
                            'or learn whether the room you are about to breach is empty, trapped, or already waiting '
                            'for you.',
             'tags': ['utility', 'divination', 'save', 'concentration']},
 'seeming': {'school': 'Illusion',
             'castingTime': '1 action',
             'range': '30 feet',
             'components': 'V, S',
             'duration': '8 hours',
             'classes': ['Bard', 'Sorcerer', 'Wizard'],
             'effect': 'Disguise a whole group at once with long-lasting false appearances',
             'description': 'Lay a broad illusion over multiple creatures and rewrite how they appear for hours at a '
                            'time. The targets still occupy their same physical space, but observers read clothing, '
                            'faces, and outlines through the false image you provide.\n'
                            '\n'
                            'Seeming is infiltration magic for the whole crew. It is excellent for social entry, '
                            'prisoner swaps, false uniforms, and any plan that only works if several people all pass '
                            'the same first glance test.',
             'tags': ['illusion', 'utility', 'stealth']},
 'telekinesis': {'school': 'Transmutation',
                 'castingTime': '1 action',
                 'range': '60 feet',
                 'components': 'V, S',
                 'duration': 'Up to 10 minutes',
                 'concentration': True,
                 'classes': ['Bard', 'Sorcerer', 'Wizard'],
                 'savingThrow': 'STR',
                 'effect': 'Move creatures or objects with force of will and keep doing it every round',
                 'description': 'Grip a creature or object at range with invisible force and move it without touching '
                                'it. The spell can lift heavy objects, shove problems out of the way, or force a '
                                'creature into a repeated contest against your magical leverage while concentration '
                                'holds.\n'
                                '\n'
                                'Telekinesis is control through positioning. It wins fights by putting the wrong '
                                'target in the wrong place over and over again.',
                 'tags': ['control', 'utility', 'concentration', 'save']},
 'teleportation-circle': {'school': 'Conjuration',
                          'castingTime': '1 minute',
                          'range': '10 feet',
                          'components': 'V, M',
                          'duration': '1 round',
                          'classes': ['Sorcerer', 'Wizard'],
                          'effect': 'Open a stable linked portal to a permanent circle you know',
                          'description': 'Trace a glowing circle on the ground and open a brief gate to a permanent '
                                         'teleportation circle whose sigil sequence you know. For one round, creatures '
                                         'stepping through are carried instantly to the linked destination.\n'
                                         '\n'
                                         'Teleportation Circle is infrastructure magic. It matters most in campaign '
                                         'play where travel, safehouses, faction hubs, and prepared routes are part of '
                                         'the world.',
                          'tags': ['utility', 'teleport', 'travel']},
 'wall-of-force': {'school': 'Evocation',
                   'castingTime': '1 action',
                   'range': '120 feet',
                   'components': 'V, S, M',
                   'duration': 'Up to 10 minutes',
                   'concentration': True,
                   'classes': ['Wizard'],
                   'effect': 'Create a nearly untouchable barrier of force that shapes the battlefield',
                   'description': 'Shape a sheet, dome, or enclosure of pure force at a point in range and hold it in '
                                  'place with concentration. The wall does not depend on hit points the way ordinary '
                                  'barriers do, which makes it one of the cleanest ways to divide a battle on '
                                  'command.\n'
                                  '\n'
                                  'Wall of Force is encounter control at the highest level. Split a boss from its '
                                  'support, protect the retreat lane, or seal away a threat the party cannot afford to '
                                  'trade with directly.',
                   'tags': ['control', 'barrier', 'concentration', 'utility']}}


STAGE4E_AUTHORED_OVERRIDES: dict[str, dict[str, Any]] = {'abi-dalzims-horrid-wilting': {'description': 'Wither living bodies and plants alike with a wave of desiccating '
                                               'necromancy. Abi-Dalzim’s Horrid Wilting is efficient mass punishment '
                                               'for clustered enemies, especially in encounters where conventional '
                                               'elemental resistances are a problem.\n'
                                               '\n'
                                               'It is a brutally clean answer to large groups.',
                                'effect': 'Suck the moisture out of creatures in a wide area for savage necrotic '
                                          'damage.'},
 'antimagic-field': {'description': 'Erase active magic from the space around you and force the encounter to work '
                                    'under mortal rules again. Antimagic Field is a hard counter spell for mage '
                                    'fights, summon-heavy battles, and magical terrain that would otherwise define the '
                                    'scene.\n'
                                    '\n'
                                    'It does not solve every problem, but it changes which problems are allowed to '
                                    'exist.',
                     'effect': 'Carry a moving dead zone that suppresses spells, magic items, and summoned effects '
                               'around you.'},
 'antipathy-sympathy': {'description': 'Imprint an emotional command onto a creature or object and let nearby minds '
                                       'orbit or flee accordingly. Antipathy/Sympathy is large-scale social and '
                                       'territorial control magic, useful for protecting spaces, luring crowds, or '
                                       'making approach impossible.\n'
                                       '\n'
                                       'It is campaign leverage disguised as enchantment.',
                        'effect': 'Enchant a target so creatures are irresistibly drawn toward it or driven violently '
                                  'away from it.'},
 'arcane-gate': {'description': 'Open two linked gates at points you can see and let creatures move between them while '
                                'the spell lasts. Arcane Gate turns vertical terrain, gaps, hazards, and split battle '
                                'lines into something the party can ignore for a few crucial rounds.\n'
                                '\n'
                                'Use it to extract allies, redeploy the front line, or force enemies to respect angles '
                                'they thought were safe.',
                 'effect': 'Link two visible points with paired portals for rapid repositioning.'},
 'astral-projection': {'description': 'Slip free of your bodies and travel the Astral Plane by silver cord rather than '
                                      'by ordinary motion. Astral Projection is planar expedition magic for campaigns '
                                      'that have outgrown mundane geography entirely.\n'
                                      '\n'
                                      'Once this spell is relevant, the campaign is playing at a very different scale.',
                       'effect': 'Send your souls into the Astral Plane while leaving physical bodies behind on the '
                                 'material side.'},
 'blade-barrier': {'description': 'Shape a humming barrier of whirling blades and hold it in place with concentration. '
                                  'Blade Barrier is both area denial and punishment magic, making corridors, choke '
                                  'points, and retreat lanes miserable for anything trying to cross.\n'
                                  '\n'
                                  'It is strongest when the rest of the party can keep creatures trapped inside the '
                                  'danger zone or force them to walk through it.',
                   'effect': 'Raise a wall of spinning blades that cuts creatures who pass through or start inside '
                             'it.'},
 'blade-of-disaster': {'description': 'Open a sliver of cosmic ruin and drive it across the battlefield with your '
                                      'bonus actions while concentration lasts. Blade of Disaster is elite '
                                      'single-target pressure for the highest-tier encounters, especially when the '
                                      'party just needs one creature to disappear faster.\n'
                                      '\n'
                                      'It is relentless and wonderfully unfair.',
                       'effect': 'Summon a riftlike blade of force that tears through a target each round and '
                                 'threatens critical devastation.'},
 'circle-of-death': {'description': 'Collapse a wide area into a wave of withering necrotic force and force creatures '
                                    'inside it to survive the blast. Circle of Death is a battlefield-clearer for '
                                    'crowded encounters, undead wars, and scenes where raw area coverage matters more '
                                    'than precision.\n'
                                    '\n'
                                    'Drop it on clustered enemies, back-line casters, or reinforcement waves before '
                                    'they can spread out.',
                     'effect': 'Detonate a huge necrotic burst that punishes packed enemies at long range.'},
 'clone': {'description': 'Invest in future survival by preparing a spare body before the worst day arrives. Clone is '
                          'less a turn-by-turn spell than an insurance policy against final death, and that alone '
                          'makes it one of the most strategically important spells in the game.\n'
                          '\n'
                          'It matters because you cast it long before you need it.',
           'effect': 'Grow a replacement body that can receive your soul if your original body dies.'},
 'conjure-celestial': {'description': 'Invite a powerful celestial being into the encounter and keep it present with '
                                      'concentration. Conjure Celestial is elite summon magic, useful when the party '
                                      'needs both raw capability and a toolbox of divine-flavored support options.\n'
                                      '\n'
                                      'Treat the summon as a spotlight ally, not background damage.',
                       'effect': 'Call a celestial ally whose presence can heal, support, or dominate a battlefield.'},
 'conjure-fey': {'description': 'Call a fey creature into the fight and keep it present with concentration. Conjure '
                                'Fey shines when the summoned creature’s movement, senses, and special abilities '
                                'matter as much as its damage output.\n'
                                '\n'
                                'Treat it like a flexible extra party member rather than a simple damage button.',
                 'effect': 'Summon a fey ally that brings mobility, charm pressure, and table-driven utility.'},
 'control-weather': {'description': 'Take command of sky, wind, temperature, and precipitation across a huge area. '
                                    'Control Weather is campaign-scale environmental magic for naval travel, sieges, '
                                    'escapes, regional disruption, or divine spectacle.\n'
                                    '\n'
                                    'When it is cast, everyone in the area is playing your weather now.',
                     'effect': 'Gradually reshape the local weather into the version of the battlefield or region you '
                               'want.'},
 'create-undead': {'description': 'Work foul necromancy over corpses and create more dangerous undead than the '
                                  'lower-tier animation spells allow. Create Undead is campaign magic first: it '
                                  'rewards planning, resources, and a table that tracks long-term minions.\n'
                                  '\n'
                                  'It is most useful between fights, when you can choose what kind of servant the '
                                  'situation actually needs.',
                   'effect': 'Animate stronger undead servants for long-term control, guard duty, or grim battlefield '
                             'support.'},
 'crown-of-stars': {'description': 'Crown yourself with starfire and spend later turns launching radiant bolts as '
                                   'needed. Crown of Stars is excellent sustained pressure because it leaves your '
                                   'concentration free and lets you keep threatening damage while casting other '
                                   'spells.\n'
                                   '\n'
                                   'It is strongest in long fights where repeated bonus-action attacks add up.',
                    'effect': 'Orbit yourself with motes of stellar light that can be fired off over time without '
                              'concentration.'},
 'delayed-blast-fireball': {'description': 'Create a bead of compressed flame and decide whether to detonate now or '
                                           'gamble on a larger explosion. Delayed Blast Fireball rewards setup, forced '
                                           'movement, and nerve, especially when the enemy has limited room to escape '
                                           'the blast zone.\n'
                                           '\n'
                                           'If you can make them stay put, the spell becomes terrifying.',
                            'effect': 'Charge an unstable fireball that grows deadlier the longer you dare hold it.'},
 'demiplane': {'description': 'Create or revisit a hidden personal room outside the normal world and use it for '
                              'storage, secrecy, or control. Demiplane is prized by cautious casters because it gives '
                              'them a place where ordinary geography cannot easily follow.\n'
                              '\n'
                              'It is logistics and paranoia in perfect balance.',
               'effect': 'Open a door into a private extradimensional chamber that can become a permanent secure '
                         'space.'},
 'disintegrate': {'description': 'Lance a target with concentrated force and dare it to survive the saving throw. '
                                 'Disintegrate is one of the cleanest single-target finishers in the spell list, and '
                                 'it is especially brutal when the party has already stripped a creature’s defenses.\n'
                                 '\n'
                                 'Use it to delete a priority target, destroy obstacles, or punish something that '
                                 'thought it could hide behind hit points alone.',
                  'effect': 'Fire a devastating green ray that can erase a target or object outright.'},
 'divine-word': {'description': 'Let divine authority roll out from you in a single word and judge creatures by how '
                                'much strength they have left. Divine Word is a finisher spell: it is at its best '
                                'after the party has already bloodied the field and now wants the encounter to '
                                'collapse all at once.\n'
                                '\n'
                                'Use it when multiple enemies are hanging on by a thread.',
                 'effect': 'Speak a holy command that banishes or cripples weakened enemies in a large area.'},
 'dominate-monster': {'description': 'Overpower a creature’s will and turn its body into a problem for its former '
                                     'allies. Dominate Monster is one of the cleanest encounter-flipping spells in the '
                                     'game, especially when the target is dangerous enough to justify the slot.\n'
                                     '\n'
                                     'The harder the monster hits, the better this spell feels.',
                      'effect': 'Seize control of almost any creature and direct its actions while concentration '
                                'holds.'},
 'earthquake': {'description': 'Shake the battlefield hard enough that footing, walls, and concentration all become '
                               'uncertain. Earthquake is catastrophic area control, useful when the goal is to break a '
                               'fortification, scatter an army, or make everyone stop fighting on stable terms.\n'
                               '\n'
                               'This is destruction on an architectural scale.',
                'effect': 'Rend the ground, topple structures, and turn a huge area into unstable disaster terrain.'},
 'etherealness': {'description': 'Step sideways out of the ordinary world and move through a ghostly version of '
                                 'reality. Etherealness is infiltration, escape, and scouting magic for problems that '
                                 'do not care about hit points but absolutely care about walls, locks, and pursuit.\n'
                                 '\n'
                                 'It lets the party stop playing by local geography for a while.',
                  'effect': 'Shift into the Ethereal Plane to bypass walls, pursuit, and many normal dangers.'},
 'eyebite': {'description': 'Wrap your gaze in dark magic and choose a new victim each turn while concentration holds. '
                            'Eyebite is not about one huge swing; it is about repeatedly wrecking one enemy at a time '
                            'until the encounter starts falling apart.\n'
                            '\n'
                            'It works best when the party can capitalize on frightened, sleeping, or weakened targets '
                            'immediately.',
             'effect': 'Project a repeating stare that can sicken, panic, or put enemies to sleep each round.'},
 'feeblemind': {'description': 'Assault the mind so thoroughly that language, reason, and complex magic fall apart. '
                               'Feeblemind is a terrifying answer to enemy casters and masterminds because even '
                               'surviving the hit can leave them functionally removed from the story for a long time.\n'
                               '\n'
                               'Use it on the creature who absolutely must stop thinking clearly.',
                'effect': 'Shatter a creature’s intellect and spellcasting capacity with a single brutal curse.'},
 'find-the-path': {'description': 'Bind your senses to the route toward a known destination and follow the spell’s '
                                  'guidance through wilderness, dungeon routes, and hostile terrain. Find the Path is '
                                  'expedition magic for campaigns where getting there alive is the challenge.\n'
                                  '\n'
                                  'Cast it when navigation failure would cost time, secrecy, or survival.',
                   'effect': 'Receive supernatural guidance toward a specific destination without getting turned '
                             'around.'},
 'finger-of-death': {'description': 'Point, speak the doom, and flood a creature with death magic hard enough to '
                                    'change the encounter. Finger of Death is premium single-target punishment, '
                                    'especially when the target has already spent its best defenses.\n'
                                    '\n'
                                    'When the victim is humanoid, the aftermath can matter just as much as the hit.',
                     'effect': 'Blast one creature with lethal necrotic power and potentially raise its corpse as a '
                               'zombie.'},
 'fire-storm': {'description': 'Drop a sculpted inferno onto the battlefield and choose exactly which spaces burn. '
                               'Fire Storm is ideal when you need big area damage without roasting allies, civilians, '
                               'or objectives standing nearby.\n'
                               '\n'
                               'Its shape control is what makes it special.',
                'effect': 'Arrange multiple sheets of roaring fire to scorch a huge custom-shaped area.'},
 'flesh-to-stone': {'description': 'Curse a creature with calcifying magic and keep the pressure on while '
                                   'concentration lasts. Flesh to Stone is a control spell that becomes a long-term '
                                   'answer if the target keeps failing saves and the party protects your '
                                   'concentration.\n'
                                   '\n'
                                   'It is best against single dangerous enemies that cannot afford to lose turns.',
                    'effect': 'Slowly petrify a creature until it hardens into helpless stone.'},
 'forcecage': {'description': 'Snap an invisible cage or box into existence and let the target discover that movement '
                              'is no longer a real option. Forcecage is encounter-warping control because it does not '
                              'rely on concentration and often demands very specific answers to escape.\n'
                              '\n'
                              'Use it to remove one nightmare threat while the party deals with everything else.',
               'effect': 'Seal a creature or area inside an almost impossible prison of magical force.'},
 'foresight': {'description': 'Flood a creature with intuitive warning until it seems to be moving a heartbeat ahead '
                              'of the world. Foresight is one of the best long-duration buffs in the game because it '
                              'touches almost every meaningful roll that creature cares about.\n'
                              '\n'
                              'Cast it on the person who will carry the next major fight.',
               'effect': 'Grant a creature extraordinary premonition that boosts offense, defense, and survival for '
                         'hours.'},
 'gate': {'description': 'Tear a stable opening through reality and decide whether it serves as a road or a summons. '
                         'Gate is pinnacle travel and confrontation magic, letting the party go where it has no '
                         'business going or force something powerful to come here instead.\n'
                         '\n'
                         'This spell changes the scope of a scene the moment it resolves.',
          'effect': 'Open a portal across planes or call a specific extraplanar being through by naming it.'},
 'glibness': {'description': 'Turn speech itself into a weapon and a shield for the duration of the spell. Glibness is '
                             'social dominance magic for lies, negotiations, infiltration, and moments where being '
                             'believed is more valuable than dealing damage.\n'
                             '\n'
                             'If the campaign has intrigue, this spell can feel unfair in the best way.',
              'effect': 'Wrap yourself in impossible verbal confidence for supreme deception and social control.'},
 'globe-of-invulnerability': {'description': 'Anchor a shimmering globe around yourself and let hostile magic break '
                                             'against it. Globe of Invulnerability is a caster duel spell: it protects '
                                             'a space, stabilizes a position, and forces enemy mages to escalate or '
                                             'relocate.\n'
                                             '\n'
                                             'Use it when the fight is being decided by hostile control, attrition '
                                             'magic, or spell volleys instead of weapon swings.',
                              'effect': 'Surround yourself with a warded sphere that shuts down many lower-level '
                                        'spells.'},
 'harm': {'description': 'Deliver a crushing burst of necrotic power that strips away an enormous amount of vitality '
                         'in a single cast. Harm is a brutal anti-boss spell because it does not need fancy setup to '
                         'matter; it just makes one creature much easier to finish.\n'
                         '\n'
                         'Pair it with allies who can immediately capitalize on the target’s sudden drop in staying '
                         'power.',
          'effect': 'Flood a creature with necrotic ruin and leave it barely holding together.'},
 'heal': {'description': 'Pour powerful restorative magic into a creature and bring it back from the edge in one cast. '
                         'Heal is not subtle, but that is the point: it resets a front-liner, stabilizes a crisis, and '
                         'strips away conditions that would otherwise keep the target out of the fight.\n'
                         '\n'
                         'Use it when a smaller heal would only delay the problem for one more enemy turn.',
          'effect': 'Restore a huge chunk of hit points and clear multiple debilitating conditions at once.',
          'healingFormula': '70 hit points'},
 'heroes-feast': {'description': 'Spend time and treasure on a magical feast that leaves the group tougher, steadier, '
                                 'and harder to frighten or poison. Heroes’ Feast is pre-raid preparation magic for '
                                 'boss fights, cursed strongholds, and days you know will be miserable.\n'
                                 '\n'
                                 'Its value comes before initiative is rolled, not after.',
                  'effect': 'Prepare a protective banquet that fortifies the whole party before a major challenge.'},
 'holy-aura': {'description': 'Cloak the party in holy brilliance and make every hostile attack into a riskier choice. '
                              'Holy Aura is one of the best endgame support spells because it raises the whole group’s '
                              'durability while forcing painful consequences on aggressive enemies.\n'
                              '\n'
                              'Cast it before the boss gets its big turn, not after.',
               'effect': 'Flood allies with radiant protection that improves defense and punishes enemies who strike '
                         'them.'},
 'illusory-dragon': {'description': 'Manifest a nightmare dragon over the battlefield and let it terrorize creatures '
                                    'while concentration holds. Illusory Dragon is flashy control-plus-damage magic '
                                    'that wins through fear, repeated pressure, and sheer spectacle.\n'
                                    '\n'
                                    'It is excellent when the party wants both morale collapse and area punishment.',
                     'effect': 'Summon a terrifying dragon illusion that frightens foes and breathes repeated psychic '
                               'devastation.'},
 'imprisonment': {'description': 'Remove a creature from the story with one of the game’s most final containment '
                                 'effects. Imprisonment is not just control; it is judgment, reserve power, and '
                                 'campaign-level problem solving for entities too dangerous to kill or too valuable to '
                                 'release.\n'
                                 '\n'
                                 'If it lands, the adventure changes.',
                  'effect': 'Bind a creature in an exotic permanent prison tailored to the form of captivity you '
                            'choose.'},
 'incendiary-cloud': {'description': 'Fill a large area with superheated smoke and let it keep cooking anything '
                                     'trapped inside. Incendiary Cloud is persistent zone damage first and foremost, '
                                     'rewarding forced movement, cramped terrain, and enemies with nowhere safe to '
                                     'reposition.\n'
                                     '\n'
                                     'It turns standing still into a losing plan.',
                      'effect': 'Spread a roiling cloud of fire that keeps burning and drifting across the '
                                'battlefield.'},
 'investiture-of-flame': {'description': 'Take on an aspect of living flame and keep it active with concentration. '
                                         'This investiture is a stance spell for casters who expect to stay near the '
                                         'action and punish creatures that close in.\n'
                                         '\n'
                                         'It is strongest in cramped fights where resistance, aura damage, and line '
                                         'attacks all matter.',
                          'effect': 'Wrap yourself in fire, gain resistance, and project burning pressure around your '
                                    'space.'},
 'investiture-of-ice': {'description': 'Cloak yourself in freezing magic and weaponize the space around you while '
                                       'concentration holds. Investiture of Ice mixes defense, control, and repeatable '
                                       'pressure rather than chasing one giant damage spike.\n'
                                       '\n'
                                       'Use it when slowing the fight down helps your side more than it helps the '
                                       'enemy.',
                        'effect': 'Take on an icy form that resists cold and turns nearby space into hostile terrain.'},
 'investiture-of-stone': {'description': 'Bind yourself to the strength of earth and become harder to move, punish, or '
                                         'pin down. Investiture of Stone is about survivability and presence, letting '
                                         'you hold dangerous ground longer than a normal caster should.\n'
                                         '\n'
                                         'It is a good answer when the party needs someone to stand in the wrong place '
                                         'on purpose.',
                          'effect': 'Adopt a stone-hardened form that improves durability and earth-focused movement '
                                    'tricks.'},
 'investiture-of-wind': {'description': 'Surround yourself with cutting gusts and use concentration to stay mobile, '
                                        'evasive, and hard to approach cleanly. Investiture of Wind is the most '
                                        'reposition-heavy of the investitures, rewarding players who want to dominate '
                                        'space instead of trading stillness for damage.\n'
                                        '\n'
                                        'Use it when controlling lines of fire matters more than standing still and '
                                        'blasting.',
                         'effect': 'Ride a mantle of violent wind that boosts mobility and swats away ranged '
                                   'pressure.'},
 'invulnerability': {'description': 'Wrap yourself in absolute defensive magic and force the encounter to answer you '
                                    'some other way. Invulnerability is a selfish spell, but in the right fight that '
                                    'selfishness is exactly what wins: you can hold position, bait resources, and keep '
                                    'concentration alive with absurd confidence.\n'
                                    '\n'
                                    'Use it when surviving the next minute matters more than anything else.',
                     'effect': 'Become almost untouchable by damage for a short but decisive stretch of combat.'},
 'maddening-darkness': {'description': 'Collapse sight and sanity together in one massive field and hold it there with '
                                       'concentration. Maddening Darkness is attrition control: it blocks vision, '
                                       'pressures positioning, and keeps punishing creatures that cannot escape the '
                                       'zone.\n'
                                       '\n'
                                       'Use it when denying information is as valuable as denying hit points.',
                        'effect': 'Drown a huge area in magical darkness that also tears at the minds of creatures '
                                  'inside it.'},
 'magic-jar': {'description': 'Rip your spirit free, anchor it in a container, and use the spell to seize another body '
                              'if the opportunity presents itself. Magic Jar is advanced story magic with huge upside '
                              'and obvious disaster potential if the vessel or your original body is compromised.\n'
                              '\n'
                              'Treat it like a high-risk infiltration plan, not a casual combat cast.',
               'effect': 'Store your soul in a vessel and attempt dangerous body-hopping possession magic.'},
 'mass-heal': {'description': 'Flood your allies with restorative power on a scale ordinary healing cannot touch. Mass '
                              'Heal is the reset button for catastrophic fights, able to pull an entire team back from '
                              'collapse in a single cast.\n'
                              '\n'
                              'Use it the moment the party’s survival stops being a math problem and starts being a '
                              'crisis.',
               'effect': 'Pour an enormous pool of healing across multiple creatures and erase a battlefield disaster '
                         'in one action.',
               'healingFormula': 'Up to 700 hit points divided among creatures'},
 'mass-suggestion': {'description': 'Shape the behavior of several creatures with one carefully framed command and let '
                                    'the magic do the patient work. Mass Suggestion is a campaign-warping spell '
                                    'because it can solve encounters, social scenes, or logistics without ever rolling '
                                    'damage.\n'
                                    '\n'
                                    'The better your wording, the more absurd the payoff.',
                     'effect': 'Implant a convincing course of action into multiple creatures at once for a very long '
                               'duration.'},
 'maze': {'description': 'Erase a target from the encounter for as long as the spell can keep it lost. Maze is premium '
                         'single-target control because it does not need to grind through hit points; it simply makes '
                         'one creature stop being your problem for a while.\n'
                         '\n'
                         'Use the breathing room to win the rest of the fight first.',
          'effect': 'Banish one creature into a labyrinth outside the battlefield until it finds its way back.'},
 'mental-prison': {'description': 'Lock a creature inside a private hallucination and make every attempt to escape '
                                  'hurt. Mental Prison is ideal against dangerous single targets that rely on '
                                  'movement, line of sight, or confidence to do their job.\n'
                                  '\n'
                                  'It rewards focus fire from the party while the victim is boxed into a terrible '
                                  'decision.',
                   'effect': 'Trap a target in a nightmare illusion that punishes movement and failed resistance.'},
 'mind-blank': {'description': 'Lay down a long-lasting mental ward and make one creature extremely difficult to '
                               'manipulate or profile supernaturally. Mind Blank is strategic protection magic for '
                               'espionage arcs, psychic enemies, and anyone carrying secrets that cannot leak.\n'
                               '\n'
                               'It is a quiet spell with enormous payoff.',
                'effect': 'Seal a creature’s mind against psychic intrusion, mind reading, and many forms of magical '
                          'detection.'},
 'mirage-arcane': {'description': 'Flood a huge region with illusion until it becomes a false landscape that behaves '
                                  'like the fiction you built. Mirage Arcane is story-scale magic for heists, '
                                  'fortifications, territorial control, and elaborate ambushes.\n'
                                  '\n'
                                  'It rewards creativity and preparation more than combat tempo.',
                   'effect': 'Rewrite the look and feel of a massive area so the terrain itself lies to everyone '
                             'inside it.'},
 'mordenkainens-magnificent-mansion': {'description': 'Conjure a hidden mansion with servants, food, rest, and '
                                                      'security far beyond an ordinary campsite. The spell is perfect '
                                                      'for long expeditions because it gives the party a stable place '
                                                      'to recover without trusting the surrounding world.\n'
                                                      '\n'
                                                      'It is safety, comfort, and logistics in one cast.',
                                       'effect': 'Open a luxurious extradimensional refuge that serves as a safe house '
                                                 'for a full day.'},
 'mordenkainens-sword': {'description': 'Call a hovering blade into existence and direct it with your bonus actions '
                                        'while concentration lasts. Mordenkainen’s Sword is repeatable single-target '
                                        'pressure, useful when you want another source of damage operating alongside '
                                        'your action.\n'
                                        '\n'
                                        'It is simple, stubborn, and good at making one enemy miserable.',
                         'effect': 'Summon a floating sword of force that keeps carving at a target each round.'},
 'move-earth': {'description': 'Spend concentration on raw large-scale engineering and let the landscape change around '
                               'you. Move Earth is less about winning one round of combat and more about deciding what '
                               'the battlefield, fortress, or campsite looks like before the next problem arrives.\n'
                               '\n'
                               'Use it when terrain itself is the real objective.',
                'effect': 'Reshape huge amounts of loose earth over time to build, bury, fortify, or sabotage '
                          'terrain.'},
 'otilukes-freezing-sphere': {'description': 'Shape intense cold into a sphere that can burst now or be set up for a '
                                             'later explosion. Otiluke’s Freezing Sphere is flexible artillery magic, '
                                             'letting you punish clusters immediately or prepare a nasty surprise in '
                                             'advance.\n'
                                             '\n'
                                             'It is strongest when the field or the party’s plan gives the enemy '
                                             'nowhere good to stand.',
                              'effect': 'Unleash a massive cold detonation or hold the spell briefly as a suspended '
                                        'icy globe.'},
 'ottos-irresistible-dance': {'description': 'Overwhelm a target with involuntary dancing and let the spell tear apart '
                                             'its ability to fight normally. Otto’s Irresistible Dance is a premium '
                                             'shutdown option against one important enemy, especially if that enemy '
                                             'depends on weapon accuracy or positioning.\n'
                                             '\n'
                                             'Once it lands, the rest of the party should make the victim regret every '
                                             'step.',
                              'effect': 'Compel a creature into humiliating uncontrolled movement that wrecks its '
                                        'action economy.'},
 'planar-ally': {'description': 'Call for help from a celestial, elemental, fiend, or other planar power and bargain '
                                'for its service. Planar Ally is as much a relationship spell as a combat spell, and '
                                'its best use depends on your campaign’s factions, favors, and consequences.\n'
                                '\n'
                                'Think of it as hiring a miracle, not summoning a disposable pet.',
                 'effect': 'Negotiate aid from a powerful extraplanar being for a price the table must respect.'},
 'plane-shift': {'description': 'Tear a route from one plane to another and move creatures through it if the '
                                'components and destination are right. Plane Shift is part travel spell and part '
                                'banishment threat, depending on whether the creature being moved wants to go.\n'
                                '\n'
                                'It matters most in planar campaigns, but when it matters, it matters a lot.',
                 'effect': 'Carry creatures between planes or use a tuned fork to send a touched target away.'},
 'power-word-kill': {'description': 'End a creature with language alone if it is weak enough for the magic to take '
                                    'hold. Power Word Kill is not about damage efficiency; it is about certainty, '
                                    'turning a nearly finished enemy into a finished enemy with no save at all.\n'
                                    '\n'
                                    'It is cruel, simple, and perfect for closing the door.',
                     'effect': 'Speak a final word that instantly kills a creature beneath the spell’s hit point '
                               'threshold.'},
 'power-word-pain': {'description': 'Speak a word of pure suffering and watch a creature’s offense fall apart under '
                                    'it. Power Word Pain is not a flashy burst spell; it is a cruel control option '
                                    'designed to ruin the target’s ability to function cleanly.\n'
                                    '\n'
                                    'Use it when stopping the enemy matters more than killing the enemy quickly.',
                     'effect': 'Cripple a target with overwhelming agony without making an attack roll.'},
 'power-word-stun': {'description': 'End a target’s momentum with a command that does not ask permission from AC or '
                                    'saving throws at the moment of impact. Power Word Stun is a brutal setup spell '
                                    'because a stunned creature gives the whole party an opening immediately.\n'
                                    '\n'
                                    'Cast it on the enemy whose next turn would hurt the most.',
                     'effect': 'Speak a word that can instantly stun a creature below the spell’s hit point '
                               'threshold.'},
 'prismatic-spray': {'description': 'Fan out a chaotic spray of prismatic energy and let fate decide exactly how each '
                                    'creature suffers. Prismatic Spray is swingy, dangerous, and spectacular, making '
                                    'it perfect for desperate turns and legendary set pieces.\n'
                                    '\n'
                                    'Cast it when controlled damage is no longer the point.',
                     'effect': 'Blast a cone of wild multicolored rays that produce a range of brutal magical '
                               'outcomes.'},
 'prismatic-wall': {'description': 'Assemble one of the nastiest barriers in the game and let each color demand a '
                                   'different answer. Prismatic Wall is an apex defensive spell, equally good for '
                                   'sealing an approach, fortifying a position, or turning pursuit into suicide.\n'
                                   '\n'
                                   'Anyone trying to cross it had better know exactly what they are doing.',
                    'effect': 'Raise a layered wall of deadly color bands, each with its own punishment and defenses.'},
 'programmed-illusion': {'description': 'Build a delayed magical performance and decide when the scene should spring '
                                        'to life. Programmed Illusion is long-game utility for ambushes, decoys, '
                                        'warnings, traps, and story staging rather than a fast combat cast.\n'
                                        '\n'
                                        'It shines when you prepare the battlefield before anyone else even knows '
                                        'there is a battlefield.',
                         'effect': 'Set a large illusion to trigger later under conditions you define in advance.'},
 'project-image': {'description': 'Split off a convincing image of yourself and operate through it while concentration '
                                  'holds. Project Image is a dominance spell for safe casting, deception, diplomacy, '
                                  'and setting up angles your real body should never risk.\n'
                                  '\n'
                                  'It lets you be present without being vulnerable.',
                   'effect': 'Create a remote illusory double that can cast your spells from a faraway position.'},
 'psychic-scream': {'description': 'Crush enemy minds in a shared psychic howl and let the survivors deal with the '
                                   'aftermath. Psychic Scream is elite crowd control because it pressures several '
                                   'important creatures at once and can leave them stunned rather than merely '
                                   'injured.\n'
                                   '\n'
                                   'Use it when one creature is not enough.',
                    'effect': 'Explode a burst of mental terror that can stun multiple creatures at once.'},
 'regenerate': {'description': 'Kick a creature’s natural recovery into impossible territory and let the magic keep '
                               'knitting it back together over the next hour. Regenerate is a long-form recovery spell '
                               'for allies who are broken, maimed, or about to endure a lot more punishment.\n'
                               '\n'
                               'It is one of the best answers to damage that ordinary healing cannot truly erase.',
                'effect': 'Restore a creature steadily over time and even regrow lost body parts.',
                'healingFormula': '4d8 + 15 hit points, then 1 hit point each round'},
 'resurrection': {'description': 'Call a soul back across the gap of death even after simpler revival magic would have '
                                 'failed. Resurrection is expensive, dramatic, and campaign-shaping, because it can '
                                 'undo losses that would otherwise stay written into the story.\n'
                                 '\n'
                                 'Use it when the party is not ready to let the dead remain dead.',
                  'effect': 'Return a long-dead creature to life if you still have enough of it to work with.'},
 'reverse-gravity': {'description': 'Invalidate the battlefield’s relationship with the ground and let the ceiling '
                                    'become the new problem. Reverse Gravity is chaotic control magic that splits '
                                    'encounters apart, drops enemies out of position, and creates brutal follow-up '
                                    'turns.\n'
                                    '\n'
                                    'It is best where ceilings, fall distance, and panic all help you.',
                     'effect': 'Turn a huge area upside down and send creatures and objects hurtling upward.'},
 'scatter': {'description': 'Pick several creatures and violently rewrite where they are standing. Scatter is one of '
                            'the cleanest reposition tools in the game because it can rescue allies, isolate enemies, '
                            'or break a perfect formation in one action.\n'
                            '\n'
                            'Use it when geography is the actual problem you need to solve.',
             'effect': 'Instantly rearrange multiple creatures across the battlefield to break formations or rescue '
                       'allies.'},
 'sequester': {'description': 'Lock something away in suspended hidden stasis and let time pass around it. Sequester '
                              'is story utility for safeguarding relics, protecting people, or setting up reveals long '
                              'after the spell is cast.\n'
                              '\n'
                              'It is less a combat spell than a campaign device with huge narrative leverage.',
               'effect': 'Hide a creature or object outside normal notice until a condition you choose is met.'},
 'shapechange': {'description': 'Take on a new form with tremendous tactical value and keep adapting as the scene '
                                'evolves. Shapechange is apex flexibility, letting one caster solve wildly different '
                                'problems by becoming the right monster at the right moment.\n'
                                '\n'
                                'The better you know your options, the stronger this spell becomes.',
                 'effect': 'Transform yourself into a high-end creature while keeping your own mind and spellcasting '
                           'decisions.'},
 'simulacrum': {'description': 'Build a snow-and-shadow copy of a creature and preserve it as a lasting magical asset. '
                               'Simulacrum is one of the strongest preparation spells in the game because it turns '
                               'money and time into another set of actions, spells, and skills.\n'
                               '\n'
                               'If your campaign allows it to breathe, it changes what the party can attempt.',
                'effect': 'Craft an obedient duplicate of a creature with much of the original’s capability.'},
 'soul-cage': {'description': 'Snare a departing soul in a tiny vessel and draw on it for information, defense, or '
                              'endurance before the spell ends. Soul Cage is dark utility magic that rewards planning, '
                              'timing, and a table comfortable with its tone.\n'
                              '\n'
                              'It is strongest when cast immediately after an important enemy falls.',
               'effect': 'Capture the fading soul of a nearby creature and spend it for grim utility effects.'},
 'storm-of-vengeance': {'description': 'Unleash a battlefield-wide disaster and let each round add a new layer of '
                                       'misery. Storm of Vengeance is not subtle and it is not precise; it is the '
                                       'spell you cast when you want the whole scene to feel condemned.\n'
                                       '\n'
                                       'Use it when the encounter is large enough to deserve weather as a weapon.',
                        'effect': 'Call down a cascading apocalyptic storm that worsens over several rounds.'},
 'sunbeam': {'description': 'Open yourself to blazing solar magic and fire a punishing beam each round while '
                            'concentration lasts. Sunbeam is sustained pressure, not one-and-done burst, and it gets '
                            'nastier when the battlefield funnels targets into repeated lines.\n'
                            '\n'
                            'Use it when radiant damage, blindness pressure, and action-to-action consistency matter.',
             'effect': 'Project a repeatable line of radiant power that burns enemies and threatens blindness.'},
 'sunburst': {'description': 'Detonate daylight at catastrophic scale and force the field to endure the blaze. '
                             'Sunburst is wide radiant punishment with a strong control rider, making it especially '
                             'good against armies, undead, and creatures that hate bright light.\n'
                             '\n'
                             'When it lands, the whole encounter notices.',
              'effect': 'Explode a vast sphere of searing sunlight that can blind survivors.'},
 'symbol': {'description': 'Bake a trap, curse, or magical trigger into a surface and leave it waiting for the right '
                           'victim. Symbol is defensive prep magic at a very high tier, perfect for vaults, sanctums, '
                           'ambush doors, and places the party intends to control.\n'
                           '\n'
                           'It rewards patience, planning, and a willingness to spend gold before the fight starts.',
            'effect': 'Inscribe a hidden magical sigil that triggers a devastating effect when conditions are met.'},
 'tashas-bubbling-cauldron': {'description': 'Set a conjured cauldron to work and pull practical magical brews from it '
                                             'while the spell lasts. Tasha’s Bubbling Cauldron is flexible camp and '
                                             'travel support rather than a direct combat nuke.\n'
                                             '\n'
                                             'Cast it when the group values preparation, healing support, and weird '
                                             'utility over immediate damage.',
                              'effect': 'Conjure a magical cauldron that brews useful restorative or utility '
                                        'concoctions for the party.'},
 'telepathy': {'description': 'Open a mind-to-mind channel and remove distance, silence, and many language barriers '
                              'from the conversation. Telepathy is premium coordination magic for scouting, intrigue, '
                              'infiltration, and plans that fall apart the moment someone needs to whisper.\n'
                              '\n'
                              'It is not flashy, but it makes complex groups feel seamless.',
               'effect': 'Forge a long-range mental link that allows direct communication without speech.'},
 'teleport': {'description': 'Collapse travel time to nearly nothing and accept that familiarity with the destination '
                             'still matters. Teleport is one of the spells that makes a party feel world-scale, '
                             'enabling rescue missions, strike teams, and continent-spanning logistics in one cast.\n'
                             '\n'
                             'Its risk is part of the tension, so choose your landing point carefully.',
              'effect': 'Instantly transport the group across enormous distances with accuracy based on how well you '
                        'know the destination.'},
 'time-stop': {'description': 'Slip outside the normal flow of turns and take a burst of setup actions while everyone '
                              'else is effectively frozen. Time Stop rarely wins by itself, but it lets you build the '
                              'turn that wins: move, protect yourself, summon tools, and create the board state you '
                              'wanted.\n'
                              '\n'
                              'Treat it as a setup spell for your nastiest follow-up.',
               'effect': 'Seize several stolen moments in a row to reposition, buff, or prepare before time catches '
                         'back up.'},
 'transport-via-plants': {'description': 'Turn living vegetation into a travel network and move the party through it '
                                         'in moments. Transport via Plants is one of the strongest world-movement '
                                         'spells because it bypasses distance, terrain, and many ordinary travel '
                                         'dangers.\n'
                                         '\n'
                                         'It rewards a druidic campaign that remembers where the good trees are.',
                          'effect': 'Step into one large plant and emerge from another known plant anywhere the spell '
                                    'can reach.'},
 'true-polymorph': {'description': 'Use transmutation at reality-warping scale and decide whether the result is '
                                   'rescue, reward, punishment, or pure creativity. True Polymorph is one of the most '
                                   'open-ended spells in the game because it can solve problems, create new ones, or '
                                   'permanently alter the cast of the story.\n'
                                   '\n'
                                   'It is limited more by imagination and table trust than by the text box.',
                    'effect': 'Permanently reshape a creature or object into something entirely different if '
                              'concentration lasts long enough.'},
 'true-resurrection': {'description': 'Reach beyond the failures of lesser revival magic and call someone back fully, '
                                      'even after terrible loss. True Resurrection is miracle-tier recovery, the kind '
                                      'of spell that can rewrite grief, prophecy, and the assumed finality of death '
                                      'itself.\n'
                                      '\n'
                                      'When this spell enters the campaign, mortality feels negotiable.',
                       'effect': 'Return even long-dead creatures to life in a complete body with almost no ordinary '
                                 'limits left.'},
 'true-seeing': {'description': 'Sharpen a creature’s perception until deception starts falling apart around it. True '
                                'Seeing is the spell you cast when the problem is not damage but uncertainty: '
                                'invisible stalkers, shapechangers, glamours, secret doors, and false appearances.\n'
                                '\n'
                                'It turns mystery encounters into honest encounters.',
                 'effect': 'Grant sight that pierces many illusions, disguises, hidden creatures, and false forms.'},
 'tsunami': {'description': 'Drag the sea onto the battlefield and let it keep moving under your control. Tsunami is '
                            'large-scale positional devastation, useful when the field is open enough for the water to '
                            'keep mattering after the first impact.\n'
                            '\n'
                            'It is best in big scenes where space itself becomes the weapon.',
             'effect': 'Conjure an immense moving wall of water that crushes, carries, and floods creatures in its '
                       'path.'},
 'wall-of-ice': {'description': 'Shape thick magical ice into a wall, hemispherical shelter, or trap and keep it '
                                'standing with concentration. Wall of Ice is a hybrid of barrier control and burst '
                                'damage, especially when enemies are forced to stay near it.\n'
                                '\n'
                                'Use it to split lines, pin targets, or create cover the party can immediately '
                                'exploit.',
                 'effect': 'Raise or dome a freezing barrier that blocks movement and punishes creatures when it '
                           'breaks.'},
 'wall-of-thorns': {'description': 'Grow a dense barrier of razor vegetation and let terrain itself do the killing. '
                                   'Wall of Thorns is druid control at its meanest, turning approach lanes and retreat '
                                   'paths into a punishment engine.\n'
                                   '\n'
                                   'It is best when the rest of the party can shove, lure, or hold creatures inside '
                                   'the hazard.',
                    'effect': 'Fill a large space with brutal living thorns that maul anything trying to pass '
                              'through.'},
 'weird': {'description': 'Project personalized horror into the minds of your enemies and let fear become a weapon '
                          'with staying power. Weird is large-scale psychic control and attrition, useful when you '
                          'want both panic and continued punishment instead of one simple blast.\n'
                          '\n'
                          'It is strongest against creatures that still know how to be afraid.',
           'effect': 'Flood multiple creatures with lethal nightmare visions that terrify and damage them over time.'},
 'whirlwind': {'description': 'Spin a violent column of air into the battlefield and let it turn positioning into a '
                              'disaster. Whirlwind is excellent against formations because it damages, restrains, and '
                              'relocates creatures while concentration holds.\n'
                              '\n'
                              'Use it when chaos itself is an ally.',
               'effect': 'Create a mobile vortex that lifts, batters, and displaces creatures inside it.'},
 'wind-walk': {'description': 'Loosen bodies into wind-carried shapes and let the party cross huge distances with '
                              'little regard for ordinary roads. Wind Walk is strategic mobility magic for raids, '
                              'escapes, scouting, and travel-heavy campaigns.\n'
                              '\n'
                              'It matters most when where you arrive is more important than what you do on the next '
                              'initiative count.',
               'effect': 'Transform the group into cloudlike forms for fast overland travel and hard-to-reach '
                         'approaches.'},
 'word-of-recall': {'description': 'Bind your magic to a prepared sanctuary and use the spell as an emergency '
                                   'extraction when things go bad. Word of Recall is one of the safest panic buttons '
                                   'in the game because it converts disaster into retreat immediately.\n'
                                   '\n'
                                   'Prepare the destination well, because the spell is only as good as the refuge '
                                   'waiting there.',
                    'effect': 'Instantly pull yourself and chosen allies back to a sanctified safe point.'}}
