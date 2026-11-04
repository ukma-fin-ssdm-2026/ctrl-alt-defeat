"""
Check that requirements-lock.txt (hashed, used by the Docker image) pins exactly the same
versions as requirements.txt. Regenerate the lock after changing requirements.txt:

    uv pip compile requirements.txt --generate-hashes --python-version 3.11 \
        --python-platform linux --no-header -o requirements-lock.txt
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)")


def normalize(name: str) -> str:
    """PEP 503 name normalization: `pydantic_core` and `Pydantic-Core` are the same package."""
    return re.sub(r"[-_.]+", "-", name).lower()


def read_pins(path: Path) -> dict:
    pins = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = PIN.match(line.strip())
        if match:
            pins[normalize(match.group(1))] = match.group(2)
    return pins


def find_mismatches(requirements: dict, lock: dict) -> list:
    problems = []
    for name, version in sorted(requirements.items()):
        locked = lock.get(name)
        if locked is None:
            problems.append(f"{name}=={version} is missing from requirements-lock.txt")
        elif locked != version:
            problems.append(f"{name}: requirements.txt has {version}, requirements-lock.txt has {locked}")
    return problems


def main() -> int:
    problems = find_mismatches(read_pins(ROOT / "requirements.txt"), read_pins(ROOT / "requirements-lock.txt"))
    if problems:
        print("requirements-lock.txt is out of date:")
        for problem in problems:
            print(f"  - {problem}")
        print(__doc__)
        return 1
    print("requirements-lock.txt matches requirements.txt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
