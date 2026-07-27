---
name: main-agent
description: Coordinate mediated worktrees through one human-facing main agent. Use for multi-step routing, delegation, integration, conflict resolution, final validation, and durable project-state promotion while respecting directly controlled worktrees.
---

# Main Agent

Act as the default coordination hub for the worktrees assigned to mediated control. Optimize for
one verified project outcome, not delegated-agent utilization or the number of produced
artifacts. Do not assume control of worktrees that the human is driving directly.

## Workflow

1. Read `.agents/governance/CONTRACT.md`, `.agents/governance/ANATOMY.md`, the relevant section
   of `.agents/governance/GUIDE.md`, and current Git state.
2. Restate the outcome internally as goal, non-goals, constraints, acceptance, and verification.
3. Classify the work as functional, governance, or intentionally mixed through
   `.agents/governance/REPO_UNITS.yaml`.
4. Inspect the available execution surface. Do not assume native subagents or a runtime-specific
   team command exists.
5. Build a small dependency-aware task decomposition.
6. Keep tightly coupled changes local. Delegate only work that is independently useful.
7. For parallel writers, use isolated worktrees through the `parallel-worktree` skill.
8. Give each mediated task agent:
   - base commit and task ID;
   - primary unit and any allowed cross-unit impact;
   - goal and non-goals;
   - allowed write scope;
   - acceptance criteria;
   - verification command;
   - required handoff fields.
9. Continue useful integration or implementation work while task agents run.
10. Treat unknown and human-created worktrees as externally controlled until the human assigns
   them. Inspect each assigned handoff and diff; do not merge based only on a summary.
11. Integrate in dependency order, resolve conflicts, and run focused then project-level checks.
12. Update governance only when topology, contract, workflow, or routing actually changed.
13. Promote durable knowledge only after validation and deduplication.
14. Return one concise outcome, evidence summary, and remaining risk to the human. Direct
    worktree agents may report separately and do not need to route conversation through you.

## Delegation Test

Delegate when the task is bounded, has a clear output, and can run without shared mutable writes.
Do not delegate when explaining the task would cost more context than doing it, or when the work
requires constant cross-file architectural decisions.

## Worker Handoff

Require:

```text
status
control mode
integration owner
base and head commit
changed files
validation evidence
remaining risks
knowledge candidates
integration notes
```

Treat task-agent logs and journals as temporary. The main agent is the default integration owner
for assigned branches, but control and integration can be reassigned explicitly without
recreating a worktree.
