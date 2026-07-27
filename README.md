# Agent-Native Research Template

A thin GitHub template for research and software projects where one human directs a main
agent, the main agent coordinates isolated workers, and the repository remains the source of
truth.

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

The always-present governance layer consists of:

- `AGENTS.md`: agent entry point and routing;
- `ANATOMY.md`: current system map;
- `CONTRACT.md`: project invariants;
- `GUIDE.md`: stable operating procedures.

Project code, tests, evaluations, experiments, and results remain the center of the repository.

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
