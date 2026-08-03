from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = "schemas/archive-manifest.schema.json"
VERIFY_METHODS = {"local_readback", "external_evidence"}
TARGET_KINDS = {"run", "worktree", "branch", "provider"}


class ArchiveError(ValueError):
    """Raised when an archive manifest or retirement decision is invalid."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ArchiveError(f"cannot read archive manifest {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArchiveError("archive manifest must be a YAML mapping")
    return value


def load_schema(root: Path) -> dict[str, Any]:
    path = root / SCHEMA_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ArchiveError(f"cannot read archive schema: {exc}") from exc
    Draft202012Validator.check_schema(value)
    return value


def schema_location(parts: list[object]) -> str:
    location = "$"
    for part in parts:
        location += f"[{part}]" if isinstance(part, int) else f".{part}"
    return location


def validate_manifest(data: dict[str, Any], root: Path = ROOT) -> None:
    errors = sorted(
        Draft202012Validator(load_schema(root)).iter_errors(data),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        raise ArchiveError(
            f"archive manifest does not match schema at "
            f"{schema_location(list(error.absolute_path))}: {error.message}"
        )

    asset_ids = [asset["id"] for asset in data["assets"]]
    if len(asset_ids) != len(set(asset_ids)):
        raise ArchiveError("archive asset IDs must be unique")
    target_ids = [target["id"] for target in data.get("retirement_targets", [])]
    if len(target_ids) != len(set(target_ids)):
        raise ArchiveError("retirement target IDs must be unique")
    known_assets = set(asset_ids)
    for target in data.get("retirement_targets", []):
        unknown = sorted(set(target.get("required_asset_ids", [])) - known_assets)
        if unknown:
            raise ArchiveError(
                f"retirement target {target['id']!r} references unknown assets: "
                + ", ".join(unknown)
            )


def normalized_path(root: Path, value: str, field: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts or "\\" in value:
        raise ArchiveError(f"{field} must be a normalized repository-relative path")
    resolved = (root / raw).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ArchiveError(f"{field} resolves outside the repository") from exc
    return resolved


def verify_copy(
    asset: dict[str, Any], copy: dict[str, Any], root: Path
) -> tuple[bool, str | None]:
    verification = copy.get("verification") or {}
    method = verification.get("method")
    if method not in VERIFY_METHODS:
        return False, "copy has no supported verification method"
    expected = asset["sha256"]
    if verification.get("sha256") != expected:
        return False, "verification hash does not match the asset hash"
    if not verification.get("verified_at"):
        return False, "copy has no verification timestamp"

    if method == "local_readback":
        location = copy.get("location")
        if not isinstance(location, str):
            return False, "local copy has no repository-relative location"
        try:
            path = normalized_path(root, location, "copy.location")
        except ArchiveError as exc:
            return False, str(exc)
        if not path.is_file():
            return False, f"local copy is missing: {location}"
        if sha256_file(path) != expected:
            return False, f"local copy checksum mismatch: {location}"
        return True, None

    evidence = verification.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        return False, "external verification requires non-empty evidence"
    return True, None


def verify_archive(data: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    validate_manifest(data, root)
    records: list[dict[str, Any]] = []
    archive_blockers: list[str] = []
    safe_assets: set[str] = set()

    for asset in data["assets"]:
        verified_domains: set[str] = set()
        copy_records: list[dict[str, Any]] = []
        for copy in asset.get("copies", []):
            verified, reason = verify_copy(asset, copy, root)
            if verified:
                verified_domains.add(copy["fault_domain"])
            copy_records.append(
                {
                    "id": copy["id"],
                    "fault_domain": copy["fault_domain"],
                    "verified": verified,
                    "reason": reason,
                }
            )

        required_domains = 1 if asset.get("reconstructable", True) else 2
        asset_safe = len(verified_domains) >= required_domains
        if asset_safe:
            safe_assets.add(asset["id"])
        else:
            archive_blockers.append(
                f"asset {asset['id']} requires {required_domains} verified independent "
                f"fault domain(s), found {len(verified_domains)}"
            )
        records.append(
            {
                "id": asset["id"],
                "reconstructable": asset.get("reconstructable", True),
                "required_fault_domains": required_domains,
                "verified_fault_domains": sorted(verified_domains),
                "safe_to_retire_source": asset_safe,
                "copies": copy_records,
            }
        )

    return {
        "archive_id": data["archive_id"],
        "verified": not archive_blockers,
        "assets": records,
        "blockers": archive_blockers,
        "safe_asset_ids": sorted(safe_assets),
    }


def retirement_preflight(data: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    verification = verify_archive(data, root)
    safe_assets = set(verification["safe_asset_ids"])
    decisions: list[dict[str, Any]] = []

    for target in data.get("retirement_targets", []):
        blockers: list[str] = []
        required_assets = set(target.get("required_asset_ids", []))
        unsafe = sorted(required_assets - safe_assets)
        if unsafe:
            blockers.append("required assets are not safely archived: " + ", ".join(unsafe))
        unique_paths = target.get("unique_untracked_paths", [])
        if unique_paths:
            blockers.append(
                "unique untracked paths remain: " + ", ".join(sorted(unique_paths))
            )
        pending = target.get("pending_actions", [])
        if pending:
            blockers.append("pending retention actions remain: " + ", ".join(sorted(pending)))
        decisions.append(
            {
                "id": target["id"],
                "kind": target["kind"],
                "decision": "allow" if not blockers else "block",
                "blockers": blockers,
                "destructive_action_performed": False,
            }
        )

    return {
        "archive_id": data["archive_id"],
        "archive_verified": verification["verified"],
        "targets": decisions,
        "stop_delete_retire_are_separate": True,
        "destructive_action_performed": False,
    }


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate archives and produce read-only retirement decisions."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("validate", "validate one archive manifest"),
        ("verify", "verify recorded archive copies"),
        ("retirement-preflight", "report whether declared targets are safe to retire"),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument("manifest")
    return parser


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        path = normalized_path(root, args.manifest, "manifest")
        data = load_yaml(path)
        if args.command == "validate":
            validate_manifest(data, root)
            emit({"valid": True, "archive_id": data["archive_id"]})
        elif args.command == "verify":
            result = verify_archive(data, root)
            emit(result)
            return 0 if result["verified"] else 3
        else:
            result = retirement_preflight(data, root)
            emit(result)
            return 0 if all(item["decision"] == "allow" for item in result["targets"]) else 4
        return 0
    except (ArchiveError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
