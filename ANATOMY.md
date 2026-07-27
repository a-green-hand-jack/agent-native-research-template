# Repository Anatomy

## System Shape

```text
Human
  <-> Main Agent
        -> isolated worker worktrees
        -> integration and verification

Constitution: AGENTS + ANATOMY + CONTRACT + GUIDE
                         |
Project:       code + tests + evals + experiments
                         |
Execution:     environments + infra + baselines
                         |
Evidence:      run manifests + reports + paper outputs
```

The constitutional layer guides the project but is not the project. Code, evaluations, and
validated outcomes remain the primary product.

## Static Surfaces

| Path | Responsibility |
|---|---|
| `src/` | Project implementation and contribution code |
| `tests/` | Local correctness and regression protection |
| `evals/` | Executable scientific or product evaluation protocols |
| `configs/` | Versioned human-authored configuration |
| `environments/` | Reproducible dependency-set descriptions |
| `infra/` | Logical executor, storage, resource, and environment-variable descriptions |
| `experiments/specs/` | Intended experiment definitions |
| `experiments/reports/` | Curated reports that reference immutable runs |
| `.agents/memory/` | Accepted project facts and their index |
| `.agents/skills/` | Repeatable project procedures |

Create `baselines/`, `packages/`, or `paper/` only when the project has a real baseline,
independent component boundary, or publication workflow.

## Dynamic Surfaces

| Path | Responsibility |
|---|---|
| `.agents/runtime/` | Per-worktree pads, task state, handoffs, and candidates |
| `runs/` | Local run outputs and immutable manifests |
| external artifact storage | Large datasets, checkpoints, logs, and generated artifacts |

Dynamic surfaces are not project truth. Accepted facts move into code, tests, evaluations,
reports, decisions, or project memory through an explicit review.

## Dependency Direction

- Product code must not depend on `.agents/`, reports, or runtime state.
- Tests and evaluations may depend on product interfaces.
- Experiment specs reference code, config, environment, infra, data, and evaluation by stable
  path or ID.
- Infra resolves logical names to runtime locations; project configs must not scatter private
  absolute paths.
- Reports reference run IDs and evidence; they do not rewrite run facts.

## Growth Rules

- A second incompatible dependency set earns a second environment.
- A second execution backend earns an executor registry.
- A second external implementation earns a baseline adapter boundary.
- Repeated full-config copying earns base-plus-delta configuration.
- A stable independent interface, test boundary, and lifecycle earn a package.
- Repeated procedure earns a skill.
- Repeated failure earns an executable check.

