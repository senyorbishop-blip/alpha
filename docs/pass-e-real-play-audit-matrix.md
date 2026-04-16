# Pass E Real-Play Audit Matrix (Alpha)

This matrix is the runtime playability audit surface used for Pass E hardening.

## Class matrix

| Class | Build audited | Basic attack loop | Class resource loop | Major feature loop | Spell loop | Subclass loop | Summon/deploy loop | Level-up continuation |
|---|---|---|---|---|---|---|---|---|
| Barbarian | Berserker | ✅ | ✅ Rage | ✅ Reckless/Frenzy surfaces | N/A | ✅ | N/A | ✅ (4→5) |
| Bard | College of Lore | ✅ | ✅ Bardic Inspiration | ✅ Inspiration + support cadence | ✅ known/slot model | ✅ | N/A | Covered by runtime loop matrix |
| Cleric | Life Domain | ✅ | ✅ Channel Divinity resources | ✅ domain feature surfaces | ✅ prepared/slot model | ✅ | N/A | Covered by runtime loop matrix |
| Druid | Circle of the Land | ✅ | ✅ Wild Shape/resources | ✅ druid utility + combat features | ✅ prepared/slot model | ✅ | N/A | Covered by runtime loop matrix |
| Fighter | Battlemaster | ✅ | ✅ Second Wind/Action Surge | ✅ maneuver cadence | N/A | ✅ | N/A | Covered by runtime loop matrix |
| Monk | Way of the Open Hand | ✅ | ✅ Focus/Ki resources | ✅ martial arts loop | N/A | ✅ | N/A | Covered by runtime loop matrix |
| Paladin | Oath of Devotion | ✅ | ✅ Lay on Hands + Channel Divinity | ✅ smite + aura surfaces | ✅ half-caster slot model | ✅ | N/A | Covered by runtime loop matrix |
| Ranger | Hunter + Beast Master | ✅ | ✅ class/subclass resources | ✅ Hunter path choices | ✅ half-caster slot model | ✅ | ✅ Primal Beast summon action | ✅ (4→5) |
| Rogue | Thief | ✅ | ✅ feature-gated resources | ✅ sneak/cunning loop surfaces | N/A | ✅ | N/A | Covered by runtime loop matrix |
| Sorcerer | Draconic Bloodline | ✅ | ✅ Sorcery points | ✅ metamagic surfaces | ✅ known/spell-point style loop | ✅ | N/A | Covered by runtime loop matrix |
| Warlock | Fiend Patron (+ Chain boon for summon check) | ✅ | ✅ pact slots/invocations | ✅ eldritch pressure loop | ✅ pact magic model | ✅ | ✅ Pact of the Chain familiar summon action | Covered by runtime loop matrix |
| Wizard | Evoker | ✅ | ✅ class resources | ✅ arcane utility + evocation surfaces | ✅ prepared + spellbook model | ✅ | N/A | ✅ (4→5) |
| Tinker | Mechanist | ✅ | ✅ gadget/deploy resources | ✅ gadget + support loop | ✅ class spell model | ✅ | ✅ Companion Frame deploy action | Covered by runtime loop matrix |
| Pirate | Corsair | ✅ | ✅ swagger-style resources | ✅ subclass combat pressure | N/A | ✅ | N/A | Covered by runtime loop matrix |

## Highest-value breakpoints found in Pass E audit

### Blockers (fixed)

1. `server/character/spell_text_generator.py` had a syntax error in spell inference (`f-string: unmatched '('`) that broke character runtime imports and blocked class play validation paths.
2. `server/character/resolver.py` dropped `selectedFeatures` while normalizing class rows, causing selected subclass feature choices to disappear from runtime class loops (e.g., Hunter's Prey choice variant not surfaced).
3. Resource cards with equivalent meaning (hyphen/underscore variants) could appear duplicated in runtime output, reducing first-turn usability signal.
4. Some classes had no immediate action in runtime action lanes when no explicit attack/class-action row was emitted.

### Non-blockers (left as-is in Pass E)

1. Warlock level-up option validation can still reject a preview-proposed spell option in certain data combinations (catalog legality mismatch). This is documented but not widened into a rules-content rewrite in Pass E.

### Deferred

1. Full end-to-end browser multi-role manual verification (DM/player/viewer) requires a live session harness and coordinated windows; this pass focused on deterministic runtime/test coverage and runtime-path repairs.
2. Broader authored-content normalization for legacy unlock ID naming (outside direct runtime blockers) is deferred to a content cleanup pass.
