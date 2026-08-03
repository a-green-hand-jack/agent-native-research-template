# Evidence Manifests

This directory contains compact, reviewed evidence envelopes promoted from local run manifests.
Raw logs, checkpoints, and large artifacts remain under ignored `runs/` paths or external storage.

The built-in local runner deliberately supports one bounded execution rather than pretending to be
a sweep scheduler. A runnable spec must declare exactly one fixed seed, `max_runs: 1`, a positive
`max_wall_time_seconds`, and `stopping_rule: {type: after_runs, runs: 1}`. The selected seed is
exposed to the command as `RESEARCH_SEED`. Multi-seed, random, range, cost-accounted, and
metric-driven execution must be delegated to an external scheduler that creates separate runs.

Generic input declarations use `path`, `uri`, or `opaque` identities. Repository path inputs are
hashed before execution and checked again before replay. URI and opaque identities are recorded as
declared and are never fetched implicitly. See `docs/INPUT_IDENTITY.md`.

Declared artifacts are copied into `runs/<run-id>/artifacts/` before they are recorded. The run
manifest keeps both the immutable snapshot path and the original `source_path`; later runs may
replace the original output without invalidating the earlier run.

The JSON Schema documents under `schemas/` are executable contracts, not examples. Draft 2020-12
validation checks each experiment, environment, executor, evaluation, run manifest, and evidence
envelope at its owning boundary. Python validation remains responsible for cross-file references,
repository paths, global identifiers, command agreement, input hashing, replay drift, and artifact
checksums.

A run's `state.json` is non-terminal progress; `result.json` is the atomic terminal completion
record. Status is never inferred from process or accelerator idleness. Missing terminal evidence
is incomplete, and verification is a read-only projection rather than a mutation.

Promote a run only after its artifact checksums and interpretation have been reviewed. Evidence
execution, verification, replay, and promotion belong exclusively to `tools/evidence.py`;
`tools/research.py` validates research definitions and supplies shared non-executing utilities:

```bash
uv run python tools/evidence.py validate experiments/specs/<name>.yaml
uv run python tools/evidence.py verify-run <run-id>
uv run python tools/evidence.py promote <run-id> \
  --decision accepted \
  --note "Supports the stated smoke claim."
```

Metrics are structured observations with explicit units, sampling, aggregation, resource mode,
and observation counts. Missing observations use named reasons; NaN and fabricated dispersion
are rejected. See `docs/METRIC_OBSERVATIONS.md`.

Each evidence file records:

- the source run ID, manifest path, and source-manifest SHA-256;
- resolved input identities and immutable artifact snapshots;
- the promotion timestamp;
- a review decision: `accepted`, `rejected`, or `inconclusive`;
- an optional review note;
- the complete immutable run manifest.

Do not edit a promoted evidence file in place. A corrected execution receives a new run ID and a
new evidence envelope. Reports should cite the promoted run ID and evidence file hash.

Before retiring temporary storage or execution surfaces, inventory and verify run artifacts and
logical assets with `tools/archive.py`. A checksum-only record is not a verified copy, and
non-reconstructable items require two independent verified fault domains. Retirement preflight
never performs deletion; see `docs/ARCHIVE_RETIREMENT.md`.
