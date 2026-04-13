# Stage 9 — Commercial Layer Readiness (Billing/Plans/Support/Legal/Release Ops)

Date: 2026-03-27

## Scope and runtime boundaries used

This stage intentionally avoids gameplay rewrites. The implementation introduces account-level commercial seams only:

- plan/entitlement resolution at the account layer
- admin entitlement override endpoint
- deployment/support/legal metadata plumbing via config

No gameplay WebSocket handlers or `client/templates/play.html` gameplay runtime behavior were modified.

## 1) Commercial readiness findings

### Product model clarity

Current repo reality:
- The codebase is currently optimized for **self-host** by default.
- The existing `LICENSE.txt` explicitly prohibits operating a paid hosted service without separate permission.

Practical model recommendation for this repo state:
- **Primary now:** self-host licensed
- **Future capable:** hybrid (hosted SaaS + self-host licensing) once billing/legal assets are finalized

### Entitlement state before this stage

Before this stage, there was no structured account-level entitlement table or formal plan resolver. Any commercial gating would have been ad hoc.

### Support/admin visibility before this stage

Admin already had a host-key pattern (`/admin/*`) for sensitive operations (e.g., password reset), but no commercial/admin path for plan assignment or override management.

### Legal/release readiness gaps before this stage

- License existed, but there was no explicit runtime/legal metadata surface (terms/privacy/DPA URLs) in account-facing API context.
- Release operations existed (tests/workflow), but no commercial ops checklist/runbook anchor.

## 2) Minimal implementation plan (executed)

1. Add a small **commercial service seam** (`server/commercial/service.py`) for plan catalog + entitlement resolution.
2. Add a **persistence table** for per-user entitlement overrides (`user_entitlements`) in auth DB init.
3. Add account/admin APIs:
   - `GET /api/account/commercial-context`
   - `PATCH /admin/commercial/entitlements/{user_id}`
4. Extend `AppConfig` and `.env.example` with commercial/support/legal metadata fields.
5. Add tests for config parsing, entitlement resolution, and entitlement persistence.
6. Add this stage doc so future work can layer billing providers without coupling into gameplay systems.

## 3) Integration points now available

### Subscription status

`user_entitlements.subscription_status` (e.g., `active`, `trialing`, `canceled`, `inactive`) is now the canonical account-level field.

### Plan caps + feature gating

Plan baselines live in `server/commercial/service.py` (`community`, `pro`, `studio`) with:
- `caps`
- `features`
- `support_tier`

Per-user overrides are supported via `feature_overrides` JSON.

### Support/admin visibility

Admin can set/update entitlements through:
- `PATCH /admin/commercial/entitlements/{user_id}` (host key protected)

Authenticated users can inspect resolved context through:
- `GET /api/account/commercial-context`

### Legal metadata integration

Config now supports optional URLs for:
- terms
- privacy
- DPA

These are included in the commercial context payload for consistent client/admin surfaces.

## 4) What still remains for full sellability

1. Billing provider adapter (Stripe/Paddle/etc.)
2. Webhook ingestion + signature verification + idempotency store
3. Customer portal/session endpoint integration
4. Invoices/tax handling strategy by region
5. Published Terms/Privacy/Data Processing docs at stable URLs
6. Support SLAs + escalation process + incident runbook
7. Release/versioning policy (semantic versioning + changelog discipline)

## 5) Non-goals explicitly preserved

- No feature gates were injected into combat/tokens/map/chat handlers.
- No change to play-page role behavior (DM/player/viewer).
- No modifications to WebSocket dispatch contract in `server/handlers/__init__.py`.

This keeps current gameplay stable while creating the seam needed for a future paid offering.
