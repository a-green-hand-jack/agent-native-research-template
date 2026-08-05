# Reference Implementation Scope

The repository separates a broadly reusable research contract from one deliberately concrete
functional implementation.

## Portable Contract

These ideas are intended to remain useful across languages and execution stacks:

- project-first ownership with an optional governance sidecar;
- versioned experiment, environment, executor, evaluation, run, and evidence contracts;
- explicit initialization, template provenance, and reviewed migrations;
- bounded attempts, immutable run facts, artifact snapshots, replay provenance, and reviewed
  evidence promotion;
- a stable project workload command boundary with per-phase protected-file mutation detection;
- one canonical source for each durable fact and one canonical executable path for each promise.

Projects may replace the supplied language, package manager, test runner, build system, or local
executor while preserving those contracts.

## Supplied Functional Stack

The checked-in reference implementation targets:

- CPython 3.11 or newer;
- uv for Python installation, dependency locking, environments, and command execution;
- Hatchling for packaging;
- Pytest for tests;
- Ruff for linting and formatting;
- GNU Make and POSIX shell commands for the public local interface;
- Ubuntu GitHub-hosted runners as the continuously verified operating-system surface.

CI verifies the minimum supported Python version and a current stable Python version. It does not
claim native Windows or macOS shell compatibility. Projects requiring those platforms should add
platform-native command adapters and CI jobs before claiming support.

The supplied source guard is not a container or kernel capability boundary. Workload code can read
the executable source it needs; mutations to protected project paths are detected and fail the run,
but are not automatically reverted.

## Changing The Stack

A stack change is complete only when it updates the public commands, lock and environment model,
initializer, real-template E2E check, CI, documentation, and any affected Contract promises. Do not
retain Python-specific files merely to satisfy the template if the downstream project intentionally
adopts another stack; replace the functional reference implementation coherently while keeping the
optional governance boundary non-invasive.
