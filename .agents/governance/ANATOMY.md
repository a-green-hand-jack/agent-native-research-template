# Repository Anatomy

## System Shape

```text
agent runtime                             outside tracked repo units
├── Codex / OMX / another execution surface
├── solo session / native child / runtime team worker
└── optional ignored tool state, e.g. .omx/
              │ reads guidance and operates declared interfaces
              ▼
repo/
├── functional project                    default owner
│   ├── src + tests
│   ├── configs + environments + infra
│   ├── evals + experiments + evidence
│   └── README + CONTRIBUTIONS + Makefile
├── template/                             functional, template-only lifecycle
│   └── initializer + projection regression checks
│
├── AGENTS.md                             thin discovery adapter
└── .agents/                              governance sidecar
    ├── governance/                       contracts, map, guide, doctor
    ├── skills/                           repeatable agent procedures
    ├── memory/                           reviewed durable project facts
    └── runtime/                          ignored pads, control, handoffs
```

The repository has a primary functional project and an optional governance sidecar. `template/`
is functional source-template maintenance code, not a third ownership unit, and is removed from
the initialized downstream projection. The units share Git history but not runtime. An agent
runtime operates them from outside that two-unit model. The physical boundary is intentionally
asymmetric:

- `.agents/` contains governance.
- `AGENTS.md` is the only root governance file because agent tools discover it there.
- Every other path is functional by default.
- Ignored tool state such as `.omx/` or the project-local `.uv-cache/` may appear in the working
  directory but is not a third tracked repository unit.

The interactive **[Repository Anatomy Map](docs/repository-map.html)** shows the physical
boundary, allowed interactions, and worktree control modes. [Repository Evolution](docs/EVOLUTION.md)
describes when functional project structure should grow.

The interactive **[Worktree Control Model](docs/worktree-control.html)** separately explains
human, main-agent, worktree, and worktree-agent identity, authority, persistence, and control
transfer.

Ownership, lifecycle, and readership are independent classifications. A machine-first schema can
be downstream-required functional code; an agent-invoked command can still be project-owned; and
template-only code remains functional even though it is absent downstream. The canonical lifecycle
classes are `downstream_required`, `downstream_optional`, `template_only`, and `runtime_only` in
`REPO_UNITS.yaml`.

## Non-Invasive Interaction

Governance interacts through observable project interfaces:

```text
governance sidecar
    ├── reads Git, code, config, tests, manifests, and reports
    ├── invokes public setup, test, evaluation, and experiment commands
    └── writes project paths only when the active task authorizes that change

functional project
    └── never imports, reads, sources, or requires .agents/
```

The project `Makefile`, package environment, code, tests, configs, experiments, and reports do
not call governance. CI may run project verification and governance validation as independent
jobs. Pre-commit hooks validate project files without requiring the sidecar.

## Governance Sidecar

| Path | Responsibility |
|---|---|
| `AGENTS.md` | Minimal agent-tool discovery and boundary summary |
| `.agents/governance/ANATOMY.md` | Current topology, ownership, and dependency direction |
| `.agents/governance/CONTRACT.md` | Durable project and sidecar invariants |
| `.agents/governance/GUIDE.md` | Stable operating and control-transfer procedures |
| `.agents/governance/REPO_UNITS.yaml` | Machine-readable ownership and adapter declaration |
| `.agents/governance/tools/repo_check.py` | Sidecar structure and non-invasion validation |
| `.agents/governance/docs/` | Governance rationale, maps, and repository evolution |
| `.agents/memory/` | Reviewed facts that reduce future orientation cost |
| `.agents/skills/` | Repeatable project procedures |
| `.agents/runtime/` | Ignored per-worktree pads, control notes, and handoffs |

## Agent Runtime

The agent runtime supplies execution capabilities rather than repository truth:

| Surface | Responsibility |
|---|---|
| direct or solo session | Execute a bounded task in the current checkout |
| native child agent | Execute an independent delegated task supported by the current tool |
| runtime team worker | Execute a role created by a specific orchestration runtime |
| runtime hooks and routing | Select or constrain execution behavior for the current session |
| tool state such as `.omx/` | Ignored runtime-owned state with its own lifecycle |

`main agent` and `worktree agent` are repository roles. They do not require a particular agent
type or orchestration product. A runtime may implement those roles differently while preserving
the same worktree control and integration invariants.

Runtime-generated model tables, hook registries, keyword routing, and session state stay owned by
that runtime. They enter repository governance only if the project explicitly adopts a stable,
portable contract rather than copying generated output.

## Functional Project

| Path | Responsibility |
|---|---|
| `README.md` | Project identity, purpose, and primary entry point |
| `CONTRIBUTIONS.md` | Core contributions linked to code, parameters, and evidence |
| `src/` | Project implementation and contribution code |
| `tests/` | Local correctness and regression protection |
| `evals/` | Executable scientific or product evaluation protocols |
| `configs/` | Versioned human-authored configuration |
| `environments/` | Reproducible dependency-set descriptions |
| `infra/` | Logical executor, storage, resource, and environment descriptions |
| `experiments/specs/` | Intended experiment definitions |
| `experiments/reports/` | Curated reports that reference immutable runs |
| `Makefile` | Public project setup, test, smoke, and verification interface |
| `PROJECT.yaml` + `tools/project.py` | Retained project identity, provenance, and consistency checks |
| `tools/control_cli.py` + `tools/workload.py` + `src/<package>/workloads.py` | Stable project workload routing without exposing internal implementation entry points |
| `tools/source_guard.py` | Per-phase detection of protected project file creation, removal, or modification |
| `tools/template_compat.py` + `tools/template_lifecycle.py` | Registered downstream migrations and deterministic reviewed update plans |
| optional `RELEASE.yaml` + `tools/release.py` | Immutable draft artifacts, artifact-only verification, and explicit approval records |
| optional `external-facts/` | Official-source observations with computed freshness and content identity |

## Source Template Maintenance

| Path | Responsibility |
|---|---|
| `template/initialize_project.py` | Replace bootstrap identity and remove template-only surfaces |
| `template/tests/` | Characterize initializer and downstream projection behavior |
| `template/verify_downstream.py` | Exercise a real initialized copy before and after sidecar removal |

Initialized repositories do not retain `template/`, `template-test`, or `template-e2e`. Their
functional checks use the installed project CLI and never import template-maintainer code.

Create `baselines/`, `packages/`, or `paper/` only when the project has a real baseline,
independent component boundary, or publication workflow.

## Worktree Control Plane

Interaction mode belongs to a worktree, not to the repository:

```text
mediated: Human <-> Main Agent <-> Agent @ worktree A
direct:   Human <----------------> Agent @ worktree B

Human or Main Agent -> create/adopt either worktree
worktree A or B      -> checkpoint -> switch mode
```

Both modes may operate concurrently. A main agent may coordinate some worktrees while the human
directly drives others. Git provides isolation and history; ignored runtime handoffs preserve
only the context required to transfer control.

Creation and control are independent:

- a human-created worktree can be adopted by the main agent;
- a main-agent-created worktree can be taken over directly by the human;
- the active controller has exclusive write authority until handoff;
- the integration owner is explicit and may remain the main agent across control changes.

## Dynamic Surfaces

| Unit | Path | Responsibility |
|---|---|---|
| governance | `.agents/runtime/` | Per-worktree pads, control state, and handoffs |
| external runtime | `.omx/` or equivalent ignored path | Tool-owned execution and workflow state |
| functional tool | `.uv-cache/` | Ignored project-local dependency cache for sandbox-safe `uv` commands |
| functional | `runs/` | Local run outputs and immutable manifests |
| functional | external artifact storage | Large datasets, checkpoints, logs, and generated artifacts |

Dynamic surfaces are not automatically project truth. Accepted facts move into code, tests,
evaluations, reports, decisions, or reviewed memory through explicit validation.

## Growth Rules

- Functional growth is the default; governance growth must stay inside the sidecar and remove a
  repeated coordination, correctness, recovery, or maintenance cost.
- A second incompatible dependency set earns a second environment.
- A second execution backend earns an executor registry.
- A second external implementation earns a baseline adapter boundary.
- Repeated full-config copying earns base-plus-delta configuration.
