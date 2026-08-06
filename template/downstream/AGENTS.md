# Agent Entry

The functional project is primary. `.agents/` contains project-owned context for agents; it does not implement project behavior.

1. Run `__CLI_NAME__ project describe --json` to discover the project identity, command groups, and context roots.
2. Read `.agents/system/manifest.yaml`.
3. Load only the relevant project knowledge, memory, or project-specific skill.
4. Use `__CLI_NAME__` for repeatable project actions. Do not bypass the public CLI with hidden scripts when a command exists.
5. Keep reusable project behavior in the functional package with tests, not under `.agents/`.
6. Treat `.agents/runtime/` as ignored, non-durable coordination state.
7. Human authorization is still required for commits, pushes, pull requests, merges, releases, messages, configuration changes, and deletion.
