from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import experiment_plan
import input_identity
import research

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DECISIONS = ("accepted", "rejected", "inconclusive")
SEED_ENVIRONMENT_VARIABLE = "RESEARCH_SEED"
TIMEOUT_RETURN_CODE = 124


class EvidenceError(ValueError):
    """Raised when a run cannot be executed, verified, replayed, or promoted."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_key(data: object, key: str) -> object:
    current = data
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise EvidenceError(f"JSON metric key does not exist: {key}")
    return current


def coerce_metric(value: object, metric_type: str, metric_id: str) -> bool | int | float | str:
    if metric_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
    elif metric_type == "integer":
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str):
            return int(value)
    elif metric_type == "number":
        if isinstance(value, int | float) and not isinstance(value, bool):
            return value
        if isinstance(value, str):
            return float(value)
    elif metric_type == "string" and isinstance(value, str):
        return value
    raise EvidenceError(f"metric {metric_id!r} cannot be coerced to {metric_type}")


def extract_metrics(
    evaluation: dict[str, Any],
    *,
    return_code: int,
    stdout: str,
    root: Path,
) -> tuple[dict[str, bool | int | float | str], list[str]]:
    metrics: dict[str, bool | int | float | str] = {}
    errors: list[str] = []
    for metric in evaluation["metrics"]:
        metric_id = metric["id"]
        metric_type = metric["type"]
        source = metric["source"]
        try:
            if source["type"] == "return_code":
                raw: object = return_code == 0 if metric_type == "boolean" else return_code
            elif source["type"] == "stdout_regex":
                match = re.search(source["pattern"], stdout, re.MULTILINE)
                if match is None:
                    raise EvidenceError(f"metric {metric_id!r} pattern did not match stdout")
                group = source.get("group", 1 if match.lastindex else 0)
                raw = match.group(group)
            elif source["type"] == "json_file":
                path = root / source["path"]
                if not path.is_file():
                    raise EvidenceError(
                        f"metric {metric_id!r} JSON file is missing: {source['path']}"
                    )
                raw = read_key(json.loads(path.read_text(encoding="utf-8")), source["key"])
            else:
                raise EvidenceError(f"metric {metric_id!r} has unsupported source")
            metrics[metric_id] = coerce_metric(raw, metric_type, metric_id)
        except (EvidenceError, OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
    return metrics, errors


def supported_execution_controls(spec: dict[str, Any]) -> tuple[int, int]:
    seed_policy = spec["seed_policy"]
    if seed_policy.get("mode") != "fixed" or len(seed_policy.get("seeds", [])) != 1:
        raise EvidenceError(
            "the local runner supports exactly one fixed seed; use an external scheduler for "
            "multi-seed, range, or random execution"
        )
    seed = seed_policy["seeds"][0]

    budget = spec["budget"]
    if budget.get("max_runs", 1) != 1:
        raise EvidenceError(
            "the local runner supports exactly one execution; use an external scheduler for "
            "max_runs greater than 1"
        )
    if "max_cost_units" in budget:
        raise EvidenceError(
            "the local runner has no cost accounting and cannot enforce budget.max_cost_units"
        )
    timeout = budget.get("max_wall_time_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise EvidenceError(
            "the local runner requires a positive budget.max_wall_time_seconds so every run is "
            "bounded"
        )

    stopping_rule = spec["stopping_rule"]
    if stopping_rule.get("type") != "after_runs" or stopping_rule.get("runs") != 1:
        raise EvidenceError(
            "the local runner supports only stopping_rule {type: after_runs, runs: 1}; use an "
            "external scheduler for budget- or metric-driven stopping"
        )
    return seed, timeout


def validate_supported_spec(spec_path: Path, root: Path = ROOT) -> dict[str, Any]:
    resolved = research.validate_spec(spec_path, root)
    plan = experiment_plan.build_plan(resolved)
    if len(plan["resolved"]["cells"]) != 1:
        raise EvidenceError(
            "the local runner executes exactly one plan cell; use an external scheduler "
            "for matrix plans"
        )
    seed, timeout = supported_execution_controls(resolved["spec"])
    return {
        **resolved,
        "seed": seed,
        "timeout": timeout,
        "plan": plan["resolved"],
        "plan_sha256": plan["sha256"],
    }


def timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def run_once(spec_path: Path, root: Path = ROOT) -> tuple[Path, int]:
    resolved = validate_supported_spec(spec_path, root)
    spec = resolved["spec"]
    seed = resolved["seed"]
    timeout = resolved["timeout"]
    git = research.git_state(root)
    head_label = (git["commit"] or "nogit")[:8]
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}-{spec['id']}-{head_label}-{uuid.uuid4().hex[:8]}"
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    environment = os.environ.copy()
    environment[SEED_ENVIRONMENT_VARIABLE] = str(seed)
    started_at = utc_now()
    try:
        process = subprocess.run(
            resolved["argv"],
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
        termination = {"reason": "completed"}
    except subprocess.TimeoutExpired as exc:
        return_code = TIMEOUT_RETURN_CODE
        stdout = timeout_text(exc.stdout)
        stderr = timeout_text(exc.stderr)
        termination = {
            "reason": "timeout",
            "max_wall_time_seconds": timeout,
        }
    finished_at = utc_now()

    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")

    def relative(value: Path | None) -> str | None:
        return research.relative_name(value, root) if value is not None else None

    manifest = {
        "schema_version": research.SCHEMA_VERSION,
        "run_id": run_id,
        "parent_run_id": None,
        "status": "succeeded" if return_code == 0 else "failed",
        "started_at": started_at,
        "finished_at": finished_at,
        "return_code": return_code,
        "termination": termination,
        "seed": seed,
        "seed_environment_variable": SEED_ENVIRONMENT_VARIABLE,
        "question": spec["question"],
        "contribution": spec["contribution"],
        "plan": {
            "sha256": resolved["plan_sha256"],
            "resolved": resolved["plan"],
        },
        "config": {
            "path": relative(resolved["config_path"]),
            "sha256": research.sha256_file(resolved["config_path"]),
        },
        "data": spec.get("data"),
        "inputs": resolved["inputs"],
        "spec": {
            "path": relative(resolved["spec_path"]),
            "sha256": research.sha256_file(resolved["spec_path"]),
            "resolved": spec,
        },
        "git": git,
        "environment": {
            "id": spec["environment"],
            "definition": relative(resolved["environment_path"]),
            "definition_sha256": research.sha256_file(resolved["environment_path"]),
            "lockfile": relative(resolved["lockfile_path"]),
            "lockfile_sha256": research.sha256_file(resolved["lockfile_path"]),
        },
        "executor": {
            "id": spec["executor"],
            "definition": relative(resolved["executor_path"]),
            "definition_sha256": research.sha256_file(resolved["executor_path"]),
        },
        "evaluation": {
            "id": spec["evaluation"],
            "definition": relative(resolved["evaluation_path"]),
            "definition_sha256": research.sha256_file(resolved["evaluation_path"]),
        },
        "hardware": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
        },
        "command": resolved["argv"],
        "metrics": research.extract_return_code_metrics(resolved["evaluation"], return_code),
        "artifacts": [
            {"path": relative(stdout_path), "sha256": research.sha256_file(stdout_path)},
            {"path": relative(stderr_path), "sha256": research.sha256_file(stderr_path)},
        ],
    }
    manifest_path = run_dir / "manifest.json"
    research.validate_document(manifest, "run manifest", manifest_path, root)
    research.write_json(manifest_path, manifest)
    return manifest_path, return_code


def declared_artifacts(
    spec: dict[str, Any],
    root: Path,
    run_dir: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    resolved_root = root.resolve()
    for declaration in spec.get("artifacts", []):
        pattern = declaration["path"]
        matches = sorted(path for path in root.glob(pattern) if path.is_file())
        if declaration.get("required", False) and not matches:
            errors.append(f"required artifact pattern matched no files: {pattern}")
        for path in matches:
            try:
                resolved_source = path.resolve()
                resolved_source.relative_to(resolved_root)
                relative = research.relative_name(path, root)
            except ValueError:
                errors.append(f"declared artifact resolves outside the repository: {path}")
                continue
            if relative in seen or relative.startswith("runs/"):
                continue
            seen.add(relative)
            destination = run_dir / "artifacts" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resolved_source, destination)
            records.append(
                {
                    "path": research.relative_name(destination, root),
                    "source_path": relative,
                    "sha256": research.sha256_file(destination),
                    "kind": declaration.get("kind", "declared"),
                }
            )
    return records, errors


def enrich_manifest(
    manifest_path: Path,
    root: Path,
    *,
    parent_run_id: str | None,
) -> tuple[Path, int]:
    manifest = research.load_json(manifest_path)
    run_dir = manifest_path.parent
    stdout_path = root / manifest["artifacts"][0]["path"]
    evaluation_path = root / manifest["evaluation"]["definition"]
    evaluation = research.load_yaml(evaluation_path)
    metrics, errors = extract_metrics(
        evaluation,
        return_code=manifest["return_code"],
        stdout=stdout_path.read_text(encoding="utf-8"),
        root=root,
    )
    artifacts, artifact_errors = declared_artifacts(
        manifest["spec"]["resolved"],
        root,
        run_dir,
    )
    errors.extend(artifact_errors)
    existing = {artifact["path"] for artifact in manifest["artifacts"]}
    manifest["artifacts"].extend(
        artifact for artifact in artifacts if artifact["path"] not in existing
    )
    manifest["metrics"] = metrics
    manifest["evaluation_errors"] = errors
    manifest["parent_run_id"] = parent_run_id
    manifest["status"] = "succeeded" if manifest["return_code"] == 0 and not errors else "failed"
    research.validate_document(manifest, "run manifest", manifest_path, root)
    research.write_json(manifest_path, manifest)
    return manifest_path, manifest["return_code"] or (3 if errors else 0)


def run_spec(
    spec_path: Path,
    root: Path = ROOT,
    *,
    parent_run_id: str | None = None,
) -> tuple[Path, int]:
    if parent_run_id is not None:
        parent = verify_run(parent_run_id, root)
        if parent["run_id"] != parent_run_id:
            raise EvidenceError("parent run identity does not match its manifest")
    manifest_path, _ = run_once(spec_path, root)
    return enrich_manifest(manifest_path, root, parent_run_id=parent_run_id)


def verify_run(value: str, root: Path = ROOT) -> dict[str, Any]:
    source = research.resolve_manifest(root, value)
    manifest = research.load_json(source)
    research.validate_document(manifest, "run manifest", source, root)
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise EvidenceError(f"manifest has no run_id: {source}")
    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict):
            raise EvidenceError(f"manifest artifact is not a mapping: {source}")
        relative = artifact.get("path")
        expected = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise EvidenceError(f"manifest artifact is incomplete: {source}")
        path = root / relative
        if not path.is_file():
            raise EvidenceError(f"artifact is missing: {relative}")
        if research.sha256_file(path) != expected:
            raise EvidenceError(f"artifact checksum mismatch: {relative}")
    return manifest


def recorded_input_drift(manifest: dict[str, Any], root: Path) -> list[str]:
    checks = [
        (manifest["spec"]["path"], manifest["spec"]["sha256"], "spec"),
        (manifest["config"]["path"], manifest["config"]["sha256"], "config"),
        (
            manifest["environment"]["definition"],
            manifest["environment"]["definition_sha256"],
            "environment definition",
        ),
        (
            manifest["environment"]["lockfile"],
            manifest["environment"]["lockfile_sha256"],
            "environment lockfile",
        ),
        (
            manifest["executor"]["definition"],
            manifest["executor"]["definition_sha256"],
            "executor definition",
        ),
        (
            manifest["evaluation"]["definition"],
            manifest["evaluation"]["definition_sha256"],
            "evaluation definition",
        ),
    ]
    drift: list[str] = []
    for relative, expected, label in checks:
        path = root / relative
        if not path.is_file():
            drift.append(f"{label} is missing: {relative}")
        elif research.sha256_file(path) != expected:
            drift.append(f"{label} changed: {relative}")
    drift.extend(input_identity.recorded_input_drift(manifest.get("inputs", []), root))
    return drift


def replay_run(
    value: str,
    root: Path = ROOT,
    *,
    allow_drift: bool = False,
) -> tuple[Path, int]:
    manifest = verify_run(value, root)
    drift = recorded_input_drift(manifest, root)
    if drift and not allow_drift:
        raise EvidenceError("recorded inputs drifted: " + "; ".join(drift))
    return run_spec(root / manifest["spec"]["path"], root, parent_run_id=manifest["run_id"])


def promote_manifest(
    value: str,
    root: Path = ROOT,
    *,
    decision: str,
    note: str | None = None,
) -> Path:
    if decision not in REVIEW_DECISIONS:
        raise EvidenceError(f"review decision must be one of: {', '.join(REVIEW_DECISIONS)}")
    source = research.resolve_manifest(root, value)
    manifest = verify_run(value, root)
    destination = root / "evidence" / "manifests" / f"{manifest['run_id']}.json"
    if destination.exists():
        raise EvidenceError(
            f"evidence manifest already exists: {research.relative_name(destination, root)}"
        )
    envelope = {
        "schema_version": research.SCHEMA_VERSION,
        "evidence_version": 1,
        "run_id": manifest["run_id"],
        "promoted_at": utc_now(),
        "source": {
            "path": research.relative_name(source, root),
            "sha256": research.sha256_file(source),
        },
        "review": {"decision": decision, "note": note},
        "manifest": manifest,
    }
    research.validate_document(envelope, "evidence manifest", destination, root)
    research.write_json(destination, envelope)
    return destination


def validate_specs(values: list[str], root: Path = ROOT) -> list[Path]:
    paths = research.spec_paths(root, values)
    research.validate_all(root, paths)
    for path in paths:
        validate_supported_spec(path, root)
    return paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate, run, verify, replay, and promote evidence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate",
        help="validate research definitions and local-runner execution controls",
    )
    validate.add_argument("specs", nargs="*")

    plan = subparsers.add_parser("plan", help="emit a deterministic side-effect-free plan")
    plan.add_argument("spec")

    run = subparsers.add_parser("run", help="run one supported spec with full evidence extraction")
    run.add_argument("spec")
    run.add_argument("--parent")

    replay = subparsers.add_parser("replay", help="replay a run after checking input drift")
    replay.add_argument("run")
    replay.add_argument("--allow-drift", action="store_true")

    verify = subparsers.add_parser("verify-run", help="verify every recorded artifact")
    verify.add_argument("run")

    promote = subparsers.add_parser("promote", help="promote a reviewed run into evidence")
    promote.add_argument("run")
    promote.add_argument("--decision", choices=REVIEW_DECISIONS, required=True)
    promote.add_argument("--note")
    return parser


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            paths = validate_specs(args.specs, root)
            for path in paths:
                print(f"OK {research.relative_name(path, root)}")
            return 0
        if args.command == "plan":
            print(experiment_plan.render_plan(root / args.spec, root), end="")
            return 0
        if args.command == "run":
            path, code = run_spec(root / args.spec, root, parent_run_id=args.parent)
            print(research.relative_name(path, root))
            return code
        if args.command == "replay":
            path, code = replay_run(args.run, root, allow_drift=args.allow_drift)
            print(research.relative_name(path, root))
            return code
        if args.command == "verify-run":
            manifest = verify_run(args.run, root)
            print(f"OK {manifest['run_id']}")
            return 0
        if args.command == "promote":
            destination = promote_manifest(
                args.run,
                root,
                decision=args.decision,
                note=args.note,
            )
            print(research.relative_name(destination, root))
            return 0
    except (
        EvidenceError,
        experiment_plan.PlanError,
        research.SpecError,
        OSError,
        ValueError,
    ) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
