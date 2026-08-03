# Governance Influences

This file records the provenance of the optional repository-governance sidecar. It distinguishes
ideas that influenced the design from software that the template actually embeds or requires.

## LingTai-Inspired Principles

[LingTai](https://lingtai.ai/) presents an Agent OS built around a file-oriented model in which
agent identity, knowledge, memory, relationships, and communication can persist in ordinary files
and directories rather than belonging only to one model session. Its official description also
emphasizes that the durable file state can remain when the underlying model changes. The
[official LingTai overview](https://lingtai.ai/en/about/) describes this as a Unix-style
"everything is a file" approach.

This template adapts a deliberately narrow subset of those ideas to repository development
governance:

| Influenced principle | Template interpretation | Concrete implementation |
| --- | --- | --- |
| Durable agent context belongs in files | Repository-local files, not chat history, hold reviewed development guidance and handoff state | `AGENTS.md`, `.agents/governance/`, `.agents/skills/`, `.agents/memory/`, `.agents/runtime/` |
| The durable state should outlive one model or runtime | Codex, OMX, native subagents, direct sessions, or another runtime can read the same repository contract | `AGENTS.md` runtime-compatibility rules and `.agents/governance/GUIDE.md` |
| Context should be loaded progressively | A thin root adapter routes agents to one mandatory development guide, which then routes to narrower facts and procedures | `AGENTS.md` and `.agents/skills/dev-guide/SKILL.md` |
| Agent roles and relationships should be explicit | Worktree controller, integration owner, handoff point, and routing mode are repository concepts rather than hidden session assumptions | `.agents/governance/GUIDE.md` and `.agents/governance/docs/worktree-control.html` |
| File topology should be inspectable and portable | Ownership, dependency direction, required paths, and routing are represented in tracked files and checked mechanically | `.agents/governance/REPO_UNITS.yaml` and `.agents/governance/tools/repo_check.py` |

The template uses these ideas to reduce the cost and ambiguity of agent-assisted repository work.
It does not attempt to reproduce LingTai's complete Agent OS.

## Template-Specific Design

The following mechanisms are template-specific engineering decisions rather than claims about
LingTai:

- the strict split between the functional project and the removable `.agents/` governance sidecar;
- `ANATOMY.md` as structural navigation and `CONTRACT.md` as normative behavioral promises;
- exact-PR-head GitHub Actions evidence before merge;
- explicit authorization gates for commits, pushes, pull requests, merges, releases, messages,
  configuration changes, and deletion;
- project verification after deleting `.agents/` and `AGENTS.md`;
- experiment plans, run evidence, replay checks, metric semantics, archives, and retirement gates.

These additions make the governance model suitable for a GitHub research-project template rather
than a persistent general-purpose Agent OS.

## Explicit Non-Integration

This repository is not a LingTai distribution or adapter. It has no runtime dependency on LingTai
and does not embed or implement its:

- TUI or installation workflow;
- avatar or agent-lifecycle system;
- agent network or orchestration service;
- memory, mail, communication, or knowledge-store runtime;
- provider integration or model-routing layer.

Removing `.agents/` and `AGENTS.md` removes the optional governance sidecar without changing the
functional experiment and evidence interfaces. The attribution above indicates design influence,
not compatibility, endorsement, affiliation, or runtime integration.

## Maintenance Rule

When a future change materially adopts another external governance concept, update this file in the
same pull request. Keep source-derived influence, template-specific interpretation, and actual
runtime dependencies clearly separated.
