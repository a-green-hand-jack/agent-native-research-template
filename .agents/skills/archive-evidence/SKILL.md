---
name: archive-evidence
description: Create and verify durable archive evidence, then perform a non-destructive retirement preflight.
---

# Archive Evidence

Use this skill after a run is verified and its retained artifacts need durable copies. The skill
owns sequencing, review gates, and interpretation; the project CLI owns all archive validity.

## Verify The Source

Record the run ID, classify every item as reconstructable or non-reconstructable, and verify the
run before copying anything:

```bash
uv run researchctl experiment verify-run <run-id>
```

## Create And Verify

Create the manifest with explicit copy locations and fault domains, then re-read every local copy:

```bash
uv run researchctl archive create <run-id> --output archives/local/<run-id>.json <copy-options>
uv run researchctl archive verify archives/local/<run-id>.json
```

Do not treat a declared checksum as a verified copy. External copies require a verifier identity
and durable evidence URI.

## Retirement Decision

Run the read-only decision separately:

```bash
uv run researchctl archive retirement-preflight archives/local/<run-id>.json
```

This command never deletes a run, worktree, branch, provider, server, or volume. Destructive
retirement requires separate Human authorization after the required independent fault domains are
verified.
