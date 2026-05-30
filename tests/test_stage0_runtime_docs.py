from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OWNERSHIP_MAP = PROJECT_ROOT / "docs" / "runtime-ownership-map.md"
MANUAL_QA = PROJECT_ROOT / "docs" / "manual-qa-live-session.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_runtime_ownership_map_covers_stage0_systems():
    src = _read(OWNERSHIP_MAP)
    for system in (
        "System: DM live play",
        "System: Player live play",
        "System: Viewer/spectator entry",
        "System: Character creation/import",
        "System: Character sheet rendering",
        "System: Inventory system",
        "System: Viewer powers",
        "System: Combat handling",
        "System: WebSocket message handling",
        "System: CSS/layout for the play screen",
    ):
        assert system in src

    for required_field in (
        "Current main files:",
        "What it controls:",
        "Canonical / Legacy / Compatibility:",
        "Risks:",
        "Recommended future refactor path:",
    ):
        assert required_field in src


def test_manual_qa_live_session_covers_required_smoke_checks():
    src = _read(MANUAL_QA)
    for checklist_item in (
        "DM can create/open session",
        "Player can join",
        "Viewer can join",
        "DM can open map",
        "Token placement works",
        "Character sheet opens",
        "Inventory opens",
        "Notes field can be tested",
        "Viewer appears in roster",
        "Viewer power can be granted if supported",
        "Combat can start",
        "HP/AC display can be checked",
    ):
        assert checklist_item in src
