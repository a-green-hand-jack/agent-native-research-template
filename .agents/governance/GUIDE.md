# Project Guide

This guide describes stable agent procedures. Keep task-specific notes in `.agents/runtime/`
and reviewed project facts in `.agents/memory/`.

Use [Repository Evolution](docs/EVOLUTION.md) when deciding whether a project capability should
remain an inline singleton or become an explicit directory, environment, registry, or evidence
layer.

## Respect The Sidecar

Classify a task before choosing files:

- Use the **functional project** for capabilities, substrate, configs, environments, infra,
  tests, evaluations, experiments, reports, and publications.
- Use the **governance sidecar** for agent orientation, ownership, invariants, stable agent
  procedures, coordination state, and sidecar maintenance.
- Use a **mixed change** only when project work genuinely changes a durable boundary or contract.
  Keep the project and sidecar portions separately reviewable.

`.agents/governance/REPO_UNITS.yaml` is authoritative. New paths are functional by default.
Before adding governance, name the repeated cost it removes and how that reduction will be
observed.

Governance may inspect and invoke the project. Do not make project code, commands, hooks,
environments, or configs depend on `.agents/`.

## Select An Agent Runtime Surface

Repository roles are stable; execution capabilities vary by session. Before decomposing work,
inspect the tools actually available and choose the least expensive surface that preserves the
task boundary:

| Surface | Use when |
|---|---|
| solo or direct session | One agent can implement and verify the bounded change |
| native child agent | An independent read, implementation, research, or verification slice can run concurrently |
| Git worktree agent | A parallel writer needs an isolated checkout and branch |
| runtime team mode | The installed orchestration runtime provides durable staged coordination worth its overhead |

Do not invoke a runtime-specific command merely because its name appears in a generated
instruction overlay. The command must exist in the active environment and improve the current
task.

`main agent` and `worktree agent` are repository roles. The main agent is the human-facing
coordinating session. A worktree agent may be a direct session, native child agent, or runtime
team worker. Reserve the term `team worker` for an agent actually launched by a team runtime; do
not use it as a generic synonym for every delegated agent.

Repository guidance and runtime guidance have different lifecycles:

- `AGENTS.md` and `.agents/governance/` contain stable repository guidance.
- The active task or issue contains the requested outcome and acceptance criteria.
- Tool-generated overlays, model routing, keyword registries, and hooks belong to the runtime.
- `.agents/runtime/` contains template-owned temporary coordination context.
- `.omx/` or another tool-specific ignored path contains runtime-owned state.

Do not copy runtime-generated instructions into the sidecar. If a runtime must edit `AGENTS.md`,
its section must use paired tool-owned markers, remain idempotent, and be removable without
changing the stable adapter around it.

## Initialize From The Template

The initializing agent should:

1. Replace the generic package and metadata with the real project name.
2. Write the first concrete contribution and substrate relationship in `README.md`.
3. Replace the project-specific section of `.agents/governance/CONTRACT.md`.
4. Update `.agents/governance/ANATOMY.md` for the first real vertical slice.
5. Replace the bootstrap config, environment, infra profile, evaluation, and experiment spec.
6. Run `make setup`, `make verify`, and the governance doctor independently.
7. Commit the initialized baseline before parallel development.

Do not pre-create empty packages, baseline directories, publication systems, or registries.

## Work On A Task

1. Start from an accepted commit.
2. Write a bounded brief: goal, non-goals, write scope, acceptance, and verification.
3. Select the smallest available runtime surface and decide whether a worktree is needed.
4. Identify the worktree controller and intended integration owner.
5. Inspect existing code and nearby tests before adding files.
6. Implement the smallest coherent change.
7. Run focused validation, then `make verify` when the scope warrants it.
8. Run the governance doctor only when sidecar structure or its declared boundary changed.
9. Remove replaced paths and temporary output.
10. Commit implementation and evidence together.

## Choose A Control Mode

Control mode is per worktree and can differ across concurrent tasks.
Use the interactive [Worktree Control Model](docs/worktree-control.html) when distinguishing the
human, main-agent, Git worktree, worktree-agent, active controller, and integration owner.

### Mediated Mode

```text
Human <-> Main Agent <-> Agent @ worktree
```

Use mediated mode when the human wants one conversation, the work decomposes cleanly, or one
integration owner needs to coordinate dependencies. The main agent owns task routing and speaks
to the worktree agent.

### Direct Mode

```text
Human <-> Agent @ worktree
```

Use direct mode when the human needs lower-latency steering, deeper local context, or more
parallel conversational bandwidth. The worktree agent reports directly to the human and does
not wait for the main agent to relay decisions.

These modes are not global. The main agent can coordinate worktree A while the human directly
drives worktrees B and C.

## Create Or Adopt A Worktree

Either the human or main agent may create a worktree:

```bash
git worktree add ../project-<task-id> -b <kind>/<task-id> <base-commit>
```

Creation does not determine control. To adopt any existing worktree:

1. Locate it with `git worktree list --porcelain`.
2. Inspect its branch, base, commits, dirty state, and current task context.
3. Confirm no other controller is still issuing writes.
4. Establish goal, scope, acceptance, verification, and integration owner.
5. Continue in mediated or direct mode without rebuilding the worktree.

Unknown or manually created worktrees are externally controlled by default. The main agent may
inspect them but does not write until the human assigns control.

## Switch Control

Switching mode is a checkpoint operation, not a merge or worktree recreation.
The human first tells the outgoing controller to stop; opening another agent session alone does
not transfer write authority.

The outgoing controller:

1. Stops issuing new writes.
2. Commits a coherent checkpoint when practical.
3. Records any intentional dirty state, next action, validation, and risk in
   `.agents/runtime/HANDOFF.md` when Git state alone is insufficient.
4. Names the receiving controller and integration owner.

The incoming controller:

1. Reads the branch log, status, diff, task brief, and optional handoff.
2. Verifies that the checkpoint matches the stated task.
3. Takes exclusive write control and updates or removes stale runtime notes.
4. Continues on the same worktree and branch.

No durable registry is required. Git is the durable timeline; the optional handoff only bridges
uncommitted context. Direct human instructions override older mediated task packets for that
worktree.

Tool-owned session state does not transfer control by itself. A runtime may record orchestration
state under an ignored path such as `.omx/`, but the receiving controller still inspects Git and
the optional repository handoff before writing.

## Integrate Parallel Work

The main agent is the default integration owner, but the human may assign another integration
agent explicitly.

Each completed worktree returns:

```text
control mode
integration owner
base and head commit
changed files
validation evidence
remaining risks
knowledge candidates
integration notes
```

The integration owner inspects actual commits and diffs, integrates in dependency order, resolves
semantic conflicts, and runs final project verification. A direct worktree does not need to
switch back to mediated mode merely to be integrated.

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

- Keep lightweight control tooling in the main project environment.
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

Agents clean only within their touched scope. Use a bounded maintenance worktree when repeated
duplication, conflicts, stale docs, ambiguous configs, or accumulated runtime material make
continued delivery more expensive.

Prefer deletion over archive directories because Git already preserves history. Use
`.agents/skills/repo-maintenance/SKILL.md`.

## Command Surfaces

Project commands do not require governance:

```bash
make setup
make check
make test
make smoke
make verify
```

The governance doctor is separate:

```bash
uv run python .agents/governance/tools/repo_check.py
```

Add a public project command only when it replaces a repeated project procedure. Add a sidecar
procedure only when it removes a repeated agent coordination cost.

Training, inference, generation, and evaluation procedures used by experiment specs enter through
`<project-cli> workload`. Keep internal algorithms as library APIs; expose the stable operation that
an agent or human must repeat. Experiment specs do not call internal Python files, Make targets, or
free-form shell commands directly.
