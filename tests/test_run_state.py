from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_state


def manifest(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "run_id": "run-1",
        "return_code": 0,
        "termination": {"reason": "completed"},
        "plan": {
            "resolved": {
                "completion_criteria": {
                    "required_artifacts": ["outputs/metrics.json"],
                    "required_metrics": ["success"],
                }
            }
        },
        "phases": [{"id": "main", "status": "succeeded"}],
        "metrics": {"success": True},
        "evaluation_errors": [],
        "artifacts": [
            {
                "path": "runs/run-1/artifacts/outputs/metrics.json",
                "source_path": "outputs/metrics.json",
            }
        ],
    }
    value.update(updates)
    return value


def test_terminal_success_requires_completion_contract() -> None:
    result = run_state.terminal_result(manifest(), "0" * 64)
    assert result["state"] == "succeeded"
    assert result["completion"]["complete"] is True


def test_missing_metric_is_incomplete_not_success() -> None:
    result = run_state.terminal_result(manifest(metrics={}), "0" * 64)
    assert result["state"] == "incomplete"
    assert result["completion"]["missing_metrics"] == ["success"]


def test_failed_phase_is_failed() -> None:
    result = run_state.terminal_result(
        manifest(phases=[{"id": "main", "status": "failed"}]),
        "0" * 64,
    )
    assert result["state"] == "failed"


def test_progress_without_terminal_result_is_not_success(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs/run-1"
    run_state.write_progress(run_dir, "running", phase="main")
    status = run_state.status_projection(run_dir)
    assert status["state"] == "running"
    assert status["terminal"] is False
    assert "terminal result" in status["errors"][0]


def test_manifest_without_lifecycle_evidence_is_incomplete(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs/run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text("{}\n", encoding="utf-8")
    status = run_state.status_projection(run_dir)
    assert status["state"] == "incomplete"
    assert status["terminal"] is False


def test_corrupt_terminal_result_is_incomplete(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs/run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "result.json").write_text("{", encoding="utf-8")
    status = run_state.status_projection(run_dir)
    assert status["state"] == "incomplete"
    assert status["errors"]


def test_verified_projection_does_not_mutate_result(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs/run-1"
    run_dir.mkdir(parents=True)
    original = run_state.terminal_result(manifest(), "0" * 64)
    run_state.write_json_atomic(run_dir / "result.json", original)
    before = (run_dir / "result.json").read_text(encoding="utf-8")
    projected = run_state.status_projection(run_dir, verified=True)
    after = (run_dir / "result.json").read_text(encoding="utf-8")
    assert projected["state"] == "verified"
    assert projected["verified_state"] == "succeeded"
    assert before == after


def test_results_projection_is_machine_readable() -> None:
    value = manifest()
    status = {"run_id": "run-1", "state": "succeeded", "terminal": True}
    result = run_state.results_projection(value, status)
    assert json.loads(json.dumps(result))["status"]["state"] == "succeeded"
