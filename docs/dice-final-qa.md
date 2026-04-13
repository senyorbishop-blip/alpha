# Dice final QA + polish pass

This pass focused on finishing the centralized dice system.

## Completed

- Per-die audit guard added at runtime in `DiceFactory.js`
- Shared roll visuals now have a user-facing on/off setting in the Dice Vault
- Authoritative result sync now prefers app-level bridge helpers instead of direct result filling in more places
- Large-pool performance budgets tightened across renderer, solver, damping, and settle timing
- Bounce / settle feel tuned toward a heavier tabletop presentation
- Dice audio layering reduced to avoid impact spam in large pools

## Manual verification checklist

- Dice Vault: switch between **3D Dice Tray** and **Result Only**
- Dice Vault: switch **Shared roll visuals** on and off
- Saves / Skills: local d20 checks use the same dice bridge
- Actions / Spells: local rolls use the same dice bridge
- Combat initiative: local initiative presentation uses the same dice bridge
- Server authoritative dice results route through app-level sync helpers
- Large dice pools: verify reduced hitching compared with earlier passes
- d4 / d10 / d100: verify face labels visually match expected die type conventions

## Automated sweep run for this pass

- `tests/test_dice_face_mapping.py`
- `tests/test_integration_chat_dice_tab.py`
- `tests/test_dice_final_bridge_and_settings.py`
