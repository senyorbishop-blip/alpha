# Backup, Update, and Rollback Guide

## Source-of-truth data location

Runtime data is stored under `DND_DATA_DIR` (or OS default path) and includes:

- `campaigns.db`
- `maps/`
- `assets/`
- `backups/` (startup DB backups)

Treat DB + maps + assets as one snapshot set when backing up or restoring.

## Pre-update backup (required)

### Linux/macOS

```bash
export DND_DATA_DIR="${DND_DATA_DIR:-$HOME/.casual-dnd}"
ts=$(date +%Y%m%d_%H%M%S)
mkdir -p "$DND_DATA_DIR/manual_backups"
tar -czf "$DND_DATA_DIR/manual_backups/dnd_backup_${ts}.tar.gz" -C "$DND_DATA_DIR" .
```

### Windows (PowerShell)

```powershell
$DataDir = if ($env:DND_DATA_DIR) { $env:DND_DATA_DIR } else { "$env:USERPROFILE\Documents\CasualDnDData" }
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = Join-Path $DataDir "manual_backups"
New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
$Dest = Join-Path $BackupRoot "dnd_backup_$Stamp.zip"
Compress-Archive -Path (Join-Path $DataDir "*") -DestinationPath $Dest -Force
```

## Safe update workflow

1. Stop server.
2. Create backup archive.
3. Pull or unpack new release.
4. Confirm `.env` and `config.txt` values are preserved.
5. Start server.
6. Run smoke checks:
   - `GET /health` returns `{"status":"ok"}`
   - DM login + session enter
   - player join/rejoin from second tab
   - map load + token move sync
   - save/load roundtrip

## Rollback workflow

If release is unhealthy:

1. Stop server.
2. Restore previous release code.
3. Restore latest known-good backup archive.
4. Restart server.
5. Verify session/map/chat/token integrity.

## Quick rollback validation checklist

- DM can sign in and open existing campaign data.
- Player can rejoin using expected flow.
- Map state and token placements match pre-update state.
- Fog/visibility state (where used) is intact.
- Chat/history and handouts still render without errors.

## Restore notes

- DB and map/assets should be restored together from same snapshot when possible.
- Avoid mixing DB from one date with map assets from another date.
- Keep at least one backup from the last known-good release before deleting old archives.

## Founder-beta recommendation

- Take backup before each founder test cycle and before each deployment update.
- Run one rollback drill on a non-production copy before inviting external testers.
