from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ci_policy


PINNED = "0123456789abcdef0123456789abcdef01234567"


def write_policy_files(root: Path, *, workflow: str | None = None, template: str | None = None) -> None:
    workflow_path = root / ci_policy.WORKFLOW_PATH
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(
        workflow
        or (
            "name: Verify\n"
            "on:\n"
            "  pull_request:\n"
            "permissions:\n"
            "  contents: read\n"
            "jobs:\n"
            "  verify:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            f"      - uses: actions/checkout@{PINNED}\n"
        ),
        encoding="utf-8",
    )
    template_path = root / ci_policy.PR_TEMPLATE_PATH
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(
        template
        or "\n".join(
            [
                "## Related issue",
                "## Head SHA",
                "## Validation commands",
                "## Actions run or commit status",
                "## Migration / rollback",
            ]
        ),
        encoding="utf-8",
    )


def test_valid_policy_passes(tmp_path: Path) -> None:
    write_policy_files(tmp_path)
    assert ci_policy.validation_errors(tmp_path) == []


def test_pull_request_trigger_is_required(tmp_path: Path) -> None:
    write_policy_files(
        tmp_path,
        workflow=(
            "name: Verify\n"
            "on:\n"
            "  push:\n"
            "permissions:\n"
            "  contents: read\n"
            "jobs: {}\n"
        ),
    )
    assert "verify workflow must run on pull_request" in ci_policy.validation_errors(tmp_path)


def test_top_level_write_permission_is_rejected(tmp_path: Path) -> None:
    write_policy_files(
        tmp_path,
        workflow=(
            "name: Verify\n"
            "on:\n"
            "  pull_request:\n"
            "permissions:\n"
            "  contents: write\n"
            "jobs: {}\n"
        ),
    )
    assert (
        "verify workflow must set top-level permissions.contents to read"
        in ci_policy.validation_errors(tmp_path)
    )


def test_floating_action_reference_is_rejected(tmp_path: Path) -> None:
    write_policy_files(
        tmp_path,
        workflow=(
            "name: Verify\n"
            "on:\n"
            "  pull_request:\n"
            "permissions:\n"
            "  contents: read\n"
            "jobs:\n"
            "  verify:\n"
            "    steps:\n"
            "      - uses: actions/checkout@v7\n"
        ),
    )
    assert any("full commit SHA" in error for error in ci_policy.validation_errors(tmp_path))


def test_merge_evidence_markers_are_required(tmp_path: Path) -> None:
    write_policy_files(tmp_path, template="## Related issue\n")
    errors = ci_policy.validation_errors(tmp_path)
    assert "pull request template missing marker: Head SHA" in errors
    assert "pull request template missing marker: Actions run or commit status" in errors
