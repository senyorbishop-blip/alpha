# Founder Beta Support + Triage Flow

## 1) Intake channel

Pick one primary intake path and keep it consistent:

- GitHub Issues (recommended if testers are technical), or
- Shared form/doc + internal issue tracker.

Always provide:
- bug template
- feedback template
- expected response window (example: within 24 hours weekdays)

## 2) First response checklist (ask these first)

1. Role used (DM/player/viewer/admin)
2. Device + browser + desktop/phone
3. Deployment context (localhost/LAN/public)
4. Exact steps and expected vs actual
5. Screenshot/video/log snippet
6. Whether it blocks play right now

## 3) Reproduction workflow

1. Reproduce in same role and browser first.
2. Reproduce in second browser/device if sync/visibility issue.
3. Validate in a clean/new session if state-related.
4. Capture severity and probable subsystem (auth/map/combat/fog/chat/save/admin).

## 4) Labeling workflow

Use at least these labels:

- `role:dm`, `role:player`, `role:viewer`, `role:admin`
- `sev:critical|high|medium|low`
- `area:auth|session|map|fog|combat|chat|audio|save-load|ui-mobile|admin`
- `status:needs-repro|confirmed|workaround|fixed|deferred`

## 5) Patch now vs batch later

Patch immediately when:
- Critical issue confirmed
- High issue has no acceptable workaround
- Data-loss/security/admin-recovery risk present

Batch for scheduled update when:
- Medium/Low issue has workaround
- UI polish issues do not block planned playtest goals

## 6) Communication to testers

For confirmed issues, send:
- short plain-language summary
- current status (investigating/fix planned/fixed)
- temporary workaround (if any)
- target fix window (or explicitly deferred)

Maintain a single known-issues page and keep dates/status current.
