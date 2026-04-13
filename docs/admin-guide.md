# Admin Guide (Founder Beta)

## Admin key (`DND_ADMIN_KEY`)

Admin endpoints use `X-Admin-Key`.
Set `DND_ADMIN_KEY` in `.env` (recommended) or `config.txt` before startup.

If no key is set, runtime auto-generates one at startup, which is unsafe for stable operations because it changes on restart.

## Password reset operations

### 1) Review reset requests backlog

```bash
curl -H "X-Admin-Key: <YOUR_ADMIN_KEY>" \
  "http://localhost:8000/admin/reset-requests?resolved=false"
```

### 2) Reset a user password manually

```bash
curl -X PATCH "http://localhost:8000/admin/reset-password" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: <YOUR_ADMIN_KEY>" \
  -d '{"username":"player_name","new_password":"NewStrongPass123"}'
```

### 3) Optional self-service reset flow (if using app flow)

- Player requests reset via app auth endpoint
- In development mode, reset token may be surfaced in API response
- In hosted mode, treat token handling as a controlled/manual support workflow

## Safe admin practices

- Rotate admin key when staff changes
- Use HTTPS when exposing admin operations outside LAN
- Never share admin key in chat logs/screenshots
- Keep `DND_JWT_SECRET` stable and private

## Backup and restore responsibilities

- Run scheduled backups of `DND_DATA_DIR`
- Validate restore on a non-production copy
- Keep at least one known-good rollback snapshot before updates

See `docs/backup-update-rollback.md` for procedures.
