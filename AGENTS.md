# Agent Entry Point

The project is primary. Agent governance is an optional, non-runtime sidecar under `.agents/`.
This root file exists only because agent tools discover `AGENTS.md` here.

Before changing the project:

1. Read `.agents/governance/CONTRACT.md`.
2. Read `.agents/governance/ANATOMY.md`.
3. Classify ownership through `.agents/governance/REPO_UNITS.yaml`.
4. Load `.agents/governance/GUIDE.md` or a project skill only when the task needs it.
5. Inspect Git state and choose the smallest verification that proves the outcome.

## Boundary

- Project code, commands, experiments, and reports must work without `.agents/`.
- Governance may inspect and invoke public project interfaces; it must not inject runtime
  imports, environment requirements, or hidden state into them.
- New paths are functional by default. Governance growth stays inside `.agents/`.
- Temporary agent state belongs in ignored `.agents/runtime/`, never in project source paths.

## Worktree Control

Human-to-main-agent is the default routing mode, not a permanent topology.

- In **mediated mode**, the human directs the main agent, which coordinates a worktree agent.
- In **direct mode**, the human directs the agent inside that worktree.
- Modes are per worktree, may coexist, and may switch at any checkpoint.
- A worktree may be created by the human or the main agent; creation does not determine control.
- Only the current controller writes to a worktree. Before control changes, leave a coherent Git
  checkpoint and, when context is not obvious, an ignored `.agents/runtime/HANDOFF.md`.

Read `.agents/governance/GUIDE.md` for adoption, switching, and integration procedures.
