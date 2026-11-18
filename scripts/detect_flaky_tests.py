import xml.etree.ElementTree as ET
from pathlib import Path

RESULTS_DIR = Path("flaky-results")
RUNS = 5


def read_results(path):
    root = ET.parse(path).getroot()
    results = {}

    for test in root.iter("testcase"):
        name = f"{test.get('classname')}::{test.get('name')}"

        if test.find("failure") is not None:
            status = "failed"
        elif test.find("error") is not None:
            status = "error"
        elif test.find("skipped") is not None:
            status = "skipped"
        else:
            status = "passed"

        results[name] = status

    return results


def main():
    runs = []

    for i in range(1, RUNS + 1):
        path = RESULTS_DIR / f"run-{i}.xml"

        if not path.exists():
            raise FileNotFoundError(f"Missing results: {path}")

        runs.append(read_results(path))

    all_tests = set().union(*(run.keys() for run in runs))
    flaky = []

    for test in sorted(all_tests):
        statuses = [run.get(test, "missing") for run in runs]

        if len(set(statuses)) > 1:
            flaky.append((test, statuses))

    report = [
        "# Flaky Tests Report",
        "",
        f"Runs: {RUNS}",
        f"Total tests: {len(all_tests)}",
        f"Flaky tests: {len(flaky)}",
        "",
    ]

    if flaky:
        for test, statuses in flaky:
            report.append(f"- {test}: {', '.join(statuses)}")
    else:
        report.append("No flaky tests detected.")

    output = RESULTS_DIR / "report.md"
    output.write_text("\n".join(report), encoding="utf-8")

    print("\n".join(report))

    if flaky:
        raise SystemExit(1)


if __name__ == "__main__":
    main()