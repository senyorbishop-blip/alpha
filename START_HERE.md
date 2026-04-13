# START HERE — Founder Beta Handoff

Use this page when handing the app to a founder-beta DM/admin.

## 1) Install and launch

Follow [`docs/setup-and-install.md`](docs/setup-and-install.md).

## 2) Configure safely

- Copy [`.env.example`](.env.example) to `.env`
- Set `DND_ADMIN_KEY` and `DND_JWT_SECRET`
- Add optional provider keys only if needed

## 3) Learn role workflows

- DM workflow: [`docs/dm-guide.md`](docs/dm-guide.md)
- Player workflow: [`docs/player-guide.md`](docs/player-guide.md)
- Admin workflow: [`docs/admin-guide.md`](docs/admin-guide.md)

## 4) Choose access model

- Local/LAN or public self-host options: [`docs/hosting-access-guide.md`](docs/hosting-access-guide.md)

## 5) Run founder beta readiness pass

- Full pack index: [`docs/founder-beta/README.md`](docs/founder-beta/README.md)
- Master checklist: [`docs/founder-beta/master-checklist.md`](docs/founder-beta/master-checklist.md)
- GO/NO-GO gate: [`docs/founder-beta/release-go-no-go-checklist.md`](docs/founder-beta/release-go-no-go-checklist.md)
- Known beta limits: [`docs/known-issues-founder-beta.md`](docs/known-issues-founder-beta.md)

## 6) Before every update

Read and run backup/update steps in [`docs/backup-update-rollback.md`](docs/backup-update-rollback.md).

## 7) Operator smoke test before sharing with testers

Minimum manual check sequence after install/update:

1. Open `http://localhost:8000/health` and confirm `{"status":"ok"}`.
2. Open `http://localhost:8000/` and sign in as DM.
3. Start/enter a session, then join from a second tab as player.
4. Confirm join/rejoin, map visibility, token movement, and chat sync.
5. Confirm save/load and reconnect behavior once.

## Support boundaries (read before handoff)

- Founder beta is **not** public-launch production hardening.
- DM/prep workflows remain desktop-first.
- Mobile is currently best-effort for player participation, not full DM control.
- Public internet hosting quality depends on operator TLS/proxy/firewall setup.

## Release pointers

- Version: [`VERSION`](VERSION)
- Changelog: [`CHANGELOG.md`](CHANGELOG.md)
- Latest release notes: [`docs/releases/FOUNDER_BETA_v0.9.1-beta.md`](docs/releases/FOUNDER_BETA_v0.9.1-beta.md)
- Prior release notes: [`docs/releases/FOUNDER_BETA_v0.9.0-beta.md`](docs/releases/FOUNDER_BETA_v0.9.0-beta.md)
