from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import research

ROOT = Path(__file__).resolve().parents[1]
REVIEW_DECISIONS = ("accepted", "rejected", "inconclusive")


class EvidenceError(ValueError):
    """Raised when a run cannot be verified, replayed, or promoted."""


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


def declared_artifacts(spec: dict[str, Any], root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for declaration in spec.get("artifacts", []):
        pattern = declaration["path"]
        matches = sorted(path for path in root.glob(pattern) if path.is_file())
        if declaration.get("required", False) and not matches:
            errors.append(f"required artifact pattern matched no files: {pattern}")
        for path in matches:
            relative = research.relative_name(path, root)
            if relative in seen or relative.startswith("runs/"):
                continue
            seen.add(relative)
            records.append(
                {
                    "path": relative,
                    "sha256": research.sha256_file(path),
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
    stdout_path = root / manifest["artifacts"][0]["path"]
    evaluation_path = root / manifest["evaluation"]["definition"]
    evaluation = research.load_yaml(evaluation_path)
    metrics, errors = extract_metrics(
        evaluation,
        return_code=manifest["return_code"],
        stdout=stdout_path.read_text(encoding="utf-8"),
        root=root,
    )
    artifacts, artifact_errors = declared_artifacts(manifest["spec"]["resolved"], root)
    errors.extend(artifact_errors)
    existing = {artifact["path"] for artifact in manifest["artifacts"]}
    manifest["artifacts"].extend(
        artifact for artifact in artifacts if artifact["path"] not in existing
    )
    manifest["metrics"] = metrics
    manifest["evaluation_errors"] = errors
    manifest["parent_run_id"] = parent_run_id
    manifest["status"] = "succeeded" if manifest["return_code"] == 0 and not errors else "failed"
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
    manifest_path, _ = research.run_experiment(spec_path, root)
    return enrich_manifest(manifest_path, root, parent_run_id=parent_run_id)


def verify_run(value: str, root: Path = ROOT) -> dict[str, Any]:
    source = research.resolve_manifest(root, value)
    manifest = research.load_json(source)
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
    research.write_json(destination, envelope)
    return destination


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify, replay, and promote research evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="run a spec with full evidence extraction")
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
    except (EvidenceError, research.SpecError, OSError, ValueError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
