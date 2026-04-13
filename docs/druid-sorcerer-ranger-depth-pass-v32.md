# Druid / Sorcerer / Ranger depth pass v32

This pass continues the anchor-class depth roadmap by improving the next three subsystem-heavy classes:
Druid, Sorcerer, and Ranger.

## What changed

- Added stable `unlockIds` to `progressionTable` rows for Druid, Sorcerer, and Ranger so authored feature data binds directly to the runtime feature catalog.
- Added richer authored class feature definitions for key base features in all three classes.
- Added richer authored subclass feature definitions for:
  - Druid: Circle of the Land, Circle of the Moon
  - Sorcerer: Wild Magic, Draconic Bloodline
  - Ranger: Hunter, Gloom Stalker, Beast Master

## Focus of this pass

- Make class and subclass entries read like player-facing sheet content instead of generic generated summaries.
- Improve identity text around transformation, sorcery-point economy, metamagic, hunting, companions, and ambush features.
- Ensure a few signature features carry explicit action/reaction/resource metadata where that improves gameplay surfacing.

## Next recommended wave

- subclass completion sweep for remaining classes
- broader spell-catalog expansion
- then custom class planning / implementation for Tinker and Pirate on top of the stronger baseline
