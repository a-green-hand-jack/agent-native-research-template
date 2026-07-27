# Repository Evolution

These diagrams show changes in emphasis, not a sequence where earlier versions lack necessary
execution support. Even the first useful project state must close the loop across contribution,
existing substrate, environment, data, executor, and evaluation.

The stable logical model is:

```text
contribution + substrate + execution context + evaluation = reproducible result
```

These project-producing surfaces form the functional project. The governance sidecar observes
them through public interfaces and supplies orientation, constraints, coordination, validation,
and maintenance without becoming a dependency of the result.

Physical structure grows when an object becomes plural, shared, expensive, or independently
versioned.

The interactive [current repository map](repository-map.html) labels the concrete template
paths as governance or functional. The diagrams below describe how those paths become necessary
over time rather than replacing that ownership map.

## Visual Contract

Each image has one bounded semantic responsibility. Do not infer directory ownership or control
authority from an image whose scope is functional evolution.

| Image | It explains | It does not define |
|---|---|---|
| V0 | Minimum complete functional slice | Governance or agent routing |
| V1 | Non-invasive `.agents/` sidecar | Worktree control topology |
| V2 | Multiple functional environments, baselines, data, and executors | Governance ownership |
| V3 | Experiment intent, immutable facts, evaluation, and reports | Agent coordination |
| V4 | Contribution-to-evidence-to-publication traceability | A specific ML architecture |
| Governing overview | External agent runtime, control modes, sidecar boundary, and delivery | Exact directory inventory or runtime implementation |

The exact repository and agent-runtime boundary lives in
[Repository Anatomy](repository-map.html). The exact human, main-agent, worktree, and
worktree-agent authority model lives in
[Worktree Control Model](worktree-control.html).

## V0: One Complete Vertical Slice

![V0 complete vertical slice](images/repo-evolution-v0.png)

The implementation surface is small and the core contribution is easy to see, but a useful
result still closes the loop through existing substrate, environment, data, executor, and
evaluation. The contribution is prominent without being depicted as sufficient by itself.

At this stage, a singleton may remain inline:

```text
environment.lock
infra.yaml
experiment.yaml
```

## V1: Non-Invasive Agent Sidecar

![V1 non-invasive agent sidecar](images/repo-evolution-v1.png)

The repository gains a thin `.agents/` sidecar beside an independently executable project
feedback loop:

- bounded tasks;
- code, tests, and evaluations;
- ignored runtime notes and handoffs;
- reviewed durable knowledge.

Temporary runtime notes become memory only after review. The sidecar may read and invoke project
interfaces, but project verification remains usable without it.

## V2: Infrastructure And Multiple Environments

![V2 infrastructure and multiple environments](images/repo-evolution-v2.png)

Singleton descriptions become explicit collections only after the project gains incompatible
workloads, external baselines, multiple executors, or shared data:

```text
environment.lock -> environments/<id>/
infra.yaml        -> infra/profiles/ + executors/ + storage/
source.lock       -> baselines/<id>/
```

A stable command surface resolves logical names into runtime-specific values. Experiments do not
scatter server paths or merge incompatible dependencies into one environment.

This image describes functional execution structure. It does not place `infra/`, `data/`, or
environment definitions inside governance.

## V3: Experiment Traceability

![V3 experiment traceability](images/repo-evolution-v3.png)

As runs become expensive, parallel, or citable, the repository separates:

```text
experiment spec -> resolved run -> artifacts -> evaluation -> report
```

The spec is intent, the run manifest is fact, and the report is interpretation. Retries create
new immutable runs instead of overwriting history.

## V4: Scientific Narrative And Publication

![V4 scientific narrative and publication](images/repo-evolution-v4.png)

Engineering complexity can grow while the domain-general core contribution remains visible. A
contribution index links code and parameters through study definitions, run manifests, locked
evidence, accepted claims, and publication outputs.

Raw runs remain available for audit, but papers and human-facing reports consume curated,
traceable evidence rather than terminal logs or copied metrics.

## The Governing Loop

![Agent-native project governance](images/agent-native-project-governance.png)

The overview shows both control modes. In mediated mode the human talks through a main agent. In
direct mode the human talks to a selected worktree-agent. Modes are per worktree, can coexist,
and can switch after a checkpoint. Either human or main agent may create the worktree; creation,
active control, and integration ownership remain separate decisions.

The external agent runtime may instantiate the main-agent and worktree-agent roles through direct
sessions, native child agents, or a runtime-specific team surface. The same image also shows the
non-invasive sidecar boundary and the delivery path from checkpoint through optional handoff,
integration, verification, and validated outcome. Exact runtime and transfer rules remain in the
two interactive HTML maps.

The template should evolve only when a repeated project cost justifies a new permanent mechanism.
