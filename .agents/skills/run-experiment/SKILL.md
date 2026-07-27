---
name: run-experiment
description: Execute and evaluate a reproducible project experiment. Use for training, inference, rollouts, benchmark runs, sweeps, ablations, or any result that must be compared or cited later.
---

# Run Experiment

Separate intended experiment design, observed execution facts, and later interpretation.

## Prepare

1. Identify the question and the evaluation that can answer it.
2. Start from a versioned experiment spec.
3. Resolve the contribution, substrate, config, environment, data, executor, and evaluation.
4. Commit a checkpoint before an expensive run whenever practical.
5. Declare seed policy, resource budget, stopping rule, and inclusion criteria before observing
   results.
6. Run the smallest smoke path before the formal execution.

## Execute

Create a unique run ID and immutable output location. Capture:

```text
run ID and parent run
base and head Git SHA
dirty diff hash or patch
resolved config
environment lock or image digest
data and baseline identity
seed
executor and hardware
command
timestamps and status
metrics and artifact checksums
evaluation version
```

Do not overwrite a failed or superseded run. A retry is a new run linked to its parent.

## Evaluate And Report

1. Normalize outputs through the project's evaluation interface.
2. Keep raw logs and large artifacts outside Git.
3. Record exclusions and failures rather than deleting inconvenient evidence.
4. Write a curated report only when a run family answers a meaningful question.
5. Reference run IDs and evidence hashes; do not copy terminal values as untraceable facts.

## Handoff

Return the question, spec path, run IDs, evaluation result, anomalies, artifact locations,
reproduction command, and whether the evidence supports, contradicts, or leaves the question
unresolved.

