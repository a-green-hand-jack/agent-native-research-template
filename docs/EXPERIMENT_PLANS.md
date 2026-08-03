# Deterministic Experiment Plans

An experiment specification is human-maintained intent. A plan is the normalized, machine-readable
projection that is reviewed before execution and embedded in run evidence.

Generate a plan without running the experiment:

```bash
uv run researchctl experiment plan experiments/specs/<name>.yaml
```

The command prints canonical JSON containing three independent identity records and their resolved
projections. It loads and validates repository definitions, reads Git state for code identity, but
does not invoke phase commands or create a run directory.

## One command source per phase

Every experiment normalizes to an explicit phase graph. Each phase owns exactly one command.
Evaluation definitions own metric extraction and interpretation only; they do not repeat execution
commands.

A legacy single-command specification may declare a top-level `command`. It is normalized to one
`main` phase. A specification that declares both a top-level command and explicit `phases` is
rejected rather than choosing one implicitly.

This rule prevents a shell command, evaluation definition, and phase graph from becoming competing
sources of execution truth.

## Effective configuration

The execution projection embeds the complete parsed configuration under `effective_config`
together with its repository path and SHA-256. Consequently:

- changing configuration content changes the execution-plan identity;
- changing only YAML key order does not change any identity;
- a reviewer can inspect the values that will be used without reading Python defaults;
- the run manifest records the same resolved configuration.

Values that affect experiment semantics must be represented by the specification, parsed
configuration, or normalized phase commands. They must not exist only in an undocumented shell or
Python default.

## Declared execution environment

Executor profiles declare two environment surfaces:

```yaml
environment:
  PYTHONUNBUFFERED: "1"
inherit_environment:
  - PATH
  - HOME
```

The runner constructs a minimal child environment from those declarations and the reserved
`RESEARCH_SEED` binding. It does not copy the complete host environment.

Explicit values may use `${PROJECT_ROOT}`. Other placeholders are rejected. Inherited variables
must exist at run time. Run evidence records inherited variable names and value hashes rather than
silently copying or exposing their values. Secret-like names and `RESEARCH_SEED` are not valid
profile bindings.

## Layered identities

One hash cannot distinguish a scientific change from an implementation or deployment change. Every
new plan therefore contains three canonical identity records, each with `sha256` and `resolved`:

### Protocol identity

The protocol projection answers whether two runs implement the same scientific protocol. It
contains:

- `protocol_id`, research question, contribution, run class, and observation status;
- scientific parameters, seed policy, matrix, and deterministic cells;
- the evaluation definition and typed metric protocol;
- logical inputs and asset requirements;
- phase IDs, dependency topology, asset phases, and output contracts, but not commands;
- inclusion criteria, recovery policy, and completion criteria.

Changing a scientific parameter, evaluation protocol, seed policy, logical asset role, or phase
topology changes the protocol identity. Changing a command, config value, server, mount, or executor
profile does not.

### Execution-plan identity

The execution projection answers whether the same executable plan will run. It binds the protocol
identity to:

- parsed effective configuration;
- normalized phase commands and timeouts;
- environment definition and lockfile identities;
- Git commit, dirty-state status, and patch identity;
- budget, stopping rule, resolved inputs, declared artifacts, and completion semantics.

Changing configuration content, a phase command, code state, lockfile, budget, or artifact contract
changes the execution-plan identity. Physical profile and asset-binding changes do not.

For one compatibility version, top-level `sha256` and `resolved` remain aliases of
`execution.sha256` and `execution.resolved`. New integrations should read the named identity record.

### Binding identity

The binding projection answers where and under which execution profile the plan is bound. It
contains:

- executor/profile definition;
- explicit and inherited process-environment policy;
- workspace and artifact roots;
- declared physical asset bindings during planning;
- resolved asset preflight records during execution.

Changing only a server path, profile environment policy, workspace root, or physical asset binding
changes the binding identity without rewriting protocol or execution identity. The runner upgrades
the binding projection from `declared` to `resolved` after asset preflight.

## Matrix identity

Matrix keys are sorted, declared value order is preserved, and the Cartesian product is expanded in
a stable order. Each cell receives an ID derived from the canonical JSON of its full parameter set.
Duplicate declared values or duplicate expanded cells are rejected.

The built-in local runner still executes one bounded cell. A plan may describe a larger matrix for
review or an external scheduler, but `researchctl experiment run` rejects plans with more than one
cell. Each externally scheduled cell must produce its own run manifest.

## Evidence and replay boundary

New run manifests record all three identity projections and hashes. Terminal result version 2
copies the three hashes into an `identities` summary. Legacy manifests and result version 1 remain
readable.

Replay recalculates current protocol, execution, and binding identities and reports their drift
separately, in addition to file-level input and asset diagnostics. This lets reviewers distinguish:

- a scientific protocol change that requires a new research decision;
- an executable implementation change that requires a new run;
- a deployment or physical-binding change that affects provenance but not the scientific protocol.

Review and automation should compare the identity layer relevant to the decision rather than relying
on file names, prose summaries, or a single undifferentiated hash.
