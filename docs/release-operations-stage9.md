# Release Operations Baseline (Stage 9)

Date: 2026-03-30

## Purpose

Define a minimum repeatable release workflow for founder-beta delivery without changing gameplay/runtime ownership.

## Pre-release checklist (minimum)

1. Run CI-equivalent tests:
   - `python -m pytest tests/ -v --tb=short`
2. Validate account/auth and entitlement paths:
   - register/login/logout
   - `GET /api/account/commercial-context`
   - admin entitlement patch endpoint with host key
3. Validate core founder-beta workflows:
   - app boot + `/health`
   - DM session entry
   - player join/rejoin
   - map load + token sync
   - save/load roundtrip
4. Verify legal/support metadata env vars are configured for hosted deployments:
   - `SUPPORT_CONTACT_EMAIL`
   - `LEGAL_TERMS_URL`
   - `LEGAL_PRIVACY_URL`
5. Confirm deployment model env var is explicit:
   - `COMMERCIAL_DEPLOYMENT_MODEL=self_host|hosted_saas|hybrid`
6. Confirm backup + rollback docs were followed for this build:
   - `docs/backup-update-rollback.md`

## Release notes template (minimum)

- Version/date
- Runtime-impact summary
- Schema/data changes
- Backward compatibility notes
- Rollback notes
- Known issues and support boundaries

## Operational ownership notes

- Gameplay runtime authority remains `client/templates/play.html` + existing server handlers.
- Commercial/account behavior is isolated to:
  - `server/commercial/service.py`
  - `server/commercial/routes.py`
  - `server/auth/models.py` (`user_entitlements` table)

## Practical diagnostics guidance

Use existing lightweight checks before triaging deeper incidents:

- `GET /health` for server-alive status
- startup logs for data path + backup creation messages
- auth/login and session-join smoke flow in two tabs

## Immediate follow-up recommendations

1. Keep release docs synchronized (`VERSION`, `CHANGELOG.md`, release notes file).
2. Run a rollback drill on a copy of real data once per release cycle.
3. Continue adding focused critical-path regression tests before broad feature tests.
