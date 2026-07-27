# Agent Instructions

## Mission

Serve the project outcome. Reduce human-agent and agent-agent friction without turning
governance into a second product.

## Boot Sequence

Before changing files:

1. Read `CONTRACT.md` for invariants.
2. Read `ANATOMY.md` for ownership and dependency direction.
3. Read the relevant workflow in `GUIDE.md`.
4. Inspect `git status`, the current branch, and nearby tests.
5. Identify the narrowest verification command that can prove the task complete.

Do not load every memory topic, report, skill, or historical artifact by default. Follow indexes
and load details only when the task needs them.

## Authority

Use this order when instructions conflict:

1. Safety and the human's explicit current instruction.
2. `CONTRACT.md` and executable tests/evaluations.
3. The current task brief.
4. `GUIDE.md`.
5. `ANATOMY.md`.
6. Accepted project memory and skills.
7. Runtime notes and historical logs.

An explicit task may authorize a contract change. Until that change is made and validated, the
current contract remains authoritative.

## Main-Agent Workflow

The main agent is the single interface to the human. It should:

1. Translate the requested outcome into bounded tasks.
2. Keep tightly coupled work local.
3. Delegate independent read-heavy work freely and independent write work only into isolated
   Git worktrees.
4. Give each worker a base commit, goal, non-goals, write scope, acceptance criteria, and
   verification command.
5. Collect handoffs, integrate changes, resolve conflicts, and run final verification.
6. Return one consolidated result to the human.
7. Promote only validated, durable knowledge.

Workers do not modify root governance files unless their task explicitly owns an architecture,
contract, or workflow change.

## Project Skills

Read a project skill only when its trigger applies:

- `.agents/skills/main-agent/SKILL.md`: coordinate a multi-step or delegated project task.
- `.agents/skills/parallel-worktree/SKILL.md`: create or integrate parallel write work.
- `.agents/skills/run-experiment/SKILL.md`: execute a reproducible experiment.
- `.agents/skills/add-baseline/SKILL.md`: integrate an external implementation.
- `.agents/skills/repo-maintenance/SKILL.md`: run a bounded compaction pass.

## Change Rules

- Prefer an existing module, command, config, or source of truth over a new one.
- Keep temporary exploration under ignored runtime or run directories.
- A new permanent module needs a current caller, a clear responsibility, and focused validation.
- Do not mix a broad refactor with a feature or experiment unless the refactor is required.
- Remove an obsolete path in the same change that replaces it.
- Use Git history instead of `old/`, `backup/`, or unreferenced archive directories.
- Never commit secrets, local credentials, private host details, raw logs, large datasets, or
  checkpoints.

## Definition Of Done

A task is complete when:

- requested behavior exists;
- relevant tests or evaluations pass;
- the diff contains no unrelated expansion;
- temporary files are removed or ignored;
- affected Anatomy, Contract, or Guide content is updated when semantics changed;
- the handoff states changed files, validation evidence, remaining risk, and durable knowledge
  candidates.

