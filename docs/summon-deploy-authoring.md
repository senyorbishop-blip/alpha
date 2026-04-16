# Summon / Deploy Authoring Guide (Pass O)

This guide covers the **live summon/deploy content path** for new families.

## Pass O compatibility + migration notes

- Summon/deploy state normalization now writes `summons.deploySchemaVersion` and `summons.migration` markers.
- Legacy active shapes (`activeSummon`, `currentSummon`, `activeDeployment`, `activeEntities`, etc.) are upgraded into `activeSummons`.
- Unrecoverable legacy rows are moved into `quarantinedSummons` with a machine-readable `reason` instead of crashing load/restore.
- Normalization is idempotent for already-upgraded state.

Dry-run helper:

```bash
python tools/summon_deploy_compat_report.py --input /path/to/payload.json
```

The helper prints upgrade/quarantine counts without mutating stored data.

## Runtime source-of-truth path

1. `server/character/summon_catalog.py` — template registry, defaults, validation, and authoring helper blocks.
2. `server/character/summon_state.py` — feature/subclass unlock linkage into `summons.unlockedTemplates` + `selectedVariants`.
3. `server/character/resolver.py` — runtime action rows (`runtime.summonActions`) for UI and manager visibility.
4. `server/character/summon_runtime.py` — summon/deploy runtime payload creation + lifecycle behavior.
5. `server/handlers/summons.py` — live WS summon/deploy request handling.

## Authoring workflow for a new summon/deploy family

### 1) Add templates in `SUMMON_TEMPLATE_REGISTRY`

Add one or more templates with a shared `variantGroup`.

Required core fields:
- `id`
- `displayName`
- `summonCategory`
- `sourceClassId`
- `sourceFeatureId`
- `variantGroup`
- `actorType`
- `tokenName`
- `commandModel`
- `maxActive`
- `replaceOnResummon`

### 2) Use helper blocks to reduce mistakes

In `server/character/summon_catalog.py`:
- `_source_link(...)` for class/feature/subclass + spell linkage
- `_lifecycle(...)` for temporary duration/cleanup metadata
- `_control(...)` for control model metadata
- `_build_template(...)` to compose readable explicit rows

These helpers reduce duplication while leaving behavior explicit in data.

### 3) Wire unlock linkage

Update class/subclass feature definitions so unlock logic can map to templates:
- `grantsSummons`
- `summonTemplateIds`
- `variantGroup`
- optional choice mapping fields when variant choice is player-selected

Unlock synchronization is applied via `sync_summon_unlocks_from_features(...)` in `server/character/summon_state.py`.

### 4) Validate before runtime testing

Run:

```bash
python tools/validate_summon_content.py
```

Validation catches common authoring errors early:
- missing template/source linkage fields
- invalid entity kind or creature semantics
- invalid active-limit/replace semantics
- temporary lifecycle missing duration/cleanup metadata
- missing spell linkage requirements for spell-origin summons

### 5) Add or update tests

At minimum:
- registry validation tests
- helper/normalizer tests
- unlock-to-runtime extension-path coverage
- regression coverage for current live families (Beast Master / Pact Chain / Tinker / spell / non-creature)

## Creature vs non-creature expectations

- Non-creature deployables/effects should use `isCreature: false` and non-creature `entityKind` values (e.g. `device`, `effect`, `spell_effect`).
- Creature summons should keep `isCreature: true` with a creature-aligned `entityKind`.

## Temporary vs persistent lifecycle expectations

- Temporary summons should define positive `durationSeconds` and a non-empty `cleanupPolicy`.
- Persistent companions/deployables can use default dismiss/reconcile cleanup semantics.

## Live examples

- Ranger Beast Master: `ranger-primal-beast-*`
- Warlock Pact of the Chain: `warlock-chain-*`
- Tinker deployables: `tinker-mechanist-companion-frame`, `tinker-artillerist-arc-cannon`
- Spell summons/effects: `spell-conjure-fey-manifestation`, `spell-conjure-celestial-manifestation`
