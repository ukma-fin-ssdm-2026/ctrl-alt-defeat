"""GitHub Actions guard rails for a public repository."""

from pathlib import Path

import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).resolve().parents[1] / ".github" / "workflows").glob("*.yml"))


def runner_labels(job: dict) -> list:
    runs_on = job.get("runs-on", [])
    if isinstance(runs_on, dict):
        runs_on = runs_on.get("labels", [])
    return [runs_on] if isinstance(runs_on, str) else list(runs_on)


def test_workflows_are_found():
    assert WORKFLOWS


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_no_job_runs_on_a_self_hosted_runner(workflow):
    """A fork pull request could otherwise run its own code on a team member's computer."""
    jobs = yaml.safe_load(workflow.read_text(encoding="utf-8")).get("jobs", {})

    for name, job in jobs.items():
        assert "self-hosted" not in runner_labels(job), f"{workflow.name}: job '{name}' uses a self-hosted runner"
