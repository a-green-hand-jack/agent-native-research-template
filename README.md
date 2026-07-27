# Agent-Native Research Template

A project-first GitHub template for ML, DL, RL, agents, benchmarks, environments, and adjacent
research projects. The functional project remains conventional and runnable on its own. Optional
agent governance lives in a non-runtime `.agents/` sidecar.

Open the **[Repository Anatomy Map](.agents/governance/docs/repository-map.html)** to inspect the
physical boundary, non-invasive interaction ports, dynamic surfaces, and switchable worktree
control modes.

## Start A Project

1. Create a repository from this template.
2. Ask an agent to initialize it for the concrete project.
3. Replace the bootstrap package, contribution, config, environment, evaluation, and experiment
   spec with the first real vertical slice.
4. Run `make setup` and `make verify`.
5. Run `uv run python .agents/governance/tools/repo_check.py` independently.
6. Commit before launching parallel work or an expensive experiment.

A useful first instruction is:

> Initialize this template for the project described below. Keep the functional project usable
> without `.agents/`, replace generic bootstrap content with one complete runnable slice, and
> verify the project and governance sidecar independently.

## Project First

The repository has an intentionally asymmetric structure:

```text
repo/
├── project files and conventional tool paths    functional by default
├── AGENTS.md                                    thin discovery adapter
└── .agents/                                     optional governance sidecar
```

The functional project contains implementation, substrate, tests, evaluations, environments,
infra, experiments, evidence, reports, and publications. The sidecar contains agent contracts,
procedures, skills, memory, runtime handoffs, maps, and its own structural doctor.

Governance may read project state and invoke public project commands. The project must not
import, source, configure, or otherwise require governance. In particular:

- `make verify` verifies the project, not the sidecar;
- pre-commit hooks do not require `.agents/`;
- project environments and package metadata do not include governance dependencies;
- CI runs project verification and sidecar validation as independent jobs.

`.agents/governance/REPO_UNITS.yaml` is the ownership source of truth. Only `.agents/` and the
root discovery adapter `AGENTS.md` are governance-owned; every new path is functional by default.

## Agent Runtime Compatibility

The repository does not require a specific orchestration product. Codex, OMX, native subagents,
direct agent sessions, or another runtime may execute the same repository roles.

```text
agent runtime -> reads AGENTS.md -> operates governance + functional project
```

The runtime is outside the two tracked repository units. Template-owned handoffs use ignored
`.agents/runtime/`; tool-owned state such as `.omx/` stays in its own ignored directory. Generated
runtime instructions, model tables, hook registries, and session state are not durable project
knowledge and should not be copied into the sidecar.

A `worktree agent` names the role attached to a Git worktree. It may be implemented by a direct
session, a native child agent, or a runtime-specific team worker without changing the repository
contract.

## Human And Agent Routing

The default topology keeps the human in one conversation:

```text
Human <-> Main Agent <-> Agent @ worktree
```

It is a default, not a constraint. For lower-latency steering or more conversational parallelism,
the human can talk directly to an agent in any worktree:

```text
Human <-> Agent @ worktree
```

Control mode belongs to each worktree. Mediated and direct worktrees may run concurrently, and a
worktree can switch modes after a coherent checkpoint. A human-created worktree can be adopted by
the main agent; a main-agent-created worktree can be taken over directly by the human. Git state
is durable; an ignored `.agents/runtime/HANDOFF.md` carries only context that Git cannot express.

See the [Project Guide](.agents/governance/GUIDE.md) for worktree adoption, control transfer, and
integration procedures. The interactive
[Worktree Control Model](.agents/governance/docs/worktree-control.html) distinguishes human,
main-agent, Git worktree, and worktree-agent responsibilities.

## Governance Entry Points

- `AGENTS.md`: minimal discovery, boundary, and control-routing rules;
- `.agents/governance/ANATOMY.md`: physical topology and dependency direction;
- `.agents/governance/CONTRACT.md`: project and sidecar invariants;
- `.agents/governance/GUIDE.md`: stable operating and worktree-control procedures;
- `.agents/governance/REPO_UNITS.yaml`: machine-readable ownership;
- `.agents/skills/`: procedures loaded only when their trigger applies;
- `.agents/memory/`: reviewed durable facts;
- `.agents/runtime/`: ignored per-worktree pads and handoffs.

The [governance overview](.agents/governance/docs/images/agent-native-project-governance.png)
shows mediated and direct control modes, the sidecar boundary, and delivery. [Repository
Evolution](.agents/governance/docs/EVOLUTION.md) defines the semantic scope of every image and
shows how the functional project grows from one vertical slice to publication-ready evidence.

## Project Commands

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
Add sidecar structure only when a repeated agent cost cannot be removed through clearer project
interfaces, tests, or documentation.
