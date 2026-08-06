# Template Maintenance Surface

This directory exists only in the source template. It contains the bootstrap initializer, its unit tests, the downstream Agent-home projection, and the real-copy projection check used by maintainers. Initialization removes the entire directory from a downstream repository.

The source repository's root `AGENTS.md` and `.agents/` belong to template development. They are not downstream defaults. Initialization deletes that source context and creates a fresh, project-owned Agent home from `template/downstream/`; see `template/AGENT_HOME.md`.

Downstream projects retain their functional project CLI, project identity, experiments, evidence, archive, optional release capabilities, and the existing reviewed template-lifecycle interface. The Agent-home projection is deliberately separate from those functional capabilities: template-maintainer knowledge, memory, skills, and governance are never copied downstream.

Run `make template-test` for initializer regressions and `make template-e2e` to create and verify a real initialized copy. The projection must remain functional after deleting `.agents/` and `AGENTS.md`; the projected Agent home must route repeatable work through `<project-cli> project describe --json` and the public project CLI.
