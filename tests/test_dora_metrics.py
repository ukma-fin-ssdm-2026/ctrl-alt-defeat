"""Lab 10 bonus: DORA metrics from the GitHub Actions history (scripts/dora_metrics.py)."""

from datetime import date

import pytest

from scripts import dora_metrics
from scripts.dora_metrics import (
    FAIL_RATE_LEVELS,
    FREQUENCY_LEVELS,
    LEAD_TIME_LEVELS,
    History,
    MetricsError,
    collect,
    level,
    parse_period,
    render,
    summary,
)

BASE = "/repos/ukma-fin-ssdm-2026/ctrl-alt-defeat"


def run(run_id, sha, conclusion, created, attempt=1):
    return {
        "id": run_id,
        "head_sha": sha,
        "status": "completed",
        "conclusion": conclusion,
        "run_attempt": attempt,
        "created_at": created,
        "updated_at": created,
        "html_url": f"https://github.com/runs/{run_id}",
    }


def jobs(started, completed):
    return {"jobs": [{"started_at": started, "completed_at": completed}, {"started_at": started, "completed_at": None}]}


class FakeApi:
    """Five runs on main: green, red, red, green (fix), green; one commit pushed straight to main."""

    def __init__(self):
        self.calls = []
        self.answers = {
            f"{BASE}/actions/runs/1/jobs": jobs("2026-11-02T10:02:00Z", "2026-11-02T10:05:00Z"),
            f"{BASE}/actions/runs/2/jobs": jobs("2026-11-03T09:00:00Z", "2026-11-03T09:04:00Z"),
            f"{BASE}/actions/runs/3/jobs": jobs("2026-11-03T09:30:00Z", "2026-11-03T09:34:00Z"),
            f"{BASE}/actions/runs/4/jobs": jobs("2026-11-03T11:00:00Z", "2026-11-03T11:04:00Z"),
            f"{BASE}/actions/runs/5/jobs": jobs("2026-11-05T12:00:00Z", "2026-11-05T12:02:00Z"),
            f"{BASE}/compare/before...a1": {"commits": [commit("a1", "2026-11-02T08:00:00Z")]},
            f"{BASE}/compare/a1...d4": {
                "commits": [commit("b2", "2026-11-03T08:00:00Z"), commit("c3", "2026-11-03T09:20:00Z"), commit("d4")]
            },
            f"{BASE}/compare/d4...e5": {"commits": [commit("e5", "2026-11-05T11:00:00Z")]},
            f"{BASE}/commits/a1/pulls": [pull(10)],
            f"{BASE}/commits/b2/pulls": [pull(11)],
            f"{BASE}/commits/c3/pulls": [pull(12)],
            f"{BASE}/commits/d4/pulls": [pull(12)],
            f"{BASE}/commits/e5/pulls": [{"number": 99, "merged_at": None, "base": {"ref": "main"}}],
            f"{BASE}/pulls/10/commits": [commit("x", "2026-11-02T09:30:00Z"), commit("y", "2026-11-02T09:00:00Z")],
            f"{BASE}/pulls/11/commits": [commit("x", "2026-11-03T07:00:00Z")],
            f"{BASE}/pulls/12/commits": [commit("x", "2026-11-03T09:00:00Z")],
        }

    def __call__(self, path, params):
        self.calls.append((path, params))
        if path.endswith(f"/workflows/{dora_metrics.WORKFLOW_FILE}/runs"):
            if params["created"].startswith("<"):
                return {"workflow_runs": [run(0, "before", "success", "2026-10-31T10:00:00Z")]}
            return {
                "workflow_runs": [
                    run(5, "e5", "success", "2026-11-05T12:00:00Z"),
                    run(1, "a1", "success", "2026-11-02T10:00:00Z"),
                    run(2, "b2", "failure", "2026-11-03T09:00:00Z"),
                    run(3, "c3", "failure", "2026-11-03T09:30:00Z", attempt=2),
                    run(4, "d4", "success", "2026-11-03T10:30:00Z"),
                ]
            }
        return self.answers[path]


def commit(sha, authored="2026-11-03T10:00:00Z"):
    return {"sha": sha, "commit": {"author": {"date": authored}}}


def pull(number):
    return {"number": number, "merged_at": "2026-11-03T10:00:00Z", "base": {"ref": "main"}}


@pytest.fixture
def report():
    return collect(History(FakeApi()), date(2026, 11, 1), date(2026, 11, 7))


def test_runs_queue_and_execution(report):
    assert [r.run_id for r in report.runs] == [1, 2, 3, 4, 5]
    first = report.runs[0]
    assert (first.queue_min, first.exec_min) == (2.0, 3.0)
    assert report.runs[3].queue_min == 30.0  # 10:30 created, 11:00 the first job started


def test_changes_lead_time_from_the_first_pr_commit(report):
    lead = {change.label: round(change.lead_min, 1) for change in report.changes}
    # PR #10: first commit 09:00 (the oldest of its commits), delivered 10:05
    assert lead["#10"] == 65.0
    # PR #11 and #12 were in red runs; the green run 4 (11:04) delivers them, #12 only once
    assert lead["#11"] == 244.0 and lead["#12"] == 124.0
    # A commit pushed straight to main (its PR was not merged): from the commit itself
    assert lead["e5"] == 62.0
    assert len(report.changes) == 4


def test_failures_and_recovery(report):
    (incident,) = report.incidents  # two red runs in a row are one failure
    assert (incident.red_run_id, incident.green_run_id) == (2, 4)
    assert incident.recovery_min == 120.0  # end of the first red run 09:04 -> end of the green run 11:04


def test_summary_levels_and_shares(report):
    result = summary(report)
    assert result["runs"] == {"green": 3, "red": 2, "other": 0, "reruns": 1}
    assert result["deployment_frequency_per_week"] == 3.0
    assert result["deployment_frequency_level"] == ("від щодня до щотижня", 44.6)
    assert result["change_fail_rate_percent"] == 40.0
    assert result["change_fail_rate_level"] == ("32-64%", 94.1)
    assert result["recovery_median_min"] == 120.0 and result["recovery_level"] == ("менше доби", 56.5)
    assert result["lead_time_median_min"] == 94.5
    total = result["queue_share_percent"] + result["execution_share_percent"] + result["review_share_percent"]
    assert total == pytest.approx(100, abs=0.05)
    text = render(report, result)
    assert "| Частота збоїв змін | 40.0% (2 з 5) |" in text
    assert "## Збої на main" in text


def test_levels_of_dora_2025():
    assert level(57.3, FREQUENCY_LEVELS, at_least=True) == ("на вимогу (кілька разів на день)", 16.2)
    assert level(4, FREQUENCY_LEVELS, at_least=True) == ("від щодня до щотижня", 44.6)
    assert level(21.4, LEAD_TIME_LEVELS)[1] == 9.4
    assert level(0, FAIL_RATE_LEVELS) == ("0-2%", 8.5)


def test_period_arguments():
    assert parse_period(["--since", "2026-11-01", "--until", "2026-11-13"]) == (date(2026, 11, 1), date(2026, 11, 13))
    with pytest.raises(MetricsError):
        parse_period(["--since", "2026-11-13", "--until", "2026-11-01"])
    with pytest.raises(MetricsError):
        parse_period(["--since", "01.11.2026"])


def test_without_a_token_nothing_is_written(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(dora_metrics, "REPORT_FILE", tmp_path / "dora-auto.md")
    assert dora_metrics.main(["--since", "2026-11-01"]) == 1
    assert "GH_TOKEN" in capsys.readouterr().err
    assert not (tmp_path / "dora-auto.md").exists()


def test_main_writes_the_report_and_the_evidence(monkeypatch, tmp_path):
    monkeypatch.setattr(dora_metrics, "REPORT_FILE", tmp_path / "dora-auto.md")
    monkeypatch.setattr(dora_metrics, "EVIDENCE_FILE", tmp_path / "evidence" / "dora-auto.json")
    assert dora_metrics.main(["--since", "2026-11-01", "--until", "2026-11-07"], get=FakeApi()) == 0
    assert "# DORA: автоматичний підрахунок" in (tmp_path / "dora-auto.md").read_text(encoding="utf-8")
    assert '"change_fail_rate_percent": 40.0' in (tmp_path / "evidence" / "dora-auto.json").read_text(encoding="utf-8")
