---
name: dev-guide
description: Mandatory repository-local development workflow. Use before changing code, tests, configuration, experiments, documentation, governance, or GitHub state.
---

# Development Guide

Read this skill before every development task. It owns the workflow, not the repository's
structural facts or behavioral promises. Follow its links instead of copying those sources here.

## Establish The Task And Baseline

1. Re-read the latest human instruction. Separate the requested outcome, explicit non-goals,
   suggested follow-up work, and authorized external side effects.
2. Select the exact baseline: normally the current accepted default-branch commit, or an explicit
   tag or commit named by the maintainer.
3. Before analysis or editing, inspect Git state and prove the worktree is coherent. For a fresh
   task, require a clean worktree and `HEAD` equal to the selected baseline. Use an isolated
   worktree when parallel writers, uncommitted work, or branch switching could mix scopes.
4. Name the active controller and intended integration owner before another agent writes.

A branch name, directory name, recorded SHA, or stale fetch is not proof of baseline equality.

## Read The Sources Of Truth

Use progressive disclosure in this order:

1. Read `.agents/governance/ANATOMY.md` to locate components, connections, dynamic surfaces, and
   state ownership. Code is the structural source of truth; Anatomy is the maintained navigation
   system.
2. Read `.agents/governance/CONTRACT.md` to learn durable project, evidence, runtime, worktree, and
   interface promises. Contract is normative; implementation drift is a defect unless an
   authorized change deliberately changes the promise.
3. Classify every intended path through `.agents/governance/REPO_UNITS.yaml` before writing.
4. Inspect the cited code, configuration, schemas, tests, experiment definitions, and evidence.
   Documentation routes the investigation; executable state supplies the evidence.
5. Load `.agents/governance/GUIDE.md` or a narrower `.agents/skills/<name>/SKILL.md` only when the
   task needs that procedure. Do not preload unrelated manuals.

The systems have distinct jobs:

- **this skill** defines how development proceeds;
- **Anatomy** defines where the system is and how it is connected;
- **Contract** defines what the system promises;
- **code, tests, schemas, manifests, and reviewed evidence** prove the current state.

## Make The Smallest Complete Change

Before editing, state the relevant invariant, the intended variation axis, and the explicit
non-goals. Prefer one behavior-locked boundary or runnable vertical slice over speculative
abstraction or directory reshuffling.

Assess both fact systems for every change:

- Files, symbols, connections, composition, or state ownership changed: update the relevant
  Anatomy in the same change.
- Interface, behavior, error, ordering, retry, cancellation, recovery, compatibility, or validity
  semantics changed: update the relevant Contract and executable checks in the same change.
- Both changed: update both systems together.
- Neither changed: record that both were checked; do not manufacture documentation churn.

Keep functional and governance edits separately reviewable. Governance may invoke project
interfaces, but the project must remain usable after `.agents/` and `AGENTS.md` are removed.

## Validate In Layers

Run the narrowest decisive check first, then the affected broader checks:

```bash
make check
make test
make verify
uv run --no-project --with pyyaml python .agents/governance/tools/repo_check.py
```

Use `make research-run` and the evidence workflow when a change creates or supports a scientific
or benchmark claim. Run focused tests before broad suites, inspect every non-zero exit, and never
report an interrupted or timed-out command as passing.

Passing tests cannot excuse a violated Contract. Prose cannot excuse a failing executable check.
Before handoff, inspect the final diff against the human instruction and name every untested risk.

## Apply The Side-Effect Gate

Reading, analysis, local edits, local validation, and local reports do not authorize remote or
system-changing actions. Commit, push, open or edit a pull request, merge, publish, release,
install, change configuration, send messages, file issues, or delete resources only when the
human explicitly authorizes that specific side effect.

Before each authorized commit, push, or pull request action:

1. re-read the latest scope and authorization;
2. verify the selected base has not moved unexpectedly;
3. verify the intended Git author and remote account;
4. confirm the staged or proposed diff contains only the reviewed change;
5. capture validation evidence, unresolved risks, and reproduction commands.

A passing gate is not permission. Permission to open a pull request is not permission to merge it.

## Handoff

Return:

```text
requested outcome and explicit non-goals
selected baseline and branch or worktree
relevant Anatomy and Contract paths
changed files and ownership classification
validation commands and results
experiment or evidence IDs when applicable
remaining risks and untested surfaces
external side effects performed under explicit authorization
next action that still requires authorization
```
