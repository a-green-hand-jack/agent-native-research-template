from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import metric_observation


def metric(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "id": "latency",
        "unit": "seconds",
        "aggregation": "mean",
        "resource_mode": "isolated_request",
        "sample_count": 10,
        "observation_count": 1,
    }
    value.update(updates)
    return value


def test_measured_observation_records_context() -> None:
    record = metric_observation.measured(metric(), 0.25)
    assert record == {
        "state": "measured",
        "value": 0.25,
        "unit": "seconds",
        "sample_count": 10,
        "aggregation": "mean",
        "resource_mode": "isolated_request",
        "observation_count": 1,
    }


def test_missing_is_distinct_from_zero() -> None:
    missing = metric_observation.missing(metric(), "not_measured", "phase skipped")
    measured = metric_observation.measured(metric(), 0.0)
    assert missing["state"] == "missing"
    assert "value" not in missing
    assert measured["state"] == "measured"
    assert measured["value"] == 0.0


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_values_are_rejected(value: float) -> None:
    with pytest.raises(metric_observation.MetricObservationError, match="NaN or infinity"):
        metric_observation.measured(metric(), value)


def test_single_observation_cannot_claim_standard_deviation() -> None:
    with pytest.raises(metric_observation.MetricObservationError, match="fewer than two"):
        metric_observation.measured(
            metric(dispersion={"kind": "standard_deviation", "value": 0.1}),
            0.25,
        )


def test_multiple_observations_can_record_dispersion() -> None:
    record = metric_observation.measured(
        metric(
            observation_count=3,
            dispersion={"kind": "standard_deviation", "value": 0.1},
        ),
        0.25,
    )
    assert record["dispersion"] == {"kind": "standard_deviation", "value": 0.1}


def test_legacy_scalar_reader_is_explicit() -> None:
    metrics = metric_observation.normalize_legacy_metrics({"success": True, "score": 0.5})
    assert metrics["success"]["legacy"] is True
    assert metrics["success"]["unit"] == "legacy_unspecified"
    assert metrics["score"]["value"] == 0.5
