from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RESULT_VERSION = 1
LIFECYCLE_STATES = {
    "planned",
    "submitted",
    "running",
    "failed",
    "incomplete",
    "succeeded",
    "verified",
}
TERMINAL_STATES = {"failed", "incomplete", "succeeded", "verified"}


class RunStateError(ValueError):
    """Raised when run lifecycle evidence is missing, malformed, or inconsistent."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_progress(run_dir: Path, state: str, **details: object) -> Path:
    if state not in {"planned", "submitted", "running"}:
        raise RunStateError(f"progress state must be planned, submitted, or running: {state}")
    path = run_dir / "state.json"
    write_json_atomic(
        path,
        {
            "state_version": 1,
            "run_id": run_dir.name,
            "state": state,
            "recorded_at": utc_now(),
            "details": details,
        },
    )
    return path


def artifact_names(manifest: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        for key in ("path", "source_path"):
            value = artifact.get(key)
            if isinstance(value, str):
                names.add(value)
    return names


def measured_metric_ids(manifest: dict[str, Any]) -> set[str]:
    metrics = manifest.get("metrics", {})
    if not isinstance(metrics, dict):
        return set()
    measured: set[str] = set()
    for identifier, value in metrics.items():
        if isinstance(value, dict) and value.get("state") == "missing":
            continue
        measured.add(identifier)
    return measured


def completion_report(manifest: dict[str, Any]) -> dict[str, Any]:
    plan = manifest.get("plan", {}).get("resolved", {})
    criteria = plan.get("completion_criteria", {}) if isinstance(plan, dict) else {}
    required_artifacts = criteria.get("required_artifacts", [])
    required_metrics = criteria.get("required_metrics", [])
    if not isinstance(required_artifacts, list):
        required_artifacts = []
    if not isinstance(required_metrics, list):
        required_metrics = []

    available_artifacts = artifact_names(manifest)
    available_metrics = measured_metric_ids(manifest)
    missing_artifacts = sorted(
        item
        for item in required_artifacts
        if isinstance(item, str) and item not in available_artifacts
    )
    missing_metrics = sorted(
        item for item in required_metrics if isinstance(item, str) and item not in available_metrics
    )
    phases = manifest.get("phases", [])
    phase_failures = sorted(
        str(record.get("id"))
        for record in phases
        if isinstance(record, dict) and record.get("status") == "failed"
    )
    incomplete_phases = sorted(
        str(record.get("id"))
        for record in phases
        if isinstance(record, dict) and record.get("status") == "incomplete"
    )
    evaluation_errors = manifest.get("evaluation_errors", [])
    if not isinstance(evaluation_errors, list):
        evaluation_errors = ["evaluation_errors is malformed"]
    return {
        "required_artifacts": required_artifacts,
        "required_metrics": required_metrics,
        "missing_artifacts": missing_artifacts,
        "missing_metrics": missing_metrics,
        "failed_phases": phase_failures,
        "incomplete_phases": incomplete_phases,
        "evaluation_errors": list(evaluation_errors),
        "complete": not (
            missing_artifacts
            or missing_metrics
            or phase_failures
            or incomplete_phases
            or evaluation_errors
        ),
    }


def terminal_state(manifest: dict[str, Any], report: dict[str, Any]) -> str:
    if manifest.get("return_code") not in {0, None} or report["failed_phases"]:
        return "failed"
    if not report["complete"]:
        return "incomplete"
    return "succeeded"


def terminal_result(manifest: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    report = completion_report(manifest)
    return {
        "result_version": RESULT_VERSION,
        "run_id": manifest["run_id"],
        "state": terminal_state(manifest, report),
        "terminal": True,
        "recorded_at": utc_now(),
        "manifest_sha256": manifest_sha256,
        "return_code": manifest.get("return_code"),
        "termination": manifest.get("termination"),
        "completion": report,
    }


def write_terminal_result(
    manifest_path: Path,
    manifest: dict[str, Any],
    manifest_sha256: str,
) -> Path:
    result = terminal_result(manifest, manifest_sha256)
    path = manifest_path.parent / "result.json"
    write_json_atomic(path, result)
    return path


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RunStateError(f"cannot read lifecycle evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RunStateError(f"lifecycle evidence must be a JSON object: {path}")
    return value


def status_projection(run_dir: Path, *, verified: bool = False) -> dict[str, Any]:
    result_path = run_dir / "result.json"
    state_path = run_dir / "state.json"
    manifest_path = run_dir / "manifest.json"
    if result_path.is_file():
        try:
            result = read_json(result_path)
        except RunStateError as exc:
            return {
                "run_id": run_dir.name,
                "state": "incomplete",
                "terminal": False,
                "errors": [str(exc)],
            }
        state = result.get("state")
        if state not in {"failed", "incomplete", "succeeded"}:
            return {
                "run_id": run_dir.name,
                "state": "incomplete",
                "terminal": False,
                "errors": [f"terminal result has invalid state: {state}"],
            }
        projection = dict(result)
        if verified:
            projection["state"] = "verified"
            projection["verified_state"] = state
            projection["verified_at"] = utc_now()
        return projection
    if state_path.is_file():
        try:
            progress = read_json(state_path)
        except RunStateError as exc:
            return {
                "run_id": run_dir.name,
                "state": "incomplete",
                "terminal": False,
                "errors": [str(exc)],
            }
        state = progress.get("state")
        if state not in {"planned", "submitted", "running"}:
            state = "incomplete"
        return {
            "run_id": run_dir.name,
            "state": state,
            "terminal": False,
            "recorded_at": progress.get("recorded_at"),
            "details": progress.get("details", {}),
            "errors": ["terminal result is not recorded"],
        }
    if manifest_path.is_file():
        return {
            "run_id": run_dir.name,
            "state": "incomplete",
            "terminal": False,
            "errors": ["manifest exists but lifecycle evidence is missing"],
        }
    return {
        "run_id": run_dir.name,
        "state": "incomplete",
        "terminal": False,
        "errors": ["run evidence does not exist"],
    }


def results_projection(
    manifest: dict[str, Any],
    status: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": manifest["run_id"],
        "status": status,
        "plan": manifest.get("plan"),
        "phases": manifest.get("phases", []),
        "metrics": manifest.get("metrics", {}),
        "evaluation_errors": manifest.get("evaluation_errors", []),
        "artifacts": manifest.get("artifacts", []),
        "recovery": manifest.get("recovery"),
    }
