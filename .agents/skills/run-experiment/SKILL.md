---
name: run-experiment
description: Execute, verify, replay, and promote a reproducible project experiment. Use for training, inference, rollouts, benchmark runs, sweeps, ablations, or any result that must be compared or cited later.
---

# Run Experiment

Separate experiment intent, observed execution facts, verification, and interpretation.

## Prepare

1. Identify the question and evaluation that can answer it.
2. Start from a versioned experiment spec.
3. Resolve the contribution, config, environment, executor, evaluation, and generic input
   identities. Use repository paths, external URIs, or non-secret opaque logical identifiers.
4. Declare seed policy, resource budget, stopping rule, inclusion criteria, metrics, and artifacts
   before observing results.
5. Commit a checkpoint before an expensive run whenever practical.
6. Validate both the definition graph and the built-in runner's supported execution controls:

```bash
uv run python tools/research.py validate experiments/specs/<name>.yaml
uv run python tools/evidence.py validate experiments/specs/<name>.yaml
uv run python tools/evidence.py plan experiments/specs/<name>.yaml
uv run python tools/evidence.py preflight experiments/specs/<name>.yaml
make smoke
```

The built-in runner executes exactly one fixed seed, exports it as `RESEARCH_SEED`, enforces a
positive wall-time limit, and accepts only `after_runs: 1`. Use an external scheduler for sweeps,
random or range seeds, cost accounting, or metric-driven stopping; each attempt must still produce
a separate run manifest.

Repository path inputs are hashed before execution. URI and opaque identities are recorded without
network access; opaque values become durable manifest data and must not contain secrets. See
`docs/INPUT_IDENTITY.md` for the portable input contract.

## Execute

Use the evidence-aware runner:

```bash
uv run python tools/evidence.py run experiments/specs/<name>.yaml
```

For a retry or deliberately derived execution, name the parent run:

```bash
uv run python tools/evidence.py run experiments/specs/<name>.yaml --parent <run-id>
```

Review the deterministic plan and its SHA-256, then review preflight's resolved logical asset
bindings. Use `--phase generation` or `--phase evaluation` to prove oracle isolation.

A multi-cell plan requires an
external scheduler; the built-in runner executes exactly one cell.

Each execution receives a unique run ID and writes an ignored local manifest under
`runs/<run-id>/manifest.json`. The manifest records Git state, the resolved spec, versioned
configuration and environment hashes, resolved input identities, the selected seed, termination
reason, typed metrics, timestamps, status, and optional parent identity. Declared artifacts are
copied into `runs/<run-id>/artifacts/`; the manifest records the snapshot checksum and original
source path.

## Verify And Replay

Verify every recorded artifact before using or promoting a result:

```bash
uv run python tools/evidence.py verify-run <run-id>
```

Replay checks the recorded spec, config, environment, lockfile, executor, evaluation, and repository
path input hashes against the current checkout before executing:

```bash
uv run python tools/evidence.py replay <run-id>
```

Do not use `--allow-drift` unless the divergence is intentional and will be explained in the new
run's report. A replay is a new run linked to its parent; it never overwrites the original. URI and
opaque inputs are not fetched during replay; their recorded identity remains the declared source of
truth.

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
resolved input identities
selected seed and termination reason
validation and artifact-verification evidence
metrics and evaluation errors
snapshot and source artifact locations with checksums
reproduction or replay command
promotion path and review decision, when applicable
whether the evidence supports, contradicts, or leaves the question unresolved
```

Do not delete failed runs, edit promoted evidence, or copy terminal values into reports without a
traceable run ID.
