from pathlib import Path


def test_start_here_release_links_exist_and_point_to_current_release():
    start = Path("START_HERE.md").read_text(encoding="utf-8")
    version = Path("VERSION").read_text(encoding="utf-8").strip()
    expected_release_doc = f"docs/releases/FOUNDER_BETA_{version}.md"

    assert "docs/setup-and-install.md" in start
    assert "docs/backup-update-rollback.md" in start
    assert expected_release_doc in start
    assert Path(expected_release_doc).exists(), f"Missing release notes file: {expected_release_doc}"


def test_operator_guidance_docs_exist_for_handoff_workflow():
    required = [
        "docs/setup-and-install.md",
        "docs/backup-update-rollback.md",
        "docs/known-issues-founder-beta.md",
        "docs/founder-beta/master-checklist.md",
        "docs/founder-beta/release-go-no-go-checklist.md",
    ]
    for rel in required:
        assert Path(rel).exists(), f"Expected handoff doc missing: {rel}"


def test_changelog_has_current_version_heading():
    version = Path("VERSION").read_text(encoding="utf-8").strip()
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{version}]" in changelog
