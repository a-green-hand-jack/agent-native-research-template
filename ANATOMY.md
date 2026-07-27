# Repository Anatomy

## System Shape

```text
Human
  <-> Main Agent
        -> isolated worker worktrees
        -> integration and verification

Governance unit
  AGENTS + ANATOMY + CONTRACT + GUIDE
  skills + memory + checks + coordination
                       |
                       | directs, inspects, invokes, validates
                       v
Functional unit
  contribution + substrate + tests + evaluations
  environments + infra + experiments + reports
```

The repository has exactly two primary units. The **functional unit** is the project: it builds
the capability and produces evidence. The **governance unit** helps humans and agents change that
project safely and cheaply. Governance is allowed to observe and invoke functional interfaces;
functional behavior must not require governance files or agent runtime state.

`REPO_UNITS.yaml` is the machine-readable ownership map. Paths not explicitly assigned to
governance belong to the functional unit by default. This project-first default prevents a new
feature, experiment, or document from becoming governance merely because an agent created it.

The interactive **[Repository Anatomy Map](docs/governance/repository-map.html)** labels the
concrete paths and can focus the view on either unit or on dynamic surfaces.

The complete coordination and maintenance model is shown in
[the governance diagram](docs/governance/images/agent-native-project-governance.png). The staged
visual model in [Repository Evolution](docs/governance/EVOLUTION.md) explains how this anatomy
grows without changing its underlying concepts.

## Governance Unit

Governance paths sit where their consumers expect them rather than under one artificial wrapper.
Root contracts are immediately discoverable, `.agents/` is agent-local state, `.github/` is
hosting automation, and `tools/repo_check.py` is the executable structural check.

| Path | Responsibility |
|---|---|
| `AGENTS.md` | Agent entry point, authority, routing, and completion rules |
| `ANATOMY.md` | Current ownership, topology, and dependency direction |
| `CONTRACT.md` | Durable project and governance invariants |
| `GUIDE.md` | Stable operating procedures |
| `REPO_UNITS.yaml` | Machine-readable unit ownership and required paths |
| `.agents/memory/` | Accepted project facts and their index |
| `.agents/skills/` | Repeatable project procedures |
| `.agents/runtime/` | Ignored task pads, handoffs, and candidates |
| `.github/` | Collaboration and continuous verification policy |
| `docs/governance/` | Governance model and repository-evolution references |
| `tools/repo_check.py` | Fast structural and repository-policy validation |

## Functional Unit

The functional unit keeps ecosystem-native paths. Do not add a `project/` wrapper merely to make
the two-unit model look symmetrical.

| Path | Responsibility |
|---|---|
| `README.md` | Project identity, purpose, and primary entry point |
| `CONTRIBUTIONS.md` | Index from core contributions to code, parameters, and evidence |
| `src/` | Project implementation and contribution code |
| `tests/` | Local correctness and regression protection |
| `evals/` | Executable scientific or product evaluation protocols |
| `configs/` | Versioned human-authored configuration |
| `environments/` | Reproducible dependency-set descriptions |
| `infra/` | Logical executor, storage, resource, and environment-variable descriptions |
| `experiments/specs/` | Intended experiment definitions |
| `experiments/reports/` | Curated reports that reference immutable runs |

Create `baselines/`, `packages/`, or `paper/` only when the project has a real baseline,
independent component boundary, or publication workflow.

## Dynamic Surfaces

| Unit | Path | Responsibility |
|---|---|---|
| governance | `.agents/runtime/` | Per-worktree pads, task state, handoffs, and candidates |
| functional | `runs/` | Local run outputs and immutable manifests |
| functional | external artifact storage | Large datasets, checkpoints, logs, and generated artifacts |

Dynamic surfaces are not automatically project truth. Accepted facts move into code, tests,
evaluations, reports, decisions, or project memory through explicit review. Project memory is
governance-owned because it exists to orient future work; the evidence supporting a fact remains
functional.

## Dependency Direction

- Functional code, experiments, and reports must not depend on `.agents/`, governance documents,
  or runtime coordination state.
- Governance may inspect and invoke functional commands, tests, evaluations, and manifests.
- Tests and evaluations may depend on functional interfaces.
- Experiment specs reference code, config, environment, infra, data, and evaluation by stable
  path or ID.
- Infra resolves logical names to runtime locations; project configs must not scatter private
  absolute paths.
- Reports reference run IDs and evidence; they do not rewrite run facts.

## Change Routing

| Change | Primary unit |
|---|---|
| Add a model, environment, benchmark, baseline, config, report, or test | functional |
| Change an invariant, ownership boundary, stable procedure, or mandatory check | governance |
| Record temporary plans, handoffs, or candidate knowledge | governance runtime |
| Change a feature and the contract it intentionally changes | mixed, with each part explicit |

## Growth Rules

- Functional growth is the default; governance growth requires a repeated coordination,
  correctness, recovery, or maintenance cost.
- A second incompatible dependency set earns a second environment.
- A second execution backend earns an executor registry.
- A second external implementation earns a baseline adapter boundary.
- Repeated full-config copying earns base-plus-delta configuration.
- A stable independent interface, test boundary, and lifecycle earn a package.
- Repeated procedure earns a skill.
- Repeated failure earns an executable check.
- A governance mechanism that no longer reduces project cost should be simplified or retired.
