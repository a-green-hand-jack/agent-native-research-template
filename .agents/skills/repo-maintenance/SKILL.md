---
name: repo-maintenance
description: Compact code, docs, configs, memory, reports, and project state. Use when repeated glue, stale sources of truth, merge conflicts, or accumulated artifacts slow normal delivery.
---

# Repository Maintenance

Run a bounded maintenance pass when the cost of continuing through accumulated project entropy
exceeds the cost of consolidation.

## Prepare

1. Select one scope: code, config, docs, memory, reports, or artifacts.
2. Start a dedicated maintenance branch and worktree from an accepted commit.
3. Identify the primary unit of the material being compacted. The maintenance procedure is
   governance, but code, configs, reports, and evidence remain functional.
4. Identify the Contract that must remain true.
5. Add characterization tests or behavior snapshots when current behavior is not already
   protected.
6. Avoid mixing feature work into the pass.

## Compact

- Merge duplicate implementations and sources of truth.
- Inline or delete one-use glue that no longer clarifies a boundary.
- Remove replaced paths in the same change.
- Prefer Git history over `old/`, `backup/`, and unreferenced archives.
- Keep only active base configs and meaningful deltas.
- Distill journals into accepted memory only when the fact is durable and evidenced.
- Keep curated reports; move raw logs and large run output to external storage with retention.
- Mark superseded knowledge explicitly before deleting obsolete entries.

## Verify

1. Run focused tests and evaluations for the preserved Contract.
2. Run the project verification command.
3. Confirm common workflows now have fewer entry points or sources of truth.
4. Update Anatomy, Contract, Guide, and memory only where the maintenance changed their subject.
5. Report what was removed, what became canonical, evidence of preserved behavior, and remaining
   debt.

Do not measure success by the size of the refactor. Measure reduced orientation cost, fewer
duplicate paths, lower conflict probability, and preserved validated behavior.
