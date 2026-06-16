# Character Sheet Runtime QA

Runtime source of truth: backend `runtime.characterSheetRuntime`, normalized by `buildCharacterSheetRuntime()` for defensive cleanup and legacy tab fields.

1. Open Bishop Sorcerer 19.
2. Confirm header/stats/HP/AC/speed/proficiency/initiative match the backend runtime.
3. Confirm Actions tab uses runtime attacks/actions/bonus actions/reactions/limited-use actions/item spells/features.
4. Confirm Spells tab uses runtime spells and item spells; verify scaling for Fireball, Absorb Elements, Call Lightning, Lightning Bolt, Cure Wounds, Magic Missile, Scorching Ray, and Fire Bolt.
5. Confirm Features & Traits has no duplicate Sorcerer features.
6. Confirm Sorcery Points/Metamagic/Font of Magic work and are linked to one resource.
7. Confirm Quickened Spell affects bonus-action spell economy and does not duplicate spell cards.
8. Confirm Thunder Mage Quarterstaff appears as an equipped weapon attack and item-spell source.
9. Confirm item spells are separate from class prepared/known spells.
10. Open a level 5 martial character.
11. Open a level 5 caster.
12. Open imported PDF character.
13. Confirm no duplicate imported/native features.
14. Confirm Short Rest and Long Rest reset correct resources.
15. Confirm Combat Quick Bar matches the sheet, including item spells.

## Fallback systems to watch

- Frontend `buildCharacterSheetRuntime()` still contains compatibility synthesis when no backend `characterSheetRuntime` exists.
- Custom Tinker/Pirate action cards remain local fallbacks.
- Legacy `play.html` overview reads legacy fields populated from the runtime until the full play page is migrated.
