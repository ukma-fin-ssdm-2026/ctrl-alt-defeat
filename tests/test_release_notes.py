"""Automated release (Lab 8 bonus): notes from CHANGELOG.md and the release workflow."""

import json
from pathlib import Path

import pytest
import yaml

from scripts.release_notes import ReleaseError, changelog_section, check_versions, main

ROOT = Path(__file__).resolve().parents[1]

CHANGELOG = """# Changelog

## [Unreleased]

## [0.2.0] - 2026-11-13

### Added

- Каталог по 500 тайтлів.

## [0.1.1] - 2026-11-05

### Refactoring

- Логотип.

[0.2.0]: https://example.org/compare/v0.1.1...v0.2.0
[0.1.1]: https://example.org/compare/v0.1.0...v0.1.1
"""


def project(tmp_path, version="0.2.0", package_version=None, changelog=CHANGELOG):
    (tmp_path / "frontend").mkdir()
    (tmp_path / "pyproject.toml").write_text(f'[project]\nname = "x"\nversion = "{version}"\n', encoding="utf-8")
    package = {"version": package_version or version}
    (tmp_path / "frontend" / "package.json").write_text(json.dumps(package), encoding="utf-8")
    (tmp_path / "frontend" / "package-lock.json").write_text(json.dumps(package), encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    return tmp_path


def test_notes_are_the_changelog_section_of_the_version():
    assert changelog_section(CHANGELOG, "0.2.0") == "### Added\n\n- Каталог по 500 тайтлів."
    # The last section ends at the link list
    assert changelog_section(CHANGELOG, "0.1.1") == "### Refactoring\n\n- Логотип."
    with pytest.raises(ReleaseError):
        changelog_section(CHANGELOG, "9.9.9")


def test_release_stops_when_the_numbers_differ(tmp_path, capsys):
    root = project(tmp_path, package_version="0.1.1")
    with pytest.raises(ReleaseError, match="frontend/package.json: 0.1.1"):
        check_versions(root)
    assert main(["--root", str(root), "--notes-file", str(tmp_path / "notes.md")]) == 1
    assert "Release check FAILED" in capsys.readouterr().err
    assert not (tmp_path / "notes.md").exists()


def test_release_writes_the_notes_and_the_version_output(tmp_path):
    root = project(tmp_path)
    output = tmp_path / "github-output"
    notes = tmp_path / "notes.md"

    assert main(["--root", str(root), "--notes-file", str(notes), "--github-output", str(output)]) == 0
    assert notes.read_text(encoding="utf-8") == "### Added\n\n- Каталог по 500 тайтлів.\n"
    assert output.read_text(encoding="utf-8") == "version=0.2.0\n"


def test_the_repository_itself_is_ready_for_release(tmp_path):
    version = check_versions(ROOT)
    assert main(["--notes-file", str(tmp_path / "notes.md")]) == 0
    assert (tmp_path / "notes.md").read_text(encoding="utf-8").strip()
    assert version


def test_release_workflow_runs_after_a_version_change_on_main():
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    assert triggers["push"]["branches"] == ["main"]
    assert "pyproject.toml" in triggers["push"]["paths"]
    assert workflow["permissions"] == {"contents": "write"}
    steps = workflow["jobs"]["release"]["steps"]
    runs = "\n".join(step.get("run", "") for step in steps)
    assert "scripts/release_notes.py" in runs
    assert "gh release create" in runs and '--target "$GITHUB_SHA"' in runs
    # An existing tag is never moved
    assert "refs/tags/v$VERSION" in runs
