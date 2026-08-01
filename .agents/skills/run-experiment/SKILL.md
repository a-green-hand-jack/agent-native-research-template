---
name: run-experiment
description: Execute and evaluate a reproducible project experiment. Use for training, inference, rollouts, benchmark runs, sweeps, ablations, or any result that must be compared or cited later.
---

# Run Experiment

Separate intended experiment design, observed execution facts, and later interpretation.

## Prepare

1. Identify the question and the evaluation that can answer it.
2. Start from a versioned experiment spec.
3. Resolve the contribution, config, environment, executor, and evaluation.
4. Declare the seed policy, resource budget, stopping rule, and inclusion criteria before
   observing results.
5. Commit a checkpoint before an expensive run whenever practical.
6. Validate the spec and run the smallest smoke path:

```bash
uv run python tools/research.py validate experiments/specs/<name>.yaml
make smoke
```

## Execute

Use the public project runner rather than reconstructing the command manually:

```bash
uv run python tools/research.py run experiments/specs/<name>.yaml
```

Each execution receives a unique run ID and writes an ignored local manifest under
`runs/<run-id>/manifest.json`. The manifest captures:

```text
run ID and parent run
base Git SHA and dirty-state hash
resolved spec and spec hash
environment definition and lock hash
executor and evaluation definitions
seed policy, budget, stopping rule, and inclusion criteria
command, timestamps, return status
captured log paths and checksums
```

Do not overwrite a failed or superseded run. A retry is a new run linked to its parent when the
project adds retry orchestration.

## Evaluate And Promote Evidence

1. Normalize outputs through the project's evaluation interface.
2. Keep raw logs and large artifacts under `runs/` or external artifact storage.
3. Record exclusions and failures rather than deleting inconvenient evidence.
4. Inspect the local manifest and associated artifacts.
5. Promote only a reviewed compact manifest:

```bash
uv run python tools/research.py promote <run-id>
```

Promoted manifests live under `evidence/manifests/` and are immutable. Reports cite promoted run
IDs and evidence hashes; they do not copy terminal values as untraceable facts.

## Handoff

Return the question, spec path, run IDs, evaluation result, anomalies, artifact locations,
reproduction command, promoted evidence path when applicable, and whether the evidence supports,
contradicts, or leaves the question unresolved.
