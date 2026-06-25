# Casual D&D / Alpha — Map-First UI Blueprint

## Purpose

This blueprint starts the next UI direction for Casual D&D / Alpha. The new target is map-first, D&D themed, easy to read, and role focused.

The approved visual direction is:

- huge map as the main stage
- dark fantasy surface
- cyan magic highlights
- antique gold accents
- parchment notes where story text matters
- left mode rail
- right context panel
- bottom quick tool strip
- debug closed by default

This is a foundation document only. Do not rebuild every screen in this phase. Do not change gameplay behaviour, WebSocket behaviour, token authority, combat rules, visibility rules, inventory logic, or viewer power rules.

## Main principle

Map first. Tools appear only when the selected mode needs them.

The map should always feel like the table. UI should feel like tools around the table, not walls blocking the table.

## Global layout

The live play screen should use four stable regions:

1. Top session bar
2. Left mode rail
3. Centre map stage
4. Right context panel
5. Bottom quick strip

The centre map gets the most space. Side panels must be compact, collapsible, or mode based.

## Top session bar

Purpose: session status only.

Keep visible:

- campaign/session name
- current map or scene name
- save/autosave state
- live sync state
- invite/display controls when relevant
- current role indicator

Do not put large diagnostics here. Debug belongs in Debug mode.

## Left mode rail

The left rail is the DM's mode selector. It should be narrow and readable.

DM mode buttons:

- Run Game
- Combat
- Map Build
- NPC / Monster
- Loot / Shop
- Session Tools
- Viewer Powers
- Debug

The active mode controls what appears in the right context panel. The rail should not open giant panels by itself.

## Centre map stage

The map is the main UI.

Map stage must support:

- grid
- tokens
- token labels
- HP/AC badges
- fog
- walls
- doors
- props
- lighting/weather effects
- ruler/measure tools
- selected token affordances
- drag/move actions
- click/tap targeting

Map should remain large for DM, Player, and Viewer.

## Right context panel

The right panel changes by mode. It should be useful, not a dumping ground.

### Run Game context

Show:

- selected token summary
- party overview
- current scene notes
- handout shortcut
- journal shortcut
- narration shortcut
- viewer power shortcut
- compact save state

### Combat context

Show:

- current turn
- initiative order
- action usage
- movement usage
- HP summary
- conditions
- quick action cards
- end turn / next turn controls
- roll helpers

### Map Build context

Show:

- terrain tools
- fog brush
- wall tool
- door tool
- reveal/hide controls
- token layer
- prop layer
- lighting/weather layer
- asset library shortcut
- map save/apply controls

### NPC / Monster context

Show:

- bestiary search
- spawn token
- HP/AC/speed editor
- visibility state
- initiative modifier
- conditions
- notes
- creature quick actions

### Loot / Shop context

Show:

- item search
- loot containers
- corpse loot
- shop setup
- grant item
- grant gold
- charges
- attunement state

### Session Tools context

Show:

- quests
- handouts
- journal
- discoveries
- narration
- sound
- polls
- party messages
- autosave/save tools

### Viewer Powers context

Show:

- connected viewers
- viewer power grants
- pending approvals
- cooldowns
- target selection
- rejected/approved feedback

### Debug context

Show only when Debug mode is selected:

- stream readiness
- payload warnings
- reconnect warnings
- WebSocket diagnostics
- sync diagnostics
- visibility checks

Debug must be closed by default.

## Bottom quick strip

The bottom strip is for fast actions that should not take over the screen.

Examples:

- Select
- Move
- Measure
- Draw
- Light
- Notes
- More

The bottom strip should stay low profile and must not hide important map areas.

## Player layout

Player view also stays map-first.

Default Player view:

- map large
- compact character HUD
- HP / temp HP / max HP
- AC
- passive perception
- movement/speed
- initiative when relevant
- conditions
- compact Quick Actions entry
- bottom quick actions for Character, Spells, Inventory, Rest, Roll
- friendly loading/reconnect/error status

Player detailed panels open as drawers or modals:

- Quick Actions drawer
- character sheet drawer
- inventory drawer
- spellbook drawer
- rest confirmation panel
- journal/handouts drawer
- dice roller flyout

Player rules:

- compact HUD by default
- no giant full width panel unless opened
- no DM mode rail
- no map editor controls
- no debug panel

## Viewer layout

Viewer view stays map-first and stream friendly.

Default Viewer view:

- map large
- compact viewer powers panel
- power points/charges
- cooldowns
- target selection
- pending approval state
- approved/rejected feedback
- compact chat/polls/emotes
- friendly loading/reconnect status

Viewer rules:

- minimal overlay
- no DM tools
- no player sheet clutter
- no map editor controls
- no debug panel

## Function coverage matrix

### Player

| Function | Access pattern |
|---|---|
| join | join flow |
| choose active character | setup prompt and selector |
| HP/temp HP/max HP | compact HUD and character drawer |
| AC | compact HUD and character drawer |
| passive perception | compact HUD or tooltip |
| initiative | combat HUD |
| movement/speed | HUD and combat drawer |
| conditions | HUD chips and character drawer |
| quick actions | compact entry and drawer |
| weapon actions | action card with attack/effect controls |
| spell actions | spell card with attack/save/cast controls |
| spell save DC | spell card detail |
| item-granted spells | item action card |
| charges | chip and item detail |
| inventory | drawer |
| equipment | inventory drawer |
| gold | inventory summary |
| rest | confirmation panel |
| notes | drawer |
| handouts | drawer |
| journal/quests | drawer |
| chat | compact panel |
| dice roller | flyout |
| token control | selected token HUD |
| reconnect/loading/error states | friendly status |

### DM

| Function | Mode |
|---|---|
| Run Game | Run Game |
| Combat | Combat |
| Map Build | Map Build |
| NPC/Monster | NPC/Monster |
| Loot/Shop | Loot/Shop |
| Session Tools | Session Tools |
| Viewer Powers | Viewer Powers |
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
| polls | Session Tools |
| save/autosave | top bar and Session Tools |
| diagnostics | Debug only |

### Viewer

| Function | Access pattern |
|---|---|
| watch map | main stage |
| viewer powers | compact panel and drawer |
| power points/charges | compact chips |
| cooldowns | timer state |
| target selection | map or power panel |
| pending approval | status chip |
| chat/polls/emotes | compact panel |
| power feedback | toast/status |
| rejected/approved state | status chip |
| reconnect/loading state | friendly status |

## Clutter rules

- The map must remain the largest element.
- The right panel changes by mode.
- The left rail stays narrow.
- Debug is closed by default.
- Detailed tools use drawers or modals.
- Player view stays compact by default.
- Viewer view stays minimal by default.
- Do not add another always-open full-height panel unless it replaces an existing panel.

## Accessibility rules

- Icon-only controls need labels or tooltips.
- Focus states must be visible.
- Colour cannot be the only status indicator.
- Loading, disabled, error, warning, success, cooldown, approved, and rejected states need readable text or icon support.
- Motion should respect reduced-motion preferences.

## Performance rules

- Do not re-render huge panels on every WebSocket message.
- Use summaries first and detailed drawers second.
- Keep debug data out of normal live panels.
- Avoid adding more inline UI into play.html unless there is no safer route.

## Implementation phases

1. Map-first blueprint and tokens.
2. DM map-first shell with left mode rail and right context panel.
3. Player compact HUD and drawer actions.
4. Viewer compact overlay and powers panel.
5. Combat context panel upgrade.
6. Map/fog/tool UX cleanup.
7. Final dark fantasy branding pass.
