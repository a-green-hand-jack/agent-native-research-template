# Project Contract

This file defines durable repository invariants. During template initialization, add the
project-specific behavioral, scientific, and interface contracts below these shared invariants.

## Project-First Invariants

- Governance must reduce expected project cost. Do not add governance solely for completeness.
- Each durable fact, command, configuration value, and behavioral promise has one canonical
  source.
- The core contribution remains locatable even when its supporting substrate is large.
- Generated output never silently becomes source input.

## Execution Invariants

- A runnable experiment resolves its code revision, config, environment, data, executor, and
  evaluation protocol.
- Expensive runs begin from a committed checkpoint whenever practical.
- A run records its Git revision, dirty patch state, resolved config, environment identity, data
  identity, seed, executor, hardware, timestamps, metrics, and artifact references.
- Run facts are immutable. Retries create new runs linked to their parent.
- Accepted reports cite run IDs; paper values are generated from locked evidence rather than
  copied from terminal output.

## Parallel-Work Invariants

- One worktree has one bounded intent.
- Parallel writers use separate worktrees and non-overlapping ownership scopes.
- Workers do not merge directly into the canonical branch.
- The main agent integrates, validates, and reports the combined result.
- Runtime pads and worker handoffs are local coordination state, not durable project knowledge.

## Environment And Infra Invariants

- Incompatible baselines or workloads use isolated environments.
- Project configuration refers to logical executor and storage names rather than private
  machine-specific paths.
- Secrets and private infrastructure values remain in ignored overrides, encrypted files, or a
  secret manager.
- Large datasets, checkpoints, caches, and raw logs are not committed to Git.

## Governance Invariants

- `ANATOMY.md` changes when component topology or dependency direction changes.
- `CONTRACT.md` changes when promised behavior or result validity changes.
- `GUIDE.md` changes when a stable operating procedure changes.
- `AGENTS.md` changes when agent routing, authority, or mandatory verification changes.
- A governance artifact needs a reader, a trigger, an update rule, and a retirement path.

## Project-Specific Contract

Replace this section during project initialization with:

- externally observable behavior;
- scientific claims currently under test;
- input and output schemas;
- numerical or statistical validity requirements;
- compatibility constraints;
- explicit non-goals.

## Completion Contract

A change is acceptable only when its relevant implementation, validation evidence, and durable
documentation agree. Passing tests cannot excuse a violated contract, and prose cannot excuse a
failing executable check.
