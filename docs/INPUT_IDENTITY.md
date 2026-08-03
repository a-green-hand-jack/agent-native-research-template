# Research Input Identity

Experiment inputs are declared independently of any ML framework, dataset registry, storage
provider, or execution backend. The runner records resolved identities in every new run manifest.

## Repository Paths

Use `kind: path` for a versioned file or directory inside the repository:

```yaml
inputs:
  - id: source-tree
    kind: path
    path: src
```

Files are identified by SHA-256. Directories are identified by hashing the sorted list of relative
file names and file hashes, so traversal order does not affect identity. Symbolic links are rejected
to prevent a repository-relative declaration from silently reading outside the repository.

Replay recalculates path identities and stops when their content or file count has changed.

## External URIs

Use `kind: uri` when another system owns the bytes:

```yaml
inputs:
  - id: benchmark-release
    kind: uri
    uri: https://example.invalid/benchmark/releases/v3
    version: v3
    sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

`version` and `sha256` are optional because some registries expose only one stable identifier. The
template records the supplied identity but does not fetch the URI or claim that it can independently
verify an external registry.

## Opaque Logical Identities

Use `kind: opaque` for a non-secret logical identity that cannot or should not expose a locator:

```yaml
inputs:
  - id: private-evaluation-split
    kind: opaque
    value: internal-split-2026-08
    version: revision-4
```

Opaque values are written into run and evidence manifests. Never use them for credentials, private
paths, personal data, access tokens, or values that should not become durable project history.

## Compatibility

The legacy free-form `data` field remains readable in version-1 run manifests, but new template
runs use the structured `inputs` records as the reproducibility boundary. Projects may add more
input kinds only by extending the experiment schema, resolver, run schema, replay checks, tests, and
Contract together.
