"""
Release notes for the automated release (.github/workflows/release.yml, Lab 8 bonus).

Reads the project version from pyproject.toml, checks that frontend/package.json, package-lock.json and the
latest CHANGELOG.md release have the same number, writes that release's CHANGELOG section to
release-notes.md in the repository root and prints the version (the workflow reads it from stdout).

    python scripts/release_notes.py

The script takes no arguments: every path it reads or writes is fixed inside the repository, so nothing
from the command line or the environment can point it at another file.
"""

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTES_FILE = "release-notes.md"
RELEASE_HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", re.MULTILINE)


class ReleaseError(Exception):
    """The version numbers do not match or the CHANGELOG has no section for the version."""


def project_version(root: Path = ROOT) -> str:
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def changelog_section(changelog: str, version: str) -> str:
    """Body of `## [version] - date` up to the next `## ` heading or the link list at the end."""
    match = next((m for m in RELEASE_HEADING.finditer(changelog) if m.group(1) == version), None)
    if match is None:
        raise ReleaseError(f"CHANGELOG.md has no '## [{version}] - YYYY-MM-DD' section")
    rest = changelog[match.end() :]
    end = re.search(r"^## |^\[[^\]]+\]: ", rest, re.MULTILINE)
    body = (rest[: end.start()] if end else rest).strip()
    if not body:
        raise ReleaseError(f"The CHANGELOG.md section of {version} is empty")
    return body


def check_versions(root: Path = ROOT) -> str:
    """The version, if every place agrees on it; otherwise ReleaseError."""
    version = project_version(root)
    package = json.loads((root / "frontend" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    found = {
        "frontend/package.json": package.get("version"),
        "frontend/package-lock.json": lock.get("version"),
    }
    releases = RELEASE_HEADING.findall((root / "CHANGELOG.md").read_text(encoding="utf-8"))
    found["CHANGELOG.md (latest release)"] = releases[0][0] if releases else None
    wrong = {place: value for place, value in found.items() if value != version}
    if wrong:
        details = ", ".join(f"{place}: {value}" for place, value in wrong.items())
        raise ReleaseError(f"pyproject.toml has {version}, but {details}")
    return version


def main(root: Path = ROOT) -> int:
    """Writes `root/release-notes.md` and prints the version; 1 with the reason on stderr on a mismatch."""
    try:
        version = check_versions(root)
        notes = changelog_section((root / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    except ReleaseError as error:
        print(f"Release check FAILED: {error}", file=sys.stderr)
        return 1
    (root / NOTES_FILE).write_text(notes + "\n", encoding="utf-8")
    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
