# Verified Archives And Retirement Gates

Temporary servers, volumes, worktrees, and research branches are execution surfaces, not durable
storage. Retirement decisions require an asset inventory and verified copy evidence.

## Create an archive

```bash
uv run researchctl archive create <run-id> \
  --copy /absolute/archive/root-a::region-a \
  --copy /absolute/archive/root-b::region-b
```

The command inventories the run manifest's immutable artifacts and read-only logical path assets.
Before copying, it re-reads each source and verifies its recorded content identity. Local copies are
then re-read from the destination and recorded with location, SHA-256, file count, verification time,
and a named fault domain.

A checksum written into a manifest is not a verified copy. Verification requires either:

- a local copy that the archive tool can re-read now; or
- an external attestation containing a verifier identity, evidence URI, fault domain, verification
  time, and the expected content identity.

External attestations are declarations of completed provider-side verification. The template does
not fetch provider APIs or treat an upload request as proof of a durable copy.

## Copy policy

Reconstructable items require at least one verified fault domain. An item declared
`reconstructable: false` requires two verified independent fault domains. Multiple paths in the same
fault domain count as one copy for retirement decisions.

Verify an archive at any time:

```bash
uv run researchctl archive verify archives/local/<run-id>.json
```

Verification re-reads local copies and the source run manifest. A missing, corrupt, or mismatched
copy invalidates the archive decision.

## Retirement preflight

```bash
uv run researchctl archive retirement-preflight \
  archives/local/<run-id>.json \
  --target-kind run \
  --target <run-id>
```

Supported target kinds are `run`, `worktree`, `branch`, and `provider`. The command returns
machine-readable `retire_allowed` or `blocked` plus concrete blockers. Worktree retirement also
blocks on uncommitted or untracked files. Run retirement requires the archive run ID to match the
target.

The tool never stops or deletes anything. `stop`, `delete`, and `retire` remain separate actions and
permissions. Even a clean retirement decision records:

```json
{
  "destructive_action_performed": false,
  "next_action_requires_explicit_authorization": true
}
```

Provider-, branch-, volume-, server-, worktree-, and run-deletion operations must be performed by a
separate explicitly authorized mechanism after reviewing the preflight result.

## Local generated state

Default local archive manifests live under ignored `archives/local/`. Large copied artifacts belong
outside the Git repository. Promote only compact reviewed archive evidence when a project needs a
durable audit record.
