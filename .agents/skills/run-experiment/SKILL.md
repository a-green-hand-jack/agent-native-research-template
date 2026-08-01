---
name: run-experiment
description: Execute, verify, replay, and promote a reproducible project experiment. Use for training, inference, rollouts, benchmark runs, sweeps, ablations, or any result that must be compared or cited later.
---

# Run Experiment

Separate experiment intent, observed execution facts, verification, and interpretation.

## Prepare

1. Identify the question and evaluation that can answer it.
2. Start from a versioned experiment spec.
3. Resolve the contribution, config, environment, executor, and evaluation.
4. Declare seed policy, resource budget, stopping rule, inclusion criteria, metrics, and artifacts
   before observing results.
5. Commit a checkpoint before an expensive run whenever practical.
6. Validate the definitions and run the smallest smoke path:

```bash
uv run python tools/research.py validate experiments/specs/<name>.yaml
make smoke
```

## Execute

Use the evidence-aware runner:

```bash
uv run python tools/evidence.py run experiments/specs/<name>.yaml
```

For a retry or deliberately derived execution, name the parent run:

```bash
uv run python tools/evidence.py run experiments/specs/<name>.yaml --parent <run-id>
```

Each execution receives a unique run ID and writes an ignored local manifest under
`runs/<run-id>/manifest.json`. The manifest records Git state, the resolved spec, versioned
configuration and environment hashes, typed metrics, declared artifact checksums, timestamps,
status, and optional parent identity.

## Verify And Replay

Verify every recorded artifact before using or promoting a result:

```bash
uv run python tools/evidence.py verify-run <run-id>
```

Replay checks the recorded spec, config, environment, lockfile, executor, and evaluation hashes
against the current checkout before executing:

```bash
uv run python tools/evidence.py replay <run-id>
```

Do not use `--allow-drift` unless the divergence is intentional and will be explained in the new
run's report. A replay is a new run linked to its parent; it never overwrites the original.

## Promote Evidence

Keep raw logs and large artifacts under `runs/` or external storage. After reviewing the run,
promote an immutable evidence envelope with an explicit interpretation:

```bash
uv run python tools/evidence.py promote <run-id> \
  --decision accepted \
  --note "Evidence supports the stated claim."
```

The decision is `accepted`, `rejected`, or `inconclusive`. Promoted evidence records the source
manifest checksum, review decision, review note, and complete run manifest.

## Handoff

Return:

```text
question and spec path
run ID and optional parent run ID
validation and artifact-verification evidence
metrics and evaluation errors
artifact locations and checksums
reproduction or replay command
promotion path and review decision, when applicable
whether the evidence supports, contradicts, or leaves the question unresolved
```

Do not delete failed runs, edit promoted evidence, or copy terminal values into reports without a
traceable run ID.
