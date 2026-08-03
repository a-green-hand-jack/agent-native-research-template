from __future__ import annotations

import itertools
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import execution_environment
import phase_graph
import plan_identity
import research

ROOT = Path(__file__).resolve().parents[1]
PLAN_VERSION = 2
RUN_CLASSES = {"smoke", "pilot", "partial", "reference", "formal", "post_observation"}
OBSERVATION_STATUSES = {"pre_observation", "post_observation"}
SCALAR_TYPES = (str, int, float, bool, type(None))


class PlanError(ValueError):
    """Raised when an experiment cannot produce an unambiguous deterministic plan."""


def canonical_json(value: object) -> str:
    return plan_identity.canonical_json(value)


def sha256_json(value: object) -> str:
    return plan_identity.sha256_json(value)


def scalar(value: object, field: str) -> str | int | float | bool | None:
    if not isinstance(value, SCALAR_TYPES):
        raise PlanError(f"{field} must contain only JSON scalar values")
    if isinstance(value, float) and not math.isfinite(value):
        raise PlanError(f"{field} must not contain non-finite numbers")
    return value


def normalize_parameters(value: object, field: str) -> dict[str, str | int | float | bool | None]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PlanError(f"{field} must be a mapping")
    normalized: dict[str, str | int | float | bool | None] = {}
    for key in sorted(value):
        if not isinstance(key, str) or not key:
            raise PlanError(f"{field} keys must be non-empty strings")
        normalized[key] = scalar(value[key], f"{field}.{key}")
    return normalized


def normalize_matrix(value: object) -> dict[str, list[str | int | float | bool | None]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PlanError("matrix must be a mapping of parameter names to value lists")
    normalized: dict[str, list[str | int | float | bool | None]] = {}
    for key in sorted(value):
        values = value[key]
        if not isinstance(key, str) or not key:
            raise PlanError("matrix keys must be non-empty strings")
        if not isinstance(values, list) or not values:
            raise PlanError(f"matrix.{key} must be a non-empty list")
        items = [scalar(item, f"matrix.{key}") for item in values]
        rendered = [canonical_json(item) for item in items]
        if len(rendered) != len(set(rendered)):
            raise PlanError(f"matrix.{key} contains duplicate values")
        normalized[key] = items
    return normalized


def expand_cells(
    parameters: dict[str, str | int | float | bool | None],
    matrix: dict[str, list[str | int | float | bool | None]],
) -> list[dict[str, Any]]:
    if not matrix:
        combinations: list[tuple[object, ...]] = [()]
    else:
        combinations = list(itertools.product(*(matrix[key] for key in matrix)))
    cells: list[dict[str, Any]] = []
    seen: set[str] = set()
    matrix_keys = list(matrix)
    for values in combinations:
        cell_parameters = dict(parameters)
        cell_parameters.update(dict(zip(matrix_keys, values, strict=True)))
        identity = sha256_json(cell_parameters)
        if identity in seen:
            raise PlanError("matrix expansion produced duplicate cells")
        seen.add(identity)
        cells.append({"cell_id": identity[:16], "parameters": cell_parameters})
    return cells


def protocol_fields(spec: dict[str, Any]) -> tuple[str, str, str]:
    explicit_protocol = spec.get("protocol_id")
    protocol_id = explicit_protocol or spec["id"]
    research.validate_identifier(protocol_id, "protocol ID")
    run_class = spec.get("run_class", "smoke")
    if run_class not in RUN_CLASSES:
        raise PlanError(f"run_class must be one of: {', '.join(sorted(RUN_CLASSES))}")
    observation_status = spec.get("observation_status", "pre_observation")
    if observation_status not in OBSERVATION_STATUSES:
        raise PlanError("observation_status must be pre_observation or post_observation")
    if run_class == "formal":
        if explicit_protocol is None:
            raise PlanError("formal runs require an explicit protocol_id")
        if observation_status != "pre_observation":
            raise PlanError("formal runs must use pre_observation protocol status")
    if run_class == "post_observation" and observation_status != "post_observation":
        raise PlanError("post_observation runs must declare post_observation status")
    return protocol_id, run_class, observation_status


def environment_identity(resolved: dict[str, Any]) -> dict[str, Any]:
    root = resolved["root"]
    return {
        "id": resolved["spec"]["environment"],
        "definition": deepcopy(resolved["environment"]),
        "definition_path": research.relative_name(resolved["environment_path"], root),
        "definition_sha256": research.sha256_file(resolved["environment_path"]),
        "lockfile": research.relative_name(resolved["lockfile_path"], root),
        "lockfile_sha256": research.sha256_file(resolved["lockfile_path"]),
    }


def build_plan(resolved: dict[str, Any]) -> dict[str, Any]:
    spec = resolved["spec"]
    protocol_id, run_class, observation_status = protocol_fields(spec)
    parameters = normalize_parameters(spec.get("scientific_parameters"), "scientific_parameters")
    matrix = normalize_matrix(spec.get("matrix"))
    cells = expand_cells(parameters, matrix)
    recovery_policy = deepcopy(
        spec.get("recovery_policy", {"mode": "new_run", "reuse_verified_artifacts": False})
    )
    completion_criteria = deepcopy(
        spec.get("completion_criteria", {"required_artifacts": [], "required_metrics": []})
    )
    phases = phase_graph.normalize_phases(spec, resolved["argv"])
    effective_config = {
        "path": spec["config"],
        "sha256": research.sha256_file(resolved["config_path"]),
        "resolved": deepcopy(resolved["config"]),
    }
    return plan_identity.build_bundle(
        spec=spec,
        protocol_id=protocol_id,
        run_class=run_class,
        observation_status=observation_status,
        parameters=parameters,
        matrix=matrix,
        cells=cells,
        phases=phases,
        effective_config=effective_config,
        evaluation=resolved["evaluation"],
        environment=resolved["environment"],
        environment_identity=environment_identity(resolved),
        executor=resolved["executor"],
        execution_environment=execution_environment.declared_environment(
            resolved["executor"], resolved["root"]
        ),
        git=research.git_state(resolved["root"]),
        resolved_inputs=resolved["inputs"],
        recovery_policy=recovery_policy,
        completion_criteria=completion_criteria,
    )


def plan_spec(spec_path: Path, root: Path = ROOT) -> dict[str, Any]:
    resolved = research.validate_spec(spec_path, root)
    return build_plan(resolved)


def render_plan(spec_path: Path, root: Path = ROOT) -> str:
    import json

    return json.dumps(plan_spec(spec_path, root), indent=2, sort_keys=True) + "\n"
