# Tinker foundation pass v36

This pass adds a fully data-driven custom **Tinker** class to the native 5e2024 catalog.

## Added
- New class: `tinker`
- New subclasses:
  - `artillerist`
  - `alchemist`
  - `mechanist`
  - `saboteur`
- New class spell list integration via `class_spell_lists.json`
- Runtime spell-compendium support so class spell lists become visible as real class access
- Subclass spell grants for all four Tinker specializations

## Tinker identity
- Intelligence-based half-caster
- Uses a prototype rig, modular infusions, and gadget charges
- Plays as a support/control/utility engineer with deployable and loadout flavor

## Core feature spine
1. Tinkercraft
2. Prototype Rig
3. Spellcasting
4. Quick Deployment
5. Tool Expertise
6. Field Specialization
7. Specialty Spells
8. Overclocked Device
9. Modular Infusions
10. Reactive Countermeasure
11. Improved Rig
12. Signature Device
13. Emergency Repairs
14. Masterwork Infusions
15. Overcharge
16. Dual Deployment
17. Grand Invention

## Subclass roles
- **Artillerist**: ranged pressure, blast control, ordinance identity
- **Alchemist**: brews, restoration, adaptive chemistry, support identity
- **Mechanist**: companion-frame and automation play
- **Saboteur**: stealth, traps, disruption, infiltration pressure

## Runtime improvements
The spell compendium now merges `class_spell_lists.json` into spell class access, which means custom or future classes can gain real spell-list support without editing every spell row individually.
