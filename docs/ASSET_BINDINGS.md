# Logical Asset Bindings

Scientific experiment intent names logical assets; execution profiles bind those names to physical
locations. This keeps repository specs portable across worktrees, servers, and storage layouts.

## Registry

`assets/registry.yaml` owns stable asset IDs and roles:

- `source`
- `dataset`
- `generation_oracle`
- `evaluation_oracle`
- `checkpoint`
- `cache`
- `output`

The registry may also declare expected file/directory type, size bounds, whether an asset is
reconstructable, and whether an output is immutable.

## Experiment requirements

An experiment lists logical requirements only:

```yaml
assets:
  - id: source-tree
    phase: generation
    access: read
```

The requirement participates in the deterministic plan. It does not contain machine-specific
paths, mount points, credentials, or provider configuration.

## Execution profile bindings

The selected executor profile binds IDs to physical records:

```yaml
asset_bindings:
  source-tree:
    kind: path
    scope: repository
    path: src
```

Bindings may use `path`, `uri`, or `opaque`. Repository paths are content-hashed locally. External
paths must be absolute. URI and opaque records are durable declarations and are not fetched. Opaque
values must not contain secrets.

## Preflight

Run preflight without starting the experiment:

```bash
uv run python tools/evidence.py preflight experiments/specs/<name>.yaml
uv run python tools/evidence.py preflight experiments/specs/<name>.yaml --phase generation
```

Preflight checks binding presence, role/type compatibility, readability, size limits, checksums,
path escape and symlink rules, and immutable-output overwrite rules. The output is JSON with a
stable binding SHA-256.

A phase receives only assets declared for that phase or for `all`. A generation preflight therefore
does not expose evaluation-only oracles. The current one-command runner uses the `all` preflight;
phase-scoped execution uses the narrower result.

Resolved path bindings are exported only to the executing process as
`RESEARCH_ASSET_<NORMALIZED_ID>`. URI and opaque records remain evidence metadata and are never
turned into credentials or fetched implicitly.

## Identity boundary

Changing only physical bindings in an executor profile does not change the scientific plan hash.
The resolved binding identity is recorded separately in run evidence so a result remains traceable
to the actual files, URIs, or opaque provider references used.
