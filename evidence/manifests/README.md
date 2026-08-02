# Evidence Manifests

This directory contains compact, reviewed evidence envelopes promoted from local run manifests.
Raw logs, checkpoints, and large artifacts remain under ignored `runs/` paths or external storage.

Promote a run only after its artifact checksums and interpretation have been reviewed. Evidence
verification and promotion belong exclusively to `tools/evidence.py`; `tools/research.py` validates
and executes experiment specifications but does not create durable evidence:

```bash
uv run python tools/evidence.py verify-run <run-id>
uv run python tools/evidence.py promote <run-id> \
  --decision accepted \
  --note "Supports the stated smoke claim."
```

Each evidence file records:

- the source run ID, manifest path, and source-manifest SHA-256;
- the promotion timestamp;
- a review decision: `accepted`, `rejected`, or `inconclusive`;
- an optional review note;
- the complete immutable run manifest.

Do not edit a promoted evidence file in place. A corrected execution receives a new run ID and a
new evidence envelope. Reports should cite the promoted run ID and evidence file hash.
