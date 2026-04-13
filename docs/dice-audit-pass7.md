# Dice audit pass 7

## Fixed
- D4 visual/read mismatch: face values now match the physical upward-point convention.
- Authoritative sync now autostarts the shared visual path through `AppDice.syncResult` instead of mixing direct preview calls.
- Large dice pools now use tighter renderer and physics budgets.

## Tuned
- More top-down tray framing.
- Faster settling with lower restitution and pool-size-aware damping.
- Shorter worst-case roll lifetime to avoid long hangs on large pools.
