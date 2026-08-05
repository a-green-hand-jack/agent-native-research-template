from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
FACT_SCHEMA = Path("schemas/external-fact.schema.json")
FACT_ROOT = Path("external-facts")


class ExternalFactError(ValueError):
    """Raised when an external fact is missing, stale, or malformed."""


def parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ExternalFactError(f"{field} must be an ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ExternalFactError(f"{field} must include a timezone: {value}")
    return parsed.astimezone(UTC)


def load_fact(path: Path, root: Path = ROOT) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ExternalFactError(f"cannot read external fact {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExternalFactError(f"external fact must be a mapping: {path}")
    schema = json.loads((root / FACT_SCHEMA).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ExternalFactError(
            f"{path} does not match external fact schema at {location}: {error.message}"
        )
    checked = parse_time(value["checked_at"], "checked_at")
    if "valid_until" in value and parse_time(value["valid_until"], "valid_until") <= checked:
        raise ExternalFactError("valid_until must be later than checked_at")
    return value


def fact_index(
    root: Path = ROOT, requested: set[str] | None = None
) -> dict[str, tuple[Path, dict[str, Any]]]:
    records: dict[str, tuple[Path, dict[str, Any]]] = {}
    directory = root / FACT_ROOT
    if not directory.is_dir():
        return records
    for path in sorted((*directory.rglob("*.yaml"), *directory.rglob("*.yml"))):
        if requested is not None:
            try:
                candidate = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, yaml.YAMLError):
                continue
            if not isinstance(candidate, dict) or candidate.get("id") not in requested:
                continue
        fact = load_fact(path, root)
        identifier = fact["id"]
        if identifier in records:
            raise ExternalFactError(f"duplicate external fact ID: {identifier}")
        records[identifier] = (path, fact)
    return records


def snapshot(path: Path, fact: dict[str, Any], root: Path, now: datetime) -> dict[str, Any]:
    declared = fact["status"]
    if parse_time(fact["checked_at"], "checked_at") > now:
        raise ExternalFactError(f"external fact {fact['id']} has a future checked_at timestamp")
    effective = declared
    if declared == "VERIFIED" and parse_time(fact["valid_until"], "valid_until") <= now:
        effective = "STALE"
    return {
        "id": fact["id"],
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_url": fact["source_url"],
        "checked_at": fact["checked_at"],
        "valid_until": fact.get("valid_until"),
        "declared_status": declared,
        "effective_status": effective,
        "scope": list(fact["scope"]),
    }


def resolve_references(
    identifiers: list[str], root: Path = ROOT, *, now: datetime | None = None
) -> list[dict[str, Any]]:
    if len(identifiers) != len(set(identifiers)):
        raise ExternalFactError("external fact references must be unique")
    if not identifiers:
        return []
    records = fact_index(root, set(identifiers))
    observed_at = (now or datetime.now(UTC)).astimezone(UTC)
    resolved: list[dict[str, Any]] = []
    for identifier in identifiers:
        if identifier not in records:
            raise ExternalFactError(f"unknown external fact ID: {identifier}")
        path, fact = records[identifier]
        resolved.append(snapshot(path, fact, root, observed_at))
    return resolved


def require_verified(snapshots: list[dict[str, Any]], context: str) -> None:
    invalid = [fact["id"] for fact in snapshots if fact["effective_status"] != "VERIFIED"]
    if invalid:
        raise ExternalFactError(
            f"{context} requires VERIFIED external facts; invalid: {', '.join(invalid)}"
        )


def refresh_and_compare(snapshots: list[dict[str, Any]], root: Path = ROOT) -> list[dict[str, Any]]:
    current = resolve_references([fact["id"] for fact in snapshots], root)
    expected_hashes = {fact["id"]: fact["sha256"] for fact in snapshots}
    changed = [fact["id"] for fact in current if fact["sha256"] != expected_hashes.get(fact["id"])]
    if changed:
        raise ExternalFactError(
            f"external facts changed after planning/build: {', '.join(changed)}"
        )
    return current
