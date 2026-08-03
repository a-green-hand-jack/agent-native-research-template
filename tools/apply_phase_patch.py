from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}, found {count}: {old!r}")
    target.write_text(content.replace(old, new), encoding="utf-8")


def replace_between(path: str, start_marker: str, end_marker: str, replacement: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    start = content.index(start_marker)
    end = content.index(end_marker, start)
    target.write_text(content[:start] + replacement + content[end:], encoding="utf-8")


def patch_evidence() -> None:
    replace_once("tools/evidence.py", "import subprocess\n", "")
    replace_once(
        "tools/evidence.py",
        "import input_identity\nimport research\n",
        "import input_identity\nimport phase_graph\nimport research\n",
    )
    replace_once("tools/evidence.py", "TIMEOUT_RETURN_CODE = 124\n", "")
    replace_between(
        "tools/evidence.py",
        "def timeout_text(",
        "def run_once(",
        "",
    )
    new_run_once = '''def run_once(
    spec_path: Path,
    root: Path = ROOT,
    *,
    retry_phase: str | None = None,
    parent_manifest: dict[str, Any] | None = None,
) -> tuple[Path, int]:
    resolved = validate_supported_spec(spec_path, root)
    spec = resolved["spec"]
    seed = resolved["seed"]
    timeout = resolved["timeout"]
    git = research.git_state(root)
    head_label = (git["commit"] or "nogit")[:8]
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}-{spec['id']}-{head_label}-{uuid.uuid4().hex[:8]}"
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    environment = os.environ.copy()
    environment[SEED_ENVIRONMENT_VARIABLE] = str(seed)
    started_at = utc_now()
    execution = phase_graph.execute_phases(
        spec,
        resolved["executor"],
        resolved["argv"],
        root,
        run_dir,
        environment,
        timeout,
        retry_phase=retry_phase,
        parent_manifest=parent_manifest,
    )
    finished_at = utc_now()
    return_code = execution["return_code"]

    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    stdout_path.write_text(execution["stdout"], encoding="utf-8")
    stderr_path.write_text(execution["stderr"], encoding="utf-8")

    def relative(value: Path | None) -> str | None:
        return research.relative_name(value, root) if value is not None else None

    manifest = {
        "schema_version": research.SCHEMA_VERSION,
        "run_id": run_id,
        "parent_run_id": None,
        "status": "succeeded" if return_code == 0 else "failed",
        "started_at": started_at,
        "finished_at": finished_at,
        "return_code": return_code,
        "termination": execution["termination"],
        "seed": seed,
        "seed_environment_variable": SEED_ENVIRONMENT_VARIABLE,
        "question": spec["question"],
        "contribution": spec["contribution"],
        "plan": {
            "sha256": resolved["plan_sha256"],
            "resolved": resolved["plan"],
        },
        "config": {
            "path": relative(resolved["config_path"]),
            "sha256": research.sha256_file(resolved["config_path"]),
        },
        "data": spec.get("data"),
        "inputs": resolved["inputs"],
        "asset_bindings": resolved["asset_preflight"],
        "spec": {
            "path": relative(resolved["spec_path"]),
            "sha256": research.sha256_file(resolved["spec_path"]),
            "resolved": spec,
        },
        "git": git,
        "environment": {
            "id": spec["environment"],
            "definition": relative(resolved["environment_path"]),
            "definition_sha256": research.sha256_file(resolved["environment_path"]),
            "lockfile": relative(resolved["lockfile_path"]),
            "lockfile_sha256": research.sha256_file(resolved["lockfile_path"]),
        },
        "executor": {
            "id": spec["executor"],
            "definition": relative(resolved["executor_path"]),
            "definition_sha256": research.sha256_file(resolved["executor_path"]),
        },
        "evaluation": {
            "id": spec["evaluation"],
            "definition": relative(resolved["evaluation_path"]),
            "definition_sha256": research.sha256_file(resolved["evaluation_path"]),
        },
        "hardware": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
        },
        "command": resolved["argv"],
        "phases": execution["phases"],
        "recovery": execution["recovery"],
        "metrics": research.extract_return_code_metrics(resolved["evaluation"], return_code),
        "artifacts": [
            {"path": relative(stdout_path), "sha256": research.sha256_file(stdout_path)},
            {"path": relative(stderr_path), "sha256": research.sha256_file(stderr_path)},
            *execution["artifacts"],
        ],
    }
    manifest_path = run_dir / "manifest.json"
    research.validate_document(manifest, "run manifest", manifest_path, root)
    research.write_json(manifest_path, manifest)
    return manifest_path, return_code


'''
    replace_between(
        "tools/evidence.py",
        "def run_once(",
        "def declared_artifacts(",
        new_run_once,
    )
    old_run_spec = '''def run_spec(
    spec_path: Path,
    root: Path = ROOT,
    *,
    parent_run_id: str | None = None,
) -> tuple[Path, int]:
    if parent_run_id is not None:
        parent = verify_run(parent_run_id, root)
        if parent["run_id"] != parent_run_id:
            raise EvidenceError("parent run identity does not match its manifest")
    manifest_path, _ = run_once(spec_path, root)
    return enrich_manifest(manifest_path, root, parent_run_id=parent_run_id)
'''
    new_run_spec = '''def run_spec(
    spec_path: Path,
    root: Path = ROOT,
    *,
    parent_run_id: str | None = None,
    retry_phase: str | None = None,
) -> tuple[Path, int]:
    parent_manifest: dict[str, Any] | None = None
    if parent_run_id is not None:
        parent_manifest = verify_run(parent_run_id, root)
        if parent_manifest["run_id"] != parent_run_id:
            raise EvidenceError("parent run identity does not match its manifest")
    if retry_phase is not None and parent_manifest is None:
        raise EvidenceError("phase retry requires a parent run")
    manifest_path, _ = run_once(
        spec_path,
        root,
        retry_phase=retry_phase,
        parent_manifest=parent_manifest,
    )
    return enrich_manifest(manifest_path, root, parent_run_id=parent_run_id)
'''
    replace_once("tools/evidence.py", old_run_spec, new_run_spec)
    retry_function = '''def retry_phase_run(
    value: str,
    phase: str,
    root: Path = ROOT,
) -> tuple[Path, int]:
    parent = verify_run(value, root)
    drift = recorded_input_drift(parent, root)
    if drift:
        raise EvidenceError("recorded inputs drifted: " + "; ".join(drift))
    return run_spec(
        root / parent["spec"]["path"],
        root,
        parent_run_id=parent["run_id"],
        retry_phase=phase,
    )


'''
    replace_once(
        "tools/evidence.py",
        "def promote_manifest(\n",
        retry_function + "def promote_manifest(\n",
    )
    replace_once(
        "tools/evidence.py",
        "    replay = subparsers.add_parser(\"replay\", help=\"replay a run after checking input drift\")\n"
        "    replay.add_argument(\"run\")\n"
        "    replay.add_argument(\"--allow-drift\", action=\"store_true\")\n\n",
        "    replay = subparsers.add_parser(\"replay\", help=\"replay a run after checking input drift\")\n"
        "    replay.add_argument(\"run\")\n"
        "    replay.add_argument(\"--allow-drift\", action=\"store_true\")\n\n"
        "    retry = subparsers.add_parser(\"retry-phase\", help=\"retry one phase using verified parent outputs\")\n"
        "    retry.add_argument(\"run\")\n"
        "    retry.add_argument(\"--phase\", required=True)\n\n",
    )
    replace_once(
        "tools/evidence.py",
        "        if args.command == \"verify-run\":\n",
        "        if args.command == \"retry-phase\":\n"
        "            path, code = retry_phase_run(args.run, args.phase, root)\n"
        "            print(research.relative_name(path, root))\n"
        "            return code\n"
        "        if args.command == \"verify-run\":\n",
    )
    replace_once(
        "tools/evidence.py",
        "        experiment_plan.PlanError,\n",
        "        experiment_plan.PlanError,\n        phase_graph.PhaseGraphError,\n",
    )


def patch_plan() -> None:
    replace_once(
        "tools/experiment_plan.py",
        "import research\n",
        "import phase_graph\nimport research\n",
    )
    replace_once(
        "tools/experiment_plan.py",
        "    completion_criteria = deepcopy(\n"
        "        spec.get(\"completion_criteria\", {\"required_artifacts\": [], \"required_metrics\": []})\n"
        "    )\n"
        "    plan = {\n",
        "    completion_criteria = deepcopy(\n"
        "        spec.get(\"completion_criteria\", {\"required_artifacts\": [], \"required_metrics\": []})\n"
        "    )\n"
        "    phases = phase_graph.normalize_phases(spec, resolved[\"argv\"])\n"
        "    plan = {\n",
    )
    replace_once(
        "tools/experiment_plan.py",
        "        \"command\": list(resolved[\"argv\"]),\n"
        "        \"seed_policy\": deepcopy(spec[\"seed_policy\"]),\n",
        "        \"command\": list(resolved[\"argv\"]),\n"
        "        \"phases\": phases,\n"
        "        \"seed_policy\": deepcopy(spec[\"seed_policy\"]),\n",
    )


def patch_schemas() -> None:
    experiment_path = ROOT / "schemas/experiment.schema.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    experiment["$defs"]["phase_output"] = {
        "oneOf": [
            {"type": "string", "minLength": 1},
            {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "required": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        ]
    }
    experiment["$defs"]["phase"] = {
        "type": "object",
        "required": ["id", "command"],
        "properties": {
            "id": {"$ref": "#/$defs/identifier"},
            "command": {"$ref": "#/$defs/command"},
            "depends_on": {
                "type": "array",
                "uniqueItems": True,
                "items": {"$ref": "#/$defs/identifier"},
            },
            "asset_phase": {"enum": ["all", "generation", "evaluation"]},
            "timeout_seconds": {"type": "integer", "minimum": 1},
            "outputs": {"type": "array", "items": {"$ref": "#/$defs/phase_output"}},
        },
        "additionalProperties": False,
    }
    experiment["properties"]["phases"] = {
        "type": "array",
        "minItems": 1,
        "items": {"$ref": "#/$defs/phase"},
    }
    experiment_path.write_text(json.dumps(experiment, indent=2) + "\n", encoding="utf-8")

    run_path = ROOT / "schemas/run-manifest.schema.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["required"].insert(run["required"].index("metrics"), "phases")
    run["required"].insert(run["required"].index("metrics"), "recovery")
    termination = run["properties"]["termination"]
    termination["oneOf"].append(
        {
            "type": "object",
            "required": ["reason"],
            "properties": {"reason": {"const": "phase_failed"}},
            "additionalProperties": False,
        }
    )
    run["properties"]["phases"] = {
        "type": "array",
        "minItems": 1,
        "items": {
            "type": "object",
            "required": [
                "id",
                "status",
                "depends_on",
                "asset_phase",
                "command",
                "return_code",
                "started_at",
                "finished_at",
                "termination",
                "asset_bindings",
                "artifacts",
                "errors",
            ],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "status": {"enum": ["succeeded", "failed", "incomplete", "reused"]},
                "depends_on": {"type": "array", "items": {"type": "string"}},
                "asset_phase": {"enum": ["all", "generation", "evaluation"]},
                "command": {"type": "array", "items": {"type": "string"}},
                "return_code": {"type": ["integer", "null"]},
                "started_at": {"type": ["string", "null"]},
                "finished_at": {"type": ["string", "null"]},
                "termination": {"type": "object"},
                "asset_bindings": {"type": "object"},
                "artifacts": {"type": "array", "items": {"$ref": "#/$defs/artifact"}},
                "errors": {"type": "array", "items": {"type": "string"}},
                "source_run_id": {"type": "string"},
            },
            "additionalProperties": False,
        },
    }
    run["properties"]["recovery"] = {
        "type": "object",
        "required": [
            "mode",
            "retry_phase",
            "source_run_id",
            "reused_artifacts",
            "generation_skipped",
        ],
        "properties": {
            "mode": {"enum": ["new_run", "phase_retry"]},
            "retry_phase": {"type": ["string", "null"]},
            "source_run_id": {"type": ["string", "null"]},
            "reused_artifacts": {"type": "array", "items": {"$ref": "#/$defs/artifact"}},
            "generation_skipped": {"type": "boolean"},
        },
        "additionalProperties": False,
    }
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")


def patch_examples() -> None:
    spec_path = ROOT / "experiments/specs/smoke.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["phases"] = [
        {
            "id": "main",
            "command": spec["command"],
            "asset_phase": "all",
            "outputs": [],
        }
    ]
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")


def patch_docs() -> None:
    replace_once(
        ".agents/governance/CONTRACT.md",
        "- `tools/evidence.py` is the canonical bounded local runner. It executes exactly one fixed seed,\n",
        "- The canonical runner executes a deterministic acyclic phase graph. Specs without phases are\n"
        "  one `main` phase. Every phase writes an immutable terminal result and output snapshots; failed\n"
        "  dependencies make downstream phases explicitly incomplete.\n"
        "- Phase retry creates a child run, verifies the parent and current inputs, reuses only successful\n"
        "  verified dependency snapshots by hash, records recovery lineage, and never overwrites a parent.\n"
        "- `tools/evidence.py` is the canonical bounded local runner. It executes exactly one fixed seed,\n",
    )
    replace_once(
        ".agents/skills/run-experiment/SKILL.md",
        "uv run python tools/evidence.py run experiments/specs/<name>.yaml --parent <run-id>\n",
        "uv run python tools/evidence.py run experiments/specs/<name>.yaml --parent <run-id>\n"
        "uv run python tools/evidence.py retry-phase <run-id> --phase <phase-id>\n",
    )
    replace_once(
        ".agents/skills/run-experiment/SKILL.md",
        "Each execution receives a unique run ID and writes an ignored local manifest under\n",
        "Each phase writes `runs/<run-id>/phases/<phase-id>/result.json` plus logs and immutable\n"
        "snapshots. A failed dependency produces explicit `incomplete` downstream results.\n\n"
        "Each execution receives a unique run ID and writes an ignored local manifest under\n",
    )
    units_path = ROOT / ".agents/governance/REPO_UNITS.yaml"
    units = yaml.safe_load(units_path.read_text(encoding="utf-8"))
    required = units["required_paths"]["functional"]
    for path in ("docs/PHASE_RECOVERY.md", "tools/phase_graph.py"):
        if path not in required:
            required.append(path)
    required.sort()
    units_path.write_text(yaml.safe_dump(units, sort_keys=False), encoding="utf-8")


def main() -> None:
    patch_evidence()
    patch_plan()
    patch_schemas()
    patch_examples()
    patch_docs()


if __name__ == "__main__":
    main()
