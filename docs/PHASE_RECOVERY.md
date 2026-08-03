# Phase-Scoped Execution And Recovery

The canonical runner may execute an ordered phase graph instead of one monolithic command. A spec
without `phases` remains compatible and is normalized to one `main` phase.

## Phase graph

```yaml
phases:
  - id: generation
    command: [python, tools/generate.py]
    asset_phase: generation
    outputs:
      - path: outputs/generations.jsonl
        required: true

  - id: evaluation
    command: [python, tools/evaluate.py]
    depends_on: [generation]
    asset_phase: evaluation
    outputs:
      - path: outputs/metrics.json
        required: true
```

Phase IDs are stable lowercase identifiers. Dependencies form an acyclic graph. When several phases
are ready, lexical phase ID order makes execution deterministic.

## Phase evidence

Every phase writes:

```text
runs/<run-id>/phases/<phase-id>/result.json
runs/<run-id>/phases/<phase-id>/stdout.log
runs/<run-id>/phases/<phase-id>/stderr.log
runs/<run-id>/phases/<phase-id>/artifacts/...
```

The terminal result is `succeeded`, `failed`, `incomplete`, or `reused`. A failed phase prevents its
dependents from running; those phases receive explicit `incomplete` results rather than disappearing.
Required output patterns are copied into immutable phase-scoped snapshots. Missing required output
fails the phase even when the process returned zero.

Downstream commands receive verified dependency snapshots through
`RESEARCH_PHASE_<ID>_ARTIFACT_DIR`. They never need to read mutable producer output paths.

## Phase retry

Retry only a failed or incomplete phase:

```bash
uv run python tools/evidence.py retry-phase <parent-run-id> --phase evaluation
```

The parent run is verified before retry. Every transitive dependency must have succeeded. The new
child run records the parent, retry phase, reused artifact checksums, and whether generation was
skipped. Reused phase artifacts remain at their immutable parent locations; the child never edits or
overwrites the parent run.

The retry uses the current checked-out spec only after normal replay drift checks pass. Use a new
experiment protocol when the intended phase graph or command changes.

## Boundary

This is local deterministic recovery, not a distributed scheduler. It does not submit remote jobs,
automatically retry failures, or infer that idle hardware means completion.
