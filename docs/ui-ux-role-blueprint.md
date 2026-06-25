# Casual D&D / Alpha UI UX Role Blueprint

## Purpose

This document starts the safe visual redesign for the live VTT. It defines the role layouts, visual style, design tokens, and coverage expectations before any major screen rebuild happens.

The visual target is the approved dark fantasy mockup: deep dark surfaces, cyan magic accents, antique gold highlights, parchment notes, clean cards, clear role separation, and a stream friendly layout.

The mockup is inspiration, not a screen to copy exactly. The Player view must stay compact by default. Larger panels open only when needed.

## Core principle

Everything must be accessible. Nothing should be dumped on screen all at once.

Use progressive disclosure:

| Priority | Visibility rule | Examples |
|---|---|---|
| Critical live info | Always visible | HP, AC, passive perception, turn, selected token, current map |
| Common actions | Compact access | Action, Cast, Inventory, Roll, Rest, Character |
| Detailed tools | Drawer or modal | Spellbook, inventory, character sheet, journal |
| DM prep tools | Mode specific | Map Build, NPC/Monster, Loot/Shop, Session Tools |
| Debug tools | Closed by default | stream readiness, payload warnings, reconnect warnings |
| Rare tools | Tucked away | imports, advanced config, diagnostics |

## Design goals

1. Make the app feel like a polished tabletop VTT, not a developer console.
2. Preserve current gameplay functions while improving presentation.
3. Make DM, Player, and Viewer layouts feel intentionally different.
4. Keep the Player view compact and easy.
5. Give the DM a command centre instead of one giant mixed panel.
6. Make the Viewer view clean, fun, and stream friendly.
7. Use drawers, modes, and compact cards to prevent clutter.
8. Keep diagnostics closed unless the DM opens Debug.
9. Support desktop first and tablet second.
10. Keep WebSocket behaviour and server authority unchanged.

## Visual direction

Use deep charcoal backgrounds, cyan/teal primary accents, antique gold secondary accents, warm parchment cards, dark glass panels, clear readable hierarchy, and subtle hover/drawer motion.

Cyan and gold should guide attention. They should not cover every element.

## Player layout plan

Default Player view should show:

- compact character HUD
- HP / temp HP / max HP
- AC
- passive perception
- initiative
- movement/speed
- conditions
- turn indicator when relevant
- compact Quick Actions entry
- Character, Spells, Inventory, Rest, Journal, Chat, and Roll buttons
- friendly reconnect, loading, and error status

Player panels open as drawers or modals:

- Quick Actions drawer
- character sheet modal/drawer
- inventory drawer
- spellbook drawer
- rest confirmation panel
- journal/handouts drawer
- dice roller flyout

Player rules:

- compact HUD by default
- no giant full-width panel unless opened
- no DM tools
- no editor controls
- no debug panel
- no admin controls in the live HUD

## DM command centre plan

The DM interface should be split into command centre modes:

1. Run Game
2. Combat
3. Map Build
4. NPC/Monster
5. Loot/Shop
6. Session Tools
7. Debug

Run Game prioritises current map, selected token, party summary, narration/chat, handouts, viewer powers, and compact save state.

Combat prioritises initiative order, current turn, actions used, movement used, HP, conditions, creature state, action roll, effect roll, save DC, and dice timing.

Map Build prioritises terrain, fog, walls, doors, reveal/hide mode, token layer, prop layer, lighting/weather, asset library, and map save/apply controls.

NPC/Monster prioritises bestiary search, spawn token, HP/AC/speed, visibility state, initiative modifier, conditions, notes, and creature actions.

Loot/Shop prioritises shops, loot containers, item library, grant/take item, gold, charges, and attunement.

Session Tools prioritises quests, handouts, journal, discoveries, narration, sound, viewer powers, polls, party messages, save, and autosave.

Debug owns stream readiness, payload warnings, reconnect warnings, WebSocket diagnostics, role visibility checks, and sync diagnostics.

DM rules:

- command centre modes are required
- no debug panel visible by default
- tools grouped by mode
- advanced tools tucked away
- live mode shows what the DM needs now

## Viewer overlay plan

Default Viewer view should show:

- watch map
- compact viewer powers panel
- power points/charges
- cooldowns
- target selection
- pending DM approval state
- approved/rejected feedback
- chat/polls/emotes
- reconnect/loading state

Viewer rules:

- minimal overlay
- powers panel compact
- approval/cooldown states obvious
- no DM clutter
- no Player sheet clutter
- no editor tools
- no debug tools

## Function coverage matrix

### Player

| Function | Access pattern |
|---|---|
| join | join flow |
| choose active character | setup prompt and selector |
| HP/temp HP/max HP | HUD and character drawer |
| AC | HUD and character drawer |
| passive perception | HUD or tooltip and character drawer |
| initiative | HUD/combat tracker |
| movement/speed | HUD/combat tracker |
| conditions | HUD chips and character drawer |
| quick actions | compact entry and Quick Actions drawer |
| weapon actions | action card with action roll / effect roll |
| spell actions | spell card with action bonus or save DC |
| spell save DC | spell card with save ability and DC |
| item-granted spells | item/spell card with source label |
| charges | action card chip and item details |
| inventory | compact button and drawer |
| equipment | inventory drawer |
| gold | inventory summary and drawer |
| rest | compact button and confirmation panel |
| notes | character/journal drawer |
| handouts | notification and handouts drawer |
| journal/quests | journal drawer |
| chat | tab/button |
| dice roller | roll button and flyout |
| token control | selected token HUD and token details |
| reconnect/loading/error states | friendly inline status |

### DM

| Function | Mode |
|---|---|
| Run Game | Run Game |
| Combat | Combat |
| Map Build | Map Build |
| NPC/Monster | NPC/Monster |
| Loot/Shop | Loot/Shop |
| Session Tools | Session Tools |
| Debug | Debug |
| tokens | Run Game / Combat / Map Build |
| fog | Map Build / Run Game |
| walls | Map Build |
| doors | Map Build |
| props | Map Build |
| lighting/weather | Map Build / Session Tools |
| bestiary | NPC/Monster |
| inventory control | Loot/Shop |
| shops | Loot/Shop |
| handouts | Session Tools |
| journal | Session Tools |
| narration | Session Tools |
| sound | Session Tools |
| viewer powers | Session Tools / Run Game |
| polls | Session Tools |
| save/autosave | compact status and Session Tools |
| diagnostics | Debug only |

### Viewer

| Function | Access pattern |
|---|---|
| watch map | main view |
| viewer powers | compact panel and drawer |
| power points/charges | compact chips |
| cooldowns | timer state |
| target selection | map/power panel |
| pending DM approval | status chip |
| chat/polls/emotes | compact panel |
| power feedback | toast/status |
| rejected/approved state | status chip/toast |
| reconnect/loading state | friendly inline status |

## Layout rules

Player: compact HUD by default, no giant full-width panel unless opened, Quick Actions drawer, character sheet modal/drawer, inventory drawer, spellbook drawer, rest confirmation panel, visible HP, AC, passive perception, and conditions.

DM: command centre modes, no debug panel visible by default, tools grouped by mode, advanced tools tucked away, and Debug owns readiness/payload/reconnect diagnostics.

Viewer: minimal overlay, powers panel compact, approval/cooldown states obvious, no DM/player clutter, and no debug tools.

## Mobile and tablet rules

Desktop is primary for DM. Tablet is acceptable for Player and Viewer with overlay drawers. Phone support should favour lightweight Player/Viewer actions only. Do not force the full DM command centre onto phone layouts.

## Accessibility rules

Every icon-only button needs a label or tooltip. Focus states must be visible. Colour cannot be the only status indicator. Loading, disabled, error, warning, success, cooldown, approved, and rejected states need readable text or icon support. Motion should respect reduced-motion preferences.

## Performance rules

Do not re-render huge panels on every WebSocket message. Keep compact summaries visible first and open full data only when a drawer opens. Do not make the Player HUD wider to solve complexity. Avoid adding more inline monolith UI to play.html unless there is no safer path.

## Stream readiness rules

Viewer screen must look clean on stream. DM debug/readiness panels must be closed by default. Friendly status messages should replace raw technical errors.

## Future UI implementation phases

1. Role blueprint and design tokens.
2. Player HUD plus Quick Actions drawer.
3. Viewer overlay plus viewer powers panel.
4. DM command centre shell.
5. Combat tracker upgrade.
6. Map/fog/tool UX cleanup.
7. Final branding pass.

Do not skip directly to a full redesign of every screen. Each phase must preserve role safety and existing function coverage.
