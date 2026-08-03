# Deterministic Experiment Plans

An experiment specification is human-maintained intent. A plan is the normalized, machine-readable
projection that is reviewed before execution and embedded in run evidence.

Generate a plan without running the experiment:

```bash
uv run researchctl experiment plan experiments/specs/<name>.yaml
```

The command prints canonical JSON containing a SHA-256 identity and the complete resolved plan. It
loads and validates repository definitions but does not invoke phase commands or create a run
directory.

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

The plan embeds the complete parsed configuration under `effective_config` together with its
repository path and SHA-256. Consequently:

- changing configuration content changes the plan identity;
- changing only YAML key order does not change the plan identity;
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

## Protocol identity

Every plan records:

- a stable `protocol_id`;
- a `run_class`: `smoke`, `pilot`, `partial`, `reference`, `formal`, or `post_observation`;
- an `observation_status`: `pre_observation` or `post_observation`;
- scientific parameters and deterministic matrix cells;
- effective configuration, declared environment policy, inputs, assets, phases, artifacts, budget,
  stopping rule, recovery policy, and completion criteria.

A formal run requires an explicit protocol ID and must be declared before observing the result.
Post-observation analysis is allowed, but it is never mislabeled as a formal pre-observation run.

## Matrix identity

Matrix keys are sorted, declared value order is preserved, and the Cartesian product is expanded in
a stable order. Each cell receives an ID derived from the canonical JSON of its full parameter set.
Duplicate declared values or duplicate expanded cells are rejected.

The built-in local runner still executes one bounded cell. A plan may describe a larger matrix for
review or an external scheduler, but `researchctl experiment run` rejects plans with more than one
cell. Each externally scheduled cell must produce its own run manifest.

## Evidence boundary

New run manifests include the exact resolved plan and its SHA-256. Changing key order does not
change identity; changing protocol, parameters, matrix values, effective configuration, phase
commands, environment policy, inputs, or completion semantics does.

Review and automation should compare the plan SHA-256 rather than relying on file names or prose
summaries. A changed plan hash requires a new execution decision and new run evidence.
