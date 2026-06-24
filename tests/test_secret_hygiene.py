"""Repository-level guardrails for local config and auth secrets."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_AUTH_ASSIGNMENT = re.compile(
    r"^\s*(DND_JWT_SECRET|DND_ADMIN_KEY)\s*=\s*([A-Za-z0-9_./+=:-]{32,})\s*$"
)


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def test_config_txt_is_not_tracked():
    assert "config.txt" not in set(_tracked_files())


def test_gitignore_blocks_local_config_file():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert re.search(r"(?m)^config\.txt$", gitignore)


def test_tracked_files_do_not_contain_live_auth_secret_assignments():
    offenders: list[str] = []
    for rel_path in _tracked_files():
        path = ROOT / rel_path
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = LIVE_AUTH_ASSIGNMENT.match(line)
            if not match:
                continue
            value = match.group(2).strip()
            if value and not value.startswith("<"):
                offenders.append(f"{rel_path}:{line_number}")
    assert offenders == []
