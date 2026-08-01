from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIELDS = {
    "id",
    "question",
    "contribution",
    "config",
    "environment",
    "executor",
    "evaluation",
    "command",
    "seed_policy",
    "budget",
    "stopping_rule",
    "inclusion_criteria",
}


class SpecError(ValueError):
    """Raised when an experiment specification is incomplete or inconsistent."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SpecError(f"cannot read YAML {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError(f"{path} must contain a YAML mapping")
    return data


def repository_path(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{field} must be a non-empty repository-relative path")
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts or "\\" in value:
        raise SpecError(f"{field} must be a normalized repository-relative path: {value!r}")
    path = root / raw
    if not path.is_file():
        raise SpecError(f"{field} does not exist: {value}")
    return path


def contribution_ids(root: Path) -> set[str]:
    path = root / "CONTRIBUTIONS.md"
    if not path.is_file():
        raise SpecError("CONTRIBUTIONS.md is missing")
    identifiers: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or cells[0] in {"ID", "---"} or set(cells[0]) == {"-"}:
            continue
        identifiers.add(cells[0].strip("`"))
    return identifiers


def yaml_records(root: Path, pattern: str) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob(pattern)):
        if path.is_file():
            records.append((path, load_yaml(path)))
    return records


def record_by_id(
    root: Path, pattern: str, identifier: object, kind: str
) -> tuple[Path, dict[str, Any]]:
    if not isinstance(identifier, str) or not identifier.strip():
        raise SpecError(f"{kind} must be a non-empty ID")
    matches = [
        record for record in yaml_records(root, pattern) if record[1].get("id") == identifier
    ]
    if not matches:
        raise SpecError(f"unknown {kind} ID: {identifier}")
    if len(matches) > 1:
        paths = ", ".join(str(path.relative_to(root)) for path, _ in matches)
        raise SpecError(f"duplicate {kind} ID {identifier!r}: {paths}")
    return matches[0]


def executor_record(root: Path, identifier: object) -> tuple[Path, dict[str, Any]]:
    if not isinstance(identifier, str) or not identifier.strip():
        raise SpecError("executor must be a non-empty ID")
    matches = [
        record
        for record in yaml_records(root, "infra/profiles/**/*.yaml")
        if identifier in {record[1].get("id"), record[1].get("executor")}
    ]
    if not matches:
        raise SpecError(f"unknown executor ID: {identifier}")
    if len(matches) > 1:
        paths = ", ".join(str(path.relative_to(root)) for path, _ in matches)
        raise SpecError(f"ambiguous executor ID {identifier!r}: {paths}")
    return matches[0]


def command_argv(value: object) -> list[str]:
    if isinstance(value, str):
        argv = shlex.split(value)
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        argv = list(value)
    else:
        raise SpecError("command must be a shell-style string or a list of strings")
    if not argv:
        raise SpecError("command must not be empty")
    return argv


def validate_spec(path: Path, root: Path = ROOT) -> dict[str, Any]:
    path = path.resolve()
    root = root.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SpecError(f"spec must be inside the repository: {path}") from exc

    spec = load_yaml(path)
    missing = REQUIRED_FIELDS - spec.keys()
    if missing:
        raise SpecError(f"{path.relative_to(root)} missing fields: {', '.join(sorted(missing))}")

    for field in ("id", "question", "contribution", "environment", "executor", "evaluation"):
        if not isinstance(spec[field], str) or not spec[field].strip():
            raise SpecError(f"{field} must be a non-empty string")
    for field in ("stopping_rule", "inclusion_criteria"):
        if not isinstance(spec[field], str) or not spec[field].strip():
            raise SpecError(f"{field} must be a non-empty string")
    if not isinstance(spec["seed_policy"], dict) or not spec["seed_policy"]:
        raise SpecError("seed_policy must be a non-empty mapping")
    if not isinstance(spec["budget"], dict) or not spec["budget"]:
        raise SpecError("budget must be a non-empty mapping")

    if spec["contribution"] not in contribution_ids(root):
        raise SpecError(f"unknown contribution ID: {spec['contribution']}")
    config_path = repository_path(root, spec["config"], "config")
    environment_path, environment = record_by_id(
        root, "environments/**/*.yaml", spec["environment"], "environment"
    )
    evaluation_path, evaluation = record_by_id(
        root, "evals/**/*.yaml", spec["evaluation"], "evaluation"
    )
    executor_path, executor = executor_record(root, spec["executor"])
    argv = command_argv(spec["command"])

    evaluation_command = evaluation.get("command")
    if evaluation_command is not None and command_argv(evaluation_command) != argv:
        raise SpecError(
            f"spec command does not match evaluation {spec['evaluation']!r}: {evaluation_command!r}"
        )

    lockfile = environment.get("lockfile")
    lockfile_path = repository_path(root, lockfile, "environment lockfile") if lockfile else None

    return {
        "spec": spec,
        "spec_path": path,
        "config_path": config_path,
        "environment_path": environment_path,
        "environment": environment,
        "evaluation_path": evaluation_path,
        "evaluation": evaluation,
        "executor_path": executor_path,
        "executor": executor,
        "lockfile_path": lockfile_path,
        "argv": argv,
    }


def git_output(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )


def git_state(root: Path) -> dict[str, Any]:
    head_result = git_output(root, "rev-parse", "HEAD")
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    status_result = git_output(root, "status", "--porcelain=v1", "--untracked-files=all")
    status = status_result.stdout if status_result.returncode == 0 else ""
    diff_result = git_output(root, "diff", "--binary", "HEAD")
    diff = diff_result.stdout if diff_result.returncode == 0 else ""

    untracked: list[dict[str, str]] = []
    untracked_result = git_output(root, "ls-files", "--others", "--exclude-standard")
    if untracked_result.returncode == 0:
        for relative_name in sorted(untracked_result.stdout.splitlines()):
            file_path = root / relative_name
            if file_path.is_file() and not relative_name.startswith("runs/"):
                untracked.append({"path": relative_name, "sha256": sha256_file(file_path)})

    patch_payload = json.dumps(
        {"diff": diff, "untracked": untracked}, sort_keys=True, separators=(",", ":")
    ).encode()
    return {
        "commit": head,
        "dirty": bool(status.strip()),
        "status": status.splitlines(),
        "patch_sha256": sha256_bytes(patch_payload),
    }


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run_experiment(path: Path, root: Path = ROOT) -> tuple[Path, int]:
    resolved = validate_spec(path, root)
    spec = resolved["spec"]
    git = git_state(root)
    head_label = (git["commit"] or "nogit")[:8]
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}-{spec['id']}-{head_label}-{uuid.uuid4().hex[:8]}"
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    started_at = utc_now()
    process = subprocess.run(
        resolved["argv"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    finished_at = utc_now()

    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    stdout_path.write_text(process.stdout, encoding="utf-8")
    stderr_path.write_text(process.stderr, encoding="utf-8")

    def relative(value: Path | None) -> str | None:
        return str(value.relative_to(root)) if value is not None else None

    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "parent_run_id": None,
        "status": "succeeded" if process.returncode == 0 else "failed",
        "started_at": started_at,
        "finished_at": finished_at,
        "return_code": process.returncode,
        "question": spec["question"],
        "contribution": spec["contribution"],
        "config": {
            "path": relative(resolved["config_path"]),
            "sha256": sha256_file(resolved["config_path"]),
        },
        "data": spec.get("data"),
        "spec": {
            "path": relative(resolved["spec_path"]),
            "sha256": sha256_file(resolved["spec_path"]),
            "resolved": spec,
        },
        "git": git,
        "environment": {
            "id": spec["environment"],
            "definition": relative(resolved["environment_path"]),
            "definition_sha256": sha256_file(resolved["environment_path"]),
            "lockfile": relative(resolved["lockfile_path"]),
            "lockfile_sha256": (
                sha256_file(resolved["lockfile_path"]) if resolved["lockfile_path"] else None
            ),
        },
        "executor": {
            "id": spec["executor"],
            "definition": relative(resolved["executor_path"]),
            "definition_sha256": sha256_file(resolved["executor_path"]),
        },
        "evaluation": {
            "id": spec["evaluation"],
            "definition": relative(resolved["evaluation_path"]),
            "definition_sha256": sha256_file(resolved["evaluation_path"]),
        },
        "hardware": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
        },
        "command": resolved["argv"],
        "metrics": {"return_code": process.returncode},
        "artifacts": [
            {"path": relative(stdout_path), "sha256": sha256_file(stdout_path)},
            {"path": relative(stderr_path), "sha256": sha256_file(stderr_path)},
        ],
    }
    manifest_path = run_dir / "manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path, process.returncode


def resolve_manifest(root: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        path = candidate
    elif candidate.parts and candidate.parts[0] == "runs":
        path = root / candidate
    elif candidate.suffix == ".json":
        path = root / candidate
    else:
        path = root / "runs" / candidate / "manifest.json"
    path = path.resolve()
    if not path.is_file():
        raise SpecError(f"run manifest does not exist: {value}")
    try:
        path.relative_to((root / "runs").resolve())
    except ValueError as exc:
        raise SpecError("only manifests under runs/ can be promoted") from exc
    return path


def promote_manifest(value: str, root: Path = ROOT) -> Path:
    source = resolve_manifest(root, value)
    manifest = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise SpecError(f"manifest must contain a JSON object: {source}")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise SpecError(f"manifest has no run_id: {source}")
    destination = root / "evidence" / "manifests" / f"{run_id}.json"
    if destination.exists():
        raise SpecError(f"evidence manifest already exists: {destination.relative_to(root)}")
    write_json(destination, manifest)
    return destination


def spec_paths(root: Path, values: list[str]) -> list[Path]:
    if values:
        return [root / value for value in values]
    return sorted((root / "experiments" / "specs").rglob("*.yaml"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and execute reproducible research specs."
    )
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    validate = subparsers.add_parser("validate", help="validate one or all experiment specs")
    validate.add_argument("specs", nargs="*", help="repository-relative spec paths")

    run = subparsers.add_parser("run", help="execute a validated experiment spec")
    run.add_argument("spec", help="repository-relative spec path")

    promote = subparsers.add_parser("promote", help="copy a local run manifest into evidence")
    promote.add_argument("run", help="run ID or manifest path")
    return parser


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command_name == "validate":
            paths = spec_paths(root, args.specs)
            if not paths:
                raise SpecError("no experiment specs found")
            for path in paths:
                validate_spec(path, root)
                print(f"OK {path.relative_to(root)}")
            return 0
        if args.command_name == "run":
            manifest_path, return_code = run_experiment(root / args.spec, root)
            print(manifest_path.relative_to(root))
            return return_code
        if args.command_name == "promote":
            destination = promote_manifest(args.run, root)
            print(destination.relative_to(root))
            return 0
    except (SpecError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
