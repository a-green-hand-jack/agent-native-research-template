# Agent Entry

The functional project is primary. `.agents/` contains project-owned context for agents; it does not implement project behavior.

1. Run `repoctl describe --json` to discover the repository and project interfaces.
2. Read `.agents/system/manifest.yaml`.
3. Load only the relevant project knowledge, memory, or project-specific skill.
4. Use `repoctl` for repository-development mechanics and `__CLI_NAME__` for project and research workloads. Do not bypass a public CLI with hidden scripts when a command exists.
5. Keep reusable project behavior in the functional package with tests, not under `.agents/` or `repo_cli/`.
6. Treat `.agents/runtime/` as ignored, non-durable coordination state.
7. Human authorization is still required for commits, pushes, pull requests, merges, releases, messages, configuration changes, and deletion.
