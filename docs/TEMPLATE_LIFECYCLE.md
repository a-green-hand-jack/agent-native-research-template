# Template Lifecycle Plans

The source template's bootstrap implementation and real-copy checks live under `template/` and are
removed during initialization. Downstream repositories retain `researchctl project check`,
registered migrations under `researchctl project ...`, and the update-plan commands documented
here. Template-maintainer code is not a downstream runtime dependency.

`PROJECT.yaml.template.reviewed_template_commit` is the only durable upstream baseline. It records
the exact template commit whose relevant content was reviewed in the downstream repository. The
template contract version and migration ledger remain independent: a higher version does not imply
that every optional capability was adopted.

Generate a side-effect-free update plan from a local checkout of the source template:

```bash
uv run researchctl template inspect
uv run researchctl template plan \
  --template-root /path/to/agent-native-research-template \
  --target <exact-commit> \
  --output /tmp/template-plan.json
```

The canonical plan hash covers the baseline, target, downstream commit and path classifications.
`safe` means the downstream still matches the reviewed baseline; `already` means it matches the
target; `conflict` means downstream customization overlaps the upstream change; `manual` is used
for adoption without provenance and for deletions. Plans record dirty state but never write.

Automatic apply is restricted to `safe` writes in provenance-backed update plans, on a clean
non-default branch, with the expected plan hash:

```bash
uv run researchctl template apply /tmp/template-plan.json \
  --template-root /path/to/agent-native-research-template \
  --expected-plan-sha256 <sha256>
```

Resolve manual and conflicting paths, run downstream validation and exact-head CI, then explicitly
record the reviewed target. Recording re-reads every planned target path and refuses unresolved
content:

```bash
uv run researchctl template record-baseline /tmp/template-plan.json \
  --template-root /path/to/agent-native-research-template \
  --expected-plan-sha256 <sha256>
```

Neither planning nor a higher template version authorizes merging template history, overwriting
project-owned files, accepting optional capabilities, or recording a baseline before review.
