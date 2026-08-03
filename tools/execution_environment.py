from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
PLACEHOLDER = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")
SECRET_LIKE = re.compile(
    r"(?:SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE|CREDENTIAL|API_KEY|ACCESS_KEY)", re.IGNORECASE
)
PROJECT_ROOT_VARIABLE = "PROJECT_ROOT"
SEED_VARIABLE = "RESEARCH_SEED"


class ExecutionEnvironmentError(ValueError):
    """Raised when an executor environment is implicit, unsafe, or unresolved."""


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_name(name: object, field: str) -> str:
    if not isinstance(name, str) or not ENV_NAME.fullmatch(name):
        raise ExecutionEnvironmentError(f"{field} must be an uppercase environment variable name")
    if SECRET_LIKE.search(name):
        raise ExecutionEnvironmentError(
            f"{field} {name!r} looks secret-bearing and cannot enter durable experiment bindings"
        )
    if name == SEED_VARIABLE:
        raise ExecutionEnvironmentError(f"{SEED_VARIABLE} is reserved for the canonical runner")
    return name


def expand_value(value: object, root: Path, field: str) -> str:
    if not isinstance(value, str):
        raise ExecutionEnvironmentError(f"{field} must be a string")

    def replace(match: re.Match[str]) -> str:
        variable = match.group(1)
        if variable != PROJECT_ROOT_VARIABLE:
            raise ExecutionEnvironmentError(
                f"{field} uses undeclared placeholder ${{{variable}}}; only ${{PROJECT_ROOT}} is supported"
            )
        return str(root.resolve())

    rendered = PLACEHOLDER.sub(replace, value)
    if "${" in rendered:
        raise ExecutionEnvironmentError(f"{field} contains an invalid environment placeholder")
    return rendered


def declared_environment(executor: Mapping[str, Any], root: Path) -> dict[str, Any]:
    raw_explicit = executor.get("environment", {})
    if not isinstance(raw_explicit, dict):
        raise ExecutionEnvironmentError("executor environment must be a mapping")
    explicit: dict[str, str] = {}
    for raw_name in sorted(raw_explicit):
        name = validate_name(raw_name, "executor environment key")
        explicit[name] = expand_value(raw_explicit[raw_name], root, f"executor environment {name}")

    raw_inherit = executor.get("inherit_environment", [])
    if not isinstance(raw_inherit, list):
        raise ExecutionEnvironmentError("executor inherit_environment must be a list")
    inherited = [validate_name(name, "inherited environment variable") for name in raw_inherit]
    if len(inherited) != len(set(inherited)):
        raise ExecutionEnvironmentError("executor inherit_environment contains duplicate names")
    duplicates = sorted(set(explicit) & set(inherited))
    if duplicates:
        raise ExecutionEnvironmentError(
            "environment variables cannot be both explicit and inherited: " + ", ".join(duplicates)
        )
    declaration = {"explicit": explicit, "inherit": sorted(inherited)}
    return {**declaration, "sha256": sha256_text(canonical_json(declaration))}


def resolve_environment(
    executor: Mapping[str, Any],
    root: Path,
    seed: int,
    host: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    declaration = declared_environment(executor, root)
    host_environment = os.environ if host is None else host
    environment = dict(declaration["explicit"])
    inherited_records: list[dict[str, str]] = []
    for name in declaration["inherit"]:
        if name not in host_environment:
            raise ExecutionEnvironmentError(
                f"required inherited environment variable is missing: {name}"
            )
        value = host_environment[name]
        environment[name] = value
        inherited_records.append({"name": name, "sha256": sha256_text(value)})
    environment[SEED_VARIABLE] = str(seed)
    evidence = {
        "declaration_sha256": declaration["sha256"],
        "explicit": declaration["explicit"],
        "inherited": inherited_records,
        "seed": {"name": SEED_VARIABLE, "value": seed},
    }
    evidence["sha256"] = sha256_text(canonical_json(evidence))
    return environment, evidence
