from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

import input_identity

REGISTRY_PATH = Path("assets/registry.yaml")
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
ROLES = {
    "source",
    "dataset",
    "generation_oracle",
    "evaluation_oracle",
    "checkpoint",
    "cache",
    "output",
}
PHASES = {"all", "generation", "evaluation"}
ACCESS_MODES = {"read", "write"}


class AssetBindingError(ValueError):
    """Raised when a logical asset cannot be bound safely for execution."""


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def load_registry(root: Path) -> dict[str, dict[str, Any]]:
    path = root / REGISTRY_PATH
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise AssetBindingError(f"cannot read asset registry {REGISTRY_PATH}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise AssetBindingError("asset registry must be a schema_version 1 mapping")
    declarations = document.get("assets")
    if not isinstance(declarations, list):
        raise AssetBindingError("asset registry assets must be a list")
    records: dict[str, dict[str, Any]] = {}
    for index, declaration in enumerate(declarations):
        if not isinstance(declaration, dict):
            raise AssetBindingError(f"assets[{index}] must be a mapping")
        identifier = declaration.get("id")
        role = declaration.get("role")
        expected_type = declaration.get("expected_type")
        if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
            raise AssetBindingError(f"assets[{index}].id must be a stable lowercase identifier")
        if identifier in records:
            raise AssetBindingError(f"duplicate asset ID: {identifier}")
        if role not in ROLES:
            raise AssetBindingError(f"asset {identifier} role must be one of: {', '.join(sorted(ROLES))}")
        if expected_type not in {"file", "directory", "any"}:
            raise AssetBindingError(f"asset {identifier} expected_type must be file, directory, or any")
        if not isinstance(declaration.get("reconstructable"), bool):
            raise AssetBindingError(f"asset {identifier} reconstructable must be boolean")
        for field in ("min_bytes", "max_bytes"):
            value = declaration.get(field)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise AssetBindingError(f"asset {identifier} {field} must be a non-negative integer")
        if declaration.get("min_bytes", 0) > declaration.get("max_bytes", float("inf")):
            raise AssetBindingError(f"asset {identifier} min_bytes exceeds max_bytes")
        records[identifier] = declaration
    return records


def requirement_records(spec: dict[str, Any]) -> list[dict[str, str]]:
    requirements = spec.get("assets", [])
    if not isinstance(requirements, list):
        raise AssetBindingError("experiment assets must be a list")
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            raise AssetBindingError(f"experiment assets[{index}] must be a mapping")
        identifier = requirement.get("id")
        phase = requirement.get("phase", "all")
        access = requirement.get("access", "read")
        if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
            raise AssetBindingError(f"experiment assets[{index}].id is invalid")
        if identifier in seen:
            raise AssetBindingError(f"duplicate experiment asset requirement: {identifier}")
        seen.add(identifier)
        if phase not in PHASES:
            raise AssetBindingError(f"asset requirement {identifier} phase must be all, generation, or evaluation")
        if access not in ACCESS_MODES:
            raise AssetBindingError(f"asset requirement {identifier} access must be read or write")
        records.append({"id": identifier, "phase": phase, "access": access})
    return records


def safe_repository_target(root: Path, value: object, field: str) -> tuple[Path, str]:
    if not isinstance(value, str) or not value.strip():
        raise AssetBindingError(f"{field} must be a non-empty repository-relative path")
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts or "\\" in value:
        raise AssetBindingError(f"{field} must be a normalized repository-relative path")
    lexical = root
    for part in raw.parts:
        lexical /= part
        if lexical.is_symlink():
            raise AssetBindingError(f"{field} must not traverse a symbolic link: {value}")
    try:
        (root / raw).resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise AssetBindingError(f"{field} resolves outside the repository: {value}") from exc
    return root / raw, raw.as_posix()


def external_path(value: object, field: str) -> tuple[Path, str]:
    if not isinstance(value, str) or not value.strip():
        raise AssetBindingError(f"{field} must be a non-empty absolute path")
    raw = Path(value)
    if not raw.is_absolute() or ".." in raw.parts:
        raise AssetBindingError(f"{field} must be a normalized absolute path")
    current = Path(raw.anchor)
    for part in raw.parts[1:]:
        current /= part
        if current.is_symlink():
            raise AssetBindingError(f"{field} must not traverse a symbolic link: {value}")
    return raw, raw.as_posix()


def path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(candidate.stat().st_size for candidate in path.rglob("*") if candidate.is_file())


def resolve_path_binding(
    identifier: str,
    declaration: dict[str, Any],
    registry: dict[str, Any],
    requirement: dict[str, str],
    root: Path,
) -> dict[str, Any]:
    scope = declaration.get("scope", "repository")
    field = f"asset binding {identifier}.path"
    if scope == "repository":
        if requirement["access"] == "read":
            try:
                path, rendered = input_identity.normalized_repository_path(
                    root, declaration.get("path"), field
                )
            except input_identity.InputIdentityError as exc:
                raise AssetBindingError(str(exc)) from exc
        else:
            path, rendered = safe_repository_target(root, declaration.get("path"), field)
    elif scope == "external":
        path, rendered = external_path(declaration.get("path"), field)
    else:
        raise AssetBindingError(f"asset binding {identifier} scope must be repository or external")

    exists = path.exists()
    if requirement["access"] == "read" and not exists:
        raise AssetBindingError(f"asset binding {identifier} does not exist: {rendered}")
    if requirement["access"] == "write" and exists and registry.get("immutable_output", False):
        raise AssetBindingError(f"immutable output asset already exists: {identifier} -> {rendered}")

    expected_type = registry["expected_type"]
    if not exists:
        planned_type = expected_type if expected_type != "any" else "file"
        return {
            "id": identifier,
            "role": registry["role"],
            "phase": requirement["phase"],
            "access": requirement["access"],
            "kind": "path",
            "scope": scope,
            "path": rendered,
            "path_type": planned_type,
            "exists": False,
            "reconstructable": registry["reconstructable"],
        }

    actual_type = "directory" if path.is_dir() else "file" if path.is_file() else "other"
    if expected_type != "any" and actual_type != expected_type:
        raise AssetBindingError(
            f"asset {identifier} expected {expected_type} but binding is {actual_type}: {rendered}"
        )
    if actual_type == "directory":
        try:
            digest, file_count = input_identity.directory_identity(path)
        except input_identity.InputIdentityError as exc:
            raise AssetBindingError(str(exc)) from exc
    elif actual_type == "file":
        digest = input_identity.sha256_file(path)
        file_count = 1
    else:
        raise AssetBindingError(f"asset binding {identifier} must identify a file or directory")
    size_bytes = path_size(path)
    if size_bytes < registry.get("min_bytes", 0):
        raise AssetBindingError(f"asset {identifier} is smaller than min_bytes")
    maximum = registry.get("max_bytes")
    if maximum is not None and size_bytes > maximum:
        raise AssetBindingError(f"asset {identifier} exceeds max_bytes")
    expected_digest = declaration.get("sha256")
    if expected_digest is not None and expected_digest != digest:
        raise AssetBindingError(f"asset {identifier} checksum mismatch")
    return {
        "id": identifier,
        "role": registry["role"],
        "phase": requirement["phase"],
        "access": requirement["access"],
        "kind": "path",
        "scope": scope,
        "path": rendered,
        "path_type": actual_type,
        "exists": True,
        "sha256": digest,
        "file_count": file_count,
        "size_bytes": size_bytes,
        "reconstructable": registry["reconstructable"],
    }


def resolve_non_path_binding(
    identifier: str,
    declaration: dict[str, Any],
    registry: dict[str, Any],
    requirement: dict[str, str],
) -> dict[str, Any]:
    kind = declaration.get("kind")
    try:
        if kind == "uri":
            record = input_identity.uri_identity(identifier, declaration)
        elif kind == "opaque":
            record = input_identity.opaque_identity(identifier, declaration)
        else:
            raise AssetBindingError(f"asset binding {identifier} kind must be path, uri, or opaque")
    except input_identity.InputIdentityError as exc:
        raise AssetBindingError(str(exc)) from exc
    return {
        **record,
        "role": registry["role"],
        "phase": requirement["phase"],
        "access": requirement["access"],
        "reconstructable": registry["reconstructable"],
    }


def resolve_assets(
    spec: dict[str, Any],
    executor: dict[str, Any],
    root: Path,
    *,
    phase: str = "all",
) -> dict[str, Any]:
    if phase not in PHASES:
        raise AssetBindingError("preflight phase must be all, generation, or evaluation")
    registry = load_registry(root)
    requirements = requirement_records(spec)
    bindings = executor.get("asset_bindings", {})
    if not isinstance(bindings, dict):
        raise AssetBindingError("executor asset_bindings must be a mapping")
    resolved: list[dict[str, Any]] = []
    for requirement in requirements:
        if phase != "all" and requirement["phase"] not in {"all", phase}:
            continue
        identifier = requirement["id"]
        if identifier not in registry:
            raise AssetBindingError(f"unknown logical asset ID: {identifier}")
        declaration = bindings.get(identifier)
        if not isinstance(declaration, dict):
            raise AssetBindingError(f"executor has no binding for logical asset: {identifier}")
        kind = declaration.get("kind")
        if kind == "path":
            record = resolve_path_binding(
                identifier, declaration, registry[identifier], requirement, root
            )
        else:
            record = resolve_non_path_binding(
                identifier, declaration, registry[identifier], requirement
            )
        resolved.append(record)
    result = {"phase": phase, "assets": resolved}
    return {**result, "sha256": canonical_hash(result)}


def environment_for_assets(preflight: dict[str, Any]) -> dict[str, str]:
    environment: dict[str, str] = {}
    for record in preflight.get("assets", []):
        if not isinstance(record, dict):
            continue
        identifier = str(record["id"]).upper().replace("-", "_").replace(".", "_")
        if record.get("kind") == "path":
            environment[f"RESEARCH_ASSET_{identifier}"] = str(record["path"])
    return environment


def recorded_asset_drift(records: object, root: Path) -> list[str]:
    if not isinstance(records, list):
        return ["recorded asset bindings are not a list"]
    drift: list[str] = []
    for record in records:
        if (
            not isinstance(record, dict)
            or record.get("kind") != "path"
            or record.get("access") != "read"
        ):
            continue
        identifier = str(record.get("id", "unknown"))
        scope = record.get("scope", "repository")
        try:
            if scope == "repository":
                path, _ = input_identity.normalized_repository_path(
                    root, record.get("path"), f"recorded asset {identifier}.path"
                )
            else:
                path, _ = external_path(record.get("path"), f"recorded asset {identifier}.path")
                if not path.exists():
                    raise AssetBindingError(f"recorded asset {identifier} is missing")
            if path.is_dir():
                digest, file_count = input_identity.directory_identity(path)
            else:
                digest = input_identity.sha256_file(path)
                file_count = 1
        except (AssetBindingError, input_identity.InputIdentityError, OSError) as exc:
            drift.append(f"asset {identifier}: {exc}")
            continue
        if digest != record.get("sha256"):
            drift.append(f"asset {identifier} changed: {record.get('path')}")
        elif file_count != record.get("file_count"):
            drift.append(f"asset {identifier} file count changed: {record.get('path')}")
    return drift
