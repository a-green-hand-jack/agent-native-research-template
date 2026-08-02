# Agent Entry Point

The project is primary. Agent governance is an optional, non-runtime sidecar under `.agents/`.
This root file exists only because agent tools discover `AGENTS.md` here.

Before changing code, configuration, tests, documentation, experiments, or governance, read
`.agents/skills/dev-guide/SKILL.md`. It owns the development workflow and routes the task to the
repository's structural facts, behavioral promises, ownership boundary, focused validation, and
side-effect gates without duplicating those sources here.

## Boundary

- Project code, commands, experiments, and reports must work without `.agents/`.
- Governance may inspect and invoke public project interfaces; it must not inject runtime
  imports, environment requirements, or hidden state into them.
- New paths are functional by default. Governance growth stays inside `.agents/`.
- Template-owned temporary coordination state belongs in ignored `.agents/runtime/`, never in
  project source paths.

## Agent Runtime

This repository defines durable project and governance truth, not a required orchestration
product. Codex, OMX, native subagents, hooks, or another runtime may supply the current execution
surface.

- Detect available capabilities before choosing solo execution, native delegation, worktrees, or
  a runtime-specific team mode.
- `worktree agent` is a repository role, not a required runtime type. A direct session, native
  child agent, or runtime team worker may fill it.
- Tool-generated instruction overlays must remain bounded by paired tool-owned markers,
  repeatable to apply, and removable without damaging this adapter.
- Tool-owned state such as `.omx/` remains ignored and never becomes project truth merely because
  a runtime produced it.

## Worktree Control

Human-to-main-agent is the default routing mode, not a permanent topology.

- In **mediated mode**, the human directs the main agent, which coordinates a worktree agent.
- In **direct mode**, the human directs the agent inside that worktree.
- Modes are per worktree, may coexist, and may switch at any checkpoint.
- A worktree may be created by the human or the main agent; creation does not determine control.
- Only the current controller writes to a worktree. Before control changes, leave a coherent Git
  checkpoint and, when context is not obvious, an ignored `.agents/runtime/HANDOFF.md`.

The development guide routes to `.agents/governance/GUIDE.md` when worktree adoption, switching,
or integration procedures are needed.
