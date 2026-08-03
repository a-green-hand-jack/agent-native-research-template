from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import metric_observation
from test_evidence import configure_outputs

import evidence


def add_metric_context(root: Path) -> None:
    path = root / "evals/smoke.yaml"
    evaluation = yaml.safe_load(path.read_text(encoding="utf-8"))
    for metric in evaluation["metrics"]:
        if metric["id"] == "success":
            metric.update(
                unit="boolean",
                aggregation="single",
                resource_mode="single_process",
                sample_count=1,
                observation_count=1,
            )
        else:
            metric.update(
                unit="fraction",
                aggregation="single",
                resource_mode="single_process",
                sample_count=1,
                observation_count=1,
            )
    path.write_text(yaml.safe_dump(evaluation, sort_keys=False), encoding="utf-8")


def test_run_manifest_contains_contextual_observations(tmp_path: Path) -> None:
    spec_path = configure_outputs(tmp_path)
    add_metric_context(tmp_path)
    manifest_path, code = evidence.run_spec(spec_path, tmp_path)
    assert code == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["metrics"]["success"] == {
        "state": "measured",
        "value": True,
        "unit": "boolean",
        "sample_count": 1,
        "aggregation": "single",
        "resource_mode": "single_process",
        "observation_count": 1,
    }
    assert manifest["metrics"]["accuracy"]["value"] == 0.75
    assert manifest["metrics"]["accuracy"]["unit"] == "fraction"


def test_extraction_error_produces_missing_observation(tmp_path: Path) -> None:
    spec_path = configure_outputs(tmp_path)
    add_metric_context(tmp_path)
    path = tmp_path / "evals/smoke.yaml"
    evaluation = yaml.safe_load(path.read_text(encoding="utf-8"))
    for metric in evaluation["metrics"]:
        if metric["id"] == "accuracy":
            metric["source"]["pattern"] = "does-not-match"
    path.write_text(yaml.safe_dump(evaluation, sort_keys=False), encoding="utf-8")
    manifest_path, code = evidence.run_spec(spec_path, tmp_path)
    assert code != 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    observation = manifest["metrics"]["accuracy"]
    assert observation["state"] == "missing"
    assert observation["missing_reason"] == "evaluation_error"
    assert manifest["evaluation_errors"]


def test_declared_missing_metric_is_not_fabricated(tmp_path: Path) -> None:
    spec_path = configure_outputs(tmp_path)
    add_metric_context(tmp_path)
    path = tmp_path / "evals/smoke.yaml"
    evaluation = yaml.safe_load(path.read_text(encoding="utf-8"))
    evaluation["metrics"].append(
        {
            "id": "energy",
            "type": "number",
            "direction": "minimize",
            "unit": "joules",
            "aggregation": "sum",
            "resource_mode": "device_aggregate",
            "sample_count": 1,
            "observation_count": 1,
            "source": {"type": "missing", "reason": "not_measured"},
        }
    )
    path.write_text(yaml.safe_dump(evaluation, sort_keys=False), encoding="utf-8")
    manifest_path, _ = evidence.run_spec(spec_path, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["metrics"]["energy"]["state"] == "missing"
    assert manifest["metrics"]["energy"]["missing_reason"] == "not_measured"
    assert "value" not in manifest["metrics"]["energy"]


def test_non_finite_metric_never_reaches_json(tmp_path: Path) -> None:
    metric = {
        "id": "score",
        "unit": "fraction",
        "aggregation": "single",
        "resource_mode": "single_process",
        "sample_count": 1,
        "observation_count": 1,
    }
    with pytest.raises(metric_observation.MetricObservationError):
        metric_observation.measured(metric, math.nan)
