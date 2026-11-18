"""
DORA metrics from the GitHub Actions history (Lab 10 bonus "automatic calculation of the metrics").

Definitions of the lab (docs/ci-cd/dora-summary.md, section 1):

- deployment: a green run of the "CI Test" workflow (.github/workflows/ci.yml) after a push to main;
- failed change: a red run of that workflow on main (failure, timed out, startup failure); cancelled and
  skipped runs are not finished changes and are only counted;
- change fail rate: red runs / (green + red runs) x 100%;
- recovery time: from the end of the first red run of a series to the end of the next green run;
- change lead time: from the first commit of the merged pull request (its author date; for a commit pushed
  straight to main, the commit itself) to the end of the first green run on main that contains the commit;
- queue: from the creation of the run to the start of its first job; execution: from the start of the first
  job to the end of the last one. Both are parts of the lead time and are reported separately.

    GH_TOKEN=$(gh auth token) python scripts/dora_metrics.py --since 2026-11-01 --until 2026-11-13

The period is given in UTC days, both ends included. The script only reads the API (GH_TOKEN or GITHUB_TOKEN
with read access to the repository) and writes two fixed files inside the repository:
docs/ci-cd/dora-auto.md (the report) and docs/ci-cd/evidence/dora-auto.json (every run and change it used).
"""

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
REPORT_FILE = ROOT / "docs" / "ci-cd" / "dora-auto.md"
EVIDENCE_FILE = ROOT / "docs" / "ci-cd" / "evidence" / "dora-auto.json"

REPOSITORY = "ukma-fin-ssdm-2026/ctrl-alt-defeat"
WORKFLOW_FILE = "ci.yml"
WORKFLOW_NAME = "CI Test"
BRANCH = "main"
API = "https://api.github.com"
RETRIES = 4

GREEN = {"success"}
RED = {"failure", "timed_out", "startup_failure"}

# DORA 2025 (State of AI-assisted Software Development, fig. 11-14): level -> share of respondents
# with the same or a better result. Thresholds are upper bounds of the level.
HOUR, DAY, WEEK, MONTH = 60.0, 24 * 60.0, 7 * 24 * 60.0, 30 * 24 * 60.0
FREQUENCY_LEVELS = [  # deployments per week, lower bound of the level
    (7 * 3, "на вимогу (кілька разів на день)", 16.2),
    (7, "від щогодини до щодня", 22.7),
    (1, "від щодня до щотижня", 44.6),
    (0.25, "від щотижня до щомісяця", 76.1),
    (0, "рідше", 100.0),
]
LEAD_TIME_LEVELS = [  # minutes, upper bound
    (HOUR, "менше години", 9.4),
    (DAY, "менше доби", 24.4),
    (WEEK, "від доби до тижня", 56.4),
    (MONTH, "від тижня до місяця", 84.7),
    (float("inf"), "понад місяць", 100.0),
]
FAIL_RATE_LEVELS = [  # percent, upper bound
    (2, "0-2%", 8.5),
    (4, "2-4%", 16.7),
    (8, "4-8%", 36.2),
    (16, "8-16%", 62.2),
    (32, "16-32%", 81.6),
    (64, "32-64%", 94.1),
    (100, "понад 64%", 100.0),
]
RECOVERY_LEVELS = [  # minutes, upper bound
    (HOUR, "менше години", 21.3),
    (DAY, "менше доби", 56.5),
    (WEEK, "від доби до тижня", 84.5),
    (MONTH, "від тижня до місяця", 93.9),
    (float("inf"), "понад місяць", 100.0),
]


class MetricsError(Exception):
    """No token, a bad period or an API answer the script cannot use."""


@dataclass
class Run:
    run_id: int
    sha: str
    conclusion: str
    attempt: int
    created: datetime
    started: Optional[datetime] = None  # first job
    completed: Optional[datetime] = None  # last job
    url: str = ""

    @property
    def queue_min(self) -> float:
        return minutes(self.created, self.started) if self.started else 0.0

    @property
    def exec_min(self) -> float:
        return minutes(self.started, self.completed) if self.started and self.completed else 0.0

    @property
    def green(self) -> bool:
        return self.conclusion in GREEN

    @property
    def red(self) -> bool:
        return self.conclusion in RED


@dataclass
class Change:
    """One merged pull request (or a commit pushed straight to main) delivered by a green run."""

    label: str  # "#123" or the short sha
    started: datetime  # first commit of the PR
    run_id: int
    delivered: datetime
    queue_min: float
    exec_min: float

    @property
    def lead_min(self) -> float:
        return minutes(self.started, self.delivered)


@dataclass
class Incident:
    red_run_id: int
    failed: datetime
    green_run_id: Optional[int] = None
    recovered: Optional[datetime] = None

    @property
    def recovery_min(self) -> Optional[float]:
        return minutes(self.failed, self.recovered) if self.recovered else None


@dataclass
class Report:
    since: date
    until: date
    runs: List[Run] = field(default_factory=list)
    changes: List[Change] = field(default_factory=list)
    incidents: List[Incident] = field(default_factory=list)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def minutes(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 60


def level(value: float, levels: Iterable[Tuple[float, str, float]], at_least: bool = False) -> Tuple[str, float]:
    """The DORA 2025 level of a value and the share of respondents with the same or a better result."""
    for bound, name, share in levels:
        if (value >= bound) if at_least else (value <= bound):
            return name, share
    raise MetricsError(f"No level for {value}")


# --- GitHub API -------------------------------------------------------------------------------------------


def github_token() -> str:
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise MetricsError("Set GH_TOKEN, for example: GH_TOKEN=$(gh auth token) python scripts/dora_metrics.py ...")
    return token


def make_api_get(token: str) -> Callable[[str, Dict[str, str]], object]:
    def get(path: str, params: Dict[str, str]) -> object:
        url = f"{API}{path}?{urllib.parse.urlencode(params)}" if params else f"{API}{path}"
        request = urllib.request.Request(  # noqa: S310 - fixed https://api.github.com address
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        for attempt in range(1, RETRIES + 1):
            try:
                # Only the fixed https://api.github.com address is opened (no file:// or other schemes)
                with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310  # nosec B310
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                if error.code < 500 or attempt == RETRIES:
                    raise MetricsError(f"GitHub API {error.code} for {path}") from error
            except urllib.error.URLError as error:
                if attempt == RETRIES:
                    raise MetricsError(f"GitHub API is not reachable: {error.reason}") from error
            time.sleep(2 * attempt)  # a short pause before the next try (502/503 from the API happen)
        raise MetricsError(f"GitHub API failed for {path}")

    return get


class History:
    """Reads what the metrics need from the API, each object once."""

    def __init__(self, get: Callable[[str, Dict[str, str]], object]):
        self.get = get
        self.base = f"/repos/{REPOSITORY}"
        self._pulls: Dict[str, Optional[dict]] = {}
        self._first_commit: Dict[int, datetime] = {}

    def runs(self, created: str, extra: Optional[Dict[str, str]] = None, limit: int = 0) -> List[dict]:
        found: List[dict] = []
        page = 1
        while True:
            params = {"branch": BRANCH, "event": "push", "created": created, "per_page": "100", "page": str(page)}
            params.update(extra or {})
            data = self.get(f"{self.base}/actions/workflows/{WORKFLOW_FILE}/runs", params)
            batch = data.get("workflow_runs", [])
            found.extend(batch)
            if limit and len(found) >= limit:
                return found[:limit]
            if len(batch) < 100:
                return found
            page += 1

    def with_jobs(self, raw: dict) -> Run:
        run = Run(
            run_id=raw["id"],
            sha=raw["head_sha"],
            conclusion=raw.get("conclusion") or raw.get("status") or "",
            attempt=raw.get("run_attempt", 1),
            created=parse_time(raw["created_at"]),
            url=raw.get("html_url", ""),
        )
        jobs = self.get(f"{self.base}/actions/runs/{run.run_id}/jobs", {"per_page": "100"}).get("jobs", [])
        starts = [parse_time(job["started_at"]) for job in jobs if job.get("started_at")]
        ends = [parse_time(job["completed_at"]) for job in jobs if job.get("completed_at")]
        run.started = min(starts) if starts else None
        run.completed = max(ends) if ends else parse_time(raw["updated_at"])
        return run

    def commits_between(self, base_sha: Optional[str], head_sha: str) -> List[dict]:
        if base_sha is None:
            return [self.get(f"{self.base}/commits/{head_sha}", {})]
        data = self.get(f"{self.base}/compare/{base_sha}...{head_sha}", {"per_page": "250"})
        return data.get("commits", [])

    def pull_of(self, sha: str) -> Optional[dict]:
        if sha not in self._pulls:
            pulls = self.get(f"{self.base}/commits/{sha}/pulls", {})
            merged = [pull for pull in pulls if pull.get("merged_at") and pull["base"]["ref"] == BRANCH]
            self._pulls[sha] = merged[0] if merged else None
        return self._pulls[sha]

    def first_commit_of(self, number: int) -> datetime:
        if number not in self._first_commit:
            commits = self.get(f"{self.base}/pulls/{number}/commits", {"per_page": "100"})
            self._first_commit[number] = min(parse_time(item["commit"]["author"]["date"]) for item in commits)
        return self._first_commit[number]


# --- metrics ----------------------------------------------------------------------------------------------


def collect(history: History, since: date, until: date) -> Report:
    period = f"{since.isoformat()}..{until.isoformat()}"
    report = Report(since=since, until=until)
    raw_runs = sorted(history.runs(period), key=lambda raw: raw["created_at"])
    report.runs = [history.with_jobs(raw) for raw in raw_runs if raw.get("status") == "completed"]

    # The last green run before the period: commits after it are delivered by the first green run in it
    before = history.runs(f"<{since.isoformat()}", {"status": "success"}, limit=1)
    previous_green = before[0]["head_sha"] if before else None
    report.changes = changes_of(history, report.runs, previous_green)
    report.incidents = incidents_of(report.runs)
    return report


def changes_of(history: History, runs: List[Run], previous_green: Optional[str]) -> List[Change]:
    changes: List[Change] = []
    seen: set = set()
    for run in runs:
        if not run.green:
            continue
        for commit in history.commits_between(previous_green, run.sha):
            pull = history.pull_of(commit["sha"])
            if pull is not None:
                key, label = f"pr-{pull['number']}", f"#{pull['number']}"
                started = history.first_commit_of(pull["number"])
            else:
                key, label = commit["sha"], commit["sha"][:7]
                started = parse_time(commit["commit"]["author"]["date"])
            if key in seen:
                continue
            seen.add(key)
            changes.append(Change(label, started, run.run_id, run.completed, run.queue_min, run.exec_min))
        previous_green = run.sha
    return changes


def incidents_of(runs: List[Run]) -> List[Incident]:
    incidents: List[Incident] = []
    open_incident: Optional[Incident] = None
    for run in runs:
        if run.red and open_incident is None:
            open_incident = Incident(run.run_id, run.completed)
            incidents.append(open_incident)
        elif run.green and open_incident is not None:
            open_incident.green_run_id, open_incident.recovered = run.run_id, run.completed
            open_incident = None
    return incidents


def summary(report: Report) -> dict:
    greens = [run for run in report.runs if run.green]
    reds = [run for run in report.runs if run.red]
    other = [run for run in report.runs if not run.green and not run.red]
    weeks = ((report.until - report.since).days + 1) / 7
    finished = len(greens) + len(reds)
    leads = [change.lead_min for change in report.changes]
    recoveries = [incident.recovery_min for incident in report.incidents if incident.recovery_min is not None]
    execs = [run.exec_min for run in report.runs if run.started]
    queues = [change.queue_min for change in report.changes]
    change_execs = [change.exec_min for change in report.changes]

    frequency = len(greens) / weeks
    fail_rate = 100 * len(reds) / finished if finished else 0.0
    result = {
        "period": {"since": report.since.isoformat(), "until": report.until.isoformat(), "weeks": round(weeks, 2)},
        "runs": {"green": len(greens), "red": len(reds), "other": len(other), "reruns": rerun_count(report)},
        "deployment_frequency_per_week": round(frequency, 1),
        "deployment_frequency_level": level(frequency, FREQUENCY_LEVELS, at_least=True),
        "change_fail_rate_percent": round(fail_rate, 1),
        "change_fail_rate_level": level(fail_rate, FAIL_RATE_LEVELS),
        "success_rate_percent": round(100 - fail_rate, 1) if finished else None,
        "execution_median_min": round(statistics.median(execs), 2) if execs else None,
        "changes": len(report.changes),
    }
    if leads:
        mean_lead = statistics.mean(leads)
        result.update(
            lead_time_median_min=round(statistics.median(leads), 1),
            lead_time_mean_min=round(mean_lead, 1),
            lead_time_level=level(statistics.median(leads), LEAD_TIME_LEVELS),
            queue_mean_min=round(statistics.mean(queues), 2),
            queue_share_percent=round(100 * statistics.mean(queues) / mean_lead, 2) if mean_lead else None,
            execution_mean_min=round(statistics.mean(change_execs), 2),
            execution_share_percent=round(100 * statistics.mean(change_execs) / mean_lead, 2) if mean_lead else None,
        )
        review = mean_lead - statistics.mean(queues) - statistics.mean(change_execs)
        result.update(
            review_mean_min=round(review, 1),
            review_share_percent=round(100 * review / mean_lead, 2) if mean_lead else None,
        )
    result["incidents"] = len(report.incidents)
    if recoveries:
        result.update(
            recovery_median_min=round(statistics.median(recoveries), 1),
            recovery_mean_min=round(statistics.mean(recoveries), 1),
            recovery_level=level(statistics.median(recoveries), RECOVERY_LEVELS),
        )
    return result


def rerun_count(report: Report) -> int:
    return sum(1 for run in report.runs if run.attempt > 1)


# --- output -----------------------------------------------------------------------------------------------


def fmt_time(moment: Optional[datetime]) -> str:
    return moment.strftime("%d.%m %H:%M") if moment else "—"


def fmt_level(pair: Optional[Tuple[str, float]]) -> str:
    if not pair:
        return "—"
    name, share = pair
    return f"{name} → {share:.1f}% опитаних".replace(".", ",")


def render(report: Report, result: dict) -> str:
    lead = "—"
    if result.get("lead_time_median_min") is not None:
        lead = f"медіана {result['lead_time_median_min']} хв, середнє {result['lead_time_mean_min']} хв"
    recovery = "збоїв на main не було"
    if result.get("recovery_median_min") is not None:
        recovery = f"медіана {result['recovery_median_min']} хв, середнє {result['recovery_mean_min']} хв"
    back_to_green = "main не ламалася"
    if result.get("recovery_median_min") is not None:
        back_to_green = f"{result['recovery_median_min']} хв (медіана)"
    runs = result["runs"]
    lines = [
        "# DORA: автоматичний підрахунок",
        "",
        f"Згенеровано скриптом `scripts/dora_metrics.py` за період {report.since:%d.%m.%Y}–{report.until:%d.%m.%Y}"
        " (дні UTC, обидва включно). Не редагуйте вручну: запустіть скрипт ще раз.",
        "",
        f"Workflow `{WORKFLOW_NAME}` (`.github/workflows/{WORKFLOW_FILE}`), події `push` у `{BRANCH}`. "
        f"Запусків: {runs['green']} зелених, {runs['red']} червоних, {runs['other']} інших (скасовані, пропущені); "
        f"повторних спроб (attempt > 1): {runs['reruns']}. Змін (PR або комітів напряму в main): {result['changes']}.",
        "",
        "| Метрика | Результат | Рівень DORA 2025 |",
        "|---|---|---|",
        f"| Частота розгортань | {result['deployment_frequency_per_week']} на тиждень "
        f"({runs['green']} за {result['period']['weeks']} тиж.) | {fmt_level(result['deployment_frequency_level'])} |",
        f"| Час виконання змін | {lead} | {fmt_level(result.get('lead_time_level'))} |",
        f"| Частота збоїв змін | {result['change_fail_rate_percent']}% ({runs['red']} з {runs['green'] + runs['red']}) "
        f"| {fmt_level(result['change_fail_rate_level'])} |",
        f"| Час відновлення | {recovery} | {fmt_level(result.get('recovery_level'))} |",
        "",
        "Час виконання змін за складовими (середнє на одну зміну):",
        "",
        "| Складова | Хв | Частка |",
        "|---|---|---|",
        f"| Черга | {result.get('queue_mean_min', '—')} | {result.get('queue_share_percent', '—')}% |",
        f"| Виконання CI | {result.get('execution_mean_min', '—')} | {result.get('execution_share_percent', '—')}% |",
        f"| Решта (розробка і рев'ю PR) | {result.get('review_mean_min', '—')} "
        f"| {result.get('review_share_percent', '—')}% |",
        "",
        "Орієнтири CircleCI:",
        "",
        "| Показник | Орієнтир | Наш результат |",
        "|---|---|---|",
        f"| Частка успішних запусків на main | 90% | {result['success_rate_percent']}% |",
        f"| Повернення main до зеленого стану | до 60 хв | {back_to_green} |",
        f"| Тривалість запуску workflow | до 10 хв | {result['execution_median_min']} хв (медіана) |",
        "",
        "## Запуски",
        "",
        "| № | Коміт | Запуск | Створено | Черга, хв | Виконання, хв | Статус | Спроба |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for number, run in enumerate(report.runs, start=1):
        status = "✅" if run.green else ("❌" if run.red else run.conclusion)
        lines.append(
            f"| {number} | `{run.sha[:7]}` | [{run.run_id}]({run.url}) | {fmt_time(run.created)} | "
            f"{run.queue_min:.1f} | {run.exec_min:.1f} | {status} | {run.attempt} |"
        )
    lines += ["", "## Зміни", "", "| Зміна | Перший коміт | Зелений запуск | Завершено | Час виконання змін, хв |"]
    lines.append("|---|---|---|---|---|")
    for change in report.changes:
        lines.append(
            f"| {change.label} | {fmt_time(change.started)} | {change.run_id} | {fmt_time(change.delivered)} | "
            f"{change.lead_min:.1f} |"
        )
    if report.incidents:
        lines += ["", "## Збої на main", "", "| Червоний запуск | Збій | Зелений запуск | Відновлено | Хв |"]
        lines.append("|---|---|---|---|---|")
        for incident in report.incidents:
            recovery_min = f"{incident.recovery_min:.1f}" if incident.recovery_min is not None else "—"
            lines.append(
                f"| {incident.red_run_id} | {fmt_time(incident.failed)} | {incident.green_run_id or '—'} | "
                f"{fmt_time(incident.recovered)} | {recovery_min} |"
            )
    return "\n".join(lines) + "\n"


def evidence(report: Report, result: dict) -> dict:
    def plain(item) -> dict:
        data = asdict(item)
        return {key: value.isoformat() if isinstance(value, datetime) else value for key, value in data.items()}

    runs = [
        {**plain(run), "queue_min": round(run.queue_min, 2), "exec_min": round(run.exec_min, 2)} for run in report.runs
    ]
    changes = [{**plain(change), "lead_min": round(change.lead_min, 1)} for change in report.changes]
    return {"summary": result, "runs": runs, "changes": changes, "incidents": [plain(i) for i in report.incidents]}


def parse_period(argv: Optional[List[str]] = None) -> Tuple[date, date]:
    parser = argparse.ArgumentParser(description="DORA metrics of the CI history on main (Lab 10)")
    parser.add_argument("--since", required=True, help="first day, YYYY-MM-DD (UTC)")
    parser.add_argument("--until", default=None, help="last day, YYYY-MM-DD (UTC); default: today")
    args = parser.parse_args(argv)
    try:
        since = date.fromisoformat(args.since)
        until = date.fromisoformat(args.until) if args.until else datetime.now(timezone.utc).date()
    except ValueError as error:
        raise MetricsError(f"Dates must look like 2026-11-01: {error}") from error
    if until < since:
        raise MetricsError("--until is before --since")
    if until - since > timedelta(days=366):
        raise MetricsError("The period is longer than a year")
    return since, until


def main(argv: Optional[List[str]] = None, get: Optional[Callable[[str, Dict[str, str]], object]] = None) -> int:
    try:
        since, until = parse_period(argv)
        history = History(get or make_api_get(github_token()))
        report = collect(history, since, until)
    except MetricsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    result = summary(report)
    REPORT_FILE.write_text(render(report, result), encoding="utf-8")
    EVIDENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(evidence(report, result), ensure_ascii=False, indent=2)
    EVIDENCE_FILE.write_text(payload + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
