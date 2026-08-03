---
name: run-experiment
description: Execute, verify, replay, and promote a reproducible project experiment. Use for training, inference, rollouts, benchmark runs, sweeps, ablations, or any result that must be compared or cited later.
---

# Run Experiment

Separate experiment intent, effective configuration, observed execution facts, verification, and
interpretation.

## Prepare

1. Identify the question and evaluation protocol that can answer it.
2. Start from a versioned experiment spec.
3. Resolve the contribution, parsed config, environment, executor profile, evaluation, and generic
   input identities. Use repository paths, external URIs, or non-secret opaque logical identifiers.
4. Declare seed policy, resource budget, stopping rule, inclusion criteria, metrics, artifacts, and
   phase commands before observing results.
5. Give every phase exactly one command source. Use explicit `phases` for multi-stage work. A
   top-level `command` is only a legacy one-phase shorthand and cannot coexist with `phases`.
6. Keep evaluation definitions command-free; they own extraction and interpretation only.
7. Commit a checkpoint before an expensive run whenever practical.
8. Validate the definition graph, deterministic plan, asset bindings, and local-runner controls:

```bash
uv run researchctl experiment validate experiments/specs/<name>.yaml
uv run researchctl experiment plan experiments/specs/<name>.yaml
uv run researchctl experiment preflight experiments/specs/<name>.yaml
make smoke
```

The plan embeds the complete parsed config and its SHA-256. Changing config content or a phase
command changes plan identity; changing only YAML key order does not.

Executor profiles own the process-environment policy. Explicit non-secret values are declared under
`environment`; host variables must be individually allowed under `inherit_environment`. Only
`${PROJECT_ROOT}` may be expanded in explicit values. The runner never copies the complete host
environment. It records inherited variable names and value hashes, plus the reserved
`RESEARCH_SEED` binding, in run evidence.

The built-in runner executes exactly one fixed seed, exports it as `RESEARCH_SEED`, enforces a
positive wall-time limit, and accepts only `after_runs: 1`. Use an external scheduler for sweeps,
random or range seeds, cost accounting, or metric-driven stopping; each attempt must still produce
a separate run manifest.

Repository path inputs are hashed before execution. URI and opaque identities are recorded without
network access; opaque values become durable manifest data and must not contain secrets. See
`docs/INPUT_IDENTITY.md` for the portable input contract.

## Execute

Use the installed evidence-aware control surface:

```bash
uv run researchctl experiment run experiments/specs/<name>.yaml
```

For a retry or deliberately derived execution, name the parent run:

```bash
uv run researchctl experiment run experiments/specs/<name>.yaml --parent <run-id>
uv run researchctl experiment retry-phase <run-id> --phase <phase-id>
```

Review the deterministic plan and its SHA-256, then review preflight's resolved logical asset
bindings. Use `--phase generation` or `--phase evaluation` to prove oracle isolation. A multi-cell
plan requires an external scheduler; the built-in runner executes exactly one cell.

Each phase writes `runs/<run-id>/phases/<phase-id>/result.json` plus logs and immutable snapshots. A
failed dependency produces explicit `incomplete` downstream results.

Each execution receives a unique run ID and writes an ignored local manifest under
`runs/<run-id>/manifest.json`. The manifest records Git state, the resolved spec, effective config,
versioned environment and executor definitions, explicit environment evidence, resolved input and
asset identities, the selected seed, termination reason, contextual metrics, timestamps, status,
and optional parent identity. Declared artifacts are copied into
`runs/<run-id>/artifacts/`; the manifest records the snapshot checksum and original source path.

## Verify And Replay

Verify every recorded artifact before using or promoting a result:

```bash
uv run researchctl experiment status <run-id>
uv run researchctl experiment results <run-id>
uv run researchctl experiment verify-run <run-id>
```

Replay checks the recorded spec, effective config, environment definition and lockfile, executor,
evaluation, declared environment policy, and repository path input hashes against the current
checkout before executing:

```bash
uv run researchctl experiment replay <run-id>
```

Do not use `--allow-drift` unless the divergence is intentional and will be explained in the new
run's report. A replay is a new run linked to its parent; it never overwrites the original. URI and
opaque inputs are not fetched during replay; their recorded identity remains the declared source of
truth.

## Promote Evidence

Keep raw logs and large artifacts under `runs/` or external storage. After reviewing the run,
promote an immutable evidence envelope with an explicit interpretation:

```bash
uv run researchctl experiment promote <run-id> \
  --decision accepted \
  --note "Evidence supports the stated claim."
```

The decision is `accepted`, `rejected`, or `inconclusive`. Promoted evidence records the source
manifest checksum, review decision, review note, and complete run manifest.

## Archive And Retirement

Before retiring a run, worktree, branch, provider, server, or volume, create and verify an archive
inventory. Local copies are re-read; external copies require verifier evidence. Non-reconstructable
assets need two independent verified fault domains.

```bash
uv run researchctl archive create <run-id> \
  --copy /absolute/archive/root-a::fault-domain-a \
  --copy /absolute/archive/root-b::fault-domain-b
uv run researchctl archive verify archives/local/<run-id>.json
uv run researchctl archive retirement-preflight \
  archives/local/<run-id>.json --target-kind run --target <run-id>
```

These commands do not delete anything. Review the decision and obtain separate explicit
authorization before any stop or deletion action.

## Handoff

Return:

```text
question and spec path
plan SHA-256 and effective configuration
run ID and optional parent run ID
resolved input and asset identities
declared environment policy and inherited-value hashes
selected seed and termination reason
validation and artifact-verification evidence
metrics and evaluation errors
snapshot and source artifact locations with checksums
reproduction or replay command
promotion path and review decision, when applicable
archive manifest, verified fault domains, and retirement blockers, when applicable
whether the evidence supports, contradicts, or leaves the question unresolved
```

Do not delete failed runs, edit promoted evidence, or copy terminal values into reports without a
traceable run ID.
