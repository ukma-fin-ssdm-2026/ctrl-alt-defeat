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


def test_ci_workflow_installs_dependencies_with_hashes():
    """CI must pin resolved dependencies and enforce hash verification (SonarQube githubactions:S8544)."""
    ci_workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    content = ci_workflow.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    steps = parsed["jobs"]["build"]["steps"]
    install_step = next(s for s in steps if s.get("name") == "Install locked dependencies")
    run_cmd = install_step.get("run", "")

    assert "requirements-lock.txt" in run_cmd, "CI should install dependencies from requirements-lock.txt"
    assert "--require-hashes" in run_cmd, "CI should enforce hash verification with --require-hashes"

