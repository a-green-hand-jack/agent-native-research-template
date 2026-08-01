# Agent-Native Research Template

A project-first GitHub template for ML, DL, RL, agents, benchmarks, environments, and adjacent
research projects. The functional project remains conventional and runnable on its own. Optional
agent governance lives in a non-runtime `.agents/` sidecar.

## Five-Minute Research Loop

Create a repository from this template, then run:

```bash
make setup
make verify
make research-run
```

`make verify` checks code, tests, and every experiment specification. `make research-run` validates
and executes the bootstrap experiment, then writes an immutable local manifest under
`runs/<run-id>/manifest.json`.

Inspect the run before promoting its compact manifest into durable evidence:

```bash
uv run python tools/evidence.py promote <run-id> --decision accepted
```

Raw logs and large artifacts remain ignored under `runs/` or in external storage. Reviewed compact
manifests live under `evidence/manifests/` and can be cited by reports.

Git hooks are optional and installed separately:

```bash
make hooks
```

## Initialize A Real Project

Ask an agent to replace the bootstrap with one complete runnable vertical slice. A useful first
instruction is:

> Initialize this template for the project described below. Keep the functional project usable
> without `.agents/`, replace generic bootstrap content with one complete runnable slice, and
> verify the project and governance sidecar independently.

The initialization should replace:

1. the generic package name, implementation, and contribution entry;
2. the bootstrap config, environment, evaluation, and experiment specification;
3. the project-specific section of `.agents/governance/CONTRACT.md`;
4. the anatomy description where the real project introduces new components or dependencies.

Run `make verify`, `make research-run`, and the governance doctor before committing the initialized
baseline.

## Executable Research Contract

An experiment specification resolves a complete, reviewable execution boundary:

```text
question + contribution + config + environment + executor + evaluation + command
                         |
                         v
                    local run
                         |
                         v
               immutable run manifest
                         |
                         v
              reviewed evidence manifest
```

The public interface is:

```bash
uv run python tools/research.py validate
uv run python tools/research.py validate experiments/specs/<name>.yaml
uv run python tools/evidence.py run experiments/specs/<name>.yaml
uv run python tools/evidence.py run experiments/specs/<name>.yaml --parent <run-id>
uv run python tools/evidence.py replay <run-id>
uv run python tools/evidence.py verify-run <run-id>
uv run python tools/evidence.py promote <run-id> --decision accepted
```

Validation rejects missing research controls, unknown contribution IDs, missing config paths,
unknown environment or evaluation IDs, ambiguous executors, mismatched evaluation commands, and
missing environment locks.

A run manifest records the resolved spec, Git revision and dirty-state hash, environment lock,
executor and evaluation definitions, typed metrics, declared artifacts, timestamps, return status,
and checksums. Retries and replays receive new run IDs linked through `parent_run_id`; existing runs
and evidence are never overwritten.

Before replay, the runner compares the recorded hashes for the spec, config, environment, lockfile,
executor, and evaluation against the current checkout. Drift stops the replay unless the operator
explicitly passes `--allow-drift`. `verify-run` separately checks every recorded artifact checksum.

Evidence promotion verifies the run first, then stores an immutable envelope containing the source
manifest hash and a review decision of `accepted`, `rejected`, or `inconclusive`.

## Versioned Research Definitions

Research definitions use `schema_version: 1` and stable lowercase IDs. The repository ships
portable JSON Schema documents under `schemas/`, while `tools/research.py` and
`tools/evidence.py` perform the stronger cross-file checks that JSON Schema alone cannot express.

```text
experiments/specs/**/*.yaml  experiment intent and research controls
environments/**/*.yaml       dependency-set identity and lockfile
evals/**/*.yaml              executable protocol and typed metric sources
infra/profiles/**/*.yaml      logical executor and capabilities
schemas/*.schema.json         portable structural contracts
```

Validation discovers definitions recursively and rejects duplicate IDs, unknown references,
unversioned definitions, invalid metric directions or sources, missing locks, and commands that
do not match their evaluation protocol. This allows projects to organize studies into nested
directories without weakening global identity and traceability.

## Project First

The repository has an intentionally asymmetric structure:

```text
repo/
├── project files and conventional tool paths    functional by default
├── AGENTS.md                                    thin discovery adapter
└── .agents/                                     optional governance sidecar
```

The functional project contains implementation, tests, evaluations, environments, infrastructure,
experiments, evidence, reports, and publications. The sidecar contains agent contracts,
procedures, skills, reviewed memory, runtime handoffs, maps, and its own structural doctor.

Governance may read project state and invoke public project commands. The project must not import,
source, configure, or otherwise require governance. CI proves this behavior by deleting `.agents/`
and `AGENTS.md`, recreating the project environment, and rerunning `make verify`.

Project verification and governance validation remain independent:

```bash
make verify
uv run --no-project --with pyyaml python .agents/governance/tools/repo_check.py
```

`.agents/governance/REPO_UNITS.yaml` is the ownership source of truth. Only `.agents/` and the root
discovery adapter `AGENTS.md` are governance-owned; every new path is functional by default.

## Agent Runtime Compatibility

The repository does not require a specific orchestration product. Codex, OMX, native subagents,
direct agent sessions, or another runtime may execute the same repository roles.

```text
agent runtime -> reads AGENTS.md -> operates governance + functional project
```

The runtime is outside the two tracked repository units. Template-owned handoffs use ignored
`.agents/runtime/`; tool-owned state such as `.omx/` stays in its own ignored directory. Generated
runtime instructions, model tables, hook registries, and session state are not durable project
knowledge.

A `worktree agent` names the role attached to a Git worktree. It may be implemented by a direct
session, a native child agent, or a runtime-specific team worker without changing the repository
contract.

## Human And Agent Routing

The default topology keeps the human in one conversation:

```text
Human <-> Main Agent <-> Agent @ worktree
```

For lower-latency steering or more conversational parallelism, the human can talk directly to an
agent in a selected worktree:

```text
Human <-> Agent @ worktree
```

Control mode belongs to each worktree. Mediated and direct worktrees may run concurrently, and a
worktree can switch modes after a coherent checkpoint. Git state is durable; an ignored
`.agents/runtime/HANDOFF.md` carries only context that Git cannot express.

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

Open the [Repository Anatomy Map](.agents/governance/docs/repository-map.html) to inspect the
physical boundary, non-invasive interaction ports, dynamic surfaces, and switchable worktree
control modes.

## Project Commands

```bash
make setup
make hooks
make check
make test
make smoke
make research-validate
make research-run
make verify
```

## Growth

Start with one complete vertical slice. Add a new environment, baseline, executor, component,
study, or publication layer only when a real second instance or independent lifecycle appears.
Add sidecar structure only when a repeated agent cost cannot be removed through clearer project
interfaces, tests, executable validation, or documentation.
