---
name: adopt-research-template
description: Assess and stage adoption of selected template capabilities into an existing repository that was not created from this template. Use for mature repositories without trusted template provenance.
---

# Adopt Research Template

Use this skill when an existing repository wants selected capabilities from this template but was
not initialized from it, has no trustworthy `PROJECT.yaml` template provenance, or already has a
mature architecture that must be preserved. Do not run the one-time initializer against such a
repository.

This procedure is plan-first. Reading and producing an adoption assessment do not authorize writes,
issues, pull requests, dependency changes, or workflow changes.

## Establish A Safe Baseline

Before comparing or proposing changes:

1. identify the repository default branch and exact accepted baseline commit;
2. require a clean worktree, or use an isolated worktree whose controller and integration owner are
   explicit;
3. record the language, package manager, build system, test commands, CI provider, release process,
   and currently supported platforms;
4. run the repository's existing decisive verification commands and preserve their results as the
   pre-adoption baseline;
5. inspect current architecture, public interfaces, configuration, experiment workflow, artifacts,
   reports, and governance before loading template files.

Do not infer that a familiar directory name has the same semantics as the template. Existing code,
tests, schemas, workflows, and published behavior are the downstream source of truth.

## Select An Adoption Level

Classify the requested outcome before proposing files:

- **governance-only**: add repository-local guidance, ownership, worktree control, and side-effect
  gates while leaving the functional project unchanged;
- **research-contract-only**: adopt portable schemas, evidence semantics, or planning concepts while
  keeping the repository's current language and execution stack;
- **functional-reference adoption**: adapt the supplied Python/uv/POSIX implementation where the
  downstream stack is compatible and the owner explicitly wants it;
- **full template convergence**: pursue both governance and functional surfaces through multiple
  reviewed phases, not one bulk copy.

The template's contracts are portable; its checked-in implementation is a reference stack. Never
require Python, uv, Make, or the template directory layout merely to adopt a concept.

## Build A Capability Matrix

Compare capabilities, not file names. At minimum assess:

```text
project identity and provenance
repository ownership and governance sidecar
CI exact-head merge evidence
experiment intent and schema validation
effective configuration and environment provenance
protocol, execution-plan, and binding identities
logical assets and input identities
phase execution and recovery
run status and completion evidence
metric observation semantics
reviewed evidence promotion
archive verification and retirement preflight
real-repository initialization or conformance tests
```

For every capability assign exactly one disposition:

- **preserve**: the repository already has an equivalent or stronger implementation;
- **adopt**: the template capability can be introduced without semantic adaptation;
- **adapt**: the capability is useful but needs an adapter to existing commands, data, CI, or
  architecture;
- **skip**: the capability is irrelevant, conflicts with project constraints, or has no justified
  use case.

Record evidence and rationale, for example:

```yaml
capability: exact-head-merge-evidence
disposition: adapt
existing_surface: .github/workflows/ci.yml
proposed_surface: extend existing CI policy rather than replace the workflow
invariant: current release and deployment jobs remain unchanged
validation: existing CI plus a negative exact-head policy test
```

Do not classify a capability as `adopt` merely because its template files can be copied.

## Classify Downstream Ownership

Before any write, classify every proposed path or semantic surface:

- **project-owned**: business logic, scientific methods, existing public APIs, project-specific
  configuration, data contracts, deployment, and release behavior;
- **template-derived**: a new, deliberately adopted surface whose lifecycle the downstream owner
  agrees to track against the template contract;
- **shared/customized**: CI, README, build metadata, command entry points, schemas, or governance
  documents that combine downstream and template responsibilities.

Project-owned files are never replaced by template copies. Shared files require an explicit patch
plan and downstream-specific tests. A path classification is not permanent proof; re-evaluate it
when responsibilities change.

## Produce A Staged Adoption Plan

The assessment must be useful without changing the repository. Return:

```text
selected baseline and pre-adoption validation
repository stack and current capability inventory
preserve/adopt/adapt/skip matrix
path and semantic ownership classification
explicit invariants and non-goals
ordered phases with issue-sized acceptance criteria
validation and rollback for every phase
unresolved decisions and unsupported assumptions
```

Prefer phases that leave a runnable vertical slice after every merge. A typical order is:

1. protect the existing verification baseline;
2. add only the selected governance or contract boundary;
3. adapt one real experiment or evidence path end to end;
4. add conformance and failure-scenario tests;
5. expand only after the first slice is proven.

Do not open all issues at once unless the owner authorizes that side effect and the phases are stable.
Do not create a giant convergence pull request.

## Implement Under Explicit Authorization

For each authorized phase:

1. create an isolated branch or worktree from the recorded accepted baseline;
2. cite the adoption-plan item and its preserve/adapt invariants in the issue and pull request;
3. make the smallest complete change;
4. preserve existing commands or provide an explicit compatibility adapter;
5. run focused tests, the downstream's original verification, and the new capability checks;
6. require successful GitHub Actions or commit status for the exact final PR head;
7. use the expected head SHA for merge and verify branch cleanup.

A green template test suite cannot substitute for the downstream repository's own tests. A copied
smoke example is not evidence that a real downstream workflow was adapted correctly.

## Prohibited Shortcuts

Never:

- run `template/initialize_project.py apply` against a mature non-template repository;
- replace the downstream source tree, README, CI, build metadata, or lockfile wholesale;
- merge or copy the template default branch into the repository as an adoption strategy;
- label project-specific values, claims, metrics, or assets as template defaults;
- add the optional `.agents/` sidecar as a runtime dependency;
- report adoption complete while placeholder examples are the only exercised path.

## Handoff

Return:

```text
repository baseline and worktree state
adoption level
capability matrix with evidence
ownership classification
phases completed and phases still proposed
changed public interfaces or compatibility adapters
validation commands, exact tested head, and remote CI/status
rollback path and residual risks
external side effects performed under authorization
```
