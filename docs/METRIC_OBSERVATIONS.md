# Contextual Metric Observations

A metric name and scalar value are not enough to interpret an experiment. New run evidence records
each metric as a contextual observation.

## Measured observations

```json
{
  "state": "measured",
  "value": 0.25,
  "unit": "seconds",
  "sample_count": 100,
  "aggregation": "mean",
  "resource_mode": "isolated_request",
  "observation_count": 3,
  "dispersion": {
    "kind": "standard_deviation",
    "value": 0.04
  }
}
```

Required context:

- unit;
- sample count represented by the value;
- aggregation (`single`, `mean`, `sum`, `min`, `max`, or `rate`);
- resource mode (`single_process`, `isolated_request`, `multi_worker_wall_clock`,
  `per_sequence`, `per_token`, or `device_aggregate`);
- independent observation count.

Latency and throughput therefore cannot silently share an unspecified denominator or concurrency
model. One quality run may be a valid measured observation, but it cannot claim a cross-observation
standard deviation.

## Missing observations

Missing is not zero and is not NaN:

```json
{
  "state": "missing",
  "missing_reason": "not_measured",
  "unit": "joules",
  "sample_count": 1,
  "aggregation": "sum",
  "resource_mode": "device_aggregate",
  "observation_count": 1
}
```

Allowed reasons are `not_applicable`, `not_measured`, `empty_population`, and `evaluation_error`.
Evaluation extraction failures remain in `evaluation_errors` and also create a missing observation
for the affected metric.

NaN and infinity are rejected before durable JSON is written. Absence never becomes a fabricated
number or dispersion estimate.

## Legacy manifests

Readers may normalize legacy scalar metrics using explicit defaults and the marker
`legacy: true`. New manifests always use structured observations. Legacy normalization does not
invent units, sample counts, or scientific interpretation; the unit remains `legacy_unspecified`.
