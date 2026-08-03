from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = Path(".github/workflows/verify.yml")
PR_TEMPLATE_PATH = Path(".github/pull_request_template.md")
PINNED_ACTION = re.compile(r"^[^@\s]+@[a-f0-9]{40}$")
EXACT_HEAD_REF = "${{ github.event.pull_request.head.sha || github.sha }}"
REQUIRED_TEMPLATE_MARKERS = (
    "Related issue",
    "Head SHA",
    "Validation commands",
    "Actions run or commit status",
    "Migration / rollback",
)


class CiPolicyError(ValueError):
    """Raised when repository CI or merge-evidence policy is incomplete."""


def load_workflow(path: Path) -> dict[str, Any]:
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CiPolicyError(f"cannot read workflow {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CiPolicyError(f"workflow must contain a mapping: {path}")
    return data


def checkout_errors(workflow: dict[str, Any]) -> list[str]:
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict):
        return ["verify workflow must declare jobs"]
    errors: list[str] = []
    found = False
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            action = step.get("uses")
            if not isinstance(action, str) or not action.startswith("actions/checkout@"):
                continue
            found = True
            options = step.get("with")
            if not isinstance(options, dict) or options.get("ref") != EXACT_HEAD_REF:
                errors.append(
                    f"workflow job {job_name} must checkout the exact pull-request head with "
                    f"ref: {EXACT_HEAD_REF}"
                )
    if not found:
        errors.append("verify workflow must use actions/checkout")
    return errors


def workflow_errors(root: Path) -> list[str]:
    path = root / WORKFLOW_PATH
    if not path.is_file():
        return [f"missing workflow: {WORKFLOW_PATH.as_posix()}"]
    try:
        workflow = load_workflow(path)
    except CiPolicyError as exc:
        return [str(exc)]

    errors: list[str] = []
    triggers = workflow.get("on")
    if isinstance(triggers, str):
        trigger_names = {triggers}
    elif isinstance(triggers, dict):
        trigger_names = set(triggers)
    else:
        trigger_names = set()
    if "pull_request" not in trigger_names:
        errors.append("verify workflow must run on pull_request")

    permissions = workflow.get("permissions")
    if not isinstance(permissions, dict) or permissions.get("contents") != "read":
        errors.append("verify workflow must set top-level permissions.contents to read")
    elif any(value == "write" for value in permissions.values()):
        errors.append("verify workflow top-level permissions must not grant write access")

    errors.extend(checkout_errors(workflow))
    text = path.read_text(encoding="utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("uses:"):
            continue
        action = stripped.removeprefix("uses:").split("#", 1)[0].strip()
        if action.startswith("./"):
            continue
        if not PINNED_ACTION.fullmatch(action):
            errors.append(
                f"workflow action must be pinned to a full commit SHA at line {line_number}: {action}"
            )
    return errors


def pull_request_template_errors(root: Path) -> list[str]:
    path = root / PR_TEMPLATE_PATH
    if not path.is_file():
        return [f"missing pull request template: {PR_TEMPLATE_PATH.as_posix()}"]
    text = path.read_text(encoding="utf-8")
    return [
        f"pull request template missing marker: {marker}"
        for marker in REQUIRED_TEMPLATE_MARKERS
        if marker not in text
    ]


def validation_errors(root: Path = ROOT) -> list[str]:
    return workflow_errors(root) + pull_request_template_errors(root)


def main(root: Path = ROOT) -> int:
    errors = validation_errors(root)
    if errors:
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 2
    print(
        "OK pull-request trigger, exact-head checkout, read-only permissions, pinned actions, "
        "and merge evidence template"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
