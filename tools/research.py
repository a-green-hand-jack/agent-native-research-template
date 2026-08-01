from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
REQUIRED_EXPERIMENT_FIELDS = {
    "schema_version",
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
SCHEMA_DOCUMENTS = {
    "experiment": "schemas/experiment.schema.json",
    "environment": "schemas/environment.schema.json",
    "evaluation": "schemas/evaluation.schema.json",
    "executor": "schemas/executor.schema.json",
    "run manifest": "schemas/run-manifest.schema.json",
}


class SpecError(ValueError):
    """Raised when a research definition is incomplete or inconsistent."""


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


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError(f"{path} must contain a JSON object")
    return data


def relative_name(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def validate_identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise SpecError(
            f"{field} must match {ID_PATTERN.pattern!r}; use lowercase stable identifiers"
        )
    return value


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
        identifier = cells[0].strip("`")
        validate_identifier(identifier, "contribution ID")
        if identifier in identifiers:
            raise SpecError(f"duplicate contribution ID in CONTRIBUTIONS.md: {identifier}")
        identifiers.add(identifier)
    if not identifiers:
        raise SpecError("CONTRIBUTIONS.md contains no contribution IDs")
    return identifiers


def yaml_paths(root: Path, directory: str) -> list[Path]:
    base = root / directory
    if not base.is_dir():
        raise SpecError(f"required definition directory is missing: {directory}")
    return sorted(path for path in base.rglob("*") if path.suffix in {".yaml", ".yml"})


def record_index(root: Path, directory: str, kind: str) -> dict[str, tuple[Path, dict[str, Any]]]:
    records: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in yaml_paths(root, directory):
        record = load_yaml(path)
        if record.get("schema_version") != SCHEMA_VERSION:
            raise SpecError(
                f"{relative_name(path, root)} {kind} schema_version must be {SCHEMA_VERSION}"
            )
        identifier = validate_identifier(record.get("id"), f"{kind} ID")
        if identifier in records:
            first = relative_name(records[identifier][0], root)
            second = relative_name(path, root)
            raise SpecError(f"duplicate {kind} ID {identifier!r}: {first}, {second}")
        records[identifier] = (path, record)
    if not records:
        raise SpecError(f"no {kind} definitions found under {directory}/")
    return records


def positive_integer(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SpecError(f"{field} must be a positive integer")
    return value


def validate_string_list(value: object, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise SpecError(f"{field} must be a list of non-empty strings")
    if not value and not allow_empty:
        raise SpecError(f"{field} must not be empty")
    return value


def validate_environment(record: dict[str, Any], path: Path, root: Path) -> None:
    validate_identifier(record.get("id"), "environment ID")
    for field in ("backend", "purpose"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise SpecError(f"{relative_name(path, root)} {field} must be a non-empty string")
    repository_path(root, record.get("lockfile"), "environment lockfile")


def validate_executor(record: dict[str, Any], path: Path, root: Path) -> None:
    validate_identifier(record.get("id"), "executor ID")
    if not isinstance(record.get("executor"), str) or not record["executor"].strip():
        raise SpecError(f"{relative_name(path, root)} executor must be a non-empty string")
    validate_string_list(record.get("capabilities"), "executor capabilities")


def validate_metric(metric: object, evaluation_path: Path, root: Path) -> str:
    if not isinstance(metric, dict):
        raise SpecError(f"{relative_name(evaluation_path, root)} metrics must contain mappings")
    metric_id = validate_identifier(metric.get("id"), "metric ID")
    metric_type = metric.get("type")
    if metric_type not in {"boolean", "integer", "number", "string"}:
        raise SpecError(f"metric {metric_id!r} type must be boolean, integer, number, or string")
    direction = metric.get("direction")
    if direction not in {"maximize", "minimize", "none"}:
        raise SpecError(f"metric {metric_id!r} direction must be maximize, minimize, or none")
    source = metric.get("source")
    if not isinstance(source, dict):
        raise SpecError(f"metric {metric_id!r} source must be a mapping")
    source_type = source.get("type")
    if source_type == "return_code":
        if metric_type not in {"boolean", "integer"}:
            raise SpecError(f"return_code metric {metric_id!r} must be boolean or integer")
    elif source_type == "stdout_regex":
        if not isinstance(source.get("pattern"), str) or not source["pattern"]:
            raise SpecError(f"stdout_regex metric {metric_id!r} requires a pattern")
    elif source_type == "json_file":
        for field in ("path", "key"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise SpecError(f"json_file metric {metric_id!r} requires {field}")
        raw = Path(source["path"])
        if raw.is_absolute() or ".." in raw.parts:
            raise SpecError(f"json_file metric {metric_id!r} path must be repository-relative")
    else:
        raise SpecError(
            f"metric {metric_id!r} source.type must be return_code, stdout_regex, or json_file"
        )
    return metric_id


def validate_evaluation(record: dict[str, Any], path: Path, root: Path) -> None:
    validate_identifier(record.get("id"), "evaluation ID")
    command_argv(record.get("command"))
    if not isinstance(record.get("purpose"), str) or not record["purpose"].strip():
        raise SpecError(f"{relative_name(path, root)} purpose must be a non-empty string")
    metrics = record.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise SpecError(f"{relative_name(path, root)} metrics must be a non-empty list")
    seen: set[str] = set()
    for metric in metrics:
        metric_id = validate_metric(metric, path, root)
        if metric_id in seen:
            raise SpecError(f"duplicate metric ID {metric_id!r} in {relative_name(path, root)}")
        seen.add(metric_id)


def validate_seed_policy(value: object) -> None:
    if not isinstance(value, dict):
        raise SpecError("seed_policy must be a mapping")
    mode = value.get("mode")
    if mode == "fixed":
        seeds = value.get("seeds")
        if (
            not isinstance(seeds, list)
            or not seeds
            or not all(isinstance(seed, int) and not isinstance(seed, bool) for seed in seeds)
        ):
            raise SpecError("fixed seed_policy requires a non-empty integer seeds list")
        if len(seeds) != len(set(seeds)):
            raise SpecError("fixed seed_policy seeds must be unique")
    elif mode == "random":
        positive_integer(value.get("count"), "random seed_policy count")
    elif mode == "range":
        start = value.get("start")
        stop = value.get("stop")
        if not all(isinstance(item, int) and not isinstance(item, bool) for item in (start, stop)):
            raise SpecError("range seed_policy start and stop must be integers")
        if start >= stop:
            raise SpecError("range seed_policy start must be less than stop")
    else:
        raise SpecError("seed_policy.mode must be fixed, random, or range")


def validate_budget(value: object) -> None:
    if not isinstance(value, dict):
        raise SpecError("budget must be a mapping")
    recognized = False
    for field in ("max_runs", "max_wall_time_seconds", "max_cost_units"):
        if field in value:
            positive_integer(value[field], f"budget.{field}")
            recognized = True
    if not recognized:
        raise SpecError("budget must declare max_runs, max_wall_time_seconds, or max_cost_units")


def validate_stopping_rule(value: object) -> None:
    if not isinstance(value, dict):
        raise SpecError("stopping_rule must be a mapping")
    rule_type = value.get("type")
    if rule_type == "after_runs":
        positive_integer(value.get("runs"), "stopping_rule.runs")
    elif rule_type == "budget_exhausted":
        pass
    elif rule_type == "metric_threshold":
        validate_identifier(value.get("metric"), "stopping_rule metric")
        if value.get("operator") not in {">", ">=", "<", "<=", "=="}:
            raise SpecError("metric_threshold stopping_rule operator is invalid")
        if not isinstance(value.get("value"), int | float) or isinstance(value.get("value"), bool):
            raise SpecError("metric_threshold stopping_rule value must be numeric")
    else:
        raise SpecError(
            "stopping_rule.type must be after_runs, budget_exhausted, or metric_threshold"
        )


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


def validate_schema_documents(root: Path) -> None:
    for kind, relative_path in SCHEMA_DOCUMENTS.items():
        path = root / relative_path
        document = load_json(path)
        if document.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            raise SpecError(f"{relative_path} must use JSON Schema draft 2020-12")
        if document.get("x-schema-version") != SCHEMA_VERSION:
            raise SpecError(f"{relative_path} x-schema-version must be {SCHEMA_VERSION}")
        if not isinstance(document.get("title"), str) or not document["title"].strip():
            raise SpecError(f"{kind} schema has no title: {relative_path}")


def validate_spec(
    path: Path,
    root: Path = ROOT,
    *,
    environments: dict[str, tuple[Path, dict[str, Any]]] | None = None,
    evaluations: dict[str, tuple[Path, dict[str, Any]]] | None = None,
    executors: dict[str, tuple[Path, dict[str, Any]]] | None = None,
    contributions: set[str] | None = None,
) -> dict[str, Any]:
    path = path.resolve()
    root = root.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SpecError(f"spec must be inside the repository: {path}") from exc

    environments = environments or record_index(root, "environments", "environment")
    evaluations = evaluations or record_index(root, "evals", "evaluation")
    executors = executors or record_index(root, "infra/profiles", "executor")
    contributions = contributions or contribution_ids(root)

    for definition_path, definition in environments.values():
        validate_environment(definition, definition_path, root)
    for definition_path, definition in evaluations.values():
        validate_evaluation(definition, definition_path, root)
    for definition_path, definition in executors.values():
        validate_executor(definition, definition_path, root)

    spec = load_yaml(path)
    missing = REQUIRED_EXPERIMENT_FIELDS - spec.keys()
    if missing:
        raise SpecError(f"{relative_name(path, root)} missing fields: {', '.join(sorted(missing))}")
    if spec.get("schema_version") != SCHEMA_VERSION:
        raise SpecError(f"{relative_name(path, root)} schema_version must be {SCHEMA_VERSION}")

    validate_identifier(spec.get("id"), "experiment ID")
    for field in ("question", "contribution", "environment", "executor", "evaluation"):
        if not isinstance(spec.get(field), str) or not spec[field].strip():
            raise SpecError(f"{field} must be a non-empty string")
    validate_identifier(spec["contribution"], "contribution ID")
    validate_identifier(spec["environment"], "environment ID")
    validate_identifier(spec["executor"], "executor ID")
    validate_identifier(spec["evaluation"], "evaluation ID")
    validate_seed_policy(spec["seed_policy"])
    validate_budget(spec["budget"])
    validate_stopping_rule(spec["stopping_rule"])
    validate_string_list(spec["inclusion_criteria"], "inclusion_criteria")

    if spec["contribution"] not in contributions:
        raise SpecError(f"unknown contribution ID: {spec['contribution']}")
    if spec["environment"] not in environments:
        raise SpecError(f"unknown environment ID: {spec['environment']}")
    if spec["evaluation"] not in evaluations:
        raise SpecError(f"unknown evaluation ID: {spec['evaluation']}")
    if spec["executor"] not in executors:
        raise SpecError(f"unknown executor ID: {spec['executor']}")

    config_path = repository_path(root, spec["config"], "config")
    environment_path, environment = environments[spec["environment"]]
    evaluation_path, evaluation = evaluations[spec["evaluation"]]
    executor_path, executor = executors[spec["executor"]]
    argv = command_argv(spec["command"])
    if command_argv(evaluation["command"]) != argv:
        raise SpecError(
            f"spec command does not match evaluation {spec['evaluation']!r}: "
            f"{evaluation['command']!r}"
        )
    lockfile_path = repository_path(root, environment["lockfile"], "environment lockfile")

    artifacts = spec.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise SpecError("artifacts must be a list")
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise SpecError(f"artifacts[{index}] must be a mapping")
        if not isinstance(artifact.get("path"), str) or not artifact["path"].strip():
            raise SpecError(f"artifacts[{index}].path must be a non-empty string")
        raw = Path(artifact["path"])
        if raw.is_absolute() or ".." in raw.parts:
            raise SpecError(f"artifacts[{index}].path must be repository-relative")
        if "required" in artifact and not isinstance(artifact["required"], bool):
            raise SpecError(f"artifacts[{index}].required must be boolean")

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


def validate_all(root: Path = ROOT, paths: Iterable[Path] | None = None) -> list[Path]:
    root = root.resolve()
    validate_schema_documents(root)
    environments = record_index(root, "environments", "environment")
    evaluations = record_index(root, "evals", "evaluation")
    executors = record_index(root, "infra/profiles", "executor")
    contributions = contribution_ids(root)
    selected = list(paths) if paths is not None else yaml_paths(root, "experiments/specs")
    if not selected:
        raise SpecError("no experiment specs found")

    seen: dict[str, Path] = {}
    for path in selected:
        resolved = validate_spec(
            path,
            root,
            environments=environments,
            evaluations=evaluations,
            executors=executors,
            contributions=contributions,
        )
        identifier = resolved["spec"]["id"]
        if identifier in seen:
            first = relative_name(seen[identifier], root)
            second = relative_name(path, root)
            raise SpecError(f"duplicate experiment ID {identifier!r}: {first}, {second}")
        seen[identifier] = path
    return selected


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
        for relative_path in sorted(untracked_result.stdout.splitlines()):
            file_path = root / relative_path
            if file_path.is_file() and not relative_path.startswith("runs/"):
                untracked.append({"path": relative_path, "sha256": sha256_file(file_path)})

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


def extract_return_code_metrics(
    evaluation: dict[str, Any], return_code: int
) -> dict[str, bool | int]:
    metrics: dict[str, bool | int] = {}
    for metric in evaluation["metrics"]:
        source = metric["source"]
        if source["type"] != "return_code":
            continue
        metrics[metric["id"]] = return_code == 0 if metric["type"] == "boolean" else return_code
    return metrics


def run_experiment(path: Path, root: Path = ROOT) -> tuple[Path, int]:
    validate_schema_documents(root)
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
        return relative_name(value, root) if value is not None else None

    manifest = {
        "schema_version": SCHEMA_VERSION,
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
            "lockfile_sha256": sha256_file(resolved["lockfile_path"]),
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
        "metrics": extract_return_code_metrics(resolved["evaluation"], process.returncode),
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
    elif candidate.suffix == ".json" or (candidate.parts and candidate.parts[0] == "runs"):
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
    manifest = load_json(source)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise SpecError(f"manifest schema_version must be {SCHEMA_VERSION}: {source}")
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise SpecError(f"manifest has no run_id: {source}")
    destination = root / "evidence" / "manifests" / f"{run_id}.json"
    if destination.exists():
        raise SpecError(f"evidence manifest already exists: {relative_name(destination, root)}")
    write_json(destination, manifest)
    return destination


def spec_paths(root: Path, values: list[str]) -> list[Path]:
    if values:
        return [root / value for value in values]
    return yaml_paths(root, "experiments/specs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and execute versioned reproducible research specifications."
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
            validate_all(root, paths)
            for path in paths:
                print(f"OK {relative_name(path, root)}")
            return 0
        if args.command_name == "run":
            manifest_path, return_code = run_experiment(root / args.spec, root)
            print(relative_name(manifest_path, root))
            return return_code
        if args.command_name == "promote":
            destination = promote_manifest(args.run, root)
            print(relative_name(destination, root))
            return 0
    except (SpecError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
