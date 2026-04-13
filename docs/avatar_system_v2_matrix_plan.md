# Avatar System V2 — portrait matrix plan

This pass starts the image-driven importer creator.

## Goal
The creator should resolve a portrait from the combination of:
- species
- class
- presentation (masculine / feminine / neutral)

## Asset naming
`client/static/importer/portraits/combos/{species}__{class}__{presentation}.png`

Examples:
- `human__fighter__masculine.png`
- `human__fighter__feminine.png`
- `human__fighter__neutral.png`
- `elf__warlock__masculine.png`

## Fallback order
1. exact combo portrait
2. neutral combo portrait for that species/class
3. species portrait
4. class portrait
5. renderer fallback

## Starter scope in this build
- Human + Fighter (3)
- Elf + Warlock (3)

## Planned expansion order
1. Human × all classes × 3 presentations
2. Elf × all classes × 3 presentations
3. Aasimar / Dwarf / Dragonborn / Tiefling / Goliath

## Why manifest-based
The UI can ship now and progressively gain coverage as portraits are added.
