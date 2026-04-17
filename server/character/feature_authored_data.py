"""Authored + generated feature text enrichment for Stage 5.

This module focuses on making class features, subclass unlocks, species traits,
background features, and feats read like usable in-app entries instead of sparse
labels or raw catalog notes.
"""
from __future__ import annotations

import copy
import re
from typing import Any


def slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def normalized_feature_name(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s*\([^)]*\)", "", text).strip()
    return text.lower()


_FEATURE_OVERRIDES: dict[str, dict[str, Any]] = {
    "rage": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "resourceName": "Rage",
        "trackUses": True,
        "summary": "Enter a rage to hit harder, stay dangerous, and soak punishment in front-line fights.",
        "description": (
            "As a bonus action, you enter a Rage that turns you into a durable melee threat. While raging, your weapon attacks hit harder, "
            "you gain strong durability against common physical punishment, and many barbarian features start keying off the rage state.\n\n"
            "In play, Rage is your default combat opener when a hard fight starts. Trigger it early, then stay aggressive so you keep the "
            "benefits rolling while you pressure the enemy line."
        ),
        "effect": "Bonus damage, defensive staying power, and access to rage-linked barbarian features.",
        "recovery": "Regain uses on a Long Rest; some tables may also use short-rest recovery text surfaced elsewhere in the sheet.",
        "tags": ["combat", "resource", "defense"],
    },
    "unarmored defense": {
        "summary": "Your Armor Class comes from your body and stats instead of needing armor.",
        "description": (
            "This feature replaces the default armor math with a class-specific formula, letting your build stay effective even when you are not "
            "wearing armor. It matters every time your Dexterity, Constitution, or Wisdom changes depending on class.\n\n"
            "In play, this is passive but important: the sheet should recalculate AC correctly and keep that value stable across rests, reloads, "
            "and equipment changes."
        ),
        "tags": ["defense", "passive"],
    },
    "reckless attack": {
        "summary": "Trade defense for accuracy by going all-in on your offense.",
        "description": (
            "When you attack recklessly, you swing with full commitment to improve your chance to hit, but you expose yourself in return. "
            "This is a voluntary risk-reward toggle, not a free passive buff.\n\n"
            "Use it when landing the hit matters more than staying safe, especially while raging or when you want to push advantage-based damage."
        ),
        "effect": "Improves melee attack reliability while increasing the danger of incoming attacks.",
        "tags": ["combat", "risk-reward"],
    },
    "danger sense": {
        "summary": "You react quickly to visible threats and effects that can be dodged.",
        "description": (
            "Danger Sense is a defensive awareness feature that improves your odds against hazards, blasts, and similar threats you can actually "
            "notice. It does not replace all saving throw defenses, but it makes you much harder to catch flat-footed in obvious danger zones.\n\n"
            "In play, pressure this during trap checks, spell bursts, and breath-weapon style tests where visibility and reaction matter."
        ),
        "tags": ["defense", "awareness"],
    },
    "primal knowledge": {
        "summary": "Your barbarian instincts now support exploration and survival as well as combat.",
        "description": (
            "Primal Knowledge expands the barbarian beyond pure damage. It adds utility-facing competence so the class contributes more cleanly in "
            "tracking, movement, scouting, or wilderness-adjacent scenes depending on the exact build."
        ),
        "tags": ["utility", "exploration"],
    },
    "fast movement": {
        "summary": "You move faster than most front-line warriors, helping you stick to priority targets.",
        "description": (
            "This passive speed increase makes it easier to start fights on your terms, close gaps, and keep pressure on fragile targets. The value "
            "should apply automatically in the sheet and remain visible in combat movement surfaces."
        ),
        "tags": ["mobility", "passive"],
    },
    "feral instinct": {
        "summary": "Your battlefield instincts make it harder to catch you slow or unready.",
        "description": (
            "Feral Instinct is about acting early and staying combat-ready. It should noticeably improve how often the barbarian gets to set the tone "
            "of an encounter instead of reacting late."
        ),
        "tags": ["initiative", "combat"],
    },
    "instinctive pounce": {
        "summary": "When you ignite your combat state, you also gain immediate pressure and repositioning power.",
        "description": (
            "This feature turns your rage opener into a movement tool as well as a damage setup. It is there to help you actually reach the target "
            "that matters when the fight starts."
        ),
        "tags": ["mobility", "combat"],
    },
    "relentless rage": {
        "summary": "Dropping you is much harder once your fury is fully awake.",
        "description": (
            "Relentless Rage is a survival backstop. When a normal fighter would fall, you get a chance to stay upright and keep controlling the "
            "front line. This should feel like a dramatic durability feature, not a minor note buried in text."
        ),
        "tags": ["defense", "survival"],
    },
    "persistent rage": {
        "summary": "Your rage is easier to maintain, making the combat state more reliable over long exchanges.",
        "description": (
            "Persistent Rage reduces the chance that your signature state drops off at the wrong time. It mainly matters in multi-round fights, "
            "disruptive control situations, and any encounter where momentum matters."
        ),
        "tags": ["combat", "resource"],
    },
    "primal champion": {
        "summary": "Your body reaches a legendary peak of raw physical dominance.",
        "description": (
            "This capstone massively improves the barbarian’s raw physical profile and pushes the class into true endgame bruiser territory. "
            "The sheet should reflect the stat impact directly in attacks, saves, checks, hit points, and any other derived totals that depend on it."
        ),
        "tags": ["capstone", "stats"],
    },
    "bardic inspiration": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "resourceName": "Bardic Inspiration",
        "trackUses": True,
        "summary": "Grant an ally a die they can spend later to swing a key roll in your party’s favor.",
        "description": (
            "As a bonus action, you inspire a creature so it can add the Bardic Inspiration die to an important future roll. This is one of the bard’s "
            "core support tools and should feel visible, easy to spend, and easy to track.\n\n"
            "In play, use it before decisive attacks, saves, or ability checks instead of hoarding it too long. The sheet should make the die size, "
            "remaining uses, and refresh timing obvious."
        ),
        "effect": "Creates a flexible support resource that helps the party pass important rolls.",
        "range": "60 feet",
        "duration": "10 minutes",
        "trigger": "Use before an ally makes an ability check, attack roll, or saving throw that matters.",
        "usage": "Spend 1 Bardic Inspiration use",
        "recovery": "Refresh depends on level; later bard progression improves how often this comes back.",
        "tags": ["support", "resource", "social"],
    },
    "jack of all trades": {
        "summary": "You are broadly competent even outside your best skills.",
        "description": (
            "Jack of All Trades raises the bard floor on many checks, making the class feel smart, flexible, and rarely useless outside its primary "
            "proficiencies. This should influence derived skill math across the sheet, not just live as flavor text."
        ),
        "tags": ["skills", "utility"],
    },
    "song of rest": {
        "summary": "Your party gets better value from downtime healing during rests.",
        "description": (
            "Song of Rest improves short-rest recovery for the group. It is not an action button you spam in combat; it is a rest-phase quality boost "
            "that should be visible when the table is reviewing recovery options."
        ),
        "tags": ["healing", "rest"],
    },
    "expertise": {
        "summary": "You push chosen skills into true specialty territory.",
        "description": (
            "Expertise doubles down on a few signature proficiencies so your character becomes exceptional instead of merely trained. In the sheet, the "
            "chosen skills should clearly jump above ordinary proficiency math."
        ),
        "tags": ["skills", "passive"],
    },
    "countercharm": {
        "section": "Actions",
        "type": "action",
        "summary": "Use performance or force of presence to protect allies against mental disruption.",
        "description": (
            "Countercharm is a defensive support action for situations where fear, charm, or similar control effects are threatening the party. It is a "
            "situational feature, but when the right fight appears it should feel like a real answer, not dead text."
        ),
        "tags": ["support", "defense", "action"],
    },
    "magical secrets": {
        "summary": "You learn powerful off-list magic, widening what your bard can solve.",
        "description": (
            "Magical Secrets is one of the bard’s biggest identity spikes. It lets you poach spells that radically change your support, control, or burst "
            "toolkit. The sheet should make those extra spell choices feel first-class, not like a hidden exception."
        ),
        "tags": ["spellcasting", "customization"],
    },
    "font of inspiration": {
        "summary": "Your inspiration engine is now much easier to keep online.",
        "description": (
            "This progression point changes the cadence of Bardic Inspiration recovery. It matters because it decides whether the bard can treat inspiration "
            "as a premium panic button or as a regular combat rhythm tool."
        ),
        "tags": ["resource", "support"],
    },
    "superior inspiration": {
        "summary": "Even when running dry, you are less likely to start an important scene empty-handed.",
        "description": (
            "Superior Inspiration is an endgame reliability feature. It exists so the bard’s signature support economy feels online more often at the "
            "start of high-level encounters."
        ),
        "tags": ["capstone", "resource"],
    },
    "channel divinity": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Channel Divinity",
        "trackUses": True,
        "summary": "Spend divine power on subclass or core cleric effects such as bursts of support, turning, or domain tools.",
        "description": (
            "Channel Divinity is a spendable divine resource that powers major cleric buttons. The exact option depends on your build, but the important "
            "thing is that the sheet clearly surfaces the resource, the action timing, and the linked divine options."
        ),
        "recovery": "Usually refreshes on a Short or Long Rest depending on the surfaced class rules.",
        "tags": ["divine", "resource", "support"],
    },
    "turn undead": {
        "section": "Actions",
        "type": "action",
        "actionType": "Action",
        "resourceName": "Channel Divinity",
        "summary": "Present your holy symbol and force undead in range to make a Wisdom save or be turned.",
        "description": (
            "Each undead that fails its save is Turned for 1 minute (or until it takes damage). A turned creature must spend its turns trying to move away "
            "from you, cannot willingly move closer, and cannot take reactions. It can only Dash or try to escape effects that stop movement."
        ),
        "effect": "Undead control aura; later cleric levels may destroy low-CR undead based on your class progression.",
        "range": "30 ft from you",
        "duration": "Up to 1 minute (ends early when the target takes damage)",
        "save": "Wisdom saving throw (your cleric spell save DC)",
        "trigger": "Use when undead pressure the front line or threaten fragile allies.",
        "usage": "Spend 1 Channel Divinity use",
        "recovery": "Channel Divinity usually refreshes on a Short or Long Rest per class progression.",
        "tags": ["divine", "control", "action", "resource"],
    },
    "divine spark": {
        "section": "Actions",
        "type": "action",
        "summary": "Release a burst of divine energy for healing or harm.",
        "description": (
            "Divine Spark is the kind of flexible divine button that should feel immediately readable: pick the right target, apply the right mode, and "
            "resolve the effect cleanly without needing outside references."
        ),
        "tags": ["divine", "healing", "damage", "action"],
    },
    "divine order": {
        "summary": "Choose which kind of cleric you are emphasizing and let that choice shape the rest of the build.",
        "description": (
            "Divine Order is a structural class choice. It should influence whether the cleric reads more like a front-line divine anchor or a dedicated "
            "spell/support specialist."
        ),
        "tags": ["build", "divine"],
    },
    "blessed strikes": {
        "summary": "Your weapon or cantrip pressure carries a reliable divine rider.",
        "description": (
            "Blessed Strikes gives the cleric a steadier damage floor so cantrip turns and weapon turns both feel less flat. It should appear wherever the "
            "relevant attacks or spell cards are being surfaced."
        ),
        "tags": ["damage", "divine"],
    },
    "divine intervention": {
        "section": "Actions",
        "type": "action",
        "summary": "Call directly on your deity for a dramatic miracle when the moment is big enough.",
        "description": (
            "Divine Intervention is a high-impact divine request, not a routine combat button. It should read like a campaign-level tool that can swing "
            "major situations rather than a small numeric bonus."
        ),
        "tags": ["divine", "capstone", "action"],
    },
    "wild shape": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Wild Shape",
        "trackUses": True,
        "summary": "Transform into beast forms to scout, survive, or fight from an entirely different stat profile.",
        "description": (
            "Wild Shape changes how the druid interacts with the game by swapping into a beast form with different mobility, senses, and combat options. "
            "It is both an exploration tool and, for some circles, a combat engine.\n\n"
            "In play, the important questions are what form you can currently access, how many uses remain, and what happens to your resources and state "
            "while transformed."
        ),
        "duration": "Usually hours equal to half your druid level (minimum 1 hour), unless ended early.",
        "trigger": "Use when you need beast mobility, survivability, scouting, or circle-specific combat form pressure.",
        "usage": "Spend 1 Wild Shape use",
        "recovery": "Track uses and rest refresh directly in the sheet resource area.",
        "tags": ["shapechange", "resource", "exploration"],
    },
    "druidic": {
        "summary": "You gain access to the hidden language and cultural signals of druids.",
        "description": (
            "Druidic is mostly a world and communication feature, but it matters because it gives the class an identity hook that can surface in exploration, "
            "secrets, and faction-style interactions."
        ),
        "tags": ["language", "flavor", "utility"],
    },
    "primal order": {
        "summary": "Your druid chooses a direction that shapes how the class plays moment to moment.",
        "description": (
            "Primal Order is an early build-shaping choice that steers the druid toward a different play emphasis. It should be visible in the sheet because "
            "it changes what the player expects the character to be good at."
        ),
        "tags": ["build", "spellcasting"],
    },
    "land's stride": {
        "summary": "Terrain and natural obstacles slow you down less than they slow other people.",
        "description": (
            "Land's Stride is an exploration and battlefield mobility feature. It matters when the map has rough terrain, difficult plants, or similar "
            "environmental friction that would normally tax movement."
        ),
        "tags": ["mobility", "exploration"],
    },
    "wild companion": {
        "summary": "You can create or summon a familiar-style natural helper for scouting and utility.",
        "description": (
            "Wild Companion gives the druid a flexible utility piece that is great for scouting, delivering help, and solving problems without risking the "
            "whole party. It should not disappear into generic notes."
        ),
        "tags": ["summon", "utility"],
    },
    "beast spells": {
        "summary": "Your spellcasting remains online in forms where it normally would not.",
        "description": (
            "Beast Spells removes one of the biggest friction points in shape-based play by letting high-level druids keep meaningful magic access while "
            "shifted. That is a major usability and power spike for the class."
        ),
        "tags": ["spellcasting", "shapechange"],
    },
    "archdruid": {
        "summary": "Your mastery over shape and primal magic reaches its peak.",
        "description": (
            "Archdruid is a late-game identity capstone that makes the class’s signature systems feel effortless. The exact expression depends on the ruleset, "
            "but it should always feel like a major liberation of the druid engine."
        ),
        "tags": ["capstone", "spellcasting", "shapechange"],
    },
    "second wind": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "resourceName": "Second Wind",
        "trackUses": True,
        "summary": "Spend a bonus action to stabilize yourself with a burst of self-healing.",
        "description": (
            "Second Wind is the fighter’s emergency self-sustain button. It should be quick to read and quick to use, especially because it often decides "
            "whether the fighter can hold the line for one more round."
        ),
        "effect": "Restore hit points to yourself without giving up your main action.",
        "recovery": "Refreshes with rest based on the fighter resource rules surfaced in the sheet.",
        "tags": ["healing", "resource", "combat"],
    },
    "action surge": {
        "section": "Class Features",
        "type": "special",
        "resourceName": "Action Surge",
        "trackUses": True,
        "summary": "Explode your tempo for one turn and do something extra that most characters simply cannot.",
        "description": (
            "Action Surge is a defining fighter spike tool. It is about tempo, burst, and solving a turn right now rather than later. The sheet should make "
            "the remaining uses obvious because the player’s whole tactical plan may hinge on it."
        ),
        "effect": "Gain an extra action on your turn within the feature’s current limits.",
        "duration": "This turn only",
        "trigger": "Use when an extra action will decisively finish a target, secure position, or rescue tempo.",
        "usage": "Spend 1 Action Surge use",
        "recovery": "Usually returns on a Short or Long Rest.",
        "tags": ["combat", "resource", "burst"],
    },
    "fighting style": {
        "summary": "You adopt a permanent combat specialty that changes how your attacks or defenses feel every round.",
        "description": (
            "Fighting Style is passive, but it should still matter visually because it changes the math or utility of your preferred combat pattern. This is "
            "one of the first identity-setting picks for weapon classes."
        ),
        "tags": ["combat", "passive"],
    },
    "weapon mastery": {
        "summary": "You unlock weapon rider properties that make attacks do more than just deal damage.",
        "description": (
            "Weapon Mastery gives trained weapons additional tactical texture. The important thing is not just knowing you have mastery, but understanding which "
            "weapons can trigger which rider and when that matters in a fight."
        ),
        "tags": ["combat", "weapons"],
    },
    "indomitable": {
        "resourceName": "Indomitable",
        "trackUses": True,
        "summary": "Refuse a bad saving throw outcome when the fight cannot afford it.",
        "description": (
            "Indomitable is a defensive clutch feature that protects the fighter from losing turns or entire encounters to one failed save. It is most valuable "
            "against debilitating control, charm, fear, paralysis, and similar effects."
        ),
        "tags": ["defense", "resource"],
    },
    "tactical mind": {
        "summary": "You bring a disciplined, tactical edge that improves decision quality and consistency.",
        "description": (
            "Tactical Mind represents fighter reliability outside of pure damage math. It should be surfaced as a meaningful utility-facing layer, not hidden "
            "behind vague labels."
        ),
        "tags": ["utility", "skills"],
    },
    "tactical shift": {
        "summary": "You can reposition without surrendering all of your offensive momentum.",
        "description": (
            "Tactical Shift exists so the fighter can move, recover spacing, or rescue a turn without feeling locked in place. It matters most on maps with "
            "heavy positioning pressure."
        ),
        "tags": ["mobility", "combat"],
    },
    "monk's focus": {
        "resourceName": "Focus Points",
        "trackUses": True,
        "summary": "Your focus pool fuels the monk’s best mobility, defense, and burst techniques.",
        "description": (
            "Focus Points are the core spendable engine of the monk. The number left, the refresh timing, and the techniques that consume them should always "
            "be obvious to the player."
        ),
        "recovery": "Refreshes on rest according to the monk rules surfaced by the sheet.",
        "tags": ["resource", "combat", "mobility"],
    },
    "martial arts": {
        "summary": "Your unarmed strikes, monk weapons, and action flow now work as a connected martial system.",
        "description": (
            "Martial Arts is the monk’s core combat engine. It changes attack cadence, weapon expectations, and how bonus action offense comes online. If this "
            "is wrong, the whole class feels wrong."
        ),
        "tags": ["combat", "unarmed"],
    },
    "flurry of blows": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Spend focus to convert momentum into extra strikes.",
        "description": (
            "Flurry of Blows is the monk’s classic burst option. It turns a good opening into real pressure and should clearly show both the focus spend and the "
            "extra attack sequence it creates."
        ),
        "tags": ["combat", "resource", "unarmed"],
    },
    "patient defense": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Spend focus to become much harder to pin down or hit cleanly.",
        "description": (
            "Patient Defense is the monk’s answer when survival matters more than damage. It should be readable as a defensive stance choice rather than a mystery "
            "button."
        ),
        "tags": ["defense", "resource"],
    },
    "step of the wind": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Spend focus to move like a problem the battlefield cannot easily hold.",
        "description": (
            "Step of the Wind is about verticality, escape, and suddenly being in the right place. It matters on crowded maps, long distances, or fights where "
            "position decides who wins."
        ),
        "tags": ["mobility", "resource"],
    },
    "deflect attacks": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "Use your reaction to blunt or redirect incoming punishment.",
        "description": (
            "Deflect Attacks is a reactive defense that should feel immediate and tactical. When it is available, the player should know they have a real answer "
            "to ranged or weapon pressure instead of eating every hit full-force."
        ),
        "tags": ["reaction", "defense"],
    },
    "slow fall": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "Reduce fall damage and turn dangerous height into a manageable problem.",
        "description": (
            "Slow Fall is situational, but when it matters it matters a lot. The feature is there to make vertical maps and risky traversal feel like monk territory."
        ),
        "tags": ["reaction", "mobility", "defense"],
    },
    "stunning strike": {
        "summary": "Spend focus on a hit to threaten one of the strongest control riders in the class.",
        "description": (
            "Stunning Strike lets the monk convert a successful hit into a saving throw that can cripple a target’s turn. It is one of the class’s highest-value "
            "resource spends and should clearly show the trigger, save, and cost."
        ),
        "effect": "Control rider on a hit, usually forcing a Constitution-based defensive check from the target.",
        "tags": ["control", "resource", "combat"],
    },
    "stillness of mind": {
        "summary": "You can shake off mental disruption and regain control over yourself.",
        "description": (
            "Stillness of Mind is a self-stabilizing tool for moments when fear, charm, or similar effects would otherwise rob the monk of tempo."
        ),
        "tags": ["defense", "mind"],
    },
    "quivering palm": {
        "summary": "Plant a delayed finishing technique that can decide elite encounters.",
        "description": (
            "Quivering Palm is a high-level signature technique with enormous threat value. It should feel like a terrifying setup/payoff feature, not a vague note."
        ),
        "tags": ["capstone", "control", "damage"],
    },
    "lay on hands": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Lay on Hands",
        "trackUses": True,
        "summary": "Spend points from a healing pool to rescue allies or stabilize the front line.",
        "description": (
            "Lay on Hands is reliable, controllable healing. It matters because it is not random: the player decides exactly how much of the pool to spend and "
            "whether the moment calls for topping off, picking someone up, or removing a key condition."
        ),
        "effect": "Convert points from a limited pool into healing or specific restorative effects.",
        "range": "Touch",
        "trigger": "Use when an ally needs immediate healing, stabilization, or condition support.",
        "usage": "Spend points from your Lay on Hands pool (up to pool maximum).",
        "recovery": "The pool refreshes on a Long Rest.",
        "tags": ["healing", "resource", "divine"],
    },
    "divine sense": {
        "section": "Actions",
        "type": "action",
        "summary": "Sweep the area for strong supernatural presences that matter to a holy warrior.",
        "description": (
            "Divine Sense is an information tool. It helps the paladin confirm whether celestial, fiendish, undead, or similarly charged threats are present, "
            "which can change how the party approaches a scene."
        ),
        "tags": ["utility", "divine", "action"],
    },
    "divine smite": {
        "summary": "Spend magical fuel on a hit to turn a weapon strike into a burst of radiant punishment.",
        "description": (
            "Divine Smite is the paladin’s classic burst converter. You do not use it blindly; you spend it when a hit lands and the target or moment is worth "
            "the slot. That timing is what makes the feature feel powerful."
        ),
        "effect": "Adds radiant burst damage to a weapon hit by spending magical fuel.",
        "tags": ["combat", "burst", "spellcasting"],
    },
    "divine health": {
        "summary": "Your divine resilience makes you harder to shut down with disease or corruption.",
        "description": (
            "Divine Health is passive but meaningful. It protects the paladin from a category of problems that can otherwise derail long-form adventuring days."
        ),
        "tags": ["defense", "divine"],
    },
    "restoring touch": {
        "summary": "Your healing power becomes more flexible and can answer more than raw hit point loss.",
        "description": (
            "Restoring Touch expands the paladin’s support value by letting the class treat conditions and recovery needs that ordinary weapon turns cannot solve."
        ),
        "tags": ["healing", "support", "divine"],
    },
    "aura of protection": {
        "summary": "Allies near you become harder to break because your presence strengthens their saving throws.",
        "description": (
            "Aura of Protection is one of the strongest team-defense features in the game. Positioning matters because allies only benefit while inside the aura. "
            "The sheet should make the aura radius and defensive value obvious."
        ),
        "tags": ["aura", "support", "defense"],
    },
    "aura of courage": {
        "summary": "Your presence helps the party fight through fear and panic.",
        "description": (
            "Aura of Courage is a positioning-based morale shield. It matters when encounters use fear to scatter the group or strip turns away from the party."
        ),
        "tags": ["aura", "support", "mind"],
    },
    "faithful steed": {
        "summary": "You gain a reliable divine mount or companion for travel, control, and presence.",
        "description": (
            "Faithful Steed is more than flavor. It changes travel, positioning, and sometimes combat reach, so it should be surfaced as a real class tool."
        ),
        "tags": ["summon", "mobility", "divine"],
    },
    "radiant strikes": {
        "summary": "Your weapon routine gains a holy damage rider that keeps your baseline pressure threatening.",
        "description": (
            "Radiant Strikes smooths the paladin’s sustained damage between bigger burst turns. It should be visible on attack output rather than hidden in a passive list."
        ),
        "tags": ["damage", "divine"],
    },
    "sneak attack": {
        "summary": "Once per turn, a correctly set-up hit deals a large spike of precision damage.",
        "description": (
            "Sneak Attack is the rogue’s signature damage engine. The important thing is understanding the trigger conditions and seeing the current damage dice clearly, "
            "because the entire class feels wrong when those are muddy."
        ),
        "tags": ["combat", "precision"],
    },
    "thieves' cant": {
        "summary": "You can communicate through hidden criminal language, codes, and implied signals.",
        "description": (
            "Thieves’ Cant is a narrative and infiltration feature that pays off in urban play, social stealth, and covert exchanges."
        ),
        "tags": ["language", "utility", "social"],
    },
    "cunning action": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "You convert your bonus action into mobility and positioning control every round.",
        "description": (
            "Cunning Action is what makes the rogue feel slippery. It lets you disengage, dash, or hide without losing your main offensive turn, which is exactly what "
            "a skirmisher needs to stay alive."
        ),
        "tags": ["mobility", "stealth", "combat"],
    },
    "steady aim": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Stand still, line up the shot, and improve your chance to land the hit that matters.",
        "description": (
            "Steady Aim is a deliberate trade: give up movement this turn in exchange for better attack quality. It is built for precision turns where landing the hit matters most."
        ),
        "tags": ["combat", "precision"],
    },
    "uncanny dodge": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "Use your reaction to blunt a hit that would otherwise land too hard.",
        "description": (
            "Uncanny Dodge is a reaction-based survival button. It matters on boss hits, sniper hits, and any time the rogue gets caught with less room to avoid damage entirely."
        ),
        "tags": ["reaction", "defense"],
    },
    "evasion": {
        "summary": "Dexterity-based area threats hurt you less when you react well.",
        "description": (
            "Evasion turns many reflex-based hazards into manageable or even near-ignored problems. It is a major quality-of-life and survival boost for agile builds."
        ),
        "tags": ["defense", "agility"],
    },
    "reliable talent": {
        "summary": "Your practiced rogue skills become hard to embarrass with low rolls.",
        "description": (
            "Reliable Talent changes the floor on important proficiencies. At this point, the rogue stops feeling merely skilled and starts feeling dependable."
        ),
        "tags": ["skills", "passive"],
    },
    "stroke of luck": {
        "summary": "When failure would be disastrous, you can bend a key moment back in your favor.",
        "description": (
            "Stroke of Luck is an elite reliability feature that lets a rogue rescue a critical attack or check. It should be treated as a dramatic last-word tool."
        ),
        "tags": ["capstone", "precision"],
    },
    "spellcasting": {
        "summary": "You gain access to spell slots, a spellcasting ability, and a growing library of magical options.",
        "description": (
            "Spellcasting is the rules engine that turns this class into a caster. It should clearly define your spell ability, slot progression, preparation or known-spell rules, "
            "and where those spells are surfaced in the sheet."
        ),
        "tags": ["spellcasting", "core"],
    },
    "font of magic": {
        "section": "Class Features",
        "type": "special",
        "resourceName": "Sorcery Points",
        "trackUses": True,
        "summary": "Your sorcery points let you bend spellcasting into a more flexible economy.",
        "description": (
            "Font of Magic is the sorcerer’s resource engine. It lets you convert between magical fuel and spell output, so the sheet should make both the pool and the spend paths easy to audit."
        ),
        "usage": "Spend Sorcery Points to create slots, or spend spell slots to regain Sorcery Points per class rules.",
        "recovery": "Sorcery Points refresh on a Long Rest.",
        "tags": ["spellcasting", "resource"],
    },
    "metamagic": {
        "section": "Class Features",
        "type": "special",
        "resourceName": "Sorcery Points",
        "summary": "Alter how your spells work instead of merely choosing which spell to cast.",
        "description": (
            "Metamagic is a major sorcerer identity feature because it changes spell delivery itself. It should show the available options, their costs, and the kinds of spell turns they improve."
        ),
        "trigger": "Apply when you cast an eligible spell and want to reshape range, target count, timing, or save pressure.",
        "usage": "Spend Sorcery Points based on the selected Metamagic option.",
        "recovery": "Uses depend on Sorcery Point recovery (typically Long Rest).",
        "tags": ["spellcasting", "resource", "customization"],
    },
    "sorcery incarnate": {
        "summary": "Your magical state becomes more intense, pushing sorcerer turns toward true burst casting.",
        "description": (
            "Sorcery Incarnate is a high-impact spellcasting empowerment state. It should read like a turn-shaping escalation tool, not a generic passive note."
        ),
        "tags": ["spellcasting", "burst"],
    },
    "innate sorcery": {
        "summary": "Your magic comes from your nature, and your sheet should make that feel obvious and active.",
        "description": (
            "Innate Sorcery is an identity feature that frames the sorcerer’s relationship with magic as internal, volatile, and personal. It should reinforce that the class’s power is inborn, not merely studied."
        ),
        "tags": ["spellcasting", "identity"],
    },
    "arcane recovery": {
        "resourceName": "Arcane Recovery",
        "trackUses": True,
        "summary": "Recover a chunk of spell economy during rest so the wizard can keep solving problems.",
        "description": (
            "Arcane Recovery is a pacing feature. It rewards good rest timing and ensures the wizard does not feel empty too early in a long adventuring day."
        ),
        "tags": ["spellcasting", "rest", "resource"],
    },
    "memorize spell": {
        "summary": "You can adapt your prepared magic more fluidly than a normal prepared caster.",
        "description": (
            "Memorize Spell is about adaptability. It makes the wizard better at pivoting when the problem in front of the party changes."
        ),
        "tags": ["spellcasting", "utility"],
    },
    "spell mastery": {
        "summary": "Your favorite lower-level spells become effortless signature tools.",
        "description": (
            "Spell Mastery is one of the wizard’s most satisfying late-game powers because it turns bread-and-butter magic into near-constant utility."
        ),
        "tags": ["spellcasting", "capstone"],
    },
    "signature spells": {
        "summary": "A few spells become part of your identity and should feel easier to lean on regularly.",
        "description": (
            "Signature Spells is an endgame efficiency feature that rewards planning around a personal core spell kit."
        ),
        "tags": ["spellcasting", "capstone"],
    },
    "pact magic": {
        "section": "Class Features",
        "type": "passive",
        "resourceName": "Pact Slots",
        "trackUses": True,
        "summary": "Your spell slots are few, high-leverage, and refreshed on a different cadence than most casters.",
        "description": (
            "Pact Magic is the heart of warlock spellcasting. It should be obvious that you are not using the same slot economy as a wizard or sorcerer."
        ),
        "usage": "Spend pact slots to cast warlock spells; all pact slots cast at your current pact slot level.",
        "recovery": "Pact slots refresh on a Short Rest and Long Rest.",
        "tags": ["spellcasting", "resource"],
    },
    "eldritch invocations": {
        "summary": "You bolt permanent magical customizations onto your character one choice at a time.",
        "description": (
            "Eldritch Invocations are a major warlock customization surface. Each one changes how the character plays, so the sheet should treat them as meaningful build-defining unlocks."
        ),
        "tags": ["customization", "spellcasting"],
    },
    "pact boon": {
        "section": "Class Features",
        "type": "passive",
        "summary": "Your patron relationship manifests as a concrete magical tool or companion style.",
        "description": (
            "Pact Boon is a foundational warlock identity pick. It changes how the class behaves in combat, exploration, or utility scenes and should never feel buried."
        ),
        "trigger": "Use this to define your core warlock lane (weapon, tome, chain, or other boon path).",
        "tags": ["build", "patron"],
    },
    "mystic arcanum": {
        "summary": "You gain access to rare, high-impact magic outside the ordinary slot cycle.",
        "description": (
            "Mystic Arcanum gives the warlock unique top-end magic access. These are premium cast choices and should be surfaced distinctly from ordinary pact slots."
        ),
        "tags": ["spellcasting", "endgame"],
    },
    "magical cunning": {
        "summary": "You squeeze better sustained value out of your limited magical economy.",
        "description": (
            "Magical Cunning supports the warlock’s unique pacing. It matters because the class often lives or dies on whether it can stay relevant between short rests."
        ),
        "tags": ["spellcasting", "resource"],
    },
    "brutal strike": {
        "summary": "Turn a heavy hit into extra control, pressure, or raw damage when you really need the swing to matter.",
        "description": (
            "Brutal Strike upgrades your strongest melee hits into bigger momentum plays. Depending on the level row, it either adds more damage, lets you layer on extra riders, or both.\n\n"
            "In play, use this when a normal hit is not enough and you want the attack to shift the fight, not just shave off a few hit points."
        ),
        "effect": "Adds extra brutality to a successful hit, with stronger payoff as the barbarian levels.",
        "tags": ["combat", "burst", "control"],
    },
    "indomitable might": {
        "summary": "Your physical strength becomes so reliable that brute-force checks stop feeling swingy.",
        "description": (
            "Indomitable Might turns peak Strength into dependable performance whenever the barbarian is trying to overpower, break through, hold fast, or force a physical solution.\n\n"
            "This is not flashy, but it matters every time the scene asks whether sheer power can solve the problem."
        ),
        "tags": ["strength", "passive", "utility"],
    },
    "greater divine intervention": {
        "summary": "Your plea for divine aid becomes dramatically more reliable when the moment is truly important.",
        "description": (
            "Greater Divine Intervention is meant to feel like a late-game holy turning point. When you call for help, the response should feel less like a long-shot gamble and more like a genuine miracle button.\n\n"
            "Use it for scenes the table will remember: saving the group, reversing disaster, or shifting a battle that normal magic cannot fix cleanly."
        ),
        "tags": ["divine", "capstone", "support"],
    },
    "body and mind": {
        "summary": "Your discipline keeps both your body and your mind steady under pressure.",
        "description": (
            "Body and Mind is a high-level monk refinement feature. It reinforces the idea that the monk is hard to slow, hard to break, and difficult to throw off balance once fully mastered.\n\n"
            "In play, this should feel like calm reliability rather than a tiny background bonus."
        ),
        "tags": ["defense", "survival", "passive"],
    },
    "aura of courage extension": {
        "summary": "Your Aura of Courage reaches farther, letting more allies stay brave near you.",
        "description": (
            "This upgrade increases the practical footprint of your anti-fear support. It matters because aura features are all about positioning, and a wider radius makes the paladin's presence much easier for the party to use."
        ),
        "tags": ["aura", "support", "passive"],
    },
    "roving": {
        "summary": "You travel faster and handle rough ground with much less friction.",
        "description": (
            "Roving pushes the ranger deeper into the mobile explorer role. It helps with pursuit, repositioning, difficult terrain, and the general feeling that the ranger moves through the world with less effort than most characters."
        ),
        "tags": ["mobility", "exploration", "passive"],
    },
    "tireless": {
        "summary": "You keep going longer than most people and recover from attrition more cleanly.",
        "description": (
            "Tireless supports the ranger fantasy of being self-sufficient on long hunts, rough travel, and grindy adventuring days.\n\n"
            "It matters most when the rest of the party is starting to feel worn down and the ranger still has enough energy to keep functioning well."
        ),
        "tags": ["survival", "exploration", "resource"],
    },
    "conjure volley": {
        "summary": "Loose a large-area ranged burst that punishes clustered enemies.",
        "description": (
            "Conjure Volley is a once-in-a-big-scene style ranged spell feature for rangers who want a real area attack instead of only single-target pressure.\n\n"
            "Use it when several enemies are grouped and a normal weapon attack string would not swing the fight hard enough."
        ),
        "tags": ["combat", "area", "spellcasting"],
    },
    "foe slayer": {
        "summary": "Your experience against hunted targets turns key attacks or damage rolls into more dependable finishers.",
        "description": (
            "Foe Slayer is a capstone hunter payoff. It exists so the ranger feels precise and deadly at the top end of play, especially against the target that truly matters most in the encounter."
        ),
        "tags": ["combat", "capstone", "precision"],
    },
    "subtle strikes": {
        "summary": "You create openings more easily, making precision damage feel more consistent once the fight is underway.",
        "description": (
            "Subtle Strikes smooths out the rogue's damage pattern by making it easier to line up the attack that counts.\n\n"
            "In play, this should make the rogue feel less dependent on perfect setup every single round."
        ),
        "tags": ["combat", "precision", "rogue"],
    },
    "elusive": {
        "summary": "Pinning you down becomes extremely difficult once your defensive instincts are fully refined.",
        "description": (
            "Elusive is a top-end rogue defense feature. It should feel like the character is almost never giving enemies the clean opening they wanted.\n\n"
            "This matters most in boss rounds, focused fire, and any scene where surviving one big hit changes the outcome."
        ),
        "tags": ["defense", "survival", "rogue"],
    },
    "eldritch master": {
        "summary": "You regain your pact power with frightening efficiency.",
        "description": (
            "Eldritch Master is a high-level recovery feature that ensures the warlock can keep bringing premium magic pressure into important scenes."
        ),
        "tags": ["spellcasting", "capstone", "resource"],
    },
}


def _summary_from_text(text: str) -> str:
    clean = " ".join(str(text or "").split())
    if not clean:
        return ""
    if len(clean) <= 140:
        return clean
    cut = clean[:137].rsplit(" ", 1)[0].strip()
    return (cut or clean[:137]).rstrip(" ,.;:") + "…"


_STAGE5B_FEATURE_OVERRIDES: dict[str, dict[str, Any]] = {
    "empowered strikes": {
        "summary": "Your strikes now count as a more reliable supernatural threat against resistant enemies.",
        "description": "Empowered Strikes ensures your fists and monk weapon pressure stay relevant when ordinary physical hits would start bouncing off defenses. In play, this should reassure the monk that signature attacks still matter against tougher magical creatures.",
        "tags": ["combat", "unarmed", "passive"],
    },
    "acrobatic movement": {
        "summary": "You move across the battlefield and vertical terrain with fewer normal limitations.",
        "description": "Acrobatic Movement pushes the monk deeper into the role of map-breaker. It matters most on elevation-heavy scenes, chase sequences, rooftops, ledges, and fights where getting to the right square is the whole problem.",
        "tags": ["mobility", "exploration"],
    },
    "heightened focus": {
        "summary": "Your focus engine becomes more forgiving, making your best techniques easier to sustain through a long fight.",
        "description": "Heightened Focus improves the reliability of your core monk resource loop. The player should be able to tell that spending focus is less punishing and that the class can stay online longer across repeated encounters.",
        "tags": ["resource", "combat"],
    },
    "self-restoration": {
        "summary": "You can actively clear off problems that would normally keep other front-liners shut down.",
        "description": "Self-Restoration is a quality-of-life and survivability spike. It lets the monk spend internal discipline on fixing conditions or setbacks that would otherwise steal turns, positioning, or momentum.",
        "tags": ["defense", "recovery"],
    },
    "deflect energy": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "Use your reaction to blunt incoming elemental or force-based punishment the way you already answer weapon pressure.",
        "description": "Deflect Energy extends the monk’s reactive defense package into magical threats. This matters in caster-heavy encounters where surviving the burst is more important than winning a pure damage race.",
        "tags": ["reaction", "defense", "magic"],
    },
    "disciplined survivor": {
        "summary": "Your body and mind become much harder to crack with failed saves or attrition.",
        "description": "Disciplined Survivor is a late-game reliability feature. It should read like a broad defensive upgrade that makes the monk harder to disable, poison, frighten, or collapse under layered pressure.",
        "tags": ["defense", "survival"],
    },
    "perfect focus": {
        "summary": "Your focus resource becomes much easier to maintain at the exact point where high-tier encounters start trying to exhaust it.",
        "description": "Perfect Focus is about consistency. The monk should feel less likely to enter an important scene empty or stay empty after the first explosive exchange.",
        "tags": ["resource", "survival"],
    },
    "superior defense": {
        "summary": "Your defensive tools upgrade into a premium survival mode for the nastiest fights on the table.",
        "description": "Superior Defense is not just another passive line. It is the monk’s statement that, at high level, surviving magical pressure, focused fire, and layered control is part of the class identity.",
        "tags": ["defense", "capstone"],
    },
    "aura improvements": {
        "summary": "Your paladin aura package scales up so more allies can benefit from your battlefield presence at once.",
        "description": "Aura Improvements matter because paladin positioning is party strategy. A larger or stronger aura changes how the whole group wants to stand, rotate, and push through control effects.",
        "tags": ["aura", "support", "progression"],
    },
    "cunning strike": {
        "summary": "Your Sneak Attack turns into a toolkit of rider effects instead of only raw damage.",
        "description": "Cunning Strike lets the rogue trade some damage for control, setup, and disruption. The important in-app job is making it clear that Sneak Attack is now also a menu of tactical choices, not just a single damage number.",
        "tags": ["combat", "control", "precision"],
    },
    "improved cunning strike": {
        "summary": "Your precision damage choices get broader and more threatening, giving the rogue more ways to decide a turn.",
        "description": "Improved Cunning Strike means the rogue’s on-hit control package matures. By this point the player should feel like each correct hit can reshape movement, setup, or the enemy’s next action.",
        "tags": ["combat", "control", "precision"],
    },
    "devious strikes": {
        "summary": "Your precision attacks now carry nastier secondary consequences when the setup lands.",
        "description": "Devious Strikes is a high-level rogue payoff. It says your successful setup does more than burst; it can also tilt the battlefield in ways that create the next winning turn.",
        "tags": ["combat", "control", "precision"],
    },
    "slippery mind": {
        "summary": "Your mind becomes much harder to lock down with fear, enchantment, or similar control.",
        "description": "Slippery Mind is a reliability feature. It protects the rogue from losing entire scenes to one bad mental save and helps the class keep playing like a cunning operator instead of dead weight.",
        "tags": ["defense", "mind"],
    },
    "studied attacks": {
        "summary": "Repeated pressure makes you better at reading openings and converting ordinary swings into cleaner hits.",
        "description": "Studied Attacks is a veteran-fighter feature about momentum and adaptation. The longer the exchange goes, the more the fighter should feel like a problem the enemy cannot keep solving the same way.",
        "tags": ["combat", "tempo"],
    },
    "eldritch patron": {
        "summary": "Your patron choice defines the special pressure, utility, and weirdness layered on top of the base warlock engine.",
        "description": "This is the identity fork for the class. The sheet should make it obvious that your patron is not flavor-only; it decides which control tools, defenses, and signature powers begin to appear in later levels.",
        "tags": ["subclass", "spellcasting", "customization"],
    },
    "eldritch blast": {
        "summary": "Your signature at-will blast is a core offensive tool that scales with you and works especially well with invocations.",
        "description": "Eldritch Blast is one of the main reasons warlocks stay threatening all day. The feature entry should point the player toward the spell card and make it obvious that invocations can dramatically change how this attack behaves.",
        "tags": ["spellcasting", "combat", "cantrip"],
    },
    "combat superiority": {
        "summary": "You gain Superiority Dice and maneuvers that turn the fighter into a tactical battlefield controller, not just a damage stick.",
        "description": "Combat Superiority is the whole Battle Master engine. The important thing is seeing your die pool, maneuver list, save DC, and recovery timing clearly enough that you actually spend the resource instead of forgetting it exists.",
        "resourceName": "Superiority Dice",
        "trackUses": True,
        "tags": ["combat", "resource", "control", "subclass"],
    },
    "student of war": {
        "summary": "Your battle study turns into either practical tool utility or broader maneuver flexibility.",
        "description": "Student of War gives the Battle Master more identity outside basic attack math. It can widen your out-of-combat competence or deepen the tactical menu you bring into a fight.",
        "tags": ["utility", "subclass"],
    },
    "know your enemy": {
        "summary": "Study a target long enough and you start reading what kind of fight it actually is before blades are drawn.",
        "description": "Know Your Enemy is information warfare. Use it before committing to a duel, ambush, or boss plan so the party has a sharper read on defenses, durability, and whether brute force is the right answer.",
        "tags": ["utility", "subclass", "analysis"],
    },
    "relentless": {
        "summary": "When the fight starts and your tactical fuel is empty, you still get a little something back so the subclass can function.",
        "description": "Relentless protects the Battle Master from feeling dead-on-arrival after a long adventuring day. It is a recovery safety net that keeps maneuvers relevant in the next encounter.",
        "tags": ["resource", "subclass", "recovery"],
    },
    "improved critical": {
        "summary": "Your threat range improves, making hard weapon hits spike more often over the course of a session.",
        "description": "Improved Critical is passive, but it changes the emotional rhythm of the class. The Champion should feel like a clean, reliable hitter who converts ordinary attack volume into more explosive turns than other fighters.",
        "tags": ["combat", "subclass", "passive"],
    },
    "athletic adept": {
        "summary": "Your physical game improves beyond basic attack math, making movement, climbs, jumps, and athletic scenes feel naturally champion-coded.",
        "description": "Athletic Adept is about being excellent in motion and exertion. It should make the Champion read as a complete athlete, not only a crit-focused damage chassis.",
        "tags": ["mobility", "utility", "subclass"],
    },
    "fighting style plus": {
        "summary": "You double down on your combat identity by gaining more permanent style shaping than most martial characters get.",
        "description": "Fighting Style Plus strengthens the Champion’s straightforward identity: better fundamentals, fewer gimmicks, more clean efficiency. The sheet should make the expanded style package easy to see.",
        "tags": ["combat", "subclass", "passive"],
    },
    "survivor": {
        "summary": "You regain staying power automatically in drawn-out fights, making it much harder to grind the Champion down.",
        "description": "Survivor is the subclass payoff for simply refusing to go away. It matters most in boss fights, attrition gauntlets, and any scene where the fighter must stay upright long after others would fade.",
        "tags": ["defense", "healing", "subclass"],
    },
    "weapon bond": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Your bonded weapons stay close, resist disarm pressure, and can be recalled when you need them.",
        "description": "Weapon Bond turns your chosen weapons into dependable extensions of the build. It matters in scenes with disarms, imprisonment, thrown weapons, or any setup where getting armed again quickly changes the turn.",
        "tags": ["combat", "subclass", "mobility"],
    },
    "war magic": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Weave weapon pressure into your cantrip turns so casting does not cost all your melee momentum.",
        "description": "War Magic is the classic Eldritch Knight bridge feature. It keeps the subclass from feeling split in half by letting spells and steel feed each other inside the same round.",
        "tags": ["combat", "subclass", "spellcasting"],
    },
    "eldritch strike": {
        "summary": "A weapon hit softens the target up for your next spell, creating a clean martial-to-magic combo line.",
        "description": "Eldritch Strike rewards sequencing. Hit first, then pressure the weakened save with a spell before the window closes. The sheet should make that combo logic obvious.",
        "tags": ["combat", "subclass", "spellcasting", "control"],
    },
    "arcane charge": {
        "summary": "When you unleash Action Surge, you also gain sudden teleporting pressure and better line control.",
        "description": "Arcane Charge turns one of the fighter’s best burst buttons into a reposition tool as well. It is there to help you explode a turn and appear exactly where the enemy does not want you.",
        "tags": ["mobility", "subclass", "burst"],
    },
    "improved war magic": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Your spell turns now keep real weapon pressure online even when you cast higher-impact magic.",
        "description": "Improved War Magic is the mature version of the subclass loop: cast real spells and still threaten with steel in the same round. This is the point where the battle-mage identity should feel complete.",
        "tags": ["combat", "subclass", "spellcasting"],
    },
    "mage hand legerdemain": {
        "summary": "Your Mage Hand becomes a real trickster tool for theft, setup, trap play, and misdirection at range.",
        "description": "Mage Hand Legerdemain is not just flavor. It turns a cantrip into a signature subclass utility system for stealing, planting, manipulating, or disarming without standing in the danger square yourself.",
        "tags": ["utility", "subclass", "spellcasting"],
    },
    "magical ambush": {
        "summary": "Hidden casting becomes much nastier because your target is easier to catch with the save-based spell that follows.",
        "description": "Magical Ambush rewards stealth-first spell play. Set up from hiding, fire the effect, and make the enemy struggle to shrug it off. The subclass should clearly communicate that hidden casting is part of the plan now.",
        "tags": ["subclass", "spellcasting", "stealth", "control"],
    },
    "versatile trickster": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Use your magical hand to create distraction and line up cleaner attacks on a chosen target.",
        "description": "Versatile Trickster converts your Mage Hand from utility piece into combat setup. It is a subclass reminder that the hand is part of your offense, not just your pickpocketing package.",
        "tags": ["subclass", "combat", "spellcasting"],
    },
    "spell thief": {
        "summary": "Turn an enemy caster’s success into your own advantage by stealing access to the magic they tried to use.",
        "description": "Spell Thief is a dramatic anti-caster capstone. It should feel rare, sharp, and memorable whenever it lands because it literally rewrites who gets to control that spell in the scene.",
        "tags": ["subclass", "spellcasting", "control"],
    },
    "assassinate": {
        "summary": "When combat starts on your terms, your opening attack routine becomes terrifyingly efficient.",
        "description": "Assassinate is about winning the first meaningful exchange. It rewards scouting, surprise, initiative play, and target selection so the rogue can delete or cripple a priority threat before the battle stabilizes.",
        "tags": ["subclass", "combat", "stealth", "burst"],
    },
    "infiltration expertise": {
        "summary": "You become much better at living inside a false role long enough for the mission to work.",
        "description": "Infiltration Expertise pushes the Assassin beyond pure combat. It supports disguise-led operations, social penetration, false identities, and longer cons where patience matters more than initiative.",
        "tags": ["subclass", "social", "utility"],
    },
    "imposter": {
        "summary": "Given enough study time, you can convincingly wear someone else’s voice, habits, and public face.",
        "description": "Imposter is a mission tool for deep infiltration. It matters in intrigue campaigns, prison breaks, political scenes, and any objective where becoming the wrong person is stronger than drawing a blade.",
        "tags": ["subclass", "social", "stealth"],
    },
    "death strike": {
        "summary": "Your best ambushes do not just hit hard; they threaten to turn one opening into absurd finishing damage.",
        "description": "Death Strike is the Assassin payoff for precision setup. When surprise actually happens, this feature exists to make that moment feel lethal enough that the whole subclass was worth building toward.",
        "tags": ["subclass", "burst", "combat"],
    },
    "fast hands": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Use your bonus action to manipulate objects, tools, and theft opportunities faster than most characters can react to.",
        "description": "Fast Hands turns environment interaction into part of your combat and heist rhythm. It is what lets the Thief feel like the subclass that always has one more trick involving a lever, item, pouch, or tool.",
        "tags": ["subclass", "bonus action", "utility", "combat"],
    },
    "second-story work": {
        "summary": "Climbing and jumping become part of your normal movement game instead of special obstacles.",
        "description": "Second-Story Work is a mobility identity feature. It should make windows, ledges, roofs, and balconies read like invitations instead of barriers.",
        "tags": ["subclass", "mobility", "exploration"],
    },
    "supreme sneak": {
        "summary": "When you move carefully, your stealth profile becomes markedly more reliable.",
        "description": "Supreme Sneak is straightforward but powerful: if you respect pace and positioning, you become much harder to detect while setting up the next play.",
        "tags": ["subclass", "stealth", "utility"],
    },
    "use magic device": {
        "summary": "You can break normal access restrictions on certain magic gear and make odd treasure matter to this rogue more than anyone else.",
        "description": "Use Magic Device is a loot-to-power feature. It turns strange scrolls, wands, and attunement-gated items into live options instead of things the rogue has to hand off to someone else.",
        "tags": ["subclass", "utility", "magic"],
    },
    "thief's reflexes": {
        "summary": "Your first combat round becomes explosively efficient because you effectively get two chances to act inside it.",
        "description": "Thief's Reflexes is a capstone-level tempo tool. In the right ambush or initiative order, it lets you win the room before slower enemies have finished understanding what started.",
        "tags": ["subclass", "combat", "tempo"],
    },
    "channel divinity: sacred weapon": {
        "section": "Actions",
        "type": "action",
        "summary": "Imbue your weapon with radiant certainty so your attacks land more reliably for the next stretch of combat.",
        "description": "Sacred Weapon is an accuracy-first oath button. Use it before the big exchange, especially against slippery enemies or bosses where simply landing smites matters more than flashy positioning.",
        "duration": "1 minute",
        "resourceName": "Channel Divinity",
        "trackUses": True,
        "tags": ["subclass", "divine", "combat", "resource"],
    },
    "aura of devotion": {
        "summary": "Allies near you become much harder to compromise with charm and social-control effects.",
        "description": "Aura of Devotion is a team-defense aura. It matters in enchantment-heavy fights, manipulation scenes, and any time the encounter wants to turn your own party against itself.",
        "tags": ["subclass", "aura", "support", "defense"],
    },
    "holy nimbus": {
        "section": "Actions",
        "type": "action",
        "summary": "You erupt into a radiant battle-state that punishes nearby enemies and marks you as a true divine threat.",
        "description": "Holy Nimbus is a capstone mode, not a filler ribbon. It should feel like a commitment button for major fights where being the glowing center of the battle is exactly the point.",
        "tags": ["subclass", "divine", "aura", "damage"],
    },
    "purity of spirit": {
        "summary": "Hostile supernatural creatures and influences struggle more to gain leverage over you.",
        "description": "Purity of Spirit is a passive shield against corruption and hostile extraplanar manipulation. It matters most in fiend, undead, aberration, and possession-flavored scenes.",
        "tags": ["subclass", "defense", "divine"],
    },
    "sacred weapon improvement": {
        "summary": "Your oath’s signature radiant weapon package scales up so your battlefield presence keeps pace in late game.",
        "description": "This improvement means your Devotion oath buttons should still feel relevant in endgame play instead of fading behind raw spell slots and smite math.",
        "tags": ["subclass", "progression", "divine"],
    },
    "channel divinity: nature's wrath": {
        "section": "Actions",
        "type": "action",
        "summary": "Call primal binding power onto a target and force it to fight through restraining natural energy.",
        "description": "Nature's Wrath is a control-first Channel Divinity option for locking down a dangerous enemy early. Use it when movement denial matters more than immediate damage.",
        "save": "Con save",
        "resourceName": "Channel Divinity",
        "trackUses": True,
        "tags": ["subclass", "control", "divine", "resource"],
    },
    "aura of warding": {
        "summary": "You project a protective field that blunts incoming spell damage for nearby allies.",
        "description": "Aura of Warding is a party durability engine against magical threats. Its real value shows up in caster battles, dragon breath alternatives, and any encounter defined by spell bursts rather than blades.",
        "tags": ["subclass", "aura", "support", "defense"],
    },
    "undying sentinel": {
        "summary": "You get a dramatic refusal-to-fall moment that helps the oath stay standing when the line should have broken.",
        "description": "Undying Sentinel is there for the scene where the paladin absolutely cannot be the one who drops first. It should feel like a major survivability promise, not a footnote.",
        "tags": ["subclass", "defense", "survival"],
    },
    "elder champion": {
        "section": "Actions",
        "type": "action",
        "summary": "For one major fight, you become a radiant avatar of the natural order and start overwhelming the area around you.",
        "description": "Elder Champion is a transformation-style capstone. It should be read as a boss-fight mode that upgrades your pressure, sustain, and spell threat all at once.",
        "tags": ["subclass", "capstone", "divine", "aura"],
    },
    "channel divinity: abjure enemy": {
        "section": "Actions",
        "type": "action",
        "summary": "Drive divine terror into a target and pin it down so it cannot simply walk away from judgment.",
        "description": "Abjure Enemy is for isolating a priority threat. It is strongest when fear plus movement denial lets the party collapse on one enemy before the rest can intervene.",
        "save": "Wis save",
        "resourceName": "Channel Divinity",
        "trackUses": True,
        "tags": ["subclass", "control", "divine", "resource"],
    },
    "channel divinity: vow of enmity": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Mark one enemy for relentless pressure and gain the accuracy edge needed to bring it down.",
        "description": "Vow of Enmity is a focus-fire feature. Pick the creature that most needs to die and turn your whole next stretch of combat into a concentrated hunt.",
        "duration": "1 minute",
        "resourceName": "Channel Divinity",
        "trackUses": True,
        "tags": ["subclass", "combat", "divine", "resource"],
    },
    "relentless avenger": {
        "summary": "Opportunity attacks now help you stay glued to the enemy instead of only punishing movement once.",
        "description": "Relentless Avenger reinforces the oath’s pursuit identity. When the marked target tries to slip away, you can keep the chase live instead of watching the moment disappear.",
        "tags": ["subclass", "mobility", "combat"],
    },
    "soul of vengeance": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "When your sworn enemy acts, you can answer with immediate divine retaliation.",
        "description": "Soul of Vengeance makes your marked target feel hunted every second it is still alive. It is a reaction-based pressure tool that turns Vow of Enmity into a truly personal duel.",
        "tags": ["subclass", "reaction", "combat"],
    },
    "avenging angel": {
        "section": "Actions",
        "type": "action",
        "summary": "Assume a terrifying angelic form that lets you dominate the air and break enemy morale.",
        "description": "Avenging Angel is a dramatic transformation capstone for pursuit-and-judgment fantasy. Use it when the fight deserves the full divine executioner version of the character.",
        "tags": ["subclass", "capstone", "divine", "fear"],
    },
    "expanded spells": {
        "summary": "Your patron expands the list of magic that naturally fits your build, giving your warlock more thematic answers to real problems.",
        "description": "Expanded Spells are not passive trivia. They shape which control, utility, and burst options feel native to your patron and should be visible wherever the player is checking what this subclass actually adds.",
        "tags": ["subclass", "spellcasting", "customization"],
    },
    "fey presence": {
        "section": "Actions",
        "type": "action",
        "summary": "Flood a close area with fey emotion and leave nearby creatures charmed or frightened for a brief opening.",
        "description": "Fey Presence is an early control pulse. It is strongest when multiple enemies are crowding your position and a one-round status swing buys the party tempo.",
        "save": "Wis save",
        "usage": "1 use per Short Rest",
        "resourceName": "Fey Presence",
        "trackUses": True,
        "tags": ["subclass", "control", "spellcasting", "resource"],
    },
    "misty escape": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "When you get hit, you can slip away in a burst of invisibility and reposition before the enemy can capitalize.",
        "description": "Misty Escape is a defensive panic button with real map value. It turns a bad hit into a chance to disappear, break line, and re-enter the fight from a better square.",
        "range": "60 ft",
        "usage": "1 use per Long Rest",
        "resourceName": "Misty Escape",
        "trackUses": True,
        "tags": ["subclass", "reaction", "defense", "mobility"],
    },
    "beguiling defenses": {
        "summary": "Charm effects stop being a clean answer against you and can even become a problem for the creature that tried them.",
        "description": "Beguiling Defenses is a hard anti-charm statement. It matters in social danger, fey-themed fights, and any encounter that wants to win through manipulation instead of damage.",
        "tags": ["subclass", "defense", "mind"],
    },
    "dark delirium": {
        "section": "Actions",
        "type": "action",
        "summary": "Trap a target inside a patron-shaped nightmare state that leaves it frightened or charmed and cut off from reality.",
        "description": "Dark Delirium is a single-target control capstone. Pick the creature whose removal or confusion matters most and make the fight smaller for everyone else.",
        "usage": "1 use per Long Rest",
        "resourceName": "Dark Delirium",
        "trackUses": True,
        "tags": ["subclass", "control", "mind", "capstone"],
    },
    "dark one's blessing": {
        "summary": "Every time you finish off a hostile creature, infernal patronage pays you back with temporary staying power.",
        "description": "Dark One's Blessing rewards aggressive last-hits and target cleanup. It helps the Fiend warlock snowball through multi-enemy fights instead of feeling fragile after the first exchange.",
        "tags": ["subclass", "healing", "survival"],
    },
    "dark one's own luck": {
        "summary": "When a crucial save or check is on the line, you can spike the roll with infernal fortune after seeing the number.",
        "description": "Dark One's Own Luck is a clutch reliability button. Save it for the failure that would actually cost the scene, not a trivial check the party can live without.",
        "usage": "1 use per Long Rest",
        "resourceName": "Dark One's Own Luck",
        "trackUses": True,
        "tags": ["subclass", "resource", "defense"],
    },
    "fiendish resilience": {
        "summary": "You can tune your defenses toward the damage type the day or dungeon is actually throwing at you.",
        "description": "Fiendish Resilience is a practical resistance tool. It rewards scouting and encounter reading because choosing the right damage type can make an entire stretch of play dramatically safer.",
        "tags": ["subclass", "defense", "adaptation"],
    },
    "hurl through hell": {
        "summary": "A successful hit can temporarily throw a target through nightmare dimensions and return it badly scarred.",
        "description": "Hurl Through Hell is one of the Fiend’s signature finishers. It should feel brutal, cinematic, and reserved for the target whose removal will swing the fight the most.",
        "usage": "1 use per Long Rest",
        "resourceName": "Hurl Through Hell",
        "trackUses": True,
        "dice": "10d10",
        "tags": ["subclass", "damage", "control", "capstone"],
    },
    "awakened mind": {
        "summary": "You gain low-friction telepathic contact with creatures you can see, opening up eerie coordination and social pressure.",
        "description": "Awakened Mind changes how the warlock can communicate, intimidate, and coordinate. It matters in stealth play, social discomfort, scouting, and any scene where silent communication is king.",
        "range": "30 ft",
        "tags": ["subclass", "utility", "mind"],
    },
    "entropic ward": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "Twist hostile probability so an attack is less likely to land, then turn the miss into your own opening.",
        "description": "Entropic Ward is both protection and setup. Use it when a dangerous hit is coming in or when turning defense into counter-pressure will reshape the next exchange.",
        "usage": "1 use per Short Rest",
        "resourceName": "Entropic Ward",
        "trackUses": True,
        "tags": ["subclass", "reaction", "defense", "combat"],
    },
    "thought shield": {
        "summary": "Your mind gains hard psychic defenses and becomes much harder to probe or bully telepathically.",
        "description": "Thought Shield matters in aberration, psionic, and manipulation-heavy play. It is the feature that says your brain is no longer easy territory for anything else to occupy.",
        "tags": ["subclass", "defense", "mind"],
    },
    "create thrall": {
        "summary": "Given the right setup, you can turn an incapacitated humanoid into a long-term pawn of alien influence.",
        "description": "Create Thrall is a campaign-shaping control feature rather than a round-by-round combat button. It matters in espionage, interrogation, and longer schemes where one compromised person is enough to crack a problem open.",
        "tags": ["subclass", "social", "control", "mind"],
    },
}

_FEATURE_OVERRIDES.update(_STAGE5B_FEATURE_OVERRIDES)


_STAGE5C_FEATURE_OVERRIDES: dict[str, dict[str, Any]] = {
    "frenzy": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Your rage can convert spare momentum into an extra burst of close-range violence.",
        "description": "Frenzy turns an already-aggressive barbarian turn into even more pressure by chaining additional offense into your rage state. The important in-app job is making it clear that this is a real turn-shaping button, not just a subclass label.",
        "tags": ["combat", "subclass", "rage"],
    },
    "mindless rage": {
        "summary": "While raging, mental interference is far less likely to take you out of the fight.",
        "description": "Mindless Rage protects the berserker from fear, charm, and similar control at the exact moment front-line commitment matters most.",
        "tags": ["defense", "mind", "subclass"],
    },
    "intimidating presence": {
        "section": "Actions",
        "type": "action",
        "save": "Wisdom",
        "summary": "Project primal menace so hard that enemies can buckle under a fear effect.",
        "description": "Intimidating Presence is a control action, not flavor text. Use it when shutting down a key enemy is worth more than one more normal attack.",
        "tags": ["control", "subclass", "fear"],
    },
    "retaliation": {
        "section": "Reactions",
        "type": "reaction",
        "trigger": "A creature within reach damages you.",
        "summary": "When foes hurt you in melee, you can answer with immediate violence instead of waiting for your next turn.",
        "description": "Retaliation makes the berserker punishing to engage and rewards enemies for choosing the wrong target. The sheet should surface this as a real reaction option during combat.",
        "tags": ["reaction", "combat", "subclass"],
    },
    "animal speaker": {
        "summary": "Your spiritual path gives you a calmer line of communication with beasts and the natural world.",
        "description": "Animal Speaker pushes the totem barbarian toward exploration and wilderness utility so the subclass contributes more than raw damage outside combat.",
        "tags": ["utility", "subclass", "exploration"],
    },
    "spirit seeker": {
        "summary": "Your totem path keeps opening new spirit-guided choices as you level.",
        "description": "Spirit Seeker is the branching identity engine for the subclass. The player should be able to tell that later subclass levels are not just number bumps but meaningful animal-themed choices.",
        "tags": ["subclass", "customization", "exploration"],
    },
    "totem spirit": {
        "summary": "Your chosen totem grants a defining passive combat identity right from the subclass entry point.",
        "description": "Totem Spirit is the moment the barbarian starts specializing. It should read like a meaningful branch that changes how you tank, move, or pressure a target.",
        "tags": ["subclass", "combat", "customization"],
    },
    "aspect of the beast": {
        "summary": "Your totem path deepens with utility and movement power tied to your chosen spirit.",
        "description": "Aspect of the Beast matters because it broadens the subclass beyond rage math. It should help the player understand how their totem choice pays off in travel, scouting, or physical problem-solving scenes.",
        "tags": ["subclass", "utility", "mobility"],
    },
    "totemic attunement": {
        "summary": "Your spiritual bond peaks in a major late-game payoff unique to your chosen totem.",
        "description": "Totemic Attunement is the subclass capstone lane. It should feel like a real reason to care which animal path you committed to earlier in the build.",
        "tags": ["subclass", "capstone", "combat"],
    },
    "vitality of the tree": {
        "summary": "The World Tree path makes your barbarian feel rooted, sustaining, and difficult to wear down.",
        "description": "Vitality of the Tree is the opening expression of the subclass: durable presence, team-oriented support, and a sturdier front line than the base class alone suggests.",
        "tags": ["subclass", "defense", "support"],
    },
    "branches of the tree": {
        "section": "Actions",
        "type": "action",
        "summary": "You project World Tree influence outward to reposition, support, or control the shape of the fight.",
        "description": "Branches of the Tree should read like a real battlefield tool, not a vague lore line. Use it when controlling space or helping allies matters more than a plain weapon swing.",
        "tags": ["subclass", "support", "control"],
    },
    "battering roots": {
        "summary": "Your World Tree power turns movement and impact into a heavier form of battlefield disruption.",
        "description": "Battering Roots makes the subclass better at shoving the fight where it wants it. This should feel like map-control power layered onto barbarian aggression.",
        "tags": ["subclass", "control", "combat"],
    },
    "travel along the tree": {
        "section": "Actions",
        "type": "action",
        "summary": "You gain a high-tier movement trick that makes the World Tree path feel mythic instead of merely tough.",
        "description": "Travel Along the Tree is a dramatic mobility payoff. The sheet should make it clear this is a premium repositioning or traversal feature, not a passive note hidden in the subclass list.",
        "tags": ["subclass", "mobility", "capstone"],
    },
    "mantle of inspiration": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "resourceName": "Bardic Inspiration",
        "trackUses": True,
        "summary": "Spend inspiration to reposition and protect allies in one flashy support move.",
        "description": "Mantle of Inspiration turns Bardic Inspiration into a tempo tool. It matters because it can rescue positioning, create aggression windows, and make the Glamour bard feel like a battle conductor.",
        "tags": ["subclass", "support", "mobility", "resource"],
    },
    "enthralling performance": {
        "summary": "A strong performance can leave onlookers charmed, captivated, or socially exposed.",
        "description": "Enthralling Performance is a scene-control feature for social and downtime play. The important thing is helping the player see when performance can be the opener to a negotiation, infiltration, or manipulation plan.",
        "tags": ["subclass", "social", "control"],
    },
    "mantle of majesty": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "You project overwhelming courtly command, turning your presence into direct pressure on the field.",
        "description": "Mantle of Majesty is one of the Glamour bard’s signature swing turns. It should feel like a premium control state, not just another passive line in the feature list.",
        "tags": ["subclass", "control", "social"],
    },
    "unbreakable majesty": {
        "summary": "Enemies find it genuinely harder to commit violence against you once your glamour peaks.",
        "description": "Unbreakable Majesty is both defense and presence. It should read like a high-level answer to focused fire, hostile attention, and social intimidation all at once.",
        "tags": ["subclass", "defense", "social"],
    },
    "bonus proficiencies": {
        "summary": "This subclass grants extra training so your sheet reflects a broader skill, tool, or weapon identity than the base class alone.",
        "description": "Bonus Proficiencies is not glamorous on its own, but it changes what the character can reliably contribute. The important thing is surfacing the added proficiencies clearly so they affect real rolls.",
        "tags": ["subclass", "skills", "passive"],
    },
    "cutting words": {
        "section": "Reactions",
        "type": "reaction",
        "resourceName": "Bardic Inspiration",
        "trackUses": True,
        "summary": "Spend inspiration as a reaction to spoil an enemy’s key roll at exactly the right time.",
        "description": "Cutting Words is one of the strongest support reactions a bard gets. The sheet should make it obvious that this can swing attacks, checks, and other contested moments before it is too late.",
        "tags": ["subclass", "reaction", "support", "resource"],
    },
    "magical discoveries": {
        "summary": "Your college widens the bard spell list with carefully stolen or studied off-list magic.",
        "description": "Magical Discoveries should point the player toward real spell selection impact, because it changes the kinds of problems your bard can solve for the whole party.",
        "tags": ["subclass", "spellcasting", "customization"],
    },
    "peerless skill": {
        "resourceName": "Bardic Inspiration",
        "trackUses": True,
        "summary": "You can spend inspiration on yourself when a crucial skill check absolutely must land.",
        "description": "Peerless Skill is the Lore bard’s statement that expertise scenes belong to them. It should feel visible any time the table reaches for a decisive social, knowledge, or infiltration roll.",
        "tags": ["subclass", "skills", "resource"],
    },
    "combat inspiration": {
        "summary": "Your inspiration now helps allies fight, not just pass checks and saves.",
        "description": "Combat Inspiration makes Valor bard support more martial. It matters because the bard can turn inspiration into direct attack or defense swing value instead of purely out-of-combat utility.",
        "tags": ["subclass", "support", "combat"],
    },
    "battle magic": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Casting and striking start linking together so your turn can mix spell pressure with weapon follow-through.",
        "description": "Battle Magic should feel like a genuine action-economy payoff. It matters most when the bard wants to keep spell presence without giving up on weapon tempo entirely.",
        "tags": ["subclass", "combat", "spellcasting"],
    },
    "disciple of life": {
        "summary": "Your healing spells and effects get better baseline value than other clerics can produce.",
        "description": "Disciple of Life is why the Life domain feels like a true healing specialist. The sheet should communicate that your restorative magic punches above normal expectations.",
        "tags": ["subclass", "healing", "support"],
    },
    "preserve life": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Channel Divinity",
        "trackUses": True,
        "summary": "Channel divine energy into broad emergency healing across wounded allies.",
        "description": "Preserve Life is not just flavor; it is the cleric’s panic button for stabilizing a collapsing fight. The player should be able to find and trust it quickly.",
        "tags": ["subclass", "healing", "support", "resource"],
    },
    "blessed healer": {
        "summary": "When you heal others, some of that restorative momentum comes back to you as well.",
        "description": "Blessed Healer supports the Life cleric’s sustain loop so helping the team does not leave the caster as the easy cleanup target afterward.",
        "tags": ["subclass", "healing", "support"],
    },
    "supreme healing": {
        "summary": "Your healing spikes become much more reliable, making big recovery turns less swingy.",
        "description": "Supreme Healing is a high-level consistency reward. The class fantasy here is that when the Life cleric commits to fixing a problem, the numbers show up.",
        "tags": ["subclass", "healing", "capstone"],
    },
    "warding flare": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "Flash radiant interference into an incoming attack to make the hit less likely to land cleanly.",
        "description": "Warding Flare is a defensive reaction that should feel immediately usable. It exists to let the Light cleric answer pressure before damage is already done.",
        "tags": ["subclass", "reaction", "defense", "radiant"],
    },
    "radiance of the dawn": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Channel Divinity",
        "trackUses": True,
        "summary": "Burst out hostile darkness and scorch nearby foes with a bright divine wave.",
        "description": "Radiance of the Dawn is a signature Light domain answer to swarms, darkness, and bad positioning. It should read like a real battlefield clear tool.",
        "tags": ["subclass", "radiant", "control", "resource"],
    },
    "improved flare": {
        "summary": "Your protective glare becomes easier to spread or apply in bigger moments.",
        "description": "Improved Flare keeps the Light cleric relevant in defensive timing windows even as encounter damage scales up.",
        "tags": ["subclass", "defense", "support"],
    },
    "corona of light": {
        "section": "Actions",
        "type": "action",
        "summary": "You erupt into a high-tier radiant state that makes your offensive light magic dramatically more threatening.",
        "description": "Corona of Light should feel like a boss-fight mode. It is the payoff for leaning hard into the domain’s radiant pressure identity.",
        "tags": ["subclass", "radiant", "capstone"],
    },
    "blessing of the trickster": {
        "section": "Actions",
        "type": "action",
        "summary": "Grant stealth support to an ally so the party can set up infiltration or ambush lines more cleanly.",
        "description": "Blessing of the Trickster is simple but important. It signals that this cleric is a stealth enabler and indirect problem-solver, not only a front-and-center holy caster.",
        "tags": ["subclass", "stealth", "support"],
    },
    "invoke duplicity": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Channel Divinity",
        "trackUses": True,
        "summary": "Create an illusion double that bends positioning, sight lines, and delivery angles in your favor.",
        "description": "Invoke Duplicity is the Trickery domain’s signature battlefield toy. It should read like an actual control engine, not a vague illusion paragraph.",
        "tags": ["subclass", "illusion", "control", "resource"],
    },
    "cloak of shadows": {
        "section": "Actions",
        "type": "action",
        "summary": "Slip out of sight through shadow, trickery, or disciplined stillness when visibility itself is the problem.",
        "description": "Cloak of Shadows is about vanishing at the right moment to break targeting, reposition, or set up a better next turn. The exact expression depends on the subclass, but it should always feel like a real stealth-state button.",
        "tags": ["subclass", "stealth", "defense"],
    },
    "improved duplicity": {
        "summary": "Your illusion double becomes harder to ignore and easier to leverage in a real fight.",
        "description": "Improved Duplicity matters because the subclass fantasy is not merely having a copy, but turning that copy into meaningful map pressure and confusion.",
        "tags": ["subclass", "illusion", "control"],
    },
    "war priest": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Your domain lets you convert divine aggression into extra weapon tempo.",
        "description": "War Priest makes the cleric feel martial in a way the base chassis does not. It should be visible whenever the player is trying to blend spellcasting with sustained front-line offense.",
        "tags": ["subclass", "combat", "support"],
    },
    "guided strike": {
        "summary": "Spend divine favor to push a crucial attack from 'maybe' into 'likely'.",
        "description": "Guided Strike is the War domain’s answer to high-value miss risk. It should feel like a premium accuracy spike for turns that really matter.",
        "tags": ["subclass", "combat", "divine"],
    },
    "war god's blessing": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "Use divine intervention to help an ally land the hit that decides the exchange.",
        "description": "War God's Blessing turns the cleric into a combat enabler, not just a solo attacker. The reaction timing is the important part: it should show up clearly in the UI.",
        "tags": ["subclass", "reaction", "support", "combat"],
    },
    "avatar of battle": {
        "summary": "You become dramatically harder to bully in heavy combat, especially when steel and battlefield attrition take over.",
        "description": "Avatar of Battle is a late-game survivability stamp for the War cleric. It should read like real front-line credibility, not decorative text.",
        "tags": ["subclass", "defense", "capstone"],
    },
    "combat wild shape": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "resourceName": "Wild Shape",
        "trackUses": True,
        "summary": "Transform fast enough that shapeshifting becomes a practical combat rhythm tool instead of a prep-only option.",
        "description": "Combat Wild Shape is the Moon druid identity switch. It matters because it determines whether your beast form is actually battle-ready under pressure.",
        "tags": ["subclass", "shapechange", "combat", "resource"],
    },
    "circle forms": {
        "summary": "Your beast-form ceiling rises, turning Wild Shape into a much more threatening core plan.",
        "description": "Circle Forms tells the player that the Moon druid is expected to care deeply about available forms, not treat Wild Shape as a side gimmick.",
        "tags": ["subclass", "shapechange", "combat"],
    },
    "elemental wild shape": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Wild Shape",
        "trackUses": True,
        "summary": "Your transformation path escalates beyond beasts into major elemental forms.",
        "description": "Elemental Wild Shape is a huge subclass payoff. It should feel like the druid graduating from tough animal forms into truly encounter-defining transformation choices.",
        "tags": ["subclass", "shapechange", "elemental", "capstone"],
    },
    "thousand forms": {
        "summary": "Your body-shaping magic gains flexible disguise and identity control value outside pure combat scenes.",
        "description": "Thousand Forms is part infiltration, part roleplay utility, and part magical identity flourish. The important thing is helping the player notice it in non-combat play.",
        "tags": ["subclass", "utility", "social"],
    },
    "circle spells": {
        "summary": "Your chosen land path extends the druid’s prepared toolkit with terrain-themed magic.",
        "description": "Circle Spells matter because they widen your day-to-day spell list without costing the same preparation pressure as the core druid chassis.",
        "tags": ["subclass", "spellcasting", "terrain"],
    },
    "natural recovery": {
        "resourceName": "Natural Recovery",
        "trackUses": True,
        "summary": "You recover some spell power during a short rest, making long adventuring days much kinder to your slot economy.",
        "description": "Natural Recovery is about pace and slot economy. The Circle of the Land druid should feel noticeably better at staying magical across multiple scenes before a long rest.",
        "tags": ["subclass", "spellcasting", "resource"],
    },
    "land's aid": {
        "summary": "The land itself starts helping your magic feel more restorative, stable, or tactically kind to allies.",
        "description": "Land's Aid reinforces that this subclass is not only about broader spells but also about nature-backed support and tactical resilience.",
        "tags": ["subclass", "support", "nature"],
    },
    "nature's ward": {
        "summary": "You become more difficult for hostile nature, terrain, and certain creatures to shut down or exploit.",
        "description": "Nature's Ward is a broad defensive quality upgrade. The important thing is that the druid feels more at home and more protected in environments that would pressure other casters.",
        "tags": ["subclass", "defense", "nature"],
    },
    "nature's sanctuary": {
        "summary": "At high tier, your bond with nature makes many creatures think twice before harming you at all.",
        "description": "Nature's Sanctuary should read like a meaningful capstone defense aura, not a minor rider hidden in the subclass list.",
        "tags": ["subclass", "defense", "capstone"],
    },
    "ranger's companion": {
        "summary": "Your subclass centers on a bonded beast whose presence changes both your tactics and action economy.",
        "description": "Ranger's Companion is the structural heart of Beast Master. The sheet should make it obvious that your companion is part of your build, not decorative flavor living off to the side.",
        "tags": ["subclass", "pet", "combat"],
    },
    "exceptional training": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Your beast can follow more demanding commands, turning the companion into a cleaner tactical partner.",
        "description": "Exceptional Training matters because pet subclasses live or die on usability. The player should feel the companion becoming easier to direct and more rewarding to keep involved.",
        "tags": ["subclass", "pet", "support"],
    },
    "bestial fury": {
        "summary": "Your companion’s offensive presence rises enough that it can no longer be treated as an afterthought.",
        "description": "Bestial Fury is a damage-and-pressure milestone for the Beast Master. It should communicate that the beast now matters in the fight every round, not occasionally.",
        "tags": ["subclass", "pet", "combat"],
    },
    "share spells": {
        "summary": "Your bond with your companion becomes magical enough that beneficial spell support can extend through both of you.",
        "description": "Share Spells is the late-game payoff that finally makes the Beast Master feel like a real duo instead of a ranger with an extra token.",
        "tags": ["subclass", "pet", "spellcasting"],
    },
    "hunter's prey": {
        "summary": "Choose the offensive hunting style that best matches how you like to pick apart targets.",
        "description": "Hunter's Prey is the subclass branch point that defines whether your ranger pressures single targets, clusters, or specific tactical openings.",
        "tags": ["subclass", "combat", "customization"],
    },
    "defensive tactics": {
        "summary": "Your experience hunting dangerous creatures starts translating into smarter, sturdier survival tools.",
        "description": "Defensive Tactics matters because it broadens the Hunter from 'deal damage' into 'stay alive while pressuring the right prey.'",
        "tags": ["subclass", "defense", "combat"],
    },
    "multiattack": {
        "section": "Actions",
        "type": "action",
        "summary": "Gain a specialized attack pattern for controlling groups or pressuring multiple enemies at once.",
        "description": "Hunter Multiattack is a genuine action-choice feature. The UI should make it obvious when this is a better turn than your ordinary Attack action.",
        "tags": ["subclass", "combat", "action"],
    },
    "stand against the tide": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "When enemies overcommit, you can turn that aggression back on them through precise battlefield timing.",
        "description": "Stand Against the Tide is a reaction identity feature. It rewards positioning and patience, not just damage racing.",
        "tags": ["subclass", "reaction", "control"],
    },
    "dread ambusher": {
        "summary": "You are at your most dangerous in the opening heartbeat of a fight, before enemies fully react.",
        "description": "Dread Ambusher is a first-round tempo spike. The important thing is helping the player understand that initiative and opener positioning matter more for this subclass than for most rangers.",
        "tags": ["subclass", "combat", "initiative"],
    },
    "umbral sight": {
        "summary": "Darkness becomes a home field advantage instead of merely a risk factor.",
        "description": "Umbral Sight is a stealth and ambush feature that changes how the Gloom Stalker wants to fight on dark maps, in caves, or in night scenes.",
        "tags": ["subclass", "stealth", "vision"],
    },
    "iron mind": {
        "summary": "Your will hardens against mental collapse, making it harder to take you out with fear or enchantment.",
        "description": "Iron Mind is a reliability feature. It exists so the ranger’s stealth-and-hunter plan is less likely to disappear to one bad save.",
        "tags": ["subclass", "defense", "mind"],
    },
    "stalker's flurry": {
        "summary": "When your attack plan almost lands, you get a cleaner chance to keep the pressure on.",
        "description": "Stalker's Flurry improves the subclass’s offensive consistency. It should feel like the hunter refusing to waste a good opening.",
        "tags": ["subclass", "combat", "tempo"],
    },
    "shadowy dodge": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "When seen and targeted, you can still twist out of the line enough to reduce the enemy’s confidence.",
        "description": "Shadowy Dodge is a stealth-flavored survival tool. The important thing is surfacing it as a reactive defensive choice during live combat.",
        "tags": ["subclass", "reaction", "defense", "stealth"],
    },
    "dragon ancestor": {
        "summary": "Your draconic line defines your elemental identity, roleplay flavor, and later power payoffs.",
        "description": "Dragon Ancestor is the subclass fork that everything else builds from. The chosen lineage should feel mechanically relevant, not like pure lore dressing.",
        "tags": ["subclass", "spellcasting", "elemental"],
    },
    "draconic resilience": {
        "summary": "Your bloodline hardens your body, giving the sorcerer a sturdier baseline than most arcane casters enjoy.",
        "description": "Draconic Resilience is a survivability identity feature. It matters because the subclass can stand in riskier positions than a frailer caster would usually tolerate.",
        "tags": ["subclass", "defense", "passive"],
    },
    "wild magic surge": {
        "summary": "Your spellcasting carries instability that can explode into unexpected upside, danger, or chaos.",
        "description": "Wild Magic Surge is the subclass promise. The UI should make the player feel the subclass is alive with risk and weirdness, not just a normal sorcerer with one funny note.",
        "tags": ["subclass", "spellcasting", "chaos"],
    },
    "tides of chaos": {
        "resourceName": "Tides of Chaos",
        "trackUses": True,
        "summary": "Lean into instability to improve a key roll and invite the subclass’s chaos engine to answer later.",
        "description": "Tides of Chaos is the signature 'push your luck' button. It should be easy to see, easy to spend, and clearly connected to the possibility of future surges.",
        "tags": ["subclass", "resource", "chaos"],
    },
    "bend luck": {
        "section": "Reactions",
        "type": "reaction",
        "resourceName": "Sorcery Points",
        "trackUses": True,
        "summary": "Spend sorcery to tilt another creature’s roll at the last moment.",
        "description": "Bend Luck is one of the Wild Magic sorcerer’s best expression points: targeted roll manipulation in the exact moment a scene turns.",
        "tags": ["subclass", "reaction", "resource", "control"],
    },
    "controlled chaos": {
        "summary": "Your surge table starts feeling less like pure punishment and more like guided instability.",
        "description": "Controlled Chaos is a quality-of-life payoff. It matters because it changes how willingly the player leans into the subclass’s core risk engine.",
        "tags": ["subclass", "chaos", "spellcasting"],
    },
    "spell bombardment": {
        "summary": "When your magic spikes high, it can spike higher still and produce dramatic burst turns.",
        "description": "Spell Bombardment is a late-game damage thrill feature. It should read like the Wild Magic sorcerer occasionally punching above expected numbers in spectacular ways.",
        "tags": ["subclass", "spellcasting", "capstone"],
    },
    "abjuration savant": {
        "summary": "Your school specialization makes protective abjuration magic easier to fold into the wizard’s broader toolkit.",
        "description": "Abjuration Savant is not flashy, but it is part of making the subclass feel like a committed school specialist rather than a generic wizard with one shield trick.",
        "tags": ["subclass", "spellcasting", "specialist"],
    },
    "arcane ward": {
        "resourceName": "Arcane Ward",
        "trackUses": True,
        "summary": "Protective magic leaves behind a rechargeable buffer that can absorb punishment before your real hit points do.",
        "description": "Arcane Ward is the core abjurer identity engine. The sheet should make its current value and refresh cadence obvious so the wizard actually plays around it.",
        "tags": ["subclass", "defense", "resource", "spellcasting"],
    },
    "projected ward": {
        "section": "Reactions",
        "type": "reaction",
        "resourceName": "Arcane Ward",
        "trackUses": True,
        "summary": "You can throw your protective buffer onto an ally instead of hoarding it for yourself.",
        "description": "Projected Ward turns the abjurer into a support caster in a very visible way. It should appear as a real reaction choice when allies are under pressure.",
        "tags": ["subclass", "reaction", "support", "defense"],
    },
    "improved abjuration": {
        "summary": "Your warding and counter-magic package becomes more consistent against hostile spell pressure.",
        "description": "Improved Abjuration is about reliability in caster duels and magical defense scenes, not just raw numbers on the page.",
        "tags": ["subclass", "spellcasting", "defense"],
    },
    "spell resistance": {
        "summary": "Enemy magic struggles to stick cleanly once your school mastery is fully online.",
        "description": "Spell Resistance is the abjurer’s late-game promise: surviving magical pressure that would flatten a less specialized wizard.",
        "tags": ["subclass", "defense", "capstone"],
    },
    "divination savant": {
        "summary": "Your school focus sharpens the wizard’s relationship with foresight, information, and prediction magic.",
        "description": "Divination Savant reinforces that the subclass is about answers, planning, and seeing the important thing early, not only about raw damage or defense.",
        "tags": ["subclass", "spellcasting", "specialist"],
    },
    "portent": {
        "resourceName": "Portent",
        "trackUses": True,
        "summary": "You bank future d20 results and spend them to rewrite critical moments before they happen naturally.",
        "description": "Portent is one of the strongest information-control tools in the game. The sheet should make the stored rolls unmistakable because forgetting them is the real failure state.",
        "tags": ["subclass", "resource", "control", "prediction"],
    },
    "expert divination": {
        "summary": "Your divination engine starts refunding or sustaining itself more efficiently than ordinary wizard pacing allows.",
        "description": "Expert Divination matters because it rewards leaning into the school identity instead of treating divination as a side dish.",
        "tags": ["subclass", "spellcasting", "resource"],
    },
    "the third eye": {
        "section": "Actions",
        "type": "action",
        "summary": "Open a specialized sense mode to answer the exact perception problem the scene is presenting.",
        "description": "The Third Eye is utility-forward wizarding at its best: you prepare the right sense, then solve the obstacle that was previously hidden or unreadable.",
        "tags": ["subclass", "utility", "vision"],
    },
    "greater portent": {
        "summary": "Your prediction package grows stronger, making fate control feel even more central to the subclass identity.",
        "description": "Greater Portent is the late-game confirmation that the diviner wins by shaping pivotal rolls before they land.",
        "tags": ["subclass", "prediction", "capstone"],
    },
    "evocation savant": {
        "summary": "Your school mastery supports a wizard identity built around efficient, reliable direct magical force.",
        "description": "Evocation Savant exists so the subclass feels meaningfully committed to destructive spellcraft instead of incidentally carrying a few blasts.",
        "tags": ["subclass", "spellcasting", "specialist"],
    },
    "sculpt spells": {
        "summary": "You can blast aggressively without frying the allies who are standing in the wrong place.",
        "description": "Sculpt Spells is one of the main reasons to trust an evoker in a crowded fight. It changes how boldly the player can place large area effects.",
        "tags": ["subclass", "spellcasting", "control"],
    },
    "potent cantrip": {
        "summary": "Even your fallback magic starts punching above baseline expectations for at-will pressure.",
        "description": "Potent Cantrip exists so the wizard still feels like an evoker on lower-resource turns. It keeps the school identity visible even when premium slots stay unspent.",
        "tags": ["subclass", "spellcasting", "cantrip"],
    },
    "empowered evocation": {
        "summary": "Your intelligence and school mastery start pushing destructive spells into a higher damage bracket.",
        "description": "Empowered Evocation is a straightforward but important damage identity feature. It should make the player feel rewarded for being the dedicated blaster.",
        "tags": ["subclass", "spellcasting", "damage"],
    },
    "overchannel": {
        "summary": "You can force an evocation spell to hit like a perfect spike, even if the cost or risk rises with repeated use.",
        "description": "Overchannel is the boss-fight burst button for the evoker. It should read like controlled magical overclocking, not a vague capstone flourish.",
        "tags": ["subclass", "spellcasting", "capstone"],
    },
    "illusion savant": {
        "summary": "Your specialization makes deceptive magic easier to support as a primary wizard identity.",
        "description": "Illusion Savant is part of the subclass promise that trickery, misdirection, and false reality are not side tricks here—they are the main plan.",
        "tags": ["subclass", "spellcasting", "specialist"],
    },
    "improved minor illusion": {
        "summary": "Even your smallest illusion tools get more flexible, making creative play come online earlier and more reliably.",
        "description": "Improved Minor Illusion matters because illusion subclasses live or die on whether their low-cost tricks actually feel rewarding to use.",
        "tags": ["subclass", "illusion", "utility"],
    },
    "malleable illusions": {
        "summary": "You can reshape existing illusion work instead of having to throw it away and start over.",
        "description": "Malleable Illusions is quality-of-life with real tactical bite. It rewards creative setup and lets the illusionist keep adapting as the scene changes.",
        "tags": ["subclass", "illusion", "control"],
    },
    "illusory self": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "When danger finally reaches you, the target can hit a false version of you instead of the real thing.",
        "description": "Illusory Self is a dramatic defensive reaction. It should feel like a clean answer to the one hit the wizard really could not afford to take.",
        "tags": ["subclass", "reaction", "illusion", "defense"],
    },
    "illusory reality": {
        "section": "Actions",
        "type": "action",
        "summary": "Your illusions can harden into temporary reality, turning deception into direct problem-solving power.",
        "description": "Illusory Reality is the big illusionist payoff. It should inspire players to think about creative object play, terrain solutions, and tactical inventions rather than only fake visuals.",
        "tags": ["subclass", "illusion", "capstone", "utility"],
    },
    "necromancy savant": {
        "summary": "Your school mastery reinforces a wizard identity built around life-force manipulation and undead command.",
        "description": "Necromancy Savant exists to make the subclass feel intentionally committed to dark utility and corpse-driven magic, not just incidentally spooky.",
        "tags": ["subclass", "spellcasting", "specialist"],
    },
    "grim harvest": {
        "summary": "When your magic finishes enemies, you can harvest some of that deathward momentum back into yourself.",
        "description": "Grim Harvest helps the necromancer sustain itself through offensive spell play. It should feel visible during attrition-heavy fights.",
        "tags": ["subclass", "healing", "spellcasting"],
    },
    "undead thralls": {
        "summary": "Your undead become more worthwhile to command instead of feeling like fragile side clutter.",
        "description": "Undead Thralls is the subclass payoff that says 'yes, your minions matter.' The sheet should treat them like a real strategy layer, not trivia.",
        "tags": ["subclass", "undead", "summon"],
    },
    "inured to undead": {
        "summary": "You become harder for necrotic pressure and undead influence to meaningfully wear down.",
        "description": "Inured to Undead is a defensive identity piece that helps the necromancer survive the same kinds of dark magic it studies and commands.",
        "tags": ["subclass", "defense", "undead"],
    },
    "command undead": {
        "section": "Actions",
        "type": "action",
        "summary": "Seize control of undead forces instead of merely surviving them.",
        "description": "Command Undead is one of the most flavorful late-game necromancer buttons. It should read like a serious control power, not a ribbon feature.",
        "tags": ["subclass", "undead", "control", "capstone"],
    },
    "fey presence": {
        "section": "Actions",
        "type": "action",
        "summary": "Project a burst of fey glamour that can charm or frighten creatures around you.",
        "description": "Fey Presence is the Archfey patron’s opening pressure tool. It should feel like a real crowd-control button, especially in tight spaces and socially volatile encounters.",
        "tags": ["subclass", "fey", "control"],
    },
    "misty escape": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "When you are hit, you can vanish and reposition instead of simply eating the punishment.",
        "description": "Misty Escape turns the Archfey warlock into a slippery target. The reaction timing matters more than the flavor, so the UI should make this impossible to miss.",
        "tags": ["subclass", "reaction", "mobility", "defense"],
    },
    "beguiling defenses": {
        "summary": "Your mind becomes a much less welcoming target for hostile enchantment and social control.",
        "description": "Beguiling Defenses is a late-game survivability and identity feature. It tells the player that the manipulator is also much harder to manipulate in return.",
        "tags": ["subclass", "defense", "mind"],
    },
    "dark delirium": {
        "section": "Actions",
        "type": "action",
        "save": "Wisdom",
        "summary": "Trap a creature in a custom fey nightmare where charm, fear, and isolation do the heavy lifting.",
        "description": "Dark Delirium is the Archfey’s premium control scene. It should read like a major single-target disruption tool with strong story flavor and real tactical weight.",
        "tags": ["subclass", "control", "fey", "capstone"],
    },
    "shadow arts": {
        "summary": "Spend focus on stealth, darkness, and infiltration tricks that make the monk feel like a true shadow operative.",
        "description": "Shadow Arts is the opening identity statement for the Way of Shadow. It matters because it gives the monk non-standard tools for map access, stealth setups, and disappearing from obvious lines.",
        "tags": ["subclass", "stealth", "magic"],
    },
    "shadow step": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Teleport through dim light or darkness so your positioning becomes a weapon in its own right.",
        "description": "Shadow Step is one of the subclass’s biggest tactical spikes. It should feel like a premium ambush and escape button rather than a tiny mobility note.",
        "tags": ["subclass", "mobility", "stealth"],
    },
    "opportunist": {
        "section": "Reactions",
        "type": "reaction",
        "summary": "When another creature creates an opening, you strike immediately and punish the lapse.",
        "description": "Opportunist rewards attention and team sequencing. It should appear as a real reaction option so the player can capitalize on ally-created openings.",
        "tags": ["subclass", "reaction", "combat"],
    },
    "open hand technique": {
        "summary": "Your flurry pressure carries control riders that push, drop, or disrupt foes instead of only adding damage.",
        "description": "Open Hand Technique is why the subclass feels like a battlefield controller. The sheet should tell the player these are real rider choices, not flavor attached to Flurry of Blows.",
        "tags": ["subclass", "combat", "control"],
    },
    "wholeness of body": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Wholeness of Body",
        "trackUses": True,
        "summary": "Use disciplined breathing and inner focus to restore your own vitality mid-adventure or mid-fight.",
        "description": "Wholeness of Body is a real sustain tool for the Open Hand monk. It matters because self-healing changes whether you can stay aggressive without immediate support.",
        "tags": ["subclass", "healing", "focus"],
    },
    "tranquility": {
        "summary": "Your centered presence discourages violence until enemies deliberately break the peace around you.",
        "description": "Tranquility is about control before the first punch lands. It should stand out in scouting, negotiation, and tense pre-combat scenes where initiative has not yet exploded.",
        "tags": ["subclass", "defense", "social"],
    },
    "quivering palm": {
        "section": "Actions",
        "type": "action",
        "save": "Constitution",
        "summary": "Plant a hidden lethal vibration in a target and trigger it later for a terrifying finishing burst.",
        "description": "Quivering Palm is the Open Hand monk’s signature endgame finisher. It should feel like a major setup-and-payoff mechanic, not a one-line damage rider.",
        "tags": ["subclass", "capstone", "combat", "focus"],
    },
    "disciple of the elements": {
        "summary": "Your focus training opens an elemental technique list so the monk can solve problems with air, fire, water, and stone as well as fists.",
        "description": "Disciple of the Elements is the subclass fork that turns the monk into a hybrid martial-caster style character. The player should see immediately that focus now fuels more than mobility and strikes.",
        "tags": ["subclass", "elemental", "focus"],
    },
    "elemental disciplines": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Focus Points",
        "trackUses": True,
        "summary": "Spend focus on elemental techniques that can blast, shape space, or solve traversal problems.",
        "description": "Elemental Disciplines are the functional heart of the subclass. They should feel like a menu of real tools rather than a vague promise of elemental flavor.",
        "tags": ["subclass", "elemental", "resource", "control"],
    },
    "elemental flow": {
        "summary": "Your mastery over the elements starts blending mobility, area control, and rhythm into a smoother combat pattern.",
        "description": "Elemental Flow is about the subclass becoming less clunky and more expressive. The monk should feel like a living conduit of the battlefield’s natural forces.",
        "tags": ["subclass", "elemental", "mobility"],
    },
    "avatar of the four winds": {
        "summary": "At the height of the path, you become a major elemental presence rather than a martial artist with a few themed tricks.",
        "description": "Avatar of the Four Winds is the capstone fantasy payoff for the subclass. It should read big, mobile, and scene-shaping.",
        "tags": ["subclass", "elemental", "capstone"],
    },
}



_FEATURE_OVERRIDES.update(_STAGE5C_FEATURE_OVERRIDES)


_STAGE5D_FEATURE_OVERRIDES: dict[str, dict[str, Any]] = {
    "innate sorcery": {
        "summary": "Shift into a heightened casting state so your sorcerer turns feel more dangerous and more obviously magical.",
        "description": "Innate Sorcery is the class fantasy switch that tells the player this is not just another prepared caster. When it is active, the sorcerer should feel more explosive, more accurate, or more capable of forcing magic through pressure depending on the exact sheet rules tied to it.",
        "tags": ["spellcasting", "resource", "burst"],
    },
    "flexible casting": {
        "summary": "Convert your spell resources in the direction the moment needs instead of being locked into one rigid budget.",
        "description": "Flexible Casting is the engine that makes sorcery points feel different from ordinary spell slots. It matters because the player can trade between staying power and burst depending on whether the scene demands more casts, more metamagic, or a better late-fight refill.",
        "resourceName": "Sorcery Points",
        "trackUses": True,
        "tags": ["spellcasting", "resource", "economy"],
    },
    "sorcerous vitality": {
        "summary": "Channel raw magical power into survival so you can stay upright when another caster would crumple.",
        "description": "Sorcerous Vitality is there to make the class feel less fragile once the magic starts running hot. It should read as a real survivability button or state, not a vague flavor line about magical endurance.",
        "tags": ["defense", "resource", "spellcasting"],
    },
    "arcane apotheosis": {
        "summary": "At high level your magic stops feeling merely learned and starts feeling mythic.",
        "description": "Arcane Apotheosis is the endgame payoff for a sorcerer: your signature casting identity becomes louder, cleaner, and more decisive. The sheet should make this feel like a top-end power spike rather than a generic capstone label.",
        "tags": ["capstone", "spellcasting", "burst"],
    },
    "sorcerous origin": {
        "summary": "Your bloodline or magical source is the fork that defines what kind of sorcerer you actually are.",
        "description": "Sorcerous Origin is the subclass gate for the class. It matters because the rest of the sorcerer experience should now start picking up subclass-flavored features, spell choices, and identity cues instead of feeling generic.",
        "tags": ["subclass", "build", "spellcasting"],
    },
    "scholar": {
        "summary": "Your wizard is not just powerful, but deeply trained in how magic and knowledge fit together.",
        "description": "Scholar is an identity feature that should help the player understand the wizard as a learned specialist rather than only a spell list. In play it matters most when knowledge, research, preparation, or lore-facing problem solving comes up.",
        "tags": ["utility", "knowledge", "wizard"],
    },
    "cantrip formulas": {
        "summary": "Swap or reshape simple magical routines more easily so your low-level utility stays relevant.",
        "description": "Cantrip Formulas is about flexibility at the bottom end of your spellbook. It matters because cantrips are used constantly, and this feature makes those ever-present choices feel less locked in over a long campaign.",
        "tags": ["spellcasting", "utility", "wizard"],
    },
    "arcane tradition": {
        "summary": "Choose the school or style of wizardry that will shape the rest of your spellcraft.",
        "description": "Arcane Tradition is the moment the wizard stops being only a generalist. From here on, your subclass should start feeding distinct tools, passive perks, and tactical reasons to care about your specialty.",
        "tags": ["subclass", "build", "spellcasting"],
    },
    "magical cunning": {
        "summary": "Recover a bit of magical momentum when the adventuring day would otherwise leave you dry.",
        "description": "Magical Cunning matters because warlocks live on a tight resource rhythm. This feature helps the class stay relevant between rests and makes the player less afraid that one bad encounter will drain the entire pact magic engine.",
        "tags": ["resource", "spellcasting", "warlock"],
    },
    "mystic arcanum improvement": {
        "summary": "Your once-per-day signature magic gets sharper, broader, or easier to rely on than before.",
        "description": "An arcanum improvement is not filler. It means one of the warlock’s most dramatic magical options has become better enough that the player should revisit how they plan major fights and high-stakes scenes around it.",
        "tags": ["spellcasting", "warlock", "upgrade"],
    },
    "deft explorer": {
        "summary": "You stop feeling like only a damage dealer and start feeling truly dependable in travel, scouting, and wilderness play.",
        "description": "Deft Explorer is the ranger’s broad competence package. It matters because the class should contribute outside initiative, not just mark a target and hope the fight solves everything.",
        "tags": ["exploration", "utility", "ranger"],
    },
    "conjure barrage": {
        "section": "Actions",
        "type": "action",
        "resourceName": "Conjure Barrage",
        "trackUses": True,
        "summary": "Loose a one-shot burst of weapon-fueled area pressure when a single target is not enough.",
        "description": "Conjure Barrage is the ranger answer to clustered enemies. It should read like a real crowd-hit button with limited uses, not a stray note hidden among passive features.",
        "tags": ["combat", "area", "ranger", "resource"],
    },
    "nature's veil": {
        "section": "Bonus Actions",
        "type": "bonus action",
        "summary": "Slip behind nature’s cover to vanish, reposition, or survive a dangerous exchange.",
        "description": "Nature's Veil is a strong tactical button because invisibility or concealment changes everything about approach, escape, and target priority. The player should see immediately that this is a live combat and scouting tool.",
        "tags": ["stealth", "mobility", "ranger"],
    },
    "feral senses": {
        "summary": "You become much harder to fool, hide from, or throw off once the hunt is live.",
        "description": "Feral Senses is the ranger’s late-game answer to slippery prey. It matters when enemies rely on concealment, darkness, or positioning tricks to avoid a clean hit.",
        "tags": ["awareness", "combat", "ranger"],
    },
    "timeless body": {
        "summary": "Age and ordinary wear stop pulling on you the way they do on other adventurers.",
        "description": "Timeless Body is mostly narrative and passive, but it is still an identity spike. It tells the player the druid has become something older, steadier, and more entwined with primal cycles than an ordinary mortal.",
        "tags": ["passive", "druid", "flavor"],
    },
}


_FEATURE_OVERRIDES.update(_STAGE5D_FEATURE_OVERRIDES)


_FIELD_PATTERNS = {
    "bonus action": re.compile(r"\bas a bonus action\b", re.I),
    "reaction": re.compile(r"\buse your reaction\b|\bas a reaction\b", re.I),
    "action": re.compile(r"\bas an action\b", re.I),
    "save": re.compile(r"\b([A-Za-z]+) (?:saving throw|save)\b", re.I),
    "range": re.compile(r"\bwithin (\d+) feet\b|\b(\d+)-foot (?:radius|cone|cube|line)\b", re.I),
    "duration": re.compile(r"\bfor (1 minute|10 minutes|1 hour|8 hours|24 hours)\b|\buntil the end of your next turn\b|\buntil your next turn\b", re.I),
    "uses": re.compile(r"\bonce per (short|long) rest\b|\ba number of times equal to your proficiency bonus\b", re.I),
    "dice": re.compile(r"\b\d+d\d+\b", re.I),
}


def _parsed_fields(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    raw = str(text or "")
    if not raw:
        return out
    for kind in ("bonus action", "reaction", "action"):
        if _FIELD_PATTERNS[kind].search(raw):
            out["type"] = kind
            break
    save_match = _FIELD_PATTERNS["save"].search(raw)
    if save_match:
        out["save"] = f"{save_match.group(1).title()} save"
    range_match = _FIELD_PATTERNS["range"].search(raw)
    if range_match:
        out["range"] = next((g for g in range_match.groups() if g), "") + " ft"
    duration_match = _FIELD_PATTERNS["duration"].search(raw)
    if duration_match:
        out["duration"] = next((g for g in duration_match.groups() if g), duration_match.group(0))
    uses_match = _FIELD_PATTERNS["uses"].search(raw)
    if uses_match:
        out["usage"] = uses_match.group(0)
    dice_match = _FIELD_PATTERNS["dice"].search(raw)
    if dice_match:
        out["dice"] = dice_match.group(0)
    if raw.lower().startswith(("when ", "whenever ", "if ", "while ")):
        first_clause = re.split(r"[,.]", raw, maxsplit=1)[0].strip()
        if first_clause:
            out["trigger"] = first_clause
    return out


_ORDINAL_RE = re.compile(r"(\d+)(?:st|nd|rd|th)", re.I)


def _progression_profile(name: str) -> dict[str, Any]:
    clean = str(name or "").strip()
    lower = normalized_feature_name(clean)
    out: dict[str, Any] = {}

    m = re.search(r"sneak attack \((\d+d\d+)\)", lower)
    if m:
        dice = m.group(1).upper()
        out.update(
            {
                "summary": f"Your Sneak Attack currently adds {dice} extra precision damage once per turn when the setup is right.",
                "description": (
                    f"This progression point updates the rogue’s Sneak Attack to {dice}. The key thing for the player is that the sheet should make the current "
                    "damage dice obvious and only promise the bonus when the trigger conditions are met."
                ),
                "tags": ["combat", "precision"],
            }
        )
        return out

    m = re.search(r"bardic inspiration \((d\d+)\)", lower)
    if m:
        die = m.group(1).upper()
        out.update(
            {
                "summary": f"Your Bardic Inspiration die is now {die}.",
                "description": (
                    f"This level upgrades the size of your Bardic Inspiration die to {die}, making every inspiration use more likely to swing an important roll."
                ),
                "tags": ["support", "resource"],
                "resourceName": "Bardic Inspiration",
                "trackUses": True,
                "type": "bonus action",
                "section": "Bonus Actions",
            }
        )
        return out

    m = re.search(r"song of rest \((d\d+)\)", lower)
    if m:
        die = m.group(1).upper()
        return {
            "summary": f"Your Song of Rest recovery die is now {die}.",
            "description": f"This level improves Song of Rest to {die}, raising the value the party gets from a successful short-rest recovery window.",
            "tags": ["rest", "healing"],
        }

    m = re.search(r"action surge \((\d+) use", lower)
    if m:
        uses = m.group(1)
        return {
            "summary": f"You currently have {uses} Action Surge use{'s' if uses != '1' else ''} available between recoveries.",
            "description": f"This progression point sets your Action Surge capacity at {uses}. The sheet should show the remaining uses clearly because this resource changes entire turns.",
            "resourceName": "Action Surge",
            "trackUses": True,
            "tags": ["combat", "resource", "burst"],
        }

    m = re.search(r"indomitable \((\d+) use", lower)
    if m:
        uses = m.group(1)
        return {
            "summary": f"You currently have {uses} Indomitable use{'s' if uses != '1' else ''} between recoveries.",
            "description": f"This level sets your Indomitable capacity at {uses}, giving you more room to resist encounter-defining failed saves.",
            "resourceName": "Indomitable",
            "trackUses": True,
            "tags": ["defense", "resource"],
        }

    m = re.search(r"channel divinity \((\d+) use", lower)
    if m:
        uses = m.group(1)
        return {
            "summary": f"You currently have {uses} Channel Divinity use{'s' if uses != '1' else ''} available before recovery.",
            "description": f"This progression point increases your Channel Divinity capacity to {uses}, letting you lean on your divine feature options more often.",
            "resourceName": "Channel Divinity",
            "trackUses": True,
            "type": "action",
            "section": "Actions",
            "tags": ["divine", "resource"],
        }

    m = re.search(r"weapon mastery \((\d+) weapon", lower)
    if m:
        count = m.group(1)
        return {
            "summary": f"You can currently maintain mastery access across {count} weapon{'s' if count != '1' else ''}.",
            "description": f"This progression point expands how many weapons you can fully support with Weapon Mastery, giving your loadout more tactical breadth.",
            "tags": ["combat", "weapons"],
        }

    m = re.search(r"cantrips known: (\d+)", lower)
    if m:
        count = m.group(1)
        return {
            "summary": f"Your known cantrip count is now {count}.",
            "description": f"This progression point raises your total known cantrips to {count}, giving you more at-will magical options in and out of combat.",
            "tags": ["spellcasting"],
        }

    m = re.search(r"(\d+)(?:st|nd|rd|th)-level spells", lower)
    if m:
        level = m.group(1)
        return {
            "summary": f"You unlock access to {level}{'st' if level=='1' else 'nd' if level=='2' else 'rd' if level=='3' else 'th'}-level spells.",
            "description": f"This level opens a new tier of spell power. The spell list, preparation rules, and slot surfaces should now all support {level}th-level magic where appropriate.",
            "tags": ["spellcasting", "progression"],
        }

    m = re.search(r"(\d+)(?:st|nd|rd|th)-level spell slots", lower)
    if m:
        level = m.group(1)
        return {
            "summary": f"You now have {level}{'st' if level=='1' else 'nd' if level=='2' else 'rd' if level=='3' else 'th'}-level spell slots in your slot economy.",
            "description": f"This progression point adds {level}th-level spell slots to your available casting resources. The slot tracker should surface them directly."
        }

    m = re.search(r"mystic arcanum \((\d+)(?:st|nd|rd|th)\)", lower)
    if m:
        level = m.group(1)
        return {
            "summary": f"You gain a {level}th-level Mystic Arcanum spell option.",
            "description": f"This unlock adds a high-tier once-per-use style magical option outside the ordinary pact-slot loop. It should be surfaced distinctly from normal warlock spell slots.",
            "tags": ["spellcasting", "endgame"],
        }

    m = re.search(r"metamagic \((\d+)(?:st|nd|rd|th)? option", lower)
    if m:
        count = m.group(1)
        return {
            "summary": f"You now know {count} Metamagic option{'s' if count != '1' else ''}.",
            "description": f"This level expands your Metamagic toolkit to {count} options, widening the kinds of spell turns you can customize.",
            "tags": ["spellcasting", "customization", "resource"],
        }

    m = re.search(r"pact slot level (\d+)", lower)
    if m:
        level = m.group(1)
        return {
            "summary": f"Your pact slots now cast at level {level}.",
            "description": f"This progression point upgrades the strength of every pact slot you spend, which is one of the biggest warlock scaling jumps."
        }

    m = re.search(r"pact slots: (\d+)", lower)
    if m:
        count = m.group(1)
        return {
            "summary": f"You currently have {count} pact slot{'s' if count != '1' else ''} available before recovery.",
            "description": f"This level sets your pact slot count at {count}. The sheet should make that limited high-impact casting economy obvious.",
            "tags": ["spellcasting", "resource"],
        }

    if lower == "ability score improvement":
        return {
            "summary": "Improve key ability scores or take a feat to reshape the build.",
            "description": (
                "Ability Score Improvement is one of the biggest character-shaping progression points. It can either raise the numbers your class depends on most or open a feat that changes what the character can do."
            ),
            "tags": ["build", "progression"],
        }

    if lower == "epic boon":
        return {
            "summary": "Gain an endgame reward that pushes the build into truly legendary territory.",
            "description": "Epic Boons are late-game progression spikes that add a high-power identity capstone beyond ordinary class scaling.",
            "tags": ["capstone", "progression"],
        }

    if "subclass" in lower or "subclass" in clean.lower():
        return {
            "summary": "This level opens or advances your subclass path, adding themed powers unique to your chosen specialization.",
            "description": "A subclass unlock means the base class starts branching into a more specific identity. The sheet should surface the actual subclass feature rows beside this progression point so the player can tell what changed.",
            "tags": ["subclass", "progression"],
        }

    if lower.startswith("extra attack"):
        attacks = re.search(r"extra attack \((\d+)\)", lower)
        count = attacks.group(1) if attacks else "2"
        return {
            "summary": f"When you take the Attack action, you can now make up to {count} attacks within that action.",
            "description": f"This progression point changes your basic turn structure by increasing how many attacks fit inside a normal Attack action. It should be reflected everywhere the sheet explains attack cadence.",
            "tags": ["combat", "progression"],
        }

    aura_match = re.search(r"aura of (protection|courage).*\((\d+) ft\)", lower)
    if aura_match:
        aura_kind = aura_match.group(1)
        rng = aura_match.group(2)
        return {
            "summary": f"Your Aura of {aura_kind.title()} currently reaches {rng}.",
            "description": f"This progression point expands the radius of your aura to {rng}, meaning your positioning can protect or support more allies at once.",
            "tags": ["aura", "support"],
        }

    if lower.endswith("improvement"):
        return {
            "summary": "This level improves an existing signature class tool rather than unlocking a brand-new one.",
            "description": "An improvement upgrade matters because the old feature should now have a stronger value, broader effect, or better reliability than it did before."
        }

    return out


_PLAYER_TIPS = {
    "combat": "Use this when the fight is live and a round-to-round choice matters.",
    "support": "This shines most when it helps the party pass an important check, save, or attack.",
    "mobility": "Think about map pressure, escape lanes, and which target you need to reach this turn.",
    "defense": "Pressure this in fights where surviving a key hit, effect, or save changes the encounter.",
    "spellcasting": "Check the spell panel, slot state, and save/attack math whenever this is involved.",
    "resource": "The resource count, spend timing, and recovery cadence should all be visible in the sheet.",
    "subclass": "The sheet should make the specialization identity obvious, not bury it as a hidden unlock.",
    "utility": "This matters most in exploration, travel, scouting, or social scenes rather than raw damage races.",
}


def _player_tip(tags: list[str]) -> str:
    for tag in tags:
        key = str(tag or "").strip().lower()
        if key in _PLAYER_TIPS:
            return _PLAYER_TIPS[key]
    return ""


_RESOURCE_NAMES_BY_KEYWORD = {
    "bardic inspiration": "Bardic Inspiration",
    "channel divinity": "Channel Divinity",
    "wild shape": "Wild Shape",
    "rage": "Rage",
    "lay on hands": "Lay on Hands",
    "action surge": "Action Surge",
    "second wind": "Second Wind",
    "sorcery": "Sorcery Points",
    "focus": "Focus Points",
    "discipline": "Focus Points",
    "indomitable": "Indomitable",
}


def _infer_resource_name(name: str, description: str) -> str:
    hay = f"{name} {description}".lower()
    for needle, label in _RESOURCE_NAMES_BY_KEYWORD.items():
        if needle in hay:
            return label
    return ""


def _sanitize_player_text(text: Any) -> str:
    raw = str(text or "").replace("\r", "").strip()
    if not raw:
        return ""
    blocked_patterns = [
        r"\bthe sheet should\b",
        r"\bthe sheet should make\b",
        r"\bthe player should\b",
        r"\bpractical effect\b",
        r"\bthis shines most when\b",
        r"\bstart here\b",
        r"\bbest time to use it\b",
        r"\busually watch\b",
        r"\bimportant thing is\b",
        r"\bhidden unlock\b",
        r"\bin-app job\b",
    ]
    parts = [part.strip() for part in re.split(r"\n{2,}", raw) if str(part or "").strip()]
    kept: list[str] = []
    for part in parts:
        lowered = part.lower()
        if any(re.search(pattern, lowered) for pattern in blocked_patterns):
            continue
        cleaned = re.sub(r"\b[Ii]n play,?\s*", "", part)
        cleaned = re.sub(r"\b[Tt]his matters because\b", "It matters because", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
        if cleaned:
            kept.append(cleaned)
    if not kept:
        return ""
    return "\n\n".join(kept)


def _clean_detail_parts(parts: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        value = _sanitize_player_text(part)
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
    return cleaned



def build_feature_profile(
    *,
    name: Any,
    level: int = 0,
    description: Any = "",
    feature_id: Any = "",
    class_name: Any = "",
    subclass_name: Any = "",
    source_kind: str = "class",
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = copy.deepcopy(defaults or {})
    display_name = str(name or "").strip() or "Feature"
    clean_key = normalized_feature_name(display_name)
    authored = copy.deepcopy(_FEATURE_OVERRIDES.get(clean_key) or {})
    progression = _progression_profile(display_name)
    raw_description = str(description or authored.get("description") or base.get("description") or "").strip()
    parsed = _parsed_fields(raw_description)

    tags: list[str] = []
    for source in (base.get("tags"), authored.get("tags"), progression.get("tags")):
        if isinstance(source, list):
            tags.extend([str(item or "").strip().lower() for item in source if str(item or "").strip()])
    tags = list(dict.fromkeys(tags))
    if source_kind == "subclass" and "subclass" not in tags:
        tags.append("subclass")
    if source_kind == "trait" and "origin" not in tags:
        tags.append("origin")
    if source_kind == "feat" and "feat" not in tags:
        tags.append("feat")

    type_value = str(authored.get("type") or progression.get("type") or parsed.get("type") or base.get("type") or "passive").strip().lower()
    section = str(authored.get("section") or progression.get("section") or base.get("section") or ("Actions" if type_value == "action" else "Bonus Actions" if type_value == "bonus action" else "Reactions" if type_value == "reaction" else "Class Features")).strip()
    resource_name = str(authored.get("resourceName") or progression.get("resourceName") or base.get("resourceName") or _infer_resource_name(display_name, raw_description)).strip()
    track_uses = bool(authored.get("trackUses") or progression.get("trackUses") or base.get("trackUses") or bool(resource_name) or bool(parsed.get("usage")))
    summary = _sanitize_player_text(authored.get("summary") or progression.get("summary") or _summary_from_text(raw_description)).strip()
    if not summary:
        summary = f"Level {level} {display_name} feature." if level else f"{display_name} feature."

    if raw_description:
        detail_parts = [raw_description]
    else:
        detail_parts = []
        authored_description = str(authored.get("description") or progression.get("description") or base.get("description") or "").strip()
        if authored_description:
            detail_parts.append(authored_description)
    authored_description = str(authored.get("description") or progression.get("description") or "").strip()
    if authored_description and authored_description not in detail_parts:
        detail_parts.append(authored_description)

    if parsed.get("usage") and not any("rest" in part.lower() or "times" in part.lower() for part in detail_parts):
        detail_parts.append(f"Usage: {parsed['usage'][0].upper() + parsed['usage'][1:]}." if parsed['usage'] else "")
    if authored.get("recovery") and authored["recovery"] not in detail_parts:
        detail_parts.append(str(authored["recovery"]).strip())
    if authored.get("effect") and authored["effect"] not in detail_parts:
        detail_parts.append(f"Effect: {str(authored['effect']).strip()}")

    description_text = "\n\n".join(_clean_detail_parts([part for part in detail_parts if str(part or "").strip()]))

    return {
        "id": str(feature_id or slugify(display_name) or display_name).strip(),
        "displayName": display_name,
        "name": display_name,
        "summary": summary,
        "description": description_text,
        "level": int(level or 0),
        "section": section,
        "type": type_value,
        "resourceName": resource_name,
        "trackUses": track_uses,
        "tags": tags,
        "sourceKind": source_kind,
        "className": str(class_name or "").strip(),
        "subclassName": str(subclass_name or "").strip(),
        "range": str(authored.get("range") or parsed.get("range") or "").strip(),
        "duration": str(authored.get("duration") or parsed.get("duration") or "").strip(),
        "save": str(authored.get("save") or parsed.get("save") or "").strip(),
        "trigger": str(authored.get("trigger") or parsed.get("trigger") or "").strip(),
        "usage": str(authored.get("usage") or parsed.get("usage") or "").strip(),
        "recovery": str(authored.get("recovery") or "").strip(),
        "effect": str(authored.get("effect") or progression.get("effect") or "").strip(),
        "dice": str(authored.get("dice") or parsed.get("dice") or "").strip(),
    }



def build_species_trait_profile(species_id: Any, trait_row: dict[str, Any]) -> dict[str, Any]:
    row = trait_row if isinstance(trait_row, dict) else {}
    profile = build_feature_profile(
        name=row.get("displayName") or row.get("name") or row.get("id"),
        level=0,
        description=row.get("description") or row.get("summary"),
        feature_id=row.get("id") or f"{species_id}-{slugify(row.get('displayName') or row.get('name') or row.get('id'))}",
        class_name=str(species_id or "").strip(),
        source_kind="trait",
        defaults={
            "section": "Species / Origin Traits",
            "type": "passive",
            "tags": ["origin"],
        },
    )
    mechanics = row.get("mechanics") if isinstance(row.get("mechanics"), dict) else {}
    uses = str(mechanics.get("usesPerRest") or "").strip()
    action_type = str(mechanics.get("actionType") or "").strip().lower()
    if action_type and action_type != "none" and profile["type"] == "passive":
        profile["type"] = action_type
        profile["section"] = "Actions" if action_type == "action" else "Bonus Actions" if action_type == "bonus action" else "Reactions" if action_type == "reaction" else profile["section"]
    if uses and not profile.get("usage"):
        profile["usage"] = uses
        profile["trackUses"] = profile["trackUses"] or uses.lower() not in {"unlimited", "none"}
    profile["source"] = str(species_id or "").strip()
    return profile



def build_background_feature_profile(background_row: dict[str, Any]) -> dict[str, Any] | None:
    row = background_row if isinstance(background_row, dict) else {}
    title = str(row.get("featureTitle") or "").strip()
    desc = str(row.get("featureDescription") or row.get("description") or "").strip()
    if not title and not desc:
        return None
    return build_feature_profile(
        name=title or (str(row.get("displayName") or row.get("id") or "Background Feature").strip() + " Feature"),
        description=desc,
        feature_id=f"background-{slugify(row.get('id') or title or row.get('displayName'))}",
        class_name=str(row.get("displayName") or row.get("id") or "Background").strip(),
        source_kind="trait",
        defaults={
            "section": "Species / Origin Traits",
            "type": "passive",
            "tags": ["origin", "background", "utility"],
        },
    )



def build_feat_profile(feat_row: dict[str, Any]) -> dict[str, Any] | None:
    row = feat_row if isinstance(feat_row, dict) else {}
    title = str(row.get("displayName") or row.get("name") or row.get("id") or "").strip()
    if not title:
        return None
    description = str(row.get("description") or "").strip()
    profile = build_feature_profile(
        name=title,
        description=description,
        feature_id=row.get("id") or slugify(title),
        source_kind="feat",
        defaults={
            "section": "Feats",
            "type": "passive",
            "tags": ["feat", "build"],
        },
    )
    bonus = row.get("abilityBonus") if isinstance(row.get("abilityBonus"), dict) else {}
    prereq = str(row.get("prerequisite") or "").strip()
    extra_notes: list[str] = []
    if prereq:
        extra_notes.append(f"Prerequisite: {prereq}.")
    if bonus:
        ability = str(bonus.get("ability") or "").strip()
        amount = str(bonus.get("bonus") or "").strip()
        if ability or amount:
            extra_notes.append(f"Build impact: grants {amount or '?'} to {ability or 'an ability choice'}.".replace("  ", " ").strip())
    if extra_notes:
        profile["description"] = (profile["description"] + "\n\n" + " ".join(extra_notes)).strip()
    return profile
