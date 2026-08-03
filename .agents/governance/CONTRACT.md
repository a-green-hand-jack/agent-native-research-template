# Project Contract

This file defines durable repository invariants. During template initialization, add the
project-specific behavioral, scientific, and interface contracts below these shared invariants.

## Project-First Invariants

- The functional project is primary; governance exists only to reduce expected project cost.
- Governance is physically contained by `.agents/`, except for the minimal discovery adapter
  `AGENTS.md`.
- New paths belong to the functional unit unless
  `.agents/governance/REPO_UNITS.yaml` explicitly says otherwise.
- Project code, commands, environments, experiments, evaluations, and evidence remain usable
  when `.agents/` is absent.
- Each durable fact, command, configuration value, and behavioral promise has one canonical
  source.
- The core contribution remains locatable even when its supporting substrate is large.
- Generated output never silently becomes source input.

## Sidecar Invariants

- Governance may read project state and invoke declared project commands.
- Governance must not add project imports, runtime environment variables, package dependencies,
  configuration lookups, or execution prerequisites that point into `.agents/`.
- Project verification and governance validation are separate commands. A failed governance
  check must not make the project implementation unusable.
- Hooks must not require the governance sidecar for ordinary project commits.
- Governance writes project files only when the active task explicitly authorizes a functional
  or mixed change.
- Governance artifacts need a reader, trigger, update rule, and retirement path.

## Agent Runtime Invariants

- The agent runtime is an execution surface outside the two tracked repository units. It may
  interpret repository guidance and operate project interfaces, but it is not project truth.
- Repository guidance defines durable project state and constraints. Runtime instructions define
  how the current agent session executes. The active task defines the current requested outcome.
- Runtime safety and capability limits take precedence during execution. They do not silently
  rewrite the repository contract; an unresolved conflict is reported as a constraint or blocker.
- The repository does not require Codex, OMX, a particular model table, hook registry, subagent
  implementation, or team runtime in order to remain usable.
- Tool-generated instruction overlays must use paired, tool-owned markers and preserve the
  canonical repository guidance around them. Applying the same overlay twice must not duplicate
  sections.
- Template-owned temporary coordination state belongs in ignored `.agents/runtime/`.
  Tool-owned ephemeral state, such as `.omx/`, remains in its conventional ignored directory.
- Runtime output becomes durable only through the same review path as human output: accepted
  code, tests, evaluations, reports, decisions, or reviewed memory.

## Template Lifecycle Invariants

- `PROJECT.yaml` records the source template name, template contract version, initialization Git
  commit, and the ordered set of applied migration versions.
- Initialization records provenance once and never treats the source template as a live upstream
  that may overwrite downstream project files.
- Template compatibility checks are explicit and remain part of functional project verification.
- Template migrations are forward-only, sequential, repository-reviewed code changes. A migration
  runs only when explicitly requested; missing migration implementations are blockers rather than
  permission to perform an implicit best-effort rewrite.
- Applying the current template version is a no-op. Future migrations update the migration ledger
  only after their declared changes complete and the resulting project passes compatibility checks.

## Change Integration Invariants

- Pull-request validation must run on the `pull_request` event under read-only top-level workflow
  permissions. External Actions are pinned to immutable full commit SHAs.
- Every merge cites a successful GitHub Actions run or commit status attached to the exact pull
  request head SHA being merged. A historical run for an ancestor, another branch, or a stale base
  is not merge evidence.
- Any head movement, including a rebase, conflict resolution, generated lockfile update, bot commit,
  or manual edit, invalidates prior merge evidence and requires a new successful check.
- Merge operations use an expected head SHA so concurrent changes are rejected rather than merged
  implicitly.
- Local validation supplements the exact-head remote check; neither passing local tests nor passing
  CI grants merge permission. Explicit authorization remains an independent side-effect gate.
- Pull requests record the related issue, tested head SHA, validation commands, Actions run or
  commit status, Contract/Anatomy assessment, migration or rollback plan, and remaining risks.

## Execution Invariants

- The installed project CLI is the only public experiment and archive control surface. Its name is
  recorded in `PROJECT.yaml` and may be replaced atomically during initialization. Legacy
  `tools/*.py` entry points are compatibility adapters, not independent implementations.

- A runnable experiment resolves its code revision, config, environment, structured inputs,
  executor, and evaluation protocol.
- Every experiment has exactly one command source per phase. Evaluation definitions describe
  extraction and interpretation only; they never duplicate execution commands. Top-level
  commands are a legacy one-phase shorthand and cannot coexist with explicit phases.
- Parsed configuration and declared executor environment policy are embedded in every
  deterministic plan. The runner builds a minimal environment from explicit values and a
  reviewed inheritance allowlist; it never copies the complete host environment.
- Every execution is preceded by a deterministic, side-effect-free plan. The plan records a
  protocol ID, run class, observation status, scientific parameters, stable matrix cells,
  resource controls, commands, declared inputs and artifacts, recovery policy, and completion
  criteria. Canonical JSON supplies the plan SHA-256 recorded in run evidence.
- Formal runs require an explicit pre-observation protocol. Post-observation analyses remain
  traceable but cannot be relabeled as formal pre-observation evidence.
- Expensive runs begin from a committed checkpoint whenever practical.
- A run records its Git revision, dirty patch state, resolved config, environment identity,
  structured input identities, seed, executor, hardware, timestamps, metrics, artifact references,
  and termination reason.
- Logical assets have stable registry IDs and roles. Experiments name logical requirements,
  executor profiles bind physical `path`, `uri`, or `opaque` records, and side-effect-free
  preflight validates role, phase, access, type, size, checksum, path, and overwrite rules.
  Scientific plan identity excludes physical bindings; run evidence records their resolved hash.
- Generation preflight never exposes evaluation-only assets. Reading assets requires verified
  presence and content identity; write targets may be planned but immutable outputs cannot be
  overwritten.
- New runs resolve generic `path`, `uri`, and `opaque` input declarations before execution.
  Repository path inputs receive deterministic content hashes and participate in replay drift
  checks; URI and opaque identities are recorded without network access or implicit verification.
- The legacy free-form `data` field remains readable for old run manifests but is not the
  reproducibility boundary for new template runs. Opaque identities must never contain secrets,
  personal data, private paths, or access tokens.
- Versioned experiment, environment, executor, and evaluation definitions validate against their
  Draft 2020-12 schemas before cross-file resolution. Generated run manifests and reviewed
  evidence envelopes validate against their schemas before they are written or accepted.
- JSON Schema owns single-document structure and nested variants. Python validation owns global
  identifier uniqueness, repository paths, file existence, cross-document references, command
  agreement, input hashing, execution controls, drift detection, and artifact checksums.
- The canonical runner executes a deterministic acyclic phase graph. Specs without phases are
  one `main` phase. Every phase writes an immutable terminal result and output snapshots; failed
  dependencies make downstream phases explicitly incomplete.
- Phase retry creates a child run, verifies the parent and current inputs, reuses only successful
  verified dependency snapshots by hash, records recovery lineage, and never overwrites a parent.
- `tools/evidence.py` is the canonical bounded local runner. It executes exactly one fixed seed,
  exposes that seed as `RESEARCH_SEED`, requires and enforces a positive wall-time limit, and
  accepts only a one-run stopping rule.
- Multi-seed, range, random, cost-accounted, or metric-driven execution requires an external
  scheduler. Unsupported controls are rejected before the local command starts; each externally
  scheduled attempt still creates a separate run.
- Declared artifacts are copied into the owning `runs/<run-id>/artifacts/` directory before their
  checksums are recorded. The manifest retains the original source path for provenance, while
  verification reads the run-scoped snapshot.
- Run lifecycle is evidence-first. Atomic progress records may be planned, submitted, or
  running. Only a validated terminal result may be failed, incomplete, or succeeded; verified
  is a read-only projection after manifest and artifact verification. Missing or corrupt
  terminal evidence never implies success.
- Completion criteria require declared artifacts, metrics, and terminal phase results in
  addition to process return codes. Status and results commands read recorded evidence only;
  they never infer completion from process disappearance or hardware idleness.
- Run facts are immutable. Retries create new runs linked to their parent.
- New metric evidence uses contextual observations, never bare ambiguous scalars. Measured
  values record unit, sample count, aggregation, resource mode, and independent observation
  count. Missing values use explicit reasons and remain distinct from zero. NaN and infinity
  are invalid durable evidence; dispersion requiring repeated observations is rejected when
  fewer than two observations exist.
- Archives inventory immutable run artifacts and read-only logical assets by content identity.
  A checksum declaration alone is not a verified copy: local copies must be re-read, and
  external copies require a verifier identity plus a durable evidence URI.
- Reconstructable items require at least one verified fault domain. Non-reconstructable items
  require two verified independent fault domains before retirement may be considered.
- Stop, delete, and retire are separate actions and permissions. Archive verification and
  retirement preflight are read-only decisions; they never delete runs, worktrees, branches,
  providers, servers, or volumes. Destructive action always requires separate authorization.
- Accepted reports cite run IDs; paper values are generated from locked evidence rather than
  copied from terminal output.

## Worktree Invariants

- One worktree has one bounded intent and one active controller.
- Control mode is per worktree: `mediated` through the main agent or `direct` from the human.
- Different worktrees may use different modes concurrently.
- The human or main agent may create a worktree; creation gives no permanent authority.
- Control may switch after a coherent checkpoint. The receiving agent inspects Git state and any
  runtime handoff before writing.
- Parallel writers use separate worktrees and non-overlapping ownership scopes.
- A direct worktree agent may report to the human without routing through the main agent.
- The assigned integration owner validates and combines completed work; the main agent is the
  default integration owner, not an unavoidable communication bottleneck.
- Repository handoffs and tool runtime state are local coordination data, not durable project
  knowledge.

## Environment And Infra Invariants

- Incompatible baselines or workloads use isolated environments.
- Project configuration refers to logical executor and storage names rather than private
  machine-specific paths.
- Secrets and private infrastructure values remain in ignored overrides, encrypted files, or a
  secret manager.
- Large datasets, checkpoints, caches, and raw logs are not committed to Git.

## Governance Change Rules

- `.agents/governance/ANATOMY.md` changes when component topology or dependency direction changes.
- `.agents/governance/CONTRACT.md` changes when promised behavior or result validity changes.
- `.agents/governance/GUIDE.md` changes when a stable operating procedure changes.
- `AGENTS.md` changes only when discovery, mandatory orientation, or control routing changes.
- `.agents/governance/REPO_UNITS.yaml` changes when a durable ownership boundary changes.

## Project-Specific Contract

Replace this section during project initialization with:

- externally observable behavior;
- scientific claims currently under test;
- input and output schemas;
- numerical or statistical validity requirements;
- compatibility constraints;
- explicit non-goals.

## Completion Contract

A change is acceptable only when its relevant implementation, validation evidence, and durable
documentation agree. Passing tests cannot excuse a violated contract, and prose cannot excuse a
failing executable check.
