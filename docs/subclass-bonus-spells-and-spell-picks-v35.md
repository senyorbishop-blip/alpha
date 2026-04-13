# Subclass Bonus Spells + Spell Pick Rules Pass (v35)

This pass closes the next spell-depth gap after the catalog expansion by making subclass-granted spells behave like first-class runtime data.

## Added in this pass

- Added subclass spell grant support for several present subclasses.
- Merged always-prepared and always-known subclass spells into effective spell state.
- Updated validation so subclass-granted spells do not fail legality checks and do not consume normal prepared limits when they are always prepared.
- Updated level-up preview so subclass spell unlocks can surface when a subclass tier grants them.
- Updated spell manifest generation so bonus subclass spells appear in the player-facing spell list without requiring manual re-entry.

## Current supported grant groups

- Cleric domains: Life, Light, Trickery, War
- Paladin oath: Devotion
- Warlock patrons: Archfey, Fiend, Great Old One

## Why this matters

Before this pass, the spell catalog was broader, but subclass identity still depended too much on the player manually reconstructing what their subclass should be granting. Now the runtime can surface that identity directly in spell validation, level-up previews, and the live spell manifest.
