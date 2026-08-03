from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def edit(relative: str, old: str, new: str, *, count: int = 1) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"{relative}: expected {count}, found {actual}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


# Evidence runner: resolve physical bindings, record all identities, and diagnose drift by layer.
edit("tools/evidence.py", "import phase_graph\n", "import phase_graph\nimport plan_identity\n")
edit(
    "tools/evidence.py",
    '''    plan = experiment_plan.build_plan(resolved)
    if len(plan["resolved"]["cells"]) != 1:
        raise EvidenceError(
            "the local runner executes exactly one plan cell; use an external scheduler "
            "for matrix plans"
        )
    preflight = asset_binding.resolve_assets(
        resolved["spec"], resolved["executor"], root, phase="all"
    )''',
    '''    preflight = asset_binding.resolve_assets(
        resolved["spec"], resolved["executor"], root, phase="all"
    )
    plan = plan_identity.resolve_binding(experiment_plan.build_plan(resolved), preflight)
    if len(plan["resolved"]["cells"]) != 1:
        raise EvidenceError(
            "the local runner executes exactly one plan cell; use an external scheduler "
            "for matrix plans"
        )''',
)
edit(
    "tools/evidence.py",
    '''        "plan": plan["resolved"],
        "plan_sha256": plan["sha256"],
        "asset_preflight": preflight,''',
    '''        "plan_bundle": plan,
        "plan": plan["resolved"],
        "plan_sha256": plan["sha256"],
        "asset_preflight": preflight,''',
)
edit(
    "tools/evidence.py",
    '''    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    run_state.write_progress(run_dir, "planned", plan_sha256=resolved["plan_sha256"])
    run_state.write_progress(run_dir, "submitted", executor=spec["executor"])

    environment, environment_evidence = execution_environment.resolve_environment(
        resolved["executor"], root, seed
    )''',
    '''    environment, environment_evidence = execution_environment.resolve_environment(
        resolved["executor"], root, seed
    )
    plan_bundle = plan_identity.resolve_binding(
        resolved["plan_bundle"], resolved["asset_preflight"], environment_evidence
    )
    identities = plan_identity.identity_summary(plan_bundle)
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    run_state.write_progress(run_dir, "planned", **identities)
    run_state.write_progress(
        run_dir,
        "submitted",
        executor=spec["executor"],
        binding_sha256=identities["binding_sha256"],
    )''',
)
edit(
    "tools/evidence.py",
    '''        "plan": {
            "sha256": resolved["plan_sha256"],
            "resolved": resolved["plan"],
        },''',
    '''        "plan": plan_bundle,''',
)
insert_before = "\n\ndef recorded_input_drift(manifest: dict[str, Any], root: Path) -> list[str]:"
identity_drift = '''

def recorded_plan_identity_drift(manifest: dict[str, Any], root: Path) -> list[str]:
    recorded = manifest.get("plan")
    if not isinstance(recorded, dict) or not all(
        isinstance(recorded.get(layer), dict) for layer in ("protocol", "execution", "binding")
    ):
        return []
    spec_path = root / manifest["spec"]["path"]
    current = validate_supported_spec(spec_path, root)
    _, environment_evidence = execution_environment.resolve_environment(
        current["executor"], root, current["seed"]
    )
    bundle = plan_identity.resolve_binding(
        current["plan_bundle"], current["asset_preflight"], environment_evidence
    )
    labels = {
        "protocol": "protocol identity changed",
        "execution": "execution plan identity changed",
        "binding": "binding identity changed",
    }
    return [
        labels[layer]
        for layer in ("protocol", "execution", "binding")
        if recorded[layer].get("sha256") != bundle[layer]["sha256"]
    ]
'''
edit("tools/evidence.py", insert_before, identity_drift + insert_before)
edit(
    "tools/evidence.py",
    '''    drift: list[str] = []
    for relative, expected, label in checks:''',
    '''    drift = recorded_plan_identity_drift(manifest, root)
    for relative, expected, label in checks:''',
)

# Terminal lifecycle evidence carries the same identity summary without breaking v1 readers.
edit("tools/run_state.py", "RESULT_VERSION = 1", "RESULT_VERSION = 2")
edit(
    "tools/run_state.py",
    '''        "termination": manifest.get("termination"),
        "completion": report,''',
    '''        "termination": manifest.get("termination"),
        "identities": {
            "protocol_sha256": manifest["plan"]["protocol"]["sha256"],
            "execution_plan_sha256": manifest["plan"]["execution"]["sha256"],
            "binding_sha256": manifest["plan"]["binding"]["sha256"],
        },
        "completion": report,''',
)
edit(
    "tools/run_state.py",
    '''        "plan": manifest.get("plan"),
        "phases": manifest.get("phases", []),''',
    '''        "plan": manifest.get("plan"),
        "identities": status.get("identities", {}),
        "phases": manifest.get("phases", []),''',
)

# Schemas accept legacy plan/result evidence while requiring layered fields for new versions.
manifest_schema_path = ROOT / "schemas/run-manifest.schema.json"
manifest_schema = json.loads(manifest_schema_path.read_text(encoding="utf-8"))
manifest_schema["$defs"]["identity_record"] = {
    "type": "object",
    "required": ["sha256", "resolved"],
    "properties": {
        "sha256": {"$ref": "#/$defs/sha256"},
        "resolved": {"type": "object"},
    },
    "additionalProperties": False,
}
plan_schema = manifest_schema["properties"]["plan"]
plan_schema["properties"].update(
    {
        "identity_version": {"const": 1},
        "protocol": {"$ref": "#/$defs/identity_record"},
        "execution": {"$ref": "#/$defs/identity_record"},
        "binding": {"$ref": "#/$defs/identity_record"},
    }
)
plan_schema["oneOf"] = [
    {
        "required": ["sha256", "resolved"],
        "not": {"required": ["identity_version"]},
    },
    {
        "required": [
            "identity_version",
            "protocol",
            "execution",
            "binding",
            "sha256",
            "resolved",
        ]
    },
]
manifest_schema_path.write_text(json.dumps(manifest_schema, indent=2) + "\n", encoding="utf-8")

result_schema_path = ROOT / "schemas/run-result.schema.json"
result_schema = json.loads(result_schema_path.read_text(encoding="utf-8"))
result_schema["properties"]["result_version"] = {"enum": [1, 2]}
result_schema["properties"]["identities"] = {
    "type": "object",
    "required": ["protocol_sha256", "execution_plan_sha256", "binding_sha256"],
    "properties": {
        "protocol_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "execution_plan_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        "binding_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    },
    "additionalProperties": False,
}
result_schema["allOf"] = [
    {
        "if": {"properties": {"result_version": {"const": 2}}},
        "then": {"required": ["identities"]},
    }
]
result_schema_path.write_text(json.dumps(result_schema, indent=2) + "\n", encoding="utf-8")

# Integration coverage for manifest/result identities and layer-specific replay drift.
(ROOT / "tests/test_plan_identity_evidence.py").write_text(
    '''from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\nimport yaml\n\nfrom tools import evidence\n\nfrom test_evidence import configure_outputs\n\n\ndef load(path: Path) -> dict[str, object]:\n    value = yaml.safe_load(path.read_text(encoding="utf-8"))\n    assert isinstance(value, dict)\n    return value\n\n\ndef write(path: Path, value: dict[str, object]) -> None:\n    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")\n\n\ndef run(root: Path) -> tuple[Path, dict[str, object]]:\n    spec = configure_outputs(root)\n    manifest_path, code = evidence.run_spec(spec, root)\n    assert code == 0\n    return manifest_path, json.loads(manifest_path.read_text(encoding="utf-8"))\n\n\ndef test_run_and_terminal_result_record_all_identity_layers(tmp_path: Path) -> None:\n    manifest_path, manifest = run(tmp_path)\n    plan = manifest["plan"]\n    assert plan["sha256"] == plan["execution"]["sha256"]\n    assert plan["resolved"] == plan["execution"]["resolved"]\n    result = json.loads((manifest_path.parent / "result.json").read_text(encoding="utf-8"))\n    assert result["result_version"] == 2\n    assert result["identities"] == {\n        "protocol_sha256": plan["protocol"]["sha256"],\n        "execution_plan_sha256": plan["execution"]["sha256"],\n        "binding_sha256": plan["binding"]["sha256"],\n    }\n\n\ndef test_protocol_drift_is_reported_separately(tmp_path: Path) -> None:\n    _, manifest = run(tmp_path)\n    spec_path = tmp_path / manifest["spec"]["path"]\n    spec = load(spec_path)\n    spec["scientific_parameters"] = {"temperature": 0.4}\n    write(spec_path, spec)\n    drift = evidence.recorded_plan_identity_drift(manifest, tmp_path)\n    assert "protocol identity changed" in drift\n    assert "execution plan identity changed" in drift\n    assert "binding identity changed" not in drift\n\n\ndef test_config_drift_changes_execution_only(tmp_path: Path) -> None:\n    _, manifest = run(tmp_path)\n    (tmp_path / "configs/base.yaml").write_text("seed: 1\\n", encoding="utf-8")\n    drift = evidence.recorded_plan_identity_drift(manifest, tmp_path)\n    assert drift == ["execution plan identity changed"]\n\n\ndef test_profile_drift_changes_binding_only(tmp_path: Path) -> None:\n    _, manifest = run(tmp_path)\n    profile_path = tmp_path / "infra/profiles/local.yaml"\n    profile = load(profile_path)\n    profile["environment"] = {"PYTHONUNBUFFERED": "1", "WORKERS": "2"}\n    write(profile_path, profile)\n    drift = evidence.recorded_plan_identity_drift(manifest, tmp_path)\n    assert drift == ["binding identity changed"]\n''',
    encoding="utf-8",
)

# Template lifecycle and ownership.
edit("tools/initialize_project.py", "TEMPLATE_VERSION = 4", "TEMPLATE_VERSION = 5")
edit("PROJECT.yaml", "  version: 4\n", "  version: 5\n")
compat_path = ROOT / "tools/template_compat.py"
compat = compat_path.read_text(encoding="utf-8")
registry = "MIGRATIONS: dict[int, Migration] = {2: migrate_to_v2, 3: migrate_to_v3, 4: migrate_to_v4}"
if compat.count(registry) != 1:
    raise RuntimeError("template migration registry changed")
compat = compat.replace(
    registry,
    '''def migrate_to_v5(root: Path, state: dict[str, Any]) -> list[str]:
    return []


MIGRATIONS: dict[int, Migration] = {
    2: migrate_to_v2,
    3: migrate_to_v3,
    4: migrate_to_v4,
    5: migrate_to_v5,
}''',
)
compat_path.write_text(compat, encoding="utf-8")
for relative in ["tests/test_initialize_project.py", "tests/test_template_compat.py"]:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    text = text.replace("version: 4\\n", "version: 5\\n")
    text = text.replace('"version": 4,', '"version": 5,')
    text = text.replace("Template v4", "Template v5")
    path.write_text(text, encoding="utf-8")

edit(
    ".agents/governance/REPO_UNITS.yaml",
    "  - tools/phase_graph.py\n",
    "  - tools/phase_graph.py\n  - tools/plan_identity.py\n",
)
edit(
    ".agents/governance/CONTRACT.md",
    "- Every execution is preceded by a deterministic, side-effect-free plan.",
    "- Experiment identity is layered. The protocol identity contains scientific intent and phase\n"
    "  topology; the execution-plan identity binds protocol to parsed config, commands, code,\n"
    "  environment lock, budget, and artifact contract; the binding identity records the selected\n"
    "  executor profile, process-environment policy, and resolved physical assets. Profile changes\n"
    "  never silently rewrite protocol identity.\n"
    "- Every execution is preceded by a deterministic, side-effect-free plan.",
)

Path(__file__).unlink()
