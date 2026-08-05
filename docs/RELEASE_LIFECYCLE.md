# Optional Release Lifecycle

Release is an optional functional surface. Projects without `RELEASE.yaml` continue to use every
experiment, evidence, archive, and verification command without release configuration.

A release profile declares explicit included paths and artifact-only verification commands. Draft
builds create an immutable ZIP plus `dist/<release-id>/manifest.json`; the manifest records the Git
revision, dirty-state identity, profile and artifact checksums, verification commands, and always
sets `release_ready: false`.

```bash
uv run researchctl release validate RELEASE.yaml
uv run researchctl release build RELEASE.yaml --release-id <release-id>
uv run researchctl release verify dist/<release-id>/manifest.json
```

Strict recording is a separate Human approval transition. It requires a clean checkout, the exact
expected source revision, a verified artifact, and a non-empty approver identity. It refuses to
overwrite either the approved manifest or reviewed Markdown provenance:

```bash
uv run researchctl release record dist/<release-id>/manifest.json \
  --approved-by <identity> \
  --expected-source-revision <exact-commit>
```

Generated trees remain ignored under `dist/`. The compact `releases/<release-id>.md` record may be
reviewed and committed. A draft build, including one produced by CI, can never claim release-ready
status.
