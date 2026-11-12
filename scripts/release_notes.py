"""
Release notes for the automated release (.github/workflows/release.yml, Lab 8 bonus).

Reads the project version from pyproject.toml, checks that frontend/package.json, package-lock.json and the
latest CHANGELOG.md release have the same number, and writes that release's CHANGELOG section as the notes.

    python scripts/release_notes.py --notes-file release-notes.md [--github-output "$GITHUB_OUTPUT"]
"""

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--notes-file", required=True, type=Path)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        version = check_versions(args.root)
        notes = changelog_section((args.root / "CHANGELOG.md").read_text(encoding="utf-8"), version)
    except ReleaseError as error:
        print(f"Release check FAILED: {error}", file=sys.stderr)
        return 1
    args.notes_file.write_text(notes + "\n", encoding="utf-8")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"version={version}\n")
    print(f"Release v{version}: notes written to {args.notes_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
