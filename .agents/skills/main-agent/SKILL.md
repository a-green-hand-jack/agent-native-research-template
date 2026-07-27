---
name: main-agent
description: Coordinate a project task through one human-facing main agent. Use for multi-step work, parallel delegation, integration, conflict resolution, final validation, and durable project-state promotion.
---

# Main Agent

Act as the project's single interface to the human. Optimize for one verified project outcome,
not for worker utilization or the number of produced artifacts.

## Workflow

1. Read the root Contract, Anatomy, Guide, and current Git state.
2. Restate the outcome internally as goal, non-goals, constraints, acceptance, and verification.
3. Classify the work as functional, governance, or intentionally mixed through
   `REPO_UNITS.yaml`.
4. Build a small dependency-aware task decomposition.
5. Keep tightly coupled changes local. Delegate only work that is independently useful.
6. For parallel writers, use isolated worktrees through the `parallel-worktree` skill.
7. Give each worker:
   - base commit and task ID;
   - primary unit and any allowed cross-unit impact;
   - goal and non-goals;
   - allowed write scope;
   - acceptance criteria;
   - verification command;
   - required handoff fields.
8. Continue useful integration or implementation work while workers run.
9. Inspect each handoff and diff. Do not merge based only on a worker's summary.
10. Integrate in dependency order, resolve conflicts, and run focused then project-level checks.
11. Update governance only when topology, contract, workflow, or routing actually changed.
12. Promote durable knowledge only after validation and deduplication.
13. Return one concise outcome, evidence summary, and remaining risk to the human.

## Delegation Test

Delegate when the task is bounded, has a clear output, and can run without shared mutable writes.
Do not delegate when explaining the task would cost more context than doing it, or when the work
requires constant cross-file architectural decisions.

## Worker Handoff

Require:

```text
status
base and head commit
changed files
validation evidence
remaining risks
knowledge candidates
integration notes
```

Treat worker logs and journals as temporary. The main agent owns the canonical merge, governance
changes, and final human communication.
