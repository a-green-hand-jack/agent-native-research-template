# Project Guide

This guide describes stable procedures. Keep task-specific notes in `.agents/runtime/` and
project facts in `.agents/memory/`.

Use [Repository Evolution](docs/governance/EVOLUTION.md) when deciding whether a new project
capability should remain an inline singleton or become an explicit directory, environment,
registry, or evidence layer.

## Choose The Unit

Classify a task before choosing files:

- Use the **functional unit** for project capabilities, substrate, configs, environments, infra,
  tests, evaluations, experiments, reports, and publications.
- Use the **governance unit** only for ownership, invariants, stable procedures, agent routing,
  coordination state, mandatory checks, or repository maintenance.
- Use a **mixed change** only when functional work genuinely changes one of those governance
  subjects. Keep the functional and governance portions separately reviewable.

`REPO_UNITS.yaml` is authoritative for path ownership. New paths are functional by default.
Before adding governance, name the repeated cost or failure it removes and the check that will
show whether it works.

## Initialize From The Template

The main agent should:

1. Replace the generic package and metadata with the real project name.
2. Write the first concrete contribution and substrate relationship in `README.md`.
3. Replace the project-specific section of `CONTRACT.md`.
4. Update `ANATOMY.md` to describe the actual first vertical slice.
5. Replace the bootstrap config, environment, infra profile, evaluation, and experiment spec.
6. Run `make setup` and `make verify`.
7. Commit the initialized baseline before parallel development.

Do not pre-create empty packages, baseline directories, publication systems, or registries.

## Work On A Task

1. Start from an accepted commit.
2. Write a bounded task brief: goal, non-goals, write scope, acceptance, and verification.
3. Declare the primary unit and any intentional cross-unit impact.
4. Inspect existing code and nearby tests before adding files.
5. Implement the smallest coherent change.
6. Run focused validation, then `make verify` when the scope warrants it.
7. Remove replaced paths and temporary output.
8. Commit implementation and evidence together.

## Coordinate Parallel Work

Use one worktree per independent write task. Keep read-only exploration in the main agent when
delegation would add more context than it saves.

The main agent owns:

- branch and worktree allocation;
- write-scope separation;
- worker task packets;
- integration order;
- final verification;
- governance and memory promotion.

Workers return:

```text
status
base and head commit
changed files
validation evidence
remaining risks
knowledge candidates
integration notes
```

Use `.agents/skills/parallel-worktree/SKILL.md` for the concrete procedure.

## Run Experiments

Treat experiment intent, execution fact, and interpretation as different artifacts:

```text
experiment spec -> run manifest -> evaluation -> report
```

Commit before an expensive run. Store raw outputs under `runs/` or external artifact storage.
Reports cite run IDs and record inclusion or exclusion decisions. Use
`.agents/skills/run-experiment/SKILL.md` for the full procedure.

## Manage Environments And Infra

- Keep the lightweight control tooling in the main project environment.
- Give incompatible workloads and baselines separate environment descriptions.
- Put committed, non-secret executor and storage descriptions under `infra/`.
- Put private values in ignored local overrides or external secret storage.
- Use logical storage and executor names in experiment specs.
- Keep large execution assets on the appropriate execution plane.

## Add A Baseline

Do not merge incompatible baseline dependencies into the main environment. Pin the upstream
source, preserve required patches, add a project adapter, and prove the integration with a smoke
test. Use `.agents/skills/add-baseline/SKILL.md`.

## Maintain The Repository

Workers clean only within their touched scope. The main agent schedules a bounded maintenance
worktree when repeated duplication, conflicts, stale docs, ambiguous configs, or accumulated
runtime material make continued delivery more expensive.

Prefer deletion over archive directories because Git already preserves history. Use
`.agents/skills/repo-maintenance/SKILL.md`.

## Command Surface

```bash
make setup       # install the lightweight project environment and hooks
make check       # formatting, lint, and repository validation
make test        # test suite
make smoke       # bounded end-to-end smoke check
make verify      # check plus tests
```

Add new public commands only when they replace a repeated manual procedure.
