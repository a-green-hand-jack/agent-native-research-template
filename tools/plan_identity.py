from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

IDENTITY_VERSION = 1


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def record(projection: dict[str, Any]) -> dict[str, Any]:
    return {"sha256": sha256_json(projection), "resolved": projection}


def phase_topology(phases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": phase["id"],
            "depends_on": list(phase.get("depends_on", [])),
            "asset_phase": phase.get("asset_phase", "all"),
            "outputs": deepcopy(phase.get("outputs", [])),
        }
        for phase in phases
    ]


def build_bundle(
    *,
    spec: dict[str, Any],
    protocol_id: str,
    run_class: str,
    observation_status: str,
    parameters: dict[str, Any],
    matrix: dict[str, Any],
    cells: list[dict[str, Any]],
    phases: list[dict[str, Any]],
    effective_config: dict[str, Any],
    evaluation: dict[str, Any],
    environment: dict[str, Any],
    environment_identity: dict[str, Any],
    executor: dict[str, Any],
    execution_environment: dict[str, Any],
    git: dict[str, Any],
    resolved_inputs: list[dict[str, Any]],
    resolved_external_facts: list[dict[str, Any]],
    recovery_policy: dict[str, Any],
    completion_criteria: dict[str, Any],
) -> dict[str, Any]:
    protocol_projection = {
        "identity_version": IDENTITY_VERSION,
        "experiment_id": spec["id"],
        "protocol_id": protocol_id,
        "run_class": run_class,
        "observation_status": observation_status,
        "question": spec["question"],
        "contribution": spec["contribution"],
        "scientific_parameters": deepcopy(parameters),
        "matrix": deepcopy(matrix),
        "cells": deepcopy(cells),
        "seed_policy": deepcopy(spec["seed_policy"]),
        "evaluation": deepcopy(evaluation),
        "inputs": deepcopy(spec.get("inputs", [])),
        "logical_assets": deepcopy(spec.get("assets", [])),
        "external_fact_ids": list(spec.get("external_facts", [])),
        "phase_topology": phase_topology(phases),
        "inclusion_criteria": list(spec["inclusion_criteria"]),
        "recovery_policy": deepcopy(recovery_policy),
        "completion_criteria": deepcopy(completion_criteria),
    }
    protocol = record(protocol_projection)

    execution_projection = {
        "identity_version": IDENTITY_VERSION,
        "plan_version": 2,
        "protocol_sha256": protocol["sha256"],
        "experiment_id": spec["id"],
        "protocol_id": protocol_id,
        "run_class": run_class,
        "observation_status": observation_status,
        "question": spec["question"],
        "contribution": spec["contribution"],
        "scientific_parameters": deepcopy(parameters),
        "matrix": deepcopy(matrix),
        "cells": deepcopy(cells),
        "effective_config": deepcopy(effective_config),
        "environment": deepcopy(environment_identity),
        "code": deepcopy(git),
        "phases": deepcopy(phases),
        "seed_policy": deepcopy(spec["seed_policy"]),
        "budget": deepcopy(spec["budget"]),
        "stopping_rule": deepcopy(spec["stopping_rule"]),
        "resolved_inputs": deepcopy(resolved_inputs),
        "resolved_external_facts": deepcopy(resolved_external_facts),
        "artifacts": deepcopy(spec.get("artifacts", [])),
        "inclusion_criteria": list(spec["inclusion_criteria"]),
        "recovery_policy": deepcopy(recovery_policy),
        "completion_criteria": deepcopy(completion_criteria),
    }
    execution = record(execution_projection)

    binding_projection = {
        "identity_version": IDENTITY_VERSION,
        "binding_state": "declared",
        "executor_id": spec["executor"],
        "executor": deepcopy(executor),
        "execution_environment": deepcopy(execution_environment),
        "asset_bindings": deepcopy(executor.get("asset_bindings", {})),
    }
    binding = record(binding_projection)

    return {
        "identity_version": IDENTITY_VERSION,
        "protocol": protocol,
        "execution": execution,
        "binding": binding,
        "sha256": execution["sha256"],
        "resolved": execution["resolved"],
    }


def resolve_binding(
    bundle: dict[str, Any],
    asset_preflight: dict[str, Any],
    environment_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    updated = deepcopy(bundle)
    projection = deepcopy(updated["binding"]["resolved"])
    projection["binding_state"] = "resolved"
    projection["resolved_assets"] = deepcopy(asset_preflight.get("assets", []))
    projection["asset_preflight_sha256"] = asset_preflight["sha256"]
    if environment_evidence is not None:
        projection["execution_environment_evidence"] = deepcopy(environment_evidence)
    updated["binding"] = record(projection)
    return updated


def identity_summary(bundle: dict[str, Any]) -> dict[str, str]:
    return {
        "protocol_sha256": bundle["protocol"]["sha256"],
        "execution_plan_sha256": bundle["execution"]["sha256"],
        "binding_sha256": bundle["binding"]["sha256"],
    }
