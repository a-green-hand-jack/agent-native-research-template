---
name: prepare-release
description: Validate, build, verify, and explicitly record an optional immutable project release.
---

# Prepare Release

Use this skill only when the downstream project adopts `RELEASE.yaml`. The skill owns the sequence
and approval gate; deterministic artifacts and approval records are produced by the project CLI.

## Draft

```bash
uv run researchctl release validate RELEASE.yaml
uv run researchctl release build RELEASE.yaml --release-id <release-id>
uv run researchctl release verify dist/<release-id>/manifest.json
```

Artifact verification does not make a draft release-ready.

## Record Approval

Require a clean exact source revision, verify the manifest again, and obtain an explicit Human
approval before running:

```bash
uv run researchctl release record dist/<release-id>/manifest.json \
  --approver "<Human Name>" \
  --decision approved
```

Never infer approval from CI, an agent decision, or a successful artifact build. Refuse overwrite;
changes require a new release ID or a separately reviewed correction path.
