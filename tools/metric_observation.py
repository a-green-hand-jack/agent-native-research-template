from __future__ import annotations

import math
from typing import Any

MISSING_REASONS = {
    "not_applicable",
    "not_measured",
    "empty_population",
    "evaluation_error",
}
AGGREGATIONS = {"single", "mean", "sum", "min", "max", "rate"}
RESOURCE_MODES = {
    "single_process",
    "isolated_request",
    "multi_worker_wall_clock",
    "per_sequence",
    "per_token",
    "device_aggregate",
}


class MetricObservationError(ValueError):
    """Raised when a metric observation is ambiguous or statistically invalid."""


def positive_integer(value: object, field: str, default: int = 1) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise MetricObservationError(f"{field} must be a positive integer")
    return value


def context(metric: dict[str, Any]) -> dict[str, Any]:
    metric_id = metric.get("id", "metric")
    unit = metric.get("unit")
    if not isinstance(unit, str) or not unit.strip():
        raise MetricObservationError(f"metric {metric_id!r} requires a unit")
    aggregation = metric.get("aggregation", "single")
    if aggregation not in AGGREGATIONS:
        raise MetricObservationError(
            f"metric {metric_id!r} aggregation must be one of: {', '.join(sorted(AGGREGATIONS))}"
        )
    resource_mode = metric.get("resource_mode", "single_process")
    if resource_mode not in RESOURCE_MODES:
        raise MetricObservationError(
            f"metric {metric_id!r} resource_mode must be one of: "
            f"{', '.join(sorted(RESOURCE_MODES))}"
        )
    sample_count = positive_integer(metric.get("sample_count"), f"metric {metric_id} sample_count")
    observation_count = positive_integer(
        metric.get("observation_count"), f"metric {metric_id} observation_count"
    )
    return {
        "unit": unit,
        "sample_count": sample_count,
        "aggregation": aggregation,
        "resource_mode": resource_mode,
        "observation_count": observation_count,
    }


def finite_value(value: object, metric_id: str) -> bool | int | float | str:
    if isinstance(value, bool | int | str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MetricObservationError(f"metric {metric_id!r} must not contain NaN or infinity")
        return value
    raise MetricObservationError(f"metric {metric_id!r} value is not a supported scalar")


def dispersion(metric: dict[str, Any]) -> dict[str, Any] | None:
    value = metric.get("dispersion")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise MetricObservationError(f"metric {metric.get('id')!r} dispersion must be a mapping")
    kind = value.get("kind")
    amount = value.get("value")
    if kind not in {"standard_deviation", "standard_error", "range", "confidence_interval"}:
        raise MetricObservationError(f"metric {metric.get('id')!r} dispersion kind is invalid")
    if not isinstance(amount, int | float) or isinstance(amount, bool) or not math.isfinite(float(amount)):
        raise MetricObservationError(f"metric {metric.get('id')!r} dispersion value must be finite")
    observations = positive_integer(
        metric.get("observation_count"), f"metric {metric.get('id')} observation_count"
    )
    if kind in {"standard_deviation", "standard_error", "confidence_interval"} and observations < 2:
        raise MetricObservationError(
            f"metric {metric.get('id')!r} cannot report {kind} with fewer than two observations"
        )
    return {"kind": kind, "value": amount}


def measured(metric: dict[str, Any], value: object) -> dict[str, Any]:
    metric_id = str(metric["id"])
    record: dict[str, Any] = {
        "state": "measured",
        "value": finite_value(value, metric_id),
        **context(metric),
    }
    spread = dispersion(metric)
    if spread is not None:
        record["dispersion"] = spread
    return record


def missing(metric: dict[str, Any], reason: str, detail: str | None = None) -> dict[str, Any]:
    if reason not in MISSING_REASONS:
        raise MetricObservationError(
            f"missing reason must be one of: {', '.join(sorted(MISSING_REASONS))}"
        )
    record: dict[str, Any] = {
        "state": "missing",
        "missing_reason": reason,
        **context(metric),
    }
    if detail:
        record["detail"] = detail
    return record


def normalize_legacy_record(metric_id: str, value: object) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("state") in {"measured", "missing"}:
        return value
    return {
        "state": "measured",
        "value": finite_value(value, metric_id),
        "unit": "legacy_unspecified",
        "sample_count": 1,
        "aggregation": "single",
        "resource_mode": "single_process",
        "observation_count": 1,
        "legacy": True,
    }


def normalize_legacy_metrics(value: object) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        raise MetricObservationError("legacy metrics must be a mapping")
    return {str(metric_id): normalize_legacy_record(str(metric_id), record) for metric_id, record in value.items()}
