"""
server/paths.py — stable runtime data locations shared across snapshots
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

APP_DIR_NAME = "CasualDnDData"
REPO_ROOT = Path(__file__).resolve().parent.parent


def _default_data_dir() -> Path:
    env = os.environ.get("DND_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    if os.name == "nt":
        docs = Path.home() / "Documents"
        return docs / APP_DIR_NAME
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg:
        return Path(xdg).expanduser() / "casual-dnd"
    return Path.home() / ".casual-dnd"


DATA_DIR = _default_data_dir()
DB_PATH = Path(os.environ.get("DND_DB_PATH", str(DATA_DIR / "campaigns.db"))).expanduser()
MAPS_DIR = DATA_DIR / "maps"
MAPS_IMPORT_DIR = MAPS_DIR / "import"
MAPS_BUILTIN_DIR = MAPS_DIR / "builtin"
MAPS_THUMBNAILS_DIR = MAPS_BUILTIN_DIR / "thumbnails"
MAPS_PREVIEWS_DIR = MAPS_BUILTIN_DIR / "previews"
MAPS_GENERATED_DIR = MAPS_DIR / "generated"
MAPS_MANIFESTS_DIR = MAPS_DIR / "manifests"
BACKUPS_DIR = DATA_DIR / "backups"
ASSETS_DIR = DATA_DIR / "assets"
USER_MANIFEST_PATH = ASSETS_DIR / "user_manifest.json"

_BACKUP_KEEP = 10  # number of startup backups to retain


def ensure_data_dirs() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_BUILTIN_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    MAPS_MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def migrate_legacy_data() -> dict:
    """Copy snapshot-local saves into the persistent data dir on first run."""
    ensure_data_dirs()
    report = {
        "db_copied": False,
        "maps_copied": 0,
        "legacy_db_found": False,
        "legacy_maps_found": False,
        "data_dir": str(DATA_DIR),
        "db_path": str(DB_PATH),
        "maps_dir": str(MAPS_DIR),
    }

    legacy_db = REPO_ROOT / "campaigns.db"
    if legacy_db.exists():
        report["legacy_db_found"] = True
    if not DB_PATH.exists() and legacy_db.exists():
        shutil.copy2(legacy_db, DB_PATH)
        for suffix in ("-shm", "-wal"):
            sidecar = legacy_db.with_name(legacy_db.name + suffix)
            if sidecar.exists():
                shutil.copy2(sidecar, DB_PATH.with_name(DB_PATH.name + suffix))
        report["db_copied"] = True

    legacy_maps = REPO_ROOT / "client" / "static" / "maps"
    if legacy_maps.exists():
        report["legacy_maps_found"] = True
        copied = 0
        for src in legacy_maps.iterdir():
            if not src.is_file():
                continue
            dest = MAPS_DIR / src.name
            if dest.exists():
                continue
            shutil.copy2(src, dest)
            copied += 1
        report["maps_copied"] = copied

    return report


def create_startup_backup() -> Optional[Path]:
    """Create a timestamped backup of the campaigns database at startup.

    Stores backups in BACKUPS_DIR and keeps only the most recent
    _BACKUP_KEEP copies to avoid unbounded disk usage.

    Returns the backup Path on success, or None if the database does not
    exist yet or the copy fails.
    """
    if not DB_PATH.exists():
        return None

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUPS_DIR / f"campaigns_{timestamp}.db"

    try:
        shutil.copy2(DB_PATH, backup_path)
        for suffix in ("-shm", "-wal"):
            sidecar = DB_PATH.with_name(DB_PATH.name + suffix)
            if sidecar.exists():
                shutil.copy2(sidecar, backup_path.with_name(backup_path.name + suffix))
    except Exception as e:
        logger.error("[BACKUP] Failed to create startup backup: %s", e)
        return None

    _prune_old_backups()
    return backup_path


def _prune_old_backups() -> None:
    """Remove oldest backups, keeping only the most recent _BACKUP_KEEP copies."""
    try:
        backups = sorted(BACKUPS_DIR.glob("campaigns_*.db"))
        for old in backups[:max(0, len(backups) - _BACKUP_KEEP)]:
            try:
                old.unlink()
                for suffix in ("-shm", "-wal"):
                    sidecar = old.with_name(old.name + suffix)
                    if sidecar.exists():
                        sidecar.unlink()
            except Exception:
                pass
    except Exception:
        pass
