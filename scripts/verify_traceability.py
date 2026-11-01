#!/usr/bin/env python3
"""
Automated RTM ↔ Test Traceability Verification Script.

Parses docs/requirements/rtm.md for test case IDs (T-NNN) and scans
test files for '# Trace: T-NNN' comments. Fails (exit 1) if:
  - A required T-ID from RTM has no matching test in code
  - A test references a T-ID not found in RTM

Usage:
    python3 scripts/verify_traceability.py

Exit codes:
    0 — all traceability checks passed
    1 — gaps or orphan references found
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# User stories explicitly excluded from test scope (documented in test-plan.md)
EXCLUDED_US = {"US-005"}

# T-IDs marked as [xfail: заплановано] in test-plan.md
XFAIL_TIDS = {
    "T-006",
    "T-023",
    "T-024",
    "T-025",
    "T-035",
    "T-036",
}


def parse_rtm():
    """Extract T-IDs and their parent US from rtm.md."""
    rtm_path = PROJECT_ROOT / "docs" / "requirements" / "rtm.md"
    content = rtm_path.read_text(encoding="utf-8")

    tid_to_us = {}
    current_us = None
    for line in content.splitlines():
        if "|" not in line:
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 3:
            continue
        # Detect US-NNN in the first data column
        us_match = re.search(r"US-\d+", cols[1])
        if us_match:
            current_us = us_match.group()
        elif cols[1].strip() == "-":
            current_us = None
        # Collect every T-NNN in the row
        for tid_match in re.finditer(r"T-(\d+)", line):
            tid = f"T-{tid_match.group(1)}"
            tid_to_us[tid] = current_us

    return tid_to_us


def scan_tests():
    """Scan test files for '# Trace: T-NNN' comments."""
    tests_dir = PROJECT_ROOT / "tests"
    traced = set()

    for py_file in tests_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for match in re.finditer(r"#\s*Trace:\s*(T-\d+)", content):
            traced.add(match.group(1))

    # Also scan .js files for T-NNN references (k6 performance tests)
    for js_file in tests_dir.rglob("*.js"):
        content = js_file.read_text(encoding="utf-8")
        for match in re.finditer(r"\bT-(\d+)\b", content):
            traced.add(f"T-{match.group(1)}")

    return traced


def main():
    rtm_tids = parse_rtm()
    test_tids = scan_tests()

    all_tids = set(rtm_tids.keys())

    # T-IDs belonging to excluded user stories
    excluded = {tid for tid, us in rtm_tids.items() if us in EXCLUDED_US}
    # T-IDs without a parent US (e.g. FR-012 TMDB)
    no_us = {tid for tid, us in rtm_tids.items() if us is None}

    # Required coverage = all - excluded - no_us - xfail
    required = all_tids - excluded - no_us - XFAIL_TIDS

    # Gaps: required T-IDs not covered by any test
    gaps = required - test_tids

    # Orphans: T-IDs referenced in tests but absent from RTM
    orphans = test_tids - all_tids

    # Report
    print("=" * 60)
    print("RTM <-> Test Traceability Report")
    print("=" * 60)
    print(f"  Total T-IDs in RTM:      {len(all_tids)}")
    print(f"  Excluded (out of scope): {len(excluded | no_us)}")
    print(f"  Planned [xfail]:         {len(XFAIL_TIDS)}")
    print(f"  Required coverage:       {len(required)}")
    print(f"  Covered by tests:        {len(test_tids & required)}")
    print()

    ok = True

    if gaps:
        print(f"FAIL: {len(gaps)} required T-ID(s) have no tests:")
        for tid in sorted(gaps):
            us = rtm_tids.get(tid, "?")
            print(f"   {tid} ({us})")
        ok = False
    else:
        print("PASS: All required T-IDs are covered by tests.")

    if orphans:
        print(f"FAIL: {len(orphans)} test trace(s) reference T-IDs not in RTM:")
        for tid in sorted(orphans):
            print(f"   {tid}")
        ok = False
    else:
        print("PASS: All test traces reference valid RTM T-IDs.")

    print()
    if ok:
        print("Traceability check PASSED.")
    else:
        print("Traceability check FAILED.")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
