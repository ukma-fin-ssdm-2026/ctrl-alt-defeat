"""GitHub Actions guard rails for a public repository."""

import json
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


def test_render_does_not_wait_for_the_deployment_check():
    """
    "Production deployment" is a check of the main commit that waits for Render to serve that commit.
    With autoDeployTrigger: checksPass Render would wait for this check as well, so nothing would deploy.
    """
    root = Path(__file__).resolve().parents[1]
    services = yaml.safe_load((root / "render.yaml").read_text(encoding="utf-8"))["services"]
    recorder = root / ".github" / "workflows" / "production-deployment.yml"

    assert recorder.exists()
    for service in services:
        assert service.get("autoDeployTrigger") != "checksPass", service["name"]


def test_reliability_tests_run_as_a_separate_ci_job():
    """Lab 9 bonus: the job "reliability" runs tests/reliability on every PR, so it can be a required check."""
    ci = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    triggers = ci.get("on", ci.get(True))
    steps = ci["jobs"]["reliability"]["steps"]

    assert "pull_request" in triggers
    assert any("pytest tests/reliability" in step.get("run", "") for step in steps)
    assert any("npm run test:reliability" in step.get("run", "") for step in steps)
    # The locally installed vitest is used: npx could download and run a package (SonarCloud security rule)
    assert not any("npx " in step.get("run", "") for step in steps)
    package = json.loads((Path(__file__).resolve().parents[1] / "frontend" / "package.json").read_text("utf-8"))
    assert package["scripts"]["test:reliability"] == "vitest run src/reliability"
