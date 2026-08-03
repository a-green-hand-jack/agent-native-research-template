from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asset_binding

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
TIMEOUT_RETURN_CODE = 124
OUTPUT_CONTRACT_RETURN_CODE = 3
PHASE_STATUSES = {"succeeded", "failed", "incomplete", "reused"}


class PhaseGraphError(ValueError):
    """Raised when a phase graph or phase recovery request is invalid."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def command_argv(value: object) -> list[str]:
    if isinstance(value, str):
        argv = shlex.split(value)
    elif isinstance(value, list) and all(isinstance(item, str) and item for item in value):
        argv = list(value)
    else:
        raise PhaseGraphError("phase command must be a shell-style string or non-empty string list")
    if not argv:
        raise PhaseGraphError("phase command must not be empty")
    return argv


def normalize_outputs(value: object, phase_id: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise PhaseGraphError(f"phase {phase_id} outputs must be a list")
    records: list[dict[str, Any]] = []
    for index, declaration in enumerate(value):
        if isinstance(declaration, str):
            declaration = {"path": declaration}
        if not isinstance(declaration, dict):
            raise PhaseGraphError(f"phase {phase_id} outputs[{index}] must be a string or mapping")
        path = declaration.get("path")
        if not isinstance(path, str) or not path.strip():
            raise PhaseGraphError(f"phase {phase_id} outputs[{index}].path is required")
        raw = Path(path)
        if raw.is_absolute() or ".." in raw.parts:
            raise PhaseGraphError(f"phase {phase_id} output paths must be repository-relative")
        required = declaration.get("required", False)
        if not isinstance(required, bool):
            raise PhaseGraphError(f"phase {phase_id} outputs[{index}].required must be boolean")
        records.append({"path": path, "required": required})
    return records


def normalize_phases(spec: dict[str, Any], default_argv: list[str]) -> list[dict[str, Any]]:
    declarations = spec.get("phases")
    if declarations is None:
        declarations = [
            {
                "id": "main",
                "command": default_argv,
                "depends_on": [],
                "asset_phase": "all",
                "outputs": [],
            }
        ]
    if not isinstance(declarations, list) or not declarations:
        raise PhaseGraphError("phases must be a non-empty list")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, declaration in enumerate(declarations):
        if not isinstance(declaration, dict):
            raise PhaseGraphError(f"phases[{index}] must be a mapping")
        identifier = declaration.get("id")
        if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
            raise PhaseGraphError(f"phases[{index}].id must be a stable lowercase identifier")
        if identifier in seen:
            raise PhaseGraphError(f"duplicate phase ID: {identifier}")
        seen.add(identifier)
        depends_on = declaration.get("depends_on", [])
        if not isinstance(depends_on, list) or not all(
            isinstance(item, str) and ID_PATTERN.fullmatch(item) for item in depends_on
        ):
            raise PhaseGraphError(f"phase {identifier} depends_on must contain phase IDs")
        if len(depends_on) != len(set(depends_on)):
            raise PhaseGraphError(f"phase {identifier} has duplicate dependencies")
        if identifier in depends_on:
            raise PhaseGraphError(f"phase {identifier} cannot depend on itself")
        asset_phase = declaration.get("asset_phase", "all")
        if asset_phase not in asset_binding.PHASES:
            raise PhaseGraphError(f"phase {identifier} asset_phase is invalid")
        timeout = declaration.get("timeout_seconds")
        if timeout is not None and (
            not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0
        ):
            raise PhaseGraphError(f"phase {identifier} timeout_seconds must be positive")
        records.append(
            {
                "id": identifier,
                "command": command_argv(declaration.get("command")),
                "depends_on": list(depends_on),
                "asset_phase": asset_phase,
                "timeout_seconds": timeout,
                "outputs": normalize_outputs(declaration.get("outputs"), identifier),
            }
        )
    identifiers = {record["id"] for record in records}
    for record in records:
        unknown = set(record["depends_on"]) - identifiers
        if unknown:
            raise PhaseGraphError(
                f"phase {record['id']} depends on unknown phases: {', '.join(sorted(unknown))}"
            )
    ordered_ids = topological_order(records)
    by_id = {record["id"]: record for record in records}
    return [by_id[identifier] for identifier in ordered_ids]


def topological_order(phases: list[dict[str, Any]]) -> list[str]:
    dependencies = {record["id"]: set(record["depends_on"]) for record in phases}
    ordered: list[str] = []
    while dependencies:
        ready = sorted(identifier for identifier, values in dependencies.items() if not values)
        if not ready:
            cycle = ", ".join(sorted(dependencies))
            raise PhaseGraphError(f"phase graph contains a cycle involving: {cycle}")
        ordered.extend(ready)
        for identifier in ready:
            del dependencies[identifier]
        for values in dependencies.values():
            values.difference_update(ready)
    return ordered


def dependency_closure(phases: list[dict[str, Any]], selected: str) -> set[str]:
    by_id = {phase["id"]: phase for phase in phases}
    if selected not in by_id:
        raise PhaseGraphError(f"unknown retry phase: {selected}")
    closure: set[str] = set()
    pending = list(by_id[selected]["depends_on"])
    while pending:
        identifier = pending.pop()
        if identifier in closure:
            continue
        closure.add(identifier)
        pending.extend(by_id[identifier]["depends_on"])
    return closure


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_outputs(
    root: Path,
    phase_dir: Path,
    declarations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    artifacts: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    root_resolved = root.resolve()
    for declaration in declarations:
        pattern = declaration["path"]
        matches = sorted(candidate for candidate in root.glob(pattern) if candidate.is_file())
        if declaration["required"] and not matches:
            errors.append(f"required phase output matched no files: {pattern}")
        for source in matches:
            if source.is_symlink():
                errors.append(f"phase output must not be a symbolic link: {source}")
                continue
            try:
                source.resolve().relative_to(root_resolved)
            except ValueError:
                errors.append(f"phase output resolves outside repository: {source}")
                continue
            relative = source.relative_to(root).as_posix()
            if relative in seen or relative.startswith("runs/"):
                continue
            seen.add(relative)
            destination = phase_dir / "artifacts" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            artifacts.append(
                {
                    "path": destination.relative_to(root).as_posix(),
                    "source_path": relative,
                    "sha256": sha256_file(destination),
                    "kind": "phase_output",
                }
            )
    return artifacts, errors


def timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def reused_phase_record(parent: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {
        "id": parent["id"],
        "status": "reused",
        "depends_on": list(parent.get("depends_on", [])),
        "asset_phase": parent.get("asset_phase", "all"),
        "command": list(parent.get("command", [])),
        "return_code": 0,
        "started_at": None,
        "finished_at": None,
        "termination": {"reason": "reused_verified_parent"},
        "asset_bindings": parent.get("asset_bindings", {"phase": "all", "assets": [], "sha256": ""}),
        "artifacts": list(parent.get("artifacts", [])),
        "errors": [],
        "source_run_id": run_id,
    }


def incomplete_phase_record(phase: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "id": phase["id"],
        "status": "incomplete",
        "depends_on": list(phase["depends_on"]),
        "asset_phase": phase["asset_phase"],
        "command": list(phase["command"]),
        "return_code": None,
        "started_at": None,
        "finished_at": None,
        "termination": {"reason": reason},
        "asset_bindings": {"phase": phase["asset_phase"], "assets": [], "sha256": ""},
        "artifacts": [],
        "errors": [],
    }


def execute_phases(
    spec: dict[str, Any],
    executor: dict[str, Any],
    default_argv: list[str],
    root: Path,
    run_dir: Path,
    base_environment: dict[str, str],
    max_wall_time_seconds: int,
    *,
    retry_phase: str | None = None,
    parent_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    phases = normalize_phases(spec, default_argv)
    by_id = {phase["id"]: phase for phase in phases}
    parent_by_id = {
        phase["id"]: phase
        for phase in (parent_manifest or {}).get("phases", [])
        if isinstance(phase, dict) and isinstance(phase.get("id"), str)
    }
    dependencies_to_reuse: set[str] = set()
    if retry_phase is not None:
        if parent_manifest is None:
            raise PhaseGraphError("phase retry requires a verified parent manifest")
        dependencies_to_reuse = dependency_closure(phases, retry_phase)
        for identifier in dependencies_to_reuse:
            parent = parent_by_id.get(identifier)
            if parent is None or parent.get("status") not in {"succeeded", "reused"}:
                raise PhaseGraphError(f"parent phase is not reusable: {identifier}")

    results: list[dict[str, Any]] = []
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    overall_return_code = 0
    deadline = time.monotonic() + max_wall_time_seconds
    blocked = False
    reused_artifacts: list[dict[str, Any]] = []

    for phase in phases:
        identifier = phase["id"]
        phase_dir = run_dir / "phases" / identifier
        phase_dir.mkdir(parents=True, exist_ok=True)
        if identifier in dependencies_to_reuse:
            record = reused_phase_record(parent_by_id[identifier], parent_manifest["run_id"])
            reused_artifacts.extend(record["artifacts"])
            write_json(phase_dir / "result.json", record)
            results.append(record)
            continue
        if retry_phase is not None and identifier != retry_phase:
            record = incomplete_phase_record(phase, "not_selected_for_retry")
            write_json(phase_dir / "result.json", record)
            results.append(record)
            continue
        if blocked:
            record = incomplete_phase_record(phase, "dependency_failed")
            write_json(phase_dir / "result.json", record)
            results.append(record)
            continue

        preflight = asset_binding.resolve_assets(
            spec, executor, root, phase=phase["asset_phase"]
        )
        environment = dict(base_environment)
        environment.update(asset_binding.environment_for_assets(preflight))
        for dependency in phase["depends_on"]:
            source_record = next(record for record in results if record["id"] == dependency)
            source_run = source_record.get("source_run_id", run_dir.name)
            source_dir = root / "runs" / source_run / "phases" / dependency / "artifacts"
            key = dependency.upper().replace("-", "_").replace(".", "_")
            environment[f"RESEARCH_PHASE_{key}_ARTIFACT_DIR"] = str(source_dir)
        environment["RESEARCH_PHASE_ID"] = identifier
        environment["RESEARCH_PHASE_DIR"] = str(phase_dir)

        remaining = max(1, int(deadline - time.monotonic()))
        timeout = min(phase["timeout_seconds"] or remaining, remaining)
        started_at = utc_now()
        try:
            process = subprocess.run(
                phase["command"],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                env=environment,
                timeout=timeout,
            )
            return_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr
            termination: dict[str, Any] = {"reason": "completed"}
        except subprocess.TimeoutExpired as exc:
            return_code = TIMEOUT_RETURN_CODE
            stdout = timeout_text(exc.stdout)
            stderr = timeout_text(exc.stderr)
            termination = {"reason": "timeout", "max_wall_time_seconds": timeout}
        finished_at = utc_now()
        (phase_dir / "stdout.log").write_text(stdout, encoding="utf-8")
        (phase_dir / "stderr.log").write_text(stderr, encoding="utf-8")
        stdout_parts.append(f"===== {identifier} =====\n{stdout}")
        stderr_parts.append(f"===== {identifier} =====\n{stderr}")
        artifacts, errors = snapshot_outputs(root, phase_dir, phase["outputs"])
        if return_code == 0 and errors:
            return_code = OUTPUT_CONTRACT_RETURN_CODE
            termination = {"reason": "output_contract_failed"}
        status = "succeeded" if return_code == 0 else "failed"
        record = {
            "id": identifier,
            "status": status,
            "depends_on": list(phase["depends_on"]),
            "asset_phase": phase["asset_phase"],
            "command": list(phase["command"]),
            "return_code": return_code,
            "started_at": started_at,
            "finished_at": finished_at,
            "termination": termination,
            "asset_bindings": preflight,
            "artifacts": artifacts,
            "errors": errors,
        }
        write_json(phase_dir / "result.json", record)
        results.append(record)
        if return_code != 0:
            overall_return_code = return_code
            blocked = True

    if overall_return_code == 0 and any(record["status"] == "incomplete" for record in results):
        overall_return_code = OUTPUT_CONTRACT_RETURN_CODE
    recovery = {
        "mode": "phase_retry" if retry_phase else "new_run",
        "retry_phase": retry_phase,
        "source_run_id": (parent_manifest or {}).get("run_id"),
        "reused_artifacts": reused_artifacts,
        "generation_skipped": any(
            record["status"] == "reused" and record.get("asset_phase") == "generation"
            for record in results
        ),
    }
    return {
        "phases": results,
        "stdout": "".join(stdout_parts),
        "stderr": "".join(stderr_parts),
        "return_code": overall_return_code,
        "termination": {
            "reason": "completed" if overall_return_code == 0 else "phase_failed"
        },
        "recovery": recovery,
        "artifacts": [artifact for record in results for artifact in record.get("artifacts", [])],
    }
