"""The release number is the same in every place it is written (SemVer, Lab 8)."""

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def project_version() -> str:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def test_project_version_is_semver():
    assert SEMVER.match(project_version())


def test_frontend_package_has_the_same_version():
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))

    assert package["version"] == project_version()
    assert lock["version"] == lock["packages"][""]["version"] == project_version()


def test_latest_changelog_release_is_the_project_version():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    releases = re.findall(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", changelog, flags=re.MULTILINE)

    assert releases, "CHANGELOG.md has no '## [X.Y.Z] - YYYY-MM-DD' sections"
    assert releases[0][0] == project_version()
    assert f"[{project_version()}]: " in changelog, "missing compare link for the latest release"
