---
name: parallel-worktree
description: Coordinate independent parallel write tasks with Git worktrees. Use when multiple agents need to modify the same project concurrently without sharing mutable files or branches.
---

# Parallel Worktree

Use Git as the temporal and concurrency layer. One worktree represents one bounded possible
future of the project. Worktree creation, conversational control, and integration ownership are
three separate decisions.

## Create

1. Verify the canonical repository, accepted base commit, active worktrees, and dirty state.
2. Choose a short task ID and branch such as `feat/<id>`, `exp/<id>`, or `maint/<id>`.
3. The human or main agent creates a sibling worktree from the explicit base commit.
4. Create ignored runtime state inside that worktree when the task needs a pad or handoff file.
5. Record mediated or direct control, the integration owner, primary unit, non-overlapping write
   scope, and explicit verification command. Governance paths are out of scope unless named.

Example:

```bash
git worktree add ../project-<task-id> -b <kind>/<task-id> <base-commit>
```

Adapt the sibling path to the repository's local convention. Do not assume a private absolute
path in committed project files.

Creation does not grant permanent control. A main agent may adopt a human-created worktree, and
the human may directly take over a main-agent-created worktree.

## Coordinate

- Never assign two workers ownership of the same mutable files.
- Share immutable inputs such as committed configs, data hashes, and environment locks.
- Keep outputs namespaced by task or run ID.
- In mediated mode, route scope changes through the main agent.
- In direct mode, the worktree agent resolves scope changes with the human.
- Never let the main agent and human-controlled agent issue writes to the same worktree
  concurrently.
- Commit coherent checkpoints; do not leave integration dependent on an unexplained dirty tree.

## Switch Control

1. Stop writes from the outgoing controller.
2. Commit a coherent checkpoint when practical.
3. Put uncommitted context, next action, validation, and risk in ignored
   `.agents/runtime/HANDOFF.md` when Git is insufficient.
4. The incoming controller reads the log, status, diff, task brief, and handoff before writing.
5. Continue on the same branch and worktree. Do not recreate or merge solely to change mode.

Different worktrees may use mediated and direct modes at the same time.

## Integrate

1. Read the worktree handoff and inspect the actual commits and diff.
2. Rebase or merge only after checking whether the accepted base changed.
3. Integrate dependent branches in dependency order.
4. Resolve semantic conflicts against `.agents/governance/CONTRACT.md`, not by mechanically
   choosing one side.
5. Run focused checks after each integration and the project verification at the end.
6. Remove merged worktrees and branches using ordinary non-destructive Git procedures.

Do not use destructive cleanup commands to resolve uncertainty. Preserve unmerged work until its
status is understood.
