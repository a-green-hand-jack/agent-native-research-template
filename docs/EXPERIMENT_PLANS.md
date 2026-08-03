# Deterministic Experiment Plans

An experiment specification is human-maintained intent. A plan is the normalized, machine-readable
projection that is reviewed before execution and embedded in run evidence.

Generate a plan without running the experiment:

```bash
uv run python tools/evidence.py plan experiments/specs/<name>.yaml
```

The command prints canonical JSON containing a SHA-256 identity and the complete resolved plan. It
loads and validates repository definitions but does not invoke the experiment command or create a
run directory.

## Protocol identity

Every plan records:

- a stable `protocol_id`;
- a `run_class`: `smoke`, `pilot`, `partial`, `reference`, `formal`, or `post_observation`;
- an `observation_status`: `pre_observation` or `post_observation`;
- scientific parameters and deterministic matrix cells;
- inputs, artifacts, command, budget, stopping rule, recovery policy, and completion criteria.

A formal run requires an explicit protocol ID and must be declared before observing the result.
Post-observation analysis is allowed, but it is never mislabeled as a formal pre-observation run.

## Matrix identity

Matrix keys are sorted, declared value order is preserved, and the Cartesian product is expanded in
a stable order. Each cell receives an ID derived from the canonical JSON of its full parameter set.
Duplicate declared values or duplicate expanded cells are rejected.

The built-in local runner still executes one bounded cell. A plan may describe a larger matrix for
review or an external scheduler, but `tools/evidence.py run` rejects plans with more than one cell.
Each externally scheduled cell must produce its own run manifest.

## Evidence boundary

New run manifests include the exact resolved plan and its SHA-256. Changing key order does not
change identity; changing protocol, parameters, matrix values, resources, commands, inputs, or
completion semantics does.
