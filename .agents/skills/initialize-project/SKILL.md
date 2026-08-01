---
name: initialize-project
description: Replace the template bootstrap with one consistent project identity and first vertical slice. Use immediately after creating a repository from this template.
---

# Initialize Project

Initialize once, before parallel development or expensive experiments. Keep the functional project
usable without `.agents/`.

## Collect Identity

Require four explicit values:

```text
human-readable project name
lowercase distribution name, using hyphens
lowercase Python package name, using underscores
stable lowercase contribution ID
```

Do not infer these values from a repository URL when the requested identity is ambiguous.

## Preview

Run a dry run first:

```bash
uv run python tools/initialize_project.py apply \
  --project-name "<Project Name>" \
  --distribution-name <distribution-name> \
  --package-name <package_name> \
  --contribution-id <contribution-id> \
  --dry-run
```

Inspect the planned writes and removals. The initializer updates `PROJECT.yaml`, package metadata,
the source package, smoke test, contribution index, smoke experiment, README, lockfile identity,
and the project-specific governance contract when the sidecar is present.

## Apply And Complete The Slice

Run the same command without `--dry-run`, then replace the initialized bootstrap implementation,
configuration, evaluation, and experiment question with the first real vertical slice. The tool
establishes a consistent identity; it does not invent the project's scientific contract.

## Verify

Run:

```bash
uv run python tools/initialize_project.py check
make verify
make research-run
uv run --no-project --with pyyaml python .agents/governance/tools/repo_check.py
```

The identity check rejects stale package paths, old imports, the template distribution name,
`bootstrap` contribution references, and inconsistent `PROJECT.yaml` values after initialization.
It also works when `.agents/` has been removed.

## Handoff

Return:

```text
PROJECT.yaml identity
renamed source and test paths
updated contribution and experiment IDs
project-specific contract status
verification commands and results
remaining bootstrap behavior that still needs a real implementation
```

Do not claim initialization is complete while placeholder behavior, claims, or evaluation logic
remain unexplained.
