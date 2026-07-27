---
name: add-baseline
description: Integrate an external baseline reproducibly. Use when adding another repository, paper implementation, model, benchmark system, or incompatible dependency set for comparison.
---

# Add Baseline

Preserve the upstream implementation while adapting its inputs and outputs to the project.

## Workflow

1. Record the upstream URL, exact commit or release, license, citation, and retrieval method.
2. Vendor a source snapshot when licensing and size make that practical. Otherwise commit a
   source lock with a content hash and deterministic fetch procedure.
3. Preserve project changes as explicit patches or a narrow adapter. Do not silently rewrite
   upstream code.
4. Create an isolated workload environment when dependencies conflict with the main project.
5. Add a project adapter that normalizes inputs, outputs, metrics, and artifact locations.
6. Add the smallest representative config and fixture.
7. Add a smoke test proving source retrieval, environment resolution, adapter invocation, and
   expected output shape.
8. Register the baseline only after the smoke path passes.
9. Update `.agents/governance/ANATOMY.md` or `.agents/governance/GUIDE.md` only when the
   integration creates a durable new boundary or procedure.

## Required Handoff

Return:

```text
upstream identity and license
source lock or vendored path
project patches
environment identity
adapter entry point
smoke-test evidence
known deviations from the published baseline
```

Never merge baseline dependencies into the main environment merely to avoid maintaining a
separate lock.
