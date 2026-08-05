---
name: validate-external-facts
description: Refresh official-source observations and validate every experiment or release that consumes them.
---

# Validate External Facts

Use this skill when an experiment or release depends on time-sensitive external platform, API,
dataset, model, access, hardware, or toolchain facts. Facts are functional project evidence under
`external-facts/`; this skill only owns the refresh and review procedure.

## Refresh

Open the official HTTPS source, update the relevant fact's observed fields, `checked_at`,
`valid_until`, status, and scope, and review the resulting content diff. Never copy credentials,
private paths, personal data, or access tokens into a fact record.

## Validate Consumers

Use the public project interfaces that consume the facts:

```bash
uv run researchctl experiment validate
uv run researchctl release validate RELEASE.yaml
```

Run only the applicable command when the project has no release configuration. A stale or changed
fact invalidates an earlier plan or draft; do not silently refresh an existing evidence identity.
