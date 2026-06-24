# Admin/Host QA Checklist (Founder Beta)

Use this before each beta wave and after each update.

## 1) Admin key and auth safety

- [ ] `DND_ADMIN_KEY` is explicitly set in `.env` or the deployment environment.
- [ ] `DND_JWT_SECRET` is set in `.env` or the deployment environment and is stable.
- [ ] `config.txt` is untracked and contains no secrets.
- [ ] Admin endpoints reject missing/invalid key.

## 2) Password reset operations

- [ ] Password reset request flow can be received/reviewed.
- [ ] Admin/manual reset flow completes successfully.
- [ ] User can log in after reset.

## 3) Backup and restore readiness

- [ ] Backup created before update or beta distribution.
- [ ] Backup contains DB + map/assets data paths required by deployment.
- [ ] Restore steps documented and quickly executable.

## 4) Update and rollback notes

- [ ] Current update procedure reviewed.
- [ ] Rollback snapshot/reference is available.
- [ ] Known risky migration notes are documented.

## 5) Known issues and communication

- [ ] Known beta limitations reviewed before invite send.
- [ ] Current workaround notes are ready for copy/paste support replies.
- [ ] Support contact path and response expectation are documented.
