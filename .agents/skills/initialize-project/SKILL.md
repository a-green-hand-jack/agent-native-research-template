---
name: initialize-project
description: Replace the bootstrap in a fresh repository created from this template with one consistent project identity and first vertical slice. Do not use for a mature existing repository.
---

# Initialize Project

Use this skill once, immediately after creating a new repository from this template and before
parallel development or expensive experiments. Keep the functional project usable without
`.agents/`.

Do not run this initializer against a mature repository that was not created from the template. Use
`.agents/skills/adopt-research-template/SKILL.md` for that case. After initialization, use
`.agents/skills/update-from-template/SKILL.md` for reviewed downstream template updates.

## Confirm The Repository State

Before previewing initialization:

1. require the uninitialized `PROJECT.yaml` template identity;
2. select and record the exact template commit used as the baseline;
3. require a clean worktree and no parallel writer;
4. run the current template verification so failures are not misattributed to initialization;
5. confirm that the repository still contains the expected bootstrap package and smoke test.

Initialization is an identity replacement, not a general repository merger or architecture
migration.

## Collect Identity

Require five explicit values:

```text
human-readable project name
lowercase distribution name, using hyphens
lowercase Python package name, using underscores
lowercase installed CLI name, using hyphens
stable lowercase contribution ID
```

The distribution and CLI names may be the same, but both must be chosen deliberately. Do not infer
identity values from a repository URL when the requested identity is ambiguous. The CLI name must
replace the template default `researchctl`.

## Preview

Run a dry run first:

```bash
uv run python tools/initialize_project.py apply \
  --project-name "<Project Name>" \
  --distribution-name <distribution-name> \
  --package-name <package_name> \
  --cli-name <cli-name> \
  --contribution-id <contribution-id> \
  --dry-run
```

Inspect every planned write and removal. The functional initializer updates `PROJECT.yaml`, package
metadata, installed console-script entry, source package, smoke test, contribution index, smoke
experiment, Makefile, README, and lockfile identity. It removes template-only README sections while
preserving a compact provenance marker. It never reads or writes the governance sidecar.

Initialization records the source template name, template contract version, source Git commit, and
an initially empty migration ledger in `PROJECT.yaml`. These fields describe provenance; they do
not authorize automatic synchronization from the template repository.

## Apply And Complete The Slice

Run the same command without `--dry-run`, then replace the initialized bootstrap implementation,
configuration, evaluation, and experiment question with the first real vertical slice. The tool
establishes consistent identity and paths; it does not invent the project's behavior, scientific
contract, metrics, assets, or claims.

When the optional sidecar exists, update the project-specific section of
`.agents/governance/CONTRACT.md` as a separate governance change. Record externally observable
behavior, scientific claims under test, schemas, validity requirements, compatibility constraints,
and explicit non-goals.

The initialized CLI must be the public experiment and archive control surface. Verify that the
configured command from `PROJECT.yaml.cli_name` is installed and that the template default CLI no
longer remains in package metadata.

## Check And Migrate

Check template compatibility explicitly:

```bash
uv run python tools/template_compat.py check
```

When a future template version ships a reviewed registered migration, preview and apply it
explicitly:

```bash
uv run python tools/template_compat.py migrate --to <version> --dry-run
uv run python tools/template_compat.py migrate --to <version>
```

Migrations are forward-only, sequential, and registered in repository code. They do not synchronize
every upstream file. Use `.agents/skills/update-from-template/SKILL.md` when assessing additional
upstream capabilities or shared-file changes. Never pull or overwrite arbitrary downstream files
merely because the source template changed.

## Verify

Run:

```bash
uv run python tools/initialize_project.py check
uv run python tools/template_compat.py check
uv run <cli-name> --help
make verify
make research-run
uv run --no-project --with pyyaml python .agents/governance/tools/repo_check.py
```

The identity check rejects stale package paths, old imports, the template distribution and CLI
names, `bootstrap` contribution references, inconsistent `PROJECT.yaml` values, and malformed
provenance. The compatibility check rejects unsupported or unapplied template versions. Functional
checks continue to work after `.agents/` and `AGENTS.md` are removed.

## Handoff

Return:

```text
selected template baseline commit
PROJECT.yaml identity and template provenance
project, distribution, package, CLI, and contribution identities
renamed source and test paths
updated contribution and experiment IDs
applied migration versions
project-specific contract status, when the sidecar exists
verification commands and results
remaining bootstrap behavior that still needs a real implementation
```

Do not claim initialization is complete while placeholder behavior, claims, evaluation logic, or
an unverified console-script identity remain unexplained.
