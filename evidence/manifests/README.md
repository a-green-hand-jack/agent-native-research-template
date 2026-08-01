# Evidence Manifests

This directory contains reviewed, compact run manifests promoted from ignored local runs.

A normal execution writes raw logs and a manifest under `runs/<run-id>/`. After inspecting the
run, promote its manifest with:

```bash
uv run python tools/research.py promote <run-id>
```

Promoted manifests are immutable evidence records. A retry or corrected execution receives a new
run ID and a new manifest rather than replacing an existing record.

Keep large logs, datasets, checkpoints, and generated artifacts under `runs/` or external artifact
storage. A promoted manifest records their repository-relative references and checksums; it does
not make those large artifacts suitable for Git.
