"""
server/srd_npcs.py — Pre-built NPC seed data.
Provides a broad set of ready-to-use NPCs across archetypes:
  Townsfolk, Faction, Villains, and Allies.

Each entry maps to the user_creature_library table schema.
NPC-specific flavour (personality, ideals, bonds, flaws, appearance,
quest hooks) is stored as structured text in the backstory field.
"""

SRD_NPCS: list[dict] = [
    # ══════════════════════════════════════════════════════════════════════
    # TOWNSFOLK
    # ══════════════════════════════════════════════════════════════════════
    {
        "srd_id": "npc_blacksmith",
        "name": "Aldric the Blacksmith",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "1/8", "hp": 15, "ac": 10, "speed": "30 ft.",
        "str_score": 16, "dex_score": 9, "con_score": 14, "int_score": 10, "wis_score": 12, "cha_score": 10,
        "attacks": [{"name": "Hammer", "bonus": 5, "damage": "1d6+3", "type": "bludgeoning"}],
        "abilities": [{"name": "Skilled Craftsman", "desc": "Proficient with smith's tools; can repair metal armour and weapons during a short rest."}],
        "backstory": (
            "Race: Human | Occupation: Village Blacksmith\n"
            "Personality: Hard-working and blunt; speaks plainly and values results over words. "
            "Soft-hearted toward children and animals despite his gruff exterior.\n"
            "Ideal: Honest craft — a well-made blade speaks for itself.\n"
            "Bond: His late father's anvil sits in the shop; he will never sell it.\n"
            "Flaw: Stubborn to a fault; refuses to admit when he is wrong.\n"
            "Appearance: Broad-shouldered human man with burn-scarred forearms, a shaved head, "
            "and a short reddish beard. Always wears a leather apron.\n"
            "Quest Hooks: (1) A merchant stole a large order of weapons without paying — Aldric "
            "needs adventurers to reclaim the goods. (2) Strange metal ore has appeared near the "
            "old mine and Aldric wants a sample to study."
        ),
        "tags": ["humanoid", "npc", "townsfolk"],
    },
    {
        "srd_id": "npc_innkeeper",
        "name": "Marta the Innkeeper",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "0", "hp": 9, "ac": 10, "speed": "30 ft.",
        "str_score": 10, "dex_score": 12, "con_score": 10, "int_score": 13, "wis_score": 14, "cha_score": 16,
        "attacks": [{"name": "Rolling Pin", "bonus": 2, "damage": "1d4", "type": "bludgeoning"}],
        "abilities": [{"name": "Well-Connected", "desc": "Knows almost every traveller who has passed through town; can share rumours as a free action during conversation."}],
        "backstory": (
            "Race: Halfling | Occupation: Innkeeper & Tavern Owner\n"
            "Personality: Warm and garrulous; remembers the name of every patron who has stayed "
            "more than one night. Has strong opinions on everything.\n"
            "Ideal: Community — a tavern is the heart of a town.\n"
            "Bond: Her inn has been in the family for four generations; she will do anything to "
            "keep it running.\n"
            "Flaw: Cannot keep a secret; she gossips without meaning to.\n"
            "Appearance: Short halfling woman with curly auburn hair pinned up under a cloth cap, "
            "rosy cheeks, and quick green eyes. Always smells faintly of cinnamon.\n"
            "Quest Hooks: (1) A room has been left paid and empty for three weeks; the guest has "
            "not returned. (2) Marta overheard a hushed conversation about a stolen shipment and "
            "will share details in exchange for a favour."
        ),
        "tags": ["humanoid", "npc", "townsfolk"],
    },
    {
        "srd_id": "npc_merchant",
        "name": "Oswynn the Merchant",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "1/8", "hp": 9, "ac": 11, "speed": "30 ft.",
        "str_score": 9, "dex_score": 12, "con_score": 10, "int_score": 15, "wis_score": 11, "cha_score": 14,
        "attacks": [{"name": "Dagger", "bonus": 3, "damage": "1d4+1", "type": "piercing"}],
        "abilities": [{"name": "Appraiser", "desc": "Can identify the value of non-magical trade goods, gems, and art objects without tools."}],
        "backstory": (
            "Race: Human | Occupation: Travelling Merchant\n"
            "Personality: Shrewd but fair; always angling for a better deal but never outright "
            "dishonest. Enjoys a lively haggle.\n"
            "Ideal: Profit with principle — reputation is the most valuable currency.\n"
            "Bond: Owes a life debt to a caravan guard who once saved his shipment from bandits.\n"
            "Flaw: Greedy; he occasionally inflates prices for outsiders who don't know local rates.\n"
            "Appearance: Lean human man in his forties wearing fine but travel-worn clothes. "
            "Silver rings on three fingers and a quill perpetually behind one ear.\n"
            "Quest Hooks: (1) His caravan was raided and a specific crate — contents unknown — "
            "was taken. He offers a generous reward for its return unopened. (2) Needs escorts "
            "through a dangerous pass to reach the next city before a rival gets there."
        ),
        "tags": ["humanoid", "npc", "townsfolk"],
    },
    {
        "srd_id": "npc_beggar",
        "name": "Tam the Beggar",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "0", "hp": 4, "ac": 10, "speed": "30 ft.",
        "str_score": 8, "dex_score": 10, "con_score": 9, "int_score": 12, "wis_score": 14, "cha_score": 9,
        "attacks": [{"name": "Improvised Weapon", "bonus": 1, "damage": "1d4-1", "type": "bludgeoning"}],
        "abilities": [{"name": "Eyes of the Street", "desc": "Notices things others ignore; makes Perception checks with advantage in urban environments."}],
        "backstory": (
            "Race: Human | Occupation: Beggar / Street Informant\n"
            "Personality: Watchful and cautious; reveals little of himself but notices everything. "
            "Surprisingly witty when comfortable.\n"
            "Ideal: Survival — nothing else matters when you're hungry.\n"
            "Bond: Looks after a group of orphan children who sleep under the market bridge.\n"
            "Flaw: Distrusts anyone who appears wealthy or authoritative.\n"
            "Appearance: Gaunt human with weathered skin, mismatched worn clothing, and sharp "
            "grey eyes that miss nothing. A ragged cloak serves as both coat and blanket.\n"
            "Quest Hooks: (1) Tam witnessed a late-night murder but fears retaliation if he "
            "speaks to the guard — he will only tell adventurers he trusts. (2) He has found "
            "a sewer entrance that leads somewhere strange and dangerous."
        ),
        "tags": ["humanoid", "npc", "townsfolk"],
    },
    {
        "srd_id": "npc_town_guard",
        "name": "Sergeant Brynn",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "1/8", "hp": 16, "ac": 16, "speed": "30 ft.",
        "str_score": 13, "dex_score": 12, "con_score": 12, "int_score": 10, "wis_score": 11, "cha_score": 10,
        "attacks": [{"name": "Spear", "bonus": 3, "damage": "1d6+1", "type": "piercing"},
                    {"name": "Heavy Crossbow", "bonus": 3, "damage": "1d10+1", "type": "piercing", "range": "100/400 ft."}],
        "abilities": [{"name": "Crowd Control", "desc": "Can attempt to grapple or shove as a bonus action when adjacent to an unarmoured target."}],
        "backstory": (
            "Race: Human | Occupation: Town Guard Sergeant\n"
            "Personality: Dutiful and by-the-book; she treats every citizen equally and will not "
            "bend rules even for friends. Has a dry sense of humour off duty.\n"
            "Ideal: Order — laws exist to protect everyone, not just the privileged.\n"
            "Bond: Her squad of six guards are like family; she will risk her own safety for them.\n"
            "Flaw: Overly rigid; she struggles when rules conflict with obvious justice.\n"
            "Appearance: Stocky woman in polished chain mail with a red sergeant's sash. Close-"
            "cropped dark hair and a scar across the chin from an old arrest gone wrong.\n"
            "Quest Hooks: (1) A series of thefts has confounded the guard and Brynn discreetly "
            "asks adventurers to look into it unofficially. (2) One of her guards has gone "
            "missing during night patrol."
        ),
        "tags": ["humanoid", "npc", "townsfolk"],
    },
    {
        "srd_id": "npc_priest",
        "name": "Brother Caelen",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "2", "hp": 27, "ac": 13, "speed": "30 ft.",
        "str_score": 10, "dex_score": 10, "con_score": 12, "int_score": 13, "wis_score": 16, "cha_score": 13,
        "attacks": [{"name": "Mace", "bonus": 2, "damage": "1d6", "type": "bludgeoning"}],
        "abilities": [{"name": "Spellcasting (WIS)", "desc": "Spell save DC 13. Prepared: cure wounds, guiding bolt, sanctuary; hold person, spiritual weapon; dispel magic."},
                      {"name": "Divine Eminence", "desc": "As a bonus action, can expend a spell slot to add 10 (3d6) radiant damage to the next weapon hit."}],
        "backstory": (
            "Race: Human | Occupation: Temple Priest\n"
            "Personality: Compassionate and patient; listens more than he speaks. "
            "Quietly passionate about matters of faith.\n"
            "Ideal: Charity — faith without service is hollow.\n"
            "Bond: The temple's ancient library holds a forbidden text he vowed never to open.\n"
            "Flaw: Naïve about the capacity for evil; he always looks for the best in people.\n"
            "Appearance: Slender human man in white and gold vestments, with tonsured dark hair "
            "and gentle brown eyes. Carries a carved wooden holy symbol.\n"
            "Quest Hooks: (1) Undead have been disturbing the temple graveyard at night. "
            "(2) A family begs him to retrieve a stolen family relic from a local criminal."
        ),
        "tags": ["humanoid", "npc", "townsfolk"],
    },
    {
        "srd_id": "npc_herbalist",
        "name": "Ysolde the Herbalist",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "0", "hp": 9, "ac": 10, "speed": "30 ft.",
        "str_score": 8, "dex_score": 13, "con_score": 10, "int_score": 16, "wis_score": 15, "cha_score": 12,
        "attacks": [{"name": "Staff", "bonus": 1, "damage": "1d6-1", "type": "bludgeoning"}],
        "abilities": [{"name": "Herbalism", "desc": "Can craft a healer's kit or a basic antitoxin from wild plants given 1 hour and the right environment."}],
        "backstory": (
            "Race: Wood Elf | Occupation: Herbalist & Apothecary\n"
            "Personality: Thoughtful and methodical; approaches problems as puzzles. "
            "Gets excited about unusual plants or fungi.\n"
            "Ideal: Knowledge — understanding the natural world is a lifelong pursuit.\n"
            "Bond: A rare orchid she has cultivated for twenty years; she considers it a friend.\n"
            "Flaw: Loses track of time when absorbed in research; often forgets appointments.\n"
            "Appearance: Slender elf woman with silver-streaked hair worn loose, ink-stained "
            "fingers, and eyes the colour of new leaves. Smells of dried lavender and soil.\n"
            "Quest Hooks: (1) A blight has killed her herb garden overnight — unnatural in origin. "
            "(2) She needs a rare ingredient from a dangerous forest to complete a cure."
        ),
        "tags": ["humanoid", "npc", "townsfolk"],
    },

    # ══════════════════════════════════════════════════════════════════════
    # FACTION
    # ══════════════════════════════════════════════════════════════════════
    {
        "srd_id": "npc_guild_master",
        "name": "Halvard, Merchants' Guild Master",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "3", "hp": 52, "ac": 14, "speed": "30 ft.",
        "str_score": 11, "dex_score": 14, "con_score": 12, "int_score": 17, "wis_score": 13, "cha_score": 18,
        "attacks": [{"name": "Rapier", "bonus": 4, "damage": "1d8+2", "type": "piercing"},
                    {"name": "Parry (Reaction)", "bonus": 0, "damage": "+2 AC", "type": ""}],
        "abilities": [{"name": "Silver Tongue", "desc": "Advantage on Persuasion and Deception checks in mercantile or social contexts."},
                      {"name": "Contacts Network", "desc": "Can arrange meetings with city officials, merchants, or underworld figures within 24 hours."}],
        "backstory": (
            "Race: Human | Occupation: Merchants' Guild Master\n"
            "Personality: Charming and calculating; always three moves ahead in any negotiation. "
            "Generous with those who are useful, ruthless toward those who cross him.\n"
            "Ideal: Power through prosperity — a wealthy guild is a powerful guild.\n"
            "Bond: An old debt to a thieves' guild that he desperately wants to settle quietly.\n"
            "Flaw: Pride — he cannot tolerate being publicly humiliated.\n"
            "Appearance: Portly human man in his fifties in fine embroidered doublet. "
            "Thinning silver hair, a well-groomed goatee, and rings on every finger.\n"
            "Quest Hooks: (1) He wants a rival guild's ledger stolen — discreetly. "
            "(2) A protected shipment has gone missing and he suspects an inside job."
        ),
        "tags": ["humanoid", "npc", "faction"],
    },
    {
        "srd_id": "npc_thieves_fence",
        "name": "Sal 'Two Fingers' Dunwick",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "2", "hp": 33, "ac": 14, "speed": "30 ft.",
        "str_score": 10, "dex_score": 18, "con_score": 12, "int_score": 14, "wis_score": 13, "cha_score": 15,
        "attacks": [{"name": "Shortsword", "bonus": 6, "damage": "1d6+4", "type": "piercing"},
                    {"name": "Hand Crossbow", "bonus": 6, "damage": "1d6+4", "type": "piercing", "range": "30/120 ft."}],
        "abilities": [{"name": "Fence Network", "desc": "Can move stolen goods and identify buyers or sellers for illegal wares within a city."},
                      {"name": "Evasion", "desc": "If subjected to an effect that allows a DEX save for half damage, he takes no damage on success and half on failure."}],
        "backstory": (
            "Race: Human | Occupation: Thieves' Guild Fence\n"
            "Personality: Friendly in a slippery way; always joking, never fully honest. "
            "Has a code — won't deal in children or magic that 'goes boom nearby'.\n"
            "Ideal: Loyalty — the guild looks after its own, everyone else is fair game.\n"
            "Bond: A younger sister who doesn't know how he earns his coin; he keeps her far away.\n"
            "Flaw: Compulsive gambler; owes money to dangerous people.\n"
            "Appearance: Wiry human with close-cropped dark hair and a sly smile. "
            "Missing the ring and little finger on his left hand. Wears nondescript city clothes.\n"
            "Quest Hooks: (1) A stolen item has passed through his hands that he now realises "
            "was never meant to be sold — it's cursed. He wants it gone. "
            "(2) He'll point the party toward a score in exchange for a favour later."
        ),
        "tags": ["humanoid", "npc", "faction"],
    },
    {
        "srd_id": "npc_watch_captain",
        "name": "Captain Delara Stonewall",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "3", "hp": 52, "ac": 18, "speed": "30 ft.",
        "str_score": 16, "dex_score": 12, "con_score": 14, "int_score": 12, "wis_score": 14, "cha_score": 15,
        "attacks": [{"name": "Multiattack (2 attacks)", "bonus": 0, "damage": "", "type": ""},
                    {"name": "Longsword", "bonus": 5, "damage": "1d8+3", "type": "slashing"},
                    {"name": "Shield Bash", "bonus": 5, "damage": "1d6+3", "type": "bludgeoning"}],
        "abilities": [{"name": "Brave", "desc": "Advantage on saving throws against being frightened."},
                      {"name": "Leadership (Recharges after Short/Long Rest)", "desc": "Allies within 30 ft. who can hear her add 1d4 to attack rolls and saving throws for 1 minute."}],
        "backstory": (
            "Race: Dwarf | Occupation: City Watch Captain\n"
            "Personality: No-nonsense and fiercely protective of the citizens in her district. "
            "Respects competence and distrusts flowery promises.\n"
            "Ideal: Justice — the law is a shield, not a sword.\n"
            "Bond: Her squad died protecting her from an ambush; she carries survivor's guilt.\n"
            "Flaw: Holds grudges — she never forgives a betrayal.\n"
            "Appearance: Stocky dwarf woman with iron-grey braided hair and a scar running "
            "through one eyebrow. Full plate bearing the city's crest, worn to a polish.\n"
            "Quest Hooks: (1) She needs deniable agents to investigate corruption inside the watch. "
            "(2) A serial arsonist has evaded her patrols and she asks adventurers for help."
        ),
        "tags": ["humanoid", "npc", "faction"],
    },
    {
        "srd_id": "npc_noble_lord",
        "name": "Lord Edris Vane",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "1/8", "hp": 9, "ac": 15, "speed": "30 ft.",
        "str_score": 11, "dex_score": 12, "con_score": 11, "int_score": 14, "wis_score": 12, "cha_score": 16,
        "attacks": [{"name": "Rapier", "bonus": 3, "damage": "1d8+1", "type": "piercing"}],
        "abilities": [{"name": "Noble Bearing", "desc": "Advantage on Persuasion checks with commoners and lower-ranking nobles; disadvantage on Persuasion checks with people who distrust the aristocracy."}],
        "backstory": (
            "Race: Human | Occupation: Minor Nobility / Lord of a Rural Estate\n"
            "Personality: Polite, educated, and secretly anxious about his family's declining wealth. "
            "Can be generous when it suits his public image.\n"
            "Ideal: Legacy — the Vane name must endure another generation.\n"
            "Bond: His ancestral manor, which is deeply mortgaged to a city bank.\n"
            "Flaw: Vain; spends money he doesn't have on appearances.\n"
            "Appearance: Tall human in his late thirties with immaculate dark hair, "
            "fine clothes that are subtly frayed at the edges, and a nervous habit of "
            "adjusting his cuffs.\n"
            "Quest Hooks: (1) He offers land in exchange for clearing an old crypt beneath his estate. "
            "(2) His heir has vanished with a suspicious 'tutor'."
        ),
        "tags": ["humanoid", "npc", "faction"],
    },
    {
        "srd_id": "npc_court_mage",
        "name": "Archimandrite Sepha",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "6", "hp": 40, "ac": 12, "speed": "30 ft.",
        "str_score": 9, "dex_score": 14, "con_score": 11, "int_score": 18, "wis_score": 12, "cha_score": 12,
        "attacks": [{"name": "Dagger", "bonus": 4, "damage": "1d4+2", "type": "piercing"},
                    {"name": "Fire Bolt (cantrip)", "bonus": 7, "damage": "4d10", "type": "fire", "range": "120 ft."}],
        "abilities": [{"name": "Spellcasting (INT)", "desc": "Spell save DC 15. Prepared: mage armor, magic missile, shield, misty step, counterspell, fireball, greater invisibility, Bigby's hand."},
                      {"name": "Arcane Recovery (1/Day)", "desc": "During a short rest, recover expended spell slots up to 3rd level."}],
        "backstory": (
            "Race: Tiefling | Occupation: Royal Court Mage\n"
            "Personality: Precise and quietly imperious; never wastes a word. "
            "Fascinated by arcane theory and impatient with those who aren't.\n"
            "Ideal: Knowledge is power — and power must be wielded carefully.\n"
            "Bond: An apprentice she failed years ago who is now an enemy.\n"
            "Flaw: Arrogant; dismisses anyone without formal arcane training.\n"
            "Appearance: Lean tiefling woman with small horns, deep purple skin, "
            "white hair coiled at the nape, and eyes like polished amethyst. "
            "Always wearing midnight-blue robes embroidered with silver sigils.\n"
            "Quest Hooks: (1) A magical anomaly in the palace requires adventurers "
            "to investigate what she cannot risk entering herself. "
            "(2) Her apprentice-turned-rival has stolen a dangerous ritual text."
        ),
        "tags": ["humanoid", "npc", "faction"],
    },

    # ══════════════════════════════════════════════════════════════════════
    # VILLAINS
    # ══════════════════════════════════════════════════════════════════════
    {
        "srd_id": "npc_crime_lord",
        "name": "The Pale Baron",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "5", "hp": 78, "ac": 16, "speed": "30 ft.",
        "str_score": 14, "dex_score": 17, "con_score": 14, "int_score": 18, "wis_score": 14, "cha_score": 20,
        "attacks": [{"name": "Multiattack (2 attacks)", "bonus": 0, "damage": "", "type": ""},
                    {"name": "Poisoned Rapier", "bonus": 8, "damage": "1d8+5", "type": "piercing"},
                    {"name": "Hand Crossbow", "bonus": 8, "damage": "1d6+5", "type": "piercing", "range": "30/120 ft."}],
        "abilities": [{"name": "Uncanny Dodge", "desc": "When hit by an attack the Baron can see, halves the damage taken."},
                      {"name": "Cunning Action", "desc": "Bonus action to Dash, Disengage, or Hide."},
                      {"name": "Master of Shadows", "desc": "While in dim light or darkness has advantage on DEX (Stealth) checks."}],
        "backstory": (
            "Race: Human | Occupation: Crime Lord / Underworld Kingpin\n"
            "Personality: Silky mannered and terrifyingly calm; speaks softly even when giving "
            "orders to kill. Rewards talent and punishes disloyalty with equal extremity.\n"
            "Ideal: Control — fear is a currency that never devalues.\n"
            "Bond: A child he raised as an heir whom he controls absolutely.\n"
            "Flaw: Paranoid; sees betrayal in every shadow and has burned loyal lieutenants "
            "on suspicion.\n"
            "Appearance: Pale human man of indeterminate age, always immaculately dressed in "
            "black. White hair slicked back; pale grey eyes with an unnerving stillness.\n"
            "Quest Hooks: (1) The party is hired to eliminate a rival the Baron also wants "
            "dead — but he wants the credit. (2) A victim of his extortion begs the party to "
            "find evidence against him that would hold up to a lord's court."
        ),
        "tags": ["humanoid", "npc", "villain"],
    },
    {
        "srd_id": "npc_corrupt_official",
        "name": "Magistrate Corvin Shroud",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "1/4", "hp": 20, "ac": 12, "speed": "30 ft.",
        "str_score": 10, "dex_score": 12, "con_score": 11, "int_score": 15, "wis_score": 10, "cha_score": 14,
        "attacks": [{"name": "Dagger (concealed)", "bonus": 3, "damage": "1d4+1", "type": "piercing"}],
        "abilities": [{"name": "Legal Authority", "desc": "Can invoke his office to command guards to detain any creature. Guards of lower rank must make DC 14 CHA save to refuse an unlawful order."}],
        "backstory": (
            "Race: Human | Occupation: Corrupt City Magistrate\n"
            "Personality: Sanctimonious and self-righteous in public; cold and transactional in "
            "private. Genuinely believes that everyone is corrupt — some just hide it better.\n"
            "Ideal: Security — enough wealth and power to be untouchable.\n"
            "Bond: A blackmail dossier on every powerful person in the city; losing it terrifies him.\n"
            "Flaw: Cowardly when personally threatened; will sacrifice allies without hesitation.\n"
            "Appearance: Soft-featured human man in fine legal robes. Thinning brown hair, "
            "soft hands that have never done manual labour, and watery eyes that never quite "
            "meet yours.\n"
            "Quest Hooks: (1) He is framing an innocent person for a crime; the party has been "
            "hired by the victim's family. (2) He approaches the party to eliminate someone who "
            "has evidence of his crimes."
        ),
        "tags": ["humanoid", "npc", "villain"],
    },
    {
        "srd_id": "npc_cult_leader",
        "name": "High Votary Mireth",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "6", "hp": 71, "ac": 14, "speed": "30 ft.",
        "str_score": 10, "dex_score": 14, "con_score": 13, "int_score": 14, "wis_score": 18, "cha_score": 17,
        "attacks": [{"name": "Spiritual Touch", "bonus": 6, "damage": "2d6+4", "type": "necrotic"}],
        "abilities": [{"name": "Spellcasting (WIS)", "desc": "Spell save DC 15. At will: thaumaturgy. Prepared: command, inflict wounds, blindness/deafness, hold person, bestow curse, spirit guardians, contagion."},
                      {"name": "Compelling Sermon", "desc": "As an action, one creature within 30 ft. makes DC 15 WIS save or is charmed until end of Mireth's next turn."}],
        "backstory": (
            "Race: Human | Occupation: Cult Leader / Dark Apostle\n"
            "Personality: Mesmerising and zealous; truly believes in the dark deity she serves. "
            "Uses charm to mask menace and frames cruelty as divine mercy.\n"
            "Ideal: Devotion — sacrifice is the highest form of worship.\n"
            "Bond: The cult is her family; she would die — and kill — for it.\n"
            "Flaw: Fanaticism; she cannot conceive that her patron's will might be wrong.\n"
            "Appearance: Tall human woman in crimson and black robes, with a shaved head "
            "tattooed with religious symbols and eyes perpetually wide with fervour. "
            "An unsettling smile that never fades.\n"
            "Quest Hooks: (1) Missing townsfolk have been lured into her cult's underground temple. "
            "(2) She is preparing a ritual requiring a specific magical item the party possesses."
        ),
        "tags": ["humanoid", "npc", "villain"],
    },
    {
        "srd_id": "npc_bounty_hunter",
        "name": "Revka the Bloodhound",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "4", "hp": 65, "ac": 15, "speed": "30 ft.",
        "str_score": 16, "dex_score": 15, "con_score": 15, "int_score": 12, "wis_score": 15, "cha_score": 11,
        "attacks": [{"name": "Multiattack (2 attacks)", "bonus": 0, "damage": "", "type": ""},
                    {"name": "Net (Range 5/10)", "bonus": 0, "damage": "restrained", "type": ""},
                    {"name": "Handaxe", "bonus": 5, "damage": "1d6+3", "type": "slashing"},
                    {"name": "Light Crossbow", "bonus": 4, "damage": "1d8+2", "type": "piercing", "range": "80/320 ft."}],
        "abilities": [{"name": "Tracker", "desc": "Advantage on Survival checks to track and Perception checks to find hidden creatures."},
                      {"name": "Restraint Expertise", "desc": "Advantage on checks to apply manacles or pin a grappled target."}],
        "backstory": (
            "Race: Half-Orc | Occupation: Bounty Hunter\n"
            "Personality: Efficient and professional; does not enjoy violence but has no "
            "qualms about it. Takes pride in delivering targets alive when possible.\n"
            "Ideal: Contract — a deal struck is a deal kept, no matter who the quarry is.\n"
            "Bond: She is hunting the person who murdered her partner, alongside paid contracts.\n"
            "Flaw: Will not abandon a contracted target even when it becomes clearly wrong.\n"
            "Appearance: Muscular half-orc woman with close-cropped black hair and a network "
            "of tracking sigils tattooed on her arms. Practical leather armour with many pouches.\n"
            "Quest Hooks: (1) She is hunting the same target the party is — cooperation or "
            "conflict? (2) She is after an innocent person framed for a crime and will listen "
            "to evidence but the contract pulls at her."
        ),
        "tags": ["humanoid", "npc", "villain"],
    },
    {
        "srd_id": "npc_assassin",
        "name": "The Needle",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "8", "hp": 78, "ac": 15, "speed": "30 ft.",
        "str_score": 11, "dex_score": 19, "con_score": 14, "int_score": 13, "wis_score": 12, "cha_score": 10,
        "attacks": [{"name": "Multiattack (2 attacks)", "bonus": 0, "damage": "", "type": ""},
                    {"name": "Poisoned Shortsword", "bonus": 8, "damage": "1d6+4", "type": "piercing"},
                    {"name": "Poisoned Hand Crossbow", "bonus": 8, "damage": "1d6+4", "type": "piercing", "range": "30/120 ft."}],
        "abilities": [{"name": "Assassinate", "desc": "On the first turn of combat, attacks against surprised creatures have advantage and score a critical hit."},
                      {"name": "Sneak Attack", "desc": "Deals 4d6 extra damage when hitting with advantage or when an ally is adjacent to the target."},
                      {"name": "Evasion", "desc": "Takes no damage on successful DEX saves that normally deal half damage."}],
        "backstory": (
            "Race: Elf | Occupation: Professional Assassin\n"
            "Personality: Methodical and utterly without sentiment on the job. Off duty, "
            "unexpectedly fond of good food and terrible poetry.\n"
            "Ideal: Craft — every kill is a problem elegantly solved.\n"
            "Bond: A young elf who witnessed one of her kills and whom she chose to spare; "
            "she keeps anonymous tabs on them.\n"
            "Flaw: Curious; she always wants to know who hired her and why.\n"
            "Appearance: Slender elf of indeterminate age, plain features designed to be "
            "forgettable, unremarkable grey clothing. Only distinguishing feature: "
            "a single thin scar across the throat.\n"
            "Quest Hooks: (1) She has been hired to kill someone the party is protecting. "
            "(2) Her current employer has become too dangerous; she needs a way out and "
            "information about them."
        ),
        "tags": ["humanoid", "npc", "villain"],
    },

    # ══════════════════════════════════════════════════════════════════════
    # ALLIES
    # ══════════════════════════════════════════════════════════════════════
    {
        "srd_id": "npc_retired_adventurer",
        "name": "Gareth 'Old Boots' Masson",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "5", "hp": 82, "ac": 16, "speed": "30 ft.",
        "str_score": 17, "dex_score": 13, "con_score": 16, "int_score": 11, "wis_score": 14, "cha_score": 13,
        "attacks": [{"name": "Multiattack (2 attacks)", "bonus": 0, "damage": "", "type": ""},
                    {"name": "Longsword", "bonus": 7, "damage": "1d8+4", "type": "slashing"},
                    {"name": "Javelin", "bonus": 7, "damage": "1d6+4", "type": "piercing", "range": "30/120 ft."}],
        "abilities": [{"name": "Brave", "desc": "Advantage on saving throws against being frightened."},
                      {"name": "Battle-Scarred Veteran", "desc": "Advantage on saving throws against being frightened or charmed; cannot be surprised while conscious."}],
        "backstory": (
            "Race: Human | Occupation: Retired Adventurer / Inn Regular\n"
            "Personality: Gruff but warm; peppering stories with useful advice and terrible jokes. "
            "Still sharpens his sword every morning out of habit.\n"
            "Ideal: Protect those who can't protect themselves — that's why he started and why "
            "he keeps helping.\n"
            "Bond: His old party's grave marker in the village — he visits it every Highsun.\n"
            "Flaw: Drinks too much when the memories get loud.\n"
            "Appearance: Broad human man in his fifties with a white-flecked beard, "
            "a badly healed leg scar, and calloused hands. Wears his old shield as a table decoration "
            "but never leaves home without a blade.\n"
            "Quest Hooks: (1) He knows where an old dungeon entrance is — and what lurks inside. "
            "(2) An old nemesis has surfaced and he can't face them alone anymore."
        ),
        "tags": ["humanoid", "npc", "ally"],
    },
    {
        "srd_id": "npc_eccentric_wizard",
        "name": "Professor Elowen Quirk",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "6", "hp": 40, "ac": 12, "speed": "30 ft.",
        "str_score": 8, "dex_score": 14, "con_score": 11, "int_score": 20, "wis_score": 11, "cha_score": 11,
        "attacks": [{"name": "Quarterstaff", "bonus": 2, "damage": "1d6-1", "type": "bludgeoning"},
                    {"name": "Magic Missile (1st-level)", "bonus": 0, "damage": "3d4+3 force (auto-hit)", "type": "force"}],
        "abilities": [{"name": "Spellcasting (INT)", "desc": "Spell save DC 16. Broad spellbook: detect magic, identify, mage armor, magic missile, misty step, counterspell, fireball, polymorph, dimension door, wall of force."},
                      {"name": "Arcane Recovery (1/Day)", "desc": "Recover expended spell slots up to 4th level during a short rest."}],
        "backstory": (
            "Race: Gnome | Occupation: Independent Scholar & Eccentric Wizard\n"
            "Personality: Enthusiastic to the point of exhaustion; never uses one word when a "
            "hundred will do. Surprisingly perceptive beneath the scatter-brained exterior.\n"
            "Ideal: Discovery — the universe is a puzzle and she intends to solve all of it.\n"
            "Bond: Her tower crammed with decades of research notes — she fears fire above all else.\n"
            "Flaw: Impractical; forgets to eat, sleep, and pay taxes.\n"
            "Appearance: Small gnome woman with wild grey-streaked auburn hair, spectacles on a "
            "chain, and ink on her nose. Always carrying too many books.\n"
            "Quest Hooks: (1) She needs rare components from a dangerous location and will share "
            "knowledge freely in exchange. (2) An experiment has gone wrong and she needs "
            "adventurers to recapture something that escaped."
        ),
        "tags": ["humanoid", "npc", "ally"],
    },
    {
        "srd_id": "npc_wandering_bard",
        "name": "Florindo the Wanderer",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "2", "hp": 27, "ac": 13, "speed": "30 ft.",
        "str_score": 10, "dex_score": 14, "con_score": 11, "int_score": 13, "wis_score": 12, "cha_score": 18,
        "attacks": [{"name": "Rapier", "bonus": 4, "damage": "1d8+2", "type": "piercing"}],
        "abilities": [{"name": "Bardic Inspiration (d8, 4/Day)", "desc": "Grant one creature a d8 Inspiration die to add to an ability check, attack roll, or saving throw."},
                      {"name": "Spellcasting (CHA)", "desc": "Spell save DC 14. Cantrips: vicious mockery, minor illusion. 1st: charm person, healing word, thunderwave. 2nd: invisibility, suggestion."},
                      {"name": "Lore of the Road", "desc": "Advantage on History and Arcana checks about people, places, and events he has personally witnessed or heard about."}],
        "backstory": (
            "Race: Half-Elf | Occupation: Travelling Bard\n"
            "Personality: Charming, irreverent, and perpetually curious. Collects stories "
            "the way others collect coins — and considers himself rich.\n"
            "Ideal: Freedom — no stage too small, no story too dangerous to follow.\n"
            "Bond: A song he has never finished, dedicated to someone he lost.\n"
            "Flaw: Cannot resist meddling in other people's affairs, even at personal risk.\n"
            "Appearance: Tall half-elf with warm brown skin, long dark hair in loose braids, "
            "colourful mismatched clothing, and an ever-present lute case on his back.\n"
            "Quest Hooks: (1) He witnessed something he shouldn't have and is now being hunted. "
            "(2) He knows a song that contains the key to an ancient mystery — if he can "
            "decipher the last verse."
        ),
        "tags": ["humanoid", "npc", "ally"],
    },
    {
        "srd_id": "npc_dwarven_runesmith",
        "name": "Thurid Ironveil",
        "creature_type": "npc",
        "monster_type": "humanoid",
        "cr": "4", "hp": 65, "ac": 16, "speed": "25 ft.",
        "str_score": 17, "dex_score": 9, "con_score": 18, "int_score": 16, "wis_score": 13, "cha_score": 10,
        "attacks": [{"name": "Runic War Pick", "bonus": 6, "damage": "1d8+4", "type": "piercing"}],
        "abilities": [{"name": "Runic Crafting", "desc": "Can inscribe runes on weapons and armour during a long rest: +1 to attack/damage, or grant resistance to one damage type (24 hours)."},
                      {"name": "Stonecunning", "desc": "Treat any stonework-related History check as proficient; double proficiency bonus applies."},
                      {"name": "Dwarven Resilience", "desc": "Advantage on saving throws against poison."}],
        "backstory": (
            "Race: Dwarf | Occupation: Runesmith / Arcane Craftsperson\n"
            "Personality: Terse and practical; considers most conversation a waste of breath "
            "that could be spent working. Intensely loyal once trust is earned.\n"
            "Ideal: Mastery — a flawed rune is worse than no rune at all.\n"
            "Bond: Her clan's runebook, stolen by a rival clan; she will do anything to recover it.\n"
            "Flaw: Perfectionist; will delay a project indefinitely rather than deliver "
            "something imperfect.\n"
            "Appearance: Short, powerfully built dwarf woman with stone-dust in her braided "
            "auburn beard and runes tattooed across her forearms and knuckles. "
            "Smells of hot metal and enchanting reagents.\n"
            "Quest Hooks: (1) She will enchant the party's gear in exchange for retrieving "
            "her stolen runebook from a rival's vault. "
            "(2) A rune she inscribed long ago on an ancient door has activated — "
            "she needs adventurers to investigate what it has sealed in (or out)."
        ),
        "tags": ["humanoid", "npc", "ally"],
    },
]
