from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def edit(relative: str, old: str, new: str, *, count: int = 1) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"{relative}: expected {count}, found {actual}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


# Research validation: one command source, command-free evaluation, parsed config, explicit env policy.
edit("tools/research.py", "import input_identity\n", "import execution_environment\nimport input_identity\n")
edit("tools/research.py", '    "command",\n', "")
edit(
    "tools/research.py",
    '    validate_string_list(record.get("capabilities"), "executor capabilities")',
    '    validate_string_list(record.get("capabilities"), "executor capabilities")\n'
    '    try:\n'
    '        execution_environment.declared_environment(record, root)\n'
    '    except execution_environment.ExecutionEnvironmentError as exc:\n'
    '        raise SpecError(str(exc)) from exc',
)
edit("tools/research.py", '    command_argv(record.get("command"))\n', "")
edit(
    "tools/research.py",
    '    resolved_inputs = input_identity.resolve_inputs(spec.get("inputs", []), root)\n'
    '    missing = REQUIRED_EXPERIMENT_FIELDS - spec.keys()',
    '    resolved_inputs = input_identity.resolve_inputs(spec.get("inputs", []), root)\n'
    '    has_command = "command" in spec\n'
    '    has_phases = "phases" in spec\n'
    '    if has_command == has_phases:\n'
    '        raise SpecError("experiment must declare exactly one of command or phases")\n'
    '    missing = REQUIRED_EXPERIMENT_FIELDS - spec.keys()',
)
edit(
    "tools/research.py",
    '    config_path = repository_path(root, spec["config"], "config")\n'
    '    environment_path, environment = environments[spec["environment"]]',
    '    config_path = repository_path(root, spec["config"], "config")\n'
    '    config = load_yaml(config_path)\n'
    '    environment_path, environment = environments[spec["environment"]]',
)
edit(
    "tools/research.py",
    '    argv = command_argv(spec["command"])\n'
    '    if command_argv(evaluation["command"]) != argv:\n'
    '        raise SpecError(\n'
    '            f"spec command does not match evaluation {spec[\'evaluation\']!r}: "\n'
    '            f"{evaluation[\'command\']!r}"\n'
    '        )',
    '    argv = command_argv(spec["command"]) if "command" in spec else []',
)
edit(
    "tools/research.py",
    '        "spec": spec,\n'
    '        "spec_path": path,\n'
    '        "config_path": config_path,',
    '        "root": root,\n'
    '        "spec": spec,\n'
    '        "spec_path": path,\n'
    '        "config_path": config_path,\n'
    '        "config": config,',
)
edit(
    "tools/research.py",
    '        metric_observation.MetricObservationError,\n'
    '        OSError,',
    '        metric_observation.MetricObservationError,\n'
    '        execution_environment.ExecutionEnvironmentError,\n'
    '        OSError,',
)

# Plans contain normalized phases, parsed config, and the declared environment policy.
edit("tools/experiment_plan.py", "import phase_graph\n", "import execution_environment\nimport phase_graph\n")
edit(
    "tools/experiment_plan.py",
    '        "config": spec["config"],\n'
    '        "environment": spec["environment"],\n'
    '        "executor": spec["executor"],\n'
    '        "evaluation": spec["evaluation"],\n'
    '        "command": list(resolved["argv"]),\n'
    '        "phases": phases,',
    '        "config": spec["config"],\n'
    '        "effective_config": {\n'
    '            "path": spec["config"],\n'
    '            "sha256": research.sha256_file(resolved["config_path"]),\n'
    '            "resolved": deepcopy(resolved["config"]),\n'
    '        },\n'
    '        "environment": spec["environment"],\n'
    '        "executor": spec["executor"],\n'
    '        "evaluation": spec["evaluation"],\n'
    '        "execution_environment": execution_environment.declared_environment(\n'
    '            resolved["executor"], resolved["root"]\n'
    '        ),\n'
    '        "phases": phases,',
)

# Runner uses only explicit/inherited bindings and records their identity.
edit("tools/evidence.py", "import experiment_plan\n", "import execution_environment\nimport experiment_plan\n")
edit(
    "tools/evidence.py",
    '    environment = os.environ.copy()\n'
    '    environment[SEED_ENVIRONMENT_VARIABLE] = str(seed)',
    '    environment, environment_evidence = execution_environment.resolve_environment(\n'
    '        resolved["executor"], root, seed\n'
    '    )',
)
edit(
    "tools/evidence.py",
    '        "config": {\n'
    '            "path": relative(resolved["config_path"]),\n'
    '            "sha256": research.sha256_file(resolved["config_path"]),\n'
    '        },',
    '        "config": {\n'
    '            "path": relative(resolved["config_path"]),\n'
    '            "sha256": research.sha256_file(resolved["config_path"]),\n'
    '            "resolved": resolved["config"],\n'
    '        },',
)
edit(
    "tools/evidence.py",
    '        "executor": {\n'
    '            "id": spec["executor"],\n'
    '            "definition": relative(resolved["executor_path"]),\n'
    '            "definition_sha256": research.sha256_file(resolved["executor_path"]),\n'
    '        },',
    '        "executor": {\n'
    '            "id": spec["executor"],\n'
    '            "definition": relative(resolved["executor_path"]),\n'
    '            "definition_sha256": research.sha256_file(resolved["executor_path"]),\n'
    '            "execution_environment": environment_evidence,\n'
    '        },',
)
edit("tools/evidence.py", '        "command": resolved["argv"],\n', "")
edit(
    "tools/evidence.py",
    '        experiment_plan.PlanError,\n'
    '        metric_observation.MetricObservationError,',
    '        experiment_plan.PlanError,\n'
    '        execution_environment.ExecutionEnvironmentError,\n'
    '        metric_observation.MetricObservationError,',
)

# New manifests use phases only; the old command field remains readable.
run_schema_path = ROOT / "schemas/run-manifest.schema.json"
run_schema = json.loads(run_schema_path.read_text(encoding="utf-8"))
run_schema["required"] = [field for field in run_schema["required"] if field != "command"]
run_schema_path.write_text(json.dumps(run_schema, indent=2) + "\n", encoding="utf-8")

# Fixtures and plan tests.
edit(
    "tests/test_research.py",
    '            "schema_version: 1\\nid: smoke\\ncommand: make smoke\\n"\n'
    '            "purpose: execute the smallest path\\nmetrics:\\n"',
    '            "schema_version: 1\\nid: smoke\\n"\n'
    '            "purpose: execute the smallest path\\nmetrics:\\n"',
)
edit(
    "tests/test_research.py",
    '            "schema_version: 1\\nid: local\\nexecutor: local\\ncapabilities: [cpu]\\n"',
    '            "schema_version: 1\\nid: local\\nexecutor: local\\ncapabilities: [cpu]\\n"\n'
    '            "environment: {PYTHONUNBUFFERED: \'1\'}\\n"\n'
    '            "inherit_environment: [PATH, HOME]\\n"',
)
insert_marker = "\n\ndef test_validate_rejects_unversioned_definition"
addition = '''\n\ndef test_validate_rejects_duplicate_command_sources(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    text = spec_path.read_text(encoding="utf-8")
    spec_path.write_text(
        text + "phases:\\n  - id: main\\n    command: make smoke\\n",
        encoding="utf-8",
    )
    with pytest.raises(research.SpecError, match="exactly one of command or phases"):
        research.validate_all(tmp_path)
'''
edit("tests/test_research.py", insert_marker, addition + insert_marker)

edit(
    "tests/test_evidence.py",
    '        "schema_version: 1\\nid: smoke\\ncommand: make smoke\\n"\n'
    '        "purpose: execute the smallest path\\nmetrics:\\n"',
    '        "schema_version: 1\\nid: smoke\\n"\n'
    '        "purpose: execute the smallest path\\nmetrics:\\n"',
)
edit(
    "tests/test_experiment_plan.py",
    '    assert document["resolved"]["command"] == ["make", "smoke"]',
    '    assert document["resolved"]["phases"][0]["command"] == ["make", "smoke"]',
)
insert_marker = "\n\ndef test_matrix_expansion_has_stable_cell_ids"
addition = '''\n\ndef test_config_content_changes_plan_identity(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    first = plan_tool.plan_spec(spec_path, tmp_path)
    (tmp_path / "configs/base.yaml").write_text("seed: 1\\n", encoding="utf-8")
    second = plan_tool.plan_spec(spec_path, tmp_path)
    assert first["sha256"] != second["sha256"]
    assert second["resolved"]["effective_config"]["resolved"] == {"seed": 1}
'''
edit("tests/test_experiment_plan.py", insert_marker, addition + insert_marker)

# Focused environment tests.
(ROOT / "tests/test_execution_environment.py").write_text(
    '''from __future__ import annotations\n\nfrom pathlib import Path\n\nimport pytest\n\nfrom tools import execution_environment\n\n\ndef profile() -> dict[str, object]:\n    return {\n        "environment": {"OUTPUT_ROOT": "${PROJECT_ROOT}/outputs"},\n        "inherit_environment": ["PATH"],\n    }\n\n\ndef test_only_declared_environment_reaches_execution(tmp_path: Path) -> None:\n    environment, evidence = execution_environment.resolve_environment(\n        profile(), tmp_path, 7, {"PATH": "/bin", "UNDECLARED": "hidden"}\n    )\n    assert environment == {\n        "OUTPUT_ROOT": f"{tmp_path.resolve()}/outputs",\n        "PATH": "/bin",\n        "RESEARCH_SEED": "7",\n    }\n    assert "UNDECLARED" not in environment\n    assert evidence["inherited"][0]["name"] == "PATH"\n    assert "value" not in evidence["inherited"][0]\n\n\ndef test_missing_inherited_variable_is_rejected(tmp_path: Path) -> None:\n    with pytest.raises(\n        execution_environment.ExecutionEnvironmentError, match="required inherited"\n    ):\n        execution_environment.resolve_environment(profile(), tmp_path, 0, {})\n\n\ndef test_secret_like_names_are_rejected(tmp_path: Path) -> None:\n    with pytest.raises(execution_environment.ExecutionEnvironmentError, match="secret-bearing"):\n        execution_environment.declared_environment(\n            {"environment": {"API_TOKEN": "not-a-secret"}}, tmp_path\n        )\n\n\ndef test_undeclared_placeholder_is_rejected(tmp_path: Path) -> None:\n    with pytest.raises(execution_environment.ExecutionEnvironmentError, match="undeclared"):\n        execution_environment.declared_environment(\n            {"environment": {"OUTPUT": "${HOME}/outputs"}}, tmp_path\n        )\n''',
    encoding="utf-8",
)

# Template v4 migration updates the shipped smoke definitions and local profile.
edit("tools/initialize_project.py", "TEMPLATE_VERSION = 3", "TEMPLATE_VERSION = 4")
edit("PROJECT.yaml", "  version: 3\n", "  version: 4\n")
compat_path = ROOT / "tools/template_compat.py"
compat = compat_path.read_text(encoding="utf-8")
marker = "\n\nMIGRATIONS: dict[int, Migration] = {2: migrate_to_v2, 3: migrate_to_v3}"
if marker not in compat:
    raise RuntimeError("template migration registry changed")
migration = '''\n\ndef migrate_to_v4(root: Path, state: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    spec_path = root / "experiments/specs/smoke.yaml"
    if spec_path.is_file():
        spec = initialize_project.load_yaml(spec_path)
        if spec.get("phases") and "command" in spec:
            spec.pop("command")
            initialize_project.write_text(spec_path, initialize_project.dump_yaml(spec))
            changes.append("write experiments/specs/smoke.yaml")
    evaluation_path = root / "evals/smoke.yaml"
    if evaluation_path.is_file():
        evaluation = initialize_project.load_yaml(evaluation_path)
        if "command" in evaluation:
            evaluation.pop("command")
            initialize_project.write_text(
                evaluation_path, initialize_project.dump_yaml(evaluation)
            )
            changes.append("write evals/smoke.yaml")
    profile_path = root / "infra/profiles/local.yaml"
    if profile_path.is_file():
        profile = initialize_project.load_yaml(profile_path)
        profile.setdefault("environment", {"PYTHONUNBUFFERED": "1"})
        profile.setdefault("inherit_environment", ["PATH", "HOME"])
        initialize_project.write_text(profile_path, initialize_project.dump_yaml(profile))
        changes.append("write infra/profiles/local.yaml")
    return changes
'''
compat = compat.replace(
    marker,
    migration + "\n\nMIGRATIONS: dict[int, Migration] = {2: migrate_to_v2, 3: migrate_to_v3, 4: migrate_to_v4}",
)
compat_path.write_text(compat, encoding="utf-8")

# Update current-version test fixtures without rewriting explicit historical versions.
for relative in ["tests/test_initialize_project.py", "tests/test_template_compat.py"]:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    text = text.replace("version: 3\\n", "version: 4\\n")
    text = text.replace('"version": 3,', '"version": 4,')
    text = text.replace("Template v3", "Template v4")
    path.write_text(text, encoding="utf-8")

# Durable documentation and ownership.
edit(
    ".agents/governance/REPO_UNITS.yaml",
    "  - tools/evidence.py\n",
    "  - tools/evidence.py\n  - tools/execution_environment.py\n",
)
edit(
    ".agents/governance/CONTRACT.md",
    "- Every execution is preceded by a deterministic, side-effect-free plan.",
    "- Every experiment has exactly one command source per phase. Evaluation definitions describe\n"
    "  extraction and interpretation only; they never duplicate execution commands. Top-level\n"
    "  commands are a legacy one-phase shorthand and cannot coexist with explicit phases.\n"
    "- Parsed configuration and declared executor environment policy are embedded in every\n"
    "  deterministic plan. The runner builds a minimal environment from explicit values and a\n"
    "  reviewed inheritance allowlist; it never copies the complete host environment.\n"
    "- Every execution is preceded by a deterministic, side-effect-free plan.",
)

Path(__file__).unlink()
