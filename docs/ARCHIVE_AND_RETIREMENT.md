# Archive Verification And Retirement

Temporary servers, worktrees, branches, volumes, and local run directories are not durable storage.
This template therefore separates three decisions:

1. **stop** an execution or service;
2. **delete** a physical resource;
3. **retire** a logical run, branch, worktree, or provider allocation after retained assets are safe.

`tools/archive.py` is read-only. It validates manifests, verifies declared copies, and emits
machine-readable retirement decisions. It never stops or deletes anything.

## Archive manifests

An archive manifest records each retained asset's logical identity, content SHA-256,
reconstructability, storage locations, fault domains, and copy-verification evidence.

A checksum written into YAML is not verification. A copy is verified only when either:

- `local_readback` re-opens the repository-relative copy and recomputes its SHA-256; or
- `external_evidence` records a verification timestamp, matching SHA-256, and non-empty evidence
  describing the independent read-back or provider verification.

Reconstructable assets require one verified fault domain. Assets marked
`reconstructable: false` require at least two verified copies in distinct fault domains.

## Commands

```bash
uv run python tools/archive.py validate archives/example.yaml
uv run python tools/archive.py verify archives/example.yaml
uv run python tools/archive.py retirement-preflight archives/example.yaml
```

All commands print JSON. `verify` exits non-zero when copy requirements are unmet.
`retirement-preflight` exits non-zero when required assets are unsafe, unique untracked paths
remain, or declared retention actions are pending.

## Safety boundary

Retirement output contains `destructive_action_performed: false`. A human or separately authorized
provider tool may later act on an allowed decision, but stopping and deletion remain distinct,
explicit permissions. Never place credentials, private provider paths, or secrets in archive
manifests or external evidence strings.
