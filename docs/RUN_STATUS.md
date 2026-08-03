# Evidence-First Run Status

Process exit, missing processes, idle accelerators, and directory existence are not completion
evidence. Run status is derived only from recorded lifecycle files under `runs/<run-id>/`.

## Lifecycle records

The runner atomically records non-terminal progress in `state.json`:

- `planned`
- `submitted`
- `running`

After phase execution, metric extraction, artifact snapshotting, and completion evaluation finish, it
atomically writes `result.json` with one terminal state:

- `failed`
- `incomplete`
- `succeeded`

`verified` is a read-only projection produced after manifest and artifact verification. Verification
never rewrites historical run facts or the terminal result.

## Commands

```bash
uv run python tools/evidence.py status <run-id>
uv run python tools/evidence.py results <run-id>
uv run python tools/evidence.py verify-run <run-id>
```

`status` prints machine-readable JSON. A missing or corrupt terminal result never becomes success.
The latest recorded progress may remain `planned`, `submitted`, or `running`; these values describe
only the last durable lifecycle transition and do not assert that a process is currently alive. A
manifest without lifecycle evidence is `incomplete`.

`results` combines status with the plan, phase records, metrics, evaluation errors, artifacts, and
recovery lineage. It does not parse terminal logs or infer missing values.

## Completion contract

The plan's `completion_criteria` declares required artifact names and metric IDs. A zero process
return code is insufficient when a required artifact or metric is absent, a phase is incomplete, or
evaluation extraction reported errors. Such a run receives terminal state `incomplete`.

A failed return code or failed phase receives `failed`. A run becomes `succeeded` only when the
execution and completion contract both succeed.

## Atomicity

Lifecycle files use write-to-temporary-plus-rename. A partially written JSON file is invalid
evidence and is reported as incomplete. The terminal result records the SHA-256 of the manifest it
summarizes so verification can detect mismatched evidence.
