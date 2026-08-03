---
name: update-from-template
description: Assess and apply reviewed template updates to an initialized downstream repository while preserving project-owned customizations. Use only when trusted template provenance exists.
---

# Update From Template

Use this skill for a downstream repository whose `PROJECT.yaml` records
`template.name: agent-native-research-template`, `initialized: true`, a supported template version,
and a trusted `initialized_from_commit`. If that provenance is missing, malformed, or known to be
incorrect, stop and use `.agents/skills/adopt-research-template/SKILL.md` instead.

Updating is not the same as merging the template default branch. The safe model is:

```text
registered contract migrations
        +
ownership-aware upstream difference assessment
        +
downstream-specific staged pull requests
```

Reading and producing an update plan do not authorize writes, dependency changes, workflow changes,
issues, pull requests, or merges.

## Establish Provenance And Baselines

Before proposing an update, record:

```text
downstream default branch and exact accepted commit
clean worktree or isolated worktree controller
template name and current contract version from PROJECT.yaml
initialized_from_commit and applied_migrations
target template version
target template tag or exact commit SHA
existing downstream verification commands and results
```

Use exact commits, not branch names or a stale local fetch. Confirm that the recorded source commit
belongs to the expected template repository. If the project maintains a later reviewed template
source checkpoint outside `PROJECT.yaml`, cite it explicitly; never invent one.

The current metadata records the initialization source and migration ledger, not a complete history
of every manually adopted upstream change. State this limitation when a precise three-way base
cannot be proven.

## Run Compatibility Checks First

Inspect the downstream copies of the initializer and compatibility tool, then run:

```bash
uv run python tools/initialize_project.py check
uv run python tools/template_compat.py check
uv run python tools/template_compat.py migrate --to <target-version> --dry-run
```

Registered migrations are the authoritative path for known template contract versions. They are
forward-only, sequential, and must fail when an intermediate implementation is missing.

Do not copy a newer `template_compat.py` into the repository merely to make an unsupported migration
appear available. First review the target template's migration implementation and bring it in as an
independent, testable compatibility change when needed.

## Separate Migration From Synchronization

Classify target changes into:

1. **registered migration**: an explicit downstream transformation represented by the migration
   registry and ledger;
2. **new optional capability**: a template feature that the downstream may adopt, adapt, or skip;
3. **maintenance update**: dependency pins, CI policy, documentation, schema tightening, or tooling
   that may apply without changing project behavior;
4. **template-only change**: bootstrap examples, initializer behavior, or defaults irrelevant after
   downstream initialization;
5. **project conflict**: an upstream change that would overwrite or contradict downstream-owned
   behavior.

Applying a registered migration does not imply that every upstream file should be synchronized.
Likewise, a higher template version in `PROJECT.yaml` is not proof that optional upstream features
were adopted.

## Classify Ownership Before Patching

For every changed semantic surface or path, assign one of:

- **template-owned**: deliberately retained downstream infrastructure whose behavior is still
  governed by the template contract and has not been project-customized;
- **project-owned**: source, experiments, scientific claims, public APIs, deployment, release,
  project configuration, and any surface the downstream has taken over;
- **shared/customized**: README, CI, build metadata, command entry points, schemas, Makefile, and
  governance files containing both template and project decisions;
- **not present / intentionally removed**: optional sidecar or feature surfaces the downstream does
  not carry.

These are evidence-based classifications, not hard-coded path lists. Use Git history, current
content, ownership documents, tests, and maintainer intent. Project-owned files are never replaced.
Shared files require a semantic patch and downstream-specific validation.

## Compare The Source And Target Safely

When trusted source and target template commits are available, inspect:

```text
source template commit -> target template commit     upstream intent
downstream baseline -> current downstream tree       downstream customization
```

Use a three-way comparison only as evidence for a plan. Do not automatically accept either side.
For each upstream change record:

```yaml
surface: exact-head-ci-policy
upstream_change: require checkout of the exact PR head
ownership: shared/customized
downstream_state: existing CI includes deployment jobs
resolution: adapt the policy into the existing workflow
validation: negative policy test plus unchanged deployment checks
```

When no reliable common source exists, do not claim a three-way merge. Fall back to capability-level
assessment and route uncertain features through the adoption skill.

## Produce An Update Plan

Return a plan before writing:

```text
provenance and exact commits
current and target template versions
registered migration plan
upstream changes classified by category
path and semantic ownership
adopt/adapt/skip decision for optional capabilities
ordered issue-sized phases
validation and rollback per phase
known provenance gaps and unresolved conflicts
```

Recommended phase order:

1. import and test any missing migration implementation;
2. apply registered migrations and verify the ledger;
3. add unmodified template-owned maintenance changes;
4. adapt shared surfaces one at a time;
5. adopt optional capabilities only through separate justified issues;
6. leave project-owned and intentionally removed surfaces unchanged.

Do not combine a mechanical migration, a CI rewrite, a dependency upgrade, and a new research
capability into one unreviewable pull request.

## Apply Under Explicit Authorization

For each authorized phase:

1. create an isolated branch or worktree from the recorded downstream baseline;
2. preview the migration or patch before writing;
3. inspect the final diff for template defaults, renamed project identity, CLI name, package name,
   contribution IDs, and downstream-specific paths;
4. run focused migration tests, downstream verification, and any real experiment or conformance
   checks affected by the change;
5. run verification without `.agents/` when the downstream retains the optional sidecar boundary;
6. require successful GitHub Actions or commit status on the exact final PR head;
7. merge with the expected head SHA and verify branch cleanup.

After a migration, `PROJECT.yaml.template.version` and `applied_migrations` must match the registered
result. Do not add ad hoc provenance fields without a reviewed template-contract change. Record the
target source commit and update evidence in the issue, pull request, and final handoff.

## Prohibited Shortcuts

Never:

- merge, rebase, or copy the template `main` branch into a downstream repository as the update
  procedure;
- force checkout template versions of project-owned or shared files;
- overwrite the downstream package, CLI name, README, CI, lockfile, experiments, or source tree;
- mark a migration applied without executing and validating its registered implementation;
- treat deletion from the template as permission to delete a downstream path;
- restore an optional `.agents/` sidecar that the downstream deliberately removed;
- reuse CI evidence from an ancestor after the update head moves.

## Handoff

Return:

```text
downstream baseline and target template commit
provenance confidence and limitations
current and target contract versions
migrations imported, previewed, and applied
upstream changes adopted, adapted, skipped, or blocked
ownership classification and preserved downstream surfaces
validation commands, exact tested head, and remote CI/status
rollback path, unresolved conflicts, and future optional phases
external side effects performed under authorization
```
