from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import input_identity
import research

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_VERSION = 1
ARCHIVE_SCHEMA = Path("schemas/archive-manifest.schema.json")
DEFAULT_ARCHIVE_DIR = Path("archives/local")
TARGET_KINDS = {"run", "worktree", "branch", "provider"}


class ArchiveError(ValueError):
    """Raised when archive evidence or retirement prerequisites are invalid."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArchiveError(f"JSON document must be an object: {path}")
    return value


def schema_validator(root: Path) -> Draft202012Validator:
    schema = read_json(root / ARCHIVE_SCHEMA)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_schema(value: dict[str, Any], source: Path, root: Path) -> None:
    errors = sorted(
        schema_validator(root).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ArchiveError(f"{source} does not match archive schema at {location}: {error.message}")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def path_identity(path: Path) -> tuple[str, str, int]:
    if path.is_symlink():
        raise ArchiveError(f"archive source must not be a symbolic link: {path}")
    if path.is_file():
        return "file", sha256_file(path), 1
    if path.is_dir():
        try:
            digest, count = input_identity.directory_identity(path)
        except input_identity.InputIdentityError as exc:
            raise ArchiveError(str(exc)) from exc
        return "directory", digest, count
    raise ArchiveError(f"archive source is not a file or directory: {path}")


def safe_item_name(identifier: str) -> str:
    rendered = re.sub(r"[^a-zA-Z0-9._-]+", "_", identifier).strip("_")
    return rendered or hashlib.sha256(identifier.encode()).hexdigest()[:16]


def repository_source(root: Path, value: str) -> Path:
    candidate = root / value
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ArchiveError(f"archive source escapes repository: {value}") from exc
    return candidate


def inventory_from_manifest(manifest: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        relative = artifact.get("path")
        expected = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ArchiveError("run artifact record is incomplete")
        path = repository_source(root, relative)
        kind, digest, file_count = path_identity(path)
        if digest != expected:
            raise ArchiveError(f"run artifact checksum mismatch before archive: {relative}")
        source_key = str(path.resolve())
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        items.append(
            {
                "id": f"artifact:{relative}",
                "kind": "run_artifact",
                "source": str(path.resolve()),
                "path_type": kind,
                "sha256": digest,
                "file_count": file_count,
                "reconstructable": True,
                "copies": [],
            }
        )

    bindings = manifest.get("asset_bindings", {}).get("assets", [])
    for binding in bindings:
        if (
            not isinstance(binding, dict)
            or binding.get("kind") != "path"
            or binding.get("access") != "read"
            or binding.get("exists") is False
        ):
            continue
        scope = binding.get("scope", "repository")
        rendered = binding.get("path")
        if not isinstance(rendered, str):
            continue
        path = repository_source(root, rendered) if scope == "repository" else Path(rendered)
        kind, digest, file_count = path_identity(path)
        expected = binding.get("sha256")
        if isinstance(expected, str) and expected != digest:
            raise ArchiveError(
                f"logical asset checksum mismatch before archive: {binding.get('id')}"
            )
        source_key = str(path.resolve())
        if source_key in seen_sources:
            for item in items:
                if item["source"] == source_key and binding.get("reconstructable") is False:
                    item["reconstructable"] = False
                    item["logical_asset_id"] = binding.get("id")
            continue
        seen_sources.add(source_key)
        items.append(
            {
                "id": f"asset:{binding.get('id')}",
                "kind": "logical_asset",
                "logical_asset_id": binding.get("id"),
                "source": source_key,
                "path_type": kind,
                "sha256": digest,
                "file_count": file_count,
                "reconstructable": bool(binding.get("reconstructable", True)),
                "copies": [],
            }
        )
    return items


def copy_item(
    item: dict[str, Any], copy_root: Path, run_id: str, fault_domain: str
) -> dict[str, Any]:
    if not fault_domain.strip():
        raise ArchiveError("copy fault domain must be non-empty")
    source = Path(item["source"])
    destination = copy_root.resolve() / run_id / safe_item_name(item["id"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ArchiveError(f"archive copy destination already exists: {destination}")
    if item["path_type"] == "file":
        shutil.copy2(source, destination)
    else:
        shutil.copytree(source, destination, symlinks=False)
    path_type, digest, file_count = path_identity(destination)
    if digest != item["sha256"] or path_type != item["path_type"]:
        raise ArchiveError(f"archive copy verification failed: {destination}")
    return {
        "method": "local_reread",
        "location": str(destination),
        "fault_domain": fault_domain,
        "sha256": digest,
        "file_count": file_count,
        "verified_at": utc_now(),
    }


def parse_copy(value: str) -> tuple[Path, str]:
    try:
        root, domain = value.rsplit("::", 1)
    except ValueError as exc:
        raise ArchiveError("--copy must use ROOT::FAULT_DOMAIN") from exc
    path = Path(root).expanduser()
    if not path.is_absolute():
        raise ArchiveError("archive copy root must be absolute")
    return path, domain


def parse_external_copy(value: str) -> tuple[str, str, str, str]:
    parts = value.split("::", 3)
    if len(parts) != 4 or not all(part.strip() for part in parts):
        raise ArchiveError("--external-copy must use ITEM_ID::FAULT_DOMAIN::EVIDENCE_URI::VERIFIER")
    return parts[0], parts[1], parts[2], parts[3]


def create_archive(
    value: str,
    root: Path = ROOT,
    *,
    copies: list[tuple[Path, str]] | None = None,
    external_copies: list[tuple[str, str, str, str]] | None = None,
    destination: Path | None = None,
) -> Path:
    manifest_path = research.resolve_manifest(root, value)
    manifest = research.load_json(manifest_path)
    items = inventory_from_manifest(manifest, root)
    run_id = manifest["run_id"]
    for copy_root, fault_domain in copies or []:
        for item in items:
            item["copies"].append(copy_item(item, copy_root, run_id, fault_domain))
    by_id = {item["id"]: item for item in items}
    for item_id, fault_domain, evidence_uri, verifier in external_copies or []:
        if item_id not in by_id:
            raise ArchiveError(f"external copy references unknown archive item: {item_id}")
        item = by_id[item_id]
        item["copies"].append(
            {
                "method": "external_attestation",
                "location": evidence_uri,
                "fault_domain": fault_domain,
                "sha256": item["sha256"],
                "file_count": item["file_count"],
                "verified_at": utc_now(),
                "verifier": verifier,
                "evidence_uri": evidence_uri,
            }
        )
    archive = {
        "archive_version": ARCHIVE_VERSION,
        "run_id": run_id,
        "created_at": utc_now(),
        "source_manifest": {
            "path": research.relative_name(manifest_path, root),
            "sha256": research.sha256_file(manifest_path),
        },
        "items": items,
    }
    output = destination or root / DEFAULT_ARCHIVE_DIR / f"{run_id}.json"
    validate_schema(archive, output, root)
    write_json_atomic(output, archive)
    return output


def copy_errors(item: dict[str, Any], copy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if copy.get("sha256") != item.get("sha256"):
        errors.append(f"copy checksum declaration differs for {item['id']}")
    method = copy.get("method")
    if method == "local_reread":
        location = copy.get("location")
        if not isinstance(location, str):
            return [f"local copy location missing for {item['id']}"]
        path = Path(location)
        try:
            path_type, digest, file_count = path_identity(path)
        except (ArchiveError, OSError) as exc:
            return [f"copy unavailable for {item['id']}: {exc}"]
        if digest != item.get("sha256") or path_type != item.get("path_type"):
            errors.append(f"copy content mismatch for {item['id']}: {location}")
        if file_count != item.get("file_count"):
            errors.append(f"copy file count mismatch for {item['id']}: {location}")
    elif method == "external_attestation":
        if not copy.get("evidence_uri") or not copy.get("verifier") or not copy.get("verified_at"):
            errors.append(f"external copy lacks verification evidence for {item['id']}")
    else:
        errors.append(f"copy method is not verified for {item['id']}")
    if not copy.get("fault_domain"):
        errors.append(f"copy fault domain missing for {item['id']}")
    return errors


def verify_archive(path: Path, root: Path = ROOT) -> dict[str, Any]:
    archive = read_json(path)
    validate_schema(archive, path, root)
    errors: list[str] = []
    source = archive["source_manifest"]
    source_path = root / source["path"]
    if not source_path.is_file():
        errors.append(f"source run manifest is missing: {source['path']}")
    elif research.sha256_file(source_path) != source["sha256"]:
        errors.append(f"source run manifest changed: {source['path']}")
    item_reports: list[dict[str, Any]] = []
    for item in archive["items"]:
        verified_domains: set[str] = set()
        item_errors: list[str] = []
        for copy in item["copies"]:
            failures = copy_errors(item, copy)
            item_errors.extend(failures)
            if not failures:
                verified_domains.add(copy["fault_domain"])
        required_copies = 1 if item["reconstructable"] else 2
        if len(verified_domains) < required_copies:
            item_errors.append(
                f"{item['id']} requires {required_copies} verified independent fault domains; "
                f"found {len(verified_domains)}"
            )
        errors.extend(item_errors)
        item_reports.append(
            {
                "id": item["id"],
                "verified_fault_domains": sorted(verified_domains),
                "required_copies": required_copies,
                "errors": item_errors,
            }
        )
    return {
        "archive": str(path),
        "run_id": archive["run_id"],
        "valid": not errors,
        "errors": errors,
        "items": item_reports,
    }


def worktree_blockers(path: Path) -> list[str]:
    if not path.is_dir():
        return [f"worktree does not exist: {path}"]
    process = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=path,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    if process.returncode != 0:
        return [f"cannot inspect worktree Git state: {process.stderr.strip()}"]
    if process.stdout.strip():
        return ["worktree contains uncommitted or untracked files"]
    return []


def retirement_preflight(
    archive_path: Path,
    target_kind: str,
    target: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    if target_kind not in TARGET_KINDS:
        raise ArchiveError(f"target kind must be one of: {', '.join(sorted(TARGET_KINDS))}")
    verification = verify_archive(archive_path, root)
    blockers = list(verification["errors"])
    if target_kind == "run" and target != verification["run_id"]:
        blockers.append(
            f"retirement target run {target!r} does not match archive run {verification['run_id']!r}"
        )
    if target_kind == "worktree":
        blockers.extend(worktree_blockers(Path(target)))
    return {
        "target_kind": target_kind,
        "target": target,
        "decision": "retire_allowed" if not blockers else "blocked",
        "blockers": blockers,
        "archive_verification": verification,
        "destructive_action_performed": False,
        "next_action_requires_explicit_authorization": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create verified archives and retirement decisions."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create", help="create an archive manifest and verified copies")
    create.add_argument("run")
    create.add_argument("--copy", action="append", default=[], metavar="ROOT::FAULT_DOMAIN")
    create.add_argument(
        "--external-copy",
        action="append",
        default=[],
        metavar="ITEM_ID::FAULT_DOMAIN::EVIDENCE_URI::VERIFIER",
    )
    create.add_argument("--output")
    verify = subparsers.add_parser("verify", help="re-read and verify archive evidence")
    verify.add_argument("archive")
    retire = subparsers.add_parser("retirement-preflight", help="report retirement blockers")
    retire.add_argument("archive")
    retire.add_argument("--target-kind", choices=sorted(TARGET_KINDS), required=True)
    retire.add_argument("--target", required=True)
    return parser


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            output = Path(args.output) if args.output else None
            path = create_archive(
                args.run,
                root,
                copies=[parse_copy(value) for value in args.copy],
                external_copies=[parse_external_copy(value) for value in args.external_copy],
                destination=output,
            )
            print(path)
            return 0
        if args.command == "verify":
            report = verify_archive(Path(args.archive), root)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["valid"] else 3
        if args.command == "retirement-preflight":
            report = retirement_preflight(Path(args.archive), args.target_kind, args.target, root)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["decision"] == "retire_allowed" else 3
    except (ArchiveError, OSError, ValueError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
