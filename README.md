# Agent-Native Research Template

A thin GitHub template for research and software projects where one human directs a main
agent, the main agent coordinates isolated workers, and the repository remains the source of
truth.

Open the **[Repository Anatomy Map](docs/governance/repository-map.html)** to inspect the real
directory structure, switch between governance and functional ownership, and isolate dynamic
surfaces.

The template is designed for ML, DL, RL, agents, benchmarks, environments, and adjacent
research projects. It provides a small constitutional layer, a reproducible execution seed,
project-local skills, Git/worktree conventions, and lightweight validation. It deliberately
does not provide a workflow engine, a project database, or automatic memory promotion.

## Start A Project

1. Create a repository from this template.
2. Ask the main agent to initialize it for the concrete project.
3. Replace the bootstrap package, contribution, config, environment, evaluation, and experiment
   spec with the first real vertical slice.
4. Run `make setup` and `make verify`.
5. Commit before launching an expensive experiment.

A useful first instruction is:

> Initialize this template for the project described below. Preserve the repository contracts,
> replace generic bootstrap content with one complete runnable slice, and verify it end to end.

## Governing Idea

Governance serves delivery. The repository should reduce:

- agent orientation time;
- repeated human explanation;
- parallel write conflicts;
- time from a wrong change to a visible failure;
- effort required to reproduce an accepted result.

The repository makes one primary split:

- The **functional unit** is the actual project: implementation, substrate, tests, evaluations,
  environments, infra, experiments, reports, and publications.
- The **governance unit** reduces the cost of directing, changing, validating, integrating, and
  maintaining that project.

Functional ownership is the default. Governance paths are explicitly declared in
`REPO_UNITS.yaml`, so ordinary project growth does not silently expand the governance system.
Standard paths such as `src/`, `tests/`, and `infra/` stay where their tools expect them.

The always-present governance entry points are:

- `AGENTS.md`: agent entry point and routing;
- `ANATOMY.md`: current system map;
- `CONTRACT.md`: project invariants;
- `GUIDE.md`: stable operating procedures.

Project code, tests, evaluations, experiments, and results remain the center of the repository.

The [governance loop diagram](docs/governance/images/agent-native-project-governance.png) shows
how one human-facing main agent coordinates delivery and bounded maintenance across these units.

See [Repository Evolution](docs/governance/EVOLUTION.md) for the visual progression from one
complete vertical slice to parallel execution, experiment governance, and publication-ready
evidence.

## Commands

```bash
make setup
make check
make test
make smoke
make verify
```

## Growth

Start with one complete vertical slice. Add a new environment, baseline, executor, component,
study, or publication layer only when a real second instance or independent lifecycle appears.
Use the project-local skills under `.agents/skills/` for repeatable expansion procedures.
