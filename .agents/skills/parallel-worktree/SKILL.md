---
name: parallel-worktree
description: Coordinate independent parallel write tasks with Git worktrees. Use when multiple agents need to modify the same project concurrently without sharing mutable files or branches.
---

# Parallel Worktree

Use Git as the temporal and concurrency layer. One worktree represents one bounded possible
future of the project.

## Create

1. Verify the canonical repository, accepted base commit, active worktrees, and dirty state.
2. Choose a short task ID and branch such as `feat/<id>`, `exp/<id>`, or `maint/<id>`.
3. Create a sibling worktree from the explicit base commit.
4. Create ignored runtime state inside that worktree when the task needs a pad or handoff file.
5. Give the worker a primary unit, non-overlapping write scope, and explicit verification
   command. Governance paths are out of scope unless named explicitly.

Example:

```bash
git worktree add ../project-<task-id> -b <kind>/<task-id> <base-commit>
```

Adapt the sibling path to the repository's local convention. Do not assume a private absolute
path in committed project files.

## Coordinate

- Never assign two workers ownership of the same mutable files.
- Share immutable inputs such as committed configs, data hashes, and environment locks.
- Keep outputs namespaced by task or run ID.
- Send scope changes through the main agent before writing outside the assigned boundary.
- Commit coherent checkpoints; do not leave integration dependent on an unexplained dirty tree.

## Integrate

1. Read the worker handoff and inspect the actual commits and diff.
2. Rebase or merge only after checking whether the accepted base changed.
3. Integrate dependent branches in dependency order.
4. Resolve semantic conflicts against the Contract, not by mechanically choosing one side.
5. Run focused checks after each integration and the project verification at the end.
6. Remove merged worktrees and branches using ordinary non-destructive Git procedures.

Do not use destructive cleanup commands to resolve uncertainty. Preserve unmerged work until its
status is understood.
