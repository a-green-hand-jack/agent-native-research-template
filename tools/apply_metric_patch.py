from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}, found {count}: {old!r}")
    target.write_text(content.replace(old, new), encoding="utf-8")


def patch_research() -> None:
    replace_once(
        "tools/research.py",
        "import input_identity\n",
        "import input_identity\nimport metric_observation\n",
    )
    replace_once(
        "tools/research.py",
        "    source = metric.get(\"source\")\n",
        "    try:\n"
        "        metric_observation.context(metric)\n"
        "        metric_observation.dispersion(metric)\n"
        "    except metric_observation.MetricObservationError as exc:\n"
        "        raise SpecError(str(exc)) from exc\n"
        "    source = metric.get(\"source\")\n",
    )
    replace_once(
        "tools/research.py",
        "    elif source_type == \"json_file\":\n",
        "    elif source_type == \"missing\":\n"
        "        if source.get(\"reason\") not in metric_observation.MISSING_REASONS:\n"
        "            raise SpecError(f\"metric {metric_id!r} missing reason is invalid\")\n"
        "    elif source_type == \"json_file\":\n",
    )
    replace_once(
        "tools/research.py",
        "            f\"metric {metric_id!r} source.type must be return_code, stdout_regex, or json_file\"\n",
        "            f\"metric {metric_id!r} source.type must be return_code, stdout_regex, json_file, or missing\"\n",
    )
    old_extract = '''def extract_return_code_metrics(
    evaluation: dict[str, Any], return_code: int
) -> dict[str, bool | int]:
    metrics: dict[str, bool | int] = {}
    for metric in evaluation["metrics"]:
        source = metric["source"]
        if source["type"] != "return_code":
            continue
        metrics[metric["id"]] = return_code == 0 if metric["type"] == "boolean" else return_code
    return metrics
'''
    new_extract = '''def extract_return_code_metrics(
    evaluation: dict[str, Any], return_code: int
) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for metric in evaluation["metrics"]:
        source = metric["source"]
        if source["type"] == "return_code":
            raw = return_code == 0 if metric["type"] == "boolean" else return_code
            metrics[metric["id"]] = metric_observation.measured(metric, raw)
        elif source["type"] == "missing":
            metrics[metric["id"]] = metric_observation.missing(metric, source["reason"])
    return metrics
'''
    replace_once("tools/research.py", old_extract, new_extract)
    replace_once(
        "tools/research.py",
        "    except (SpecError, input_identity.InputIdentityError, OSError) as exc:\n",
        "    except (\n"
        "        SpecError,\n"
        "        input_identity.InputIdentityError,\n"
        "        metric_observation.MetricObservationError,\n"
        "        OSError,\n"
        "    ) as exc:\n",
    )


def patch_evidence() -> None:
    replace_once(
        "tools/evidence.py",
        "import input_identity\nimport phase_graph\n",
        "import input_identity\nimport metric_observation\nimport phase_graph\n",
    )
    replace_once(
        "tools/evidence.py",
        ") -> tuple[dict[str, bool | int | float | str], list[str]]:\n"
        "    metrics: dict[str, bool | int | float | str] = {}\n",
        ") -> tuple[dict[str, dict[str, Any]], list[str]]:\n"
        "    metrics: dict[str, dict[str, Any]] = {}\n",
    )
    replace_once(
        "tools/evidence.py",
        "            if source[\"type\"] == \"return_code\":\n",
        "            if source[\"type\"] == \"missing\":\n"
        "                metrics[metric_id] = metric_observation.missing(\n"
        "                    metric, source[\"reason\"]\n"
        "                )\n"
        "                continue\n"
        "            if source[\"type\"] == \"return_code\":\n",
    )
    replace_once(
        "tools/evidence.py",
        "            metrics[metric_id] = coerce_metric(raw, metric_type, metric_id)\n"
        "        except (EvidenceError, OSError, ValueError, json.JSONDecodeError) as exc:\n"
        "            errors.append(str(exc))\n",
        "            value = coerce_metric(raw, metric_type, metric_id)\n"
        "            metrics[metric_id] = metric_observation.measured(metric, value)\n"
        "        except (\n"
        "            EvidenceError,\n"
        "            metric_observation.MetricObservationError,\n"
        "            OSError,\n"
        "            ValueError,\n"
        "            json.JSONDecodeError,\n"
        "        ) as exc:\n"
        "            errors.append(str(exc))\n"
        "            try:\n"
        "                metrics[metric_id] = metric_observation.missing(\n"
        "                    metric, \"evaluation_error\", str(exc)\n"
        "                )\n"
        "            except metric_observation.MetricObservationError:\n"
        "                pass\n",
    )
    replace_once(
        "tools/evidence.py",
        "        input_identity.InputIdentityError,\n",
        "        input_identity.InputIdentityError,\n        metric_observation.MetricObservationError,\n",
    )


def patch_schemas() -> None:
    evaluation_path = ROOT / "schemas/evaluation.schema.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    evaluation["$defs"]["source"]["oneOf"].append(
        {
            "type": "object",
            "required": ["type", "reason"],
            "properties": {
                "type": {"const": "missing"},
                "reason": {
                    "enum": [
                        "not_applicable",
                        "not_measured",
                        "empty_population",
                        "evaluation_error",
                    ]
                },
            },
            "additionalProperties": False,
        }
    )
    metric = evaluation["properties"]["metrics"]["items"]
    metric["required"].extend(
        ["unit", "aggregation", "resource_mode", "sample_count", "observation_count"]
    )
    metric["properties"].update(
        {
            "unit": {"type": "string", "minLength": 1},
            "aggregation": {"enum": ["single", "mean", "sum", "min", "max", "rate"]},
            "resource_mode": {
                "enum": [
                    "single_process",
                    "isolated_request",
                    "multi_worker_wall_clock",
                    "per_sequence",
                    "per_token",
                    "device_aggregate",
                ]
            },
            "sample_count": {"type": "integer", "minimum": 1},
            "observation_count": {"type": "integer", "minimum": 1},
            "dispersion": {
                "type": "object",
                "required": ["kind", "value"],
                "properties": {
                    "kind": {
                        "enum": [
                            "standard_deviation",
                            "standard_error",
                            "range",
                            "confidence_interval",
                        ]
                    },
                    "value": {"type": "number"},
                },
                "additionalProperties": False,
            },
        }
    )
    evaluation_path.write_text(json.dumps(evaluation, indent=2) + "\n", encoding="utf-8")

    run_path = ROOT / "schemas/run-manifest.schema.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["$defs"]["metric_observation"] = {
        "oneOf": [
            {
                "type": "object",
                "required": [
                    "state",
                    "value",
                    "unit",
                    "sample_count",
                    "aggregation",
                    "resource_mode",
                    "observation_count",
                ],
                "properties": {
                    "state": {"const": "measured"},
                    "value": {"type": ["boolean", "integer", "number", "string"]},
                    "unit": {"type": "string", "minLength": 1},
                    "sample_count": {"type": "integer", "minimum": 1},
                    "aggregation": {"enum": ["single", "mean", "sum", "min", "max", "rate"]},
                    "resource_mode": {
                        "enum": [
                            "single_process",
                            "isolated_request",
                            "multi_worker_wall_clock",
                            "per_sequence",
                            "per_token",
                            "device_aggregate",
                        ]
                    },
                    "observation_count": {"type": "integer", "minimum": 1},
                    "dispersion": {"type": "object"},
                    "legacy": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            {
                "type": "object",
                "required": [
                    "state",
                    "missing_reason",
                    "unit",
                    "sample_count",
                    "aggregation",
                    "resource_mode",
                    "observation_count",
                ],
                "properties": {
                    "state": {"const": "missing"},
                    "missing_reason": {
                        "enum": [
                            "not_applicable",
                            "not_measured",
                            "empty_population",
                            "evaluation_error",
                        ]
                    },
                    "detail": {"type": "string"},
                    "unit": {"type": "string", "minLength": 1},
                    "sample_count": {"type": "integer", "minimum": 1},
                    "aggregation": {"enum": ["single", "mean", "sum", "min", "max", "rate"]},
                    "resource_mode": {
                        "enum": [
                            "single_process",
                            "isolated_request",
                            "multi_worker_wall_clock",
                            "per_sequence",
                            "per_token",
                            "device_aggregate",
                        ]
                    },
                    "observation_count": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
        ]
    }
    run["properties"]["metrics"] = {
        "type": "object",
        "additionalProperties": {"$ref": "#/$defs/metric_observation"},
    }
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")


def add_context(metric: dict[str, object], unit: str) -> None:
    metric.update(
        unit=unit,
        aggregation="single",
        resource_mode="single_process",
        sample_count=1,
        observation_count=1,
    )


def patch_examples_and_tests() -> None:
    smoke_path = ROOT / "evals/smoke.yaml"
    smoke = yaml.safe_load(smoke_path.read_text(encoding="utf-8"))
    for metric in smoke["metrics"]:
        add_context(metric, "boolean" if metric["type"] == "boolean" else "count")
    smoke_path.write_text(yaml.safe_dump(smoke, sort_keys=False), encoding="utf-8")

    replace_once(
        "tests/test_research.py",
        "            \"    source:\\n      type: return_code\\n\"\n",
        "            \"    unit: boolean\\n    aggregation: single\\n\"\n"
        "            \"    resource_mode: single_process\\n    sample_count: 1\\n\"\n"
        "            \"    observation_count: 1\\n    source:\\n      type: return_code\\n\"\n",
    )
    replace_once(
        "tests/test_evidence.py",
        "        \"    source:\\n      type: return_code\\n\"\n",
        "        \"    unit: boolean\\n    aggregation: single\\n\"\n"
        "        \"    resource_mode: single_process\\n    sample_count: 1\\n\"\n"
        "        \"    observation_count: 1\\n    source:\\n      type: return_code\\n\"\n",
    )
    replace_once(
        "tests/test_evidence.py",
        "        \"    source:\\n      type: stdout_regex\\n      pattern: 'accuracy=([0-9.]+)'\\n\"\n",
        "        \"    unit: fraction\\n    aggregation: single\\n\"\n"
        "        \"    resource_mode: single_process\\n    sample_count: 1\\n\"\n"
        "        \"    observation_count: 1\\n    source:\\n\"\n"
        "        \"      type: stdout_regex\\n      pattern: 'accuracy=([0-9.]+)'\\n\"\n",
    )
    replace_once(
        "tests/test_evidence.py",
        "        \"    source:\\n      type: json_file\\n      path: outputs/metrics.json\\n      key: score\\n\",\n",
        "        \"    unit: fraction\\n    aggregation: single\\n\"\n"
        "        \"    resource_mode: single_process\\n    sample_count: 1\\n\"\n"
        "        \"    observation_count: 1\\n    source:\\n      type: json_file\\n\"\n"
        "        \"      path: outputs/metrics.json\\n      key: score\\n\",\n",
    )
    replace_once(
        "tests/test_evidence.py",
        "    assert manifest[\"metrics\"] == {\"accuracy\": 0.75, \"score\": 0.75, \"success\": True}\n",
        "    assert manifest[\"metrics\"][\"accuracy\"][\"value\"] == 0.75\n"
        "    assert manifest[\"metrics\"][\"score\"][\"value\"] == 0.75\n"
        "    assert manifest[\"metrics\"][\"success\"][\"value\"] is True\n",
    )
    replace_once(
        "tests/test_run_status_evidence.py",
        "    assert results[\"metrics\"][\"success\"] is True\n",
        "    assert results[\"metrics\"][\"success\"][\"value\"] is True\n",
    )


def patch_docs() -> None:
    replace_once(
        ".agents/governance/CONTRACT.md",
        "- Accepted reports cite run IDs; paper values are generated from locked evidence rather than\n",
        "- New metric evidence uses contextual observations, never bare ambiguous scalars. Measured\n"
        "  values record unit, sample count, aggregation, resource mode, and independent observation\n"
        "  count. Missing values use explicit reasons and remain distinct from zero. NaN and infinity\n"
        "  are invalid durable evidence; dispersion requiring repeated observations is rejected when\n"
        "  fewer than two observations exist.\n"
        "- Accepted reports cite run IDs; paper values are generated from locked evidence rather than\n",
    )
    replace_once(
        "evidence/manifests/README.md",
        "Each evidence file records:\n",
        "Metrics are structured observations with explicit units, sampling, aggregation, resource mode,\n"
        "and observation counts. Missing observations use named reasons; NaN and fabricated dispersion\n"
        "are rejected. See `docs/METRIC_OBSERVATIONS.md`.\n\nEach evidence file records:\n",
    )
    units_path = ROOT / ".agents/governance/REPO_UNITS.yaml"
    units = yaml.safe_load(units_path.read_text(encoding="utf-8"))
    required = units["required_paths"]["functional"]
    for path in ("docs/METRIC_OBSERVATIONS.md", "tools/metric_observation.py"):
        if path not in required:
            required.append(path)
    required.sort()
    units_path.write_text(yaml.safe_dump(units, sort_keys=False), encoding="utf-8")


def main() -> None:
    patch_research()
    patch_evidence()
    patch_schemas()
    patch_examples_and_tests()
    patch_docs()


if __name__ == "__main__":
    main()
