# Template Maintenance Surface

This directory exists only in the source template. It contains the bootstrap initializer, its
unit tests, and the real-copy projection check used by maintainers.
Initialization removes the entire directory from a downstream repository.

The canonical ownership and lifecycle classification is
`.agents/governance/REPO_UNITS.yaml`; this directory does not duplicate it.

Downstream projects retain project identity and compatibility checks through
`<project-cli> project check`, `<project-cli> workload ...`, and `<project-cli> template ...`.
Those commands are functional project interfaces implemented under `tools/` and `src/<package>/`;
they do not import this directory.

Run `make template-test` for initializer regressions and `make template-e2e` to create and verify
a real initialized copy, including a second verification pass after removing `.agents/` and
`AGENTS.md`.
