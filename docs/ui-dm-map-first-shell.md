# Casual D&D / Alpha — DM Map-First Shell Scaffold

## Purpose

This document describes the first practical shell scaffold for the map-first DM layout. It follows the map-first foundation from `docs/ui-map-first-blueprint.md` and prepares the app for a later wiring PR.

This stage is intentionally low risk:

- no live gameplay behaviour changes
- no WebSocket changes
- no token authority changes
- no combat rule changes
- no inventory changes
- no viewer-power behaviour changes
- no full `play.html` rewrite

## Target layout

```text
top session bar
left mode rail | huge centre map | right context panel
bottom quick strip
```

The map remains the largest element. The right context panel changes based on the active DM mode.

## DM mode rail

Mode IDs:

- `run`
- `combat`
- `map-build`
- `npc-monster`
- `loot-shop`
- `session-tools`
- `viewer-powers`
- `debug`

## Context panel ownership

| Mode | Context panel owns |
|---|---|
| Run Game | selected token, party overview, handouts, narration, save state |
| Combat | current turn, initiative, action usage, movement, HP, conditions |
| Map Build | terrain, fog, walls, doors, reveal/hide, layers, lighting/weather |
| NPC / Monster | bestiary, spawn token, creature stats, notes, conditions |
| Loot / Shop | items, loot containers, shops, gold, charges, attunement |
| Session Tools | quests, handouts, journal, narration, sound, polls |
| Viewer Powers | connected viewers, grants, approvals, cooldowns, feedback |
| Debug | readiness, payload, reconnect, WebSocket and sync diagnostics |

## Bottom quick strip

Default actions:

- Select
- Move
- Measure
- Draw
- Light
- Notes
- More

## Scaffold files

This stage adds:

- `client/static/css/dm-map-first-shell.css`
- `client/static/js/ui/dm_map_first_shell.js`
- `tests/test_dm_map_first_shell.py`

The CSS provides reusable classes. The JS provides mode metadata. Nothing is wired into the live screen in this stage.

## Next wiring stage

The next PR can safely:

1. load `map-first-ui-tokens.css`
2. load `dm-map-first-shell.css`
3. load `dm_map_first_shell.js`
4. wrap the existing DM screen in the shell classes
5. map existing tabs/tools into mode groups without deleting functionality

The wiring PR must keep a rollback path and must not remove current controls.
