from __future__ import annotations

import importlib.util
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SPEC = importlib.util.spec_from_file_location("ci_policy_tool", TOOLS / "ci_policy.py")
assert SPEC and SPEC.loader
ci_policy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ci_policy)

PINNED = "0123456789abcdef0123456789abcdef01234567"
VALID_TEMPLATE = """## Related issue
## Head SHA
## Validation commands
## Actions run or commit status
## Migration / rollback
"""


def write_policy_files(
    root: Path, *, workflow: str | None = None, template: str | None = None
) -> None:
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
            "        with:\n"
            "          ref: ${{ github.event.pull_request.head.sha || github.sha }}\n"
        ),
        encoding="utf-8",
    )
    template_path = root / ci_policy.PR_TEMPLATE_PATH
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(template or VALID_TEMPLATE, encoding="utf-8")


def test_valid_policy_passes(tmp_path: Path) -> None:
    write_policy_files(tmp_path)
    assert ci_policy.validation_errors(tmp_path) == []


def test_pull_request_trigger_is_required(tmp_path: Path) -> None:
    write_policy_files(
        tmp_path,
        workflow=("name: Verify\non:\n  push:\npermissions:\n  contents: read\njobs: {}\n"),
    )
    assert "verify workflow must run on pull_request" in ci_policy.validation_errors(tmp_path)


def test_top_level_write_permission_is_rejected(tmp_path: Path) -> None:
    write_policy_files(
        tmp_path,
        workflow=(
            "name: Verify\non:\n  pull_request:\npermissions:\n  contents: write\njobs: {}\n"
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
            "        with:\n"
            "          ref: ${{ github.event.pull_request.head.sha || github.sha }}\n"
        ),
    )
    assert any("full commit SHA" in error for error in ci_policy.validation_errors(tmp_path))


def test_checkout_must_use_exact_pull_request_head(tmp_path: Path) -> None:
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
            f"      - uses: actions/checkout@{PINNED}\n"
        ),
    )
    assert any(
        "exact pull-request head" in error for error in ci_policy.validation_errors(tmp_path)
    )


def test_merge_evidence_markers_are_required(tmp_path: Path) -> None:
    write_policy_files(tmp_path, template="## Related issue\n")
    errors = ci_policy.validation_errors(tmp_path)
    assert "pull request template missing marker: Head SHA" in errors
    assert "pull request template missing marker: Actions run or commit status" in errors
