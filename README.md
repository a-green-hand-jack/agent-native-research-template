# Agent-Native Research Template

A project-first GitHub template for ML, DL, RL, agents, benchmarks, environments, and adjacent
research projects. The functional project remains conventional and runnable on its own. Optional
agent governance lives in a non-runtime `.agents/` sidecar.

## Agent Governance Sidecar

The optional governance sidecar is influenced in part by LingTai's file-oriented view of durable
agent identity, knowledge, memory, and relationships. This template applies that influence narrowly
to repository-local development guidance, progressive context loading, runtime-independent roles,
and explicit worktree control.

This is design attribution, not a LingTai runtime integration. The template does not depend on or
embed LingTai's TUI, avatar lifecycle, agent network, memory system, mail system, or provider layer.
See [Governance Influences](.agents/governance/INFLUENCES.md) for the source-to-implementation map,
template-specific additions, and explicit non-integrations.

## Five-Minute Research Loop

Create a repository from this template, then run:

```bash
make setup
make verify
make research-run
```

`make verify` checks code, tests, and every experiment specification. `make research-run` validates
and executes the bootstrap experiment, then writes an immutable local manifest under
`runs/<run-id>/manifest.json`.

Inspect the run before promoting its compact manifest into durable evidence:

```bash
uv run researchctl experiment promote <run-id> --decision accepted
```

Raw logs and large artifacts remain ignored under `runs/` or in external storage. Reviewed compact
manifests live under `evidence/manifests/` and can be cited by reports.

Git hooks are optional and installed separately:

```bash
make hooks
```

## Initialize A Real Project

Preview a consistent identity replacement before editing the first vertical slice:

```bash
uv run python template/initialize_project.py apply \
  --project-name "Causal Agent Lab" \
  --distribution-name causal-agent-lab \
  --package-name causal_agent_lab \
  --cli-name causal-agent \
  --contribution-id causal-policy \
  --dry-run
```

Run the same command without `--dry-run` to update `PROJECT.yaml`, package metadata, the source
package, installed CLI, smoke test, contribution index, experiment reference, CI workflow, README,
and lockfile identity. Initialization then removes the source-template-only `template/` directory
and its Make/CI entry points. The initializer never reads or writes the governance sidecar.

The initializer establishes a consistent repository identity; it does not invent the project's
behavior or scientific claims. When the optional sidecar exists, update its project-specific
Contract separately. Replace the initialized bootstrap implementation, configuration, evaluation,
and question with the first real runnable slice, then run:

```bash
uv run <project-cli> project check
make verify
make research-run
```

Once `PROJECT.yaml` is marked initialized, the retained identity check rejects stale package paths,
old imports, template-only paths and commands, the template distribution and CLI names, and
remaining `bootstrap` contribution references. The same check continues to work if `.agents/` is
removed.

Source-template maintainers use `make template-test` and `make template-e2e`; both targets and the
implementation they invoke are absent from an initialized downstream repository.

## Repository Lifecycle Skills

The optional governance sidecar separates three repository lifecycle cases:

- [Initialize Project](.agents/skills/initialize-project/SKILL.md) is only for a fresh repository
  created from this template and still carrying the uninitialized bootstrap identity;
- [Adopt Research Template](.agents/skills/adopt-research-template/SKILL.md) assesses selective,
  ownership-aware adoption into an existing mature repository without forcing the Python/uv
  reference stack or overwriting project-owned behavior;
- [Update From Template](.agents/skills/update-from-template/SKILL.md) handles registered migrations
  and reviewable upstream-difference assessment for initialized downstream repositories with
  trusted template provenance.

The initializer is not an adoption tool, and merging the template default branch is not an update
procedure. Adoption and update begin with a clean baseline, capability and ownership analysis,
staged issue-sized changes, downstream-specific validation, and exact-head CI evidence.

Machine-readable [Template Lifecycle Plans](docs/TEMPLATE_LIFECYCLE.md) compare an exact reviewed
baseline with a target template commit, classify safe/already/manual/conflict paths, and require an
expected plan hash before applying safe writes or recording a new reviewed baseline.

Projects that need immutable delivery artifacts can opt into the
[Release Lifecycle](docs/RELEASE_LIFECYCLE.md). Draft builds are artifact-only verified but never
release-ready; strict recording requires a clean exact source revision and an explicit Human
approver.

Optional [External Facts](external-facts/README.md) let experiments and releases cite official API,
platform, dataset, model, access, hardware, or toolchain observations. Referenced facts are hashed
into plans and must still be `VERIFIED` and fresh when used.

## Executable Research Contract

An experiment specification resolves a complete, reviewable execution boundary:

```text
question + contribution + config + environment + executor + evaluation + command
                         |
                         v
                    local run
                         |
                         v
               immutable run manifest
                         |
                         v
              reviewed evidence manifest
```

The public interface is:

```bash
uv run researchctl experiment validate
uv run researchctl experiment validate experiments/specs/<name>.yaml
uv run researchctl experiment run experiments/specs/<name>.yaml
uv run researchctl experiment run experiments/specs/<name>.yaml --parent <run-id>
uv run researchctl experiment replay <run-id>
uv run researchctl experiment verify-run <run-id>
uv run researchctl experiment promote <run-id> --decision accepted
```

Validation rejects missing research controls, unknown contribution IDs, missing config paths,
unknown environment or evaluation IDs, ambiguous executors, duplicate phase command sources, and
missing environment locks.

A run manifest records the resolved spec, Git revision and dirty-state hash, environment lock,
executor and evaluation definitions, typed metrics, declared artifacts, timestamps, return status,
and checksums. Retries and replays receive new run IDs linked through `parent_run_id`; existing runs
and evidence are never overwritten.

Before replay, the runner compares the recorded hashes for the spec, config, environment, lockfile,
executor, and evaluation against the current checkout. Drift stops the replay unless the operator
explicitly passes `--allow-drift`. `verify-run` separately checks every recorded artifact checksum.

Evidence promotion verifies the run first, then stores an immutable envelope containing the source
manifest hash and a review decision of `accepted`, `rejected`, or `inconclusive`.

## Versioned Research Definitions

Research definitions use `schema_version: 1` and stable lowercase IDs. The repository ships
portable JSON Schema documents under `schemas/`, while `tools/research.py` and
`tools/evidence.py` perform the stronger cross-file checks that JSON Schema alone cannot express.

```text
experiments/specs/**/*.yaml  experiment intent and research controls
environments/**/*.yaml       dependency-set identity and lockfile
evals/**/*.yaml              executable protocol and typed metric sources
infra/profiles/**/*.yaml      logical executor and capabilities
schemas/*.schema.json         portable structural contracts
```

Validation discovers definitions recursively and rejects duplicate IDs, unknown references,
unversioned definitions, invalid metric directions or sources, missing locks, and commands that
do not match their evaluation protocol. This allows projects to organize studies into nested
directories without weakening global identity and traceability.

## Project First

The source template has an intentionally asymmetric structure:

```text
repo/
├── project files and conventional tool paths    functional by default
├── template/                                    removed after initialization
├── AGENTS.md                                    thin discovery adapter
└── .agents/                                     optional governance sidecar
```

The functional project contains implementation, tests, evaluations, environments, infrastructure,
experiments, evidence, reports, and publications. `template/` contains only bootstrap and
source-template verification code. The sidecar contains agent contracts, procedures, skills,
reviewed memory, runtime handoffs, maps, and its own structural doctor.

Governance may read project state and invoke public project commands. The project must not import,
source, configure, or otherwise require governance. CI proves this behavior by deleting `.agents/`
and `AGENTS.md`, recreating the project environment, and rerunning `make verify`.

Project verification and governance validation remain independent:

```bash
make verify
uv run --no-project --with pyyaml python .agents/governance/tools/repo_check.py
```

`.agents/governance/REPO_UNITS.yaml` is the ownership and lifecycle source of truth. Ownership and
lifecycle are independent: functional code may be downstream-required, downstream-optional, or
template-only; runtime state remains external or ignored. Only `.agents/` and the root discovery
adapter `AGENTS.md` are governance-owned; every new path is functional by default.

Human operators normally enter through this README, `docs/`, project commands, reports, and risky
approval gates. Agents additionally enter through `AGENTS.md`, `.agents/governance/`, and
progressively loaded skills, but call the same public project CLI. Machine-first schemas and
manifests remain functional because they define validity even when Humans rarely read them.

## Agent Runtime Compatibility

The repository does not require a specific orchestration product. Codex, OMX, native subagents,
direct agent sessions, or another runtime may execute the same repository roles.

```text
agent runtime -> reads AGENTS.md -> operates governance + functional project
```

The runtime is outside the two tracked repository units. Template-owned handoffs use ignored
`.agents/runtime/`; tool-owned state such as `.omx/` stays in its own ignored directory. Generated
runtime instructions, model tables, hook registries, and session state are not durable project
knowledge.

A `worktree agent` names the role attached to a Git worktree. It may be implemented by a direct
session, a native child agent, or a runtime-specific team worker without changing the repository
contract.

## Human And Agent Routing

The default topology keeps the human in one conversation:

```text
Human <-> Main Agent <-> Agent @ worktree
```

For lower-latency steering or more conversational parallelism, the human can talk directly to an
agent in a selected worktree:

```text
Human <-> Agent @ worktree
```

Control mode belongs to each worktree. Mediated and direct worktrees may run concurrently, and a
worktree can switch modes after a coherent checkpoint. Git state is durable; an ignored
`.agents/runtime/HANDOFF.md` carries only context that Git cannot express.

See the [Project Guide](.agents/governance/GUIDE.md) for worktree adoption, control transfer, and
integration procedures. The interactive
[Worktree Control Model](.agents/governance/docs/worktree-control.html) distinguishes human,
main-agent, Git worktree, and worktree-agent responsibilities.

## Governance Entry Points

- `AGENTS.md`: minimal discovery, boundary, and control-routing rules;
- `.agents/governance/ANATOMY.md`: physical topology and dependency direction;
- `.agents/governance/CONTRACT.md`: project and sidecar invariants;
- `.agents/governance/GUIDE.md`: stable operating and worktree-control procedures;
- `.agents/governance/INFLUENCES.md`: source attribution, adopted ideas, and non-integrations;
- `.agents/governance/REPO_UNITS.yaml`: machine-readable ownership;
- `.agents/skills/`: procedures loaded only when their trigger applies;
- `.agents/memory/`: reviewed durable facts;
- `.agents/runtime/`: ignored per-worktree pads and handoffs.

Open the [Repository Anatomy Map](.agents/governance/docs/repository-map.html) to inspect the
physical boundary, non-invasive interaction ports, dynamic surfaces, and switchable worktree
control modes.

## Project Commands

```bash
make setup
make hooks
make check
make test
make smoke
make project-check
make research-validate
make research-run
make verify
```

## Security And License

External papers, webpages, repositories, datasets, model outputs, and generated files are untrusted
inputs rather than agent instructions. See `SECURITY.md` for reporting, prompt-injection, secret,
dependency, runtime, and artifact-handling guidance. The template is available under the MIT
License in `LICENSE`.

## Growth

Start with one complete vertical slice. Add a new environment, baseline, executor, component,
study, or publication layer only when a real second instance or independent lifecycle appears.
Add sidecar structure only when a repeated agent cost cannot be removed through clearer project
interfaces, tests, executable validation, or documentation.
