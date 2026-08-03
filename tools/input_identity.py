from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class InputIdentityError(ValueError):
    """Raised when a declared research input cannot be identified safely."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalized_repository_path(root: Path, value: object, field: str) -> tuple[Path, str]:
    if not isinstance(value, str) or not value.strip():
        raise InputIdentityError(f"{field} must be a non-empty repository-relative path")
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts or "\\" in value:
        raise InputIdentityError(f"{field} must be a normalized repository-relative path")

    lexical = root
    for part in raw.parts:
        lexical = lexical / part
        if lexical.is_symlink():
            raise InputIdentityError(f"{field} must not traverse a symbolic link: {value}")

    path = root / raw
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise InputIdentityError(f"{field} resolves outside the repository: {value}") from exc
    if not path.exists():
        raise InputIdentityError(f"{field} does not exist: {value}")
    return path, raw.as_posix()


def directory_identity(path: Path) -> tuple[str, int]:
    entries: list[dict[str, str]] = []
    for candidate in sorted(path.rglob("*")):
        if candidate.is_symlink():
            relative = candidate.relative_to(path).as_posix()
            raise InputIdentityError(f"path input contains a symbolic link: {relative}")
        if not candidate.is_file():
            continue
        entries.append(
            {
                "path": candidate.relative_to(path).as_posix(),
                "sha256": sha256_file(candidate),
            }
        )
    payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return sha256_bytes(payload), len(entries)


def path_identity(identifier: str, declaration: dict[str, Any], root: Path) -> dict[str, Any]:
    path, relative = normalized_repository_path(root, declaration.get("path"), "input.path")
    if path.is_dir():
        digest, file_count = directory_identity(path)
        path_type = "directory"
    elif path.is_file():
        digest = sha256_file(path)
        file_count = 1
        path_type = "file"
    else:
        raise InputIdentityError(f"input.path must identify a file or directory: {relative}")
    return {
        "id": identifier,
        "kind": "path",
        "path": relative,
        "path_type": path_type,
        "sha256": digest,
        "file_count": file_count,
    }


def uri_identity(identifier: str, declaration: dict[str, Any]) -> dict[str, Any]:
    uri = declaration.get("uri")
    if not isinstance(uri, str) or not uri.strip():
        raise InputIdentityError("uri input requires a non-empty uri")
    record: dict[str, Any] = {"id": identifier, "kind": "uri", "uri": uri}
    version = declaration.get("version")
    if version is not None:
        if not isinstance(version, str) or not version.strip():
            raise InputIdentityError("uri input version must be a non-empty string")
        record["version"] = version
    digest = declaration.get("sha256")
    if digest is not None:
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise InputIdentityError("uri input sha256 must be 64 lowercase hexadecimal characters")
        record["sha256"] = digest
    return record


def opaque_identity(identifier: str, declaration: dict[str, Any]) -> dict[str, Any]:
    value = declaration.get("value")
    if not isinstance(value, str) or not value.strip():
        raise InputIdentityError("opaque input requires a non-empty value")
    record: dict[str, Any] = {"id": identifier, "kind": "opaque", "value": value}
    version = declaration.get("version")
    if version is not None:
        if not isinstance(version, str) or not version.strip():
            raise InputIdentityError("opaque input version must be a non-empty string")
        record["version"] = version
    return record


def resolve_inputs(declarations: object, root: Path) -> list[dict[str, Any]]:
    if declarations is None:
        return []
    if not isinstance(declarations, list):
        raise InputIdentityError("inputs must be a list")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, declaration in enumerate(declarations):
        if not isinstance(declaration, dict):
            raise InputIdentityError(f"inputs[{index}] must be a mapping")
        identifier = declaration.get("id")
        if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
            raise InputIdentityError(f"inputs[{index}].id must be a stable lowercase identifier")
        if identifier in seen:
            raise InputIdentityError(f"duplicate input ID: {identifier}")
        seen.add(identifier)
        kind = declaration.get("kind")
        if kind == "path":
            records.append(path_identity(identifier, declaration, root))
        elif kind == "uri":
            records.append(uri_identity(identifier, declaration))
        elif kind == "opaque":
            records.append(opaque_identity(identifier, declaration))
        else:
            raise InputIdentityError(f"inputs[{index}].kind must be path, uri, or opaque")
    return records


def recorded_input_drift(records: object, root: Path) -> list[str]:
    if not isinstance(records, list):
        return ["recorded inputs are not a list"]
    drift: list[str] = []
    for record in records:
        if not isinstance(record, dict) or record.get("kind") != "path":
            continue
        identifier = record.get("id", "unknown")
        try:
            current = path_identity(str(identifier), record, root)
        except InputIdentityError as exc:
            drift.append(f"input {identifier}: {exc}")
            continue
        if current["sha256"] != record.get("sha256"):
            drift.append(f"input {identifier} changed: {record.get('path')}")
        elif current["file_count"] != record.get("file_count"):
            drift.append(f"input {identifier} file count changed: {record.get('path')}")
    return drift
